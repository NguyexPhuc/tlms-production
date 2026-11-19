'use client';

import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { CheckCircle2, ChevronLeft, Circle, LockKeyhole } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { apiClient } from '@/lib/api';
import { ResearchParticipantProgress } from '@/types/research';

const surveyStatements = [
  'Câu hỏi phù hợp với kiến thức hiện tại của tôi.',
  'Độ khó thay đổi hợp lý theo kết quả trả lời.',
  'Nội dung câu hỏi rõ ràng và dễ hiểu.',
  'Phản hồi sau câu trả lời giúp tôi học tốt hơn.',
  'Bộ câu hỏi bao phủ đúng kỹ năng công nghệ cần thiết.',
  'Tôi nhận thấy tiến bộ sau giai đoạn luyện tập.',
  'Thời lượng làm bài phù hợp.',
  'Giao diện giúp tôi tập trung vào câu hỏi.',
  'Tôi tin tưởng kết quả đánh giá của hệ thống.',
  'Tôi muốn tiếp tục sử dụng cách học thích ứng này.',
];

const errorMessage = (error: unknown, fallback: string) => {
  if (error && typeof error === 'object' && 'response' in error) {
    const response = (error as { response?: { data?: { detail?: string } } }).response;
    return response?.data?.detail || fallback;
  }
  return fallback;
};

