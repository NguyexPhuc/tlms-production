'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { apiClient } from '@/lib/api';
import { TaskDetailResponse, TaskParticipant, TaskStatus } from '@/types/task';
import Link from 'next/link';

const STATUS_COLORS: Record<string, string> = {
  available: 'bg-slate-100 text-slate-700',
  in_progress: 'bg-blue-100 text-blue-700',
  submitted: 'bg-violet-100 text-violet-700',
  approved: 'bg-emerald-100 text-emerald-700',
  completed: 'bg-emerald-100 text-emerald-700',
  rejected: 'bg-red-100 text-red-700',
  locked: 'bg-slate-100 text-slate-500',
};

const DIFFICULTY_COLORS: Record<string, string> = {
  easy: 'bg-emerald-100 text-emerald-700',
  medium: 'bg-amber-100 text-amber-700',
  hard: 'bg-orange-100 text-orange-700',
  expert: 'bg-red-100 text-red-700',
};

export default function TaskVisualizationPage() {
  const router = useRouter();
  const params = useParams();
  const taskId = params.id as string;

  const [loading, setLoading] = useState(true);
  const [taskDetail, setTaskDetail] = useState<TaskDetailResponse | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>('all');

  useEffect(() => {
    loadTaskDetails();
  }, []);

  const loadTaskDetails = async () => {
    try {
      setLoading(true);
      const data = await apiClient.getTaskDetails(taskId);
      setTaskDetail(data);
    } catch (error: any) {
      console.error('Failed to load task details:', error);
      alert('Không thể tải thông tin task');
      router.push('/mentor/tasks');
    } finally {
      setLoading(false);
    }
  };

  if (loading || !taskDetail) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-violet-50 via-white to-fuchsia-50 flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-violet-200 border-t-violet-600 rounded-full animate-spin"></div>
      </div>
    );
  }

  const filteredParticipants = taskDetail.participants.filter(p => 
    filterStatus === 'all' || p.task_status === filterStatus
  );

  const scopeLabels: Record<string, string> = {
    mandatory: 'Bắt buộc (Toàn bộ)',
    opt_in: 'Đăng ký (Opt-in)',
    private: 'Riêng tư (Private)'
  };

  const typeLabels: Record<string, string> = {
    core: 'CORE',
    bounty: 'BOUNTY'
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-violet-50 via-white to-fuchsia-50 py-8">
      <div className="max-w-7xl mx-auto px-4">
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold bg-gradient-to-r from-violet-600 to-fuchsia-600 bg-clip-text text-transparent">
              Thống kê Task
            </h1>
            <p className="text-sm text-gray-500 mt-1">{taskDetail.title}</p>
          </div>
          <div className="flex items-center gap-2">
            <Link
              href={`/mentor/tasks/edit/${taskId}`}
              className="px-4 py-2 bg-[#1E90FF] text-white rounded-lg hover:bg-[#1a7de0] text-sm font-medium transition-colors shadow-sm"
            >
              Chỉnh sửa
            </Link>
            <Link
              href="/mentor/tasks"
              className="px-4 py-2 border border-gray-200 rounded-lg text-gray-700 hover:bg-gray-50 text-sm font-medium transition-colors"
            >
              ← Quay lại
            </Link>
          </div>
        </div>

        {/* Task Info Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white/80 backdrop-blur-sm rounded-xl p-4 border border-violet-100 shadow-sm">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Loại Task</p>
            <div className="flex items-center gap-2 mt-2">
              <span className={`px-2 py-1 text-xs font-medium rounded ${
                taskDetail.type === 'core' ? 'bg-red-100 text-red-700' : 'bg-[#1E90FF]/10 text-[#1E90FF]'
              }`}>
                {typeLabels[taskDetail.type]}
              </span>
              <span className={`px-2 py-1 text-xs font-medium rounded ${DIFFICULTY_COLORS[taskDetail.difficulty]}`}>
                {taskDetail.difficulty.toUpperCase()}
              </span>
            </div>
            <p className="text-xs text-gray-500 mt-2">Phạm vi: {scopeLabels[taskDetail.scope]}</p>
          </div>

          <div className="bg-white/80 backdrop-blur-sm rounded-xl p-4 border border-violet-100 shadow-sm">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">XP Reward</p>
            <p className="text-2xl font-semibold text-[#32CD32] mt-1">+{taskDetail.xp_reward} XP</p>
            <p className="text-xs text-gray-500 mt-2">Level yêu cầu: {taskDetail.min_level_required}</p>
          </div>

          <div className="bg-white/80 backdrop-blur-sm rounded-xl p-4 border border-violet-100 shadow-sm">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Trạng thái</p>
            <p className={`text-lg font-semibold mt-1 ${taskDetail.is_active ? 'text-green-600' : 'text-gray-400'}`}>
              {taskDetail.is_active ? '● Hoạt động' : '○ Không hoạt động'}
            </p>
            {taskDetail.scope === 'opt_in' && taskDetail.max_participants && (
              <p className="text-xs text-gray-500 mt-2">Tối đa: {taskDetail.max_participants} người</p>
            )}
          </div>

          <div className="bg-white/80 backdrop-blur-sm rounded-xl p-4 border border-violet-100 shadow-sm">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Tổng người tham gia</p>
            <p className="text-2xl font-semibold text-violet-600 mt-1">{taskDetail.total_participants}</p>
            {taskDetail.scope === 'private' && (
              <p className="text-xs text-amber-600 mt-2">Chỉ định: {taskDetail.assignee_ids.length} người</p>
            )}
          </div>
        </div>

        {/* Status Statistics */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
          <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Đang làm</p>
            <p className="text-2xl font-semibold text-blue-600 mt-1">{taskDetail.in_progress_count}</p>
          </div>
          <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Chờ review</p>
            <p className="text-2xl font-semibold text-violet-600 mt-1">{taskDetail.submitted_count}</p>
          </div>
          <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Hoàn thành</p>
            <p className="text-2xl font-semibold text-emerald-600 mt-1">{taskDetail.completed_count}</p>
          </div>
          <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Từ chối</p>
            <p className="text-2xl font-semibold text-red-600 mt-1">{taskDetail.rejected_count}</p>
          </div>
          <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Chưa bắt đầu</p>
            <p className="text-2xl font-semibold text-slate-600 mt-1">
              {taskDetail.total_participants - taskDetail.in_progress_count - taskDetail.submitted_count - taskDetail.completed_count - taskDetail.rejected_count}
            </p>
          </div>
        </div>

        {/* Participants Table */}
        <div className="bg-white/80 backdrop-blur-sm rounded-2xl border border-violet-100 shadow-lg shadow-violet-50 overflow-hidden">
          <div className="p-5 border-b border-violet-100 flex items-center justify-between">
            <h2 className="text-lg font-bold text-violet-600">Danh sách người tham gia</h2>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-violet-500 focus:border-violet-500 bg-white"
            >
              <option value="all">Tất cả ({taskDetail.participants.length})</option>
              <option value="available">Chưa bắt đầu</option>
              <option value="in_progress">Đang làm</option>
              <option value="submitted">Chờ review</option>
              <option value="completed">Hoàn thành</option>
              <option value="rejected">Từ chối</option>
            </select>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gradient-to-r from-violet-50 to-fuchsia-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">Người dùng</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">Role</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">Level</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">XP</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">Trạng thái</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">Thời gian</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">Link bài làm</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">Nhận xét</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filteredParticipants.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-12 text-center text-gray-500">
                      Không có người tham gia nào
                    </td>
                  </tr>
                ) : (
                  filteredParticipants.map((participant) => (
                    <tr key={participant.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          {participant.avatar_url ? (
                            <img
                              src={participant.avatar_url}
                              alt={participant.full_name || participant.email}
                              className="w-8 h-8 rounded-full object-cover"
                            />
                          ) : (
                            <div className="w-8 h-8 rounded-full bg-gradient-to-r from-violet-500 to-fuchsia-500 flex items-center justify-center text-white text-xs font-bold">
                              {(participant.full_name || participant.email)[0]?.toUpperCase()}
                            </div>
                          )}
                          <div>
                            <p className="text-sm font-medium text-gray-900">
                              {participant.full_name || participant.email}
                            </p>
                            <p className="text-xs text-gray-500">{participant.email}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className="px-2 py-1 bg-gray-100 text-gray-700 text-xs font-medium rounded uppercase">
                          {participant.role}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-700">
                        {participant.level}
                      </td>
                      <td className="px-4 py-3 text-sm font-medium text-[#32CD32]">
                        {participant.current_xp}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-1 text-xs font-medium rounded ${STATUS_COLORS[participant.task_status]}`}>
                          {participant.task_status.toUpperCase().replace('_', ' ')}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-500">
                        {participant.started_at && (
                          <div>
                            <p>Bắt đầu: {new Date(participant.started_at).toLocaleDateString('vi-VN')}</p>
                            {participant.completed_at && (
                              <p>Hoàn thành: {new Date(participant.completed_at).toLocaleDateString('vi-VN')}</p>
                            )}
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {participant.proof_link ? (
                          <a
                            href={participant.proof_link}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-[#1E90FF] hover:underline text-sm truncate block max-w-[200px]"
                          >
                            Xem bài làm
                          </a>
                        ) : (
                          <span className="text-gray-400 text-sm">-</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {participant.mentor_comment ? (
                          <p className="text-xs text-gray-600 max-w-[200px] truncate" title={participant.mentor_comment}>
                            {participant.mentor_comment}
                          </p>
                        ) : (
                          <span className="text-gray-400 text-sm">-</span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
