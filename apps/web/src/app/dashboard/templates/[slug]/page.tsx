'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  LayoutTemplate,
  ArrowLeft,
  Star,
  Users,
  Calendar,
  User,
  Copy,
  Upload,
  LinkIcon,
  CheckCircle,
  Sparkles,
  Loader2,
  AlertCircle,
  FileCode,
  ChevronDown,
  ChevronUp,
  ThumbsUp,
  MessageSquare,
  Send,
  Heart,
  Terminal,
  RefreshCw,
  ExternalLink,
  Settings,
} from 'lucide-react';
import {
  useMarketplaceTemplate,
  useTemplateReviews,
  useUseMarketplaceTemplate,
  useToggleTemplateLike,
  useCreateTemplateReview,
  useProjects,
} from '@/hooks/useApi';
import { cn } from '@/lib/utils';
import type { TemplateReview, Project } from '@/lib/api';

/**
 * Template Detail Page
 * Per Interaction_design.md §5.6:
 * - Template info with domain, compatibility badges
 * - Clone, Publish Version, Attach to Project buttons
 * - Reviews section
 */
export default function TemplateDetailPage() {
  const params = useParams();
  const router = useRouter();
  const slug = params.slug as string;

  const [showAttachDialog, setShowAttachDialog] = useState(false);
  const [selectedProject, setSelectedProject] = useState<string | null>(null);
  const [showReviewForm, setShowReviewForm] = useState(false);
  const [reviewRating, setReviewRating] = useState(5);
  const [reviewTitle, setReviewTitle] = useState('');
  const [reviewContent, setReviewContent] = useState('');
  const [showFullDescription, setShowFullDescription] = useState(false);

  const { data: template, isLoading, error, refetch } = useMarketplaceTemplate(slug);
  const { data: reviewsData, isLoading: loadingReviews } = useTemplateReviews(
    template?.id || '',
    { limit: 10 }
  );
  const { data: projectsData } = useProjects();
  const useTemplateMutation = useUseMarketplaceTemplate();
  const toggleLikeMutation = useToggleTemplateLike();
  const createReviewMutation = useCreateTemplateReview();

  const reviews = reviewsData?.items || [];
  const projects: Project[] = projectsData || [];

  const handleClone = () => {
    if (!template) return;
    useTemplateMutation.mutate(
      { templateId: template.id, data: { create_type: 'scenario' } },
      {
        onSuccess: (result) => {
          router.push(`/dashboard/projects/${result.created_id}`);
        },
      }
    );
  };

  const handleAttachToProject = () => {
    if (!template || !selectedProject) return;
    useTemplateMutation.mutate(
      {
        templateId: template.id,
        data: { target_project_id: selectedProject, create_type: 'scenario' },
      },
      {
        onSuccess: () => {
          setShowAttachDialog(false);
          setSelectedProject(null);
          router.push(`/dashboard/projects/${selectedProject}`);
        },
      }
    );
  };

  const handleToggleLike = () => {
    if (!template) return;
    toggleLikeMutation.mutate(template.id);
  };

  const handleSubmitReview = () => {
    if (!template) return;
    createReviewMutation.mutate(
      {
        templateId: template.id,
        data: {
          rating: reviewRating,
          title: reviewTitle || undefined,
          content: reviewContent || undefined,
        },
      },
      {
        onSuccess: () => {
          setShowReviewForm(false);
          setReviewRating(5);
          setReviewTitle('');
          setReviewContent('');
        },
      }
    );
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-black p-6 flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-white/40" />
      </div>
    );
  }

  if (error || !template) {
    return (
      <div className="min-h-screen bg-black p-6">
        <div className="max-w-2xl mx-auto text-center py-16">
          <AlertCircle className="w-10 h-10 text-red-400 mx-auto mb-4" />
          <h1 className="text-xl font-mono font-bold text-white mb-2">Template Not Found</h1>
          <p className="text-sm font-mono text-white/50 mb-6">
            The template you are looking for does not exist or has been removed.
          </p>
          <Link href="/dashboard/templates">
            <Button variant="outline" className="font-mono text-xs">
              <ArrowLeft className="w-3 h-3 mr-2" />
              BACK TO TEMPLATES
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black p-6">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <Link href="/dashboard/templates">
          <Button
            variant="outline"
            size="sm"
            className="font-mono text-xs border-white/20 text-white/60 hover:bg-white/5 hover:text-white"
          >
            <ArrowLeft className="w-3 h-3 mr-2" />
            TEMPLATES
          </Button>
        </Link>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Template Header */}
          <div className="bg-white/5 border border-white/10 p-6">
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                {template.is_verified && (
                  <div className="flex items-center gap-1 text-green-400">
                    <CheckCircle className="w-4 h-4" />
                    <span className="text-[10px] font-mono uppercase">Verified</span>
                  </div>
                )}
                {template.is_featured && (
                  <div className="flex items-center gap-1 text-yellow-400">
                    <Sparkles className="w-4 h-4" />
                    <span className="text-[10px] font-mono uppercase">Featured</span>
                  </div>
                )}
                {template.is_premium && (
                  <span className="text-[10px] font-mono bg-purple-500/20 text-purple-400 px-2 py-0.5">
                    PRO
                  </span>
                )}
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleToggleLike}
                disabled={toggleLikeMutation.isPending}
                className={cn(
                  'font-mono text-xs',
                  template.is_liked_by_user ? 'text-red-400' : 'text-white/40 hover:text-red-400'
                )}
              >
                <Heart
                  className={cn('w-4 h-4 mr-1', template.is_liked_by_user && 'fill-current')}
                />
                {template.like_count || 0}
              </Button>
            </div>

            <h1 className="text-2xl font-mono font-bold text-white mb-2">{template.name}</h1>
            <p className="text-sm font-mono text-white/50 mb-4">
              {template.short_description}
            </p>

            {/* Stats Row */}
            <div className="flex items-center gap-6 text-sm font-mono text-white/40">
              <div className="flex items-center gap-1">
                <Star className="w-4 h-4 text-yellow-400 fill-yellow-400" />
                <span className="text-white">
                  {template.rating_average?.toFixed(1) || '-'}
                </span>
                <span className="text-white/30">({template.rating_count || 0})</span>
              </div>
              <div className="flex items-center gap-1">
                <Users className="w-4 h-4" />
                <span>{template.usage_count} uses</span>
              </div>
              <div className="flex items-center gap-1">
                <Calendar className="w-4 h-4" />
                <span>{new Date(template.created_at).toLocaleDateString()}</span>
              </div>
            </div>
          </div>

          {/* Description */}
          <div className="bg-white/5 border border-white/10 p-6">
            <h2 className="text-sm font-mono font-bold text-white mb-4 flex items-center gap-2">
              <FileCode className="w-4 h-4 text-white/40" />
              DESCRIPTION
            </h2>
            <div
              className={cn(
                'text-sm font-mono text-white/70 whitespace-pre-wrap',
                !showFullDescription && 'line-clamp-6'
              )}
            >
              {template.description || template.short_description}
            </div>
            {template.description && template.description.length > 400 && (
              <button
                onClick={() => setShowFullDescription(!showFullDescription)}
                className="flex items-center gap-1 text-xs font-mono text-cyan-400 mt-3 hover:text-cyan-300"
              >
                {showFullDescription ? (
                  <>
                    <ChevronUp className="w-3 h-3" />
                    Show Less
                  </>
                ) : (
                  <>
                    <ChevronDown className="w-3 h-3" />
                    Show More
                  </>
                )}
              </button>
            )}
          </div>

          {/* Tags */}
          {template.tags && template.tags.length > 0 && (
            <div className="bg-white/5 border border-white/10 p-6">
              <h2 className="text-sm font-mono font-bold text-white mb-4">TAGS</h2>
              <div className="flex flex-wrap gap-2">
                {template.tags.map((tag) => (
                  <span
                    key={tag}
                    className="text-xs font-mono px-2 py-1 bg-white/10 text-white/60 border border-white/10"
                  >
                    #{tag}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Reviews */}
          <div className="bg-white/5 border border-white/10 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-mono font-bold text-white flex items-center gap-2">
                <MessageSquare className="w-4 h-4 text-white/40" />
                REVIEWS ({template.rating_count || 0})
              </h2>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowReviewForm(!showReviewForm)}
                className="font-mono text-xs border-white/20 text-white/60 hover:bg-white/5 hover:text-white"
              >
                WRITE REVIEW
              </Button>
            </div>

            {/* Review Form */}
            {showReviewForm && (
              <div className="border border-white/10 p-4 mb-4 bg-black/50">
                <div className="flex items-center gap-2 mb-4">
                  <span className="text-xs font-mono text-white/50">Rating:</span>
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button
                      key={star}
                      onClick={() => setReviewRating(star)}
                      className="p-0.5"
                    >
                      <Star
                        className={cn(
                          'w-5 h-5 transition-colors',
                          star <= reviewRating
                            ? 'text-yellow-400 fill-yellow-400'
                            : 'text-white/20'
                        )}
                      />
                    </button>
                  ))}
                </div>
                <input
                  type="text"
                  placeholder="Review title (optional)"
                  value={reviewTitle}
                  onChange={(e) => setReviewTitle(e.target.value)}
                  className="w-full px-3 py-2 bg-white/5 border border-white/10 text-sm font-mono text-white placeholder:text-white/30 mb-3 focus:outline-none focus:border-white/30"
                />
                <textarea
                  placeholder="Write your review..."
                  value={reviewContent}
                  onChange={(e) => setReviewContent(e.target.value)}
                  rows={3}
                  className="w-full px-3 py-2 bg-white/5 border border-white/10 text-sm font-mono text-white placeholder:text-white/30 resize-none mb-3 focus:outline-none focus:border-white/30"
                />
                <div className="flex justify-end gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowReviewForm(false)}
                    className="font-mono text-xs text-white/50"
                  >
                    CANCEL
                  </Button>
                  <Button
                    size="sm"
                    onClick={handleSubmitReview}
                    disabled={createReviewMutation.isPending}
                    className="font-mono text-xs"
                  >
                    {createReviewMutation.isPending ? (
                      <Loader2 className="w-3 h-3 animate-spin mr-2" />
                    ) : (
                      <Send className="w-3 h-3 mr-2" />
                    )}
                    SUBMIT
                  </Button>
                </div>
              </div>
            )}

            {/* Reviews List */}
            {loadingReviews ? (
              <div className="py-8 flex justify-center">
                <Loader2 className="w-5 h-5 animate-spin text-white/40" />
              </div>
            ) : reviews.length > 0 ? (
              <div className="space-y-4">
                {reviews.map((review) => (
                  <ReviewCard key={review.id} review={review} />
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <MessageSquare className="w-8 h-8 text-white/20 mx-auto mb-2" />
                <p className="text-sm font-mono text-white/40">No reviews yet</p>
                <p className="text-xs font-mono text-white/30">Be the first to review</p>
              </div>
            )}
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Action Buttons */}
          <div className="bg-white/5 border border-white/10 p-6">
            <div className="space-y-3">
              <Button
                onClick={handleClone}
                disabled={useTemplateMutation.isPending}
                className="w-full font-mono text-xs"
              >
                {useTemplateMutation.isPending ? (
                  <Loader2 className="w-3 h-3 animate-spin mr-2" />
                ) : (
                  <Copy className="w-3 h-3 mr-2" />
                )}
                CLONE TEMPLATE
              </Button>

              <Button
                variant="outline"
                onClick={() => setShowAttachDialog(!showAttachDialog)}
                className="w-full font-mono text-xs border-white/20 text-white/60 hover:bg-white/5 hover:text-white"
              >
                <LinkIcon className="w-3 h-3 mr-2" />
                ATTACH TO PROJECT
              </Button>

              {template.author_id && (
                <Button
                  variant="outline"
                  onClick={() => router.push(`/dashboard/templates/${slug}/edit`)}
                  className="w-full font-mono text-xs border-white/20 text-white/60 hover:bg-white/5 hover:text-white"
                >
                  <Settings className="w-3 h-3 mr-2" />
                  EDIT / PUBLISH VERSION
                </Button>
              )}
            </div>

            {/* Attach Dialog */}
            {showAttachDialog && (
              <div className="mt-4 border border-white/10 p-4 bg-black/50">
                <p className="text-xs font-mono text-white/50 mb-3">Select a project:</p>
                {projects.length > 0 ? (
                  <>
                    <div className="max-h-40 overflow-y-auto space-y-1 mb-3">
                      {projects.map((project) => (
                        <button
                          key={project.id}
                          onClick={() => setSelectedProject(project.id)}
                          className={cn(
                            'w-full text-left px-3 py-2 text-xs font-mono transition-colors',
                            selectedProject === project.id
                              ? 'bg-cyan-500/20 border-cyan-500/50 text-cyan-400'
                              : 'bg-white/5 hover:bg-white/10 text-white/60'
                          )}
                        >
                          {project.name}
                        </button>
                      ))}
                    </div>
                    <Button
                      size="sm"
                      onClick={handleAttachToProject}
                      disabled={!selectedProject || useTemplateMutation.isPending}
                      className="w-full font-mono text-xs"
                    >
                      {useTemplateMutation.isPending ? (
                        <Loader2 className="w-3 h-3 animate-spin mr-2" />
                      ) : (
                        <ExternalLink className="w-3 h-3 mr-2" />
                      )}
                      ATTACH
                    </Button>
                  </>
                ) : (
                  <p className="text-xs font-mono text-white/30">No projects available</p>
                )}
              </div>
            )}
          </div>

          {/* Template Info */}
          <div className="bg-white/5 border border-white/10 p-6">
            <h3 className="text-xs font-mono text-white/40 uppercase tracking-wider mb-4">
              DETAILS
            </h3>
            <div className="space-y-3 text-sm font-mono">
              <div className="flex justify-between">
                <span className="text-white/40">Category</span>
                <span className="text-white">{template.category_name || 'General'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-white/40">Type</span>
                <span className="text-white capitalize">
                  {template.scenario_type || 'Template'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-white/40">Version</span>
                <span className="text-white">{template.version || '1.0.0'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-white/40">Author</span>
                <span className="text-white flex items-center gap-1">
                  <User className="w-3 h-3" />
                  {template.author_name || 'Unknown'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-white/40">Updated</span>
                <span className="text-white">
                  {new Date(template.updated_at).toLocaleDateString()}
                </span>
              </div>
            </div>
          </div>

          {/* Compatibility */}
          <div className="bg-white/5 border border-white/10 p-6">
            <h3 className="text-xs font-mono text-white/40 uppercase tracking-wider mb-4">
              COMPATIBILITY
            </h3>
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-green-400" />
                <span className="text-sm font-mono text-white/60">Society Mode</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-green-400" />
                <span className="text-sm font-mono text-white/60">Target Mode</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-green-400" />
                <span className="text-sm font-mono text-white/60">Reliability Reports</span>
              </div>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="bg-white/5 border border-white/10 p-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => refetch()}
              className="w-full font-mono text-xs text-white/40 hover:text-white"
            >
              <RefreshCw className="w-3 h-3 mr-2" />
              REFRESH
            </Button>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-8 pt-4 border-t border-white/5">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1">
              <Terminal className="w-3 h-3" />
              <span>TEMPLATE DETAIL</span>
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
    <div className="border border-white/5 p-4 bg-black/30">
      <div className="flex items-start justify-between mb-2">
        <div>
          <div className="flex items-center gap-2 mb-1">
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
            {review.title && (
              <span className="text-sm font-mono font-medium text-white">
                {review.title}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2 text-[10px] font-mono text-white/30">
            <User className="w-3 h-3" />
            <span>{review.user_name || 'Anonymous'}</span>
            <span>•</span>
            <span>{new Date(review.created_at).toLocaleDateString()}</span>
          </div>
        </div>
        {review.is_helpful_count > 0 && (
          <div className="flex items-center gap-1 text-[10px] font-mono text-white/30">
            <ThumbsUp className="w-3 h-3" />
            <span>{review.is_helpful_count}</span>
          </div>
        )}
      </div>
      {review.content && (
        <p className="text-sm font-mono text-white/60">{review.content}</p>
      )}
    </div>
  );
}
