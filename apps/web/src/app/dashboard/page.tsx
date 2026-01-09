'use client';

/**
 * Main Dashboard Page
 * Spec-compliant overview with runs, nodes, and project stats
 * Reference: project.md §6, C1-C6 constraints
 */

import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  FolderKanban,
  Play,
  BarChart3,
  ArrowRight,
  GitBranch,
  TrendingUp,
  Loader2,
  Terminal,
  Activity,
  Cpu,
  Clock,
  CheckCircle,
  XCircle,
  GitMerge,
  Target,
  Zap,
} from 'lucide-react';
import { useProjectSpecs, useRuns, useNodes } from '@/hooks/useApi';
import { cn } from '@/lib/utils';
import type { SpecRunStatus } from '@/lib/api';

const statusColors: Record<SpecRunStatus, string> = {
  queued: 'text-orange-400',
  starting: 'text-yellow-400',
  running: 'text-blue-400',
  succeeded: 'text-green-400',
  failed: 'text-red-400',
  cancelled: 'text-white/40',
};

const statusIcons: Record<SpecRunStatus, React.ReactNode> = {
  queued: <Clock className="w-3 h-3" />,
  starting: <Zap className="w-3 h-3" />,
  running: <Activity className="w-3 h-3 animate-pulse" />,
  succeeded: <CheckCircle className="w-3 h-3" />,
  failed: <XCircle className="w-3 h-3" />,
  cancelled: <XCircle className="w-3 h-3" />,
};

