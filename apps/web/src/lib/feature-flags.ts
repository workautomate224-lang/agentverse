/**
 * Feature Flags Configuration
 *
 * Controls which features are enabled in the application.
 * Reference: blueprint_v3.md - Wizard-only Blueprint enforcement
 */

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
