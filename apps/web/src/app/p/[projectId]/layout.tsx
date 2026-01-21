'use client';

/**
 * Project Workspace Layout
 * Provides project-specific navigation sidebar for all /p/:projectId/* routes
 *
 * MVP Mode (DEMO2_MVP_EXECUTION.md):
 * - Only shows Demo2-enabled routes in navigation
 * - Hides advanced features (Universe Map, Rules, Reliability, Replay, World, Society, Target)
 */

import { useSession } from 'next-auth/react';
import { useRouter, useParams, usePathname } from 'next/navigation';
import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { cn } from '@/lib/utils';
import {
  Terminal,
  Loader2,
  Menu,
  X,
  ArrowLeft,
  LayoutDashboard,
  Users,
  ScrollText,
  Play,
  Globe,
  Settings,
  Target,
  Layers,
  FolderKanban,
  Sparkles,
  Network,
  Crosshair,
  ShieldCheck,
  Activity,
  Map,
  FileBarChart,
} from 'lucide-react';
import { ActiveJobsBanner } from '@/components/pil';
import { isRouteEnabled, isMvpMode } from '@/lib/feature-flags';

// Mock project data - in real app this would come from API
const getMockProject = (projectId: string) => ({
  id: projectId,
  name: projectId.startsWith('proj_') ? 'New Project' : 'Sample Project',
  coreType: 'collective' as const,
});

// Project navigation items - full 12-item navigation
// MVP Mode filters these to only show Demo2-enabled routes
const allProjectNavItems = [
  { name: 'Overview', href: 'overview', icon: LayoutDashboard },
  { name: 'Data & Personas', href: 'data-personas', icon: Users },
  { name: 'Rules & Assumptions', href: 'rules', icon: ScrollText },
  { name: 'Run Center', href: 'run-center', icon: Play },
  { name: 'Universe Map', href: 'universe-map', icon: Globe },
  { name: 'Event Lab', href: 'event-lab', icon: Sparkles },
  { name: 'Society Simulation', href: 'society', icon: Network },
  { name: 'Target Planner', href: 'target', icon: Crosshair },
  { name: 'Reliability', href: 'reliability', icon: ShieldCheck },
  { name: 'Telemetry & Replay', href: 'replay', icon: Activity },
  { name: '2D World Viewer', href: 'world-viewer', icon: Map },
  { name: 'Reports', href: 'reports', icon: FileBarChart },
];

// Filter navigation items based on MVP mode
const projectNavItems = allProjectNavItems.filter((item) =>
  isRouteEnabled(item.href)
);

// Secondary navigation
const secondaryNavItems = [
  { name: 'Settings', href: 'settings', icon: Settings },
];

// Core type styling
const coreTypeConfig = {
  collective: { label: 'Collective', icon: Users, color: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30' },
  target: { label: 'Target', icon: Target, color: 'bg-purple-500/20 text-purple-400 border-purple-500/30' },
  hybrid: { label: 'Hybrid', icon: Layers, color: 'bg-amber-500/20 text-amber-400 border-amber-500/30' },
};

// Loading skeleton for project workspace
function ProjectWorkspaceSkeleton() {
  return (
    <div className="flex h-screen bg-black">
      {/* Sidebar skeleton */}
      <div className="w-56 border-r border-white/10 bg-black">
        <div className="flex items-center gap-2 px-4 py-4 border-b border-white/10">
          <div className="w-7 h-7 bg-white/10 animate-pulse" />
          <div className="h-4 w-24 bg-white/10 animate-pulse" />
        </div>
        <div className="p-4 space-y-3">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-6 bg-white/5 animate-pulse" />
          ))}
        </div>
      </div>

      {/* Main content skeleton */}
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-2 border-cyan-500/30 flex items-center justify-center mx-auto mb-4">
            <Terminal className="w-8 h-8 text-cyan-500 animate-pulse" />
          </div>
          <div className="flex items-center gap-2 justify-center">
            <Loader2 className="w-4 h-4 text-cyan-500 animate-spin" />
            <span className="text-sm font-mono text-white/40">LOADING PROJECT...</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// Project Sidebar Component
