'use client';

import { cn } from '@/lib/utils';
import { CheckCircle, XCircle, AlertCircle, Info } from 'lucide-react';

interface SignificanceIndicatorProps {
  pValue: number;
  threshold?: number;
  showLabel?: boolean;
  showPValue?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function SignificanceIndicator({
  pValue,
  threshold = 0.05,
  showLabel = true,
  showPValue = true,
  size = 'md',
  className,
}: SignificanceIndicatorProps) {
  const isSignificant = pValue < threshold;
  const isHighlySignificant = pValue < 0.01;
  const isMarginal = pValue >= threshold && pValue < 0.1;

  const sizeClasses = {
    sm: 'text-[10px]',
    md: 'text-xs',
    lg: 'text-sm',
  };

  const iconSizes = {
    sm: 'w-3 h-3',
    md: 'w-4 h-4',
    lg: 'w-5 h-5',
  };

  const getConfig = () => {
    if (isHighlySignificant) {
      return {
        icon: CheckCircle,
        label: 'Highly Significant',
        color: 'text-green-400',
        bgColor: 'bg-green-500/10',
        borderColor: 'border-green-500/30',
      };
    }
    if (isSignificant) {
      return {
        icon: CheckCircle,
        label: 'Significant',
        color: 'text-green-400',
        bgColor: 'bg-green-500/10',
        borderColor: 'border-green-500/30',
      };
    }
    if (isMarginal) {
      return {
        icon: AlertCircle,
        label: 'Marginally Significant',
        color: 'text-yellow-400',
        bgColor: 'bg-yellow-500/10',
        borderColor: 'border-yellow-500/30',
      };
    }
    return {
      icon: XCircle,
      label: 'Not Significant',
      color: 'text-white/40',
      bgColor: 'bg-white/5',
      borderColor: 'border-white/10',
    };
  };

  const config = getConfig();
  const Icon = config.icon;

  return (
    <div
      className={cn(
        "inline-flex items-center gap-1.5 px-2 py-1 border font-mono",
        config.bgColor,
        config.borderColor,
        sizeClasses[size],
        className
      )}
    >
      <Icon className={cn(iconSizes[size], config.color)} />
      {showLabel && (
        <span className={config.color}>{config.label}</span>
      )}
      {showPValue && (
        <span className="text-white/40 ml-1">
          (p={pValue < 0.001 ? '<0.001' : pValue.toFixed(3)})
        </span>
      )}
    </div>
  );
}

// Companion component for displaying significance explanation
interface SignificanceTooltipProps {
  className?: string;
}

export function SignificanceTooltip({ className }: SignificanceTooltipProps) {
  return (
    <div className={cn("bg-white/5 border border-white/10 p-3", className)}>
      <div className="flex items-center gap-2 mb-2">
        <Info className="w-4 h-4 text-white/40" />
        <span className="text-xs font-mono font-bold text-white">Statistical Significance</span>
      </div>
      <div className="space-y-2 text-[10px] font-mono text-white/60">
        <div className="flex items-center gap-2">
          <CheckCircle className="w-3 h-3 text-green-400" />
          <span><strong className="text-green-400">p &lt; 0.05</strong>: Statistically significant difference</span>
        </div>
        <div className="flex items-center gap-2">
          <AlertCircle className="w-3 h-3 text-yellow-400" />
          <span><strong className="text-yellow-400">0.05 ≤ p &lt; 0.10</strong>: Marginally significant</span>
        </div>
        <div className="flex items-center gap-2">
          <XCircle className="w-3 h-3 text-white/40" />
          <span><strong className="text-white/40">p ≥ 0.10</strong>: Not statistically significant</span>
        </div>
      </div>
      <p className="mt-2 text-[10px] font-mono text-white/40">
        Lower p-values indicate stronger evidence that the observed difference is not due to chance.
      </p>
    </div>
  );
}
