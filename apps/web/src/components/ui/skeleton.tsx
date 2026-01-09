'use client';

import { cn } from '@/lib/utils';
import { memo } from 'react';

interface SkeletonProps {
  className?: string;
}

export const Skeleton = memo(function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn(
        'animate-pulse bg-white/10 rounded',
        className
      )}
    />
  );
});

// Pre-built skeleton patterns for common UI elements
export const SkeletonCard = memo(function SkeletonCard({ className }: SkeletonProps) {
  return (
    <div className={cn('border border-white/10 p-4 space-y-3', className)}>
      <Skeleton className="h-4 w-3/4" />
      <Skeleton className="h-3 w-1/2" />
      <div className="flex gap-2 mt-4">
        <Skeleton className="h-6 w-16" />
        <Skeleton className="h-6 w-16" />
      </div>
    </div>
  );
});

export const SkeletonTable = memo(function SkeletonTable({
  rows = 5,
  columns = 4,
  className
}: { rows?: number; columns?: number } & SkeletonProps) {
  return (
    <div className={cn('border border-white/10', className)}>
      {/* Header */}
      <div className="flex gap-4 p-4 border-b border-white/10">
        {Array.from({ length: columns }).map((_, i) => (
          <Skeleton key={i} className="h-4 flex-1" />
        ))}
      </div>
      {/* Rows */}
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={rowIndex} className="flex gap-4 p-4 border-b border-white/5">
          {Array.from({ length: columns }).map((_, colIndex) => (
            <Skeleton key={colIndex} className="h-4 flex-1" />
          ))}
        </div>
      ))}
    </div>
  );
});

export const SkeletonList = memo(function SkeletonList({
  items = 5,
  className
}: { items?: number } & SkeletonProps) {
  return (
    <div className={cn('space-y-3', className)}>
      {Array.from({ length: items }).map((_, i) => (
        <div key={i} className="flex items-center gap-3 p-3 border border-white/10">
          <Skeleton className="w-10 h-10 rounded" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-2/3" />
            <Skeleton className="h-3 w-1/3" />
          </div>
        </div>
      ))}
    </div>
  );
});

export const SkeletonStats = memo(function SkeletonStats({
  count = 4,
  className
}: { count?: number } & SkeletonProps) {
  return (
    <div className={cn('grid grid-cols-2 md:grid-cols-4 gap-4', className)}>
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="border border-white/10 p-4">
          <Skeleton className="h-3 w-1/2 mb-2" />
          <Skeleton className="h-8 w-3/4" />
        </div>
      ))}
    </div>
  );
});

export const SkeletonGrid = memo(function SkeletonGrid({
  items = 6,
  columns = 3,
  className
}: { items?: number; columns?: number } & SkeletonProps) {
  return (
    <div className={cn(`grid grid-cols-1 md:grid-cols-${columns} gap-4`, className)}>
      {Array.from({ length: items }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  );
});
