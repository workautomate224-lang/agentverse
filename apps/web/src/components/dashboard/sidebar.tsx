'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { memo, useState } from 'react';
import { signOut, useSession } from 'next-auth/react';
import { cn } from '@/lib/utils';
import {
  LayoutDashboard,
  FolderKanban,
  Settings,
  Terminal,
  LogOut,
  ChevronUp,
  User,
  Shield,
  LayoutTemplate,
  FlaskConical,
  ListTodo,
  ShieldCheck,
  BookOpen,
  type LucideIcon,
} from 'lucide-react';

// Primary navigation per Interaction_design.md §2.1
const navigation: { name: string; href: string; icon: LucideIcon; roleRequired?: string }[] = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Projects', href: '/dashboard/projects', icon: FolderKanban },
  { name: 'Templates', href: '/dashboard/templates', icon: LayoutTemplate },
  { name: 'Calibration Lab', href: '/dashboard/calibration', icon: FlaskConical },
  { name: 'Runs & Jobs', href: '/dashboard/runs', icon: ListTodo },
  { name: 'Admin', href: '/dashboard/admin', icon: ShieldCheck, roleRequired: 'admin' },
];

const secondaryNavigation: { name: string; href: string; icon: LucideIcon }[] = [
  { name: 'Guide', href: '/dashboard/guide', icon: BookOpen },
  { name: 'Settings', href: '/dashboard/settings', icon: Settings },
];

