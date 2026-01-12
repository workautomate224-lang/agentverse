'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { memo, useState } from 'react';
import { signOut, useSession } from 'next-auth/react';
import { cn } from '@/lib/utils';
import { useSidebarStore } from '@/store/sidebar';
import {
  LayoutDashboard,
  FolderKanban,
  Settings,
  Terminal,
  LogOut,
  ChevronUp,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  User,
  Shield,
  Library,
  FlaskConical,
  ListTodo,
  ShieldCheck,
  BookOpen,
  Users,
  LayoutTemplate,
  ScrollText,
  FileSearch,
  type LucideIcon,
} from 'lucide-react';

// Navigation item type
interface NavItem {
  name: string;
  href: string;
  icon: LucideIcon;
  roleRequired?: string;
  children?: NavItem[];
}

// Primary navigation
const navigation: NavItem[] = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Projects', href: '/dashboard/projects', icon: FolderKanban },
  {
    name: 'Library',
    href: '/dashboard/library',
    icon: Library,
    children: [
      { name: 'Personas Library', href: '/dashboard/library/personas', icon: Users },
      { name: 'Templates', href: '/dashboard/library/templates', icon: LayoutTemplate },
      { name: 'Rulesets', href: '/dashboard/library/rulesets', icon: ScrollText },
      { name: 'Evidence Source', href: '/dashboard/library/evidence', icon: FileSearch },
    ],
  },
  { name: 'Calibration Lab', href: '/dashboard/calibration', icon: FlaskConical },
  { name: 'Runs & Jobs', href: '/dashboard/runs', icon: ListTodo },
  { name: 'Admin', href: '/dashboard/admin', icon: ShieldCheck, roleRequired: 'admin' },
];

const secondaryNavigation: NavItem[] = [
  { name: 'Guide', href: '/dashboard/guide', icon: BookOpen },
  { name: 'Settings', href: '/dashboard/settings', icon: Settings },
];

