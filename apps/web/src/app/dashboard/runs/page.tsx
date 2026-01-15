'use client';

/**
 * Job Center Page
 * Unified view for simulation runs and PIL background jobs.
 *
 * Reference: blueprint_v2.md Phase C - Job Center
 * Spec-compliant run management: project.md §6.5-6.6
 */

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  Plus,
  Play,
  MoreVertical,
  Loader2,
  Search,
  XCircle,
  CheckCircle,
  Clock,
  Activity,
  Eye,
  Terminal,
  GitBranch,
  RefreshCw,
  Pause,
  BarChart3,
  Zap,
  Shield,
  ShieldCheck,
  ShieldX,
  Brain,
  Target,
  FileText,
  Sparkles,
  FolderOpen,
  Filter,
  ChevronDown,
} from 'lucide-react';
import {
  useRuns,
  useCancelRun,
  useStartRun,
  usePILJobs,
  useProjects,
  useCancelPILJob,
  useRetryPILJob,
} from '@/hooks/useApi';
import { useToast } from '@/hooks/use-toast';
import type { RunSummary, SpecRunStatus, PILJob, PILJobStatus, PILJobType } from '@/lib/api';
import { cn } from '@/lib/utils';

// Tab types
type TabType = 'runs' | 'jobs';

// Status colors for runs
const runStatusColors: Record<string, { className: string; icon: React.ReactNode; label: string }> = {
  queued: {
    className: 'bg-orange-500/20 text-orange-400',
    icon: <Clock className="w-2.5 h-2.5" />,
    label: 'QUEUED',
  },
  starting: {
    className: 'bg-yellow-500/20 text-yellow-400',
    icon: <Zap className="w-2.5 h-2.5" />,
    label: 'STARTING',
  },
  running: {
    className: 'bg-blue-500/20 text-blue-400 animate-pulse',
    icon: <Activity className="w-2.5 h-2.5" />,
    label: 'RUNNING',
  },
  succeeded: {
    className: 'bg-green-500/20 text-green-400',
    icon: <CheckCircle className="w-2.5 h-2.5" />,
    label: 'SUCCEEDED',
  },
  failed: {
    className: 'bg-red-500/20 text-red-400',
    icon: <XCircle className="w-2.5 h-2.5" />,
    label: 'FAILED',
  },
  cancelled: {
    className: 'bg-white/10 text-white/50',
    icon: <Pause className="w-2.5 h-2.5" />,
    label: 'CANCELLED',
  },
};

// Status colors for PIL jobs
const pilJobStatusColors: Record<PILJobStatus, { className: string; icon: React.ReactNode; label: string }> = {
  queued: {
    className: 'bg-yellow-500/20 text-yellow-400',
    icon: <Clock className="w-2.5 h-2.5" />,
    label: 'QUEUED',
  },
  running: {
    className: 'bg-cyan-500/20 text-cyan-400 animate-pulse',
    icon: <Loader2 className="w-2.5 h-2.5 animate-spin" />,
    label: 'RUNNING',
  },
  succeeded: {
    className: 'bg-green-500/20 text-green-400',
    icon: <CheckCircle className="w-2.5 h-2.5" />,
    label: 'SUCCEEDED',
  },
  failed: {
    className: 'bg-red-500/20 text-red-400',
    icon: <XCircle className="w-2.5 h-2.5" />,
    label: 'FAILED',
  },
  cancelled: {
    className: 'bg-white/10 text-white/50',
    icon: <Pause className="w-2.5 h-2.5" />,
    label: 'CANCELLED',
  },
};

// Job type icons
const jobTypeIcons: Record<PILJobType, { icon: typeof Target; label: string }> = {
  goal_analysis: { icon: Target, label: 'Goal Analysis' },
  blueprint_build: { icon: FileText, label: 'Blueprint Build' },
  slot_validation: { icon: CheckCircle, label: 'Slot Validation' },
  summarization: { icon: Sparkles, label: 'Summarization' },
  alignment_scoring: { icon: Zap, label: 'Alignment Scoring' },
};

