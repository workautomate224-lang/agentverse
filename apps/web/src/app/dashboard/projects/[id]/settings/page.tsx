'use client';

import { Settings } from 'lucide-react';
import { PlaceholderPage } from '@/components/project/PlaceholderPage';
import { useProject } from '@/components/project/ProjectContext';
import { GuidancePanel } from '@/components/pil/v2/GuidancePanel';

export default function SettingsPage() {
  const { projectId } = useProject();

  return (
    <div className="h-full flex flex-col">
      <div className="px-4 pt-4 flex-shrink-0">
        <GuidancePanel projectId={projectId} section="settings" className="mb-4" />
      </div>
      <div className="flex-1 min-h-0">
        <PlaceholderPage
          title="Project Settings"
          description="Configure project parameters, default run configurations, and access controls. Admin access required."
          icon={Settings}
        />
      </div>
    </div>
  );
}
