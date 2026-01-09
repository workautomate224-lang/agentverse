'use client';

import { MarketplaceTemplateListItem } from '@/lib/api';
import { TemplateCard } from './TemplateCard';

interface TemplateGridProps {
  templates: MarketplaceTemplateListItem[];
  onLike?: (templateId: string) => void;
  likedIds?: Set<string>;
  loading?: boolean;
  emptyMessage?: string;
}

export function TemplateGrid({
  templates,
  onLike,
  likedIds = new Set(),
  loading = false,
  emptyMessage = 'No templates found',
}: TemplateGridProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {[...Array(8)].map((_, i) => (
          <div
            key={i}
            className="bg-white rounded-lg border border-gray-200 animate-pulse"
          >
            <div className="h-40 bg-gray-200 rounded-t-lg" />
            <div className="p-4 space-y-3">
              <div className="h-4 bg-gray-200 rounded w-1/4" />
              <div className="h-5 bg-gray-200 rounded w-3/4" />
              <div className="h-4 bg-gray-200 rounded w-full" />
              <div className="h-4 bg-gray-200 rounded w-2/3" />
              <div className="flex gap-2 pt-3 border-t border-gray-100">
                <div className="h-4 bg-gray-200 rounded w-16" />
                <div className="h-4 bg-gray-200 rounded w-16" />
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (templates.length === 0) {
    return (
      <div className="text-center py-12 bg-gray-50 rounded-lg">
        <p className="text-gray-500">{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
      {templates.map((template) => (
        <TemplateCard
          key={template.id}
          template={template}
          onLike={onLike}
          isLiked={likedIds.has(template.id)}
        />
      ))}
    </div>
  );
}

export default TemplateGrid;
