'use client';

import { useProject } from '@/components/project/ProjectContext';
import { ExportsPage } from '@/components/exports';
import { GuidancePanel } from '@/components/pil/v2/GuidancePanel';

export default function ExportsPageRoute() {
  const { projectId } = useProject();

  return (
    <div className="h-full flex flex-col">
      <div className="px-4 pt-4 flex-shrink-0">
        <GuidancePanel projectId={projectId} section="reports" className="mb-4" />
      </div>
      <div className="flex-1 min-h-0">
        <ExportsPage projectId={projectId} />
      </div>
    </div>
  );
}
