import { NextRequest, NextResponse } from 'next/server';

// Prevent static generation - this endpoint must be dynamic
export const dynamic = 'force-dynamic';

// Runtime API route handler for /api/health
// This proxies to the backend health endpoint at runtime (not build time)
const BACKEND_URL = process.env.BACKEND_API_URL || 'http://localhost:8000';

export async function GET(request: NextRequest) {
  try {
    const response = await fetch(`${BACKEND_URL}/health`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      // Don't cache health checks
      cache: 'no-store',
    });

    const data = await response.json();

    return NextResponse.json(data, {
      status: response.status,
      headers: {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
      },
    });
  } catch (error) {
    // Return a structured error response
    return NextResponse.json(
      {
        status: 'unhealthy',
        error: 'Failed to connect to backend',
        backend_url: BACKEND_URL.replace(/\/\/[^:]+:[^@]+@/, '//***:***@'), // Mask credentials if any
      },
      { status: 503 }
    );
  }
}
