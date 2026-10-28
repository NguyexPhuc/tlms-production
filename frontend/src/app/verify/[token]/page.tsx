'use client';

import { use, useEffect, useState } from 'react';
import { AlertTriangle, BadgeCheck, Ban, SearchX } from 'lucide-react';

import { apiClient } from '@/lib/api';
import { CertificateVerification } from '@/types/certification';


const statusView = {
  VALID: { label: 'VALID', text: 'Chứng chỉ hợp lệ', color: 'text-emerald-700 bg-emerald-50 border-emerald-200', icon: BadgeCheck },
  EXPIRED: { label: 'EXPIRED', text: 'Chứng chỉ đã hết hạn', color: 'text-amber-700 bg-amber-50 border-amber-200', icon: AlertTriangle },
  REVOKED: { label: 'REVOKED', text: 'Chứng chỉ đã bị thu hồi', color: 'text-red-700 bg-red-50 border-red-200', icon: Ban },
  NOT_FOUND: { label: 'NOT FOUND', text: 'Không tìm thấy chứng chỉ', color: 'text-slate-700 bg-slate-100 border-slate-200', icon: SearchX },
};

export default function VerifyCertificatePage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = use(params);
  const [data, setData] = useState<CertificateVerification | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    apiClient.verifyCertificate(token).then(setData).catch(() => setError('Không thể kết nối hệ thống xác minh.'));
  }, [token]);

  if (!data && !error) return <div className="flex min-h-screen items-center justify-center bg-[#FFFCF5] text-sm text-slate-500">Đang xác minh dữ liệu...</div>;
  if (error) return <div className="flex min-h-screen items-center justify-center bg-[#FFFCF5] px-4"><div className="rounded-lg border border-red-200 bg-white p-6 text-red-700">{error}</div></div>;
  if (!data) return null;
  const view = statusView[data.verification_status];
  const Icon = view.icon;

  return (
    <main className="min-h-screen bg-[#FFFCF5] px-4 py-10">
      <section className="mx-auto max-w-3xl overflow-hidden rounded-lg border border-amber-200 bg-white shadow-lg">
        <div className="border-b-4 border-red-700 px-6 py-7 sm:px-10">
          <p className="text-xs font-bold uppercase text-red-700">T&A Lab · Official Verification</p>
          <h1 className="mt-2 text-2xl font-bold text-[#101D35]">Xác minh chứng chỉ số</h1>
        </div>
        <div className="p-6 sm:p-10">
          <div className={`flex items-center gap-4 rounded-lg border p-4 ${view.color}`}>
            <Icon size={34} />
            <div><p className="text-xl font-black">{view.label}</p><p className="text-sm">{view.text}</p></div>
          </div>
          {data.certificate_id && (
            <dl className="mt-8 grid gap-x-8 gap-y-5 sm:grid-cols-2">
              <div><dt className="text-xs font-semibold uppercase text-slate-500">Người được cấp</dt><dd className="mt-1 text-lg font-bold text-slate-950">{data.full_name}</dd></div>
              <div><dt className="text-xs font-semibold uppercase text-slate-500">Mã chứng chỉ</dt><dd className="mt-1 font-mono text-sm font-semibold text-slate-900">{data.certificate_id}</dd></div>
              <div className="sm:col-span-2"><dt className="text-xs font-semibold uppercase text-slate-500">Chứng nhận</dt><dd className="mt-1 text-lg font-bold text-slate-950">{data.certificate_name}</dd></div>
              <div><dt className="text-xs font-semibold uppercase text-slate-500">Đơn vị cấp</dt><dd className="mt-1 text-sm text-slate-800">{data.issuer_name}</dd></div>
              <div><dt className="text-xs font-semibold uppercase text-slate-500">Mức năng lực</dt><dd className="mt-1 text-sm font-semibold text-slate-800">{data.proficiency_level}</dd></div>
              <div><dt className="text-xs font-semibold uppercase text-slate-500">Ngày cấp</dt><dd className="mt-1 text-sm text-slate-800">{data.issued_at ? new Date(data.issued_at).toLocaleDateString('vi-VN') : '--'}</dd></div>
              <div><dt className="text-xs font-semibold uppercase text-slate-500">Hết hạn</dt><dd className="mt-1 text-sm text-slate-800">{data.expires_at ? new Date(data.expires_at).toLocaleDateString('vi-VN') : 'Không thời hạn'}</dd></div>
              {data.score !== null && data.score !== undefined && <div><dt className="text-xs font-semibold uppercase text-slate-500">Điểm công khai</dt><dd className="mt-1 text-sm font-bold text-slate-800">{data.score}%</dd></div>}
              {data.skills.length > 0 && <div className="sm:col-span-2"><dt className="text-xs font-semibold uppercase text-slate-500">Kỹ năng</dt><dd className="mt-2 flex flex-wrap gap-2">{data.skills.map((skill) => <span key={skill} className="rounded bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">{skill}</span>)}</dd></div>}
            </dl>
          )}
          <p className="mt-9 border-t border-slate-100 pt-5 text-xs leading-5 text-slate-500">Kết quả này được truy vấn trực tiếp từ hệ thống TLMS. QR không tự quyết định tính hợp lệ của chứng chỉ.</p>
        </div>
      </section>
    </main>
  );
}
