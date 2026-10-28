'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { apiClient } from '@/lib/api';
import { Task, TaskScope, TaskType, TaskDifficulty } from '@/types/task';
import { User } from '@/types';
import Link from 'next/link';

export default function EditTaskPage() {
  const router = useRouter();
  const params = useParams();
  const taskId = params.id as string;
  
  const [loading, setLoading] = useState(false);
  const [fetchingTask, setFetchingTask] = useState(true);
  const [users, setUsers] = useState<User[]>([]);

  const [formData, setFormData] = useState({
    title: '',
    description: '',
    type: 'core' as TaskType,
    scope: 'mandatory' as TaskScope,
    difficulty: 'medium' as TaskDifficulty,
    min_level_required: 1,
    xp_reward: 100,
    skill_tags: '',
    max_participants: '',
    assignee_ids: [] as string[],
    instructions: '',
    reference_links: ''
  });

  useEffect(() => {
    loadTask();
    loadUsers();
  }, []);

  const loadTask = async () => {
    try {
      setFetchingTask(true);
      const task = await apiClient.getTask(taskId);
      setFormData({
        title: task.title,
        description: task.description,
        type: task.type,
        scope: task.scope,
        difficulty: task.difficulty,
        min_level_required: task.min_level_required,
        xp_reward: task.xp_reward,
        skill_tags: task.skill_tags.join(', '),
        max_participants: task.max_participants?.toString() || '',
        assignee_ids: task.assignee_ids || [],
        instructions: task.instructions || '',
        reference_links: task.reference_links.join('\n')
      });
    } catch (error: any) {
      console.error('Failed to load task:', error);
      alert('Không thể tải thông tin task');
      router.push('/mentor/tasks');
    } finally {
      setFetchingTask(false);
    }
  };

  const loadUsers = async () => {
    try {
      const res = await apiClient.getUsers({ page_size: 100 });
      setUsers(res.users || []);
    } catch (error) {
      console.error('Failed to load users', error);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const payload = {
        ...formData,
        skill_tags: formData.skill_tags.split(',').map(t => t.trim()).filter(Boolean),
        reference_links: formData.reference_links.split('\n').map(l => l.trim()).filter(Boolean),
        max_participants: formData.scope === 'opt_in' && formData.max_participants ? parseInt(formData.max_participants) : undefined,
        assignee_ids: formData.scope === 'private' ? formData.assignee_ids : []
      };

      await apiClient.updateTask(taskId, payload);
      alert('Cập nhật task thành công!');
      router.push('/mentor/tasks');
    } catch (error: any) {
      console.error(error);
      alert(error.response?.data?.detail || 'Cập nhật task thất bại');
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

  if (fetchingTask) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-violet-50 via-white to-fuchsia-50 flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-violet-200 border-t-violet-600 rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-violet-50 via-white to-fuchsia-50 py-8">
      <div className="max-w-3xl mx-auto px-4">
        <div className="mb-6 flex items-center justify-between">
            <h1 className="text-2xl font-bold bg-gradient-to-r from-violet-600 to-fuchsia-600 bg-clip-text text-transparent">Chỉnh sửa Nhiệm vụ</h1>
            <Link href="/mentor/tasks" className="text-gray-600 hover:text-violet-600 transition-colors">
                Cancel
            </Link>
        </div>

        <div className="bg-white/80 backdrop-blur-sm rounded-2xl border border-violet-100 shadow-lg shadow-violet-50 p-6">
          <form onSubmit={handleSubmit} className="space-y-6">

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
                            value={formData.type}
                            onChange={e => setFormData({...formData, type: e.target.value as TaskType})}
                        >
                            <option value="core">Core Task (Bắt buộc)</option>
                            <option value="bounty">Bounty Task (Thử thách)</option>
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
            <div className="border-t border-violet-100 pt-4 mt-4">
                <h3 className="text-lg font-bold text-violet-600 mb-4">Phạm vi & Đối tượng</h3>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                    <label className={`border-2 p-3 rounded-xl cursor-pointer transition-all ${formData.scope === 'mandatory' ? 'bg-gradient-to-r from-violet-50 to-fuchsia-50 border-violet-400' : 'border-gray-200 hover:bg-gray-50'}`}>
                        <input
                            type="radio"
                            name="scope"
                            value="mandatory"
                            checked={formData.scope === 'mandatory'}
                            onChange={e => setFormData({...formData, scope: 'mandatory' as TaskScope})}
                            className="mr-2 text-violet-600"
                        />
                        <span className="font-semibold">Bắt buộc (Toàn bộ)</span>
                        <p className="text-xs text-gray-500 mt-1">Giao cho tất cả thành viên, không cần accept.</p>
                    </label>

                    <label className={`border-2 p-3 rounded-xl cursor-pointer transition-all ${formData.scope === 'opt_in' ? 'bg-gradient-to-r from-cyan-50 to-teal-50 border-cyan-400' : 'border-gray-200 hover:bg-gray-50'}`}>
                        <input
                            type="radio"
                            name="scope"
                            value="opt_in"
                            checked={formData.scope === 'opt_in'}
                            onChange={e => setFormData({...formData, scope: 'opt_in' as TaskScope})}
                            className="mr-2 text-cyan-600"
                        />
                        <span className="font-semibold">Đăng ký (Opt-in)</span>
                        <p className="text-xs text-gray-500 mt-1">Giới hạn số lượng, cần bấm nhận task.</p>
                    </label>

                    <label className={`border-2 p-3 rounded-xl cursor-pointer transition-all ${formData.scope === 'private' ? 'bg-gradient-to-r from-amber-50 to-orange-50 border-amber-400' : 'border-gray-200 hover:bg-gray-50'}`}>
                        <input
                            type="radio"
                            name="scope"
                            value="private"
                            checked={formData.scope === 'private'}
                            onChange={e => setFormData({...formData, scope: 'private' as TaskScope})}
                            className="mr-2 text-amber-600"
                        />
                        <span className="font-semibold">Riêng tư (Private)</span>
                        <p className="text-xs text-gray-500 mt-1">Chỉ hiện với người được chỉ định.</p>
                    </label>
                </div>

                {formData.scope === 'opt_in' && (
                    <div className="mb-4 bg-gradient-to-r from-cyan-50 to-teal-50 p-4 rounded-xl border border-cyan-200">
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

                {formData.scope === 'private' && (
                    <div className="mb-4 bg-gradient-to-r from-amber-50 to-orange-50 p-4 rounded-xl border border-amber-200">
                        <label className="block text-sm font-semibold text-amber-700 mb-2">Chọn người thực hiện</label>
                        <div className="max-h-60 overflow-y-auto border border-amber-200 rounded-xl bg-white p-2">
                             {users.length === 0 ? (
                                 <p className="text-sm text-gray-500 p-2">Không tìm thấy users hoặc không có quyền xem.</p>
                             ) : (
                                 users.map(u => (
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
                    href="/mentor/tasks"
                    className="px-6 py-2.5 border border-gray-200 rounded-xl text-gray-700 hover:bg-gray-50 font-medium transition-colors"
                >
                    Hủy
                </Link>
                <button
                    type="submit"
                    disabled={loading}
                    className="px-6 py-2.5 bg-gradient-to-r from-violet-600 to-fuchsia-600 text-white rounded-xl hover:from-violet-700 hover:to-fuchsia-700 disabled:opacity-50 font-semibold shadow-lg shadow-violet-200 transition-all"
                >
                    {loading ? 'Đang cập nhật...' : 'Lưu thay đổi'}
                </button>
            </div>

          </form>
        </div>
      </div>
    </div>
  );
}
