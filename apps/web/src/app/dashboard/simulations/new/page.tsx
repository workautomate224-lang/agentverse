'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  ArrowLeft,
  ArrowRight,
  Play,
  Loader2,
  Users,
  Cpu,
  AlertCircle,
  CheckCircle,
  Settings,
  Terminal,
  FolderKanban,
  FileText,
  Sparkles,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  useProjects,
  useScenariosByProject,
  usePersonaTemplates,
  useCreateSimulation,
  useRunSimulation,
  useSimulation
} from '@/hooks/useApi';

const models = [
  {
    id: 'anthropic/claude-3-haiku',
    name: 'Claude 3 Haiku',
    description: 'Fast and cost-effective',
    cost: '$0.25/1M tokens',
    speed: 'Fast',
  },
  {
    id: 'anthropic/claude-3.5-sonnet',
    name: 'Claude 3.5 Sonnet',
    description: 'Balanced performance',
    cost: '$3/1M tokens',
    speed: 'Medium',
  },
  {
    id: 'openai/gpt-4o-mini',
    name: 'GPT-4o Mini',
    description: 'OpenAI fast model',
    cost: '$0.15/1M tokens',
    speed: 'Fast',
  },
  {
    id: 'openai/gpt-4o',
    name: 'GPT-4o',
    description: 'OpenAI flagship model',
    cost: '$5/1M tokens',
    speed: 'Medium',
  },
];