export default function JobCenterPage() {
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState<TabType>('runs');
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [projectFilter, setProjectFilter] = useState<string>('');
  const [showProjectDropdown, setShowProjectDropdown] = useState(false);

  // Fetch data
  const { data: projects } = useProjects({ limit: 100 });
  const { data: runs, isLoading: runsLoading, refetch: refetchRuns } = useRuns(
    statusFilter && activeTab === 'runs' ? { status: statusFilter as SpecRunStatus } : undefined
  );
  const { data: pilJobs, isLoading: jobsLoading, refetch: refetchJobs } = usePILJobs({
    project_id: projectFilter || undefined,
    status: (statusFilter && activeTab === 'jobs') ? statusFilter as PILJobStatus : undefined,
    limit: 100,
  });

  // Track previous job statuses for notifications
  const [previousJobStatuses, setPreviousJobStatuses] = useState<Record<string, PILJobStatus>>({});

  // Notify on job completion
  useEffect(() => {
    if (!pilJobs) return;

    pilJobs.forEach((job) => {
      const prevStatus = previousJobStatuses[job.id];
      if (prevStatus && prevStatus !== job.status) {
        if (job.status === 'succeeded') {
          toast({
            title: 'Job Completed',
            description: `${job.job_name} completed successfully`,
          });
        } else if (job.status === 'failed') {
          toast({
            title: 'Job Failed',
            description: `${job.job_name} failed: ${job.error_message || 'Unknown error'}`,
          });
        }
      }
    });

    // Update tracking
    const newStatuses: Record<string, PILJobStatus> = {};
    pilJobs.forEach((job) => {
      newStatuses[job.id] = job.status;
    });
    setPreviousJobStatuses(newStatuses);
  }, [pilJobs, previousJobStatuses, toast]);

  // Filter runs (note: RunSummary doesn't include project_id, so project filter only applies to jobs)
  const filteredRuns = runs?.filter(run => {
    const matchesSearch = !searchQuery ||
      run.run_id.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesSearch;
  });

  // Filter PIL jobs
  const filteredJobs = pilJobs?.filter(job => {
    const matchesSearch = !searchQuery ||
      job.job_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      job.id.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesSearch;
  });

  // Calculate stats
  const runStats = {
    running: runs?.filter(r => r.status === 'running' || r.status === 'starting').length || 0,
    queued: runs?.filter(r => r.status === 'queued').length || 0,
    succeeded: runs?.filter(r => r.status === 'succeeded').length || 0,
    total: runs?.length || 0,
  };

  const jobStats = {
    running: pilJobs?.filter(j => j.status === 'running').length || 0,
    queued: pilJobs?.filter(j => j.status === 'queued').length || 0,
    succeeded: pilJobs?.filter(j => j.status === 'succeeded').length || 0,
    total: pilJobs?.length || 0,
  };

  const isLoading = activeTab === 'runs' ? runsLoading : jobsLoading;
  const refetch = activeTab === 'runs' ? refetchRuns : refetchJobs;
  const stats = activeTab === 'runs' ? runStats : jobStats;

  return (
    <div className="min-h-screen bg-black p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Brain className="w-4 h-4 text-cyan-400" />
            <span className="text-xs font-mono text-white/40 uppercase tracking-wider">Process Control</span>
          </div>
          <h1 className="text-xl font-mono font-bold text-white">Job Center</h1>
          <p className="text-sm font-mono text-white/50 mt-1">
            Monitor simulations and background jobs
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" size="sm" onClick={() => refetch()}>
            <RefreshCw className="w-3 h-3 mr-2" />
            REFRESH
          </Button>
          <Link href="/dashboard/projects">
            <Button size="sm">
              <Plus className="w-3 h-3 mr-2" />
              NEW PROJECT
            </Button>
          </Link>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 p-1 bg-white/5 w-fit">
        <button
          onClick={() => setActiveTab('runs')}
          className={cn(
            'px-4 py-2 text-xs font-mono transition-all flex items-center gap-2',
            activeTab === 'runs'
              ? 'bg-cyan-500 text-black'
              : 'text-white/60 hover:text-white hover:bg-white/10'
          )}
        >
          <Play className="w-3 h-3" />
          Simulation Runs
          {runStats.running > 0 && (
            <span className={cn(
              'px-1.5 py-0.5 text-[10px]',
              activeTab === 'runs' ? 'bg-black/20' : 'bg-cyan-500/20 text-cyan-400'
            )}>
              {runStats.running}
            </span>
          )}
        </button>
        <button
          onClick={() => setActiveTab('jobs')}
          className={cn(
            'px-4 py-2 text-xs font-mono transition-all flex items-center gap-2',
            activeTab === 'jobs'
              ? 'bg-cyan-500 text-black'
              : 'text-white/60 hover:text-white hover:bg-white/10'
          )}
        >
          <Sparkles className="w-3 h-3" />
          Background Jobs
          {jobStats.running > 0 && (
            <span className={cn(
              'px-1.5 py-0.5 text-[10px]',
              activeTab === 'jobs' ? 'bg-black/20' : 'bg-purple-500/20 text-purple-400'
            )}>
              {jobStats.running}
            </span>
          )}
        </button>
      </div>

      {/* Stats Bar */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex items-center gap-2 mb-2">
            <Activity className="w-4 h-4 text-blue-400" />
            <span className="text-xs font-mono text-white/40">RUNNING</span>
          </div>
          <span className="text-2xl font-mono font-bold text-white">{stats.running}</span>
        </div>
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex items-center gap-2 mb-2">
            <Clock className="w-4 h-4 text-yellow-400" />
            <span className="text-xs font-mono text-white/40">QUEUED</span>
          </div>
          <span className="text-2xl font-mono font-bold text-white">{stats.queued}</span>
        </div>
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle className="w-4 h-4 text-green-400" />
            <span className="text-xs font-mono text-white/40">SUCCEEDED</span>
          </div>
          <span className="text-2xl font-mono font-bold text-white">{stats.succeeded}</span>
        </div>
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex items-center gap-2 mb-2">
            <BarChart3 className="w-4 h-4 text-purple-400" />
            <span className="text-xs font-mono text-white/40">TOTAL</span>
          </div>
          <span className="text-2xl font-mono font-bold text-white">{stats.total}</span>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-6">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-white/30" />
          <input
            type="text"
            placeholder={`Search ${activeTab === 'runs' ? 'runs' : 'jobs'}...`}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-7 pr-3 py-1.5 bg-white/5 border border-white/10 text-xs font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-cyan-500/50"
          />
        </div>

        {/* Project Filter */}
        <div className="relative">
          <button
            onClick={() => setShowProjectDropdown(!showProjectDropdown)}
            className="flex items-center gap-2 px-3 py-1.5 bg-white/5 border border-white/10 text-xs font-mono text-white hover:bg-white/10"
          >
            <FolderOpen className="w-3 h-3 text-white/40" />
            {projectFilter ? (
              projects?.find(p => p.id === projectFilter)?.name?.slice(0, 15) || 'Project'
            ) : (
              'All Projects'
            )}
            <ChevronDown className="w-3 h-3 text-white/40" />
          </button>
          {showProjectDropdown && (
            <>
              <div
                className="fixed inset-0 z-10"
                onClick={() => setShowProjectDropdown(false)}
              />
              <div className="absolute left-0 top-full mt-1 w-48 bg-black border border-white/20 py-1 z-20 max-h-60 overflow-auto">
                <button
                  onClick={() => {
                    setProjectFilter('');
                    setShowProjectDropdown(false);
                  }}
                  className={cn(
                    'w-full px-3 py-1.5 text-left text-xs font-mono hover:bg-white/10',
                    !projectFilter ? 'text-cyan-400' : 'text-white/60'
                  )}
                >
                  All Projects
                </button>
                {projects?.map((project) => (
                  <button
                    key={project.id}
                    onClick={() => {
                      setProjectFilter(project.id);
                      setShowProjectDropdown(false);
                    }}
                    className={cn(
                      'w-full px-3 py-1.5 text-left text-xs font-mono hover:bg-white/10 truncate',
                      projectFilter === project.id ? 'text-cyan-400' : 'text-white/60'
                    )}
                  >
                    {project.name}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>

        {/* Status Filter */}
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-1.5 bg-white/5 border border-white/10 text-xs font-mono text-white appearance-none focus:outline-none focus:border-cyan-500/50"
        >
          <option value="">All Status</option>
          <option value="queued">Queued</option>
          {activeTab === 'runs' && <option value="starting">Starting</option>}
          <option value="running">Running</option>
          <option value="succeeded">Succeeded</option>
          <option value="failed">Failed</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-4 h-4 animate-spin text-cyan-400" />
          <span className="ml-2 text-sm font-mono text-white/40">
            Loading {activeTab === 'runs' ? 'runs' : 'jobs'}...
          </span>
        </div>
      )}

      {/* Runs Tab Content */}
      {!isLoading && activeTab === 'runs' && (
        <RunsTable runs={filteredRuns || []} onUpdate={refetchRuns} />
      )}

      {/* Jobs Tab Content */}
      {!isLoading && activeTab === 'jobs' && (
        <PILJobsTable jobs={filteredJobs || []} onUpdate={refetchJobs} projects={projects || []} />
      )}

      {/* Footer Status */}
      <div className="mt-8 pt-4 border-t border-white/5">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1">
              <Terminal className="w-3 h-3" />
              <span>JOB CENTER v2</span>
            </div>
            <div className="flex items-center gap-1">
              <GitBranch className="w-3 h-3" />
              <span>C1: FORK-NOT-MUTATE</span>
            </div>
          </div>
          <span>blueprint_v2.md Phase C</span>
        </div>
      </div>
    </div>
  );
}

// Runs Table Component
function RunsTable({ runs, onUpdate }: { runs: RunSummary[]; onUpdate: () => void }) {
  if (runs.length === 0) {
    return (
      <div className="bg-white/5 border border-white/10">
        <div className="p-12 text-center">
          <div className="w-12 h-12 bg-cyan-500/10 flex items-center justify-center mx-auto mb-4">
            <Play className="w-5 h-5 text-cyan-400" />
          </div>
          <p className="text-sm font-mono text-white/60 mb-1">No simulation runs</p>
          <p className="text-xs font-mono text-white/30 mb-4">
            Create a project and start your first simulation run
          </p>
          <Link href="/dashboard/projects">
            <Button size="sm">
              <Plus className="w-3 h-3 mr-2" />
              CREATE PROJECT
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white/5 border border-white/10">
      <table className="w-full">
        <thead className="border-b border-white/10">
          <tr>
            <th className="text-left px-4 py-3 text-[10px] font-mono text-white/40 uppercase tracking-wider">Status</th>
            <th className="text-left px-4 py-3 text-[10px] font-mono text-white/40 uppercase tracking-wider">Isolation</th>
            <th className="text-left px-4 py-3 text-[10px] font-mono text-white/40 uppercase tracking-wider">Run ID</th>
            <th className="text-left px-4 py-3 text-[10px] font-mono text-white/40 uppercase tracking-wider">Node</th>
            <th className="text-left px-4 py-3 text-[10px] font-mono text-white/40 uppercase tracking-wider">Progress</th>
            <th className="text-left px-4 py-3 text-[10px] font-mono text-white/40 uppercase tracking-wider">Ticks</th>
            <th className="text-left px-4 py-3 text-[10px] font-mono text-white/40 uppercase tracking-wider">Created</th>
            <th className="text-right px-4 py-3 text-[10px] font-mono text-white/40 uppercase tracking-wider">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-white/5">
          {runs.map((run) => (
            <RunRow key={run.run_id} run={run} onUpdate={onUpdate} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Run Row Component
function RunRow({ run, onUpdate }: { run: RunSummary; onUpdate: () => void }) {
  const [showMenu, setShowMenu] = useState(false);
  const cancelRun = useCancelRun();
  const startRun = useStartRun();

  const status = runStatusColors[run.status] || runStatusColors.queued;
  const currentTick = run.timing?.current_tick || 0;
  const totalTicks = run.timing?.total_ticks || 0;
  const progress = totalTicks > 0 ? (currentTick / totalTicks) * 100 : 0;

  const handleCancel = async () => {
    if (confirm('Cancel this run?')) {
      try {
        await cancelRun.mutateAsync(run.run_id);
        onUpdate();
      } catch {
        // Error handled by mutation
      }
    }
    setShowMenu(false);
  };

  const handleStart = async () => {
    try {
      await startRun.mutateAsync(run.run_id);
      onUpdate();
    } catch {
      // Error handled by mutation
    }
    setShowMenu(false);
  };

  const renderIsolationBadge = () => {
    if (!run.isolation_status) {
      return (
        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-white/5 text-white/30 text-[10px] font-mono">
          <Shield className="w-2.5 h-2.5" />
          N/A
        </span>
      );
    }
    if (run.isolation_status === 'PASS') {
      return (
        <Link
          href={`/dashboard/runs/${run.run_id}/audit`}
          className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-green-500/20 text-green-400 text-[10px] font-mono hover:bg-green-500/30 transition-colors"
        >
          <ShieldCheck className="w-2.5 h-2.5" />
          PASS
        </Link>
      );
    }
    return (
      <Link
        href={`/dashboard/runs/${run.run_id}/audit`}
        className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-red-500/20 text-red-400 text-[10px] font-mono hover:bg-red-500/30 transition-colors"
      >
        <ShieldX className="w-2.5 h-2.5" />
        FAIL
      </Link>
    );
  };

  return (
    <tr className="hover:bg-white/5 transition-colors">
      <td className="px-4 py-3">
        <span className={cn('inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-mono uppercase', status.className)}>
          {status.icon}
          {status.label}
        </span>
      </td>
      <td className="px-4 py-3">{renderIsolationBadge()}</td>
      <td className="px-4 py-3">
        <Link
          href={`/dashboard/runs/${run.run_id}`}
          className="text-xs font-mono text-cyan-400 hover:text-cyan-300 hover:underline"
        >
          {run.run_id.slice(0, 12)}...
        </Link>
      </td>
      <td className="px-4 py-3">
        {run.node_id ? (
          <Link
            href={`/dashboard/nodes/${run.node_id}`}
            className="flex items-center gap-1 text-xs font-mono text-white/60 hover:text-white"
          >
            <GitBranch className="w-3 h-3" />
            {run.node_id.slice(0, 8)}
          </Link>
        ) : (
          <span className="text-xs font-mono text-white/30">-</span>
        )}
      </td>
      <td className="px-4 py-3">
        <div className="w-full max-w-[100px]">
          <div className="flex items-center gap-2">
            <div className="flex-1 bg-white/10 h-1">
              <div
                className={cn('h-1 transition-all', progress >= 100 ? 'bg-green-500' : 'bg-cyan-500')}
                style={{ width: `${Math.min(progress, 100)}%` }}
              />
            </div>
            <span className="text-[10px] font-mono text-white/40 w-8">{progress.toFixed(0)}%</span>
          </div>
        </div>
      </td>
      <td className="px-4 py-3 text-xs font-mono text-white/60">{currentTick}/{totalTicks}</td>
      <td className="px-4 py-3 text-[10px] font-mono text-white/30">
        {new Date(run.created_at).toLocaleDateString()}
      </td>
      <td className="px-4 py-3 text-right">
        <div className="relative inline-block">
          <button
            onClick={() => setShowMenu(!showMenu)}
            className="p-1.5 hover:bg-white/10 transition-colors"
          >
            <MoreVertical className="w-3 h-3 text-white/40" />
          </button>
          {showMenu && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setShowMenu(false)} />
              <div className="absolute right-0 mt-1 w-36 bg-black border border-white/20 py-1 z-20">
                <Link
                  href={`/dashboard/runs/${run.run_id}`}
                  className="flex items-center gap-2 px-3 py-1.5 text-xs font-mono text-white/60 hover:bg-white/10"
                  onClick={() => setShowMenu(false)}
                >
                  <Eye className="w-3 h-3" />
                  View Details
                </Link>
                {run.status === 'succeeded' && (
                  <>
                    <Link
                      href={`/dashboard/runs/${run.run_id}/telemetry`}
                      className="flex items-center gap-2 px-3 py-1.5 text-xs font-mono text-white/60 hover:bg-white/10"
                      onClick={() => setShowMenu(false)}
                    >
                      <BarChart3 className="w-3 h-3" />
                      Telemetry
                    </Link>
                    <Link
                      href={`/dashboard/runs/${run.run_id}/audit`}
                      className="flex items-center gap-2 px-3 py-1.5 text-xs font-mono text-white/60 hover:bg-white/10"
                      onClick={() => setShowMenu(false)}
                    >
                      <Shield className="w-3 h-3" />
                      Audit Report
                    </Link>
                  </>
                )}
                {run.status === 'queued' && (
                  <button
                    onClick={handleStart}
                    disabled={startRun.isPending}
                    className="flex items-center gap-2 w-full px-3 py-1.5 text-xs font-mono text-green-400 hover:bg-white/10 disabled:opacity-50"
                  >
                    <Play className="w-3 h-3" />
                    Start
                  </button>
                )}
                {run.status === 'running' && (
                  <button
                    onClick={handleCancel}
                    disabled={cancelRun.isPending}
                    className="flex items-center gap-2 w-full px-3 py-1.5 text-xs font-mono text-red-400 hover:bg-white/10 disabled:opacity-50"
                  >
                    <XCircle className="w-3 h-3" />
                    Cancel
                  </button>
                )}
              </div>
            </>
          )}
        </div>
      </td>
    </tr>
  );
}

// PIL Jobs Table Component
function PILJobsTable({
  jobs,
  onUpdate,
  projects,
}: {
  jobs: PILJob[];
  onUpdate: () => void;
  projects: { id: string; name: string }[];
}) {
  if (jobs.length === 0) {
    return (
      <div className="bg-white/5 border border-white/10">
        <div className="p-12 text-center">
          <div className="w-12 h-12 bg-purple-500/10 flex items-center justify-center mx-auto mb-4">
            <Sparkles className="w-5 h-5 text-purple-400" />
          </div>
          <p className="text-sm font-mono text-white/60 mb-1">No background jobs</p>
          <p className="text-xs font-mono text-white/30 mb-4">
            Background jobs are created during project setup and blueprint generation
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white/5 border border-white/10">
      <table className="w-full">
        <thead className="border-b border-white/10">
          <tr>
            <th className="text-left px-4 py-3 text-[10px] font-mono text-white/40 uppercase tracking-wider">Status</th>
            <th className="text-left px-4 py-3 text-[10px] font-mono text-white/40 uppercase tracking-wider">Type</th>
            <th className="text-left px-4 py-3 text-[10px] font-mono text-white/40 uppercase tracking-wider">Job Name</th>
            <th className="text-left px-4 py-3 text-[10px] font-mono text-white/40 uppercase tracking-wider">Project</th>
            <th className="text-left px-4 py-3 text-[10px] font-mono text-white/40 uppercase tracking-wider">Progress</th>
            <th className="text-left px-4 py-3 text-[10px] font-mono text-white/40 uppercase tracking-wider">Created</th>
            <th className="text-right px-4 py-3 text-[10px] font-mono text-white/40 uppercase tracking-wider">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-white/5">
          {jobs.map((job) => (
            <PILJobRow key={job.id} job={job} onUpdate={onUpdate} projects={projects} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

// PIL Job Row Component
function PILJobRow({
  job,
  onUpdate,
  projects,
}: {
  job: PILJob;
  onUpdate: () => void;
  projects: { id: string; name: string }[];
}) {
  const [showMenu, setShowMenu] = useState(false);
  const cancelJob = useCancelPILJob();
  const retryJob = useRetryPILJob();

  const status = pilJobStatusColors[job.status];
  const typeConfig = jobTypeIcons[job.job_type];
  const TypeIcon = typeConfig.icon;
  const projectName = projects.find(p => p.id === job.project_id)?.name;

  const handleCancel = async () => {
    try {
      await cancelJob.mutateAsync(job.id);
      onUpdate();
    } catch {
      // Error handled by mutation
    }
    setShowMenu(false);
  };

  const handleRetry = async () => {
    try {
      await retryJob.mutateAsync(job.id);
      onUpdate();
    } catch {
      // Error handled by mutation
    }
    setShowMenu(false);
  };

  return (
    <tr className="hover:bg-white/5 transition-colors">
      <td className="px-4 py-3">
        <span className={cn('inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-mono uppercase', status.className)}>
          {status.icon}
          {status.label}
        </span>
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <TypeIcon className="w-3 h-3 text-purple-400" />
          <span className="text-xs font-mono text-white/60">{typeConfig.label}</span>
        </div>
      </td>
      <td className="px-4 py-3">
        <span className="text-xs font-mono text-white">{job.job_name}</span>
        {job.stage_name && (
          <p className="text-[10px] font-mono text-white/40 mt-0.5">{job.stage_name}</p>
        )}
      </td>
      <td className="px-4 py-3">
        {job.project_id && projectName ? (
          <Link
            href={`/p/${job.project_id}`}
            className="text-xs font-mono text-cyan-400 hover:text-cyan-300 hover:underline"
          >
            {projectName.slice(0, 15)}{projectName.length > 15 ? '...' : ''}
          </Link>
        ) : (
          <span className="text-xs font-mono text-white/30">-</span>
        )}
      </td>
      <td className="px-4 py-3">
        <div className="w-full max-w-[100px]">
          <div className="flex items-center gap-2">
            <div className="flex-1 bg-white/10 h-1">
              <div
                className={cn(
                  'h-1 transition-all',
                  job.status === 'succeeded' ? 'bg-green-500' : 'bg-purple-500'
                )}
                style={{ width: `${job.progress_percent}%` }}
              />
            </div>
            <span className="text-[10px] font-mono text-white/40 w-8">{job.progress_percent}%</span>
          </div>
        </div>
      </td>
      <td className="px-4 py-3 text-[10px] font-mono text-white/30">
        {new Date(job.created_at).toLocaleDateString()}
      </td>
      <td className="px-4 py-3 text-right">
        <div className="relative inline-block">
          <button
            onClick={() => setShowMenu(!showMenu)}
            className="p-1.5 hover:bg-white/10 transition-colors"
          >
            <MoreVertical className="w-3 h-3 text-white/40" />
          </button>
          {showMenu && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setShowMenu(false)} />
              <div className="absolute right-0 mt-1 w-36 bg-black border border-white/20 py-1 z-20">
                {job.project_id && (
                  <Link
                    href={`/p/${job.project_id}`}
                    className="flex items-center gap-2 px-3 py-1.5 text-xs font-mono text-white/60 hover:bg-white/10"
                    onClick={() => setShowMenu(false)}
                  >
                    <FolderOpen className="w-3 h-3" />
                    View Project
                  </Link>
                )}
                {job.status === 'succeeded' && (
                  <button
                    className="flex items-center gap-2 w-full px-3 py-1.5 text-xs font-mono text-white/60 hover:bg-white/10"
                    onClick={() => setShowMenu(false)}
                  >
                    <FileText className="w-3 h-3" />
                    View Artifacts
                  </button>
                )}
                {(job.status === 'queued' || job.status === 'running') && (
                  <button
                    onClick={handleCancel}
                    disabled={cancelJob.isPending}
                    className="flex items-center gap-2 w-full px-3 py-1.5 text-xs font-mono text-red-400 hover:bg-white/10 disabled:opacity-50"
                  >
                    <XCircle className="w-3 h-3" />
                    Cancel
                  </button>
                )}
                {job.status === 'failed' && (
                  <button
                    onClick={handleRetry}
                    disabled={retryJob.isPending}
                    className="flex items-center gap-2 w-full px-3 py-1.5 text-xs font-mono text-yellow-400 hover:bg-white/10 disabled:opacity-50"
                  >
                    <RefreshCw className="w-3 h-3" />
                    Retry
                  </button>
                )}
              </div>
            </>
          )}
        </div>
      </td>
    </tr>
  );
}
