export type DailyQuestDifficulty = 'easy' | 'medium' | 'hard';
export type DailyQuestStatus = 'pending' | 'in_progress' | 'submitted' | 'ai_reviewed' | 'completed' | 'rejected' | 'expired';
export type DailyQuestType = 'daily' | 'limit';

export interface DailyQuest {
  id: string;
  user_id: string;
  created_by_id?: string | null;
  title: string;
  description: string;
  quest_type: DailyQuestType;
  difficulty: DailyQuestDifficulty;
  xp_reward: number;
  status: DailyQuestStatus;
  created_at: string;
  expires_at: string;
  completed_at?: string | null;
  proof_text?: string | null;
  proof_link?: string | null;
  proof_image_url?: string | null;
  proof_image_name?: string | null;
  submitted_at?: string | null;
  ai_score?: number | null;
  ai_feedback?: string | null;
  reviewed_at?: string | null;
  requires_image_proof: boolean;
  auto_pass_score: number;
}

export interface DailyQuestListResponse {
  quests: DailyQuest[];
  total: number;
  reset_at: string;
  max_quests: number;
  active_count: number;
  completed_count: number;
  expired_count: number;
}

export interface DailyQuestLimitResponse {
  max_quests: number;
  generated_count: number;
  active_count: number;
  completed_count: number;
  expired_count: number;
  remaining_generation_slots: number;
  reset_at: string;
}

export interface DailyQuestCompleteResponse {
  quest: DailyQuest;
  current_xp: number;
  level: number;
}

export interface DailyQuestProofSubmitResponse extends DailyQuestCompleteResponse {
  passed: boolean;
}

export interface LimitQuestCreateRequest {
  target_user_ids: string[];
  title: string;
  description: string;
  difficulty?: DailyQuestDifficulty;
  xp_reward?: number;
  expires_at?: string;
  auto_pass_score?: number;
}

export interface LimitQuestCreateResponse {
  quests: DailyQuest[];
  created_count: number;
}
