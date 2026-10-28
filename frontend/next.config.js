/** @type {import('next').NextConfig} */
const backendUrl = (process.env.BACKEND_URL || 'http://tlms-backend:8000').replace(/\/$/, '')

const nextConfig = {
  output: 'standalone',
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || '/api',
  },
  async rewrites() {
    return {
      beforeFiles: [
        {
          source: '/api/:path*',
          destination: `${backendUrl}/api/:path*`,
        },
        {
          source: '/uploads/:path*',
          destination: `${backendUrl}/uploads/:path*`,
        },
      ],
    }
  },
}

module.exports = nextConfig
