'use client';

import { Star } from 'lucide-react';
import { useState } from 'react';

interface RatingStarsProps {
  rating: number;
  maxRating?: number;
  size?: 'sm' | 'md' | 'lg';
  showValue?: boolean;
  count?: number;
  interactive?: boolean;
  onChange?: (rating: number) => void;
}

const sizeClasses = {
  sm: 'w-3 h-3',
  md: 'w-4 h-4',
  lg: 'w-5 h-5',
};

export function RatingStars({
  rating,
  maxRating = 5,
  size = 'md',
  showValue = false,
  count,
  interactive = false,
  onChange,
}: RatingStarsProps) {
  const [hoverRating, setHoverRating] = useState(0);

  const displayRating = hoverRating || rating;

  return (
    <div className="flex items-center gap-1">
      <div className="flex">
        {[...Array(maxRating)].map((_, i) => {
          const starValue = i + 1;
          const isFilled = starValue <= Math.floor(displayRating);
          const isHalfFilled =
            !isFilled &&
            starValue === Math.ceil(displayRating) &&
            displayRating % 1 !== 0;

          return (
            <button
              key={i}
              type="button"
              disabled={!interactive}
              className={`${interactive ? 'cursor-pointer' : 'cursor-default'} p-0.5 transition-transform ${
                interactive ? 'hover:scale-110' : ''
              }`}
              onClick={() => interactive && onChange?.(starValue)}
              onMouseEnter={() => interactive && setHoverRating(starValue)}
              onMouseLeave={() => interactive && setHoverRating(0)}
            >
              {isHalfFilled ? (
                <div className="relative">
                  <Star className={`${sizeClasses[size]} text-gray-300`} />
                  <div className="absolute inset-0 overflow-hidden w-1/2">
                    <Star
                      className={`${sizeClasses[size]} text-yellow-400 fill-yellow-400`}
                    />
                  </div>
                </div>
              ) : (
                <Star
                  className={`${sizeClasses[size]} ${
                    isFilled
                      ? 'text-yellow-400 fill-yellow-400'
                      : 'text-gray-300'
                  }`}
                />
              )}
            </button>
          );
        })}
      </div>
      {showValue && (
        <span className="text-sm text-gray-600 ml-1">
          {rating.toFixed(1)}
          {count !== undefined && (
            <span className="text-gray-400"> ({count})</span>
          )}
        </span>
      )}
    </div>
  );
}

interface RatingDistributionProps {
  distribution: Record<number, number>;
  total: number;
}

export function RatingDistribution({ distribution, total }: RatingDistributionProps) {
  return (
    <div className="space-y-2">
      {[5, 4, 3, 2, 1].map((rating) => {
        const count = distribution[rating] || 0;
        const percentage = total > 0 ? (count / total) * 100 : 0;

        return (
          <div key={rating} className="flex items-center gap-2">
            <span className="text-sm text-gray-600 w-8">{rating} star</span>
            <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-yellow-400 rounded-full transition-all duration-500"
                style={{ width: `${percentage}%` }}
              />
            </div>
            <span className="text-sm text-gray-500 w-10 text-right">{count}</span>
          </div>
        );
      })}
    </div>
  );
}

export default RatingStars;
