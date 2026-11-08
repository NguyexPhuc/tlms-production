'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';
import {
  DailyTaskAssignResponse,
  ManagerDevelopmentSummary,
  PromotionReview,
} from '@/types/development';
import { MemberLevel } from '@/types';

const levelLabels: Record<MemberLevel, string> = {
  new: 'Thành viên mới',
  diligent: 'Thành viên chuyên cần',
  official: 'Thành viên chính thức',
};

export default function ManagerDevelopmentPage() {
  const router = useRouter();
  const { user, isLoading } = useAuth();
  const [summary, setSummary] = useState<ManagerDevelopmentSummary | null>(null);
  const [promotions, setPromotions] = useState<PromotionReview[]>([]);
  const [loading, setLoading] = useState(true);
  const [targetDate, setTargetDate] = useState(new Date().toISOString().slice(0, 10));
  const [targetLevel, setTargetLevel] = useState<MemberLevel>('new');
  const [tasksPerMember, setTasksPerMember] = useState(5);
  const [lastAssign, setLastAssign] = useState<DailyTaskAssignResponse | null>(null);
  const [busy, setBusy] = useState('');
  const [message, setMessage] = useState('');

  const canAccess = user?.roles?.includes('mentor') || user?.roles?.includes('admin');

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [summaryData, promotionData] = await Promise.all([
        apiClient.getManagerDevelopmentSummary(),
        apiClient.listPromotionReviews(),
      ]);
      setSummary(summaryData);
      setPromotions(promotionData);
    } catch (error) {
      console.error('Failed to load manager development data:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isLoading && !user) {
      router.push('/login');
      return;
    }
    if (user && !canAccess) {
      router.push('/dashboard');
      return;
    }
    if (user && canAccess) void loadData();
  }, [isLoading, user, canAccess, router, loadData]);

  const handleAssignDailyTasks = async () => {
    try {
      setBusy('assign');
      setMessage('');
      const result = await apiClient.assignDailyTasks({
        target_date: targetDate,
        target_member_level: targetLevel,
        tasks_per_member: tasksPerMember,
        include_ai_tasks: true,
      });
      setLastAssign(result);
      setMessage(`Đã tạo ${result.assignments_created} assignment mới.`);
      await loadData();
    } catch (error: any) {
      setMessage(error.response?.data?.detail || 'Không thể assign Daily Task');
    } finally {
      setBusy('');
    }
  };

  const handleReconcile = async () => {
    try {
      setBusy('reconcile');
      setMessage('');
      const result = await apiClient.reconcileDailyTasks(targetDate);
      setMessage(`Đã reconcile ${result.processed_count} thành viên cho ngày ${targetDate}.`);
      await loadData();
    } catch (error: any) {
      setMessage(error.response?.data?.detail || 'Không thể reconcile Daily Task');
    } finally {
      setBusy('');
    }
  };

  const handlePromotion = async (promotionId: string, approved: boolean) => {
    try {
      setBusy(promotionId);
      if (approved) {
        await apiClient.approvePromotion(promotionId, 'Đã duyệt từ manager dashboard.');
      } else {
        await apiClient.rejectPromotion(promotionId, 'Chưa đạt yêu cầu ở lần xét này.');
      }
      await loadData();
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Không thể xử lý promotion');
    } finally {
      setBusy('');
    }
  };

  if (isLoading || loading || !summary) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-gray-300 border-t-[#1E90FF] rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h1 className="text-xl font-semibold text-gray-900">Quản lý phát triển</h1>
              <p className="text-sm text-gray-500 mt-0.5">Daily Task, score và promotion</p>
            </div>
            <div className="flex items-center gap-2">
              <Link href="/mentor/tasks/create" className="px-3 py-2 bg-[#1E90FF] text-white rounded-lg hover:bg-[#1a7de0] text-sm font-medium">
                Tạo task
              </Link>
              <Link href="/dashboard" className="px-3 py-2 text-sm text-gray-600 hover:text-[#1E90FF] hover:bg-blue-50 rounded-lg transition-colors">
                Quay lại
              </Link>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
          <Metric label="Total Members" value={summary.total_members} />
          <Metric label="New Members" value={summary.new_members} />
          <Metric label="Diligent" value={summary.diligent_members} />
          <Metric label="Official" value={summary.official_members} />
          <Metric label="Active Today" value={summary.active_members} />
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
          <Metric label="Daily Completion" value={`${summary.daily_task_completion.toFixed(0)}%`} />
          <Metric label="Missed Tasks" value={summary.missed_tasks} />
          <Metric label="Pending Reviews" value={summary.pending_reviews} />
          <Metric label="Promotion Eligible" value={summary.promotion_eligible} />
          <Metric label="Average Rate" value={`${summary.average_completion_rate.toFixed(0)}%`} />
        </div>

        <section className="bg-white rounded-xl border border-gray-200 shadow-sm">
          <div className="px-5 py-4 border-b border-gray-100">
            <h2 className="font-semibold text-gray-900">Daily Task 24h</h2>
          </div>
          <div className="p-5 grid grid-cols-1 lg:grid-cols-5 gap-4 items-end">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Ngày</label>
              <input
                type="date"
                value={targetDate}
                onChange={(e) => setTargetDate(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1E90FF] focus:border-[#1E90FF] text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Cấp</label>
              <select
                value={targetLevel}
                onChange={(e) => setTargetLevel(e.target.value as MemberLevel)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1E90FF] focus:border-[#1E90FF] text-sm"
              >
                {Object.entries(levelLabels).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Task/người</label>
              <input
                type="number"
                min={1}
                max={20}
                value={tasksPerMember}
                onChange={(e) => setTasksPerMember(Number(e.target.value))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1E90FF] focus:border-[#1E90FF] text-sm"
              />
            </div>
            <button
              onClick={handleAssignDailyTasks}
              disabled={busy === 'assign'}
              className="px-4 py-2 bg-[#1E90FF] text-white rounded-lg hover:bg-[#1a7de0] text-sm font-medium disabled:opacity-50"
            >
              {busy === 'assign' ? 'Đang assign' : 'Assign'}
            </button>
            <button
              onClick={handleReconcile}
              disabled={busy === 'reconcile'}
              className="px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 text-sm font-medium disabled:opacity-50"
            >
              {busy === 'reconcile' ? 'Đang chạy' : 'Reconcile'}
            </button>
          </div>
          {(message || lastAssign) && (
            <div className="px-5 pb-5 text-sm text-gray-600">
              {message && <p>{message}</p>}
              {lastAssign && (
                <p className="mt-1">
                  Skipped existing: {lastAssign.skipped_existing}, skipped official AI: {lastAssign.skipped_official_ai}
                </p>
              )}
            </div>
          )}
        </section>

        <section className="bg-white rounded-xl border border-gray-200 shadow-sm">
          <div className="px-5 py-4 border-b border-gray-100">
            <h2 className="font-semibold text-gray-900">Promotion Reviews</h2>
          </div>
          <div className="divide-y divide-gray-100">
            {promotions.length === 0 ? (
              <div className="p-8 text-sm text-gray-500 text-center">Chưa có hồ sơ promotion.</div>
            ) : (
              promotions.map((promotion) => (
                <div key={promotion.id} className="p-5">
                  <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                    <div>
                      <p className="font-medium text-gray-900">{promotion.user_full_name || promotion.user_email || promotion.user_id}</p>
                      <p className="text-sm text-gray-500 mt-1">
                        {levelLabels[promotion.from_member_level]} sang {levelLabels[promotion.to_member_level]} • {promotion.status}
                      </p>
                      {promotion.metrics && (
                        <p className="text-xs text-gray-500 mt-2">
                          Score: {Number(promotion.metrics.member_score || 0).toFixed(0)} • Progress: {Number(promotion.metrics.promotion_progress || 0).toFixed(0)}%
                        </p>
                      )}
                    </div>
                    {['eligible', 'pending'].includes(promotion.status) && (
                      <div className="flex gap-2">
                        <button
                          onClick={() => handlePromotion(promotion.id, true)}
                          disabled={busy === promotion.id}
                          className="px-4 py-2 bg-[#32CD32] text-white rounded-lg hover:bg-[#22c55e] text-sm font-medium disabled:opacity-50"
                        >
                          Duyệt
                        </button>
                        <button
                          onClick={() => handlePromotion(promotion.id, false)}
                          disabled={busy === promotion.id}
                          className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 text-sm font-medium disabled:opacity-50"
                        >
                          Từ chối
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </section>
      </main>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
      <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</p>
      <p className="text-2xl font-semibold text-gray-900 mt-1">{value}</p>
    </div>
  );
}
