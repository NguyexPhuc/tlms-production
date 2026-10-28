'use client';

import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import { Archive, CheckCircle2, CirclePlus, Search } from 'lucide-react';
import { useRouter } from 'next/navigation';

import { useAuth } from '@/contexts/AuthContext';
import { apiClient } from '@/lib/api';
import { Question } from '@/types/question';

const emptyForm = {
  title: '', question: '', category: 'technology', topic: '', difficulty: 'medium',
  numeric_difficulty: 3, target_member_level: 'new', question_type: 'single_choice',
  option_a: '', option_b: '', option_c: '', option_d: '', correct_option: 'A',
  correct_options: 'A,C', expected_answer: '', points: 10, expected_duration_minutes: 2,
};

export default function AdminQuestionBankPage() {
  const router = useRouter();
  const { user, isLoading } = useAuth();
  const [questions, setQuestions] = useState<Question[]>([]);
  const [form, setForm] = useState(emptyForm);
  const [query, setQuery] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const load = useCallback(async () => {
    try { setQuestions((await apiClient.listQuestions()).questions); }
    catch { setError('Không thể tải ngân hàng câu hỏi.'); }
  }, []);

  useEffect(() => {
    if (!isLoading && (!user || !user.roles.includes('admin'))) router.push('/dashboard');
    if (user?.roles.includes('admin')) load();
  }, [isLoading, user, router, load]);

  const visible = useMemo(() => {
    const keyword = query.trim().toLocaleLowerCase('vi');
    return keyword ? questions.filter((item) => `${item.title} ${item.question} ${item.topic || ''}`.toLocaleLowerCase('vi').includes(keyword)) : questions;
  }, [questions, query]);

  const create = async (event: FormEvent) => {
    event.preventDefault(); setSaving(true); setError(''); setNotice('');
    const objective = ['single_choice', 'multiple_choice', 'true_false'].includes(form.question_type);
    const multiAnswers = form.correct_options.split(',').map((value) => value.trim().toUpperCase()).filter((value) => /^[A-D]$/.test(value));
    try {
      await apiClient.createQuestion({
        title: form.title.trim(), question: form.question.trim(), category: form.category.trim() || undefined,
        topic: form.topic.trim() || undefined, difficulty: form.difficulty as Question['difficulty'],
        numeric_difficulty: form.numeric_difficulty, target_member_level: form.target_member_level as Question['target_member_level'],
        question_type: form.question_type, creator_type: 'manager', source: 'manager', points: form.points,
        expected_duration_minutes: form.expected_duration_minutes,
        options: form.question_type === 'true_false' ? { A: 'Đúng', B: 'Sai' } : objective ? { A: form.option_a, B: form.option_b, C: form.option_c, D: form.option_d } : undefined,
        correct_option: ['single_choice', 'true_false'].includes(form.question_type) ? form.correct_option : undefined,
        correct_options: form.question_type === 'multiple_choice' ? multiAnswers : undefined,
        expected_answer: objective ? undefined : form.expected_answer.trim(),
      });
      setForm(emptyForm); setNotice('Đã thêm câu hỏi vào ngân hàng.'); await load();
    } catch { setError('Không thể tạo câu hỏi. Kiểm tra đủ lựa chọn và đáp án đúng.'); }
    finally { setSaving(false); }
  };

  const archive = async (question: Question) => {
    try { await apiClient.updateQuestion(question.id, { status: 'archived' }); await load(); }
    catch { setError('Không thể lưu trạng thái câu hỏi.'); }
  };

  if (isLoading || !user) return <div className="flex min-h-screen items-center justify-center bg-slate-50 text-sm text-slate-500">Đang tải...</div>;
  const input = 'mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm outline-none focus:border-red-500';
  const objective = ['single_choice', 'multiple_choice', 'true_false'].includes(form.question_type);
  return <div className="min-h-screen bg-slate-50">
    <header className="border-b border-slate-200 bg-white"><div className="mx-auto flex min-h-16 max-w-7xl items-center justify-between gap-4 px-4 py-3"><div><p className="text-xs font-semibold uppercase text-red-700">Certification</p><h1 className="text-xl font-bold text-slate-950">Ngân hàng câu hỏi</h1></div><button onClick={() => router.push('/admin/certifications')} className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700">Quay lại</button></div></header>
    <main className="mx-auto grid max-w-7xl gap-6 px-4 py-7 lg:grid-cols-[390px_1fr]">
      <form onSubmit={create} className="space-y-4 rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex items-center gap-2"><CirclePlus size={20} className="text-red-700" /><h2 className="font-bold text-slate-950">Thêm câu hỏi</h2></div>
        <label className="block text-sm font-medium text-slate-700">Tiêu đề<input required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} className={input} /></label>
        <label className="block text-sm font-medium text-slate-700">Nội dung<textarea required rows={4} value={form.question} onChange={(e) => setForm({ ...form, question: e.target.value })} className={input} /></label>
        <div className="grid grid-cols-2 gap-3"><label className="text-sm font-medium text-slate-700">Loại<select value={form.question_type} onChange={(e) => setForm({ ...form, question_type: e.target.value })} className={input}><option value="single_choice">Một đáp án</option><option value="multiple_choice">Nhiều đáp án</option><option value="true_false">Đúng / Sai</option><option value="short_answer">Tự luận ngắn</option></select></label><label className="text-sm font-medium text-slate-700">Độ khó<select value={form.difficulty} onChange={(e) => setForm({ ...form, difficulty: e.target.value })} className={input}><option value="easy">Dễ</option><option value="medium">Vừa</option><option value="hard">Khó</option><option value="advanced">Nâng cao</option></select></label></div>
        <div className="grid grid-cols-2 gap-3"><label className="text-sm font-medium text-slate-700">Chủ đề<input value={form.topic} onChange={(e) => setForm({ ...form, topic: e.target.value })} className={input} placeholder="SQL, Backend..." /></label><label className="text-sm font-medium text-slate-700">Mức thành viên<select value={form.target_member_level} onChange={(e) => setForm({ ...form, target_member_level: e.target.value })} className={input}><option value="new">Thành viên mới</option><option value="diligent">Chuyên cần</option><option value="official">Chính thức</option></select></label></div>
        {objective ? <div className="space-y-2"><p className="text-sm font-medium text-slate-700">{form.question_type === 'true_false' ? 'Lựa chọn cố định: A. Đúng / B. Sai' : 'Lựa chọn A-D'}</p>{form.question_type !== 'true_false' && (['A','B','C','D'] as const).map((key) => <div key={key} className="flex items-center gap-2"><span className="w-5 text-sm font-bold text-slate-500">{key}</span><input required value={form[`option_${key.toLowerCase()}` as keyof typeof form] as string} onChange={(e) => setForm({ ...form, [`option_${key.toLowerCase()}`]: e.target.value })} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></div>)}{form.question_type === 'multiple_choice' ? <label className="block text-sm font-medium text-slate-700">Các đáp án đúng<input required pattern="[A-Da-d](\s*,\s*[A-Da-d])+" value={form.correct_options} onChange={(e) => setForm({ ...form, correct_options: e.target.value })} className={input} placeholder="A,C" /></label> : <label className="block text-sm font-medium text-slate-700">Đáp án đúng<select value={form.correct_option} onChange={(e) => setForm({ ...form, correct_option: e.target.value })} className={input}>{(form.question_type === 'true_false' ? ['A','B'] : ['A','B','C','D']).map((key) => <option key={key}>{key}</option>)}</select></label>}</div> : <label className="block text-sm font-medium text-slate-700">Đáp án tham chiếu<textarea required rows={3} value={form.expected_answer} onChange={(e) => setForm({ ...form, expected_answer: e.target.value })} className={input} /></label>}
        <div className="grid grid-cols-3 gap-3"><label className="text-xs font-medium text-slate-700">Độ khó 1-10<input type="number" min={1} max={10} value={form.numeric_difficulty} onChange={(e) => setForm({ ...form, numeric_difficulty: Number(e.target.value) })} className={input} /></label><label className="text-xs font-medium text-slate-700">Điểm<input type="number" min={0} value={form.points} onChange={(e) => setForm({ ...form, points: Number(e.target.value) })} className={input} /></label><label className="text-xs font-medium text-slate-700">Số phút<input type="number" min={1} value={form.expected_duration_minutes} onChange={(e) => setForm({ ...form, expected_duration_minutes: Number(e.target.value) })} className={input} /></label></div>
        {error && <p className="text-sm text-red-700">{error}</p>}{notice && <p className="text-sm text-emerald-700">{notice}</p>}
        <button disabled={saving} className="w-full rounded-lg bg-red-700 px-4 py-2.5 text-sm font-semibold text-white disabled:bg-slate-300">{saving ? 'Đang lưu...' : 'Thêm câu hỏi'}</button>
      </form>
      <section className="min-w-0"><div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center"><div><h2 className="font-bold text-slate-950">Danh sách câu hỏi</h2><p className="text-sm text-slate-500">{questions.length} câu đang hoạt động</p></div><label className="relative"><Search size={17} className="absolute left-3 top-3 text-slate-400" /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Tìm câu hỏi" className="w-full rounded-lg border border-slate-300 py-2.5 pl-9 pr-3 text-sm sm:w-72" /></label></div>
          <div className="mt-4 space-y-3">{visible.map((question) => <article key={question.id} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm"><div className="flex items-start justify-between gap-3"><div className="min-w-0"><div className="flex flex-wrap gap-2"><span className="rounded bg-red-50 px-2 py-1 text-xs font-semibold text-red-700">{{ single_choice: 'Một đáp án', multiple_choice: 'Nhiều đáp án', true_false: 'Đúng / Sai', short_answer: 'Tự luận' }[question.question_type] || question.question_type}</span><span className="rounded bg-slate-100 px-2 py-1 text-xs text-slate-600">{question.topic || question.category || 'Chung'}</span><span className="rounded bg-blue-50 px-2 py-1 text-xs text-blue-700">Độ khó {question.numeric_difficulty}/10</span></div><h3 className="mt-3 font-bold text-slate-950">{question.title}</h3><p className="mt-1 text-sm leading-6 text-slate-600">{question.question}</p></div><button onClick={() => archive(question)} title="Lưu trữ" className="rounded-lg p-2 text-slate-400 hover:bg-red-50 hover:text-red-700"><Archive size={17} /></button></div>{question.options && <div className="mt-3 grid gap-2 sm:grid-cols-2">{Object.entries(question.options).map(([key, value]) => <p key={key} className="rounded bg-slate-50 px-3 py-2 text-xs text-slate-600"><strong>{key}.</strong> {value}</p>)}</div>}<div className="mt-3 flex items-center gap-1 text-xs text-emerald-700"><CheckCircle2 size={14} /> Đáp án được bảo vệ phía server</div></article>)}{visible.length === 0 && <div className="rounded-lg border border-dashed border-slate-300 p-10 text-center text-sm text-slate-500">Không có câu hỏi phù hợp.</div>}</div>
      </section>
    </main>
  </div>;
}
