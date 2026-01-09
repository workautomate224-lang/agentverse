'use client';

// Vi World Page
// Route: /dashboard/personas/[id]/world
// Displays the Vi World visualization for a persona template

import { useParams } from 'next/navigation';
import { ViWorld } from '@/components/vi-world';

export default function ViWorldPage() {
  const params = useParams();
  const templateId = params.id as string;

  return <ViWorld templateId={templateId} />;
}
