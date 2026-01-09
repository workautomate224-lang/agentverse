'use client';

/**
 * ProjectOverview Component
 * Detailed view of a project spec with stats and actions.
 * Reference: project.md §6.1 (ProjectSpec)
 */

import { memo, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  FolderKanban,
  Play,
  GitBranch,
  Activity,
  Map,
  Clock,
  Calendar,
  Hash,
  Loader2,
  AlertCircle,
  RefreshCw,
  ChevronRight,
  BarChart3,
  ExternalLink,
  Globe,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { ProjectStatusBadge } from './ProjectStatusBadge';
import { RunStatusBadge } from '@/components/runs/RunStatusBadge';
import { useProjectSpec, useProjectSpecStats, useRuns } from '@/hooks/useApi';
import type { RunSummary } from '@/lib/api';

interface ProjectOverviewProps {
  projectId: string;
  onCreateRun?: () => void;
  onViewMap?: () => void;
  onViewRun?: (runId: string) => void;
  className?: string;
}

export const ProjectOverview = memo(function ProjectOverview({
  projectId,
  onCreateRun,
  onViewMap,
  onViewRun,
  className,
}: ProjectOverviewProps) {
  const router = useRouter();

  // Fetch project data
  const {
    data: project,
    isLoading: projectLoading,
    error: projectError,
    refetch: refetchProject,
  } = useProjectSpec(projectId);

  // Fetch project stats
  const { data: stats } = useProjectSpecStats(projectId);

  // Fetch recent runs
  const { data: recentRuns = [] } = useRuns({ project_id: projectId, limit: 5 });

  // Format date
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // Handle view run
  const handleViewRun = useCallback(
    (runId: string) => {
      onViewRun?.(runId);
      router.push(`/dashboard/runs/${runId}`);
    },
    [router, onViewRun]
  );

  // Loading state
  if (projectLoading) {
    return (
      <div className={cn('flex items-center justify-center p-12', className)}>
        <div className="flex items-center gap-3 text-white/40">
          <Loader2 className="w-5 h-5 animate-spin" />
          <span className="text-sm font-mono">Loading project...</span>
        </div>
      </div>
    );
  }

  // Error state
  if (projectError || !project) {
    return (
      <div className={cn('flex items-center justify-center p-12', className)}>
        <div className="text-center">
          <AlertCircle className="w-8 h-8 text-red-400 mx-auto mb-3" />
          <p className="text-sm font-mono text-red-400 mb-2">Failed to load project</p>
          <Button variant="secondary" size="sm" onClick={() => refetchProject()}>
            <RefreshCw className="w-3 h-3 mr-1" />
            Retry
          </Button>
        </div>
      </div>
    );
  }

  // Calculate status
  const status = (project.run_count || 0) > 0 ? 'active' : 'draft';

  return (
    <div className={cn('space-y-6', className)}>
      {/* Header */}
      <div className="bg-black border border-white/10">
        <div className="p-6 border-b border-white/5">
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-cyan-500/10">
                <FolderKanban className="w-6 h-6 text-cyan-400" />
              </div>
              <div>
                <h1 className="text-xl font-mono font-bold text-white">{project.name}</h1>
                <div className="flex items-center gap-3 mt-1">
                  <ProjectStatusBadge status={status} size="sm" />
                  <span className="text-xs font-mono text-white/40">
                    ID: {project.id.slice(0, 16)}...
                  </span>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Button variant="secondary" size="sm" onClick={onViewMap}>
                <Map className="w-3 h-3 mr-1" />
                Universe Map
              </Button>
              <Button variant="primary" size="sm" onClick={onCreateRun}>
                <Play className="w-3 h-3 mr-1" />
                New Run
              </Button>
            </div>
          </div>

          {project.description && (
            <p className="text-sm font-mono text-white/60 max-w-2xl">
              {project.description}
            </p>
          )}
        </div>

        {/* Metadata */}
        <div className="grid grid-cols-2 md:grid-cols-4 divide-x divide-white/5">
          <div className="p-4">
            <div className="flex items-center gap-2 text-white/40 mb-1">
              <Calendar className="w-3 h-3" />
              <span className="text-[10px] font-mono uppercase">Created</span>
            </div>
            <p className="text-xs font-mono text-white">{formatDate(project.created_at)}</p>
          </div>
          <div className="p-4">
            <div className="flex items-center gap-2 text-white/40 mb-1">
              <Clock className="w-3 h-3" />
              <span className="text-[10px] font-mono uppercase">Updated</span>
            </div>
            <p className="text-xs font-mono text-white">
              {formatDate(project.updated_at || project.created_at)}
            </p>
          </div>
          <div className="p-4">
            <div className="flex items-center gap-2 text-white/40 mb-1">
              <Globe className="w-3 h-3" />
              <span className="text-[10px] font-mono uppercase">Domain</span>
            </div>
            <p className="text-xs font-mono text-white">{project.domain || 'general'}</p>
          </div>
          <div className="p-4">
            <div className="flex items-center gap-2 text-white/40 mb-1">
              <Hash className="w-3 h-3" />
              <span className="text-[10px] font-mono uppercase">Root Node</span>
            </div>
            <p className="text-xs font-mono text-white">
              {project.root_node_id ? project.root_node_id.slice(0, 8) : 'None'}
            </p>
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          icon={Activity}
          label="Total Runs"
          value={project.run_count || stats?.run_count || 0}
          color="green"
        />
        <StatCard
          icon={GitBranch}
          label="Nodes"
          value={project.node_count || stats?.node_count || 0}
          color="purple"
        />
        <StatCard
          icon={BarChart3}
          label="Completed"
          value={stats?.completed_runs || 0}
          color="cyan"
        />
        <StatCard
          icon={AlertCircle}
          label="Failed"
          value={stats?.failed_runs || 0}
          color="orange"
        />
      </div>

      {/* Recent Runs */}
      <div className="bg-black border border-white/10">
        <div className="flex items-center justify-between p-4 border-b border-white/5">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-white/40" />
            <span className="text-xs font-mono text-white/40 uppercase tracking-wider">
              Recent Runs
            </span>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.push(`/dashboard/projects/${projectId}/runs`)}
          >
            View All
            <ChevronRight className="w-3 h-3 ml-1" />
          </Button>
        </div>

        {recentRuns.length > 0 ? (
          <div className="divide-y divide-white/5">
            {recentRuns.slice(0, 5).map((run) => (
              <RunListItem key={run.run_id} run={run} onView={handleViewRun} />
            ))}
          </div>
        ) : (
          <div className="p-8 text-center">
            <Activity className="w-6 h-6 text-white/20 mx-auto mb-2" />
            <p className="text-xs font-mono text-white/40 mb-3">No runs yet</p>
            <Button variant="secondary" size="sm" onClick={onCreateRun}>
              <Play className="w-3 h-3 mr-1" />
              Start First Run
            </Button>
          </div>
        )}
      </div>

      {/* Settings Summary */}
      {project.settings && (
        <div className="bg-black border border-white/10">
          <div className="flex items-center justify-between p-4 border-b border-white/5">
            <div className="flex items-center gap-2">
              <Hash className="w-4 h-4 text-white/40" />
              <span className="text-xs font-mono text-white/40 uppercase tracking-wider">
                Default Settings
              </span>
            </div>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 divide-x divide-white/5">
            <div className="p-4">
              <p className="text-[10px] font-mono text-white/40 uppercase mb-1">Horizon</p>
              <p className="text-sm font-mono text-white">{project.settings.default_horizon} ticks</p>
            </div>
            <div className="p-4">
              <p className="text-[10px] font-mono text-white/40 uppercase mb-1">Tick Rate</p>
              <p className="text-sm font-mono text-white">{project.settings.default_tick_rate} ms</p>
            </div>
            <div className="p-4">
              <p className="text-[10px] font-mono text-white/40 uppercase mb-1">Agent Count</p>
              <p className="text-sm font-mono text-white">{project.settings.default_agent_count}</p>
            </div>
            <div className="p-4">
              <p className="text-[10px] font-mono text-white/40 uppercase mb-1">Public Templates</p>
              <p className="text-sm font-mono text-white">
                {project.settings.allow_public_templates ? 'Allowed' : 'Disabled'}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
});

// Stat card sub-component
const StatCard = memo(function StatCard({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: typeof Activity;
  label: string;
  value: number | string;
  color: 'cyan' | 'green' | 'purple' | 'orange';
}) {
  const colorClasses = {
    cyan: 'bg-cyan-500/10 text-cyan-400',
    green: 'bg-green-500/10 text-green-400',
    purple: 'bg-purple-500/10 text-purple-400',
    orange: 'bg-orange-500/10 text-orange-400',
  };

  return (
    <div className="bg-black border border-white/10 p-4">
      <div className="flex items-center justify-between mb-3">
        <div className={cn('p-2', colorClasses[color].split(' ')[0])}>
          <Icon className={cn('w-4 h-4', colorClasses[color].split(' ')[1])} />
        </div>
      </div>
      <p className="text-2xl font-mono font-bold text-white">{value}</p>
      <p className="text-[10px] font-mono text-white/40 uppercase tracking-wider mt-1">
        {label}
      </p>
    </div>
  );
});

// Run list item sub-component
const RunListItem = memo(function RunListItem({
  run,
  onView,
}: {
  run: RunSummary;
  onView: (runId: string) => void;
}) {
  return (
    <button
      onClick={() => onView(run.run_id)}
      className="w-full flex items-center justify-between p-4 hover:bg-white/5 transition-colors text-left"
    >
      <div className="flex items-center gap-3">
        <RunStatusBadge status={run.status} size="sm" />
        <div>
          <p className="text-sm font-mono text-white">
            Run {run.run_id.slice(0, 8)}
          </p>
          <p className="text-[10px] font-mono text-white/40">
            {new Date(run.created_at).toLocaleString()}
          </p>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <div className="text-right">
          <p className="text-xs font-mono text-white/60">
            {run.timing.current_tick || 0} / {run.timing.total_ticks || '--'} ticks
          </p>
          {run.has_results && (
            <p className="text-[10px] font-mono text-green-400">
              Results available
            </p>
          )}
        </div>
        <ExternalLink className="w-3 h-3 text-white/30" />
      </div>
    </button>
  );
});

export default ProjectOverview;
