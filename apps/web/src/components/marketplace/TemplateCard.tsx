'use client';

import Link from 'next/link';
import { Star, Heart, Download, CheckCircle, Sparkles, User } from 'lucide-react';
import { MarketplaceTemplateListItem } from '@/lib/api';
import { formatDistanceToNow } from 'date-fns';

interface TemplateCardProps {
  template: MarketplaceTemplateListItem;
  onLike?: (templateId: string) => void;
  isLiked?: boolean;
}

export function TemplateCard({ template, onLike, isLiked }: TemplateCardProps) {
  const handleLike = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onLike?.(template.id);
  };

  return (
    <Link
      href={`/dashboard/marketplace/${template.slug}`}
      className="group block bg-white rounded-lg border border-gray-200 hover:border-primary-300 hover:shadow-lg transition-all duration-200"
    >
      {/* Preview Image */}
      <div className="relative h-40 bg-gradient-to-br from-primary-50 to-primary-100 rounded-t-lg overflow-hidden">
        {template.preview_image_url ? (
          <img
            src={template.preview_image_url}
            alt={template.name}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="flex items-center justify-center h-full">
            <span className="text-5xl font-bold text-primary-200">
              {template.name.charAt(0).toUpperCase()}
            </span>
          </div>
        )}

        {/* Badges */}
        <div className="absolute top-2 left-2 flex gap-1">
          {template.is_featured && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-yellow-500 text-white text-xs font-medium rounded-full">
              <Sparkles className="w-3 h-3" />
              Featured
            </span>
          )}
          {template.is_verified && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-green-500 text-white text-xs font-medium rounded-full">
              <CheckCircle className="w-3 h-3" />
              Verified
            </span>
          )}
        </div>

        {/* Like button */}
        {onLike && (
          <button
            onClick={handleLike}
            className="absolute top-2 right-2 p-2 bg-white/80 hover:bg-white rounded-full shadow-sm transition-colors"
          >
            <Heart
              className={`w-4 h-4 ${
                isLiked ? 'fill-red-500 text-red-500' : 'text-gray-600'
              }`}
            />
          </button>
        )}

        {/* Premium badge */}
        {template.is_premium && (
          <div className="absolute bottom-2 right-2 px-2 py-1 bg-primary-600 text-white text-xs font-semibold rounded">
            ${template.price_usd?.toFixed(2)}
          </div>
        )}
      </div>

      {/* Content */}
      <div className="p-4">
        {/* Category and scenario type */}
        <div className="flex items-center gap-2 mb-2">
          {template.category_name && (
            <span className="text-xs font-medium text-primary-600 bg-primary-50 px-2 py-0.5 rounded">
              {template.category_name}
            </span>
          )}
          <span className="text-xs text-gray-500 capitalize">
            {template.scenario_type.replace('_', ' ')}
          </span>
        </div>

        {/* Title */}
        <h3 className="font-semibold text-gray-900 group-hover:text-primary-600 transition-colors line-clamp-1">
          {template.name}
        </h3>

        {/* Description */}
        {template.short_description && (
          <p className="mt-1 text-sm text-gray-600 line-clamp-2">
            {template.short_description}
          </p>
        )}

        {/* Tags */}
        {template.tags.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {template.tags.slice(0, 3).map((tag) => (
              <span
                key={tag}
                className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded"
              >
                {tag}
              </span>
            ))}
            {template.tags.length > 3 && (
              <span className="text-xs text-gray-400">
                +{template.tags.length - 3}
              </span>
            )}
          </div>
        )}

        {/* Stats */}
        <div className="mt-3 pt-3 border-t border-gray-100 flex items-center justify-between">
          <div className="flex items-center gap-3 text-sm text-gray-500">
            <span className="flex items-center gap-1">
              <Star className="w-4 h-4 text-yellow-500 fill-yellow-500" />
              {template.rating_average.toFixed(1)}
              <span className="text-gray-400">({template.rating_count})</span>
            </span>
            <span className="flex items-center gap-1">
              <Download className="w-4 h-4" />
              {template.usage_count}
            </span>
          </div>
          <span className="flex items-center gap-1">
            <Heart
              className={`w-4 h-4 ${
                isLiked ? 'fill-red-500 text-red-500' : 'text-gray-400'
              }`}
            />
            <span className="text-sm text-gray-500">{template.like_count}</span>
          </span>
        </div>

        {/* Author */}
        <div className="mt-2 flex items-center gap-2 text-xs text-gray-500">
          <User className="w-3 h-3" />
          <span>{template.author_name || 'Anonymous'}</span>
          {template.published_at && (
            <>
              <span className="text-gray-300">|</span>
              <span>
                {formatDistanceToNow(new Date(template.published_at), {
                  addSuffix: true,
                })}
              </span>
            </>
          )}
        </div>
      </div>
    </Link>
  );
}

export default TemplateCard;
