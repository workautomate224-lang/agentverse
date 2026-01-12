'use client';

import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { Sidebar } from '@/components/dashboard/sidebar';
import { SkipLink } from '@/components/ui/skip-link';
import { SKIP_LINK_TARGETS } from '@/lib/accessibility';
import { useSidebarStore } from '@/store/sidebar';
import { cn } from '@/lib/utils';
import { Terminal, Loader2 } from 'lucide-react';

// Loading skeleton for dashboard
function DashboardSkeleton() {
  return (
    <div className="flex h-screen bg-black">
      {/* Sidebar skeleton */}
      <div className="w-56 border-r border-white/10 bg-black">
        <div className="flex items-center gap-2 px-4 py-4 border-b border-white/10">
          <div className="w-7 h-7 bg-white/10 animate-pulse" />
          <div className="h-4 w-24 bg-white/10 animate-pulse" />
        </div>
        <div className="p-4 space-y-3">
          {[...Array(8)].map((_, i) => (
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
            <span className="text-sm font-mono text-white/40">INITIALIZING SYSTEM...</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { status } = useSession();
  const router = useRouter();
  const { isCollapsed } = useSidebarStore();

  useEffect(() => {
    // If unauthenticated and not loading, redirect to login
    if (status === 'unauthenticated') {
      router.push('/auth/login?callbackUrl=/dashboard');
    }
  }, [status, router]);

  // Show loading state while checking auth
  if (status === 'loading') {
    return <DashboardSkeleton />;
  }

  // If unauthenticated, show loading (will redirect)
  if (status === 'unauthenticated') {
    return <DashboardSkeleton />;
  }

  // Authenticated - render dashboard
  return (
    <div className="flex h-screen bg-black">
      {/* Skip links for keyboard navigation (Interaction_design.md §9) */}
      <SkipLink
        targetId={SKIP_LINK_TARGETS.mainContent}
        label="Skip to main content"
      />
      <SkipLink
        targetId={SKIP_LINK_TARGETS.navigation}
        label="Skip to navigation"
        className="left-48"
      />

      {/* Navigation landmark */}
      <nav
        id={SKIP_LINK_TARGETS.navigation}
        aria-label="Main navigation"
        className={cn(
          'flex-shrink-0 transition-all duration-300',
          isCollapsed ? 'w-14' : 'w-56'
        )}
      >
        <Sidebar />
      </nav>

      {/* Main content landmark */}
      <main
        id={SKIP_LINK_TARGETS.mainContent}
        className="flex-1 overflow-auto transition-all duration-300"
        role="main"
        aria-label="Main content"
      >
        {children}
      </main>
    </div>
  );
}
