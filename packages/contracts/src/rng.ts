/**
 * Random Number Generation Policy
 * Reference: project.md §5.3, §10.1
 *
 * CRITICAL INVARIANT:
 * Same RunConfig + seed + versions = same aggregated outcome
 *
 * All randomness in the simulation MUST go through seeded RNG.
 * This file defines the policy and utilities for deterministic randomness.
 */

// ============================================================================
// Seed Constants
// ============================================================================

/**
 * Maximum safe integer for seeds (2^32 - 1)
 * We use 32-bit seeds for compatibility with most RNG implementations
 */
export const MAX_SEED = 0xFFFFFFFF;

/**
 * Minimum valid seed value
 */
export const MIN_SEED = 0;

/**
 * Default seed for development/testing
 */
export const DEFAULT_SEED = 42;

/**
 * Number of seeds for variance analysis (multi-seed strategy)
 */
export const DEFAULT_MULTI_SEED_COUNT = 10;

/**
 * Maximum seeds allowed per run configuration
 */
export const MAX_SEEDS_PER_RUN = 100;

// ============================================================================
// Seed Validation
// ============================================================================

export interface SeedValidationResult {
  isValid: boolean;
  errors: string[];
  normalizedSeed?: number;
}

/**
 * Validates and normalizes a seed value
 */
export function validateSeed(seed: unknown): SeedValidationResult {
  const errors: string[] = [];

  // Check type
  if (typeof seed !== 'number') {
    errors.push(`Seed must be a number, got ${typeof seed}`);
    return { isValid: false, errors };
  }

  // Check for NaN
  if (Number.isNaN(seed)) {
    errors.push('Seed cannot be NaN');
    return { isValid: false, errors };
  }

  // Check for infinity
  if (!Number.isFinite(seed)) {
    errors.push('Seed must be a finite number');
    return { isValid: false, errors };
  }

  // Normalize to integer
  const normalizedSeed = Math.floor(Math.abs(seed)) % (MAX_SEED + 1);

  return {
    isValid: true,
    errors: [],
    normalizedSeed,
  };
}

/**
 * Validates an array of seeds
 */
export function validateSeeds(seeds: unknown[]): SeedValidationResult {
  const errors: string[] = [];
  const normalizedSeeds: number[] = [];

  if (!Array.isArray(seeds)) {
    errors.push('Seeds must be an array');
    return { isValid: false, errors };
  }

  if (seeds.length === 0) {
    errors.push('Seeds array cannot be empty');
    return { isValid: false, errors };
  }

  if (seeds.length > MAX_SEEDS_PER_RUN) {
    errors.push(`Too many seeds: ${seeds.length} exceeds maximum of ${MAX_SEEDS_PER_RUN}`);
    return { isValid: false, errors };
  }

  for (let i = 0; i < seeds.length; i++) {
    const result = validateSeed(seeds[i]);
    if (!result.isValid) {
      errors.push(`Seed at index ${i}: ${result.errors.join(', ')}`);
    } else if (result.normalizedSeed !== undefined) {
      normalizedSeeds.push(result.normalizedSeed);
    }
  }

  // Check for duplicates
  const uniqueSeeds = new Set(normalizedSeeds);
  if (uniqueSeeds.size !== normalizedSeeds.length) {
    errors.push('Seeds array contains duplicates');
  }

  return {
    isValid: errors.length === 0,
    errors,
    normalizedSeed: normalizedSeeds[0], // Return first for convenience
  };
}

// ============================================================================
// Seed Generation
// ============================================================================

/**
 * Generates a cryptographically random seed
 * For use in production when no specific seed is requested
 */
export function generateRandomSeed(): number {
  // In browser or Node.js with crypto
  if (typeof crypto !== 'undefined' && crypto.getRandomValues) {
    const array = new Uint32Array(1);
    crypto.getRandomValues(array);
    return array[0];
  }

  // Fallback (less secure, should not be used in production)
  return Math.floor(Math.random() * MAX_SEED);
}

/**
 * Generates multiple unique random seeds
 */
export function generateRandomSeeds(count: number): number[] {
  if (count <= 0 || count > MAX_SEEDS_PER_RUN) {
    throw new Error(`Invalid seed count: ${count}`);
  }

  const seeds = new Set<number>();
  while (seeds.size < count) {
    seeds.add(generateRandomSeed());
  }

  return Array.from(seeds);
}

/**
 * Generates deterministic sub-seeds from a primary seed
 * Used for multi-seed runs where seeds need to be reproducible
 */
export function generateSubSeeds(primarySeed: number, count: number): number[] {
  if (count <= 0 || count > MAX_SEEDS_PER_RUN) {
    throw new Error(`Invalid seed count: ${count}`);
  }

  const seeds: number[] = [];

  // Use a simple hash-based generator for deterministic sub-seeds
  // This ensures same primary seed always produces same sub-seeds
  let current = primarySeed;

  for (let i = 0; i < count; i++) {
    // Simple xorshift32 to generate sub-seeds
    current ^= current << 13;
    current ^= current >>> 17;
    current ^= current << 5;
    seeds.push(Math.abs(current) % (MAX_SEED + 1));
  }

  return seeds;
}

// ============================================================================
// Seed Derivation (for hierarchical randomness)
// ============================================================================

/**
 * Derives a child seed from a parent seed and a domain string
 * Used for creating independent RNG streams within a simulation
 *
 * Example domains:
 * - "agent:123" - RNG for agent with ID 123
 * - "event:456" - RNG for event with ID 456
 * - "scheduler" - RNG for the scheduler
 */
