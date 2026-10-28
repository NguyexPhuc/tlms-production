'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { apiClient } from '@/lib/api';
import { User } from '@/types';
import Link from 'next/link';

interface UserStats {
  user_id: string;
  user_name: string;
  user_email: string;
  // All-time stats
  total_tasks: number;
  completed_tasks: number;
  in_progress_tasks: number;
  submitted_tasks: number;
  total_checkins: number;
  morning_shifts: number;
  afternoon_shifts: number;
  evening_shifts: number;
  total_hours: number;
  // Weekly stats
  weekly_tasks: number;
  weekly_completed_tasks: number;
  weekly_checkins: number;
  weekly_morning_shifts: number;
  weekly_afternoon_shifts: number;
  weekly_evening_shifts: number;
  weekly_hours: number;
}

export default function DashboardVisualizePage() {
  const router = useRouter();
  const { user: currentUser, isLoading } = useAuth();
  
  const [users, setUsers] = useState<User[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<string>('');
  const [stats, setStats] = useState<UserStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [currentWeekStart, setCurrentWeekStart] = useState<Date>(() => {
    const now = new Date();
    const day = now.getDay();
    const diff = now.getDate() - day + (day === 0 ? -6 : 1);
    return new Date(now.setDate(diff));
  });

  useEffect(() => {
    if (!isLoading && currentUser) {
      if (!currentUser.roles.includes('mentor') && !currentUser.roles.includes('admin')) {
        router.push('/dashboard');
        return;
      }
      loadUsers();
    }
  }, [isLoading, currentUser, router]);

  const loadUsers = async () => {
    try {
      const response = await apiClient.getUsers({ page_size: 1000 });
      setUsers(response.users || []);
    } catch (error) {
      console.error('Failed to load users:', error);
    }
  };

  const loadUserStats = async (userId: string) => {
    try {
      setLoading(true);
      const weekStartStr = currentWeekStart.toISOString().split('T')[0];
      const data = await apiClient.getUserStats(userId, weekStartStr);
      setStats(data);
    } catch (error) {
      console.error('Failed to load user stats:', error);
      setStats(null);
    } finally {
      setLoading(false);
    }
  };

  const previousWeek = () => {
    const newWeekStart = new Date(currentWeekStart);
    newWeekStart.setDate(currentWeekStart.getDate() - 7);
    setCurrentWeekStart(newWeekStart);
    if (selectedUserId) {
      loadUserStats(selectedUserId);
    }
  };

  const nextWeek = () => {
    const newWeekStart = new Date(currentWeekStart);
    newWeekStart.setDate(currentWeekStart.getDate() + 7);
    setCurrentWeekStart(newWeekStart);
    if (selectedUserId) {
      loadUserStats(selectedUserId);
    }
  };

  const weekEnd = new Date(currentWeekStart);
  weekEnd.setDate(currentWeekStart.getDate() + 6);

  const handleUserSelect = (userId: string) => {
    setSelectedUserId(userId);
    loadUserStats(userId);
  };

  const filteredUsers = users.filter(u =>
    u.full_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    u.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
    u.student_id?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-violet-50 via-white to-fuchsia-50 flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-violet-200 border-t-violet-600 rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-violet-50 via-white to-fuchsia-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold bg-gradient-to-r from-violet-600 to-fuchsia-600 bg-clip-text text-transparent">
                Thống kê tuần
              </h1>
              <p className="text-sm text-gray-500 mt-0.5">Thống kê chi tiết thành viên theo tuần</p>
            </div>
            <div className="flex items-center gap-2">
              <Link
                href="/mentor"
                className="px-4 py-2 text-sm text-gray-600 hover:text-violet-600 hover:bg-violet-50 rounded-lg transition-colors font-medium"
              >
                ← Quay lại
              </Link>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {/* User Selection */}
        <div className="bg-white rounded-xl shadow-md p-5">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Chọn thành viên</h2>
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Tìm kiếm theo tên, email, MSSV..."
            className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-violet-500 focus:border-violet-500 bg-gray-50 hover:bg-white transition-all mb-4"
          />
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 max-h-96 overflow-y-auto">
            {filteredUsers.map((user) => (
              <button
                key={user.id}
                onClick={() => handleUserSelect(user.id)}
                className={`p-4 rounded-xl border-2 text-left transition-all ${
                  selectedUserId === user.id
                    ? 'border-violet-500 bg-violet-50 shadow-md'
                    : 'border-gray-200 hover:border-violet-300 hover:bg-gray-50'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-violet-500 to-fuchsia-500 flex items-center justify-center text-white font-bold">
                    {(user.full_name || user.email)[0]?.toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-900 truncate">{user.full_name || user.email}</p>
                    <p className="text-xs text-gray-500 truncate">{user.email}</p>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Stats Display */}
        {loading ? (
          <div className="bg-white rounded-xl shadow-md p-12 text-center">
            <div className="w-12 h-12 border-4 border-violet-200 border-t-violet-600 rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-gray-500">Đang tải thống kê...</p>
          </div>
        ) : stats ? (
          <>
            {/* User Info Card */}
            <div className="bg-gradient-to-r from-violet-600 to-fuchsia-600 rounded-xl shadow-lg p-6 text-white">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-4">
                  <div className="w-16 h-16 rounded-full bg-white/20 flex items-center justify-center text-2xl font-bold">
                    {stats.user_name[0]?.toUpperCase()}
                  </div>
                  <div>
                    <h2 className="text-xl font-bold">{stats.user_name}</h2>
                    <p className="text-white/80">{stats.user_email}</p>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm text-white/80">Tuần này</div>
                  <div className="text-lg font-bold">
                    {currentWeekStart.toLocaleDateString('vi-VN', { day: 'numeric', month: 'numeric' })} - {weekEnd.toLocaleDateString('vi-VN', { day: 'numeric', month: 'numeric', year: 'numeric' })}
                  </div>
                </div>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={previousWeek}
                  className="px-3 py-1.5 bg-white/20 hover:bg-white/30 rounded-lg text-sm font-medium transition-colors"
                >
                  ← Tuần trước
                </button>
                <button
                  onClick={nextWeek}
                  className="px-3 py-1.5 bg-white/20 hover:bg-white/30 rounded-lg text-sm font-medium transition-colors"
                >
                  Tuần sau →
                </button>
              </div>
            </div>

            {/* Weekly Task Statistics */}
            <div className="bg-white rounded-xl shadow-md p-5 border-2 border-violet-200">
              <h3 className="text-lg font-semibold text-violet-600 mb-4 flex items-center gap-2">
                <span className="text-2xl">📝</span>
                Tasks tuần này
              </h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-violet-50 rounded-xl p-6 text-center border-2 border-violet-200">
                  <div className="text-4xl font-bold text-violet-600">{stats.weekly_tasks}</div>
                  <div className="text-sm text-gray-600 mt-2">Tasks đã làm</div>
                </div>
                <div className="bg-emerald-50 rounded-xl p-6 text-center border-2 border-emerald-200">
                  <div className="text-4xl font-bold text-emerald-600">{stats.weekly_completed_tasks}</div>
                  <div className="text-sm text-gray-600 mt-2">Hoàn thành</div>
                </div>
              </div>
              {/* Progress bar */}
              <div className="mt-4">
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-gray-600">Tỷ lệ hoàn thành</span>
                  <span className="font-bold text-emerald-600">
                    {stats.weekly_tasks > 0 ? Math.round((stats.weekly_completed_tasks / stats.weekly_tasks) * 100) : 0}%
                  </span>
                </div>
                <div className="h-4 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-emerald-500 to-teal-500 transition-all duration-500"
                    style={{ width: `${stats.weekly_tasks > 0 ? (stats.weekly_completed_tasks / stats.weekly_tasks) * 100 : 0}%` }}
                  />
                </div>
              </div>
            </div>

            {/* Weekly Attendance Statistics */}
            <div className="bg-white rounded-xl shadow-md p-5 border-2 border-blue-200">
              <h3 className="text-lg font-semibold text-blue-600 mb-4 flex items-center gap-2">
                <span className="text-2xl">✅</span>
                Check-in tuần này
              </h3>
              <div className="grid grid-cols-4 gap-4">
                <div className="bg-blue-50 rounded-xl p-6 text-center border-2 border-blue-200">
                  <div className="text-4xl font-bold text-blue-600">{stats.weekly_checkins}</div>
                  <div className="text-sm text-gray-600 mt-2">Tổng check-in</div>
                </div>
                <div className="bg-amber-50 rounded-xl p-6 text-center border-2 border-amber-200">
                  <div className="text-4xl font-bold text-amber-600">{stats.weekly_morning_shifts}</div>
                  <div className="text-sm text-gray-600 mt-2">Ca sáng</div>
                </div>
                <div className="bg-emerald-50 rounded-xl p-6 text-center border-2 border-emerald-200">
                  <div className="text-4xl font-bold text-emerald-600">{stats.weekly_afternoon_shifts}</div>
                  <div className="text-sm text-gray-600 mt-2">Ca chiều</div>
                </div>
                <div className="bg-purple-50 rounded-xl p-6 text-center border-2 border-purple-200">
                  <div className="text-4xl font-bold text-purple-600">{stats.weekly_evening_shifts}</div>
                  <div className="text-sm text-gray-600 mt-2">Ca tối</div>
                </div>
              </div>
              {/* Hours worked */}
              <div className="mt-4 bg-gradient-to-r from-violet-50 to-fuchsia-50 rounded-xl p-4 border border-violet-200">
                <div className="text-center">
                  <div className="text-3xl font-bold text-violet-600">{stats.weekly_hours}h</div>
                  <div className="text-sm text-gray-600 mt-1">Tổng giờ làm tuần này</div>
                </div>
              </div>
            </div>
          </>
        ) : selectedUserId ? (
          <div className="bg-white rounded-xl shadow-md p-12 text-center">
            <div className="text-6xl mb-4">😕</div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Không thể tải thống kê</h3>
            <p className="text-gray-500">Vui lòng thử lại sau</p>
          </div>
        ) : (
          <div className="bg-white rounded-xl shadow-md p-12 text-center">
            <div className="text-6xl mb-4">👆</div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Chọn một thành viên để xem thống kê</h3>
            <p className="text-gray-500">Thông tin sẽ hiển thị ở đây</p>
          </div>
        )}
      </main>
    </div>
  );
}
