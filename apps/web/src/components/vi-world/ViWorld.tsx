'use client';

// ViWorld - Main Container Component
// Fetches persona data and renders the Vi World visualization
// Syncs with persistent backend world state

import React, { useState, useCallback, useMemo, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft,
  Maximize2,
  Minimize2,
  RefreshCw,
  Users,
  MessageCircle,
  Loader2,
  AlertCircle,
  Play,
  Pause,
  Square,
  Zap,
  Clock,
} from 'lucide-react';
import { api, WorldState as ApiWorldState, NPCState as ApiNPCState, WorldStatus } from '@/lib/api';
import { ViWorldCanvas } from './ViWorldCanvas';
import { NPCConfig, WorldStats, Gender } from './types';
import { getCharacterColors } from './utils/colors';

interface ViWorldProps {
  templateId: string;
}

// Infer gender from name (simple heuristic)
function inferGender(name: string): Gender {
  const femaleNames = [
    'sarah', 'emma', 'olivia', 'ava', 'sophia', 'isabella', 'mia', 'charlotte',
    'amelia', 'harper', 'evelyn', 'abigail', 'emily', 'elizabeth', 'sofia',
    'ella', 'madison', 'scarlett', 'victoria', 'aria', 'grace', 'chloe',
    'camila', 'penelope', 'riley', 'layla', 'lillian', 'nora', 'zoey', 'hannah',
    'lily', 'eleanor', 'hazel', 'violet', 'aurora', 'savannah', 'audrey',
    'brooklyn', 'bella', 'claire', 'skylar', 'lucy', 'paisley', 'everly',
    'anna', 'caroline', 'nova', 'genesis', 'emilia', 'kennedy', 'maya',
    'willow', 'kinsley', 'naomi', 'aaliyah', 'elena', 'sarah', 'ariana',
    'allison', 'gabriella', 'alice', 'madelyn', 'cora', 'ruby', 'eva',
    'serenity', 'autumn', 'adeline', 'hailey', 'gianna', 'valentina',
    'ellie', 'sophie', 'mary', 'maria', 'jennifer', 'linda', 'susan', 'jessica',
    'karen', 'nancy', 'margaret', 'sandra', 'ashley', 'dorothy', 'kimberly',
    'michelle', 'donna', 'carol', 'amanda', 'melissa', 'deborah', 'stephanie',
    'rebecca', 'laura', 'helen', 'sharon', 'cynthia', 'kathleen', 'amy', 'angela',
  ];

  const firstName = name.split(' ')[0].toLowerCase();
  return femaleNames.includes(firstName) ? 'female' : 'male';
}

