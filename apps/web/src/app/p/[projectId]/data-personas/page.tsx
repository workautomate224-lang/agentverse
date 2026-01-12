'use client';

/**
 * Data & Personas Page (Placeholder)
 * Configure data sources and simulation personas
 */

import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  Users,
  Upload,
  Database,
  Plus,
  ArrowLeft,
  Terminal,
  FileText,
  Search,
  Zap,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Persona source options
const personaSources = [
  {
    id: 'template',
    name: 'Use Templates',
    description: 'Start with pre-built persona templates from the library',
    icon: FileText,
    color: 'cyan',
  },
  {
    id: 'upload',
    name: 'Upload Data',
    description: 'Upload your own demographic or survey data',
    icon: Upload,
    color: 'purple',
  },
  {
    id: 'generate',
    name: 'AI Generation',
    description: 'Generate synthetic personas based on your goal',
    icon: Zap,
    color: 'amber',
  },
  {
    id: 'search',
    name: 'Deep Search',
    description: 'Advanced persona discovery from multiple sources',
    icon: Search,
    color: 'green',
  },
];

export default function DataPersonasPage() {
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
          <Users className="w-3.5 h-3.5 md:w-4 md:h-4 text-cyan-400" />
          <span className="text-[10px] md:text-xs font-mono text-white/40 uppercase tracking-wider">Data & Personas</span>
        </div>
        <h1 className="text-lg md:text-xl font-mono font-bold text-white">Configure Personas</h1>
        <p className="text-xs md:text-sm font-mono text-white/50 mt-1">
          Define and configure the agents that will participate in your simulation
        </p>
      </div>

      {/* Status Banner */}
      <div className="max-w-3xl mb-6 p-4 bg-yellow-500/10 border border-yellow-500/30">
        <div className="flex items-center gap-2">
          <Database className="w-4 h-4 text-yellow-400" />
          <span className="text-sm font-mono text-yellow-400">No personas configured yet</span>
        </div>
        <p className="text-xs font-mono text-white/50 mt-1">
          Choose a method below to add personas to your project.
        </p>
      </div>

      {/* Persona Source Options */}
      <div className="max-w-3xl">
        <h2 className="text-xs font-mono text-white/40 uppercase tracking-wider mb-4">Select Persona Source</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {personaSources.map((source) => {
            const Icon = source.icon;
            const colorClasses = {
              cyan: 'hover:bg-cyan-500/10 hover:border-cyan-500/30',
              purple: 'hover:bg-purple-500/10 hover:border-purple-500/30',
              amber: 'hover:bg-amber-500/10 hover:border-amber-500/30',
              green: 'hover:bg-green-500/10 hover:border-green-500/30',
            }[source.color];

            const iconColor = {
              cyan: 'text-cyan-400',
              purple: 'text-purple-400',
              amber: 'text-amber-400',
              green: 'text-green-400',
            }[source.color];

            return (
              <button
                key={source.id}
                className={cn(
                  'flex items-start gap-3 p-4 bg-white/5 border border-white/10 transition-all text-left',
                  colorClasses
                )}
              >
                <div className="w-10 h-10 bg-white/5 flex items-center justify-center flex-shrink-0">
                  <Icon className={cn('w-5 h-5', iconColor)} />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-sm font-mono font-bold text-white">{source.name}</h3>
                  <p className="text-xs font-mono text-white/50 mt-1">{source.description}</p>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Empty State Placeholder */}
      <div className="max-w-3xl mt-8">
        <div className="bg-white/5 border border-white/10 p-8 text-center">
          <div className="w-16 h-16 bg-white/5 flex items-center justify-center mx-auto mb-4">
            <Users className="w-8 h-8 text-white/20" />
          </div>
          <h3 className="text-sm font-mono text-white/60 mb-2">Personas will appear here</h3>
          <p className="text-xs font-mono text-white/40 mb-4">
            Select a source above to start building your persona pool
          </p>
          <Button size="sm" className="text-xs font-mono">
            <Plus className="w-3 h-3 mr-2" />
            ADD PERSONAS
          </Button>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-8 pt-4 border-t border-white/5 max-w-3xl">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-1">
            <Terminal className="w-3 h-3" />
            <span>DATA & PERSONAS</span>
          </div>
          <span>AGENTVERSE v1.0</span>
        </div>
      </div>
    </div>
  );
}
