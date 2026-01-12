'use client';

/**
 * Telemetry & Replay Page
 * Watch simulation replays and explore telemetry data
 */

import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  Activity,
  ArrowLeft,
  Terminal,
  Play,
  Pause,
  SkipBack,
  SkipForward,
  Clock,
  Users,
  TrendingUp,
  Settings,
} from 'lucide-react';

export default function TelemetryReplayPage() {
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
          <Activity className="w-3.5 h-3.5 md:w-4 md:h-4 text-cyan-400" />
          <span className="text-[10px] md:text-xs font-mono text-white/40 uppercase tracking-wider">Telemetry</span>
        </div>
        <h1 className="text-lg md:text-xl font-mono font-bold text-white">Telemetry & Replay</h1>
        <p className="text-xs md:text-sm font-mono text-white/50 mt-1">
          Watch simulation replays and explore telemetry data (read-only)
        </p>
      </div>

      {/* Run Selector */}
      <div className="max-w-5xl mb-6">
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
            <div>
              <h3 className="text-xs font-mono font-bold text-white mb-1">Select Run to Replay</h3>
              <p className="text-[10px] font-mono text-white/40">Choose a completed run with telemetry data</p>
            </div>
            <select className="px-3 py-2 bg-black border border-white/10 text-sm font-mono text-white/50 focus:outline-none focus:border-white/30 appearance-none min-w-[200px]">
              <option>No runs available</option>
            </select>
          </div>
        </div>
      </div>

      {/* Replay Viewport */}
      <div className="max-w-5xl mb-4">
        <div className="bg-white/5 border border-white/10 aspect-video min-h-[300px] relative">
          {/* Grid Background */}
          <div
            className="absolute inset-0 opacity-20"
            style={{
              backgroundImage: `
                linear-gradient(to right, rgba(255,255,255,0.05) 1px, transparent 1px),
                linear-gradient(to bottom, rgba(255,255,255,0.05) 1px, transparent 1px)
              `,
              backgroundSize: '30px 30px',
            }}
          />

          {/* Empty State */}
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <div className="w-16 h-16 bg-white/5 flex items-center justify-center mx-auto mb-4">
                <Activity className="w-8 h-8 text-white/20" />
              </div>
              <h3 className="text-sm font-mono text-white/60 mb-2">No replay data</h3>
              <p className="text-xs font-mono text-white/40 max-w-sm">
                Run a simulation with telemetry enabled to view replays here
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Playback Controls */}
      <div className="max-w-5xl mb-6">
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Button size="sm" variant="outline" className="w-8 h-8 p-0" disabled>
                <SkipBack className="w-3 h-3" />
              </Button>
              <Button size="sm" className="w-8 h-8 p-0" disabled>
                <Play className="w-3 h-3" />
              </Button>
              <Button size="sm" variant="outline" className="w-8 h-8 p-0" disabled>
                <SkipForward className="w-3 h-3" />
              </Button>
            </div>
            <div className="flex-1 mx-4">
              <div className="h-1 bg-white/10 rounded-full">
                <div className="h-full w-0 bg-cyan-500 rounded-full" />
              </div>
              <div className="flex justify-between mt-1 text-[10px] font-mono text-white/30">
                <span>Tick 0</span>
                <span>Tick 0</span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <select className="px-2 py-1 bg-black border border-white/10 text-[10px] font-mono text-white appearance-none">
                <option>1x</option>
                <option>2x</option>
                <option>4x</option>
              </select>
              <Button size="sm" variant="outline" className="w-8 h-8 p-0">
                <Settings className="w-3 h-3" />
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Metrics Panel */}
      <div className="max-w-5xl">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white/5 border border-white/10 p-4">
            <div className="flex items-center gap-2 mb-2">
              <Clock className="w-4 h-4 text-white/40" />
              <span className="text-[10px] font-mono text-white/40 uppercase">Current Tick</span>
            </div>
            <div className="text-2xl font-mono font-bold text-white">--</div>
          </div>
          <div className="bg-white/5 border border-white/10 p-4">
            <div className="flex items-center gap-2 mb-2">
              <Users className="w-4 h-4 text-white/40" />
              <span className="text-[10px] font-mono text-white/40 uppercase">Active Agents</span>
            </div>
            <div className="text-2xl font-mono font-bold text-white">--</div>
          </div>
          <div className="bg-white/5 border border-white/10 p-4">
            <div className="flex items-center gap-2 mb-2">
              <TrendingUp className="w-4 h-4 text-white/40" />
              <span className="text-[10px] font-mono text-white/40 uppercase">Events This Tick</span>
            </div>
            <div className="text-2xl font-mono font-bold text-white">--</div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-8 pt-4 border-t border-white/5 max-w-5xl">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-1">
            <Terminal className="w-3 h-3" />
            <span>TELEMETRY & REPLAY (READ-ONLY)</span>
          </div>
          <span>AGENTVERSE v1.0</span>
        </div>
      </div>
    </div>
  );
}
