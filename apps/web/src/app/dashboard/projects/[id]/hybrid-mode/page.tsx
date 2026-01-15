'use client';

/**
 * Hybrid Mode Page
 * Reference: project.md §11 Phase 6, Interaction_design.md §5.14
 *
 * Model key actors inside a population context when needed.
 */

import { useProject } from '@/components/project/ProjectContext';
import { HybridModeStudio } from '@/components/hybrid-mode';
import { GuidancePanel } from '@/components/pil/v2/GuidancePanel';

export default function HybridModePage() {
  const { projectId } = useProject();

  return (
    <div className="h-full flex flex-col">
      <div className="px-4 pt-4 flex-shrink-0">
        <GuidancePanel projectId={projectId} section="runs" className="mb-4" />
      </div>
      <div className="flex-1 min-h-0">
        <HybridModeStudio projectId={projectId} />
      </div>
    </div>
  );
}
