'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api';
import Link from 'next/link';

export default function RegisterPage() {
  const router = useRouter();
  
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    phone: '',
    firstName: '',
    lastName: '',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (formData.password !== formData.confirmPassword) {
      setError('Mật khẩu xác nhận không khớp');
      return;
    }

    if (formData.password.length < 6) {
      setError('Mật khẩu phải có ít nhất 6 ký tự');
      return;
    }

    if (!formData.phone.trim()) {
      setError('Số điện thoại không được để trống');
      return;
    }

    setIsLoading(true);

    try {
      await apiClient.register({
        email: formData.email.trim(),
        password: formData.password,
        phone: formData.phone.trim(),
        firstName: formData.firstName.trim(),
        lastName: formData.lastName.trim(),
      });
      if (typeof window !== 'undefined') {
        window.localStorage.setItem('tlmsNeedsBaselineTest', '1');
      }
      setSuccess(true);
      setTimeout(() => {
        router.push('/login');
      }, 2000);
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Đăng ký thất bại. Vui lòng thử lại.';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
        <div className="max-w-sm w-full">
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 text-center">
            <div className="inline-flex items-center justify-center w-12 h-12 bg-[#32CD32]/10 rounded-full mb-4">
              <svg className="w-6 h-6 text-[#32CD32]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h2 className="text-lg font-semibold text-gray-900 mb-2">Đăng ký thành công!</h2>
            <p className="text-sm text-gray-600">Đang chuyển hướng đến trang đăng nhập...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4 py-8">
      <div className="max-w-sm w-full">
        {/* Logo & Title */}
        <div className="text-center mb-8">
          <img src="/logo/logo.jpg" alt="TLMS Logo" className="w-12 h-12 rounded-xl mb-4 shadow-lg object-cover" />
          <h1 className="text-2xl font-semibold text-gray-900">TLMS</h1>
          <p className="text-sm text-gray-500 mt-1">Đăng ký tài khoản mới</p>
        </div>

        {/* Register Card */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-6">Tạo tài khoản</h2>

          {/* Error Alert */}
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Name Fields */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="firstName" className="block text-sm font-medium text-gray-700 mb-1.5">
                  Họ
                </label>
                <input
                  id="firstName"
                  name="firstName"
                  type="text"
                  value={formData.firstName}
                  onChange={handleChange}
                  required
                  className="block w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1E90FF] focus:border-[#1E90FF] text-sm transition-colors"
                  placeholder="Nguyễn"
                />
              </div>
              <div>
                <label htmlFor="lastName" className="block text-sm font-medium text-gray-700 mb-1.5">
                  Tên
                </label>
                <input
                  id="lastName"
                  name="lastName"
                  type="text"
                  value={formData.lastName}
                  onChange={handleChange}
                  required
                  className="block w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1E90FF] focus:border-[#1E90FF] text-sm transition-colors"
                  placeholder="Văn A"
                />
              </div>
            </div>

            {/* Email Field */}
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1.5">
                Email
              </label>
              <input
                id="email"
                name="email"
                type="email"
                value={formData.email}
                onChange={handleChange}
                required
                className="block w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1E90FF] focus:border-[#1E90FF] text-sm transition-colors"
                placeholder="your@email.com"
              />
            </div>

            {/* Phone Field */}
            <div>
              <label htmlFor="phone" className="block text-sm font-medium text-gray-700 mb-1.5">
                Số điện thoại
              </label>
              <input
                id="phone"
                name="phone"
                type="tel"
                value={formData.phone}
                onChange={handleChange}
                required
                className="block w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1E90FF] focus:border-[#1E90FF] text-sm transition-colors"
                placeholder="0901234567"
              />
            </div>

            {/* Password Field */}
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1.5">
                Mật khẩu
              </label>
              <div className="relative">
                <input
                  id="password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  value={formData.password}
                  onChange={handleChange}
                  required
                  className="block w-full px-3 py-2.5 pr-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1E90FF] focus:border-[#1E90FF] text-sm transition-colors"
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-[#1E90FF]"
                >
                  {showPassword ? (
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                    </svg>
                  ) : (
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                  )}
                </button>
              </div>
              <p className="text-xs text-gray-500 mt-1">Tối thiểu 6 ký tự</p>
            </div>

            {/* Confirm Password Field */}
            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700 mb-1.5">
                Xác nhận mật khẩu
              </label>
              <input
                id="confirmPassword"
                name="confirmPassword"
                type={showPassword ? 'text' : 'password'}
                value={formData.confirmPassword}
                onChange={handleChange}
                required
                className="block w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1E90FF] focus:border-[#1E90FF] text-sm transition-colors"
                placeholder="••••••••"
              />
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-[#1E90FF] hover:bg-[#1a7de0] text-white font-medium py-2.5 px-4 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-sm shadow-sm"
            >
              {isLoading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Đang đăng ký...
                </span>
              ) : (
                'Đăng ký'
              )}
            </button>
          </form>

          {/* Login Link */}
          <div className="mt-6 text-center">
            <p className="text-sm text-gray-600">
              Đã có tài khoản?{' '}
              <Link href="/login" className="text-[#1E90FF] hover:text-[#1a7de0] hover:underline font-medium">
                Đăng nhập
              </Link>
            </p>
          </div>
        </div>

        {/* Footer */}
        <p className="text-center text-xs text-gray-500 mt-6">
          © 2026 T&A Lab. All rights reserved.
        </p>
      </div>
    </div>
  );
}
