'use client';

import { useProject } from '@/components/project/ProjectContext';
import { ReliabilityDashboard } from '@/components/reliability';
import { GuidancePanel } from '@/components/pil/v2/GuidancePanel';

export default function ReliabilityPage() {
  const { projectId } = useProject();

  return (
    <div className="h-full flex flex-col overflow-hidden">
      <div className="px-4 pt-4 flex-shrink-0">
        <GuidancePanel projectId={projectId} section="reliability" className="mb-4" />
      </div>
      <div className="flex-1 min-h-0 overflow-auto">
        <ReliabilityDashboard projectId={projectId} />
      </div>
    </div>
  );
}
