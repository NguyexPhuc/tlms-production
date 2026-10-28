export interface Course {
  id: string;
  code: string;
  title: string;
  description?: string | null;
  skills: string[];
  is_published: boolean;
  certificate_template_id?: string | null;
  created_at: string;
}

export interface CourseEnrollment {
  id: string;
  course_id: string;
  user_id: string;
  status: string;
  progress_percentage: number;
  enrolled_at: string;
}

export interface CourseLesson {
  id: string;
  course_id: string;
  title: string;
  content?: string | null;
  position: number;
  is_published: boolean;
}

export interface CertificationExam {
  id: string;
  course_id: string;
  course_title: string;
  title: string;
  description?: string | null;
  duration_minutes: number;
  pass_percentage: number;
  max_attempts: number;
  is_published: boolean;
  certificate_name?: string | null;
  opens_at?: string | null;
  closes_at?: string | null;
  question_count: number;
  attempts_used: number;
  best_percentage?: number | null;
}

export interface ExamQuestion {
  id: string;
  question_id: string;
  position: number;
  points: number;
  title: string;
  question: string;
  description?: string | null;
  question_type: string;
  options?: Record<string, string> | null;
  allow_multiple: boolean;
}

export interface ExamAttempt {
  id: string;
  exam_id: string;
  exam_title: string;
  attempt_number: number;
  status: string;
  started_at: string;
  expires_at: string;
  submitted_at?: string | null;
  questions: ExamQuestion[];
}

export interface ExamSubmissionAnswer {
  exam_question_id: string;
  selected_options?: string[];
  text_answer?: string;
}

export interface ExamResult {
  id?: string | null;
  attempt_id: string;
  score: number;
  max_score: number;
  percentage: number;
  passed: boolean;
  proficiency_level: string;
  status: string;
  certificate_id?: string | null;
  verification_token?: string | null;
}

export interface AdminExamResult {
  id: string;
  attempt_id: string;
  user_id: string;
  user_name: string;
  user_email: string;
  exam_id: string;
  exam_title: string;
  course_title: string;
  score: number;
  max_score: number;
  percentage: number;
  passed: boolean;
  proficiency_level: string;
  graded_at: string;
  certificate_id?: string | null;
}

export interface PendingExamAnswer {
  id: string;
  attempt_id: string;
  user_id: string;
  user_name: string;
  user_email: string;
  exam_title: string;
  question_title: string;
  question_text: string;
  text_answer?: string | null;
  max_points: number;
  submitted_at: string;
}

export interface Certificate {
  id: string;
  certificate_id: string;
  full_name: string;
  certificate_name: string;
  issuer_name: string;
  score: number;
  proficiency_level: string;
  skills: string[];
  issued_at: string;
  expires_at?: string | null;
  status: string;
  verification_token: string;
  score_is_public: boolean;
}

export interface CertificateVerification {
  verification_status: 'VALID' | 'EXPIRED' | 'REVOKED' | 'NOT_FOUND';
  certificate_id?: string | null;
  full_name?: string | null;
  certificate_name?: string | null;
  issuer_name?: string | null;
  skills: string[];
  score?: number | null;
  proficiency_level?: string | null;
  issued_at?: string | null;
  expires_at?: string | null;
}

export interface CertificateStatistics {
  total_users: number;
  total_attempts: number;
  pass_rate: number;
  total_certificates: number;
  valid_certificates: number;
  expired_certificates: number;
  revoked_certificates: number;
}

export interface CertificateTemplate {
  id: string;
  name: string;
  organization_name: string;
  title: string;
  subtitle: string;
  primary_color: string;
  secondary_color: string;
  accent_color: string;
  background_color: string;
  logo_storage_key?: string | null;
  background_storage_key?: string | null;
  signature_name?: string | null;
  signature_title?: string | null;
  font_family: string;
  layout: Record<string, unknown>;
  version: number;
  is_default: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CourseCreate {
  code: string;
  title: string;
  description?: string;
  skills: string[];
  is_published: boolean;
  certificate_template_id?: string;
}

export interface CourseUpdate {
  title?: string;
  description?: string;
  skills?: string[];
  is_published?: boolean;
  certificate_template_id?: string | null;
}

export interface LessonCreate {
  title: string;
  content?: string;
  position: number;
  is_published: boolean;
}

export interface ExamCreate {
  course_id: string;
  title: string;
  description?: string;
  duration_minutes: number;
  pass_percentage: number;
  max_attempts: number;
  is_published: boolean;
  certificate_name?: string;
  certificate_valid_days?: number;
  questions: Array<{
    question_id: string;
    position: number;
    points: number;
  }>;
}

export interface CertificateAuditLog {
  id: string;
  certificate_id: string;
  actor_id?: string | null;
  action: string;
  reason?: string | null;
  metadata_json: Record<string, unknown>;
  created_at: string;
}

export interface CertificateVerificationLog {
  id: string;
  certificate_id?: string | null;
  token_fingerprint: string;
  result: string;
  user_agent?: string | null;
  verified_at: string;
}
