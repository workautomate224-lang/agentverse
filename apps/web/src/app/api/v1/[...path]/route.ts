import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';

// Read at runtime, not module init time
function getBackendUrl(): string {
  return process.env.BACKEND_API_URL || 'http://localhost:8000';
}

async function proxyRequest(
  request: NextRequest,
  path: string,
  method: string
): Promise<NextResponse> {
  // Read backend URL at runtime
  const BACKEND_URL = getBackendUrl();

  // Build the backend URL
  const url = new URL(request.url);
  // FastAPI expects trailing slashes for collection endpoints, but NOT for:
  // - Paths ending with a UUID (resource endpoints)
  // - Paths with file extensions
  // - Paths ending with known action names (active, checklist, etc.)
  // - Paths that already have a trailing slash
  const knownActions = /\/(active|checklist|execute|expand|publish|cancel)$/;
  const needsTrailingSlash = !path.endsWith('/') &&
    !path.includes('.') &&
    !path.match(/\/[a-f0-9-]{36}$/) &&
    !knownActions.test(path);
  const normalizedPath = needsTrailingSlash ? `${path}/` : path;
  const backendPath = `/api/v1/${normalizedPath}${url.search}`;
  const backendUrl = `${BACKEND_URL}${backendPath}`;

  // Get authorization header from client or session
  let authHeader = request.headers.get('authorization');
  if (!authHeader) {
    const session = await getServerSession(authOptions);
    if (session?.user?.accessToken) {
      authHeader = `Bearer ${session.user.accessToken}`;
    }
  }

  // Read body for non-GET requests BEFORE doing anything else
  let body: string | undefined;
  if (method !== 'GET' && method !== 'HEAD') {
    try {
      body = await request.text();
    } catch {
      // No body
    }
  }

  // Build simple headers like the debug proxy
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (authHeader) {
    headers['Authorization'] = authHeader;
  }

  // Make the request
  try {
    const response = await fetch(backendUrl, {
      method,
      headers,
      body,
    });

    // Get response body
    const responseBody = await response.text();

    // Create response with same status and headers
    const responseHeaders = new Headers();
    response.headers.forEach((value, key) => {
      // Don't forward these headers
      if (!['transfer-encoding', 'connection', 'keep-alive'].includes(key.toLowerCase())) {
        responseHeaders.set(key, value);
      }
    });

    // Handle 204 No Content - MUST NOT have a body per HTTP spec
    if (response.status === 204) {
      return new NextResponse(null, {
        status: 204,
        headers: responseHeaders,
      });
    }

    return new NextResponse(responseBody, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
    });
  } catch (error) {
    console.error('[API Proxy] Failed to connect to backend:', {
      BACKEND_URL,
      backendUrl,
      method,
      error: error instanceof Error ? error.message : String(error),
      stack: error instanceof Error ? error.stack : undefined,
    });
    return NextResponse.json(
      { error: 'Failed to connect to backend', details: error instanceof Error ? error.message : String(error), url: backendUrl },
      { status: 502 }
    );
  }
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxyRequest(request, path.join('/'), 'GET');
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxyRequest(request, path.join('/'), 'POST');
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxyRequest(request, path.join('/'), 'PUT');
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxyRequest(request, path.join('/'), 'PATCH');
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxyRequest(request, path.join('/'), 'DELETE');
}
