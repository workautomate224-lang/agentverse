/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  // Skip ESLint during production builds (for CI/CD)
  eslint: {
    ignoreDuringBuilds: true,
  },
  // Skip TypeScript errors during production builds
  typescript: {
    ignoreBuildErrors: true,
  },
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
    // Note: /api/health is handled by src/app/api/health/route.ts (runtime handler)
    // Note: /api/v1/* is handled by src/app/api/v1/[...path]/route.ts (runtime handler)
    // Rewrites here are evaluated at build time, not runtime, so they won't work
    // for dynamic backend URLs in production deployments.
    return {
      beforeFiles: [],
      afterFiles: [],
      fallback: [],
    };
  },
  async redirects() {
    return [
      // Redirect top-level routes TO dashboard routes (to ensure sidebar is always visible)
      // Projects redirects
      {
        source: '/projects',
        destination: '/dashboard/projects',
        permanent: true,
      },
      {
        source: '/projects/new',
        destination: '/dashboard/projects/new',
        permanent: true,
      },
      // Library redirects
      {
        source: '/library',
        destination: '/dashboard/library',
        permanent: true,
      },
      {
        source: '/library/personas',
        destination: '/dashboard/library/personas',
        permanent: true,
      },
      {
        source: '/library/templates',
        destination: '/dashboard/library/templates',
        permanent: true,
      },
      {
        source: '/library/rulesets',
        destination: '/dashboard/library/rulesets',
        permanent: true,
      },
      {
        source: '/library/evidence',
        destination: '/dashboard/library/evidence',
        permanent: true,
      },
      // Runs & Jobs redirects
      {
        source: '/runs-jobs',
        destination: '/dashboard/runs',
        permanent: true,
      },
      {
        source: '/runs-jobs/:id',
        destination: '/dashboard/runs/:id',
        permanent: true,
      },
      {
        source: '/runs-jobs/:id/telemetry',
        destination: '/dashboard/runs/:id/telemetry',
        permanent: true,
      },
      // Calibration redirect
      {
        source: '/calibration',
        destination: '/dashboard/calibration',
        permanent: true,
      },
    ];
  },
};

module.exports = nextConfig;
