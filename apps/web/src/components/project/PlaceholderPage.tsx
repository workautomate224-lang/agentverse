'use client';

import { type LucideIcon, Construction } from 'lucide-react';

interface PlaceholderPageProps {
  title: string;
  description: string;
  icon?: LucideIcon;
}

export function PlaceholderPage({ title, description, icon: Icon = Construction }: PlaceholderPageProps) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center p-8 text-center">
      <div className="flex flex-col items-center gap-6 max-w-md">
        {/* Icon */}
        <div className="flex h-20 w-20 items-center justify-center border border-white/20 bg-white/5">
          <Icon className="h-10 w-10 text-cyan-400" />
        </div>

        {/* Coming Soon badge */}
        <span className="px-3 py-1 text-xs font-medium bg-amber-500/20 text-amber-300 border border-amber-500/30">
          COMING SOON
        </span>

        {/* Title */}
        <h2 className="text-2xl font-bold text-white">{title}</h2>

        {/* Description */}
        <p className="text-white/60">{description}</p>

        {/* Decorative line */}
        <div className="w-32 h-px bg-gradient-to-r from-transparent via-cyan-400/50 to-transparent" />
      </div>
    </div>
  );
}
