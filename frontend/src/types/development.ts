import { MemberLevel } from '@/types';
import { UserTask } from '@/types/task';

export type DailyTaskStatus = 'complete' | 'partial' | 'missed';
export type PromotionStatus = 'eligible' | 'pending' | 'approved' | 'rejected';
export type NotificationChannel = 'in_app' | 'email' | 'push' | 'sms';

export interface Notification {
  id: string;
  user_id: string;
  event_type: string;
  title: string;
  message: string;
  channel: NotificationChannel;
  payload?: Record<string, unknown> | null;
  actor_id?: string | null;
  read_at?: string | null;
  is_read: boolean;
  created_at: string;
}

export interface NotificationListResponse {
  notifications: Notification[];
  total: number;
  unread_count: number;
}

export interface RoadmapWeek {
  id: string;
  week_number: number;
  title: string;
  stage: string;
  goals: string[];
  question_focus: string;
  daily_task_focus: string;
  quest_focus: string;
  skill_targets: string[];
  progress_percentage: number;
  weekly_evaluation?: string | null;
  planned_start_at: string;
  planned_end_at: string;
  is_current: boolean;
  is_completed: boolean;
}

export interface MemberRoadmap {
  id: string;
  user_id: string;
  status: string;
  started_at: string;
  target_end_at: string;
  current_week: number;
  current_day: number;
  total_weeks: number;
  total_days: number;
  progress_percentage: number;
  current_stage: string;
  weeks: RoadmapWeek[];
}

export interface AchievementBadgeProgress {
  id: string;
  code: string;
  title: string;
  description: string;
  category: string;
  metric: string;
  target_value: number;
  current_value: number;
  progress_percentage: number;
  is_unlocked: boolean;
  unlocked_at?: string | null;
  badge_icon: string;
  badge_color: string;
  sort_order: number;
}

export interface AchievementDashboard {
  total_count: number;
  unlocked_count: number;
  overall_progress: number;
  featured: AchievementBadgeProgress[];
  next_milestones: AchievementBadgeProgress[];
  badges: AchievementBadgeProgress[];
}

export interface MemberDevelopmentDashboard {
  member_level: MemberLevel;
  current_xp: number;
  level: number;
  discipline_score: number;
  reliability_score: number;
  member_score: number;
  promotion_progress: number;
  today_tasks: UserTask[];
  assigned_tasks: UserTask[];
  completed_tasks: number;
  pending_tasks: number;
  daily_completion_rate: number;
  attendance_status?: DailyTaskStatus | null;
  promotion_eligible: boolean;
  unread_notifications: number;
  notifications: Notification[];
  roadmap?: MemberRoadmap | null;
  achievements: AchievementDashboard;
}

export interface DailyTaskAssignRequest {
  target_date?: string;
  target_member_level: MemberLevel;
  user_ids?: string[];
  task_ids?: string[];
  tasks_per_member?: number;
  deadline_at?: string;
  include_ai_tasks?: boolean;
}

export interface DailyTaskAssignResponse {
  target_date: string;
  target_member_level: MemberLevel;
  users_considered: number;
  tasks_considered: number;
  assignments_created: number;
  skipped_existing: number;
  skipped_official_ai: number;
}

export interface ManagerDevelopmentSummary {
  total_members: number;
  new_members: number;
  diligent_members: number;
  official_members: number;
  daily_task_completion: number;
  missed_tasks: number;
  pending_reviews: number;
  promotion_eligible: number;
  average_completion_rate: number;
  active_members: number;
}

export interface PromotionReview {
  id: string;
  user_id: string;
  user_email?: string | null;
  user_full_name?: string | null;
  from_member_level: MemberLevel;
  to_member_level: MemberLevel;
  status: PromotionStatus;
  metrics?: Record<string, unknown> | null;
  manager_id?: string | null;
  manager_notes?: string | null;
  decided_at?: string | null;
  created_at: string;
  updated_at: string;
}