function ProjectSidebar({
  project,
  isMobile = false,
  onCloseMobile,
}: {
  project: { id: string; name: string; coreType: 'collective' | 'target' | 'hybrid' };
  isMobile?: boolean;
  onCloseMobile?: () => void;
}) {
  const pathname = usePathname();
  const params = useParams();
  const projectId = params.projectId as string;

  const coreConfig = coreTypeConfig[project.coreType];
  const CoreIcon = coreConfig.icon;

  const handleLinkClick = () => {
    if (isMobile && onCloseMobile) {
      onCloseMobile();
    }
  };

  return (
    <div className={cn(
      'flex flex-col h-full bg-black text-white border-r border-white/10',
      isMobile ? 'w-full' : 'w-56'
    )}>
      {/* Project Header */}
      <div className="px-3 py-4 border-b border-white/10">
        <div className="flex items-center justify-between mb-3">
          <Link
            href="/dashboard/projects"
            className="flex items-center gap-1.5 text-[10px] font-mono text-white/40 hover:text-white transition-colors"
            onClick={handleLinkClick}
          >
            <ArrowLeft className="w-3 h-3" />
            ALL PROJECTS
          </Link>
          {isMobile && onCloseMobile && (
            <button
              onClick={onCloseMobile}
              className="p-1 text-white/40 hover:text-white transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-white/10 flex items-center justify-center flex-shrink-0">
            <FolderKanban className="w-4 h-4 text-white/60" />
          </div>
          <div className="flex-1 min-w-0">
            <h2 className="text-sm font-mono font-bold text-white truncate">
              {project.name}
            </h2>
            <div className={cn(
              'inline-flex items-center gap-1 px-1.5 py-0.5 text-[9px] font-mono border mt-1',
              coreConfig.color
            )}>
              <CoreIcon className="w-2.5 h-2.5" />
              {coreConfig.label}
            </div>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto">
        <div className="px-2 py-1.5">
          <span className="text-[10px] font-mono text-white/30 uppercase tracking-wider">
            Workspace
          </span>
        </div>
        {projectNavItems.map((item) => {
          const fullHref = `/p/${projectId}/${item.href}`;
          const isActive = pathname === fullHref || pathname.startsWith(fullHref + '/');
          const Icon = item.icon;

          return (
            <Link
              key={item.name}
              href={fullHref}
              onClick={handleLinkClick}
              className={cn(
                'flex items-center gap-2 px-2 py-1.5 text-xs font-mono transition-all duration-150',
                isActive
                  ? 'bg-white text-black'
                  : 'text-white/60 hover:text-white hover:bg-white/5'
              )}
            >
              <Icon className="w-3.5 h-3.5 flex-shrink-0" />
              <span>{item.name}</span>
              {isActive && <span className="ml-auto text-[10px]">_</span>}
            </Link>
          );
        })}

        {/* Settings Section */}
        <div className="pt-4">
          <div className="px-2 py-1.5">
            <span className="text-[10px] font-mono text-white/30 uppercase tracking-wider">
              Config
            </span>
          </div>
          {secondaryNavItems.map((item) => {
            const fullHref = `/p/${projectId}/${item.href}`;
            const isActive = pathname === fullHref || pathname.startsWith(fullHref + '/');
            const Icon = item.icon;

            return (
              <Link
                key={item.name}
                href={fullHref}
                onClick={handleLinkClick}
                className={cn(
                  'flex items-center gap-2 px-2 py-1.5 text-xs font-mono transition-all duration-150',
                  isActive
                    ? 'bg-white text-black'
                    : 'text-white/60 hover:text-white hover:bg-white/5'
                )}
              >
                <Icon className="w-3.5 h-3.5 flex-shrink-0" />
                <span>{item.name}</span>
                {isActive && <span className="ml-auto text-[10px]">_</span>}
              </Link>
            );
          })}
        </div>
      </nav>

      {/* Quick Actions */}
      <div className="px-2 py-3 border-t border-white/10">
        <div className="px-2 py-1.5">
          <span className="text-[10px] font-mono text-white/30 uppercase tracking-wider">
            Quick Actions
          </span>
        </div>
        <Link
          href={`/p/${projectId}/run-center`}
          onClick={handleLinkClick}
          className="flex items-center gap-2 px-2 py-1.5 text-xs font-mono text-cyan-400 hover:bg-cyan-500/10 transition-colors"
        >
          <Play className="w-3.5 h-3.5" />
          <span>Run Simulation</span>
        </Link>
      </div>

      {/* Footer */}
      <div className="px-4 py-2 border-t border-white/5">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/20">
          <div className="flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
            <span>CONNECTED</span>
          </div>
          <span>v1.0</span>
        </div>
      </div>
    </div>
  );
}

export default function ProjectWorkspaceLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { status } = useSession();
  const router = useRouter();
  const params = useParams();
  const projectId = params.projectId as string;

  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const [project, setProject] = useState<ReturnType<typeof getMockProject> | null>(null);

  const openMobileSidebar = useCallback(() => {
    setIsMobileSidebarOpen(true);
  }, []);

  const closeMobileSidebar = useCallback(() => {
    setIsMobileSidebarOpen(false);
  }, []);

  // Load project data
  useEffect(() => {
    if (projectId) {
      // Mock loading - in real app this would be an API call
      const mockProject = getMockProject(projectId);
      setProject(mockProject);
    }
  }, [projectId]);

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/auth/login?callbackUrl=/dashboard');
    }
  }, [status, router]);

  // Show loading state while checking auth or loading project
  if (status === 'loading' || !project) {
    return <ProjectWorkspaceSkeleton />;
  }

  if (status === 'unauthenticated') {
    return <ProjectWorkspaceSkeleton />;
  }

  return (
    <div className="flex h-screen bg-black">
      {/* Mobile Header */}
      <div className="fixed top-0 left-0 right-0 z-40 md:hidden bg-black border-b border-white/10">
        <div className="flex items-center justify-between px-4 py-3">
          <div className="flex items-center gap-2 min-w-0">
            <FolderKanban className="w-4 h-4 text-white/60 flex-shrink-0" />
            <span className="text-sm font-mono font-bold text-white truncate">{project.name}</span>
          </div>
          <button
            type="button"
            onClick={openMobileSidebar}
            className="p-2 text-white/60 hover:text-white hover:bg-white/5 transition-colors"
            aria-label="Open navigation menu"
          >
            <Menu className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Mobile Sidebar Overlay */}
      <div
        className={cn(
          'fixed inset-0 z-50 md:hidden transition-opacity duration-200',
          isMobileSidebarOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
        )}
      >
        <div
          className="absolute inset-0 bg-black/80 backdrop-blur-sm"
          onClick={closeMobileSidebar}
        />
        <nav
          className={cn(
            'absolute left-0 top-0 bottom-0 w-72 max-w-[85vw] bg-black transition-transform duration-200',
            isMobileSidebarOpen ? 'translate-x-0' : '-translate-x-full'
          )}
        >
          <ProjectSidebar
            project={project}
            isMobile
            onCloseMobile={closeMobileSidebar}
          />
        </nav>
      </div>

      {/* Desktop Sidebar */}
      <nav className="hidden md:block flex-shrink-0">
        <ProjectSidebar project={project} />
      </nav>

      {/* Main Content */}
      <main className="flex-1 overflow-auto pt-14 md:pt-0">
        {/* Global Active Jobs Banner - PHASE 6: Loading Architecture */}
        <div className="px-4 pt-4 md:px-6 md:pt-6">
          <ActiveJobsBanner projectId={projectId} maxVisible={2} className="mb-0" />
        </div>
        {children}
      </main>
    </div>
  );
}
