'use client';

/**
 * Create Project Wizard - 3-Step Flow
 * Step 1: Goal (textarea + example chips)
 * Step 2: Pick a Core (Collective/Target/Hybrid)
 * Step 3: Project Setup (name, tags, visibility)
 */

import { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
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
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Wizard step definitions - simplified to 3 steps
const STEPS = [
  { id: 'goal', label: 'Goal', number: 1 },
  { id: 'core', label: 'Pick Core', number: 2 },
  { id: 'setup', label: 'Setup', number: 3 },
] as const;

type StepId = typeof STEPS[number]['id'];

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

export default function CreateProjectWizardPage() {
  const router = useRouter();

  const [currentStep, setCurrentStep] = useState<StepId>('goal');
  const [formData, setFormData] = useState<WizardFormData>({
    goal: '',
    coreType: 'collective',
    name: '',
    tags: [],
    isPublic: true,
  });
  const [tagInput, setTagInput] = useState('');

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

  // Validation per step
  const isStepValid = (stepId: StepId): boolean => {
    switch (stepId) {
      case 'goal':
        return formData.goal.trim().length >= 10;
      case 'core':
        return !!formData.coreType;
      case 'setup':
        return formData.name.trim().length >= 3;
      default:
        return false;
    }
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

  // Handle form submission - creates project and navigates to workspace
  const handleCreate = () => {
    // Generate a mock project ID (in real app this would come from backend)
    const mockProjectId = `proj_${Date.now().toString(36)}`;

    // Navigate to the project workspace
    router.push(`/p/${mockProjectId}/overview`);
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
            </div>
          </div>
        )}

        {/* Step 2: Pick a Core */}
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

        {/* Step 3: Project Setup */}
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
            <Link href="/dashboard/projects" className="w-full sm:w-auto">
              <Button variant="outline" size="sm" className="w-full text-xs">
                CANCEL
              </Button>
            </Link>
            {currentStep === 'setup' ? (
              <Button
                onClick={handleCreate}
                disabled={!isStepValid('setup')}
                size="sm"
                className="w-full sm:w-auto text-xs"
              >
                <FolderKanban className="w-3 h-3 mr-2" />
                CREATE PROJECT
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
