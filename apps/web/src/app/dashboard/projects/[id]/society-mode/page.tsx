'use client';

import { useProject } from '@/components/project/ProjectContext';
import { SocietyModeStudio } from '@/components/society-mode';
import { GuidancePanel } from '@/components/pil/v2/GuidancePanel';

export default function SocietyModePage() {
  const { projectId } = useProject();

  return (
    <div className="h-full flex flex-col">
      <div className="px-4 pt-4 flex-shrink-0">
        <GuidancePanel projectId={projectId} section="society" className="mb-4" />
      </div>
      <div className="flex-1 min-h-0">
        <SocietyModeStudio projectId={projectId} />
      </div>
    </div>
  );
}
