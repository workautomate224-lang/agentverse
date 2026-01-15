'use client';

/**
 * Alignment Score Component
 * Reference: blueprint.md §6
 *
 * Displays alignment between project configuration and blueprint requirements.
 * Shows how well the current setup matches the intended simulation goals.
 */

import { useMemo } from 'react';
import {
  Target,
  CheckCircle,
  AlertCircle,
  XCircle,
  TrendingUp,
  Sparkles,
  Loader2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Progress } from '@/components/ui/progress';
import { useProjectChecklist } from '@/hooks/useApi';
import type { ProjectChecklist, AlertState } from '@/lib/api';

interface AlignmentScoreProps {
  /** Project ID */
  projectId: string;
  /** Whether to show in compact mode */
  compact?: boolean;
  /** Whether to show breakdown by section */
  showBreakdown?: boolean;
  /** Additional CSS classes */
  className?: string;
}

// Score thresholds for color coding
const SCORE_THRESHOLDS = {
  excellent: 90,
  good: 70,
  fair: 50,
  poor: 0,
};

// Get color based on score
function getScoreColor(score: number): string {
  if (score >= SCORE_THRESHOLDS.excellent) return 'text-green-400';
  if (score >= SCORE_THRESHOLDS.good) return 'text-cyan-400';
  if (score >= SCORE_THRESHOLDS.fair) return 'text-yellow-400';
  return 'text-red-400';
}

function getScoreBgColor(score: number): string {
  if (score >= SCORE_THRESHOLDS.excellent) return 'bg-green-400/10 border-green-400/30';
  if (score >= SCORE_THRESHOLDS.good) return 'bg-cyan-400/10 border-cyan-400/30';
  if (score >= SCORE_THRESHOLDS.fair) return 'bg-yellow-400/10 border-yellow-400/30';
  return 'bg-red-400/10 border-red-400/30';
}

function getScoreLabel(score: number): string {
  if (score >= SCORE_THRESHOLDS.excellent) return 'Excellent';
  if (score >= SCORE_THRESHOLDS.good) return 'Good';
  if (score >= SCORE_THRESHOLDS.fair) return 'Needs Work';
  return 'Low';
}

// Calculate overall alignment score from checklist
function calculateAlignmentScore(checklist: ProjectChecklist | null | undefined): {
  overall: number;
  bySection: Record<string, { score: number; count: number }>;
  byStatus: Record<AlertState, number>;
} {
  if (!checklist || checklist.items.length === 0) {
    return {
      overall: 0,
      bySection: {},
      byStatus: { ready: 0, needs_attention: 0, blocked: 0, not_started: 0 },
    };
  }

  const bySection: Record<string, { score: number; count: number }> = {};
  const byStatus: Record<AlertState, number> = {
    ready: 0,
    needs_attention: 0,
    blocked: 0,
    not_started: 0,
  };

  let totalScore = 0;
  let scoredItems = 0;

  for (const item of checklist.items) {
    // Count by status
    byStatus[item.status] = (byStatus[item.status] || 0) + 1;

    // Use match_score if available, otherwise derive from status
    let itemScore = item.match_score;
    if (itemScore === null || itemScore === undefined) {
      // Derive score from status
      switch (item.status) {
        case 'ready':
          itemScore = 1.0;
          break;
        case 'needs_attention':
          itemScore = 0.5;
          break;
        case 'blocked':
          itemScore = 0.2;
          break;
        case 'not_started':
          itemScore = 0;
          break;
      }
    }

    totalScore += itemScore;
    scoredItems++;

    // Group by section
    if (!bySection[item.section_id]) {
      bySection[item.section_id] = { score: 0, count: 0 };
    }
    bySection[item.section_id].score += itemScore;
    bySection[item.section_id].count++;
  }

  // Calculate section averages
  for (const section of Object.keys(bySection)) {
    if (bySection[section].count > 0) {
      bySection[section].score = Math.round(
        (bySection[section].score / bySection[section].count) * 100
      );
    }
  }

  const overall = scoredItems > 0 ? Math.round((totalScore / scoredItems) * 100) : 0;

  return { overall, bySection, byStatus };
}

// Section display names
const SECTION_NAMES: Record<string, string> = {
  'data': 'Data',
  'personas': 'Personas',
  'data-personas': 'Data & Personas',
  'rules': 'Rules',
  'scenarios': 'Scenarios',
  'event-lab': 'Event Lab',
  'universe': 'Universe',
  'universe-map': 'Universe Map',
  'run': 'Runs',
  'run-center': 'Run Center',
};

