'use client';

/**
 * 2D Replay Page
 * Reference: project.md §11 Phase 8, Interaction_design.md §5.17
 *
 * Watch "what happened" in a node/run using telemetry only.
 * READ-ONLY (C3 Compliant) - Never triggers simulations.
 */

import React, { useState, useCallback, useMemo } from 'react';
import dynamic from 'next/dynamic';
import { useRouter, useSearchParams } from 'next/navigation';
import { useProject } from '@/components/project/ProjectContext';
import { PageLoading } from '@/components/ui/page-loading';
import { GuidancePanel } from '@/components/pil/v2/GuidancePanel';

// Dynamic import for heavy canvas/PixiJS component
const ReplayPlayer = dynamic(
  () => import('@/components/replay').then((mod) => mod.ReplayPlayer),
  {
    loading: () => <PageLoading type="graph" title="2D Replay" />,
    ssr: false,
  }
);
import {
  useLoadReplay,
  useReplayState,
  useRuns,
  useRun,
} from '@/hooks/useApi';
import type { LoadReplayRequest, ReplayAgentState, RunSummary } from '@/lib/api';
import type { WorldState } from '@/components/replay/ReplayCanvas';

export default function ReplayPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { projectId, nodes } = useProject();

  // Get node_id from URL params or use first node with outcome
  const nodeIdParam = searchParams.get('node_id');

  // Find the target node
  const targetNode = useMemo(() => {
    if (nodeIdParam) {
      return nodes.find(n => n.node_id === nodeIdParam);
    }
    // Find the most recent node with a completed outcome
    return nodes.find(n => n.has_outcome);
  }, [nodes, nodeIdParam]);

  // Fetch runs for the target node to find one with telemetry
  const { data: runsData } = useRuns({
    node_id: targetNode?.node_id,
    status: 'succeeded',
    limit: 10,
  });

  // Get the most recent completed run with results
  const latestRunSummary: RunSummary | undefined = useMemo(() => {
    if (!runsData || runsData.length === 0) return undefined;
    return runsData.find((run: RunSummary) => run.has_results);
  }, [runsData]);

  // Fetch full run details to get telemetry_ref
  const { data: fullRun } = useRun(latestRunSummary?.run_id);

  // Build storage ref from run's telemetry_ref
  const storageRef: LoadReplayRequest | null = useMemo(() => {
    if (!fullRun?.outputs?.telemetry_ref) return null;
    return {
      storage_ref: fullRun.outputs.telemetry_ref,
      preload_ticks: 100,
      node_id: targetNode?.node_id,
    };
  }, [fullRun, targetNode]);

  // Current tick for state fetching
  const [currentTick, setCurrentTick] = useState(0);

  // Load replay timeline
  const {
    data: timeline,
    isLoading: isTimelineLoading,
    error: timelineError,
    refetch: refetchTimeline,
  } = useLoadReplay(storageRef);

  // Fetch current world state
  const {
    data: replayWorldState,
    isLoading: isStateLoading,
  } = useReplayState(currentTick, storageRef);

  // Convert API world state to component world state
  const worldState: WorldState | null = useMemo(() => {
    if (!replayWorldState) return null;

    return {
      tick: replayWorldState.tick,
      timestamp: replayWorldState.timestamp,
      agents: Object.fromEntries(
        Object.entries(replayWorldState.agents).map(([id, agentData]) => {
          const agent = agentData as ReplayAgentState;
          return [
            id,
            {
              agent_id: agent.agent_id,
              tick: agent.tick,
              position: agent.position,
              segment: agent.segment,
              region: agent.region,
              stance: agent.stance,
              emotion: agent.emotion,
              influence: agent.influence,
              exposure: agent.exposure,
              last_action: agent.last_action,
              last_event: agent.last_event,
              beliefs: agent.beliefs,
            },
          ];
        })
      ),
      environment: {
        tick: replayWorldState.environment.tick,
        variables: replayWorldState.environment.variables,
        active_events: replayWorldState.environment.active_events,
        metrics: replayWorldState.environment.metrics,
      },
      event_log: replayWorldState.event_log,
    };
  }, [replayWorldState]);

  // Handlers
  const handleSeekToTick = useCallback((tick: number) => {
    setCurrentTick(tick);
  }, []);

  const handleOpenNode = useCallback((nodeId: string) => {
    router.push(`/dashboard/nodes/${nodeId}`);
  }, [router]);

  const handleOpenReliability = useCallback((nodeId: string) => {
    router.push(`/dashboard/projects/${projectId}/reliability?node_id=${nodeId}`);
  }, [router, projectId]);

  const handleRetry = useCallback(() => {
    refetchTimeline();
  }, [refetchTimeline]);

  // Error message
  const errorMessage = useMemo(() => {
    if (timelineError) {
      return timelineError instanceof Error
        ? timelineError.message
        : 'Failed to load replay data';
    }
    if (!targetNode) {
      return 'No completed runs with telemetry data found. Run a simulation first.';
    }
    if (!fullRun?.outputs?.telemetry_ref) {
      return 'This node does not have telemetry data for replay. Re-run with logging enabled.';
    }
    return null;
  }, [timelineError, targetNode, fullRun]);

  // Timeline data for the player
  const timelineData = useMemo(() => {
    if (!timeline) return null;
    return {
      run_id: timeline.run_id,
      node_id: timeline.node_id,
      total_ticks: timeline.total_ticks,
      keyframe_ticks: timeline.keyframe_ticks,
      event_markers: timeline.event_markers,
      duration_seconds: timeline.duration_seconds,
      tick_rate: timeline.tick_rate,
      seed_used: timeline.seed_used,
      agent_count: timeline.agent_count,
      segment_distribution: timeline.segment_distribution,
      region_distribution: timeline.region_distribution,
      metrics_summary: timeline.metrics_summary,
    };
  }, [timeline]);

  return (
    <div className="h-full flex flex-col">
      <div className="px-4 pt-4 flex-shrink-0">
        <GuidancePanel projectId={projectId} section="telemetry" className="mb-4" />
      </div>
      <div className="flex-1 min-h-0">
        <ReplayPlayer
          timeline={timelineData}
          worldState={worldState}
          isLoading={isTimelineLoading || isStateLoading}
          error={errorMessage}
          storageRef={storageRef}
          onSeekToTick={handleSeekToTick}
          onOpenNode={handleOpenNode}
          onOpenReliability={handleOpenReliability}
          onRetry={handleRetry}
        />
      </div>
    </div>
  );
}
