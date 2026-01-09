'use client';

/**
 * 2D Replay Layer Panel Component
 * Reference: project.md §11 Phase 8, Interaction_design.md §5.17
 *
 * Left panel with layer toggles (emotion, stance, influence, exposure)
 * and region/segment filters.
 */

import React from 'react';
import {
  Eye,
  EyeOff,
  Heart,
  TrendingUp,
  Users,
  Radio,
  Zap,
  MapPin,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { LayerVisibility } from './ReplayCanvas';

interface LayerConfig {
  key: keyof LayerVisibility;
  label: string;
  icon: React.ReactNode;
  color: string;
  description: string;
}

const LAYERS: LayerConfig[] = [
  {
    key: 'stance',
    label: 'Stance',
    icon: <TrendingUp className="h-4 w-4" />,
    color: 'text-green-400',
    description: 'Show agent stance as color (red=negative, green=positive)',
  },
  {
    key: 'emotion',
    label: 'Emotion',
    icon: <Heart className="h-4 w-4" />,
    color: 'text-yellow-400',
    description: 'Show emotional intensity as glow effect',
  },
  {
    key: 'influence',
    label: 'Influence',
    icon: <Users className="h-4 w-4" />,
    color: 'text-blue-400',
    description: 'Show influence level as agent size',
  },
  {
    key: 'exposure',
    label: 'Exposure',
    icon: <Radio className="h-4 w-4" />,
    color: 'text-orange-400',
    description: 'Show media exposure as outer ring',
  },
  {
    key: 'events',
    label: 'Events',
    icon: <Zap className="h-4 w-4" />,
    color: 'text-purple-400',
    description: 'Show recent event indicators',
  },
  {
    key: 'trails',
    label: 'Trails',
    icon: <MapPin className="h-4 w-4" />,
    color: 'text-cyan-400',
    description: 'Show agent movement trails',
  },
];

interface SegmentStats {
  segment: string;
  count: number;
  avgStance: number;
}

interface RegionStats {
  region: string;
  count: number;
}

interface ReplayLayerPanelProps {
  visibility: LayerVisibility;
  onVisibilityChange: (visibility: LayerVisibility) => void;
  segments: SegmentStats[];
  regions: RegionStats[];
  selectedSegments: string[];
  selectedRegions: string[];
  onSegmentFilter: (segments: string[]) => void;
  onRegionFilter: (regions: string[]) => void;
  className?: string;
}

export function ReplayLayerPanel({
  visibility,
  onVisibilityChange,
  segments,
  regions,
  selectedSegments,
  selectedRegions,
  onSegmentFilter,
  onRegionFilter,
  className,
}: ReplayLayerPanelProps) {
  // Toggle a layer
  const toggleLayer = (key: keyof LayerVisibility) => {
    onVisibilityChange({
      ...visibility,
      [key]: !visibility[key],
    });
  };

  // Toggle all layers
  const toggleAllLayers = (enabled: boolean) => {
    const newVisibility: LayerVisibility = {
      stance: enabled,
      emotion: enabled,
      influence: enabled,
      exposure: enabled,
      events: enabled,
      trails: enabled,
    };
    onVisibilityChange(newVisibility);
  };

  // Toggle segment filter
  const toggleSegment = (segment: string) => {
    if (selectedSegments.includes(segment)) {
      onSegmentFilter(selectedSegments.filter(s => s !== segment));
    } else {
      onSegmentFilter([...selectedSegments, segment]);
    }
  };

  // Toggle region filter
  const toggleRegion = (region: string) => {
    if (selectedRegions.includes(region)) {
      onRegionFilter(selectedRegions.filter(r => r !== region));
    } else {
      onRegionFilter([...selectedRegions, region]);
    }
  };

  // Get stance color class
  const getStanceColor = (stance: number): string => {
    if (stance < -0.3) return 'text-red-400';
    if (stance > 0.3) return 'text-green-400';
    return 'text-gray-400';
  };

  const allLayersEnabled = Object.values(visibility).every(Boolean);

  return (
    <div className={cn(
      'w-56 bg-black/80 border-r border-white/10 flex flex-col',
      className
    )}>
      {/* Header */}
      <div className="p-3 border-b border-white/10">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium text-white/80">Layers</h3>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => toggleAllLayers(!allLayersEnabled)}
            className="h-6 px-2 text-xs text-white/60 hover:text-cyan-400"
          >
            {allLayersEnabled ? (
              <>
                <EyeOff className="h-3 w-3 mr-1" />
                Hide All
              </>
            ) : (
              <>
                <Eye className="h-3 w-3 mr-1" />
                Show All
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Layer toggles */}
      <div className="p-2 border-b border-white/10">
        {LAYERS.map(layer => (
          <button
            key={layer.key}
            onClick={() => toggleLayer(layer.key)}
            className={cn(
              'w-full flex items-center gap-2 px-2 py-1.5 rounded text-sm transition-colors',
              visibility[layer.key]
                ? `${layer.color} bg-white/5`
                : 'text-white/40 hover:text-white/60 hover:bg-white/5'
            )}
            title={layer.description}
          >
            {layer.icon}
            <span className="flex-1 text-left">{layer.label}</span>
            {visibility[layer.key] ? (
              <Eye className="h-3 w-3 opacity-60" />
            ) : (
              <EyeOff className="h-3 w-3 opacity-40" />
            )}
          </button>
        ))}
      </div>

      {/* Segment filters */}
      <div className="flex-1 overflow-auto p-2">
        <h4 className="text-xs font-medium text-white/60 mb-2 px-2">SEGMENTS</h4>
        {segments.length === 0 ? (
          <div className="text-xs text-white/40 px-2">No segments</div>
        ) : (
          <div className="space-y-0.5">
            {segments.map(seg => (
              <button
                key={seg.segment}
                onClick={() => toggleSegment(seg.segment)}
                className={cn(
                  'w-full flex items-center gap-2 px-2 py-1 rounded text-xs transition-colors',
                  selectedSegments.includes(seg.segment) || selectedSegments.length === 0
                    ? 'text-white/80 bg-white/5'
                    : 'text-white/40 hover:text-white/60'
                )}
              >
                <span className="flex-1 text-left truncate">{seg.segment}</span>
                <span className="text-white/40">{seg.count}</span>
                <span className={cn('text-xs', getStanceColor(seg.avgStance))}>
                  {seg.avgStance > 0 ? '+' : ''}{(seg.avgStance * 100).toFixed(0)}%
                </span>
              </button>
            ))}
          </div>
        )}

        <h4 className="text-xs font-medium text-white/60 mt-4 mb-2 px-2">REGIONS</h4>
        {regions.length === 0 ? (
          <div className="text-xs text-white/40 px-2">No regions</div>
        ) : (
          <div className="space-y-0.5">
            {regions.map(reg => (
              <button
                key={reg.region}
                onClick={() => toggleRegion(reg.region)}
                className={cn(
                  'w-full flex items-center gap-2 px-2 py-1 rounded text-xs transition-colors',
                  selectedRegions.includes(reg.region) || selectedRegions.length === 0
                    ? 'text-white/80 bg-white/5'
                    : 'text-white/40 hover:text-white/60'
                )}
              >
                <span className="flex-1 text-left truncate">{reg.region}</span>
                <span className="text-white/40">{reg.count}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Quick stats */}
      <div className="p-2 border-t border-white/10 text-xs text-white/40">
        <div className="flex justify-between">
          <span>Visible agents:</span>
          <span className="text-cyan-400">
            {segments.reduce((sum, s) => sum + s.count, 0)}
          </span>
        </div>
      </div>
    </div>
  );
}
