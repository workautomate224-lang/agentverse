'use client';

/**
 * Run Center Page (Placeholder)
 * Configure and execute simulation runs
 */

import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  Play,
  ArrowLeft,
  Terminal,
  Clock,
  Settings,
  History,
  Gauge,
  Zap,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Run configuration options
const runOptions = [
  {
    id: 'baseline',
    name: 'Baseline Run',
    description: 'Standard simulation with default parameters',
    icon: Play,
    color: 'green',
  },
  {
    id: 'quick',
    name: 'Quick Test',
    description: 'Faster run with reduced agent count',
    icon: Zap,
    color: 'yellow',
  },
  {
    id: 'custom',
    name: 'Custom Run',
    description: 'Configure all parameters manually',
    icon: Settings,
    color: 'purple',
  },
];

export default function RunCenterPage() {
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
          <Play className="w-3.5 h-3.5 md:w-4 md:h-4 text-green-400" />
          <span className="text-[10px] md:text-xs font-mono text-white/40 uppercase tracking-wider">Run Center</span>
        </div>
        <h1 className="text-lg md:text-xl font-mono font-bold text-white">Simulation Runs</h1>
        <p className="text-xs md:text-sm font-mono text-white/50 mt-1">
          Configure and execute simulation runs for your project
        </p>
      </div>

      {/* Run Options */}
      <div className="max-w-3xl mb-8">
        <h2 className="text-xs font-mono text-white/40 uppercase tracking-wider mb-4">Start New Run</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {runOptions.map((option) => {
            const Icon = option.icon;
            const colorClasses = {
              green: 'hover:bg-green-500/10 hover:border-green-500/30',
              yellow: 'hover:bg-yellow-500/10 hover:border-yellow-500/30',
              purple: 'hover:bg-purple-500/10 hover:border-purple-500/30',
            }[option.color];

            const iconColor = {
              green: 'text-green-400',
              yellow: 'text-yellow-400',
              purple: 'text-purple-400',
            }[option.color];

            return (
              <button
                key={option.id}
                className={cn(
                  'flex flex-col items-center gap-3 p-4 bg-white/5 border border-white/10 transition-all text-center',
                  colorClasses
                )}
              >
                <div className="w-12 h-12 bg-white/5 flex items-center justify-center">
                  <Icon className={cn('w-6 h-6', iconColor)} />
                </div>
                <div>
                  <h3 className="text-sm font-mono font-bold text-white">{option.name}</h3>
                  <p className="text-[10px] font-mono text-white/50 mt-1">{option.description}</p>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Quick Stats */}
      <div className="max-w-3xl mb-8">
        <h2 className="text-xs font-mono text-white/40 uppercase tracking-wider mb-4">Configuration Summary</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="bg-white/5 border border-white/10 p-4">
            <div className="flex items-center gap-2 text-white/40 mb-2">
              <Clock className="w-3.5 h-3.5" />
              <span className="text-[10px] font-mono uppercase">Horizon</span>
            </div>
            <p className="text-lg font-mono font-bold text-white">100</p>
            <p className="text-[10px] font-mono text-white/40">ticks</p>
          </div>
          <div className="bg-white/5 border border-white/10 p-4">
            <div className="flex items-center gap-2 text-white/40 mb-2">
              <Gauge className="w-3.5 h-3.5" />
              <span className="text-[10px] font-mono uppercase">Agents</span>
            </div>
            <p className="text-lg font-mono font-bold text-white">0</p>
            <p className="text-[10px] font-mono text-white/40">configured</p>
          </div>
          <div className="bg-white/5 border border-white/10 p-4">
            <div className="flex items-center gap-2 text-white/40 mb-2">
              <Settings className="w-3.5 h-3.5" />
              <span className="text-[10px] font-mono uppercase">Rules</span>
            </div>
            <p className="text-lg font-mono font-bold text-white">0</p>
            <p className="text-[10px] font-mono text-white/40">defined</p>
          </div>
          <div className="bg-white/5 border border-white/10 p-4">
            <div className="flex items-center gap-2 text-white/40 mb-2">
              <History className="w-3.5 h-3.5" />
              <span className="text-[10px] font-mono uppercase">Runs</span>
            </div>
            <p className="text-lg font-mono font-bold text-white">0</p>
            <p className="text-[10px] font-mono text-white/40">completed</p>
          </div>
        </div>
      </div>

      {/* Run History */}
      <div className="max-w-3xl">
        <h2 className="text-xs font-mono text-white/40 uppercase tracking-wider mb-4">Run History</h2>
        <div className="bg-white/5 border border-white/10 p-8 text-center">
          <div className="w-16 h-16 bg-white/5 flex items-center justify-center mx-auto mb-4">
            <History className="w-8 h-8 text-white/20" />
          </div>
          <h3 className="text-sm font-mono text-white/60 mb-2">No runs yet</h3>
          <p className="text-xs font-mono text-white/40 mb-4">
            Configure your project and start your first simulation run
          </p>
          <Button size="sm" className="text-xs font-mono bg-green-500 hover:bg-green-600">
            <Play className="w-3 h-3 mr-2" />
            START BASELINE RUN
          </Button>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-8 pt-4 border-t border-white/5 max-w-3xl">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-1">
            <Terminal className="w-3 h-3" />
            <span>RUN CENTER</span>
          </div>
          <span>AGENTVERSE v1.0</span>
        </div>
      </div>
    </div>
  );
}
