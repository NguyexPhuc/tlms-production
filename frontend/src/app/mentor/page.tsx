'use client';

import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';
import { apiClient } from '@/lib/api';
import { UserTask } from '@/types/task';
import Link from 'next/link';

export default function MentorDashboard() {
  const { user, isLoading } = useAuth();
  const router = useRouter();
  const [pendingReviews, setPendingReviews] = useState<UserTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [reviewingTask, setReviewingTask] = useState<string | null>(null);
  const [comment, setComment] = useState('');
  const [score, setScore] = useState('');

  const loadPendingReviews = useCallback(async () => {
    try {
      setLoading(true);
      const data = await apiClient.getPendingReviews();
      setPendingReviews(data.tasks);
    } catch (error) {
      console.error('Failed to load pending reviews:', error);
    } finally {
      setLoading(false);
    }
  }, []);

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
      void loadPendingReviews();
    }
  }, [isLoading, user, router, loadPendingReviews]);

  const handleReview = async (userTaskId: string, approved: boolean) => {
    if (!comment.trim() && !approved) {
      alert('Vui lòng nhập lý do từ chối');
      return;
    }

    try {
      await apiClient.reviewTask(userTaskId, {
        status: approved ? 'approved' : 'rejected',
        mentor_comment: comment.trim() || undefined,
        manager_score: score ? Number(score) : undefined,
        final_score: score ? Number(score) : undefined,
      });
      setReviewingTask(null);
      setComment('');
      setScore('');
      await loadPendingReviews();
      alert(approved ? 'Đã duyệt task!' : 'Đã từ chối task');
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to review task');
    }
  };

  if (isLoading || !user) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-gray-300 border-t-[#1E90FF] rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10 shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-semibold text-gray-900">Mentor Dashboard</h1>
              <p className="text-sm text-gray-500 mt-0.5">Review và duyệt bài làm</p>
            </div>
            <div className="flex items-center gap-2">
              <Link
                href="/mentor/weekly-stats"
                className="px-3 py-2 bg-gradient-to-r from-violet-600 to-fuchsia-600 text-white rounded-lg hover:from-violet-700 hover:to-fuchsia-700 text-sm font-medium transition-all shadow-sm"
              >
                📊 Thống kê tuần
              </Link>
              <Link
                href="/mentor/tasks"
                className="px-3 py-2 text-sm text-gray-600 hover:text-[#1E90FF] hover:bg-blue-50 rounded-lg transition-colors"
              >
                Quản lý tasks
              </Link>
              <Link
                href="/mentor/tasks/create"
                className="px-3 py-2 bg-gradient-to-r from-[#1E90FF] to-[#9333ea] text-white rounded-lg hover:opacity-90 text-sm font-medium transition-all shadow-sm"
              >
                + Tạo nhiệm vụ
              </Link>
              <button
                onClick={() => router.push('/dashboard')}
                className="px-3 py-2 text-sm text-gray-600 hover:text-[#1E90FF] hover:bg-blue-50 rounded-lg transition-colors"
              >
                ← Quay lại
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-6 space-y-6">
        {/* Stats */}
        <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Chờ review</p>
              <p className="text-2xl font-semibold text-[#FFA500] mt-1">{pendingReviews.length}</p>
            </div>
          </div>
        </div>

        {/* Pending Reviews */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
          <div className="p-5 border-b border-gray-200">
            <h2 className="text-base font-semibold text-gray-900">Bài nộp đang chờ review</h2>
          </div>
          
          {loading ? (
            <div className="p-12 text-center text-gray-500">Đang tải...</div>
          ) : pendingReviews.length === 0 ? (
            <div className="p-12 text-center text-gray-500">
              Không có bài nào cần review
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {pendingReviews.map((userTask) => (
                <div key={userTask.id} className="p-5">
                  <div className="flex flex-wrap items-center gap-2 mb-2">
                    <span className={`px-2 py-0.5 text-xs font-medium rounded ${
                      userTask.task.type === 'core' ? 'bg-red-100 text-red-700' : 'bg-[#1E90FF]/10 text-[#1E90FF]'
                    }`}>
                      {userTask.task.type === 'core' ? 'CORE' : 'BOUNTY'}
                    </span>
                    <span className="text-xs text-[#32CD32] font-medium">+{userTask.task.xp_reward} XP</span>
                  </div>
                  
                  <h3 className="text-base font-medium text-gray-900 mb-1">{userTask.task.title}</h3>
                  <p className="text-sm text-gray-600 mb-4">{userTask.task.description}</p>

                  {/* Student Info */}
                  <div className="bg-gray-50 rounded-lg p-3 mb-4 text-sm">
                    <p className="text-gray-700">
                      <span className="font-medium">Thành viên:</span>{' '}
                      <span className="font-medium text-[#1E90FF]">
                        {userTask.user_full_name || userTask.user_email || 'Unknown'}
                      </span>
                    </p>
                    <p className="text-gray-700 mt-1">
                      <span className="font-medium">Email:</span>{' '}
                      {userTask.user_email || 'N/A'}
                    </p>
                    <p className="text-gray-700 mt-1">
                      <span className="font-medium">Thời gian nộp:</span>{' '}
                      {userTask.submitted_at ? new Date(userTask.submitted_at).toLocaleString('vi-VN') : 'N/A'}
                    </p>
                  </div>

                  {/* Submission */}
                  <div className="bg-[#1E90FF]/5 border border-[#1E90FF]/20 rounded-lg p-4 mb-4">
                    <p className="text-sm font-medium text-gray-700 mb-2">Link bài làm:</p>
                    {userTask.proof_link ? (
                      <a
                        href={userTask.proof_link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-[#1E90FF] hover:underline break-all"
                      >
                        {userTask.proof_link}
                      </a>
                    ) : (
                      <p className="text-sm text-gray-500 italic">Chưa có link</p>
                    )}
                    
                    {userTask.submission_notes && (
                      <div className="mt-3 pt-3 border-t border-[#1E90FF]/20">
                        <p className="text-sm font-medium text-gray-700 mb-1">Ghi chú:</p>
                        <p className="text-sm text-gray-600 whitespace-pre-wrap">{userTask.submission_notes}</p>
                      </div>
                    )}
                    {userTask.ai_score !== null && userTask.ai_score !== undefined && (
                      <div className="mt-3 pt-3 border-t border-[#1E90FF]/20">
                        <p className="text-sm font-medium text-gray-700 mb-1">AI score gợi ý: {userTask.ai_score.toFixed(1)}/100</p>
                        {userTask.ai_feedback && (
                          <p className="text-sm text-gray-600 whitespace-pre-wrap">{userTask.ai_feedback}</p>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Review Form */}
                  {reviewingTask === userTask.id ? (
                    <div className="border-t border-gray-200 pt-4">
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Manager score
                      </label>
                      <input
                        type="number"
                        min={0}
                        max={100}
                        value={score}
                        onChange={(e) => setScore(e.target.value)}
                        placeholder="0-100"
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1E90FF] focus:border-[#1E90FF] text-sm mb-3"
                      />
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Nhận xét (tùy chọn)
                      </label>
                      <textarea
                        value={comment}
                        onChange={(e) => setComment(e.target.value)}
                        rows={3}
                        placeholder="Nhận xét về bài làm..."
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1E90FF] focus:border-[#1E90FF] text-sm mb-3"
                      />
                      <div className="flex flex-wrap gap-2">
                        <button
                          onClick={() => handleReview(userTask.id, true)}
                          className="px-4 py-2 bg-[#32CD32] text-white rounded-lg hover:bg-[#22c55e] text-sm font-medium transition-colors shadow-sm"
                        >
                          Duyệt
                        </button>
                        <button
                          onClick={() => handleReview(userTask.id, false)}
                          className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 text-sm font-medium transition-colors shadow-sm"
                        >
                          Từ chối
                        </button>
                        <button
                          onClick={() => {
                            setReviewingTask(null);
                            setComment('');
                            setScore('');
                          }}
                          className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 text-sm transition-colors"
                        >
                          Hủy
                        </button>
                      </div>
                    </div>
                  ) : (
                    <button
                      onClick={() => setReviewingTask(userTask.id)}
                      className="px-4 py-2 bg-[#1E90FF] text-white rounded-lg hover:bg-[#1a7de0] text-sm font-medium transition-colors shadow-sm"
                    >
                      Review ngay
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