export function AlignmentScore({
  projectId,
  compact = false,
  showBreakdown = false,
  className,
}: AlignmentScoreProps) {
  const { data: checklist, isLoading } = useProjectChecklist(projectId);

  const alignment = useMemo(
    () => calculateAlignmentScore(checklist),
    [checklist]
  );

  if (isLoading) {
    return (
      <div className={cn('flex items-center gap-2 text-gray-400', className)}>
        <Loader2 className="h-4 w-4 animate-spin" />
        <span className="text-xs font-mono">Calculating alignment...</span>
      </div>
    );
  }

  if (!checklist || checklist.items.length === 0) {
    return (
      <div className={cn('flex items-center gap-2 text-gray-500', className)}>
        <Target className="h-4 w-4" />
        <span className="text-xs font-mono">No alignment data available</span>
      </div>
    );
  }

  const scoreColor = getScoreColor(alignment.overall);
  const scoreBgColor = getScoreBgColor(alignment.overall);
  const scoreLabel = getScoreLabel(alignment.overall);

  if (compact) {
    return (
      <div
        className={cn(
          'flex items-center gap-2 px-3 py-1.5 border',
          scoreBgColor,
          className
        )}
        title={`Alignment: ${alignment.overall}% (${scoreLabel})`}
      >
        <Target className={cn('h-3.5 w-3.5', scoreColor)} />
        <span className={cn('text-xs font-mono font-bold', scoreColor)}>
          {alignment.overall}%
        </span>
        <span className="text-[10px] font-mono text-gray-400">aligned</span>
      </div>
    );
  }

  return (
    <div className={cn('space-y-4', className)}>
      {/* Main Score */}
      <div className={cn('p-4 border', scoreBgColor)}>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Target className={cn('h-5 w-5', scoreColor)} />
            <h3 className="text-sm font-mono font-medium text-white">
              Blueprint Alignment
            </h3>
          </div>
          <div className="flex items-center gap-2">
            <span className={cn('text-2xl font-mono font-bold', scoreColor)}>
              {alignment.overall}%
            </span>
            <span className={cn('text-xs font-mono px-2 py-0.5 rounded', scoreBgColor, scoreColor)}>
              {scoreLabel}
            </span>
          </div>
        </div>

        <Progress value={alignment.overall} className="h-2 mb-3" />

        {/* Status summary */}
        <div className="flex items-center gap-4 text-[10px] font-mono">
          <div className="flex items-center gap-1 text-green-400">
            <CheckCircle className="h-3 w-3" />
            <span>{alignment.byStatus.ready} ready</span>
          </div>
          <div className="flex items-center gap-1 text-yellow-400">
            <AlertCircle className="h-3 w-3" />
            <span>{alignment.byStatus.needs_attention} needs work</span>
          </div>
          {alignment.byStatus.blocked > 0 && (
            <div className="flex items-center gap-1 text-red-400">
              <XCircle className="h-3 w-3" />
              <span>{alignment.byStatus.blocked} blocked</span>
            </div>
          )}
        </div>
      </div>

      {/* Section Breakdown */}
      {showBreakdown && Object.keys(alignment.bySection).length > 0 && (
        <div className="space-y-2">
          <h4 className="text-[10px] font-mono text-gray-500 uppercase tracking-wider">
            By Section
          </h4>
          <div className="space-y-2">
            {Object.entries(alignment.bySection).map(([sectionId, data]) => {
              const sectionScore = data.score;
              const sectionColor = getScoreColor(sectionScore);
              const sectionName = SECTION_NAMES[sectionId] || sectionId;

              return (
                <div
                  key={sectionId}
                  className="flex items-center justify-between p-2 bg-black/50 border border-white/5"
                >
                  <span className="text-xs font-mono text-gray-400">
                    {sectionName}
                  </span>
                  <div className="flex items-center gap-2">
                    <Progress value={sectionScore} className="w-16 h-1" />
                    <span className={cn('text-xs font-mono font-bold', sectionColor)}>
                      {sectionScore}%
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Inline alignment badge for use in lists and cards
 */
export function AlignmentBadge({
  score,
  className,
}: {
  score: number | null | undefined;
  className?: string;
}) {
  if (score === null || score === undefined) {
    return null;
  }

  const percent = Math.round(score * 100);
  const color = getScoreColor(percent);
  const bgColor = getScoreBgColor(percent);

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-mono border',
        bgColor,
        color,
        className
      )}
    >
      <TrendingUp className="h-2.5 w-2.5" />
      {percent}%
    </span>
  );
}

export default AlignmentScore;
