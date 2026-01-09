/**
 * Versioning Strategy
 * Reference: project.md §6.5, §12.1
 *
 * All artifacts must have version fields for reproducibility.
 * Same RunConfig + seed + versions = same outcome (guaranteed)
 */

import { ArtifactVersion } from './common';

// ============================================================================
// Current Platform Versions (bump these when making changes)
// ============================================================================

/**
 * Current engine version.
 * Bump MAJOR for breaking simulation logic changes.
 * Bump MINOR for backward-compatible algorithm improvements.
 * Bump PATCH for bug fixes that don't change outcomes.
 */
export const CURRENT_ENGINE_VERSION = '1.0.0';

/**
 * Current ruleset version.
 * Bump when agent rules, event processing, or scheduler logic changes.
 */
export const CURRENT_RULESET_VERSION = '1.0.0';

/**
 * Current schema version.
 * Bump when data contract structures change.
 */
export const CURRENT_SCHEMA_VERSION = '1.0.0';

/**
 * Dataset version is dynamic (typically a date string).
 * This default is used when no specific dataset is loaded.
 */
export const DEFAULT_DATASET_VERSION = '2026-01-08';

// ============================================================================
// Version Object Utilities
// ============================================================================

/**
 * Creates a complete ArtifactVersion with current defaults
 */
export function createCurrentVersion(
  datasetVersion?: string
): ArtifactVersion {
  return {
    engine_version: CURRENT_ENGINE_VERSION,
    ruleset_version: CURRENT_RULESET_VERSION,
    dataset_version: datasetVersion ?? DEFAULT_DATASET_VERSION,
    schema_version: CURRENT_SCHEMA_VERSION,
  };
}

/**
 * Merges partial version with current defaults
 */
export function mergeWithCurrentVersion(
  partial: Partial<ArtifactVersion>
): ArtifactVersion {
  return {
    engine_version: partial.engine_version ?? CURRENT_ENGINE_VERSION,
    ruleset_version: partial.ruleset_version ?? CURRENT_RULESET_VERSION,
    dataset_version: partial.dataset_version ?? DEFAULT_DATASET_VERSION,
    schema_version: partial.schema_version ?? CURRENT_SCHEMA_VERSION,
  };
}

// ============================================================================
// Semantic Version Parsing
// ============================================================================

export interface ParsedVersion {
  major: number;
  minor: number;
  patch: number;
  prerelease?: string;
  isValid: boolean;
}

/**
 * Parses a semantic version string (e.g., "1.2.3" or "1.2.3-beta.1")
 */
export function parseVersion(version: string): ParsedVersion {
  const regex = /^(\d+)\.(\d+)\.(\d+)(?:-(.+))?$/;
  const match = version.match(regex);

  if (!match) {
    return { major: 0, minor: 0, patch: 0, isValid: false };
  }

  return {
    major: parseInt(match[1], 10),
    minor: parseInt(match[2], 10),
    patch: parseInt(match[3], 10),
    prerelease: match[4],
    isValid: true,
  };
}

/**
 * Formats a ParsedVersion back to string
 */
export function formatVersion(parsed: ParsedVersion): string {
  const base = `${parsed.major}.${parsed.minor}.${parsed.patch}`;
  return parsed.prerelease ? `${base}-${parsed.prerelease}` : base;
}

// ============================================================================
// Version Comparison
// ============================================================================

export type VersionComparison = 'older' | 'same' | 'newer' | 'incompatible';

/**
 * Compares two version strings.
 * Returns:
 * - 'older': a < b
 * - 'same': a === b
 * - 'newer': a > b
 * - 'incompatible': cannot compare (invalid versions)
 */
export function compareVersions(a: string, b: string): VersionComparison {
  const parsedA = parseVersion(a);
  const parsedB = parseVersion(b);

  if (!parsedA.isValid || !parsedB.isValid) {
    return 'incompatible';
  }

  // Compare major
  if (parsedA.major !== parsedB.major) {
    return parsedA.major < parsedB.major ? 'older' : 'newer';
  }

  // Compare minor
  if (parsedA.minor !== parsedB.minor) {
    return parsedA.minor < parsedB.minor ? 'older' : 'newer';
  }

  // Compare patch
  if (parsedA.patch !== parsedB.patch) {
    return parsedA.patch < parsedB.patch ? 'older' : 'newer';
  }

  // Handle prerelease (prerelease < release)
  if (parsedA.prerelease && !parsedB.prerelease) {
    return 'older';
  }
  if (!parsedA.prerelease && parsedB.prerelease) {
    return 'newer';
  }

  return 'same';
}

/**
 * Checks if two artifact versions are fully compatible
 */
export function areVersionsCompatible(a: ArtifactVersion, b: ArtifactVersion): boolean {
  return (
    a.engine_version === b.engine_version &&
    a.ruleset_version === b.ruleset_version &&
    a.schema_version === b.schema_version
    // Note: dataset_version can differ (different data snapshots are okay)
  );
}

/**
 * Checks if a is compatible with or newer than b (for forward compatibility)
 */
export function isVersionCompatibleOrNewer(a: string, b: string): boolean {
  const comparison = compareVersions(a, b);
  return comparison === 'same' || comparison === 'newer';
}

