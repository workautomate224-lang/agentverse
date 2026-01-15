'use client';

/**
 * Project Overview Page
 * Shows project header, setup checklist, real stats, and quick action CTAs
 * Reference: blueprint.md §4, §7
 */

import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  FolderKanban,
  Users,
  Target,
  Layers,
  Play,
  CheckCircle,
  Circle,
  ArrowRight,
  ScrollText,
  Globe,
  Terminal,
  Sparkles,
  Clock,
  GitBranch,
  Activity,
  TrendingUp,
  BarChart3,
  Loader2,
  XCircle,
  AlertCircle,
  HelpCircle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useNodes, useRuns, useProject, useActiveBlueprint } from '@/hooks/useApi';
import { ClarifyPanel } from '@/components/pil';
import { useMemo } from 'react';

// Core type styling
const coreTypeConfig = {
  collective: { label: 'Collective Dynamics', icon: Users, color: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30' },
  target: { label: 'Targeted Decision', icon: Target, color: 'bg-purple-500/20 text-purple-400 border-purple-500/30' },
  hybrid: { label: 'Hybrid Strategic', icon: Layers, color: 'bg-amber-500/20 text-amber-400 border-amber-500/30' },
};

// Setup checklist items
const checklistItems = [
  {
    id: 'data-personas',
    name: 'Configure Data & Personas',
    description: 'Upload data sources and define your simulation personas',
    href: 'data-personas',
    icon: Users,
  },
  {
    id: 'rules',
    name: 'Define Rules & Logic',
    description: 'Set up decision rules and behavioral patterns',
    href: 'rules',
    icon: ScrollText,
  },
  {
    id: 'run-center',
    name: 'Configure Run Parameters',
    description: 'Set simulation parameters and baseline configuration',
    href: 'run-center',
    icon: Play,
  },
  {
    id: 'universe-map',
    name: 'Review Universe Map',
    description: 'Visualize and verify your simulation universe',
    href: 'universe-map',
    icon: Globe,
  },
];

// Stats card component
function StatCard({
  icon: Icon,
  label,
  value,
  subValue,
  color,
  href,
  projectId,
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  subValue?: string;
  color: string;
  href?: string;
  projectId?: string;
}) {
  const content = (
    <div className={cn(
      'p-4 border transition-all',
      href ? 'hover:bg-white/5 cursor-pointer' : '',
      color
    )}>
      <div className="flex items-center gap-2 mb-2">
        <Icon className="w-4 h-4" />
        <span className="text-[10px] font-mono uppercase tracking-wider">{label}</span>
      </div>
      <div className="text-2xl font-mono font-bold text-white">{value}</div>
      {subValue && (
        <div className="text-[10px] font-mono text-white/40 mt-1">{subValue}</div>
      )}
    </div>
  );

  if (href && projectId) {
    return <Link href={`/p/${projectId}/${href}`}>{content}</Link>;
  }
  return content;
}

export default function ProjectOverviewPage() {
  const params = useParams();
  const projectId = params.projectId as string;

  // Fetch real data from API
  const { data: project, isLoading: projectLoading } = useProject(projectId);
  const { data: nodes, isLoading: nodesLoading } = useNodes({ project_id: projectId, limit: 100 });
  const { data: runs, isLoading: runsLoading } = useRuns({ project_id: projectId, limit: 100 });

  // Blueprint data for Clarify Panel (blueprint.md §4, §7)
  const { data: blueprint, isLoading: blueprintLoading } = useActiveBlueprint(projectId);

  const isLoading = projectLoading || nodesLoading || runsLoading || blueprintLoading;

  // Calculate stats from real data
  const stats = useMemo(() => {
    const allRuns = runs || [];
    const allNodes = nodes || [];

    const totalRuns = allRuns.length;
    const succeededRuns = allRuns.filter(r => r.status === 'succeeded').length;
    const failedRuns = allRuns.filter(r => r.status === 'failed').length;
    const runningRuns = allRuns.filter(r => r.status === 'running').length;
    const queuedRuns = allRuns.filter(r => r.status === 'queued').length;

    const successRate = totalRuns > 0 ? Math.round((succeededRuns / totalRuns) * 100) : 0;

    const nodeCount = allNodes.length;
    const forkCount = allNodes.filter(n => n.parent_node_id).length;

    return {
      totalRuns,
      succeededRuns,
      failedRuns,
      runningRuns,
      queuedRuns,
      successRate,
      nodeCount,
      forkCount,
    };
  }, [runs, nodes]);

  // Determine setup progress based on actual data
  const setupProgress = useMemo(() => ({
    dataPersonas: (nodes?.length || 0) > 0 || (runs?.length || 0) > 0,
    rules: true, // Assume rules are defined if project exists
    runCenter: (runs?.length || 0) > 0,
    universeMap: (nodes?.length || 0) > 0,
  }), [nodes, runs]);

  // Project display info
  const projectName = project?.name || 'Project';
  const projectGoal = project?.description || 'No description';
  const projectCreatedAt = project?.created_at || new Date().toISOString();
  const coreType = 'collective' as const; // Default for now

  const coreConfig = coreTypeConfig[coreType];
  const CoreIcon = coreConfig.icon;

  // Calculate setup progress
  const completedSteps = Object.values(setupProgress).filter(Boolean).length;
  const totalSteps = checklistItems.length;
  const progressPercent = Math.round((completedSteps / totalSteps) * 100);

  return (
    <div className="min-h-screen bg-black p-4 md:p-6">
      {/* Loading State */}
      {isLoading && (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-6 h-6 text-cyan-400 animate-spin" />
        </div>
      )}

      {!isLoading && (
        <>
          {/* Header */}
          <div className="mb-6 md:mb-8">
            <div className="flex items-center gap-2 mb-1">
              <FolderKanban className="w-3.5 h-3.5 md:w-4 md:h-4 text-white/60" />
              <span className="text-[10px] md:text-xs font-mono text-white/40 uppercase tracking-wider">Project Overview</span>
            </div>
            <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4">
              <h1 className="text-lg md:text-xl font-mono font-bold text-white">{projectName}</h1>
              <span className={cn(
                'inline-flex items-center gap-1.5 px-2 py-1 text-[10px] md:text-xs font-mono border self-start',
                coreConfig.color
              )}>
                <CoreIcon className="w-3 h-3" />
                {coreConfig.label}
              </span>
            </div>
            <p className="text-xs md:text-sm font-mono text-white/50 mt-2 max-w-2xl">
              {projectGoal}
            </p>
          </div>

          {/* Real Stats Dashboard */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 md:gap-4 mb-6 md:mb-8 max-w-4xl">
            <StatCard
              icon={GitBranch}
              label="Nodes"
              value={stats.nodeCount + 1} // +1 for baseline
              subValue={`${stats.forkCount} forks`}
              color="bg-purple-500/10 border-purple-500/30 text-purple-400"
              href="universe-map"
              projectId={projectId}
            />
            <StatCard
              icon={Activity}
              label="Total Runs"
              value={stats.totalRuns}
              subValue={stats.runningRuns > 0 ? `${stats.runningRuns} running` : undefined}
              color="bg-cyan-500/10 border-cyan-500/30 text-cyan-400"
              href="run-center"
              projectId={projectId}
            />
            <StatCard
              icon={CheckCircle}
              label="Succeeded"
              value={stats.succeededRuns}
              subValue={stats.failedRuns > 0 ? `${stats.failedRuns} failed` : undefined}
              color="bg-green-500/10 border-green-500/30 text-green-400"
              href="results"
              projectId={projectId}
            />
            <StatCard
              icon={TrendingUp}
              label="Success Rate"
              value={`${stats.successRate}%`}
              subValue={stats.totalRuns > 0 ? `of ${stats.totalRuns} runs` : 'No runs yet'}
              color={stats.successRate >= 70
                ? "bg-green-500/10 border-green-500/30 text-green-400"
                : stats.successRate >= 40
                  ? "bg-yellow-500/10 border-yellow-500/30 text-yellow-400"
                  : "bg-white/5 border-white/10 text-white/60"
              }
            />
          </div>

          {/* Active Runs Banner */}
          {stats.runningRuns > 0 && (
            <div className="max-w-4xl mb-6">
              <Link href={`/p/${projectId}/run-center`}>
                <div className="p-3 bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-between group cursor-pointer hover:bg-cyan-500/20 transition-colors">
                  <div className="flex items-center gap-2">
                    <Activity className="w-4 h-4 text-cyan-400 animate-pulse" />
                    <span className="font-mono text-sm text-cyan-400">
                      {stats.runningRuns} simulation{stats.runningRuns > 1 ? 's' : ''} running
                    </span>
                  </div>
                  <ArrowRight className="w-4 h-4 text-cyan-400 group-hover:translate-x-1 transition-transform" />
                </div>
              </Link>
            </div>
          )}

          {/* Clarify Panel - shows when blueprint is draft and needs clarification (blueprint.md §4) */}
          {blueprint && blueprint.is_draft && (
            <div className="max-w-2xl mb-6">
              <ClarifyPanel projectId={projectId} />
            </div>
          )}

          {/* Quick Actions */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 md:gap-4 mb-6 md:mb-8 max-w-2xl">
            <Link href={`/p/${projectId}/data-personas`}>
              <Button
                variant="outline"
                size="lg"
                className="w-full h-auto py-4 px-4 flex flex-col items-start gap-2 bg-white/5 border-white/10 hover:bg-cyan-500/10 hover:border-cyan-500/30 transition-all group"
              >
                <div className="flex items-center gap-2">
                  <Users className="w-4 h-4 text-cyan-400" />
                  <span className="text-sm font-mono text-white group-hover:text-cyan-400">
                    Go to Data & Personas
                  </span>
                  <ArrowRight className="w-3 h-3 text-white/40 group-hover:text-cyan-400 group-hover:translate-x-1 transition-transform" />
                </div>
                <span className="text-[10px] font-mono text-white/40">
                  Configure your simulation population
                </span>
              </Button>
            </Link>

            <Link href={`/p/${projectId}/run-center`}>
              <Button
                variant="outline"
                size="lg"
                className="w-full h-auto py-4 px-4 flex flex-col items-start gap-2 bg-white/5 border-white/10 hover:bg-green-500/10 hover:border-green-500/30 transition-all group"
              >
                <div className="flex items-center gap-2">
                  <Play className="w-4 h-4 text-green-400" />
                  <span className="text-sm font-mono text-white group-hover:text-green-400">
                    Run Baseline
                  </span>
                  <ArrowRight className="w-3 h-3 text-white/40 group-hover:text-green-400 group-hover:translate-x-1 transition-transform" />
                </div>
                <span className="text-[10px] font-mono text-white/40">
                  Start your first simulation run
                </span>
              </Button>
            </Link>
          </div>

          {/* Setup Progress */}
          <div className="max-w-2xl mb-6 md:mb-8">
            <div className="bg-white/5 border border-white/10 p-4 md:p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-cyan-400" />
                  <h2 className="text-sm md:text-base font-mono font-bold text-white">Setup Checklist</h2>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-20 h-1.5 bg-white/10">
                    <div
                      className="h-full bg-cyan-500 transition-all"
                      style={{ width: `${progressPercent}%` }}
                    />
                  </div>
                  <span className="text-[10px] font-mono text-white/40">{completedSteps}/{totalSteps}</span>
                </div>
              </div>

              <p className="text-xs font-mono text-white/50 mb-4">
                Complete these steps to configure your project before running simulations.
              </p>

              <div className="space-y-2">
                {checklistItems.map((item, index) => {
                  // Map checklist item id to setupProgress key
                  const progressKey = item.id === 'data-personas' ? 'dataPersonas'
                    : item.id === 'run-center' ? 'runCenter'
                    : item.id === 'universe-map' ? 'universeMap'
                    : item.id as keyof typeof setupProgress;
                  const isCompleted = setupProgress[progressKey] ?? false;
                  const Icon = item.icon;

                  return (
                    <Link
                      key={item.id}
                      href={`/p/${projectId}/${item.href}`}
                      className={cn(
                        'flex items-start gap-3 p-3 border transition-all group',
                        isCompleted
                          ? 'bg-green-500/5 border-green-500/20'
                          : 'bg-black border-white/10 hover:border-white/20'
                      )}
                    >
                      <div className={cn(
                        'w-6 h-6 flex items-center justify-center flex-shrink-0 mt-0.5',
                        isCompleted ? 'bg-green-500/20' : 'bg-white/5'
                      )}>
                        {isCompleted ? (
                          <CheckCircle className="w-4 h-4 text-green-400" />
                        ) : (
                          <span className="text-[10px] font-mono text-white/40">{index + 1}</span>
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <Icon className={cn(
                            'w-3.5 h-3.5',
                            isCompleted ? 'text-green-400' : 'text-white/40 group-hover:text-white/60'
                          )} />
                          <h3 className={cn(
                            'text-xs md:text-sm font-mono font-bold',
                            isCompleted ? 'text-green-400' : 'text-white group-hover:text-white'
                          )}>
                            {item.name}
                          </h3>
                        </div>
                        <p className="text-[10px] md:text-xs font-mono text-white/40 mt-1">
                          {item.description}
                        </p>
                      </div>
                      <ArrowRight className={cn(
                        'w-4 h-4 flex-shrink-0 mt-1 transition-transform',
                        isCompleted ? 'text-green-400' : 'text-white/20 group-hover:text-white/40 group-hover:translate-x-1'
                      )} />
                    </Link>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Project Info */}
          <div className="max-w-2xl">
            <div className="bg-white/5 border border-white/10 p-4 md:p-6">
              <h2 className="text-xs font-mono text-white/40 uppercase tracking-wider mb-4">Project Details</h2>
              <div className="grid grid-cols-2 gap-4 text-sm font-mono">
                <div>
                  <span className="text-white/40 text-xs">Project ID</span>
                  <p className="text-white/60 mt-1 text-xs truncate">{projectId}</p>
                </div>
                <div>
                  <span className="text-white/40 text-xs">Created</span>
                  <p className="text-white/60 mt-1 text-xs flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {new Date(projectCreatedAt).toLocaleDateString()}
                  </p>
                </div>
                <div>
                  <span className="text-white/40 text-xs">Core Type</span>
                  <p className={cn('mt-1 text-xs', coreConfig.color.split(' ')[1])}>
                    {coreConfig.label}
                  </p>
                </div>
                <div>
                  <span className="text-white/40 text-xs">Status</span>
                  <p className={cn(
                    'mt-1 text-xs flex items-center gap-1',
                    completedSteps === totalSteps ? 'text-green-400' : 'text-yellow-400'
                  )}>
                    <Circle className="w-2 h-2 fill-current" />
                    {completedSteps === totalSteps ? 'Ready' : 'Setup Required'}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="mt-8 pt-4 border-t border-white/5 max-w-2xl">
            <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
              <div className="flex items-center gap-1">
                <Terminal className="w-3 h-3" />
                <span>PROJECT OVERVIEW</span>
              </div>
              <span>AGENTVERSE v1.0</span>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
