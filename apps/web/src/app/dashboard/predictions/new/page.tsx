'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import {
  ArrowLeft,
  ArrowRight,
  Check,
  TrendingUp,
  FileText,
  Palette,
  Users,
  Brain,
  Settings,
  Play,
  Plus,
  X,
  Loader2,
  Terminal,
} from 'lucide-react';
import { useCreatePrediction } from '@/hooks/useApi';
import { PredictionCreate, ScenarioType, NetworkType, PredictionCategory, BehavioralParams } from '@/lib/api';
import { cn } from '@/lib/utils';

const STEPS = [
  { id: 1, name: 'Basic Info', icon: FileText },
  { id: 2, name: 'Categories', icon: Palette },
  { id: 3, name: 'Agent Config', icon: Users },
  { id: 4, name: 'Behavioral', icon: Brain },
  { id: 5, name: 'Settings', icon: Settings },
  { id: 6, name: 'Review', icon: Play },
];

const SCENARIO_TYPES: { value: ScenarioType; label: string; description: string }[] = [
  { value: 'election', label: 'Election', description: 'Political voting predictions' },
  { value: 'consumer', label: 'Consumer', description: 'Product purchase decisions' },
  { value: 'market', label: 'Market', description: 'Financial market behavior' },
  { value: 'social', label: 'Social', description: 'Social trend predictions' },
];

const NETWORK_TYPES: { value: NetworkType; label: string; description: string }[] = [
  { value: 'small_world', label: 'Small World', description: 'Clustered with short paths (recommended)' },
  { value: 'scale_free', label: 'Scale Free', description: 'Hub-based network structure' },
  { value: 'random', label: 'Random', description: 'Uniformly random connections' },
  { value: 'complete', label: 'Complete', description: 'All agents connected' },
];

const DEFAULT_COLORS = [
  '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
  '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9',
];

interface FormData {
  name: string;
  description: string;
  scenario_type: ScenarioType;
  categories: PredictionCategory[];
  agentCount: number;
  demographics: {
    age_distribution: Record<string, number>;
  };
  behavioralParams: BehavioralParams;
  numSteps: number;
  monteCarloRuns: number;
  confidenceLevel: number;
  networkType: NetworkType;
  enableMarl: boolean;
  useCalibration: boolean;
}

const initialFormData: FormData = {
  name: '',
  description: '',
  scenario_type: 'election',
  categories: [
    { name: 'Option A', color: '#FF6B6B' },
    { name: 'Option B', color: '#4ECDC4' },
  ],
  agentCount: 1000,
  demographics: {
    age_distribution: {
      '18_24': 0.15,
      '25_34': 0.25,
      '35_44': 0.25,
      '45_54': 0.20,
      '55_plus': 0.15,
    },
  },
  behavioralParams: {
    loss_aversion: 2.25,
    status_quo_bias: 0.3,
    bandwagon_effect: 0.2,
    social_influence_weight: 0.15,
    confirmation_bias: 0.25,
  },
  numSteps: 30,
  monteCarloRuns: 50,
  confidenceLevel: 0.95,
  networkType: 'small_world',
  enableMarl: false,
  useCalibration: true,
};

