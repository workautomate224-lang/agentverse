'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Loader2,
  FileText,
  MessageSquare,
  Users,
  Settings,
  Rocket,
  Plus,
  X,
  Info,
  Terminal,
  Sparkles,
  LayoutTemplate,
} from 'lucide-react';
import { useCreateScenario, useAITemplates, useGenerateAIContent } from '@/hooks/useApi';
import { toast } from '@/hooks/use-toast';

const steps = [
  { id: 1, name: 'Basics', icon: FileText },
  { id: 2, name: 'Context', icon: MessageSquare },
  { id: 3, name: 'Questions', icon: MessageSquare },
  { id: 4, name: 'Population', icon: Users },
  { id: 5, name: 'Review', icon: Rocket },
];

interface Question {
  id: string;
  type: 'multiple_choice' | 'scale' | 'open_ended';
  text: string;
  options?: string[];
  scale_min?: number;
  scale_max?: number;
}

interface Demographics {
  age_distribution: { [key: string]: number };
  gender_distribution: { [key: string]: number };
  education_distribution: { [key: string]: number };
  income_distribution: { [key: string]: number };
}

interface FormData {
  name: string;
  description: string;
  context: string;
  questions: Question[];
  population_size: number;
  demographics: Demographics;
}

const defaultDemographics: Demographics = {
  age_distribution: {
    '18-24': 15,
    '25-34': 25,
    '35-44': 25,
    '45-54': 20,
    '55+': 15,
  },
  gender_distribution: {
    male: 48,
    female: 50,
    other: 2,
  },
  education_distribution: {
    high_school: 30,
    bachelor: 40,
    master: 20,
    doctorate: 10,
  },
  income_distribution: {
    low: 25,
    middle: 50,
    high: 25,
  },
};

