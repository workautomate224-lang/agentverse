'use client';

import { useProject } from '@/components/project/ProjectContext';
import { SocietyModeStudio } from '@/components/society-mode';

export default function SocietyModePage() {
  const { projectId } = useProject();

  return (
    <div className="h-full">
      <SocietyModeStudio projectId={projectId} />
    </div>
  );
}
