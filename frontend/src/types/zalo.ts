export type ZaloProvider = 'mock' | 'zalo_oa';
export type ZaloLinkStatus = 'pending' | 'linked' | 'revoked';
export type ZaloQuizStatus = 'active' | 'completed' | 'expired';
export type ZaloDeliveryStatus = 'pending' | 'sent' | 'failed' | 'skipped';

export interface ZaloLink {
  status: ZaloLinkStatus;
  consent_granted: boolean;
  notifications_enabled: boolean;
  linked_at?: string;
  last_interaction_at?: string;
  link_code?: string;
  link_expires_at?: string;
  oa_url?: string;
  provider: ZaloProvider;
}

export interface ZaloIntegrationConfig {
  id: string;
  enabled: boolean;
  environment_enabled: boolean;
  effective_enabled: boolean;
  provider: ZaloProvider;
  send_hour: number;
  send_minute: number;
  reminder_hour: number;
  reminder_minute: number;
  quiz_size: number;
  session_ttl_minutes: number;
  send_window_days: number;
  max_retries: number;
  oa_configured: boolean;
  webhook_url: string;
  web_app_url: string;
  updated_at: string;
}

export interface ZaloQuizItem {
  position: number;
  prompt: string;
  options: Record<string, string>;
  selected_option?: string;
  is_correct?: boolean;
  points_awarded: number;
}

export interface ZaloQuizSession {
  id: string;
  user_id: string;
  user_email?: string;
  session_date: string;
  status: ZaloQuizStatus;
  total_questions: number;
  answered_count: number;
  correct_count: number;
  score: number;
  xp_awarded: number;
  expires_at: string;
  completed_at?: string;
  items: ZaloQuizItem[];
}

export interface ZaloDeliveryLog {
  id: string;
  user_id?: string;
  user_email?: string;
  event_type: string;
  status: ZaloDeliveryStatus;
  retry_count: number;
  max_retries: number;
  last_error?: string;
  sent_at?: string;
  created_at: string;
}

export interface ZaloAdminDashboard {
  config: ZaloIntegrationConfig;
  linked_users: number;
  opted_in_users: number;
  active_sessions: number;
  completed_today: number;
  failed_deliveries: number;
  sessions: ZaloQuizSession[];
  deliveries: ZaloDeliveryLog[];
}

export interface ZaloDispatchResult {
  considered: number;
  sessions_created: number;
  messages_sent: number;
  skipped: number;
  failed: number;
}
