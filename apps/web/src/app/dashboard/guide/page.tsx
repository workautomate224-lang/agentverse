'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  ArrowLeft,
  ArrowRight,
  FolderKanban,
  Users,
  FileText,
  Play,
  BarChart3,
  CheckCircle,
  Terminal,
  Lightbulb,
  Target,
  TrendingUp,
  ChevronDown,
  ChevronUp,
  Zap,
  Database,
  Brain,
  Globe,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const steps = [
  {
    id: 1,
    title: 'Create a Project',
    icon: FolderKanban,
    description: 'Start by creating a project to organize your simulations',
    details: [
      'Go to Projects section and click "NEW PROJECT"',
      'Give your project a name (e.g., "Q4 Product Launch Analysis")',
      'Add a description to help you remember the purpose',
      'Select a domain (e.g., Marketing, Political, Consumer)',
      'Projects help you organize multiple scenarios and simulations',
    ],
    tip: 'Use descriptive names that indicate the goal of your research',
    link: '/dashboard/projects/new',
    linkText: 'Create Project',
  },
  {
    id: 2,
    title: 'Create a Scenario',
    icon: FileText,
    description: 'Define what you want to simulate within your project',
    details: [
      'Open your project and click "NEW SCENARIO"',
      'Provide context for the simulation (background information)',
      'Add questions you want to ask the AI personas',
      'Set the population size (number of personas to simulate)',
      'Configure demographics to match your target audience',
    ],
    tip: 'Be specific with your context - the more detail, the better the simulation',
    link: '/dashboard/projects',
    linkText: 'View Projects',
  },
  {
    id: 3,
    title: 'Generate Personas',
    icon: Users,
    description: 'Create AI personas that represent your target audience',
    details: [
      'Go to Personas section and click "CREATE PERSONAS"',
      'Choose your data source: AI Generated, File Upload, or AI Research',
      'Select the region and target demographics',
      'Specify the number of personas to generate (10-10,000)',
      'Our AI creates realistic personas based on census data',
    ],
    tip: 'AI Generated personas use real census data for authenticity',
    link: '/dashboard/personas/new',
    linkText: 'Create Personas',
  },
  {
    id: 4,
    title: 'Run Simulation',
    icon: Play,
    description: 'Execute your scenario with the generated personas',
    details: [
      'From the scenario, click "RUN" to start',
      'Select the number of agents to simulate',
      'Choose the AI model for responses',
      'Monitor real-time progress as agents respond',
      'Each agent answers based on their unique persona profile',
    ],
    tip: 'Start with 50-100 agents to test, then scale up for final results',
    link: '/dashboard/simulations/new',
    linkText: 'New Simulation',
  },
  {
    id: 5,
    title: 'Analyze Results',
    icon: BarChart3,
    description: 'View aggregated insights from your simulation',
    details: [
      'Go to Results to see completed simulations',
      'View response distribution charts and statistics',
      'Analyze demographic breakdowns by age, income, region',
      'Review individual agent responses for qualitative insights',
      'Export data for further analysis',
    ],
    tip: 'Compare results across different demographic segments',
    link: '/dashboard/results',
    linkText: 'View Results',
  },
];

const productTypes = [
  {
    type: 'Predict',
    icon: TrendingUp,
    description: 'Forecast outcomes like elections, product launches, or market trends',
    useCases: ['Election predictions', 'Product adoption rates', 'Market sentiment analysis'],
  },
  {
    type: 'Insight',
    icon: Lightbulb,
    description: 'Gather qualitative feedback and understand audience perspectives',
    useCases: ['Brand perception', 'Feature preferences', 'Customer pain points'],
  },
  {
    type: 'Simulate',
    icon: Users,
    description: 'Model behavior patterns and decision-making processes',
    useCases: ['User journey simulation', 'A/B testing scenarios', 'Policy impact analysis'],
  },
];

const features = [
  {
    icon: Brain,
    title: 'AI-Powered Personas',
    description: 'Generate realistic personas backed by census data and behavioral research',
  },
  {
    icon: Database,
    title: 'Census-Backed Data',
    description: 'Personas reflect real demographic distributions from official sources',
  },
  {
    icon: Globe,
    title: 'Multi-Region Support',
    description: 'Create personas for US, UK, EU, and other major regions',
  },
  {
    icon: Zap,
    title: 'Scalable Simulations',
    description: 'Run simulations with 10 to 10,000 AI agents simultaneously',
  },
];

