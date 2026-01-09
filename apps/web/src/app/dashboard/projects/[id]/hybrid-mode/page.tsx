'use client';

/**
 * Hybrid Mode Page
 * Reference: project.md §11 Phase 6, Interaction_design.md §5.14
 *
 * Model key actors inside a population context when needed.
 */

import { useProject } from '@/components/project/ProjectContext';
import { HybridModeStudio } from '@/components/hybrid-mode';

export default function HybridModePage() {
  const { projectId } = useProject();

  return (
    <div className="h-full">
      <HybridModeStudio projectId={projectId} />
    </div>
  );
}