export default function NewScenarioPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;
  const createScenario = useCreateScenario();

  const [currentStep, setCurrentStep] = useState(1);
  const [error, setError] = useState('');

  const [formData, setFormData] = useState<FormData>({
    name: '',
    description: '',
    context: '',
    questions: [],
    population_size: 1000,
    demographics: defaultDemographics,
  });

  const updateFormData = (updates: Partial<FormData>) => {
    setFormData((prev) => ({ ...prev, ...updates }));
  };

  const canProceed = () => {
    switch (currentStep) {
      case 1:
        return formData.name.trim().length > 0;
      case 2:
        return formData.context.trim().length > 0;
      case 3:
        return formData.questions.length > 0;
      case 4:
        return formData.population_size > 0;
      case 5:
        return true;
      default:
        return false;
    }
  };

  const handleNext = () => {
    if (currentStep < 5) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleSubmit = async () => {
    setError('');

    try {
      const scenario = await createScenario.mutateAsync({
        project_id: projectId,
        name: formData.name,
        description: formData.description || undefined,
        scenario_type: 'survey',
        context: formData.context,
        questions: formData.questions,
        population_size: formData.population_size,
        demographics: formData.demographics,
      });
      router.push(`/dashboard/projects/${projectId}`);
    } catch (err: any) {
      setError(err.detail || err.message || 'An error occurred');
    }
  };

  return (
    <div className="min-h-screen bg-black p-6">
      {/* Header */}
      <div className="max-w-4xl mx-auto mb-8">
        <Link href={`/dashboard/projects/${projectId}`}>
          <Button variant="ghost" size="sm" className="text-white/60 hover:text-white hover:bg-white/5 font-mono text-xs mb-4">
            <ArrowLeft className="w-3 h-3 mr-2" />
            BACK TO PROJECT
          </Button>
        </Link>
        <div className="flex items-center gap-2 mb-1">
          <FileText className="w-4 h-4 text-white/60" />
          <span className="text-xs font-mono text-white/40 uppercase tracking-wider">Scenario Module</span>
        </div>
        <h1 className="text-xl font-mono font-bold text-white">Create New Scenario</h1>
        <p className="text-xs font-mono text-white/40 mt-1">
          Set up your simulation scenario step by step
        </p>
      </div>

      {/* Progress Steps */}
      <div className="max-w-4xl mx-auto mb-8">
        <div className="flex items-center justify-between">
          {steps.map((step, index) => (
            <div key={step.id} className="flex items-center">
              <div
                className={cn(
                  'flex items-center justify-center w-10 h-10 border transition-colors',
                  currentStep === step.id
                    ? 'border-white bg-white text-black'
                    : currentStep > step.id
                    ? 'border-white bg-white/20 text-white'
                    : 'border-white/20 bg-white/5 text-white/30'
                )}
              >
                {currentStep > step.id ? (
                  <Check className="w-4 h-4" />
                ) : (
                  <step.icon className="w-4 h-4" />
                )}
              </div>
              {index < steps.length - 1 && (
                <div
                  className={cn(
                    'w-full h-[2px] mx-2',
                    currentStep > step.id ? 'bg-white' : 'bg-white/10'
                  )}
                  style={{ width: '60px' }}
                />
              )}
            </div>
          ))}
        </div>
        <div className="flex items-center justify-between mt-2">
          {steps.map((step) => (
            <span
              key={step.id}
              className={cn(
                'text-[10px] font-mono uppercase',
                currentStep >= step.id ? 'text-white' : 'text-white/30'
              )}
            >
              {step.name}
            </span>
          ))}
        </div>
      </div>

      {/* Step Content */}
      <div className="max-w-4xl mx-auto">
        <div className="bg-white/5 border border-white/10 p-6 mb-6">
          {error && (
            <div className="mb-4 bg-red-500/10 border border-red-500/30 p-4">
              <p className="text-xs font-mono text-red-400">{error}</p>
            </div>
          )}

          {currentStep === 1 && (
            <Step1Basics formData={formData} updateFormData={updateFormData} />
          )}
          {currentStep === 2 && (
            <Step2Context formData={formData} updateFormData={updateFormData} />
          )}
          {currentStep === 3 && (
            <Step3Questions formData={formData} updateFormData={updateFormData} />
          )}
          {currentStep === 4 && (
            <Step4Population formData={formData} updateFormData={updateFormData} />
          )}
          {currentStep === 5 && <Step5Review formData={formData} />}
        </div>

        {/* Navigation */}
        <div className="flex justify-between">
          <Button
            variant="outline"
            onClick={handleBack}
            disabled={currentStep === 1}
            className="font-mono text-xs border-white/20 text-white/60 hover:bg-white/5"
          >
            <ArrowLeft className="w-3 h-3 mr-2" />
            BACK
          </Button>

          {currentStep < 5 ? (
            <Button
              onClick={handleNext}
              disabled={!canProceed()}
              
            >
              NEXT
              <ArrowRight className="w-3 h-3 ml-2" />
            </Button>
          ) : (
            <Button
              onClick={handleSubmit}
              disabled={createScenario.isPending}
              
            >
              {createScenario.isPending ? (
                <>
                  <Loader2 className="w-3 h-3 mr-2 animate-spin" />
                  CREATING...
                </>
              ) : (
                <>
                  <Rocket className="w-3 h-3 mr-2" />
                  CREATE SCENARIO
                </>
              )}
            </Button>
          )}
        </div>
      </div>

      {/* Footer Status */}
      <div className="max-w-4xl mx-auto mt-8 pt-4 border-t border-white/5">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-1">
            <Terminal className="w-3 h-3" />
            <span>SCENARIO CREATE MODULE</span>
          </div>
          <span>AGENTVERSE v1.0.0</span>
        </div>
      </div>
    </div>
  );
}