export default function ResearchPage() {
  const router = useRouter();
  const { user, isLoading, isAuthenticated } = useAuth();
  const [progress, setProgress] = useState<ResearchParticipantProgress | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [likert, setLikert] = useState<number[]>(Array(10).fill(0));
  const [usefulFeedback, setUsefulFeedback] = useState('');
  const [improvementFeedback, setImprovementFeedback] = useState('');

  const loadProgress = async () => {
    try {
      setProgress(await apiClient.getMyResearchProgress());
      setError('');
    } catch (requestError) {
      setProgress(null);
      setError(errorMessage(requestError, 'Không thể tải tiến độ nghiên cứu.'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!isLoading && !isAuthenticated) router.replace('/login');
  }, [isAuthenticated, isLoading, router]);

  useEffect(() => {
    if (user) loadProgress();
  }, [user]);

  const consentGranted = progress?.consent_status === 'GRANTED';
  const trainReady = Boolean(consentGranted && progress?.pre_completed);
  const postReady = Boolean(
    trainReady && progress && progress.train_completed >= progress.train_required
  );
  const surveyReady = Boolean(postReady && progress?.post_completed);
  const trainPercent = useMemo(() => {
    if (!progress) return 0;
    return Math.min(100, (progress.train_completed / progress.train_required) * 100);
  }, [progress]);

  const updateConsent = async (status: 'GRANTED' | 'DECLINED') => {
    setBusy(true);
    setError('');
    try {
      await apiClient.updateMyResearchConsent(status);
      await loadProgress();
    } catch (requestError) {
      setError(errorMessage(requestError, 'Không thể cập nhật đồng ý tham gia.'));
    } finally {
      setBusy(false);
    }
  };

  const submitSurvey = async () => {
    if (likert.some((answer) => answer === 0)) {
      setError('Vui lòng trả lời đủ 10 nhận định trước khi gửi khảo sát.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      await apiClient.submitMyResearchSurvey({
        likert_answers: likert,
        useful_feedback: usefulFeedback,
        improvement_feedback: improvementFeedback,
      });
      await loadProgress();
    } catch (requestError) {
      setError(errorMessage(requestError, 'Không thể gửi khảo sát.'));
    } finally {
      setBusy(false);
    }
  };

  if (isLoading || loading) {
    return <div className="flex min-h-screen items-center justify-center bg-slate-50 text-slate-500">Đang tải...</div>;
  }

  if (!progress) {
    return (
      <main className="min-h-screen bg-slate-50 px-4 py-12">
        <div className="mx-auto max-w-xl rounded-lg border border-slate-200 bg-white p-6">
          <h1 className="text-xl font-semibold text-slate-950">Nghiên cứu TLMS 2026</h1>
          <p className="mt-2 text-sm text-slate-600">Tài khoản này chưa được chọn tham gia nghiên cứu.</p>
          {error && <p className="mt-4 text-sm text-red-600">{error}</p>}
          <button onClick={() => router.push('/dashboard')} className="mt-6 text-sm font-medium text-blue-600">Quay lại dashboard</button>
        </div>
      </main>
    );
  }

  const stages = [
    { label: 'Đồng ý tham gia', done: consentGranted },
    { label: 'PRE 20 câu', done: progress.pre_completed },
    { label: `TRAIN ${progress.train_completed}/${progress.train_required}`, done: progress.train_completed >= progress.train_required },
    { label: 'POST 20 câu', done: progress.post_completed },
    { label: 'Khảo sát', done: progress.survey_completed },
  ];

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8">
      <div className="mx-auto max-w-4xl">
        <button onClick={() => router.push('/dashboard')} className="mb-5 inline-flex items-center gap-2 text-sm font-medium text-slate-600 hover:text-blue-600">
          <ChevronLeft size={18} /> Quay lại
        </button>

        <header className="mb-6">
          <p className="text-sm font-semibold text-blue-600">{progress.participant_code}</p>
          <h1 className="mt-1 text-3xl font-bold text-slate-950">Nghiên cứu TLMS 2026</h1>
          <p className="mt-2 text-slate-600">Hoàn thành lần lượt PRE, luyện tập thích ứng, POST và khảo sát.</p>
        </header>

        <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-5">
          {stages.map((stage) => (
            <div key={stage.label} className="flex min-h-20 items-center gap-2 rounded-lg border border-slate-200 bg-white p-3">
              {stage.done ? <CheckCircle2 className="shrink-0 text-emerald-600" size={20} /> : <Circle className="shrink-0 text-slate-300" size={20} />}
              <span className="text-sm font-medium text-slate-700">{stage.label}</span>
            </div>
          ))}
        </div>

        {error && <div className="mb-5 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>}

        {!consentGranted && !['DECLINED', 'WITHDRAWN'].includes(progress.consent_status) && (
          <section className="rounded-lg border border-blue-200 bg-white p-6">
            <h2 className="text-xl font-semibold text-slate-950">Xác nhận tham gia</h2>
            <div className="mt-3 space-y-2 text-sm leading-6 text-slate-600">
              <p>Dữ liệu dùng cho nghiên cứu gồm đáp án, điểm, thời gian phản hồi, độ khó và tiến độ kỹ năng.</p>
              <p>Dữ liệu xuất nghiên cứu dùng mã người tham gia, không xuất tên, email, số điện thoại hoặc MSSV.</p>
              <p>Bạn có thể từ chối. Việc từ chối không làm mất tài khoản hoặc dữ liệu học tập TLMS.</p>
            </div>
            <div className="mt-5 flex flex-wrap gap-3">
              <button disabled={busy} onClick={() => updateConsent('GRANTED')} className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50">Đồng ý tham gia</button>
              <button disabled={busy} onClick={() => updateConsent('DECLINED')} className="rounded-lg border border-slate-300 px-5 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50">Từ chối</button>
            </div>
          </section>
        )}

        {['DECLINED', 'WITHDRAWN'].includes(progress.consent_status) && (
          <section className="rounded-lg border border-slate-200 bg-white p-6 text-sm text-slate-600">
            Bạn đã {progress.consent_status === 'DECLINED' ? 'từ chối tham gia' : 'rút lại đồng ý'}. Luồng nghiên cứu đã được khóa.
          </section>
        )}

        {consentGranted && (
          <div className="space-y-4">
            <section className="rounded-lg border border-slate-200 bg-white p-5">
              <div className="flex items-center justify-between gap-4">
                <div><p className="text-xs font-semibold uppercase text-slate-500">Bước 1</p><h2 className="mt-1 text-lg font-semibold">Bài PRE · 20 câu</h2><p className="mt-1 text-sm text-slate-600">Đánh giá năng lực trước khi luyện tập.</p></div>
                {progress.pre_completed ? <CheckCircle2 className="text-emerald-600" /> : <button disabled={!progress.pre_exam_id} onClick={() => router.push(`/certifications/exams/${progress.pre_exam_id}`)} className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white disabled:bg-slate-300">Bắt đầu PRE</button>}
              </div>
            </section>

            <section className="rounded-lg border border-slate-200 bg-white p-5">
              <div className="flex items-center justify-between gap-4">
                <div className="flex-1"><p className="text-xs font-semibold uppercase text-slate-500">Bước 2</p><h2 className="mt-1 text-lg font-semibold">TRAIN thích ứng</h2><p className="mt-1 text-sm text-slate-600">Hệ thống chọn câu tiếp theo theo kết quả của bạn.</p><div className="mt-3 h-2 overflow-hidden rounded bg-slate-100"><div className="h-full bg-blue-600" style={{ width: `${trainPercent}%` }} /></div></div>
                {trainReady ? <button onClick={() => router.push('/candidate/questions')} className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white">Tiếp tục TRAIN</button> : <LockKeyhole className="text-slate-400" />}
              </div>
            </section>

            <section className="rounded-lg border border-slate-200 bg-white p-5">
              <div className="flex items-center justify-between gap-4">
                <div><p className="text-xs font-semibold uppercase text-slate-500">Bước 3</p><h2 className="mt-1 text-lg font-semibold">Bài POST · 20 câu</h2><p className="mt-1 text-sm text-slate-600">Đánh giá sau tối thiểu 20 câu TRAIN.</p></div>
                {progress.post_completed ? <CheckCircle2 className="text-emerald-600" /> : postReady ? <button disabled={!progress.post_exam_id} onClick={() => router.push(`/certifications/exams/${progress.post_exam_id}`)} className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white disabled:bg-slate-300">Bắt đầu POST</button> : <LockKeyhole className="text-slate-400" />}
              </div>
            </section>

            {surveyReady && !progress.survey_completed && (
              <section className="rounded-lg border border-slate-200 bg-white p-6">
                <h2 className="text-xl font-semibold text-slate-950">Khảo sát sau nghiên cứu</h2>
                <p className="mt-1 text-sm text-slate-600">1 = hoàn toàn không đồng ý, 5 = hoàn toàn đồng ý.</p>
                <div className="mt-5 space-y-5">
                  {surveyStatements.map((statement, index) => (
                    <fieldset key={statement}>
                      <legend className="text-sm font-medium text-slate-800">{index + 1}. {statement}</legend>
                      <div className="mt-2 flex gap-4">
                        {[1, 2, 3, 4, 5].map((value) => <label key={value} className="flex items-center gap-1 text-sm"><input type="radio" name={`likert-${index}`} checked={likert[index] === value} onChange={() => setLikert((current) => current.map((item, itemIndex) => itemIndex === index ? value : item))} />{value}</label>)}
                      </div>
                    </fieldset>
                  ))}
                  <label className="block text-sm font-medium text-slate-800">Điều hữu ích nhất<textarea value={usefulFeedback} onChange={(event) => setUsefulFeedback(event.target.value)} className="mt-2 min-h-24 w-full rounded-lg border border-slate-300 p-3 font-normal" maxLength={2000} /></label>
                  <label className="block text-sm font-medium text-slate-800">Điều cần cải thiện<textarea value={improvementFeedback} onChange={(event) => setImprovementFeedback(event.target.value)} className="mt-2 min-h-24 w-full rounded-lg border border-slate-300 p-3 font-normal" maxLength={2000} /></label>
                  <button disabled={busy} onClick={submitSurvey} className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-50">{busy ? 'Đang gửi...' : 'Hoàn thành khảo sát'}</button>
                </div>
              </section>
            )}

            {progress.survey_completed && <section className="rounded-lg border border-emerald-200 bg-emerald-50 p-5 text-sm font-medium text-emerald-800">Bạn đã hoàn thành toàn bộ quy trình nghiên cứu. Cảm ơn bạn đã tham gia.</section>}
          </div>
        )}
      </div>
    </main>
  );
}