export default function NewPredictionPage() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState(1);
  const [formData, setFormData] = useState<FormData>(initialFormData);
  const createPrediction = useCreatePrediction();

  const handleNext = () => {
    if (currentStep < 6) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handlePrev = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleSubmit = async () => {
    const payload: PredictionCreate = {
      name: formData.name,
      description: formData.description || undefined,
      scenario_type: formData.scenario_type,
      config: {
        categories: formData.categories,
        agent_config: {
          count: formData.agentCount,
          demographics: formData.demographics,
          behavioral_params: formData.behavioralParams,
        },
        num_steps: formData.numSteps,
        monte_carlo_runs: formData.monteCarloRuns,
        confidence_level: formData.confidenceLevel,
        social_network_type: formData.networkType,
        enable_marl: formData.enableMarl,
        use_calibration: formData.useCalibration,
      },
    };

    try {
      const result = await createPrediction.mutateAsync(payload);
      router.push(`/dashboard/predictions/${result.id}`);
    } catch {
      // Error handled by mutation
    }
  };

  const isStepValid = (step: number): boolean => {
    switch (step) {
      case 1:
        return formData.name.trim().length >= 3;
      case 2:
        return formData.categories.length >= 2 && formData.categories.every(c => c.name.trim().length > 0);
      case 3:
        return formData.agentCount >= 10 && formData.agentCount <= 100000;
      case 4:
        return true;
      case 5:
        return formData.numSteps >= 1 && formData.monteCarloRuns >= 1;
      case 6:
        return true;
      default:
        return false;
    }
  };

  return (
    <div className="min-h-screen bg-black p-6">
      {/* Header */}
      <div className="flex items-center gap-4 mb-8">
        <button
          onClick={() => router.push('/dashboard/predictions')}
          className="p-2 hover:bg-white/10 transition-colors"
        >
          <ArrowLeft className="w-4 h-4 text-white/60" />
        </button>
        <div>
          <div className="flex items-center gap-2 mb-1">
            <TrendingUp className="w-4 h-4 text-white/60" />
            <span className="text-xs font-mono text-white/40 uppercase tracking-wider">New Prediction</span>
          </div>
          <h1 className="text-xl font-mono font-bold text-white">Create Prediction</h1>
        </div>
      </div>

      {/* Step Indicator */}
      <div className="flex items-center justify-between mb-8 max-w-3xl">
        {STEPS.map((step, index) => {
          const isActive = currentStep === step.id;
          const isCompleted = currentStep > step.id;
          const StepIcon = step.icon;

          return (
            <div key={step.id} className="flex items-center">
              <div className="flex flex-col items-center">
                <div
                  className={cn(
                    'w-10 h-10 flex items-center justify-center border transition-colors',
                    isActive
                      ? 'bg-white text-black border-white'
                      : isCompleted
                      ? 'bg-green-500/20 text-green-400 border-green-500/50'
                      : 'bg-white/5 text-white/40 border-white/10'
                  )}
                >
                  {isCompleted ? (
                    <Check className="w-4 h-4" />
                  ) : (
                    <StepIcon className="w-4 h-4" />
                  )}
                </div>
                <span
                  className={cn(
                    'text-[10px] font-mono mt-2 uppercase tracking-wider',
                    isActive ? 'text-white' : 'text-white/40'
                  )}
                >
                  {step.name}
                </span>
              </div>
              {index < STEPS.length - 1 && (
                <div
                  className={cn(
                    'w-12 h-px mx-2 mt-[-20px]',
                    isCompleted ? 'bg-green-500/50' : 'bg-white/10'
                  )}
                />
              )}
            </div>
          );
        })}
      </div>

      {/* Form Content */}
      <div className="max-w-2xl">
        <div className="bg-white/5 border border-white/10 p-6 mb-6">
          {currentStep === 1 && (
            <Step1BasicInfo formData={formData} setFormData={setFormData} />
          )}
          {currentStep === 2 && (
            <Step2Categories formData={formData} setFormData={setFormData} />
          )}
          {currentStep === 3 && (
            <Step3AgentConfig formData={formData} setFormData={setFormData} />
          )}
          {currentStep === 4 && (
            <Step4Behavioral formData={formData} setFormData={setFormData} />
          )}
          {currentStep === 5 && (
            <Step5Settings formData={formData} setFormData={setFormData} />
          )}
          {currentStep === 6 && (
            <Step6Review formData={formData} />
          )}
        </div>

        {/* Navigation */}
        <div className="flex items-center justify-between">
          <Button
            variant="outline"
            onClick={handlePrev}
            disabled={currentStep === 1}
            className="font-mono text-xs"
          >
            <ArrowLeft className="w-3 h-3 mr-2" />
            PREVIOUS
          </Button>

          {currentStep < 6 ? (
            <Button
              onClick={handleNext}
              disabled={!isStepValid(currentStep)}
              className="font-mono text-xs"
            >
              NEXT
              <ArrowRight className="w-3 h-3 ml-2" />
            </Button>
          ) : (
            <Button
              onClick={handleSubmit}
              disabled={createPrediction.isPending}
              className="font-mono text-xs bg-cyan-600 hover:bg-cyan-500"
            >
              {createPrediction.isPending ? (
                <>
                  <Loader2 className="w-3 h-3 mr-2 animate-spin" />
                  CREATING...
                </>
              ) : (
                <>
                  <Play className="w-3 h-3 mr-2" />
                  START PREDICTION
                </>
              )}
            </Button>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="mt-8 pt-4 border-t border-white/5">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-1">
            <Terminal className="w-3 h-3" />
            <span>PREDICTION WIZARD</span>
          </div>
          <span>Step {currentStep} of 6</span>
        </div>
      </div>
    </div>
  );
}

// Step 1: Basic Info
function Step1BasicInfo({
  formData,
  setFormData,
}: {
  formData: FormData;
  setFormData: (data: FormData) => void;
}) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-mono font-bold text-white mb-2">Basic Information</h2>
        <p className="text-sm font-mono text-white/50">Enter the name and type of your prediction</p>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-[10px] font-mono text-white/40 uppercase tracking-wider mb-2">
            Prediction Name *
          </label>
          <input
            type="text"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            placeholder="e.g., 2024 Election Prediction"
            className="w-full px-3 py-2 bg-white/5 border border-white/10 text-sm font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-white/30"
          />
        </div>

        <div>
          <label className="block text-[10px] font-mono text-white/40 uppercase tracking-wider mb-2">
            Description
          </label>
          <textarea
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            placeholder="Optional description..."
            rows={3}
            className="w-full px-3 py-2 bg-white/5 border border-white/10 text-sm font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-white/30 resize-none"
          />
        </div>

        <div>
          <label className="block text-[10px] font-mono text-white/40 uppercase tracking-wider mb-2">
            Scenario Type *
          </label>
          <div className="grid grid-cols-2 gap-3">
            {SCENARIO_TYPES.map((type) => (
              <button
                key={type.value}
                onClick={() => setFormData({ ...formData, scenario_type: type.value })}
                className={cn(
                  'p-4 border text-left transition-colors',
                  formData.scenario_type === type.value
                    ? 'bg-white/10 border-white/30'
                    : 'bg-white/5 border-white/10 hover:border-white/20'
                )}
              >
                <div className="text-sm font-mono font-bold text-white mb-1">{type.label}</div>
                <div className="text-[10px] font-mono text-white/40">{type.description}</div>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// Step 2: Categories
function Step2Categories({
  formData,
  setFormData,
}: {
  formData: FormData;
  setFormData: (data: FormData) => void;
}) {
  const addCategory = () => {
    const nextColorIndex = formData.categories.length % DEFAULT_COLORS.length;
    setFormData({
      ...formData,
      categories: [
        ...formData.categories,
        { name: '', color: DEFAULT_COLORS[nextColorIndex] },
      ],
    });
  };

  const removeCategory = (index: number) => {
    if (formData.categories.length <= 2) return;
    setFormData({
      ...formData,
      categories: formData.categories.filter((_, i) => i !== index),
    });
  };

  const updateCategory = (index: number, updates: Partial<PredictionCategory>) => {
    const newCategories = [...formData.categories];
    newCategories[index] = { ...newCategories[index], ...updates };
    setFormData({ ...formData, categories: newCategories });
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-mono font-bold text-white mb-2">Prediction Categories</h2>
        <p className="text-sm font-mono text-white/50">
          Define the outcome categories (min 2)
        </p>
      </div>

      <div className="space-y-3">
        {formData.categories.map((category, index) => (
          <div key={index} className="flex items-center gap-3">
            <input
              type="color"
              value={category.color || '#FF6B6B'}
              onChange={(e) => updateCategory(index, { color: e.target.value })}
              className="w-10 h-10 bg-transparent border-0 cursor-pointer"
            />
            <input
              type="text"
              value={category.name}
              onChange={(e) => updateCategory(index, { name: e.target.value })}
              placeholder={`Category ${index + 1} name`}
              className="flex-1 px-3 py-2 bg-white/5 border border-white/10 text-sm font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-white/30"
            />
            {formData.categories.length > 2 && (
              <button
                onClick={() => removeCategory(index)}
                className="p-2 hover:bg-red-500/20 text-red-400 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        ))}
      </div>

      <Button
        variant="outline"
        onClick={addCategory}
        className="font-mono text-xs"
      >
        <Plus className="w-3 h-3 mr-2" />
        ADD CATEGORY
      </Button>
    </div>
  );
}

// Step 3: Agent Config
function Step3AgentConfig({
  formData,
  setFormData,
}: {
  formData: FormData;
  setFormData: (data: FormData) => void;
}) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-mono font-bold text-white mb-2">Agent Configuration</h2>
        <p className="text-sm font-mono text-white/50">Configure the simulated agent population</p>
      </div>

      <div className="space-y-6">
        <div>
          <label className="block text-[10px] font-mono text-white/40 uppercase tracking-wider mb-2">
            Agent Count: {formData.agentCount.toLocaleString()}
          </label>
          <input
            type="range"
            min="10"
            max="100000"
            step="10"
            value={formData.agentCount}
            onChange={(e) => setFormData({ ...formData, agentCount: parseInt(e.target.value) })}
            className="w-full accent-cyan-500"
          />
          <div className="flex justify-between text-[10px] font-mono text-white/30 mt-1">
            <span>10</span>
            <span>1K</span>
            <span>10K</span>
            <span>50K</span>
            <span>100K</span>
          </div>
        </div>

        <div>
          <label className="block text-[10px] font-mono text-white/40 uppercase tracking-wider mb-3">
            Age Distribution
          </label>
          <div className="space-y-3">
            {Object.entries(formData.demographics.age_distribution).map(([key, value]) => (
              <div key={key} className="flex items-center gap-3">
                <span className="text-xs font-mono text-white/60 w-20">
                  {key.replace('_', '-').replace('plus', '+')}
                </span>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.01"
                  value={value}
                  onChange={(e) => {
                    const newDist = { ...formData.demographics.age_distribution };
                    newDist[key] = parseFloat(e.target.value);
                    setFormData({
                      ...formData,
                      demographics: { ...formData.demographics, age_distribution: newDist },
                    });
                  }}
                  className="flex-1 accent-cyan-500"
                />
                <span className="text-xs font-mono text-white/40 w-12 text-right">
                  {Math.round(value * 100)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// Step 4: Behavioral Params
function Step4Behavioral({
  formData,
  setFormData,
}: {
  formData: FormData;
  setFormData: (data: FormData) => void;
}) {
  const params = [
    { key: 'loss_aversion', label: 'Loss Aversion (λ)', min: 1, max: 4, step: 0.05, description: 'Kahneman-Tversky: losses loom larger than gains' },
    { key: 'status_quo_bias', label: 'Status Quo Bias', min: 0, max: 1, step: 0.05, description: 'Preference for current state' },
    { key: 'bandwagon_effect', label: 'Bandwagon Effect', min: 0, max: 1, step: 0.05, description: 'Following popular choices' },
    { key: 'social_influence_weight', label: 'Social Influence', min: 0, max: 1, step: 0.05, description: 'Weight of peer opinions' },
    { key: 'confirmation_bias', label: 'Confirmation Bias', min: 0, max: 1, step: 0.05, description: 'Preference for confirming beliefs' },
  ] as const;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-mono font-bold text-white mb-2">Behavioral Economics</h2>
        <p className="text-sm font-mono text-white/50">Tune cognitive biases and behavioral parameters</p>
      </div>

      <div className="space-y-4">
        {params.map((param) => (
          <div key={param.key} className="p-3 bg-white/[0.02] border border-white/5">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-mono text-white">{param.label}</span>
              <span className="text-xs font-mono text-cyan-400">
                {(formData.behavioralParams[param.key as keyof BehavioralParams] ?? 0).toFixed(2)}
              </span>
            </div>
            <p className="text-[10px] font-mono text-white/30 mb-2">{param.description}</p>
            <input
              type="range"
              min={param.min}
              max={param.max}
              step={param.step}
              value={formData.behavioralParams[param.key as keyof BehavioralParams] ?? 0}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  behavioralParams: {
                    ...formData.behavioralParams,
                    [param.key]: parseFloat(e.target.value),
                  },
                })
              }
              className="w-full accent-cyan-500"
            />
          </div>
        ))}
      </div>
    </div>
  );
}

// Step 5: Simulation Settings
function Step5Settings({
  formData,
  setFormData,
}: {
  formData: FormData;
  setFormData: (data: FormData) => void;
}) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-mono font-bold text-white mb-2">Simulation Settings</h2>
        <p className="text-sm font-mono text-white/50">Configure simulation parameters</p>
      </div>

      <div className="space-y-6">
        <div>
          <label className="block text-[10px] font-mono text-white/40 uppercase tracking-wider mb-2">
            Simulation Steps: {formData.numSteps}
          </label>
          <input
            type="range"
            min="1"
            max="100"
            value={formData.numSteps}
            onChange={(e) => setFormData({ ...formData, numSteps: parseInt(e.target.value) })}
            className="w-full accent-cyan-500"
          />
        </div>

        <div>
          <label className="block text-[10px] font-mono text-white/40 uppercase tracking-wider mb-2">
            Monte Carlo Runs: {formData.monteCarloRuns}
          </label>
          <input
            type="range"
            min="1"
            max="200"
            value={formData.monteCarloRuns}
            onChange={(e) => setFormData({ ...formData, monteCarloRuns: parseInt(e.target.value) })}
            className="w-full accent-cyan-500"
          />
          <p className="text-[10px] font-mono text-white/30 mt-1">
            More runs = better confidence intervals but longer runtime
          </p>
        </div>

        <div>
          <label className="block text-[10px] font-mono text-white/40 uppercase tracking-wider mb-2">
            Social Network Type
          </label>
          <div className="grid grid-cols-2 gap-2">
            {NETWORK_TYPES.map((type) => (
              <button
                key={type.value}
                onClick={() => setFormData({ ...formData, networkType: type.value })}
                className={cn(
                  'p-3 border text-left transition-colors',
                  formData.networkType === type.value
                    ? 'bg-white/10 border-white/30'
                    : 'bg-white/5 border-white/10 hover:border-white/20'
                )}
              >
                <div className="text-xs font-mono font-bold text-white">{type.label}</div>
                <div className="text-[10px] font-mono text-white/40 mt-1">{type.description}</div>
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-6">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={formData.useCalibration}
              onChange={(e) => setFormData({ ...formData, useCalibration: e.target.checked })}
              className="w-4 h-4 accent-cyan-500"
            />
            <span className="text-xs font-mono text-white">Enable Calibration (&gt;80% accuracy)</span>
          </label>

          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={formData.enableMarl}
              onChange={(e) => setFormData({ ...formData, enableMarl: e.target.checked })}
              className="w-4 h-4 accent-cyan-500"
            />
            <span className="text-xs font-mono text-white">Enable MARL Training</span>
          </label>
        </div>
      </div>
    </div>
  );
}

// Step 6: Review
function Step6Review({ formData }: { formData: FormData }) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-mono font-bold text-white mb-2">Review & Start</h2>
        <p className="text-sm font-mono text-white/50">Confirm your prediction configuration</p>
      </div>

      <div className="space-y-4">
        <div className="p-4 bg-white/[0.02] border border-white/5">
          <div className="text-[10px] font-mono text-white/40 uppercase tracking-wider mb-2">Basic Info</div>
          <div className="text-sm font-mono text-white mb-1">{formData.name}</div>
          <div className="text-xs font-mono text-white/50">{formData.scenario_type.toUpperCase()} prediction</div>
        </div>

        <div className="p-4 bg-white/[0.02] border border-white/5">
          <div className="text-[10px] font-mono text-white/40 uppercase tracking-wider mb-2">Categories</div>
          <div className="flex flex-wrap gap-2">
            {formData.categories.map((cat, i) => (
              <span
                key={i}
                className="px-2 py-1 text-xs font-mono"
                style={{ backgroundColor: cat.color + '20', color: cat.color }}
              >
                {cat.name}
              </span>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="p-4 bg-white/[0.02] border border-white/5">
            <div className="text-[10px] font-mono text-white/40 uppercase tracking-wider mb-2">Agents</div>
            <div className="text-lg font-mono font-bold text-white">{formData.agentCount.toLocaleString()}</div>
          </div>
          <div className="p-4 bg-white/[0.02] border border-white/5">
            <div className="text-[10px] font-mono text-white/40 uppercase tracking-wider mb-2">Monte Carlo Runs</div>
            <div className="text-lg font-mono font-bold text-white">{formData.monteCarloRuns}</div>
          </div>
          <div className="p-4 bg-white/[0.02] border border-white/5">
            <div className="text-[10px] font-mono text-white/40 uppercase tracking-wider mb-2">Simulation Steps</div>
            <div className="text-lg font-mono font-bold text-white">{formData.numSteps}</div>
          </div>
          <div className="p-4 bg-white/[0.02] border border-white/5">
            <div className="text-[10px] font-mono text-white/40 uppercase tracking-wider mb-2">Network Type</div>
            <div className="text-lg font-mono font-bold text-white capitalize">{formData.networkType.replace('_', ' ')}</div>
          </div>
        </div>

        <div className="p-4 bg-white/[0.02] border border-white/5">
          <div className="text-[10px] font-mono text-white/40 uppercase tracking-wider mb-2">Key Behavioral Params</div>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <div className="text-[10px] font-mono text-white/30">Loss Aversion</div>
              <div className="text-sm font-mono text-cyan-400">{formData.behavioralParams.loss_aversion?.toFixed(2)}</div>
            </div>
            <div>
              <div className="text-[10px] font-mono text-white/30">Status Quo</div>
              <div className="text-sm font-mono text-cyan-400">{formData.behavioralParams.status_quo_bias?.toFixed(2)}</div>
            </div>
            <div>
              <div className="text-[10px] font-mono text-white/30">Bandwagon</div>
              <div className="text-sm font-mono text-cyan-400">{formData.behavioralParams.bandwagon_effect?.toFixed(2)}</div>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {formData.useCalibration && (
            <span className="px-2 py-1 bg-cyan-500/20 text-cyan-400 text-xs font-mono">CALIBRATION ON</span>
          )}
          {formData.enableMarl && (
            <span className="px-2 py-1 bg-purple-500/20 text-purple-400 text-xs font-mono">MARL ENABLED</span>
          )}
        </div>
      </div>
    </div>
  );
}
