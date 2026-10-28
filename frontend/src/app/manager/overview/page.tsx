'use client';

import { useEffect, useState, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { apiClient } from '@/lib/api';
import { User } from '@/types';
import { UserTaskListResponse } from '@/types/task';
import {
  Schedule,
  Shift,
  SHIFT_LABELS,
} from '@/types/schedule';

interface UserScheduleData {
  user: {
    id: string;
    full_name: string;
    email: string;
    student_id?: string;
  };
  schedules: Schedule[];
  class_schedules: any[];
}

interface SlotData {
  users: {
    id: string;
    name: string;
  }[];
}

interface ModalData {
  users: SlotData['users'];
  shift: string;
  date: string;
}

export default function ManagerOverviewPage() {
  const { user, isLoading: authLoading } = useAuth();
  const router = useRouter();
  
  const [weekStart, setWeekStart] = useState<Date>(getMonday(new Date()));
  const [users, setUsers] = useState<User[]>([]);
  const [usersScheduleData, setUsersScheduleData] = useState<Record<string, UserScheduleData>>({});
  const [loading, setLoading] = useState(true);
  const [loadingSchedules, setLoadingSchedules] = useState(false);
  const [modalData, setModalData] = useState<ModalData | null>(null);
  
  // Task modal state
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [userTasks, setUserTasks] = useState<UserTaskListResponse | null>(null);
  const [userStats, setUserStats] = useState<any | null>(null);
  const [loadingTasks, setLoadingTasks] = useState(false);
  const [selectedTask, setSelectedTask] = useState<any | null>(null);
  
  const hasRole = (role: string) => user?.roles?.includes(role as any) ?? false;
  const canAccess = hasRole('admin') || hasRole('mentor');
  
  function getMonday(date: Date): Date {
    const d = new Date(date);
    const day = d.getDay();
    const diff = d.getDate() - day + (day === 0 ? -6 : 1);
    return new Date(d.setDate(diff));
  }
  
  function formatDate(date: Date): string {
    return date.toISOString().split('T')[0];
  }
  
  function getWeekDates(): Date[] {
    const dates = [];
    for (let i = 0; i < 7; i++) {
      const date = new Date(weekStart);
      date.setDate(weekStart.getDate() + i);
      dates.push(date);
    }
    return dates;
  }
  
  const loadAllUsersSchedules = useCallback(async () => {
    try {
      setLoading(true);
      // First load all users
      const response = await apiClient.listUsers({ page_size: 1000 });
      const allUsers = response.users || [];
      setUsers(allUsers);

      if (allUsers.length === 0) {
        setUsersScheduleData({});
        setLoading(false);
        return;
      }

      // Then load all schedules
      setLoadingSchedules(true);
      const weekStartStr = formatDate(weekStart);
      const userIds = allUsers.map((u: User) => u.id);
      const data = await apiClient.getUsersSchedulesForManager(weekStartStr, userIds);
      setUsersScheduleData(data);
    } catch (error) {
      console.error('Failed to load data:', error);
    } finally {
      setLoading(false);
      setLoadingSchedules(false);
    }
  }, [weekStart]);

  // Highlight matching text
  const highlightMatch = (text: string | null | undefined, searchQuery: string) => {
    if (!text || !searchQuery.trim()) return text;
    
    const searchWords = searchQuery.toLowerCase().trim().split(/\s+/).filter(w => w.length > 0);
    let highlighted = text;
    
    searchWords.forEach(word => {
      const regex = new RegExp(`(${word})`, 'gi');
      highlighted = highlighted.replace(regex, '<mark class="bg-yellow-200 text-gray-900 font-medium">$1</mark>');
    });
    
    return <span dangerouslySetInnerHTML={{ __html: highlighted }} />;
  };

  const loadUserTasks = async (userId: string) => {
    try {
      setLoadingTasks(true);
      const [tasksData, statsData] = await Promise.all([
        apiClient.getUserTasks(userId),
        apiClient.getUserStats(userId)
      ]);
      setUserTasks(tasksData);
      setUserStats(statsData);
    } catch (error) {
      console.error('Failed to load user data:', error);
      setUserTasks(null);
      setUserStats(null);
    } finally {
      setLoadingTasks(false);
    }
  };

  const handleUserClick = (user: User) => {
    setSelectedUser(user);
    loadUserTasks(user.id);
  };

  const closeTaskModal = () => {
    setSelectedUser(null);
    setUserTasks(null);
    setUserStats(null);
    setSelectedTask(null);
  };
  
  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login');
      return;
    }
    
    if (user && canAccess) {
      loadAllUsersSchedules();
    }
  }, [user, authLoading, router, canAccess, loadAllUsersSchedules]);
  
  function previousWeek() {
    const newWeekStart = new Date(weekStart);
    newWeekStart.setDate(weekStart.getDate() - 7);
    setWeekStart(newWeekStart);
  }
  
  function nextWeek() {
    const newWeekStart = new Date(weekStart);
    newWeekStart.setDate(weekStart.getDate() + 7);
    setWeekStart(newWeekStart);
  }
  
  // Build combined schedule data
  function getSlotData(dateStr: string, shift: Shift): SlotData {
    const slotUsers: SlotData['users'] = [];
    
    Object.values(usersScheduleData).forEach((userData) => {
      const schedule = userData.schedules.find(
        s => s.work_date === dateStr && s.shift === shift && !s.is_cancelled
      );
      
      if (schedule) {
        slotUsers.push({
          id: userData.user.id,
          name: userData.user.full_name || userData.user.email.split('@')[0]
        });
      }
    });
    
    return { users: slotUsers };
  }
  
  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="w-6 h-6 border-2 border-gray-300 border-t-[#1E90FF] rounded-full animate-spin"></div>
      </div>
    );
  }
  
  if (!user || !canAccess) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
        <div className="bg-white border border-red-200 rounded-xl p-6 max-w-md w-full shadow-sm">
          <h2 className="text-lg font-semibold text-red-600 mb-2">Không có quyền truy cập</h2>
          <p className="text-sm text-gray-600 mb-4">Chỉ Admin và Mentor mới có quyền truy cập trang này.</p>
          <button
            onClick={() => router.push('/dashboard')}
            className="w-full px-4 py-2 bg-[#1E90FF] text-white rounded-lg hover:bg-[#1a7de0] text-sm font-medium transition-colors"
          >
            Quay về Dashboard
          </button>
        </div>
      </div>
    );
  }
  
  const weekDates = getWeekDates();
  const today = formatDate(new Date());
  
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-semibold text-gray-900">Tổng quan lịch làm việc</h1>
              <p className="text-sm text-gray-500 mt-0.5">Xem tất cả người có lịch làm trong tuần</p>
            </div>
            <div className="flex items-center gap-2">
              <Link
                href="/mentor/weekly-stats"
                className="px-3 py-2 bg-gradient-to-r from-violet-600 to-fuchsia-600 text-white rounded-lg hover:from-violet-700 hover:to-fuchsia-700 text-sm font-medium transition-all shadow-sm"
              >
                📊 Thống kê tuần
              </Link>
              <button
                onClick={() => router.push('/manager')}
                className="px-3 py-2 text-sm text-gray-600 hover:text-[#1E90FF] hover:bg-blue-50 rounded-lg transition-colors"
              >
                Xem từng người
              </button>
              <button
                onClick={() => router.push('/dashboard')}
                className="px-3 py-2 text-sm text-gray-600 hover:text-[#1E90FF] hover:bg-blue-50 rounded-lg transition-colors"
              >
                ← Quay lại
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {/* Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Tổng thành viên</p>
            <p className="text-2xl font-semibold text-[#1E90FF] mt-1">{users.length}</p>
          </div>
          <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Có lịch tuần này</p>
            <p className="text-2xl font-semibold text-[#32CD32] mt-1">
              {Object.values(usersScheduleData).filter(d => d.schedules.length > 0).length}
            </p>
          </div>
          <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Tổng ca làm</p>
            <p className="text-2xl font-semibold text-[#9333ea] mt-1">
              {Object.values(usersScheduleData).reduce((sum, d) => sum + d.schedules.filter(s => !s.is_cancelled).length, 0)}
            </p>
          </div>
          <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Đã hủy</p>
            <p className="text-2xl font-semibold text-[#FFA500] mt-1">
              {Object.values(usersScheduleData).reduce((sum, d) => sum + d.schedules.filter(s => s.is_cancelled).length, 0)}
            </p>
          </div>
        </div>

        {/* Week Navigation */}
        <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-gray-900">Lịch tuần</h2>
            <div className="flex items-center gap-2">
              <button onClick={previousWeek} className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
                <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
              <span className="text-sm font-medium text-gray-700 min-w-[160px] text-center">
                {formatDate(weekDates[0])} - {formatDate(weekDates[6])}
              </span>
              <button onClick={nextWeek} className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
                <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
              <button 
                onClick={loadAllUsersSchedules}
                disabled={loadingSchedules}
                className="ml-2 px-3 py-1.5 text-xs bg-[#1E90FF]/10 text-[#1E90FF] rounded-lg hover:bg-[#1E90FF]/20 disabled:opacity-50 font-medium"
              >
                {loadingSchedules ? 'Đang tải...' : 'Làm mới'}
              </button>
            </div>
          </div>
        </div>
        
        {/* Combined Schedule Table */}
        {loading || loadingSchedules ? (
          <div className="bg-white rounded-xl border border-gray-200 p-12 text-center shadow-sm">
            <div className="w-6 h-6 border-2 border-gray-300 border-t-[#1E90FF] rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-sm text-gray-500">Đang tải lịch...</p>
          </div>
        ) : (
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[900px]">
                <thead>
                  <tr className="bg-gray-50">
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide w-28 border-b border-gray-200">Ca làm</th>
                    {weekDates.map((date, idx) => (
                      <th 
                        key={idx} 
                        className={`px-3 py-3 text-center text-xs font-medium uppercase tracking-wide border-b border-gray-200 ${
                          formatDate(date) === today ? 'bg-[#1E90FF]/10 text-[#1E90FF]' : 'text-gray-500'
                        }`}
                      >
                        <div>{['CN', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7'][date.getDay()]}</div>
                        <div className="font-semibold text-sm mt-0.5">{date.getDate()}/{date.getMonth() + 1}</div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {[Shift.MORNING, Shift.AFTERNOON, Shift.EVENING].map(shift => (
                    <tr key={shift} className="border-b border-gray-100 last:border-b-0">
                      <td className="px-4 py-4 text-sm font-medium text-gray-700 bg-gray-50 align-middle">
                        {SHIFT_LABELS[shift]}
                      </td>
                      {weekDates.map((date, idx) => {
                        const dateStr = formatDate(date);
                        const slotData = getSlotData(dateStr, shift);
                        const isSunday = date.getDay() === 0;
                        const isToday = dateStr === today;
                        const displayLimit = 2;
                        const remainingCount = slotData.users.length - displayLimit;
                        
                        return (
                          <td 
                            key={idx} 
                            className={`px-3 py-3 align-middle min-w-[120px] ${
                              isToday ? 'bg-[#1E90FF]/5' : ''
                            } ${isSunday ? 'bg-gray-100' : ''}`}
                          >
                            {isSunday ? (
                              <span className="text-xs text-gray-400">Nghỉ</span>
                            ) : slotData.users.length === 0 ? (
                              <span className="text-xs text-gray-300">—</span>
                            ) : (
                              <div 
                                className="space-y-1 cursor-pointer group"
                                onClick={() => setModalData({
                                  users: slotData.users,
                                  shift: SHIFT_LABELS[shift],
                                  date: `${date.getDate()}/${date.getMonth() + 1}`
                                })}
                              >
                                {slotData.users.slice(0, displayLimit).map((u) => (
                                  <div 
                                    key={u.id}
                                    className="text-xs px-2 py-1 rounded bg-[#1E90FF]/10 text-[#1E90FF] group-hover:bg-[#1E90FF]/20 transition-colors truncate max-w-[100px]"
                                    title={u.name}
                                  >
                                    {u.name}
                                  </div>
                                ))}
                                {remainingCount > 0 && (
                                  <div className="text-xs px-2 py-1 rounded bg-[#32CD32]/10 text-[#32CD32] group-hover:bg-[#32CD32]/20 transition-colors font-medium">
                                    +{remainingCount} người khác
                                  </div>
                                )}
                                <div className="text-[10px] text-gray-400 group-hover:text-[#1E90FF] transition-colors">
                                  Click xem chi tiết
                                </div>
                              </div>
                            )}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
        
        {/* Legend */}
        <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
          <h3 className="text-sm font-medium text-gray-700 mb-3">Chú thích</h3>
          <div className="flex flex-wrap gap-4 text-xs">
            <div className="flex items-center gap-2">
              <span className="inline-block px-2 py-1 bg-[#1E90FF]/10 text-[#1E90FF] rounded font-medium">Tên</span>
              <span className="text-gray-600">Có lịch làm</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="inline-block px-2 py-1 bg-[#32CD32]/10 text-[#32CD32] rounded font-medium">+N</span>
              <span className="text-gray-600">Số người khác</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="inline-block w-6 h-6 bg-gray-100 rounded"></span>
              <span className="text-gray-600">Chủ nhật (Nghỉ)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="inline-block w-6 h-6 bg-[#1E90FF]/10 rounded border border-[#1E90FF]/30"></span>
              <span className="text-gray-600">Hôm nay</span>
            </div>
          </div>
        </div>
      </main>

      {/* Modal Popup */}
      {modalData && (
        <div 
          className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
          onClick={() => setModalData(null)}
        >
          <div 
            className="bg-white rounded-2xl shadow-xl max-w-md w-full max-h-[80vh] overflow-hidden animate-in fade-in zoom-in duration-200"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="bg-gradient-to-r from-[#1E90FF] to-[#32CD32] px-6 py-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-white">
                    {modalData.shift} - {modalData.date}
                  </h3>
                  <p className="text-white/80 text-sm">
                    {modalData.users.length} người có lịch làm
                  </p>
                </div>
                <button 
                  onClick={() => setModalData(null)}
                  className="w-8 h-8 rounded-full bg-white/20 hover:bg-white/30 flex items-center justify-center transition-colors"
                >
                  <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
            
            {/* Modal Body */}
            <div className="p-4 overflow-y-auto max-h-[60vh]">
              <div className="space-y-2">
                {modalData.users.map((u, index) => {
                  // Find full user object
                  const fullUser = users.find(user => user.id === u.id);
                  return (
                    <div
                      key={u.id}
                      className="flex items-center gap-3 p-3 rounded-xl bg-gray-50 hover:bg-[#1E90FF]/5 transition-colors cursor-pointer"
                      onClick={() => fullUser && handleUserClick(fullUser)}
                    >
                      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#1E90FF] to-[#32CD32] flex items-center justify-center text-white font-medium text-sm">
                        {index + 1}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-gray-900 truncate">{u.name}</p>
                      </div>
                      <div className="px-2 py-1 rounded-full bg-[#32CD32]/10 text-[#32CD32] text-xs font-medium">
                        Làm
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
            
            {/* Modal Footer */}
            <div className="px-6 py-4 border-t border-gray-100 bg-gray-50">
              <button
                onClick={() => setModalData(null)}
                className="w-full px-4 py-2.5 bg-[#1E90FF] text-white rounded-xl hover:bg-[#1a7de0] font-medium transition-colors"
              >
                Đóng
              </button>
            </div>
          </div>
        </div>
      )}

      {/* User Task Modal */}
      {selectedUser && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={closeTaskModal}>
          <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[80vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            {/* Modal Header */}
            <div className="sticky top-0 bg-gradient-to-r from-violet-600 to-fuchsia-600 text-white px-6 py-4 rounded-t-2xl">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold">{selectedUser.full_name || selectedUser.email}</h2>
                  <p className="text-sm text-white/80 mt-0.5">
                    {selectedUser.student_id && `MSSV: ${selectedUser.student_id} • `}
                    {selectedUser.roles?.join(', ') || 'User'}
                  </p>
                </div>
                <button
                  onClick={closeTaskModal}
                  className="w-8 h-8 bg-white/20 hover:bg-white/30 rounded-full flex items-center justify-center transition-colors"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>

            {/* Modal Body */}
            <div className="p-6">
              {loadingTasks ? (
                <div className="text-center py-12">
                  <div className="w-10 h-10 border-4 border-violet-200 border-t-violet-600 rounded-full animate-spin mx-auto mb-4"></div>
                  <p className="text-gray-500">Đang tải tasks...</p>
                </div>
              ) : userTasks ? (
                <>
                  {/* Stats Summary */}
                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
                    <div className="bg-violet-50 rounded-xl p-4 text-center">
                      <div className="text-2xl font-bold text-violet-600">{userTasks.total}</div>
                      <div className="text-xs text-gray-600 mt-1">Tổng tasks</div>
                    </div>
                    <div className="bg-emerald-50 rounded-xl p-4 text-center">
                      <div className="text-2xl font-bold text-emerald-600">{userTasks.completed_count}</div>
                      <div className="text-xs text-gray-600 mt-1">Hoàn thành</div>
                    </div>
                    <div className="bg-blue-50 rounded-xl p-4 text-center">
                      <div className="text-2xl font-bold text-blue-600">{userTasks.in_progress_count}</div>
                      <div className="text-xs text-gray-600 mt-1">Đang làm</div>
                    </div>
                    <div className="bg-amber-50 rounded-xl p-4 text-center">
                      <div className="text-2xl font-bold text-amber-600">{userTasks.pending_count}</div>
                      <div className="text-xs text-gray-600 mt-1">Chờ review</div>
                    </div>
                    <div className="bg-gradient-to-br from-violet-50 to-fuchsia-50 rounded-xl p-4 text-center border-2 border-violet-200">
                      <div className="text-2xl font-bold text-violet-600">{userStats?.weekly_hours || 0}h</div>
                      <div className="text-xs text-gray-600 mt-1">Giờ làm tuần này</div>
                    </div>
                    <div className="bg-gradient-to-br from-emerald-50 to-teal-50 rounded-xl p-4 text-center border-2 border-emerald-200">
                      <div className="text-2xl font-bold text-emerald-600">{userStats?.total_hours || 0}h</div>
                      <div className="text-xs text-gray-600 mt-1">Tổng giờ làm</div>
                    </div>
                  </div>

                  {/* Tasks List */}
                  <div className="space-y-3">
                    <h3 className="font-semibold text-gray-900 mb-3">Danh sách tasks</h3>
                    {userTasks.tasks.length === 0 ? (
                      <div className="text-center py-8 text-gray-500">
                        <div className="text-4xl mb-2">📝</div>
                        <p>Chưa có task nào</p>
                      </div>
                    ) : (
                      userTasks.tasks.map((userTask) => (
                        <div
                          key={userTask.id}
                          className="border border-gray-200 rounded-xl p-4 hover:border-violet-200 hover:shadow-sm transition-all cursor-pointer"
                          onClick={() => setSelectedTask(userTask)}
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-2">
                                <span className={`px-2 py-0.5 text-xs font-medium rounded ${
                                  userTask.task.type === 'core' ? 'bg-red-100 text-red-700' : 'bg-blue-100 text-blue-700'
                                }`}>
                                  {userTask.task.type.toUpperCase()}
                                </span>
                                <span className={`px-2 py-0.5 text-xs font-medium rounded ${
                                  userTask.status === 'completed' ? 'bg-emerald-100 text-emerald-700' :
                                  userTask.status === 'in_progress' ? 'bg-blue-100 text-blue-700' :
                                  userTask.status === 'submitted' ? 'bg-amber-100 text-amber-700' :
                                  userTask.status === 'rejected' ? 'bg-red-100 text-red-700' :
                                  'bg-gray-100 text-gray-700'
                                }`}>
                                  {userTask.status.replace('_', ' ').toUpperCase()}
                                </span>
                                <span className="text-xs text-emerald-600 font-medium">+{userTask.xp_earned} XP</span>
                              </div>
                              <h4 className="font-medium text-gray-900 mb-1">{userTask.task.title}</h4>
                              <p className="text-sm text-gray-600 line-clamp-2">{userTask.task.description}</p>
                              {userTask.proof_link && (
                                <a
                                  href={userTask.proof_link}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-xs text-violet-600 hover:underline mt-2 inline-block"
                                  onClick={(e) => e.stopPropagation()}
                                >
                                  🔗 Xem bài làm
                                </a>
                              )}
                              {userTask.mentor_comment && (
                                <div className="mt-2 p-2 bg-gray-50 rounded text-xs text-gray-700">
                                  <span className="font-medium">Nhận xét:</span> {userTask.mentor_comment}
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </>
              ) : (
                <div className="text-center py-12 text-gray-500">
                  <p>Không thể tải thông tin tasks</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Task Detail Modal */}
      {selectedTask && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setSelectedTask(null)}>
          <div className="bg-white rounded-2xl max-w-3xl w-full max-h-[80vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            {/* Modal Header */}
            <div className="sticky top-0 bg-gradient-to-r from-violet-600 to-fuchsia-600 text-white px-6 py-4 rounded-t-2xl">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold">Chi tiết Task</h2>
                  <p className="text-sm text-white/80 mt-0.5">
                    {selectedTask.task.type.toUpperCase()} • {selectedTask.status.replace('_', ' ').toUpperCase()}
                  </p>
                </div>
                <button
                  onClick={() => setSelectedTask(null)}
                  className="w-8 h-8 bg-white/20 hover:bg-white/30 rounded-full flex items-center justify-center transition-colors"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>

            {/* Modal Body */}
            <div className="p-6">
              {/* Task Info */}
              <div className="mb-6">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-lg font-bold text-gray-900">{selectedTask.task.title}</h3>
                  {selectedTask.task.creator_name && (
                    <div className="px-3 py-1.5 bg-violet-100 text-violet-700 rounded-lg text-xs font-medium whitespace-nowrap">
                      👤 Tạo bởi: {selectedTask.task.creator_name}
                    </div>
                  )}
                </div>
                <p className="text-gray-600">{selectedTask.task.description}</p>
                
                <div className="flex flex-wrap gap-2 mt-3">
                  <span className={`px-2 py-1 text-xs font-medium rounded ${
                    selectedTask.task.type === 'core' ? 'bg-red-100 text-red-700' : 'bg-blue-100 text-blue-700'
                  }`}>
                    {selectedTask.task.type.toUpperCase()}
                  </span>
                  <span className={`px-2 py-1 text-xs font-medium rounded ${
                    selectedTask.status === 'completed' ? 'bg-emerald-100 text-emerald-700' :
                    selectedTask.status === 'in_progress' ? 'bg-blue-100 text-blue-700' :
                    selectedTask.status === 'submitted' ? 'bg-amber-100 text-amber-700' :
                    selectedTask.status === 'rejected' ? 'bg-red-100 text-red-700' :
                    'bg-gray-100 text-gray-700'
                  }`}>
                    {selectedTask.status.replace('_', ' ').toUpperCase()}
                  </span>
                  <span className="px-2 py-1 text-xs font-medium rounded bg-emerald-100 text-emerald-700">
                    +{selectedTask.xp_earned} XP
                  </span>
                  {selectedTask.task.skill_tags?.length > 0 && (
                    selectedTask.task.skill_tags.slice(0, 5).map((skill: string, idx: number) => (
                      <span key={idx} className="px-2 py-1 text-xs font-medium rounded bg-gray-100 text-gray-700">
                        {skill}
                      </span>
                    ))
                  )}
                </div>
              </div>

              {/* Stats Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
                <div className="bg-violet-50 rounded-xl p-3 text-center">
                  <div className="text-xs text-gray-600">Độ khó</div>
                  <div className="text-sm font-bold text-violet-600 mt-1">{selectedTask.task.difficulty.toUpperCase()}</div>
                </div>
                <div className="bg-blue-50 rounded-xl p-3 text-center">
                  <div className="text-xs text-gray-600">Level yêu cầu</div>
                  <div className="text-sm font-bold text-blue-600 mt-1">Lv.{selectedTask.task.min_level_required}</div>
                </div>
                <div className="bg-amber-50 rounded-xl p-3 text-center">
                  <div className="text-xs text-gray-600">XP Reward</div>
                  <div className="text-sm font-bold text-amber-600 mt-1">+{selectedTask.task.xp_reward}</div>
                </div>
                <div className="bg-emerald-50 rounded-xl p-3 text-center">
                  <div className="text-xs text-gray-600">XP nhận được</div>
                  <div className="text-sm font-bold text-emerald-600 mt-1">+{selectedTask.xp_earned}</div>
                </div>
              </div>

              {/* Instructions */}
              {selectedTask.task.instructions && (
                <div className="mb-6">
                  <h4 className="font-semibold text-gray-900 mb-2 flex items-center gap-2">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    Hướng dẫn
                  </h4>
                  <div className="bg-gray-50 rounded-xl p-4 text-sm text-gray-700 whitespace-pre-wrap">
                    {selectedTask.task.instructions}
                  </div>
                </div>
              )}

              {/* Reference Links */}
              {selectedTask.task.reference_links?.length > 0 && (
                <div className="mb-6">
                  <h4 className="font-semibold text-gray-900 mb-2 flex items-center gap-2">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                    </svg>
                    Tài liệu tham khảo
                  </h4>
                  <ul className="space-y-1">
                    {selectedTask.task.reference_links.map((link: string, idx: number) => (
                      <li key={idx}>
                        <a
                          href={link}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sm text-violet-600 hover:underline flex items-center gap-1"
                        >
                          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                          </svg>
                          {link}
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Submission Info */}
              <div className="border-t border-gray-200 pt-4 mt-6">
                <h4 className="font-semibold text-gray-900 mb-3">Thông tin nộp bài</h4>
                
                {selectedTask.proof_link && (
                  <div className="mb-3">
                    <p className="text-sm text-gray-600 mb-1">Link bài làm:</p>
                    <a
                      href={selectedTask.proof_link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-violet-600 hover:underline flex items-center gap-1"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                      </svg>
                      {selectedTask.proof_link}
                    </a>
                  </div>
                )}
                
                {selectedTask.submission_notes && (
                  <div className="mb-3">
                    <p className="text-sm text-gray-600 mb-1">Ghi chú:</p>
                    <div className="bg-gray-50 rounded-lg p-3 text-sm text-gray-700 whitespace-pre-wrap">
                      {selectedTask.submission_notes}
                    </div>
                  </div>
                )}
                
                {selectedTask.mentor_comment && (
                  <div className="mb-3">
                    <p className="text-sm text-gray-600 mb-1">Nhận xét từ mentor:</p>
                    <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm text-amber-800">
                      {selectedTask.mentor_comment}
                    </div>
                  </div>
                )}
                
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <span className="text-gray-500">Bắt đầu:</span>
                    <p className="font-medium text-gray-900">
                      {selectedTask.started_at ? new Date(selectedTask.started_at).toLocaleString('vi-VN') : 'Chưa bắt đầu'}
                    </p>
                  </div>
                  <div>
                    <span className="text-gray-500">Nộp bài:</span>
                    <p className="font-medium text-gray-900">
                      {selectedTask.submitted_at ? new Date(selectedTask.submitted_at).toLocaleString('vi-VN') : 'Chưa nộp'}
                    </p>
                  </div>
                  <div>
                    <span className="text-gray-500">Hoàn thành:</span>
                    <p className="font-medium text-gray-900">
                      {selectedTask.completed_at ? new Date(selectedTask.completed_at).toLocaleString('vi-VN') : 'Chưa hoàn thành'}
                    </p>
                  </div>
                  <div>
                    <span className="text-gray-500">Review:</span>
                    <p className="font-medium text-gray-900">
                      {selectedTask.reviewed_at ? new Date(selectedTask.reviewed_at).toLocaleString('vi-VN') : 'Chưa review'}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="sticky bottom-0 bg-gray-50 px-6 py-4 border-t border-gray-200 rounded-b-2xl">
              <button
                onClick={() => setSelectedTask(null)}
                className="w-full px-4 py-2.5 bg-gradient-to-r from-violet-600 to-fuchsia-600 text-white rounded-xl hover:from-violet-700 hover:to-fuchsia-700 font-semibold transition-all shadow-lg"
              >
                Đóng
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
