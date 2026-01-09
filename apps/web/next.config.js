/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  // Prevent Next.js from redirecting trailing slashes - let API routes handle them
  skipTrailingSlashRedirect: true,
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '*.cloudflare.com',
      },
    ],
  },
  env: {
    // Use empty string for relative URLs in production, fallback to localhost only if undefined
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL !== undefined
      ? process.env.NEXT_PUBLIC_API_URL
      : 'http://localhost:8000',
    NEXT_PUBLIC_APP_NAME: 'AgentVerse',
  },
  async rewrites() {
    // Get the backend URL from environment, defaulting to localhost for development only
    const backendUrl = process.env.BACKEND_API_URL || 'http://localhost:8000';

    return {
      // beforeFiles are checked before pages/api routes
      beforeFiles: [],
      // afterFiles are checked after pages/api routes
      afterFiles: [
        {
          // Proxy health check endpoint
          source: '/api/health',
          destination: `${backendUrl}/health`,
        },
      ],
      // fallback rewrites are checked last (after all routes)
      // Note: API route handler at src/app/api/v1/[...path]/route.ts handles all /api/v1/* requests
      fallback: [],
    };
  },
};

module.exports = nextConfig;
