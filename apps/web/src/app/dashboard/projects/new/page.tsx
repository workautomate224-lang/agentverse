'use client';

/**
 * Create Project Wizard
 * Multi-step wizard for creating ProjectSpec
 * Reference: Interaction_design.md §5.3, project.md §6.1
 */

import { useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  ArrowLeft,
  ArrowRight,
  Loader2,
  FolderKanban,
  Target,
  Users,
  TrendingUp,
  Zap,
  Upload,
  FileText,
  Search,
  Check,
  AlertTriangle,
  BarChart3,
  Activity,
  Shield,
  Terminal,
  ChevronRight,
  Lightbulb,
  Database,
  Layers,
  PieChart,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useCreateProjectSpec } from '@/hooks/useApi';
import { toast } from '@/hooks/use-toast';

// Wizard step definitions
const STEPS = [
  { id: 'goal', label: 'Goal', number: 1 },
  { id: 'core', label: 'Core', number: 2 },
  { id: 'data', label: 'Data', number: 3 },
  { id: 'outputs', label: 'Outputs', number: 4 },
  { id: 'review', label: 'Review', number: 5 },
] as const;

type StepId = typeof STEPS[number]['id'];

// Prediction Core options
const PREDICTION_CORES = [
  {
    id: 'collective',
    name: 'Collective Dynamics',
    subtitle: 'Society Mode',
    description: 'Model how opinions, behaviors, and trends emerge and spread through populations. Best for market trends, social movements, public opinion.',
    icon: Users,
    color: 'cyan',
    recommended: ['social', 'market', 'political', 'trends'],
  },
  {
    id: 'targeted',
    name: 'Targeted Decision',
    subtitle: 'Target Mode',
    description: 'Simulate individual decision-making processes for specific personas. Best for consumer choice, voting behavior, product adoption.',
    icon: Target,
    color: 'purple',
    recommended: ['consumer', 'voting', 'adoption', 'choice'],
  },
  {
    id: 'hybrid',
    name: 'Hybrid Strategic',
    subtitle: 'Hybrid Mode',
    description: 'Combine collective dynamics with targeted decision modeling. Best for complex scenarios involving both social influence and individual choice.',
    icon: Zap,
    color: 'yellow',
    recommended: ['complex', 'strategic', 'combined'],
  },
] as const;

// Domain hints
const DOMAIN_HINTS = [
  { id: 'market', label: 'Market Research' },
  { id: 'political', label: 'Political Analysis' },
  { id: 'social', label: 'Social Trends' },
  { id: 'consumer', label: 'Consumer Behavior' },
  { id: 'finance', label: 'Financial Decisions' },
  { id: 'health', label: 'Health & Wellness' },
  { id: 'technology', label: 'Technology Adoption' },
  { id: 'custom', label: 'Custom Domain' },
];

// Persona source options
const PERSONA_SOURCES = [
  {
    id: 'template',
    name: 'Use Templates',
    description: 'Start with pre-built persona templates from the marketplace',
    icon: FileText,
    estimatedCount: '100-500',
    uncertainty: 'low',
  },
  {
    id: 'upload',
    name: 'Upload Data',
    description: 'Upload your own demographic or survey data',
    icon: Upload,
    estimatedCount: 'Varies',
    uncertainty: 'medium',
  },
  {
    id: 'generate',
    name: 'AI Generation',
    description: 'Generate synthetic personas based on your goal',
    icon: Zap,
    estimatedCount: '50-200',
    uncertainty: 'medium',
  },
  {
    id: 'search',
    name: 'Deep Search',
    description: 'Advanced persona discovery (can be enabled later)',
    icon: Search,
    estimatedCount: '200-1000',
    uncertainty: 'high',
    advanced: true,
  },
];

// Output metrics options
const OUTPUT_METRICS = [
  {
    id: 'outcome_distribution',
    name: 'Outcome Probability Distribution',
    description: 'Probability distribution across possible outcomes',
    icon: PieChart,
    default: true,
  },
  {
    id: 'trend_over_time',
    name: 'Trend Over Time',
    description: 'How outcomes evolve across simulation ticks',
    icon: TrendingUp,
    default: true,
  },
  {
    id: 'key_drivers',
    name: 'Key Drivers Analysis',
    description: 'Factors most influencing the predicted outcomes',
    icon: Activity,
    default: false,
  },
  {
    id: 'reliability_report',
    name: 'Reliability Report',
    description: 'Confidence scores, calibration, and uncertainty metrics',
    icon: Shield,
    default: true,
    required: true,
  },
];

