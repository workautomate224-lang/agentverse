'use client';

/**
 * RunProgress Component
 * Displays real-time progress for a product simulation run.
 */

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useRunProgress, RunCompleteData, RunFailedData } from '@/hooks/useWebSocket';
import {
  CheckCircle,
  XCircle,
  Loader2,
  Users,
  AlertTriangle,
  Wifi,
  WifiOff,
  BarChart3,
} from 'lucide-react';

// ============= Types =============

interface RunProgressProps {
  runId: string;
  productId: string;
  onComplete?: (resultId: string) => void;
  onFailed?: (error: string) => void;
  showDetails?: boolean;
  compact?: boolean;
}

// ============= Sub-Components =============

function ProgressBar({ progress, className = '' }: { progress: number; className?: string }) {
  return (
    <div className={`w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3 overflow-hidden ${className}`}>
      <div
        className="h-full bg-gradient-to-r from-blue-500 to-indigo-600 rounded-full transition-all duration-300 ease-out"
        style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
      />
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const statusConfig: Record<string, { color: string; icon: React.ReactNode; text: string }> = {
    pending: {
      color: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
      icon: <Loader2 className="h-3 w-3 animate-spin" />,
      text: 'Pending',
    },
    running: {
      color: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
      icon: <Loader2 className="h-3 w-3 animate-spin" />,
      text: 'Running',
    },
    completed: {
      color: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
      icon: <CheckCircle className="h-3 w-3" />,
      text: 'Completed',
    },
    failed: {
      color: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
      icon: <XCircle className="h-3 w-3" />,
      text: 'Failed',
    },
    cancelled: {
      color: 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400',
      icon: <XCircle className="h-3 w-3" />,
      text: 'Cancelled',
    },
  };

  const config = statusConfig[status] || statusConfig.pending;

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${config.color}`}>
      {config.icon}
      {config.text}
    </span>
  );
}

function ConnectionIndicator({ status }: { status: string }) {
  const isConnected = status === 'connected';

  return (
    <div className={`flex items-center gap-1.5 text-xs ${isConnected ? 'text-green-600' : 'text-gray-400'}`}>
      {isConnected ? (
        <>
          <Wifi className="h-3 w-3" />
          <span>Live</span>
        </>
      ) : (
        <>
          <WifiOff className="h-3 w-3" />
          <span>Connecting...</span>
        </>
      )}
    </div>
  );
}

// ============= Main Component =============

export function RunProgress({
  runId,
  productId,
  onComplete,
  onFailed,
  showDetails = true,
  compact = false,
}: RunProgressProps) {
  const router = useRouter();
  const [startTime] = useState(Date.now());
  const [elapsedTime, setElapsedTime] = useState(0);

  const handleComplete = (data: RunCompleteData) => {
    onComplete?.(data.result_id);
  };

  const handleFailed = (data: RunFailedData) => {
    onFailed?.(data.error);
  };

  const {
    status: wsStatus,
    progress,
    agentsCompleted,
    agentsFailed,
    agentsTotal,
    runStatus,
    isComplete,
    isFailed,
    error,
    resultId,
  } = useRunProgress({
    runId,
    onComplete: handleComplete,
    onFailed: handleFailed,
  });

  // Update elapsed time
  useEffect(() => {
    if (isComplete || isFailed) return;

    const interval = setInterval(() => {
      setElapsedTime(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);

    return () => clearInterval(interval);
  }, [startTime, isComplete, isFailed]);

  // Format elapsed time
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Calculate stats
  const successRate = agentsTotal > 0 ? Math.round((agentsCompleted / agentsTotal) * 100) : 0;
  const failureRate = agentsTotal > 0 ? Math.round((agentsFailed / agentsTotal) * 100) : 0;
  const estimatedTimeRemaining = agentsCompleted > 0 && progress < 100
    ? Math.round((elapsedTime / progress) * (100 - progress))
    : null;

  // Compact version
  if (compact) {
    return (
      <div className="flex items-center gap-4 p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
        <StatusBadge status={runStatus} />
        <div className="flex-1">
          <ProgressBar progress={progress} />
        </div>
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
          {progress}%
        </span>
        {isComplete && resultId && (
          <button
            onClick={() => router.push(`/dashboard/products/${productId}/results/${resultId}`)}
            className="px-3 py-1 text-sm bg-indigo-600 text-white rounded-md hover:bg-indigo-700 transition-colors"
          >
            View Results
          </button>
        )}
      </div>
    );
  }

  // Full version
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-100 dark:bg-indigo-900/30 rounded-lg">
            <BarChart3 className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white">
              Simulation Progress
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Run ID: {runId.slice(0, 8)}...
            </p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <ConnectionIndicator status={wsStatus} />
          <StatusBadge status={runStatus} />
        </div>
      </div>

      {/* Progress Section */}
      <div className="px-6 py-6">
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Overall Progress
            </span>
            <span className="text-sm font-bold text-gray-900 dark:text-white">
              {progress}%
            </span>
          </div>
          <ProgressBar progress={progress} />
        </div>

        {/* Stats Grid */}
        {showDetails && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
            {/* Agents Completed */}
            <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-1">
                <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400" />
                <span className="text-xs font-medium text-green-700 dark:text-green-400">
                  Completed
                </span>
              </div>
              <p className="text-2xl font-bold text-green-700 dark:text-green-300">
                {agentsCompleted}
              </p>
              <p className="text-xs text-green-600 dark:text-green-400">
                {successRate}% success
              </p>
            </div>

            {/* Agents Failed */}
            <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-1">
                <XCircle className="h-4 w-4 text-red-600 dark:text-red-400" />
                <span className="text-xs font-medium text-red-700 dark:text-red-400">
                  Failed
                </span>
              </div>
              <p className="text-2xl font-bold text-red-700 dark:text-red-300">
                {agentsFailed}
              </p>
              <p className="text-xs text-red-600 dark:text-red-400">
                {failureRate}% failure
              </p>
            </div>

            {/* Total Agents */}
            <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-1">
                <Users className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                <span className="text-xs font-medium text-blue-700 dark:text-blue-400">
                  Total Agents
                </span>
              </div>
              <p className="text-2xl font-bold text-blue-700 dark:text-blue-300">
                {agentsTotal}
              </p>
              <p className="text-xs text-blue-600 dark:text-blue-400">
                {agentsTotal - agentsCompleted - agentsFailed} remaining
              </p>
            </div>

            {/* Time */}
            <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-1">
                <Loader2 className={`h-4 w-4 text-gray-600 dark:text-gray-400 ${!isComplete && !isFailed ? 'animate-spin' : ''}`} />
                <span className="text-xs font-medium text-gray-700 dark:text-gray-400">
                  Elapsed Time
                </span>
              </div>
              <p className="text-2xl font-bold text-gray-700 dark:text-gray-300">
                {formatTime(elapsedTime)}
              </p>
              {estimatedTimeRemaining && (
                <p className="text-xs text-gray-600 dark:text-gray-400">
                  ~{formatTime(estimatedTimeRemaining)} remaining
                </p>
              )}
            </div>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="mt-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
            <div>
              <h4 className="text-sm font-medium text-red-800 dark:text-red-300">
                Error
              </h4>
              <p className="text-sm text-red-700 dark:text-red-400 mt-1">
                {error}
              </p>
            </div>
          </div>
        )}

        {/* Completion Actions */}
        {isComplete && resultId && (
          <div className="mt-6 p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <CheckCircle className="h-6 w-6 text-green-600 dark:text-green-400" />
                <div>
                  <h4 className="font-medium text-green-800 dark:text-green-300">
                    Simulation Complete!
                  </h4>
                  <p className="text-sm text-green-700 dark:text-green-400">
                    Results are ready for review.
                  </p>
                </div>
              </div>
              <button
                onClick={() => router.push(`/dashboard/products/${productId}/results/${resultId}`)}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium"
              >
                View Results
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default RunProgress;
