'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { apiClient } from '@/lib/api';
import { User } from '@/types';
import Link from 'next/link';

// Cover images options
const COVER_IMAGES = [
  'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
  'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
  'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
  'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
  'linear-gradient(135deg, #30cfd0 0%, #330867 100%)',
  'linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)',
  'linear-gradient(135deg, #ff9a9e 0%, #fecfef 99%, #fecfef 100%)',
];

// Skills icons
const SKILL_ICONS: Record<string, string> = {
  react: '⚛️',
  javascript: '📜',
  typescript: '📘',
  python: '🐍',
  docker: '🐳',
  kubernetes: '☸️',
  aws: '☁️',
  azure: '🔷',
  frontend: '🎨',
  backend: '⚙️',
  database: '🗄️',
  devops: '🔄',
  ai: '🤖',
  ml: '🧠',
};

export default function ProfilePage() {
  const router = useRouter();
  const params = useParams();
  const { user: currentUser, isLoading: authLoading } = useAuth();
  
  // If no ID provided, redirect to own profile
  const userId = (params.id as string) || currentUser?.id;

  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<any>(null);

  useEffect(() => {
    if (!authLoading && currentUser && userId) {
      loadUserProfile();
    }
  }, [authLoading, currentUser, userId]);

  const loadUserProfile = async () => {
    try {
      setLoading(true);
      if (!userId) {
        router.push('/dashboard');
        return;
      }
      const userData = await apiClient.getUserById(userId);
      setUser(userData);

      // Load stats for the viewed user (only if viewing own profile or admin/mentor)
      if (userData.id === currentUser?.id || currentUser?.roles.includes('admin') || currentUser?.roles.includes('mentor')) {
        try {
          // For own profile, use getProfileStats
          if (userData.id === currentUser?.id) {
            const statsData = await apiClient.getProfileStats();
            setStats(statsData);
          } else {
            // For admin/mentor viewing others, we need a different endpoint
            // For now, just show basic user info
            setStats(null);
          }
        } catch (e) {
          console.log('Could not load detailed stats:', e);
          setStats(null);
        }
      } else {
        // Regular users viewing others - no stats access
        setStats(null);
      }
    } catch (error: any) {
      console.error('Failed to load user profile:', error);
      if (error.response?.status === 404) {
        alert('Không tìm thấy người dùng này');
        router.push('/dashboard');
      }
    } finally {
      setLoading(false);
    }
  };

  if (authLoading || loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-gray-200 border-t-[#667eea] rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-500">Đang tải profile...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  const isOwnProfile = user.id === currentUser?.id;
  const displayLevel = user.roles.includes('mentor') || user.roles.includes('admin') ? 99 : user.level;
  const xpForNextLevel = ((displayLevel - 1) * 100 + 100);
  const xpProgress = ((user.current_xp % 100) / 100) * 100;

  // Generate a consistent cover gradient based on user ID
  const coverGradient = COVER_IMAGES[(userId || user.id).split('').reduce((acc, char) => acc + char.charCodeAt(0), 0) % COVER_IMAGES.length];

  // Extract skills from evidence or use default based on role
  const skills = ['React', 'TypeScript', 'Node.js', 'Python'];

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      {/* Cover Image */}
      <div 
        className="h-48 md:h-64 w-full relative"
        style={{ background: coverGradient }}
      >
        <div className="absolute inset-0 bg-black/10"></div>
        
        {/* Navigation */}
        <nav className="absolute top-0 left-0 right-0 p-4 flex justify-between items-center">
          <button
            onClick={() => router.push(isOwnProfile ? '/dashboard' : '/mentor')}
            className="px-4 py-2 bg-white/90 backdrop-blur-sm rounded-full text-sm font-medium text-gray-700 hover:bg-white transition-colors shadow-lg"
          >
            ← Quay lại
          </button>
          <Link
            href="/users"
            className="px-4 py-2 bg-white/90 backdrop-blur-sm rounded-full text-sm font-medium text-gray-700 hover:bg-white transition-colors shadow-lg"
          >
            👥 Danh sách thành viên
          </Link>
        </nav>
      </div>

      {/* Profile Header */}
      <div className="max-w-5xl mx-auto px-4 -mt-20 relative z-10">
        <div className="bg-white rounded-2xl shadow-xl p-6 md:p-8">
          <div className="flex flex-col md:flex-row items-center md:items-end gap-6">
            {/* Avatar */}
            <div className="relative">
              <div className="w-32 h-32 md:w-40 md:h-40 rounded-full border-4 border-white shadow-2xl bg-gradient-to-br from-violet-500 to-fuchsia-500 flex items-center justify-center text-white text-5xl md:text-6xl font-bold">
                {(user.full_name || user.email)[0]?.toUpperCase()}
              </div>
              {user.status === 'active' && (
                <div className="absolute bottom-2 right-2 w-5 h-5 bg-green-500 border-4 border-white rounded-full"></div>
              )}
            </div>

            {/* Info */}
            <div className="flex-1 text-center md:text-left">
              <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">
                {user.full_name || 'User'}
              </h1>
              <p className="text-gray-500 mb-3">{user.email}</p>
              
              <div className="flex flex-wrap justify-center md:justify-start gap-2 mb-3">
                {user.roles.map((role) => (
                  <span
                    key={role}
                    className={`px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wide ${
                      role === 'admin' ? 'bg-red-100 text-red-700' :
                      role === 'mentor' ? 'bg-purple-100 text-purple-700' :
                      role === 'member' ? 'bg-blue-100 text-blue-700' :
                      'bg-gray-100 text-gray-700'
                    }`}
                  >
                    {role}
                  </span>
                ))}
              </div>

              {user.student_id && (
                <p className="text-sm text-gray-600">
                  <span className="font-medium">MSSV:</span> {user.student_id}
                </p>
              )}
            </div>

            {/* Level & XP */}
            <div className="text-center md:text-right">
              <div className="text-4xl font-bold bg-gradient-to-r from-violet-600 to-fuchsia-600 bg-clip-text text-transparent">
                Level {displayLevel}
              </div>
              <div className="mt-2 w-40 md:w-48">
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-gray-500">{user.current_xp} XP</span>
                  <span className="text-gray-400">/{xpForNextLevel}</span>
                </div>
                <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-violet-500 to-fuchsia-500 transition-all duration-500"
                    style={{ width: `${xpProgress}%` }}
                  />
                </div>
              </div>
              <p className="text-xs text-gray-400 mt-1">
                {100 - (user.current_xp % 100)} XP nữa để lên level {displayLevel + 1}
              </p>
            </div>
          </div>

          {/* Skills */}
          <div className="mt-8 pt-6 border-t border-gray-100">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Kỹ năng</h3>
            <div className="flex flex-wrap gap-2">
              {skills.map((skill) => (
                <span
                  key={skill}
                  className="px-3 py-1.5 bg-gradient-to-r from-violet-50 to-fuchsia-50 border border-violet-200 rounded-lg text-sm font-medium text-gray-700 hover:shadow-md transition-shadow cursor-default"
                >
                  {SKILL_ICONS[skill.toLowerCase()] || '📌'} {skill}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
          <div className="bg-white rounded-xl p-5 shadow-md hover:shadow-lg transition-shadow">
            <div className="text-3xl font-bold text-violet-600">{stats?.tasks?.total_tasks_completed || 0}</div>
            <div className="text-sm text-gray-500 mt-1">Task hoàn thành</div>
          </div>
          <div className="bg-white rounded-xl p-5 shadow-md hover:shadow-lg transition-shadow">
            <div className="text-3xl font-bold text-emerald-600">{user.current_xp}</div>
            <div className="text-sm text-gray-500 mt-1">Tổng XP</div>
          </div>
          <div className="bg-white rounded-xl p-5 shadow-md hover:shadow-lg transition-shadow">
            <div className="text-3xl font-bold text-blue-600">{stats?.work_schedule?.total_hours_this_month || 0}</div>
            <div className="text-sm text-gray-500 mt-1">Giờ làm tháng này</div>
          </div>
          <div className="bg-white rounded-xl p-5 shadow-md hover:shadow-lg transition-shadow">
            <div className="text-3xl font-bold text-amber-600">{user.discipline_score}</div>
            <div className="text-sm text-gray-500 mt-1">Điểm kỷ luật</div>
          </div>
        </div>

        {/* Recent Activity */}
        <div className="bg-white rounded-xl shadow-lg mt-6 overflow-hidden">
          <div className="p-5 border-b border-gray-100">
            <h2 className="text-lg font-bold text-gray-900">Hoạt động gần đây</h2>
          </div>
          <div className="p-5">
            <div className="text-center text-gray-500 py-8">
              <div className="text-4xl mb-3">📝</div>
              <p>Chưa có hoạt động gần đây</p>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        {!isOwnProfile && (currentUser?.roles.includes('mentor') || currentUser?.roles.includes('admin')) && (
          <div className="mt-6 flex gap-3">
            <Link
              href={`/mentor/tasks`}
              className="flex-1 px-4 py-3 bg-gradient-to-r from-violet-600 to-fuchsia-600 text-white rounded-xl font-semibold hover:from-violet-700 hover:to-fuchsia-700 transition-all shadow-lg text-center"
            >
              Quản lý Tasks
            </Link>
            <button
              onClick={() => router.push(`/mentor/users/${user.id}`)}
              className="flex-1 px-4 py-3 bg-white border-2 border-violet-200 text-violet-600 rounded-xl font-semibold hover:bg-violet-50 transition-all shadow-md"
            >
              Xem chi tiết
            </button>
          </div>
        )}

        {/* Footer */}
        <div className="text-center text-gray-400 text-sm py-8">
          Tham gia từ {new Date(user.created_at).toLocaleDateString('vi-VN', { month: 'long', year: 'numeric' })}
        </div>
      </div>
    </div>
  );
}
