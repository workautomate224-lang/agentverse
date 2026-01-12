'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  ArrowLeft,
  ArrowRight,
  FolderKanban,
  Users,
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
  Brain,
  Globe,
  GitBranch,
  MessageSquare,
  Settings2,
  Shield,
  PlayCircle,
  Map,
  Compass,
  Layers,
  Search,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const steps = [
  {
    id: 1,
    title: 'Create a Project',
    icon: FolderKanban,
    description: 'Define your prediction goal and configure the simulation',
    details: [
      'Go to Projects and click "CREATE PROJECT"',
      'Enter your prediction goal (e.g., "What will be the public response to our new product launch?")',
      'Select a Prediction Core: Collective (group behavior), Target (individual paths), or Hybrid (both)',
      'Choose a domain template (Consumer, Political, Health, Financial) or start blank',
      'Configure output metrics: Reliability Report, Telemetry, Exports',
    ],
    tip: 'Start with "Collective" mode for aggregate predictions, use "Target" for individual decision modeling',
    link: '/dashboard/projects/new',
    linkText: 'Create Project',
  },
  {
    id: 2,
    title: 'Set Up Personas',
    icon: Users,
    description: 'Build your agent population from various sources',
    details: [
      'Go to the Personas Studio in your project',
      'Choose a data source: Domain Template, Upload CSV, AI Generation, or Deep Search',
      'Configure demographics to match your target population',
      'Review and validate persona distributions',
      'Personas represent the agents that will participate in your simulations',
    ],
    tip: 'Use "Deep Search" for AI-powered persona research based on real-world data',
    link: '/dashboard/personas',
    linkText: 'Personas Studio',
  },
  {
    id: 3,
    title: 'Run Baseline Simulation',
    icon: Play,
    description: 'Create your root node with initial world state',
    details: [
      'Open your project and click "Run Baseline" on the Overview page',
      'Configure society rules (Conformity, Media Influence, Social Network effects)',
      'Set simulation horizon (number of ticks/steps)',
      'The baseline creates your Root Node - the starting point for all branches',
      'All future "what-if" scenarios fork from this baseline',
    ],
    tip: 'The baseline represents your "current state" - future branches explore alternative outcomes',
    link: '/dashboard/projects',
    linkText: 'View Projects',
  },
  {
    id: 4,
    title: 'Explore the Universe Map',
    icon: Map,
    description: 'Visualize and navigate your branching scenario tree',
    details: [
      'Open Universe Map from your project tabs',
      'See your Root Node and all branched scenarios as a tree',
      'Click nodes to inspect outcomes, probability, and confidence',
      'Use pan/zoom to navigate complex scenario trees',
      'Compare 2-4 nodes side-by-side for detailed analysis',
    ],
    tip: 'Each node represents an immutable snapshot - changes create new branches, never modify history',
    link: '/dashboard/projects',
    linkText: 'Open Project',
  },
  {
    id: 5,
    title: 'Ask "What If" Questions',
    icon: MessageSquare,
    description: 'Use natural language to create branching scenarios',
    details: [
      'Click "Ask" button in Universe Map',
      'Enter a natural language prompt (e.g., "What if a competitor launches a similar product?")',
      'The Event Compiler analyzes intent and decomposes into sub-effects',
      'Review generated scenario clusters and their probabilities',
      'Select scenarios to branch into new nodes',
    ],
    tip: 'The Ask feature uses AI to translate your questions into concrete simulation variables',
    link: '/dashboard/projects',
    linkText: 'Try Ask',
  },
  {
    id: 6,
    title: 'Fork & Tune Variables',
    icon: GitBranch,
    description: 'Manually adjust simulation variables to explore scenarios',
    details: [
      'Click "Fork & Tune" on any node in Universe Map',
      'Adjust variables by category: Economy, Media, Social, Trust',
      'Use sliders or numeric inputs for precise control',
      'See intervention magnitude indicator (small/medium/large)',
      'Click "Run Fork" to create a new branch with your changes',
    ],
    tip: 'Small interventions often reveal more about system behavior than dramatic changes',
    link: '/dashboard/projects',
    linkText: 'Fork Node',
  },
  {
    id: 7,
    title: 'Review Reliability',
    icon: Shield,
    description: 'Assess prediction confidence and calibration',
    details: [
      'Open Reliability tab in your project',
      'View overall reliability grade and component scores',
      'Check Calibration: How accurate are probability estimates?',
      'Check Stability: How consistent across random seeds?',
      'Check Sensitivity: Which variables have biggest impact?',
      'Check Drift: Has data distribution shifted?',
    ],
    tip: 'Re-run reliability analysis after major changes to ensure prediction quality',
    link: '/dashboard/calibration',
    linkText: 'Calibration Lab',
  },
  {
    id: 8,
    title: 'Watch 2D Replay',
    icon: PlayCircle,
    description: 'Visualize simulation dynamics over time',
    details: [
      'Open 2D Replay tab from any completed run',
      'Use play/pause/seek controls to navigate time',
      'Toggle layers: Emotion, Stance, Influence, Exposure',
      'Filter by region or persona segment',
      'Click any agent to see their state history and events',
      'Important: Replay is READ-ONLY - it never triggers new simulations',
    ],
    tip: 'Watch how opinions shift through the population over time to understand dynamics',
    link: '/dashboard/projects',
    linkText: 'Open Replay',
  },
];

