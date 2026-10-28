'use client';

import { FormEvent, useEffect, useState } from 'react';
import { QrCode, Save } from 'lucide-react';
import { useRouter } from 'next/navigation';

import { useAuth } from '@/contexts/AuthContext';
import { apiClient } from '@/lib/api';

const initial = {
  name: 'Premium Technology Certificate',
  organization_name: 'T&A Lab',
  title: 'CERTIFICATE OF ACHIEVEMENT',
  subtitle: 'DIGITAL TECHNOLOGY & PROFESSIONAL SKILLS',
  primary_color: '#C8102E',
  secondary_color: '#101D35',
  accent_color: '#C6A15B',
  background_color: '#FFFCF5',
  signature_name: '',
  signature_title: '',
  font_family: 'DejaVu Sans',
  layout: { page: 'A4_portrait', design: 'premium_technology_v1', signature_x_pct: 24, signature_y_pct: 13.3, qr_x_pct: 76, qr_y_pct: 7.5 },
  is_default: false,
};

export default function NewCertificateTemplatePage() {
  const router = useRouter();
  const { user, isLoading } = useAuth();
  const [form, setForm] = useState(initial);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [logo, setLogo] = useState<File | null>(null);
  const [background, setBackground] = useState<File | null>(null);

  useEffect(() => {
    if (!isLoading && (!user || !user.roles.includes('admin'))) router.push('/dashboard');
  }, [isLoading, user, router]);

  const submit = async (event: FormEvent) => {
    event.preventDefault(); setSaving(true); setError('');
    try {
      const template = await apiClient.createCertificateTemplate({
        ...form,
        signature_name: form.signature_name || null,
        signature_title: form.signature_title || null,
      });
      if (logo) await apiClient.uploadCertificateTemplateAsset(template.id, 'logo', logo);
      if (background) await apiClient.uploadCertificateTemplateAsset(template.id, 'background', background);
      router.push('/admin/certifications');
    } catch { setError('Không thể lưu mẫu. Hãy kiểm tra các trường màu và nội dung.'); }
    finally { setSaving(false); }
  };

  if (isLoading || !user) return <div className="flex min-h-screen items-center justify-center bg-slate-50 text-sm text-slate-500">Đang tải...</div>;
  const inputClass = 'mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm focus:border-red-500';

  return (
    <div className="min-h-screen bg-slate-100">
      <header className="border-b border-slate-200 bg-white"><div className="mx-auto flex min-h-16 max-w-7xl items-center justify-between gap-4 px-4 py-3"><div><p className="text-xs font-semibold uppercase text-red-700">Template Editor</p><h1 className="text-xl font-bold text-slate-950">Thiết kế chứng chỉ</h1></div><button onClick={() => router.push('/admin/certifications')} className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700">Hủy</button></div></header>
      <main className="mx-auto grid max-w-7xl gap-6 px-4 py-7 lg:grid-cols-[380px_1fr]">
        <form onSubmit={submit} className="space-y-4 rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <label className="block text-sm font-medium text-slate-700">Tên mẫu<input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className={inputClass} /></label>
          <label className="block text-sm font-medium text-slate-700">Đơn vị phát hành<input required value={form.organization_name} onChange={(e) => setForm({ ...form, organization_name: e.target.value })} className={inputClass} /></label>
          <label className="block text-sm font-medium text-slate-700">Tiêu đề<input required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} className={inputClass} /></label>
          <label className="block text-sm font-medium text-slate-700">Phụ đề<input value={form.subtitle} onChange={(e) => setForm({ ...form, subtitle: e.target.value })} className={inputClass} /></label>
          <div className="grid grid-cols-2 gap-3">
            {[['primary_color', 'Ruby'], ['secondary_color', 'Navy'], ['accent_color', 'Gold'], ['background_color', 'Nền']].map(([key, label]) => <label key={key} className="text-sm font-medium text-slate-700">{label}<span className="mt-1 flex rounded-lg border border-slate-300 bg-white p-1"><input type="color" value={form[key as keyof typeof form] as string} onChange={(e) => setForm({ ...form, [key]: e.target.value })} className="h-9 w-11 cursor-pointer border-0 bg-transparent" /><input value={form[key as keyof typeof form] as string} onChange={(e) => setForm({ ...form, [key]: e.target.value })} pattern="#[0-9A-Fa-f]{6}" className="min-w-0 flex-1 px-2 text-xs" /></span></label>)}
          </div>
          <label className="block text-sm font-medium text-slate-700">Người ký<input value={form.signature_name} onChange={(e) => setForm({ ...form, signature_name: e.target.value })} className={inputClass} placeholder="Authorized Representative" /></label>
          <label className="block text-sm font-medium text-slate-700">Chức danh<input value={form.signature_title} onChange={(e) => setForm({ ...form, signature_title: e.target.value })} className={inputClass} /></label>
          <label className="block text-sm font-medium text-slate-700">Kiểu chữ<select value={form.font_family} onChange={(e) => setForm({ ...form, font_family: e.target.value })} className={inputClass}><option value="DejaVu Sans">DejaVu Sans</option><option value="DejaVu Serif">DejaVu Serif</option></select></label>
          <div className="grid grid-cols-2 gap-3"><label className="text-xs font-medium text-slate-600">Vị trí chữ ký<input type="range" min={18} max={76} value={form.layout.signature_x_pct} onChange={(e) => setForm({ ...form, layout: { ...form.layout, signature_x_pct: Number(e.target.value) } })} className="mt-2 w-full accent-red-700" /></label><label className="text-xs font-medium text-slate-600">Vị trí QR<input type="range" min={5} max={82} value={form.layout.qr_x_pct} onChange={(e) => setForm({ ...form, layout: { ...form.layout, qr_x_pct: Number(e.target.value) } })} className="mt-2 w-full accent-red-700" /></label></div>
          <div className="grid grid-cols-2 gap-3"><label className="text-sm font-medium text-slate-700">Logo<input type="file" accept="image/png,image/jpeg,image/webp" onChange={(e) => setLogo(e.target.files?.[0] || null)} className="mt-1 block w-full text-xs text-slate-500 file:mr-2 file:rounded file:border-0 file:bg-slate-100 file:px-2 file:py-2" /></label><label className="text-sm font-medium text-slate-700">Ảnh nền<input type="file" accept="image/png,image/jpeg,image/webp" onChange={(e) => setBackground(e.target.files?.[0] || null)} className="mt-1 block w-full text-xs text-slate-500 file:mr-2 file:rounded file:border-0 file:bg-slate-100 file:px-2 file:py-2" /></label></div>
          <p className="text-xs text-slate-500">PNG, JPEG hoặc WebP, tối đa 5 MB mỗi ảnh.</p>
          <label className="flex items-center gap-2 text-sm text-slate-700"><input type="checkbox" checked={form.is_default} onChange={(e) => setForm({ ...form, is_default: e.target.checked })} /> Dùng làm mẫu mặc định</label>
          {error && <p className="text-sm text-red-700">{error}</p>}
          <button disabled={saving} className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-red-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-red-800 disabled:bg-slate-300"><Save size={17} /> {saving ? 'Đang lưu...' : 'Lưu mẫu'}</button>
        </form>

        <section className="flex items-start justify-center overflow-auto rounded-lg border border-slate-200 bg-slate-200 p-4 sm:p-8">
          <div className="relative aspect-[210/297] w-full max-w-[650px] overflow-hidden bg-white p-[5%] shadow-xl" style={{ backgroundColor: form.background_color, border: `5px solid ${form.primary_color}`, outline: `2px solid ${form.accent_color}`, outlineOffset: '-13px' }}>
            <div className="absolute right-5 top-5 h-16 w-16 rounded-full" style={{ backgroundColor: form.primary_color }} />
            <p className="text-[clamp(9px,1.5vw,15px)] font-bold" style={{ color: form.secondary_color }}>{form.organization_name.toUpperCase()}</p>
            <div className="mt-[16%] text-center">
              <h2 className="text-[clamp(17px,3vw,31px)] font-black" style={{ color: form.primary_color }}>{form.title}</h2>
              <p className="mt-2 text-[clamp(7px,1.3vw,12px)] font-bold" style={{ color: form.accent_color }}>{form.subtitle}</p>
              <p className="mt-[10%] text-[clamp(8px,1.4vw,13px)]" style={{ color: form.secondary_color }}>This is to certify that</p>
              <p className="mt-4 border-b pb-3 text-[clamp(18px,3.2vw,34px)] font-bold" style={{ color: form.secondary_color, borderColor: form.accent_color }}>Nguyễn Ngọc Quang Phúc</p>
              <p className="mt-6 text-[clamp(8px,1.4vw,13px)]" style={{ color: form.secondary_color }}>has successfully completed the professional assessment</p>
              <p className="mt-4 text-[clamp(13px,2.3vw,23px)] font-bold" style={{ color: form.secondary_color }}>Digital Technology Foundation</p>
            </div>
            <div className="absolute bottom-[8%] -translate-x-1/2 text-center" style={{ color: form.secondary_color, left: `${form.layout.signature_x_pct}%`, fontFamily: form.font_family.includes('Serif') ? 'serif' : 'sans-serif' }}><div className="w-32 border-t pt-2 text-[clamp(7px,1.2vw,11px)] font-bold" style={{ borderColor: form.secondary_color }}>{form.signature_name || 'Authorized Representative'}</div><p className="mt-1 text-[clamp(6px,1vw,9px)]">{form.signature_title || form.organization_name}</p></div>
            <div className="absolute bottom-[7%] -translate-x-1/2 text-center" style={{ color: form.secondary_color, left: `${form.layout.qr_x_pct}%` }}><QrCode className="mx-auto h-14 w-14 sm:h-20 sm:w-20" /><p className="mt-1 text-[7px] font-bold">SCAN TO VERIFY</p></div>
          </div>
        </section>
      </main>
    </div>
  );
}
