'use client';

import dynamic from 'next/dynamic';
import { useProject } from '@/components/project/ProjectContext';
import { PageLoading } from '@/components/ui/page-loading';
import { GuidancePanel } from '@/components/pil/v2/GuidancePanel';

// Dynamic import for heavy multi-panel studio component
const TargetModeStudio = dynamic(
  () => import('@/components/target-mode').then((mod) => mod.TargetModeStudio),
  {
    loading: () => <PageLoading type="detail" title="Target Mode Studio" />,
    ssr: false,
  }
);

export default function TargetModePage() {
  const { projectId } = useProject();

  return (
    <div className="h-full flex flex-col">
      <div className="px-4 pt-4 flex-shrink-0">
        <GuidancePanel projectId={projectId} section="target" className="mb-4" />
      </div>
      <div className="flex-1 min-h-0">
        <TargetModeStudio projectId={projectId} />
      </div>
    </div>
  );
}
