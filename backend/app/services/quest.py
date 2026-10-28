"""Daily Quest service."""
import json
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx
import pytz
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.models.quest import DailyQuest, DailyQuestDifficulty, DailyQuestStatus, DailyQuestType, QuestLimitConfig
from app.models.task import Task, TaskStatus, UserTask
from app.models.user import User, UserRole, UserStatus
from app.services.ai_json import ai_json_service
from app.services.notification import notification_service

logger = logging.getLogger(__name__)

VN_TIMEZONE = pytz.timezone("Asia/Ho_Chi_Minh")
ACTIVE_QUEST_STATUSES = [
    DailyQuestStatus.PENDING,
    DailyQuestStatus.IN_PROGRESS,
    DailyQuestStatus.SUBMITTED,
    DailyQuestStatus.AI_REVIEWED,
    DailyQuestStatus.REJECTED,
]


class DailyQuestService:
    """Business logic for generated Daily Quests."""

    def _now(self) -> datetime:
        return datetime.now(VN_TIMEZONE).replace(tzinfo=None)

    def _gemini_models(self, configured_model: str) -> List[str]:
        models = [configured_model.strip()] if configured_model.strip() else []
        models.extend(["gemini-3.6-flash", "gemini-3.5-flash"])
        return list(dict.fromkeys(model for model in models if model))

    def _reset_hour(self) -> int:
        settings = get_settings()
        return max(0, min(settings.DAILY_QUEST_RESET_HOUR, 23))

    def _reset_window(self, now: Optional[datetime] = None) -> tuple[datetime, datetime]:
        current = now or self._now()
        reset_hour = self._reset_hour()
        today_reset = current.replace(hour=reset_hour, minute=0, second=0, microsecond=0)
        if current >= today_reset:
            start_at = today_reset
            reset_at = today_reset + timedelta(days=1)
        else:
            start_at = today_reset - timedelta(days=1)
            reset_at = today_reset
        return start_at, reset_at

    def _ensure_eligible_user(self, user: User) -> None:
        if not (user.has_role(UserRole.CANDIDATE.value) or user.has_role(UserRole.MEMBER.value)):
            raise ForbiddenException("Daily Quest chỉ áp dụng cho candidate/member")

    def _coerce_naive_vn_datetime(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value
        return value.astimezone(VN_TIMEZONE).replace(tzinfo=None)

    async def _get_current_window_quests(
        self,
        db: AsyncSession,
        user_id: UUID,
        start_at: datetime,
        reset_at: datetime,
    ) -> List[DailyQuest]:
        result = await db.execute(
            select(DailyQuest)
            .where(
                DailyQuest.user_id == user_id,
                DailyQuest.quest_type == DailyQuestType.DAILY,
                DailyQuest.created_at >= start_at,
                DailyQuest.created_at < reset_at,
            )
            .order_by(DailyQuest.created_at, DailyQuest.id)
        )
        return list(result.scalars().all())

    async def _expire_old_quests(
        self,
        db: AsyncSession,
        now: Optional[datetime] = None,
        user_id: Optional[UUID] = None,
    ) -> int:
        current = now or self._now()
        query = select(DailyQuest).where(
            DailyQuest.status.in_(ACTIVE_QUEST_STATUSES),
            DailyQuest.expires_at <= current,
        )
        if user_id:
            query = query.where(DailyQuest.user_id == user_id)

        quests = list((await db.execute(query)).scalars().all())
        for quest in quests:
            quest.status = DailyQuestStatus.EXPIRED
        return len(quests)

    async def expire_old_quests(self, db: AsyncSession) -> int:
        """Expire all active quests whose reset time has passed."""
        expired_count = await self._expire_old_quests(db)
        await db.commit()
        if expired_count:
            logger.info("Expired %s Daily Quests", expired_count)
        return expired_count

    async def resolve_quest_limit(self, db: AsyncSession, user: User) -> int:
        """Resolve limit from config table, falling back to env."""
        settings = get_settings()
        roles = user.roles or []
        result = await db.execute(
            select(QuestLimitConfig)
            .where(
                QuestLimitConfig.is_active == True,
                QuestLimitConfig.min_level <= user.level,
                or_(QuestLimitConfig.max_level.is_(None), QuestLimitConfig.max_level >= user.level),
                or_(QuestLimitConfig.role.is_(None), QuestLimitConfig.role.in_(roles)),
            )
            .order_by(
                QuestLimitConfig.role.is_(None),
                QuestLimitConfig.min_level.desc(),
                QuestLimitConfig.quest_limit.desc(),
            )
            .limit(1)
        )
        config = result.scalar_one_or_none()
        limit = config.quest_limit if config else settings.DAILY_QUEST_LIMIT
        return max(1, min(int(limit), 20))

    async def get_daily_quests(self, db: AsyncSession, user: User) -> dict:
        """Return the current reset-window quests, generating a set if needed."""
        self._ensure_eligible_user(user)
        now = self._now()
        start_at, reset_at = self._reset_window(now)

        await self._expire_old_quests(db, now=now, user_id=user.id)
        quests = await self.generate_daily_quests(db, user, now=now, reset_at=reset_at)

        return await self._build_list_payload(db, user, quests, reset_at)

    async def get_limit_info(self, db: AsyncSession, user: User) -> dict:
        """Return current daily generation/active usage counts."""
        self._ensure_eligible_user(user)
        now = self._now()
        start_at, reset_at = self._reset_window(now)
        await self._expire_old_quests(db, now=now, user_id=user.id)
        quests = await self._get_current_window_quests(db, user.id, start_at, reset_at)
        await db.commit()
        return await self._build_limit_payload(db, user, quests, reset_at)

    async def generate_daily_quests(
        self,
        db: AsyncSession,
        user: User,
        now: Optional[datetime] = None,
        reset_at: Optional[datetime] = None,
    ) -> List[DailyQuest]:
        """Generate one daily quest set for the current reset window."""
        self._ensure_eligible_user(user)
        current = now or self._now()
        start_at, resolved_reset_at = self._reset_window(current)
        expires_at = reset_at or resolved_reset_at
        limit = await self.resolve_quest_limit(db, user)

        await self._expire_old_quests(db, now=current, user_id=user.id)
        existing_today = await self._get_current_window_quests(db, user.id, start_at, expires_at)
        if len(existing_today) >= limit and all(quest.status == DailyQuestStatus.COMPLETED for quest in existing_today):
            await db.commit()
            return existing_today

        active_count = (
            await db.execute(
                select(func.count(DailyQuest.id)).where(
                    DailyQuest.user_id == user.id,
                    DailyQuest.quest_type == DailyQuestType.DAILY,
                    DailyQuest.status.in_(ACTIVE_QUEST_STATUSES),
                    DailyQuest.expires_at > current,
                )
            )
        ).scalar() or 0
        slots = min(
            max(0, limit - len(existing_today)),
            max(0, limit - active_count),
        )
        if slots <= 0:
            await db.commit()
            return existing_today

        context = await self._build_candidate_context(db, user)
        quest_items = await self._generate_quest_items(user, context, slots)

        quests: List[DailyQuest] = []
        for item in quest_items[:slots]:
            quest = DailyQuest(
                user_id=user.id,
                title=item["title"],
                description=item["description"],
                quest_type=DailyQuestType.DAILY,
                difficulty=item["difficulty"],
                xp_reward=item["xp_reward"],
                status=DailyQuestStatus.PENDING,
                created_at=current,
                expires_at=expires_at,
                auto_pass_score=get_settings().AI_AUTO_PASS_SCORE,
            )
            db.add(quest)
            quests.append(quest)

        if quests:
            await notification_service.create_notification(
                db,
                user_id=user.id,
                event_type="DAILY_QUEST_GENERATED",
                title="Daily Quest mới đã sẵn sàng",
                message=f"Hôm nay bạn có {len(quests)} quest mới trước {expires_at.strftime('%H:%M %d/%m/%Y')}.",
                payload={"count": len(quests), "reset_at": expires_at.isoformat()},
            )

        await db.commit()
        for quest in quests:
            await db.refresh(quest)
        return existing_today + quests

    async def complete_quest(self, db: AsyncSession, quest_id: UUID, user: User) -> dict:
        """Legacy endpoint kept for clients that have not migrated to proof submit."""
        self._ensure_eligible_user(user)
        now = self._now()
        await self._expire_old_quests(db, now=now, user_id=user.id)

        quest = (
            await db.execute(
                select(DailyQuest).where(DailyQuest.id == quest_id, DailyQuest.user_id == user.id)
            )
        ).scalar_one_or_none()
        if not quest:
            raise NotFoundException("Daily Quest not found")
        if quest.status == DailyQuestStatus.COMPLETED:
            return {
                "quest": quest,
                "current_xp": user.current_xp,
                "level": user.level,
            }
        if quest.status == DailyQuestStatus.EXPIRED or quest.expires_at <= now:
            quest.status = DailyQuestStatus.EXPIRED
            await db.commit()
            raise BadRequestException("Daily Quest đã hết hạn")

        raise BadRequestException("Vui lòng nộp minh chứng để AI chấm điểm Daily Quest")

    async def list_limit_quests(self, db: AsyncSession, user: User) -> dict:
        """Return Limit Quests assigned to the current user."""
        self._ensure_eligible_user(user)
        now = self._now()
        await self._expire_old_quests(db, now=now, user_id=user.id)
        result = await db.execute(
            select(DailyQuest)
            .where(
                DailyQuest.user_id == user.id,
                DailyQuest.quest_type == DailyQuestType.LIMIT,
            )
            .order_by(DailyQuest.created_at.desc(), DailyQuest.id)
        )
        quests = list(result.scalars().all())
        await db.commit()

        active_expirations = [
            quest.expires_at for quest in quests if quest.status in ACTIVE_QUEST_STATUSES and quest.expires_at > now
        ]
        reset_at = min(active_expirations) if active_expirations else now
        completed_count = sum(1 for quest in quests if quest.status == DailyQuestStatus.COMPLETED)
        expired_count = sum(1 for quest in quests if quest.status == DailyQuestStatus.EXPIRED)
        active_count = sum(1 for quest in quests if quest.status in ACTIVE_QUEST_STATUSES)
        return {
            "quests": quests,
            "total": len(quests),
            "reset_at": reset_at,
            "max_quests": len(quests),
            "active_count": active_count,
            "completed_count": completed_count,
            "expired_count": expired_count,
        }

    async def create_limit_quest(self, db: AsyncSession, admin: User, data) -> dict:
        """Create admin-only Limit Quest assignments for coaching/offline proof."""
        if not admin.is_admin():
            raise ForbiddenException("Admin access required")

        now = self._now()
        expires_at = data.expires_at or (now + timedelta(days=7))
        expires_at = self._coerce_naive_vn_datetime(expires_at)
        if expires_at <= now:
            raise BadRequestException("expires_at must be in the future")

        users = list(
            (
                await db.execute(
                    select(User).where(
                        User.id.in_(data.target_user_ids),
                        User.status == UserStatus.ACTIVE,
                        or_(User.roles.any(UserRole.CANDIDATE.value), User.roles.any(UserRole.MEMBER.value)),
                    )
                )
            ).scalars().all()
        )
        if not users:
            raise BadRequestException("No active candidate/member users found for Limit Quest")

        quests: List[DailyQuest] = []
        for target in users:
            quest = DailyQuest(
                user_id=target.id,
                created_by_id=admin.id,
                title=data.title,
                description=data.description,
                quest_type=DailyQuestType.LIMIT,
                difficulty=data.difficulty,
                xp_reward=data.xp_reward,
                status=DailyQuestStatus.PENDING,
                created_at=now,
                expires_at=expires_at,
                requires_image_proof=True,
                auto_pass_score=data.auto_pass_score,
            )
            db.add(quest)
            quests.append(quest)

        for target in users:
            await notification_service.create_notification(
                db,
                user_id=target.id,
                event_type="LIMIT_QUEST_CREATED",
                title="Limit Quest mới",
                message=f"Bạn có Limit Quest mới cần nộp ảnh minh chứng trước {expires_at.strftime('%H:%M %d/%m/%Y')}.",
                actor_id=admin.id,
                payload={"title": data.title, "expires_at": expires_at.isoformat()},
            )

        await db.commit()
        for quest in quests:
            await db.refresh(quest)
        return {"quests": quests, "created_count": len(quests)}

    async def submit_quest_proof(
        self,
        db: AsyncSession,
        quest_id: UUID,
        user: User,
        proof_text: Optional[str] = None,
        proof_link: Optional[str] = None,
        proof_image_url: Optional[str] = None,
        proof_image_name: Optional[str] = None,
    ) -> dict:
        """Submit proof and let AI decide whether the quest passes."""
        self._ensure_eligible_user(user)
        now = self._now()
        await self._expire_old_quests(db, now=now, user_id=user.id)

        quest = (
            await db.execute(
                select(DailyQuest).where(DailyQuest.id == quest_id, DailyQuest.user_id == user.id)
            )
        ).scalar_one_or_none()
        if not quest:
            raise NotFoundException("Quest not found")
        if quest.status == DailyQuestStatus.COMPLETED:
            raise BadRequestException("Quest already completed")
        if quest.status == DailyQuestStatus.EXPIRED or quest.expires_at <= now:
            quest.status = DailyQuestStatus.EXPIRED
            await db.commit()
            raise BadRequestException("Quest đã hết hạn")

        clean_text = (proof_text or "").strip()
        clean_link = (proof_link or "").strip()
        if quest.requires_image_proof and not (proof_image_url or quest.proof_image_url):
            raise BadRequestException("Limit Quest cần ảnh minh chứng")
        if not (clean_text or clean_link or proof_image_url or quest.proof_image_url):
            raise BadRequestException("Vui lòng nộp minh chứng để AI chấm điểm")

        quest.proof_text = clean_text or quest.proof_text
        quest.proof_link = clean_link or quest.proof_link
        quest.proof_image_url = proof_image_url or quest.proof_image_url
        quest.proof_image_name = proof_image_name or quest.proof_image_name
        quest.submitted_at = now
        quest.status = DailyQuestStatus.SUBMITTED

        review = await self._grade_quest_submission(quest, user)
        quest.ai_score = review["score"]
        quest.ai_feedback = review["feedback"]
        quest.reviewed_at = now

        passed = review["passed"]
        if passed:
            quest.status = DailyQuestStatus.COMPLETED
            quest.completed_at = now
            await self._award_quest_xp(user, quest)
        else:
            quest.status = DailyQuestStatus.REJECTED

        await notification_service.create_notification(
            db,
            user_id=user.id,
            event_type="QUEST_AI_REVIEWED",
            title="AI đã chấm minh chứng quest",
            message=quest.ai_feedback or ("Quest đã đạt." if passed else "Quest cần bổ sung minh chứng."),
            payload={
                "quest_id": str(quest.id),
                "quest_type": quest.quest_type.value,
                "ai_score": quest.ai_score,
                "passed": passed,
            },
        )

        await db.commit()
        await db.refresh(quest)
        await db.refresh(user)
        return {
            "quest": quest,
            "current_xp": user.current_xp,
            "level": user.level,
            "passed": passed,
        }

    async def _award_quest_xp(self, user: User, quest: DailyQuest) -> None:
        user.current_xp += quest.xp_reward
        user.level = user.calculate_level()

    async def _grade_quest_submission(self, quest: DailyQuest, user: User) -> dict:
        system_prompt = (
            "Bạn là AI reviewer của TLMS. Chấm minh chứng quest công bằng theo thang 0-100. "
            "Limit Quest là coaching 1:1 hoặc họp offline và bắt buộc có ảnh minh chứng. "
            "Trả về đúng JSON: {\"score\": number, \"feedback\": string, \"passed\": boolean}."
        )
        user_prompt = json.dumps(
            {
                "quest": {
                    "type": quest.quest_type.value,
                    "title": quest.title,
                    "description": quest.description,
                    "difficulty": quest.difficulty.value,
                    "xp_reward": quest.xp_reward,
                    "requires_image_proof": quest.requires_image_proof,
                    "auto_pass_score": quest.auto_pass_score,
                },
                "candidate": {
                    "level": user.level,
                    "current_xp": user.current_xp,
                    "roles": user.roles or [],
                },
                "proof": {
                    "text": quest.proof_text,
                    "link": quest.proof_link,
                    "image_url": quest.proof_image_url,
                    "has_image": bool(quest.proof_image_url),
                },
            },
            ensure_ascii=False,
        )
        try:
            result = await ai_json_service.generate_json(system_prompt, user_prompt, max_tokens=500, temperature=0.1)
            score = round(float(result.get("score", 0)), 1)
            score = min(max(score, 0.0), 100.0)
            feedback = str(result.get("feedback") or "").strip()
            passed = bool(result.get("passed", score >= quest.auto_pass_score)) and score >= quest.auto_pass_score
            return {
                "score": score,
                "feedback": feedback or ("Minh chứng đạt yêu cầu." if passed else "Minh chứng chưa đủ rõ để cộng XP."),
                "passed": passed,
            }
        except Exception as exc:
            logger.warning("Quest AI grading failed for %s: %s", quest.id, exc)
            score = self._fallback_submission_score(quest)
            passed = score >= quest.auto_pass_score
            return {
                "score": score,
                "feedback": "AI provider lỗi tạm thời; hệ thống đã dùng rule fallback dựa trên minh chứng đã nộp.",
                "passed": passed,
            }

    def _fallback_submission_score(self, quest: DailyQuest) -> float:
        score = 35.0
        if quest.proof_text and len(quest.proof_text.split()) >= 6:
            score += 20.0
        if quest.proof_link:
            score += 20.0
        if quest.proof_image_url:
            score += 35.0 if quest.quest_type == DailyQuestType.LIMIT else 20.0
        if quest.requires_image_proof and not quest.proof_image_url:
            return 0.0
        return round(min(score, 100.0), 1)

    async def reset_daily_quests_for_all(self, db: AsyncSession) -> dict:
        """Scheduler entrypoint: expire old quests and generate a fresh set."""
        expired_count = await self._expire_old_quests(db)
        result = await db.execute(
            select(User).where(
                User.status == UserStatus.ACTIVE,
                or_(User.roles.any(UserRole.CANDIDATE.value), User.roles.any(UserRole.MEMBER.value)),
            )
        )
        users = list(result.scalars().all())
        generated_count = 0
        failed_count = 0
        now = self._now()
        start_at, reset_at = self._reset_window(now)

        for user in users:
            try:
                before_ids = {
                    quest.id
                    for quest in await self._get_current_window_quests(db, user.id, start_at, reset_at)
                }
                quests = await self.generate_daily_quests(db, user, now=now, reset_at=reset_at)
                generated_count += len([quest for quest in quests if quest.id not in before_ids])
            except Exception as exc:
                failed_count += 1
                logger.error("Failed to generate Daily Quests for %s: %s", user.email, exc, exc_info=True)

        await db.commit()
        summary = {
            "expired_count": expired_count,
            "users_processed": len(users),
            "generated_count": generated_count,
            "failed_count": failed_count,
        }
        logger.info("Daily Quest reset completed: %s", summary)
        return summary

    async def _build_candidate_context(self, db: AsyncSession, user: User) -> Dict[str, Any]:
        completed_rows = list(
            (
                await db.execute(
                    select(UserTask, Task)
                    .join(Task, UserTask.task_id == Task.id)
                    .where(
                        UserTask.user_id == user.id,
                        UserTask.status == TaskStatus.COMPLETED,
                    )
                    .order_by(UserTask.completed_at.desc().nullslast())
                    .limit(10)
                )
            ).all()
        )
        completed_tasks = [task.title for _, task in completed_rows]
        completed_skills = sorted({skill for _, task in completed_rows for skill in (task.skill_tags or [])})

        roadmap_tasks = list(
            (
                await db.execute(
                    select(Task)
                    .where(Task.is_active == True, Task.min_level_required <= user.level)
                    .order_by(Task.order_index, Task.created_at)
                    .limit(10)
                )
            ).scalars().all()
        )

        return {
            "level": user.level,
            "current_xp": user.current_xp,
            "member_level": getattr(user.member_level, "value", user.member_level),
            "completed_tasks": completed_tasks,
            "completed_skills": completed_skills,
            "roadmap_tasks": [
                {
                    "title": task.title,
                    "difficulty": getattr(task.difficulty, "value", task.difficulty),
                    "skills": task.skill_tags or [],
                }
                for task in roadmap_tasks
            ],
        }

    async def _generate_quest_items(self, user: User, context: Dict[str, Any], count: int) -> List[Dict[str, Any]]:
        try:
            ai_items = await self._generate_with_ai(user, context, count)
            items = self._normalize_items(ai_items, user.level)
            if len(items) >= count:
                provider = get_settings().AI_PROVIDER.lower().strip()
                logger.info(
                    "Daily Quest AI generated %s quests for %s using %s",
                    count,
                    user.email,
                    provider,
                )
                return items[:count]
            fallback = self._fallback_items(user, context, count - len(items))
            return (items + fallback)[:count]
        except Exception as exc:
            logger.warning("Daily Quest AI generation failed for %s: %s", user.email, exc)
            return self._fallback_items(user, context, count)

    async def _generate_with_ai(self, user: User, context: Dict[str, Any], count: int) -> List[Dict[str, Any]]:
        settings = get_settings()
        provider = settings.AI_PROVIDER.lower().strip()
        api_key = settings.AI_API_KEY.strip()
        if not api_key and provider == "gemini":
            api_key = settings.GEMINI_API_KEY.strip()
        if not api_key and provider == "anthropic":
            api_key = settings.ANTHROPIC_API_KEY.strip()
        if not api_key:
            api_key = settings.OPENAI_API_KEY.strip()
        if not api_key:
            raise RuntimeError("AI_API_KEY/OPENAI_API_KEY/ANTHROPIC_API_KEY/GEMINI_API_KEY is not configured")

        prompt = (
            "Generate Daily Quests for a lab trainee. Return only valid JSON with key quests. "
            "Each quest must have title, description, difficulty in easy|medium|hard, xp_reward. "
            f"Create exactly {count} quests. Keep each description under 160 Vietnamese characters.\n"
            f"Candidate context: {json.dumps(context, ensure_ascii=False)}"
        )
        timeout = httpx.Timeout(60.0)

        async with httpx.AsyncClient(timeout=timeout) as client:
            if provider == "gemini":
                last_error: Exception | None = None
                for model in self._gemini_models(settings.AI_MODEL):
                    try:
                        response = await client.post(
                            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                            headers={
                                "Content-Type": "application/json",
                                "x-goog-api-key": api_key,
                            },
                            json={
                                "systemInstruction": {
                                    "parts": [{"text": "You create concise Vietnamese learning quests and output JSON only."}],
                                },
                                "contents": [
                                    {
                                        "role": "user",
                                        "parts": [{"text": prompt}],
                                    }
                                ],
                                "generationConfig": {
                                    "temperature": 0.6,
                                    "maxOutputTokens": 700,
                                    "responseMimeType": "application/json",
                                    "thinkingConfig": {"thinkingLevel": "low"},
                                    "responseSchema": {
                                        "type": "object",
                                        "properties": {
                                            "quests": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "title": {"type": "string"},
                                                        "description": {"type": "string"},
                                                        "difficulty": {"type": "string", "enum": ["easy", "medium", "hard"]},
                                                        "xp_reward": {"type": "integer"},
                                                    },
                                                    "required": ["title", "description", "difficulty", "xp_reward"],
                                                },
                                            }
                                        },
                                        "required": ["quests"],
                                    },
                                },
                            },
                        )
                        response.raise_for_status()
                        data = response.json()
                        content = "".join(
                            part.get("text", "")
                            for candidate in data.get("candidates", [])
                            for part in candidate.get("content", {}).get("parts", [])
                        )
                        if not content:
                            raise ValueError("Gemini response did not contain text")
                        return self._extract_json_items(content)
                    except (httpx.HTTPError, ValueError, json.JSONDecodeError) as exc:
                        last_error = exc
                        logger.warning("Daily Quest Gemini generation failed with %s: %s", model, exc)
                raise RuntimeError(f"Gemini API failed for all configured models: {last_error}")

            if provider == "anthropic":
                model = settings.AI_MODEL or "claude-3-haiku-20240307"
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": model,
                        "max_tokens": 900,
                        "temperature": 0.6,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )
                response.raise_for_status()
                data = response.json()
                content = "".join(block.get("text", "") for block in data.get("content", []))
                return self._extract_json_items(content)

            model = settings.AI_MODEL or "gpt-4o-mini"
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "temperature": 0.6,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {
                            "role": "system",
                            "content": "You create concise Vietnamese learning quests and output JSON only.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                },
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return self._extract_json_items(content)

    def _extract_json_items(self, content: str) -> List[Dict[str, Any]]:
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if not match:
                raise
            parsed = json.loads(match.group(0))

        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            quests = parsed.get("quests")
            if isinstance(quests, list):
                return quests
        raise ValueError("AI response does not contain quests")

    def _normalize_items(self, items: List[Dict[str, Any]], user_level: int) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        for item in items:
            title = str(item.get("title", "")).strip()
            description = str(item.get("description", "")).strip()
            if not title or not description:
                continue

            difficulty_raw = str(item.get("difficulty", "easy")).lower().strip()
            difficulty_aliases = {
                "dễ": "easy",
                "de": "easy",
                "vừa": "medium",
                "vua": "medium",
                "trung bình": "medium",
                "khó": "hard",
                "kho": "hard",
            }
            difficulty = difficulty_aliases.get(difficulty_raw, difficulty_raw)
            if difficulty not in {value.value for value in DailyQuestDifficulty}:
                difficulty = "medium"

            try:
                xp_reward = int(item.get("xp_reward", self._default_xp(difficulty, user_level)))
            except (TypeError, ValueError):
                xp_reward = self._default_xp(difficulty, user_level)

            normalized.append(
                {
                    "title": title[:255],
                    "description": description,
                    "difficulty": DailyQuestDifficulty(difficulty),
                    "xp_reward": max(5, min(xp_reward, 100)),
                }
            )
        return normalized

    def _fallback_items(self, user: User, context: Dict[str, Any], count: int) -> List[Dict[str, Any]]:
        skills = context.get("completed_skills") or []
        roadmap = context.get("roadmap_tasks") or []
        focus = skills[0] if skills else (roadmap[0]["title"] if roadmap else "kỹ năng nền tảng")
        templates = [
            {
                "title": f"Ôn lại {focus}",
                "description": f"Tóm tắt 3 ý chính bạn đã học về {focus} và ghi lại một điểm còn chưa rõ.",
                "difficulty": DailyQuestDifficulty.EASY,
            },
            {
                "title": "Hoàn thiện một bước nhỏ trong lộ trình",
                "description": "Chọn một task phù hợp level hiện tại, đọc yêu cầu và chuẩn bị kế hoạch thực hiện ngắn.",
                "difficulty": DailyQuestDifficulty.MEDIUM,
            },
            {
                "title": "Thực hành có minh chứng",
                "description": "Tạo một kết quả nhỏ có thể kiểm tra được và lưu link minh chứng cho mentor xem lại.",
                "difficulty": DailyQuestDifficulty.HARD,
            },
            {
                "title": "Củng cố kỹ năng hôm nay",
                "description": "Viết lại cách bạn sẽ áp dụng kiến thức hôm nay vào một task thật trong lab.",
                "difficulty": DailyQuestDifficulty.EASY,
            },
        ]

        items: List[Dict[str, Any]] = []
        for index in range(count):
            template = templates[index % len(templates)]
            difficulty = template["difficulty"]
            items.append(
                {
                    "title": template["title"],
                    "description": template["description"],
                    "difficulty": difficulty,
                    "xp_reward": self._default_xp(difficulty.value, user.level),
                }
            )
        return items

    def _default_xp(self, difficulty: str, user_level: int) -> int:
        base = {
            DailyQuestDifficulty.EASY.value: 10,
            DailyQuestDifficulty.MEDIUM.value: 20,
            DailyQuestDifficulty.HARD.value: 35,
        }.get(difficulty, 15)
        level_bonus = min(max(user_level - 1, 0) * 2, 20)
        return base + level_bonus

    async def _build_list_payload(
        self,
        db: AsyncSession,
        user: User,
        quests: List[DailyQuest],
        reset_at: datetime,
    ) -> dict:
        limit_info = await self._build_limit_payload(db, user, quests, reset_at)
        return {
            "quests": quests,
            "total": len(quests),
            "reset_at": reset_at,
            "max_quests": limit_info["max_quests"],
            "active_count": limit_info["active_count"],
            "completed_count": limit_info["completed_count"],
            "expired_count": limit_info["expired_count"],
        }

    async def _build_limit_payload(
        self,
        db: AsyncSession,
        user: User,
        quests: List[DailyQuest],
        reset_at: datetime,
    ) -> dict:
        max_quests = await self.resolve_quest_limit(db, user)
        active_count = sum(1 for quest in quests if quest.status in ACTIVE_QUEST_STATUSES)
        completed_count = sum(1 for quest in quests if quest.status == DailyQuestStatus.COMPLETED)
        expired_count = sum(1 for quest in quests if quest.status == DailyQuestStatus.EXPIRED)
        generated_count = len(quests)
        return {
            "max_quests": max_quests,
            "generated_count": generated_count,
            "active_count": active_count,
            "completed_count": completed_count,
            "expired_count": expired_count,
            "remaining_generation_slots": max(0, max_quests - generated_count),
            "reset_at": reset_at,
        }

daily_quest_service = DailyQuestService()