// Step 1: Basic Info
function Step1Basics({
  formData,
  updateFormData,
}: {
  formData: FormData;
  updateFormData: (updates: Partial<FormData>) => void;
}) {
  return (
    <div className="space-y-4">
      <h2 className="text-sm font-mono font-bold text-white uppercase mb-4">Basic Information</h2>

      <div>
        <label className="block text-[10px] font-mono text-white/40 uppercase mb-2">
          Scenario Name <span className="text-red-400">*</span>
        </label>
        <input
          type="text"
          value={formData.name}
          onChange={(e) => updateFormData({ name: e.target.value })}
          placeholder="e.g., Product Launch Survey"
          className="w-full px-3 py-2 bg-black border border-white/10 text-xs font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-white/30"
        />
      </div>

      <div>
        <label className="block text-[10px] font-mono text-white/40 uppercase mb-2">Description</label>
        <textarea
          value={formData.description}
          onChange={(e) => updateFormData({ description: e.target.value })}
          placeholder="What is this scenario about?"
          rows={3}
          className="w-full px-3 py-2 bg-black border border-white/10 text-xs font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-white/30 resize-none"
        />
      </div>
    </div>
  );
}

// Step 2: Context
function Step2Context({
  formData,
  updateFormData,
}: {
  formData: FormData;
  updateFormData: (updates: Partial<FormData>) => void;
}) {
  const { data: templatesData, isLoading: templatesLoading } = useAITemplates();
  const generateContent = useGenerateAIContent();
  const [selectedTemplate, setSelectedTemplate] = useState('');

  const handleTemplateSelect = (templateId: string) => {
    setSelectedTemplate(templateId);
    if (templateId && templatesData?.templates) {
      const template = templatesData.templates.find(t => t.id === templateId);
      if (template) {
        updateFormData({
          context: template.context,
          questions: template.questions.map((q, i) => ({
            id: `q_${Date.now()}_${i}`,
            type: q.type as 'multiple_choice' | 'scale' | 'open_ended',
            text: q.text,
            options: q.options,
          })),
        });
        toast({
          title: 'Template Applied',
          description: `"${template.name}" template has been applied. You can edit the content.`,
          variant: 'success',
        });
      }
    }
  };

  const handleGenerateContext = async () => {
    if (!formData.name.trim()) {
      toast({
        title: 'Name Required',
        description: 'Please enter a scenario name first to generate context.',
        variant: 'warning',
      });
      return;
    }

    try {
      const result = await generateContent.mutateAsync({
        title: formData.name,
      });

      if (result.success && result.content) {
        updateFormData({
          context: result.content.context || '',
          description: result.content.description || formData.description,
        });

        // Also update questions if available
        if (result.content.questions && result.content.questions.length > 0) {
          updateFormData({
            questions: result.content.questions.map((q, i) => ({
              id: `q_${Date.now()}_${i}`,
              type: q.type as 'multiple_choice' | 'scale' | 'open_ended',
              text: q.text,
              options: q.options,
            })),
          });
        }

        toast({
          title: 'Content Generated',
          description: 'AI has generated context based on your scenario name. You can edit it.',
          variant: 'success',
        });
      }
    } catch (error) {
      toast({
        title: 'Generation Failed',
        description: 'Failed to generate content. Please try again.',
        variant: 'destructive',
      });
    }
  };

  return (
    <div className="space-y-4">
      <h2 className="text-sm font-mono font-bold text-white uppercase mb-4">Simulation Context</h2>

      {/* AI Tools Panel */}
      <div className="bg-gradient-to-r from-purple-500/10 to-blue-500/10 border border-purple-500/30 p-4 mb-4">
        <div className="flex items-center gap-2 mb-3">
          <Sparkles className="w-4 h-4 text-purple-400" />
          <span className="text-xs font-mono font-bold text-white uppercase">AI Assistant</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Template Selection */}
          <div>
            <label className="block text-[10px] font-mono text-white/40 uppercase mb-2">
              <LayoutTemplate className="w-3 h-3 inline mr-1" />
              Use Template
            </label>
            <select
              value={selectedTemplate}
              onChange={(e) => handleTemplateSelect(e.target.value)}
              disabled={templatesLoading}
              className="w-full px-3 py-2 bg-black border border-white/20 text-xs font-mono text-white focus:outline-none focus:border-purple-500/50"
            >
              <option value="">-- Select a template --</option>
              {templatesData?.templates.map((template) => (
                <option key={template.id} value={template.id}>
                  {template.name} ({template.category})
                </option>
              ))}
            </select>
          </div>

          {/* AI Generate Button */}
          <div>
            <label className="block text-[10px] font-mono text-white/40 uppercase mb-2">
              <Sparkles className="w-3 h-3 inline mr-1" />
              Generate from Title
            </label>
            <Button
              onClick={handleGenerateContext}
              disabled={generateContent.isPending || !formData.name.trim()}
              variant="outline"
              className="w-full font-mono text-xs border-purple-500/30 text-purple-400 hover:bg-purple-500/10 hover:text-purple-300"
            >
              {generateContent.isPending ? (
                <>
                  <Loader2 className="w-3 h-3 mr-2 animate-spin" />
                  GENERATING...
                </>
              ) : (
                <>
                  <Sparkles className="w-3 h-3 mr-2" />
                  GENERATE WITH AI
                </>
              )}
            </Button>
            {!formData.name.trim() && (
              <p className="text-[10px] font-mono text-white/30 mt-1">
                Enter a scenario name first
              </p>
            )}
          </div>
        </div>
      </div>

      <div className="bg-white/5 border border-white/10 p-4 mb-4">
        <div className="flex items-start gap-2">
          <Info className="w-4 h-4 text-white/60 mt-0.5" />
          <div className="text-xs font-mono text-white/60">
            <p className="font-bold text-white mb-1">What is context?</p>
            <p>
              The context provides background information that all AI agents will
              consider when responding to your questions. This could include market
              conditions, product details, or any relevant scenario setup.
            </p>
          </div>
        </div>
      </div>

      <div>
        <label className="block text-[10px] font-mono text-white/40 uppercase mb-2">
          Context <span className="text-red-400">*</span>
        </label>
        <textarea
          value={formData.context}
          onChange={(e) => updateFormData({ context: e.target.value })}
          placeholder={`Example: "You are evaluating a new smartphone that costs $999. It features a 6.7-inch OLED display, 5G connectivity, and a 48MP camera system. The phone is from a well-known brand and offers 2-year warranty."`}
          rows={8}
          className="w-full px-3 py-2 bg-black border border-white/10 text-xs font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-white/30 resize-none"
        />
        <p className="text-[10px] font-mono text-white/30 mt-1">
          {formData.context.length} characters • All AI-generated content is fully editable
        </p>
      </div>
    </div>
  );
}