// ============================================================================
// Version Validation
// ============================================================================

export interface VersionValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
}

/**
 * Validates a version string format
 */
export function validateVersionString(version: string): VersionValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  if (!version || version.trim() === '') {
    errors.push('Version string cannot be empty');
    return { isValid: false, errors, warnings };
  }

  const parsed = parseVersion(version);
  if (!parsed.isValid) {
    errors.push(`Invalid version format: "${version}". Expected format: MAJOR.MINOR.PATCH`);
    return { isValid: false, errors, warnings };
  }

  if (parsed.prerelease) {
    warnings.push('Prerelease versions may not be stable for production use');
  }

  return { isValid: true, errors, warnings };
}

/**
 * Validates a complete ArtifactVersion
 */
export function validateArtifactVersion(version: ArtifactVersion): VersionValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  // Validate each version field
  const fields: (keyof ArtifactVersion)[] = [
    'engine_version',
    'ruleset_version',
    'schema_version',
  ];

  for (const field of fields) {
    const result = validateVersionString(version[field]);
    if (!result.isValid) {
      errors.push(...result.errors.map(e => `${field}: ${e}`));
    }
    warnings.push(...result.warnings.map(w => `${field}: ${w}`));
  }

  // Dataset version can be a date or version string
  if (!version.dataset_version || version.dataset_version.trim() === '') {
    errors.push('dataset_version cannot be empty');
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
  };
}

// ============================================================================
// Version Drift Detection
// ============================================================================

export interface VersionDrift {
  field: keyof ArtifactVersion;
  currentVersion: string;
  artifactVersion: string;
  comparison: VersionComparison;
  isMajorDrift: boolean;
}

/**
 * Detects drift between an artifact's version and current platform versions
 */
export function detectVersionDrift(artifactVersion: ArtifactVersion): VersionDrift[] {
  const drifts: VersionDrift[] = [];
  const current = createCurrentVersion();

  const fields: (keyof Omit<ArtifactVersion, 'dataset_version'>)[] = [
    'engine_version',
    'ruleset_version',
    'schema_version',
  ];

  for (const field of fields) {
    const comparison = compareVersions(current[field], artifactVersion[field]);
    if (comparison !== 'same') {
      const currentParsed = parseVersion(current[field]);
      const artifactParsed = parseVersion(artifactVersion[field]);

      drifts.push({
        field,
        currentVersion: current[field],
        artifactVersion: artifactVersion[field],
        comparison,
        isMajorDrift: currentParsed.major !== artifactParsed.major,
      });
    }
  }

  return drifts;
}

// ============================================================================
// Version Fingerprint (for reproducibility checks)
// ============================================================================

/**
 * Creates a deterministic fingerprint from versions + seed
 * Used for reproducibility verification
 */
export function createVersionFingerprint(
  version: ArtifactVersion,
  seed: number
): string {
  const components = [
    `engine:${version.engine_version}`,
    `ruleset:${version.ruleset_version}`,
    `dataset:${version.dataset_version}`,
    `schema:${version.schema_version}`,
    `seed:${seed}`,
  ];
  return components.join('|');
}

/**
 * Parses a version fingerprint back to components
 */
export function parseVersionFingerprint(fingerprint: string): {
  version: ArtifactVersion;
  seed: number;
} | null {
  const regex = /engine:(.+)\|ruleset:(.+)\|dataset:(.+)\|schema:(.+)\|seed:(\d+)/;
  const match = fingerprint.match(regex);

  if (!match) {
    return null;
  }

  return {
    version: {
      engine_version: match[1],
      ruleset_version: match[2],
      dataset_version: match[3],
      schema_version: match[4],
    },
    seed: parseInt(match[5], 10),
  };
}

// ============================================================================
// Migration Support
// ============================================================================

export interface MigrationPath {
  fromVersion: string;
  toVersion: string;
  migrationId: string;
  isAutomatic: boolean;
  requiresRerun: boolean;
  description: string;
}

/**
 * Determines if a migration path exists between versions
 * (Stub - actual migration registry would be in backend)
 */
export function getMigrationPath(
  from: string,
  to: string
): MigrationPath | null {
  // This is a stub. In production, this would query a migration registry.
  // For now, we assume adjacent minor versions are auto-migratable.

  const parsedFrom = parseVersion(from);
  const parsedTo = parseVersion(to);

  if (!parsedFrom.isValid || !parsedTo.isValid) {
    return null;
  }

  // Same version, no migration needed
  if (compareVersions(from, to) === 'same') {
    return null;
  }

  // Major version changes require manual migration
  if (parsedFrom.major !== parsedTo.major) {
    return {
      fromVersion: from,
      toVersion: to,
      migrationId: `major-${from}-to-${to}`,
      isAutomatic: false,
      requiresRerun: true,
      description: 'Major version migration requires manual intervention',
    };
  }

  // Minor/patch changes can be auto-migrated
  return {
    fromVersion: from,
    toVersion: to,
    migrationId: `auto-${from}-to-${to}`,
    isAutomatic: true,
    requiresRerun: false,
    description: 'Automatic schema migration',
  };
}
