/**
 * Profile types for TLMS
 * Based on backend profile schemas
 */

export type EvidenceStatus = 'pending' | 'verified' | 'rejected';

// ============================================
// Profile Evidence
// ============================================

export interface ProfileEvidenceBase {
  title: string;
  description?: string | null;
  evidence_links: string[];
  tags: string[];
  task_id?: string | null;
  is_public: boolean;
}

export interface ProfileEvidenceCreate extends ProfileEvidenceBase {}

export interface ProfileEvidenceUpdate {
  title?: string;
  description?: string | null;
  evidence_links?: string[];
  tags?: string[];
  is_public?: boolean;
}

export interface ProfileEvidenceVerify {
  status: EvidenceStatus;
  verification_notes?: string | null;
  is_featured: boolean;
}

export interface ProfileEvidence extends ProfileEvidenceBase {
  id: string;
  user_id: string;
  status: EvidenceStatus;
  is_featured: boolean;
  verified_by_id?: string | null;
  verified_at?: string | null;
  verification_notes?: string | null;
  created_at: string;
  updated_at: string;
}

// ============================================
// Profile Statistics
// ============================================

export interface WorkScheduleStats {
  total_hours_this_week: number;
  total_hours_this_month: number;
  total_hours_all_time: number;
  attendance_rate: number;
  total_days_worked: number;
}

export interface TaskStats {
  total_tasks_completed: number;
  core_tasks_completed: number;
  bounty_tasks_completed: number;
  total_xp_earned: number;
  current_level: number;
  current_xp: number;
  core_task_progress: number;
}

export interface AchievementSummary {
  total_evidence: number;
  verified_evidence: number;
  featured_evidence: number;
  skill_tags: string[];
  discipline_score: number;
  is_ready_to_promote: boolean;
}

export interface ProfileStats {
  work_schedule: WorkScheduleStats;
  tasks: TaskStats;
  achievements: AchievementSummary;
}

// ============================================
// Auto-Schedule
// ============================================

export interface AutoScheduleRequest {
  week_start_date: string; // ISO date string
  target_hours_per_day?: number;
  prefer_morning?: boolean;
  prefer_afternoon?: boolean;
  prefer_evening?: boolean;
}

export interface ScheduleConflict {
  date: string;
  shift: string;
  reason: string;
}

export interface AutoScheduleResult {
  success: boolean;
  message: string;
  schedules_created: number;
  conflicts: ScheduleConflict[];
}

// ============================================
// Complete Profile Response
// ============================================

export interface UserBasicInfo {
  id: string;
  email: string;
  student_id?: string | null;
  full_name: string;
  roles: string[];
  primary_role: string;
}

export interface RecentTask {
  task_id: string;
  title: string;
  status: string;
  submitted_at?: string | null;
  xp_earned: number;
}

export interface UpcomingSchedule {
  date: string;
  shift: string;
  registration_type: string;
}

export interface ProfileResponse {
  user: UserBasicInfo;
  stats: ProfileStats;
  evidence: ProfileEvidence[];
  recent_tasks: RecentTask[];
  upcoming_schedules: UpcomingSchedule[];
}
