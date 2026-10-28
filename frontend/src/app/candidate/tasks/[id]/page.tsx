'use client';

import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import { useEffect, useState, use } from 'react';
import { apiClient } from '@/lib/api';
import { UserTask } from '@/types/task';
import Link from 'next/link';

export default function SubmitTaskPage({ params }: { params: Promise<{ id: string }> }) {
  const { user, isLoading } = useAuth();
  const router = useRouter();
  const resolvedParams = use(params);
  const [userTask, setUserTask] = useState<UserTask | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [savingProgress, setSavingProgress] = useState(false);
  const [proofLink, setProofLink] = useState('');
  const [notes, setNotes] = useState('');
  const [completionPercentage, setCompletionPercentage] = useState(100);
  const [progressPercentage, setProgressPercentage] = useState(0);
  const [evidenceLinks, setEvidenceLinks] = useState('');

  useEffect(() => {
    if (!isLoading && !user) {
      router.push('/login');
      return;
    }

    if (user) {
      loadTask();
    }
  }, [isLoading, user, router, resolvedParams.id]);

  const loadTask = async () => {
    try {
      setLoading(true);
      console.log('Loading task with ID:', resolvedParams.id);
      
      const myTasksResponse = await apiClient.getMyTasks();
      console.log('My tasks response:', myTasksResponse);
      console.log('Number of tasks:', myTasksResponse.tasks.length);
      
      const task = myTasksResponse.tasks.find(t => {
        const match = t.id === resolvedParams.id;
        console.log(`Comparing task ID: ${t.id} === ${resolvedParams.id} = ${match}`);
        return match;
      });

      if (!task) {
        console.error('Task not found. Available task IDs:', myTasksResponse.tasks.map(t => t.id));
        alert('Task not found. Please make sure you have started this task first.');
        router.push('/candidate');
        return;
      }

      console.log('Task found:', task);
      setUserTask(task);
      if (task.proof_link) {
        setProofLink(task.proof_link);
      }
      if (task.submission_notes) {
        setNotes(task.submission_notes);
      }
      setCompletionPercentage(task.completion_percentage || 100);
      setProgressPercentage(task.progress_percentage || 0);
      setEvidenceLinks((task.evidence_links || []).join('\n'));
    } catch (error: any) {
      console.error('Failed to load task:', error);
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to load task';
      alert(`Error: ${errorMessage}`);
      router.push('/candidate');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveProgress = async () => {
    try {
      setSavingProgress(true);
      await apiClient.updateTaskProgress(resolvedParams.id, progressPercentage, notes.trim() || undefined);
      await loadTask();
      alert('Đã lưu tiến độ');
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Không thể lưu tiến độ');
    } finally {
      setSavingProgress(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!proofLink.trim() && !notes.trim()) {
      alert('Vui lòng nhập link bài làm hoặc ghi chú');
      return;
    }

    try {
      setSubmitting(true);
      await apiClient.submitTask(resolvedParams.id, {
        proof_link: proofLink,
        submission_notes: notes,
        completion_percentage: completionPercentage,
        evidence_links: evidenceLinks.split('\n').map(link => link.trim()).filter(Boolean),
      });
      alert('Nộp minh chứng thành công. AI đã chấm và cập nhật trạng thái.');
      router.push('/candidate');
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to submit task');
    } finally {
      setSubmitting(false);
    }
  };

  if (isLoading || loading || !user || !userTask) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-violet-50 via-white to-fuchsia-50 flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-violet-200 border-t-violet-600 rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-violet-50 via-white to-fuchsia-50">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-md border-b border-violet-100 sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            <h1 className="text-2xl font-bold bg-gradient-to-r from-violet-600 to-fuchsia-600 bg-clip-text text-transparent">Nộp bài Task</h1>
            <Link
              href="/candidate"
              className="px-4 py-2 text-gray-600 hover:text-violet-600 hover:bg-violet-50 rounded-xl transition-colors"
            >
              ← Quay lại
            </Link>
          </div>
        </div>
      </header>

      {/* Content */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Task Info */}
        <div className="bg-white/80 backdrop-blur-sm rounded-2xl border border-violet-100 shadow-lg shadow-violet-50 p-6 mb-6">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <span className={`px-3 py-1 text-xs font-bold rounded-xl ${
                userTask.task.type === 'core' ? 'bg-gradient-to-r from-rose-100 to-pink-100 text-rose-700' : 'bg-gradient-to-r from-cyan-100 to-teal-100 text-cyan-700'
              }`}>
                {userTask.task.type === 'core' ? 'CORE' : 'BOUNTY'}
              </span>
              <span className="text-sm text-emerald-600 font-bold">
                +{userTask.task.xp_reward} XP
              </span>
            </div>
            {(userTask.task as any).creator_name && (
              <div className="px-3 py-1.5 bg-violet-100 text-violet-700 rounded-lg text-xs font-medium whitespace-nowrap">
                👤 Tạo bởi: {(userTask.task as any).creator_name}
              </div>
            )}
          </div>
          <h2 className="text-xl font-bold text-gray-900 mb-3">{userTask.task.title}</h2>
          <p className="text-gray-600 mb-4">{userTask.task.description}</p>
          
          {userTask.task.instructions && (
            <div className="bg-gradient-to-r from-cyan-50 to-teal-50 border border-cyan-200 rounded-xl p-4 mb-4">
              <h3 className="font-bold text-cyan-800 mb-2">Hướng dẫn:</h3>
              <div className="text-gray-700 whitespace-pre-wrap">{userTask.task.instructions}</div>
            </div>
          )}

          {userTask.task.reference_links.length > 0 && (
            <div className="mb-4">
              <h3 className="font-bold text-gray-900 mb-2">Tài liệu tham khảo:</h3>
              <ul className="list-disc list-inside space-y-1">
                {userTask.task.reference_links.map((link, idx) => (
                  <li key={idx}>
                    <a href={link} target="_blank" rel="noopener noreferrer" className="text-violet-600 hover:text-fuchsia-600 hover:underline transition-colors">
                      {link}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {userTask.task.skill_tags.length > 0 && (
            <div>
              <h3 className="font-bold text-gray-900 mb-2">Kỹ năng:</h3>
              <div className="flex flex-wrap gap-2">
                {userTask.task.skill_tags.map((skill, idx) => (
                  <span key={idx} className="px-3 py-1 bg-gradient-to-r from-violet-100 to-fuchsia-100 text-violet-700 text-sm rounded-xl font-medium">
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Submit Form */}
        <div className="bg-white/80 backdrop-blur-sm rounded-2xl border border-violet-100 shadow-lg shadow-violet-50 p-6">
          <h3 className="text-lg font-bold bg-gradient-to-r from-violet-600 to-fuchsia-600 bg-clip-text text-transparent mb-4">Nộp bài làm</h3>
          
          {userTask.status === 'submitted' && (
            <div className="mb-4 p-4 bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200 rounded-xl">
              <p className="text-amber-800 font-medium">
                Bài của bạn đã được nộp và AI đang xử lý điểm.
              </p>
              {userTask.submitted_at && (
                <p className="text-sm text-amber-700 mt-1">
                  Thời gian nộp: {new Date(userTask.submitted_at).toLocaleString('vi-VN')}
                </p>
              )}
            </div>
          )}

          {userTask.status === 'rejected' && (
            <div className="mb-4 p-4 bg-gradient-to-r from-rose-50 to-pink-50 border border-rose-200 rounded-xl">
              <p className="text-rose-800 font-bold">✗ Bài làm chưa đạt yêu cầu</p>
              {userTask.mentor_comment && (
                <p className="text-rose-700 mt-2">
                  <span className="font-semibold">Nhận xét:</span> {userTask.mentor_comment}
                </p>
              )}
              <p className="text-rose-700 mt-2">Vui lòng hoàn thiện và nộp lại.</p>
            </div>
          )}

          {userTask.ai_score !== null && userTask.ai_score !== undefined && (
            <div className="mb-4 p-4 bg-violet-50 border border-violet-200 rounded-xl">
              <p className="text-violet-800 font-semibold">AI score: {userTask.ai_score.toFixed(1)}/100</p>
              {userTask.ai_feedback && (
                <p className="text-sm text-violet-700 mt-1">{userTask.ai_feedback}</p>
              )}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
              <div>
                <label htmlFor="progress" className="block text-sm font-semibold text-gray-700 mb-2">
                  Tiến độ hiện tại
                </label>
                <input
                  type="number"
                  id="progress"
                  min={0}
                  max={100}
                  value={progressPercentage}
                  onChange={(e) => setProgressPercentage(Number(e.target.value))}
                  className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-violet-500 focus:border-violet-500 bg-gray-50/50 hover:bg-white transition-all"
                  disabled={userTask.status === 'completed'}
                />
              </div>
              <div>
                <label htmlFor="completion" className="block text-sm font-semibold text-gray-700 mb-2">
                  Mức hoàn thành khi nộp
                </label>
                <input
                  type="number"
                  id="completion"
                  min={0}
                  max={100}
                  value={completionPercentage}
                  onChange={(e) => setCompletionPercentage(Number(e.target.value))}
                  className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-violet-500 focus:border-violet-500 bg-gray-50/50 hover:bg-white transition-all"
                  disabled={userTask.status === 'completed'}
                />
              </div>
            </div>

            <div className="mb-4">
              <label htmlFor="proofLink" className="block text-sm font-semibold text-gray-700 mb-2">
                Link bài làm (tùy chọn)
              </label>
              <input
                type="url"
                id="proofLink"
                value={proofLink}
                onChange={(e) => setProofLink(e.target.value)}
                placeholder="https://github.com/your-repo hoặc link Google Drive"
                className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-violet-500 focus:border-violet-500 bg-gray-50/50 hover:bg-white transition-all"
                disabled={userTask.status === 'completed'}
              />
              <p className="text-sm text-gray-500 mt-1">
                Có thể là link Github, Google Drive, hoặc bất kỳ link nào chứa bài làm của bạn
              </p>
            </div>

            <div className="mb-4">
              <label htmlFor="evidenceLinks" className="block text-sm font-semibold text-gray-700 mb-2">
                Evidence links
              </label>
              <textarea
                id="evidenceLinks"
                value={evidenceLinks}
                onChange={(e) => setEvidenceLinks(e.target.value)}
                rows={3}
                placeholder="Mỗi link một dòng"
                className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-violet-500 focus:border-violet-500 bg-gray-50/50 hover:bg-white transition-all"
                disabled={userTask.status === 'completed'}
              />
            </div>

            <div className="mb-6">
              <label htmlFor="notes" className="block text-sm font-semibold text-gray-700 mb-2">
                Ghi chú (tùy chọn)
              </label>
              <textarea
                id="notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={4}
                placeholder="Mô tả ngắn về bài làm, minh chứng, hoặc nội dung bài làm..."
                className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-violet-500 focus:border-violet-500 bg-gray-50/50 hover:bg-white transition-all"
                disabled={userTask.status === 'completed'}
              />
              <p className="text-sm text-gray-500 mt-1">
                Nhập nội dung bài làm hoặc ghi chú minh chứng ở đây
              </p>
            </div>

            {userTask.status !== 'completed' && (
              <div className="flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={handleSaveProgress}
                  disabled={savingProgress}
                  className="px-6 py-2.5 bg-[#1E90FF] text-white rounded-xl hover:bg-[#1a7de0] disabled:opacity-50 font-semibold shadow-lg shadow-blue-100 transition-all"
                >
                  {savingProgress ? 'Đang lưu...' : 'Lưu tiến độ'}
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-6 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-500 text-white rounded-xl hover:from-emerald-600 hover:to-teal-600 disabled:opacity-50 font-semibold shadow-lg shadow-emerald-100 transition-all"
                >
                  {submitting ? 'Đang nộp...' : 'Nộp bài'}
                </button>
                <Link
                  href="/candidate"
                  className="px-6 py-2.5 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200 font-medium transition-colors"
                >
                  Hủy
                </Link>
              </div>
            )}

            {userTask.status === 'completed' && (
              <div className="p-4 bg-gradient-to-r from-emerald-50 to-teal-50 border border-emerald-200 rounded-xl">
                <p className="text-emerald-800 font-bold">✓ Bài làm đã được duyệt!</p>
                <p className="text-sm text-emerald-700 mt-1">Bạn đã nhận được <span className="font-bold">{userTask.xp_earned} XP</span></p>
                {userTask.mentor_comment && (
                  <p className="text-gray-700 mt-2">
                    <span className="font-semibold">Nhận xét:</span> {userTask.mentor_comment}
                  </p>
                )}
              </div>
            )}
          </form>
        </div>
      </div>
    </div>
  );
}