// Step 3: Questions
function Step3Questions({
  formData,
  updateFormData,
}: {
  formData: FormData;
  updateFormData: (updates: Partial<FormData>) => void;
}) {
  const addQuestion = () => {
    const newQuestion: Question = {
      id: `q_${Date.now()}`,
      type: 'multiple_choice',
      text: '',
      options: ['Option 1', 'Option 2'],
    };
    updateFormData({ questions: [...formData.questions, newQuestion] });
  };

  const updateQuestion = (id: string, updates: Partial<Question>) => {
    updateFormData({
      questions: formData.questions.map((q) =>
        q.id === id ? { ...q, ...updates } : q
      ),
    });
  };

  const removeQuestion = (id: string) => {
    updateFormData({
      questions: formData.questions.filter((q) => q.id !== id),
    });
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-mono font-bold text-white uppercase">Questions</h2>
        <Button
          onClick={addQuestion}
          variant="outline"
          size="sm"
          className="font-mono text-[10px] border-white/20 text-white/60 hover:bg-white/5"
        >
          <Plus className="w-3 h-3 mr-2" />
          ADD QUESTION
        </Button>
      </div>

      {formData.questions.length === 0 ? (
        <div className="text-center py-12 bg-white/5 border border-dashed border-white/20">
          <MessageSquare className="w-10 h-10 text-white/20 mx-auto mb-4" />
          <h3 className="font-mono text-sm font-bold text-white mb-1">NO QUESTIONS YET</h3>
          <p className="text-xs font-mono text-white/40 mb-4">
            Add questions that AI agents will answer
          </p>
          <Button
            onClick={addQuestion}
            
          >
            <Plus className="w-3 h-3 mr-2" />
            ADD FIRST QUESTION
          </Button>
        </div>
      ) : (
        <div className="space-y-4">
          {formData.questions.map((question, index) => (
            <QuestionEditor
              key={question.id}
              question={question}
              index={index}
              onUpdate={(updates) => updateQuestion(question.id, updates)}
              onRemove={() => removeQuestion(question.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function QuestionEditor({
  question,
  index,
  onUpdate,
  onRemove,
}: {
  question: Question;
  index: number;
  onUpdate: (updates: Partial<Question>) => void;
  onRemove: () => void;
}) {
  const addOption = () => {
    onUpdate({
      options: [...(question.options || []), `Option ${(question.options?.length || 0) + 1}`],
    });
  };

  const updateOption = (optionIndex: number, value: string) => {
    const newOptions = [...(question.options || [])];
    newOptions[optionIndex] = value;
    onUpdate({ options: newOptions });
  };

  const removeOption = (optionIndex: number) => {
    onUpdate({
      options: (question.options || []).filter((_, i) => i !== optionIndex),
    });
  };

  return (
    <div className="bg-white/5 border border-white/10 p-4">
      <div className="flex items-start justify-between mb-4">
        <span className="text-[10px] font-mono text-white/40 uppercase">
          Question {index + 1}
        </span>
        <button
          onClick={onRemove}
          className="p-1 hover:bg-white/10 text-white/40 hover:text-white"
        >
          <X className="w-3 h-3" />
        </button>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-[10px] font-mono text-white/40 uppercase mb-2">Question Type</label>
          <select
            value={question.type}
            onChange={(e) =>
              onUpdate({ type: e.target.value as Question['type'] })
            }
            className="w-full px-3 py-2 bg-black border border-white/10 text-xs font-mono text-white focus:outline-none focus:border-white/30"
          >
            <option value="multiple_choice">Multiple Choice</option>
            <option value="scale">Scale (1-10)</option>
            <option value="open_ended">Open Ended</option>
          </select>
        </div>

        <div>
          <label className="block text-[10px] font-mono text-white/40 uppercase mb-2">Question Text</label>
          <input
            type="text"
            value={question.text}
            onChange={(e) => onUpdate({ text: e.target.value })}
            placeholder="Enter your question"
            className="w-full px-3 py-2 bg-black border border-white/10 text-xs font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-white/30"
          />
        </div>

        {question.type === 'multiple_choice' && (
          <div>
            <label className="block text-[10px] font-mono text-white/40 uppercase mb-2">Options</label>
            <div className="space-y-2">
              {(question.options || []).map((option, optionIndex) => (
                <div key={optionIndex} className="flex items-center gap-2">
                  <input
                    type="text"
                    value={option}
                    onChange={(e) => updateOption(optionIndex, e.target.value)}
                    className="flex-1 px-3 py-2 bg-black border border-white/10 text-xs font-mono text-white focus:outline-none focus:border-white/30"
                  />
                  {(question.options?.length || 0) > 2 && (
                    <button
                      onClick={() => removeOption(optionIndex)}
                      className="p-2 hover:bg-white/10 text-white/40 hover:text-white"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  )}
                </div>
              ))}
              <Button
                onClick={addOption}
                variant="outline"
                size="sm"
                className="font-mono text-[10px] border-white/20 text-white/60 hover:bg-white/5"
              >
                <Plus className="w-3 h-3 mr-2" />
                ADD OPTION
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// Step 4: Population
function Step4Population({
  formData,
  updateFormData,
}: {
  formData: FormData;
  updateFormData: (updates: Partial<FormData>) => void;
}) {
  return (
    <div className="space-y-6">
      <h2 className="text-sm font-mono font-bold text-white uppercase mb-4">Population Settings</h2>

      <div>
        <label className="block text-[10px] font-mono text-white/40 uppercase mb-2">
          Population Size <span className="text-red-400">*</span>
        </label>
        <input
          type="number"
          value={formData.population_size}
          onChange={(e) =>
            updateFormData({ population_size: parseInt(e.target.value) || 0 })
          }
          min={10}
          max={10000}
          className="w-full px-3 py-2 bg-black border border-white/10 text-xs font-mono text-white focus:outline-none focus:border-white/30"
        />
        <p className="text-[10px] font-mono text-white/30 mt-1">
          Number of AI agents to simulate (10 - 10,000)
        </p>
      </div>

      <div>
        <h3 className="text-xs font-mono font-bold text-white uppercase mb-3">Demographics Distribution</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <DemographicsSlider
            title="Age Groups"
            distribution={formData.demographics.age_distribution}
            onChange={(dist) =>
              updateFormData({
                demographics: { ...formData.demographics, age_distribution: dist },
              })
            }
          />
          <DemographicsSlider
            title="Gender"
            distribution={formData.demographics.gender_distribution}
            onChange={(dist) =>
              updateFormData({
                demographics: { ...formData.demographics, gender_distribution: dist },
              })
            }
          />
        </div>
      </div>
    </div>
  );
}

function DemographicsSlider({
  title,
  distribution,
  onChange,
}: {
  title: string;
  distribution: { [key: string]: number };
  onChange: (dist: { [key: string]: number }) => void;
}) {
  return (
    <div className="bg-white/5 border border-white/10 p-4">
      <h4 className="text-xs font-mono font-bold text-white uppercase mb-3">{title}</h4>
      <div className="space-y-3">
        {Object.entries(distribution).map(([key, value]) => (
          <div key={key}>
            <div className="flex items-center justify-between text-xs font-mono mb-1">
              <span className="capitalize text-white/60">{key.replace('_', ' ')}</span>
              <span className="text-white">{value}%</span>
            </div>
            <input
              type="range"
              min={0}
              max={100}
              value={value}
              onChange={(e) =>
                onChange({ ...distribution, [key]: parseInt(e.target.value) })
              }
              className="w-full accent-white"
            />
          </div>
        ))}
      </div>
    </div>
  );
}

// Step 5: Review
function Step5Review({ formData }: { formData: FormData }) {
  return (
    <div className="space-y-6">
      <h2 className="text-sm font-mono font-bold text-white uppercase mb-4">Review & Create</h2>

      <div className="space-y-4">
        <div className="bg-white/5 border border-white/10 p-4">
          <h3 className="text-xs font-mono font-bold text-white uppercase mb-2">Basic Information</h3>
          <dl className="grid grid-cols-2 gap-2 text-xs font-mono">
            <dt className="text-white/40">Name:</dt>
            <dd className="text-white">{formData.name}</dd>
            <dt className="text-white/40">Description:</dt>
            <dd className="text-white">{formData.description || '-'}</dd>
          </dl>
        </div>

        <div className="bg-white/5 border border-white/10 p-4">
          <h3 className="text-xs font-mono font-bold text-white uppercase mb-2">Context</h3>
          <p className="text-xs font-mono text-white/60 whitespace-pre-wrap">
            {formData.context}
          </p>
        </div>

        <div className="bg-white/5 border border-white/10 p-4">
          <h3 className="text-xs font-mono font-bold text-white uppercase mb-2">
            Questions ({formData.questions.length})
          </h3>
          <ul className="space-y-2">
            {formData.questions.map((q, i) => (
              <li key={q.id} className="text-xs font-mono">
                <span className="text-white">{i + 1}.</span>{' '}
                <span className="text-white/60">{q.text}</span>
                <span className="text-white/30 ml-2">({q.type})</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="bg-white/5 border border-white/10 p-4">
          <h3 className="text-xs font-mono font-bold text-white uppercase mb-2">Population</h3>
          <p className="text-xs font-mono">
            <span className="text-white">{formData.population_size.toLocaleString()}</span>
            <span className="text-white/40"> AI agents</span>
          </p>
        </div>
      </div>

      <div className="bg-white/5 border border-white/10 p-4">
        <div className="flex items-start gap-2">
          <Info className="w-4 h-4 text-white/60 mt-0.5" />
          <div className="text-xs font-mono text-white/60">
            <p className="font-bold text-white mb-1">Ready to create</p>
            <p>
              Your scenario will be saved as a draft. You can run the simulation
              from the project page.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
