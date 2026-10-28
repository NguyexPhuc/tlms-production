'use client';

import { useCallback, useEffect, useState } from 'react';
import { Award, Ban, CheckCircle2, FileQuestion, FileText, LayoutTemplate, Settings2, Users } from 'lucide-react';
import { useRouter } from 'next/navigation';

import { useAuth } from '@/contexts/AuthContext';
import { apiClient } from '@/lib/api';
import { AdminExamResult, Certificate, CertificateStatistics, CertificateTemplate, CertificateVerificationLog, PendingExamAnswer } from '@/types/certification';

export default function AdminCertificationsPage() {
  const router = useRouter();
  const { user, isLoading } = useAuth();
  const [stats, setStats] = useState<CertificateStatistics | null>(null);
  const [certificates, setCertificates] = useState<Certificate[]>([]);
  const [templates, setTemplates] = useState<CertificateTemplate[]>([]);
  const [verificationLogs, setVerificationLogs] = useState<CertificateVerificationLog[]>([]);
  const [results, setResults] = useState<AdminExamResult[]>([]);
  const [pendingAnswers, setPendingAnswers] = useState<PendingExamAnswer[]>([]);
  const [reviewScores, setReviewScores] = useState<Record<string, string>>({});
  const [tab, setTab] = useState<'certificates' | 'results' | 'reviews' | 'templates' | 'verifications'>('certificates');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const load = useCallback(async () => {
    try {
      const [summary, certificateRows, templateRows, verificationRows, resultRows, pendingRows] = await Promise.all([
        apiClient.getCertificateStatistics(),
        apiClient.listAdminCertificates(),
        apiClient.listCertificateTemplates(),
        apiClient.listCertificateVerificationLogs(),
        apiClient.listAdminExamResults(),
        apiClient.listPendingExamAnswers(),
      ]);
      setStats(summary);
      setCertificates(certificateRows);
      setTemplates(templateRows);
      setVerificationLogs(verificationRows);
      setResults(resultRows);
      setPendingAnswers(pendingRows);
    } catch {
      setError('Không thể tải trung tâm quản trị chứng chỉ.');
    }
  }, []);

  useEffect(() => {
    if (!isLoading && (!user || !user.roles.includes('admin'))) router.push('/dashboard');
    if (user?.roles.includes('admin')) {
      const timer = window.setTimeout(() => { void load(); }, 0);
      return () => window.clearTimeout(timer);
    }
  }, [isLoading, user, router, load]);

  const revoke = async (certificate: Certificate) => {
    const reason = window.prompt('Nhập lý do thu hồi chứng chỉ (tối thiểu 5 ký tự):');
    if (!reason || reason.trim().length < 5) return;
    try {
      await apiClient.revokeCertificate(certificate.id, reason.trim());
      setNotice(`Đã thu hồi ${certificate.certificate_id}.`);
      await load();
    } catch {
      setError('Thu hồi chứng chỉ thất bại.');
    }
  };

  const review = async (answer: PendingExamAnswer) => {
    const score = Number(reviewScores[answer.id]);
    if (!Number.isFinite(score) || score < 0 || score > answer.max_points) {
      setError(`Điểm phải từ 0 đến ${answer.max_points}.`); return;
    }
    try {
      await apiClient.reviewExamAnswer(answer.id, score);
      setNotice('Đã lưu điểm câu tự luận.'); await load();
    } catch { setError('Không thể lưu điểm đánh giá.'); }
  };

  if (isLoading || !user) return <div className="flex min-h-screen items-center justify-center bg-slate-50 text-sm text-slate-500">Đang tải...</div>;

  const cards = [
    { label: 'Người dùng', value: stats?.total_users ?? 0, icon: Users, color: 'text-blue-700 bg-blue-50' },
    { label: 'Lượt thi', value: stats?.total_attempts ?? 0, icon: FileText, color: 'text-violet-700 bg-violet-50' },
    { label: 'Tỷ lệ đạt', value: `${stats?.pass_rate ?? 0}%`, icon: CheckCircle2, color: 'text-emerald-700 bg-emerald-50' },
    { label: 'Chứng chỉ', value: stats?.total_certificates ?? 0, icon: Award, color: 'text-amber-700 bg-amber-50' },
  ];

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex min-h-16 max-w-7xl items-center justify-between gap-4 px-4 py-3">
          <div><p className="text-xs font-semibold uppercase text-red-700">Admin</p><h1 className="text-xl font-bold text-slate-950">Quản trị chứng chỉ</h1></div>
          <div className="flex gap-2">
            <button onClick={() => router.push('/admin/certifications/setup')} title="Cấu hình khóa học và bài thi" className="rounded-lg border border-slate-200 p-2.5 text-slate-700 hover:border-red-300 hover:text-red-700"><Settings2 size={18} /></button>
            <button onClick={() => router.push('/admin/questions')} title="Ngân hàng câu hỏi" className="rounded-lg border border-slate-200 p-2.5 text-slate-700 hover:border-red-300 hover:text-red-700"><FileQuestion size={18} /></button>
            <button onClick={() => router.push('/admin/certifications/templates/new')} title="Tạo mẫu chứng chỉ" className="rounded-lg border border-slate-200 p-2.5 text-slate-700 hover:border-red-300 hover:text-red-700"><LayoutTemplate size={18} /></button>
            <button onClick={() => router.push('/dashboard')} className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700">Quay lại</button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl space-y-6 px-4 py-7">
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {cards.map(({ label, value, icon: Icon, color }) => (
            <div key={label} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <div className={`flex h-9 w-9 items-center justify-center rounded-lg ${color}`}><Icon size={18} /></div>
              <p className="mt-3 text-xs font-semibold uppercase text-slate-500">{label}</p>
              <p className="mt-1 text-2xl font-bold text-slate-950">{value}</p>
            </div>
          ))}
        </div>
        <div className="flex gap-1 border-b border-slate-200">
          <button onClick={() => setTab('certificates')} className={`border-b-2 px-4 py-3 text-sm font-semibold ${tab === 'certificates' ? 'border-red-700 text-red-700' : 'border-transparent text-slate-500'}`}>Chứng chỉ</button>
          <button onClick={() => setTab('results')} className={`border-b-2 px-4 py-3 text-sm font-semibold ${tab === 'results' ? 'border-red-700 text-red-700' : 'border-transparent text-slate-500'}`}>Kết quả thi</button>
          <button onClick={() => setTab('reviews')} className={`border-b-2 px-4 py-3 text-sm font-semibold ${tab === 'reviews' ? 'border-red-700 text-red-700' : 'border-transparent text-slate-500'}`}>Chờ chấm ({pendingAnswers.length})</button>
          <button onClick={() => setTab('templates')} className={`border-b-2 px-4 py-3 text-sm font-semibold ${tab === 'templates' ? 'border-red-700 text-red-700' : 'border-transparent text-slate-500'}`}>Mẫu thiết kế</button>
          <button onClick={() => setTab('verifications')} className={`border-b-2 px-4 py-3 text-sm font-semibold ${tab === 'verifications' ? 'border-red-700 text-red-700' : 'border-transparent text-slate-500'}`}>Lịch sử xác minh</button>
        </div>
        {error && <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}
        {notice && <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{notice}</div>}

        {tab === 'certificates' ? (
          <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase text-slate-500"><tr><th className="px-4 py-3">Người nhận</th><th className="px-4 py-3">Chứng chỉ</th><th className="px-4 py-3">Điểm</th><th className="px-4 py-3">Ngày cấp</th><th className="px-4 py-3">Trạng thái</th><th className="px-4 py-3 text-right">Thao tác</th></tr></thead>
              <tbody className="divide-y divide-slate-100">
                {certificates.map((certificate) => (
                  <tr key={certificate.id}>
                    <td className="px-4 py-3 font-medium text-slate-900">{certificate.full_name}</td>
                    <td className="px-4 py-3"><p className="font-medium text-slate-900">{certificate.certificate_name}</p><p className="text-xs text-slate-500">{certificate.certificate_id}</p></td>
                    <td className="px-4 py-3 font-semibold">{certificate.score}%</td>
                    <td className="px-4 py-3 text-slate-600">{new Date(certificate.issued_at).toLocaleDateString('vi-VN')}</td>
                    <td className="px-4 py-3"><span className={`rounded px-2 py-1 text-xs font-semibold ${certificate.status === 'revoked' ? 'bg-red-50 text-red-700' : 'bg-emerald-50 text-emerald-700'}`}>{certificate.status === 'revoked' ? 'Đã thu hồi' : 'Hợp lệ'}</span></td>
                    <td className="px-4 py-3 text-right">{certificate.status !== 'revoked' && <button onClick={() => revoke(certificate)} title="Thu hồi" className="rounded-lg p-2 text-slate-500 hover:bg-red-50 hover:text-red-700"><Ban size={17} /></button>}</td>
                  </tr>
                ))}
                {certificates.length === 0 && <tr><td colSpan={6} className="px-4 py-10 text-center text-slate-500">Chưa có chứng chỉ được cấp.</td></tr>}
              </tbody>
            </table>
          </div>
        ) : tab === 'results' ? (
          <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
            <table className="w-full min-w-[820px] text-left text-sm"><thead className="bg-slate-50 text-xs uppercase text-slate-500"><tr><th className="px-4 py-3">Thành viên</th><th className="px-4 py-3">Bài thi</th><th className="px-4 py-3">Điểm</th><th className="px-4 py-3">Năng lực</th><th className="px-4 py-3">Thời gian</th><th className="px-4 py-3">Chứng chỉ</th></tr></thead><tbody className="divide-y divide-slate-100">{results.map((result) => <tr key={result.id}><td className="px-4 py-3"><p className="font-medium text-slate-900">{result.user_name}</p><p className="text-xs text-slate-500">{result.user_email}</p></td><td className="px-4 py-3"><p className="font-medium text-slate-900">{result.exam_title}</p><p className="text-xs text-slate-500">{result.course_title}</p></td><td className={`px-4 py-3 font-bold ${result.passed ? 'text-emerald-700' : 'text-red-700'}`}>{result.percentage}%</td><td className="px-4 py-3 text-slate-600">{result.proficiency_level}</td><td className="px-4 py-3 text-slate-600">{new Date(result.graded_at).toLocaleString('vi-VN')}</td><td className="px-4 py-3">{result.certificate_id ? <span className="rounded bg-emerald-50 px-2 py-1 text-xs font-semibold text-emerald-700">Đã cấp</span> : <span className="text-xs text-slate-500">Chưa cấp</span>}</td></tr>)}{results.length === 0 && <tr><td colSpan={6} className="px-4 py-10 text-center text-slate-500">Chưa có kết quả thi.</td></tr>}</tbody></table>
          </div>
        ) : tab === 'reviews' ? (
          <div className="grid gap-4 md:grid-cols-2">{pendingAnswers.map((answer) => <article key={answer.id} className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm"><p className="text-xs font-semibold uppercase text-red-700">{answer.exam_title}</p><h2 className="mt-2 font-bold text-slate-950">{answer.question_title}</h2><p className="mt-2 text-sm text-slate-600">{answer.question_text}</p><div className="mt-4 rounded-lg bg-slate-50 p-3 text-sm text-slate-800"><span className="mb-1 block text-xs font-semibold text-slate-500">Bài làm của {answer.user_name}</span>{answer.text_answer || '--'}</div><div className="mt-4 flex items-end gap-3"><label className="flex-1 text-xs font-semibold text-slate-600">Điểm / {answer.max_points}<input type="number" min={0} max={answer.max_points} step="0.5" value={reviewScores[answer.id] || ''} onChange={(e) => setReviewScores((current) => ({ ...current, [answer.id]: e.target.value }))} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></label><button onClick={() => review(answer)} className="rounded-lg bg-red-700 px-4 py-2 text-sm font-semibold text-white">Lưu điểm</button></div></article>)}{pendingAnswers.length === 0 && <div className="md:col-span-2 rounded-lg border border-dashed border-slate-300 p-10 text-center text-sm text-slate-500">Không có bài tự luận chờ chấm.</div>}</div>
        ) : tab === 'templates' ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {templates.map((template) => (
              <article key={template.id} className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
                <div className="flex items-start justify-between">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg" style={{ backgroundColor: `${template.primary_color}18`, color: template.primary_color }}><LayoutTemplate size={20} /></div>
                  {template.is_default && <span className="rounded bg-amber-50 px-2 py-1 text-xs font-semibold text-amber-700">Mặc định</span>}
                </div>
                <h2 className="mt-4 font-bold text-slate-950">{template.name}</h2>
                <p className="mt-1 text-sm text-slate-500">{template.organization_name} · v{template.version}</p>
                <div className="mt-4 flex gap-2">{[template.primary_color, template.secondary_color, template.accent_color, template.background_color].map((color) => <span key={color} className="h-6 w-6 rounded-full border border-slate-200" style={{ backgroundColor: color }} title={color} />)}</div>
              </article>
            ))}
          </div>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
            <table className="w-full min-w-[680px] text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase text-slate-500"><tr><th className="px-4 py-3">Thời gian</th><th className="px-4 py-3">Kết quả</th><th className="px-4 py-3">Token fingerprint</th><th className="px-4 py-3">Thiết bị</th></tr></thead>
              <tbody className="divide-y divide-slate-100">
                {verificationLogs.map((log) => <tr key={log.id}><td className="px-4 py-3 text-slate-600">{new Date(log.verified_at).toLocaleString('vi-VN')}</td><td className="px-4 py-3"><span className={`rounded px-2 py-1 text-xs font-semibold ${log.result === 'VALID' ? 'bg-emerald-50 text-emerald-700' : log.result === 'REVOKED' ? 'bg-red-50 text-red-700' : 'bg-amber-50 text-amber-700'}`}>{log.result}</span></td><td className="px-4 py-3 font-mono text-xs text-slate-500">{log.token_fingerprint.slice(0, 16)}...</td><td className="max-w-sm truncate px-4 py-3 text-xs text-slate-500">{log.user_agent || '--'}</td></tr>)}
                {verificationLogs.length === 0 && <tr><td colSpan={4} className="px-4 py-10 text-center text-slate-500">Chưa có lượt xác minh.</td></tr>}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  );
}
