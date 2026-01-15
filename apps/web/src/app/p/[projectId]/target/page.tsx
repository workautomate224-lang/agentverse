'use client';

/**
 * Target Planner Page
 * User-defined intervention plans for Target Mode.
 *
 * Features:
 * A. Context selectors (Node selector, Run selector with deep links)
 * B. Target definition (metric dropdown, value input, constraints)
 * C. Plan builder (intervention steps with CRUD, auto-save)
 * D. AI plan generation via OpenRouter
 * E. Branch creation + navigation to Universe Map
 * F. Next actions (Run this Branch → Run Center)
 */

import { useParams, useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useState, useEffect, useCallback, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import {
  useNodes,
  useRuns,
  useUserTargetPlans,
  useUserTargetPlan,
  useCreateUserTargetPlan,
  useUpdateUserTargetPlan,
  useDeleteUserTargetPlan,
  useCreateBranchFromUserPlan,
} from '@/hooks/useApi';
import type { InterventionStep, PlanConstraints, TargetPlanSource, RunSummary, NodeSummary } from '@/lib/api';
import { GuidancePanel } from '@/components/pil';
import {
  Crosshair,
  ArrowLeft,
  Terminal,
  Plus,
  Trash2,
  Save,
  Sparkles,
  GitBranch,
  Play,
  Loader2,
  ChevronDown,
  Target,
  Clock,
  Layers,
  ArrowRight,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  MapIcon,
  Activity,
  GripVertical,
} from 'lucide-react';

// Metric options
const METRIC_OPTIONS = [
  { value: 'market_share', label: 'Market Share' },
  { value: 'revenue', label: 'Revenue' },
  { value: 'customer_satisfaction', label: 'Customer Satisfaction' },
  { value: 'brand_awareness', label: 'Brand Awareness' },
  { value: 'conversion_rate', label: 'Conversion Rate' },
  { value: 'retention_rate', label: 'Retention Rate' },
  { value: 'nps_score', label: 'NPS Score' },
  { value: 'engagement_rate', label: 'Engagement Rate' },
  { value: 'churn_rate', label: 'Churn Rate' },
  { value: 'custom', label: 'Custom Metric' },
];

// Action type options
const ACTION_TYPE_OPTIONS = [
  { value: 'price_change', label: 'Price Change' },
  { value: 'marketing_campaign', label: 'Marketing Campaign' },
  { value: 'product_launch', label: 'Product Launch' },
  { value: 'promotion', label: 'Promotion/Discount' },
  { value: 'messaging', label: 'Messaging Change' },
  { value: 'channel_expansion', label: 'Channel Expansion' },
  { value: 'competitor_response', label: 'Competitor Response' },
  { value: 'policy_change', label: 'Policy Change' },
  { value: 'custom', label: 'Custom Action' },
];

// Generate unique ID
function generateId() {
  return `step_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

export default function TargetPlannerPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { toast } = useToast();
  const projectId = params.projectId as string;

  // URL params for deep linking
  const nodeIdParam = searchParams.get('node');
  const runIdParam = searchParams.get('run');
  const planIdParam = searchParams.get('plan');

  // Local state
  const [selectedNodeId, setSelectedNodeId] = useState<string | undefined>(nodeIdParam || undefined);
  const [selectedRunId, setSelectedRunId] = useState<string | undefined>(runIdParam || undefined);
  const [selectedPlanId, setSelectedPlanId] = useState<string | undefined>(planIdParam || undefined);

  // Plan form state
  const [planName, setPlanName] = useState('');
  const [targetMetric, setTargetMetric] = useState('market_share');
  const [customMetric, setCustomMetric] = useState('');
  const [targetValue, setTargetValue] = useState<number>(0);
  const [horizonTicks, setHorizonTicks] = useState<number>(100);
  const [steps, setSteps] = useState<InterventionStep[]>([]);
  const [constraints, setConstraints] = useState<PlanConstraints>({});

  // AI generation state
  const [aiPrompt, setAiPrompt] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);

  // Auto-save state
  const [isDirty, setIsDirty] = useState(false);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  // Data queries
  const { data: nodes, isLoading: nodesLoading } = useNodes({ project_id: projectId });
  const { data: runs, isLoading: runsLoading } = useRuns({ project_id: projectId, limit: 50 });
  const { data: plansData, isLoading: plansLoading, refetch: refetchPlans } = useUserTargetPlans(projectId);
  const { data: selectedPlan, isLoading: planLoading } = useUserTargetPlan(selectedPlanId);

  // Mutations
  const createPlan = useCreateUserTargetPlan();
  const updatePlan = useUpdateUserTargetPlan();
  const deletePlan = useDeleteUserTargetPlan();
  const createBranch = useCreateBranchFromUserPlan();

  // Load plan data when selected
  useEffect(() => {
    if (selectedPlan) {
      setPlanName(selectedPlan.name);
      setTargetMetric(selectedPlan.target_metric);
      setTargetValue(selectedPlan.target_value);
      setHorizonTicks(selectedPlan.horizon_ticks);
      setSteps(selectedPlan.steps_json || []);
      setConstraints(selectedPlan.constraints_json || {});
      setSelectedNodeId(selectedPlan.node_id || undefined);
      setIsDirty(false);
    }
  }, [selectedPlan]);

  // Update URL with current selections
  useEffect(() => {
    const params = new URLSearchParams();
    if (selectedNodeId) params.set('node', selectedNodeId);
    if (selectedRunId) params.set('run', selectedRunId);
    if (selectedPlanId) params.set('plan', selectedPlanId);

    const newUrl = params.toString() ? `?${params.toString()}` : '';
    window.history.replaceState({}, '', `/p/${projectId}/target${newUrl}`);
  }, [projectId, selectedNodeId, selectedRunId, selectedPlanId]);

  // Auto-save with debounce
  useEffect(() => {
    if (!isDirty || !selectedPlanId) return;

    const timeout = setTimeout(async () => {
      await handleSave();
    }, 2000);

    return () => clearTimeout(timeout);
  }, [isDirty, planName, targetMetric, targetValue, horizonTicks, steps, constraints]);

  // Handle form changes
  const markDirty = useCallback(() => {
    setIsDirty(true);
  }, []);

  // Add new step
  const handleAddStep = useCallback(() => {
    const newStep: InterventionStep = {
      id: generateId(),
      tick: Math.max(0, ...steps.map(s => s.tick)) + 10,
      action_type: 'marketing_campaign',
      target: 'all_agents',
      parameters: {},
      description: '',
    };
    setSteps(prev => [...prev, newStep]);
    markDirty();
  }, [steps, markDirty]);

  // Update step
  const handleUpdateStep = useCallback((stepId: string, updates: Partial<InterventionStep>) => {
    setSteps(prev => prev.map(s => s.id === stepId ? { ...s, ...updates } : s));
    markDirty();
  }, [markDirty]);

  // Delete step
  const handleDeleteStep = useCallback((stepId: string) => {
    setSteps(prev => prev.filter(s => s.id !== stepId));
    markDirty();
  }, [markDirty]);

  // Save plan
  const handleSave = useCallback(async () => {
    if (!planName.trim()) {
      toast({ title: 'Error', description: 'Plan name is required', variant: 'destructive' });
      return;
    }

    setIsSaving(true);
    try {
      const planData = {
        name: planName,
        node_id: selectedNodeId,
        target_metric: targetMetric === 'custom' ? customMetric : targetMetric,
        target_value: targetValue,
        horizon_ticks: horizonTicks,
        steps_json: steps,
        constraints_json: constraints,
      };

      if (selectedPlanId) {
        await updatePlan.mutateAsync({ planId: selectedPlanId, data: planData });
      } else {
        const newPlan = await createPlan.mutateAsync({ projectId, data: { ...planData, source: 'manual' as TargetPlanSource } });
        setSelectedPlanId(newPlan.id);
      }

      setIsDirty(false);
      setLastSaved(new Date());
      toast({ title: 'Saved', description: 'Plan saved successfully' });
      refetchPlans();
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to save plan', variant: 'destructive' });
    } finally {
      setIsSaving(false);
    }
  }, [planName, selectedNodeId, targetMetric, customMetric, targetValue, horizonTicks, steps, constraints, selectedPlanId, projectId, createPlan, updatePlan, refetchPlans, toast]);

  // Create new plan
  const handleNewPlan = useCallback(() => {
    setSelectedPlanId(undefined);
    setPlanName('');
    setTargetMetric('market_share');
    setTargetValue(0);
    setHorizonTicks(100);
    setSteps([]);
    setConstraints({});
    setIsDirty(false);
  }, []);

  // Delete plan
  const handleDeletePlan = useCallback(async () => {
    if (!selectedPlanId) return;

    try {
      await deletePlan.mutateAsync({ planId: selectedPlanId, projectId });
      handleNewPlan();
      toast({ title: 'Deleted', description: 'Plan deleted successfully' });
      refetchPlans();
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to delete plan', variant: 'destructive' });
    }
  }, [selectedPlanId, projectId, deletePlan, handleNewPlan, refetchPlans, toast]);

  // AI generation
  const handleAIGenerate = useCallback(async () => {
    if (!aiPrompt.trim()) {
      toast({ title: 'Error', description: 'Please enter a prompt', variant: 'destructive' });
      return;
    }

    setIsGenerating(true);
    try {
      // Call OpenRouter through Next.js API route
      const response = await fetch('/api/ask/generate-plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: aiPrompt,
          target_metric: targetMetric,
          horizon_ticks: horizonTicks,
          context: {
            project_id: projectId,
            node_id: selectedNodeId,
          },
        }),
      });

      if (!response.ok) throw new Error('AI generation failed');

      const result = await response.json();

      // Apply AI-generated plan (map API response fields to form fields)
      if (result.name) setPlanName(result.name);
      if (result.target_metric) setTargetMetric(result.target_metric);
      if (result.target_value) setTargetValue(result.target_value);
      if (result.horizon_ticks) setHorizonTicks(result.horizon_ticks);
      if (result.steps && Array.isArray(result.steps)) {
        setSteps(result.steps.map((s: { tick?: number; action?: string; parameters?: Record<string, unknown>; expected_impact?: string }, i: number) => ({
          id: generateId(),
          tick: s.tick ?? i * 20,
          action_type: s.action || 'custom',
          target: 'all_agents',
          parameters: s.parameters || {},
          description: s.expected_impact || '',
        })));
      }

      markDirty();
      toast({ title: 'Generated', description: 'AI plan generated successfully' });
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to generate plan with AI', variant: 'destructive' });
    } finally {
      setIsGenerating(false);
    }
  }, [aiPrompt, targetMetric, horizonTicks, projectId, selectedNodeId, markDirty, toast]);

  // Create branch from plan
  const handleCreateBranch = useCallback(async () => {
    if (!selectedPlanId) {
      await handleSave();
    }

    const planId = selectedPlanId;
    if (!planId) {
      toast({ title: 'Error', description: 'Please save the plan first', variant: 'destructive' });
      return;
    }

    try {
      const result = await createBranch.mutateAsync({
        planId,
        data: { plan_id: planId, branch_name: `Branch: ${planName}` },
      });

      toast({ title: 'Branch Created', description: result.message });

      // Navigate to Universe Map
      router.push(`/p/${projectId}/universe-map?node=${result.node_id}`);
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to create branch', variant: 'destructive' });
    }
  }, [selectedPlanId, planName, projectId, createBranch, handleSave, router, toast]);

  // Filter runs by node
  const filteredRuns = useMemo((): RunSummary[] => {
    if (!runs) return [];
    if (!selectedNodeId) return runs;
    return runs.filter((r: RunSummary) => r.node_id === selectedNodeId);
  }, [runs, selectedNodeId]);

  const plans = plansData?.plans || [];

  return (
    <div className="min-h-screen bg-black p-4 md:p-6">
      {/* Header */}
      <div className="mb-6">
        <Link href={`/p/${projectId}/overview`}>
          <Button variant="ghost" size="sm" className="mb-3 text-[10px] md:text-xs">
            <ArrowLeft className="w-3 h-3 mr-1 md:mr-2" />
            BACK TO OVERVIEW
          </Button>
        </Link>
        <div className="flex items-center gap-2 mb-1">
          <Crosshair className="w-3.5 h-3.5 md:w-4 md:h-4 text-purple-400" />
          <span className="text-[10px] md:text-xs font-mono text-white/40 uppercase tracking-wider">Target Mode</span>
        </div>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg md:text-xl font-mono font-bold text-white">Target Planner</h1>
            <p className="text-xs md:text-sm font-mono text-white/50 mt-1">
              Define intervention plans and create simulation branches
            </p>
          </div>
          <div className="flex items-center gap-2">
            {isDirty && (
              <span className="text-[10px] font-mono text-amber-400 flex items-center gap-1">
                <AlertCircle className="w-3 h-3" />
                Unsaved
              </span>
            )}
            {lastSaved && !isDirty && (
              <span className="text-[10px] font-mono text-green-400 flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" />
                Saved {lastSaved.toLocaleTimeString()}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Guidance Panel - Blueprint-driven guidance */}
      <div className="max-w-6xl mb-6">
        <GuidancePanel
          projectId={projectId}
          sectionId="target"
          className="mb-0"
        />
      </div>

      <div className="max-w-6xl grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Left Sidebar - Plan List */}
        <div className="lg:col-span-1 space-y-4">
          {/* Plan Selector */}
          <div className="bg-white/5 border border-white/10 p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-xs font-mono font-bold text-white">Plans</h3>
              <Button size="sm" variant="ghost" onClick={handleNewPlan} className="text-[10px] h-6 px-2">
                <Plus className="w-3 h-3 mr-1" />
                NEW
              </Button>
            </div>
            <div className="space-y-1 max-h-60 overflow-y-auto">
              {plansLoading ? (
                <div className="flex items-center justify-center py-4">
                  <Loader2 className="w-4 h-4 text-white/40 animate-spin" />
                </div>
              ) : plans.length === 0 ? (
                <p className="text-[10px] font-mono text-white/40 text-center py-4">
                  No plans yet. Create one!
                </p>
              ) : (
                plans.map(plan => (
                  <button
                    key={plan.id}
                    onClick={() => setSelectedPlanId(plan.id)}
                    className={`w-full text-left p-2 transition-colors ${
                      selectedPlanId === plan.id
                        ? 'bg-purple-500/20 border border-purple-500/30'
                        : 'bg-black/30 border border-white/5 hover:border-white/20'
                    }`}
                  >
                    <div className="text-xs font-mono text-white truncate">{plan.name}</div>
                    <div className="text-[10px] font-mono text-white/40 flex items-center gap-2 mt-1">
                      <span>{plan.source === 'ai' ? '✨ AI' : '✏️ Manual'}</span>
                      <span>•</span>
                      <span>{plan.steps_json?.length || 0} steps</span>
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>

          {/* Context Selectors */}
          <div className="bg-white/5 border border-white/10 p-4">
            <h3 className="text-xs font-mono font-bold text-white mb-3">Context</h3>

            {/* Node Selector */}
            <div className="mb-3">
              <label className="block text-[10px] font-mono text-white/40 uppercase mb-1">
                Starting Node
              </label>
              <select
                value={selectedNodeId || ''}
                onChange={(e) => {
                  setSelectedNodeId(e.target.value || undefined);
                  markDirty();
                }}
                className="w-full px-3 py-2 bg-black border border-white/10 text-xs font-mono text-white focus:outline-none focus:border-purple-500/50"
              >
                <option value="">Select node...</option>
                {nodes?.map((node: NodeSummary) => (
                  <option key={node.node_id} value={node.node_id}>
                    {node.label || `Node ${node.node_id.slice(0, 8)}`}
                  </option>
                ))}
              </select>
            </div>

            {/* Run Selector */}
            <div>
              <label className="block text-[10px] font-mono text-white/40 uppercase mb-1">
                Reference Run (optional)
              </label>
              <select
                value={selectedRunId || ''}
                onChange={(e) => setSelectedRunId(e.target.value || undefined)}
                className="w-full px-3 py-2 bg-black border border-white/10 text-xs font-mono text-white focus:outline-none focus:border-purple-500/50"
              >
                <option value="">Select run...</option>
                {filteredRuns.map((run: RunSummary) => (
                  <option key={run.run_id} value={run.run_id}>
                    {run.run_id.slice(0, 8)} - {run.status}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Main Content - Plan Builder */}
        <div className="lg:col-span-3 space-y-4">
          {/* Plan Header */}
          <div className="bg-white/5 border border-white/10 p-4">
            <div className="flex items-center justify-between mb-4">
              <input
                type="text"
                value={planName}
                onChange={(e) => { setPlanName(e.target.value); markDirty(); }}
                placeholder="Plan name..."
                className="flex-1 bg-transparent text-lg font-mono font-bold text-white border-none outline-none placeholder:text-white/30"
              />
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={handleSave}
                  disabled={isSaving || !planName.trim()}
                  className="text-xs"
                >
                  {isSaving ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}
                  <span className="ml-1">SAVE</span>
                </Button>
                {selectedPlanId && (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={handleDeletePlan}
                    className="text-xs text-red-400 hover:text-red-300"
                  >
                    <Trash2 className="w-3 h-3" />
                  </Button>
                )}
              </div>
            </div>

            {/* Target Definition */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-[10px] font-mono text-white/40 uppercase mb-1">
                  Target Metric
                </label>
                <select
                  value={targetMetric}
                  onChange={(e) => { setTargetMetric(e.target.value); markDirty(); }}
                  className="w-full px-3 py-2 bg-black border border-white/10 text-xs font-mono text-white focus:outline-none focus:border-purple-500/50"
                >
                  {METRIC_OPTIONS.map(opt => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
                {targetMetric === 'custom' && (
                  <input
                    type="text"
                    value={customMetric}
                    onChange={(e) => { setCustomMetric(e.target.value); markDirty(); }}
                    placeholder="Custom metric name..."
                    className="w-full mt-2 px-3 py-2 bg-black border border-white/10 text-xs font-mono text-white focus:outline-none focus:border-purple-500/50"
                  />
                )}
              </div>
              <div>
                <label className="block text-[10px] font-mono text-white/40 uppercase mb-1">
                  Target Value
                </label>
                <input
                  type="number"
                  value={targetValue}
                  onChange={(e) => { setTargetValue(parseFloat(e.target.value) || 0); markDirty(); }}
                  className="w-full px-3 py-2 bg-black border border-white/10 text-xs font-mono text-white focus:outline-none focus:border-purple-500/50"
                />
              </div>
              <div>
                <label className="block text-[10px] font-mono text-white/40 uppercase mb-1">
                  Horizon (ticks)
                </label>
                <input
                  type="number"
                  value={horizonTicks}
                  onChange={(e) => { setHorizonTicks(parseInt(e.target.value) || 100); markDirty(); }}
                  min={1}
                  max={10000}
                  className="w-full px-3 py-2 bg-black border border-white/10 text-xs font-mono text-white focus:outline-none focus:border-purple-500/50"
                />
              </div>
            </div>
          </div>

          {/* AI Generation */}
          <div className="bg-gradient-to-r from-purple-500/10 to-cyan-500/10 border border-purple-500/30 p-4">
            <div className="flex items-center gap-2 mb-3">
              <Sparkles className="w-4 h-4 text-purple-400" />
              <h3 className="text-xs font-mono font-bold text-white">AI Plan Generation</h3>
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                value={aiPrompt}
                onChange={(e) => setAiPrompt(e.target.value)}
                placeholder="What if we increase prices by 10% and launch a marketing campaign?"
                className="flex-1 px-3 py-2 bg-black border border-white/10 text-xs font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-purple-500/50"
              />
              <Button
                size="sm"
                onClick={handleAIGenerate}
                disabled={isGenerating || !aiPrompt.trim()}
                className="text-xs bg-purple-500 hover:bg-purple-600"
              >
                {isGenerating ? <Loader2 className="w-3 h-3 animate-spin" /> : <Sparkles className="w-3 h-3" />}
                <span className="ml-1">GENERATE</span>
              </Button>
            </div>
          </div>

          {/* Intervention Steps */}
          <div className="bg-white/5 border border-white/10 p-4">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Layers className="w-4 h-4 text-cyan-400" />
                <h3 className="text-xs font-mono font-bold text-white">Intervention Steps</h3>
                <span className="text-[10px] font-mono text-white/40">({steps.length})</span>
              </div>
              <Button size="sm" variant="outline" onClick={handleAddStep} className="text-xs">
                <Plus className="w-3 h-3 mr-1" />
                ADD STEP
              </Button>
            </div>

            <div className="space-y-3">
              {steps.length === 0 ? (
                <div className="text-center py-8 border border-dashed border-white/10">
                  <Layers className="w-8 h-8 text-white/20 mx-auto mb-2" />
                  <p className="text-xs font-mono text-white/40">No intervention steps yet</p>
                  <p className="text-[10px] font-mono text-white/30 mt-1">
                    Add steps manually or use AI generation
                  </p>
                </div>
              ) : (
                steps.sort((a, b) => a.tick - b.tick).map((step, index) => (
                  <div
                    key={step.id}
                    className="bg-black/30 border border-white/10 p-3 group"
                  >
                    <div className="flex items-start gap-3">
                      <div className="flex items-center gap-2 mt-1">
                        <GripVertical className="w-4 h-4 text-white/20 cursor-grab" />
                        <div className="w-6 h-6 bg-cyan-500/20 flex items-center justify-center text-[10px] font-mono text-cyan-400">
                          {index + 1}
                        </div>
                      </div>
                      <div className="flex-1 grid grid-cols-1 md:grid-cols-4 gap-3">
                        <div>
                          <label className="block text-[10px] font-mono text-white/40 uppercase mb-1">Tick</label>
                          <input
                            type="number"
                            value={step.tick}
                            onChange={(e) => handleUpdateStep(step.id, { tick: parseInt(e.target.value) || 0 })}
                            min={0}
                            className="w-full px-2 py-1 bg-black border border-white/10 text-xs font-mono text-white focus:outline-none focus:border-cyan-500/50"
                          />
                        </div>
                        <div>
                          <label className="block text-[10px] font-mono text-white/40 uppercase mb-1">Action</label>
                          <select
                            value={step.action_type}
                            onChange={(e) => handleUpdateStep(step.id, { action_type: e.target.value })}
                            className="w-full px-2 py-1 bg-black border border-white/10 text-xs font-mono text-white focus:outline-none focus:border-cyan-500/50"
                          >
                            {ACTION_TYPE_OPTIONS.map(opt => (
                              <option key={opt.value} value={opt.value}>{opt.label}</option>
                            ))}
                          </select>
                        </div>
                        <div>
                          <label className="block text-[10px] font-mono text-white/40 uppercase mb-1">Target</label>
                          <input
                            type="text"
                            value={step.target}
                            onChange={(e) => handleUpdateStep(step.id, { target: e.target.value })}
                            placeholder="all_agents"
                            className="w-full px-2 py-1 bg-black border border-white/10 text-xs font-mono text-white focus:outline-none focus:border-cyan-500/50"
                          />
                        </div>
                        <div>
                          <label className="block text-[10px] font-mono text-white/40 uppercase mb-1">Description</label>
                          <input
                            type="text"
                            value={step.description || ''}
                            onChange={(e) => handleUpdateStep(step.id, { description: e.target.value })}
                            placeholder="What happens..."
                            className="w-full px-2 py-1 bg-black border border-white/10 text-xs font-mono text-white focus:outline-none focus:border-cyan-500/50"
                          />
                        </div>
                      </div>
                      <button
                        onClick={() => handleDeleteStep(step.id)}
                        className="p-1 text-white/20 hover:text-red-400 transition-colors opacity-0 group-hover:opacity-100"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Actions */}
          <div className="flex flex-col md:flex-row gap-4">
            {/* Create Branch */}
            <div className="flex-1 bg-gradient-to-r from-green-500/10 to-emerald-500/10 border border-green-500/30 p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <GitBranch className="w-5 h-5 text-green-400" />
                  <div>
                    <h3 className="text-sm font-mono font-bold text-white">Create Branch</h3>
                    <p className="text-[10px] font-mono text-white/40">
                      Fork from {selectedNodeId ? 'selected node' : 'root'} with this plan
                    </p>
                  </div>
                </div>
                <Button
                  onClick={handleCreateBranch}
                  disabled={createBranch.isPending || steps.length === 0}
                  className="text-xs bg-green-500 hover:bg-green-600"
                >
                  {createBranch.isPending ? (
                    <Loader2 className="w-3 h-3 animate-spin" />
                  ) : (
                    <GitBranch className="w-3 h-3" />
                  )}
                  <span className="ml-1">CREATE BRANCH</span>
                </Button>
              </div>
            </div>

            {/* Quick Links */}
            <div className="flex gap-2">
              <Link href={`/p/${projectId}/universe-map`}>
                <Button variant="outline" size="sm" className="text-xs h-full">
                  <MapIcon className="w-3 h-3 mr-1" />
                  UNIVERSE MAP
                </Button>
              </Link>
              <Link href={`/p/${projectId}/run-center`}>
                <Button variant="outline" size="sm" className="text-xs h-full">
                  <Activity className="w-3 h-3 mr-1" />
                  RUN CENTER
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-8 pt-4 border-t border-white/5 max-w-6xl">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-1">
            <Terminal className="w-3 h-3" />
            <span>TARGET PLANNER</span>
          </div>
          <span>AGENTVERSE v1.0</span>
        </div>
      </div>
    </div>
  );
}
