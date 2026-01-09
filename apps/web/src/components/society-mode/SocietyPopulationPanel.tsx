'use client';

/**
 * Society Population Panel Component
 * Reference: Interaction_design.md §5.12
 *
 * Display segment composition and persona coverage.
 */

import {
  Users,
  PieChart,
  AlertTriangle,
  CheckCircle,
  MapPin,
  TrendingUp,
} from 'lucide-react';
import { ProjectSpecStats } from '@/lib/api';
import { cn } from '@/lib/utils';
import { SocietyRunConfig } from './SocietyModeStudio';

interface SocietyPopulationPanelProps {
  projectId: string;
  stats: ProjectSpecStats | null | undefined;
  config: SocietyRunConfig;
}

// Mock segments - in real implementation this would come from API
const SEGMENTS = [
  { id: 'innovators', name: 'Innovators', count: 150, percentage: 15 },
  { id: 'early_adopters', name: 'Early Adopters', count: 200, percentage: 20 },
  { id: 'early_majority', name: 'Early Majority', count: 300, percentage: 30 },
  { id: 'late_majority', name: 'Late Majority', count: 250, percentage: 25 },
  { id: 'laggards', name: 'Laggards', count: 100, percentage: 10 },
];

const REGIONS = [
  { id: 'urban', name: 'Urban', count: 600, percentage: 60 },
  { id: 'suburban', name: 'Suburban', count: 300, percentage: 30 },
  { id: 'rural', name: 'Rural', count: 100, percentage: 10 },
];

function getCoverageStatus(coverage: number): { label: string; color: string; icon: typeof CheckCircle } {
  if (coverage >= 90) return { label: 'Excellent', color: 'text-green-400', icon: CheckCircle };
  if (coverage >= 70) return { label: 'Good', color: 'text-cyan-400', icon: CheckCircle };
  if (coverage >= 50) return { label: 'Moderate', color: 'text-yellow-400', icon: AlertTriangle };
  return { label: 'Poor', color: 'text-red-400', icon: AlertTriangle };
}

export function SocietyPopulationPanel({
  projectId,
  stats,
  config,
}: SocietyPopulationPanelProps) {
  // Use node_count as proxy for available population capacity
  const totalAgentCapacity = stats?.node_count ? stats.node_count * 100 : 0;
  const coverage = totalAgentCapacity > 0 ? Math.min((totalAgentCapacity / config.max_agents) * 100, 100) : 0;
  const coverageStatus = getCoverageStatus(coverage);
  const CoverageIcon = coverageStatus.icon;

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-white/10">
        <div className="flex items-center gap-2">
          <Users className="h-4 w-4 text-cyan-400" />
          <h3 className="text-sm font-medium">Population Overview</h3>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {/* Coverage Summary */}
        <div className="border border-white/10 bg-white/5 p-4">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm text-white/80">Persona Coverage</span>
            <div className={cn('flex items-center gap-1.5', coverageStatus.color)}>
              <CoverageIcon className="h-4 w-4" />
              <span className="text-sm font-medium">{coverageStatus.label}</span>
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-white/60">Agent Capacity</span>
              <span className="font-mono text-white/90">{totalAgentCapacity.toLocaleString()}</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-white/60">Max Agents Configured</span>
              <span className="font-mono text-white/90">{config.max_agents.toLocaleString()}</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-white/60">Effective Coverage</span>
              <span className="font-mono text-cyan-400">{coverage.toFixed(1)}%</span>
            </div>
          </div>

          {/* Coverage Bar */}
          <div className="mt-3 h-2 bg-white/10 overflow-hidden">
            <div
              className={cn(
                'h-full transition-all',
                coverage >= 90 ? 'bg-green-500' :
                coverage >= 70 ? 'bg-cyan-500' :
                coverage >= 50 ? 'bg-yellow-500' : 'bg-red-500'
              )}
              style={{ width: `${Math.min(coverage, 100)}%` }}
            />
          </div>

          {/* Warning if coverage is low */}
          {coverage < 50 && (
            <div className="mt-3 flex items-start gap-2 text-yellow-400 text-xs">
              <AlertTriangle className="h-3.5 w-3.5 flex-shrink-0 mt-0.5" />
              <span>
                Low persona coverage may lead to unreliable results. Consider adding more personas or reducing max agents.
              </span>
            </div>
          )}
        </div>

        {/* Segment Composition */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <PieChart className="h-3.5 w-3.5 text-white/40" />
            <span className="text-sm text-white/80">Segment Composition</span>
          </div>

          <div className="space-y-2">
            {SEGMENTS.map((segment) => (
              <div key={segment.id} className="flex items-center gap-3">
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-white/80">{segment.name}</span>
                    <span className="text-xs font-mono text-white/60">
                      {segment.count} ({segment.percentage}%)
                    </span>
                  </div>
                  <div className="h-1.5 bg-white/10 overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-cyan-500 to-purple-500"
                      style={{ width: `${segment.percentage}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Region Distribution */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <MapPin className="h-3.5 w-3.5 text-white/40" />
            <span className="text-sm text-white/80">Region Distribution</span>
          </div>

          <div className="grid grid-cols-3 gap-2">
            {REGIONS.map((region) => (
              <div
                key={region.id}
                className="border border-white/10 bg-white/5 p-2 text-center"
              >
                <div className="text-lg font-mono text-cyan-400">{region.percentage}%</div>
                <div className="text-xs text-white/60">{region.name}</div>
                <div className="text-xs text-white/40">{region.count}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Stats Summary */}
        {stats && (
          <div>
            <div className="flex items-center gap-2 mb-3">
              <TrendingUp className="h-3.5 w-3.5 text-white/40" />
              <span className="text-sm text-white/80">Project Stats</span>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="border border-white/10 bg-white/5 p-2">
                <div className="text-white/40">Total Nodes</div>
                <div className="font-mono text-white/90">{stats.node_count}</div>
              </div>
              <div className="border border-white/10 bg-white/5 p-2">
                <div className="text-white/40">Total Runs</div>
                <div className="font-mono text-white/90">{stats.run_count}</div>
              </div>
              <div className="border border-white/10 bg-white/5 p-2">
                <div className="text-white/40">Completed</div>
                <div className="font-mono text-green-400">{stats.completed_runs}</div>
              </div>
              <div className="border border-white/10 bg-white/5 p-2">
                <div className="text-white/40">Failed</div>
                <div className="font-mono text-red-400">{stats.failed_runs}</div>
              </div>
            </div>
          </div>
        )}

        {/* Empty State */}
        {!stats && (
          <div className="text-center py-8">
            <Users className="h-8 w-8 mx-auto mb-2 text-white/20" />
            <p className="text-sm text-white/40">No population data available</p>
            <p className="text-xs text-white/30 mt-1">
              Add personas to your project to see composition
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
