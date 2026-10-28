/**
 * API Client for TLMS Backend
 */
import axios, { AxiosInstance, AxiosError } from 'axios';
import Cookies from 'js-cookie';
import { 
  AuthResponse, 
  LoginRequest, 
  RegisterRequest, 
  User, 
  UserListResponse, 
  UserStatsResponse, 
  UserRole, 
  UserStatus, 
  MemberLevel,
  ApiError 
} from '@/types';
import {
  Task,
  UserTask,
  TaskListResponse,
  UserTaskListResponse,
  TaskStatsResponse,
  TaskDetailResponse,
  TaskStartRequest,
  TaskSubmitRequest,
  TaskReviewRequest,
  TaskType
} from '@/types/task';
import {
  LeaderboardResponse,
  UserRankInfo,
  LeaderboardStats
} from '@/types/leaderboard';
import {
  ProfileResponse,
  ProfileEvidence,
  ProfileEvidenceCreate,
  ProfileEvidenceUpdate,
  ProfileStats,
  AutoScheduleRequest,
  AutoScheduleResult
} from '@/types/profile';
import { ForceSyncAllUsersResponse } from '@/types/schedule';
import {
  AchievementDashboard,
  DailyTaskAssignRequest,
  DailyTaskAssignResponse,
  ManagerDevelopmentSummary,
  MemberDevelopmentDashboard,
  MemberRoadmap,
  NotificationListResponse,
  PromotionReview,
} from '@/types/development';
import {
  Question,
  QuestionAnswer,
  QuestionAnswerStatus,
  QuestionListResponse,
} from '@/types/question';
import {
  DailyQuestCompleteResponse,
  DailyQuestLimitResponse,
  DailyQuestListResponse,
  DailyQuestProofSubmitResponse,
  LimitQuestCreateRequest,
  LimitQuestCreateResponse,
} from '@/types/quest';
import {
  WeeklyCupDashboard,
  WeeklyCupStartResponse,
  WeeklyCupSubmitResponse,
} from '@/types/cup';
import {
  ZaloAdminDashboard,
  ZaloDispatchResult,
  ZaloIntegrationConfig,
  ZaloLink,
  ZaloProvider,
} from '@/types/zalo';
import {
  AdminExamResult,
  Certificate,
  CertificateAuditLog,
  CertificateStatistics,
  CertificateTemplate,
  CertificateVerification,
  CertificateVerificationLog,
  CertificationExam,
  Course,
  CourseCreate,
  CourseUpdate,
  CourseEnrollment,
  CourseLesson,
  ExamAttempt,
  ExamResult,
  ExamCreate,
  ExamSubmissionAnswer,
  LessonCreate,
  PendingExamAnswer,
} from '@/types/certification';

