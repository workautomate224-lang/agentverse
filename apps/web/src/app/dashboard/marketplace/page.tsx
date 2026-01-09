'use client';

import { useState, useMemo } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  Plus,
  Store,
  Search,
  Loader2,
  Star,
  TrendingUp,
  Users,
  ArrowRight,
  CheckCircle,
  Sparkles,
  Filter,
  Grid3X3,
  List,
  Terminal,
} from 'lucide-react';
import {
  useMarketplaceTemplates,
  useMarketplaceCategories,
  useFeaturedTemplates,
  useMarketplaceStats,
  useToggleTemplateLike,
} from '@/hooks/useApi';
import type { MarketplaceTemplateListItem, MarketplaceCategory } from '@/lib/api';
import { cn } from '@/lib/utils';

export default function MarketplacePage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState('popular');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [filters, setFilters] = useState<{
    is_featured?: boolean;
    is_verified?: boolean;
    is_premium?: boolean;
    min_rating?: number;
  }>({});

  const { data: categories, isLoading: loadingCategories } = useMarketplaceCategories();
  const { data: featured, isLoading: loadingFeatured } = useFeaturedTemplates();
  const { data: stats } = useMarketplaceStats();
  const { data: templatesData, isLoading: loadingTemplates } = useMarketplaceTemplates({
    query: searchQuery || undefined,
    category_id: selectedCategory || undefined,
    sort_by: sortBy as 'popular' | 'newest' | 'rating' | 'usage' | 'name',
    ...filters,
    page_size: 50,
  });
  const toggleLike = useToggleTemplateLike();

  const templates = templatesData?.items || [];
  const totalTemplates = templatesData?.total || 0;

  const handleLike = async (templateId: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    await toggleLike.mutateAsync(templateId);
  };

  const handleFilterChange = (key: string, value: unknown) => {
    setFilters((prev) => ({
      ...prev,
      [key]: value === prev[key as keyof typeof prev] ? undefined : value,
    }));
  };

  return (
    <div className="min-h-screen bg-black p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Store className="w-4 h-4 text-white/60" />
            <span className="text-xs font-mono text-white/40 uppercase tracking-wider">
              Scenario Marketplace
            </span>
          </div>
          <h1 className="text-xl font-mono font-bold text-white">Templates</h1>
          <p className="text-sm font-mono text-white/50 mt-1">
            Browse and use community templates
          </p>
        </div>
        <Link href="/dashboard/marketplace/publish">
          <Button size="sm">
            <Plus className="w-3 h-3 mr-2" />
            PUBLISH
          </Button>
        </Link>
      </div>

      {/* Stats Overview */}
      {stats && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-8">
          <div className="bg-white/5 border border-white/10 p-4">
            <p className="text-[10px] font-mono text-white/40 uppercase tracking-wider">
              TEMPLATES
            </p>
            <p className="text-2xl font-mono font-bold text-white mt-1">
              {stats.total_templates}
            </p>
          </div>
          <div className="bg-white/5 border border-white/10 p-4">
            <p className="text-[10px] font-mono text-white/40 uppercase tracking-wider">
              CATEGORIES
            </p>
            <p className="text-2xl font-mono font-bold text-white mt-1">
              {stats.total_categories}
            </p>
          </div>
          <div className="bg-white/5 border border-white/10 p-4">
            <p className="text-[10px] font-mono text-white/40 uppercase tracking-wider">USAGE</p>
            <p className="text-2xl font-mono font-bold text-green-400 mt-1">
              {formatNumber(stats.total_usages)}
            </p>
          </div>
          <div className="bg-white/5 border border-white/10 p-4">
            <p className="text-[10px] font-mono text-white/40 uppercase tracking-wider">
              AVG RATING
            </p>
            <div className="flex items-center gap-1 mt-1">
              <Star className="w-4 h-4 text-yellow-400 fill-yellow-400" />
              <p className="text-2xl font-mono font-bold text-white">
                {stats.average_rating?.toFixed(1) || '-'}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Featured Templates */}
      {featured?.featured && featured.featured.length > 0 && !searchQuery && !selectedCategory && (
        <div className="mb-8">
          <div className="flex items-center gap-2 mb-3">
            <Sparkles className="w-3 h-3 text-yellow-400" />
            <h2 className="text-xs font-mono text-white/40 uppercase tracking-wider">
              Featured Templates
            </h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {featured.featured.slice(0, 3).map((template: MarketplaceTemplateListItem) => (
              <FeaturedCard key={template.id} template={template} onLike={handleLike} />
            ))}
          </div>
        </div>
      )}

      {/* Search & Filters */}
      <div className="mb-6 space-y-4">
        <div className="flex items-center gap-4">
          {/* Search */}
          <div className="relative flex-1">
            <Search className="w-3 h-3 absolute left-3 top-1/2 -translate-y-1/2 text-white/30" />
            <input
              type="text"
              placeholder="Search templates..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2 bg-white/5 border border-white/10 text-sm font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-white/30"
            />
          </div>

          {/* Sort */}
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="px-3 py-2 bg-white/5 border border-white/10 text-sm font-mono text-white appearance-none focus:outline-none focus:border-white/30"
          >
            <option value="popular">Popular</option>
            <option value="newest">Newest</option>
            <option value="rating">Top Rated</option>
            <option value="usage">Most Used</option>
            <option value="name">Name (A-Z)</option>
          </select>

          {/* View Toggle */}
          <div className="flex border border-white/10">
            <button
              onClick={() => setViewMode('grid')}
              className={cn(
                'p-2 transition-colors',
                viewMode === 'grid' ? 'bg-white/10' : 'hover:bg-white/5'
              )}
            >
              <Grid3X3 className="w-4 h-4 text-white/60" />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={cn(
                'p-2 transition-colors',
                viewMode === 'list' ? 'bg-white/10' : 'hover:bg-white/5'
              )}
            >
              <List className="w-4 h-4 text-white/60" />
            </button>
          </div>
        </div>

        {/* Quick Filters */}
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => handleFilterChange('is_featured', true)}
            className={cn(
              'text-xs font-mono px-2 py-1 border transition-colors',
              filters.is_featured
                ? 'bg-yellow-500/20 border-yellow-500/50 text-yellow-400'
                : 'border-white/10 text-white/40 hover:bg-white/5'
            )}
          >
            <Sparkles className="w-3 h-3 inline mr-1" />
            Featured
          </button>
          <button
            onClick={() => handleFilterChange('is_verified', true)}
            className={cn(
              'text-xs font-mono px-2 py-1 border transition-colors',
              filters.is_verified
                ? 'bg-green-500/20 border-green-500/50 text-green-400'
                : 'border-white/10 text-white/40 hover:bg-white/5'
            )}
          >
            <CheckCircle className="w-3 h-3 inline mr-1" />
            Verified
          </button>
          <button
            onClick={() => handleFilterChange('is_premium', false)}
            className={cn(
              'text-xs font-mono px-2 py-1 border transition-colors',
              filters.is_premium === false
                ? 'bg-blue-500/20 border-blue-500/50 text-blue-400'
                : 'border-white/10 text-white/40 hover:bg-white/5'
            )}
          >
            Free Only
          </button>

          {/* Categories */}
          {categories && categories.length > 0 && (
            <>
              <span className="text-white/20">|</span>
              {categories.slice(0, 5).map((category) => (
                <button
                  key={category.id}
                  onClick={() =>
                    setSelectedCategory(
                      selectedCategory === category.id ? null : category.id
                    )
                  }
                  className={cn(
                    'text-xs font-mono px-2 py-1 border transition-colors',
                    selectedCategory === category.id
                      ? 'bg-white/10 border-white/30 text-white'
                      : 'border-white/10 text-white/40 hover:bg-white/5'
                  )}
                >
                  {category.name}
                </button>
              ))}
            </>
          )}
        </div>
      </div>

      {/* Templates Grid/List */}
      <div className="bg-white/5 border border-white/10">
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
          <div className="flex items-center gap-2">
            <Terminal className="w-3 h-3 text-white/40" />
            <span className="text-xs font-mono text-white/40 uppercase tracking-wider">
              Templates
            </span>
          </div>
          <span className="text-xs font-mono text-white/30">
            {totalTemplates} results
          </span>
        </div>

        {loadingTemplates ? (
          <div className="p-12 flex items-center justify-center">
            <Loader2 className="w-5 h-5 animate-spin text-white/40" />
          </div>
        ) : templates.length > 0 ? (
          viewMode === 'grid' ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-px bg-white/10">
              {templates.map((template) => (
                <TemplateCard key={template.id} template={template} onLike={handleLike} />
              ))}
            </div>
          ) : (
            <div className="divide-y divide-white/5">
              {templates.map((template) => (
                <TemplateRow key={template.id} template={template} onLike={handleLike} />
              ))}
            </div>
          )
        ) : (
          <div className="p-12 text-center">
            <div className="w-12 h-12 bg-white/5 flex items-center justify-center mx-auto mb-4">
              <Store className="w-5 h-5 text-white/30" />
            </div>
            <p className="text-sm font-mono text-white/60 mb-1">No templates found</p>
            <p className="text-xs font-mono text-white/30 mb-4">
              Try adjusting your filters
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setSearchQuery('');
                setSelectedCategory(null);
                setFilters({});
              }}
              className="font-mono text-xs border-white/20 text-white/60 hover:bg-white/5 hover:text-white"
            >
              CLEAR FILTERS
            </Button>
          </div>
        )}
      </div>

      {/* My Templates Link */}
      <div className="mt-6 flex justify-center">
        <Link href="/dashboard/marketplace/my-templates">
          <Button
            variant="outline"
            size="sm"
            className="font-mono text-xs border-white/20 text-white/60 hover:bg-white/5 hover:text-white"
          >
            VIEW MY TEMPLATES
            <ArrowRight className="w-3 h-3 ml-2" />
          </Button>
        </Link>
      </div>

      {/* Footer */}
      <div className="mt-8 pt-4 border-t border-white/5">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1">
              <Terminal className="w-3 h-3" />
              <span>MARKETPLACE MODULE</span>
            </div>
          </div>
          <span>AGENTVERSE v1.0.0</span>
        </div>
      </div>
    </div>
  );
}

