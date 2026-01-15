'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  ArrowLeft,
  Play,
  Settings,
  Calendar,
  Users,
  Loader2,
  FolderKanban,
  Terminal,
  Map,
  MessageCircle,
  Activity,
  AlertTriangle,
  CheckCircle2,
  Target,
  TrendingUp,
  Shield,
  Zap,
  GitBranch,
  Layers,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useProjectSpec, useProjectSpecStats, useNodes, useCreateProjectSpecRun } from '@/hooks/useApi';
import type { NodeSummary } from '@/lib/api';
import { GuidancePanel } from '@/components/pil/v2/GuidancePanel';

export default function ProjectOverviewPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;
  const [isCreatingBaseline, setIsCreatingBaseline] = useState(false);

  const { data: project, isLoading: projectLoading, error: projectError } = useProjectSpec(projectId);
  const { data: stats } = useProjectSpecStats(projectId);
  const { data: nodes, isLoading: nodesLoading } = useNodes({ project_id: projectId, limit: 10 });
  const createProjectRun = useCreateProjectSpecRun();

  // Find the baseline/root node and latest node
  const rootNode = nodes?.find((n: NodeSummary) => n.is_baseline);
  const latestNode = nodes?.[0]; // Assuming sorted by created_at desc

  const handleRunBaseline = async () => {
    if (!project) return;
    setIsCreatingBaseline(true);
    try {
      // Create baseline run for this project (no node_id = creates root node)
      await createProjectRun.mutateAsync({
        projectId,
        data: {
          config_overrides: {
            horizon: project.settings?.default_horizon || 100,
          },
        },
      });
      // Redirect to runs page to see the new run
      router.push(`/dashboard/runs?project_id=${projectId}`);
    } catch {
      setIsCreatingBaseline(false);
    }
  };

  if (projectLoading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <Loader2 className="w-5 h-5 md:w-6 md:h-6 animate-spin text-white/40" />
      </div>
    );
  }

  if (projectError || !project) {
    return (
      <div className="min-h-screen bg-black p-4 md:p-6">
        <div className="bg-red-500/10 border border-red-500/30 p-4 md:p-6 text-center">
          <h2 className="text-base md:text-lg font-mono font-bold text-red-400 mb-2">PROJECT NOT FOUND</h2>
          <p className="text-xs md:text-sm font-mono text-red-400/70 mb-4">The requested project could not be loaded.</p>
          <Link href="/dashboard/projects">
            <Button variant="outline" className="font-mono text-xs border-white/20 text-white/60 hover:bg-white/5">
              BACK TO PROJECTS
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  const hasBaseline = !!rootNode;

  return (
    <div className="min-h-screen bg-black p-4 md:p-6">
      {/* Header */}
      <div className="mb-6 md:mb-8">
        <Link href="/dashboard/projects">
          <Button variant="ghost" size="sm" className="text-white/60 hover:text-white hover:bg-white/5 font-mono text-[10px] md:text-xs mb-3 md:mb-4">
            <ArrowLeft className="w-3 h-3 mr-1 md:mr-2" />
            BACK TO PROJECTS
          </Button>
        </Link>

        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 md:gap-4">
          <div className="min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <FolderKanban className="w-3.5 h-3.5 md:w-4 md:h-4 text-cyan-400" />
              <span className="text-[10px] md:text-xs font-mono text-white/40 uppercase tracking-wider">Project Overview</span>
            </div>
            <h1 className="text-lg md:text-xl font-mono font-bold text-white truncate">{project.name}</h1>
            <p className="text-xs md:text-sm font-mono text-white/50 mt-1 line-clamp-2 md:line-clamp-none md:max-w-2xl">{project.description || 'No description'}</p>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <Link href={`/dashboard/projects/${projectId}/settings`}>
              <Button variant="outline" size="sm" className="font-mono text-[10px] border-white/20 text-white/60 hover:bg-white/5">
                <Settings className="w-3 h-3 mr-1 md:mr-2" />
                <span className="hidden sm:inline">SETTINGS</span>
                <span className="sm:hidden">SET</span>
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* Blueprint Guidance Panel */}
      <GuidancePanel
        projectId={projectId}
        section="overview"
        className="mb-4 md:mb-6"
      />

      {/* Top Summary Block */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 md:gap-3 mb-4 md:mb-6">
        <div className="bg-white/5 border border-white/10 p-3 md:p-4">
          <p className="text-[9px] md:text-[10px] font-mono text-white/40 uppercase mb-1">Domain</p>
          <p className="text-xs md:text-sm font-mono text-white font-bold truncate">{project.domain}</p>
        </div>
        <div className="bg-white/5 border border-white/10 p-3 md:p-4">
          <p className="text-[9px] md:text-[10px] font-mono text-white/40 uppercase mb-1">Prediction Core</p>
          <p className="text-xs md:text-sm font-mono text-cyan-400 font-bold flex items-center gap-1">
            <Target className="w-3 h-3 flex-shrink-0" />
            <span className="truncate">Collective</span>
          </p>
        </div>
        <div className="bg-white/5 border border-white/10 p-3 md:p-4">
          <p className="text-[9px] md:text-[10px] font-mono text-white/40 uppercase mb-1">Horizon</p>
          <p className="text-xs md:text-sm font-mono text-white font-bold">{project.settings?.default_horizon || 100} ticks</p>
        </div>
        <div className="bg-white/5 border border-white/10 p-3 md:p-4">
          <p className="text-[9px] md:text-[10px] font-mono text-white/40 uppercase mb-1">Updated</p>
          <p className="text-xs md:text-sm font-mono text-white flex items-center gap-1">
            <Calendar className="w-3 h-3 text-white/40 flex-shrink-0" />
            <span className="truncate">{new Date(project.updated_at).toLocaleDateString()}</span>
          </p>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6 mb-6 md:mb-8">

        {/* Baseline Block */}
        <div className={cn(
          "border p-4 md:p-6 col-span-1",
          hasBaseline
            ? "bg-green-500/5 border-green-500/30"
            : "bg-yellow-500/5 border-yellow-500/30"
        )}>
          <div className="flex items-center gap-2 mb-3 md:mb-4">
            {hasBaseline ? (
              <CheckCircle2 className="w-4 h-4 md:w-5 md:h-5 text-green-400" />
            ) : (
              <AlertTriangle className="w-4 h-4 md:w-5 md:h-5 text-yellow-400" />
            )}
            <h3 className="font-mono font-bold text-white text-xs md:text-sm uppercase">
              {hasBaseline ? "Baseline Complete" : "Baseline Required"}
            </h3>
          </div>

          {hasBaseline && rootNode ? (
            <div className="space-y-2 md:space-y-3">
              <div className="flex items-center justify-between text-[10px] md:text-xs font-mono">
                <span className="text-white/50">Probability</span>
                <span className="text-green-400">{(rootNode.probability * 100).toFixed(0)}%</span>
              </div>
              <div className="flex items-center justify-between text-[10px] md:text-xs font-mono">
                <span className="text-white/50">Confidence</span>
                <span className={cn(
                  (rootNode.confidence_level === 'high' || rootNode.confidence_level === 'very_high') && "text-green-400",
                  rootNode.confidence_level === 'medium' && "text-yellow-400",
                  (rootNode.confidence_level === 'low' || rootNode.confidence_level === 'very_low') && "text-red-400"
                )}>
                  {rootNode.confidence_level?.toUpperCase() || 'N/A'}
                </span>
              </div>
              <div className="flex items-center justify-between text-[10px] md:text-xs font-mono">
                <span className="text-white/50">Children</span>
                <span className="text-white">{rootNode.child_count}</span>
              </div>
              <Link href={`/dashboard/nodes/${rootNode.node_id}`}>
                <Button variant="outline" size="sm" className="w-full mt-3 md:mt-4 font-mono text-[10px] border-white/20 text-white/60 hover:bg-white/5">
                  VIEW BASELINE
                </Button>
              </Link>
            </div>
          ) : (
            <div className="space-y-2 md:space-y-3">
              <p className="text-[10px] md:text-xs font-mono text-white/50">
                Run a baseline simulation to establish the default future.
              </p>
              <Button
                onClick={handleRunBaseline}
                disabled={isCreatingBaseline}
                className="w-full bg-yellow-500/20 hover:bg-yellow-500/30 border-yellow-500/50 text-yellow-400 text-xs"
              >
                {isCreatingBaseline ? (
                  <Loader2 className="w-3.5 h-3.5 md:w-4 md:h-4 mr-2 animate-spin" />
                ) : (
                  <Play className="w-3.5 h-3.5 md:w-4 md:h-4 mr-2" />
                )}
                RUN BASELINE
              </Button>
            </div>
          )}
        </div>

        {/* Latest Node Block */}
        <div className="bg-white/5 border border-white/10 p-4 md:p-6">
          <div className="flex items-center gap-2 mb-3 md:mb-4">
            <GitBranch className="w-4 h-4 md:w-5 md:h-5 text-cyan-400" />
            <h3 className="font-mono font-bold text-white text-xs md:text-sm uppercase">Latest Node</h3>
          </div>

          {nodesLoading ? (
            <div className="flex items-center justify-center py-6 md:py-8">
              <Loader2 className="w-4 h-4 md:w-5 md:h-5 animate-spin text-white/40" />
            </div>
          ) : latestNode ? (
            <div className="space-y-2 md:space-y-3">
              <p className="text-[10px] md:text-xs font-mono text-white/70 truncate">
                {latestNode.label || `Node ${latestNode.node_id.slice(0, 8)}`}
              </p>
              <div className="flex items-center justify-between text-[10px] md:text-xs font-mono">
                <span className="text-white/50">Probability</span>
                <span className="text-cyan-400">{(latestNode.probability * 100).toFixed(1)}%</span>
              </div>
              <div className="flex items-center justify-between text-[10px] md:text-xs font-mono">
                <span className="text-white/50">Confidence</span>
                <span className={cn(
                  (latestNode.confidence_level === 'high' || latestNode.confidence_level === 'very_high') && "text-green-400",
                  latestNode.confidence_level === 'medium' && "text-yellow-400",
                  (latestNode.confidence_level === 'low' || latestNode.confidence_level === 'very_low') && "text-red-400"
                )}>
                  {latestNode.confidence_level?.toUpperCase() || 'N/A'}
                </span>
              </div>
              <div className="flex items-center justify-between text-[10px] md:text-xs font-mono">
                <span className="text-white/50">Has Outcome</span>
                <span className={latestNode.has_outcome ? "text-green-400" : "text-white/40"}>
                  {latestNode.has_outcome ? 'YES' : 'PENDING'}
                </span>
              </div>
              <Link href={`/dashboard/nodes/${latestNode.node_id}`}>
                <Button variant="outline" size="sm" className="w-full mt-3 md:mt-4 font-mono text-[10px] border-white/20 text-white/60 hover:bg-white/5">
                  VIEW NODE
                </Button>
              </Link>
            </div>
          ) : (
            <div className="text-center py-6 md:py-8">
              <Layers className="w-6 h-6 md:w-8 md:h-8 text-white/20 mx-auto mb-2" />
              <p className="text-[10px] md:text-xs font-mono text-white/40">No nodes yet</p>
            </div>
          )}
        </div>

        {/* Reliability Block */}
        <div className="bg-white/5 border border-white/10 p-4 md:p-6 md:col-span-2 lg:col-span-1">
          <div className="flex items-center gap-2 mb-3 md:mb-4">
            <Shield className="w-4 h-4 md:w-5 md:h-5 text-purple-400" />
            <h3 className="font-mono font-bold text-white text-xs md:text-sm uppercase">Reliability</h3>
          </div>

          <div className="space-y-2 md:space-y-3">
            <div className="flex items-center justify-between text-[10px] md:text-xs font-mono">
              <span className="text-white/50">Calibration</span>
              <span className="text-white/40">Not calibrated</span>
            </div>
            <div className="flex items-center justify-between text-[10px] md:text-xs font-mono">
              <span className="text-white/50">Stability</span>
              <span className="text-white/40">—</span>
            </div>
            <div className="flex items-center justify-between text-[10px] md:text-xs font-mono">
              <span className="text-white/50">Drift</span>
              <span className="text-green-400">None detected</span>
            </div>
            <div className="flex items-center justify-between text-[10px] md:text-xs font-mono">
              <span className="text-white/50">Data Gaps</span>
              <span className="text-white/40">—</span>
            </div>
            <Link href={`/dashboard/projects/${projectId}/reliability`}>
              <Button variant="outline" size="sm" className="w-full mt-3 md:mt-4 font-mono text-[10px] border-white/20 text-white/60 hover:bg-white/5">
                VIEW RELIABILITY
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 md:gap-3 mb-6 md:mb-8">
        <div className="bg-white/5 border border-white/10 p-3 md:p-4">
          <div className="flex items-center gap-2 md:gap-3">
            <div className="w-8 h-8 md:w-10 md:h-10 bg-cyan-500/10 flex items-center justify-center flex-shrink-0">
              <Layers className="w-4 h-4 md:w-5 md:h-5 text-cyan-400" />
            </div>
            <div className="min-w-0">
              <p className="text-[9px] md:text-[10px] font-mono text-white/40 uppercase">Nodes</p>
              <p className="text-base md:text-xl font-mono font-bold text-white">{stats?.node_count || project.node_count || 0}</p>
            </div>
          </div>
        </div>
        <div className="bg-white/5 border border-white/10 p-3 md:p-4">
          <div className="flex items-center gap-2 md:gap-3">
            <div className="w-8 h-8 md:w-10 md:h-10 bg-purple-500/10 flex items-center justify-center flex-shrink-0">
              <Activity className="w-4 h-4 md:w-5 md:h-5 text-purple-400" />
            </div>
            <div className="min-w-0">
              <p className="text-[9px] md:text-[10px] font-mono text-white/40 uppercase">Runs</p>
              <p className="text-base md:text-xl font-mono font-bold text-white">{stats?.run_count || project.run_count || 0}</p>
            </div>
          </div>
        </div>
        <div className="bg-white/5 border border-white/10 p-3 md:p-4">
          <div className="flex items-center gap-2 md:gap-3">
            <div className="w-8 h-8 md:w-10 md:h-10 bg-green-500/10 flex items-center justify-center flex-shrink-0">
              <CheckCircle2 className="w-4 h-4 md:w-5 md:h-5 text-green-400" />
            </div>
            <div className="min-w-0">
              <p className="text-[9px] md:text-[10px] font-mono text-white/40 uppercase">Completed</p>
              <p className="text-base md:text-xl font-mono font-bold text-white">{stats?.completed_runs || 0}</p>
            </div>
          </div>
        </div>
        <div className="bg-white/5 border border-white/10 p-3 md:p-4">
          <div className="flex items-center gap-2 md:gap-3">
            <div className="w-8 h-8 md:w-10 md:h-10 bg-white/10 flex items-center justify-center flex-shrink-0">
              <Users className="w-4 h-4 md:w-5 md:h-5 text-white/60" />
            </div>
            <div className="min-w-0">
              <p className="text-[9px] md:text-[10px] font-mono text-white/40 uppercase">Agents</p>
              <p className="text-base md:text-xl font-mono font-bold text-white">{project.settings?.default_agent_count?.toLocaleString() || '—'}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Suggested Actions */}
      <div className="mb-6 md:mb-8">
        <h2 className="text-xs md:text-sm font-mono font-bold text-white mb-3 md:mb-4 uppercase flex items-center gap-2">
          <Zap className="w-3.5 h-3.5 md:w-4 md:h-4 text-yellow-400" />
          Suggested Actions
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2 md:gap-3">
          <Link href={`/dashboard/nodes?project_id=${projectId}`}>
            <div className="bg-white/5 border border-white/10 p-3 md:p-4 hover:bg-white/[0.07] hover:border-cyan-500/30 transition-all cursor-pointer group">
              <div className="flex items-center gap-2 md:gap-3">
                <Map className="w-4 h-4 md:w-5 md:h-5 text-cyan-400 flex-shrink-0" />
                <div className="min-w-0">
                  <p className="text-xs md:text-sm font-mono text-white font-bold group-hover:text-cyan-400 transition-colors truncate">Open Universe Map</p>
                  <p className="text-[9px] md:text-[10px] font-mono text-white/40 truncate">Explore future branches</p>
                </div>
              </div>
            </div>
          </Link>

          <button
            disabled={!hasBaseline}
            className={cn(
              "bg-white/5 border border-white/10 p-3 md:p-4 hover:bg-white/[0.07] hover:border-purple-500/30 transition-all cursor-pointer group text-left w-full",
              !hasBaseline && "opacity-50 cursor-not-allowed"
            )}
          >
            <div className="flex items-center gap-2 md:gap-3">
              <MessageCircle className="w-4 h-4 md:w-5 md:h-5 text-purple-400 flex-shrink-0" />
              <div className="min-w-0">
                <p className="text-xs md:text-sm font-mono text-white font-bold group-hover:text-purple-400 transition-colors truncate">Ask a What-If</p>
                <p className="text-[9px] md:text-[10px] font-mono text-white/40 truncate">{hasBaseline ? "Create new scenarios" : "Run baseline first"}</p>
              </div>
            </div>
          </button>

          <Link href={`/dashboard/personas?project_id=${projectId}`}>
            <div className="bg-white/5 border border-white/10 p-3 md:p-4 hover:bg-white/[0.07] hover:border-green-500/30 transition-all cursor-pointer group">
              <div className="flex items-center gap-2 md:gap-3">
                <Users className="w-4 h-4 md:w-5 md:h-5 text-green-400 flex-shrink-0" />
                <div className="min-w-0">
                  <p className="text-xs md:text-sm font-mono text-white font-bold group-hover:text-green-400 transition-colors truncate">Manage Personas</p>
                  <p className="text-[9px] md:text-[10px] font-mono text-white/40 truncate">Add or edit personas</p>
                </div>
              </div>
            </div>
          </Link>

          <Link href={`/dashboard/projects/${projectId}/calibrate`}>
            <div className="bg-white/5 border border-white/10 p-3 md:p-4 hover:bg-white/[0.07] hover:border-yellow-500/30 transition-all cursor-pointer group">
              <div className="flex items-center gap-2 md:gap-3">
                <TrendingUp className="w-4 h-4 md:w-5 md:h-5 text-yellow-400 flex-shrink-0" />
                <div className="min-w-0">
                  <p className="text-xs md:text-sm font-mono text-white font-bold group-hover:text-yellow-400 transition-colors truncate">Calibrate</p>
                  <p className="text-[9px] md:text-[10px] font-mono text-white/40 truncate">Improve accuracy</p>
                </div>
              </div>
            </div>
          </Link>
        </div>
      </div>

      {/* Footer Status */}
      <div className="mt-6 md:mt-8 pt-3 md:pt-4 border-t border-white/5">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 text-[9px] md:text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-1">
            <Terminal className="w-3 h-3" />
            <span>PROJECT OVERVIEW MODULE</span>
          </div>
          <span className="text-white/20 sm:text-white/30">AGENTVERSE v1.0.0</span>
        </div>
      </div>
    </div>
  );
}
