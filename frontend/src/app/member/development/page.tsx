'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft,
  Bell,
  CalendarDays,
  CheckCircle2,
  ChevronRight,
  CircleGauge,
  ClipboardList,
  Medal,
  Sparkles,
} from 'lucide-react';
import { apiClient } from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';
import { MemberDevelopmentDashboard, Notification } from '@/types/development';
import { UserTask } from '@/types/task';

const memberLevelLabels: Record<string, string> = {
  new: 'Thành viên mới',
  diligent: 'Thành viên chuyên cần',
  official: 'Thành viên chính thức',
};

const statusLabels: Record<string, string> = {
  available: 'Chưa bắt đầu',
  in_progress: 'Đang làm',
  submitted: 'Chờ duyệt',
  ai_reviewed: 'AI đã chấm',
  late: 'Nộp trễ',
  missed: 'Bỏ lỡ',
  completed: 'Hoàn thành',
  approved: 'Đã duyệt',
  rejected: 'Cần làm lại',
  locked: 'Đang khóa',
};

const statusColors: Record<string, string> = {
  available: 'bg-slate-100 text-slate-700',
  in_progress: 'bg-blue-100 text-blue-700',
  submitted: 'bg-amber-100 text-amber-700',
  ai_reviewed: 'bg-cyan-100 text-cyan-800',
  late: 'bg-orange-100 text-orange-700',
  missed: 'bg-red-100 text-red-700',
  completed: 'bg-emerald-100 text-emerald-700',
  approved: 'bg-emerald-100 text-emerald-700',
  rejected: 'bg-red-100 text-red-700',
  locked: 'bg-gray-100 text-gray-600',
};

