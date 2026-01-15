'use client';

import dynamic from 'next/dynamic';
import { useProject } from '@/components/project/ProjectContext';
import { PageLoading } from '@/components/ui/page-loading';
import { GuidancePanel } from '@/components/pil/v2/GuidancePanel';

// Dynamic import for heavy SVG canvas component
const UniverseMap = dynamic(
  () => import('@/components/universe-map').then((mod) => mod.UniverseMap),
  {
    loading: () => <PageLoading type="graph" title="Universe Map" />,
    ssr: false, // Disable SSR for canvas-heavy component
  }
);

export default function UniverseMapPage() {
  const { projectId } = useProject();

  return (
    <div className="h-full flex flex-col">
      <div className="px-4 pt-4 flex-shrink-0">
        <GuidancePanel projectId={projectId} section="universe" className="mb-4" />
      </div>
      <div className="flex-1 min-h-0">
        <UniverseMap projectId={projectId} showSidebar />
      </div>
    </div>
  );
}
