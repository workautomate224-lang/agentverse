'use client';

/**
 * Reports Page
 * Generate and export simulation reports
 */

import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  FileBarChart,
  ArrowLeft,
  Terminal,
  Download,
  Plus,
  FileText,
  Clock,
  Share,
  Trash2,
} from 'lucide-react';

export default function ReportsPage() {
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
          <FileBarChart className="w-3.5 h-3.5 md:w-4 md:h-4 text-blue-400" />
          <span className="text-[10px] md:text-xs font-mono text-white/40 uppercase tracking-wider">Reports</span>
        </div>
        <h1 className="text-lg md:text-xl font-mono font-bold text-white">Reports</h1>
        <p className="text-xs md:text-sm font-mono text-white/50 mt-1">
          Generate and export simulation reports
        </p>
      </div>

      {/* Report Types */}
      <div className="max-w-4xl mb-6">
        <h2 className="text-sm font-mono font-bold text-white mb-3">Generate New Report</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <button className="p-4 bg-white/5 border border-white/10 hover:border-blue-500/30 transition-all text-left group">
            <div className="w-10 h-10 bg-blue-500/20 flex items-center justify-center mb-3 group-hover:bg-blue-500/30 transition-colors">
              <FileBarChart className="w-5 h-5 text-blue-400" />
            </div>
            <h3 className="text-sm font-mono font-bold text-white mb-1">Summary Report</h3>
            <p className="text-[10px] font-mono text-white/40">
              High-level overview of simulation results and key metrics
            </p>
          </button>
          <button className="p-4 bg-white/5 border border-white/10 hover:border-purple-500/30 transition-all text-left group">
            <div className="w-10 h-10 bg-purple-500/20 flex items-center justify-center mb-3 group-hover:bg-purple-500/30 transition-colors">
              <FileText className="w-5 h-5 text-purple-400" />
            </div>
            <h3 className="text-sm font-mono font-bold text-white mb-1">Detailed Analysis</h3>
            <p className="text-[10px] font-mono text-white/40">
              In-depth analysis with segment breakdowns and trends
            </p>
          </button>
          <button className="p-4 bg-white/5 border border-white/10 hover:border-green-500/30 transition-all text-left group">
            <div className="w-10 h-10 bg-green-500/20 flex items-center justify-center mb-3 group-hover:bg-green-500/30 transition-colors">
              <Download className="w-5 h-5 text-green-400" />
            </div>
            <h3 className="text-sm font-mono font-bold text-white mb-1">Data Export</h3>
            <p className="text-[10px] font-mono text-white/40">
              Export raw data in CSV, JSON, or Excel formats
            </p>
          </button>
        </div>
      </div>

      {/* Recent Reports */}
      <div className="max-w-4xl">
        <div className="bg-white/5 border border-white/10">
          <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
            <h2 className="text-sm font-mono font-bold text-white">Recent Reports</h2>
            <Button size="sm" className="text-xs">
              <Plus className="w-3 h-3 mr-1" />
              NEW REPORT
            </Button>
          </div>

          {/* Empty State */}
          <div className="p-12 text-center">
            <div className="w-16 h-16 bg-white/5 flex items-center justify-center mx-auto mb-4">
              <FileBarChart className="w-8 h-8 text-white/20" />
            </div>
            <h3 className="text-sm font-mono text-white/60 mb-2">No reports yet</h3>
            <p className="text-xs font-mono text-white/40 mb-4 max-w-sm mx-auto">
              Generate your first report after running a simulation to analyze and share results
            </p>
            <Button size="sm" variant="secondary">
              <Plus className="w-3 h-3 mr-2" />
              Generate First Report
            </Button>
          </div>

          {/* Example Report Row (hidden for now)
          <div className="divide-y divide-white/5">
            <div className="flex items-center justify-between px-4 py-3 hover:bg-white/[0.02]">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-blue-500/20 flex items-center justify-center">
                  <FileBarChart className="w-4 h-4 text-blue-400" />
                </div>
                <div>
                  <div className="text-sm font-mono text-white">Summary Report</div>
                  <div className="text-[10px] font-mono text-white/40 flex items-center gap-2">
                    <Clock className="w-3 h-3" />
                    Generated 2 hours ago
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button size="sm" variant="ghost" className="w-7 h-7 p-0">
                  <Share className="w-3 h-3 text-white/40" />
                </Button>
                <Button size="sm" variant="ghost" className="w-7 h-7 p-0">
                  <Download className="w-3 h-3 text-white/40" />
                </Button>
                <Button size="sm" variant="ghost" className="w-7 h-7 p-0">
                  <Trash2 className="w-3 h-3 text-red-400" />
                </Button>
              </div>
            </div>
          </div>
          */}
        </div>
      </div>

      {/* Footer */}
      <div className="mt-8 pt-4 border-t border-white/5 max-w-4xl">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-1">
            <Terminal className="w-3 h-3" />
            <span>REPORTS</span>
          </div>
          <span>AGENTVERSE v1.0</span>
        </div>
      </div>
    </div>
  );
}
