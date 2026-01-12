'use client';

/**
 * Universe Map Page (Placeholder)
 * Visualize the simulation universe and agent relationships
 */

import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  Globe,
  ArrowLeft,
  Terminal,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Filter,
  Download,
  RefreshCw,
} from 'lucide-react';

export default function UniverseMapPage() {
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
          <Globe className="w-3.5 h-3.5 md:w-4 md:h-4 text-blue-400" />
          <span className="text-[10px] md:text-xs font-mono text-white/40 uppercase tracking-wider">Universe Map</span>
        </div>
        <h1 className="text-lg md:text-xl font-mono font-bold text-white">Simulation Universe</h1>
        <p className="text-xs md:text-sm font-mono text-white/50 mt-1">
          Visualize your simulation universe, agents, and their relationships
        </p>
      </div>

      {/* Toolbar */}
      <div className="max-w-5xl mb-4">
        <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-white/5 border border-white/10">
          <div className="flex items-center gap-2">
            <Button variant="secondary" size="sm" className="text-xs">
              <ZoomIn className="w-3 h-3 mr-1" />
              ZOOM IN
            </Button>
            <Button variant="secondary" size="sm" className="text-xs">
              <ZoomOut className="w-3 h-3 mr-1" />
              ZOOM OUT
            </Button>
            <Button variant="secondary" size="sm" className="text-xs">
              <Maximize2 className="w-3 h-3 mr-1" />
              FIT VIEW
            </Button>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" className="text-xs">
              <Filter className="w-3 h-3 mr-1" />
              FILTER
            </Button>
            <Button variant="outline" size="sm" className="text-xs">
              <RefreshCw className="w-3 h-3 mr-1" />
              REFRESH
            </Button>
            <Button variant="outline" size="sm" className="text-xs">
              <Download className="w-3 h-3 mr-1" />
              EXPORT
            </Button>
          </div>
        </div>
      </div>

      {/* Map Viewport */}
      <div className="max-w-5xl">
        <div className="relative bg-white/5 border border-white/10 aspect-[16/10] min-h-[400px]">
          {/* Grid Background */}
          <div
            className="absolute inset-0 opacity-20"
            style={{
              backgroundImage: `
                linear-gradient(to right, rgba(255,255,255,0.05) 1px, transparent 1px),
                linear-gradient(to bottom, rgba(255,255,255,0.05) 1px, transparent 1px)
              `,
              backgroundSize: '40px 40px',
            }}
          />

          {/* Empty State */}
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <div className="w-20 h-20 bg-white/5 flex items-center justify-center mx-auto mb-4 rounded-full">
                <Globe className="w-10 h-10 text-white/20" />
              </div>
              <h3 className="text-sm font-mono text-white/60 mb-2">Universe is empty</h3>
              <p className="text-xs font-mono text-white/40 mb-4 max-w-xs">
                Add personas and define rules to populate your simulation universe
              </p>
              <div className="flex items-center justify-center gap-3">
                <Link href={`/p/${projectId}/data-personas`}>
                  <Button size="sm" variant="secondary" className="text-xs">
                    ADD PERSONAS
                  </Button>
                </Link>
                <Link href={`/p/${projectId}/rules`}>
                  <Button size="sm" variant="secondary" className="text-xs">
                    DEFINE RULES
                  </Button>
                </Link>
              </div>
            </div>
          </div>

          {/* Coordinate Display */}
          <div className="absolute bottom-3 left-3 px-2 py-1 bg-black/80 text-[10px] font-mono text-white/40">
            X: 0.00, Y: 0.00
          </div>

          {/* Agent Count */}
          <div className="absolute bottom-3 right-3 px-2 py-1 bg-black/80 text-[10px] font-mono text-white/40">
            0 agents
          </div>
        </div>
      </div>

      {/* Legend */}
      <div className="max-w-5xl mt-4">
        <div className="flex flex-wrap items-center gap-4 p-3 bg-white/5 border border-white/10">
          <span className="text-[10px] font-mono text-white/40 uppercase">Legend:</span>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-cyan-500 rounded-full" />
            <span className="text-xs font-mono text-white/60">Collective Agents</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-purple-500 rounded-full" />
            <span className="text-xs font-mono text-white/60">Target Agents</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-1 h-3 bg-white/30" />
            <span className="text-xs font-mono text-white/60">Connections</span>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-8 pt-4 border-t border-white/5 max-w-5xl">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-1">
            <Terminal className="w-3 h-3" />
            <span>UNIVERSE MAP</span>
          </div>
          <span>AGENTVERSE v1.0</span>
        </div>
      </div>
    </div>
  );
}