// Form data interface
interface WizardFormData {
  // Step 1: Goal
  goal: string;
  domain: string;
  isSensitive: boolean;
  // Step 2: Core
  predictionCore: 'collective' | 'targeted' | 'hybrid';
  // Step 3: Data
  personaSource: 'template' | 'upload' | 'generate' | 'search';
  // Step 4: Outputs
  outputMetrics: string[];
  // Derived
  name: string;
}

export default function CreateProjectWizardPage() {
  const router = useRouter();
  const createProjectSpec = useCreateProjectSpec();

  const [currentStep, setCurrentStep] = useState<StepId>('goal');
  const [formData, setFormData] = useState<WizardFormData>({
    goal: '',
    domain: '',
    isSensitive: false,
    predictionCore: 'collective',
    personaSource: 'template',
    outputMetrics: ['outcome_distribution', 'trend_over_time', 'reliability_report'],
    name: '',
  });
  const [error, setError] = useState('');

  // Get current step index
  const currentStepIndex = STEPS.findIndex(s => s.id === currentStep);

  // Recommend core based on domain and goal keywords
  const recommendedCore = useMemo(() => {
    const goalLower = formData.goal.toLowerCase();
    const domainLower = formData.domain.toLowerCase();

    for (const core of PREDICTION_CORES) {
      if (core.recommended.some(keyword =>
        goalLower.includes(keyword) || domainLower.includes(keyword)
      )) {
        return core.id;
      }
    }
    return 'collective'; // Default
  }, [formData.goal, formData.domain]);

  // Navigation handlers
  const goToStep = (stepId: StepId) => {
    setCurrentStep(stepId);
    setError('');
  };

  const goNext = () => {
    const nextIndex = currentStepIndex + 1;
    if (nextIndex < STEPS.length) {
      setCurrentStep(STEPS[nextIndex].id);
      setError('');
    }
  };

  const goBack = () => {
    const prevIndex = currentStepIndex - 1;
    if (prevIndex >= 0) {
      setCurrentStep(STEPS[prevIndex].id);
      setError('');
    }
  };

  // Validation per step
  const isStepValid = (stepId: StepId): boolean => {
    switch (stepId) {
      case 'goal':
        return formData.goal.trim().length >= 10;
      case 'core':
        return !!formData.predictionCore;
      case 'data':
        return !!formData.personaSource;
      case 'outputs':
        return formData.outputMetrics.length > 0;
      case 'review':
        return true;
      default:
        return false;
    }
  };

  // Handle form submission
  const handleSubmit = async () => {
    setError('');

    // Generate name from goal if not set
    const projectName = formData.name ||
      formData.goal.slice(0, 50).trim() + (formData.goal.length > 50 ? '...' : '');

    try {
      const project = await createProjectSpec.mutateAsync({
        name: projectName,
        description: formData.goal,
        domain: formData.domain || 'custom',
        settings: {
          default_horizon: 100,
          default_tick_rate: 1,
          default_agent_count: formData.personaSource === 'search' ? 500 : 100,
          allow_public_templates: !formData.isSensitive,
        },
      });

      toast({
        title: 'Project Created',
        description: 'Your project has been created. Run a baseline simulation to get started.',
        variant: 'success',
      });

      router.push(`/dashboard/projects/${project.id}`);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'An error occurred';
      setError(errorMessage);
      toast({
        title: 'Error',
        description: 'Failed to create project. Please try again.',
        variant: 'destructive',
      });
    }
  };

  // Toggle output metric
  const toggleMetric = (metricId: string) => {
    const metric = OUTPUT_METRICS.find(m => m.id === metricId);
    if (metric?.required) return; // Can't toggle required metrics

    setFormData(prev => ({
      ...prev,
      outputMetrics: prev.outputMetrics.includes(metricId)
        ? prev.outputMetrics.filter(id => id !== metricId)
        : [...prev.outputMetrics, metricId],
    }));
  };

  return (
    <div className="min-h-screen bg-black p-6">
      {/* Header */}
      <div className="mb-8">
        <Link href="/dashboard/projects">
          <Button variant="ghost" size="sm" className="mb-4">
            <ArrowLeft className="w-3 h-3 mr-2" />
            BACK TO PROJECTS
          </Button>
        </Link>
        <div className="flex items-center gap-2 mb-1">
          <FolderKanban className="w-4 h-4 text-cyan-400" />
          <span className="text-xs font-mono text-white/40 uppercase tracking-wider">Create Project</span>
        </div>
        <h1 className="text-xl font-mono font-bold text-white">Project Wizard</h1>
        <p className="text-sm font-mono text-white/50 mt-1">
          Define your prediction goal and configure your simulation
        </p>
      </div>

      {/* Step Indicator */}
      <div className="flex items-center gap-1 mb-8 max-w-3xl">
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
                  'flex items-center gap-2 px-3 py-2 border transition-all flex-1',
                  isActive
                    ? 'bg-cyan-500/20 border-cyan-500/50 text-cyan-400'
                    : isCompleted
                    ? 'bg-green-500/10 border-green-500/30 text-green-400'
                    : 'bg-white/5 border-white/10 text-white/40',
                  isClickable && !isActive && 'hover:bg-white/10 cursor-pointer'
                )}
              >
                <span className={cn(
                  'w-5 h-5 flex items-center justify-center text-[10px] font-mono font-bold',
                  isCompleted ? 'bg-green-500 text-black' : isActive ? 'bg-cyan-500 text-black' : 'bg-white/10'
                )}>
                  {isCompleted ? <Check className="w-3 h-3" /> : step.number}
                </span>
                <span className="text-xs font-mono hidden sm:block">{step.label}</span>
              </button>
              {index < STEPS.length - 1 && (
                <ChevronRight className="w-4 h-4 text-white/20 mx-1 flex-shrink-0" />
              )}
            </div>
          );
        })}
      </div>

      {/* Error Display */}
      {error && (
        <div className="max-w-3xl mb-6 bg-red-500/10 border border-red-500/30 p-4">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-red-400" />
            <p className="text-sm font-mono text-red-400">{error}</p>
          </div>
        </div>
      )}

      {/* Step Content */}
      <div className="max-w-3xl">
        {/* Step 1: Goal */}
        {currentStep === 'goal' && (
          <div className="bg-white/5 border border-white/10 p-6">
            <div className="flex items-center gap-2 mb-6">
              <Lightbulb className="w-5 h-5 text-cyan-400" />
              <h2 className="text-lg font-mono font-bold text-white">Define Your Prediction Goal</h2>
            </div>

            <div className="space-y-6">
              {/* Goal Input */}
              <div>
                <label className="block text-xs font-mono text-white/60 uppercase mb-2">
                  What do you want to predict? <span className="text-red-400">*</span>
                </label>
                <textarea
                  value={formData.goal}
                  onChange={(e) => setFormData({ ...formData, goal: e.target.value })}
                  placeholder="e.g., How will consumer sentiment shift towards electric vehicles in urban markets over the next 6 months?"
                  rows={4}
                  className="w-full px-4 py-3 bg-black border border-white/10 text-sm font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-cyan-500/50"
                />
                <p className="text-[10px] font-mono text-white/30 mt-2">
                  Be specific about what you want to predict, the population, and the timeframe.
                </p>
              </div>

              {/* Domain Hints */}
              <div>
                <label className="block text-xs font-mono text-white/60 uppercase mb-2">
                  Domain Hint (optional)
                </label>
                <div className="flex flex-wrap gap-2">
                  {DOMAIN_HINTS.map((domain) => (
                    <button
                      key={domain.id}
                      type="button"
                      onClick={() => setFormData({ ...formData, domain: domain.id })}
                      className={cn(
                        'px-3 py-1.5 text-xs font-mono border transition-all',
                        formData.domain === domain.id
                          ? 'bg-cyan-500/20 border-cyan-500/50 text-cyan-400'
                          : 'bg-white/5 border-white/10 text-white/60 hover:border-white/20'
                      )}
                    >
                      {domain.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Sensitive Domain */}
              <div className="p-4 bg-yellow-500/5 border border-yellow-500/20">
                <label className="flex items-start gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.isSensitive}
                    onChange={(e) => setFormData({ ...formData, isSensitive: e.target.checked })}
                    className="mt-1 w-4 h-4 bg-white/5 border border-white/20"
                  />
                  <div>
                    <span className="text-xs font-mono text-yellow-400 font-bold block">
                      Sensitive Domain
                    </span>
                    <span className="text-[10px] font-mono text-white/50">
                      Enable additional privacy controls and policy checks for sensitive topics
                      (health, politics, finance, etc.)
                    </span>
                  </div>
                </label>
              </div>
            </div>
          </div>
        )}

        {/* Step 2: Core Recommendation */}
        {currentStep === 'core' && (
          <div className="bg-white/5 border border-white/10 p-6">
            <div className="flex items-center gap-2 mb-2">
              <Layers className="w-5 h-5 text-purple-400" />
              <h2 className="text-lg font-mono font-bold text-white">Select Prediction Core</h2>
            </div>
            <p className="text-sm font-mono text-white/50 mb-6">
              Based on your goal, we recommend <span className="text-cyan-400">{
                PREDICTION_CORES.find(c => c.id === recommendedCore)?.name
              }</span>
            </p>

            <div className="space-y-3">
              {PREDICTION_CORES.map((core) => {
                const isSelected = formData.predictionCore === core.id;
                const isRecommended = core.id === recommendedCore;
                const Icon = core.icon;
                const colorClasses = {
                  cyan: { bg: 'bg-cyan-500/10', border: 'border-cyan-500/50', text: 'text-cyan-400' },
                  purple: { bg: 'bg-purple-500/10', border: 'border-purple-500/50', text: 'text-purple-400' },
                  yellow: { bg: 'bg-yellow-500/10', border: 'border-yellow-500/50', text: 'text-yellow-400' },
                }[core.color];

                return (
                  <button
                    key={core.id}
                    type="button"
                    onClick={() => setFormData({ ...formData, predictionCore: core.id })}
                    className={cn(
                      'w-full flex items-start gap-4 p-4 border transition-all text-left',
                      isSelected
                        ? `${colorClasses.bg} ${colorClasses.border}`
                        : 'bg-black border-white/10 hover:border-white/20'
                    )}
                  >
                    <div className={cn(
                      'w-12 h-12 flex items-center justify-center flex-shrink-0',
                      isSelected ? colorClasses.bg : 'bg-white/5'
                    )}>
                      <Icon className={cn('w-6 h-6', isSelected ? colorClasses.text : 'text-white/40')} />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h3 className={cn('font-mono font-bold', isSelected ? colorClasses.text : 'text-white')}>
                          {core.name}
                        </h3>
                        <span className="text-[10px] font-mono text-white/40">
                          ({core.subtitle})
                        </span>
                        {isRecommended && (
                          <span className="px-2 py-0.5 bg-green-500/20 text-green-400 text-[10px] font-mono">
                            RECOMMENDED
                          </span>
                        )}
                      </div>
                      <p className="text-xs font-mono text-white/50 mt-1">
                        {core.description}
                      </p>
                    </div>
                    <div className={cn(
                      'w-5 h-5 border flex items-center justify-center flex-shrink-0',
                      isSelected ? `${colorClasses.border} ${colorClasses.bg}` : 'border-white/20'
                    )}>
                      {isSelected && <Check className={cn('w-3 h-3', colorClasses.text)} />}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Step 3: Data & Personas */}
        {currentStep === 'data' && (
          <div className="bg-white/5 border border-white/10 p-6">
            <div className="flex items-center gap-2 mb-2">
              <Database className="w-5 h-5 text-blue-400" />
              <h2 className="text-lg font-mono font-bold text-white">Data & Personas Source</h2>
            </div>
            <p className="text-sm font-mono text-white/50 mb-6">
              Choose how to populate your simulation with personas
            </p>

            <div className="space-y-3">
              {PERSONA_SOURCES.map((source) => {
                const isSelected = formData.personaSource === source.id;
                const Icon = source.icon;

                return (
                  <button
                    key={source.id}
                    type="button"
                    onClick={() => setFormData({ ...formData, personaSource: source.id as WizardFormData['personaSource'] })}
                    className={cn(
                      'w-full flex items-start gap-4 p-4 border transition-all text-left',
                      isSelected
                        ? 'bg-blue-500/10 border-blue-500/50'
                        : 'bg-black border-white/10 hover:border-white/20',
                      source.advanced && 'opacity-70'
                    )}
                  >
                    <div className={cn(
                      'w-10 h-10 flex items-center justify-center flex-shrink-0',
                      isSelected ? 'bg-blue-500/20' : 'bg-white/5'
                    )}>
                      <Icon className={cn('w-5 h-5', isSelected ? 'text-blue-400' : 'text-white/40')} />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h3 className={cn('font-mono font-bold text-sm', isSelected ? 'text-blue-400' : 'text-white')}>
                          {source.name}
                        </h3>
                        {source.advanced && (
                          <span className="px-2 py-0.5 bg-white/10 text-white/40 text-[10px] font-mono">
                            ADVANCED
                          </span>
                        )}
                      </div>
                      <p className="text-xs font-mono text-white/50 mt-1">
                        {source.description}
                      </p>
                      <div className="flex items-center gap-4 mt-2">
                        <span className="text-[10px] font-mono text-white/40">
                          Est. personas: <span className="text-white/60">{source.estimatedCount}</span>
                        </span>
                        <span className={cn(
                          'text-[10px] font-mono px-1.5 py-0.5',
                          source.uncertainty === 'low' ? 'bg-green-500/20 text-green-400' :
                          source.uncertainty === 'medium' ? 'bg-yellow-500/20 text-yellow-400' :
                          'bg-red-500/20 text-red-400'
                        )}>
                          {source.uncertainty.toUpperCase()} UNCERTAINTY
                        </span>
                      </div>
                    </div>
                    <div className={cn(
                      'w-5 h-5 border flex items-center justify-center flex-shrink-0',
                      isSelected ? 'border-blue-500/50 bg-blue-500/20' : 'border-white/20'
                    )}>
                      {isSelected && <Check className="w-3 h-3 text-blue-400" />}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Step 4: Outputs */}
        {currentStep === 'outputs' && (
          <div className="bg-white/5 border border-white/10 p-6">
            <div className="flex items-center gap-2 mb-2">
              <BarChart3 className="w-5 h-5 text-green-400" />
              <h2 className="text-lg font-mono font-bold text-white">Output Metrics</h2>
            </div>
            <p className="text-sm font-mono text-white/50 mb-6">
              Select which metrics to include in your simulation results
            </p>

            <div className="space-y-3">
              {OUTPUT_METRICS.map((metric) => {
                const isSelected = formData.outputMetrics.includes(metric.id);
                const Icon = metric.icon;

                return (
                  <button
                    key={metric.id}
                    type="button"
                    onClick={() => toggleMetric(metric.id)}
                    disabled={metric.required}
                    className={cn(
                      'w-full flex items-center gap-4 p-4 border transition-all text-left',
                      isSelected
                        ? 'bg-green-500/10 border-green-500/50'
                        : 'bg-black border-white/10 hover:border-white/20',
                      metric.required && 'cursor-not-allowed'
                    )}
                  >
                    <div className={cn(
                      'w-10 h-10 flex items-center justify-center flex-shrink-0',
                      isSelected ? 'bg-green-500/20' : 'bg-white/5'
                    )}>
                      <Icon className={cn('w-5 h-5', isSelected ? 'text-green-400' : 'text-white/40')} />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h3 className={cn('font-mono font-bold text-sm', isSelected ? 'text-green-400' : 'text-white')}>
                          {metric.name}
                        </h3>
                        {metric.required && (
                          <span className="px-2 py-0.5 bg-white/10 text-white/40 text-[10px] font-mono">
                            REQUIRED
                          </span>
                        )}
                      </div>
                      <p className="text-xs font-mono text-white/50 mt-1">
                        {metric.description}
                      </p>
                    </div>
                    <div className={cn(
                      'w-5 h-5 border flex items-center justify-center flex-shrink-0',
                      isSelected ? 'border-green-500/50 bg-green-500/20' : 'border-white/20'
                    )}>
                      {isSelected && <Check className="w-3 h-3 text-green-400" />}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Step 5: Review & Create */}
        {currentStep === 'review' && (
          <div className="space-y-4">
            <div className="bg-white/5 border border-white/10 p-6">
              <div className="flex items-center gap-2 mb-6">
                <FileText className="w-5 h-5 text-white/60" />
                <h2 className="text-lg font-mono font-bold text-white">Review Project Configuration</h2>
              </div>

              {/* Summary */}
              <div className="space-y-4">
                {/* Goal */}
                <div className="p-4 bg-black border border-white/10">
                  <div className="text-[10px] font-mono text-white/40 uppercase mb-2">Prediction Goal</div>
                  <p className="text-sm font-mono text-white">{formData.goal}</p>
                  {formData.domain && (
                    <span className="inline-block mt-2 px-2 py-0.5 bg-white/10 text-xs font-mono text-white/60">
                      {DOMAIN_HINTS.find(d => d.id === formData.domain)?.label}
                    </span>
                  )}
                </div>

                {/* Core */}
                <div className="p-4 bg-black border border-white/10">
                  <div className="text-[10px] font-mono text-white/40 uppercase mb-2">Prediction Core</div>
                  <div className="flex items-center gap-3">
                    {(() => {
                      const core = PREDICTION_CORES.find(c => c.id === formData.predictionCore);
                      const Icon = core?.icon || Target;
                      return (
                        <>
                          <Icon className="w-5 h-5 text-cyan-400" />
                          <span className="text-sm font-mono text-white">{core?.name}</span>
                          <span className="text-xs font-mono text-white/40">({core?.subtitle})</span>
                        </>
                      );
                    })()}
                  </div>
                </div>

                {/* Data Source */}
                <div className="p-4 bg-black border border-white/10">
                  <div className="text-[10px] font-mono text-white/40 uppercase mb-2">Persona Source</div>
                  <div className="flex items-center gap-3">
                    {(() => {
                      const source = PERSONA_SOURCES.find(s => s.id === formData.personaSource);
                      const Icon = source?.icon || Users;
                      return (
                        <>
                          <Icon className="w-5 h-5 text-blue-400" />
                          <span className="text-sm font-mono text-white">{source?.name}</span>
                          <span className="text-xs font-mono text-white/40">
                            (~{source?.estimatedCount} personas)
                          </span>
                        </>
                      );
                    })()}
                  </div>
                </div>

                {/* Output Metrics */}
                <div className="p-4 bg-black border border-white/10">
                  <div className="text-[10px] font-mono text-white/40 uppercase mb-2">Output Metrics</div>
                  <div className="flex flex-wrap gap-2">
                    {formData.outputMetrics.map(metricId => {
                      const metric = OUTPUT_METRICS.find(m => m.id === metricId);
                      return (
                        <span key={metricId} className="px-2 py-1 bg-green-500/10 border border-green-500/30 text-xs font-mono text-green-400">
                          {metric?.name}
                        </span>
                      );
                    })}
                  </div>
                </div>
              </div>

              {/* Sensitive Domain Warning */}
              {formData.isSensitive && (
                <div className="mt-4 p-4 bg-yellow-500/10 border border-yellow-500/30">
                  <div className="flex items-start gap-3">
                    <AlertTriangle className="w-5 h-5 text-yellow-400 flex-shrink-0" />
                    <div>
                      <p className="text-xs font-mono text-yellow-400 font-bold">Sensitive Domain Enabled</p>
                      <p className="text-[10px] font-mono text-white/50 mt-1">
                        Additional privacy controls and audit logging will be applied to this project.
                        Results may be restricted based on your organization&apos;s policies.
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Project Name (editable) */}
            <div className="bg-white/5 border border-white/10 p-6">
              <div className="text-[10px] font-mono text-white/40 uppercase mb-2">Project Name</div>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder={formData.goal.slice(0, 50) || 'Auto-generated from goal'}
                className="w-full px-3 py-2 bg-black border border-white/10 text-sm font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-white/20"
              />
              <p className="text-[10px] font-mono text-white/30 mt-2">
                Leave blank to auto-generate from your prediction goal
              </p>
            </div>
          </div>
        )}

        {/* Navigation Buttons */}
        <div className="flex justify-between mt-6">
          <div>
            {currentStepIndex > 0 && (
              <Button variant="secondary" onClick={goBack}>
                <ArrowLeft className="w-3 h-3 mr-2" />
                BACK
              </Button>
            )}
          </div>
          <div className="flex gap-3">
            <Link href="/dashboard/projects">
              <Button variant="outline">
                CANCEL
              </Button>
            </Link>
            {currentStep === 'review' ? (
              <Button
                onClick={handleSubmit}
                disabled={createProjectSpec.isPending}
              >
                {createProjectSpec.isPending ? (
                  <>
                    <Loader2 className="w-3 h-3 mr-2 animate-spin" />
                    CREATING...
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
              >
                NEXT
                <ArrowRight className="w-3 h-3 ml-2" />
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-8 pt-4 border-t border-white/5 max-w-3xl">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-1">
            <Terminal className="w-3 h-3" />
            <span>PROJECT WIZARD</span>
          </div>
          <span>Interaction_design.md §5.3</span>
        </div>
      </div>
    </div>
  );
}