const predictionCores = [
  {
    type: 'Collective (Society Mode)',
    icon: Users,
    description: 'Simulate population-level behavior using rule-based agent dynamics',
    useCases: ['Market sentiment', 'Public opinion shifts', 'Adoption patterns', 'Social contagion'],
    when: 'When you care about aggregate outcomes, not individual decisions',
  },
  {
    type: 'Target Mode',
    icon: Target,
    description: 'Model individual decision paths for specific persona archetypes',
    useCases: ['Customer journey mapping', 'Decision tree analysis', 'Behavioral intervention design'],
    when: 'When you need to understand WHY individuals make specific choices',
  },
  {
    type: 'Hybrid Mode',
    icon: Compass,
    description: 'Combine key actors (target-style) with population context (society-style)',
    useCases: ['Influencer impact analysis', 'Leadership decisions', 'Key stakeholder modeling'],
    when: 'When both individual actors AND population dynamics matter',
  },
];

const features = [
  {
    icon: Map,
    title: 'Universe Map',
    description: 'Branching scenario tree - explore multiple futures from any point, never mutating history',
  },
  {
    icon: Brain,
    title: 'LLM Event Compiler',
    description: 'Ask "what if" in natural language, AI translates to simulation variables',
  },
  {
    icon: Layers,
    title: 'Telemetry & Replay',
    description: 'Time-series data with 2D visualization of agent states, emotions, and interactions',
  },
  {
    icon: Shield,
    title: 'Reliability Tracking',
    description: 'Calibration, stability, sensitivity, and drift detection for trustworthy predictions',
  },
  {
    icon: GitBranch,
    title: 'Fork & Tune',
    description: 'Create alternative scenarios by adjusting variables and running new simulations',
  },
  {
    icon: Search,
    title: 'Deep Search',
    description: 'AI-powered persona research using real-world data and census information',
  },
  {
    icon: Settings2,
    title: 'Admin Model Controls',
    description: 'Configure AI models per feature, track costs, manage fallback chains',
  },
  {
    icon: BarChart3,
    title: 'Exports & Reports',
    description: 'Export nodes, comparisons, reliability reports, and telemetry snapshots',
  },
];

