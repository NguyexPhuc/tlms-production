'use client';

import { useEffect, useState } from 'react';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { apiClient } from '@/lib/api';
import { UserRole } from '@/types';
import { MemberDevelopmentDashboard } from '@/types/development';
import { DailyQuestLimitResponse } from '@/types/quest';

const roleLabels: Record<string, string> = {
  candidate: 'Thực tập sinh',
  member: 'Thành viên',
  mentor: 'Mentor',
  admin: 'Admin',
};

const memberLevelLabels: Record<string, string> = {
  new: 'Thành viên mới',
  diligent: 'Thành viên chuyên cần',
  official: 'Thành viên chính thức',
};

const skillTargetLabels: Record<string, string> = {
  review: 'Ôn tập kiến thức',
  learning_speed: 'Tăng tốc độ học',
  weak_skills: 'Củng cố kỹ năng yếu',
  strong_skills: 'Phát huy kỹ năng mạnh',
};

const formatSkillTarget = (target: string) =>
  skillTargetLabels[target] || target.replaceAll('_', ' ');

export default function DashboardPage() {
  const router = useRouter();
  const { user, isLoading, isAuthenticated, logout, refreshUser } = useAuth();
  const [settingAdmin, setSettingAdmin] = useState(false);
  const [adminError, setAdminError] = useState('');
  const [hasAdmin, setHasAdmin] = useState<boolean | null>(null);
  const [development, setDevelopment] = useState<MemberDevelopmentDashboard | null>(null);
  const [dailyQuestLimit, setDailyQuestLimit] = useState<DailyQuestLimitResponse | null>(null);

  const hasRole = (role: UserRole) => user?.roles?.includes(role) ?? false;
  const isLearningAccount = hasRole('candidate') || hasRole('member');
  const canUseAdmin = hasRole('admin') && !isLearningAccount;
  const canUseMentor = (hasRole('mentor') || hasRole('admin')) && !isLearningAccount;
  const visibleRoles = hasRole('candidate')
    ? ['candidate']
    : hasRole('member')
      ? ['member']
      : (user?.roles ?? []);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isLoading, isAuthenticated, router]);

  useEffect(() => {
    const checkAdmin = async () => {
      if (user && !canUseAdmin) {
        try {
          const exists = await apiClient.checkAdminExists();
          setHasAdmin(exists);
        } catch (err) {
          console.error('Failed to check admin exists:', err);
          setHasAdmin(true);
        }
      }
    };
    checkAdmin();
  }, [user, canUseAdmin]);

  useEffect(() => {
    const loadDevelopment = async () => {
      if (!user) return;
      try {
        const data = await apiClient.getDevelopmentDashboard();
        setDevelopment(data);
      } catch (err) {
        console.error('Failed to load development dashboard:', err);
      }

      if (!isLearningAccount) {
        setDailyQuestLimit(null);
        return;
      }

      try {
        const limit = await apiClient.getDailyQuestLimit();
        setDailyQuestLimit(limit);
      } catch (err) {
        console.error('Failed to load daily quest dashboard stats:', err);
        setDailyQuestLimit(null);
      }
    };
    loadDevelopment();
  }, [user, isLearningAccount]);

  const handleLogout = async () => {
    await logout();
    router.push('/login');
  };

  const handleSetFirstAdmin = async () => {
    setSettingAdmin(true);
    setAdminError('');
    try {
      await apiClient.setFirstAdmin();
      await refreshUser();
      setHasAdmin(true);
    } catch (err: unknown) {
      const message =
        err && typeof err === 'object' && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined;
      setAdminError(message || 'Không thể đặt quyền Admin');
    } finally {
      setSettingAdmin(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="w-8 h-8 border-2 border-gray-300 border-t-[#1E90FF] rounded-full animate-spin"></div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  const currentXp = user.current_xp || 0;
  const dashboardLevel = (canUseAdmin || canUseMentor)
    ? 99
    : Math.max(1, Math.floor(currentXp / 100) + 1);
  const xpForCurrentLevel = (dashboardLevel - 1) * 100;
  const xpForNextLevel = dashboardLevel * 100;
  const xpProgress = ((currentXp - xpForCurrentLevel) / (xpForNextLevel - xpForCurrentLevel)) * 100;
  const dashboardDailyTotal = dailyQuestLimit
    ? Math.max(dailyQuestLimit.generated_count, dailyQuestLimit.max_quests)
    : development?.today_tasks.length ?? 0;
  const dashboardDailyCompleted = dailyQuestLimit?.completed_count ?? development?.completed_tasks ?? 0;
  const dashboardDailyProgress = dashboardDailyTotal > 0
    ? (dashboardDailyCompleted / dashboardDailyTotal) * 100
    : development?.daily_completion_rate ?? 0;
  const roadmap = development?.roadmap ?? null;
  const currentRoadmapWeek = roadmap?.weeks.find((week) => week.week_number === roadmap.current_week) ?? roadmap?.weeks[0];
  const roadmapProgress = Math.min(Math.max(roadmap?.progress_percentage ?? 0, 0), 100);

  const menuItems = [
    {
      title: 'Nhiệm vụ',
      description: 'Core Tasks & Bounty',
      href: '/candidate',
      show: true,
    },
    {
      title: 'Phát triển thành viên',
      description: 'Daily task, tiến độ, thông báo',
      href: '/member/development',
      show: true,
    },
    {
      title: 'Câu hỏi',
      description: 'Question theo cấp thành viên',
      href: '/candidate/questions',
      show: true,
    },
    {
      title: 'Lịch làm việc',
      description: 'Check-in & xem lịch',
      href: '/schedule',
      show: true,
    },
    {
      title: 'Bảng xếp hạng',
      description: 'Xem thứ hạng XP',
      href: '/leaderboard',
      show: true,
    },
    {
      title: 'Tranh Cup',
      description: 'Sự kiện thứ 6 hàng tuần',
      href: '/cups',
      show: true,
    },
    {
      title: 'Hồ sơ năng lực',
      description: 'ePortfolio',
      href: '/profile',
      show: true,
    },
    {
      title: 'Thành tích & Huy hiệu',
      description: 'Mốc phấn đấu và huy hiệu',
      href: '/achievements',
      show: true,
    },
    {
      title: 'Danh sách thành viên',
      description: 'Tìm kiếm & xem profile',
      href: '/users',
      show: true,
    },
    {
      title: 'Tạo nhiệm vụ',
      description: 'Giao task mới',
      href: '/mentor/tasks/create',
      show: canUseMentor,
    },
    {
      title: 'Review bài',
      description: 'Duyệt task thành viên',
      href: '/mentor',
      show: canUseMentor,
    },
    {
      title: 'Tổng quan lịch',
      description: 'Tổng quan lịch làm việc',
      href: '/manager/overview',
      show: canUseMentor,
    },
    {
      title: 'Quản lý phát triển',
      description: 'Daily task & promotion',
      href: '/manager/development',
      show: canUseMentor,
    },
    {
      title: 'So sánh lịch',
      description: 'Đối chiếu lịch thành viên',
      href: '/manager',
      show: canUseMentor,
    },
    {
      title: 'Quản lý users',
      description: 'Phân quyền hệ thống',
      href: '/admin/users',
      show: canUseAdmin,
    },
    {
      title: 'Zalo Daily Task',
      description: 'Liên kết và nhận quiz qua Zalo OA',
      href: '/zalo',
      show: isLearningAccount,
    },
    {
      title: 'Quản trị Zalo',
      description: 'Lịch gửi, phiên quiz và lịch sử thông báo',
      href: '/admin/zalo',
      show: canUseAdmin,
    },
    {
      title: 'Hướng dẫn sử dụng',
      description: 'Quy trình & HDSD',
      href: '/dashboard/guide',
      show: true,
    },
    {
      title: 'Bài thi & Chứng chỉ',
      description: 'Thi năng lực, tải PDF và xác minh',
      href: '/certifications',
      show: isLearningAccount,
    },
    {
      title: 'Quản trị chứng chỉ',
      description: 'Thống kê, mẫu và thu hồi',
      href: '/admin/certifications',
      show: canUseAdmin,
    },
    {
      title: 'Ngân hàng câu hỏi',
      description: 'Soạn câu hỏi và đáp án bài thi',
      href: '/admin/questions',
      show: canUseAdmin,
    },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10 shadow-sm">
        <div className="max-w-5xl mx-auto px-4">
          <div className="flex justify-between items-center h-14">
            <div className="flex items-center gap-2">
              <Image src="/logo/logo.jpg" alt="TLMS Logo" width={32} height={32} className="w-8 h-8 rounded-lg shadow-sm object-cover" />
              <span className="font-semibold text-gray-900 hidden sm:block">TLMS</span>
            </div>

            <div className="flex items-center gap-3">
              {canUseAdmin && (
                <button
                  onClick={() => router.push('/admin/users')}
                  className="text-sm text-gray-600 hover:text-[#1E90FF] px-3 py-1.5 hover:bg-blue-50 rounded-lg transition-colors hidden sm:block"
                >
                  Admin
                </button>
              )}
              
              <div className="text-right hidden sm:block">
                <p className="text-sm font-medium text-gray-900 truncate max-w-[150px]">{user.full_name || user.email}</p>
              </div>
              <button
                onClick={handleLogout}
                className="text-sm text-gray-600 hover:text-red-600 px-3 py-1.5 hover:bg-red-50 rounded-lg transition-colors"
              >
                Đăng xuất
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-6 space-y-6">
        {/* Welcome */}
        <div className="bg-gradient-to-r from-[#1E90FF] to-[#9333ea] rounded-xl p-5 sm:p-6 text-white shadow-lg">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h1 className="text-xl sm:text-2xl font-semibold">
                Xin chào, {user.full_name || user.email}
              </h1>
              <p className="text-white/80 text-sm mt-1">
                Tiếp tục hành trình học tập của bạn
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              {visibleRoles.map((role) => (
                <span key={role} className="px-2.5 py-1 bg-white/20 rounded text-xs font-medium backdrop-blur-sm">
                  {roleLabels[role]}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* First Admin Setup */}
        {!canUseAdmin && hasAdmin === false && (
          <div className="bg-[#FFA500]/10 border border-[#FFA500]/30 rounded-xl p-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h3 className="font-semibold text-[#c2410c]">Thiết lập Admin đầu tiên</h3>
                <p className="text-sm text-[#9a3412] mt-1">
                  Hệ thống chưa có Admin. Nhấn để trở thành Admin đầu tiên.
                </p>
              </div>
              <button
                onClick={handleSetFirstAdmin}
                disabled={settingAdmin}
                className="px-4 py-2 bg-[#FFA500] text-white rounded-lg hover:bg-[#ea580c] disabled:opacity-50 transition-colors text-sm font-medium whitespace-nowrap shadow-sm"
              >
                {settingAdmin ? 'Đang xử lý...' : 'Trở thành Admin'}
              </button>
            </div>
            {adminError && (
              <p className="mt-3 text-red-600 text-sm">{adminError}</p>
            )}
          </div>
        )}

        {/* Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Level</p>
            <p className="text-3xl font-semibold text-[#1E90FF] mt-1">{dashboardLevel}</p>
            <div className="mt-2">
              <div className="w-full bg-gray-100 rounded-full h-1.5">
                <div
                  className="bg-gradient-to-r from-[#1E90FF] to-[#9333ea] h-1.5 rounded-full transition-all"
                  style={{ width: `${Math.min(Math.max(xpProgress, 0), 100)}%` }}
                ></div>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">XP</p>
            <p className="text-3xl font-semibold text-[#9333ea] mt-1">{currentXp}</p>
            <p className="text-xs text-gray-500 mt-2">Cần {Math.max(xpForNextLevel - currentXp, 0)} để lên cấp</p>
          </div>

          <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Kỷ luật</p>
            <p className="text-3xl font-semibold text-gray-900 mt-1">{(user.discipline_score || 100).toFixed(0)}</p>
            <div className="mt-2">
              <div className="w-full bg-gray-100 rounded-full h-1.5">
                <div
                  className={`h-1.5 rounded-full transition-all ${
                    (user.discipline_score || 100) >= 80 ? 'bg-[#32CD32]' : (user.discipline_score || 100) >= 50 ? 'bg-[#FFA500]' : 'bg-red-500'
                  }`}
                  style={{ width: `${user.discipline_score || 100}%` }}
                ></div>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Vai trò</p>
            <div className="mt-2 flex flex-wrap gap-1">
              {visibleRoles.map((role) => (
                <span key={role} className="px-2 py-0.5 bg-[#1E90FF]/10 text-[#1E90FF] rounded text-xs font-medium">
                  {roleLabels[role]}
                </span>
              ))}
            </div>
            <p className="text-xs text-gray-500 mt-2">
              {canUseAdmin ? 'Quản trị hệ thống' :
               canUseMentor ? 'Hướng dẫn thành viên' :
               hasRole('member') ? 'Thành viên chính thức' : 'Hoàn thành task để thăng cấp'}
            </p>
          </div>
        </div>

        {roadmap && (
          <section className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
            <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-4">
              <div className="min-w-0">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Lộ trình phát triển</p>
                <div className="flex flex-wrap items-end gap-x-3 gap-y-1 mt-2">
                  <h2 className="text-2xl font-semibold text-gray-900">
                    Tuần {roadmap.current_week} / {roadmap.total_weeks}
                  </h2>
                  <span className="text-sm font-semibold text-[#9333ea] pb-1">{roadmapProgress.toFixed(1)}%</span>
                </div>
                <p className="text-sm text-gray-500 mt-1">
                  Ngày thứ {roadmap.current_day} / {roadmap.total_days}
                </p>
              </div>
              <div className="lg:text-right">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Giai đoạn hiện tại</p>
                <p className="text-sm font-semibold text-gray-900 mt-2">{roadmap.current_stage}</p>
              </div>
            </div>
            <div className="mt-4">
              <div className="w-full bg-gray-100 rounded-full h-2">
                <div
                  className="bg-gradient-to-r from-[#1E90FF] to-[#9333ea] h-2 rounded-full transition-all"
                  style={{ width: `${roadmapProgress}%` }}
                />
              </div>
            </div>
            {currentRoadmapWeek && (
              <div className="mt-4 grid grid-cols-1 lg:grid-cols-3 gap-3 text-sm">
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Câu hỏi trọng tâm</p>
                  <p className="text-gray-700 mt-1 line-clamp-2">{currentRoadmapWeek.question_focus}</p>
                </div>
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Nhiệm vụ hôm nay</p>
                  <p className="text-gray-700 mt-1 line-clamp-2">{currentRoadmapWeek.daily_task_focus}</p>
                </div>
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Kỹ năng mục tiêu</p>
                  <p className="text-gray-700 mt-1 line-clamp-2">
                    {currentRoadmapWeek.skill_targets.map(formatSkillTarget).join(', ')}
                  </p>
                </div>
              </div>
            )}
          </section>
        )}

        {development && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Cấp thành viên</p>
              <h2 className="text-lg font-semibold text-gray-900 mt-2">
                {memberLevelLabels[development.member_level] || development.member_level}
              </h2>
              <p className="text-sm text-gray-500 mt-1">
                Quyền: {visibleRoles.map((role) => roleLabels[role]).join(', ')}
              </p>
              <div className="mt-4">
                <div className="flex justify-between text-xs text-gray-500 mb-1">
                  <span>Promotion</span>
                  <span>{development.promotion_progress.toFixed(0)}%</span>
                </div>
                <div className="w-full bg-gray-100 rounded-full h-2">
                  <div
                    className="bg-[#32CD32] h-2 rounded-full transition-all"
                    style={{ width: `${Math.min(Math.max(development.promotion_progress, 0), 100)}%` }}
                  />
                </div>
              </div>
            </div>

            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Daily Task hôm nay</p>
              <div className="flex items-end gap-2 mt-2">
                <span className="text-3xl font-semibold text-[#1E90FF]">{dashboardDailyCompleted}</span>
                <span className="text-sm text-gray-500 pb-1">/ {dashboardDailyTotal} hoàn thành</span>
              </div>
              <div className="mt-3">
                <div className="w-full bg-gray-100 rounded-full h-2">
                  <div
                    className="bg-gradient-to-r from-[#1E90FF] to-[#9333ea] h-2 rounded-full transition-all"
                    style={{ width: `${Math.min(Math.max(dashboardDailyProgress, 0), 100)}%` }}
                  />
                </div>
                <p className="text-xs text-gray-500 mt-2">
                  Attendance: {development.attendance_status || 'chưa reconcile'}
                </p>
              </div>
            </div>

            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Score</p>
              <div className="grid grid-cols-3 gap-2 mt-3">
                <div>
                  <p className="text-lg font-semibold text-gray-900">{development.member_score.toFixed(0)}</p>
                  <p className="text-xs text-gray-500">Member</p>
                </div>
                <div>
                  <p className="text-lg font-semibold text-gray-900">{development.reliability_score.toFixed(0)}</p>
                  <p className="text-xs text-gray-500">Reliability</p>
                </div>
                <div>
                  <p className="text-lg font-semibold text-gray-900">{development.unread_notifications}</p>
                  <p className="text-xs text-gray-500">Chưa đọc</p>
                </div>
              </div>
              {development.notifications[0] && (
                <p className="text-sm text-gray-600 mt-4 line-clamp-2">{development.notifications[0].message}</p>
              )}
            </div>
          </div>
        )}

        {/* Account Info & Quick Links */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Account Info */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
            <div className="px-5 py-4 border-b border-gray-100">
              <h2 className="font-semibold text-gray-900">Thông tin tài khoản</h2>
            </div>
            <div className="p-5 space-y-3">
              <div className="flex justify-between py-2">
                <span className="text-sm text-gray-600">Email</span>
                <span className="text-sm font-medium text-gray-900 truncate ml-4">{user.email}</span>
              </div>
              <div className="flex justify-between py-2 border-t border-gray-50">
                <span className="text-sm text-gray-600">S4H ID</span>
                <span className="text-sm font-mono text-gray-500">{user.s4h_user_id?.slice(0, 8)}...</span>
              </div>
              <div className="flex justify-between py-2 border-t border-gray-50">
                <span className="text-sm text-gray-600">Trạng thái</span>
                <span className={`text-xs px-2 py-0.5 rounded font-medium ${
                  user.status === 'active' ? 'bg-[#32CD32]/10 text-[#22c55e]' : 
                  user.status === 'suspended' ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-700'
                }`}>
                  {user.status === 'active' ? 'Hoạt động' : 
                   user.status === 'suspended' ? 'Đình chỉ' : 'Không hoạt động'}
                </span>
              </div>
              <div className="flex justify-between py-2 border-t border-gray-50">
                <span className="text-sm text-gray-600">Ngày tham gia</span>
                <span className="text-sm text-gray-900">
                  {new Date(user.created_at).toLocaleDateString('vi-VN')}
                </span>
              </div>
            </div>
          </div>

          {/* Quick Links */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
            <div className="px-5 py-4 border-b border-gray-100">
              <h2 className="font-semibold text-gray-900">Chức năng</h2>
            </div>
            <div className="divide-y divide-gray-50">
              {menuItems.filter(item => item.show).map((item) => (
                <button 
                  key={item.href}
                  onClick={() => router.push(item.href)}
                  className="w-full flex items-center justify-between p-4 hover:bg-blue-50 transition-colors text-left group"
                >
                  <div>
                    <p className="text-sm font-medium text-gray-900 group-hover:text-[#1E90FF]">{item.title}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{item.description}</p>
                  </div>
                  <svg className="w-4 h-4 text-gray-400 group-hover:text-[#1E90FF]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </button>
              ))}
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 mt-12 bg-white">
        <div className="max-w-5xl mx-auto px-4 py-6">
          <p className="text-center text-xs text-gray-500">
            © 2026 T&A Lab Management System
          </p>
        </div>
      </footer>
    </div>
  );
}
