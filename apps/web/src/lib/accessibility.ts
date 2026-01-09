/**
 * Accessibility utilities
 * Reference: Interaction_design.md §9
 */

/**
 * Generate ARIA props for interactive elements
 */
export function ariaButton(label: string, pressed?: boolean) {
  return {
    'aria-label': label,
    'aria-pressed': pressed,
    role: 'button',
    tabIndex: 0,
  };
}

/**
 * Generate ARIA props for toggles
 */
export function ariaToggle(label: string, checked: boolean) {
  return {
    'aria-label': label,
    'aria-checked': checked,
    role: 'switch',
    tabIndex: 0,
  };
}

/**
 * Generate ARIA props for expandable sections
 */
export function ariaExpand(label: string, expanded: boolean, controlsId: string) {
  return {
    'aria-label': label,
    'aria-expanded': expanded,
    'aria-controls': controlsId,
    tabIndex: 0,
  };
}

/**
 * Generate ARIA props for live regions
 */
export function ariaLive(type: 'polite' | 'assertive' = 'polite') {
  return {
    'aria-live': type,
    role: type === 'assertive' ? 'alert' : 'status',
  };
}

/**
 * Generate ARIA props for loading states
 */
export function ariaLoading(isLoading: boolean, label: string) {
  return {
    'aria-busy': isLoading,
    'aria-label': isLoading ? `Loading ${label}...` : label,
  };
}

/**
 * Generate ARIA props for navigation
 */
export function ariaNav(label: string) {
  return {
    'aria-label': label,
    role: 'navigation',
  };
}

/**
 * Generate ARIA props for regions
 */
export function ariaRegion(label: string) {
  return {
    'aria-label': label,
    role: 'region',
  };
}

/**
 * Generate ARIA props for progress indicators
 */
export function ariaProgress(label: string, value: number, max: number = 100) {
  return {
    'aria-label': label,
    'aria-valuenow': value,
    'aria-valuemin': 0,
    'aria-valuemax': max,
    role: 'progressbar',
  };
}

/**
 * Generate ARIA props for lists
 */
export function ariaList(label: string, count: number) {
  return {
    'aria-label': `${label} (${count} items)`,
    role: 'list',
  };
}

/**
 * Keyboard event handler for Enter/Space activation
 */
export function onKeyboardActivate(handler: () => void) {
  return {
    onKeyDown: (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        handler();
      }
    },
  };
}

/**
 * Keyboard event handler for arrow key navigation
 */
export function onArrowKeyNav(
  direction: 'horizontal' | 'vertical' | 'both',
  handlers: {
    onUp?: () => void;
    onDown?: () => void;
    onLeft?: () => void;
    onRight?: () => void;
  }
) {
  return {
    onKeyDown: (e: React.KeyboardEvent) => {
      switch (e.key) {
        case 'ArrowUp':
          if (direction !== 'horizontal' && handlers.onUp) {
            e.preventDefault();
            handlers.onUp();
          }
          break;
        case 'ArrowDown':
          if (direction !== 'horizontal' && handlers.onDown) {
            e.preventDefault();
            handlers.onDown();
          }
          break;
        case 'ArrowLeft':
          if (direction !== 'vertical' && handlers.onLeft) {
            e.preventDefault();
            handlers.onLeft();
          }
          break;
        case 'ArrowRight':
          if (direction !== 'vertical' && handlers.onRight) {
            e.preventDefault();
            handlers.onRight();
          }
          break;
      }
    },
  };
}

/**
 * Focus trap for modals/drawers
 */
export function createFocusTrap(containerRef: React.RefObject<HTMLElement>) {
  const getFocusableElements = () => {
    if (!containerRef.current) return [];
    return Array.from(
      containerRef.current.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      )
    ).filter(el => !el.hasAttribute('disabled'));
  };

  return {
    onKeyDown: (e: React.KeyboardEvent) => {
      if (e.key !== 'Tab') return;

      const focusable = getFocusableElements();
      if (focusable.length === 0) return;

      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    },
  };
}

/**
 * Skip link target ID generator
 */
export const SKIP_LINK_TARGETS = {
  mainContent: 'main-content',
  navigation: 'main-nav',
  search: 'search-input',
} as const;

/**
 * Color-blind friendly status colors with patterns/icons
 */
export const STATUS_INDICATORS = {
  success: { color: 'text-green-400', icon: 'CheckCircle', pattern: 'solid' },
  warning: { color: 'text-yellow-400', icon: 'AlertTriangle', pattern: 'dashed' },
  error: { color: 'text-red-400', icon: 'XCircle', pattern: 'dotted' },
  info: { color: 'text-cyan-400', icon: 'Info', pattern: 'solid' },
  pending: { color: 'text-white/40', icon: 'Clock', pattern: 'dashed' },
  running: { color: 'text-blue-400', icon: 'Loader2', pattern: 'animated' },
} as const;

export type StatusType = keyof typeof STATUS_INDICATORS;
