'use client';

/**
 * AskDrawer Component
 * Natural language "What if..." prompt drawer that compiles prompts into executable scenarios.
 * Reference: Interaction_design.md §5.9, project.md §11 Phase 4
 * Constraint C5: LLMs compile events, NOT tick-by-tick agent brains
 */

import { useState, useCallback, useMemo } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import {
  X,
  HelpCircle,
  Loader2,
  ChevronDown,
  ChevronRight,
  Sparkles,
  Play,
  AlertTriangle,
  Info,
  Brain,
  GitBranch,
  Layers,
  TrendingUp,
  TrendingDown,
  Clock,
  CheckCircle2,
  XCircle,
  RotateCcw,
  Maximize2,
  Eye,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import {
  useCompileAskPrompt,
  useExpandAskCluster,
  useExecuteAskScenario,
} from '@/hooks/useApi';
import type {
  AskCompilationResult,
  AskScenarioCluster,
  AskCandidateScenario,
  AskIntentType,
} from '@/lib/api';

// Intent type display config
const INTENT_CONFIG: Record<AskIntentType, { label: string; icon: typeof Brain; color: string }> = {
  event: { label: 'Event', icon: Sparkles, color: 'text-purple-400' },
  variable: { label: 'Variable Change', icon: TrendingUp, color: 'text-cyan-400' },
  query: { label: 'Query', icon: Eye, color: 'text-blue-400' },
  comparison: { label: 'Comparison', icon: Layers, color: 'text-green-400' },
  explanation: { label: 'Explanation', icon: Brain, color: 'text-yellow-400' },
};

// Example prompts for inspiration
const EXAMPLE_PROMPTS = [
  "What if inflation rises by 5% over the next quarter?",
  "What happens if a major competitor launches a similar product?",
  "What if social media sentiment turns negative?",
  "What would happen if consumer confidence drops by 20%?",
  "What if interest rates increase by 0.5%?",
];

interface AskDrawerProps {
  projectId: string;
  nodeId?: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onScenarioExecuted?: (nodeId: string, runId?: string) => void;
}

export function AskDrawer({
  projectId,
  nodeId,
  open,
  onOpenChange,
  onScenarioExecuted,
}: AskDrawerProps) {
  // State
  const [prompt, setPrompt] = useState('');
  const [compilation, setCompilation] = useState<AskCompilationResult | null>(null);
  const [selectedScenarioId, setSelectedScenarioId] = useState<string | null>(null);
  const [expandedClusters, setExpandedClusters] = useState<Set<string>>(new Set());
  const [showExplanation, setShowExplanation] = useState(false);
  const [autoFork, setAutoFork] = useState(true);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [maxScenarios, setMaxScenarios] = useState(10);
  const [clusteringEnabled, setClusteringEnabled] = useState(true);

  // API mutations
  const compilePrompt = useCompileAskPrompt();
  const expandCluster = useExpandAskCluster();
  const executeScenario = useExecuteAskScenario();

  // Derived state
  const isCompiling = compilePrompt.isPending;
  const isExpanding = expandCluster.isPending;
  const isExecuting = executeScenario.isPending;
  const isPending = isCompiling || isExpanding || isExecuting;

  // Get selected scenario
  const selectedScenario = useMemo(() => {
    if (!compilation || !selectedScenarioId) return null;

    // Check in clusters first
    for (const cluster of compilation.clusters) {
      if (cluster.representative_scenario.scenario_id === selectedScenarioId) {
        return cluster.representative_scenario;
      }
      for (const child of cluster.child_scenarios || []) {
        if (child.scenario_id === selectedScenarioId) {
          return child;
        }
      }
    }

    // Check in standalone scenarios
    return compilation.candidate_scenarios.find(s => s.scenario_id === selectedScenarioId) || null;
  }, [compilation, selectedScenarioId]);

  // Handle compile
  const handleCompile = useCallback(async () => {
    if (!prompt.trim()) return;

    try {
      const result = await compilePrompt.mutateAsync({
        project_id: projectId,
        prompt: prompt.trim(),
        max_scenarios: maxScenarios,
        clustering_enabled: clusteringEnabled,
      });
      setCompilation(result);
      setSelectedScenarioId(null);
      setExpandedClusters(new Set());
    } catch {
      // Error handled by mutation
    }
  }, [prompt, projectId, maxScenarios, clusteringEnabled, compilePrompt]);

  // Handle cluster expansion
  const handleExpandCluster = useCallback(async (clusterId: string) => {
    if (!compilation) return;

    if (expandedClusters.has(clusterId)) {
      // Collapse
      setExpandedClusters(prev => {
        const next = new Set(prev);
        next.delete(clusterId);
        return next;
      });
    } else {
      // Expand via API
      try {
        await expandCluster.mutateAsync({
          compilation_id: compilation.compilation_id,
          cluster_id: clusterId,
          max_children: 5,
        });
        setExpandedClusters(prev => new Set([...prev, clusterId]));
      } catch {
        // Error handled by mutation
      }
    }
  }, [compilation, expandedClusters, expandCluster]);

  // Handle scenario execution
  const handleExecute = useCallback(async () => {
    if (!compilation || !selectedScenarioId) return;

    try {
      const result = await executeScenario.mutateAsync({
        compilation_id: compilation.compilation_id,
        scenario_id: selectedScenarioId,
        node_id: nodeId,
        auto_fork: autoFork,
      });

      onScenarioExecuted?.(result.node_id, result.run_id);
      onOpenChange(false);
    } catch {
      // Error handled by mutation
    }
  }, [compilation, selectedScenarioId, nodeId, autoFork, executeScenario, onScenarioExecuted, onOpenChange]);

  // Reset state
  const handleReset = useCallback(() => {
    setPrompt('');
    setCompilation(null);
    setSelectedScenarioId(null);
    setExpandedClusters(new Set());
  }, []);

  // Use example prompt
  const selectExample = useCallback((example: string) => {
    setPrompt(example);
    setCompilation(null);
    setSelectedScenarioId(null);
  }, []);

  // Render scenario card
  const renderScenarioCard = (scenario: AskCandidateScenario, isInCluster = false) => {
    const isSelected = selectedScenarioId === scenario.scenario_id;
    const magnitudeLevel = scenario.total_magnitude < 0.3 ? 'low' : scenario.total_magnitude < 0.6 ? 'medium' : 'high';

    return (
      <button
        key={scenario.scenario_id}
        onClick={() => setSelectedScenarioId(scenario.scenario_id)}
        className={cn(
          'w-full text-left p-3 border transition-colors',
          isInCluster ? 'ml-4 border-l-2 border-l-cyan-500/30' : '',
          isSelected
            ? 'bg-cyan-500/10 border-cyan-500/50'
            : 'bg-white/[0.02] border-white/10 hover:bg-white/5'
        )}
      >
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <p className="text-xs font-mono font-medium text-white truncate">
              {scenario.label}
            </p>
            <p className="text-[10px] font-mono text-white/50 mt-1 line-clamp-2">
              {scenario.description}
            </p>
          </div>
          <div className="flex flex-col items-end gap-1">
            <span className={cn(
              'px-1.5 py-0.5 text-[9px] font-mono uppercase',
              magnitudeLevel === 'low' && 'bg-green-500/20 text-green-400',
              magnitudeLevel === 'medium' && 'bg-yellow-500/20 text-yellow-400',
              magnitudeLevel === 'high' && 'bg-red-500/20 text-red-400',
            )}>
              {magnitudeLevel}
            </span>
            <span className="text-[9px] font-mono text-white/40">
              {(scenario.confidence * 100).toFixed(0)}% conf
            </span>
          </div>
        </div>

        {/* Variable deltas preview */}
        {Object.keys(scenario.variable_deltas).length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {Object.entries(scenario.variable_deltas).slice(0, 3).map(([key, value]) => (
              <span
                key={key}
                className={cn(
                  'px-1 py-0.5 text-[9px] font-mono',
                  value > 0 ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'
                )}
              >
                {key.replace(/_/g, ' ')}: {value > 0 ? '+' : ''}{(value * 100).toFixed(1)}%
              </span>
            ))}
            {Object.keys(scenario.variable_deltas).length > 3 && (
              <span className="px-1 py-0.5 text-[9px] font-mono bg-white/5 text-white/40">
                +{Object.keys(scenario.variable_deltas).length - 3} more
              </span>
            )}
          </div>
        )}
      </button>
    );
  };

  // Render cluster
  const renderCluster = (cluster: AskScenarioCluster) => {
    const isExpanded = expandedClusters.has(cluster.cluster_id);

    return (
      <div key={cluster.cluster_id} className="border border-white/10 bg-white/[0.02]">
        {/* Cluster header */}
        <button
          onClick={() => handleExpandCluster(cluster.cluster_id)}
          disabled={isExpanding}
          className="w-full flex items-center justify-between p-3 hover:bg-white/5 transition-colors"
        >
          <div className="flex items-center gap-2">
            {isExpanding ? (
              <Loader2 className="w-3.5 h-3.5 text-cyan-400 animate-spin" />
            ) : isExpanded ? (
              <ChevronDown className="w-3.5 h-3.5 text-white/40" />
            ) : (
              <ChevronRight className="w-3.5 h-3.5 text-white/40" />
            )}
            <Layers className="w-3.5 h-3.5 text-cyan-400" />
            <span className="text-xs font-mono font-medium text-white">
              {cluster.label}
            </span>
            <span className="px-1.5 py-0.5 bg-cyan-500/20 text-[10px] font-mono text-cyan-400">
              {cluster.scenario_count} scenarios
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono text-white/40">
              magnitude: {cluster.magnitude_range.min.toFixed(2)} - {cluster.magnitude_range.max.toFixed(2)}
            </span>
          </div>
        </button>

        {/* Cluster description */}
        <div className="px-3 pb-2 border-t border-white/5">
          <p className="text-[10px] font-mono text-white/50 pt-2">
            {cluster.description}
          </p>
        </div>

        {/* Representative scenario (always shown) */}
        <div className="border-t border-white/5 pt-2 px-2 pb-2">
          {renderScenarioCard(cluster.representative_scenario, false)}
        </div>

        {/* Expanded child scenarios */}
        {isExpanded && cluster.child_scenarios && cluster.child_scenarios.length > 0 && (
          <div className="border-t border-white/5 px-2 pb-2 space-y-1">
            <p className="text-[10px] font-mono text-white/30 px-3 pt-2 uppercase tracking-wider">
              Variations
            </p>
            {cluster.child_scenarios.map(scenario => renderScenarioCard(scenario, true))}
          </div>
        )}
      </div>
    );
  };

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/80 z-50" />
        <Dialog.Content className="fixed right-0 top-0 h-full w-full max-w-lg bg-black border-l border-white/10 z-50 overflow-hidden flex flex-col">
          {/* Header */}
          <div className="flex-shrink-0 border-b border-white/10 p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-cyan-500/20 border border-cyan-500/50 flex items-center justify-center">
                  <HelpCircle className="w-4 h-4 text-cyan-400" />
                </div>
                <div>
                  <Dialog.Title className="text-sm font-mono font-bold text-white">
                    Ask &quot;What If...?&quot;
                  </Dialog.Title>
                  <Dialog.Description className="text-[10px] font-mono text-white/40">
                    Describe a scenario to explore future possibilities
                  </Dialog.Description>
                </div>
              </div>
              <Dialog.Close asChild>
                <Button variant="ghost" size="icon-sm">
                  <X className="w-4 h-4" />
                </Button>
              </Dialog.Close>
            </div>
          </div>

          {/* Scrollable Content */}
          <div className="flex-1 overflow-y-auto">
            {/* Prompt Input Section */}
            <div className="p-4 border-b border-white/5">
              <label className="text-[10px] font-mono text-white/40 uppercase tracking-wider block mb-2">
                Your Question
              </label>
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="What if inflation rises by 5%? What happens if..."
                rows={3}
                className="w-full px-3 py-2 bg-white/5 border border-white/10 text-sm font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-cyan-500/50 resize-none"
                disabled={isPending}
              />

              {/* Example prompts */}
              {!compilation && (
                <div className="mt-3">
                  <p className="text-[10px] font-mono text-white/30 mb-2">Try an example:</p>
                  <div className="flex flex-wrap gap-1">
                    {EXAMPLE_PROMPTS.slice(0, 3).map((example, i) => (
                      <button
                        key={i}
                        onClick={() => selectExample(example)}
                        className="px-2 py-1 text-[10px] font-mono text-white/50 bg-white/5 border border-white/10 hover:bg-white/10 hover:text-white/70 transition-colors truncate max-w-[200px]"
                      >
                        {example}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Advanced Settings */}
              <button
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="flex items-center gap-2 text-[10px] font-mono text-white/40 hover:text-white/60 mt-3"
              >
                {showAdvanced ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                Advanced Options
              </button>

              {showAdvanced && (
                <div className="mt-3 p-3 bg-white/[0.02] border border-white/10 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono text-white/60">Max scenarios</span>
                    <input
                      type="number"
                      value={maxScenarios}
                      onChange={(e) => setMaxScenarios(Math.max(1, Math.min(50, parseInt(e.target.value) || 10)))}
                      className="w-16 px-2 py-1 bg-white/5 border border-white/10 text-xs font-mono text-white text-right focus:outline-none focus:border-white/20"
                    />
                  </div>
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={clusteringEnabled}
                      onChange={(e) => setClusteringEnabled(e.target.checked)}
                      className="w-4 h-4 bg-white/5 border border-white/20"
                    />
                    <span className="text-[10px] font-mono text-white/60">
                      Enable scenario clustering
                    </span>
                  </label>
                </div>
              )}

              {/* Compile Button */}
              <Button
                onClick={handleCompile}
                disabled={!prompt.trim() || isPending}
                className="w-full mt-4"
              >
                {isCompiling ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 mr-2 animate-spin" />
                    Compiling scenarios...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-3.5 h-3.5 mr-2" />
                    Compile Scenarios
                  </>
                )}
              </Button>
            </div>

            {/* Compilation Results */}
            {compilation && (
              <>
                {/* Intent Summary */}
                <div className="p-4 border-b border-white/5">
                  <div className="flex items-center gap-2 mb-2">
                    {(() => {
                      const config = INTENT_CONFIG[compilation.intent.intent_type];
                      const Icon = config.icon;
                      return (
                        <>
                          <Icon className={cn('w-3.5 h-3.5', config.color)} />
                          <span className={cn('text-xs font-mono', config.color)}>
                            {config.label} Intent
                          </span>
                          <span className="text-[10px] font-mono text-white/40">
                            ({(compilation.intent.confidence * 100).toFixed(0)}% confidence)
                          </span>
                        </>
                      );
                    })()}
                  </div>
                  <p className="text-[10px] font-mono text-white/60">
                    {compilation.intent.normalized_prompt}
                  </p>

                  {/* Compilation stats */}
                  <div className="flex items-center gap-4 mt-3 text-[9px] font-mono text-white/40">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {compilation.compilation_time_ms}ms
                    </span>
                    <span>
                      {compilation.clusters.length} clusters
                    </span>
                    <span>
                      {compilation.candidate_scenarios.length} total scenarios
                    </span>
                  </div>

                  {/* Warnings */}
                  {compilation.warnings.length > 0 && (
                    <div className="mt-3 p-2 bg-yellow-500/10 border border-yellow-500/30">
                      <div className="flex items-start gap-2">
                        <AlertTriangle className="w-3.5 h-3.5 text-yellow-400 flex-shrink-0 mt-0.5" />
                        <div className="text-[10px] font-mono text-yellow-300">
                          {compilation.warnings.map((w, i) => (
                            <p key={i}>{w}</p>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Explanation Toggle */}
                <div className="px-4 py-2 border-b border-white/5">
                  <button
                    onClick={() => setShowExplanation(!showExplanation)}
                    className="flex items-center gap-2 text-xs font-mono text-white/60 hover:text-white/80"
                  >
                    {showExplanation ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                    <Brain className="w-3.5 h-3.5" />
                    Causal Explanation
                  </button>

                  {showExplanation && (
                    <div className="mt-3 p-3 bg-white/[0.02] border border-white/10 space-y-3">
                      <p className="text-xs font-mono text-white/80">
                        {compilation.explanation.summary}
                      </p>

                      {compilation.explanation.causal_chain.length > 0 && (
                        <div>
                          <p className="text-[10px] font-mono text-white/40 uppercase tracking-wider mb-2">
                            Causal Chain
                          </p>
                          <div className="space-y-1">
                            {compilation.explanation.causal_chain.slice(0, 5).map((link, i) => (
                              <div key={i} className="flex items-center gap-2 text-[10px] font-mono">
                                <span className="text-cyan-400">{link.from_concept}</span>
                                <span className="text-white/30">→</span>
                                <span className="text-purple-400">{link.to_concept}</span>
                                <span className="text-white/20">({(link.strength * 100).toFixed(0)}%)</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {compilation.explanation.key_assumptions.length > 0 && (
                        <div>
                          <p className="text-[10px] font-mono text-white/40 uppercase tracking-wider mb-1">
                            Key Assumptions
                          </p>
                          <ul className="text-[10px] font-mono text-white/50 space-y-0.5">
                            {compilation.explanation.key_assumptions.slice(0, 3).map((a, i) => (
                              <li key={i} className="flex items-start gap-1">
                                <span className="text-yellow-400">•</span>
                                {a}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Scenario Clusters */}
                <div className="p-4">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <Layers className="w-3.5 h-3.5 text-white/40" />
                      <span className="text-[10px] font-mono text-white/40 uppercase tracking-wider">
                        Generated Scenarios
                      </span>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleReset}
                      className="text-[10px]"
                    >
                      <RotateCcw className="w-3 h-3 mr-1" />
                      Reset
                    </Button>
                  </div>

                  <div className="space-y-2">
                    {compilation.clusters.map(renderCluster)}
                  </div>
                </div>
              </>
            )}
          </div>

          {/* Footer Actions */}
          {compilation && (
            <div className="flex-shrink-0 border-t border-white/10 p-4">
              {/* Selected scenario summary */}
              {selectedScenario && (
                <div className="mb-3 p-3 bg-cyan-500/10 border border-cyan-500/30">
                  <div className="flex items-center gap-2 mb-1">
                    <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400" />
                    <span className="text-xs font-mono font-medium text-white">
                      {selectedScenario.label}
                    </span>
                  </div>
                  <p className="text-[10px] font-mono text-white/50">
                    {Object.keys(selectedScenario.variable_deltas).length} variable changes,{' '}
                    magnitude: {selectedScenario.total_magnitude.toFixed(2)}
                  </p>
                </div>
              )}

              {/* Auto-fork option */}
              <label className="flex items-center gap-3 cursor-pointer mb-3">
                <input
                  type="checkbox"
                  checked={autoFork}
                  onChange={(e) => setAutoFork(e.target.checked)}
                  className="w-4 h-4 bg-white/5 border border-white/20"
                />
                <span className="text-xs font-mono text-white/70">
                  Fork node and start simulation run
                </span>
              </label>

              {/* Action buttons */}
              <div className="flex items-center gap-3">
                <Button
                  variant="secondary"
                  onClick={() => onOpenChange(false)}
                  disabled={isPending}
                  className="flex-1"
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleExecute}
                  disabled={!selectedScenarioId || isPending}
                  className="flex-1"
                >
                  {isExecuting ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 mr-2 animate-spin" />
                      Executing...
                    </>
                  ) : (
                    <>
                      <Play className="w-3.5 h-3.5 mr-2" />
                      {autoFork ? 'Fork & Run' : 'Apply Scenario'}
                    </>
                  )}
                </Button>
              </div>
            </div>
          )}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

export default AskDrawer;
