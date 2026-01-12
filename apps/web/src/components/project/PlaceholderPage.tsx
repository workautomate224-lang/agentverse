'use client';

import { type LucideIcon, Construction } from 'lucide-react';

interface PlaceholderPageProps {
  title: string;
  description: string;
  icon?: LucideIcon;
}

export function PlaceholderPage({ title, description, icon: Icon = Construction }: PlaceholderPageProps) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center p-4 md:p-8 text-center">
      <div className="flex flex-col items-center gap-4 md:gap-6 max-w-md">
        {/* Icon */}
        <div className="flex h-16 w-16 md:h-20 md:w-20 items-center justify-center border border-white/20 bg-white/5">
          <Icon className="h-8 w-8 md:h-10 md:w-10 text-cyan-400" />
        </div>

        {/* Coming Soon badge */}
        <span className="px-2 md:px-3 py-1 text-[10px] md:text-xs font-medium bg-amber-500/20 text-amber-300 border border-amber-500/30">
          COMING SOON
        </span>

        {/* Title */}
        <h2 className="text-lg md:text-2xl font-bold text-white">{title}</h2>

        {/* Description */}
        <p className="text-sm md:text-base text-white/60">{description}</p>

        {/* Decorative line */}
        <div className="w-24 md:w-32 h-px bg-gradient-to-r from-transparent via-cyan-400/50 to-transparent" />
      </div>
    </div>
  );
}
