'use client';

/**
 * TEG View Toggle Component
 *
 * Switches between Graph, Table, and RAW views.
 * Reference: docs/TEG_UNIVERSE_MAP_EXECUTION.md Section 2.2
 */

import { Network, Table, Code } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { TEGViewMode } from './types';

interface TEGViewToggleProps {
  mode: TEGViewMode;
  onChange: (mode: TEGViewMode) => void;
}

const views: Array<{ mode: TEGViewMode; label: string; icon: typeof Network }> = [
  { mode: 'graph', label: 'Graph', icon: Network },
  { mode: 'table', label: 'Table', icon: Table },
  { mode: 'raw', label: 'RAW', icon: Code },
];

export function TEGViewToggle({ mode, onChange }: TEGViewToggleProps) {
  return (
    <div className="flex items-center gap-1 bg-black/40 border border-white/10 p-1">
      {views.map(({ mode: viewMode, label, icon: Icon }) => (
        <button
          key={viewMode}
          onClick={() => onChange(viewMode)}
          className={cn(
            'flex items-center gap-2 px-3 py-1.5 text-xs font-mono uppercase transition-all',
            mode === viewMode
              ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40'
              : 'text-white/60 hover:text-white hover:bg-white/5'
          )}
        >
          <Icon className="w-3.5 h-3.5" />
          {label}
        </button>
      ))}
    </div>
  );
}
