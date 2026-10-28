'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { apiClient } from '@/lib/api';
import { User, UserListResponse } from '@/types';
import Link from 'next/link';

const ROLE_COLORS: Record<string, string> = {
  admin: 'bg-red-100 text-red-700 border-red-200',
  mentor: 'bg-purple-100 text-purple-700 border-purple-200',
  member: 'bg-blue-100 text-blue-700 border-blue-200',
  candidate: 'bg-gray-100 text-gray-700 border-gray-200',
};

const STATUS_COLORS: Record<string, string> = {
  active: 'bg-green-100 text-green-700',
  inactive: 'bg-gray-100 text-gray-700',
};

export default function UsersDirectoryPage() {
  const router = useRouter();
  const { user: currentUser, isLoading: authLoading } = useAuth();
  
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [roleFilter, setRoleFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('active');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const pageSize = 20;

  const loadUsers = useCallback(async () => {
    try {
      setLoading(true);
      const params: any = {
        page,
        page_size: pageSize,
      };
      
      if (roleFilter !== 'all') {
        params.role = roleFilter;
      }
      
      if (statusFilter) {
        params.status = statusFilter;
      }
      
      if (searchTerm.trim()) {
        params.search = searchTerm.trim();
      }

      const data: UserListResponse = await apiClient.getUsers(params);
      setUsers(data.users || []);
      setTotal(data.total || 0);
    } catch (error: any) {
      console.error('Failed to load users:', error);
      // If not admin, try to get users without admin endpoint
      if (error.response?.status === 403) {
        // Non-admin users can't access user list
      }
    } finally {
      setLoading(false);
    }
  }, [page, roleFilter, statusFilter, searchTerm]);

  useEffect(() => {
    if (!authLoading && currentUser) {
      loadUsers();
    }
  }, [authLoading, currentUser, loadUsers]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadUsers();
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold bg-gradient-to-r from-violet-600 to-fuchsia-600 bg-clip-text text-transparent">
                Danh sách thành viên
              </h1>
              <p className="text-sm text-gray-500 mt-0.5">
                {total} thành viên được tìm thấy
              </p>
            </div>
            <button
              onClick={() => router.push('/dashboard')}
              className="px-4 py-2 text-sm text-gray-600 hover:text-violet-600 hover:bg-violet-50 rounded-lg transition-colors font-medium"
            >
              ← Quay lại
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {/* Search & Filters */}
        <div className="bg-white rounded-xl shadow-md p-5">
          <form onSubmit={handleSearch} className="flex flex-col md:flex-row gap-4">
            <div className="flex-1">
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Tìm kiếm theo tên, email, MSSV..."
                className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-violet-500 focus:border-violet-500 bg-gray-50 hover:bg-white transition-all"
              />
            </div>
            <select
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value)}
              className="px-4 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-violet-500 focus:border-violet-500 bg-white"
            >
              <option value="all">Tất cả vai trò</option>
              <option value="admin">Admin</option>
              <option value="mentor">Mentor</option>
              <option value="member">Member</option>
              <option value="candidate">Candidate</option>
            </select>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-4 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-violet-500 focus:border-violet-500 bg-white"
            >
              <option value="active">Đang hoạt động</option>
              <option value="inactive">Không hoạt động</option>
              <option value="">Tất cả</option>
            </select>
            <button
              type="submit"
              className="px-6 py-2.5 bg-gradient-to-r from-violet-600 to-fuchsia-600 text-white rounded-lg hover:from-violet-700 hover:to-fuchsia-700 font-semibold shadow-md transition-all"
            >
              Tìm kiếm
            </button>
          </form>
        </div>

        {/* Users Grid */}
        {loading ? (
          <div className="flex justify-center items-center py-20">
            <div className="text-center">
              <div className="w-12 h-12 border-4 border-gray-200 border-t-violet-600 rounded-full animate-spin mx-auto mb-4"></div>
              <p className="text-gray-500">Đang tải...</p>
            </div>
          </div>
        ) : users.length === 0 ? (
          <div className="bg-white rounded-xl shadow-md p-12 text-center">
            <div className="text-6xl mb-4">🔍</div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Không tìm thấy kết quả</h3>
            <p className="text-gray-500">Thử thay đổi từ khóa tìm kiếm hoặc bộ lọc</p>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {users.map((user) => {
                const displayLevel = user.roles.includes('mentor') || user.roles.includes('admin') ? 99 : user.level;
                const primaryRole = user.roles[0] || 'candidate';
                
                return (
                  <div
                    key={user.id}
                    className="bg-white rounded-xl shadow-md hover:shadow-xl transition-all duration-300 overflow-hidden group cursor-pointer"
                    onClick={() => router.push(`/profile/${user.id}`)}
                  >
                    {/* Card Header with Gradient */}
                    <div className="h-20 bg-gradient-to-r from-violet-500 to-fuchsia-500 relative">
                      <div className="absolute -bottom-8 left-4">
                        <div className="w-16 h-16 rounded-full border-4 border-white bg-gradient-to-br from-violet-400 to-fuchsia-400 flex items-center justify-center text-white text-2xl font-bold shadow-lg">
                          {(user.full_name || user.email)[0]?.toUpperCase()}
                        </div>
                      </div>
                    </div>

                    {/* Card Body */}
                    <div className="pt-10 p-4">
                      <h3 className="font-bold text-gray-900 truncate group-hover:text-violet-600 transition-colors">
                        {user.full_name || 'User'}
                      </h3>
                      <p className="text-sm text-gray-500 truncate mb-3">{user.email}</p>

                      <div className="flex flex-wrap gap-1.5 mb-3">
                        <span className={`px-2 py-0.5 text-xs font-medium rounded-full border ${ROLE_COLORS[primaryRole] || ROLE_COLORS.candidate}`}>
                          {primaryRole}
                        </span>
                        <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${STATUS_COLORS[user.status] || STATUS_COLORS.active}`}>
                          {user.status === 'active' ? '● Active' : '○ Inactive'}
                        </span>
                      </div>

                      <div className="flex items-center justify-between pt-3 border-t border-gray-100">
                        <div>
                          <p className="text-xs text-gray-500">Level {displayLevel}</p>
                          <p className="text-sm font-semibold text-violet-600">{user.current_xp} XP</p>
                        </div>
                        {user.student_id && (
                          <div className="text-right">
                            <p className="text-xs text-gray-500">MSSV</p>
                            <p className="text-sm font-medium text-gray-700">{user.student_id}</p>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="bg-white rounded-xl shadow-md p-4 flex items-center justify-between">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  ← Trước
                </button>
                
                <div className="flex items-center gap-2">
                  {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                    let pageNum;
                    if (totalPages <= 5) {
                      pageNum = i + 1;
                    } else if (page <= 3) {
                      pageNum = i + 1;
                    } else if (page >= totalPages - 2) {
                      pageNum = totalPages - 4 + i;
                    } else {
                      pageNum = page - 2 + i;
                    }
                    
                    return (
                      <button
                        key={pageNum}
                        onClick={() => setPage(pageNum)}
                        className={`w-10 h-10 rounded-lg text-sm font-medium transition-colors ${
                          page === pageNum
                            ? 'bg-gradient-to-r from-violet-600 to-fuchsia-600 text-white'
                            : 'text-gray-700 hover:bg-gray-100'
                        }`}
                      >
                        {pageNum}
                      </button>
                    );
                  })}
                </div>

                <button
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Sau →
                </button>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
