'use client';

import { useCallback, useEffect, useState } from 'react';
import { Bell, ExternalLink, Link2, MessageCircle, ShieldCheck, Unlink } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { apiClient } from '@/lib/api';
import { ZaloLink } from '@/types/zalo';

const ZALO_READ_ONLY = true;

function errorMessage(error: unknown): string {
  if (error && typeof error === 'object' && 'response' in error) {
    const response = (error as { response?: { data?: { detail?: string } } }).response;
    return response?.data?.detail || 'Không thể thực hiện yêu cầu.';
  }
  return 'Không thể thực hiện yêu cầu.';
}

export default function ZaloLinkPage() {
  const router = useRouter();
  const { user, isLoading } = useAuth();
  const [link, setLink] = useState<ZaloLink | null>(null);
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const loadLink = useCallback(async () => {
    try {
      setLink(await apiClient.getMyZaloLink());
    } catch (err) {
      setError(errorMessage(err));
    }
  }, []);

  useEffect(() => {
    if (!isLoading && !user) router.replace('/login');
    if (user) loadLink();
  }, [isLoading, user, router, loadLink]);

  useEffect(() => {
    if (link?.status !== 'pending') return;
    const timer = window.setInterval(loadLink, 5000);
    return () => window.clearInterval(timer);
  }, [link?.status, loadLink]);

  const startLink = async () => {
    if (ZALO_READ_ONLY) return;
    setBusy(true);
    setError('');
    setMessage('');
    try {
      const result = await apiClient.createZaloLinkIntent(consent);
      setLink(result);
      setMessage(result.status === 'linked' ? 'Đã liên kết Zalo.' : 'Mã liên kết đã sẵn sàng.');
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const toggleNotifications = async () => {
    if (!link || ZALO_READ_ONLY) return;
    setBusy(true);
    setError('');
    try {
      setLink(await apiClient.updateZaloNotifications(!link.notifications_enabled));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const revoke = async () => {
    if (ZALO_READ_ONLY) return;
    setBusy(true);
    setError('');
    try {
      setLink(await apiClient.revokeZaloLink());
      setConsent(false);
      setMessage('Đã ngắt liên kết Zalo.');
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  if (isLoading || !user || !link) {
    return <div className="min-h-screen bg-gray-50 flex items-center justify-center text-sm text-gray-500">Đang tải...</div>;
  }

  const linked = link.status === 'linked';

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex h-16 max-w-5xl items-center justify-between px-4">
          <div className="flex items-center gap-3">
            <MessageCircle className="h-6 w-6 text-blue-600" />
            <div>
              <h1 className="font-semibold">Zalo Daily Task</h1>
              <p className="text-xs text-gray-500">{user.email}</p>
            </div>
          </div>
          <button onClick={() => router.push('/dashboard')} className="text-sm text-gray-600 hover:text-blue-600">Quay lại</button>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 py-8 space-y-6">
        {ZALO_READ_ONLY && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
            <p className="font-semibold text-amber-900">Đang phát triển</p>
            <p className="mt-1 text-sm text-amber-800">
              Bạn có thể xem trước trang tích hợp. Chức năng liên kết tài khoản và nhận Daily Task qua Zalo OA sẽ được mở sau.
            </p>
          </div>
        )}
        <section className="border border-gray-200 bg-white p-6 shadow-sm">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className={`flex h-10 w-10 items-center justify-center rounded-full ${linked ? 'bg-green-50 text-green-600' : 'bg-blue-50 text-blue-600'}`}>
                {linked ? <ShieldCheck className="h-5 w-5" /> : <Link2 className="h-5 w-5" />}
              </div>
              <div>
                <h2 className="font-semibold">{linked ? 'Đã liên kết' : 'Liên kết Zalo OA'}</h2>
                <p className="mt-1 text-sm text-gray-500">
                  {linked ? 'Daily Quiz sẽ được gửi theo lịch đã cấu hình.' : 'Nhận và trả lời câu hỏi A/B/C/D trong Zalo.'}
                </p>
              </div>
            </div>
            <span className={`px-2 py-1 text-xs font-medium ${linked ? 'bg-green-50 text-green-700' : 'bg-gray-100 text-gray-600'}`}>
              {link.status}
            </span>
          </div>

          {!linked && (
            <div className="mt-6 space-y-4 border-t border-gray-100 pt-5">
              <label className="flex items-start gap-3 text-sm text-gray-700">
                <input
                  type="checkbox"
                  checked={consent}
                  onChange={(event) => setConsent(event.target.checked)}
                  disabled={ZALO_READ_ONLY}
                  className="mt-0.5 h-4 w-4 accent-blue-600"
                />
                <span>Tôi đồng ý liên kết tài khoản và nhận thông báo Daily Task qua Zalo OA.</span>
              </label>
              <button
                onClick={startLink}
                disabled={ZALO_READ_ONLY || !consent || busy}
                className="inline-flex items-center gap-2 bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Link2 className="h-4 w-4" />
                {busy ? 'Đang xử lý...' : 'Tạo liên kết'}
              </button>
            </div>
          )}

          {link.status === 'pending' && link.link_code && (
            <div className="mt-6 border-t border-gray-100 pt-5">
              <p className="text-sm text-gray-600">Gửi nội dung sau cho OA:</p>
              <div className="mt-2 bg-gray-950 px-4 py-3 font-mono text-sm text-white">TLMS LINK {link.link_code}</div>
              {link.oa_url && (
                <a href={link.oa_url} target="_blank" rel="noreferrer" className="mt-3 inline-flex items-center gap-2 text-sm font-medium text-blue-600">
                  Mở Zalo OA <ExternalLink className="h-4 w-4" />
                </a>
              )}
            </div>
          )}

          {linked && (
            <div className="mt-6 grid gap-3 border-t border-gray-100 pt-5 sm:grid-cols-2">
              <button
                onClick={toggleNotifications}
                disabled={ZALO_READ_ONLY || busy}
                className="flex items-center justify-center gap-2 border border-gray-300 px-4 py-2 text-sm font-medium hover:bg-gray-50 disabled:opacity-50"
              >
                <Bell className="h-4 w-4" />
                {link.notifications_enabled ? 'Tắt thông báo' : 'Bật thông báo'}
              </button>
              <button
                onClick={revoke}
                disabled={ZALO_READ_ONLY || busy}
                className="flex items-center justify-center gap-2 border border-red-200 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 disabled:opacity-50"
              >
                <Unlink className="h-4 w-4" /> Ngắt liên kết
              </button>
            </div>
          )}
        </section>

        {message && <div className="border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">{message}</div>}
        {error && <div className="border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
      </main>
    </div>
  );
}
