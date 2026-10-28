import { MemberLevel } from '@/types';
import { TaskCreatorType, TaskDifficulty } from '@/types/task';

export type QuestionStatus = 'active' | 'archived';
export type QuestionAnswerStatus = 'not_started' | 'submitted' | 'ai_reviewed' | 'approved' | 'rejected';

export interface Question {
  id: string;
  title: string;
  question: string;
  description?: string | null;
  difficulty: TaskDifficulty;
  category?: string | null;
  topic?: string | null;
  skill_key?: string | null;
  question_type: string;
  numeric_difficulty: number;
  source: string;
  learning_objective?: string | null;
  is_baseline: boolean;
  points: number;
  expected_duration_minutes?: number | null;
  target_member_level: MemberLevel;
  creator_type: TaskCreatorType;
  created_by_id?: string | null;
  expected_answer?: string | null;
  accepted_concepts?: string[][] | null;
  options?: Record<string, string> | null;
  correct_option?: string | null;
  correct_options?: string[] | null;
  feedback?: string | null;
  status: QuestionStatus;
  created_at: string;
  updated_at: string;
}

export interface QuestionListResponse {
  questions: Question[];
  total: number;
}

export interface QuestionAnswer {
  id: string;
  user_id: string;
  question_id: string;
  question?: Question | null;
  answer: string;
  ai_score?: number | null;
  ai_feedback?: string | null;
  ai_confidence?: number | null;
  ai_breakdown?: Record<string, number | string[] | null> | null;
  manager_score?: number | null;
  final_score?: number | null;
  points_awarded: number;
  feedback?: string | null;
  status: QuestionAnswerStatus;
  reviewed_by_id?: string | null;
  submitted_at: string;
  reviewed_at?: string | null;
  created_at: string;
  updated_at: string;
}