export default function DashboardPage() {
  const { data: projects, isLoading: projectsLoading } = useProjectSpecs();
  const { data: runs, isLoading: runsLoading } = useRuns();
  const { data: nodes, isLoading: nodesLoading } = useNodes();

  // Calculate stats
  const runningRuns = runs?.filter(r => r.status === 'running' || r.status === 'starting').length || 0;
  const succeededRuns = runs?.filter(r => r.status === 'succeeded').length || 0;
  const failedRuns = runs?.filter(r => r.status === 'failed').length || 0;
  const rootNodes = nodes?.filter(n => !n.parent_node_id).length || 0;
  const forkNodes = nodes?.filter(n => n.parent_node_id).length || 0;

  const dashboardStats = [
    {
      name: 'PROJECTS',
      value: projectsLoading ? '...' : String(projects?.length || 0),
      icon: FolderKanban,
      color: 'text-cyan-400',
    },
    {
      name: 'TOTAL RUNS',
      value: runsLoading ? '...' : String(runs?.length || 0),
      icon: Play,
      color: 'text-blue-400',
    },
    {
      name: 'SUCCEEDED',
      value: runsLoading ? '...' : String(succeededRuns),
      icon: CheckCircle,
      color: 'text-green-400',
    },
    {
      name: 'NODES',
      value: nodesLoading ? '...' : String(nodes?.length || 0),
      icon: GitMerge,
      color: 'text-purple-400',
    },
  ];

  const quickActions = [
    {
      title: 'New Project',
      description: 'Create project spec',
      href: '/dashboard/projects/new',
      icon: FolderKanban,
      key: 'P',
    },
    {
      title: 'View Runs',
      description: 'Monitor simulations',
      href: '/dashboard/runs',
      icon: Play,
      key: 'R',
    },
    {
      title: 'Universe Map',
      description: 'Browse nodes',
      href: '/dashboard/nodes',
      icon: GitMerge,
      key: 'N',
    },
  ];

  return (
    <div className="min-h-screen bg-black p-6">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-1">
          <Terminal className="w-4 h-4 text-cyan-400" />
          <span className="text-xs font-mono text-white/40 uppercase tracking-wider">System Dashboard</span>
        </div>
        <h1 className="text-xl font-mono font-bold text-white">
          Future Predictive AI Platform
        </h1>
        <p className="text-sm font-mono text-white/50 mt-1">
          Spec-Compliant Simulation Engine
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-8">
        {dashboardStats.map((stat) => (
          <div
            key={stat.name}
            className="bg-white/5 border border-white/10 p-4 hover:bg-white/[0.07] transition-colors"
          >
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[10px] font-mono text-white/40 uppercase tracking-wider">{stat.name}</p>
                <p className="text-2xl font-mono font-bold text-white mt-1">{stat.value}</p>
              </div>
              <stat.icon className={cn('w-4 h-4', stat.color)} />
            </div>
          </div>
        ))}
      </div>

      {/* Quick Actions */}
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-3">
          <Cpu className="w-3 h-3 text-white/40" />
          <h2 className="text-xs font-mono text-white/40 uppercase tracking-wider">Quick Actions</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {quickActions.map((action) => (
            <Link
              key={action.title}
              href={action.href}
              className="group bg-white/5 border border-white/10 p-4 hover:bg-white/[0.07] hover:border-white/20 transition-all"
            >
              <div className="flex items-start justify-between mb-3">
                <action.icon className="w-4 h-4 text-white/60" />
                <div className="flex items-center gap-1">
                  <span className="text-[10px] font-mono text-white/30">[{action.key}]</span>
                  <ArrowRight className="w-3 h-3 text-white/30 group-hover:text-white/60 transition-colors" />
                </div>
              </div>
              <h3 className="text-sm font-mono font-medium text-white">{action.title}</h3>
              <p className="text-xs font-mono text-white/40 mt-1">{action.description}</p>
            </Link>
          ))}
        </div>
      </div>

      {/* Active Runs */}
      {runningRuns > 0 && (
        <div className="bg-blue-500/10 border border-blue-500/30 p-4 mb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Activity className="w-5 h-5 text-blue-400 animate-pulse" />
              <div>
                <p className="text-sm font-mono font-bold text-blue-400">
                  {runningRuns} Active Run{runningRuns > 1 ? 's' : ''}
                </p>
                <p className="text-xs font-mono text-white/40">
                  Simulations currently executing
                </p>
              </div>
            </div>
            <Link href="/dashboard/runs?status=running">
              <Button variant="secondary" size="sm">
                VIEW RUNS
              </Button>
            </Link>
          </div>
        </div>
      )}

      {/* Getting Started - Only show if no projects */}
      {!projectsLoading && (!projects || projects.length === 0) && (
        <div className="bg-white/5 border border-white/10 p-6 mb-8">
          <div className="flex items-start gap-4">
            <div className="w-10 h-10 bg-cyan-500 flex items-center justify-center flex-shrink-0">
              <Terminal className="w-5 h-5 text-black" />
            </div>
            <div className="flex-1">
              <div className="text-[10px] font-mono text-white/40 uppercase tracking-wider mb-1">Getting Started</div>
              <h2 className="text-lg font-mono font-bold text-white mb-2">Initialize Your First Project</h2>
              <p className="text-sm font-mono text-white/50 mb-4 max-w-xl">
                Create a project spec to define your simulation. Configure personas, scenarios, and run parameters.
              </p>
              <Link href="/dashboard/projects/new">
                <Button size="sm">
                  CREATE PROJECT
                </Button>
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Runs */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Play className="w-3 h-3 text-blue-400" />
              <h2 className="text-xs font-mono text-white/40 uppercase tracking-wider">Recent Runs</h2>
            </div>
            <Link href="/dashboard/runs" className="text-xs font-mono text-white/40 hover:text-white/60 transition-colors">
              View All &rarr;
            </Link>
          </div>
          <div className="bg-white/5 border border-white/10">
            {runsLoading ? (
              <div className="p-8 flex items-center justify-center">
                <Loader2 className="w-4 h-4 animate-spin text-white/40" />
              </div>
            ) : runs && runs.length > 0 ? (
              <div className="divide-y divide-white/5">
                {runs.slice(0, 5).map((run) => (
                  <Link
                    key={run.run_id}
                    href={`/dashboard/runs/${run.run_id}`}
                    className="flex items-center justify-between p-4 hover:bg-white/5 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <div className={cn('w-6 h-6 flex items-center justify-center', statusColors[run.status])}>
                        {statusIcons[run.status]}
                      </div>
                      <div>
                        <p className="text-sm font-mono text-white">
                          {run.run_id.slice(0, 12)}...
                        </p>
                        <p className="text-xs font-mono text-white/40">
                          {run.timing?.current_tick || 0}/{run.timing?.total_ticks || 0} ticks
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className={cn('text-xs font-mono uppercase', statusColors[run.status])}>
                        {run.status}
                      </p>
                      <p className="text-[10px] font-mono text-white/30">
                        {new Date(run.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <div className="p-8 text-center">
                <div className="w-12 h-12 bg-white/5 flex items-center justify-center mx-auto mb-4">
                  <Play className="w-5 h-5 text-white/30" />
                </div>
                <p className="text-sm font-mono text-white/60 mb-1">No runs yet</p>
                <p className="text-xs font-mono text-white/30 mb-4">
                  Create a project to start running simulations
                </p>
                <Link href="/dashboard/projects">
                  <Button variant="secondary" size="sm">
                    VIEW PROJECTS
                  </Button>
                </Link>
              </div>
            )}
          </div>
        </div>

        {/* Universe Map Summary */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <GitMerge className="w-3 h-3 text-purple-400" />
              <h2 className="text-xs font-mono text-white/40 uppercase tracking-wider">Universe Map</h2>
            </div>
            <Link href="/dashboard/nodes" className="text-xs font-mono text-white/40 hover:text-white/60 transition-colors">
              View All &rarr;
            </Link>
          </div>
          <div className="bg-white/5 border border-white/10">
            {nodesLoading ? (
              <div className="p-8 flex items-center justify-center">
                <Loader2 className="w-4 h-4 animate-spin text-white/40" />
              </div>
            ) : nodes && nodes.length > 0 ? (
              <div>
                {/* Node Stats */}
                <div className="grid grid-cols-2 gap-3 p-4 border-b border-white/5">
                  <div className="bg-cyan-500/10 border border-cyan-500/30 p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <Target className="w-3 h-3 text-cyan-400" />
                      <span className="text-[10px] font-mono text-white/40 uppercase">Root Nodes</span>
                    </div>
                    <span className="text-xl font-mono font-bold text-white">{rootNodes}</span>
                  </div>
                  <div className="bg-purple-500/10 border border-purple-500/30 p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <GitBranch className="w-3 h-3 text-purple-400" />
                      <span className="text-[10px] font-mono text-white/40 uppercase">Fork Nodes</span>
                    </div>
                    <span className="text-xl font-mono font-bold text-white">{forkNodes}</span>
                  </div>
                </div>
                {/* Recent Nodes */}
                <div className="divide-y divide-white/5">
                  {nodes.slice(0, 4).map((node) => (
                    <Link
                      key={node.node_id}
                      href={`/dashboard/nodes/${node.node_id}`}
                      className="flex items-center justify-between p-4 hover:bg-white/5 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        {node.parent_node_id ? (
                          <GitBranch className="w-4 h-4 text-purple-400" />
                        ) : (
                          <Target className="w-4 h-4 text-cyan-400" />
                        )}
                        <div>
                          <p className="text-sm font-mono text-white">
                            {node.node_id.slice(0, 12)}...
                          </p>
                          {node.label && (
                            <p className="text-xs font-mono text-white/40 truncate max-w-[150px]">
                              {node.label}
                            </p>
                          )}
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-xs font-mono text-white">
                          {(node.probability * 100).toFixed(0)}%
                        </p>
                        <p className="text-[10px] font-mono text-white/30 capitalize">
                          {node.confidence_level}
                        </p>
                      </div>
                    </Link>
                  ))}
                </div>
              </div>
            ) : (
              <div className="p-8 text-center">
                <div className="w-12 h-12 bg-white/5 flex items-center justify-center mx-auto mb-4">
                  <GitMerge className="w-5 h-5 text-white/30" />
                </div>
                <p className="text-sm font-mono text-white/60 mb-1">No nodes yet</p>
                <p className="text-xs font-mono text-white/30 mb-4">
                  Run a simulation to generate universe map nodes
                </p>
                <Link href="/dashboard/runs">
                  <Button variant="secondary" size="sm">
                    VIEW RUNS
                  </Button>
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Constraint Compliance Footer */}
      <div className="mt-8 pt-4 border-t border-white/5">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1">
              <div className="w-1.5 h-1.5 bg-green-500 rounded-full" />
              <span>SYSTEM ONLINE</span>
            </div>
            <span>|</span>
            <span>C1: FORK-NOT-MUTATE</span>
            <span>|</span>
            <span>C3: REPLAY READ-ONLY</span>
          </div>
          <span>project.md compliant</span>
        </div>
      </div>
    </div>
  );
}
