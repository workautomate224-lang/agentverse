/**
 * 2D Replay Components
 * Reference: project.md §11 Phase 8, Interaction_design.md §5.17
 *
 * All replay components are READ-ONLY (C3 Compliant) - never trigger simulations.
 */

export { ReplayPlayer } from './ReplayPlayer';
export type { ReplayTimelineData } from './ReplayPlayer';

export { ReplayCanvas } from './ReplayCanvas';
export type {
  AgentState,
  EnvironmentState,
  WorldState,
  ZoneDefinition,
  LayerVisibility,
} from './ReplayCanvas';

export { ReplayControls } from './ReplayControls';
export type { TimelineMarker } from './ReplayControls';

export { ReplayLayerPanel } from './ReplayLayerPanel';
export { ReplayInspector } from './ReplayInspector';
export { ReplayTimeline } from './ReplayTimeline';
