'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api';
import { TaskCreatorType, TaskScope, TaskType, TaskDifficulty } from '@/types/task';
import { DailyQuestDifficulty } from '@/types/quest';
import Link from 'next/link';
import { MemberLevel, User } from '@/types';
import { useAuth } from '@/contexts/AuthContext';

type CreateItemKind = 'core' | 'bounty' | 'available_quest' | 'limit_quest';

const toDailyQuestDifficulty = (difficulty: TaskDifficulty): DailyQuestDifficulty => {
  if (difficulty === 'easy' || difficulty === 'medium' || difficulty === 'hard') {
    return difficulty;
  }
  return 'hard';
};

export default function CreateTaskPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [formError, setFormError] = useState('');
  const [users, setUsers] = useState<User[]>([]);
  
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    creation_kind: 'core' as CreateItemKind,
    type: 'core' as TaskType,
    scope: 'mandatory' as TaskScope,
    difficulty: 'medium' as TaskDifficulty,
    min_level_required: 1,
    xp_reward: 100,
    skill_tags: '',
    max_participants: '',
    assignee_ids: [] as string[],
    instructions: '',
    reference_links: '',
    deadline: '',
    estimated_duration_minutes: 60,
    creator_type: 'manager' as TaskCreatorType,
    target_member_level: 'new' as MemberLevel,
    requires_manager_review: true
  });

  const loadUsers = useCallback(async () => {
    try {
      const res = await apiClient.getUsers({ page_size: 100 });
      setUsers(res.users || []);
    } catch (error) {
      console.error('Failed to load users', error);
      // Fail silently if not admin, or just empty list
    }
  }, []);

  useEffect(() => {
    void loadUsers();
  }, [loadUsers]);

  const isAdmin = Boolean(user?.roles?.includes('admin'));
  const isLimitQuest = formData.creation_kind === 'limit_quest';
  const isAvailableQuest = formData.creation_kind === 'available_quest';
  const assigneeUsers = users.filter((candidate) =>
    candidate.roles?.some((role) => role === 'candidate' || role === 'member') ||
    candidate.primary_role === 'candidate' ||
    candidate.primary_role === 'member'
  );

  const handleCreationKindChange = (creationKind: CreateItemKind) => {
    setFormData((prev) => {
      const nextDifficulty =
        creationKind === 'limit_quest' && (prev.difficulty === 'advanced' || prev.difficulty === 'expert')
          ? 'hard'
          : prev.difficulty;

      return {
        ...prev,
        creation_kind: creationKind,
        type: creationKind === 'core' ? 'core' : 'bounty',
        scope:
          creationKind === 'core'
            ? 'mandatory'
            : creationKind === 'available_quest'
              ? 'opt_in'
              : creationKind === 'limit_quest'
                ? 'private'
                : prev.scope,
        difficulty: nextDifficulty as TaskDifficulty,
        assignee_ids: creationKind === 'limit_quest' ? [] : prev.assignee_ids,
        requires_manager_review: creationKind === 'limit_quest' ? false : prev.requires_manager_review,
      };
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setFormError('');

    try {
      if (isLimitQuest) {
        if (!isAdmin) {
          setFormError('Chỉ admin mới được tạo Limit Quest.');
          return;
        }
        if (formData.assignee_ids.length === 0) {
          setFormError('Vui lòng chọn ít nhất một thực tập sinh hoặc thành viên.');
          return;
        }

        await apiClient.createLimitQuest({
          target_user_ids: formData.assignee_ids,
          title: formData.title,
          description: formData.description,
          difficulty: toDailyQuestDifficulty(formData.difficulty),
          xp_reward: formData.xp_reward,
          expires_at: formData.deadline || undefined,
          auto_pass_score: 70,
        });
        router.push('/dashboard');
        return;
      }

      const resolvedScope = isAvailableQuest ? 'opt_in' : formData.scope;
      if (resolvedScope === 'private' && formData.assignee_ids.length === 0) {
        setFormError('Vui lòng chọn ít nhất một người nhận nhiệm vụ riêng.');
        return;
      }
      const payload = {
        title: formData.title,
        description: formData.description,
        type: formData.type,
        scope: resolvedScope,
        difficulty: formData.difficulty,
        min_level_required: formData.min_level_required,
        xp_reward: formData.xp_reward,
        skill_tags: formData.skill_tags.split(',').map(t => t.trim()).filter(Boolean),
        reference_links: formData.reference_links.split('\n').map(l => l.trim()).filter(Boolean),
        max_participants: resolvedScope === 'opt_in' && formData.max_participants ? parseInt(formData.max_participants) : undefined,
        assignee_ids: resolvedScope === 'private' ? formData.assignee_ids : [],
        instructions: formData.instructions,
        deadline: formData.deadline || undefined,
        estimated_duration_minutes: formData.estimated_duration_minutes,
        creator_type: formData.creator_type,
        target_member_level: formData.target_member_level,
        requires_manager_review: formData.requires_manager_review,
      };

      await apiClient.createTask(payload);
      router.push('/mentor');
    } catch (error: unknown) {
      console.error(error);
      const message =
        error && typeof error === 'object' && 'response' in error
          ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined;
      setFormError(message || 'Tạo nhiệm vụ thất bại. Vui lòng kiểm tra lại thông tin.');
    } finally {
      setLoading(false);
    }
  };

  const toggleAssignee = (userId: string) => {
    setFormData(prev => {
      const current = prev.assignee_ids;
      if (current.includes(userId)) {
        return { ...prev, assignee_ids: current.filter(id => id !== userId) };
      } else {
        return { ...prev, assignee_ids: [...current, userId] };
      }
    });
  };

  return (
    <div className="min-h-screen bg-slate-50 py-8">
      <div className="max-w-3xl mx-auto px-4">
        <div className="mb-6 flex items-center justify-between">
            <h1 className="text-2xl font-bold text-slate-900">Tạo nhiệm vụ mới</h1>
            <Link href="/mentor" className="text-gray-600 hover:text-blue-600 transition-colors">
                Hủy
            </Link>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <form onSubmit={handleSubmit} className="space-y-6">
            {formError && <div role="alert" className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{formError}</div>}
            
            {/* Basic Info */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-semibold text-gray-700 mb-1">Tiêu đề</label>
                        <input
                            type="text"
                            required
                            className="w-full border border-gray-200 rounded-xl px-4 py-3 focus:ring-2 focus:ring-violet-500 focus:border-violet-500 bg-gray-50/50 hover:bg-white transition-all"
                            value={formData.title}
                            onChange={e => setFormData({...formData, title: e.target.value})}
                        />
                    </div>
                </div>

                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-semibold text-gray-700 mb-1">Loại Task</label>
                        <select
                            className="w-full border border-gray-200 rounded-xl px-4 py-3 focus:ring-2 focus:ring-violet-500 focus:border-violet-500 bg-gray-50/50 hover:bg-white transition-all"
                            value={formData.creation_kind}
                            onChange={e => handleCreationKindChange(e.target.value as CreateItemKind)}
                        >
                            <option value="core">Core Task (Bắt buộc)</option>
                            <option value="bounty">Bounty Task (Thử thách)</option>
                            <option value="available_quest">Quest có thể làm</option>
                            {isAdmin && <option value="limit_quest">Limit Quest (Admin)</option>}
                        </select>
                    </div>
                </div>
            </div>

            <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1">Mô tả</label>
                <textarea
                    required
                    rows={3}
                    className="w-full border border-gray-200 rounded-xl px-4 py-3 focus:ring-2 focus:ring-violet-500 focus:border-violet-500 bg-gray-50/50 hover:bg-white transition-all"
                    value={formData.description}
                    onChange={e => setFormData({...formData, description: e.target.value})}
                />
            </div>

            {/* Scope Configuration */}
            <div className="border-t border-slate-200 pt-4 mt-4">
                <h3 className="text-lg font-bold text-blue-700 mb-4">Phạm vi & Đối tượng</h3>
                {isAvailableQuest && (
                    <p className="mb-4 rounded-xl border border-cyan-200 bg-cyan-50 px-4 py-3 text-sm text-cyan-700">
                        Quest có thể làm sẽ hiển thị ở tab Có thể làm và người dùng tự bấm bắt đầu.
                    </p>
                )}
                {isLimitQuest && (
                    <p className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
                        Limit Quest chỉ admin tạo, dùng cho coaching 1:1 hoặc họp offline và bắt buộc người nhận upload ảnh minh chứng.
                    </p>
                )}
                
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                    <label className={`border-2 p-3 rounded-lg cursor-pointer transition-all ${formData.scope === 'mandatory' ? 'bg-blue-50 border-blue-400' : 'border-gray-200 hover:bg-gray-50'}`}>
                        <input
                            type="radio"
                            name="scope"
                            value="mandatory"
                            checked={formData.scope === 'mandatory'}
                            disabled={isAvailableQuest || isLimitQuest}
                            onChange={() => setFormData({...formData, scope: 'mandatory' as TaskScope})}
                            className="mr-2 text-blue-600"
                        />
                        <span className="font-semibold">Bắt buộc (Toàn bộ)</span>
                        <p className="text-xs text-gray-500 mt-1">Giao cho tất cả thành viên, không cần accept.</p>
                    </label>

                    <label className={`border-2 p-3 rounded-lg cursor-pointer transition-all ${formData.scope === 'opt_in' ? 'bg-cyan-50 border-cyan-400' : 'border-gray-200 hover:bg-gray-50'}`}>
                        <input
                            type="radio"
                            name="scope"
                            value="opt_in"
                            checked={formData.scope === 'opt_in'}
                            disabled={isAvailableQuest || isLimitQuest}
                            onChange={() => setFormData({...formData, scope: 'opt_in' as TaskScope})}
                            className="mr-2 text-cyan-600"
                        />
                        <span className="font-semibold">Đăng ký (Opt-in)</span>
                        <p className="text-xs text-gray-500 mt-1">Giới hạn số lượng, cần bấm nhận task.</p>
                    </label>

                    <label className={`border-2 p-3 rounded-lg cursor-pointer transition-all ${formData.scope === 'private' ? 'bg-amber-50 border-amber-400' : 'border-gray-200 hover:bg-gray-50'}`}>
                        <input
                            type="radio"
                            name="scope"
                            value="private"
                            checked={formData.scope === 'private'}
                            disabled={isAvailableQuest || isLimitQuest}
                            onChange={() => setFormData({...formData, scope: 'private' as TaskScope})}
                            className="mr-2 text-amber-600"
                        />
                        <span className="font-semibold">Riêng tư (Private)</span>
                        <p className="text-xs text-gray-500 mt-1">Chỉ hiện với người được chỉ định.</p>
                    </label>
                </div>

                {formData.scope === 'opt_in' && (
                    <div className="mb-4 bg-cyan-50 p-4 rounded-lg border border-cyan-200">
                        <label className="block text-sm font-semibold text-cyan-700 mb-1">Số lượng tối đa</label>
                        <input
                            type="number"
                            min="1"
                            placeholder="Không giới hạn nếu để trống"
                            className="border border-cyan-200 rounded-xl px-4 py-2.5 w-full max-w-xs focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 bg-white"
                            value={formData.max_participants}
                            onChange={e => setFormData({...formData, max_participants: e.target.value})}
                        />
                    </div>
                )}

                {(formData.scope === 'private' || isLimitQuest) && (
                    <div className="mb-4 bg-amber-50 p-4 rounded-lg border border-amber-200">
                        <label className="block text-sm font-semibold text-amber-700 mb-2">
                            {isLimitQuest ? 'Chọn người nhận Limit Quest' : 'Chọn người thực hiện'}
                        </label>
                        <div className="max-h-60 overflow-y-auto border border-amber-200 rounded-xl bg-white p-2">
                             {assigneeUsers.length === 0 ? (
                                 <p className="text-sm text-gray-500 p-2">Không tìm thấy users hoặc không có quyền xem.</p>
                             ) : (
                                 assigneeUsers.map(u => (
                                     <div key={u.id} className="flex items-center p-2 hover:bg-amber-50 rounded-lg border-b border-amber-100 last:border-0">
                                         <input
                                             type="checkbox"
                                             checked={formData.assignee_ids.includes(u.id)}
                                             onChange={() => toggleAssignee(u.id)}
                                             className="mr-3 text-amber-600 rounded"
                                         />
                                         <div>
                                             <div className="font-medium text-gray-900">{u.full_name || u.email}</div>
                                             <div className="text-xs text-gray-500">{u.email} - {u.primary_role}</div>
                                         </div>
                                     </div>
                                 ))
                             )}
                        </div>
                        <p className="text-xs text-amber-700 mt-2 font-medium">Đã chọn: {formData.assignee_ids.length} người</p>
                    </div>
                )}
            </div>

            {/* Details */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-1">Độ khó</label>
                    <select
                        className="w-full border border-gray-200 rounded-xl px-4 py-3 focus:ring-2 focus:ring-violet-500 focus:border-violet-500 bg-gray-50/50 hover:bg-white transition-all"
                        value={formData.difficulty}
                        onChange={e => setFormData({...formData, difficulty: e.target.value as TaskDifficulty})}
                    >
                        <option value="easy">Easy</option>
                        <option value="medium">Medium</option>
                        <option value="hard">Hard</option>
                        <option value="advanced">Advanced</option>
                        <option value="expert">Expert</option>
                    </select>
                </div>
                <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-1">XP Reward</label>
                    <input
                        type="number"
                        className="w-full border border-gray-200 rounded-xl px-4 py-3 focus:ring-2 focus:ring-violet-500 focus:border-violet-500 bg-gray-50/50 hover:bg-white transition-all"
                        value={formData.xp_reward}
                        onChange={e => setFormData({...formData, xp_reward: parseInt(e.target.value)})}
                    />
                </div>
                <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-1">Min Level</label>
                    <input
                        type="number"
                        className="w-full border border-gray-200 rounded-xl px-4 py-3 focus:ring-2 focus:ring-violet-500 focus:border-violet-500 bg-gray-50/50 hover:bg-white transition-all"
                        value={formData.min_level_required}
                        onChange={e => setFormData({...formData, min_level_required: parseInt(e.target.value)})}
                    />
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-1">Cấp áp dụng</label>
                    <select
                        className="w-full border border-gray-200 rounded-xl px-4 py-3 focus:ring-2 focus:ring-violet-500 focus:border-violet-500 bg-gray-50/50 hover:bg-white transition-all"
                        value={formData.target_member_level}
                        onChange={e => setFormData({...formData, target_member_level: e.target.value as MemberLevel})}
                        disabled={formData.scope === 'mandatory' || formData.scope === 'private'}
                    >
                        <option value="new">Thành viên mới</option>
                        <option value="diligent">Thành viên chuyên cần</option>
                        <option value="official">Thành viên chính thức</option>
                    </select>
                </div>
                <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-1">Nguồn tạo</label>
                    <select
                        className="w-full border border-gray-200 rounded-xl px-4 py-3 focus:ring-2 focus:ring-violet-500 focus:border-violet-500 bg-gray-50/50 hover:bg-white transition-all"
                        value={formData.creator_type}
                        onChange={e => setFormData({...formData, creator_type: e.target.value as TaskCreatorType})}
                    >
                        <option value="manager">Manager</option>
                        <option value="ai">AI</option>
                        <option value="system">System</option>
                    </select>
                </div>
                <label className="flex items-center gap-3 border border-gray-200 rounded-xl px-4 py-3 bg-gray-50/50">
                    <input
                        type="checkbox"
                        checked={formData.requires_manager_review}
                        onChange={e => setFormData({...formData, requires_manager_review: e.target.checked})}
                        className="w-4 h-4 text-violet-600 border-gray-300 rounded"
                    />
                    <span className="text-sm font-semibold text-gray-700">Cần manager review</span>
                </label>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-1">Deadline</label>
                    <input
                        type="datetime-local"
                        className="w-full border border-gray-200 rounded-xl px-4 py-3 focus:ring-2 focus:ring-violet-500 focus:border-violet-500 bg-gray-50/50 hover:bg-white transition-all"
                        value={formData.deadline}
                        onChange={e => setFormData({...formData, deadline: e.target.value})}
                    />
                </div>
                <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-1">Thời lượng ước tính phút</label>
                    <input
                        type="number"
                        min="1"
                        className="w-full border border-gray-200 rounded-xl px-4 py-3 focus:ring-2 focus:ring-violet-500 focus:border-violet-500 bg-gray-50/50 hover:bg-white transition-all"
                        value={formData.estimated_duration_minutes}
                        onChange={e => setFormData({...formData, estimated_duration_minutes: parseInt(e.target.value)})}
                    />
                </div>
            </div>

            <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1">Skill Tags (cách nhau bởi dấu phẩy)</label>
                <input
                    type="text"
                    placeholder="react, backend, docker"
                    className="w-full border border-gray-200 rounded-xl px-4 py-3 focus:ring-2 focus:ring-violet-500 focus:border-violet-500 bg-gray-50/50 hover:bg-white transition-all"
                    value={formData.skill_tags}
                    onChange={e => setFormData({...formData, skill_tags: e.target.value})}
                />
            </div>

            <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1">Hướng dẫn chi tiết (Markdown)</label>
                <textarea
                    rows={5}
                    className="w-full border border-gray-200 rounded-xl px-4 py-3 focus:ring-2 focus:ring-violet-500 focus:border-violet-500 bg-gray-50/50 hover:bg-white transition-all font-mono text-sm"
                    value={formData.instructions}
                    onChange={e => setFormData({...formData, instructions: e.target.value})}
                />
            </div>

            <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1">Reference Links (Mỗi link 1 dòng)</label>
                <textarea
                    rows={3}
                    className="w-full border border-gray-200 rounded-xl px-4 py-3 focus:ring-2 focus:ring-violet-500 focus:border-violet-500 bg-gray-50/50 hover:bg-white transition-all font-mono text-sm"
                    value={formData.reference_links}
                    onChange={e => setFormData({...formData, reference_links: e.target.value})}
                />
            </div>

            <div className="pt-4 flex justify-end gap-3">
                <Link
                    href="/mentor"
                    className="px-6 py-2.5 border border-gray-200 rounded-xl text-gray-700 hover:bg-gray-50 font-medium transition-colors"
                >
                    Hủy
                </Link>
                <button
                    type="submit"
                    disabled={loading}
                    className="px-6 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 font-semibold shadow-sm transition-colors"
                >
                    {loading ? 'Đang tạo...' : isLimitQuest ? 'Tạo Limit Quest' : 'Tạo Task'}
                </button>
            </div>

          </form>
        </div>
      </div>
    </div>
  );
}
