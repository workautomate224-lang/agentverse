'use client';

/**
 * Feature Disabled Component
 *
 * Displays a friendly message when users access routes that are
 * disabled in MVP mode. Provides a link back to Overview.
 *
 * Reference: DEMO2_MVP_EXECUTION.md - MVP Mode Gating
 */

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { Lock, ArrowLeft, Sparkles } from 'lucide-react';

interface FeatureDisabledProps {
  featureName?: string;
  description?: string;
}

export function FeatureDisabled({
  featureName = 'This feature',
  description,
}: FeatureDisabledProps) {
  const params = useParams();
  const projectId = params.projectId as string;

  return (
    <div className="flex-1 flex items-center justify-center min-h-[60vh]">
      <div className="max-w-md text-center px-6">
        {/* Icon */}
        <div className="w-20 h-20 mx-auto mb-6 bg-white/5 border border-white/10 flex items-center justify-center">
          <Lock className="w-10 h-10 text-white/40" />
        </div>

        {/* Title */}
        <h1 className="text-xl font-mono font-bold text-white mb-3">
          {featureName} is not available in MVP mode
        </h1>

        {/* Description */}
        <p className="text-sm font-mono text-white/60 mb-6">
          {description ||
            'This feature is part of our advanced capabilities and will be available in a future release. For now, focus on the core Demo2 workflow: create personas, run baseline, ask what-if questions, and compare results.'}
        </p>

        {/* Coming Soon Badge */}
        <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-cyan-500/10 border border-cyan-500/30 mb-8">
          <Sparkles className="w-4 h-4 text-cyan-400" />
          <span className="text-xs font-mono text-cyan-400">
            COMING IN FUTURE RELEASE
          </span>
        </div>

        {/* Back to Overview */}
        <div>
          <Link
            href={projectId ? `/p/${projectId}/overview` : '/dashboard/projects'}
            className="inline-flex items-center gap-2 px-4 py-2 bg-white text-black text-sm font-mono hover:bg-white/90 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Overview
          </Link>
        </div>

        {/* MVP Mode Indicator */}
        <div className="mt-8 pt-6 border-t border-white/10">
          <p className="text-[10px] font-mono text-white/30 uppercase tracking-wider">
            Product Mode: MVP_DEMO2
          </p>
        </div>
      </div>
    </div>
  );
}

export default FeatureDisabled;
