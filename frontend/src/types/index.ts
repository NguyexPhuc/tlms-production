/**
 * User types based on backend models
 */

export type UserRole = 'candidate' | 'member' | 'mentor' | 'admin';
export type UserStatus = 'active' | 'inactive' | 'suspended';
export type MemberLevel = 'new' | 'diligent' | 'official';

export interface User {
  id: string;  // UUID
  s4h_user_id: string;
  student_id?: string | null;
  email: string;
  first_name?: string | null;
  last_name?: string | null;
  full_name: string | null;
  phone?: string | null;
  roles: UserRole[];  // Array of roles
  primary_role: UserRole;  // Highest priority role for display
  status: UserStatus;
  current_xp: number;
  discipline_score: number;
  reliability_score?: number;
  member_score?: number;
  promotion_progress?: number;
  member_level?: MemberLevel;
  core_task_progress?: number;
  is_ready_to_promote?: boolean;
  level: number;
  created_at: string;
  updated_at: string;
}

export interface TokenResponse {
  accessToken: string;
  refreshToken: string;
}

export interface AuthResponse {
  tokens: TokenResponse;
  user: User;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  phone: string;
  firstName: string;
  lastName: string;
}

export interface UserListResponse {
  users: User[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface UserStatsResponse {
  by_role: Record<UserRole, number>;
  total: number;
}

export interface ApiError {
  error: string;
  detail: string;
  success: boolean;
}
