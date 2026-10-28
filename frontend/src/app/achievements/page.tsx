'use client';

import { useEffect, useMemo, useState } from 'react';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { apiClient } from '@/lib/api';
import { AchievementBadgeProgress, AchievementDashboard } from '@/types/development';

const categoryLabels: Record<string, string> = {
  xp: 'XP',
  task: 'Task',
  quest: 'Quest',
  question: 'Question',
  profile: 'Profile',
  discipline: 'Kỷ luật',
};

const formatAchievementValue = (value: number) => {
  if (Number.isInteger(value)) return value.toString();
  return value.toFixed(1);
};

const clampProgress = (value: number) => Math.min(Math.max(value, 0), 100);

export default function AchievementsPage() {
  const router = useRouter();
  const { user, isLoading, isAuthenticated, logout } = useAuth();
  const [achievements, setAchievements] = useState<AchievementDashboard | null>(null);
  const [loadingAchievements, setLoadingAchievements] = useState(true);
  const [loadError, setLoadError] = useState('');

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isLoading, isAuthenticated, router]);

  useEffect(() => {
    const loadAchievements = async () => {
      if (!user) return;
      setLoadingAchievements(true);
      setLoadError('');
      try {
        const data = await apiClient.getMyAchievements();
        setAchievements(data);
      } catch (err) {
        console.error('Failed to load achievements:', err);
        setLoadError('Không thể tải danh sách thành tích lúc này.');
      } finally {
        setLoadingAchievements(false);
      }
    };

    loadAchievements();
  }, [user]);

  const sortedBadges = useMemo(() => {
    return [...(achievements?.badges ?? [])].sort((a, b) => a.sort_order - b.sort_order);
  }, [achievements]);

  const handleLogout = async () => {
    await logout();
    router.push('/login');
  };

  const renderBadgeCircle = (badge: AchievementBadgeProgress, large = false) => {
    const progress = clampProgress(badge.progress_percentage);
    const color = badge.is_unlocked ? badge.badge_color : '#94a3b8';
    const softColor = badge.is_unlocked ? `${badge.badge_color}1F` : '#f1f5f9';

    return (
      <div
        className={`relative flex shrink-0 items-center justify-center rounded-full border font-semibold shadow-sm ${
          large ? 'h-20 w-20 text-lg' : 'h-14 w-14 text-sm'
        }`}
        style={{
          color,
          borderColor: badge.is_unlocked ? badge.badge_color : '#e2e8f0',
          background: `conic-gradient(${color} ${progress * 3.6}deg, #eef2f7 0deg)`,
        }}
      >
        <div
          className={`flex items-center justify-center rounded-full ${large ? 'h-16 w-16' : 'h-11 w-11'}`}
          style={{ backgroundColor: softColor }}
        >
          {badge.badge_icon}
        </div>
      </div>
    );
  };

  const renderBadgeRow = (badge: AchievementBadgeProgress) => {
    const progress = clampProgress(badge.progress_percentage);

    return (
      <div
        key={badge.id}
        className="flex flex-col gap-4 rounded-xl border border-gray-200 bg-white p-4 shadow-sm transition-colors hover:border-[#1E90FF]/40 sm:flex-row sm:items-center"
      >
        {renderBadgeCircle(badge)}
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-base font-semibold text-gray-900">{badge.title}</h3>
            <span className="rounded-full bg-gray-100 px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide text-gray-500">
              {categoryLabels[badge.category] || badge.category}
            </span>
            {badge.is_unlocked && (
              <span className="rounded-full bg-[#32CD32]/10 px-2 py-0.5 text-xs font-medium text-[#16A34A]">
                Mở
              </span>
            )}
          </div>
          <p className="mt-1 text-sm text-gray-600">{badge.description}</p>
          <div className="mt-3">
            <div className="mb-1 flex justify-between text-xs text-gray-500">
              <span>{formatAchievementValue(badge.current_value)}</span>
              <span>{formatAchievementValue(badge.target_value)}</span>
            </div>
            <div className="h-2 w-full rounded-full bg-gray-100">
              <div
                className="h-2 rounded-full transition-all"
                style={{
                  width: `${progress}%`,
                  background: badge.is_unlocked
                    ? `linear-gradient(90deg, ${badge.badge_color}, #9333ea)`
                    : '#94a3b8',
                }}
              />
            </div>
          </div>
        </div>
        <div className="text-left sm:w-20 sm:text-right">
          <p className={`text-sm font-semibold ${badge.is_unlocked ? 'text-[#16A34A]' : 'text-gray-500'}`}>
            {badge.is_unlocked ? 'Hoàn tất' : `${progress.toFixed(0)}%`}
          </p>
        </div>
      </div>
    );
  };

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-gray-300 border-t-[#1E90FF]" />
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="sticky top-0 z-10 border-b border-gray-200 bg-white shadow-sm">
        <div className="mx-auto max-w-6xl px-4">
          <div className="flex h-14 items-center justify-between">
            <button onClick={() => router.push('/dashboard')} className="flex items-center gap-2">
              <Image src="/logo/logo.jpg" alt="TLMS Logo" width={32} height={32} className="h-8 w-8 rounded-lg object-cover shadow-sm" />
              <span className="hidden font-semibold text-gray-900 sm:block">TLMS</span>
            </button>
            <div className="flex items-center gap-3">
              <p className="hidden max-w-[160px] truncate text-sm font-medium text-gray-900 sm:block">
                {user.full_name || user.email}
              </p>
              <button
                onClick={handleLogout}
                className="rounded-lg px-3 py-1.5 text-sm text-gray-600 transition-colors hover:bg-red-50 hover:text-red-600"
              >
                Đăng xuất
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-6 px-4 py-8">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Member Growth</p>
            <h1 className="mt-1 text-3xl font-semibold text-gray-900">Thành tích & Huy hiệu</h1>
            <p className="mt-2 text-sm text-gray-500">Theo dõi các mốc phấn đấu và huy hiệu đã mở trong TLMS.</p>
          </div>
          <button
            onClick={() => router.push('/dashboard')}
            className="w-fit rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-600 shadow-sm hover:border-[#1E90FF] hover:text-[#1E90FF]"
          >
            Quay lại
          </button>
        </div>

        {loadingAchievements && (
          <div className="rounded-xl border border-gray-200 bg-white p-8 text-center text-sm text-gray-500 shadow-sm">
            Đang tải huy hiệu...
          </div>
        )}

        {!loadingAchievements && loadError && (
          <div className="rounded-xl border border-red-100 bg-red-50 p-4 text-sm text-red-600">{loadError}</div>
        )}

        {!loadingAchievements && achievements && (
          <>
            <section className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
              <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Tổng quan</p>
                  <div className="mt-2 flex flex-wrap items-end gap-x-3 gap-y-1">
                    <h2 className="text-3xl font-semibold text-gray-900">
                      {achievements.unlocked_count} / {achievements.total_count}
                    </h2>
                    <span className="pb-1 text-sm font-semibold text-[#9333ea]">
                      {achievements.overall_progress.toFixed(1)}%
                    </span>
                  </div>
                </div>
                <div className="flex flex-wrap gap-3">
                  {achievements.featured.slice(0, 4).map((badge) => (
                    <div key={badge.id} className="text-center">
                      {renderBadgeCircle(badge, true)}
                      <p className="mt-2 w-20 truncate text-xs font-medium text-gray-700">{badge.title}</p>
                    </div>
                  ))}
                </div>
              </div>
              <div className="mt-5 h-2 w-full rounded-full bg-gray-100">
                <div
                  className="h-2 rounded-full bg-gradient-to-r from-[#1E90FF] to-[#9333ea] transition-all"
                  style={{ width: `${clampProgress(achievements.overall_progress)}%` }}
                />
              </div>
            </section>

            {achievements.next_milestones.length > 0 && (
              <section className="space-y-3">
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold text-gray-900">Mốc sắp đạt</h2>
                  <span className="text-xs text-gray-500">{achievements.next_milestones.length} mốc gần nhất</span>
                </div>
                <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
                  {achievements.next_milestones.map((badge) => renderBadgeRow(badge))}
                </div>
              </section>
            )}

            <section className="space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-gray-900">Danh sách huy hiệu</h2>
                <span className="text-xs text-gray-500">{sortedBadges.length} huy hiệu</span>
              </div>
              <div className="space-y-3">
                {sortedBadges.map((badge) => renderBadgeRow(badge))}
              </div>
            </section>
          </>
        )}
      </main>
    </div>
  );
}
