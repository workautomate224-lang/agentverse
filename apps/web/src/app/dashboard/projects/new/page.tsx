'use client';

/**
 * Create Project Wizard - 4-Step Flow
 * Step 1: Goal (textarea + example chips)
 * Step 2: Temporal Context (mode, as-of date, isolation level)
 * Step 3: Pick a Core (Collective/Target/Hybrid)
 * Step 4: Project Setup (name, tags, visibility)
 *
 * Reference: temporal.md §3 - Create Project Flow UI
 */

import { useState, useCallback, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import * as Dialog from '@radix-ui/react-dialog';
import { Button } from '@/components/ui/button';
import {
  ArrowLeft,
  ArrowRight,
  FolderKanban,
  Target,
  Users,
  Layers,
  Check,
  Terminal,
  ChevronRight,
  Lightbulb,
  Tag,
  Eye,
  EyeOff,
  X,
  Sparkles,
  Loader2,
  AlertCircle,
  Clock,
  Calendar,
  Globe,
  Shield,
  Database,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  Info,
  Save,
  Trash2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useCreateProjectSpec, useCreateBlueprint } from '@/hooks/useApi';
import { isFeatureEnabled } from '@/lib/feature-flags';
import { GoalAssistantPanel } from '@/components/pil/v2/GoalAssistantPanel';
import type { BlueprintDraft } from '@/types/blueprint-v2';

// Wizard step definitions - 4-step flow per temporal.md §3
const STEPS = [
  { id: 'goal', label: 'Goal', number: 1 },
  { id: 'temporal', label: 'Temporal', number: 2 },
  { id: 'core', label: 'Pick Core', number: 3 },
  { id: 'setup', label: 'Setup', number: 4 },
] as const;

type StepId = typeof STEPS[number]['id'];

// Temporal mode options
type TemporalMode = 'live' | 'backtest';

// Isolation level definitions per temporal.md §4
const ISOLATION_LEVELS = [
  {
    level: 1,
    name: 'Level 1 - Basic',
    description: 'Cutoff enforced, but latest-only sources allowed with disclaimer. Suitable for quick exploratory analyses.',
    badge: 'BASIC',
    color: 'amber',
  },
  {
    level: 2,
    name: 'Level 2 - Strict (Recommended)',
    description: 'No latest-only sources permitted. Must use historical or as-of capable sources. Required for publishable backtests.',
    badge: 'STRICT',
    color: 'cyan',
  },
  {
    level: 3,
    name: 'Level 3 - Audit-First',
    description: 'Strictest mode. Output auditor reviews every LLM response. Reserved for regulatory or compliance-sensitive predictions.',
    badge: 'AUDIT',
    color: 'purple',
  },
] as const;

// Common timezone options
const TIMEZONE_OPTIONS = [
  { value: 'Asia/Kuala_Lumpur', label: 'Malaysia (GMT+8)', shortLabel: 'MYT' },
  { value: 'Asia/Singapore', label: 'Singapore (GMT+8)', shortLabel: 'SGT' },
  { value: 'Asia/Hong_Kong', label: 'Hong Kong (GMT+8)', shortLabel: 'HKT' },
  { value: 'Asia/Tokyo', label: 'Japan (GMT+9)', shortLabel: 'JST' },
  { value: 'America/New_York', label: 'US Eastern (GMT-5)', shortLabel: 'EST' },
  { value: 'America/Los_Angeles', label: 'US Pacific (GMT-8)', shortLabel: 'PST' },
  { value: 'Europe/London', label: 'UK (GMT+0)', shortLabel: 'GMT' },
  { value: 'UTC', label: 'UTC (GMT+0)', shortLabel: 'UTC' },
] as const;

// Available data sources (would come from API in production)
const AVAILABLE_SOURCES = [
  { id: 'census_bureau', name: 'US Census Bureau', category: 'Government', badge: 'HISTORICAL' },
  { id: 'eurostat', name: 'Eurostat', category: 'Government', badge: 'HISTORICAL' },
  { id: 'world_bank', name: 'World Bank', category: 'International', badge: 'HISTORICAL' },
  { id: 'imf', name: 'IMF Data', category: 'International', badge: 'HISTORICAL' },
  { id: 'fred', name: 'FRED Economic Data', category: 'Economic', badge: 'HISTORICAL' },
  { id: 'internal_personas', name: 'Internal Personas', category: 'Internal', badge: 'INTERNAL' },
  { id: 'internal_scenarios', name: 'Internal Scenarios', category: 'Internal', badge: 'INTERNAL' },
] as const;

// Example goal chips for quick fill
const EXAMPLE_GOALS = [
  'GE2026 Malaysia election outcome',
  'Ad campaign backlash risk assessment',
  'Policy change impact on inflation sentiment',
  'New product launch reception prediction',
  'Brand perception shift after PR crisis',
];

// Prediction Core options
const PREDICTION_CORES = [
  {
    id: 'collective',
    name: 'Collective Dynamics',
    subtitle: 'Society Mode',
    description: 'Model how opinions, behaviors, and trends emerge and spread through populations. Best for market trends, social movements, public opinion.',
    icon: Users,
    color: 'cyan',
  },
  {
    id: 'target',
    name: 'Targeted Decision',
    subtitle: 'Planner Mode',
    description: 'Simulate individual decision-making processes for specific personas. Best for consumer choice, voting behavior, product adoption.',
    icon: Target,
    color: 'purple',
  },
  {
    id: 'hybrid',
    name: 'Hybrid Strategic',
    subtitle: 'Combined Mode',
    description: 'Combine collective dynamics with targeted decision modeling. Best for complex scenarios involving both social influence and individual choice.',
    icon: Layers,
    color: 'amber',
  },
] as const;

type CoreType = 'collective' | 'target' | 'hybrid';

// Form data interface
interface WizardFormData {
  goal: string;
  // Temporal context fields (per temporal.md §3)
  temporalMode: TemporalMode;
  asOfDate: string; // ISO date string YYYY-MM-DD
  asOfTime: string; // Time string HH:MM
  timezone: string;
  isolationLevel: 1 | 2 | 3;
  allowedSources: string[]; // Source IDs
  backtestConfirmation: boolean; // Required true for backtest
  // Core & setup
  coreType: CoreType;
  name: string;
  tags: string[];
  isPublic: boolean;
}

// Generate a project name from the goal
function generateProjectName(goal: string): string {
  if (!goal.trim()) return '';
  // Take first 40 chars, capitalize first letter
  const name = goal.slice(0, 40).trim();
  return name.charAt(0).toUpperCase() + name.slice(1) + (goal.length > 40 ? '...' : '');
}

// Recommend a core type based on goal keywords
function getRecommendedCore(goal: string): CoreType {
  const lowerGoal = goal.toLowerCase();

  // Keywords suggesting collective dynamics
  const collectiveKeywords = ['election', 'trend', 'movement', 'social', 'public', 'opinion', 'sentiment', 'market'];
  // Keywords suggesting targeted decision
  const targetKeywords = ['consumer', 'product', 'launch', 'adoption', 'choice', 'decision', 'brand', 'campaign'];

  const collectiveScore = collectiveKeywords.filter(k => lowerGoal.includes(k)).length;
  const targetScore = targetKeywords.filter(k => lowerGoal.includes(k)).length;

  if (collectiveScore > targetScore) return 'collective';
  if (targetScore > collectiveScore) return 'target';
  if (collectiveScore > 0 && targetScore > 0) return 'hybrid';

  return 'collective'; // Default
}

// Detect domain from goal text (API expects: marketing, political, finance, custom)
function detectDomain(goal: string): 'marketing' | 'political' | 'finance' | 'custom' {
  const lowerGoal = goal.toLowerCase();

  // Political keywords
  const politicalKeywords = ['election', 'vote', 'voting', 'political', 'policy', 'government', 'candidate', 'campaign', 'democrat', 'republican', 'president', 'congress', 'senator'];
  // Marketing keywords
  const marketingKeywords = ['marketing', 'brand', 'ad', 'advertisement', 'pr', 'public relations', 'product launch', 'customer', 'consumer', 'market share'];
  // Finance keywords
  const financeKeywords = ['finance', 'stock', 'investment', 'trading', 'crypto', 'bitcoin', 'inflation', 'interest rate', 'economy', 'economic', 'gdp', 'market'];

  const politicalScore = politicalKeywords.filter(k => lowerGoal.includes(k)).length;
  const marketingScore = marketingKeywords.filter(k => lowerGoal.includes(k)).length;
  const financeScore = financeKeywords.filter(k => lowerGoal.includes(k)).length;

  // Return highest scoring domain
  if (politicalScore > marketingScore && politicalScore > financeScore) return 'political';
  if (marketingScore > politicalScore && marketingScore > financeScore) return 'marketing';
  if (financeScore > politicalScore && financeScore > marketingScore) return 'finance';

  return 'custom'; // Default
}

export default function CreateProjectWizardPage() {
  const router = useRouter();
  const createProjectMutation = useCreateProjectSpec();
  const createBlueprintMutation = useCreateBlueprint();

  // Feature flag for v2 wizard
  const isV2WizardEnabled = isFeatureEnabled('BLUEPRINT_V2_WIZARD');

  const [currentStep, setCurrentStep] = useState<StepId>('goal');
  // Blueprint draft state for v2 flow
  const [blueprintDraft, setBlueprintDraft] = useState<BlueprintDraft | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [formData, setFormData] = useState<WizardFormData>({
    goal: '',
    // Temporal defaults per temporal.md §3
    temporalMode: 'live',
    asOfDate: '',
    asOfTime: '',
    timezone: 'Asia/Kuala_Lumpur',
    isolationLevel: 2, // Default to Strict for backtests
    allowedSources: AVAILABLE_SOURCES.map(s => s.id), // All sources by default
    backtestConfirmation: false,
    // Core & setup
    coreType: 'collective',
    name: '',
    tags: [],
    isPublic: true,
  });
  const [tagInput, setTagInput] = useState('');
  const [createError, setCreateError] = useState<string | null>(null);
  const [showSourcesPanel, setShowSourcesPanel] = useState(false);
  // Exit confirmation modal state (per blueprint_v2.md §2.1.2)
  const [showExitModal, setShowExitModal] = useState(false);

  // Check if there's unsaved draft state that should trigger exit confirmation
  const hasDraftState = useCallback(() => {
    // Has goal text entered
    const hasGoal = formData.goal.trim().length > 0;
    // Has blueprint draft generated
    const hasBlueprintDraft = blueprintDraft !== null;
    // Is currently analyzing
    const isRunningAnalysis = isAnalyzing;

    return hasGoal || hasBlueprintDraft || isRunningAnalysis;
  }, [formData.goal, blueprintDraft, isAnalyzing]);

  // Handle cancel button click - show modal if draft state exists
  const handleCancelClick = useCallback(() => {
    if (hasDraftState()) {
      setShowExitModal(true);
    } else {
      router.push('/dashboard/projects');
    }
  }, [hasDraftState, router]);

  // Handle discard and exit
  const handleDiscardExit = useCallback(() => {
    // Clear all state and navigate away
    setShowExitModal(false);
    router.push('/dashboard/projects');
  }, [router]);

  // Handle save draft and exit (for future implementation)
  const handleSaveDraftExit = useCallback(() => {
    // TODO: In Phase B.3, implement localStorage draft persistence
    // For now, just show a toast and exit
    setShowExitModal(false);
    // Store draft to localStorage
    if (typeof window !== 'undefined') {
      const draftData = {
        goal: formData.goal,
        blueprintDraft,
        temporalMode: formData.temporalMode,
        asOfDate: formData.asOfDate,
        asOfTime: formData.asOfTime,
        timezone: formData.timezone,
        isolationLevel: formData.isolationLevel,
        coreType: formData.coreType,
        savedAt: new Date().toISOString(),
      };
      localStorage.setItem('agentverse_project_draft', JSON.stringify(draftData));
    }
    router.push('/dashboard/projects');
  }, [formData, blueprintDraft, router]);

  // Handle browser back button / navigation away
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (hasDraftState()) {
        e.preventDefault();
        e.returnValue = '';
        return '';
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [hasDraftState]);

  // Get current step index
  const currentStepIndex = STEPS.findIndex(s => s.id === currentStep);

  // Get recommended core based on goal
  const recommendedCore = getRecommendedCore(formData.goal);

  // Navigation handlers
  const goToStep = (stepId: StepId) => {
    setCurrentStep(stepId);
  };

  const goNext = () => {
    const nextIndex = currentStepIndex + 1;
    if (nextIndex < STEPS.length) {
      // Auto-generate name when moving to setup step
      if (STEPS[nextIndex].id === 'setup' && !formData.name) {
        setFormData(prev => ({
          ...prev,
          name: generateProjectName(prev.goal),
        }));
      }
      setCurrentStep(STEPS[nextIndex].id);
    }
  };

  const goBack = () => {
    const prevIndex = currentStepIndex - 1;
    if (prevIndex >= 0) {
      setCurrentStep(STEPS[prevIndex].id);
    }
  };

  // Callback for when blueprint is ready in v2 flow
  const handleBlueprintReady = useCallback((blueprint: BlueprintDraft) => {
    setBlueprintDraft(blueprint);
    // Auto-set core type from blueprint strategy
    if (blueprint.strategy?.chosen_core) {
      setFormData(prev => ({ ...prev, coreType: blueprint.strategy.chosen_core }));
    }
  }, []);

  // Validation per step (blueprint_v3.md - always requires blueprint)
  const isStepValid = (stepId: StepId): boolean => {
    switch (stepId) {
      case 'goal':
        // Blueprint v3: Always requires blueprint to be generated before proceeding
        return formData.goal.trim().length >= 10 && blueprintDraft !== null;
      case 'temporal':
        // Live mode: always valid (no temporal constraints)
        if (formData.temporalMode === 'live') return true;
        // Backtest mode: requires date, time, and confirmation
        const hasDate = formData.asOfDate.trim().length > 0;
        const hasTime = formData.asOfTime.trim().length > 0;
        const hasConfirmation = formData.backtestConfirmation;
        // Validate date is not in the future
        if (hasDate && hasTime) {
          const asOfDateTime = new Date(`${formData.asOfDate}T${formData.asOfTime}`);
          if (asOfDateTime > new Date()) return false; // Cannot be in future
        }
        return hasDate && hasTime && hasConfirmation;
      case 'core':
        return !!formData.coreType;
      case 'setup':
        // Blueprint v3: Project cannot be created without finalized blueprint
        return formData.name.trim().length >= 3 && blueprintDraft !== null;
      default:
        return false;
    }
  };

  // Check if as-of date is in the future (validation helper)
  const isAsOfInFuture = (): boolean => {
    if (formData.asOfDate && formData.asOfTime) {
      const asOfDateTime = new Date(`${formData.asOfDate}T${formData.asOfTime}`);
      return asOfDateTime > new Date();
    }
    return false;
  };

  // Handle example chip click
  const handleExampleClick = (example: string) => {
    setFormData(prev => ({ ...prev, goal: example }));
  };

  // Handle tag input
  const handleAddTag = useCallback(() => {
    const tag = tagInput.trim().toLowerCase();
    if (tag && !formData.tags.includes(tag) && formData.tags.length < 5) {
      setFormData(prev => ({ ...prev, tags: [...prev.tags, tag] }));
      setTagInput('');
    }
  }, [tagInput, formData.tags]);

  const handleRemoveTag = (tagToRemove: string) => {
    setFormData(prev => ({
      ...prev,
      tags: prev.tags.filter(t => t !== tagToRemove),
    }));
  };

  const handleTagKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAddTag();
    }
  };

  // Handle form submission - creates project via API and navigates to workspace
  // Blueprint v3: Project cannot be created without finalized blueprint
  const handleCreate = async () => {
    setCreateError(null);

    // Blueprint v3 enforcement: Fail early if blueprint is missing
    if (!blueprintDraft) {
      setCreateError('Blueprint is required. Please complete goal analysis in Step 1 before creating a project.');
      return;
    }

    try {
      // Detect domain from goal (API expects: marketing, political, finance, custom)
      const domain = detectDomain(formData.goal);

      // Build temporal context for backtest mode
      let temporalContext = undefined;
      if (formData.temporalMode === 'backtest') {
        // Construct ISO datetime from date and time
        const asOfDateTimeIso = `${formData.asOfDate}T${formData.asOfTime}:00`;
        temporalContext = {
          mode: 'backtest' as const,
          as_of_datetime: asOfDateTimeIso,
          timezone: formData.timezone,
          isolation_level: formData.isolationLevel,
          allowed_sources: formData.allowedSources,
        };
      }

      // Create project via backend API
      const project = await createProjectMutation.mutateAsync({
        name: formData.name,
        description: formData.goal,
        domain, // auto-detected from goal text
        settings: {
          default_horizon: 100,
          default_tick_rate: 1000,
          default_agent_count: 100,
          allow_public_templates: formData.isPublic,
        },
        // Include temporal context if backtest mode (per temporal.md §3)
        ...(temporalContext && { temporal_context: temporalContext }),
      });

      // Create Blueprint with finalized v1 (blueprint_v3.md requirement)
      // Blueprint draft was already generated in Step 1, now commit it to the project
      await createBlueprintMutation.mutateAsync({
        project_id: project.id,
        goal_text: formData.goal,
        // Skip clarification since it was already done in Step 1
        skip_clarification: true,
      });

      // Navigate to the project workspace using real UUID from backend
      // Overview is read-only per blueprint_v3.md
      router.push(`/p/${project.id}/overview`);
    } catch (error) {
      setCreateError(error instanceof Error ? error.message : 'Failed to create project');
    }
  };

  return (
    <div className="min-h-screen bg-black p-4 md:p-6">
      {/* Header */}
      <div className="mb-6 md:mb-8">
        <Link href="/dashboard/projects">
          <Button variant="ghost" size="sm" className="mb-3 md:mb-4 text-[10px] md:text-xs">
            <ArrowLeft className="w-3 h-3 mr-1 md:mr-2" />
            BACK TO PROJECTS
          </Button>
        </Link>
        <div className="flex items-center gap-2 mb-1">
          <FolderKanban className="w-3.5 h-3.5 md:w-4 md:h-4 text-cyan-400" />
          <span className="text-[10px] md:text-xs font-mono text-white/40 uppercase tracking-wider">Create Project</span>
        </div>
        <h1 className="text-lg md:text-xl font-mono font-bold text-white">New Project</h1>
        <p className="text-xs md:text-sm font-mono text-white/50 mt-1">
          Define your prediction goal and set up your project
        </p>
      </div>

      {/* Step Indicator */}
      <div className="flex items-center gap-1 md:gap-2 mb-6 md:mb-8 max-w-2xl">
        {STEPS.map((step, index) => {
          const isActive = step.id === currentStep;
          const isCompleted = index < currentStepIndex;
          const isClickable = index <= currentStepIndex || (index === currentStepIndex + 1 && isStepValid(currentStep));

          return (
            <div key={step.id} className="flex items-center flex-1">
              <button
                onClick={() => isClickable && goToStep(step.id)}
                disabled={!isClickable}
                className={cn(
                  'flex items-center gap-2 md:gap-3 px-3 md:px-4 py-2 md:py-2.5 border transition-all flex-1',
                  isActive
                    ? 'bg-cyan-500/20 border-cyan-500/50 text-cyan-400'
                    : isCompleted
                    ? 'bg-green-500/10 border-green-500/30 text-green-400'
                    : 'bg-white/5 border-white/10 text-white/40',
                  isClickable && !isActive && 'hover:bg-white/10 cursor-pointer'
                )}
              >
                <span className={cn(
                  'w-5 h-5 md:w-6 md:h-6 flex items-center justify-center text-[10px] md:text-xs font-mono font-bold flex-shrink-0',
                  isCompleted ? 'bg-green-500 text-black' : isActive ? 'bg-cyan-500 text-black' : 'bg-white/10'
                )}>
                  {isCompleted ? <Check className="w-3 h-3" /> : step.number}
                </span>
                <span className="text-xs md:text-sm font-mono hidden sm:block">{step.label}</span>
              </button>
              {index < STEPS.length - 1 && (
                <ChevronRight className="w-4 h-4 text-white/20 mx-1 md:mx-2 flex-shrink-0" />
              )}
            </div>
          );
        })}
      </div>

      {/* Step Content */}
      <div className="max-w-2xl">
        {/* Step 1: Goal */}
        {currentStep === 'goal' && (
          <div className="bg-white/5 border border-white/10 p-4 md:p-6">
            <div className="flex items-center gap-2 mb-4 md:mb-6">
              <Lightbulb className="w-4 h-4 md:w-5 md:h-5 text-cyan-400" />
              <h2 className="text-base md:text-lg font-mono font-bold text-white">What do you want to predict?</h2>
            </div>

            <div className="space-y-4 md:space-y-6">
              {/* Goal Textarea */}
              <div>
                <textarea
                  value={formData.goal}
                  onChange={(e) => setFormData({ ...formData, goal: e.target.value })}
                  placeholder="Describe your prediction goal in detail..."
                  rows={5}
                  className="w-full px-3 md:px-4 py-2 md:py-3 bg-black border border-white/10 text-sm md:text-base font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-cyan-500/50 resize-none"
                />
                <div className="flex justify-between mt-2">
                  <p className="text-[10px] md:text-xs font-mono text-white/30">
                    Minimum 10 characters
                  </p>
                  <p className={cn(
                    'text-[10px] md:text-xs font-mono',
                    formData.goal.length >= 10 ? 'text-green-400' : 'text-white/30'
                  )}>
                    {formData.goal.length} characters
                  </p>
                </div>
              </div>

              {/* Example Chips */}
              <div>
                <label className="block text-[10px] md:text-xs font-mono text-white/40 uppercase mb-2 md:mb-3">
                  <Sparkles className="w-3 h-3 inline mr-1" />
                  Quick Examples (click to use)
                </label>
                <div className="flex flex-wrap gap-2">
                  {EXAMPLE_GOALS.map((example) => (
                    <button
                      key={example}
                      type="button"
                      onClick={() => handleExampleClick(example)}
                      className={cn(
                        'px-2.5 md:px-3 py-1.5 text-[10px] md:text-xs font-mono border transition-all',
                        formData.goal === example
                          ? 'bg-cyan-500/20 border-cyan-500/50 text-cyan-400'
                          : 'bg-white/5 border-white/10 text-white/60 hover:border-white/30 hover:text-white'
                      )}
                    >
                      {example}
                    </button>
                  ))}
                </div>
              </div>

              {/* V2 Goal Assistant Panel - Analyze Goal, Clarify, Blueprint Preview */}
              {isV2WizardEnabled && formData.goal.trim().length >= 10 && (
                <GoalAssistantPanel
                  goalText={formData.goal}
                  onBlueprintReady={handleBlueprintReady}
                  onAnalysisStart={() => setIsAnalyzing(true)}
                  className="mt-4"
                />
              )}

              {/* V2 Mode Indicator */}
              {isV2WizardEnabled && (
                <div className="flex items-center gap-2 pt-4 border-t border-white/10 mt-4">
                  <div className="w-2 h-2 bg-cyan-400 animate-pulse" />
                  <span className="text-[10px] font-mono text-white/40">
                    BLUEPRINT V2 MODE — {blueprintDraft ? 'Blueprint Ready' : 'Analyze goal to continue'}
                  </span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Step 2: Temporal Context (per temporal.md §3) */}
        {currentStep === 'temporal' && (
          <div className="space-y-4">
            {/* Mode Selector */}
            <div className="bg-white/5 border border-white/10 p-4 md:p-6">
              <div className="flex items-center gap-2 mb-4">
                <Clock className="w-4 h-4 md:w-5 md:h-5 text-cyan-400" />
                <h2 className="text-base md:text-lg font-mono font-bold text-white">Temporal Context</h2>
              </div>
              <p className="text-xs md:text-sm font-mono text-white/50 mb-4 md:mb-6">
                Choose how your project handles time and data access.
              </p>

              {/* Mode Selection */}
              <div className="space-y-3 mb-6">
                <label className="block text-[10px] md:text-xs font-mono text-white/40 uppercase mb-2">
                  Prediction Mode
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {/* Live Mode */}
                  <button
                    type="button"
                    onClick={() => setFormData(prev => ({
                      ...prev,
                      temporalMode: 'live',
                      backtestConfirmation: false,
                    }))}
                    className={cn(
                      'flex flex-col items-start p-4 border transition-all text-left',
                      formData.temporalMode === 'live'
                        ? 'bg-green-500/10 border-green-500/50'
                        : 'bg-black border-white/10 hover:border-white/20'
                    )}
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <div className={cn(
                        'w-4 h-4 border flex items-center justify-center',
                        formData.temporalMode === 'live' ? 'border-green-500 bg-green-500/20' : 'border-white/20'
                      )}>
                        {formData.temporalMode === 'live' && <Check className="w-3 h-3 text-green-400" />}
                      </div>
                      <span className={cn(
                        'text-sm font-mono font-bold',
                        formData.temporalMode === 'live' ? 'text-green-400' : 'text-white'
                      )}>
                        Live Mode
                      </span>
                      <span className="px-2 py-0.5 bg-green-500/20 text-green-400 text-[9px] font-mono">
                        DEFAULT
                      </span>
                    </div>
                    <p className="text-xs font-mono text-white/50 leading-relaxed">
                      Real-time predictions using the latest available data. No temporal restrictions applied.
                    </p>
                  </button>

                  {/* Backtest Mode */}
                  <button
                    type="button"
                    onClick={() => setFormData(prev => ({
                      ...prev,
                      temporalMode: 'backtest',
                    }))}
                    className={cn(
                      'flex flex-col items-start p-4 border transition-all text-left',
                      formData.temporalMode === 'backtest'
                        ? 'bg-amber-500/10 border-amber-500/50'
                        : 'bg-black border-white/10 hover:border-white/20'
                    )}
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <div className={cn(
                        'w-4 h-4 border flex items-center justify-center',
                        formData.temporalMode === 'backtest' ? 'border-amber-500 bg-amber-500/20' : 'border-white/20'
                      )}>
                        {formData.temporalMode === 'backtest' && <Check className="w-3 h-3 text-amber-400" />}
                      </div>
                      <span className={cn(
                        'text-sm font-mono font-bold',
                        formData.temporalMode === 'backtest' ? 'text-amber-400' : 'text-white'
                      )}>
                        Backtest Mode
                      </span>
                    </div>
                    <p className="text-xs font-mono text-white/50 leading-relaxed">
                      Simulate as-of a historical date. All data is filtered to enforce temporal isolation.
                    </p>
                  </button>
                </div>
              </div>

              {/* Backtest Configuration (visible only in backtest mode) */}
              {formData.temporalMode === 'backtest' && (
                <div className="space-y-4 pt-4 border-t border-white/10">
                  {/* As-of Date/Time */}
                  <div>
                    <label className="block text-[10px] md:text-xs font-mono text-white/40 uppercase mb-2">
                      <Calendar className="w-3 h-3 inline mr-1" />
                      As-of Date & Time <span className="text-red-400">*</span>
                    </label>
                    <div className="grid grid-cols-2 gap-3">
                      <input
                        type="date"
                        value={formData.asOfDate}
                        onChange={(e) => setFormData(prev => ({ ...prev, asOfDate: e.target.value }))}
                        max={new Date().toISOString().split('T')[0]}
                        className="w-full px-3 py-2 bg-black border border-white/10 text-sm font-mono text-white focus:outline-none focus:border-cyan-500/50"
                      />
                      <input
                        type="time"
                        value={formData.asOfTime}
                        onChange={(e) => setFormData(prev => ({ ...prev, asOfTime: e.target.value }))}
                        className="w-full px-3 py-2 bg-black border border-white/10 text-sm font-mono text-white focus:outline-none focus:border-cyan-500/50"
                      />
                    </div>
                    {isAsOfInFuture() && (
                      <div className="flex items-center gap-2 mt-2 text-red-400">
                        <AlertTriangle className="w-3 h-3" />
                        <span className="text-[10px] font-mono">As-of date cannot be in the future</span>
                      </div>
                    )}
                    <p className="text-[10px] font-mono text-white/30 mt-2">
                      The simulation will pretend it is this date. No data after this point will be accessible.
                    </p>
                  </div>

                  {/* Timezone */}
                  <div>
                    <label className="block text-[10px] md:text-xs font-mono text-white/40 uppercase mb-2">
                      <Globe className="w-3 h-3 inline mr-1" />
                      Timezone
                    </label>
                    <select
                      value={formData.timezone}
                      onChange={(e) => setFormData(prev => ({ ...prev, timezone: e.target.value }))}
                      className="w-full px-3 py-2 bg-black border border-white/10 text-sm font-mono text-white focus:outline-none focus:border-cyan-500/50"
                    >
                      {TIMEZONE_OPTIONS.map((tz) => (
                        <option key={tz.value} value={tz.value}>
                          {tz.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Isolation Level */}
                  <div>
                    <label className="block text-[10px] md:text-xs font-mono text-white/40 uppercase mb-2">
                      <Shield className="w-3 h-3 inline mr-1" />
                      Isolation Level
                    </label>
                    <div className="space-y-2">
                      {ISOLATION_LEVELS.map((level) => {
                        const isSelected = formData.isolationLevel === level.level;
                        const colorClasses = {
                          amber: { bg: 'bg-amber-500/10', border: 'border-amber-500/50', text: 'text-amber-400', badge: 'bg-amber-500/20 text-amber-400' },
                          cyan: { bg: 'bg-cyan-500/10', border: 'border-cyan-500/50', text: 'text-cyan-400', badge: 'bg-cyan-500/20 text-cyan-400' },
                          purple: { bg: 'bg-purple-500/10', border: 'border-purple-500/50', text: 'text-purple-400', badge: 'bg-purple-500/20 text-purple-400' },
                        }[level.color];

                        return (
                          <button
                            key={level.level}
                            type="button"
                            onClick={() => setFormData(prev => ({ ...prev, isolationLevel: level.level as 1 | 2 | 3 }))}
                            className={cn(
                              'w-full flex items-start gap-3 p-3 border transition-all text-left',
                              isSelected
                                ? `${colorClasses.bg} ${colorClasses.border}`
                                : 'bg-black border-white/10 hover:border-white/20'
                            )}
                          >
                            <div className={cn(
                              'w-4 h-4 border flex items-center justify-center flex-shrink-0 mt-0.5',
                              isSelected ? `${colorClasses.border} ${colorClasses.bg}` : 'border-white/20'
                            )}>
                              {isSelected && <Check className={cn('w-3 h-3', colorClasses.text)} />}
                            </div>
                            <div className="flex-1">
                              <div className="flex items-center gap-2">
                                <span className={cn('text-sm font-mono font-bold', isSelected ? colorClasses.text : 'text-white')}>
                                  {level.name}
                                </span>
                                <span className={cn('px-2 py-0.5 text-[9px] font-mono', colorClasses.badge)}>
                                  {level.badge}
                                </span>
                              </div>
                              <p className="text-xs font-mono text-white/50 mt-1 leading-relaxed">
                                {level.description}
                              </p>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Allowed Sources (Collapsible) */}
                  <div>
                    <button
                      type="button"
                      onClick={() => setShowSourcesPanel(!showSourcesPanel)}
                      className="flex items-center justify-between w-full text-left"
                    >
                      <label className="text-[10px] md:text-xs font-mono text-white/40 uppercase cursor-pointer">
                        <Database className="w-3 h-3 inline mr-1" />
                        Allowed Data Sources ({formData.allowedSources.length} selected)
                      </label>
                      {showSourcesPanel ? (
                        <ChevronUp className="w-4 h-4 text-white/40" />
                      ) : (
                        <ChevronDown className="w-4 h-4 text-white/40" />
                      )}
                    </button>

                    {showSourcesPanel && (
                      <div className="mt-3 space-y-2">
                        {AVAILABLE_SOURCES.map((source) => {
                          const isChecked = formData.allowedSources.includes(source.id);
                          return (
                            <label
                              key={source.id}
                              className={cn(
                                'flex items-center gap-3 p-2 border cursor-pointer transition-all',
                                isChecked
                                  ? 'bg-cyan-500/5 border-cyan-500/30'
                                  : 'bg-black border-white/10 hover:border-white/20'
                              )}
                            >
                              <input
                                type="checkbox"
                                checked={isChecked}
                                onChange={(e) => {
                                  if (e.target.checked) {
                                    setFormData(prev => ({
                                      ...prev,
                                      allowedSources: [...prev.allowedSources, source.id],
                                    }));
                                  } else {
                                    setFormData(prev => ({
                                      ...prev,
                                      allowedSources: prev.allowedSources.filter(s => s !== source.id),
                                    }));
                                  }
                                }}
                                className="w-4 h-4 accent-cyan-500"
                              />
                              <span className="flex-1 text-xs font-mono text-white/80">{source.name}</span>
                              <span className="text-[9px] font-mono text-white/40">{source.category}</span>
                              <span className={cn(
                                'px-2 py-0.5 text-[9px] font-mono',
                                source.badge === 'HISTORICAL' ? 'bg-green-500/20 text-green-400' : 'bg-cyan-500/20 text-cyan-400'
                              )}>
                                {source.badge}
                              </span>
                            </label>
                          );
                        })}
                      </div>
                    )}
                  </div>

                  {/* Confirmation Checkbox */}
                  <div className="pt-4 border-t border-white/10">
                    <label className={cn(
                      'flex items-start gap-3 p-4 border cursor-pointer transition-all',
                      formData.backtestConfirmation
                        ? 'bg-amber-500/10 border-amber-500/50'
                        : 'bg-black border-white/10 hover:border-white/20'
                    )}>
                      <input
                        type="checkbox"
                        checked={formData.backtestConfirmation}
                        onChange={(e) => setFormData(prev => ({ ...prev, backtestConfirmation: e.target.checked }))}
                        className="w-5 h-5 mt-0.5 accent-amber-500"
                      />
                      <div>
                        <span className={cn(
                          'text-sm font-mono font-bold block',
                          formData.backtestConfirmation ? 'text-amber-400' : 'text-white'
                        )}>
                          I understand this is a backtest simulation
                        </span>
                        <p className="text-xs font-mono text-white/50 mt-1 leading-relaxed">
                          The temporal context will be <strong className="text-white/70">locked</strong> once the project is created.
                          All data access will be restricted to before the as-of date. This cannot be changed after creation.
                        </p>
                      </div>
                    </label>
                  </div>
                </div>
              )}

              {/* Live Mode Info */}
              {formData.temporalMode === 'live' && (
                <div className="flex items-start gap-3 p-4 bg-green-500/5 border border-green-500/20">
                  <Info className="w-5 h-5 text-green-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <span className="text-sm font-mono text-green-400 font-bold block">Live Mode Selected</span>
                    <p className="text-xs font-mono text-white/50 mt-1">
                      Your project will use real-time data without temporal restrictions.
                      You can proceed to the next step.
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Step 3: Pick a Core */}
        {currentStep === 'core' && (
          <div className="bg-white/5 border border-white/10 p-4 md:p-6">
            <div className="flex items-center gap-2 mb-2">
              <Layers className="w-4 h-4 md:w-5 md:h-5 text-purple-400" />
              <h2 className="text-base md:text-lg font-mono font-bold text-white">Pick a Core</h2>
            </div>
            <p className="text-xs md:text-sm font-mono text-white/50 mb-4 md:mb-6">
              Recommended: <span className="text-cyan-400">{PREDICTION_CORES.find(c => c.id === recommendedCore)?.name}</span>
            </p>

            <div className="space-y-3">
              {PREDICTION_CORES.map((core) => {
                const isSelected = formData.coreType === core.id;
                const isRecommended = core.id === recommendedCore;
                const Icon = core.icon;
                const colorClasses = {
                  cyan: { bg: 'bg-cyan-500/10', border: 'border-cyan-500/50', text: 'text-cyan-400', iconBg: 'bg-cyan-500/20' },
                  purple: { bg: 'bg-purple-500/10', border: 'border-purple-500/50', text: 'text-purple-400', iconBg: 'bg-purple-500/20' },
                  amber: { bg: 'bg-amber-500/10', border: 'border-amber-500/50', text: 'text-amber-400', iconBg: 'bg-amber-500/20' },
                }[core.color];

                return (
                  <button
                    key={core.id}
                    type="button"
                    onClick={() => setFormData({ ...formData, coreType: core.id as CoreType })}
                    className={cn(
                      'w-full flex items-start gap-3 md:gap-4 p-3 md:p-4 border transition-all text-left',
                      isSelected
                        ? `${colorClasses.bg} ${colorClasses.border}`
                        : 'bg-black border-white/10 hover:border-white/20'
                    )}
                  >
                    <div className={cn(
                      'w-12 h-12 md:w-14 md:h-14 flex items-center justify-center flex-shrink-0',
                      isSelected ? colorClasses.iconBg : 'bg-white/5'
                    )}>
                      <Icon className={cn('w-6 h-6 md:w-7 md:h-7', isSelected ? colorClasses.text : 'text-white/40')} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className={cn('text-sm md:text-base font-mono font-bold', isSelected ? colorClasses.text : 'text-white')}>
                          {core.name}
                        </h3>
                        <span className="text-[10px] md:text-xs font-mono text-white/40">
                          ({core.subtitle})
                        </span>
                        {isRecommended && (
                          <span className="px-2 py-0.5 bg-green-500/20 text-green-400 text-[9px] md:text-[10px] font-mono">
                            RECOMMENDED
                          </span>
                        )}
                      </div>
                      <p className="text-xs md:text-sm font-mono text-white/50 mt-1.5 leading-relaxed">
                        {core.description}
                      </p>
                    </div>
                    <div className={cn(
                      'w-5 h-5 md:w-6 md:h-6 border flex items-center justify-center flex-shrink-0 mt-1',
                      isSelected ? `${colorClasses.border} ${colorClasses.bg}` : 'border-white/20'
                    )}>
                      {isSelected && <Check className={cn('w-3 h-3 md:w-4 md:h-4', colorClasses.text)} />}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Step 4: Project Setup */}
        {currentStep === 'setup' && (
          <div className="space-y-4">
            {/* Project Name */}
            <div className="bg-white/5 border border-white/10 p-4 md:p-6">
              <div className="flex items-center gap-2 mb-4">
                <FolderKanban className="w-4 h-4 md:w-5 md:h-5 text-white/60" />
                <h2 className="text-base md:text-lg font-mono font-bold text-white">Project Setup</h2>
              </div>

              <div className="space-y-4">
                {/* Name */}
                <div>
                  <label className="block text-[10px] md:text-xs font-mono text-white/60 uppercase mb-2">
                    Project Name <span className="text-red-400">*</span>
                  </label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="Enter project name..."
                    className="w-full px-3 md:px-4 py-2 md:py-2.5 bg-black border border-white/10 text-sm md:text-base font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-cyan-500/50"
                  />
                  <p className="text-[10px] md:text-xs font-mono text-white/30 mt-2">
                    Auto-generated from your goal. Edit if needed.
                  </p>
                </div>

                {/* Tags */}
                <div>
                  <label className="block text-[10px] md:text-xs font-mono text-white/60 uppercase mb-2">
                    <Tag className="w-3 h-3 inline mr-1" />
                    Tags (optional)
                  </label>
                  <div className="flex gap-2 mb-2">
                    <input
                      type="text"
                      value={tagInput}
                      onChange={(e) => setTagInput(e.target.value)}
                      onKeyDown={handleTagKeyDown}
                      placeholder="Add a tag..."
                      className="flex-1 px-3 py-2 bg-black border border-white/10 text-xs md:text-sm font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-white/30"
                    />
                    <Button
                      type="button"
                      variant="secondary"
                      size="sm"
                      onClick={handleAddTag}
                      disabled={!tagInput.trim() || formData.tags.length >= 5}
                      className="text-xs"
                    >
                      Add
                    </Button>
                  </div>
                  {formData.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {formData.tags.map((tag) => (
                        <span
                          key={tag}
                          className="inline-flex items-center gap-1 px-2 py-1 bg-white/10 text-xs font-mono text-white/70"
                        >
                          #{tag}
                          <button
                            type="button"
                            onClick={() => handleRemoveTag(tag)}
                            className="text-white/40 hover:text-white"
                          >
                            <X className="w-3 h-3" />
                          </button>
                        </span>
                      ))}
                    </div>
                  )}
                  <p className="text-[10px] font-mono text-white/30 mt-2">
                    Up to 5 tags. Press Enter to add.
                  </p>
                </div>

                {/* Visibility */}
                <div>
                  <label className="block text-[10px] md:text-xs font-mono text-white/60 uppercase mb-2">
                    Visibility
                  </label>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setFormData({ ...formData, isPublic: true })}
                      className={cn(
                        'flex-1 flex items-center justify-center gap-2 px-3 py-2.5 border transition-all',
                        formData.isPublic
                          ? 'bg-cyan-500/20 border-cyan-500/50 text-cyan-400'
                          : 'bg-black border-white/10 text-white/60 hover:border-white/20'
                      )}
                    >
                      <Eye className="w-4 h-4" />
                      <span className="text-xs font-mono">Public</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setFormData({ ...formData, isPublic: false })}
                      className={cn(
                        'flex-1 flex items-center justify-center gap-2 px-3 py-2.5 border transition-all',
                        !formData.isPublic
                          ? 'bg-purple-500/20 border-purple-500/50 text-purple-400'
                          : 'bg-black border-white/10 text-white/60 hover:border-white/20'
                      )}
                    >
                      <EyeOff className="w-4 h-4" />
                      <span className="text-xs font-mono">Private</span>
                    </button>
                  </div>
                  <p className="text-[10px] font-mono text-white/30 mt-2">
                    {formData.isPublic
                      ? 'Project visible to all team members'
                      : 'Only you can access this project'}
                  </p>
                </div>
              </div>
            </div>

            {/* Summary */}
            <div className="bg-white/5 border border-white/10 p-4 md:p-6">
              <h3 className="text-xs font-mono text-white/40 uppercase mb-3">Summary</h3>
              <div className="space-y-2 text-sm font-mono">
                <div className="flex justify-between">
                  <span className="text-white/50">Goal:</span>
                  <span className="text-white/80 text-right max-w-[60%] truncate">{formData.goal}</span>
                </div>
                {/* Temporal Context Summary */}
                <div className="flex justify-between">
                  <span className="text-white/50">Mode:</span>
                  <span className={cn(
                    'px-2 py-0.5 text-xs',
                    formData.temporalMode === 'live' ? 'bg-green-500/20 text-green-400' : 'bg-amber-500/20 text-amber-400'
                  )}>
                    {formData.temporalMode === 'live' ? 'LIVE' : 'BACKTEST'}
                  </span>
                </div>
                {formData.temporalMode === 'backtest' && (
                  <>
                    <div className="flex justify-between">
                      <span className="text-white/50">As-of:</span>
                      <span className="text-white/80">
                        {formData.asOfDate} {formData.asOfTime}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-white/50">Isolation:</span>
                      <span className={cn(
                        'px-2 py-0.5 text-xs',
                        formData.isolationLevel === 1 && 'bg-amber-500/20 text-amber-400',
                        formData.isolationLevel === 2 && 'bg-cyan-500/20 text-cyan-400',
                        formData.isolationLevel === 3 && 'bg-purple-500/20 text-purple-400'
                      )}>
                        Level {formData.isolationLevel}
                      </span>
                    </div>
                  </>
                )}
                <div className="flex justify-between">
                  <span className="text-white/50">Core:</span>
                  <span className={cn(
                    'px-2 py-0.5 text-xs',
                    formData.coreType === 'collective' && 'bg-cyan-500/20 text-cyan-400',
                    formData.coreType === 'target' && 'bg-purple-500/20 text-purple-400',
                    formData.coreType === 'hybrid' && 'bg-amber-500/20 text-amber-400'
                  )}>
                    {PREDICTION_CORES.find(c => c.id === formData.coreType)?.name}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-white/50">Visibility:</span>
                  <span className="text-white/80">{formData.isPublic ? 'Public' : 'Private'}</span>
                </div>
              </div>
            </div>

            {/* Error Display */}
            {createError && (
              <div className="bg-red-500/10 border border-red-500/30 p-4 flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-mono text-red-400 font-bold">Failed to create project</p>
                  <p className="text-xs font-mono text-red-400/70 mt-1">{createError}</p>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Navigation Buttons */}
        <div className="flex flex-col-reverse sm:flex-row justify-between gap-3 mt-6">
          <div>
            {currentStepIndex > 0 && (
              <Button variant="secondary" onClick={goBack} size="sm" className="w-full sm:w-auto text-xs">
                <ArrowLeft className="w-3 h-3 mr-2" />
                BACK
              </Button>
            )}
          </div>
          <div className="flex flex-col sm:flex-row gap-2 md:gap-3">
            <Button
              variant="outline"
              size="sm"
              className="w-full sm:w-auto text-xs"
              onClick={handleCancelClick}
            >
              CANCEL
            </Button>
            {currentStep === 'setup' ? (
              <Button
                onClick={handleCreate}
                disabled={!isStepValid('setup') || createProjectMutation.isPending || createBlueprintMutation.isPending}
                size="sm"
                className="w-full sm:w-auto text-xs"
              >
                {createProjectMutation.isPending ? (
                  <>
                    <Loader2 className="w-3 h-3 mr-2 animate-spin" />
                    CREATING PROJECT...
                  </>
                ) : createBlueprintMutation.isPending ? (
                  <>
                    <Loader2 className="w-3 h-3 mr-2 animate-spin" />
                    ANALYZING GOAL...
                  </>
                ) : (
                  <>
                    <FolderKanban className="w-3 h-3 mr-2" />
                    CREATE PROJECT
                  </>
                )}
              </Button>
            ) : (
              <Button
                onClick={goNext}
                disabled={!isStepValid(currentStep)}
                size="sm"
                className="w-full sm:w-auto text-xs"
              >
                NEXT
                <ArrowRight className="w-3 h-3 ml-2" />
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Exit Confirmation Modal (per blueprint_v2.md §2.1.2) */}
      <Dialog.Root open={showExitModal} onOpenChange={setShowExitModal}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-black/80 z-50" />
          <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-black border border-white/20 p-6 z-50 w-full max-w-md">
            <Dialog.Title className="flex items-center gap-2 text-lg font-mono font-bold text-white mb-2">
              <AlertTriangle className="w-5 h-5 text-amber-400" />
              Leave Setup?
            </Dialog.Title>
            <Dialog.Description className="text-sm font-mono text-white/60 mb-6 leading-relaxed">
              {isAnalyzing ? (
                <>
                  A goal analysis is currently running. Leaving now will cancel the analysis
                  and discard your draft.
                </>
              ) : blueprintDraft ? (
                <>
                  You have a generated blueprint draft. Your progress will be lost
                  unless you save it as a draft.
                </>
              ) : (
                <>
                  You have unsaved changes. Your draft will not be saved unless
                  you click &quot;Save Draft&quot;.
                </>
              )}
            </Dialog.Description>

            <div className="space-y-3">
              {/* Save Draft & Exit */}
              <Button
                variant="secondary"
                className="w-full justify-start text-sm"
                onClick={handleSaveDraftExit}
              >
                <Save className="w-4 h-4 mr-2" />
                Save Draft & Exit
                <span className="ml-auto text-[10px] text-white/40">Resume later</span>
              </Button>

              {/* Discard Draft & Exit */}
              <Button
                variant="outline"
                className="w-full justify-start text-sm text-red-400 border-red-500/30 hover:bg-red-500/10"
                onClick={handleDiscardExit}
              >
                <Trash2 className="w-4 h-4 mr-2" />
                Discard Draft & Exit
                <span className="ml-auto text-[10px] text-red-400/60">Cannot undo</span>
              </Button>

              {/* Continue Setup */}
              <Button
                className="w-full justify-center text-sm"
                onClick={() => setShowExitModal(false)}
              >
                <ArrowRight className="w-4 h-4 mr-2" />
                Continue Setup
              </Button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>

      {/* Footer */}
      <div className="mt-8 pt-4 border-t border-white/5 max-w-2xl">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-1">
            <Terminal className="w-3 h-3" />
            <span>CREATE PROJECT</span>
          </div>
          <span>AGENTVERSE v1.0</span>
        </div>
      </div>
    </div>
  );
}