function FeaturedCard({
  template,
  onLike,
}: {
  template: MarketplaceTemplateListItem;
  onLike: (id: string, e: React.MouseEvent) => void;
}) {
  return (
    <Link
      href={`/dashboard/marketplace/${template.slug}`}
      className="group bg-gradient-to-br from-yellow-500/10 to-transparent border border-yellow-500/20 p-4 hover:border-yellow-500/40 transition-all"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-yellow-400" />
          <span className="text-[10px] font-mono text-yellow-400 uppercase">Featured</span>
        </div>
        <div className="flex items-center gap-1">
          <Star className="w-3 h-3 text-yellow-400 fill-yellow-400" />
          <span className="text-xs font-mono text-white/60">
            {template.rating_average?.toFixed(1) || '-'}
          </span>
        </div>
      </div>
      <h3 className="text-sm font-mono font-bold text-white mb-1">{template.name}</h3>
      <p className="text-xs font-mono text-white/40 mb-3 line-clamp-2">
        {template.short_description}
      </p>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 text-[10px] font-mono text-white/30">
          <span className="flex items-center gap-1">
            <Users className="w-3 h-3" />
            {template.usage_count}
          </span>
          <span className="flex items-center gap-1">
            <TrendingUp className="w-3 h-3" />
            {template.like_count}
          </span>
        </div>
        <ArrowRight className="w-3 h-3 text-white/30 group-hover:text-yellow-400 transition-colors" />
      </div>
    </Link>
  );
}

