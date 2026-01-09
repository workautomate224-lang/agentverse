'use client';

import {
  memo,
  useCallback,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { cn } from '@/lib/utils';
import { Skeleton } from './skeleton';

/**
 * VirtualizedList - Renders only visible items for performance
 * Uses IntersectionObserver for visibility detection
 * Supports infinite scroll with loadMore callback
 */

interface VirtualizedListProps<T> {
  /** Data items to render */
  items: T[];
  /** Key extractor for React reconciliation */
  keyExtractor: (item: T, index: number) => string;
  /** Render function for each item */
  renderItem: (item: T, index: number) => ReactNode;
  /** Estimated height of each item in pixels */
  estimatedItemHeight: number;
  /** Number of items to render above/below viewport */
  overscan?: number;
  /** Container className */
  className?: string;
  /** Loading state */
  isLoading?: boolean;
  /** Load more callback for infinite scroll */
  onLoadMore?: () => void;
  /** Whether there are more items to load */
  hasMore?: boolean;
  /** Skeleton count while loading */
  skeletonCount?: number;
  /** Custom skeleton render function */
  renderSkeleton?: () => ReactNode;
  /** Empty state content */
  emptyContent?: ReactNode;
}

export const VirtualizedList = memo(function VirtualizedList<T>({
  items,
  keyExtractor,
  renderItem,
  estimatedItemHeight,
  overscan = 5,
  className,
  isLoading = false,
  onLoadMore,
  hasMore = false,
  skeletonCount = 5,
  renderSkeleton,
  emptyContent,
}: VirtualizedListProps<T>) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [visibleRange, setVisibleRange] = useState({ start: 0, end: 20 });
  const loadMoreRef = useRef<HTMLDivElement>(null);

  // Calculate visible range based on scroll position
  const updateVisibleRange = useCallback(() => {
    if (!containerRef.current) return;

    const container = containerRef.current;
    const scrollTop = container.scrollTop;
    const clientHeight = container.clientHeight;

    const startIndex = Math.max(0, Math.floor(scrollTop / estimatedItemHeight) - overscan);
    const visibleCount = Math.ceil(clientHeight / estimatedItemHeight);
    const endIndex = Math.min(items.length, startIndex + visibleCount + overscan * 2);

    setVisibleRange({ start: startIndex, end: endIndex });
  }, [items.length, estimatedItemHeight, overscan]);

  // Setup scroll listener
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    container.addEventListener('scroll', updateVisibleRange);
    updateVisibleRange();

    return () => {
      container.removeEventListener('scroll', updateVisibleRange);
    };
  }, [updateVisibleRange]);

  // Setup IntersectionObserver for infinite scroll
  useEffect(() => {
    if (!onLoadMore || !hasMore || isLoading) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) {
          onLoadMore();
        }
      },
      { threshold: 0.1 }
    );

    const loadMoreElement = loadMoreRef.current;
    if (loadMoreElement) {
      observer.observe(loadMoreElement);
    }

    return () => {
      if (loadMoreElement) {
        observer.unobserve(loadMoreElement);
      }
    };
  }, [onLoadMore, hasMore, isLoading]);

  // Empty state
  if (!isLoading && items.length === 0) {
    return (
      <div className={cn('flex items-center justify-center py-12 text-white/40', className)}>
        {emptyContent || 'No items'}
      </div>
    );
  }

  // Loading state
  if (isLoading && items.length === 0) {
    return (
      <div className={cn('space-y-2', className)}>
        {Array.from({ length: skeletonCount }).map((_, i) => (
          <div key={i}>
            {renderSkeleton ? renderSkeleton() : (
              <Skeleton className="h-16 w-full" />
            )}
          </div>
        ))}
      </div>
    );
  }

  const totalHeight = items.length * estimatedItemHeight;
  const offsetTop = visibleRange.start * estimatedItemHeight;
  const visibleItems = items.slice(visibleRange.start, visibleRange.end);

  return (
    <div
      ref={containerRef}
      className={cn('overflow-y-auto', className)}
      style={{ height: '100%' }}
    >
      <div style={{ height: totalHeight, position: 'relative' }}>
        <div style={{ transform: `translateY(${offsetTop}px)` }}>
          {visibleItems.map((item, i) => {
            const actualIndex = visibleRange.start + i;
            return (
              <div key={keyExtractor(item, actualIndex)}>
                {renderItem(item, actualIndex)}
              </div>
            );
          })}
        </div>
      </div>

      {/* Load more trigger */}
      {hasMore && (
        <div ref={loadMoreRef} className="py-4 flex justify-center">
          {isLoading ? (
            <div className="flex items-center gap-2 text-white/40">
              <div className="w-4 h-4 border-2 border-cyan-500/30 border-t-cyan-500 rounded-full animate-spin" />
              <span className="text-sm font-mono">LOADING...</span>
            </div>
          ) : (
            <span className="text-xs text-white/30 font-mono">SCROLL FOR MORE</span>
          )}
        </div>
      )}
    </div>
  );
}) as <T>(props: VirtualizedListProps<T>) => ReactNode;

/**
 * LazyLoadSection - Loads content when it comes into viewport
 */
interface LazyLoadSectionProps {
  children: ReactNode;
  skeleton?: ReactNode;
  onVisible?: () => void;
  className?: string;
  rootMargin?: string;
}

export const LazyLoadSection = memo(function LazyLoadSection({
  children,
  skeleton,
  onVisible,
  className,
  rootMargin = '100px',
}: LazyLoadSectionProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [hasLoaded, setHasLoaded] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting && !hasLoaded) {
          setIsVisible(true);
          setHasLoaded(true);
          onVisible?.();
        }
      },
      { rootMargin, threshold: 0 }
    );

    observer.observe(element);

    return () => {
      observer.unobserve(element);
    };
  }, [hasLoaded, onVisible, rootMargin]);

  return (
    <div ref={ref} className={className}>
      {isVisible ? children : (skeleton || <Skeleton className="h-32 w-full" />)}
    </div>
  );
});

/**
 * InfiniteScroll - Generic infinite scroll wrapper
 */
interface InfiniteScrollProps {
  children: ReactNode;
  onLoadMore: () => void;
  hasMore: boolean;
  isLoading: boolean;
  loader?: ReactNode;
  endMessage?: ReactNode;
  className?: string;
}

export const InfiniteScroll = memo(function InfiniteScroll({
  children,
  onLoadMore,
  hasMore,
  isLoading,
  loader,
  endMessage,
  className,
}: InfiniteScrollProps) {
  const loadMoreRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!hasMore || isLoading) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) {
          onLoadMore();
        }
      },
      { threshold: 0.1, rootMargin: '100px' }
    );

    const element = loadMoreRef.current;
    if (element) {
      observer.observe(element);
    }

    return () => {
      if (element) {
        observer.unobserve(element);
      }
    };
  }, [hasMore, isLoading, onLoadMore]);

  return (
    <div className={className}>
      {children}

      <div ref={loadMoreRef}>
        {isLoading && (
          loader || (
            <div className="py-4 flex justify-center">
              <div className="flex items-center gap-2 text-white/40">
                <div className="w-4 h-4 border-2 border-cyan-500/30 border-t-cyan-500 rounded-full animate-spin" />
                <span className="text-sm font-mono">LOADING...</span>
              </div>
            </div>
          )
        )}

        {!hasMore && !isLoading && endMessage && (
          <div className="py-4 text-center text-white/30 text-sm font-mono">
            {endMessage}
          </div>
        )}
      </div>
    </div>
  );
});
