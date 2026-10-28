'use client';

import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { apiClient } from '@/lib/api';
import { LeaderboardEntry, LeaderboardResponse, UserRankInfo } from '@/types/leaderboard';

const ROLE_LABELS: Record<string, string> = {
  candidate: 'Thực tập sinh',
  member: 'Thành viên',
  mentor: 'Mentor',
  admin: 'Admin',
};

export default function LeaderboardPage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();
  const [leaderboard, setLeaderboard] = useState<LeaderboardResponse | null>(null);
  const [myRankInfo, setMyRankInfo] = useState<UserRankInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [roleFilter, setRoleFilter] = useState<string>('');

  useEffect(() => {
    if (!isLoading && !user) {
      router.push('/login');
      return;
    }

    if (user) {
      loadData();
    }
  }, [isLoading, user, router, roleFilter]);

  const loadData = async () => {
    try {
      setLoading(true);
      const params = roleFilter ? { role: roleFilter, limit: 100 } : { limit: 100 };
      const [leaderboardData, rankData] = await Promise.all([
        apiClient.getLeaderboard(params),
        apiClient.getMyRank().catch(() => null),
      ]);
      setLeaderboard(leaderboardData);
      setMyRankInfo(rankData);
    } catch (error) {
      console.error('Failed to load leaderboard:', error);
    } finally {
      setLoading(false);
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
              <h1 className="text-xl font-semibold text-gray-900">Bảng xếp hạng</h1>
              <p className="text-sm text-gray-500 mt-0.5">Xếp hạng theo điểm kinh nghiệm (XP)</p>
            </div>
            <button
              onClick={() => router.push('/dashboard')}
              className="px-3 py-2 text-sm text-gray-600 hover:text-[#1E90FF] hover:bg-blue-50 rounded-lg transition-colors"
            >
              ← Quay lại
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-6 space-y-6">
        {/* My Rank Card */}
        {myRankInfo && (
          <div className="bg-gradient-to-r from-[#1E90FF] to-[#9333ea] rounded-xl p-5 text-white shadow-lg">
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <div>
                <p className="text-xs text-white/70 uppercase tracking-wide">Thứ hạng</p>
                <p className="text-2xl font-semibold mt-1">#{myRankInfo.rank}</p>
                <p className="text-xs text-white/70 mt-1">/ {myRankInfo.total_users} người</p>
              </div>
              <div>
                <p className="text-xs text-white/70 uppercase tracking-wide">Percentile</p>
                <p className="text-2xl font-semibold mt-1">{myRankInfo.percentile}%</p>
                <p className="text-xs text-white/70 mt-1">Cao hơn {myRankInfo.percentile}% users</p>
              </div>
              <div>
                <p className="text-xs text-white/70 uppercase tracking-wide">XP hiện tại</p>
                <p className="text-2xl font-semibold mt-1">{myRankInfo.current_xp}</p>
                <p className="text-xs text-white/70 mt-1">Điểm kinh nghiệm</p>
              </div>
              <div>
                <p className="text-xs text-white/70 uppercase tracking-wide">Đến hạng kế</p>
                <p className="text-2xl font-semibold mt-1">
                  {myRankInfo.xp_to_next_rank !== null && myRankInfo.xp_to_next_rank !== undefined
                    ? myRankInfo.xp_to_next_rank
                    : '—'}
                </p>
                <p className="text-xs text-white/70 mt-1">
                  {myRankInfo.xp_to_next_rank !== null && myRankInfo.xp_to_next_rank !== undefined
                    ? 'XP cần thêm'
                    : 'Bạn đang top 1!'}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm text-gray-600 mr-2">Lọc:</span>
            {[
              { value: '', label: 'Tất cả' },
              { value: 'candidate', label: 'Thực tập sinh' },
              { value: 'member', label: 'Thành viên' },
            ].map(({ value, label }) => (
              <button
                key={value}
                onClick={() => setRoleFilter(value)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  roleFilter === value 
                    ? 'bg-[#1E90FF] text-white shadow-sm' 
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {/* Leaderboard Table */}
        {loading ? (
          <div className="text-center py-12 text-gray-500">Đang tải...</div>
        ) : !leaderboard || leaderboard.entries.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-xl border border-gray-200 shadow-sm">
            <p className="text-gray-500">Chưa có dữ liệu xếp hạng</p>
          </div>
        ) : (
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[700px]">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-200">
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide w-20">Hạng</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">Thành viên</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide w-28">Vai trò</th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wide w-20">Level</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wide w-24">XP</th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wide w-20">Tasks</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide w-32">Kỷ luật</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {leaderboard.entries.map((entry) => (
                    <tr
                      key={entry.user_id}
                      className={`hover:bg-gray-50 transition-colors ${
                        user.id === entry.user_id ? 'bg-[#1E90FF]/5' : ''
                      }`}
                    >
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center justify-center w-8 h-8 rounded-full text-sm font-semibold ${
                          entry.rank === 1 ? 'bg-[#FFA500]/20 text-[#c2410c]' :
                          entry.rank === 2 ? 'bg-gray-200 text-gray-700' :
                          entry.rank === 3 ? 'bg-orange-100 text-orange-700' :
                          'bg-gray-100 text-gray-600'
                        }`}>
                          {entry.rank}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div>
                          <p className="text-sm font-medium text-gray-900">
                            {entry.full_name || entry.email}
                            {user.id === entry.user_id && (
                              <span className="ml-2 text-xs text-[#1E90FF]">(Bạn)</span>
                            )}
                          </p>
                          <p className="text-xs text-gray-500">{entry.email}</p>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className="px-2 py-1 bg-[#1E90FF]/10 text-[#1E90FF] rounded text-xs font-medium">
                          {ROLE_LABELS[entry.primary_role]}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className="text-sm font-semibold text-[#9333ea]">{entry.level}</span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className="text-sm font-semibold text-gray-900">{entry.current_xp}</span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className="text-sm text-gray-600">{entry.completed_tasks}</span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <span className="text-sm text-gray-900 w-8">{entry.discipline_score.toFixed(0)}</span>
                          <div className="flex-1 max-w-[60px] bg-gray-100 rounded-full h-1.5">
                            <div
                              className={`h-1.5 rounded-full ${
                                entry.discipline_score >= 80
                                  ? 'bg-[#32CD32]'
                                  : entry.discipline_score >= 50
                                  ? 'bg-[#FFA500]'
                                  : 'bg-red-500'
                              }`}
                              style={{ width: `${Math.min(entry.discipline_score, 100)}%` }}
                            ></div>
                          </div>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="bg-gray-50 px-4 py-3 border-t border-gray-200">
              <p className="text-xs text-gray-500 text-center">
                Hiển thị {leaderboard.entries.length} / {leaderboard.total_users} thành viên
              </p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