export function ViWorld({ templateId }: ViWorldProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [stats, setStats] = useState<WorldStats>({
    population: 0,
    activeChats: 0,
    totalMessages: 0,
  });
  const [seed, setSeed] = useState(() => Date.now());
  const [worldCreated, setWorldCreated] = useState(false);

  // Fetch template data
  const { data: template, isLoading: templateLoading, error: templateError } = useQuery({
    queryKey: ['persona-template', templateId],
    queryFn: () => api.getPersonaTemplate(templateId),
    retry: 1,
  });

  // Fetch persona records
  const { data: records, isLoading: recordsLoading, error: recordsError } = useQuery({
    queryKey: ['persona-records', templateId],
    queryFn: () => api.listPersonas(templateId, { limit: 100 }),
    enabled: !!template,
    retry: 1,
  });

  // Fetch world state from backend
  const {
    data: worldState,
    isLoading: worldLoading,
    error: worldError,
    refetch: refetchWorld,
  } = useQuery({
    queryKey: ['world-state', templateId],
    queryFn: () => api.getWorldByTemplate(templateId),
    enabled: !!records && records.length > 0,
    retry: false, // Don't retry, we'll auto-create if not found
    refetchInterval: (query) => {
      // Poll every second if world is running
      const data = query.state.data as ApiWorldState | undefined;
      return data?.status === 'running' ? 1000 : false;
    },
  });

  // Auto-create world mutation
  const createWorldMutation = useMutation({
    mutationFn: () => api.autoCreateWorld(templateId),
    onSuccess: (data) => {
      setWorldCreated(true);
      queryClient.setQueryData(['world-state', templateId], data);
    },
  });

  // Control world mutation (start/pause/stop)
  const controlWorldMutation = useMutation({
    mutationFn: ({ action, speed }: { action: 'start' | 'pause' | 'resume' | 'stop' | 'reset'; speed?: number }) =>
      api.controlWorld(worldState!.id, action, speed),
    onSuccess: (data) => {
      queryClient.setQueryData(['world-state', templateId], data);
    },
  });

  // Auto-create world if it doesn't exist
  useEffect(() => {
    if (
      records &&
      records.length > 0 &&
      !worldState &&
      !worldLoading &&
      worldError &&
      !createWorldMutation.isPending &&
      !worldCreated
    ) {
      createWorldMutation.mutate();
    }
  }, [records, worldState, worldLoading, worldError, createWorldMutation, worldCreated]);

  // Convert persona records to NPC configs, incorporating backend state
  const npcConfigs: NPCConfig[] = useMemo(() => {
    if (!records || records.length === 0) return [];

    return records.map((record: any) => {
      const profile = record.profile || {};
      const name = profile.name || record.name || `Agent ${record.id.slice(0, 6)}`;
      const gender = inferGender(name);
      const colors = getCharacterColors(record.id);

      // Extract traits from profile
      const traits: string[] = [];
      if (profile.personality) traits.push(...profile.personality.split(',').map((t: string) => t.trim()));
      if (profile.occupation) traits.push(profile.occupation);
      if (profile.interests) traits.push(...profile.interests);

      // Get backend NPC state if available
      const backendState = worldState?.npc_states?.[record.id];

      return {
        id: record.id,
        name,
        gender,
        skinColor: colors.skinColor,
        hairColor: colors.hairColor,
        shirtColor: colors.shirtColor,
        pantsColor: colors.pantsColor,
        traits: traits.slice(0, 5),
        // Include backend position if available
        initialPosition: backendState?.position,
        initialState: backendState?.state,
        initialDirection: backendState?.direction,
      };
    });
  }, [records, worldState?.npc_states]);

  // Handlers
  const handleBack = useCallback(() => {
    router.back();
  }, [router]);

  const handleFullscreen = useCallback(() => {
    setIsFullscreen(!isFullscreen);
  }, [isFullscreen]);

  const handleRefresh = useCallback(() => {
    setSeed(Date.now());
    refetchWorld();
  }, [refetchWorld]);

  const handleStatsUpdate = useCallback((newStats: WorldStats) => {
    setStats(newStats);
  }, []);

  const handlePlay = useCallback(() => {
    if (worldState) {
      const action = worldState.status === 'paused' ? 'resume' : 'start';
      controlWorldMutation.mutate({ action });
    }
  }, [worldState, controlWorldMutation]);

  const handlePause = useCallback(() => {
    if (worldState) {
      controlWorldMutation.mutate({ action: 'pause' });
    }
  }, [worldState, controlWorldMutation]);

  const handleStop = useCallback(() => {
    if (worldState) {
      controlWorldMutation.mutate({ action: 'stop' });
    }
  }, [worldState, controlWorldMutation]);

  // Format uptime
  const formatUptime = (seconds: number): string => {
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${mins}m`;
  };

  // Loading state
  if (templateLoading || recordsLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-cyan-400 mx-auto mb-4" />
          <p className="text-slate-400 font-mono">Loading Vi World...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (templateError || recordsError) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center max-w-md">
          <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-white mb-2">Failed to Load World</h2>
          <p className="text-slate-400 mb-4">
            {(templateError as Error)?.message || (recordsError as Error)?.message || 'An error occurred'}
          </p>
          <button
            onClick={handleBack}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg transition-colors"
          >
            Go Back
          </button>
        </div>
      </div>
    );
  }

  // No personas state
  if (npcConfigs.length === 0) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center max-w-md">
          <Users className="w-12 h-12 text-slate-600 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-white mb-2">No Personas Found</h2>
          <p className="text-slate-400 mb-4">
            This template doesn&apos;t have any persona records yet. Generate some personas first to see them in Vi World.
          </p>
          <button
            onClick={handleBack}
            className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg transition-colors"
          >
            Go Back
          </button>
        </div>
      </div>
    );
  }

  // Creating world state
  if (createWorldMutation.isPending) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-cyan-400 mx-auto mb-4" />
          <p className="text-slate-400 font-mono">Creating persistent world...</p>
        </div>
      </div>
    );
  }

  const containerClass = isFullscreen
    ? 'fixed inset-0 z-50 bg-slate-950'
    : 'min-h-screen bg-slate-950';

  const isRunning = worldState?.status === 'running';
  const isPaused = worldState?.status === 'paused';

  return (
    <div className={containerClass}>
      {/* Header */}
      <div className="bg-slate-900/80 backdrop-blur-sm border-b border-slate-800 px-4 py-3">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          {/* Left: Back button and title */}
          <div className="flex items-center gap-4">
            <button
              onClick={handleBack}
              className="p-2 hover:bg-slate-800 rounded-lg transition-colors text-slate-400 hover:text-white"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <h1 className="text-lg font-bold text-white font-mono flex items-center gap-2">
                Vi World
                {isRunning && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-green-500/20 text-green-400 text-xs rounded-full">
                    <span className="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse" />
                    Live
                  </span>
                )}
                {isPaused && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-yellow-500/20 text-yellow-400 text-xs rounded-full">
                    Paused
                  </span>
                )}
              </h1>
              <p className="text-sm text-slate-400">
                {template?.name || 'Persona World'}
              </p>
            </div>
          </div>

          {/* Center: Simulation Controls */}
          <div className="flex items-center gap-2">
            {!isRunning ? (
              <button
                onClick={handlePlay}
                disabled={controlWorldMutation.isPending}
                className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-500 disabled:bg-green-800 text-white rounded-lg transition-colors font-mono text-sm"
              >
                <Play className="w-4 h-4" />
                {isPaused ? 'Resume' : 'Start'}
              </button>
            ) : (
              <button
                onClick={handlePause}
                disabled={controlWorldMutation.isPending}
                className="flex items-center gap-2 px-4 py-2 bg-yellow-600 hover:bg-yellow-500 disabled:bg-yellow-800 text-white rounded-lg transition-colors font-mono text-sm"
              >
                <Pause className="w-4 h-4" />
                Pause
              </button>
            )}
            <button
              onClick={handleStop}
              disabled={controlWorldMutation.isPending || worldState?.status === 'inactive'}
              className="p-2 bg-slate-700 hover:bg-slate-600 disabled:bg-slate-800 disabled:text-slate-600 text-white rounded-lg transition-colors"
              title="Stop Simulation"
            >
              <Square className="w-4 h-4" />
            </button>
          </div>

          {/* Right: Controls */}
          <div className="flex items-center gap-2">
            <button
              onClick={handleRefresh}
              className="p-2 hover:bg-slate-800 rounded-lg transition-colors text-slate-400 hover:text-white"
              title="Refresh World"
            >
              <RefreshCw className="w-5 h-5" />
            </button>
            <button
              onClick={handleFullscreen}
              className="p-2 hover:bg-slate-800 rounded-lg transition-colors text-slate-400 hover:text-white"
              title={isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
            >
              {isFullscreen ? (
                <Minimize2 className="w-5 h-5" />
              ) : (
                <Maximize2 className="w-5 h-5" />
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className={`flex flex-col ${isFullscreen ? 'h-[calc(100vh-64px)]' : ''}`}>
        {/* Canvas Container */}
        <div className="flex-1 p-4 flex items-center justify-center">
          <div className="relative rounded-xl overflow-hidden shadow-2xl border border-slate-800">
            <ViWorldCanvas
              npcs={npcConfigs}
              onStatsUpdate={handleStatsUpdate}
              width={800}
              height={608}
              seed={seed}
            />
          </div>
        </div>

        {/* Stats Bar */}
        <div className="bg-slate-900/80 backdrop-blur-sm border-t border-slate-800 px-4 py-3">
          <div className="max-w-7xl mx-auto flex items-center justify-center gap-8">
            <div className="flex items-center gap-2 text-slate-400">
              <Users className="w-4 h-4" />
              <span className="font-mono">
                Population: <span className="text-cyan-400">{stats.population}</span>
              </span>
            </div>
            <div className="flex items-center gap-2 text-slate-400">
              <MessageCircle className="w-4 h-4" />
              <span className="font-mono">
                Active Chats: <span className="text-green-400">{stats.activeChats}</span>
              </span>
            </div>
            <div className="flex items-center gap-2 text-slate-400">
              <span className="font-mono">
                Total Messages: <span className="text-purple-400">{worldState?.total_messages || stats.totalMessages}</span>
              </span>
            </div>
            {worldState && (
              <>
                <div className="flex items-center gap-2 text-slate-400">
                  <Zap className="w-4 h-4" />
                  <span className="font-mono">
                    Ticks: <span className="text-orange-400">{worldState.ticks_processed.toLocaleString()}</span>
                  </span>
                </div>
                <div className="flex items-center gap-2 text-slate-400">
                  <Clock className="w-4 h-4" />
                  <span className="font-mono">
                    Uptime: <span className="text-blue-400">{formatUptime(worldState.total_simulation_time)}</span>
                  </span>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
