'use client';

import { memo } from 'react';
import { cn } from '@/lib/utils';
import { SKIP_LINK_TARGETS } from '@/lib/accessibility';

interface SkipLinkProps {
  targetId?: string;
  label?: string;
  className?: string;
}

/**
 * Skip link for keyboard navigation
 * Allows users to skip to main content (Interaction_design.md §9)
 */
export const SkipLink = memo(function SkipLink({
  targetId = SKIP_LINK_TARGETS.mainContent,
  label = 'Skip to main content',
  className,
}: SkipLinkProps) {
  return (
    <a
      href={`#${targetId}`}
      className={cn(
        // Visually hidden until focused
        'absolute left-4 top-4 z-50 -translate-y-full opacity-0',
        'focus:translate-y-0 focus:opacity-100',
        // Styled button
        'bg-cyan-500 text-black px-4 py-2 font-mono text-sm',
        'focus:outline-none focus:ring-2 focus:ring-cyan-400',
        'transition-all duration-200',
        className
      )}
    >
      {label}
    </a>
  );
});

/**
 * Skip link group for multiple targets
 */
export const SkipLinkGroup = memo(function SkipLinkGroup() {
  return (
    <div className="fixed top-0 left-0 z-50">
      <SkipLink
        targetId={SKIP_LINK_TARGETS.mainContent}
        label="Skip to main content"
      />
      <SkipLink
        targetId={SKIP_LINK_TARGETS.navigation}
        label="Skip to navigation"
        className="left-48"
      />
    </div>
  );
});