function TemplateCard({
  template,
  onLike,
}: {
  template: MarketplaceTemplateListItem;
  onLike: (id: string, e: React.MouseEvent) => void;
}) {
  return (
    <Link
      href={`/dashboard/marketplace/${template.slug}`}
      className="group bg-black p-4 hover:bg-white/5 transition-colors"
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          {template.is_verified && (
            <CheckCircle className="w-3 h-3 text-green-400" />
          )}
          {template.is_featured && <Sparkles className="w-3 h-3 text-yellow-400" />}
          {template.is_premium && (
            <span className="text-[9px] font-mono bg-purple-500/20 text-purple-400 px-1">
              PRO
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          <Star className="w-3 h-3 text-yellow-400 fill-yellow-400" />
          <span className="text-xs font-mono text-white/60">
            {template.rating_average?.toFixed(1) || '-'}
          </span>
        </div>
      </div>

      <h3 className="text-sm font-mono font-medium text-white mb-1 line-clamp-1">
        {template.name}
      </h3>
      <p className="text-xs font-mono text-white/40 mb-3 line-clamp-2">
        {template.short_description}
      </p>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 text-[10px] font-mono text-white/30">
          <span>{template.category_name || 'General'}</span>
          <span className="flex items-center gap-1">
            <Users className="w-3 h-3" />
            {template.usage_count}
          </span>
        </div>
        <ArrowRight className="w-3 h-3 text-white/30 group-hover:text-white/60 transition-colors" />
      </div>
    </Link>
  );
}

function TemplateRow({
  template,
  onLike,
}: {
  template: MarketplaceTemplateListItem;
  onLike: (id: string, e: React.MouseEvent) => void;
}) {
  return (
    <Link
      href={`/dashboard/marketplace/${template.slug}`}
      className="flex items-center justify-between p-4 hover:bg-white/5 transition-colors"
    >
      <div className="flex items-center gap-4 flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-shrink-0">
          {template.is_verified && <CheckCircle className="w-3 h-3 text-green-400" />}
          {template.is_featured && <Sparkles className="w-3 h-3 text-yellow-400" />}
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-mono font-medium text-white truncate">
            {template.name}
          </h3>
          <p className="text-xs font-mono text-white/40 truncate">
            {template.short_description}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-6 flex-shrink-0">
        <span className="text-xs font-mono text-white/30">
          {template.category_name || 'General'}
        </span>
        <div className="flex items-center gap-1">
          <Star className="w-3 h-3 text-yellow-400 fill-yellow-400" />
          <span className="text-xs font-mono text-white/60">
            {template.rating_average?.toFixed(1) || '-'}
          </span>
        </div>
        <span className="text-xs font-mono text-white/30 flex items-center gap-1">
          <Users className="w-3 h-3" />
          {template.usage_count}
        </span>
        <ArrowRight className="w-3 h-3 text-white/30" />
      </div>
    </Link>
  );
}

function formatNumber(num: number): string {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M';
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K';
  }
  return String(num);
}
