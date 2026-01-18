import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const badgeVariants = cva(
  'inline-flex items-center px-2 py-0.5 text-xs font-mono transition-colors focus:outline-none focus:ring-1 focus:ring-white/50',
  {
    variants: {
      variant: {
        default: 'border border-white/20 bg-white/5 text-white',
        secondary: 'border border-white/10 bg-white/5 text-white/60',
        outline: 'border border-white/20 bg-transparent text-white/80',
        destructive: 'border border-red-500/30 bg-red-500/10 text-red-400',
        success: 'border border-green-500/30 bg-green-500/10 text-green-400',
        warning: 'border border-yellow-500/30 bg-yellow-500/10 text-yellow-400',
        info: 'border border-cyan-500/30 bg-cyan-500/10 text-cyan-400',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