export default function GuidePage() {
  const [expandedStep, setExpandedStep] = useState<number | null>(1);
  const [activeSection, setActiveSection] = useState<'workflow' | 'products' | 'features'>('workflow');

  return (
    <div className="min-h-screen bg-black p-6">
      {/* Header */}
      <div className="mb-8">
        <Link href="/dashboard">
          <Button variant="ghost" size="sm" className="mb-4">
            <ArrowLeft className="w-3 h-3 mr-2" />
            BACK TO DASHBOARD
          </Button>
        </Link>

        <div className="flex items-center gap-2 mb-1">
          <Terminal className="w-4 h-4 text-white/60" />
          <span className="text-xs font-mono text-white/40 uppercase tracking-wider">Platform Guide</span>
        </div>
        <h1 className="text-2xl font-mono font-bold text-white">How AgentVerse Works</h1>
        <p className="text-sm font-mono text-white/50 mt-2 max-w-2xl">
          AgentVerse is an AI-powered simulation platform that creates realistic synthetic personas
          to help you predict outcomes, gather insights, and understand your audience.
        </p>
      </div>

      {/* Section Tabs */}
      <div className="flex gap-2 mb-8">
        {[
          { id: 'workflow', label: 'WORKFLOW', icon: Play },
          { id: 'products', label: 'PRODUCT TYPES', icon: Target },
          { id: 'features', label: 'FEATURES', icon: Zap },
        ].map((section) => (
          <button
            key={section.id}
            onClick={() => setActiveSection(section.id as any)}
            className={cn(
              'flex items-center gap-2 px-4 py-2 text-xs font-mono transition-colors',
              activeSection === section.id
                ? 'bg-white text-black'
                : 'bg-white/5 text-white/60 hover:bg-white/10 border border-white/10'
            )}
          >
            <section.icon className="w-3 h-3" />
            {section.label}
          </button>
        ))}
      </div>

      {/* Workflow Section */}
      {activeSection === 'workflow' && (
        <div className="space-y-4">
          <div className="bg-white/5 border border-white/10 p-4 mb-6">
            <h2 className="text-sm font-mono font-bold text-white uppercase mb-2">5-Step Workflow</h2>
            <p className="text-xs font-mono text-white/50">
              Follow these steps to create your first simulation and gather insights
            </p>
          </div>

          {steps.map((step, index) => {
            const StepIcon = step.icon;
            const isExpanded = expandedStep === step.id;
            const isCompleted = expandedStep !== null && step.id < expandedStep;

            return (
              <div
                key={step.id}
                className={cn(
                  'bg-white/5 border transition-all',
                  isExpanded ? 'border-white/30' : 'border-white/10'
                )}
              >
                <button
                  onClick={() => setExpandedStep(isExpanded ? null : step.id)}
                  className="w-full p-4 flex items-center justify-between"
                >
                  <div className="flex items-center gap-4">
                    <div className={cn(
                      'w-10 h-10 flex items-center justify-center font-mono font-bold text-sm',
                      isCompleted ? 'bg-green-500/20 text-green-400' :
                      isExpanded ? 'bg-white text-black' : 'bg-white/10 text-white/60'
                    )}>
                      {isCompleted ? <CheckCircle className="w-5 h-5" /> : step.id}
                    </div>
                    <div className="text-left">
                      <h3 className="font-mono font-bold text-white text-sm">{step.title}</h3>
                      <p className="text-xs font-mono text-white/40">{step.description}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <StepIcon className="w-5 h-5 text-white/40" />
                    {isExpanded ? (
                      <ChevronUp className="w-4 h-4 text-white/40" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-white/40" />
                    )}
                  </div>
                </button>

                {isExpanded && (
                  <div className="px-4 pb-4 pt-0 border-t border-white/10">
                    <div className="ml-14 space-y-4">
                      <div className="space-y-2 mt-4">
                        {step.details.map((detail, idx) => (
                          <div key={idx} className="flex items-start gap-2">
                            <span className="text-white/30 text-xs font-mono mt-0.5">{idx + 1}.</span>
                            <span className="text-xs font-mono text-white/70">{detail}</span>
                          </div>
                        ))}
                      </div>

                      <div className="bg-white/5 border border-white/10 p-3">
                        <div className="flex items-center gap-2 mb-1">
                          <Lightbulb className="w-3 h-3 text-yellow-400" />
                          <span className="text-[10px] font-mono text-yellow-400 uppercase">Pro Tip</span>
                        </div>
                        <p className="text-xs font-mono text-white/60">{step.tip}</p>
                      </div>

                      <div className="flex items-center justify-between pt-2">
                        <Link href={step.link}>
                          <Button size="sm">
                            {step.linkText}
                            <ArrowRight className="w-3 h-3 ml-2" />
                          </Button>
                        </Link>
                        {index < steps.length - 1 && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setExpandedStep(step.id + 1)}
                          >
                            Next Step
                            <ArrowRight className="w-3 h-3 ml-2" />
                          </Button>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Product Types Section */}
      {activeSection === 'products' && (
        <div className="space-y-4">
          <div className="bg-white/5 border border-white/10 p-4 mb-6">
            <h2 className="text-sm font-mono font-bold text-white uppercase mb-2">Product Types</h2>
            <p className="text-xs font-mono text-white/50">
              Choose the right product type based on your research goals
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {productTypes.map((product) => {
              const ProductIcon = product.icon;
              return (
                <div key={product.type} className="bg-white/5 border border-white/10 p-6">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 bg-white/10 flex items-center justify-center">
                      <ProductIcon className="w-5 h-5 text-white/60" />
                    </div>
                    <h3 className="font-mono font-bold text-white text-lg">{product.type}</h3>
                  </div>
                  <p className="text-xs font-mono text-white/60 mb-4">{product.description}</p>
                  <div className="space-y-2">
                    <p className="text-[10px] font-mono text-white/40 uppercase">Use Cases:</p>
                    {product.useCases.map((useCase, idx) => (
                      <div key={idx} className="flex items-center gap-2">
                        <div className="w-1 h-1 bg-white/40" />
                        <span className="text-xs font-mono text-white/50">{useCase}</span>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>

          <div className="mt-6">
            <Link href="/dashboard/products/new">
              <Button>
                Create Your First Product
                <ArrowRight className="w-3 h-3 ml-2" />
              </Button>
            </Link>
          </div>
        </div>
      )}

      {/* Features Section */}
      {activeSection === 'features' && (
        <div className="space-y-4">
          <div className="bg-white/5 border border-white/10 p-4 mb-6">
            <h2 className="text-sm font-mono font-bold text-white uppercase mb-2">Platform Features</h2>
            <p className="text-xs font-mono text-white/50">
              What makes AgentVerse powerful
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {features.map((feature) => {
              const FeatureIcon = feature.icon;
              return (
                <div key={feature.title} className="bg-white/5 border border-white/10 p-6">
                  <div className="flex items-start gap-4">
                    <div className="w-10 h-10 bg-white/10 flex items-center justify-center flex-shrink-0">
                      <FeatureIcon className="w-5 h-5 text-white/60" />
                    </div>
                    <div>
                      <h3 className="font-mono font-bold text-white text-sm mb-2">{feature.title}</h3>
                      <p className="text-xs font-mono text-white/50">{feature.description}</p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="bg-white/5 border border-white/10 p-6 mt-6">
            <h3 className="font-mono font-bold text-white text-sm mb-4">Quick Start Checklist</h3>
            <div className="space-y-3">
              {[
                'Create your first project',
                'Generate 100 personas for your target market',
                'Set up a scenario with 3-5 questions',
                'Run a test simulation with 50 agents',
                'Analyze results and iterate',
              ].map((item, idx) => (
                <div key={idx} className="flex items-center gap-3">
                  <div className="w-5 h-5 border border-white/20 flex items-center justify-center text-[10px] font-mono text-white/40">
                    {idx + 1}
                  </div>
                  <span className="text-xs font-mono text-white/60">{item}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="mt-12 pt-4 border-t border-white/5">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-1">
            <Terminal className="w-3 h-3" />
            <span>GUIDE MODULE</span>
          </div>
          <span>AGENTVERSE v1.0.0</span>
        </div>
      </div>
    </div>
  );
}
