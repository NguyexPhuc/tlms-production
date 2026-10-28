export interface CupUserSummary {
  id: string;
  email: string;
  full_name?: string | null;
  current_xp: number;
  level: number;
  discipline_score: number;
}

export interface CupDefinition {
  id: string;
  code: string;
  title: string;
  description: string;
  icon: string;
  color: string;
  sort_order: number;
  is_active: boolean;
  is_awarded: boolean;
  awarded_at?: string | null;
  awarded_to?: CupUserSummary | null;
}

export interface WeeklyCupQuestionOption {
  id: string;
  text: string;
}

export interface WeeklyCupQuestion {
  id: string;
  question: string;
  options: WeeklyCupQuestionOption[];
}

export interface WeeklyCupAttempt {
  id: string;
  event_id: string;
  started_at: string;
  submitted_at?: string | null;
  score?: number | null;
  total_questions: number;
  duration_seconds?: number | null;
  answers: Record<string, string>;
}

export interface WeeklyCupEvent {
  id: string;
  week_start: string;
  opens_at: string;
  closes_at: string;
  status: 'scheduled' | 'open' | 'closed' | 'awarded' | string;
  cup: CupDefinition;
  winner?: CupUserSummary | null;
  winner_score?: number | null;
  awarded_at?: string | null;
  questions: WeeklyCupQuestion[];
}

export interface WeeklyCupLeaderboardEntry {
  rank: number;
  user_id: string;
  email: string;
  full_name?: string | null;
  level: number;
  current_xp: number;
  discipline_score: number;
  score?: number | null;
  total_questions: number;
  duration_seconds?: number | null;
  submitted_at?: string | null;
  eligible: boolean;
}

export interface WeeklyCupEligibility {
  eligible: boolean;
  reason?: string | null;
  discipline_score: number;
  min_discipline_score: number;
  my_rank?: number | null;
  can_start: boolean;
  can_submit: boolean;
}

export interface WeeklyCupDashboard {
  event?: WeeklyCupEvent | null;
  cups: CupDefinition[];
  leaderboard: WeeklyCupLeaderboardEntry[];
  my_eligibility: WeeklyCupEligibility;
  my_attempt?: WeeklyCupAttempt | null;
  remaining_cups: number;
  min_discipline_score: number;
  next_event_at?: string | null;
  updated_at: string;
}

export interface WeeklyCupStartResponse {
  message: string;
  dashboard: WeeklyCupDashboard;
}

export interface WeeklyCupSubmitResponse {
  message: string;
  score: number;
  total_questions: number;
  duration_seconds: number;
  dashboard: WeeklyCupDashboard;
}
