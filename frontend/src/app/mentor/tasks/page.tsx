'use client';

import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { apiClient } from '@/lib/api';
import { Task, TaskListResponse } from '@/types/task';
import Link from 'next/link';

export default function MentorTasksPage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'active' | 'inactive'>('all');
  const [typeFilter, setTypeFilter] = useState<'all' | 'core' | 'bounty'>('all');

  useEffect(() => {
    if (!isLoading && !user) {
      router.push('/login');
      return;
    }

    if (user) {
      if (!user.roles.includes('mentor') && !user.roles.includes('admin')) {
        router.push('/dashboard');
        return;
      }
      loadTasks();
    }
  }, [isLoading, user, router]);

  const loadTasks = async () => {
    try {
      setLoading(true);
      const params: any = { page_size: 100 };
      if (filter === 'active' || filter === 'inactive') {
        params.is_active = filter === 'active';
      }
      if (typeFilter !== 'all') {
        params.task_type = typeFilter;
      }
      const data: TaskListResponse = await apiClient.listTasks(params);
      setTasks(data.tasks);
    } catch (error) {
      console.error('Failed to load tasks:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (taskId: string, taskTitle: string) => {
    if (!confirm(`Bạn có chắc chắn muốn xóa task "${taskTitle}"? Hành động này không thể hoàn tác.`)) {
      return;
    }

    try {
      await apiClient.deleteTask(taskId);
      alert('Đã xóa task thành công!');
      await loadTasks();
    } catch (error: any) {
      console.error('Failed to delete task:', error);
      alert(error.response?.data?.detail || 'Không thể xóa task');
    }
  };

  if (isLoading || !user) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-gray-300 border-t-[#1E90FF] rounded-full animate-spin"></div>
      </div>
    );
  }

  const filteredTasks = tasks.filter(task => {
    if (filter === 'active' && !task.is_active) return false;
    if (filter === 'inactive' && task.is_active) return false;
    if (typeFilter !== 'all' && task.type !== typeFilter) return false;
    return true;
  });

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-semibold text-gray-900">Quản lý Tasks</h1>
              <p className="text-sm text-gray-500 mt-0.5">Tạo, chỉnh sửa và xóa tasks</p>
            </div>
            <div className="flex items-center gap-2">
              <Link
                href="/mentor/tasks/create"
                className="px-3 py-2 bg-gradient-to-r from-[#1E90FF] to-[#9333ea] text-white rounded-lg hover:opacity-90 text-sm font-medium transition-all shadow-sm"
              >
                + Tạo task mới
              </Link>
              <Link
                href="/mentor"
                className="px-3 py-2 text-sm text-gray-600 hover:text-[#1E90FF] hover:bg-blue-50 rounded-lg transition-colors"
              >
                ← Quay lại
              </Link>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {/* Filters */}
        <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
          <div className="flex flex-wrap gap-3">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-700">Trạng thái:</span>
              <select
                value={filter}
                onChange={(e) => setFilter(e.target.value as any)}
                className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-[#1E90FF] focus:border-[#1E90FF]"
              >
                <option value="all">Tất cả</option>
                <option value="active">Hoạt động</option>
                <option value="inactive">Không hoạt động</option>
              </select>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-700">Loại:</span>
              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value as any)}
                className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-[#1E90FF] focus:border-[#1E90FF]"
              >
                <option value="all">Tất cả</option>
                <option value="core">Core</option>
                <option value="bounty">Bounty</option>
              </select>
            </div>
            <div className="ml-auto text-sm text-gray-600">
              Tổng: <span className="font-medium">{filteredTasks.length}</span> tasks
            </div>
          </div>
        </div>

        {/* Task List */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
          <div className="p-5 border-b border-gray-200">
            <h2 className="text-base font-semibold text-gray-900">Danh sách tasks</h2>
          </div>

          {loading ? (
            <div className="p-12 text-center text-gray-500">Đang tải...</div>
          ) : filteredTasks.length === 0 ? (
            <div className="p-12 text-center text-gray-500">
              Không có task nào
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {filteredTasks.map((task) => (
                <div key={task.id} className="p-5 hover:bg-gray-50 transition-colors">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex flex-wrap items-center gap-2 mb-2">
                        <span className={`px-2 py-0.5 text-xs font-medium rounded ${
                          task.type === 'core' ? 'bg-red-100 text-red-700' : 'bg-[#1E90FF]/10 text-[#1E90FF]'
                        }`}>
                          {task.type.toUpperCase()}
                        </span>
                        <span className={`px-2 py-0.5 text-xs font-medium rounded ${
                          task.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'
                        }`}>
                          {task.is_active ? 'ACTIVE' : 'INACTIVE'}
                        </span>
                        <span className="text-xs text-[#32CD32] font-medium">+{task.xp_reward} XP</span>
                        {task.difficulty && (
                          <span className={`px-2 py-0.5 text-xs font-medium rounded ${
                            task.difficulty === 'easy' ? 'bg-blue-100 text-blue-700' :
                            task.difficulty === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                            'bg-red-100 text-red-700'
                          }`}>
                            {task.difficulty.toUpperCase()}
                          </span>
                        )}
                      </div>

                      <h3 className="text-base font-medium text-gray-900 mb-1">{task.title}</h3>
                      <p className="text-sm text-gray-600 mb-2 line-clamp-2">{task.description}</p>

                      <div className="flex flex-wrap gap-4 text-xs text-gray-500">
                        <span>Level yêu cầu: {task.min_level_required}</span>
                        {task.skill_tags.length > 0 && (
                          <span>Kỹ năng: {task.skill_tags.join(', ')}</span>
                        )}
                        {task.scope && (
                          <span>Phạm vi: {scopeLabels[task.scope] || task.scope}</span>
                        )}
                      </div>
                    </div>

                    <div className="flex flex-col gap-2">
                      <Link
                        href={`/mentor/tasks/${task.id}/visualize`}
                        className="px-3 py-1.5 bg-gradient-to-r from-violet-600 to-fuchsia-600 text-white text-sm rounded-lg hover:from-violet-700 hover:to-fuchsia-700 transition-colors font-medium"
                      >
                        Thống kê
                      </Link>
                      <Link
                        href={`/mentor/tasks/edit/${task.id}`}
                        className="px-3 py-1.5 bg-[#1E90FF] text-white text-sm rounded-lg hover:bg-[#1a7de0] transition-colors font-medium"
                      >
                        Sửa
                      </Link>
                      <button
                        onClick={() => handleDelete(task.id, task.title)}
                        className="px-3 py-1.5 bg-red-500 text-white text-sm rounded-lg hover:bg-red-600 transition-colors font-medium"
                      >
                        Xóa
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

const scopeLabels: Record<string, string> = {
  mandatory: 'Bắt buộc',
  opt_in: 'Tự nguyện',
  private: 'Riêng tư'
};
