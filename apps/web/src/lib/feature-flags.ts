/**
 * Feature Flags Configuration
 *
 * Controls which features are enabled in the application.
 * Reference: DEMO2_MVP_EXECUTION.md - MVP Mode Feature Gating
 */

// Product mode from environment variable
export type ProductMode = 'MVP_DEMO2' | 'FULL';

export const PRODUCT_MODE: ProductMode =
  (process.env.NEXT_PUBLIC_PRODUCT_MODE as ProductMode) || 'MVP_DEMO2';

/**
 * Check if running in MVP Demo2 mode
 */
export function isMvpMode(): boolean {
  return PRODUCT_MODE === 'MVP_DEMO2';
}

/**
 * Demo2 MVP - Enabled routes (keep visible)
 * These are the core Demo2 user journey routes
 */
export const MVP_ENABLED_ROUTES = [
  'overview',
  'data-personas',
  'event-lab',
  'run-center',
  'reports',
  'settings',
] as const;

/**
 * Demo2 MVP - Disabled routes (hide in navigation)
 * These features are hidden to reduce cognitive load
 */
export const MVP_DISABLED_ROUTES = [
  'universe-map',
  'rules',
  'reliability',
  'replay',
  'world-viewer',
  'society',
  'target',
] as const;

export type MvpRoute = (typeof MVP_ENABLED_ROUTES)[number];
export type DisabledRoute = (typeof MVP_DISABLED_ROUTES)[number];

/**
 * Check if a route is enabled in current product mode
 */
export function isRouteEnabled(route: string): boolean {
  if (PRODUCT_MODE === 'FULL') {
    return true;
  }

  // MVP_DEMO2 mode - only allow enabled routes
  return MVP_ENABLED_ROUTES.includes(route as MvpRoute);
}

/**
 * Check if a route is disabled in current product mode
 */
export function isRouteDisabled(route: string): boolean {
  if (PRODUCT_MODE === 'FULL') {
    return false;
  }

  return MVP_DISABLED_ROUTES.includes(route as DisabledRoute);
}

/**
 * Get the list of enabled routes for navigation
 */
export function getEnabledRoutes(): readonly string[] {
  if (PRODUCT_MODE === 'FULL') {
    return [...MVP_ENABLED_ROUTES, ...MVP_DISABLED_ROUTES];
  }

  return MVP_ENABLED_ROUTES;
}

/**
 * Get the list of disabled routes
 */
export function getDisabledRoutes(): readonly string[] {
  if (PRODUCT_MODE === 'FULL') {
    return [];
  }

  return MVP_DISABLED_ROUTES;
}

// Feature flag environment variable or default to enabled for development
export const FEATURE_FLAGS = {
  /**
   * BLUEPRINT_V2_WIZARD
   *
   * ALWAYS ENABLED (v3 enforcement)
   * - Create Project Wizard Step 1 includes goal analysis, clarifying questions, and blueprint preview
   * - Project cannot be created without Blueprint v1
   * - Overview shows read-only blueprint summary (no clarification flow)
   *
   * The legacy flow (Step 1 textarea only, clarification on Overview) is no longer supported.
   * Per blueprint_v3.md: All goal clarification + blueprint generation happens ONLY in Create Project → Step 1
   */
  BLUEPRINT_V2_WIZARD: true, // Always enabled per blueprint_v3.md - no legacy path
} as const;

export type FeatureFlagKey = keyof typeof FEATURE_FLAGS;

/**
 * Check if a feature flag is enabled
 */
export function isFeatureEnabled(flag: FeatureFlagKey): boolean {
  return FEATURE_FLAGS[flag] ?? false;
}

/**
 * Hook-compatible feature flag checker
 * Can be used in components to conditionally render based on flags
 */
export function useFeatureFlag(flag: FeatureFlagKey): boolean {
  return FEATURE_FLAGS[flag] ?? false;
}

/**
 * Hook for checking route availability in current product mode
 */
export function useRouteEnabled(route: string): boolean {
  return isRouteEnabled(route);
}

/**
 * Hook for checking if we're in MVP mode
 */
export function useMvpMode(): boolean {
  return isMvpMode();
}
