'use client';

import { useProject } from '@/components/project/ProjectContext';
import { ReliabilityDashboard } from '@/components/reliability';

export default function ReliabilityPage() {
  const { projectId } = useProject();

  return (
    <div className="h-full overflow-auto">
      <ReliabilityDashboard projectId={projectId} />
    </div>
  );
}
