'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useSession } from 'next-auth/react';
import {
  LayoutDashboard,
  Map,
  Users,
  Users2,
  Target,
  Combine,
  Shield,
  PlayCircle,
  Download,
  Settings,
  type LucideIcon,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface Tab {
  name: string;
  href: string;
  icon: LucideIcon;
  roleRequired?: string;
}

interface ProjectTabNavProps {
  projectId: string;
}

export function ProjectTabNav({ projectId }: ProjectTabNavProps) {
  const pathname = usePathname();
  const { data: session } = useSession();

  const basePath = `/dashboard/projects/${projectId}`;

  const tabs: Tab[] = [
    { name: 'Overview', href: basePath, icon: LayoutDashboard },
    { name: 'Universe Map', href: `${basePath}/universe-map`, icon: Map },
    { name: 'Personas', href: `${basePath}/personas`, icon: Users },
    { name: 'Society Mode', href: `${basePath}/society-mode`, icon: Users2 },
    { name: 'Target Mode', href: `${basePath}/target-mode`, icon: Target },
    { name: 'Hybrid Mode', href: `${basePath}/hybrid-mode`, icon: Combine },
    { name: 'Reliability', href: `${basePath}/reliability`, icon: Shield },
    { name: '2D Replay', href: `${basePath}/replay`, icon: PlayCircle },
    { name: 'Exports', href: `${basePath}/exports`, icon: Download },
    { name: 'Settings', href: `${basePath}/settings`, icon: Settings, roleRequired: 'admin' },
  ];

  // Filter tabs based on role
  const visibleTabs = tabs.filter((tab) => {
    if (tab.roleRequired) {
      const userRole = (session?.user as { role?: string } | undefined)?.role;
      return userRole === tab.roleRequired || userRole === 'admin';
    }
    return true;
  });

  // Determine if tab is active
  const isActive = (tabHref: string) => {
    if (tabHref === basePath) {
      return pathname === basePath;
    }
    return pathname.startsWith(tabHref);
  };

  return (
    <div className="border-b border-white/10 bg-black/30">
      <nav className="-mb-px flex overflow-x-auto scrollbar-hide">
        {visibleTabs.map((tab) => {
          const Icon = tab.icon;
          const active = isActive(tab.href);

          return (
            <Link
              key={tab.name}
              href={tab.href}
              className={cn(
                'group relative flex items-center gap-2 whitespace-nowrap px-4 py-3 text-sm font-medium transition-colors',
                active
                  ? 'text-cyan-400 border-b-2 border-cyan-400'
                  : 'text-white/60 hover:text-white/90 border-b-2 border-transparent hover:border-white/20'
              )}
            >
              <Icon className={cn('h-4 w-4', active ? 'text-cyan-400' : 'text-white/40 group-hover:text-white/60')} />
              {tab.name}
              {active && (
                <span
                  className="absolute inset-x-0 bottom-0 h-0.5 bg-gradient-to-r from-cyan-400 to-purple-500"
                  aria-hidden="true"
                />
              )}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
