'use client';

/**
 * Event Lab Page
 * Natural language → branch workflow for "what-if" scenario generation
 */

import { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  Sparkles,
  ArrowLeft,
  Terminal,
  Play,
  MessageSquare,
  Loader2,
  AlertCircle,
  GitFork,
  TrendingUp,
  TrendingDown,
  Minus,
  Clock,
  ChevronRight,
  Trash2,
  RotateCcw,
} from 'lucide-react';
import { useForkNode, useUniverseMap } from '@/hooks/useApi';
import type { AskCandidateScenario, AskCompilationResult } from '@/lib/api';
import { useMutation } from '@tanstack/react-query';
import { cn } from '@/lib/utils';

// Local storage keys
const STORAGE_KEY_PREFIX = 'eventlab_';
const MAX_RECENT_PROMPTS = 5;
const MAX_RECENT_COMPILATIONS = 3;

interface StoredPrompt {
  prompt: string;
  timestamp: number;
}

interface StoredCompilation {
  prompt: string;
  result: AskCompilationResult;
  timestamp: number;
}

// Direction indicator component
function DirectionIndicator({ magnitude }: { magnitude: number }) {
  if (magnitude > 0.1) {
    return (
      <div className="flex items-center gap-1 text-emerald-400">
        <TrendingUp className="w-3 h-3" />
        <span className="text-[10px]">Increase</span>
      </div>
    );
  } else if (magnitude < -0.1) {
    return (
      <div className="flex items-center gap-1 text-red-400">
        <TrendingDown className="w-3 h-3" />
        <span className="text-[10px]">Decrease</span>
      </div>
    );
  }
  return (
    <div className="flex items-center gap-1 text-white/40">
      <Minus className="w-3 h-3" />
      <span className="text-[10px]">Neutral</span>
    </div>
  );
}

// Confidence badge component
function ConfidenceBadge({ confidence }: { confidence: number }) {
  const percent = Math.round(confidence * 100);
  const color = confidence >= 0.7 ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' :
                confidence >= 0.4 ? 'bg-amber-500/20 text-amber-400 border-amber-500/30' :
                'bg-red-500/20 text-red-400 border-red-500/30';

  return (
    <span className={cn('px-2 py-0.5 text-[10px] font-mono border', color)}>
      {percent}% confidence
    </span>
  );
}

