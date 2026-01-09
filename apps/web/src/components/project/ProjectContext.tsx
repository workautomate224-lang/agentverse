'use client';

import { createContext, useContext, ReactNode } from 'react';
import { useParams } from 'next/navigation';
import { useProjectSpec, useProjectSpecStats, useNodes } from '@/hooks/useApi';
import type { ProjectSpec, ProjectSpecStats, NodeSummary } from '@/lib/api';

interface ProjectContextValue {
  projectId: string;
  project: ProjectSpec | undefined;
  stats: ProjectSpecStats | undefined;
  nodes: NodeSummary[];
  rootNode: NodeSummary | undefined;
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
}

const ProjectContext = createContext<ProjectContextValue | null>(null);

export function ProjectProvider({ children }: { children: ReactNode }) {
  const params = useParams();
  const projectId = params.id as string;

  const {
    data: project,
    isLoading: isLoadingProject,
    isError: isErrorProject,
    error: projectError,
  } = useProjectSpec(projectId);

  const {
    data: stats,
    isLoading: isLoadingStats,
  } = useProjectSpecStats(projectId);

  const {
    data: nodes,
    isLoading: isLoadingNodes,
  } = useNodes({ project_id: projectId, limit: 100 });

  const nodeList = nodes ?? [];
  const rootNode = nodeList.find((n) => n.is_baseline);

  const isLoading = isLoadingProject || isLoadingStats || isLoadingNodes;
  const isError = isErrorProject;
  const error = projectError as Error | null;

  return (
    <ProjectContext.Provider
      value={{
        projectId,
        project,
        stats,
        nodes: nodeList,
        rootNode,
        isLoading,
        isError,
        error,
      }}
    >
      {children}
    </ProjectContext.Provider>
  );
}

export function useProject() {
  const context = useContext(ProjectContext);
  if (!context) {
    throw new Error('useProject must be used within a ProjectProvider');
  }
  return context;
}
