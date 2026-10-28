'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';

export default function ProfileRedirect() {
  const router = useRouter();
  const { user, isLoading } = useAuth();

  useEffect(() => {
    if (!isLoading && user) {
      router.push(`/profile/${user.id}`);
    } else if (!isLoading && !user) {
      router.push('/login');
    }
  }, [isLoading, user, router]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 flex items-center justify-center">
      <div className="text-center">
        <div className="w-12 h-12 border-4 border-gray-200 border-t-violet-600 rounded-full animate-spin mx-auto mb-4"></div>
        <p className="text-gray-500">Đang chuyển hướng...</p>
      </div>
    </div>
  );
}
