'use client';

/**
 * Error Boundary for Project Workspace
 * Catches and displays errors that occur in project pages
 */

import { useEffect } from 'react';
import Link from 'next/link';
import { AlertTriangle, RefreshCw, ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function ProjectWorkspaceError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log the error to console for debugging
    console.error('Project workspace error:', error);
  }, [error]);

  return (
    <div className="min-h-screen bg-black flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white/5 border border-red-500/30 p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-red-500/10 border border-red-500/30">
            <AlertTriangle className="h-5 w-5 text-red-400" />
          </div>
          <div>
            <h2 className="text-lg font-mono font-bold text-white">
              Something went wrong
            </h2>
            <p className="text-xs font-mono text-gray-400">
              An error occurred while loading this page
            </p>
          </div>
        </div>

        {/* Error details */}
        <div className="mb-4 p-3 bg-black/50 border border-white/10 overflow-auto max-h-48">
          <p className="text-xs font-mono text-red-400 break-all">
            {error.message}
          </p>
          {error.digest && (
            <p className="text-xs font-mono text-gray-500 mt-2">
              Digest: {error.digest}
            </p>
          )}
          {error.stack && (
            <details className="mt-2">
              <summary className="text-xs font-mono text-gray-500 cursor-pointer hover:text-gray-400">
                Stack trace
              </summary>
              <pre className="text-[10px] font-mono text-gray-600 mt-1 whitespace-pre-wrap">
                {error.stack}
              </pre>
            </details>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={reset}
            className="text-xs font-mono border-white/20 hover:bg-white/5"
          >
            <RefreshCw className="h-3 w-3 mr-2" />
            Try again
          </Button>
          <Link href="/dashboard/projects">
            <Button
              variant="outline"
              size="sm"
              className="text-xs font-mono border-white/20 hover:bg-white/5"
            >
              <ArrowLeft className="h-3 w-3 mr-2" />
              Back to projects
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