export default function GuidePage() {
  const [expandedStep, setExpandedStep] = useState<number | null>(1);
  const [activeSection, setActiveSection] = useState<'workflow' | 'cores' | 'features'>('workflow');

  return (
    <div className="min-h-screen bg-black p-4 md:p-6">
      {/* Header */}
      <div className="mb-6 md:mb-8">
        <Link href="/dashboard">
          <Button variant="ghost" size="sm" className="mb-3 md:mb-4 font-mono text-[10px] md:text-xs">
            <ArrowLeft className="w-3 h-3 mr-1.5 md:mr-2" />
            <span className="hidden sm:inline">BACK TO DASHBOARD</span>
            <span className="sm:hidden">BACK</span>
          </Button>
        </Link>

        <div className="flex items-center gap-2 mb-1">
          <Terminal className="w-3.5 h-3.5 md:w-4 md:h-4 text-white/60" />
          <span className="text-[10px] md:text-xs font-mono text-white/40 uppercase tracking-wider">Platform Handbook</span>
        </div>
        <h1 className="text-lg md:text-2xl font-mono font-bold text-white">AgentVerse User Guide</h1>
        <p className="text-xs md:text-sm font-mono text-white/50 mt-1.5 md:mt-2 max-w-2xl">
          AgentVerse is a <span className="text-cyan-400">Future Predictive AI Platform</span> that creates reversible,
          on-demand simulations producing auditable predictions.
        </p>
      </div>

      {/* Section Tabs */}
      <div className="flex flex-wrap gap-1.5 md:gap-2 mb-6 md:mb-8">
        {[
          { id: 'workflow', label: '8-STEP WORKFLOW', shortLabel: 'WORKFLOW', icon: Play },
          { id: 'cores', label: 'PREDICTION CORES', shortLabel: 'CORES', icon: Target },
          { id: 'features', label: 'KEY FEATURES', shortLabel: 'FEATURES', icon: Zap },
        ].map((section) => (
          <button
            key={section.id}
            onClick={() => setActiveSection(section.id as 'workflow' | 'cores' | 'features')}
            className={cn(
              'flex items-center gap-1.5 md:gap-2 px-2.5 md:px-4 py-1.5 md:py-2 text-[10px] md:text-xs font-mono transition-colors',
              activeSection === section.id
                ? 'bg-white text-black'
                : 'bg-white/5 text-white/60 hover:bg-white/10 border border-white/10'
            )}
          >
            <section.icon className="w-3 h-3" />
            <span className="hidden sm:inline">{section.label}</span>
            <span className="sm:hidden">{section.shortLabel}</span>
          </button>
        ))}
      </div>

      {/* Workflow Section */}
      {activeSection === 'workflow' && (
        <div className="space-y-3 md:space-y-4">
          <div className="bg-white/5 border border-white/10 p-3 md:p-4 mb-4 md:mb-6">
            <h2 className="text-xs md:text-sm font-mono font-bold text-white uppercase mb-1.5 md:mb-2">Complete Workflow</h2>
            <p className="text-[10px] md:text-xs font-mono text-white/50">
              From project creation to insight extraction - follow these steps for your first prediction
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
                  isExpanded ? 'border-cyan-400/30' : 'border-white/10'
                )}
              >
                <button
                  onClick={() => setExpandedStep(isExpanded ? null : step.id)}
                  className="w-full p-3 md:p-4 flex items-center justify-between gap-2"
                >
                  <div className="flex items-center gap-2.5 md:gap-4 min-w-0">
                    <div className={cn(
                      'w-8 h-8 md:w-10 md:h-10 flex items-center justify-center font-mono font-bold text-xs md:text-sm flex-shrink-0',
                      isCompleted ? 'bg-green-500/20 text-green-400' :
                      isExpanded ? 'bg-cyan-400 text-black' : 'bg-white/10 text-white/60'
                    )}>
                      {isCompleted ? <CheckCircle className="w-4 h-4 md:w-5 md:h-5" /> : step.id}
                    </div>
                    <div className="text-left min-w-0">
                      <h3 className="font-mono font-bold text-white text-xs md:text-sm truncate">{step.title}</h3>
                      <p className="text-[10px] md:text-xs font-mono text-white/40 truncate">{step.description}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 md:gap-3 flex-shrink-0">
                    <StepIcon className="w-4 h-4 md:w-5 md:h-5 text-white/40 hidden sm:block" />
                    {isExpanded ? (
                      <ChevronUp className="w-4 h-4 text-white/40" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-white/40" />
                    )}
                  </div>
                </button>

                {isExpanded && (
                  <div className="px-3 md:px-4 pb-3 md:pb-4 pt-0 border-t border-white/10">
                    <div className="ml-0 md:ml-14 space-y-3 md:space-y-4">
                      <div className="space-y-1.5 md:space-y-2 mt-3 md:mt-4">
                        {step.details.map((detail, idx) => (
                          <div key={idx} className="flex items-start gap-2">
                            <span className="text-cyan-400/60 text-[10px] md:text-xs font-mono mt-0.5">{idx + 1}.</span>
                            <span className="text-[10px] md:text-xs font-mono text-white/70">{detail}</span>
                          </div>
                        ))}
                      </div>

                      <div className="bg-cyan-400/5 border border-cyan-400/20 p-2.5 md:p-3">
                        <div className="flex items-center gap-2 mb-1">
                          <Lightbulb className="w-3 h-3 text-cyan-400" />
                          <span className="text-[9px] md:text-[10px] font-mono text-cyan-400 uppercase">Pro Tip</span>
                        </div>
                        <p className="text-[10px] md:text-xs font-mono text-white/60">{step.tip}</p>
                      </div>

                      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 pt-2">
                        <Link href={step.link}>
                          <Button size="sm" className="w-full sm:w-auto font-mono text-[10px] md:text-xs">
                            {step.linkText}
                            <ArrowRight className="w-3 h-3 ml-1.5 md:ml-2" />
                          </Button>
                        </Link>
                        {index < steps.length - 1 && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setExpandedStep(step.id + 1)}
                            className="w-full sm:w-auto font-mono text-[10px] md:text-xs"
                          >
                            Next Step
                            <ArrowRight className="w-3 h-3 ml-1.5 md:ml-2" />
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

      {/* Prediction Cores Section */}
      {activeSection === 'cores' && (
        <div className="space-y-3 md:space-y-4">
          <div className="bg-white/5 border border-white/10 p-3 md:p-4 mb-4 md:mb-6">
            <h2 className="text-xs md:text-sm font-mono font-bold text-white uppercase mb-1.5 md:mb-2">Prediction Cores</h2>
            <p className="text-[10px] md:text-xs font-mono text-white/50">
              Choose the right simulation mode based on your prediction needs
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 md:gap-4">
            {predictionCores.map((core) => {
              const CoreIcon = core.icon;
              return (
                <div key={core.type} className="bg-white/5 border border-white/10 p-4 md:p-6">
                  <div className="flex items-center gap-2.5 md:gap-3 mb-3 md:mb-4">
                    <div className="w-8 h-8 md:w-10 md:h-10 bg-cyan-400/10 flex items-center justify-center flex-shrink-0">
                      <CoreIcon className="w-4 h-4 md:w-5 md:h-5 text-cyan-400" />
                    </div>
                    <h3 className="font-mono font-bold text-white text-xs md:text-sm">{core.type}</h3>
                  </div>
                  <p className="text-[10px] md:text-xs font-mono text-white/60 mb-3 md:mb-4">{core.description}</p>

                  <div className="space-y-2.5 md:space-y-3">
                    <div>
                      <p className="text-[9px] md:text-[10px] font-mono text-white/40 uppercase mb-1.5 md:mb-2">Use Cases:</p>
                      {core.useCases.map((useCase, idx) => (
                        <div key={idx} className="flex items-center gap-2">
                          <div className="w-1 h-1 bg-cyan-400/40 flex-shrink-0" />
                          <span className="text-[10px] md:text-xs font-mono text-white/50">{useCase}</span>
                        </div>
                      ))}
                    </div>

                    <div className="pt-2.5 md:pt-3 border-t border-white/10">
                      <p className="text-[9px] md:text-[10px] font-mono text-cyan-400/60 uppercase mb-1">When to use:</p>
                      <p className="text-[10px] md:text-xs font-mono text-white/50">{core.when}</p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="mt-4 md:mt-6 bg-white/5 border border-white/10 p-3 md:p-4">
            <h3 className="text-xs md:text-sm font-mono font-bold text-white mb-2">Quick Decision Guide</h3>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 md:gap-4 text-[10px] md:text-xs font-mono">
              <div className="text-white/60">
                <span className="text-cyan-400">Collective:</span> "What will the market think?"
              </div>
              <div className="text-white/60">
                <span className="text-cyan-400">Target:</span> "How will this person decide?"
              </div>
              <div className="text-white/60">
                <span className="text-cyan-400">Hybrid:</span> "How will this leader affect the crowd?"
              </div>
            </div>
          </div>

          <div className="mt-4 md:mt-6">
            <Link href="/dashboard/projects/new">
              <Button className="w-full sm:w-auto font-mono text-[10px] md:text-xs">
                Create Your First Project
                <ArrowRight className="w-3 h-3 ml-1.5 md:ml-2" />
              </Button>
            </Link>
          </div>
        </div>
      )}

      {/* Features Section */}
      {activeSection === 'features' && (
        <div className="space-y-3 md:space-y-4">
          <div className="bg-white/5 border border-white/10 p-3 md:p-4 mb-4 md:mb-6">
            <h2 className="text-xs md:text-sm font-mono font-bold text-white uppercase mb-1.5 md:mb-2">Key Features</h2>
            <p className="text-[10px] md:text-xs font-mono text-white/50">
              Core capabilities of the AgentVerse platform
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-4">
            {features.map((feature) => {
              const FeatureIcon = feature.icon;
              return (
                <div key={feature.title} className="bg-white/5 border border-white/10 p-4 md:p-6">
                  <div className="flex items-start gap-3 md:gap-4">
                    <div className="w-8 h-8 md:w-10 md:h-10 bg-cyan-400/10 flex items-center justify-center flex-shrink-0">
                      <FeatureIcon className="w-4 h-4 md:w-5 md:h-5 text-cyan-400" />
                    </div>
                    <div className="min-w-0">
                      <h3 className="font-mono font-bold text-white text-xs md:text-sm mb-1.5 md:mb-2">{feature.title}</h3>
                      <p className="text-[10px] md:text-xs font-mono text-white/50">{feature.description}</p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="bg-white/5 border border-white/10 p-4 md:p-6 mt-4 md:mt-6">
            <h3 className="font-mono font-bold text-white text-xs md:text-sm mb-3 md:mb-4">Core Principles</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 md:gap-4">
              {[
                { label: 'Fork-Not-Mutate', desc: 'Nodes are immutable - changes create new branches' },
                { label: 'On-Demand Execution', desc: 'Simulations run explicitly, not continuously' },
                { label: 'Read-Only Replay', desc: '2D visualization never triggers new simulations' },
                { label: 'Auditable Artifacts', desc: 'All predictions are versioned and traceable' },
                { label: 'LLMs as Compilers', desc: 'AI translates prompts, rules execute deterministically' },
                { label: 'Multi-Tenant', desc: 'Isolated data per organization with role-based access' },
              ].map((principle, idx) => (
                <div key={idx} className="flex items-start gap-2.5 md:gap-3">
                  <div className="w-4 h-4 md:w-5 md:h-5 border border-cyan-400/30 flex items-center justify-center text-[9px] md:text-[10px] font-mono text-cyan-400/60 flex-shrink-0">
                    {idx + 1}
                  </div>
                  <div className="min-w-0">
                    <span className="text-[10px] md:text-xs font-mono text-white font-bold">{principle.label}</span>
                    <p className="text-[9px] md:text-[11px] font-mono text-white/40">{principle.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-cyan-400/5 border border-cyan-400/20 p-4 md:p-6 mt-4 md:mt-6">
            <h3 className="font-mono font-bold text-cyan-400 text-xs md:text-sm mb-3 md:mb-4">Quick Start Checklist</h3>
            <div className="space-y-2.5 md:space-y-3">
              {[
                'Create your first project with a clear prediction goal',
                'Select the appropriate Prediction Core (Collective/Target/Hybrid)',
                'Import or generate your persona population',
                'Run a baseline simulation to create your Root Node',
                'Use "Ask" to explore what-if scenarios',
                'Review Reliability metrics before acting on predictions',
              ].map((item, idx) => (
                <div key={idx} className="flex items-start gap-2.5 md:gap-3">
                  <div className="w-4 h-4 md:w-5 md:h-5 border border-cyan-400/30 flex items-center justify-center text-[9px] md:text-[10px] font-mono text-cyan-400 flex-shrink-0">
                    {idx + 1}
                  </div>
                  <span className="text-[10px] md:text-xs font-mono text-white/60">{item}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="mt-8 md:mt-12 pt-3 md:pt-4 border-t border-white/5">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-1">
            <Terminal className="w-3 h-3" />
            <span className="hidden sm:inline">USER HANDBOOK</span>
            <span className="sm:hidden">GUIDE</span>
          </div>
          <span className="hidden sm:inline">AGENTVERSE v1.0.0 - Future Predictive AI Platform</span>
          <span className="sm:hidden">AGENTVERSE v1.0.0</span>
        </div>
      </div>
    </div>
  );
}