export default function MemberDevelopmentPage() {
  const router = useRouter();
  const { user, isLoading } = useAuth();
  const [dashboard, setDashboard] = useState<MemberDevelopmentDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyTask, setBusyTask] = useState<string | null>(null);
  const [message, setMessage] = useState('');

  const loadDashboard = useCallback(async () => {
    try {
      setLoading(true);
      setDashboard(await apiClient.getDevelopmentDashboard());
      setMessage('');
    } catch (error) {
      console.error('Failed to load development dashboard:', error);
      setMessage('Không thể tải tiến độ. Vui lòng thử lại.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isLoading && !user) {
      router.push('/login');
      return;
    }
    if (user) void loadDashboard();
  }, [isLoading, user, router, loadDashboard]);

  const handleStart = async (task: UserTask) => {
    try {
      setBusyTask(task.id);
      setMessage('');
      await apiClient.startAssignedTask(task.id);
      router.push(`/candidate/tasks/${task.id}`);
    } catch (error: any) {
      setMessage(error.response?.data?.detail || 'Không thể bắt đầu nhiệm vụ.');
    } finally {
      setBusyTask(null);
    }
  };

  const handleMarkAllRead = async () => {
    await apiClient.markAllNotificationsRead();
    await loadDashboard();
  };

  const visibleTasks = useMemo(() => {
    if (!dashboard) return [];
    const unique = new Map<string, UserTask>();
    [...dashboard.today_tasks, ...(dashboard.assigned_tasks || [])].forEach((task) => unique.set(task.id, task));
    return Array.from(unique.values());
  }, [dashboard]);

  if (isLoading || loading || !dashboard) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="h-7 w-7 animate-spin rounded-full border-2 border-slate-200 border-t-blue-600" />
      </div>
    );
  }

  const dailyProgress = Math.min(Math.max(dashboard.daily_completion_rate, 0), 100);
  const promotionProgress = Math.min(Math.max(dashboard.promotion_progress, 0), 100);
  const roadmap = dashboard.roadmap;
  const roadmapProgress = Math.min(Math.max(roadmap?.progress_percentage ?? 0, 0), 100);
  const currentWeek = roadmap
    ? roadmap.weeks.find((week) => week.is_current) ?? roadmap.weeks[roadmap.current_week - 1]
    : undefined;

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-4">
          <div>
            <p className="text-xs font-semibold uppercase text-blue-600">Không gian học tập</p>
            <h1 className="text-xl font-bold">Tiến độ của bạn</h1>
          </div>
          <Link href="/dashboard" className="inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100">
            <ArrowLeft size={17} /> Quay lại
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-6 px-4 py-6">
        {message && <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{message}</div>}

        <section className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <Metric icon={<Sparkles size={18} />} label="Cấp hiện tại" value={memberLevelLabels[dashboard.member_level] || dashboard.member_level} tone="blue" />
          <Metric icon={<CircleGauge size={18} />} label="Level & XP" value={`Lv.${dashboard.level} · ${dashboard.current_xp} XP`} tone="cyan" />
          <Metric icon={<CheckCircle2 size={18} />} label="Hôm nay" value={`${dashboard.completed_tasks}/${dashboard.today_tasks.length} xong`} tone="green" />
          <Metric icon={<ClipboardList size={18} />} label="Cần làm" value={`${visibleTasks.length} nhiệm vụ`} tone="orange" />
        </section>

        {roadmap && (
          <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
              <div>
                <p className="text-sm font-semibold text-blue-600">Tuần {roadmap.current_week}/{roadmap.total_weeks}</p>
                <h2 className="mt-1 text-lg font-bold">{currentWeek?.title || roadmap.current_stage}</h2>
                <p className="mt-1 text-sm text-slate-500">{currentWeek?.stage || roadmap.current_stage} · Ngày {roadmap.current_day}/{roadmap.total_days}</p>
              </div>
              <strong className="text-2xl text-blue-600">{roadmapProgress.toFixed(0)}%</strong>
            </div>
            <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-100">
              <div className="h-full rounded-full bg-blue-600 transition-all" style={{ width: `${roadmapProgress}%` }} />
            </div>
            <div className="mt-4 grid grid-cols-8 gap-2" aria-label="Tiến độ 8 tuần">
              {roadmap.weeks.map((week) => (
                <div key={week.id} className="text-center">
                  <div className={`h-2 rounded-full ${week.is_completed ? 'bg-emerald-500' : week.is_current ? 'bg-blue-600' : 'bg-slate-200'}`} />
                  <span className="mt-1 block text-xs text-slate-500">T{week.week_number}</span>
                </div>
              ))}
            </div>
          </section>
        )}

        <section className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
          <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
            <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
              <div>
                <h2 className="font-bold">Việc cần làm</h2>
                <p className="mt-0.5 text-sm text-slate-500">Daily Task và nhiệm vụ quản lý vừa giao</p>
              </div>
              <span className="rounded-md bg-blue-50 px-2.5 py-1 text-sm font-semibold text-blue-700">{visibleTasks.length}</span>
            </div>
            {visibleTasks.length === 0 ? (
              <div className="px-5 py-12 text-center">
                <CheckCircle2 className="mx-auto text-emerald-500" size={34} />
                <p className="mt-3 font-medium">Bạn đã xử lý hết nhiệm vụ</p>
                <p className="mt-1 text-sm text-slate-500">Nhiệm vụ mới sẽ xuất hiện tại đây.</p>
              </div>
            ) : (
              <div className="divide-y divide-slate-100">
                {visibleTasks.map((task) => (
                  <article key={task.id} className="flex flex-col gap-4 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
                    <div className="min-w-0">
                      <div className="mb-2 flex flex-wrap items-center gap-2">
                        <span className={`rounded px-2 py-0.5 text-xs font-medium ${statusColors[task.status] || statusColors.available}`}>
                          {statusLabels[task.status] || task.status}
                        </span>
                        <span className="text-xs font-semibold text-emerald-600">+{task.task.xp_reward} XP</span>
                      </div>
                      <h3 className="truncate font-semibold">{task.task.title}</h3>
                      <p className="mt-1 line-clamp-1 text-sm text-slate-500">{task.task.description}</p>
                    </div>
                    {task.status === 'available' ? (
                      <button onClick={() => handleStart(task)} disabled={busyTask === task.id} className="shrink-0 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50">
                        {busyTask === task.id ? 'Đang mở...' : 'Bắt đầu'}
                      </button>
                    ) : (
                      <Link href={`/candidate/tasks/${task.id}`} className="inline-flex shrink-0 items-center justify-center gap-1 rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold hover:border-blue-300 hover:text-blue-700">
                        Xem chi tiết <ChevronRight size={16} />
                      </Link>
                    )}
                  </article>
                ))}
              </div>
            )}
          </div>

          <aside className="space-y-4">
            <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex items-center justify-between">
                <h2 className="font-bold">Tiến độ thăng cấp</h2>
                <span className="font-bold text-emerald-600">{promotionProgress.toFixed(0)}%</span>
              </div>
              <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100">
                <div className="h-full rounded-full bg-emerald-500" style={{ width: `${promotionProgress}%` }} />
              </div>
            </section>

            <nav className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm" aria-label="Lối tắt">
              <QuickLink href="/candidate" icon={<ClipboardList size={19} />} label="Nhiệm vụ & Quest" />
              <QuickLink href="/schedule" icon={<CalendarDays size={19} />} label="Lịch học và làm việc" />
              <QuickLink href="/achievements" icon={<Medal size={19} />} label="Thành tích & huy hiệu" />
            </nav>

            <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
              <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
                <div className="flex items-center gap-2 font-bold"><Bell size={18} /> Thông báo</div>
                {dashboard.unread_notifications > 0 && <button onClick={handleMarkAllRead} className="text-xs font-medium text-blue-600 hover:underline">Đã đọc</button>}
              </div>
              <div className="divide-y divide-slate-100">
                {dashboard.notifications.slice(0, 3).map((notification: Notification) => (
                  <div key={notification.id} className="px-4 py-3">
                    <p className="text-sm font-medium">{notification.title}</p>
                    <p className="mt-0.5 line-clamp-2 text-xs text-slate-500">{notification.message}</p>
                  </div>
                ))}
                {dashboard.notifications.length === 0 && <p className="px-4 py-5 text-sm text-slate-500">Chưa có thông báo mới.</p>}
              </div>
            </section>
          </aside>
        </section>

        {dashboard.today_tasks.length > 0 && (
          <section className="rounded-lg border border-slate-200 bg-white px-5 py-4 shadow-sm">
            <div className="flex items-center justify-between text-sm">
              <span className="font-semibold">Daily Task hôm nay</span>
              <span className="font-bold text-blue-600">{dailyProgress.toFixed(0)}%</span>
            </div>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100">
              <div className="h-full rounded-full bg-blue-600" style={{ width: `${dailyProgress}%` }} />
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

function Metric({ icon, label, value, tone }: { icon: React.ReactNode; label: string; value: string; tone: 'blue' | 'cyan' | 'green' | 'orange' }) {
  const tones = {
    blue: 'bg-blue-50 text-blue-700',
    cyan: 'bg-cyan-50 text-cyan-700',
    green: 'bg-emerald-50 text-emerald-700',
    orange: 'bg-orange-50 text-orange-700',
  };
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className={`mb-3 flex h-8 w-8 items-center justify-center rounded-md ${tones[tone]}`}>{icon}</div>
      <p className="text-xs font-semibold uppercase text-slate-500">{label}</p>
      <p className="mt-1 truncate font-bold text-slate-900">{value}</p>
    </div>
  );
}

function QuickLink({ href, icon, label }: { href: string; icon: React.ReactNode; label: string }) {
  return (
    <Link href={href} className="flex items-center gap-3 border-b border-slate-100 px-4 py-3 text-sm font-medium last:border-0 hover:bg-blue-50 hover:text-blue-700">
      <span className="text-blue-600">{icon}</span>
      <span className="flex-1">{label}</span>
      <ChevronRight size={16} className="text-slate-400" />
    </Link>
  );
}
