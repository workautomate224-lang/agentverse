'use client';

import { useProject } from '@/components/project/ProjectContext';
import { ExportsPage } from '@/components/exports';

export default function ExportsPageRoute() {
  const { projectId } = useProject();

  return (
    <div className="h-full">
      <ExportsPage projectId={projectId} />
    </div>
  );
}