export default function NewSimulationPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const projectIdParam = searchParams.get('project');
  const scenarioIdParam = searchParams.get('scenario');

  // Data fetching - all inline, no redirects
  const { data: projects, isLoading: projectsLoading } = useProjects();
  const { data: personaTemplates, isLoading: personasLoading } = usePersonaTemplates();

  const [selectedProjectId, setSelectedProjectId] = useState(projectIdParam || '');

  // Fetch scenarios for selected project
  const { data: scenarios, isLoading: scenariosLoading } = useScenariosByProject(selectedProjectId);

  const createSimulation = useCreateSimulation();
  const runSimulation = useRunSimulation();

  const [step, setStep] = useState(1);
  const [error, setError] = useState('');
  const [runId, setRunId] = useState<string | null>(null);

  const [formData, setFormData] = useState({
    scenarioId: scenarioIdParam || '',
    personaTemplateId: '',
    agentCount: 100,
    model: 'anthropic/claude-3-haiku',
  });

  // Auto-select first project if available
  useEffect(() => {
    if (projects && projects.length > 0 && !selectedProjectId) {
      setSelectedProjectId(projects[0].id);
    }
  }, [projects, selectedProjectId]);

  // Auto-select first scenario when project changes
  useEffect(() => {
    if (scenarios && scenarios.length > 0 && !formData.scenarioId) {
      setFormData(prev => ({ ...prev, scenarioId: scenarios[0].id }));
    }
  }, [scenarios, formData.scenarioId]);

  // Auto-select first persona template
  useEffect(() => {
    if (personaTemplates && personaTemplates.length > 0 && !formData.personaTemplateId) {
      setFormData(prev => ({ ...prev, personaTemplateId: personaTemplates[0].id }));
    }
  }, [personaTemplates, formData.personaTemplateId]);

  // Poll for simulation status when running
  const { data: simulation } = useSimulation(runId || '');

  // Redirect to results when completed
  useEffect(() => {
    if (simulation?.status === 'completed') {
      router.push(`/dashboard/results/${simulation.id}`);
    }
  }, [simulation, router]);

  const handleProjectChange = (projectId: string) => {
    setSelectedProjectId(projectId);
    // Reset scenario selection when project changes
    setFormData(prev => ({ ...prev, scenarioId: '' }));
  };

  const handleSubmit = async () => {
    setError('');

    try {
      // Step 1: Create the simulation
      const sim = await createSimulation.mutateAsync({
        scenario_id: formData.scenarioId,
        agent_count: formData.agentCount,
        model_used: formData.model,
      });

      setRunId(sim.id);
      setStep(3);

      // Step 2: Run the simulation
      await runSimulation.mutateAsync(sim.id);
    } catch (err: any) {
      setError(err.detail || err.message || 'Failed to start simulation');
      setStep(2);
    }
  };

  const selectedProject = projects?.find(p => p.id === selectedProjectId);
  const selectedScenario = scenarios?.find(s => s.id === formData.scenarioId);
  const selectedPersonaTemplate = personaTemplates?.find(p => p.id === formData.personaTemplateId);
  const selectedModel = models.find(m => m.id === formData.model);

  const canProceedStep1 = selectedProjectId && formData.scenarioId;
  const canProceedStep2 = formData.agentCount >= 10 && formData.model;

  return (
    <div className="min-h-screen bg-black p-4 md:p-6">
      {/* Header */}
      <div className="mb-6 md:mb-8">
        <Link href="/dashboard/simulations">
          <Button variant="ghost" size="sm" className="text-white/60 hover:text-white hover:bg-white/5 font-mono text-[10px] md:text-xs mb-3 md:mb-4">
            <ArrowLeft className="w-3 h-3 mr-1.5 md:mr-2" />
            <span className="hidden sm:inline">BACK TO SIMULATIONS</span>
            <span className="sm:hidden">BACK</span>
          </Button>
        </Link>
        <div className="flex items-center gap-2 mb-1">
          <Play className="w-3.5 h-3.5 md:w-4 md:h-4 text-white/60" />
          <span className="text-[10px] md:text-xs font-mono text-white/40 uppercase tracking-wider">Simulation Module</span>
        </div>
        <h1 className="text-lg md:text-xl font-mono font-bold text-white">Run Simulation</h1>
        <p className="text-xs md:text-sm font-mono text-white/50 mt-1">
          Configure and execute your AI agent simulation
        </p>
      </div>

      {/* Progress Steps - Desktop */}
      <div className="hidden md:flex items-center gap-4 mb-8">
        <StepIndicator step={1} current={step} label="Select Data" />
        <div className="flex-1 h-px bg-white/10" />
        <StepIndicator step={2} current={step} label="Configure" />
        <div className="flex-1 h-px bg-white/10" />
        <StepIndicator step={3} current={step} label="Running" />
      </div>

      {/* Progress Steps - Mobile */}
      <div className="flex md:hidden items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono text-white/40">Step</span>
          <span className="text-xs font-mono font-bold text-white">{step}</span>
          <span className="text-[10px] font-mono text-white/40">of 3</span>
        </div>
        <span className="text-xs font-mono text-white">
          {step === 1 ? 'Select Data' : step === 2 ? 'Configure' : 'Running'}
        </span>
      </div>

      {/* Mobile: Dots progress indicator */}
      <div className="flex md:hidden items-center justify-center gap-2 mb-6">
        {[1, 2, 3].map((s) => (
          <div
            key={s}
            className={cn(
              'w-2 h-2 transition-colors',
              step === s
                ? 'bg-white'
                : step > s
                ? 'bg-white/50'
                : 'bg-white/20'
            )}
          />
        ))}
      </div>

      {error && (
        <div className="mb-4 md:mb-6 bg-red-500/10 border border-red-500/30 p-3 md:p-4 flex items-start md:items-center gap-2">
          <AlertCircle className="w-3.5 h-3.5 md:w-4 md:h-4 text-red-400 flex-shrink-0 mt-0.5 md:mt-0" />
          <span className="text-xs md:text-sm font-mono text-red-400">{error}</span>
        </div>
      )}

      {/* Step 1: Select Project, Scenario, Personas */}
      {step === 1 && (
        <div className="bg-white/5 border border-white/10">
          <div className="p-4 md:p-6 border-b border-white/10">
            <h2 className="font-mono text-xs md:text-sm font-bold text-white flex items-center gap-2">
              <Settings className="w-3.5 h-3.5 md:w-4 md:h-4 text-white/60" />
              SELECT SIMULATION DATA
            </h2>
            <p className="text-[10px] md:text-xs font-mono text-white/40 mt-1">
              Choose your project, scenario, and persona template
            </p>
          </div>

          <div className="p-4 md:p-6 space-y-4 md:space-y-6">
            {/* Project Selection */}
            <div>
              <label className="block text-[10px] font-mono text-white/40 uppercase mb-1.5 md:mb-2">
                <FolderKanban className="w-3 h-3 inline mr-1.5 md:mr-2" />
                Project <span className="text-red-400">*</span>
              </label>
              {projectsLoading ? (
                <div className="flex items-center gap-2 text-white/40 text-[10px] md:text-xs font-mono py-2">
                  <Loader2 className="w-3 h-3 animate-spin" />
                  Loading projects...
                </div>
              ) : !projects || projects.length === 0 ? (
                <div className="bg-yellow-500/10 border border-yellow-500/30 p-3 md:p-4">
                  <p className="text-[10px] md:text-xs font-mono text-yellow-400">
                    No projects found.{' '}
                    <Link href="/dashboard/projects/new" className="underline hover:text-yellow-300">
                      Create a project
                    </Link>{' '}
                    first.
                  </p>
                </div>
              ) : (
                <select
                  value={selectedProjectId}
                  onChange={(e) => handleProjectChange(e.target.value)}
                  className="w-full px-2.5 md:px-3 py-2 bg-black border border-white/10 text-[11px] md:text-xs font-mono text-white focus:outline-none focus:border-white/30"
                >
                  <option value="">-- Select a project --</option>
                  {projects.map((project) => (
                    <option key={project.id} value={project.id}>
                      {project.name} ({project.domain})
                    </option>
                  ))}
                </select>
              )}
            </div>

            {/* Scenario Selection */}
            <div>
              <label className="block text-[10px] font-mono text-white/40 uppercase mb-1.5 md:mb-2">
                <FileText className="w-3 h-3 inline mr-1.5 md:mr-2" />
                Scenario <span className="text-red-400">*</span>
              </label>
              {!selectedProjectId ? (
                <p className="text-[10px] md:text-xs font-mono text-white/30 py-2">Select a project first</p>
              ) : scenariosLoading ? (
                <div className="flex items-center gap-2 text-white/40 text-[10px] md:text-xs font-mono py-2">
                  <Loader2 className="w-3 h-3 animate-spin" />
                  Loading scenarios...
                </div>
              ) : !scenarios || scenarios.length === 0 ? (
                <div className="bg-yellow-500/10 border border-yellow-500/30 p-3 md:p-4">
                  <p className="text-[10px] md:text-xs font-mono text-yellow-400">
                    No scenarios in this project.{' '}
                    <Link href={`/dashboard/projects/${selectedProjectId}/scenarios/new`} className="underline hover:text-yellow-300">
                      Create a scenario
                    </Link>{' '}
                    first.
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  {scenarios.map((scenario) => (
                    <button
                      key={scenario.id}
                      type="button"
                      onClick={() => setFormData({ ...formData, scenarioId: scenario.id })}
                      className={cn(
                        'w-full flex items-start gap-3 md:gap-4 p-3 md:p-4 border text-left transition-all',
                        formData.scenarioId === scenario.id
                          ? 'border-white bg-white/10'
                          : 'border-white/10 hover:border-white/30 bg-white/5'
                      )}
                    >
                      <div className={cn(
                        'w-7 h-7 md:w-8 md:h-8 flex items-center justify-center flex-shrink-0',
                        formData.scenarioId === scenario.id ? 'bg-white/20' : 'bg-white/10'
                      )}>
                        <FileText className="w-3.5 h-3.5 md:w-4 md:h-4 text-white/60" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <h3 className="font-mono font-bold text-white text-xs md:text-sm truncate">{scenario.name}</h3>
                        <p className="text-[10px] md:text-xs font-mono text-white/40 mt-1 line-clamp-2">
                          {scenario.description || 'No description'}
                        </p>
                        <div className="flex flex-wrap gap-2 md:gap-4 mt-2 text-[10px] font-mono text-white/30">
                          <span>{scenario.population_size} agents</span>
                          <span>{scenario.questions?.length || 0} questions</span>
                          <span className={cn(
                            scenario.status === 'ready' ? 'text-green-400' : 'text-yellow-400'
                          )}>
                            {scenario.status?.toUpperCase() || 'DRAFT'}
                          </span>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Persona Template Selection */}
            <div>
              <label className="block text-[10px] font-mono text-white/40 uppercase mb-1.5 md:mb-2">
                <Users className="w-3 h-3 inline mr-1.5 md:mr-2" />
                Persona Template (Optional)
              </label>
              {personasLoading ? (
                <div className="flex items-center gap-2 text-white/40 text-[10px] md:text-xs font-mono py-2">
                  <Loader2 className="w-3 h-3 animate-spin" />
                  Loading personas...
                </div>
              ) : !personaTemplates || personaTemplates.length === 0 ? (
                <p className="text-[10px] md:text-xs font-mono text-white/30 py-2">
                  No persona templates available. AI will generate personas automatically.
                </p>
              ) : (
                <select
                  value={formData.personaTemplateId}
                  onChange={(e) => setFormData({ ...formData, personaTemplateId: e.target.value })}
                  className="w-full px-2.5 md:px-3 py-2 bg-black border border-white/10 text-[11px] md:text-xs font-mono text-white focus:outline-none focus:border-white/30"
                >
                  <option value="">-- Use AI-generated personas --</option>
                  {personaTemplates.map((template) => (
                    <option key={template.id} value={template.id}>
                      {template.name} ({template.region}) - {template.persona_count || 0} personas
                    </option>
                  ))}
                </select>
              )}
              {selectedPersonaTemplate && (
                <p className="text-[10px] font-mono text-white/30 mt-2">
                  <Sparkles className="w-3 h-3 inline mr-1" />
                  Using {selectedPersonaTemplate.persona_count || 0} pre-defined personas from &quot;{selectedPersonaTemplate.name}&quot;
                </p>
              )}
            </div>
          </div>

          <div className="p-4 md:p-6 border-t border-white/10 flex justify-end">
            <Button
              onClick={() => setStep(2)}
              disabled={!canProceedStep1}
              className="w-full sm:w-auto font-mono text-[10px] md:text-xs"
            >
              CONTINUE
              <ArrowRight className="w-3 h-3 ml-1.5 md:ml-2" />
            </Button>
          </div>
        </div>
      )}

      {/* Step 2: Configure */}
      {step === 2 && (
        <div className="bg-white/5 border border-white/10">
          <div className="p-4 md:p-6 border-b border-white/10">
            <h2 className="font-mono text-xs md:text-sm font-bold text-white flex items-center gap-2">
              <Cpu className="w-3.5 h-3.5 md:w-4 md:h-4 text-white/60" />
              CONFIGURE SIMULATION
            </h2>
            <p className="text-[10px] md:text-xs font-mono text-white/40 mt-1">
              Set the number of agents and model to use
            </p>
          </div>

          <div className="p-4 md:p-6 space-y-4 md:space-y-6">
            {/* Selected Summary */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 md:gap-3">
              <div className="bg-white/5 border border-white/10 p-3 md:p-4">
                <p className="text-[10px] font-mono text-white/40 uppercase">Project</p>
                <p className="font-mono text-white text-xs md:text-sm font-bold mt-1 truncate">{selectedProject?.name || '-'}</p>
              </div>
              <div className="bg-white/5 border border-white/10 p-3 md:p-4">
                <p className="text-[10px] font-mono text-white/40 uppercase">Scenario</p>
                <p className="font-mono text-white text-xs md:text-sm font-bold mt-1 truncate">{selectedScenario?.name || '-'}</p>
              </div>
            </div>

            {/* Agent Count */}
            <div>
              <label className="block text-[10px] font-mono text-white/40 uppercase mb-1.5 md:mb-2">
                <Users className="w-3 h-3 inline mr-1.5 md:mr-2" />
                Number of Agents
              </label>
              <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 md:gap-4">
                <input
                  type="range"
                  min="10"
                  max="1000"
                  step="10"
                  value={formData.agentCount}
                  onChange={(e) => setFormData({ ...formData, agentCount: Number(e.target.value) })}
                  className="flex-1 accent-white"
                />
                <input
                  type="number"
                  min="10"
                  max="1000"
                  value={formData.agentCount}
                  onChange={(e) => setFormData({ ...formData, agentCount: Number(e.target.value) })}
                  className="w-full sm:w-24 px-2.5 md:px-3 py-2 bg-black border border-white/10 text-[11px] md:text-xs font-mono text-white text-center focus:outline-none focus:border-white/30"
                />
              </div>
              <p className="text-[10px] font-mono text-white/30 mt-1">
                More agents = better statistical significance, but higher cost
              </p>
            </div>

            {/* Model Selection */}
            <div>
              <label className="block text-[10px] font-mono text-white/40 uppercase mb-2 md:mb-3">
                <Cpu className="w-3 h-3 inline mr-1.5 md:mr-2" />
                AI Model
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 md:gap-3">
                {models.map((model) => (
                  <button
                    key={model.id}
                    type="button"
                    onClick={() => setFormData({ ...formData, model: model.id })}
                    className={cn(
                      'flex flex-col p-3 md:p-4 border text-left transition-all',
                      formData.model === model.id
                        ? 'border-white bg-white/10'
                        : 'border-white/10 hover:border-white/30 bg-white/5'
                    )}
                  >
                    <h4 className="font-mono font-bold text-white text-xs md:text-sm">{model.name}</h4>
                    <p className="text-[10px] md:text-xs font-mono text-white/40">{model.description}</p>
                    <div className="flex gap-3 md:gap-4 mt-2 text-[10px] font-mono">
                      <span className="text-green-400">{model.cost}</span>
                      <span className="text-white/40">{model.speed}</span>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Cost Estimate */}
            <div className="bg-white/5 border border-white/20 p-3 md:p-4">
              <h4 className="font-mono text-[10px] md:text-xs font-bold text-white">ESTIMATED COST</h4>
              <p className="text-xl md:text-2xl font-mono font-bold text-white mt-1">
                ${estimateCost(formData.agentCount, formData.model)}
              </p>
              <p className="text-[10px] font-mono text-white/40 mt-1">
                Based on {formData.agentCount} agents using {selectedModel?.name}
              </p>
            </div>
          </div>

          <div className="p-4 md:p-6 border-t border-white/10 flex flex-col sm:flex-row gap-3 sm:justify-between">
            <Button variant="outline" onClick={() => setStep(1)} className="w-full sm:w-auto font-mono text-[10px] md:text-xs border-white/20 text-white/60 hover:bg-white/5">
              <ArrowLeft className="w-3 h-3 mr-1.5 md:mr-2" />
              BACK
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={createSimulation.isPending || runSimulation.isPending || !canProceedStep2}
              className="w-full sm:w-auto font-mono text-[10px] md:text-xs"
            >
              {createSimulation.isPending || runSimulation.isPending ? (
                <>
                  <Loader2 className="w-3 h-3 mr-1.5 md:mr-2 animate-spin" />
                  <span className="hidden sm:inline">STARTING...</span>
                  <span className="sm:hidden">START...</span>
                </>
              ) : (
                <>
                  <Play className="w-3 h-3 mr-1.5 md:mr-2" />
                  <span className="hidden sm:inline">RUN SIMULATION</span>
                  <span className="sm:hidden">RUN</span>
                </>
              )}
            </Button>
          </div>
        </div>
      )}

      {/* Step 3: Running */}
      {step === 3 && simulation && (
        <div className="bg-white/5 border border-white/10">
          <div className="p-4 md:p-6 border-b border-white/10">
            <h2 className="font-mono text-xs md:text-sm font-bold text-white flex items-center gap-2">
              {simulation.status === 'completed' ? (
                <CheckCircle className="w-3.5 h-3.5 md:w-4 md:h-4 text-green-400" />
              ) : simulation.status === 'failed' ? (
                <AlertCircle className="w-3.5 h-3.5 md:w-4 md:h-4 text-red-400" />
              ) : (
                <Loader2 className="w-3.5 h-3.5 md:w-4 md:h-4 text-white/60 animate-spin" />
              )}
              <span className="hidden sm:inline">
                {simulation.status === 'completed' ? 'SIMULATION COMPLETE!' :
                 simulation.status === 'failed' ? 'SIMULATION FAILED' :
                 'SIMULATION RUNNING...'}
              </span>
              <span className="sm:hidden">
                {simulation.status === 'completed' ? 'COMPLETE!' :
                 simulation.status === 'failed' ? 'FAILED' :
                 'RUNNING...'}
              </span>
            </h2>
          </div>

          <div className="p-4 md:p-6">
            {/* Progress */}
            {simulation.status === 'running' && (
              <div className="mb-4 md:mb-6">
                <div className="flex justify-between text-[10px] md:text-xs font-mono mb-2">
                  <span className="text-white/40">PROGRESS</span>
                  <span className="text-white">{simulation.progress}%</span>
                </div>
                <div className="w-full bg-white/10 h-1">
                  <div
                    className="bg-white h-1 transition-all duration-300"
                    style={{ width: `${simulation.progress}%` }}
                  />
                </div>
                <p className="text-[10px] font-mono text-white/30 mt-2">
                  Processing {simulation.agent_count} agent responses...
                </p>
              </div>
            )}

            {/* Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 md:gap-3">
              <div className="bg-white/5 border border-white/10 p-3 md:p-4 text-center">
                <p className="text-[10px] font-mono text-white/40 uppercase">Agents</p>
                <p className="text-lg md:text-xl font-mono font-bold text-white">{simulation.agent_count}</p>
              </div>
              <div className="bg-white/5 border border-white/10 p-3 md:p-4 text-center">
                <p className="text-[10px] font-mono text-white/40 uppercase">Model</p>
                <p className="text-[10px] md:text-xs font-mono text-white truncate">{simulation.model_used.split('/').pop()}</p>
              </div>
              <div className="bg-white/5 border border-white/10 p-3 md:p-4 text-center">
                <p className="text-[10px] font-mono text-white/40 uppercase">Tokens</p>
                <p className="text-lg md:text-xl font-mono font-bold text-white">{formatNumber(simulation.tokens_used)}</p>
              </div>
              <div className="bg-white/5 border border-white/10 p-3 md:p-4 text-center">
                <p className="text-[10px] font-mono text-white/40 uppercase">Cost</p>
                <p className="text-lg md:text-xl font-mono font-bold text-white">${simulation.cost_usd.toFixed(4)}</p>
              </div>
            </div>

            {/* Actions */}
            {simulation.status === 'completed' && (
              <div className="mt-4 md:mt-6 text-center">
                <Link href={`/dashboard/results/${simulation.id}`}>
                  <Button className="w-full sm:w-auto font-mono text-[10px] md:text-xs">
                    <span className="hidden sm:inline">VIEW RESULTS</span>
                    <span className="sm:hidden">RESULTS</span>
                    <ArrowRight className="w-3 h-3 ml-1.5 md:ml-2" />
                  </Button>
                </Link>
              </div>
            )}

            {simulation.status === 'failed' && (
              <div className="mt-4 md:mt-6">
                <div className="bg-red-500/10 border border-red-500/30 p-3 md:p-4 mb-3 md:mb-4">
                  <p className="text-[10px] md:text-xs font-mono text-red-400">
                    The simulation encountered an error. Please try again or contact support.
                  </p>
                </div>
                <Button variant="outline" onClick={() => setStep(2)} className="w-full sm:w-auto font-mono text-[10px] md:text-xs border-white/20 text-white/60 hover:bg-white/5">
                  <ArrowLeft className="w-3 h-3 mr-1.5 md:mr-2" />
                  TRY AGAIN
                </Button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Footer Status */}
      <div className="mt-6 md:mt-8 pt-3 md:pt-4 border-t border-white/5">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-1">
            <Terminal className="w-3 h-3" />
            <span className="hidden sm:inline">SIMULATION CREATE MODULE</span>
            <span className="sm:hidden">SIMULATION</span>
          </div>
          <span>AGENTVERSE v1.0.0</span>
        </div>
      </div>
    </div>
  );
}

function StepIndicator({ step, current, label }: { step: number; current: number; label: string }) {
  const isActive = current >= step;
  const isComplete = current > step;

  return (
    <div className="flex items-center gap-2">
      <div className={cn(
        'w-8 h-8 flex items-center justify-center text-xs font-mono',
        isComplete ? 'bg-green-500/20 text-green-400' :
        isActive ? 'bg-white text-black' :
        'bg-white/10 text-white/40'
      )}>
        {isComplete ? <CheckCircle className="w-4 h-4" /> : step}
      </div>
      <span className={cn(
        'text-xs font-mono hidden md:block',
        isActive ? 'text-white' : 'text-white/40'
      )}>
        {label}
      </span>
    </div>
  );
}

function estimateCost(agents: number, model: string): string {
  // Rough estimate: ~500 tokens per agent
  const tokensPerAgent = 500;
  const totalTokens = agents * tokensPerAgent;

  const costPerMillion: Record<string, number> = {
    'anthropic/claude-3-haiku': 0.25,
    'anthropic/claude-3.5-sonnet': 3,
    'openai/gpt-4o-mini': 0.15,
    'openai/gpt-4o': 5,
  };

  const cost = (totalTokens / 1000000) * (costPerMillion[model] || 1);
  return cost.toFixed(4);
}

function formatNumber(num: number): string {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M';
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K';
  }
  return String(num);
}
