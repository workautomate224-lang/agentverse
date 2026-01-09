'use client';

import { Users } from 'lucide-react';
import { PlaceholderPage } from '@/components/project/PlaceholderPage';

export default function PersonasPage() {
  return (
    <PlaceholderPage
      title="Personas"
      description="Manage project-scoped personas. Import from templates, generate new personas, or upload custom data to build your simulation population."
      icon={Users}
    />
  );
}
