/**
 * Leaderboard types
 */

export interface LeaderboardEntry {
  rank: number;
  user_id: string;
  email: string;
  full_name?: string | null;
  roles: string[];
  primary_role: string;
  level: number;
  current_xp: number;
  discipline_score: number;
  core_task_progress: number;
  completed_tasks: number;
  is_ready_to_promote: boolean;
}

export interface LeaderboardResponse {
  entries: LeaderboardEntry[];
  total_users: number;
  my_rank?: number | null;
  updated_at: string;
}

export interface UserRankInfo {
  rank: number;
  total_users: number;
  percentile: number;
  current_xp: number;
  next_rank_xp?: number | null;
  xp_to_next_rank?: number | null;
}

export interface LeaderboardStats {
  total_active_users: number;
  average_xp: number;
  average_level: number;
  highest_xp: number;
  ready_for_promotion: number;
}
