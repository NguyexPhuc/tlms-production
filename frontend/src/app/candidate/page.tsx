'use client';

import { useAuth } from '@/contexts/AuthContext';
import { apiClient } from '@/lib/api';
import { DailyQuest, DailyQuestLimitResponse, DailyQuestListResponse } from '@/types/quest';
import { Task, UserTask } from '@/types/task';
import { CheckCircle2, ChevronRight, FileCheck2, Image as ImageIcon, Link2, ListChecks, Sparkles, Target, X } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';

type ActiveTab = 'daily-quest' | 'limit-quest' | 'available' | 'my-tasks';

type QuestProofFormState = {
  proofText: string;
  proofLink: string;
  proofImage: File | null;
};

const EMPTY_PROOF_FORM: QuestProofFormState = {
  proofText: '',
  proofLink: '',
  proofImage: null,
};

const DIFFICULTY_COLORS: Record<string, string> = {
  easy: 'bg-emerald-100 text-emerald-700',
  medium: 'bg-amber-100 text-amber-700',
  hard: 'bg-orange-100 text-orange-700',
  advanced: 'bg-purple-100 text-purple-700',
  expert: 'bg-red-100 text-red-700',
};

const STATUS_COLORS: Record<string, string> = {
  available: 'bg-slate-100 text-slate-700',
  in_progress: 'bg-blue-100 text-blue-700',
  submitted: 'bg-violet-100 text-violet-700',
  ai_reviewed: 'bg-violet-100 text-violet-700',
  late: 'bg-orange-100 text-orange-700',
  missed: 'bg-red-100 text-red-700',
  approved: 'bg-emerald-100 text-emerald-700',
  completed: 'bg-emerald-100 text-emerald-700',
  rejected: 'bg-red-100 text-red-700',
  locked: 'bg-slate-100 text-slate-500',
};

const TASK_STATUS_LABELS: Record<string, string> = {
  available: 'Có thể làm',
  in_progress: 'Đang làm',
  submitted: 'Đã nộp',
  ai_reviewed: 'AI đã chấm',
  late: 'Nộp muộn',
  missed: 'Quá hạn',
  approved: 'Đã duyệt',
  completed: 'Hoàn thành',
  rejected: 'Chưa đạt',
  locked: 'Khóa',
};

const QUEST_STATUS_COLORS: Record<string, string> = {
  pending: 'bg-slate-100 text-slate-700',
  in_progress: 'bg-blue-100 text-blue-700',
  submitted: 'bg-violet-100 text-violet-700',
  ai_reviewed: 'bg-violet-100 text-violet-700',
  completed: 'bg-emerald-100 text-emerald-700',
  rejected: 'bg-red-100 text-red-700',
  expired: 'bg-red-100 text-red-700',
};

const QUEST_STATUS_LABELS: Record<string, string> = {
  pending: 'Chờ nộp',
  in_progress: 'Đang làm',
  submitted: 'Đã nộp',
  ai_reviewed: 'AI đã chấm',
  completed: 'Hoàn thành',
  rejected: 'Cần bổ sung',
  expired: 'Hết hạn',
};

const QUEST_DIFFICULTY_LABELS: Record<string, string> = {
  easy: 'Dễ',
  medium: 'Vừa',
  hard: 'Khó',
};

const getFallbackResetAt = (timestamp: number) => {
  const resetAt = new Date(timestamp);
  resetAt.setHours(24, 0, 0, 0);
  return resetAt.toISOString();
};

const formatDateTime = (value?: string | null) => {
  if (!value) return '-';
  return new Date(value).toLocaleString('vi-VN');
};

type QuestDetailSection = {
  kind: 'objective' | 'steps' | 'evidence' | 'criteria';
  title: string;
  content: string;
};

