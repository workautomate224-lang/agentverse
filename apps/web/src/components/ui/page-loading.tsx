'use client';

import { memo } from 'react';
import { cn } from '@/lib/utils';
import { Skeleton, SkeletonStats, SkeletonCard, SkeletonTable, SkeletonList } from './skeleton';

type LoadingType = 'default' | 'dashboard' | 'table' | 'cards' | 'list' | 'graph' | 'detail';

interface PageLoadingProps {
  type?: LoadingType;
  title?: string;
  className?: string;
}

/**
 * Route-level loading component for code splitting
 * Used in loading.tsx files for each route
 */
export const PageLoading = memo(function PageLoading({
  type = 'default',
  title,
  className,
}: PageLoadingProps) {
  return (
    <div className={cn('animate-in fade-in-0 duration-300 p-6 space-y-6', className)}>
      {/* Header skeleton */}
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          {title ? (
            <h1 className="text-xl font-mono text-white/40">{title}</h1>
          ) : (
            <Skeleton className="h-8 w-48" />
          )}
          <Skeleton className="h-4 w-72" />
        </div>
        <div className="flex gap-2">
          <Skeleton className="h-9 w-24" />
          <Skeleton className="h-9 w-32" />
        </div>
      </div>

      {/* Content skeleton based on type */}
      {type === 'dashboard' && (
        <>
          <SkeletonStats count={4} />
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <SkeletonCard className="h-64" />
            <SkeletonCard className="h-64" />
          </div>
          <SkeletonTable rows={5} columns={5} />
        </>
      )}

      {type === 'table' && <SkeletonTable rows={10} columns={5} />}

      {type === 'cards' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <SkeletonCard key={i} className="h-48" />
          ))}
        </div>
      )}

      {type === 'list' && <SkeletonList items={8} />}

      {type === 'graph' && (
        <div className="border border-white/10 p-4">
          <div className="flex items-center justify-between mb-4">
            <Skeleton className="h-6 w-32" />
            <div className="flex gap-2">
              <Skeleton className="h-8 w-8" />
              <Skeleton className="h-8 w-8" />
              <Skeleton className="h-8 w-8" />
            </div>
          </div>
          <Skeleton className="h-[500px] w-full" />
          <div className="flex justify-center gap-4 mt-4">
            <Skeleton className="h-6 w-24" />
            <Skeleton className="h-6 w-24" />
          </div>
        </div>
      )}

      {type === 'detail' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-4">
            <SkeletonCard className="h-32" />
            <SkeletonCard className="h-64" />
            <SkeletonTable rows={5} columns={4} />
          </div>
          <div className="space-y-4">
            <SkeletonCard className="h-48" />
            <SkeletonList items={4} />
          </div>
        </div>
      )}

      {type === 'default' && (
        <div className="space-y-4">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      )}
    </div>
  );
});

/**
 * Minimal loading spinner for smaller components
 */
export const LoadingSpinner = memo(function LoadingSpinner({
  size = 'md',
  className,
}: {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}) {
  const sizeClasses = {
    sm: 'w-4 h-4 border-2',
    md: 'w-8 h-8 border-2',
    lg: 'w-12 h-12 border-3',
  };

  return (
    <div
      className={cn(
        'animate-spin rounded-full border-white/20 border-t-cyan-400',
        sizeClasses[size],
        className
      )}
    />
  );
});

/**
 * Full page loading overlay
 */
export const PageLoadingOverlay = memo(function PageLoadingOverlay({
  message,
}: {
  message?: string;
}) {
  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="flex flex-col items-center gap-4">
        <LoadingSpinner size="lg" />
        {message && (
          <p className="text-sm font-mono text-white/60">{message}</p>
        )}
      </div>
    </div>
  );
});
