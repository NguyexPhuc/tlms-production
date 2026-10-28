'use client';

import { useState } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ArrowRight, CalendarCheck2, Eye, EyeOff, LockKeyhole, Mail, Sparkles, Target } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await login(email, password);
      if (window.localStorage.getItem('tlmsNeedsBaselineTest') === '1') {
        window.localStorage.removeItem('tlmsNeedsBaselineTest');
        router.push('/candidate/questions?baseline=1');
        return;
      }
      router.push('/dashboard');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Email hoặc mật khẩu chưa đúng. Vui lòng thử lại.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 sm:px-6 lg:flex lg:items-center lg:py-12">
      <div className="mx-auto grid w-full max-w-5xl overflow-hidden rounded-lg border border-slate-200 bg-white shadow-xl lg:grid-cols-[0.9fr_1.1fr]">
        <section className="order-2 hidden flex-col justify-between bg-blue-700 p-7 text-white sm:p-10 lg:order-1 lg:flex">
          <div>
            <div className="flex items-center gap-3">
              <Image src="/logo/logo.jpg" alt="TLMS" width={48} height={48} className="rounded-lg object-cover shadow-md" priority />
              <div>
                <p className="text-xl font-bold">TLMS</p>
                <p className="text-sm text-blue-100">T&A Lab Management System</p>
              </div>
            </div>
            <h1 className="mt-10 max-w-sm text-3xl font-bold leading-tight sm:text-4xl">Mỗi ngày một bước tiến rõ ràng.</h1>
            <p className="mt-3 max-w-md text-sm leading-6 text-blue-100">Theo dõi lộ trình, hoàn thành nhiệm vụ và phát triển kỹ năng cùng đội ngũ T&A Lab.</p>
          </div>
          <div className="mt-10 grid gap-3 sm:grid-cols-3 lg:grid-cols-1">
            <Feature icon={<Target size={19} />} title="Lộ trình cá nhân" />
            <Feature icon={<CalendarCheck2 size={19} />} title="Lịch học đồng bộ" />
            <Feature icon={<Sparkles size={19} />} title="Đánh giá theo năng lực" />
          </div>
        </section>

        <section className="order-1 flex items-center p-7 sm:p-10 lg:order-2 lg:p-14">
          <div className="mx-auto w-full max-w-md">
            <div className="mb-7 flex items-center gap-3 lg:hidden">
              <Image src="/logo/logo.jpg" alt="TLMS" width={44} height={44} className="rounded-lg object-cover shadow-sm" priority />
              <div>
                <p className="text-lg font-bold text-slate-900">TLMS</p>
                <p className="text-xs text-slate-500">T&A Lab Management System</p>
              </div>
            </div>
            <p className="text-sm font-semibold text-blue-600">Chào mừng trở lại</p>
            <h2 className="mt-1 text-2xl font-bold text-slate-900">Đăng nhập TLMS</h2>
            <p className="mt-2 text-sm text-slate-500">Tiếp tục công việc và lộ trình hôm nay.</p>

            {error && <div role="alert" className="mt-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

            <form onSubmit={handleSubmit} className="mt-7 space-y-5">
              <div>
                <label htmlFor="email" className="mb-2 block text-sm font-semibold text-slate-700">Email</label>
                <div className="relative">
                  <Mail size={18} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                  <input id="email" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} required className="w-full rounded-lg border border-slate-300 py-3 pl-10 pr-3 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100" placeholder="name@email.com" />
                </div>
              </div>

              <div>
                <label htmlFor="password" className="mb-2 block text-sm font-semibold text-slate-700">Mật khẩu</label>
                <div className="relative">
                  <LockKeyhole size={18} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                  <input id="password" type={showPassword ? 'text' : 'password'} autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required className="w-full rounded-lg border border-slate-300 py-3 pl-10 pr-11 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100" placeholder="Nhập mật khẩu" />
                  <button type="button" onClick={() => setShowPassword((value) => !value)} className="absolute right-2 top-1/2 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-md text-slate-400 hover:bg-slate-100 hover:text-blue-600" aria-label={showPassword ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}>
                    {showPassword ? <EyeOff size={19} /> : <Eye size={19} />}
                  </button>
                </div>
              </div>

              <button type="submit" disabled={isLoading} className="flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-3 text-sm font-bold text-white shadow-sm transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60">
                {isLoading ? <><span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" /> Đang đăng nhập...</> : <>Đăng nhập <ArrowRight size={18} /></>}
              </button>
            </form>

            <p className="mt-7 text-center text-sm text-slate-600">
              Chưa có tài khoản? <Link href="/register" className="font-semibold text-blue-600 hover:underline">Đăng ký ngay</Link>
            </p>
          </div>
        </section>
      </div>
    </main>
  );
}

function Feature({ icon, title }: { icon: React.ReactNode; title: string }) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-white/20 bg-white/10 px-3 py-2.5">
      <span className="flex h-8 w-8 items-center justify-center rounded-md bg-white/15">{icon}</span>
      <span className="text-sm font-semibold">{title}</span>
    </div>
  );
}