export function deriveSeed(parentSeed: number, domain: string): number {
  // Simple string hash combined with parent seed
  let hash = parentSeed;

  for (let i = 0; i < domain.length; i++) {
    const char = domain.charCodeAt(i);
    hash = ((hash << 5) - hash + char) | 0; // Convert to 32-bit integer
  }

  return Math.abs(hash) % (MAX_SEED + 1);
}

/**
 * Derives a seed for a specific tick
 * Ensures each tick has deterministic randomness
 */
export function deriveTickSeed(runSeed: number, tick: number): number {
  return deriveSeed(runSeed, `tick:${tick}`);
}

/**
 * Derives a seed for a specific agent at a specific tick
 */
export function deriveAgentTickSeed(
  runSeed: number,
  agentId: string,
  tick: number
): number {
  return deriveSeed(runSeed, `agent:${agentId}:tick:${tick}`);
}

// ============================================================================
// RNG Stream Types (for documentation/type safety)
// ============================================================================

/**
 * Domains that require separate RNG streams
 */
export type RNGDomain =
  | 'scheduler'      // Agent activation order
  | 'agent'          // Agent decision making
  | 'event'          // Event probability/intensity
  | 'environment'    // Environmental randomness
  | 'observation'    // Observation noise
  | 'sampling';      // Telemetry sampling

/**
 * Describes an RNG stream for audit/debugging
 */
export interface RNGStreamDescriptor {
  domain: RNGDomain;
  parentSeed: number;
  derivedSeed: number;
  derivationPath: string;
}

/**
 * Creates a descriptor for an RNG stream
 */
export function createRNGStreamDescriptor(
  domain: RNGDomain,
  parentSeed: number,
  derivationPath: string
): RNGStreamDescriptor {
  return {
    domain,
    parentSeed,
    derivedSeed: deriveSeed(parentSeed, derivationPath),
    derivationPath,
  };
}

// ============================================================================
// Determinism Policy Checks
// ============================================================================

/**
 * Checks that are performed to ensure determinism is maintained
 */
export interface DeterminismCheckResult {
  isPassing: boolean;
  checks: {
    name: string;
    passed: boolean;
    message: string;
  }[];
}

/**
 * Validates that a seed configuration will produce deterministic results
 */
export function validateDeterminismConfig(config: {
  seed: number;
  additionalSeeds?: number[];
  rngDomains?: RNGDomain[];
}): DeterminismCheckResult {
  const checks: DeterminismCheckResult['checks'] = [];

  // Check primary seed
  const seedResult = validateSeed(config.seed);
  checks.push({
    name: 'Primary seed validation',
    passed: seedResult.isValid,
    message: seedResult.isValid
      ? `Valid seed: ${seedResult.normalizedSeed}`
      : seedResult.errors.join(', '),
  });

  // Check additional seeds if present
  if (config.additionalSeeds && config.additionalSeeds.length > 0) {
    const additionalResult = validateSeeds(config.additionalSeeds);
    checks.push({
      name: 'Additional seeds validation',
      passed: additionalResult.isValid,
      message: additionalResult.isValid
        ? `${config.additionalSeeds.length} valid additional seeds`
        : additionalResult.errors.join(', '),
    });
  }

  // Check that all required domains are covered
  const requiredDomains: RNGDomain[] = ['scheduler', 'agent', 'event'];
  const providedDomains = config.rngDomains || requiredDomains;
  const missingDomains = requiredDomains.filter(d => !providedDomains.includes(d));

  checks.push({
    name: 'RNG domain coverage',
    passed: missingDomains.length === 0,
    message: missingDomains.length === 0
      ? 'All required RNG domains covered'
      : `Missing domains: ${missingDomains.join(', ')}`,
  });

  return {
    isPassing: checks.every(c => c.passed),
    checks,
  };
}

// ============================================================================
// Seed Serialization (for storage/transmission)
// ============================================================================

/**
 * Serializes seed configuration to a compact string
 */
export function serializeSeedConfig(config: {
  primary: number;
  additional?: number[];
}): string {
  if (!config.additional || config.additional.length === 0) {
    return String(config.primary);
  }
  return `${config.primary}:${config.additional.join(',')}`;
}

/**
 * Deserializes a seed configuration string
 */
export function deserializeSeedConfig(serialized: string): {
  primary: number;
  additional: number[];
} {
  const parts = serialized.split(':');
  const primary = parseInt(parts[0], 10);
  const additional = parts[1]
    ? parts[1].split(',').map(s => parseInt(s, 10))
    : [];

  return { primary, additional };
}

// ============================================================================
// Golden Seed Registry (for testing)
// ============================================================================

/**
 * Well-known seeds used for determinism testing
 * These should produce known/verified outputs
 */
export const GOLDEN_SEEDS = {
  // Standard test seed
  TEST_STANDARD: 12345,

  // Edge case seeds
  TEST_ZERO: 0,
  TEST_MAX: MAX_SEED,
  TEST_MIDPOINT: Math.floor(MAX_SEED / 2),

  // Specific scenario seeds (add as needed for regression tests)
  REGRESSION_BASELINE: 98765,
  REGRESSION_EDGE_CASE: 11111,
} as const;

export type GoldenSeedName = keyof typeof GOLDEN_SEEDS;

/**
 * Gets a golden seed by name
 */
export function getGoldenSeed(name: GoldenSeedName): number {
  return GOLDEN_SEEDS[name];
}
