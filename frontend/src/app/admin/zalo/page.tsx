'use client';

import { useCallback, useEffect, useState } from 'react';
import { BellRing, RefreshCw, Save, Send, Settings2 } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { apiClient } from '@/lib/api';
import { ZaloAdminDashboard, ZaloIntegrationConfig } from '@/types/zalo';

function getError(error: unknown): string {
  if (error && typeof error === 'object' && 'response' in error) {
    return (error as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Yêu cầu thất bại.';
  }
  return 'Yêu cầu thất bại.';
}

export default function ZaloAdminPage() {
  const router = useRouter();
  const { user, isLoading } = useAuth();
  const [dashboard, setDashboard] = useState<ZaloAdminDashboard | null>(null);
  const [form, setForm] = useState<ZaloIntegrationConfig | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const isAdmin = user?.roles?.includes('admin') ?? false;
  const load = useCallback(async () => {
    try {
      const data = await apiClient.getZaloAdminDashboard();
      setDashboard(data);
      setForm(data.config);
      setError('');
    } catch (err) {
      setError(getError(err));
    }
  }, []);

  useEffect(() => {
    if (!isLoading && !user) router.replace('/login');
    else if (!isLoading && user && !isAdmin) router.replace('/dashboard');
    else if (isAdmin) load();
  }, [isLoading, user, isAdmin, router, load]);

  const updateNumber = (key: keyof ZaloIntegrationConfig, value: string) => {
    if (!form) return;
    setForm({ ...form, [key]: Number(value) });
  };

  const save = async () => {
    if (!form) return;
    setBusy(true);
    setError('');
    try {
      await apiClient.updateZaloConfig({
        enabled: form.enabled,
        provider: form.provider,
        send_hour: form.send_hour,
        send_minute: form.send_minute,
        reminder_hour: form.reminder_hour,
        reminder_minute: form.reminder_minute,
        quiz_size: form.quiz_size,
        session_ttl_minutes: form.session_ttl_minutes,
        send_window_days: form.send_window_days,
        max_retries: form.max_retries,
      });
      setMessage('Đã lưu cấu hình Zalo.');
      await load();
    } catch (err) {
      setError(getError(err));
    } finally {
      setBusy(false);
    }
  };

  const dispatch = async () => {
    setBusy(true);
    setError('');
    try {
      const result = await apiClient.dispatchZaloQuizzes();
      setMessage(`Đã gửi ${result.messages_sent}, tạo ${result.sessions_created} phiên, lỗi ${result.failed}.`);
      await load();
    } catch (err) {
      setError(getError(err));
    } finally {
      setBusy(false);
    }
  };

  if (isLoading || !isAdmin || !dashboard || !form) {
    return <div className="min-h-screen bg-gray-50 flex items-center justify-center text-sm text-gray-500">Đang tải...</div>;
  }

  const stats = [
    ['Đã liên kết', dashboard.linked_users],
    ['Đồng ý nhận tin', dashboard.opted_in_users],
    ['Đang làm', dashboard.active_sessions],
    ['Hoàn thành hôm nay', dashboard.completed_today],
    ['Gửi lỗi', dashboard.failed_deliveries],
  ];

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4">
          <div className="flex items-center gap-3"><Settings2 className="h-5 w-5 text-blue-600" /><h1 className="font-semibold">Quản trị Zalo Daily Task</h1></div>
          <button onClick={() => router.push('/dashboard')} className="text-sm text-gray-600 hover:text-blue-600">Quay lại</button>
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-6 px-4 py-7">
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
          {stats.map(([label, value]) => (
            <div key={String(label)} className="border border-gray-200 bg-white p-4 shadow-sm">
              <p className="text-xs text-gray-500">{label}</p><p className="mt-2 text-2xl font-semibold">{value}</p>
            </div>
          ))}
        </div>

        <section className="border border-gray-200 bg-white p-5 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div><h2 className="font-semibold">Cấu hình</h2><p className="mt-1 text-xs text-gray-500">Webhook: {form.webhook_url}</p></div>
            <div className="flex gap-2">
              <button onClick={load} className="border border-gray-300 p-2 hover:bg-gray-50" title="Làm mới"><RefreshCw className="h-4 w-4" /></button>
              <button onClick={dispatch} disabled={busy || !form.effective_enabled} className="inline-flex items-center gap-2 bg-green-600 px-3 py-2 text-sm font-medium text-white disabled:opacity-50"><Send className="h-4 w-4" /> Gửi ngay</button>
              <button onClick={save} disabled={busy} className="inline-flex items-center gap-2 bg-blue-600 px-3 py-2 text-sm font-medium text-white disabled:opacity-50"><Save className="h-4 w-4" /> Lưu</button>
            </div>
          </div>

          {!form.environment_enabled && <div className="mt-4 border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">Feature flag môi trường đang tắt.</div>}
          {form.provider === 'zalo_oa' && !form.oa_configured && <div className="mt-4 border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">Thiếu credentials Zalo OA trong biến môi trường.</div>}

          <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <label className="text-sm"><span className="block text-gray-600">Trạng thái</span><input type="checkbox" checked={form.enabled} onChange={(e) => setForm({ ...form, enabled: e.target.checked })} className="mt-3 h-5 w-5 accent-blue-600" /></label>
            <label className="text-sm"><span className="block text-gray-600">Provider</span><select value={form.provider} onChange={(e) => setForm({ ...form, provider: e.target.value as 'mock' | 'zalo_oa' })} className="mt-1 w-full border border-gray-300 px-3 py-2"><option value="mock">Mock</option><option value="zalo_oa">Zalo OA</option></select></label>
            <label className="text-sm"><span className="block text-gray-600">Giờ gửi</span><div className="mt-1 grid grid-cols-2 gap-2"><input type="number" min="0" max="23" value={form.send_hour} onChange={(e) => updateNumber('send_hour', e.target.value)} className="border border-gray-300 px-3 py-2"/><input type="number" min="0" max="59" value={form.send_minute} onChange={(e) => updateNumber('send_minute', e.target.value)} className="border border-gray-300 px-3 py-2"/></div></label>
            <label className="text-sm"><span className="block text-gray-600">Giờ nhắc</span><div className="mt-1 grid grid-cols-2 gap-2"><input type="number" min="0" max="23" value={form.reminder_hour} onChange={(e) => updateNumber('reminder_hour', e.target.value)} className="border border-gray-300 px-3 py-2"/><input type="number" min="0" max="59" value={form.reminder_minute} onChange={(e) => updateNumber('reminder_minute', e.target.value)} className="border border-gray-300 px-3 py-2"/></div></label>
            <label className="text-sm"><span className="block text-gray-600">Số câu</span><input type="number" min="1" max="20" value={form.quiz_size} onChange={(e) => updateNumber('quiz_size', e.target.value)} className="mt-1 w-full border border-gray-300 px-3 py-2"/></label>
            <label className="text-sm"><span className="block text-gray-600">Hết hạn (phút)</span><input type="number" min="15" max="1440" value={form.session_ttl_minutes} onChange={(e) => updateNumber('session_ttl_minutes', e.target.value)} className="mt-1 w-full border border-gray-300 px-3 py-2"/></label>
            <label className="text-sm"><span className="block text-gray-600">Cửa sổ tương tác (ngày)</span><input type="number" min="1" max="7" value={form.send_window_days} onChange={(e) => updateNumber('send_window_days', e.target.value)} className="mt-1 w-full border border-gray-300 px-3 py-2"/></label>
            <label className="text-sm"><span className="block text-gray-600">Retry tối đa</span><input type="number" min="0" max="10" value={form.max_retries} onChange={(e) => updateNumber('max_retries', e.target.value)} className="mt-1 w-full border border-gray-300 px-3 py-2"/></label>
          </div>
        </section>

        {message && <div className="border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">{message}</div>}
        {error && <div className="border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

        <section className="border border-gray-200 bg-white shadow-sm">
          <div className="flex items-center gap-2 border-b border-gray-100 px-5 py-4"><BellRing className="h-4 w-4 text-blue-600"/><h2 className="font-semibold">Phiên gần đây</h2></div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm"><thead className="bg-gray-50 text-left text-xs text-gray-500"><tr><th className="px-4 py-3">User</th><th className="px-4 py-3">Ngày</th><th className="px-4 py-3">Tiến độ</th><th className="px-4 py-3">Điểm</th><th className="px-4 py-3">XP</th><th className="px-4 py-3">Trạng thái</th></tr></thead><tbody className="divide-y divide-gray-100">{dashboard.sessions.map((session) => <tr key={session.id}><td className="px-4 py-3">{session.user_email || session.user_id}</td><td className="px-4 py-3">{session.session_date}</td><td className="px-4 py-3">{session.answered_count}/{session.total_questions}</td><td className="px-4 py-3">{session.score.toFixed(0)}</td><td className="px-4 py-3">{session.xp_awarded}</td><td className="px-4 py-3">{session.status}</td></tr>)}</tbody></table>
          </div>
        </section>

        <section className="border border-gray-200 bg-white shadow-sm">
          <div className="border-b border-gray-100 px-5 py-4"><h2 className="font-semibold">Lịch sử gửi</h2></div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm"><thead className="bg-gray-50 text-left text-xs text-gray-500"><tr><th className="px-4 py-3">Thời gian</th><th className="px-4 py-3">User</th><th className="px-4 py-3">Loại</th><th className="px-4 py-3">Trạng thái</th><th className="px-4 py-3">Retry</th><th className="px-4 py-3">Lỗi</th></tr></thead><tbody className="divide-y divide-gray-100">{dashboard.deliveries.map((item) => <tr key={item.id}><td className="px-4 py-3 whitespace-nowrap">{new Date(item.created_at).toLocaleString('vi-VN')}</td><td className="px-4 py-3">{item.user_email || '-'}</td><td className="px-4 py-3">{item.event_type}</td><td className="px-4 py-3">{item.status}</td><td className="px-4 py-3">{item.retry_count}/{item.max_retries}</td><td className="max-w-xs truncate px-4 py-3 text-red-600">{item.last_error || '-'}</td></tr>)}</tbody></table>
          </div>
        </section>
      </main>
    </div>
  );
}