const API_URL = process.env.NEXT_PUBLIC_API_URL || '/api';

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: `${API_URL}/v1`,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Add auth token to requests
    this.client.interceptors.request.use((config) => {
      const token = Cookies.get('accessToken');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    // Handle token refresh on 401
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError<ApiError>) => {
        const originalRequest = error.config as any;
        const requestUrl = originalRequest?.url || '';
        const isAuthEndpoint =
          requestUrl.includes('/auth/login') ||
          requestUrl.includes('/auth/register') ||
          requestUrl.includes('/auth/refresh');

        if (
          error.response?.status === 401 &&
          originalRequest &&
          !isAuthEndpoint &&
          !originalRequest._retry
        ) {
          originalRequest._retry = true;
          const refreshToken = Cookies.get('refreshToken');
          
          if (refreshToken) {
            try {
              const response = await axios.post(`${API_URL}/v1/auth/refresh`, {
                refreshToken,
              });
              
              const { accessToken } = response.data;
              Cookies.set('accessToken', accessToken, { expires: 1 });
              
              originalRequest.headers.Authorization = `Bearer ${accessToken}`;
              return this.client(originalRequest);
            } catch {
              // Refresh failed, clear tokens
              this.clearTokens();
              if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
                window.location.href = '/login';
              }
            }
          } else {
            this.clearTokens();
            if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
              window.location.href = '/login';
            }
          }
        }
        
        return Promise.reject(error);
      }
    );
  }

  private setTokens(accessToken: string, refreshToken: string) {
    Cookies.set('accessToken', accessToken, { expires: 1 }); // 1 day
    Cookies.set('refreshToken', refreshToken, { expires: 7 }); // 7 days
  }

  private clearTokens() {
    Cookies.remove('accessToken');
    Cookies.remove('refreshToken');
  }

  async login(credentials: LoginRequest): Promise<AuthResponse> {
    const response = await this.client.post<AuthResponse>('/auth/login', credentials);
    const { tokens } = response.data;
    this.setTokens(tokens.accessToken, tokens.refreshToken);
    return response.data;
  }

  async register(data: RegisterRequest): Promise<{ message: string; success: boolean }> {
    const response = await this.client.post('/auth/register', data);
    return response.data;
  }

  async logout(): Promise<void> {
    try {
      await this.client.post('/auth/logout');
    } finally {
      this.clearTokens();
    }
  }

  async refreshToken(): Promise<string> {
    const refreshToken = Cookies.get('refreshToken');
    if (!refreshToken) {
      throw new Error('No refresh token');
    }
    
    const response = await this.client.post('/auth/refresh', { refreshToken });
    const { accessToken } = response.data;
    Cookies.set('accessToken', accessToken, { expires: 1 });
    return accessToken;
  }

  isAuthenticated(): boolean {
    return !!Cookies.get('accessToken');
  }

  // ============ User Management (Admin) ============
  
  async getMe(): Promise<User> {
    const response = await this.client.get<User>('/users/me');
    return response.data;
  }

  async checkAdminExists(): Promise<boolean> {
    const response = await this.client.get<{ has_admin: boolean }>('/users/check-admin-exists');
    return response.data.has_admin;
  }

  async listUsers(params?: {
    page?: number;
    page_size?: number;
    role?: UserRole;
    status?: UserStatus;
    search?: string;
  }): Promise<UserListResponse> {
    const response = await this.client.get<UserListResponse>('/users', { params });
    return response.data;
  }

  async getUser(userId: string): Promise<User> {
    const response = await this.client.get<User>(`/users/${userId}`);
    return response.data;
  }

  async updateUserRoles(userId: string, roles: UserRole[]): Promise<User> {
    const response = await this.client.patch<User>(`/users/${userId}/roles`, { roles });
    return response.data;
  }

  async updateUserStatus(userId: string, status: UserStatus): Promise<User> {
    const response = await this.client.patch<User>(`/users/${userId}/status`, { status });
    return response.data;
  }

  async updateUserMemberLevel(userId: string, memberLevel: MemberLevel): Promise<User> {
    const response = await this.client.patch<User>(`/users/${userId}/member-level`, {
      member_level: memberLevel,
    });
    return response.data;
  }

  async setFirstAdmin(): Promise<User> {
    const response = await this.client.post<User>('/users/set-first-admin');
    return response.data;
  }

  async getUserStatsByRole(): Promise<UserStatsResponse> {
    const response = await this.client.get<UserStatsResponse>('/users/stats/by-role');
    return response.data;
  }

  // ============ Task Management ============

  // Tasks (all users)
  async listTasks(params?: {
    task_type?: TaskType;
    is_active?: boolean;
    page?: number;
    page_size?: number;
  }): Promise<TaskListResponse> {
    const response = await this.client.get<TaskListResponse>('/tasks', { params });
    return response.data;
  }

  async getTask(taskId: string): Promise<Task> {
    const response = await this.client.get<Task>(`/tasks/${taskId}`);
    return response.data;
  }

  async getTaskStats(): Promise<TaskStatsResponse> {
    const response = await this.client.get<TaskStatsResponse>('/tasks/stats');
    return response.data;
  }

  // User tasks
  async getAvailableTasks(): Promise<TaskListResponse> {
    const response = await this.client.get<TaskListResponse>('/tasks/available/me');
    return response.data;
  }

  async getMyTasks(status?: string): Promise<UserTaskListResponse> {
    const params = status ? { status } : {};
    const response = await this.client.get<UserTaskListResponse>('/tasks/my-tasks', { params });
    return response.data;
  }

  async getUserTasks(userId: string, status?: string): Promise<UserTaskListResponse> {
    const params = status ? { status } : {};
    const response = await this.client.get<UserTaskListResponse>(`/tasks/user/${userId}`, { params });
    return response.data;
  }

  async getUserStats(userId: string, weekStart?: string): Promise<any> {
    const params = weekStart ? { week_start: weekStart } : {};
    const response = await this.client.get(`/tasks/user-stats/${userId}`, { params });
    return response.data;
  }

  async startTask(data: TaskStartRequest): Promise<UserTask> {
    const response = await this.client.post<UserTask>('/tasks/start', data);
    return response.data;
  }

  async startAssignedTask(userTaskId: string): Promise<UserTask> {
    const response = await this.client.post<UserTask>(`/tasks/start-assigned/${userTaskId}`);
    return response.data;
  }

  async submitTask(userTaskId: string, data: TaskSubmitRequest): Promise<UserTask> {
    const response = await this.client.post<UserTask>(`/tasks/submit/${userTaskId}`, data);
    return response.data;
  }

  // Mentor
  async getPendingReviews(): Promise<UserTaskListResponse> {
    const response = await this.client.get<UserTaskListResponse>('/tasks/pending-reviews');
    return response.data;
  }

  async reviewTask(userTaskId: string, data: TaskReviewRequest): Promise<UserTask> {
    const response = await this.client.post<UserTask>(`/tasks/review/${userTaskId}`, data);
    return response.data;
  }

  async updateTaskProgress(userTaskId: string, progress_percentage: number, notes?: string): Promise<UserTask> {
    const response = await this.client.post<UserTask>(`/development/tasks/${userTaskId}/progress`, {
      progress_percentage,
      notes,
    });
    return response.data;
  }

  // Admin - Create/Update/Delete tasks
  async createTask(data: any): Promise<Task> {
    const response = await this.client.post<Task>('/tasks', data);
    return response.data;
  }

  async updateTask(taskId: string, data: any): Promise<Task> {
    const response = await this.client.patch<Task>(`/tasks/${taskId}`, data);
    return response.data;
  }

  async deleteTask(taskId: string): Promise<void> {
    await this.client.delete(`/tasks/${taskId}`);
  }

  async getTaskDetails(taskId: string): Promise<TaskDetailResponse> {
    const response = await this.client.get<TaskDetailResponse>(`/tasks/${taskId}/details`);
    return response.data;
  }

  // ============ Leaderboard ============

  async getLeaderboard(params?: {
    role?: string;
    limit?: number;
  }): Promise<LeaderboardResponse> {
    const response = await this.client.get<LeaderboardResponse>('/leaderboard', { params });
    return response.data;
  }

  async getMyRank(): Promise<UserRankInfo> {
    const response = await this.client.get<UserRankInfo>('/leaderboard/my-rank');
    return response.data;
  }

  async getLeaderboardStats(): Promise<LeaderboardStats> {
    const response = await this.client.get<LeaderboardStats>('/leaderboard/stats');
    return response.data;
  }

  async getTopPerformers(limit: number = 10): Promise<any> {
    const response = await this.client.get(`/leaderboard/top/${limit}`);
    return response.data;
  }

  // ============ Schedule & Attendance ============

  async getWeekSchedules(weekStart: string): Promise<any> {
    const response = await this.client.get(`/schedules/week/${weekStart}`);
    return response.data;
  }

  async syncStudentSchedule(weekStart: string, force: boolean = false): Promise<any> {
    const response = await this.client.post(`/schedules/week/${weekStart}/sync`, null, {
      params: { force },
    });
    return response.data;
  }

  async forceSyncAllUsersSchedules(weekStart?: string): Promise<ForceSyncAllUsersResponse> {
    const payload = weekStart ? { week_start: weekStart } : {};
    const response = await this.client.post<ForceSyncAllUsersResponse>(
      '/schedules/admin/force-sync-all-users',
      payload
    );
    return response.data;
  }

  async getUsers(params?: any): Promise<any> {
    const response = await this.client.get('/users', { params });
    return response.data;
  }

  async getUserById(userId: string): Promise<User> {
    const response = await this.client.get<User>(`/users/${userId}`);
    return response.data;
  }

  async updateStudentId(studentId: string): Promise<User> {
    const response = await this.client.put<User>('/users/me/student-id', { student_id: studentId });
    return response.data;
  }

  async getMySchedules(params?: {
    start_date?: string;
    end_date?: string;
    include_cancelled?: boolean;
  }): Promise<any> {
    const response = await this.client.get('/schedules/my', { params });
    return response.data;
  }

  async registerWeekSchedules(data: any): Promise<any> {
    const response = await this.client.post('/schedules/week', data);
    return response.data;
  }

  async cancelSchedule(scheduleId: string, reason: string): Promise<any> {
    const response = await this.client.patch(`/schedules/${scheduleId}/cancel`, {
      reason
    });
    return response.data;
  }

  async checkIn(data: any): Promise<any> {
    const response = await this.client.post('/schedules/check-in', data);
    return response.data;
  }

  async checkOut(attendanceId: string, data: any): Promise<any> {
    const response = await this.client.post(`/schedules/check-out/${attendanceId}`, data);
    return response.data;
  }

  async getMyAttendances(params?: {
    start_date?: string;
    end_date?: string;
  }): Promise<any> {
    const response = await this.client.get('/schedules/attendance/my', { params });
    return response.data;
  }

  async getAttendanceStats(params?: {
    start_date?: string;
    end_date?: string;
  }): Promise<any> {
    const response = await this.client.get('/schedules/attendance/stats', { params });
    return response.data;
  }

  // ============================================
  // Manager - View multiple users schedules
  // ============================================

  async getUsersSchedulesForManager(weekStart: string, userIds: string[]): Promise<any> {
    const response = await this.client.get('/schedules/manager/users-schedules', {
      params: {
        week_start: weekStart,
        user_ids: userIds.join(',')
      }
    });
    return response.data;
  }

  // ============================================
  // Profile APIs
  // ============================================

  async getMyProfile(): Promise<ProfileResponse> {
    const response = await this.client.get<ProfileResponse>('/profile/me');
    return response.data;
  }

  async getProfileStats(): Promise<ProfileStats> {
    const response = await this.client.get<ProfileStats>('/profile/stats');
    return response.data;
  }

  async getUserProfile(userId: string): Promise<ProfileResponse> {
    const response = await this.client.get<ProfileResponse>(`/profile/user/${userId}`);
    return response.data;
  }

  async createEvidence(data: ProfileEvidenceCreate): Promise<ProfileEvidence> {
    const response = await this.client.post<ProfileEvidence>('/profile/evidence', data);
    return response.data;
  }

  async getEvidence(includePending: boolean = true): Promise<ProfileEvidence[]> {
    const response = await this.client.get<ProfileEvidence[]>('/profile/evidence', {
      params: { include_pending: includePending }
    });
    return response.data;
  }

  async updateEvidence(evidenceId: string, data: ProfileEvidenceUpdate): Promise<ProfileEvidence> {
    const response = await this.client.patch<ProfileEvidence>(`/profile/evidence/${evidenceId}`, data);
    return response.data;
  }

  async deleteEvidence(evidenceId: string): Promise<void> {
    await this.client.delete(`/profile/evidence/${evidenceId}`);
  }

  async verifyEvidence(evidenceId: string, data: any): Promise<ProfileEvidence> {
    const response = await this.client.post<ProfileEvidence>(`/profile/evidence/${evidenceId}/verify`, data);
    return response.data;
  }

  async autoSchedule(request: AutoScheduleRequest): Promise<AutoScheduleResult> {
    const response = await this.client.post<AutoScheduleResult>('/profile/auto-schedule', request);
    return response.data;
  }

  // ============================================
  // Member Development
  // ============================================

  async getDevelopmentDashboard(): Promise<MemberDevelopmentDashboard> {
    const response = await this.client.get<MemberDevelopmentDashboard>('/development/me');
    return response.data;
  }

  async getMyRoadmap(): Promise<MemberRoadmap> {
    const response = await this.client.get<MemberRoadmap>('/development/roadmap/me');
    return response.data;
  }

  async getMyAchievements(): Promise<AchievementDashboard> {
    const response = await this.client.get<AchievementDashboard>('/development/achievements/me');
    return response.data;
  }

  async getManagerDevelopmentSummary(): Promise<ManagerDevelopmentSummary> {
    const response = await this.client.get<ManagerDevelopmentSummary>('/development/manager-summary');
    return response.data;
  }

  async assignDailyTasks(data: DailyTaskAssignRequest): Promise<DailyTaskAssignResponse> {
    const response = await this.client.post<DailyTaskAssignResponse>('/development/daily-tasks/assign', data);
    return response.data;
  }

  async reconcileDailyTasks(targetDate?: string): Promise<any> {
    const response = await this.client.post('/development/daily-tasks/reconcile', {
      target_date: targetDate,
    });
    return response.data;
  }

  async evaluateMember(userId: string, managerScore?: number, notes?: string): Promise<any> {
    const response = await this.client.post(`/development/evaluations/${userId}`, null, {
      params: {
        manager_score: managerScore,
        notes,
      },
    });
    return response.data;
  }

  async listPromotionReviews(status?: string): Promise<PromotionReview[]> {
    const response = await this.client.get<PromotionReview[]>('/development/promotions', {
      params: status ? { status } : {},
    });
    return response.data;
  }

  async approvePromotion(promotionId: string, manager_notes?: string): Promise<PromotionReview> {
    const response = await this.client.post<PromotionReview>(`/development/promotions/${promotionId}/approve`, {
      manager_notes,
    });
    return response.data;
  }

  async rejectPromotion(promotionId: string, manager_notes?: string): Promise<PromotionReview> {
    const response = await this.client.post<PromotionReview>(`/development/promotions/${promotionId}/reject`, {
      manager_notes,
    });
    return response.data;
  }

  async getNotifications(unreadOnly = false): Promise<NotificationListResponse> {
    const response = await this.client.get<NotificationListResponse>('/notifications/me', {
      params: { unread_only: unreadOnly },
    });
    return response.data;
  }

  async markNotificationRead(notificationId: string): Promise<void> {
    await this.client.patch(`/notifications/${notificationId}/read`);
  }

  async markAllNotificationsRead(): Promise<void> {
    await this.client.patch('/notifications/read-all');
  }

  async listQuestions(targetMemberLevel?: string): Promise<QuestionListResponse> {
    const response = await this.client.get<QuestionListResponse>('/questions', {
      params: targetMemberLevel ? { target_member_level: targetMemberLevel } : {},
    });
    return response.data;
  }

  async createQuestion(data: Partial<Question>): Promise<Question> {
    const response = await this.client.post<Question>('/questions', data);
    return response.data;
  }

  async updateQuestion(questionId: string, data: Partial<Question>): Promise<Question> {
    const response = await this.client.patch<Question>(`/questions/${questionId}`, data);
    return response.data;
  }

  async submitQuestionAnswer(questionId: string, answer: string): Promise<QuestionAnswer> {
    const response = await this.client.post<QuestionAnswer>(`/questions/${questionId}/answer`, { answer });
    return response.data;
  }

  async listQuestionAnswers(pendingOnly = false): Promise<QuestionAnswer[]> {
    const response = await this.client.get<QuestionAnswer[]>('/questions/answers', {
      params: { pending_only: pendingOnly },
    });
    return response.data;
  }

  async reviewQuestionAnswer(
    answerId: string,
    data: {
      status: QuestionAnswerStatus;
      manager_score?: number;
      final_score?: number;
      feedback?: string;
    }
  ): Promise<QuestionAnswer> {
    const response = await this.client.post<QuestionAnswer>(`/questions/answers/${answerId}/review`, data);
    return response.data;
  }

  // ============================================
  // Daily Quests
  // ============================================

  async getDailyQuests(): Promise<DailyQuestListResponse> {
    const response = await this.client.get<DailyQuestListResponse>('/quests/daily');
    return response.data;
  }

  async getDailyQuestLimit(): Promise<DailyQuestLimitResponse> {
    const response = await this.client.get<DailyQuestLimitResponse>('/quests/daily/limit');
    return response.data;
  }

  async completeDailyQuest(questId: string): Promise<DailyQuestCompleteResponse> {
    const response = await this.client.post<DailyQuestCompleteResponse>(`/quests/daily/${questId}/complete`);
    return response.data;
  }

  async getLimitQuests(): Promise<DailyQuestListResponse> {
    const response = await this.client.get<DailyQuestListResponse>('/quests/limit');
    return response.data;
  }

  async createLimitQuest(data: LimitQuestCreateRequest): Promise<LimitQuestCreateResponse> {
    const response = await this.client.post<LimitQuestCreateResponse>('/quests/limit', data);
    return response.data;
  }

  async submitQuestProof(
    questId: string,
    data: {
      proof_text?: string;
      proof_link?: string;
      proof_image?: File | null;
    }
  ): Promise<DailyQuestProofSubmitResponse> {
    const formData = new FormData();
    if (data.proof_text) formData.append('proof_text', data.proof_text);
    if (data.proof_link) formData.append('proof_link', data.proof_link);
    if (data.proof_image) formData.append('proof_image', data.proof_image);

    const response = await this.client.post<DailyQuestProofSubmitResponse>(
      `/quests/${questId}/submit`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return response.data;
  }

  async viewQuestProof(questId: string, filename = 'quest-proof'): Promise<void> {
    const response = await this.client.get(`/quests/${questId}/proof-image`, { responseType: 'blob' });
    const url = URL.createObjectURL(response.data);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.target = '_blank';
    anchor.rel = 'noopener noreferrer';
    anchor.download = filename;
    anchor.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  // ============================================
  // Weekly Cups
  // ============================================

  async getWeeklyCupDashboard(): Promise<WeeklyCupDashboard> {
    const response = await this.client.get<WeeklyCupDashboard>('/cups/weekly');
    return response.data;
  }

  async startWeeklyCupQuiz(): Promise<WeeklyCupStartResponse> {
    const response = await this.client.post<WeeklyCupStartResponse>('/cups/weekly/start');
    return response.data;
  }

  async submitWeeklyCupQuiz(answers: Record<string, string>): Promise<WeeklyCupSubmitResponse> {
    const response = await this.client.post<WeeklyCupSubmitResponse>('/cups/weekly/submit', { answers });
    return response.data;
  }

  // ============================================
  // Zalo Daily Task Quiz
  // ============================================

  async getMyZaloLink(): Promise<ZaloLink> {
    const response = await this.client.get<ZaloLink>('/zalo/me');
    return response.data;
  }

  async createZaloLinkIntent(consentGranted: boolean): Promise<ZaloLink> {
    const response = await this.client.post<ZaloLink>('/zalo/me/link-intent', {
      consent_granted: consentGranted,
    });
    return response.data;
  }

  async updateZaloNotifications(enabled: boolean): Promise<ZaloLink> {
    const response = await this.client.patch<ZaloLink>('/zalo/me/notifications', { enabled });
    return response.data;
  }

  async revokeZaloLink(): Promise<ZaloLink> {
    const response = await this.client.delete<ZaloLink>('/zalo/me');
    return response.data;
  }

  async getZaloAdminDashboard(): Promise<ZaloAdminDashboard> {
    const response = await this.client.get<ZaloAdminDashboard>('/zalo/admin/dashboard');
    return response.data;
  }

  async updateZaloConfig(data: Partial<{
    enabled: boolean;
    provider: ZaloProvider;
    send_hour: number;
    send_minute: number;
    reminder_hour: number;
    reminder_minute: number;
    quiz_size: number;
    session_ttl_minutes: number;
    send_window_days: number;
    max_retries: number;
  }>): Promise<ZaloIntegrationConfig> {
    const response = await this.client.patch<ZaloIntegrationConfig>('/zalo/admin/config', data);
    return response.data;
  }

  async dispatchZaloQuizzes(): Promise<ZaloDispatchResult> {
    const response = await this.client.post<ZaloDispatchResult>('/zalo/admin/dispatch');
    return response.data;
  }

  async sendMockZaloMessage(userId: string, text: string): Promise<{ success: boolean; action: string }> {
    const response = await this.client.post('/zalo/admin/mock-message', { user_id: userId, text });
    return response.data;
  }

  // ============================================
  // Exams & Digital Certificates
  // ============================================

  async listCertificationCourses(): Promise<Course[]> {
    const response = await this.client.get<Course[]>('/courses');
    return response.data;
  }

  async listAdminCertificationCourses(): Promise<Course[]> {
    const response = await this.client.get<Course[]>('/admin/courses');
    return response.data;
  }

  async createCertificationCourse(data: CourseCreate): Promise<Course> {
    const response = await this.client.post<Course>('/admin/courses', data);
    return response.data;
  }

  async updateCertificationCourse(courseId: string, data: CourseUpdate): Promise<Course> {
    const response = await this.client.patch<Course>(`/admin/courses/${courseId}`, data);
    return response.data;
  }

  async getMyCourseEnrollments(): Promise<CourseEnrollment[]> {
    const response = await this.client.get<CourseEnrollment[]>('/courses/enrollments/my');
    return response.data;
  }

  async enrollCertificationCourse(courseId: string): Promise<CourseEnrollment> {
    const response = await this.client.post<CourseEnrollment>(`/courses/${courseId}/enroll`);
    return response.data;
  }

  async listCourseLessons(courseId: string, admin = false): Promise<CourseLesson[]> {
    const prefix = admin ? '/admin' : '';
    const response = await this.client.get<CourseLesson[]>(`${prefix}/courses/${courseId}/lessons`);
    return response.data;
  }

  async createCourseLesson(courseId: string, data: LessonCreate): Promise<CourseLesson> {
    const response = await this.client.post<CourseLesson>(`/admin/courses/${courseId}/lessons`, data);
    return response.data;
  }

  async listCertificationExams(admin = false): Promise<CertificationExam[]> {
    const response = await this.client.get<CertificationExam[]>(admin ? '/admin/exams' : '/exams');
    return response.data;
  }

  async startCertificationExam(examId: string): Promise<ExamAttempt> {
    const response = await this.client.post<ExamAttempt>(`/exams/${examId}/start`);
    return response.data;
  }

  async createCertificationExam(data: ExamCreate): Promise<CertificationExam> {
    const response = await this.client.post<CertificationExam>('/admin/exams', data);
    return response.data;
  }

  async listAdminExamResults(): Promise<AdminExamResult[]> {
    const response = await this.client.get<AdminExamResult[]>('/admin/exam-results');
    return response.data;
  }

  async listPendingExamAnswers(): Promise<PendingExamAnswer[]> {
    const response = await this.client.get<PendingExamAnswer[]>('/admin/exam-answers/pending');
    return response.data;
  }

  async reviewExamAnswer(answerId: string, scoreAwarded: number, feedback?: string): Promise<Record<string, unknown>> {
    const response = await this.client.post<Record<string, unknown>>(`/admin/exam-answers/${answerId}/review`, {
      score_awarded: scoreAwarded,
      feedback,
    });
    return response.data;
  }

  async submitCertificationExam(attemptId: string, answers: ExamSubmissionAnswer[]): Promise<ExamResult> {
    const response = await this.client.post<ExamResult>(`/exam-attempts/${attemptId}/submit`, { answers });
    return response.data;
  }

  async getMyCertificates(): Promise<Certificate[]> {
    const response = await this.client.get<Certificate[]>('/certificates/my');
    return response.data;
  }

  async verifyCertificate(token: string): Promise<CertificateVerification> {
    const response = await this.client.get<CertificateVerification>(`/certificates/verify/${encodeURIComponent(token)}`);
    return response.data;
  }

  async downloadCertificate(certificate: Certificate): Promise<void> {
    const response = await this.client.get(`/certificates/${certificate.id}/download`, { responseType: 'blob' });
    const url = URL.createObjectURL(response.data);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `${certificate.certificate_id}.pdf`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  async getCertificateStatistics(): Promise<CertificateStatistics> {
    const response = await this.client.get<CertificateStatistics>('/admin/certificate-statistics');
    return response.data;
  }

  async listAdminCertificates(): Promise<Certificate[]> {
    const response = await this.client.get<Certificate[]>('/admin/certificates');
    return response.data;
  }

  async revokeCertificate(certificateId: string, reason: string): Promise<Certificate> {
    const response = await this.client.post<Certificate>(`/admin/certificates/${certificateId}/revoke`, { reason });
    return response.data;
  }

  async listCertificateTemplates(): Promise<CertificateTemplate[]> {
    const response = await this.client.get<CertificateTemplate[]>('/admin/certificate-templates');
    return response.data;
  }

  async createCertificateTemplate(data: Omit<CertificateTemplate, 'id' | 'version' | 'is_active' | 'created_at' | 'updated_at'>): Promise<CertificateTemplate> {
    const response = await this.client.post<CertificateTemplate>('/admin/certificate-templates', data);
    return response.data;
  }

  async uploadCertificateTemplateAsset(templateId: string, kind: 'logo' | 'background', file: File): Promise<CertificateTemplate> {
    const data = new FormData();
    data.append('asset', file);
    const response = await this.client.post<CertificateTemplate>(`/admin/certificate-templates/${templateId}/assets/${kind}`, data, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  }

  async listCertificateAuditLogs(): Promise<CertificateAuditLog[]> {
    const response = await this.client.get<CertificateAuditLog[]>('/admin/certificate-audit-logs');
    return response.data;
  }

  async listCertificateVerificationLogs(): Promise<CertificateVerificationLog[]> {
    const response = await this.client.get<CertificateVerificationLog[]>('/admin/certificate-verification-logs');
    return response.data;
  }
}

export const apiClient = new ApiClient();
