'use client';

/**
 * Target Planner Page
 * Design targeted simulations for specific user personas
 */

import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  Crosshair,
  ArrowLeft,
  Terminal,
  Plus,
  User,
  Zap,
  Clock,
  Play,
  Search,
} from 'lucide-react';

export default function TargetPlannerPage() {
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
          <Crosshair className="w-3.5 h-3.5 md:w-4 md:h-4 text-purple-400" />
          <span className="text-[10px] md:text-xs font-mono text-white/40 uppercase tracking-wider">Target Mode</span>
        </div>
        <h1 className="text-lg md:text-xl font-mono font-bold text-white">Target Planner</h1>
        <p className="text-xs md:text-sm font-mono text-white/50 mt-1">
          Design targeted simulations for specific user personas
        </p>
      </div>

      {/* Search/Select Target */}
      <div className="max-w-4xl mb-6">
        <div className="bg-white/5 border border-white/10 p-4">
          <h3 className="text-xs font-mono font-bold text-white mb-3">Select Target Persona</h3>
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
              <input
                type="text"
                placeholder="Search personas or create new..."
                className="w-full pl-10 pr-3 py-2 bg-black border border-white/10 text-sm font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-purple-500/50"
              />
            </div>
            <Link href={`/p/${projectId}/data-personas`}>
              <Button size="sm" variant="outline" className="text-xs">
                BROWSE ALL
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* Target Cards */}
      <div className="max-w-4xl mb-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {/* Example persona card */}
          <div className="bg-white/5 border border-white/10 p-4 hover:border-purple-500/30 transition-all cursor-pointer group">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 bg-purple-500/20 flex items-center justify-center">
                <User className="w-5 h-5 text-purple-400" />
              </div>
              <div>
                <h4 className="text-sm font-mono font-bold text-white">Select a Persona</h4>
                <p className="text-[10px] font-mono text-white/40">To start target planning</p>
              </div>
            </div>
            <div className="text-xs font-mono text-white/40">
              Choose from your persona library or create a new one
            </div>
          </div>
        </div>
      </div>

      {/* Configuration */}
      <div className="max-w-4xl grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        {/* Journey Configuration */}
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex items-center gap-2 mb-3">
            <Clock className="w-4 h-4 text-cyan-400" />
            <h3 className="text-xs font-mono font-bold text-white">Journey Configuration</h3>
          </div>
          <div className="space-y-3">
            <div>
              <label className="block text-[10px] font-mono text-white/40 uppercase mb-1">Duration</label>
              <select className="w-full px-3 py-2 bg-black border border-white/10 text-sm font-mono text-white focus:outline-none focus:border-white/30 appearance-none">
                <option>30 days</option>
                <option>60 days</option>
                <option>90 days</option>
                <option>Custom</option>
              </select>
            </div>
            <div>
              <label className="block text-[10px] font-mono text-white/40 uppercase mb-1">Decision Points</label>
              <input
                type="number"
                defaultValue={5}
                className="w-full px-3 py-2 bg-black border border-white/10 text-sm font-mono text-white focus:outline-none focus:border-white/30"
              />
            </div>
          </div>
        </div>

        {/* Scenarios */}
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex items-center gap-2 mb-3">
            <Zap className="w-4 h-4 text-amber-400" />
            <h3 className="text-xs font-mono font-bold text-white">Scenarios to Test</h3>
          </div>
          <div className="space-y-2">
            <div className="flex items-center gap-2 p-2 bg-black/50 border border-white/5">
              <input type="checkbox" className="accent-purple-500" />
              <span className="text-xs font-mono text-white/60">Price increase 10%</span>
            </div>
            <div className="flex items-center gap-2 p-2 bg-black/50 border border-white/5">
              <input type="checkbox" className="accent-purple-500" />
              <span className="text-xs font-mono text-white/60">Competitor discount</span>
            </div>
            <div className="flex items-center gap-2 p-2 bg-black/50 border border-white/5">
              <input type="checkbox" className="accent-purple-500" />
              <span className="text-xs font-mono text-white/60">New feature launch</span>
            </div>
            <Link href={`/p/${projectId}/event-lab`}>
              <Button size="sm" variant="ghost" className="w-full text-xs text-white/40">
                <Plus className="w-3 h-3 mr-1" />
                Add Custom Scenario
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* Run Button */}
      <div className="max-w-4xl">
        <div className="bg-purple-500/10 border border-purple-500/30 p-4 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-mono font-bold text-purple-400">Run Target Simulation</h3>
            <p className="text-[10px] font-mono text-white/40">
              Select a target persona to enable simulation
            </p>
          </div>
          <Button className="text-xs bg-purple-500 hover:bg-purple-600 text-white" disabled>
            <Play className="w-3 h-3 mr-2" />
            START
          </Button>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-8 pt-4 border-t border-white/5 max-w-4xl">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-1">
            <Terminal className="w-3 h-3" />
            <span>TARGET PLANNER</span>
          </div>
          <span>AGENTVERSE v1.0</span>
        </div>
      </div>
    </div>
  );
}
