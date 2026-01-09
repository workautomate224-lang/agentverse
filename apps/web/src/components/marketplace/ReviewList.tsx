'use client';

import { useState } from 'react';
import { formatDistanceToNow } from 'date-fns';
import { ThumbsUp, CheckCircle, User } from 'lucide-react';
import { TemplateReview } from '@/lib/api';
import { RatingStars, RatingDistribution } from './RatingStars';

interface ReviewListProps {
  reviews: TemplateReview[];
  averageRating: number;
  totalReviews: number;
  ratingDistribution: Record<number, number>;
  loading?: boolean;
  onHelpful?: (reviewId: string) => void;
  currentUserId?: string;
}

export function ReviewList({
  reviews,
  averageRating,
  totalReviews,
  ratingDistribution,
  loading = false,
  onHelpful,
  currentUserId,
}: ReviewListProps) {
  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="border-b border-gray-100 pb-6">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 bg-gray-200 rounded-full" />
              <div className="space-y-2">
                <div className="h-4 bg-gray-200 rounded w-24" />
                <div className="h-3 bg-gray-200 rounded w-32" />
              </div>
            </div>
            <div className="h-4 bg-gray-200 rounded w-3/4" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div>
      {/* Summary section */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8 pb-8 border-b border-gray-200">
        {/* Average rating */}
        <div className="text-center md:text-left">
          <div className="text-5xl font-bold text-gray-900 mb-2">
            {averageRating.toFixed(1)}
          </div>
          <RatingStars rating={averageRating} size="lg" />
          <p className="text-sm text-gray-500 mt-2">
            Based on {totalReviews} reviews
          </p>
        </div>

        {/* Distribution */}
        <RatingDistribution
          distribution={ratingDistribution}
          total={totalReviews}
        />
      </div>

      {/* Reviews list */}
      {reviews.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg">
          <p className="text-gray-500">No reviews yet. Be the first to review!</p>
        </div>
      ) : (
        <div className="space-y-6">
          {reviews.map((review) => (
            <ReviewItem
              key={review.id}
              review={review}
              onHelpful={onHelpful}
              isCurrentUser={currentUserId === review.user_id}
            />
          ))}
        </div>
      )}
    </div>
  );
}

interface ReviewItemProps {
  review: TemplateReview;
  onHelpful?: (reviewId: string) => void;
  isCurrentUser?: boolean;
}

function ReviewItem({ review, onHelpful, isCurrentUser }: ReviewItemProps) {
  return (
    <div className="border-b border-gray-100 pb-6 last:border-0">
      <div className="flex items-start gap-4">
        {/* Avatar */}
        <div className="w-10 h-10 rounded-full bg-primary-100 flex items-center justify-center flex-shrink-0">
          <User className="w-5 h-5 text-primary-600" />
        </div>

        <div className="flex-1 min-w-0">
          {/* Header */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-medium text-gray-900">
              {review.user_name || 'Anonymous'}
            </span>
            {review.is_verified_purchase && (
              <span className="inline-flex items-center gap-1 text-xs text-green-600">
                <CheckCircle className="w-3 h-3" />
                Verified User
              </span>
            )}
            {isCurrentUser && (
              <span className="text-xs text-primary-600 bg-primary-50 px-2 py-0.5 rounded">
                Your Review
              </span>
            )}
          </div>

          {/* Rating and date */}
          <div className="flex items-center gap-2 mt-1">
            <RatingStars rating={review.rating} size="sm" />
            <span className="text-xs text-gray-400">
              {formatDistanceToNow(new Date(review.created_at), {
                addSuffix: true,
              })}
            </span>
          </div>

          {/* Title */}
          {review.title && (
            <h4 className="font-medium text-gray-900 mt-3">{review.title}</h4>
          )}

          {/* Content */}
          {review.content && (
            <p className="text-gray-600 mt-2 text-sm leading-relaxed">
              {review.content}
            </p>
          )}

          {/* Helpful button */}
          {onHelpful && !isCurrentUser && (
            <button
              onClick={() => onHelpful(review.id)}
              className="mt-3 inline-flex items-center gap-1 text-sm text-gray-500 hover:text-primary-600 transition-colors"
            >
              <ThumbsUp className="w-4 h-4" />
              <span>
                Helpful ({review.is_helpful_count})
              </span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

interface ReviewFormProps {
  rating: number;
  onRatingChange: (rating: number) => void;
  title: string;
  onTitleChange: (title: string) => void;
  content: string;
  onContentChange: (content: string) => void;
  onSubmit: () => void;
  onCancel?: () => void;
  isSubmitting?: boolean;
  isEdit?: boolean;
}

export function ReviewForm({
  rating,
  onRatingChange,
  title,
  onTitleChange,
  content,
  onContentChange,
  onSubmit,
  onCancel,
  isSubmitting = false,
  isEdit = false,
}: ReviewFormProps) {
  return (
    <div className="bg-gray-50 rounded-lg p-6">
      <h3 className="font-semibold text-gray-900 mb-4">
        {isEdit ? 'Edit Your Review' : 'Write a Review'}
      </h3>

      {/* Rating */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Your Rating *
        </label>
        <RatingStars
          rating={rating}
          size="lg"
          interactive
          onChange={onRatingChange}
        />
      </div>

      {/* Title */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Review Title (optional)
        </label>
        <input
          type="text"
          value={title}
          onChange={(e) => onTitleChange(e.target.value)}
          placeholder="Summarize your experience"
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-100 focus:border-primary-500"
        />
      </div>

      {/* Content */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Review Content (optional)
        </label>
        <textarea
          value={content}
          onChange={(e) => onContentChange(e.target.value)}
          placeholder="Share your experience with this template..."
          rows={4}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-100 focus:border-primary-500 resize-none"
        />
      </div>

      {/* Buttons */}
      <div className="flex justify-end gap-3">
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
          >
            Cancel
          </button>
        )}
        <button
          type="button"
          onClick={onSubmit}
          disabled={isSubmitting || rating === 0}
          className="px-4 py-2 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSubmitting ? 'Submitting...' : isEdit ? 'Update Review' : 'Submit Review'}
        </button>
      </div>
    </div>
  );
}

export default ReviewList;
