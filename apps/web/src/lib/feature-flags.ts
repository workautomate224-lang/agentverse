/**
 * Feature Flags Configuration
 *
 * Controls which features are enabled in the application.
 * Reference: blueprint_v2.md - Migration strategy
 */

// Feature flag environment variable or default to enabled for development
export const FEATURE_FLAGS = {
  /**
   * BLUEPRINT_V2_WIZARD
   *
   * When enabled:
   * - Create Project Wizard Step 1 includes goal analysis, clarifying questions, and blueprint preview
   * - Project cannot be created without Blueprint v1
   * - Overview shows read-only blueprint summary (no clarification flow)
   *
   * When disabled (legacy):
   * - Step 1 only has goal textarea
   * - Blueprint created after project creation
   * - Clarification happens on Overview page
   */
  BLUEPRINT_V2_WIZARD: process.env.NEXT_PUBLIC_BLUEPRINT_V2_WIZARD === 'true' ||
    process.env.NODE_ENV === 'development', // Enabled by default in development
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