const QUEST_SECTION_MATCHERS = [
  { kind: 'objective' as const, title: 'Bạn cần làm gì?', pattern: /^Mục tiêu:\s*(.*)$/i },
  { kind: 'steps' as const, title: 'Các bước thực hiện', pattern: /^Các bước thực hiện:\s*(.*)$/i },
  { kind: 'evidence' as const, title: 'Minh chứng cần nộp', pattern: /^Minh chứng cần nộp:\s*(.*)$/i },
  { kind: 'criteria' as const, title: 'Khi nào được tính hoàn thành?', pattern: /^Tiêu chí hoàn thành:\s*(.*)$/i },
];

const parseQuestDetails = (description: string): QuestDetailSection[] => {
  const lines = description.split('\n').map((line) => line.trim()).filter(Boolean);
  const sections: QuestDetailSection[] = [];
  let current: QuestDetailSection | null = null;

  lines.forEach((line) => {
    const matcher = QUEST_SECTION_MATCHERS.find((item) => item.pattern.test(line));
    if (matcher) {
      const inlineContent = line.match(matcher.pattern)?.[1]?.trim() || '';
      current = { kind: matcher.kind, title: matcher.title, content: inlineContent };
      sections.push(current);
      return;
    }

    if (current) {
      current.content = current.content ? `${current.content}\n${line}` : line;
    }
  });

  if (sections.length > 0) return sections.filter((section) => section.content);

  return [
    { kind: 'objective', title: 'Bạn cần làm gì?', content: description },
    {
      kind: 'steps',
      title: 'Các bước thực hiện',
      content: '1. Đọc kỹ yêu cầu và xác định kết quả cần tạo.\n2. Thực hiện nhiệm vụ trên môi trường học tập của bạn.\n3. Kiểm tra kết quả trước khi nộp.',
    },
    {
      kind: 'evidence',
      title: 'Minh chứng cần nộp',
      content: 'Viết 2-3 câu nêu bạn đã làm gì và kết quả ra sao. Đính kèm link hoặc ảnh nếu có.',
    },
    {
      kind: 'criteria',
      title: 'Khi nào được tính hoàn thành?',
      content: 'Minh chứng phải liên quan trực tiếp đến yêu cầu và đủ rõ để AI kiểm tra.',
    },
  ];
};

const getQuestSummary = (description: string) => {
  const objective = parseQuestDetails(description).find((section) => section.kind === 'objective');
  return objective?.content || description;
};