export const Sidebar = memo(function Sidebar() {
  const pathname = usePathname();
  const { data: session } = useSession();
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [expandedItems, setExpandedItems] = useState<string[]>(['Library']);
  const { isCollapsed, toggleCollapse } = useSidebarStore();

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

  const toggleExpanded = (name: string) => {
    setExpandedItems((prev) =>
      prev.includes(name) ? prev.filter((n) => n !== name) : [...prev, name]
    );
  };

  const isItemActive = (item: NavItem): boolean => {
    // Dashboard should only be active on exact match
    if (item.href === '/dashboard') {
      return pathname === item.href;
    }
    // Check if current path matches item or its children
    if (pathname === item.href || pathname.startsWith(item.href + '/')) {
      return true;
    }
    // Check children
    if (item.children) {
      return item.children.some(
        (child) => pathname === child.href || pathname.startsWith(child.href + '/')
      );
    }
    return false;
  };

  const renderNavItem = (item: NavItem, isChild = false) => {
    const hasChildren = item.children && item.children.length > 0;
    const isActive = isItemActive(item);
    const isExpanded = expandedItems.includes(item.name);
    const isChildActive = item.children?.some(
      (child) => pathname === child.href || pathname.startsWith(child.href + '/')
    );

    if (hasChildren) {
      return (
        <div key={item.name}>
          <button
            onClick={() => toggleExpanded(item.name)}
            className={cn(
              'w-full flex items-center gap-2 px-2 py-1.5 text-xs font-mono transition-all duration-150',
              isChildActive
                ? 'bg-white/10 text-white'
                : 'text-white/60 hover:text-white hover:bg-white/5'
            )}
          >
            <item.icon className="w-3.5 h-3.5 flex-shrink-0" />
            {!isCollapsed && (
              <>
                <span className="flex-1 text-left">{item.name}</span>
                <ChevronDown
                  className={cn(
                    'w-3 h-3 transition-transform duration-200',
                    isExpanded ? 'rotate-0' : '-rotate-90'
                  )}
                />
              </>
            )}
          </button>
          {!isCollapsed && isExpanded && (
            <div className="ml-3 border-l border-white/10 pl-2 mt-0.5 space-y-0.5">
              {item.children?.map((child) => renderNavItem(child, true))}
            </div>
          )}
        </div>
      );
    }

    return (
      <Link
        key={item.name}
        href={item.href}
        title={isCollapsed ? item.name : undefined}
        className={cn(
          'flex items-center gap-2 px-2 py-1.5 text-xs font-mono transition-all duration-150',
          isActive
            ? 'bg-white text-black'
            : 'text-white/60 hover:text-white hover:bg-white/5',
          isChild && 'text-[11px]'
        )}
      >
        <item.icon className="w-3.5 h-3.5 flex-shrink-0" />
        {!isCollapsed && (
          <>
            <span>{item.name}</span>
            {isActive && <span className="ml-auto text-[10px]">_</span>}
          </>
        )}
      </Link>
    );
  };

  return (
    <div
      className={cn(
        'flex flex-col h-full bg-black text-white border-r border-white/10 transition-all duration-300',
        isCollapsed ? 'w-14' : 'w-56'
      )}
    >
      {/* Logo */}
      <div className="flex items-center gap-2 px-3 py-4 border-b border-white/10">
        <div className="w-7 h-7 bg-white flex items-center justify-center flex-shrink-0">
          <Terminal className="w-4 h-4 text-black" />
        </div>
        {!isCollapsed && (
          <>
            <span className="text-sm font-mono font-bold tracking-tight">AGENTVERSE</span>
            <span className="text-[10px] font-mono text-white/40 ml-auto">v1.0</span>
          </>
        )}
      </div>

      {/* Status indicator */}
      {!isCollapsed && (
        <div className="px-4 py-2 border-b border-white/10">
          <div className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
            <span className="text-[10px] font-mono text-white/50 uppercase tracking-wider">
              System Online
            </span>
          </div>
        </div>
      )}

      {/* Collapse Toggle */}
      <div className="px-2 py-2 border-b border-white/10">
        <button
          onClick={toggleCollapse}
          className="w-full flex items-center justify-center gap-2 px-2 py-1.5 text-xs font-mono text-white/40 hover:text-white hover:bg-white/5 transition-all duration-150"
          title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {isCollapsed ? (
            <ChevronRight className="w-4 h-4" />
          ) : (
            <>
              <ChevronLeft className="w-4 h-4" />
              <span>Collapse</span>
            </>
          )}
        </button>
      </div>

      {/* Main Navigation */}
      <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto">
        {!isCollapsed && (
          <div className="px-2 py-1.5">
            <span className="text-[10px] font-mono text-white/30 uppercase tracking-wider">
              Navigation
            </span>
          </div>
        )}
        {navigation
          .filter((item) => {
            if (item.roleRequired) {
              const userRole = (session?.user as { role?: string } | undefined)?.role;
              return userRole === item.roleRequired || userRole === 'admin';
            }
            return true;
          })
          .map((item) => renderNavItem(item))}
      </nav>

      {/* Secondary Navigation */}
      <div className="px-2 py-3 border-t border-white/10">
        {!isCollapsed && (
          <div className="px-2 py-1.5">
            <span className="text-[10px] font-mono text-white/30 uppercase tracking-wider">
              System
            </span>
          </div>
        )}
        {secondaryNavigation.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.name}
              href={item.href}
              title={isCollapsed ? item.name : undefined}
              className={cn(
                'flex items-center gap-2 px-2 py-1.5 text-xs font-mono transition-all duration-150',
                isActive
                  ? 'bg-white text-black'
                  : 'text-white/60 hover:text-white hover:bg-white/5'
              )}
            >
              <item.icon className="w-3.5 h-3.5 flex-shrink-0" />
              {!isCollapsed && <span>{item.name}</span>}
            </Link>
          );
        })}
      </div>

      {/* User Profile Section */}
      <div className="border-t border-white/10">
        <div className="relative">
          {/* User Menu Dropdown */}
          {showUserMenu && !isCollapsed && (
            <div className="absolute bottom-full left-0 right-0 mb-1 mx-2 bg-black border border-white/20 shadow-lg animate-slide-up">
              <div className="px-3 py-2 border-b border-white/10">
                <div className="text-[10px] font-mono text-white/40 uppercase tracking-wider">
                  Agent Profile
                </div>
              </div>
              <div className="px-3 py-3 border-b border-white/10">
                <div className="text-sm font-mono text-white truncate">
                  {session?.user?.name || 'Agent'}
                </div>
                <div className="text-[10px] font-mono text-white/40 truncate mt-0.5">
                  {session?.user?.email || 'agent@agentverse.io'}
                </div>
              </div>
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
              'w-full flex items-center gap-3 px-3 py-3 text-left transition-all duration-150',
              showUserMenu ? 'bg-white/5' : 'hover:bg-white/5',
              isCollapsed && 'justify-center'
            )}
            title={isCollapsed ? session?.user?.name || 'Agent' : undefined}
          >
            <div className="w-8 h-8 bg-gradient-to-br from-cyan-500 to-blue-500 flex items-center justify-center flex-shrink-0">
              <span className="text-xs font-mono font-bold text-black">{getUserInitials()}</span>
            </div>
            {!isCollapsed && (
              <>
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-mono text-white truncate">
                    {session?.user?.name || 'Agent'}
                  </div>
                  <div className="text-[10px] font-mono text-white/40 truncate">
                    {session?.user?.email?.split('@')[0] || 'agent'}
                  </div>
                </div>
                <ChevronUp
                  className={cn(
                    'w-4 h-4 text-white/40 transition-transform duration-200',
                    showUserMenu ? 'rotate-0' : 'rotate-180'
                  )}
                />
              </>
            )}
          </button>
        </div>

        {/* Status indicator */}
        {!isCollapsed && (
          <div className="px-4 py-2 border-t border-white/5">
            <div className="flex items-center justify-between text-[10px] font-mono text-white/20">
              <div className="flex items-center gap-1.5">
                <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
                <span>CONNECTED</span>
              </div>
              <span>v1.0</span>
            </div>
          </div>
        )}
      </div>

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
