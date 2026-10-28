'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { apiClient } from '@/lib/api';
import { MemberLevel, User, UserRole, UserStatus, UserStatsResponse } from '@/types';
import { ForceSyncAllUsersResponse } from '@/types/schedule';

const ROLE_LABELS: Record<UserRole, string> = {
  candidate: 'Thực tập viên',
  member: 'Thành viên',
  mentor: 'Mentor',
  admin: 'Admin',
};

const STATUS_LABELS: Record<UserStatus, string> = {
  active: 'Hoạt động',
  inactive: 'Không hoạt động',
  suspended: 'Đình chỉ',
};

const MEMBER_LEVEL_LABELS: Record<MemberLevel, string> = {
  new: 'Thành viên mới',
  diligent: 'Chuyên cần',
  official: 'Chính thức',
};

export default function AdminUsersPage() {
  const router = useRouter();
  const { user, isLoading: authLoading, refreshUser } = useAuth();
  
  const [users, setUsers] = useState<User[]>([]);
  const [stats, setStats] = useState<UserStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  
  const [filterRole, setFilterRole] = useState<UserRole | ''>('');
  const [filterStatus, setFilterStatus] = useState<UserStatus | ''>('');
  const [searchQuery, setSearchQuery] = useState('');
  
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [selectedRole, setSelectedRole] = useState<UserRole>('candidate');
  const [newStatus, setNewStatus] = useState<UserStatus>('active');
  const [newMemberLevel, setNewMemberLevel] = useState<MemberLevel>('new');
  const [saving, setSaving] = useState(false);
  const [syncingSchedules, setSyncingSchedules] = useState(false);
  const [syncResult, setSyncResult] = useState<ForceSyncAllUsersResponse | null>(null);
  const [syncError, setSyncError] = useState('');
  const [importingUsers, setImportingUsers] = useState(false);
  const [importResult, setImportResult] = useState<any | null>(null);
  const [importError, setImportError] = useState('');
  const [syncingStudentIds, setSyncingStudentIds] = useState(false);
  const [syncStudentIdsResult, setSyncStudentIdsResult] = useState<any | null>(null);
  const [syncStudentIdsError, setSyncStudentIdsError] = useState('');
  const [showSyncModal, setShowSyncModal] = useState(false);
  const [selectedUserIds, setSelectedUserIds] = useState<string[]>([]);
  const [selectAllUsers, setSelectAllUsers] = useState(false);
  const [creatingLimitQuest, setCreatingLimitQuest] = useState(false);
  const [limitQuestMessage, setLimitQuestMessage] = useState('');
  const [limitQuestError, setLimitQuestError] = useState('');
  const [limitQuestForm, setLimitQuestForm] = useState({
    targetUserId: '',
    title: 'Coaching 1:1 với giáo viên',
    description: 'Tham gia buổi coaching 1:1 hoặc họp offline và nộp ảnh minh chứng.',
    xpReward: '100',
    expiresAt: '',
  });

  const fetchUsers = useCallback(async () => {
    try {
      setLoading(true);
      setError('');
      
      const response = await apiClient.listUsers({
        page,
        page_size: 10,
        role: filterRole || undefined,
        status: filterStatus || undefined,
        search: searchQuery || undefined,
      });
      
      setUsers(response.users);
      setTotal(response.total);
      setTotalPages(response.total_pages);
    } catch (err: any) {
      console.error('Error fetching users:', err);
      if (err.response?.status === 403) {
        setError('Bạn không có quyền truy cập trang này');
      } else {
        setError(err.response?.data?.detail || 'Không thể tải danh sách người dùng');
      }
    } finally {
      setLoading(false);
    }
  }, [page, filterRole, filterStatus, searchQuery]);

  const fetchStats = useCallback(async () => {
    try {
      const response = await apiClient.getUserStatsByRole();
      setStats(response);
    } catch (err) {
      console.error('Error fetching stats:', err);
    }
  }, []);

  const hasRole = (role: string) => user?.roles?.includes(role as any) ?? false;

  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login');
      return;
    }
    
    if (user && !hasRole('admin')) {
      setError('Chỉ Admin mới có quyền truy cập trang này');
      setLoading(false);
      return;
    }
    
    if (user && hasRole('admin')) {
      fetchUsers();
      fetchStats();
    }
  }, [user, authLoading, router, fetchUsers, fetchStats]);

  const handleEditUser = (u: User) => {
    setEditingUser(u);
    setSelectedRole(u.primary_role || u.roles?.[0] || 'candidate');
    setNewStatus(u.status);
    setNewMemberLevel(u.member_level || 'new');
  };

  const handleSaveChanges = async () => {
    if (!editingUser) return;
    
    setSaving(true);
    try {
      let updatedUser = editingUser;
      
      const rolesChanged = selectedRole !== editingUser.primary_role;
      if (rolesChanged) {
        updatedUser = await apiClient.updateUserRoles(editingUser.id, [selectedRole]);
      }
      
      const isSelf = editingUser.id === user?.id;
      if (!isSelf && newStatus !== editingUser.status) {
        updatedUser = await apiClient.updateUserStatus(editingUser.id, newStatus);
      }

      if (newMemberLevel !== (editingUser.member_level || 'new')) {
        updatedUser = await apiClient.updateUserMemberLevel(editingUser.id, newMemberLevel);
      }
      
      setUsers(users.map((u: User) => u.id === updatedUser.id ? updatedUser : u));
      setEditingUser(null);
      
      if (isSelf) {
        await refreshUser();
      }
      
      fetchStats();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Không thể cập nhật người dùng');
    } finally {
      setSaving(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchUsers();
  };

  const handleForceSyncSchedules = async () => {
    try {
      setSyncingSchedules(true);
      setSyncError('');
      setSyncResult(null);

      const result = await apiClient.forceSyncAllUsersSchedules();
      setSyncResult(result);

      if (!result.success) {
        setSyncError(result.error || result.message || 'Đồng bộ lịch thất bại');
      }
    } catch (err: any) {
      setSyncError(err.response?.data?.detail || err.message || 'Không thể force sync lịch');
    } finally {
      setSyncingSchedules(false);
    }
  };

  const handleImportUsers = async () => {
    try {
      setImportingUsers(true);
      setImportError('');
      setImportResult(null);

      const importSecret = prompt('Nhập secret token để xác thực import users:');
      if (!importSecret) {
        setImportingUsers(false);
        return;
      }

      // Get token from cookies (same as apiClient does)
      const token = document.cookie
        .split('; ')
        .find(row => row.startsWith('accessToken='))
        ?.split('=')[1];

      if (!token) {
        throw new Error('Không tìm thấy access token. Vui lòng đăng nhập lại.');
      }

      const response = await fetch('/api/v1/admin/import-users', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Import-Secret': importSecret,
          'Authorization': `Bearer ${token}`,
        },
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || result.message || 'Import thất bại');
      }

      setImportResult(result);

      if (result.success) {
        fetchUsers();
        fetchStats();
      }
    } catch (err: any) {
      setImportError(err.message || 'Không thể import users');
    } finally {
      setImportingUsers(false);
    }
  };

  const handleSyncStudentIds = async (selectedIds?: string[]) => {
    try {
      setSyncingStudentIds(true);
      setSyncStudentIdsError('');
      setSyncStudentIdsResult(null);

      const token = document.cookie
        .split('; ')
        .find(row => row.startsWith('accessToken='))
        ?.split('=')[1];

      if (!token) {
        throw new Error('Không tìm thấy access token. Vui lòng đăng nhập lại.');
      }

      // If selectedIds provided and not empty, use them; otherwise sync all users in the table
      const hasSelectedIds = selectedIds && selectedIds.length > 0;
      const requestBody = hasSelectedIds
        ? JSON.stringify({ user_ids: selectedIds })
        : undefined; // Sync all when no specific IDs provided

      const response = await fetch('/api/v1/admin/sync-student-ids', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: requestBody,
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || result.message || 'Đồng bộ thất bại');
      }

      setSyncStudentIdsResult(result);

      if (result.success) {
        fetchUsers();
        fetchStats();
        setShowSyncModal(false);
        setSelectedUserIds([]);
        setSelectAllUsers(false);
      }
    } catch (err: any) {
      setSyncStudentIdsError(err.message || 'Không thể đồng bộ mã sinh viên');
    } finally {
      setSyncingStudentIds(false);
    }
  };

  const toggleUserSelection = (userId: string) => {
    setSelectedUserIds(prev => 
      prev.includes(userId) 
        ? prev.filter(id => id !== userId)
        : [...prev, userId]
    );
  };

  const toggleSelectAll = () => {
    if (selectAllUsers) {
      setSelectedUserIds([]);
    } else {
      setSelectedUserIds(users.map(u => u.id));
    }
    setSelectAllUsers(!selectAllUsers);
  };

  const eligibleLimitQuestUsers = users.filter((u) =>
    u.roles?.some((role) => role === 'candidate' || role === 'member')
  );

  const handleCreateLimitQuest = async (event: React.FormEvent) => {
    event.preventDefault();
    const targetUserId = limitQuestForm.targetUserId || eligibleLimitQuestUsers[0]?.id;
    if (!targetUserId) {
      setLimitQuestError('Chọn user candidate/member để tạo Limit Quest');
      return;
    }

    try {
      setCreatingLimitQuest(true);
      setLimitQuestMessage('');
      setLimitQuestError('');
      const result = await apiClient.createLimitQuest({
        target_user_ids: [targetUserId],
        title: limitQuestForm.title.trim(),
        description: limitQuestForm.description.trim(),
        difficulty: 'medium',
        xp_reward: Number(limitQuestForm.xpReward) || 100,
        expires_at: limitQuestForm.expiresAt ? new Date(limitQuestForm.expiresAt).toISOString() : undefined,
        auto_pass_score: 70,
      });
      setLimitQuestMessage(`Đã tạo ${result.created_count} Limit Quest`);
    } catch (err: any) {
      setLimitQuestError(err.response?.data?.detail || 'Không thể tạo Limit Quest');
    } finally {
      setCreatingLimitQuest(false);
    }
  };

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="w-6 h-6 border-2 border-gray-300 border-t-[#1E90FF] rounded-full animate-spin"></div>
      </div>
    );
  }

  if (!user || !hasRole('admin')) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
        <div className="bg-white border border-red-200 rounded-xl p-6 max-w-md w-full shadow-sm">
          <h2 className="text-lg font-semibold text-red-600 mb-2">Không có quyền truy cập</h2>
          <p className="text-sm text-gray-600 mb-4">Chỉ Admin mới có quyền truy cập trang quản lý người dùng.</p>
          <button
            onClick={() => router.push('/dashboard')}
            className="w-full px-4 py-2 bg-[#1E90FF] text-white rounded-lg hover:bg-[#1a7de0] text-sm font-medium transition-colors"
          >
            Quay về Dashboard
          </button>
        </div>
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
              <h1 className="text-xl font-semibold text-gray-900">Quản lý người dùng</h1>
              <p className="text-sm text-gray-500 mt-0.5">Phân quyền và quản lý trạng thái</p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowSyncModal(true)}
                className="px-3 py-2 text-sm bg-[#dc2626] text-white rounded-lg hover:bg-[#c21a1a] transition-colors"
              >
                Đồng bộ Mã Sinh Viên
              </button>
              <button
                onClick={handleImportUsers}
                disabled={importingUsers}
                className="px-3 py-2 text-sm bg-[#9333ea] text-white rounded-lg hover:bg-[#7e2cc9] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {importingUsers ? 'Đang import...' : 'Import Users từ MongoDB'}
              </button>
              <button
                onClick={handleForceSyncSchedules}
                disabled={syncingSchedules}
                className="px-3 py-2 text-sm bg-[#0f766e] text-white rounded-lg hover:bg-[#0d675f] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {syncingSchedules ? 'Đang đồng bộ...' : 'Force Sync Lịch'}
              </button>
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
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Tổng số</p>
              <p className="text-2xl font-semibold text-[#1E90FF] mt-1">{stats.total}</p>
            </div>
            {(Object.keys(ROLE_LABELS) as UserRole[]).map((role) => (
              <div key={role} className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{ROLE_LABELS[role]}</p>
                <p className="text-2xl font-semibold text-gray-900 mt-1">{stats.by_role[role] || 0}</p>
              </div>
            ))}
          </div>
        )}

        {/* Limit Quest */}
        <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
          <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-4">
            <div className="min-w-0">
              <h2 className="text-base font-semibold text-gray-900">Tạo Limit Quest</h2>
              <p className="text-sm text-gray-500 mt-1">Dành cho coaching 1:1 hoặc buổi họp offline có ảnh minh chứng.</p>
            </div>
            <form onSubmit={handleCreateLimitQuest} className="grid gap-3 lg:grid-cols-[220px_220px_110px_190px_auto] lg:items-end flex-1">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Người nhận</label>
                <select
                  value={limitQuestForm.targetUserId}
                  onChange={(event) => setLimitQuestForm((current) => ({ ...current, targetUserId: event.target.value }))}
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1E90FF] focus:border-[#1E90FF] text-sm"
                >
                  <option value="">Chọn user</option>
                  {eligibleLimitQuestUsers.map((u) => (
                    <option key={u.id} value={u.id}>{u.full_name || u.email}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Tiêu đề</label>
                <input
                  value={limitQuestForm.title}
                  onChange={(event) => setLimitQuestForm((current) => ({ ...current, title: event.target.value }))}
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1E90FF] focus:border-[#1E90FF] text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">XP</label>
                <input
                  type="number"
                  min="0"
                  max="500"
                  value={limitQuestForm.xpReward}
                  onChange={(event) => setLimitQuestForm((current) => ({ ...current, xpReward: event.target.value }))}
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1E90FF] focus:border-[#1E90FF] text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Hạn nộp</label>
                <input
                  type="datetime-local"
                  value={limitQuestForm.expiresAt}
                  onChange={(event) => setLimitQuestForm((current) => ({ ...current, expiresAt: event.target.value }))}
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1E90FF] focus:border-[#1E90FF] text-sm"
                />
              </div>
              <button
                type="submit"
                disabled={creatingLimitQuest}
                className="px-4 py-2.5 bg-[#1E90FF] text-white rounded-lg hover:bg-[#1a7de0] disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium transition-colors"
              >
                {creatingLimitQuest ? 'Đang tạo...' : 'Tạo quest'}
              </button>
              <div className="lg:col-span-5">
                <label className="block text-xs font-medium text-gray-600 mb-1">Mô tả</label>
                <textarea
                  rows={2}
                  value={limitQuestForm.description}
                  onChange={(event) => setLimitQuestForm((current) => ({ ...current, description: event.target.value }))}
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1E90FF] focus:border-[#1E90FF] text-sm"
                />
              </div>
            </form>
          </div>
          {limitQuestMessage && (
            <div className="mt-3 bg-emerald-50 border border-emerald-200 text-emerald-800 px-4 py-2 rounded-lg text-sm">
              {limitQuestMessage}
            </div>
          )}
          {limitQuestError && (
            <div className="mt-3 bg-red-50 border border-red-200 text-red-700 px-4 py-2 rounded-lg text-sm">
              {limitQuestError}
            </div>
          )}
        </div>

        {/* Filters */}
        <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
          <form onSubmit={handleSearch} className="flex flex-col sm:flex-row gap-3">
            <div className="flex-1">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Tìm theo tên hoặc email..."
                className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1E90FF] focus:border-[#1E90FF] text-sm"
              />
            </div>
            
            <select
              value={filterRole}
              onChange={(e) => { setFilterRole(e.target.value as UserRole | ''); setPage(1); }}
              className="px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1E90FF] focus:border-[#1E90FF] text-sm"
            >
              <option value="">Tất cả quyền</option>
              {(Object.keys(ROLE_LABELS) as UserRole[]).map((role) => (
                <option key={role} value={role}>{ROLE_LABELS[role]}</option>
              ))}
            </select>
            
            <select
              value={filterStatus}
              onChange={(e) => { setFilterStatus(e.target.value as UserStatus | ''); setPage(1); }}
              className="px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1E90FF] focus:border-[#1E90FF] text-sm"
            >
              <option value="">Tất cả trạng thái</option>
              {(Object.keys(STATUS_LABELS) as UserStatus[]).map((status) => (
                <option key={status} value={status}>{STATUS_LABELS[status]}</option>
              ))}
            </select>
            
            <button
              type="submit"
              className="px-4 py-2.5 bg-[#1E90FF] text-white rounded-lg hover:bg-[#1a7de0] text-sm font-medium transition-colors"
            >
              Tìm
            </button>
          </form>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl text-sm">
            {error}
          </div>
        )}

        {syncError && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl text-sm">
            {syncError}
          </div>
        )}

        {importError && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl text-sm">
            {importError}
          </div>
        )}

        {syncStudentIdsError && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl text-sm">
            {syncStudentIdsError}
          </div>
        )}

        {syncResult?.success && (
          <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 px-4 py-3 rounded-xl text-sm space-y-1">
            <p className="font-medium">{syncResult.message}</p>
            <p>
              Tuần: {syncResult.week_start || '-'} | Tổng: {syncResult.total_users ?? 0} | Thành công: {syncResult.success_count ?? 0} | Lỗi: {syncResult.error_count ?? 0}
            </p>
            {!!syncResult.failed_users?.length && (
              <p className="text-emerald-900">
                Có {syncResult.failed_users.length} user lỗi. Kiểm tra backend logs để xem chi tiết.
              </p>
            )}
          </div>
        )}

        {importResult?.success && (
          <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 px-4 py-3 rounded-xl text-sm space-y-1">
            <p className="font-medium">{importResult.message}</p>
            <p>
              MongoDB: {importResult.total_in_mongodb ?? 0} users | Đã import: {importResult.imported_count ?? 0} | Bỏ qua: {importResult.skipped_count ?? 0} | Lỗi: {importResult.error_count ?? 0}
            </p>
            {!!importResult.errors?.length && (
              <details className="mt-2">
                <summary className="cursor-pointer text-emerald-900 font-medium">Xem danh sách lỗi ({importResult.errors.length})</summary>
                <ul className="mt-2 list-disc list-inside text-emerald-900">
                  {importResult.errors.slice(0, 10).map((err: string, i: number) => (
                    <li key={i}>{err}</li>
                  ))}
                </ul>
              </details>
            )}
          </div>
        )}

        {syncStudentIdsResult?.success && (
          <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 px-4 py-3 rounded-xl text-sm space-y-1">
            <p className="font-medium">{syncStudentIdsResult.message}</p>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2 mt-2 text-xs">
              <div className="bg-emerald-100 rounded p-2">
                <span className="font-medium">Tổng LHU:</span> {syncStudentIdsResult.total_in_lhu ?? 0}
              </div>
              <div className="bg-emerald-100 rounded p-2">
                <span className="font-medium">Match Email:</span> {syncStudentIdsResult.matched_by_email ?? 0}
              </div>
              <div className="bg-emerald-100 rounded p-2">
                <span className="font-medium">Match Phone:</span> {syncStudentIdsResult.matched_by_phone ?? 0}
              </div>
              <div className="bg-emerald-100 rounded p-2">
                <span className="font-medium">Đã cập nhật:</span> {syncStudentIdsResult.updated_count ?? 0}
              </div>
              <div className="bg-emerald-100 rounded p-2">
                <span className="font-medium">Bỏ qua:</span> {syncStudentIdsResult.skipped_count ?? 0}
              </div>
              <div className="bg-emerald-100 rounded p-2">
                <span className="font-medium">Lỗi:</span> {syncStudentIdsResult.error_count ?? 0}
              </div>
            </div>
            {!!syncStudentIdsResult.errors?.length && (
              <details className="mt-2">
                <summary className="cursor-pointer text-emerald-900 font-medium">Xem danh sách lỗi ({syncStudentIdsResult.errors.length})</summary>
                <ul className="mt-2 list-disc list-inside text-emerald-900">
                  {syncStudentIdsResult.errors.slice(0, 10).map((err: string, i: number) => (
                    <li key={i}>{err}</li>
                  ))}
                </ul>
              </details>
            )}
          </div>
        )}

        {/* Users Table */}
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[800px]">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">Người dùng</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">Quyền</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">Cấp thành viên</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">Trạng thái</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">XP / Level</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">Kỷ luật</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">Ngày tham gia</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wide">Thao tác</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {loading ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-12 text-center">
                      <div className="w-6 h-6 border-2 border-gray-300 border-t-[#1E90FF] rounded-full animate-spin mx-auto"></div>
                    </td>
                  </tr>
                ) : users.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-12 text-center text-sm text-gray-500">
                      Không tìm thấy người dùng nào
                    </td>
                  </tr>
                ) : (
                  users.map((u) => (
                    <tr key={u.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <div>
                          <p className="text-sm font-medium text-gray-900">{u.full_name || 'Chưa cập nhật'}</p>
                          <p className="text-xs text-gray-500">{u.email}</p>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-1">
                          {u.roles?.map((role) => (
                            <span key={role} className="px-2 py-0.5 bg-[#1E90FF]/10 text-[#1E90FF] rounded text-xs font-medium">
                              {ROLE_LABELS[role]}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className="px-2 py-0.5 bg-[#9333ea]/10 text-[#7e22ce] rounded text-xs font-medium">
                          {MEMBER_LEVEL_LABELS[u.member_level || 'new']}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                          u.status === 'active' ? 'bg-[#32CD32]/10 text-[#22c55e]' :
                          u.status === 'suspended' ? 'bg-red-100 text-red-600' :
                          'bg-gray-100 text-gray-700'
                        }`}>
                          {STATUS_LABELS[u.status]}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm">
                        <span className="text-[#9333ea] font-medium">{u.current_xp} XP</span>
                        <span className="text-gray-500"> / Lv.{u.level}</span>
                      </td>
                      <td className="px-4 py-3 text-sm text-[#32CD32] font-medium">
                        {u.discipline_score.toFixed(1)}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500">
                        {new Date(u.created_at).toLocaleDateString('vi-VN')}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={() => handleEditUser(u)}
                          className="text-sm text-[#1E90FF] hover:text-[#1a7de0] font-medium"
                        >
                          {u.id === user?.id ? 'Sửa (Bạn)' : 'Sửa'}
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
            <p className="text-sm text-gray-500">
              Hiển thị {users.length} / {total} người dùng
            </p>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage(Math.max(1, page - 1))}
                disabled={page === 1}
                className="px-3 py-2 border border-gray-300 rounded-lg disabled:opacity-50 hover:bg-gray-50 text-sm transition-colors"
              >
                Trước
              </button>
              <span className="px-3 py-2 text-sm text-gray-600">
                {page} / {totalPages}
              </span>
              <button
                onClick={() => setPage(Math.min(totalPages, page + 1))}
                disabled={page === totalPages}
                className="px-3 py-2 border border-gray-300 rounded-lg disabled:opacity-50 hover:bg-gray-50 text-sm transition-colors"
              >
                Sau
              </button>
            </div>
          </div>
        )}
      </main>

      {/* Edit Modal */}
      {editingUser && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md">
            <div className="p-5 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">Chỉnh sửa người dùng</h3>
            </div>
            
            <div className="p-5 space-y-4">
              <div>
                <p className="font-medium text-gray-900">{editingUser.full_name || editingUser.email}</p>
                <p className="text-sm text-gray-500">{editingUser.email}</p>
                {editingUser.id === user?.id && (
                  <p className="text-xs text-[#FFA500] mt-1">⚠️ Đây là tài khoản của bạn</p>
                )}
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Quyền</label>
                <div className="grid grid-cols-2 gap-2">
                  {(Object.keys(ROLE_LABELS) as UserRole[]).map((role) => {
                    const isSelf = editingUser.id === user?.id;
                    return (
                      <label
                        key={role}
                        className={`flex min-h-11 items-center gap-2 rounded-lg border px-3 py-2 text-sm transition-colors ${
                          selectedRole === role
                            ? 'border-blue-500 bg-blue-50 text-blue-700'
                            : 'border-gray-200 bg-white text-gray-700 hover:border-blue-200'
                        } ${isSelf ? 'cursor-not-allowed opacity-60' : 'cursor-pointer'}`}
                      >
                        <input
                          type="radio"
                          name="user-role"
                          checked={selectedRole === role}
                          onChange={() => setSelectedRole(role)}
                          disabled={isSelf}
                          className="h-4 w-4 border-gray-300 text-blue-600 focus:ring-blue-500 disabled:cursor-not-allowed"
                        />
                        <span className="font-medium">{ROLE_LABELS[role]}</span>
                      </label>
                    );
                  })}
                </div>
                <p className="mt-2 text-xs text-gray-500">Mỗi tài khoản chỉ có một quyền để tránh xung đột chức năng.</p>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">Trạng thái</label>
                <select
                  value={newStatus}
                  onChange={(e) => setNewStatus(e.target.value as UserStatus)}
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1E90FF] focus:border-[#1E90FF] text-sm"
                  disabled={editingUser.id === user?.id}
                >
                  {(Object.keys(STATUS_LABELS) as UserStatus[]).map((status) => (
                    <option key={status} value={status}>{STATUS_LABELS[status]}</option>
                  ))}
                </select>
                {editingUser.id === user?.id && (
                  <p className="text-xs text-gray-500 mt-1">Không thể thay đổi trạng thái của chính mình</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">Cấp thành viên</label>
                <select
                  value={newMemberLevel}
                  onChange={(e) => setNewMemberLevel(e.target.value as MemberLevel)}
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1E90FF] focus:border-[#1E90FF] text-sm"
                >
                  {(Object.keys(MEMBER_LEVEL_LABELS) as MemberLevel[]).map((memberLevel) => (
                    <option key={memberLevel} value={memberLevel}>{MEMBER_LEVEL_LABELS[memberLevel]}</option>
                  ))}
                </select>
              </div>
            </div>
            
            <div className="p-5 border-t border-gray-200 flex gap-3 bg-gray-50 rounded-b-xl">
              <button
                onClick={() => setEditingUser(null)}
                className="flex-1 px-4 py-2 text-gray-700 hover:bg-gray-200 rounded-lg text-sm transition-colors"
                disabled={saving}
              >
                Hủy
              </button>
              <button
                onClick={handleSaveChanges}
                className="flex-1 px-4 py-2 bg-[#1E90FF] text-white rounded-lg hover:bg-[#1a7de0] disabled:opacity-50 text-sm font-medium transition-colors"
                disabled={
                  saving ||
                  (
                    selectedRole === editingUser.primary_role &&
                    newStatus === editingUser.status &&
                    newMemberLevel === (editingUser.member_level || 'new')
                  )
                }
              >
                {saving ? 'Đang lưu...' : 'Lưu thay đổi'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Sync Student ID Modal */}
      {showSyncModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-4xl max-h-[80vh] flex flex-col">
            <div className="p-5 border-b border-gray-200 flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">Đồng bộ Mã Sinh Viên từ LHU</h3>
                <p className="text-sm text-gray-500 mt-1">Chọn users cần đồng bộ mã sinh viên</p>
              </div>
              <button
                onClick={() => setShowSyncModal(false)}
                className="text-gray-400 hover:text-gray-600 text-xl"
              >
                ✕
              </button>
            </div>

            <div className="p-5 flex-1 overflow-y-auto">
              {/* Select All */}
              <div className="flex items-center justify-between mb-3 pb-3 border-b border-gray-200">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={selectAllUsers}
                    onChange={toggleSelectAll}
                    className="w-4 h-4 text-[#1E90FF] border-gray-300 rounded focus:ring-[#1E90FF]"
                  />
                  <span className="text-sm font-medium text-gray-700">
                    Chọn tất cả ({users.length} users)
                  </span>
                </label>
                <span className="text-sm text-gray-500">
                  Đã chọn: {selectedUserIds.length}
                </span>
              </div>

              {/* User List */}
              <div className="space-y-2">
                {users.map((u) => (
                  <label
                    key={u.id}
                    className={`flex items-center gap-3 p-3 border rounded-lg cursor-pointer transition-colors ${
                      selectedUserIds.includes(u.id)
                        ? 'border-[#1E90FF] bg-[#1E90FF]/5'
                        : 'border-gray-200 hover:bg-gray-50'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={selectedUserIds.includes(u.id)}
                      onChange={() => toggleUserSelection(u.id)}
                      className="w-4 h-4 text-[#1E90FF] border-gray-300 rounded focus:ring-[#1E90FF]"
                    />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-900">
                        {u.full_name || 'Chưa cập nhật'}
                      </p>
                      <p className="text-xs text-gray-500">{u.email}</p>
                    </div>
                    <div className="text-right">
                      {u.student_id ? (
                        <span className="text-xs font-medium text-emerald-600 bg-emerald-50 px-2 py-1 rounded">
                          MSSV: {u.student_id}
                        </span>
                      ) : (
                        <span className="text-xs text-gray-400 bg-gray-100 px-2 py-1 rounded">
                          Chưa có MSSV
                        </span>
                      )}
                    </div>
                  </label>
                ))}
              </div>
            </div>

            <div className="p-5 border-t border-gray-200 flex gap-3 bg-gray-50 rounded-b-xl">
              <button
                onClick={() => setShowSyncModal(false)}
                className="flex-1 px-4 py-2 text-gray-700 hover:bg-gray-200 rounded-lg text-sm transition-colors"
              >
                Hủy
              </button>
              <button
                onClick={() => {
                  if (selectedUserIds.length === 0) {
                    alert('Vui lòng chọn ít nhất 1 user để đồng bộ mã sinh viên!');
                    return;
                  }
                  handleSyncStudentIds(selectedUserIds);
                }}
                disabled={syncingStudentIds || selectedUserIds.length === 0}
                className="flex-1 px-4 py-2 bg-[#dc2626] text-white rounded-lg hover:bg-[#c21a1a] disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium transition-colors"
              >
                {syncingStudentIds
                  ? `Đang đồng bộ ${selectedUserIds.length} users...`
                  : `Bắt đầu đồng bộ (${selectedUserIds.length} đã chọn)`}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
