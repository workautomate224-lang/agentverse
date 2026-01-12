'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import { Users, LayoutTemplate, ScrollText, FileSearch, Library } from 'lucide-react';

const libraryTabs = [
  { name: 'Personas Library', href: '/dashboard/library/personas', icon: Users },
  { name: 'Templates', href: '/dashboard/library/templates', icon: LayoutTemplate },
  { name: 'Rulesets', href: '/dashboard/library/rulesets', icon: ScrollText },
  { name: 'Evidence Source', href: '/dashboard/library/evidence', icon: FileSearch },
];

export default function LibraryLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-black p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 bg-white/10 border border-white/20 flex items-center justify-center">
            <Library className="w-5 h-5 text-cyan-400" />
          </div>
          <div>
            <h1 className="text-xl font-mono font-bold text-white">Library</h1>
            <p className="text-xs font-mono text-white/40">
              Manage your personas, templates, rulesets, and evidence sources
            </p>
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-white/10 mb-6">
        <nav className="flex gap-1">
          {libraryTabs.map((tab) => {
            const isActive = pathname === tab.href || pathname.startsWith(tab.href + '/');
            return (
              <Link
                key={tab.name}
                href={tab.href}
                className={cn(
                  'flex items-center gap-2 px-4 py-2.5 text-xs font-mono transition-all duration-150 border-b-2 -mb-[2px]',
                  isActive
                    ? 'text-cyan-400 border-cyan-400 bg-cyan-400/5'
                    : 'text-white/50 border-transparent hover:text-white hover:bg-white/5'
                )}
              >
                <tab.icon className="w-3.5 h-3.5" />
                <span>{tab.name}</span>
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
