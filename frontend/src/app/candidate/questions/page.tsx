'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';
import { MemberLevel } from '@/types';
import { Question, QuestionAnswer } from '@/types/question';
import { TaskCreatorType, TaskDifficulty } from '@/types/task';

const levelLabels: Record<MemberLevel, string> = {
  new: 'Thành viên mới',
  diligent: 'Thành viên chuyên cần',
  official: 'Thành viên chính thức',
};

export default function QuestionsPage() {
  const router = useRouter();
  const { user, isLoading, refreshUser } = useAuth();
  const [questions, setQuestions] = useState<Question[]>([]);
  const [answers, setAnswers] = useState<QuestionAnswer[]>([]);
  const [pendingAnswers, setPendingAnswers] = useState<QuestionAnswer[]>([]);
  const [selectedQuestion, setSelectedQuestion] = useState<Question | null>(null);
  const [answerText, setAnswerText] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [submissionError, setSubmissionError] = useState('');
  const [lastGradedAnswer, setLastGradedAnswer] = useState<QuestionAnswer | null>(null);
  const [createForm, setCreateForm] = useState({
    title: '',
    question: '',
    description: '',
    difficulty: 'medium' as TaskDifficulty,
    category: '',
    points: 10,
    expected_duration_minutes: 30,
    target_member_level: 'new' as MemberLevel,
    creator_type: 'manager' as TaskCreatorType,
    topic: '',
    skill_key: '',
    numeric_difficulty: 3,
    learning_objective: '',
    expected_answer: '',
  });

  const canManage = user?.roles?.includes('mentor') || user?.roles?.includes('admin');

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [questionData, answerData] = await Promise.all([
        apiClient.listQuestions(),
        apiClient.listQuestionAnswers(false),
      ]);
      setQuestions(questionData.questions);
      setAnswers(answerData);

      if (canManage) {
        const pending = await apiClient.listQuestionAnswers(true);
        setPendingAnswers(pending);
      }
    } catch (error) {
      console.error('Failed to load questions:', error);
    } finally {
      setLoading(false);
    }
  }, [canManage]);

  useEffect(() => {
    if (!isLoading && !user) {
      router.push('/login');
      return;
    }
    if (user) void loadData();
  }, [isLoading, user, router, loadData]);

  const submitAnswer = async () => {
    if (!selectedQuestion || !answerText.trim()) return;
    try {
      setSubmitting(true);
      setSubmissionError('');
      const gradedAnswer = await apiClient.submitQuestionAnswer(selectedQuestion.id, answerText.trim());
      setLastGradedAnswer(gradedAnswer);
      setSelectedQuestion(null);
      setAnswerText('');
      void refreshUser();
      await loadData();
    } catch (error: any) {
      setSubmissionError(error.response?.data?.detail || 'Không thể nộp câu trả lời. Vui lòng thử lại.');
    } finally {
      setSubmitting(false);
    }
  };

  const createQuestion = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      await apiClient.createQuestion({
        ...createForm,
        category: createForm.category || undefined,
        description: createForm.description || undefined,
        expected_answer: createForm.expected_answer || undefined,
      });
      setCreateForm({
        title: '',
        question: '',
        description: '',
        difficulty: 'medium',
        category: '',
        points: 10,
        expected_duration_minutes: 30,
        target_member_level: 'new',
        creator_type: 'manager' as TaskCreatorType,
        topic: '',
        skill_key: '',
        numeric_difficulty: 3,
        learning_objective: '',
        expected_answer: '',
      });
      await loadData();
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Không thể tạo question');
    } finally {
      setSubmitting(false);
    }
  };

  const reviewAnswer = async (answerId: string, approved: boolean) => {
    try {
      await apiClient.reviewQuestionAnswer(answerId, {
        status: approved ? 'approved' : 'rejected',
        manager_score: approved ? 90 : 40,
        feedback: approved ? 'Đạt yêu cầu.' : 'Cần bổ sung thêm nội dung.',
      });
      await loadData();
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Không thể review answer');
    }
  };

  if (isLoading || loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-gray-300 border-t-[#1E90FF] rounded-full animate-spin" />
      </div>
    );
  }

  const answerByQuestionId = new Map(answers.map((answer) => [answer.question_id, answer]));
  const baselineQuestions = questions.filter((question) => question.is_baseline);
  const unansweredBaselineCount = baselineQuestions.filter((question) => !answerByQuestionId.has(question.id)).length;
  const completedBaselineCount = baselineQuestions.length - unansweredBaselineCount;
  const scoreBreakdownLabels: Record<string, string> = {
    correctness: 'Độ đúng',
    understanding: 'Hiểu bài',
    reasoning: 'Lập luận',
    application: 'Áp dụng',
  };

  const renderAiResult = (answer: QuestionAnswer, elevated = false) => {
    if (answer.ai_score === null || answer.ai_score === undefined) return null;

    const breakdown = answer.ai_breakdown ?? {};
    const numericBreakdown = Object.entries(breakdown).filter(
      (entry): entry is [string, number] => typeof entry[1] === 'number'
    );
    const strengths = Array.isArray(breakdown.strengths)
      ? breakdown.strengths.filter((item): item is string => typeof item === 'string')
      : [];
    const missing = Array.isArray(breakdown.missing)
      ? breakdown.missing.filter((item): item is string => typeof item === 'string')
      : [];
    const scoreColor = answer.ai_score >= 80 ? 'text-[#32CD32]' : answer.ai_score >= 60 ? 'text-[#FFA500]' : 'text-red-600';
    const cardClass = elevated
      ? 'rounded-xl border border-[#1E90FF]/20 bg-blue-50/60 p-4 shadow-sm'
      : 'mt-3 rounded-lg border border-violet-100 bg-violet-50 p-3 text-sm';

    return (
      <div className={cardClass}>
        <div className="flex flex-wrap items-center gap-3">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-gray-500">AI score</p>
            <p className={`text-2xl font-semibold ${scoreColor}`}>{answer.ai_score.toFixed(1)}/100</p>
          </div>
          <div className="rounded-lg bg-white/80 px-3 py-2">
            <p className="text-xs font-medium uppercase tracking-wide text-gray-500">XP nhận</p>
            <p className="text-lg font-semibold text-[#9333ea]">+{answer.points_awarded}</p>
          </div>
          {answer.ai_confidence !== null && answer.ai_confidence !== undefined && (
            <div className="rounded-lg bg-white/80 px-3 py-2">
              <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Tin cậy</p>
              <p className="text-lg font-semibold text-gray-900">{(answer.ai_confidence * 100).toFixed(0)}%</p>
            </div>
          )}
          <span className="rounded bg-white px-2 py-1 text-xs font-medium text-violet-700">{answer.status}</span>
        </div>

        {answer.ai_feedback && <p className="mt-3 text-sm text-gray-700">{answer.ai_feedback}</p>}

        {numericBreakdown.length > 0 && (
          <div className="mt-3 grid grid-cols-2 gap-2 lg:grid-cols-4">
            {numericBreakdown.map(([key, value]) => (
              <div key={key} className="rounded-lg bg-white/80 p-2">
                <div className="flex items-center justify-between text-[11px] text-gray-500">
                  <span>{scoreBreakdownLabels[key] || key}</span>
                  <span>{value.toFixed(0)}</span>
                </div>
                <div className="mt-1 h-1.5 rounded-full bg-gray-100">
                  <div
                    className="h-1.5 rounded-full bg-gradient-to-r from-[#1E90FF] to-[#9333ea]"
                    style={{ width: `${Math.min(Math.max(value, 0), 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        )}

        {(strengths.length > 0 || missing.length > 0) && (
          <div className="mt-3 grid grid-cols-1 gap-2 md:grid-cols-2">
            {strengths.length > 0 && (
              <div className="rounded-lg bg-white/80 p-2">
                <p className="text-xs font-semibold text-[#32CD32]">Điểm tốt</p>
                <p className="mt-1 text-xs text-gray-600">{strengths.join(', ')}</p>
              </div>
            )}
            {missing.length > 0 && (
              <div className="rounded-lg bg-white/80 p-2">
                <p className="text-xs font-semibold text-[#FFA500]">Cần bổ sung</p>
                <p className="mt-1 text-xs text-gray-600">{missing.join(', ')}</p>
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10 shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h1 className="text-xl font-semibold text-gray-900">Questions</h1>
              <p className="text-sm text-gray-500 mt-0.5">
                {user?.member_level ? levelLabels[user.member_level] : 'Thành viên'}
              </p>
            </div>
            <Link href="/dashboard" className="px-3 py-2 text-sm text-gray-600 hover:text-[#1E90FF] hover:bg-blue-50 rounded-lg">
              Quay lại
            </Link>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-6 space-y-6">
        {lastGradedAnswer && (
          <section className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div>
                <h2 className="font-semibold text-gray-900">
                  {lastGradedAnswer.question?.question_type === 'multiple_choice' ? 'Kết quả vừa chấm' : 'Kết quả AI vừa chấm'}
                </h2>
                <p className="text-sm text-gray-500 mt-0.5">
                  {lastGradedAnswer.question?.title || 'Câu trả lời mới nhất'}
                </p>
              </div>
              <button
                onClick={() => setLastGradedAnswer(null)}
                className="rounded-lg px-3 py-1.5 text-sm text-gray-500 hover:bg-gray-100"
              >
                Ẩn
              </button>
            </div>
            {renderAiResult(lastGradedAnswer, true)}
          </section>
        )}

        {canManage && (
          <section className="bg-white rounded-xl border border-gray-200 shadow-sm">
            <div className="px-5 py-4 border-b border-gray-100">
              <h2 className="font-semibold text-gray-900">Tạo Question</h2>
            </div>
            <form onSubmit={createQuestion} className="p-5 grid grid-cols-1 lg:grid-cols-2 gap-4">
              <input
                required
                value={createForm.title}
                onChange={(e) => setCreateForm({ ...createForm, title: e.target.value })}
                placeholder="Tiêu đề"
                className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
              />
              <select
                value={createForm.target_member_level}
                onChange={(e) => setCreateForm({ ...createForm, target_member_level: e.target.value as MemberLevel })}
                className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
              >
                {Object.entries(levelLabels).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
              <textarea
                required
                value={createForm.question}
                onChange={(e) => setCreateForm({ ...createForm, question: e.target.value })}
                placeholder="Nội dung câu hỏi"
                className="lg:col-span-2 px-3 py-2 border border-gray-300 rounded-lg text-sm"
                rows={3}
              />
              <input
                value={createForm.category}
                onChange={(e) => setCreateForm({ ...createForm, category: e.target.value })}
                placeholder="Category"
                className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
              />
              <input
                value={createForm.skill_key}
                onChange={(e) => setCreateForm({ ...createForm, skill_key: e.target.value })}
                placeholder="Skill key: backend, database, frontend..."
                className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
              />
              <input
                value={createForm.topic}
                onChange={(e) => setCreateForm({ ...createForm, topic: e.target.value })}
                placeholder="Topic"
                className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
              />
              <select
                value={createForm.difficulty}
                onChange={(e) => setCreateForm({ ...createForm, difficulty: e.target.value as TaskDifficulty })}
                className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
              >
                <option value="easy">Easy</option>
                <option value="medium">Medium</option>
                <option value="hard">Hard</option>
                <option value="advanced">Advanced</option>
                <option value="expert">Expert</option>
              </select>
              <input
                type="number"
                min={1}
                max={10}
                step={0.5}
                value={createForm.numeric_difficulty}
                onChange={(e) => setCreateForm({ ...createForm, numeric_difficulty: Number(e.target.value) })}
                placeholder="Độ khó 1-10"
                className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
              />
              <textarea
                value={createForm.learning_objective}
                onChange={(e) => setCreateForm({ ...createForm, learning_objective: e.target.value })}
                placeholder="Learning objective"
                className="lg:col-span-2 px-3 py-2 border border-gray-300 rounded-lg text-sm"
                rows={2}
              />
              <textarea
                value={createForm.expected_answer}
                onChange={(e) => setCreateForm({ ...createForm, expected_answer: e.target.value })}
                placeholder="Đáp án kỳ vọng"
                className="lg:col-span-2 px-3 py-2 border border-gray-300 rounded-lg text-sm"
                rows={3}
              />
              <button
                disabled={submitting}
                className="lg:col-span-2 px-4 py-2 bg-[#1E90FF] text-white rounded-lg hover:bg-[#1a7de0] text-sm font-medium disabled:opacity-50"
              >
                {submitting ? 'Đang lưu' : 'Tạo Question'}
              </button>
            </form>
          </section>
        )}

        <section className="bg-white rounded-xl border border-gray-200 shadow-sm">
          <div className="px-5 py-4 border-b border-gray-100">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <h2 className="font-semibold text-gray-900">
                  {unansweredBaselineCount > 0 ? 'Bài đánh giá tư duy CNTT' : 'Question được cá nhân hóa'}
                </h2>
                <p className="text-sm text-gray-500 mt-1">
                  {unansweredBaselineCount > 0
                    ? 'Hoàn thành 5 câu trắc nghiệm để hệ thống phân hóa câu hỏi tiếp theo.'
                    : 'Danh sách đã được sắp xếp theo skill profile và độ khó hiện tại của bạn.'}
                </p>
              </div>
              {unansweredBaselineCount > 0 && (
                <span className="px-3 py-1 bg-[#1E90FF]/10 text-[#1E90FF] rounded-full text-xs font-medium">
                  Đã làm {completedBaselineCount}/{baselineQuestions.length}
                </span>
              )}
            </div>
          </div>
          <div className="divide-y divide-gray-100">
            {questions.length === 0 ? (
              <div className="p-8 text-center text-sm text-gray-500">Chưa có question phù hợp.</div>
            ) : (
              questions.map((question) => {
                const answer = answerByQuestionId.get(question.id);
                return (
                  <div key={question.id} className="p-5">
                    <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-3">
                      <div>
                        <div className="flex flex-wrap gap-2 mb-2">
                          {question.is_baseline && (
                            <span className="px-2 py-0.5 text-xs font-medium rounded bg-[#1E90FF]/10 text-[#1E90FF]">Baseline</span>
                          )}
                          <span className="px-2 py-0.5 text-xs font-medium rounded bg-slate-100 text-slate-700">{question.difficulty}</span>
                          {question.skill_key && (
                            <span className="px-2 py-0.5 text-xs font-medium rounded bg-violet-100 text-violet-700">{question.skill_key}</span>
                          )}
                          <span className="px-2 py-0.5 text-xs font-medium rounded bg-gray-100 text-gray-700">Độ khó {question.numeric_difficulty}/10</span>
                          <span className="px-2 py-0.5 text-xs font-medium rounded bg-emerald-100 text-emerald-700">+{question.points} điểm</span>
                          {answer && (
                            <span className="px-2 py-0.5 text-xs font-medium rounded bg-violet-100 text-violet-700">{answer.status}</span>
                          )}
                        </div>
                        <h3 className="font-medium text-gray-900">{question.title}</h3>
                        {question.learning_objective && (
                          <p className="text-xs text-gray-500 mt-1">{question.learning_objective}</p>
                        )}
                        <p className="text-sm text-gray-600 mt-1 whitespace-pre-wrap">{question.question}</p>
                        {answer && renderAiResult(answer)}
                      </div>
                      <button
                        onClick={() => {
                          setSelectedQuestion(question);
                          setAnswerText(
                            question.question_type === 'multiple_choice'
                              ? answer?.answer?.trim().charAt(0).toUpperCase() || ''
                              : answer?.answer || ''
                          );
                          setSubmissionError('');
                        }}
                        className="px-4 py-2 bg-[#1E90FF] text-white rounded-lg hover:bg-[#1a7de0] text-sm font-medium"
                      >
                        {answer ? 'Cập nhật answer' : 'Trả lời'}
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </section>

        {canManage && pendingAnswers.length > 0 && (
          <section className="bg-white rounded-xl border border-gray-200 shadow-sm">
            <div className="px-5 py-4 border-b border-gray-100">
              <h2 className="font-semibold text-gray-900">Answer chờ review</h2>
            </div>
            <div className="divide-y divide-gray-100">
              {pendingAnswers.map((answer) => (
                <div key={answer.id} className="p-5">
                  <p className="font-medium text-gray-900">{answer.question?.title || answer.question_id}</p>
                  <p className="text-sm text-gray-600 mt-2 whitespace-pre-wrap">{answer.answer}</p>
                  {answer.ai_score !== null && answer.ai_score !== undefined && (
                    <p className="text-sm text-violet-700 mt-2">AI score: {answer.ai_score.toFixed(1)}/100</p>
                  )}
                  <div className="flex gap-2 mt-3">
                    <button onClick={() => reviewAnswer(answer.id, true)} className="px-4 py-2 bg-[#32CD32] text-white rounded-lg text-sm font-medium">
                      Duyệt
                    </button>
                    <button onClick={() => reviewAnswer(answer.id, false)} className="px-4 py-2 bg-red-500 text-white rounded-lg text-sm font-medium">
                      Từ chối
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}
      </main>

      {selectedQuestion && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" onClick={() => setSelectedQuestion(null)}>
          <div className="bg-white rounded-xl max-w-2xl w-full border border-gray-200 shadow-xl" onClick={(e) => e.stopPropagation()}>
            <div className="px-5 py-4 border-b border-gray-100">
              <h2 className="font-semibold text-gray-900">{selectedQuestion.title}</h2>
              <p className="text-sm text-gray-600 mt-1">{selectedQuestion.question}</p>
              <div className="flex flex-wrap gap-2 mt-3">
                {selectedQuestion.skill_key && (
                  <span className="px-2 py-0.5 text-xs font-medium rounded bg-violet-100 text-violet-700">{selectedQuestion.skill_key}</span>
                )}
                <span className="px-2 py-0.5 text-xs font-medium rounded bg-gray-100 text-gray-700">
                  Độ khó {selectedQuestion.numeric_difficulty}/10
                </span>
                <span className="px-2 py-0.5 text-xs font-medium rounded bg-emerald-100 text-emerald-700">
                  +{selectedQuestion.points} điểm
                </span>
              </div>
            </div>
            <div className="p-5">
              {selectedQuestion.question_type === 'multiple_choice' && selectedQuestion.options ? (
                <div className="grid gap-3" role="radiogroup" aria-label="Chọn đáp án">
                  {Object.entries(selectedQuestion.options).map(([key, value]) => {
                    const selected = answerText === key;
                    return (
                      <button
                        key={key}
                        type="button"
                        role="radio"
                        aria-checked={selected}
                        onClick={() => {
                          setAnswerText(key);
                          setSubmissionError('');
                        }}
                        className={`flex min-h-14 items-center gap-3 rounded-lg border px-4 py-3 text-left text-sm transition-colors ${
                          selected
                            ? 'border-[#1E90FF] bg-blue-50 text-blue-900 ring-1 ring-[#1E90FF]'
                            : 'border-gray-200 bg-white text-gray-700 hover:border-blue-300 hover:bg-blue-50/50'
                        }`}
                      >
                        <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full font-semibold ${selected ? 'bg-[#1E90FF] text-white' : 'bg-gray-100 text-gray-700'}`}>
                          {key}
                        </span>
                        <span>{value}</span>
                      </button>
                    );
                  })}
                </div>
              ) : (
                <textarea
                  value={answerText}
                  onChange={(e) => {
                    setAnswerText(e.target.value);
                    setSubmissionError('');
                  }}
                  rows={8}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-[#1E90FF] focus:border-[#1E90FF]"
                />
              )}
              {submissionError && (
                <p className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
                  {submissionError}
                </p>
              )}
              <div className="flex justify-end gap-2 mt-4">
                <button onClick={() => setSelectedQuestion(null)} className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm">
                  Hủy
                </button>
                <button onClick={submitAnswer} disabled={submitting || !answerText.trim()} className="px-4 py-2 bg-[#1E90FF] text-white rounded-lg text-sm font-medium disabled:cursor-not-allowed disabled:opacity-50">
                  {submitting ? 'Đang nộp' : selectedQuestion.question_type === 'multiple_choice' ? 'Nộp đáp án' : 'Nộp answer'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
