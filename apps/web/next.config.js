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
      // Projects redirects
      {
        source: '/dashboard/projects',
        destination: '/projects',
        permanent: true,
      },
      {
        source: '/dashboard/projects/new',
        destination: '/projects/new',
        permanent: true,
      },
      // Library redirects
      {
        source: '/dashboard/library',
        destination: '/library',
        permanent: true,
      },
      {
        source: '/dashboard/library/personas',
        destination: '/library/personas',
        permanent: true,
      },
      {
        source: '/dashboard/library/templates',
        destination: '/library/templates',
        permanent: true,
      },
      {
        source: '/dashboard/library/rulesets',
        destination: '/library/rulesets',
        permanent: true,
      },
      {
        source: '/dashboard/library/evidence',
        destination: '/library/evidence',
        permanent: true,
      },
      // Runs & Jobs redirects
      {
        source: '/dashboard/runs',
        destination: '/runs-jobs',
        permanent: true,
      },
      {
        source: '/dashboard/runs/:id',
        destination: '/runs-jobs/:id',
        permanent: true,
      },
      {
        source: '/dashboard/runs/:id/telemetry',
        destination: '/runs-jobs/:id/telemetry',
        permanent: true,
      },
      // Calibration redirect
      {
        source: '/dashboard/calibration',
        destination: '/calibration',
        permanent: true,
      },
    ];
  },
};

module.exports = nextConfig;
