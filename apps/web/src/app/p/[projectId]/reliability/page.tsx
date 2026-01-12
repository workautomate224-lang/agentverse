'use client';

/**
 * Reliability Page
 * View prediction reliability scores and confidence metrics
 */

import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  ShieldCheck,
  ArrowLeft,
  Terminal,
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  Info,
  RefreshCw,
} from 'lucide-react';

export default function ReliabilityPage() {
  const params = useParams();
  const projectId = params.projectId as string;

  return (
    <div className="min-h-screen bg-black p-4 md:p-6">
      {/* Header */}
      <div className="mb-6 md:mb-8">
        <Link href={`/p/${projectId}/overview`}>
          <Button variant="ghost" size="sm" className="mb-3 text-[10px] md:text-xs">
            <ArrowLeft className="w-3 h-3 mr-1 md:mr-2" />
            BACK TO OVERVIEW
          </Button>
        </Link>
        <div className="flex items-center gap-2 mb-1">
          <ShieldCheck className="w-3.5 h-3.5 md:w-4 md:h-4 text-green-400" />
          <span className="text-[10px] md:text-xs font-mono text-white/40 uppercase tracking-wider">Reliability</span>
        </div>
        <h1 className="text-lg md:text-xl font-mono font-bold text-white">Reliability Dashboard</h1>
        <p className="text-xs md:text-sm font-mono text-white/50 mt-1">
          View prediction reliability scores and confidence metrics
        </p>
      </div>

      {/* Score Overview */}
      <div className="max-w-4xl mb-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white/5 border border-white/10 p-4">
            <div className="text-[10px] font-mono text-white/40 uppercase mb-1">Overall Score</div>
            <div className="text-3xl font-mono font-bold text-white">--</div>
            <div className="text-xs font-mono text-white/30">No data yet</div>
          </div>
          <div className="bg-white/5 border border-white/10 p-4">
            <div className="text-[10px] font-mono text-white/40 uppercase mb-1">Confidence</div>
            <div className="text-3xl font-mono font-bold text-white">--</div>
            <div className="text-xs font-mono text-white/30">No runs</div>
          </div>
          <div className="bg-white/5 border border-white/10 p-4">
            <div className="text-[10px] font-mono text-white/40 uppercase mb-1">Stability</div>
            <div className="text-3xl font-mono font-bold text-white">--</div>
            <div className="text-xs font-mono text-white/30">Needs 3+ runs</div>
          </div>
          <div className="bg-white/5 border border-white/10 p-4">
            <div className="text-[10px] font-mono text-white/40 uppercase mb-1">Calibration</div>
            <div className="text-3xl font-mono font-bold text-white">--</div>
            <div className="text-xs font-mono text-white/30">Not calibrated</div>
          </div>
        </div>
      </div>

      {/* Reliability Factors */}
      <div className="max-w-4xl mb-6">
        <div className="bg-white/5 border border-white/10">
          <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
            <h2 className="text-sm font-mono font-bold text-white">Reliability Factors</h2>
            <Button size="sm" variant="outline" className="text-xs" disabled>
              <RefreshCw className="w-3 h-3 mr-1" />
              RECALCULATE
            </Button>
          </div>
          <div className="divide-y divide-white/5">
            <div className="flex items-center justify-between px-4 py-3">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-white/5 flex items-center justify-center">
                  <TrendingUp className="w-4 h-4 text-white/30" />
                </div>
                <div>
                  <div className="text-sm font-mono text-white">Data Quality</div>
                  <div className="text-[10px] font-mono text-white/40">Persona completeness and validity</div>
                </div>
              </div>
              <div className="text-sm font-mono text-white/30">--</div>
            </div>
            <div className="flex items-center justify-between px-4 py-3">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-white/5 flex items-center justify-center">
                  <CheckCircle className="w-4 h-4 text-white/30" />
                </div>
                <div>
                  <div className="text-sm font-mono text-white">Rule Coverage</div>
                  <div className="text-[10px] font-mono text-white/40">Decision rules and logic completeness</div>
                </div>
              </div>
              <div className="text-sm font-mono text-white/30">--</div>
            </div>
            <div className="flex items-center justify-between px-4 py-3">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-white/5 flex items-center justify-center">
                  <AlertTriangle className="w-4 h-4 text-white/30" />
                </div>
                <div>
                  <div className="text-sm font-mono text-white">Run Consistency</div>
                  <div className="text-[10px] font-mono text-white/40">Variance across multiple runs</div>
                </div>
              </div>
              <div className="text-sm font-mono text-white/30">--</div>
            </div>
          </div>
        </div>
      </div>

      {/* Info Box */}
      <div className="max-w-4xl">
        <div className="bg-cyan-500/10 border border-cyan-500/30 p-4">
          <div className="flex items-start gap-3">
            <Info className="w-5 h-5 text-cyan-400 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="text-sm font-mono font-bold text-cyan-400 mb-1">How Reliability Works</h3>
              <p className="text-xs font-mono text-white/50">
                Reliability scores are calculated based on data quality, rule coverage, run consistency,
                and calibration against historical data. Run multiple simulations and add ground truth
                data to improve your reliability score.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-8 pt-4 border-t border-white/5 max-w-4xl">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-1">
            <Terminal className="w-3 h-3" />
            <span>RELIABILITY DASHBOARD</span>
          </div>
          <span>AGENTVERSE v1.0</span>
        </div>
      </div>
    </div>
  );
}
