'use client';

import * as React from 'react';
import * as TooltipPrimitive from '@radix-ui/react-tooltip';
import { cn } from '@/lib/utils';

const TooltipProvider = TooltipPrimitive.Provider;

const Tooltip = TooltipPrimitive.Root;

const TooltipTrigger = TooltipPrimitive.Trigger;

const TooltipContent = React.forwardRef<
  React.ElementRef<typeof TooltipPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof TooltipPrimitive.Content>
>(({ className, sideOffset = 4, ...props }, ref) => (
  <TooltipPrimitive.Content
    ref={ref}
    sideOffset={sideOffset}
    className={cn(
      'z-50 overflow-hidden border border-white/20 bg-black px-3 py-1.5',
      'text-xs font-mono text-white/90',
      'animate-in fade-in-0 zoom-in-95',
      'data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95',
      'data-[side=bottom]:slide-in-from-top-2',
      'data-[side=left]:slide-in-from-right-2',
      'data-[side=right]:slide-in-from-left-2',
      'data-[side=top]:slide-in-from-bottom-2',
      className
    )}
    {...props}
  />
));
TooltipContent.displayName = TooltipPrimitive.Content.displayName;

/**
 * Simple tooltip wrapper for common use cases
 * Accessible by default - shows on hover and focus
 */
interface SimpleTooltipProps {
  content: React.ReactNode;
  children: React.ReactNode;
  side?: 'top' | 'bottom' | 'left' | 'right';
  align?: 'start' | 'center' | 'end';
  delayDuration?: number;
  className?: string;
}

const SimpleTooltip = React.memo(function SimpleTooltip({
  content,
  children,
  side = 'top',
  align = 'center',
  delayDuration = 200,
  className,
}: SimpleTooltipProps) {
  return (
    <TooltipProvider>
      <Tooltip delayDuration={delayDuration}>
        <TooltipTrigger asChild>{children}</TooltipTrigger>
        <TooltipContent side={side} align={align} className={className}>
          {content}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
});

/**
 * Parameter tooltip for advanced settings
 * Shows parameter name, description, and current value
 */
interface ParameterTooltipProps {
  name: string;
  description: string;
  defaultValue?: string | number;
  range?: { min: number; max: number };
  children: React.ReactNode;
}

const ParameterTooltip = React.memo(function ParameterTooltip({
  name,
  description,
  defaultValue,
  range,
  children,
}: ParameterTooltipProps) {
  return (
    <SimpleTooltip
      content={
        <div className="max-w-xs space-y-1">
          <p className="font-bold text-cyan-400">{name}</p>
          <p className="text-white/70">{description}</p>
          {defaultValue !== undefined && (
            <p className="text-white/50">
              Default: <span className="text-white/80">{defaultValue}</span>
            </p>
          )}
          {range && (
            <p className="text-white/50">
              Range: <span className="text-white/80">{range.min} - {range.max}</span>
            </p>
          )}
        </div>
      }
      side="right"
    >
      {children}
    </SimpleTooltip>
  );
});

export {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
  TooltipProvider,
  SimpleTooltip,
  ParameterTooltip,
};
