'use client';

import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { Sidebar } from '@/components/dashboard/sidebar';
import { SkipLink } from '@/components/ui/skip-link';
import { SKIP_LINK_TARGETS } from '@/lib/accessibility';
import { useSidebarStore } from '@/store/sidebar';
import { cn } from '@/lib/utils';
import { Terminal, Loader2, Menu } from 'lucide-react';

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
  const { isCollapsed, isMobileOpen, setMobileOpen } = useSidebarStore();
  const [mounted, setMounted] = useState(false);

  // Handle hydration - ensure component is mounted before rendering mobile UI
  useEffect(() => {
    setMounted(true);
  }, []);

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

      {/* Mobile Header - Only visible on mobile/tablet */}
      <div className="fixed top-0 left-0 right-0 z-40 md:hidden bg-black border-b border-white/10">
        <div className="flex items-center justify-between px-4 py-3">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 bg-white flex items-center justify-center">
              <Terminal className="w-4 h-4 text-black" />
            </div>
            <span className="text-sm font-mono font-bold tracking-tight text-white">AGENTVERSE</span>
          </div>
          <button
            type="button"
            onClick={() => {
              setMobileOpen(true);
            }}
            className="p-2 text-white/60 hover:text-white hover:bg-white/5 transition-colors active:bg-white/10"
            aria-label="Open navigation menu"
            aria-expanded={isMobileOpen}
          >
            <Menu className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Mobile Sidebar Overlay - Only render after mount to prevent hydration issues */}
      {mounted && isMobileOpen && (
        <div
          className="fixed inset-0 z-50 md:hidden"
          aria-hidden="true"
        >
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/80 backdrop-blur-sm"
            onClick={() => setMobileOpen(false)}
          />
          {/* Mobile Sidebar */}
          <nav
            className="absolute left-0 top-0 bottom-0 w-72 max-w-[85vw] animate-slide-in-left"
            aria-label="Mobile navigation"
          >
            <Sidebar isMobile />
          </nav>
        </div>
      )}

      {/* Desktop Navigation landmark - Hidden on mobile */}
      <nav
        id={SKIP_LINK_TARGETS.navigation}
        aria-label="Main navigation"
        className={cn(
          'hidden md:block flex-shrink-0 transition-all duration-300',
          isCollapsed ? 'w-14' : 'w-56'
        )}
      >
        <Sidebar />
      </nav>

      {/* Main content landmark */}
      <main
        id={SKIP_LINK_TARGETS.mainContent}
        className="flex-1 overflow-auto transition-all duration-300 pt-14 md:pt-0"
        role="main"
        aria-label="Main content"
      >
        {children}
      </main>

      {/* Mobile sidebar animation styles */}
      <style jsx>{`
        @keyframes slide-in-left {
          from {
            transform: translateX(-100%);
          }
          to {
            transform: translateX(0);
          }
        }
        .animate-slide-in-left {
          animation: slide-in-left 0.2s ease-out;
        }
      `}</style>
    </div>
  );
}
