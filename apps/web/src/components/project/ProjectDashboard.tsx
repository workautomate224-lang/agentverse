'use client';

/**
 * ProjectDashboard Component
 * Main dashboard for project management and simulation overview.
 * Reference: project.md §6.1 (ProjectSpec), §6.5-6.6 (Run)
 *
 * Integrates: ProjectList, ProjectOverview, Universe Map access, Run management
 */

import { memo, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  FolderKanban,
  Plus,
  Map,
  Activity,
  GitBranch,
  Terminal,
  LayoutGrid,
  PanelLeft,
  RefreshCw,
  Settings,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { ProjectList } from './ProjectList';
import { ProjectOverview } from './ProjectOverview';
import { UniverseMap } from '@/components/universe-map';
import { RunCreateForm } from '@/components/runs/RunCreateForm';
import { useCreateProjectSpec, useCreateRun } from '@/hooks/useApi';
import type { SubmitRunInput } from '@/lib/api';

interface ProjectDashboardProps {
  initialProjectId?: string;
  className?: string;
}

type ViewMode = 'list' | 'detail' | 'map' | 'run-create';

export const ProjectDashboard = memo(function ProjectDashboard({
  initialProjectId,
  className,
}: ProjectDashboardProps) {
  const router = useRouter();

  // State
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(
    initialProjectId || null
  );
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>(
    initialProjectId ? 'detail' : 'list'
  );
  const [showSidebar, setShowSidebar] = useState(true);

  // Mutations
  const createProject = useCreateProjectSpec();
  const createRun = useCreateRun();

  // Handle project selection
  const handleProjectSelect = useCallback((projectId: string) => {
    setSelectedProjectId(projectId);
    setViewMode('detail');
  }, []);

  // Handle create project
  const handleCreateProject = useCallback(() => {
    router.push('/dashboard/projects/new');
  }, [router]);

  // Handle create run
  const handleCreateRun = useCallback((projectId?: string) => {
    if (projectId) {
      setSelectedProjectId(projectId);
    }
    setViewMode('run-create');
  }, []);

  // Handle view universe map
  const handleViewMap = useCallback((projectId?: string) => {
    if (projectId) {
      setSelectedProjectId(projectId);
    }
    setViewMode('map');
  }, []);

  // Handle run submission
  const handleRunSubmit = useCallback((input: SubmitRunInput) => {
    createRun.mutate(input, {
      onSuccess: (run) => {
        router.push(`/dashboard/runs/${run.run_id}`);
      },
    });
  }, [createRun, router]);

  // Handle node selection (from Universe Map)
  const handleNodeSelect = useCallback((nodeId: string) => {
    setSelectedNodeId(nodeId);
  }, []);

  // Handle back to list
  const handleBackToList = useCallback(() => {
    setViewMode('list');
    setSelectedProjectId(null);
  }, []);

  return (
    <div className={cn('flex h-full bg-black', className)}>
      {/* Sidebar */}
      {showSidebar && viewMode !== 'list' && (
        <div className="w-80 border-r border-white/10 flex flex-col">
          <ProjectList
            selectedProjectId={selectedProjectId || undefined}
            onProjectSelect={handleProjectSelect}
            onCreateProject={handleCreateProject}
            onCreateRun={handleCreateRun}
            onViewMap={handleViewMap}
            className="h-full"
          />
        </div>
      )}

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 bg-black border-b border-white/10">
          <div className="flex items-center gap-4">
            {viewMode !== 'list' && (
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={() => setShowSidebar(!showSidebar)}
                title={showSidebar ? 'Hide sidebar' : 'Show sidebar'}
              >
                <PanelLeft className="w-4 h-4" />
              </Button>
            )}
            <div className="flex items-center gap-2">
              <Terminal className="w-4 h-4 text-white/40" />
              <span className="text-xs font-mono text-white/40 uppercase tracking-wider">
                {viewMode === 'list' && 'Project Manager'}
                {viewMode === 'detail' && 'Project Overview'}
                {viewMode === 'map' && 'Universe Map'}
                {viewMode === 'run-create' && 'Create Run'}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* View Mode Toggles */}
            {selectedProjectId && (
              <div className="flex items-center bg-white/5 border border-white/10">
                <button
                  onClick={() => setViewMode('detail')}
                  className={cn(
                    'flex items-center gap-1 px-3 py-1.5 text-xs font-mono transition-colors',
                    viewMode === 'detail'
                      ? 'bg-white text-black'
                      : 'text-white/60 hover:text-white'
                  )}
                >
                  <LayoutGrid className="w-3 h-3" />
                  Overview
                </button>
                <button
                  onClick={() => setViewMode('map')}
                  className={cn(
                    'flex items-center gap-1 px-3 py-1.5 text-xs font-mono transition-colors',
                    viewMode === 'map'
                      ? 'bg-white text-black'
                      : 'text-white/60 hover:text-white'
                  )}
                >
                  <GitBranch className="w-3 h-3" />
                  Map
                </button>
                <button
                  onClick={() => setViewMode('run-create')}
                  className={cn(
                    'flex items-center gap-1 px-3 py-1.5 text-xs font-mono transition-colors',
                    viewMode === 'run-create'
                      ? 'bg-white text-black'
                      : 'text-white/60 hover:text-white'
                  )}
                >
                  <Activity className="w-3 h-3" />
                  New Run
                </button>
              </div>
            )}

            {viewMode !== 'list' && (
              <Button variant="ghost" size="sm" onClick={handleBackToList}>
                <FolderKanban className="w-3 h-3 mr-1" />
                All Projects
              </Button>
            )}
          </div>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-auto">
          {viewMode === 'list' && (
            <ProjectList
              selectedProjectId={selectedProjectId || undefined}
              onProjectSelect={handleProjectSelect}
              onCreateProject={handleCreateProject}
              onCreateRun={handleCreateRun}
              onViewMap={handleViewMap}
              className="h-full"
            />
          )}

          {viewMode === 'detail' && selectedProjectId && (
            <div className="p-6">
              <ProjectOverview
                projectId={selectedProjectId}
                onCreateRun={() => handleCreateRun(selectedProjectId)}
                onViewMap={() => handleViewMap(selectedProjectId)}
              />
            </div>
          )}

          {viewMode === 'map' && selectedProjectId && (
            <UniverseMap
              projectId={selectedProjectId}
              onNodeSelect={handleNodeSelect}
              className="h-full"
            />
          )}

          {viewMode === 'run-create' && selectedProjectId && (
            <div className="p-6 max-w-2xl mx-auto">
              <div className="mb-6">
                <h2 className="text-lg font-mono font-bold text-white mb-1">
                  Create New Run
                </h2>
                <p className="text-xs font-mono text-white/40">
                  Configure and execute a new simulation run for this project.
                  {!selectedNodeId && ' Select a node from the Universe Map first.'}
                </p>
              </div>
              <RunCreateForm
                projectId={selectedProjectId}
                nodeId={selectedNodeId || undefined}
                onSubmit={handleRunSubmit}
                onCancel={() => setViewMode('detail')}
                isSubmitting={createRun.isPending}
              />
            </div>
          )}

          {/* Empty state when no project selected in non-list views */}
          {viewMode !== 'list' && !selectedProjectId && (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <FolderKanban className="w-10 h-10 text-white/20 mx-auto mb-4" />
                <p className="text-sm font-mono text-white/40 mb-4">
                  Select a project to view details
                </p>
                <Button variant="secondary" size="sm" onClick={handleBackToList}>
                  Browse Projects
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* Footer Status */}
        <div className="flex items-center justify-between px-6 py-2 bg-black/50 border-t border-white/10">
          <div className="flex items-center gap-4 text-[10px] font-mono text-white/30">
            <div className="flex items-center gap-1">
              <div className="w-1.5 h-1.5 bg-green-500 rounded-full" />
              <span>SYSTEM ONLINE</span>
            </div>
            {selectedProjectId && (
              <>
                <span>|</span>
                <span>Project: {selectedProjectId.slice(0, 12)}...</span>
              </>
            )}
          </div>
          <span className="text-[10px] font-mono text-white/30">
            AGENTVERSE PROJECT DASHBOARD v1.0
          </span>
        </div>
      </div>
    </div>
  );
});

export default ProjectDashboard;