export default function CandidateDashboard() {
  const { user, isLoading, refreshUser, updateUser } = useAuth();
  const router = useRouter();
  const [availableTasks, setAvailableTasks] = useState<Task[]>([]);
  const [myTasks, setMyTasks] = useState<UserTask[]>([]);
  const [dailyQuests, setDailyQuests] = useState<DailyQuest[]>([]);
  const [limitQuests, setLimitQuests] = useState<DailyQuest[]>([]);
  const [questLimit, setQuestLimit] = useState<DailyQuestLimitResponse | null>(null);
  const [proofForms, setProofForms] = useState<Record<string, QuestProofFormState>>({});
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<ActiveTab>('daily-quest');
  const [submittingQuestId, setSubmittingQuestId] = useState<string | null>(null);
  const [selectedQuest, setSelectedQuest] = useState<DailyQuest | null>(null);
  const [now, setNow] = useState<number | null>(null);
  const [questStats, setQuestStats] = useState<{ xp: number; level: number } | null>(null);
  const isLearningAccount = Boolean(user?.roles?.includes('candidate') || user?.roles?.includes('member'));
  const canUseAdmin = Boolean(user?.roles?.includes('admin') && !isLearningAccount);
  const canUseMentor = Boolean((user?.roles?.includes('mentor') || user?.roles?.includes('admin')) && !isLearningAccount);
  const displayXp = questStats?.xp ?? user?.current_xp ?? 0;
  const displayLevel = questStats?.level ?? (
    isLearningAccount
      ? Math.max(1, Math.floor((user?.current_xp || 0) / 100) + 1)
      : user?.level || 1
  );

  const applyQuestPayload = useCallback((payload: DailyQuestListResponse) => {
    setDailyQuests(payload.quests);
    setQuestLimit({
      max_quests: payload.max_quests,
      generated_count: payload.total,
      active_count: payload.active_count,
      completed_count: payload.completed_count,
      expired_count: payload.expired_count,
      remaining_generation_slots: Math.max(0, payload.max_quests - payload.total),
      reset_at: payload.reset_at,
    });
  }, []);

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [availableResult, myTasksResult, questsResult, limitResult] = await Promise.allSettled([
        apiClient.getAvailableTasks(),
        apiClient.getMyTasks(),
        apiClient.getDailyQuests(),
        apiClient.getLimitQuests(),
      ]);

      if (availableResult.status === 'fulfilled') {
        setAvailableTasks(availableResult.value.tasks);
      } else {
        console.error('Failed to load available tasks:', availableResult.reason);
        setAvailableTasks([]);
      }

      if (myTasksResult.status === 'fulfilled') {
        setMyTasks(myTasksResult.value.tasks);
      } else {
        console.error('Failed to load my tasks:', myTasksResult.reason);
        setMyTasks([]);
      }

      if (questsResult.status === 'fulfilled') {
        applyQuestPayload(questsResult.value);
      } else {
        console.error('Failed to load daily quests:', questsResult.reason);
        setDailyQuests([]);
        setQuestLimit(null);
      }

      if (limitResult.status === 'fulfilled') {
        setLimitQuests(limitResult.value.quests);
      } else {
        console.error('Failed to load limit quests:', limitResult.reason);
        setLimitQuests([]);
      }
    } finally {
      setLoading(false);
    }
  }, [applyQuestPayload]);

  useEffect(() => {
    if (!isLoading && !user) {
      router.push('/login');
      return;
    }

    if (user?.id) {
      void loadData();
    }
  }, [isLoading, user, router, loadData]);

  const handleStartTask = async (taskId: string) => {
    try {
      await apiClient.startTask({ task_id: taskId });
      await loadData();
      setActiveTab('my-tasks');
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Không thể bắt đầu task');
    }
  };

  const handleStartAssignedTask = async (userTaskId: string) => {
    try {
      await apiClient.startAssignedTask(userTaskId);
      await loadData();
      setActiveTab('my-tasks');
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Không thể bắt đầu task');
    }
  };

  const getQuestForm = (questId: string) => proofForms[questId] || EMPTY_PROOF_FORM;

  const updateQuestForm = (questId: string, patch: Partial<QuestProofFormState>) => {
    setProofForms((current) => ({
      ...current,
      [questId]: {
        ...(current[questId] || EMPTY_PROOF_FORM),
        ...patch,
      },
    }));
  };

  const handleSubmitQuestProof = async (quest: DailyQuest) => {
    const form = getQuestForm(quest.id);
    const hasProof = form.proofText.trim() || form.proofLink.trim() || form.proofImage || quest.proof_image_url;
    if (!hasProof) {
      alert('Vui lòng nộp minh chứng để AI chấm điểm');
      return;
    }
    if (quest.requires_image_proof && !form.proofImage && !quest.proof_image_url) {
      alert('Limit Quest cần ảnh minh chứng');
      return;
    }

    try {
      setSubmittingQuestId(quest.id);
      const result = await apiClient.submitQuestProof(quest.id, {
        proof_text: form.proofText.trim() || undefined,
        proof_link: form.proofLink.trim() || undefined,
        proof_image: form.proofImage,
      });

      setQuestStats({ xp: result.current_xp, level: result.level });
      updateUser({ current_xp: result.current_xp, level: result.level });

      if (result.quest.quest_type === 'limit') {
        setLimitQuests((current) => current.map((item) => (item.id === quest.id ? result.quest : item)));
      } else {
        setDailyQuests((current) => current.map((item) => (item.id === quest.id ? result.quest : item)));
        const questsData = await apiClient.getDailyQuests();
        applyQuestPayload(questsData);
      }

      setProofForms((current) => ({
        ...current,
        [quest.id]: EMPTY_PROOF_FORM,
      }));
      setSelectedQuest(result.quest);
      void refreshUser();
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Không thể nộp minh chứng quest');
    } finally {
      setSubmittingQuestId(null);
    }
  };

  if (isLoading || !user) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-gray-300 border-t-[#1E90FF] rounded-full animate-spin"></div>
      </div>
    );
  }

  const inProgressCount = myTasks.filter((task) => task.status === 'in_progress').length;
  const completedCount = myTasks.filter((task) => task.status === 'completed').length;
  const resetAt = questLimit?.reset_at || dailyQuests[0]?.expires_at || (now ? getFallbackResetAt(now) : null);
  const generatedQuestCount = questLimit?.generated_count ?? dailyQuests.length;
  const maxQuestCount = questLimit?.max_quests ?? 5;

  const formatCountdown = () => {
    if (!resetAt || now === null) return '--:--:--';
    const resetTime = new Date(resetAt).getTime();
    if (Number.isNaN(resetTime)) return '--:--:--';
    const diff = Math.max(0, resetTime - now);
    const hours = Math.floor(diff / 3600000);
    const minutes = Math.floor((diff % 3600000) / 60000);
    const seconds = Math.floor((diff % 60000) / 1000);
    return [hours, minutes, seconds].map((value) => value.toString().padStart(2, '0')).join(':');
  };

  const renderTabButton = (tab: ActiveTab, label: string, count: number) => (
    <button
      onClick={() => setActiveTab(tab)}
      className={`flex-1 sm:flex-none px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
        activeTab === tab
          ? 'border-[#1E90FF] text-[#1E90FF]'
          : 'border-transparent text-gray-500 hover:text-gray-700'
      }`}
    >
      {label} ({count})
    </button>
  );

  const renderQuestTile = (quest: DailyQuest) => (
    <button
      key={quest.id}
      type="button"
      onClick={() => setSelectedQuest(quest)}
      className="group relative aspect-square min-h-[210px] overflow-hidden rounded-lg border border-gray-200 bg-white p-4 pb-12 text-left hover:border-[#1E90FF]/70 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-[#1E90FF] transition-all"
    >
      <div className="h-full overflow-hidden pr-1">
        <div className="mb-3 flex items-start justify-between gap-2">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className={`px-2 py-0.5 text-xs font-medium rounded ${DIFFICULTY_COLORS[quest.difficulty]}`}>
              {QUEST_DIFFICULTY_LABELS[quest.difficulty]}
            </span>
            <span className={`px-2 py-0.5 text-xs font-medium rounded ${QUEST_STATUS_COLORS[quest.status]}`}>
              {QUEST_STATUS_LABELS[quest.status]}
            </span>
          </div>
          <ChevronRight className="h-4 w-4 flex-none text-gray-400 transition-transform group-hover:translate-x-0.5 group-hover:text-[#1E90FF]" />
        </div>
        <h3 className="line-clamp-2 text-base font-semibold text-gray-900">{quest.title}</h3>
        <p className="mt-2 line-clamp-4 text-sm leading-5 text-gray-600">{getQuestSummary(quest.description)}</p>
      </div>
      <div className="absolute inset-x-4 bottom-3 flex items-end justify-between gap-2 bg-white">
        <span className="text-sm font-semibold text-emerald-600">+{quest.xp_reward} XP</span>
        {quest.ai_score !== null && quest.ai_score !== undefined && (
          <span className="text-xs font-medium text-violet-700">{quest.ai_score.toFixed(0)}/100</span>
        )}
      </div>
    </button>
  );

  const renderQuestCard = (quest: DailyQuest) => {
    const canSubmit = quest.status === 'pending' || quest.status === 'in_progress' || quest.status === 'rejected';
    const isSubmitting = submittingQuestId === quest.id;
    const form = getQuestForm(quest.id);

    const detailSections = parseQuestDetails(quest.description);

    const sectionIcon = (kind: QuestDetailSection['kind']) => {
      if (kind === 'objective') return <Target className="h-5 w-5" />;
      if (kind === 'steps') return <ListChecks className="h-5 w-5" />;
      if (kind === 'evidence') return <FileCheck2 className="h-5 w-5" />;
      return <CheckCircle2 className="h-5 w-5" />;
    };

    return (
      <div key={quest.id} className="space-y-5">
        <div className="flex flex-wrap items-center gap-2 border-b border-gray-100 pb-4">
          <span className={`px-2 py-1 text-xs font-medium rounded ${DIFFICULTY_COLORS[quest.difficulty]}`}>
            {QUEST_DIFFICULTY_LABELS[quest.difficulty]}
          </span>
          <span className={`px-2 py-1 text-xs font-medium rounded ${QUEST_STATUS_COLORS[quest.status]}`}>
            {QUEST_STATUS_LABELS[quest.status]}
          </span>
          <span className="text-sm font-semibold text-emerald-600">+{quest.xp_reward} XP</span>
          <span className="text-xs text-gray-500">Cần đạt {quest.auto_pass_score}/100</span>
          <span className="ml-0 text-xs text-gray-500 sm:ml-auto">Hết hạn: {formatDateTime(quest.expires_at)}</span>
        </div>

        <div className="divide-y divide-gray-100 border-y border-gray-100">
          {detailSections.map((section) => (
            <section key={section.kind} className="grid gap-2 py-4 sm:grid-cols-[180px_1fr] sm:gap-5">
              <div className="flex items-center gap-2 font-medium text-gray-900">
                <span className="text-[#1E90FF]">{sectionIcon(section.kind)}</span>
                <h3 className="text-sm">{section.title}</h3>
              </div>
              <p className="whitespace-pre-line text-sm leading-6 text-gray-700">{section.content}</p>
            </section>
          ))}
        </div>

          {quest.ai_feedback && (
            <div className={`border-l-4 px-4 py-3 text-sm ${quest.status === 'rejected' ? 'border-red-400 bg-red-50 text-red-800' : 'border-violet-400 bg-violet-50 text-violet-800'}`}>
              <p className="font-semibold">{quest.status === 'rejected' ? 'AI nhận xét - bạn cần bổ sung' : 'AI nhận xét'}</p>
              <p className="mt-1 leading-5">{quest.ai_feedback}</p>
              {quest.ai_score !== null && quest.ai_score !== undefined && (
                <p className="mt-2 font-medium">Điểm hiện tại: {quest.ai_score.toFixed(1)}/100</p>
              )}
            </div>
          )}

          {quest.proof_link && (
            <a href={quest.proof_link} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 truncate text-sm text-[#1E90FF] hover:underline">
              <Link2 className="h-4 w-4 flex-none" />
              {quest.proof_link}
            </a>
          )}

          {quest.proof_image_url && (
            <button
              type="button"
              onClick={() => apiClient.viewQuestProof(quest.id, quest.proof_image_name || 'quest-proof')}
              className="flex items-center gap-2 text-sm text-[#1E90FF] hover:underline"
            >
              <ImageIcon className="h-4 w-4" />
              {quest.proof_image_name || 'Ảnh minh chứng'}
            </button>
          )}

          {canSubmit ? (
            <div className="grid gap-4 border-t border-gray-100 pt-5 md:grid-cols-[1fr_1fr]">
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-800">Ghi chú minh chứng</label>
                <textarea
                  value={form.proofText}
                  onChange={(event) => updateQuestForm(quest.id, { proofText: event.target.value })}
                  rows={5}
                  placeholder="Nêu rõ bạn đã làm gì, kết quả nhận được và cách bạn kiểm tra kết quả..."
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1E90FF] focus:border-[#1E90FF] text-sm"
                />
                <p className="mt-1 text-xs text-gray-500">Nên viết ít nhất 2-3 câu và bám sát phần minh chứng cần nộp.</p>
              </div>
              <div className="space-y-2">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-800">Link minh chứng</label>
                  <input
                    type="url"
                    value={form.proofLink}
                    onChange={(event) => updateQuestForm(quest.id, { proofLink: event.target.value })}
                    placeholder="https://..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1E90FF] focus:border-[#1E90FF] text-sm"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-800">
                    Ảnh minh chứng{quest.requires_image_proof ? ' *' : ''}
                  </label>
                  <input
                    type="file"
                    accept="image/*"
                    onChange={(event) => updateQuestForm(quest.id, { proofImage: event.target.files?.[0] || null })}
                    className="block w-full text-xs text-gray-600 file:mr-3 file:px-3 file:py-1.5 file:rounded-md file:border-0 file:bg-slate-100 file:text-slate-700"
                  />
                </div>
                <button
                  onClick={() => handleSubmitQuestProof(quest)}
                  disabled={isSubmitting}
                  className="mt-3 flex w-full items-center justify-center gap-2 rounded-lg bg-[#32CD32] px-4 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-[#22c55e] disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <Sparkles className="h-4 w-4" />
                  {isSubmitting ? 'AI đang chấm...' : quest.status === 'rejected' ? 'Nộp lại minh chứng' : 'Nộp minh chứng'}
                </button>
              </div>
            </div>
          ) : (
            <div className="text-sm text-gray-500">
              {quest.status === 'completed' ? 'Quest đã hoàn thành.' : quest.status === 'expired' ? 'Quest đã hết hạn.' : 'Minh chứng đang được xử lý.'}
            </div>
          )}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10 shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-semibold text-gray-900">Lộ trình học tập</h1>
              <p className="text-sm text-gray-500 mt-0.5">{user.full_name || user.email}</p>
            </div>
            <div className="flex items-center gap-2">
              {canUseAdmin && (
                <button
                  onClick={() => router.push('/admin/users')}
                  className="px-3 py-2 bg-[#9333ea] text-white rounded-lg hover:bg-[#7e22ce] text-sm font-medium transition-colors shadow-sm"
                >
                  Admin
                </button>
              )}
              {canUseMentor && (
                <button
                  onClick={() => router.push('/mentor')}
                  className="px-3 py-2 bg-[#1E90FF] text-white rounded-lg hover:bg-[#1a7de0] text-sm font-medium transition-colors shadow-sm"
                >
                  Mentor
                </button>
              )}
              <button
                onClick={() => router.push('/dashboard')}
                className="px-3 py-2 text-sm text-gray-600 hover:text-[#1E90FF] hover:bg-blue-50 rounded-lg transition-colors"
              >
                Quay lại
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-6 space-y-6">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Level</p>
            <p className="text-2xl font-semibold text-[#1E90FF] mt-1">{displayLevel}</p>
          </div>
          <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Tổng XP</p>
            <p className="text-2xl font-semibold text-[#9333ea] mt-1">{displayXp}</p>
          </div>
          <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Đang làm</p>
            <p className="text-2xl font-semibold text-[#FFA500] mt-1">{inProgressCount}</p>
          </div>
          <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Hoàn thành</p>
            <p className="text-2xl font-semibold text-[#32CD32] mt-1">{completedCount}</p>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
          <div className="border-b border-gray-200">
            <nav className="flex overflow-x-auto">
              {renderTabButton('daily-quest', 'Daily Quest', generatedQuestCount)}
              {renderTabButton('limit-quest', 'Limit Quest', limitQuests.length)}
              {renderTabButton('available', 'Có thể làm', availableTasks.length)}
              {renderTabButton('my-tasks', 'Tasks của tôi', myTasks.length)}
            </nav>
          </div>

          <div className="p-4 lg:p-6">
            {loading ? (
              <div className="text-center py-12 text-gray-500">Đang tải...</div>
            ) : activeTab === 'daily-quest' ? (
              <div className="space-y-4">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
                  <div>
                    <p className="text-sm font-medium text-slate-900">
                      Quest hôm nay: {generatedQuestCount}/{maxQuestCount}
                    </p>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Hoàn thành: {questLimit?.completed_count ?? dailyQuests.filter((quest) => quest.status === 'completed').length}
                    </p>
                  </div>
                  <div className="text-left md:text-right">
                    <p className="text-xs text-slate-500 uppercase tracking-wide">Reset sau</p>
                    <p className="text-lg font-semibold text-[#1E90FF] tabular-nums">{formatCountdown()}</p>
                  </div>
                </div>

                {dailyQuests.length === 0 ? (
                  <div className="text-center py-12 text-gray-500">Chưa có Daily Quest hôm nay</div>
                ) : (
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                    {dailyQuests.map(renderQuestTile)}
                  </div>
                )}
              </div>
            ) : activeTab === 'limit-quest' ? (
              <div className="space-y-4">
                <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
                  <p className="text-sm font-medium text-slate-900">Limit Quest: {limitQuests.length}</p>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Hoàn thành: {limitQuests.filter((quest) => quest.status === 'completed').length}
                  </p>
                </div>
                {limitQuests.length === 0 ? (
                  <div className="text-center py-12 text-gray-500">Chưa có Limit Quest được giao</div>
                ) : (
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                    {limitQuests.map(renderQuestTile)}
                  </div>
                )}
              </div>
            ) : activeTab === 'available' ? (
              <div className="space-y-4">
                {availableTasks.length === 0 ? (
                  <div className="text-center py-12 text-gray-500">Không có task nào khả dụng</div>
                ) : (
                  availableTasks.map((task) => (
                    <div key={task.id} className="border border-gray-200 rounded-lg p-4 hover:border-[#1E90FF]/50 hover:shadow-sm transition-all">
                      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                        <div className="flex-1 min-w-0">
                          <div className="flex flex-wrap items-center gap-2 mb-2">
                            <span className={`px-2 py-0.5 text-xs font-medium rounded ${
                              task.type === 'core' ? 'bg-red-100 text-red-700' : 'bg-[#1E90FF]/10 text-[#1E90FF]'
                            }`}>
                              {task.type === 'core' ? 'CORE' : 'BOUNTY'}
                            </span>
                            <span className={`px-2 py-0.5 text-xs font-medium rounded ${DIFFICULTY_COLORS[task.difficulty]}`}>
                              {task.difficulty.toUpperCase()}
                            </span>
                            <span className="text-xs text-gray-500">Level {task.min_level_required}+</span>
                          </div>
                          <h3 className="text-base font-medium text-gray-900 mb-1">{task.title}</h3>
                          <p className="text-sm text-gray-600 mb-3 line-clamp-2">{task.description}</p>
                          {task.skill_tags.length > 0 && (
                            <div className="flex flex-wrap gap-1.5 mb-3">
                              {task.skill_tags.slice(0, 4).map((skill, idx) => (
                                <span key={idx} className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded">
                                  {skill}
                                </span>
                              ))}
                              {task.skill_tags.length > 4 && (
                                <span className="text-xs text-gray-500">+{task.skill_tags.length - 4}</span>
                              )}
                            </div>
                          )}
                          <p className="text-sm font-medium text-[#32CD32]">+{task.xp_reward} XP</p>
                        </div>
                        <button
                          onClick={() => handleStartTask(task.id)}
                          className="w-full sm:w-auto px-4 py-2.5 bg-[#1E90FF] text-white rounded-lg hover:bg-[#1a7de0] text-sm font-medium transition-colors flex-shrink-0 shadow-sm"
                        >
                          Bắt đầu
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            ) : (
              <div className="space-y-4">
                {myTasks.length === 0 ? (
                  <div className="text-center py-12 text-gray-500">Bạn chưa có task nào</div>
                ) : (
                  myTasks.map((userTask) => (
                    <div key={userTask.id} className="border border-gray-200 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className={`px-2 py-0.5 text-xs font-medium rounded ${
                            userTask.task.type === 'core' ? 'bg-red-100 text-red-700' : 'bg-[#1E90FF]/10 text-[#1E90FF]'
                          }`}>
                            {userTask.task.type === 'core' ? 'CORE' : 'BOUNTY'}
                          </span>
                          <span className={`px-2 py-0.5 text-xs font-medium rounded ${STATUS_COLORS[userTask.status]}`}>
                            {TASK_STATUS_LABELS[userTask.status] || userTask.status}
                          </span>
                          {userTask.assigned_for_date && (
                            <span className="px-2 py-0.5 bg-slate-100 text-slate-700 text-xs font-medium rounded">
                              DAILY {new Date(userTask.assigned_for_date).toLocaleDateString('vi-VN')}
                            </span>
                          )}
                        </div>
                        <span className="text-xs text-emerald-600 font-medium">+{userTask.task.xp_reward} XP</span>
                      </div>
                      <h3 className="text-base font-medium text-gray-900 mb-1">{userTask.task.title}</h3>
                      <p className="text-sm text-gray-600 mb-3">{userTask.task.description}</p>
                      <div className="flex flex-wrap gap-3 text-xs text-gray-500 mb-3">
                        {userTask.deadline_at && <span>Deadline: {formatDateTime(userTask.deadline_at)}</span>}
                        {userTask.progress_percentage !== undefined && (
                          <span>Tiến độ: {userTask.progress_percentage.toFixed(0)}%</span>
                        )}
                        {userTask.ai_score !== null && userTask.ai_score !== undefined && (
                          <span>AI score: {userTask.ai_score.toFixed(1)}</span>
                        )}
                      </div>

                      {userTask.ai_feedback && (
                        <div className="rounded-lg bg-slate-50 border border-slate-200 px-3 py-2 text-sm text-slate-700 mb-3">
                          {userTask.ai_feedback}
                        </div>
                      )}

                      {userTask.status === 'available' && (
                        <button
                          onClick={() => handleStartAssignedTask(userTask.id)}
                          className="inline-block px-4 py-2 bg-[#1E90FF] text-white rounded-lg hover:bg-[#1a7de0] text-sm font-medium transition-colors shadow-sm"
                        >
                          Bắt đầu
                        </button>
                      )}

                      {userTask.status === 'in_progress' && (
                        <Link
                          href={`/candidate/tasks/${userTask.id}`}
                          className="inline-block px-4 py-2 bg-[#32CD32] text-white rounded-lg hover:bg-[#22c55e] text-sm font-medium transition-colors shadow-sm"
                        >
                          Nộp minh chứng
                        </Link>
                      )}

                      {userTask.status === 'submitted' && (
                        <div className="text-sm text-gray-600">Đã nộp: {formatDateTime(userTask.submitted_at)}</div>
                      )}

                      {userTask.status === 'completed' && (
                        <div className="text-sm text-[#32CD32] font-medium">Hoàn thành, +{userTask.xp_earned} XP</div>
                      )}

                      {userTask.status === 'rejected' && (
                        <div className="text-sm">
                          <p className="text-red-600 font-medium">Chưa đạt</p>
                          {userTask.mentor_comment && <p className="text-gray-600 mt-1">Nhận xét: {userTask.mentor_comment}</p>}
                          <Link
                            href={`/candidate/tasks/${userTask.id}`}
                            className="inline-block mt-2 px-4 py-2 bg-[#1E90FF] text-white rounded-lg hover:bg-[#1a7de0] text-sm font-medium transition-colors shadow-sm"
                          >
                            Nộp lại
                          </Link>
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </div>
      </main>

      {selectedQuest && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={() => setSelectedQuest(null)}>
          <div className="max-h-[92vh] w-full max-w-3xl overflow-y-auto rounded-lg border border-gray-200 bg-white shadow-xl" onClick={(event) => event.stopPropagation()}>
            <div className="sticky top-0 z-10 flex items-center justify-between border-b border-gray-100 bg-white px-5 py-4">
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
                  {selectedQuest.quest_type === 'limit' ? 'Limit Quest' : 'Daily Quest'}
                </p>
                <h2 className="mt-1 text-lg font-semibold text-gray-900">{selectedQuest.title}</h2>
              </div>
              <button
                onClick={() => setSelectedQuest(null)}
                aria-label="Đóng chi tiết quest"
                title="Đóng"
                className="flex h-9 w-9 items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100 hover:text-gray-900"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="p-5">
              {renderQuestCard(selectedQuest)}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
