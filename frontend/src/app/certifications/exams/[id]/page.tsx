'use client';

import { use, useCallback, useEffect, useMemo, useState } from 'react';
import { CheckCircle2, Clock3, ShieldCheck } from 'lucide-react';
import { useRouter } from 'next/navigation';

import { useAuth } from '@/contexts/AuthContext';
import { apiClient } from '@/lib/api';
import { ExamAttempt, ExamResult } from '@/types/certification';


export default function CertificationExamPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const { user, isLoading } = useAuth();
  const [attempt, setAttempt] = useState<ExamAttempt | null>(null);
  const [answers, setAnswers] = useState<Record<string, string[] | string>>({});
  const [result, setResult] = useState<ExamResult | null>(null);
  const [now, setNow] = useState(() => Date.now());
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const start = useCallback(async () => {
    setLoading(true);
    try {
      setAttempt(await apiClient.startCertificationExam(id));
    } catch (err: unknown) {
      const detail = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : undefined;
      setError(detail || 'Không thể bắt đầu bài thi.');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    if (!isLoading && !user) router.push('/login');
    if (user) start();
  }, [isLoading, user, router, start]);

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  const remaining = useMemo(() => {
    if (!attempt) return 0;
    return Math.max(0, Math.floor((new Date(attempt.expires_at).getTime() - now) / 1000));
  }, [attempt, now]);
  const answeredCount = attempt?.questions.filter((question) => {
    const value = answers[question.id];
    return Array.isArray(value) ? value.length > 0 : Boolean(value?.trim());
  }).length ?? 0;

  const chooseOption = (questionId: string, option: string, multiple: boolean) => {
    if (!multiple) {
      setAnswers((current) => ({ ...current, [questionId]: [option] }));
      return;
    }
    setAnswers((current) => {
      const selected = Array.isArray(current[questionId]) ? current[questionId] as string[] : [];
      return { ...current, [questionId]: selected.includes(option) ? selected.filter((item) => item !== option) : [...selected, option] };
    });
  };

  const submit = async () => {
    if (!attempt || answeredCount !== attempt.questions.length) {
      setError('Vui lòng trả lời đầy đủ tất cả câu hỏi.');
      return;
    }
    setSubmitting(true);
    setError('');
    try {
      const payload = attempt.questions.map((question) => ({
        exam_question_id: question.id,
        ...(Array.isArray(answers[question.id])
          ? { selected_options: answers[question.id] as string[] }
          : { text_answer: answers[question.id] as string }),
      }));
      setResult(await apiClient.submitCertificationExam(attempt.id, payload));
    } catch (err: unknown) {
      const detail = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : undefined;
      setError(detail || 'Không thể nộp bài.');
    } finally {
      setSubmitting(false);
    }
  };

  if (isLoading || loading) return <div className="flex min-h-screen items-center justify-center bg-slate-50 text-sm text-slate-500">Đang chuẩn bị bài thi...</div>;

  if (result) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-10">
        <section className="w-full max-w-xl rounded-lg border border-slate-200 bg-white p-8 text-center shadow-sm">
          <div className={`mx-auto flex h-16 w-16 items-center justify-center rounded-full ${result.passed ? 'bg-emerald-50 text-emerald-700' : result.status === 'pending_review' ? 'bg-amber-50 text-amber-700' : 'bg-red-50 text-red-700'}`}>
            {result.passed ? <CheckCircle2 size={34} /> : <ShieldCheck size={34} />}
          </div>
          <h1 className="mt-5 text-2xl font-bold text-slate-950">
            {result.status === 'pending_review' ? 'Đang chờ chấm tự luận' : result.passed ? 'Bạn đã đạt' : 'Chưa đạt lần này'}
          </h1>
          {result.status !== 'pending_review' && <p className="mt-3 text-4xl font-bold text-red-700">{result.percentage}%</p>}
          <p className="mt-2 text-sm text-slate-500">Mức năng lực: {result.proficiency_level}</p>
          <div className="mt-7 flex flex-col gap-2 sm:flex-row sm:justify-center">
            {result.verification_token && (
              <button onClick={() => router.push(`/verify/${result.verification_token}`)} className="rounded-lg bg-red-700 px-5 py-2.5 text-sm font-semibold text-white hover:bg-red-800">Xem chứng chỉ</button>
            )}
            <button onClick={() => router.push('/certifications')} className="rounded-lg border border-slate-200 px-5 py-2.5 text-sm font-semibold text-slate-700 hover:border-slate-400">Về danh sách</button>
          </div>
        </section>
      </main>
    );
  }

  if (!attempt) {
    return <main className="flex min-h-screen items-center justify-center bg-slate-50 px-4"><div className="max-w-lg rounded-lg border border-red-200 bg-white p-6 text-center text-red-700">{error || 'Không tìm thấy bài thi.'}</div></main>;
  }

  const timeText = `${Math.floor(remaining / 60).toString().padStart(2, '0')}:${(remaining % 60).toString().padStart(2, '0')}`;
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="sticky top-0 z-10 border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-4xl items-center justify-between gap-3 px-4 py-3">
          <div className="min-w-0"><p className="text-xs text-slate-500">Lượt {attempt.attempt_number}</p><h1 className="truncate font-bold text-slate-950">{attempt.exam_title}</h1></div>
          <div className={`inline-flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 font-mono text-sm font-bold ${remaining < 300 ? 'bg-red-50 text-red-700' : 'bg-slate-100 text-slate-800'}`}><Clock3 size={17} /> {timeText}</div>
        </div>
      </header>
      <main className="mx-auto max-w-4xl px-4 py-7">
        <div className="mb-6 flex items-center justify-between text-sm text-slate-500"><span>Đã trả lời {answeredCount}/{attempt.questions.length}</span><span>Điểm được chấm trên máy chủ</span></div>
        {error && <div className="mb-5 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}
        <div className="space-y-5">
          {attempt.questions.map((question, index) => {
            const isObjective = Boolean(question.options);
            const multiple = question.allow_multiple;
            const selected = Array.isArray(answers[question.id]) ? answers[question.id] as string[] : [];
            return (
              <section key={question.id} className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
                <div className="flex items-start gap-3"><span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-red-50 text-xs font-bold text-red-700">{index + 1}</span><div><h2 className="font-bold text-slate-950">{question.title}</h2><p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-700">{question.question}</p></div></div>
                {isObjective ? (
                  <div className="mt-5 grid gap-2 sm:grid-cols-2">
                    {Object.entries(question.options || {}).map(([key, text]) => (
                      <label key={key} className={`flex cursor-pointer items-start gap-3 rounded-lg border p-3 text-sm ${selected.includes(key) ? 'border-red-500 bg-red-50' : 'border-slate-200 hover:border-slate-400'}`}>
                        <input type={multiple ? 'checkbox' : 'radio'} name={question.id} checked={selected.includes(key)} onChange={() => chooseOption(question.id, key, multiple)} className="mt-0.5" />
                        <span><strong className="mr-1">{key}.</strong>{text}</span>
                      </label>
                    ))}
                  </div>
                ) : (
                  <textarea value={typeof answers[question.id] === 'string' ? answers[question.id] as string : ''} onChange={(event) => setAnswers((current) => ({ ...current, [question.id]: event.target.value }))} rows={5} maxLength={10000} className="mt-5 w-full rounded-lg border border-slate-300 p-3 text-sm focus:border-red-500" placeholder="Nhập câu trả lời..." />
                )}
              </section>
            );
          })}
        </div>
        <div className="sticky bottom-0 mt-6 border-t border-slate-200 bg-slate-50 py-4">
          <button onClick={submit} disabled={submitting || remaining === 0} className="w-full rounded-lg bg-red-700 px-5 py-3 text-sm font-bold text-white hover:bg-red-800 disabled:bg-slate-300">{submitting ? 'Đang chấm điểm...' : 'Nộp bài'}</button>
        </div>
      </main>
    </div>
  );
}
