import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { AuthProvider } from '@/contexts/AuthContext'

const inter = Inter({ subsets: ['latin', 'vietnamese'] })

export const metadata: Metadata = {
  title: 'TLMS - T&A Lab Management System',
  description: 'Hệ thống quản lý Lab T&A - Gamification & Performance Tracking',
  icons: {
    icon: '/logo/logo.jpg',
    apple: '/logo/logo.jpg',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="vi">
      <body className={inter.className}>
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  )
}
