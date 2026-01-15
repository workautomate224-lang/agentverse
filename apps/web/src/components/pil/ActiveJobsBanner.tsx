'use client';

/**
 * Active Jobs Banner Component
 * Reference: blueprint.md §5
 *
 * Shows a collapsible banner with all active PIL jobs for a project.
 * Designed to be placed at the top of pages to give visibility into background processing.
 */

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Loader2,
  ChevronDown,
  ChevronUp,
  Zap,
  AlertTriangle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { useActivePILJobs } from '@/hooks/useApi';
import { PILJobProgress } from './PILJobProgress';
import type { PILJob } from '@/lib/api';

interface ActiveJobsBannerProps {
  /** Project ID to filter jobs */
  projectId?: string;
  /** Maximum jobs to show before collapsing */
  maxVisible?: number;
  /** Callback when a job completes */
  onJobComplete?: (job: PILJob) => void;
  /** Additional CSS classes */
  className?: string;
}

export function ActiveJobsBanner({
  projectId,
  maxVisible = 3,
  onJobComplete,
  className,
}: ActiveJobsBannerProps) {
  const [expanded, setExpanded] = useState(false);
  const { data: jobs, isLoading, error } = useActivePILJobs(projectId);

  // Don't render if no active jobs
  if (!isLoading && (!jobs || jobs.length === 0)) {
    return null;
  }

  const activeJobs = jobs || [];
  const visibleJobs = expanded ? activeJobs : activeJobs.slice(0, maxVisible);
  const hiddenCount = activeJobs.length - maxVisible;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, height: 0 }}
        animate={{ opacity: 1, height: 'auto' }}
        exit={{ opacity: 0, height: 0 }}
        className={cn(
          'bg-gradient-to-r from-cyan-500/5 via-purple-500/5 to-cyan-500/5',
          'border border-cyan-400/20 rounded-lg overflow-hidden',
          className
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-2 border-b border-white/10">
          <div className="flex items-center gap-2">
            <div className="relative">
              <Zap className="h-4 w-4 text-cyan-400" />
              <motion.div
                className="absolute inset-0 rounded-full bg-cyan-400/30"
                animate={{ scale: [1, 1.5, 1], opacity: [0.5, 0, 0.5] }}
                transition={{ duration: 2, repeat: Infinity }}
              />
            </div>
            <span className="text-sm font-mono text-cyan-400">
              {isLoading ? (
                'Loading jobs...'
              ) : (
                <>
                  {activeJobs.length} Active Job{activeJobs.length !== 1 ? 's' : ''}
                </>
              )}
            </span>
          </div>

          {activeJobs.length > maxVisible && (
            <Button
              variant="ghost"
              size="sm"
              className="h-6 text-xs font-mono text-gray-400 hover:text-white"
              onClick={() => setExpanded(!expanded)}
            >
              {expanded ? (
                <>
                  <ChevronUp className="h-3 w-3 mr-1" />
                  Show Less
                </>
              ) : (
                <>
                  <ChevronDown className="h-3 w-3 mr-1" />
                  Show {hiddenCount} More
                </>
              )}
            </Button>
          )}
        </div>

        {/* Loading state */}
        {isLoading && (
          <div className="flex items-center justify-center py-4">
            <Loader2 className="h-5 w-5 animate-spin text-cyan-400" />
          </div>
        )}

        {/* Error state */}
        {error && (
          <div className="flex items-center gap-2 px-4 py-3 text-yellow-400">
            <AlertTriangle className="h-4 w-4" />
            <span className="text-xs font-mono">Failed to load active jobs</span>
          </div>
        )}

        {/* Job list */}
        {!isLoading && !error && (
          <motion.div
            className="p-2 space-y-2"
            initial={false}
            animate={{ height: 'auto' }}
          >
            <AnimatePresence mode="popLayout">
              {visibleJobs.map((job) => (
                <motion.div
                  key={job.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  layout
                >
                  <PILJobProgress
                    jobId={job.id}
                    mode="compact"
                    onComplete={onJobComplete}
                  />
                </motion.div>
              ))}
            </AnimatePresence>
          </motion.div>
        )}
      </motion.div>
    </AnimatePresence>
  );
}

export default ActiveJobsBanner;
