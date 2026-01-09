'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  ArrowLeft,
  Star,
  Users,
  Calendar,
  CheckCircle,
  Sparkles,
  Heart,
  Share2,
  Play,
  Loader2,
  Terminal,
  Tag,
  TrendingUp,
  MessageSquare,
  User,
  ThumbsUp,
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import {
  useMarketplaceTemplate,
  useTemplateReviews,
  useToggleTemplateLike,
  useUseMarketplaceTemplate,
  useCreateTemplateReview,
  useProjects,
} from '@/hooks/useApi';
import { cn } from '@/lib/utils';
import type { TemplateReview, Project } from '@/lib/api';

export default function TemplateDetailPage() {
  const params = useParams();
  const router = useRouter();
  const slug = params.slug as string;

  const [showUseModal, setShowUseModal] = useState(false);
  const [showReviewForm, setShowReviewForm] = useState(false);

  const { data: template, isLoading } = useMarketplaceTemplate(slug);
  const { data: reviewsData } = useTemplateReviews(template?.id || '', { limit: 10 });
  const { data: projects } = useProjects();
  const toggleLike = useToggleTemplateLike();
  const useTemplate = useUseMarketplaceTemplate();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-white/40" />
      </div>
    );
  }

  if (!template) {
    return (
      <div className="min-h-screen bg-black p-6">
        <div className="text-center py-20">
          <p className="text-white/60 font-mono">Template not found</p>
          <Link href="/dashboard/marketplace">
            <Button variant="outline" size="sm" className="mt-4">
              Back to Marketplace
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  const reviews = reviewsData?.items || [];

  const handleLike = async () => {
    await toggleLike.mutateAsync(template.id);
  };

  const handleUse = async (data: {
    target_project_id?: string;
    name?: string;
    create_type: 'scenario' | 'product';
  }) => {
    await useTemplate.mutateAsync({
      templateId: template.id,
      data,
    });
    setShowUseModal(false);
    router.push('/dashboard/projects');
  };

  return (
    <div className="min-h-screen bg-black p-6">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <Link href="/dashboard/marketplace">
          <button className="p-2 hover:bg-white/5 transition-colors">
            <ArrowLeft className="w-4 h-4 text-white/60" />
          </button>
        </Link>
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-white/40" />
          <span className="text-xs font-mono text-white/40 uppercase tracking-wider">
            Marketplace / Template
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Template Info */}
          <div className="bg-white/5 border border-white/10 p-6">
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-2">
                {template.is_verified && (
                  <span className="flex items-center gap-1 text-[10px] font-mono text-green-400 bg-green-500/20 px-2 py-0.5">
                    <CheckCircle className="w-3 h-3" />
                    VERIFIED
                  </span>
                )}
                {template.is_featured && (
                  <span className="flex items-center gap-1 text-[10px] font-mono text-yellow-400 bg-yellow-500/20 px-2 py-0.5">
                    <Sparkles className="w-3 h-3" />
                    FEATURED
                  </span>
                )}
                {template.is_premium && (
                  <span className="text-[10px] font-mono text-purple-400 bg-purple-500/20 px-2 py-0.5">
                    PREMIUM
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleLike}
                  disabled={toggleLike.isPending}
                  className={cn(
                    'p-2 border transition-colors',
                    template.is_liked_by_user
                      ? 'border-red-500/50 bg-red-500/20 text-red-400'
                      : 'border-white/10 text-white/40 hover:bg-white/5'
                  )}
                >
                  <Heart
                    className={cn('w-4 h-4', template.is_liked_by_user && 'fill-current')}
                  />
                </button>
                <button className="p-2 border border-white/10 text-white/40 hover:bg-white/5 transition-colors">
                  <Share2 className="w-4 h-4" />
                </button>
              </div>
            </div>

            <h1 className="text-2xl font-mono font-bold text-white mb-2">
              {template.name}
            </h1>
            <p className="text-sm font-mono text-white/60 mb-4">
              {template.short_description}
            </p>

            <div className="flex items-center gap-4 text-xs font-mono text-white/40">
              <span className="flex items-center gap-1">
                <Tag className="w-3 h-3" />
                {template.category_name || 'General'}
              </span>
              <span className="flex items-center gap-1">
                <Users className="w-3 h-3" />
                {template.usage_count} uses
              </span>
              <span className="flex items-center gap-1">
                <Heart className="w-3 h-3" />
                {template.like_count} likes
              </span>
              <span className="flex items-center gap-1">
                <Calendar className="w-3 h-3" />
                {formatDistanceToNow(new Date(template.created_at), { addSuffix: true })}
              </span>
            </div>
          </div>

          {/* Description */}
          <div className="bg-white/5 border border-white/10 p-6">
            <h2 className="text-sm font-mono text-white/60 uppercase tracking-wider mb-4">
              Description
            </h2>
            <div className="prose prose-invert prose-sm max-w-none font-mono">
              <p className="text-white/70 whitespace-pre-wrap">
                {template.description || template.short_description}
              </p>
            </div>
          </div>

          {/* Tags */}
          {template.tags && template.tags.length > 0 && (
            <div className="bg-white/5 border border-white/10 p-6">
              <h2 className="text-sm font-mono text-white/60 uppercase tracking-wider mb-4">
                Tags
              </h2>
              <div className="flex flex-wrap gap-2">
                {template.tags.map((tag) => (
                  <span
                    key={tag}
                    className="text-xs font-mono text-white/60 bg-white/10 px-2 py-1"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Reviews */}
          <div className="bg-white/5 border border-white/10 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-mono text-white/60 uppercase tracking-wider">
                Reviews ({template.rating_count})
              </h2>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowReviewForm(!showReviewForm)}
                className="font-mono text-xs border-white/20 text-white/60 hover:bg-white/5 hover:text-white"
              >
                <MessageSquare className="w-3 h-3 mr-2" />
                WRITE REVIEW
              </Button>
            </div>

            {showReviewForm && (
              <ReviewForm
                templateId={template.id}
                onClose={() => setShowReviewForm(false)}
              />
            )}

            {reviews.length > 0 ? (
              <div className="space-y-4">
                {reviews.map((review: TemplateReview) => (
                  <ReviewCard key={review.id} review={review} />
                ))}
              </div>
            ) : (
              <p className="text-sm font-mono text-white/40 text-center py-8">
                No reviews yet. Be the first to review!
              </p>
            )}
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Use Template Card */}
          <div className="bg-white/5 border border-white/10 p-6">
            <div className="flex items-center gap-2 mb-4">
              <div className="flex">
                {[1, 2, 3, 4, 5].map((star) => (
                  <Star
                    key={star}
                    className={cn(
                      'w-4 h-4',
                      star <= Math.round(template.rating_average || 0)
                        ? 'text-yellow-400 fill-yellow-400'
                        : 'text-white/20'
                    )}
                  />
                ))}
              </div>
              <span className="text-sm font-mono text-white">
                {template.rating_average?.toFixed(1) || '0.0'}
              </span>
              <span className="text-xs font-mono text-white/40">
                ({template.rating_count} reviews)
              </span>
            </div>

            {template.is_premium && template.price_usd ? (
              <p className="text-2xl font-mono font-bold text-white mb-4">
                ${template.price_usd.toFixed(2)}
              </p>
            ) : (
              <p className="text-lg font-mono font-bold text-green-400 mb-4">
                FREE
              </p>
            )}

            <Button
              size="lg"
              className="w-full font-mono"
              onClick={() => setShowUseModal(true)}
            >
              <Play className="w-4 h-4 mr-2" />
              USE TEMPLATE
            </Button>

            <p className="text-[10px] font-mono text-white/40 text-center mt-3">
              {template.recommended_population_size} agents recommended
            </p>
          </div>

          {/* Author */}
          <div className="bg-white/5 border border-white/10 p-6">
            <h3 className="text-xs font-mono text-white/60 uppercase tracking-wider mb-3">
              Author
            </h3>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-white/10 flex items-center justify-center">
                <User className="w-5 h-5 text-white/40" />
              </div>
              <div>
                <p className="text-sm font-mono text-white">
                  {template.author_name || 'Anonymous'}
                </p>
                <p className="text-xs font-mono text-white/40">Template Creator</p>
              </div>
            </div>
          </div>

          {/* Stats */}
          <div className="bg-white/5 border border-white/10 p-6">
            <h3 className="text-xs font-mono text-white/60 uppercase tracking-wider mb-3">
              Statistics
            </h3>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono text-white/40 flex items-center gap-2">
                  <Users className="w-3 h-3" />
                  Total Uses
                </span>
                <span className="text-sm font-mono text-white">
                  {template.usage_count}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono text-white/40 flex items-center gap-2">
                  <Heart className="w-3 h-3" />
                  Likes
                </span>
                <span className="text-sm font-mono text-white">
                  {template.like_count}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono text-white/40 flex items-center gap-2">
                  <MessageSquare className="w-3 h-3" />
                  Reviews
                </span>
                <span className="text-sm font-mono text-white">
                  {template.rating_count}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono text-white/40 flex items-center gap-2">
                  <TrendingUp className="w-3 h-3" />
                  Scenario Type
                </span>
                <span className="text-sm font-mono text-white uppercase">
                  {template.scenario_type}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Use Template Modal */}
      {showUseModal && (
        <UseTemplateModal
          template={template}
          projects={projects || []}
          onUse={handleUse}
          onClose={() => setShowUseModal(false)}
          isLoading={useTemplate.isPending}
        />
      )}

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

function ReviewCard({ review }: { review: TemplateReview }) {
  return (
    <div className="border-b border-white/5 pb-4 last:border-0">
      <div className="flex items-center gap-3 mb-2">
        <div className="w-8 h-8 bg-white/10 flex items-center justify-center">
          <User className="w-4 h-4 text-white/40" />
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-mono text-white">
              {review.user_name || 'Anonymous'}
            </span>
            {review.is_verified_purchase && (
              <CheckCircle className="w-3 h-3 text-green-400" />
            )}
          </div>
          <div className="flex items-center gap-2">
            <div className="flex">
              {[1, 2, 3, 4, 5].map((star) => (
                <Star
                  key={star}
                  className={cn(
                    'w-3 h-3',
                    star <= review.rating
                      ? 'text-yellow-400 fill-yellow-400'
                      : 'text-white/20'
                  )}
                />
              ))}
            </div>
            <span className="text-[10px] font-mono text-white/40">
              {formatDistanceToNow(new Date(review.created_at), { addSuffix: true })}
            </span>
          </div>
        </div>
      </div>

      {review.title && (
        <h4 className="text-sm font-mono font-medium text-white mb-1">
          {review.title}
        </h4>
      )}
      {review.content && (
        <p className="text-xs font-mono text-white/60">{review.content}</p>
      )}

      <div className="flex items-center gap-2 mt-2">
        <button className="text-[10px] font-mono text-white/40 flex items-center gap-1 hover:text-white/60">
          <ThumbsUp className="w-3 h-3" />
          Helpful ({review.is_helpful_count})
        </button>
      </div>
    </div>
  );
}

function ReviewForm({
  templateId,
  onClose,
}: {
  templateId: string;
  onClose: () => void;
}) {
  const [rating, setRating] = useState(0);
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const createReview = useCreateTemplateReview();

  const handleSubmit = async () => {
    if (rating === 0) return;
    await createReview.mutateAsync({
      templateId,
      data: { rating, title: title || undefined, content: content || undefined },
    });
    onClose();
  };

  return (
    <div className="mb-6 p-4 bg-white/5 border border-white/10">
      <div className="mb-4">
        <label className="block text-xs font-mono text-white/60 mb-2">
          Your Rating *
        </label>
        <div className="flex gap-1">
          {[1, 2, 3, 4, 5].map((star) => (
            <button
              key={star}
              onClick={() => setRating(star)}
              className="p-1 hover:scale-110 transition-transform"
            >
              <Star
                className={cn(
                  'w-5 h-5',
                  star <= rating
                    ? 'text-yellow-400 fill-yellow-400'
                    : 'text-white/20'
                )}
              />
            </button>
          ))}
        </div>
      </div>

      <div className="mb-4">
        <label className="block text-xs font-mono text-white/60 mb-2">
          Title (optional)
        </label>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Summarize your experience"
          className="w-full px-3 py-2 bg-white/5 border border-white/10 text-sm font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-white/30"
        />
      </div>

      <div className="mb-4">
        <label className="block text-xs font-mono text-white/60 mb-2">
          Review (optional)
        </label>
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Share your experience with this template..."
          rows={3}
          className="w-full px-3 py-2 bg-white/5 border border-white/10 text-sm font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-white/30 resize-none"
        />
      </div>

      <div className="flex justify-end gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={onClose}
          className="font-mono text-xs border-white/20 text-white/60 hover:bg-white/5 hover:text-white"
        >
          CANCEL
        </Button>
        <Button
          size="sm"
          onClick={handleSubmit}
          disabled={rating === 0 || createReview.isPending}
        >
          {createReview.isPending ? 'SUBMITTING...' : 'SUBMIT REVIEW'}
        </Button>
      </div>
    </div>
  );
}

function UseTemplateModal({
  template,
  projects,
  onUse,
  onClose,
  isLoading,
}: {
  template: any;
  projects: Project[];
  onUse: (data: any) => void;
  onClose: () => void;
  isLoading: boolean;
}) {
  const [createNew, setCreateNew] = useState(true);
  const [selectedProject, setSelectedProject] = useState('');
  const [customName, setCustomName] = useState('');
  const [createType, setCreateType] = useState<'scenario' | 'product'>('scenario');

  const handleSubmit = () => {
    onUse({
      target_project_id: createNew ? undefined : selectedProject,
      name: customName || undefined,
      create_type: createType,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/80" onClick={onClose} />
      <div className="relative bg-black border border-white/20 max-w-lg w-full p-6">
        <h2 className="text-lg font-mono font-bold text-white mb-4">
          Use Template
        </h2>

        <div className="mb-6 p-4 bg-white/5 border border-white/10">
          <h3 className="text-sm font-mono font-medium text-white mb-1">
            {template.name}
          </h3>
          <p className="text-xs font-mono text-white/40">
            {template.short_description}
          </p>
          <p className="text-[10px] font-mono text-white/30 mt-2">
            {template.recommended_population_size} agents recommended
          </p>
        </div>

        <div className="space-y-4 mb-6">
          <div>
            <label className="block text-xs font-mono text-white/60 mb-2">
              Create As
            </label>
            <div className="flex gap-2">
              <button
                onClick={() => setCreateType('scenario')}
                className={cn(
                  'flex-1 py-2 text-xs font-mono border transition-colors',
                  createType === 'scenario'
                    ? 'border-white/40 bg-white/10 text-white'
                    : 'border-white/10 text-white/40 hover:bg-white/5'
                )}
              >
                SCENARIO
              </button>
              <button
                onClick={() => setCreateType('product')}
                className={cn(
                  'flex-1 py-2 text-xs font-mono border transition-colors',
                  createType === 'product'
                    ? 'border-white/40 bg-white/10 text-white'
                    : 'border-white/10 text-white/40 hover:bg-white/5'
                )}
              >
                PRODUCT
              </button>
            </div>
          </div>

          <div>
            <label className="block text-xs font-mono text-white/60 mb-2">
              Target Project
            </label>
            <div className="space-y-2">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  checked={createNew}
                  onChange={() => setCreateNew(true)}
                  className="accent-white"
                />
                <span className="text-xs font-mono text-white/60">
                  Create new project
                </span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  checked={!createNew}
                  onChange={() => setCreateNew(false)}
                  className="accent-white"
                />
                <span className="text-xs font-mono text-white/60">
                  Add to existing project
                </span>
              </label>
            </div>

            {!createNew && (
              <select
                value={selectedProject}
                onChange={(e) => setSelectedProject(e.target.value)}
                className="mt-2 w-full px-3 py-2 bg-white/5 border border-white/10 text-sm font-mono text-white focus:outline-none focus:border-white/30"
              >
                <option value="">Select project...</option>
                {projects.map((project) => (
                  <option key={project.id} value={project.id}>
                    {project.name}
                  </option>
                ))}
              </select>
            )}
          </div>

          <div>
            <label className="block text-xs font-mono text-white/60 mb-2">
              Custom Name (optional)
            </label>
            <input
              type="text"
              value={customName}
              onChange={(e) => setCustomName(e.target.value)}
              placeholder={`${template.name} (Copy)`}
              className="w-full px-3 py-2 bg-white/5 border border-white/10 text-sm font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-white/30"
            />
          </div>
        </div>

        <div className="flex justify-end gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={onClose}
            className="font-mono text-xs border-white/20 text-white/60 hover:bg-white/5 hover:text-white"
          >
            CANCEL
          </Button>
          <Button
            size="sm"
            onClick={handleSubmit}
            disabled={isLoading || (!createNew && !selectedProject)}
          >
            {isLoading ? 'CREATING...' : 'USE TEMPLATE'}
          </Button>
        </div>
      </div>
    </div>
  );
}
