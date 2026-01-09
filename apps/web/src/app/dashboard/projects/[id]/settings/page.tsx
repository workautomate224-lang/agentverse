'use client';

import { Settings } from 'lucide-react';
import { PlaceholderPage } from '@/components/project/PlaceholderPage';

export default function SettingsPage() {
  return (
    <PlaceholderPage
      title="Project Settings"
      description="Configure project parameters, default run configurations, and access controls. Admin access required."
      icon={Settings}
    />
  );
}
