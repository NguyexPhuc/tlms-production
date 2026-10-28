'use client';

import { useEffect, useRef, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api';
import {
  Schedule,
  Shift,
  SHIFT_LABELS,
  Attendance,
  AttendanceStats,
  ATTENDANCE_STATUS_LABELS,
  ATTENDANCE_STATUS_COLORS,
  ClassSchedule
} from '@/types/schedule';

export default function SchedulePage() {
  const { user, refreshUser } = useAuth();
  const router = useRouter();
  
  const [weekStart, setWeekStart] = useState<Date>(getMonday(new Date()));
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [attendances, setAttendances] = useState<Attendance[]>([]);
  const [stats, setStats] = useState<AttendanceStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [classSchedules, setClassSchedules] = useState<ClassSchedule[]>([]);
  const [showStudentIdModal, setShowStudentIdModal] = useState(false);
  const [inputStudentId, setInputStudentId] = useState('');
  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const syncedWeeks = useRef<Set<string>>(new Set());
  
  useEffect(() => {
    if (user) {
      loadData();
    }
  }, [user, weekStart]);
  
  function getMonday(date: Date): Date {
    const d = new Date(date);
    const day = d.getDay();
    const diff = d.getDate() - day + (day === 0 ? -6 : 1);
    return new Date(d.setDate(diff));
  }
  
  function formatDate(date: Date): string {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  function openStudentIdModal() {
    setInputStudentId(user?.student_id || '');
    setSyncMessage(null);
    setShowStudentIdModal(true);
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
  
  async function loadData() {
    setLoading(true);
    try {
      const currentDate = new Date();
      const weekStartStr = formatDate(weekStart);
      const currentWeekStartStr = formatDate(getMonday(currentDate));
      const isCurrentWeek = weekStartStr === currentWeekStartStr;
      const todayStr = formatDate(currentDate);
      const syncKey = `lhu_synced_${weekStartStr}`;
      const lastSyncedToday = typeof window !== 'undefined' && localStorage.getItem(syncKey) === todayStr;

      const schedulesRes = await apiClient.getWeekSchedules(weekStartStr);
      setSchedules(schedulesRes.schedules || []);
      setClassSchedules(schedulesRes.class_schedules || []);

      const hasNoData = !schedulesRes.class_schedules?.length;
      // Auto-sync if: no data at all, OR it's the current week and hasn't been synced today
      const shouldAutoSync = user?.student_id &&
          !syncedWeeks.current.has(weekStartStr) &&
          (hasNoData || (isCurrentWeek && !lastSyncedToday));

      if (shouldAutoSync) {
          syncedWeeks.current.add(weekStartStr);
          try {
            // Force fetch from LHU when current week has stale cached data
            const forceUpdate = !hasNoData && isCurrentWeek && !lastSyncedToday;
            await apiClient.syncStudentSchedule(weekStartStr, forceUpdate);
            if (isCurrentWeek && typeof window !== 'undefined') {
              localStorage.setItem(syncKey, todayStr);
            }
            const res = await apiClient.getWeekSchedules(weekStartStr);
            setSchedules(res.schedules || []);
            setClassSchedules(res.class_schedules || []);
          } catch (err: any) {
            console.warn('Auto sync failed (student schedule may not be available):', err);
            setSyncMessage({
              type: 'error',
              text: err.response?.data?.detail || 'Chưa thể tự đồng bộ lịch từ LHU.',
            });
          }
      }
      
      const monthStart = new Date(currentDate.getFullYear(), currentDate.getMonth(), 1);
      const monthEnd = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 0);
      
      const attendancesRes = await apiClient.getMyAttendances({
        start_date: formatDate(monthStart),
        end_date: formatDate(monthEnd)
      });
      setAttendances(attendancesRes || []);
      
      const statsRes = await apiClient.getAttendanceStats({
        start_date: formatDate(monthStart),
        end_date: formatDate(monthEnd)
      });
      setStats(statsRes);
      
    } catch (error) {
      console.error('Failed to load schedule data:', error);
    } finally {
      setLoading(false);
    }
  }

  async function handleSyncSchedule() {
    if (!user?.student_id) {
      openStudentIdModal();
      return;
    }
    setSyncing(true);
    setSyncMessage(null);
    try {
      const weekStartStr = formatDate(weekStart);
      await apiClient.syncStudentSchedule(weekStartStr, true); // force=true: luôn lấy mới từ LHU
      // Cập nhật localStorage để tránh auto-sync lại ngay sau đó
      if (typeof window !== 'undefined') {
        localStorage.setItem(`lhu_synced_${weekStartStr}`, formatDate(new Date()));
      }
      syncedWeeks.current.add(weekStartStr);
      await loadData();
      setSyncMessage({ type: 'success', text: 'Lịch học đã được đồng bộ từ LHU.' });
    } catch (error: any) {
      console.error('Failed to sync schedule:', error);

      if (error.response?.data?.detail?.includes('Student ID') ||
          error.response?.data?.detail?.includes('Mã sinh viên')) {
        openStudentIdModal();
      } else {
        setSyncMessage({
          type: 'error',
          text: error.response?.data?.detail || 'Đồng bộ thất bại. Vui lòng thử lại.',
        });
      }
    } finally {
      setSyncing(false);
    }
  }

  async function handleUpdateStudentId() {
    if (!inputStudentId.trim()) return;
    setSyncing(true);
    setSyncMessage(null);
    try {
      await apiClient.updateStudentId(inputStudentId);
      await refreshUser();
      const weekStartStr = formatDate(weekStart);
      await apiClient.syncStudentSchedule(weekStartStr, true);
      if (typeof window !== 'undefined') {
        localStorage.setItem(`lhu_synced_${weekStartStr}`, formatDate(new Date()));
      }
      syncedWeeks.current.add(weekStartStr);
      await loadData();
      setShowStudentIdModal(false);
      setSyncMessage({ type: 'success', text: 'Đã lưu MSSV và đồng bộ lịch học thành công.' });
    } catch (error: any) {
      console.error('Failed to update student ID:', error);
      setSyncMessage({
        type: 'error',
        text: error.response?.data?.detail || 'Không thể lưu MSSV hoặc đồng bộ lịch.',
      });
    } finally {
      setSyncing(false);
    }
  }

  function getClassForSlot(dateStr: string, shift: Shift): ClassSchedule | undefined {
    return classSchedules.find(cs => {
      if (cs.is_cancelled) return false;

      const start = new Date(cs.start_datetime);
      const csDateStr = formatDate(start);
      
      if (csDateStr !== dateStr) return false;
      
      const hour = start.getHours();
      
      if (shift === Shift.MORNING && hour >= 6 && hour < 12) return true;
      if (shift === Shift.AFTERNOON && hour >= 12 && hour < 17) return true;
      if (shift === Shift.EVENING && hour >= 17 && hour < 22) return true;
      
      return false;
    });
  }
  
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
  
  function isShiftScheduled(dateStr: string, shift: Shift): boolean {
    return schedules.some(s => s.work_date === dateStr && s.shift === shift && !s.is_cancelled);
  }
  
  async function handleCancelSchedule(scheduleId: string) {
    const reason = prompt('Nhập lý do hủy lịch:');
    if (!reason) return;
    
    try {
      await apiClient.cancelSchedule(scheduleId, reason);
      await loadData();
      alert('Đã hủy lịch');
    } catch (error: any) {
      console.error('Failed to cancel schedule:', error);
      alert(error.response?.data?.detail || 'Hủy lịch thất bại');
    }
  }

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-gray-300 border-t-[#1E90FF] rounded-full animate-spin"></div>
      </div>
    );
  }
  
  const weekDates = getWeekDates();
  const today = formatDate(new Date());

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10 shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="min-w-0 flex-1">
              <h1 className="text-xl font-semibold text-gray-900 truncate">Lịch làm việc</h1>
              {user?.student_id && (
                <p className="text-sm text-gray-500 mt-0.5">
                  MSSV: {user.student_id}
                  <button 
                    onClick={openStudentIdModal}
                    className="ml-2 text-[#1E90FF] hover:text-[#1a7de0]"
                  >
                    Đổi
                  </button>
                </p>
              )}
            </div>
            <button
              onClick={() => router.push('/dashboard')}
              className="ml-4 px-3 py-2 text-sm text-gray-600 hover:text-[#1E90FF] hover:bg-blue-50 rounded-lg transition-colors"
            >
              ← Quay lại
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-6 space-y-6">
        {syncMessage && (
          <div
            role="status"
            className={`rounded-lg border px-4 py-3 text-sm ${
              syncMessage.type === 'success'
                ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
                : 'border-red-200 bg-red-50 text-red-700'
            }`}
          >
            {syncMessage.text}
          </div>
        )}
        {/* Stats Grid */}
        {stats && (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <div className="bg-white rounded-lg p-4 border border-gray-200 shadow-sm">
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Tỷ lệ tham dự</p>
              <p className="text-2xl font-semibold text-[#1E90FF] mt-1">{stats.attendance_rate}%</p>
              <p className="text-xs text-gray-500 mt-1">{stats.total_attended}/{stats.total_scheduled} ca</p>
            </div>
            
            <div className="bg-white rounded-lg p-4 border border-gray-200 shadow-sm">
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Điểm kỷ luật</p>
              <p className={`text-2xl font-semibold mt-1 ${stats.discipline_points_total >= 0 ? 'text-[#32CD32]' : 'text-red-600'}`}>
                {stats.discipline_points_total > 0 ? '+' : ''}{stats.discipline_points_total}
              </p>
              <p className="text-xs text-gray-500 mt-1">Tháng này</p>
            </div>
            
            <div className="bg-white rounded-lg p-4 border border-gray-200 shadow-sm">
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Điểm thưởng</p>
              <p className="text-2xl font-semibold text-[#9333ea] mt-1">+{stats.bonus_points_total}</p>
              <p className="text-xs text-gray-500 mt-1">{stats.total_extra} ca làm thêm</p>
            </div>
            
            <div className="bg-white rounded-lg p-4 border border-gray-200 shadow-sm">
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Vắng mặt</p>
              <p className="text-2xl font-semibold text-red-600 mt-1">{stats.total_absent}</p>
              <p className="text-xs text-gray-500 mt-1">{stats.total_late} lần đi muộn</p>
            </div>
          </div>
        )}

        {/* Weekly Schedule */}
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
          <div className="p-4 lg:p-6 border-b border-gray-200">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <h2 className="text-base font-semibold text-gray-900">Lịch tuần</h2>
                <button 
                  onClick={handleSyncSchedule}
                  disabled={syncing}
                  className="text-xs px-3 py-1.5 bg-blue-50 text-blue-700 rounded-md hover:bg-blue-100 disabled:opacity-50 transition-colors font-medium"
                >
                  {syncing ? 'Đang cập nhật...' : 'Cập nhật từ LHU'}
                </button>
              </div>
              <div className="flex items-center gap-2">
                <button onClick={previousWeek} className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
                  <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                  </svg>
                </button>
                <span className="text-sm font-medium text-gray-700 min-w-[140px] text-center">
                  {formatDate(weekDates[0])} - {formatDate(weekDates[6])}
                </span>
                <button onClick={nextWeek} className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
                  <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
          
          {/* Calendar Grid */}
          <div className="overflow-x-auto">
            <table className="w-full min-w-[600px]">
              <thead>
                <tr className="bg-gray-50">
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide w-24">Ca</th>
                  {weekDates.map((date, idx) => (
                    <th key={idx} className={`px-2 py-3 text-center text-xs font-medium uppercase tracking-wide ${formatDate(date) === today ? 'bg-[#1E90FF]/10 text-[#1E90FF]' : 'text-gray-500'}`}>
                      <div>{['CN', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7'][date.getDay()]}</div>
                      <div className="font-semibold text-sm mt-0.5">{date.getDate()}/{date.getMonth() + 1}</div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {[Shift.MORNING, Shift.AFTERNOON, Shift.EVENING].map(shift => (
                  <tr key={shift}>
                    <td className="px-3 py-4 text-sm font-medium text-gray-700 bg-gray-50">
                      {SHIFT_LABELS[shift]}
                    </td>
                    {weekDates.map((date, idx) => {
                      const dateStr = formatDate(date);
                      const isScheduled = isShiftScheduled(dateStr, shift);
                      const isPast = dateStr < today;
                      const schedule = schedules.find(s => s.work_date === dateStr && s.shift === shift);
                      const classSchedule = getClassForSlot(dateStr, shift);
                      const isSunday = date.getDay() === 0;
                      const isToday = dateStr === today;
                      
                      return (
                        <td key={idx} className={`px-2 py-3 text-center ${isToday ? 'bg-[#1E90FF]/5' : ''} ${classSchedule ? 'bg-[#FFA500]/10' : isSunday ? 'bg-gray-100' : ''}`}>
                          {classSchedule ? (
                            <div className="text-xs">
                              <span className="inline-block px-2 py-1 bg-[#FFA500]/20 text-[#c2410c] rounded font-medium">Học</span>
                              <p className="text-gray-600 mt-1 truncate max-w-[80px] mx-auto" title={classSchedule.subject_name}>
                                {classSchedule.subject_name}
                              </p>
                            </div>
                          ) : isSunday ? (
                            <span className="text-xs text-gray-400">Nghỉ</span>
                          ) : isScheduled ? (
                            <div className="text-xs">
                              <span className="inline-block px-2 py-1 rounded font-medium bg-[#32CD32]/10 text-[#22c55e]">
                                Làm
                              </span>
                              {!isPast && (
                                <button
                                  onClick={() => handleCancelSchedule(schedule!.id)}
                                  className="block mx-auto mt-1 text-red-600 hover:text-red-700"
                                >
                                  Hủy
                                </button>
                              )}
                            </div>
                          ) : (
                            <span className="text-gray-300">—</span>
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

        {/* Student ID Modal */}
        {showStudentIdModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
              <div className="p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Cập nhật Mã số sinh viên</h3>
                <p className="text-sm text-gray-600 mb-4">
                  Để đồng bộ lịch học từ hệ thống LHU, bạn cần cung cấp MSSV của mình.
                </p>
                <input
                  type="text"
                  value={inputStudentId}
                  onChange={(e) => setInputStudentId(e.target.value)}
                  placeholder="Nhập MSSV"
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1E90FF] focus:border-[#1E90FF]"
                  autoFocus
                />
              </div>
              <div className="px-6 py-4 bg-gray-50 rounded-b-lg flex justify-end gap-3">
                <button
                  onClick={() => setShowStudentIdModal(false)}
                  disabled={syncing}
                  className="px-4 py-2 text-gray-700 hover:bg-gray-200 rounded-lg transition-colors"
                >
                  Hủy
                </button>
                <button
                  onClick={handleUpdateStudentId}
                  disabled={!inputStudentId.trim() || syncing}
                  className="px-4 py-2 bg-[#1E90FF] text-white rounded-lg hover:bg-[#1a7de0] disabled:opacity-50 transition-colors shadow-sm"
                >
                  {syncing ? 'Đang đồng bộ...' : 'Lưu & Đồng bộ'}
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
