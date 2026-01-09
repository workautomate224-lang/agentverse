'use client';

import dynamic from 'next/dynamic';
import { useProject } from '@/components/project/ProjectContext';
import { PageLoading } from '@/components/ui/page-loading';

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
    <div className="h-full">
      <TargetModeStudio projectId={projectId} />
    </div>
  );
}
