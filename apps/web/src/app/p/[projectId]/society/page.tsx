'use client';

/**
 * Society Simulation Page
 * Run collective behavior simulations with agent populations
 */

import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  Network,
  ArrowLeft,
  Terminal,
  Play,
  Users,
  Zap,
  TrendingUp,
  Clock,
  Settings,
} from 'lucide-react';

export default function SocietySimulationPage() {
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
          <Network className="w-3.5 h-3.5 md:w-4 md:h-4 text-cyan-400" />
          <span className="text-[10px] md:text-xs font-mono text-white/40 uppercase tracking-wider">Society Mode</span>
        </div>
        <h1 className="text-lg md:text-xl font-mono font-bold text-white">Society Simulation</h1>
        <p className="text-xs md:text-sm font-mono text-white/50 mt-1">
          Run collective behavior simulations with agent populations
        </p>
      </div>

      {/* Configuration Panel */}
      <div className="max-w-4xl grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
        {/* Population */}
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex items-center gap-2 mb-3">
            <Users className="w-4 h-4 text-cyan-400" />
            <h3 className="text-xs font-mono font-bold text-white">Population</h3>
          </div>
          <div className="space-y-3">
            <div>
              <label className="block text-[10px] font-mono text-white/40 uppercase mb-1">Agent Count</label>
              <input
                type="number"
                defaultValue={1000}
                className="w-full px-3 py-2 bg-black border border-white/10 text-sm font-mono text-white focus:outline-none focus:border-white/30"
              />
            </div>
            <div>
              <label className="block text-[10px] font-mono text-white/40 uppercase mb-1">Segments</label>
              <select className="w-full px-3 py-2 bg-black border border-white/10 text-sm font-mono text-white focus:outline-none focus:border-white/30 appearance-none">
                <option>From Personas</option>
                <option>Auto-Generate</option>
                <option>Custom</option>
              </select>
            </div>
          </div>
        </div>

        {/* Simulation */}
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex items-center gap-2 mb-3">
            <Clock className="w-4 h-4 text-purple-400" />
            <h3 className="text-xs font-mono font-bold text-white">Simulation</h3>
          </div>
          <div className="space-y-3">
            <div>
              <label className="block text-[10px] font-mono text-white/40 uppercase mb-1">Horizon (ticks)</label>
              <input
                type="number"
                defaultValue={100}
                className="w-full px-3 py-2 bg-black border border-white/10 text-sm font-mono text-white focus:outline-none focus:border-white/30"
              />
            </div>
            <div>
              <label className="block text-[10px] font-mono text-white/40 uppercase mb-1">Tick Rate</label>
              <select className="w-full px-3 py-2 bg-black border border-white/10 text-sm font-mono text-white focus:outline-none focus:border-white/30 appearance-none">
                <option>1 day/tick</option>
                <option>1 week/tick</option>
                <option>1 hour/tick</option>
              </select>
            </div>
          </div>
        </div>

        {/* Events */}
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex items-center gap-2 mb-3">
            <Zap className="w-4 h-4 text-amber-400" />
            <h3 className="text-xs font-mono font-bold text-white">Events</h3>
          </div>
          <div className="space-y-3">
            <p className="text-[10px] font-mono text-white/40">
              Configure events in the Event Lab
            </p>
            <Link href={`/p/${projectId}/event-lab`}>
              <Button size="sm" variant="outline" className="w-full text-xs">
                OPEN EVENT LAB
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* Run Button */}
      <div className="max-w-4xl mb-6">
        <div className="bg-cyan-500/10 border border-cyan-500/30 p-4 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-mono font-bold text-cyan-400">Ready to Run</h3>
            <p className="text-[10px] font-mono text-white/40">
              1,000 agents • 100 ticks • 0 events configured
            </p>
          </div>
          <Button className="text-xs bg-cyan-500 hover:bg-cyan-600 text-black">
            <Play className="w-3 h-3 mr-2" />
            START SIMULATION
          </Button>
        </div>
      </div>

      {/* Results Preview */}
      <div className="max-w-4xl">
        <div className="bg-white/5 border border-white/10">
          <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
            <h2 className="text-sm font-mono font-bold text-white">Recent Runs</h2>
            <Link href={`/p/${projectId}/run-center`}>
              <Button size="sm" variant="outline" className="text-xs">
                VIEW ALL RUNS
              </Button>
            </Link>
          </div>
          <div className="p-12 text-center">
            <div className="w-16 h-16 bg-white/5 flex items-center justify-center mx-auto mb-4">
              <TrendingUp className="w-8 h-8 text-white/20" />
            </div>
            <h3 className="text-sm font-mono text-white/60 mb-2">No runs yet</h3>
            <p className="text-xs font-mono text-white/40 max-w-sm mx-auto">
              Configure your simulation parameters and start your first run to see results here.
            </p>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-8 pt-4 border-t border-white/5 max-w-4xl">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-1">
            <Terminal className="w-3 h-3" />
            <span>SOCIETY SIMULATION</span>
          </div>
          <span>AGENTVERSE v1.0</span>
        </div>
      </div>
    </div>
  );
}
