"""Small JSON-only AI client used by scoring services."""
import json
import logging
import re
from typing import Any, Dict

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class AIJsonService:
    """Call the configured LLM provider and parse a JSON object response."""

    def _resolve_api_key(self, provider: str) -> str:
        settings = get_settings()
        if provider == "gemini":
            return settings.GEMINI_API_KEY.strip() or settings.AI_API_KEY.strip()
        if provider == "anthropic":
            return settings.ANTHROPIC_API_KEY.strip() or settings.AI_API_KEY.strip()
        return settings.OPENAI_API_KEY.strip() or settings.AI_API_KEY.strip()

    def _gemini_models(self, configured_model: str) -> list[str]:
        models = [configured_model.strip()] if configured_model.strip() else []
        models.extend(["gemini-2.5-flash", "gemini-flash-latest", "gemini-3.6-flash"])
        return list(dict.fromkeys(model for model in models if model))

    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 700,
        temperature: float = 0.2,
    ) -> Dict[str, Any]:
        settings = get_settings()
        provider = settings.AI_PROVIDER.lower().strip() or "openai"
        api_key = self._resolve_api_key(provider)
        if not api_key:
            raise RuntimeError("AI API key is not configured")

        timeout = httpx.Timeout(60.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            if provider == "gemini":
                last_error: Exception | None = None
                for model in self._gemini_models(settings.AI_MODEL):
                    try:
                        generation_config: Dict[str, Any] = {
                            "temperature": temperature,
                            "maxOutputTokens": max_tokens,
                            "responseMimeType": "application/json",
                        }
                        if model.startswith("gemini-2.5"):
                            generation_config["thinkingConfig"] = {"thinkingBudget": 0}
                        response = await client.post(
                            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                            headers={
                                "Content-Type": "application/json",
                                "x-goog-api-key": api_key,
                            },
                            json={
                                "systemInstruction": {
                                    "parts": [{"text": system_prompt}],
                                },
                                "contents": [
                                    {
                                        "role": "user",
                                        "parts": [{"text": user_prompt}],
                                    }
                                ],
                                "generationConfig": generation_config,
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
                        return self._extract_json_object(content)
                    except (httpx.HTTPError, ValueError, json.JSONDecodeError) as exc:
                        last_error = exc
                        logger.warning("Gemini JSON generation failed with %s: %s", model, exc)
                raise RuntimeError(f"Gemini JSON generation failed for all models: {last_error}")

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
                        "system": system_prompt,
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                        "messages": [{"role": "user", "content": user_prompt}],
                    },
                )
                response.raise_for_status()
                data = response.json()
                content = "".join(block.get("text", "") for block in data.get("content", []))
                return self._extract_json_object(content)

            model = settings.AI_MODEL or "gpt-4o-mini"
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                },
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return self._extract_json_object(content)

    def _extract_json_object(self, content: str) -> Dict[str, Any]:
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if not match:
                raise
            parsed = json.loads(match.group(0))

        if not isinstance(parsed, dict):
            raise ValueError("AI response is not a JSON object")
        return parsed


ai_json_service = AIJsonService()
