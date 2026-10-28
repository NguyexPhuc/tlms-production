'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { apiClient } from '@/lib/api';
import { CupDefinition, WeeklyCupDashboard, WeeklyCupLeaderboardEntry } from '@/types/cup';

const statusLabels: Record<string, string> = {
  scheduled: 'Sắp mở',
  open: 'Đang thi',
  closed: 'Đã đóng',
  awarded: 'Đã trao',
};

const formatDateTime = (value?: string | null) => {
  if (!value) return '--';
  return new Date(value).toLocaleString('vi-VN', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

const formatDuration = (seconds?: number | null) => {
  if (seconds === null || seconds === undefined) return '--';
  const minutes = Math.floor(seconds / 60);
  const remain = seconds % 60;
  return `${minutes}:${remain.toString().padStart(2, '0')}`;
};

const formatCountdown = (target?: string | null, now = new Date()) => {
  if (!target) return '--:--:--';
  const diff = new Date(target).getTime() - now.getTime();
  if (diff <= 0) return '00:00:00';

  const totalSeconds = Math.floor(diff / 1000);
  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const time = [hours, minutes, seconds].map((part) => part.toString().padStart(2, '0')).join(':');
  return days > 0 ? `${days} ngày ${time}` : time;
};

export default function WeeklyCupsPage() {
  const router = useRouter();
  const { user, isLoading, isAuthenticated, logout } = useAuth();
  const [dashboard, setDashboard] = useState<WeeklyCupDashboard | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isLoading, isAuthenticated, router]);

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  const loadDashboard = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    setError('');
    try {
      const data = await apiClient.getWeeklyCupDashboard();
      setDashboard(data);
      setAnswers(data.my_attempt?.answers || {});
    } catch (err) {
      console.error('Failed to load weekly cups:', err);
      setError('Không thể tải sự kiện tranh cup.');
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  const sortedCups = useMemo(() => {
    return [...(dashboard?.cups ?? [])].sort((a, b) => a.sort_order - b.sort_order);
  }, [dashboard]);

  const questions = dashboard?.event?.questions ?? [];
  const answeredCount = questions.filter((question) => answers[question.id]).length;
  const attemptStartedSeconds = dashboard?.my_attempt?.started_at
    ? Math.max(0, Math.floor((now.getTime() - new Date(dashboard.my_attempt.started_at).getTime()) / 1000))
    : null;
  const countdownTarget = dashboard?.event?.status === 'open' ? dashboard.event.closes_at : dashboard?.next_event_at;

  const handleLogout = async () => {
    await logout();
    router.push('/login');
  };

  const getErrorDetail = (err: unknown, fallback: string) => {
    return err && typeof err === 'object' && 'response' in err
      ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || fallback
      : fallback;
  };

  const handleStart = async () => {
    setStarting(true);
    setMessage('');
    setError('');
    try {
      const result = await apiClient.startWeeklyCupQuiz();
      setDashboard(result.dashboard);
      setAnswers(result.dashboard.my_attempt?.answers || {});
      setMessage(result.message);
    } catch (err: unknown) {
      setError(getErrorDetail(err, 'Không thể bắt đầu bài kiểm tra lúc này.'));
    } finally {
      setStarting(false);
    }
  };

  const handleSubmit = async () => {
    if (answeredCount < questions.length) {
      setError(`Bạn còn ${questions.length - answeredCount} câu chưa chọn đáp án.`);
      return;
    }

    setSubmitting(true);
    setMessage('');
    setError('');
    try {
      const result = await apiClient.submitWeeklyCupQuiz(answers);
      setDashboard(result.dashboard);
      setAnswers(result.dashboard.my_attempt?.answers || {});
      setMessage(`${result.message} Điểm: ${result.score}/${result.total_questions}, thời gian: ${formatDuration(result.duration_seconds)}.`);
    } catch (err: unknown) {
      setError(getErrorDetail(err, 'Không thể nộp bài kiểm tra lúc này.'));
    } finally {
      setSubmitting(false);
    }
  };

  const renderCup = (cup: CupDefinition) => {
    const isCurrent = dashboard?.event?.cup.id === cup.id && dashboard?.event?.status === 'open';
    const color = cup.is_awarded ? cup.color : isCurrent ? cup.color : '#94a3b8';

    return (
      <div
        key={cup.id}
        className={`rounded-xl border bg-white p-4 shadow-sm transition-colors ${
          isCurrent ? 'border-[#1E90FF]' : cup.is_awarded ? 'border-gray-200' : 'border-gray-100'
        }`}
      >
        <div className="flex items-start gap-4">
          <div
            className="flex h-16 w-16 shrink-0 items-center justify-center rounded-full border-2 text-sm font-semibold shadow-sm"
            style={{
              color,
              borderColor: color,
              background: cup.is_awarded || isCurrent ? `${cup.color}1F` : '#f8fafc',
            }}
          >
            {cup.icon}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="font-semibold text-gray-900">{cup.title}</h3>
              {isCurrent && <span className="rounded-full bg-[#1E90FF]/10 px-2 py-0.5 text-xs font-medium text-[#1E90FF]">Tuần này</span>}
              {cup.is_awarded && <span className="rounded-full bg-[#32CD32]/10 px-2 py-0.5 text-xs font-medium text-[#16A34A]">Đã trao</span>}
            </div>
            <p className="mt-1 text-sm text-gray-600">{cup.description}</p>
            {cup.awarded_to && (
              <p className="mt-2 text-xs text-gray-500">
                Chủ cup: <span className="font-medium text-gray-800">{cup.awarded_to.full_name || cup.awarded_to.email}</span>
              </p>
            )}
          </div>
        </div>
      </div>
    );
  };

  const renderRank = (entry: WeeklyCupLeaderboardEntry) => {
    const isMe = entry.user_id === user?.id;

    return (
      <tr key={entry.user_id} className={isMe ? 'bg-[#1E90FF]/5' : ''}>
        <td className="px-4 py-3">
          <span
            className={`inline-flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold ${
              entry.rank === 1
                ? 'bg-[#FFA500]/20 text-[#c2410c]'
                : entry.rank === 2
                  ? 'bg-gray-200 text-gray-700'
                  : entry.rank === 3
                    ? 'bg-orange-100 text-orange-700'
                    : 'bg-gray-100 text-gray-600'
            }`}
          >
            {entry.rank}
          </span>
        </td>
        <td className="px-4 py-3">
          <p className="text-sm font-medium text-gray-900">
            {entry.full_name || entry.email}
            {isMe && <span className="ml-2 text-xs text-[#1E90FF]">(Bạn)</span>}
          </p>
          <p className="text-xs text-gray-500">{entry.email}</p>
        </td>
        <td className="px-4 py-3 text-center text-sm font-semibold text-[#9333ea]">
          {entry.score ?? '--'}/{entry.total_questions}
        </td>
        <td className="px-4 py-3 text-center text-sm text-gray-700">{formatDuration(entry.duration_seconds)}</td>
        <td className="px-4 py-3 text-right text-sm font-semibold text-gray-900">{entry.current_xp}</td>
        <td className="px-4 py-3">
          <div className="flex items-center gap-2">
            <span className="w-10 text-sm text-gray-900">{entry.discipline_score.toFixed(0)}%</span>
            <div className="h-1.5 flex-1 rounded-full bg-gray-100">
              <div className="h-1.5 rounded-full bg-[#32CD32]" style={{ width: `${Math.min(entry.discipline_score, 100)}%` }} />
            </div>
          </div>
        </td>
      </tr>
    );
  };

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-gray-300 border-t-[#1E90FF]" />
      </div>
    );
  }

  if (!user) return null;

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="sticky top-0 z-10 border-b border-gray-200 bg-white shadow-sm">
        <div className="mx-auto max-w-6xl px-4">
          <div className="flex h-14 items-center justify-between">
            <button onClick={() => router.push('/dashboard')} className="flex items-center gap-2">
              <Image src="/logo/logo.jpg" alt="TLMS Logo" width={32} height={32} className="h-8 w-8 rounded-lg object-cover shadow-sm" />
              <span className="hidden font-semibold text-gray-900 sm:block">TLMS</span>
            </button>
            <div className="flex items-center gap-3">
              <p className="hidden max-w-[160px] truncate text-sm font-medium text-gray-900 sm:block">{user.full_name || user.email}</p>
              <button onClick={handleLogout} className="rounded-lg px-3 py-1.5 text-sm text-gray-600 transition-colors hover:bg-red-50 hover:text-red-600">
                Đăng xuất
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-6 px-4 py-8">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Weekly Cup</p>
            <h1 className="mt-1 text-3xl font-semibold text-gray-900">Tranh Cup Thứ 6</h1>
            <p className="mt-2 text-sm text-gray-500">
              Mỗi thứ 6 mở bài test trắc nghiệm 20 câu về CNTT. Điểm cao nhất nhận cup, hòa điểm thì xét thời gian nộp nhanh hơn.
            </p>
          </div>
          <button
            onClick={() => router.push('/dashboard')}
            className="w-fit rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-600 shadow-sm hover:border-[#1E90FF] hover:text-[#1E90FF]"
          >
            Quay lại
          </button>
        </div>

        {loading ? (
          <div className="rounded-xl border border-gray-200 bg-white p-8 text-center text-sm text-gray-500 shadow-sm">Đang tải sự kiện tranh cup...</div>
        ) : dashboard && (
          <>
            <section className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
              <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Sự kiện hiện tại</p>
                  <div className="mt-2 flex flex-wrap items-center gap-3">
                    <h2 className="text-2xl font-semibold text-gray-900">{dashboard.event?.cup.title || 'Đã hết cup'}</h2>
                    {dashboard.event && (
                      <span className="rounded-full bg-[#1E90FF]/10 px-3 py-1 text-xs font-medium text-[#1E90FF]">
                        {statusLabels[dashboard.event.status] || dashboard.event.status}
                      </span>
                    )}
                  </div>
                  <p className="mt-2 text-sm text-gray-500">
                    Mở: {formatDateTime(dashboard.event?.opens_at)} · Đóng: {formatDateTime(dashboard.event?.closes_at)}
                  </p>
                  <p className="mt-1 text-sm text-gray-500">Điều kiện: chuyên cần/kỷ luật từ {dashboard.min_discipline_score.toFixed(0)}%.</p>
                </div>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                  <div className="rounded-lg bg-gray-50 p-3">
                    <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Còn lại</p>
                    <p className="mt-1 text-2xl font-semibold text-gray-900">{dashboard.remaining_cups}/8</p>
                  </div>
                  <div className="rounded-lg bg-gray-50 p-3">
                    <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Hạng của bạn</p>
                    <p className="mt-1 text-2xl font-semibold text-[#9333ea]">{dashboard.my_eligibility.my_rank ? `#${dashboard.my_eligibility.my_rank}` : '--'}</p>
                  </div>
                  <div className="rounded-lg bg-gray-50 p-3">
                    <p className="text-xs font-medium uppercase tracking-wide text-gray-500">{dashboard.event?.status === 'open' ? 'Đóng sau' : 'Mở sau'}</p>
                    <p className="mt-1 text-xl font-semibold text-[#1E90FF]">{formatCountdown(countdownTarget, now)}</p>
                  </div>
                </div>
              </div>

              <div className="mt-5 flex flex-col gap-3 border-t border-gray-100 pt-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-900">Chuyên cần của bạn: {dashboard.my_eligibility.discipline_score.toFixed(0)}%</p>
                  <p className="mt-1 text-sm text-gray-500">
                    {dashboard.my_eligibility.reason || 'Bạn đủ điều kiện chuyên cần để tham gia bài test cup.'}
                  </p>
                  {dashboard.my_attempt?.submitted_at && (
                    <p className="mt-1 text-sm font-medium text-gray-900">
                      Bài đã nộp: {dashboard.my_attempt.score}/{dashboard.my_attempt.total_questions} · {formatDuration(dashboard.my_attempt.duration_seconds)}
                    </p>
                  )}
                </div>
                {!dashboard.my_attempt?.submitted_at && (
                  <button
                    onClick={handleStart}
                    disabled={!dashboard.my_eligibility.can_start || starting}
                    className="rounded-lg bg-[#1E90FF] px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-[#1876d1] disabled:cursor-not-allowed disabled:bg-gray-200 disabled:text-gray-500"
                  >
                    {starting ? 'Đang mở bài...' : dashboard.my_attempt ? 'Tiếp tục làm bài' : 'Bắt đầu bài test'}
                  </button>
                )}
              </div>
            </section>

            {message && <div className="rounded-xl border border-green-100 bg-green-50 p-4 text-sm text-green-700">{message}</div>}
            {error && <div className="rounded-xl border border-red-100 bg-red-50 p-4 text-sm text-red-600">{error}</div>}

            {dashboard.my_eligibility.can_submit && questions.length > 0 && (
              <section className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
                <div className="flex flex-col gap-2 border-b border-gray-100 pb-4 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900">Bài kiểm tra CNTT</h2>
                    <p className="mt-1 text-sm text-gray-500">Đã chọn {answeredCount}/{questions.length} câu.</p>
                  </div>
                  <div className="text-sm font-semibold text-[#9333ea]">Thời gian: {formatDuration(attemptStartedSeconds)}</div>
                </div>
                <div className="mt-5 space-y-5">
                  {questions.map((question, index) => (
                    <div key={question.id} className="rounded-lg border border-gray-100 bg-gray-50 p-4">
                      <p className="font-medium text-gray-900">
                        {index + 1}. {question.question}
                      </p>
                      <div className="mt-3 grid grid-cols-1 gap-2 md:grid-cols-2">
                        {question.options.map((option) => (
                          <label
                            key={option.id}
                            className={`flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-sm transition-colors ${
                              answers[question.id] === option.id ? 'border-[#1E90FF] bg-blue-50 text-[#1E90FF]' : 'border-gray-200 bg-white text-gray-700'
                            }`}
                          >
                            <input
                              type="radio"
                              name={question.id}
                              value={option.id}
                              checked={answers[question.id] === option.id}
                              onChange={() => setAnswers((current) => ({ ...current, [question.id]: option.id }))}
                              className="h-4 w-4"
                            />
                            <span>{option.id}. {option.text}</span>
                          </label>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
                <div className="mt-5 flex justify-end">
                  <button
                    onClick={handleSubmit}
                    disabled={submitting}
                    className="rounded-lg bg-[#32CD32] px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-[#28a428] disabled:cursor-not-allowed disabled:bg-gray-200 disabled:text-gray-500"
                  >
                    {submitting ? 'Đang nộp...' : 'Nộp bài kiểm tra'}
                  </button>
                </div>
              </section>
            )}

            <section className="space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-gray-900">8 Cup duy nhất</h2>
                <span className="text-xs text-gray-500">{sortedCups.filter((cup) => cup.is_awarded).length} đã trao</span>
              </div>
              <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">{sortedCups.map(renderCup)}</div>
            </section>

            <section className="rounded-xl border border-gray-200 bg-white shadow-sm">
              <div className="flex items-center justify-between border-b border-gray-100 px-5 py-4">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">Bảng kết quả cup</h2>
                  <p className="mt-1 text-sm text-gray-500">Xếp theo điểm cao nhất, nếu bằng điểm thì thời gian làm bài nhanh hơn đứng trên.</p>
                </div>
              </div>
              {dashboard.leaderboard.length === 0 ? (
                <div className="p-8 text-center text-sm text-gray-500">Chưa có bài nộp nào trong sự kiện này.</div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[760px]">
                    <thead>
                      <tr className="bg-gray-50 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                        <th className="w-20 px-4 py-3">Hạng</th>
                        <th className="px-4 py-3">Thành viên</th>
                        <th className="w-24 px-4 py-3 text-center">Điểm</th>
                        <th className="w-28 px-4 py-3 text-center">Thời gian</th>
                        <th className="w-24 px-4 py-3 text-right">XP</th>
                        <th className="w-48 px-4 py-3">Chuyên cần</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">{dashboard.leaderboard.map(renderRank)}</tbody>
                  </table>
                </div>
              )}
            </section>
          </>
        )}

        {!loading && !dashboard && error && <div className="rounded-xl border border-red-100 bg-red-50 p-4 text-sm text-red-600">{error}</div>}
      </main>
    </div>
  );
}
