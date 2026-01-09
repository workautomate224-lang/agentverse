'use client';

import { Play, Settings, Loader2, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { cn } from '@/lib/utils';

interface PlannerConfig {
  max_paths: number;
  max_depth: number;
  pruning_threshold: number;
  enable_clustering: boolean;
  max_clusters: number;
}

interface PlannerPanelProps {
  config: PlannerConfig;
  onConfigChange: (config: PlannerConfig) => void;
  onRunPlanner: () => void;
  isPlanning: boolean;
  canRun: boolean;
}

export function PlannerPanel({
  config,
  onConfigChange,
  onRunPlanner,
  isPlanning,
  canRun,
}: PlannerPanelProps) {
  const updateConfig = (key: keyof PlannerConfig, value: number | boolean) => {
    onConfigChange({ ...config, [key]: value });
  };

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Settings className="h-4 w-4 text-cyan-400" />
        <span className="text-sm font-medium">Planner Settings</span>
      </div>

      {/* Max Paths */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span className="text-white/60">Max Paths</span>
          <span className="font-medium">{config.max_paths}</span>
        </div>
        <Slider
          value={[config.max_paths]}
          onValueChange={([v]) => updateConfig('max_paths', v)}
          min={10}
          max={500}
          step={10}
          className="py-2"
        />
      </div>

      {/* Max Depth */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span className="text-white/60">Max Depth (steps)</span>
          <span className="font-medium">{config.max_depth}</span>
        </div>
        <Slider
          value={[config.max_depth]}
          onValueChange={([v]) => updateConfig('max_depth', v)}
          min={3}
          max={30}
          step={1}
          className="py-2"
        />
      </div>

      {/* Pruning Threshold */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span className="text-white/60">Pruning Threshold</span>
          <span className="font-medium">{(config.pruning_threshold * 100).toFixed(1)}%</span>
        </div>
        <Slider
          value={[config.pruning_threshold * 100]}
          onValueChange={([v]) => updateConfig('pruning_threshold', v / 100)}
          min={0.1}
          max={10}
          step={0.1}
          className="py-2"
        />
        <p className="text-xs text-white/40">
          Prune paths below this probability
        </p>
      </div>

      {/* Clustering */}
      <div className="pt-2 border-t border-white/10 space-y-3">
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={config.enable_clustering}
            onChange={(e) => updateConfig('enable_clustering', e.target.checked)}
            className="w-4 h-4 rounded border-white/20 bg-white/5 text-cyan-500 focus:ring-cyan-500/50"
          />
          <div>
            <span className="text-sm font-medium">Enable Clustering</span>
            <p className="text-xs text-white/40">
              Group similar paths for progressive expansion
            </p>
          </div>
        </label>

        {config.enable_clustering && (
          <div className="space-y-2 pl-7">
            <div className="flex items-center justify-between text-xs">
              <span className="text-white/60">Max Clusters</span>
              <span className="font-medium">{config.max_clusters}</span>
            </div>
            <Slider
              value={[config.max_clusters]}
              onValueChange={([v]) => updateConfig('max_clusters', v)}
              min={2}
              max={10}
              step={1}
              className="py-2"
            />
          </div>
        )}
      </div>

      {/* Run Button */}
      <div className="pt-4 border-t border-white/10">
        <Button
          onClick={onRunPlanner}
          disabled={!canRun || isPlanning}
          className={cn(
            'w-full h-10',
            canRun && !isPlanning
              ? 'bg-cyan-500 hover:bg-cyan-600 text-black'
              : ''
          )}
        >
          {isPlanning ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Planning...
            </>
          ) : (
            <>
              <Play className="h-4 w-4 mr-2" />
              Run Planner
            </>
          )}
        </Button>
        {!canRun && (
          <p className="text-xs text-white/40 text-center mt-2">
            Select a target persona first
          </p>
        )}
      </div>

      {/* Advanced Settings Note */}
      <div className="text-xs text-white/30 text-center">
        Advanced: beam width, exploration rate, etc.
      </div>
    </div>
  );
}