// Scenario card component
function ScenarioCard({
  scenario,
  index,
  onAddAsBranch,
  isCreating,
}: {
  scenario: AskCandidateScenario;
  index: number;
  onAddAsBranch: (scenario: AskCandidateScenario) => void;
  isCreating: boolean;
}) {
  const variableEntries = Object.entries(scenario.variable_deltas || {});

  return (
    <div className="bg-white/5 border border-white/10 hover:border-cyan-500/30 transition-all">
      {/* Header */}
      <div className="px-4 py-3 border-b border-white/10 flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[10px] font-mono text-white/30">SCENARIO {index + 1}</span>
            <ConfidenceBadge confidence={scenario.confidence} />
          </div>
          <h3 className="text-sm font-mono font-bold text-white truncate">{scenario.label}</h3>
        </div>
        <DirectionIndicator magnitude={scenario.total_magnitude} />
      </div>

      {/* Description */}
      <div className="px-4 py-3 border-b border-white/5">
        <p className="text-xs font-mono text-white/60 leading-relaxed">
          {scenario.description}
        </p>
      </div>

      {/* Variables */}
      {variableEntries.length > 0 && (
        <div className="px-4 py-3 border-b border-white/5">
          <div className="text-[10px] font-mono text-white/30 uppercase mb-2">Key Variables</div>
          <div className="flex flex-wrap gap-2">
            {variableEntries.slice(0, 5).map(([key, value]) => (
              <div
                key={key}
                className={cn(
                  'px-2 py-1 text-[10px] font-mono border',
                  value > 0 ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                  value < 0 ? 'bg-red-500/10 text-red-400 border-red-500/20' :
                  'bg-white/5 text-white/40 border-white/10'
                )}
              >
                {key}: {value > 0 ? '+' : ''}{typeof value === 'number' ? value.toFixed(2) : value}
              </div>
            ))}
            {variableEntries.length > 5 && (
              <span className="text-[10px] font-mono text-white/30">
                +{variableEntries.length - 5} more
              </span>
            )}
          </div>
        </div>
      )}

      {/* Event Script Preview (if available) */}
      {scenario.event_script_preview && (
        <div className="px-4 py-3 border-b border-white/5">
          <div className="text-[10px] font-mono text-white/30 uppercase mb-1">Simulation Preview</div>
          <div className="flex flex-wrap gap-2">
            <span className="px-2 py-0.5 bg-white/5 text-[10px] font-mono text-white/40">
              Intensity: {scenario.event_script_preview.intensity_profile}
            </span>
            <span className="px-2 py-0.5 bg-white/5 text-[10px] font-mono text-white/40">
              Scope: {scenario.event_script_preview.scope}
            </span>
            <span className="px-2 py-0.5 bg-white/5 text-[10px] font-mono text-white/40">
              Duration: ~{scenario.event_script_preview.estimated_duration_ticks} ticks
            </span>
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="px-4 py-3 flex items-center justify-end gap-2">
        <Button
          size="sm"
          onClick={() => onAddAsBranch(scenario)}
          disabled={isCreating}
          className="text-xs bg-cyan-500 hover:bg-cyan-600 text-black"
        >
          {isCreating ? (
            <>
              <Loader2 className="w-3 h-3 mr-1 animate-spin" />
              CREATING...
            </>
          ) : (
            <>
              <GitFork className="w-3 h-3 mr-1" />
              ADD AS BRANCH
            </>
          )}
        </Button>
      </div>
    </div>
  );
}

export default function EventLabPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.projectId as string;

  // Form state
  const [prompt, setPrompt] = useState('');
  const [recentPrompts, setRecentPrompts] = useState<StoredPrompt[]>([]);
  const [recentCompilations, setRecentCompilations] = useState<StoredCompilation[]>([]);

  // Results state
  const [currentCompilation, setCurrentCompilation] = useState<AskCompilationResult | null>(null);
  const [creatingScenarioId, setCreatingScenarioId] = useState<string | null>(null);

  // API hooks
  const forkNode = useForkNode();
  const { data: universeState } = useUniverseMap(projectId);

  // Direct API call to our fast generation endpoint
  const generateScenarios = useMutation({
    mutationFn: async (data: { project_id: string; prompt: string; max_scenarios?: number }) => {
      const response = await fetch('/api/ask/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: 'Request failed' }));
        throw new Error(errorData.error || `HTTP ${response.status}`);
      }

      return response.json() as Promise<AskCompilationResult>;
    },
  });

  // Load recent prompts and compilations from localStorage
  useEffect(() => {
    try {
      const storedPrompts = localStorage.getItem(`${STORAGE_KEY_PREFIX}prompts_${projectId}`);
      if (storedPrompts) {
        setRecentPrompts(JSON.parse(storedPrompts));
      }

      const storedCompilations = localStorage.getItem(`${STORAGE_KEY_PREFIX}compilations_${projectId}`);
      if (storedCompilations) {
        setRecentCompilations(JSON.parse(storedCompilations));
      }
    } catch {
      // Ignore localStorage errors
    }
  }, [projectId]);

  // Save recent prompts to localStorage
  const saveRecentPrompt = useCallback((newPrompt: string) => {
    const updated: StoredPrompt[] = [
      { prompt: newPrompt, timestamp: Date.now() },
      ...recentPrompts.filter(p => p.prompt !== newPrompt)
    ].slice(0, MAX_RECENT_PROMPTS);

    setRecentPrompts(updated);
    try {
      localStorage.setItem(`${STORAGE_KEY_PREFIX}prompts_${projectId}`, JSON.stringify(updated));
    } catch {
      // Ignore localStorage errors
    }
  }, [recentPrompts, projectId]);

  // Save compilation to localStorage
  const saveCompilation = useCallback((promptText: string, result: AskCompilationResult) => {
    const updated: StoredCompilation[] = [
      { prompt: promptText, result, timestamp: Date.now() },
      ...recentCompilations.filter(c => c.prompt !== promptText)
    ].slice(0, MAX_RECENT_COMPILATIONS);

    setRecentCompilations(updated);
    try {
      localStorage.setItem(`${STORAGE_KEY_PREFIX}compilations_${projectId}`, JSON.stringify(updated));
    } catch {
      // Ignore localStorage errors
    }
  }, [recentCompilations, projectId]);

  // Handle generate scenarios
  const handleGenerate = useCallback(async () => {
    if (!prompt.trim()) return;

    saveRecentPrompt(prompt.trim());

    generateScenarios.mutate(
      {
        project_id: projectId,
        prompt: prompt.trim(),
        max_scenarios: 5,
      },
      {
        onSuccess: (result) => {
          setCurrentCompilation(result);
          saveCompilation(prompt.trim(), result);
        },
      }
    );
  }, [prompt, projectId, generateScenarios, saveRecentPrompt, saveCompilation]);

  // Handle add as branch
  const handleAddAsBranch = useCallback(async (scenario: AskCandidateScenario) => {
    setCreatingScenarioId(scenario.scenario_id);

    // Find the baseline/root node as default parent
    const parentNodeId = universeState?.root_node_id || 'baseline';

    forkNode.mutate(
      {
        parent_node_id: parentNodeId,
        label: scenario.label,
        description: scenario.description,
        intervention_type: 'nl_query',
        nl_query: currentCompilation?.original_prompt,
        scenario_patch: {
          environment_overrides: scenario.variable_deltas || {},
        },
      },
      {
        onSuccess: (result) => {
          // Navigate to universe map with the new node selected
          router.push(`/p/${projectId}/universe-map?select=${result.node.node_id}&inspect=true`);
        },
        onError: () => {
          setCreatingScenarioId(null);
        },
      }
    );
  }, [universeState, forkNode, currentCompilation, projectId, router]);

  // Clear recent prompts
  const handleClearHistory = useCallback(() => {
    setRecentPrompts([]);
    setRecentCompilations([]);
    try {
      localStorage.removeItem(`${STORAGE_KEY_PREFIX}prompts_${projectId}`);
      localStorage.removeItem(`${STORAGE_KEY_PREFIX}compilations_${projectId}`);
    } catch {
      // Ignore localStorage errors
    }
  }, [projectId]);

  // Load a recent prompt
  const handleLoadPrompt = useCallback((promptText: string) => {
    setPrompt(promptText);
  }, []);

  // Load a recent compilation
  const handleLoadCompilation = useCallback((compilation: StoredCompilation) => {
    setPrompt(compilation.prompt);
    setCurrentCompilation(compilation.result);
  }, []);

  const scenarios = currentCompilation?.candidate_scenarios || [];
  const isGenerating = generateScenarios.isPending;
  const generateError = generateScenarios.error;

  return (
    <div className="min-h-screen bg-black p-4 md:p-6">
      {/* Header */}
      <div className="mb-6 md:mb-8">
        <Link href={`/p/${projectId}/overview`}>
          <Button variant="ghost" size="sm" className="mb-3 text-[10px] md:text-xs">
            <ArrowLeft className="w-3 h-3 mr-1 md:mr-2" />
            BACK TO OVERVIEW
          </Button>
        </Link>
        <div className="flex items-center gap-2 mb-1">
          <Sparkles className="w-3.5 h-3.5 md:w-4 md:h-4 text-amber-400" />
          <span className="text-[10px] md:text-xs font-mono text-white/40 uppercase tracking-wider">Event Lab</span>
        </div>
        <h1 className="text-lg md:text-xl font-mono font-bold text-white">Natural Language Scenarios</h1>
        <p className="text-xs md:text-sm font-mono text-white/50 mt-1">
          Describe a &quot;what-if&quot; scenario and generate branches for your simulation
        </p>
      </div>

      <div className="max-w-4xl">
        {/* Input Section */}
        <div className="bg-white/5 border border-white/10 mb-6">
          <div className="px-4 py-3 border-b border-white/10 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <MessageSquare className="w-4 h-4 text-amber-400" />
              <span className="text-sm font-mono font-bold text-white">Ask a What-If Question</span>
            </div>
            {recentPrompts.length > 0 && (
              <button
                onClick={handleClearHistory}
                className="text-[10px] font-mono text-white/30 hover:text-white/50 flex items-center gap-1"
              >
                <Trash2 className="w-3 h-3" />
                Clear History
              </button>
            )}
          </div>

          <div className="p-4">
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="e.g., What if the government increases tariffs by 20%? How would this affect consumer spending patterns?"
              className="w-full h-32 px-3 py-2 bg-black border border-white/10 text-sm font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-amber-500/50 resize-none"
              disabled={isGenerating}
            />

            {/* Recent prompts */}
            {recentPrompts.length > 0 && !prompt && (
              <div className="mt-3">
                <div className="text-[10px] font-mono text-white/30 uppercase mb-2">Recent Prompts</div>
                <div className="flex flex-wrap gap-2">
                  {recentPrompts.map((rp, i) => (
                    <button
                      key={i}
                      onClick={() => handleLoadPrompt(rp.prompt)}
                      className="px-2 py-1 bg-white/5 border border-white/10 text-[10px] font-mono text-white/50 hover:text-white hover:border-white/20 truncate max-w-[200px]"
                    >
                      {rp.prompt}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <div className="mt-4 flex items-center justify-between">
              <div className="text-[10px] font-mono text-white/30">
                {prompt.length > 0 && `${prompt.length} characters`}
              </div>
              <Button
                onClick={handleGenerate}
                disabled={!prompt.trim() || isGenerating}
                className="text-xs bg-amber-500 hover:bg-amber-600 text-black"
              >
                {isGenerating ? (
                  <>
                    <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                    GENERATING...
                  </>
                ) : (
                  <>
                    <Play className="w-3 h-3 mr-1" />
                    GENERATE SCENARIOS
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>

        {/* Error State */}
        {generateError && (
          <div className="bg-red-500/10 border border-red-500/30 p-4 mb-6">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="text-sm font-mono font-bold text-red-400 mb-1">Generation Failed</h3>
                <p className="text-xs font-mono text-white/60">
                  {generateError instanceof Error ? generateError.message : 'An error occurred while generating scenarios. Please try again.'}
                </p>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={handleGenerate}
                  className="mt-2 text-xs text-red-400 hover:text-red-300"
                >
                  <RotateCcw className="w-3 h-3 mr-1" />
                  Retry
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Loading State */}
        {isGenerating && (
          <div className="bg-white/5 border border-white/10 p-12 text-center mb-6">
            <Loader2 className="w-12 h-12 text-amber-400 animate-spin mx-auto mb-4" />
            <h3 className="text-sm font-mono text-white mb-2">Analyzing Your Scenario</h3>
            <p className="text-xs font-mono text-white/40">
              Our AI is identifying variables, causal relationships, and generating alternative scenarios...
            </p>
          </div>
        )}

        {/* Results Section */}
        {!isGenerating && scenarios.length > 0 && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-mono font-bold text-white">Generated Scenarios</h2>
                <p className="text-[10px] font-mono text-white/40 mt-0.5">
                  {scenarios.length} scenario{scenarios.length !== 1 ? 's' : ''} based on your query
                </p>
              </div>
              {currentCompilation?.original_prompt && (
                <div className="text-right">
                  <div className="text-[10px] font-mono text-white/30">Query</div>
                  <div className="text-xs font-mono text-white/50 max-w-[300px] truncate">
                    &quot;{currentCompilation.original_prompt}&quot;
                  </div>
                </div>
              )}
            </div>

            <div className="grid gap-4">
              {scenarios.map((scenario, index) => (
                <ScenarioCard
                  key={scenario.scenario_id}
                  scenario={scenario}
                  index={index}
                  onAddAsBranch={handleAddAsBranch}
                  isCreating={creatingScenarioId === scenario.scenario_id}
                />
              ))}
            </div>
          </div>
        )}

        {/* Empty State (no generation yet) */}
        {!isGenerating && !generateError && scenarios.length === 0 && !currentCompilation && (
          <div className="bg-white/5 border border-white/10 p-12 text-center">
            <div className="w-16 h-16 bg-white/5 flex items-center justify-center mx-auto mb-4">
              <Sparkles className="w-8 h-8 text-white/20" />
            </div>
            <h3 className="text-sm font-mono text-white/60 mb-2">No Scenarios Yet</h3>
            <p className="text-xs font-mono text-white/40 mb-4 max-w-sm mx-auto">
              Enter a what-if question above to generate alternative scenarios for your simulation.
            </p>

            {/* Quick examples */}
            <div className="mt-6 pt-6 border-t border-white/5">
              <div className="text-[10px] font-mono text-white/30 uppercase mb-3">Try These Examples</div>
              <div className="flex flex-wrap justify-center gap-2">
                {[
                  'What if oil prices double?',
                  'What if interest rates drop to 0%?',
                  'What if a competitor enters the market?',
                ].map((example) => (
                  <button
                    key={example}
                    onClick={() => setPrompt(example)}
                    className="px-3 py-1.5 bg-amber-500/10 border border-amber-500/20 text-[11px] font-mono text-amber-400 hover:bg-amber-500/20 transition-colors flex items-center gap-1"
                  >
                    <ChevronRight className="w-3 h-3" />
                    {example}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* No results state */}
        {!isGenerating && currentCompilation && scenarios.length === 0 && (
          <div className="bg-white/5 border border-white/10 p-12 text-center">
            <div className="w-16 h-16 bg-amber-500/10 flex items-center justify-center mx-auto mb-4">
              <AlertCircle className="w-8 h-8 text-amber-400" />
            </div>
            <h3 className="text-sm font-mono text-amber-400 mb-2">No Scenarios Generated</h3>
            <p className="text-xs font-mono text-white/40 mb-4 max-w-sm mx-auto">
              The AI couldn&apos;t generate meaningful scenarios from your query. Try rephrasing or being more specific.
            </p>
            <Button
              size="sm"
              variant="secondary"
              onClick={() => {
                setCurrentCompilation(null);
                setPrompt('');
              }}
            >
              Try Again
            </Button>
          </div>
        )}

        {/* Recent Compilations */}
        {recentCompilations.length > 0 && !currentCompilation && !isGenerating && (
          <div className="mt-6 pt-6 border-t border-white/5">
            <div className="flex items-center gap-2 mb-3">
              <Clock className="w-3.5 h-3.5 text-white/30" />
              <span className="text-[10px] font-mono text-white/30 uppercase">Recent Results</span>
            </div>
            <div className="grid gap-2">
              {recentCompilations.map((comp, i) => (
                <button
                  key={i}
                  onClick={() => handleLoadCompilation(comp)}
                  className="p-3 bg-white/5 border border-white/10 hover:border-white/20 text-left transition-colors"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="text-xs font-mono text-white truncate">&quot;{comp.prompt}&quot;</div>
                      <div className="text-[10px] font-mono text-white/30 mt-1">
                        {comp.result.candidate_scenarios?.length || 0} scenarios generated
                      </div>
                    </div>
                    <div className="text-[10px] font-mono text-white/20">
                      {new Date(comp.timestamp).toLocaleDateString()}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="mt-8 pt-4 border-t border-white/5 max-w-4xl">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-1">
            <Terminal className="w-3 h-3" />
            <span>EVENT LAB</span>
          </div>
          <span>AGENTVERSE v1.0</span>
        </div>
      </div>
    </div>
  );
}
