'use client';

import { ReactNode } from 'react';
import { ProjectProvider } from '@/components/project/ProjectContext';
import { ProjectHeader } from '@/components/project/ProjectHeader';
import { ProjectTabNav } from '@/components/project/ProjectTabNav';
import { useParams } from 'next/navigation';

interface ProjectLayoutProps {
  children: ReactNode;
}

export default function ProjectLayout({ children }: ProjectLayoutProps) {
  const params = useParams();
  const projectId = params.id as string;

  return (
    <ProjectProvider>
      <div className="flex flex-col h-full">
        {/* Project Header */}
        <ProjectHeader />

        {/* Tab Navigation */}
        <ProjectTabNav projectId={projectId} />

        {/* Page Content */}
        <div className="flex-1 overflow-auto">
          {children}
        </div>
      </div>
    </ProjectProvider>
  );
}
