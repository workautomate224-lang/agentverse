'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import { Users, LayoutTemplate, ScrollText, FileSearch, Library } from 'lucide-react';

const libraryTabs = [
  { name: 'Personas Library', href: '/library/personas', icon: Users },
  { name: 'Templates', href: '/library/templates', icon: LayoutTemplate },
  { name: 'Rulesets', href: '/library/rulesets', icon: ScrollText },
  { name: 'Evidence Source', href: '/library/evidence', icon: FileSearch },
];

export default function LibraryLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-black p-4 md:p-6">
      {/* Header */}
      <div className="mb-4 md:mb-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-8 h-8 md:w-10 md:h-10 bg-white/10 border border-white/20 flex items-center justify-center flex-shrink-0">
            <Library className="w-4 h-4 md:w-5 md:h-5 text-cyan-400" />
          </div>
          <div className="min-w-0">
            <h1 className="text-lg md:text-xl font-mono font-bold text-white">Library</h1>
            <p className="text-[10px] md:text-xs font-mono text-white/40 truncate">
              Manage personas, templates, rulesets, and evidence
            </p>
          </div>
        </div>
      </div>

      {/* Tab Navigation - Horizontally scrollable on mobile */}
      <div className="border-b border-white/10 mb-4 md:mb-6 -mx-4 md:mx-0 px-4 md:px-0">
        <nav className="flex gap-1 overflow-x-auto pb-px scrollbar-hide">
          {libraryTabs.map((tab) => {
            const isActive = pathname === tab.href || pathname.startsWith(tab.href + '/');
            return (
              <Link
                key={tab.name}
                href={tab.href}
                className={cn(
                  'flex items-center gap-1.5 md:gap-2 px-3 md:px-4 py-2 md:py-2.5 text-[10px] md:text-xs font-mono transition-all duration-150 border-b-2 -mb-[2px] whitespace-nowrap flex-shrink-0',
                  isActive
                    ? 'text-cyan-400 border-cyan-400 bg-cyan-400/5'
                    : 'text-white/50 border-transparent hover:text-white hover:bg-white/5'
                )}
              >
                <tab.icon className="w-3 h-3 md:w-3.5 md:h-3.5" />
                <span className="hidden sm:inline">{tab.name}</span>
                <span className="sm:hidden">{tab.name.split(' ')[0]}</span>
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Content */}
      {children}
    </div>
  );
}