export const Sidebar = memo(function Sidebar() {
  const pathname = usePathname();
  const { data: session } = useSession();
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  const handleLogout = async () => {
    setIsLoggingOut(true);
    try {
      await signOut({ callbackUrl: '/' });
    } catch {
      setIsLoggingOut(false);
    }
  };

  // Get user initials for avatar
  const getUserInitials = () => {
    if (session?.user?.name) {
      return session.user.name
        .split(' ')
        .map((n) => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2);
    }
    if (session?.user?.email) {
      return session.user.email[0].toUpperCase();
    }
    return 'AG';
  };

  return (
    <div className="flex flex-col h-full bg-black text-white w-56 border-r border-white/10">
      {/* Logo */}
      <div className="flex items-center gap-2 px-4 py-4 border-b border-white/10">
        <div className="w-7 h-7 bg-white flex items-center justify-center">
          <Terminal className="w-4 h-4 text-black" />
        </div>
        <span className="text-sm font-mono font-bold tracking-tight">AGENTVERSE</span>
        <span className="text-[10px] font-mono text-white/40 ml-auto">v1.0</span>
      </div>

      {/* Status indicator */}
      <div className="px-4 py-2 border-b border-white/10">
        <div className="flex items-center gap-2">
          <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
          <span className="text-[10px] font-mono text-white/50 uppercase tracking-wider">System Online</span>
        </div>
      </div>

      {/* Main Navigation */}
      <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto">
        <div className="px-2 py-1.5">
          <span className="text-[10px] font-mono text-white/30 uppercase tracking-wider">Navigation</span>
        </div>
        {navigation
          .filter((item) => {
            // Filter out role-gated items if user doesn't have required role
            if (item.roleRequired) {
              const userRole = (session?.user as { role?: string } | undefined)?.role;
              return userRole === item.roleRequired || userRole === 'admin';
            }
            return true;
          })
          .map((item) => {
            // Dashboard should only be active on exact match (it's the root route)
            const isActive = item.href === '/dashboard'
              ? pathname === item.href
              : pathname === item.href || pathname.startsWith(item.href + '/');
            return (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  'flex items-center gap-2 px-2 py-1.5 text-xs font-mono transition-all duration-150',
                  isActive
                    ? 'bg-white text-black'
                    : 'text-white/60 hover:text-white hover:bg-white/5'
                )}
              >
                <item.icon className="w-3.5 h-3.5" />
                <span>{item.name}</span>
                {isActive && (
                  <span className="ml-auto text-[10px]">_</span>
                )}
              </Link>
            );
          })}
      </nav>

      {/* Secondary Navigation */}
      <div className="px-2 py-3 border-t border-white/10">
        <div className="px-2 py-1.5">
          <span className="text-[10px] font-mono text-white/30 uppercase tracking-wider">System</span>
        </div>
        {secondaryNavigation.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                'flex items-center gap-2 px-2 py-1.5 text-xs font-mono transition-all duration-150',
                isActive
                  ? 'bg-white text-black'
                  : 'text-white/60 hover:text-white hover:bg-white/5'
              )}
            >
              <item.icon className="w-3.5 h-3.5" />
              <span>{item.name}</span>
            </Link>
          );
        })}
      </div>

      {/* User Profile Section */}
      <div className="border-t border-white/10">
        <div className="relative">
          {/* User Menu Dropdown */}
          {showUserMenu && (
            <div className="absolute bottom-full left-0 right-0 mb-1 mx-2 bg-black border border-white/20 shadow-lg animate-slide-up">
              {/* Menu Header */}
              <div className="px-3 py-2 border-b border-white/10">
                <div className="text-[10px] font-mono text-white/40 uppercase tracking-wider">
                  Agent Profile
                </div>
              </div>

              {/* User Info */}
              <div className="px-3 py-3 border-b border-white/10">
                <div className="text-sm font-mono text-white truncate">
                  {session?.user?.name || 'Agent'}
                </div>
                <div className="text-[10px] font-mono text-white/40 truncate mt-0.5">
                  {session?.user?.email || 'agent@agentverse.io'}
                </div>
              </div>

              {/* Menu Items */}
              <div className="py-1">
                <Link
                  href="/dashboard/settings"
                  className="flex items-center gap-2 px-3 py-2 text-xs font-mono text-white/60 hover:text-white hover:bg-white/5 transition-colors"
                  onClick={() => setShowUserMenu(false)}
                >
                  <User className="w-3.5 h-3.5" />
                  <span>Account Settings</span>
                </Link>
                <Link
                  href="/dashboard/settings"
                  className="flex items-center gap-2 px-3 py-2 text-xs font-mono text-white/60 hover:text-white hover:bg-white/5 transition-colors"
                  onClick={() => setShowUserMenu(false)}
                >
                  <Shield className="w-3.5 h-3.5" />
                  <span>Security</span>
                </Link>
              </div>

              {/* Logout */}
              <div className="border-t border-white/10 py-1">
                <button
                  onClick={handleLogout}
                  disabled={isLoggingOut}
                  className="flex items-center gap-2 w-full px-3 py-2 text-xs font-mono text-red-400 hover:text-red-300 hover:bg-red-500/10 transition-colors disabled:opacity-50"
                >
                  <LogOut className="w-3.5 h-3.5" />
                  <span>{isLoggingOut ? 'Disconnecting...' : 'Disconnect Session'}</span>
                </button>
              </div>
            </div>
          )}

          {/* User Button */}
          <button
            onClick={() => setShowUserMenu(!showUserMenu)}
            className={cn(
              'w-full flex items-center gap-3 px-4 py-3 text-left transition-all duration-150',
              showUserMenu ? 'bg-white/5' : 'hover:bg-white/5'
            )}
          >
            {/* Avatar */}
            <div className="w-8 h-8 bg-gradient-to-br from-cyan-500 to-blue-500 flex items-center justify-center flex-shrink-0">
              <span className="text-xs font-mono font-bold text-black">
                {getUserInitials()}
              </span>
            </div>

            {/* User Info */}
            <div className="flex-1 min-w-0">
              <div className="text-xs font-mono text-white truncate">
                {session?.user?.name || 'Agent'}
              </div>
              <div className="text-[10px] font-mono text-white/40 truncate">
                {session?.user?.email?.split('@')[0] || 'agent'}
              </div>
            </div>

            {/* Expand Icon */}
            <ChevronUp
              className={cn(
                'w-4 h-4 text-white/40 transition-transform duration-200',
                showUserMenu ? 'rotate-0' : 'rotate-180'
              )}
            />
          </button>
        </div>

        {/* Status indicator */}
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

      {/* Animation styles */}
      <style jsx>{`
        @keyframes slide-up {
          from {
            opacity: 0;
            transform: translateY(8px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .animate-slide-up {
          animation: slide-up 0.15s ease-out;
        }
      `}</style>
    </div>
  );
});
