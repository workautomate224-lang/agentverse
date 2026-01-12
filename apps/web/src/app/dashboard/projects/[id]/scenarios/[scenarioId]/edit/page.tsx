'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  ArrowLeft,
  Save,
  Loader2,
  Terminal,
  Settings,
  AlertTriangle,
  Users,
  FileText,
  HelpCircle,
} from 'lucide-react';
import { useScenario, useUpdateScenario } from '@/hooks/useApi';
import { cn } from '@/lib/utils';
import type { Question } from '@/lib/api';

export default function ScenarioEditPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;
  const scenarioId = params.scenarioId as string;

  const { data: scenario, isLoading: scenarioLoading, error: scenarioError } = useScenario(scenarioId);
  const updateScenario = useUpdateScenario();

  const [formData, setFormData] = useState({
    name: '',
    description: '',
    context: '',
    questions: [] as Question[],
    population_size: 100,
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    if (scenario) {
      setFormData({
        name: scenario.name || '',
        description: scenario.description || '',
        context: scenario.context || '',
        questions: scenario.questions || [],
        population_size: scenario.population_size || 100,
      });
    }
  }, [scenario]);

  if (scenarioLoading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <Loader2 className="w-5 h-5 md:w-6 md:h-6 animate-spin text-white/40" />
      </div>
    );
  }

  if (scenarioError || !scenario) {
    return (
      <div className="min-h-screen bg-black p-4 md:p-6">
        <div className="bg-red-500/10 border border-red-500/30 p-4 md:p-6 text-center">
          <AlertTriangle className="w-6 h-6 md:w-8 md:h-8 text-red-400 mx-auto mb-3 md:mb-4" />
          <h2 className="text-base md:text-lg font-mono font-bold text-red-400 mb-2">SCENARIO NOT FOUND</h2>
          <p className="text-xs md:text-sm font-mono text-red-400/70 mb-3 md:mb-4">The requested scenario could not be loaded.</p>
          <Link href={`/dashboard/projects/${projectId}`}>
            <Button variant="outline" className="font-mono text-[10px] md:text-xs border-white/20 text-white/60 hover:bg-white/5">
              BACK TO PROJECT
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  const handleAddQuestion = () => {
    const newQuestion: Question = {
      id: `q-${Date.now()}`,
      text: '',
      type: 'open_ended',
      required: true,
    };
    setFormData({
      ...formData,
      questions: [...formData.questions, newQuestion],
    });
  };

  const handleRemoveQuestion = (index: number) => {
    if (formData.questions.length > 1) {
      setFormData({
        ...formData,
        questions: formData.questions.filter((_, i) => i !== index),
      });
    }
  };

  const handleQuestionChange = (index: number, value: string) => {
    const newQuestions = [...formData.questions];
    newQuestions[index] = { ...newQuestions[index], text: value };
    setFormData({ ...formData, questions: newQuestions });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess(false);

    // Filter out empty questions
    const filteredQuestions = formData.questions.filter((q) => q.text.trim() !== '');
    if (filteredQuestions.length === 0) {
      setError('At least one question is required');
      return;
    }

    try {
      await updateScenario.mutateAsync({
        scenarioId,
        data: {
          name: formData.name,
          description: formData.description || undefined,
          context: formData.context,
          questions: filteredQuestions,
          population_size: formData.population_size,
        },
      });
      setSuccess(true);
      setTimeout(() => {
        router.push(`/dashboard/projects/${projectId}`);
      }, 1000);
    } catch (err: any) {
      setError(err.detail || err.message || 'Failed to update scenario');
    }
  };

  return (
    <div className="min-h-screen bg-black p-4 md:p-6">
      {/* Header */}
      <div className="mb-6 md:mb-8">
        <Link href={`/dashboard/projects/${projectId}`}>
          <Button variant="ghost" size="sm" className="text-white/60 hover:text-white hover:bg-white/5 font-mono text-[10px] md:text-xs mb-3 md:mb-4">
            <ArrowLeft className="w-3 h-3 mr-1.5 md:mr-2" />
            <span className="hidden sm:inline">BACK TO PROJECT</span>
            <span className="sm:hidden">BACK</span>
          </Button>
        </Link>

        <div className="flex items-center gap-2 mb-1">
          <Settings className="w-3.5 h-3.5 md:w-4 md:h-4 text-white/60" />
          <span className="text-[10px] md:text-xs font-mono text-white/40 uppercase tracking-wider">Edit Scenario</span>
        </div>
        <h1 className="text-lg md:text-xl font-mono font-bold text-white truncate">{scenario.name}</h1>
        <p className="text-xs md:text-sm font-mono text-white/50 mt-1">Update scenario configuration</p>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit}>
        <div className="bg-white/5 border border-white/10 p-4 md:p-6 mb-4 md:mb-6">
          <h2 className="text-xs md:text-sm font-mono font-bold text-white uppercase mb-4 md:mb-6 flex items-center gap-2">
            <FileText className="w-3.5 h-3.5 md:w-4 md:h-4 text-white/60" />
            BASIC INFORMATION
          </h2>

          <div className="space-y-3 md:space-y-4">
            <div>
              <label className="block text-[10px] md:text-xs font-mono text-white/60 mb-1.5 md:mb-2">SCENARIO NAME *</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-2.5 md:px-3 py-2 bg-black border border-white/20 text-white font-mono text-[11px] md:text-sm focus:border-white/40 focus:outline-none"
                placeholder="Enter scenario name"
                required
              />
            </div>

            <div>
              <label className="block text-[10px] md:text-xs font-mono text-white/60 mb-1.5 md:mb-2">DESCRIPTION</label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                rows={2}
                className="w-full px-2.5 md:px-3 py-2 bg-black border border-white/20 text-white font-mono text-[11px] md:text-sm focus:border-white/40 focus:outline-none resize-none"
                placeholder="Enter scenario description"
              />
            </div>

            <div>
              <label className="block text-[10px] md:text-xs font-mono text-white/60 mb-1.5 md:mb-2">CONTEXT *</label>
              <textarea
                value={formData.context}
                onChange={(e) => setFormData({ ...formData, context: e.target.value })}
                rows={4}
                className="w-full px-2.5 md:px-3 py-2 bg-black border border-white/20 text-white font-mono text-[11px] md:text-sm focus:border-white/40 focus:outline-none resize-none"
                placeholder="Provide context for the simulation..."
                required
              />
              <p className="text-[10px] font-mono text-white/30 mt-1">Background context that personas will understand</p>
            </div>
          </div>
        </div>

        <div className="bg-white/5 border border-white/10 p-4 md:p-6 mb-4 md:mb-6">
          <h2 className="text-xs md:text-sm font-mono font-bold text-white uppercase mb-4 md:mb-6 flex items-center gap-2">
            <HelpCircle className="w-3.5 h-3.5 md:w-4 md:h-4 text-white/60" />
            QUESTIONS
          </h2>

          <div className="space-y-3">
            {formData.questions.map((question, index) => (
              <div key={question.id || index} className="flex flex-col sm:flex-row gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-[10px] font-mono text-white/40">Q{index + 1}</span>
                    <span className="text-[10px] font-mono text-white/20">({question.type})</span>
                  </div>
                  <input
                    type="text"
                    value={question.text}
                    onChange={(e) => handleQuestionChange(index, e.target.value)}
                    className="w-full px-2.5 md:px-3 py-2 bg-black border border-white/20 text-white font-mono text-[11px] md:text-sm focus:border-white/40 focus:outline-none"
                    placeholder="Enter a question..."
                  />
                </div>
                {formData.questions.length > 1 && (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => handleRemoveQuestion(index)}
                    className="border-red-500/30 text-red-400 hover:bg-red-500/10 sm:mt-5 h-8 md:h-9 text-[10px] md:text-xs"
                  >
                    Remove
                  </Button>
                )}
              </div>
            ))}
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleAddQuestion}
              className="border-white/20 text-white/60 hover:bg-white/5 font-mono text-[10px] md:text-xs w-full sm:w-auto"
            >
              + Add Question
            </Button>
          </div>
        </div>

        <div className="bg-white/5 border border-white/10 p-4 md:p-6 mb-4 md:mb-6">
          <h2 className="text-xs md:text-sm font-mono font-bold text-white uppercase mb-4 md:mb-6 flex items-center gap-2">
            <Users className="w-3.5 h-3.5 md:w-4 md:h-4 text-white/60" />
            SIMULATION SETTINGS
          </h2>

          <div>
            <label className="block text-[10px] md:text-xs font-mono text-white/60 mb-1.5 md:mb-2">POPULATION SIZE</label>
            <input
              type="number"
              value={formData.population_size}
              onChange={(e) => setFormData({ ...formData, population_size: parseInt(e.target.value) || 100 })}
              min={10}
              max={10000}
              className="w-full sm:w-48 px-2.5 md:px-3 py-2 bg-black border border-white/20 text-white font-mono text-[11px] md:text-sm focus:border-white/40 focus:outline-none"
            />
            <p className="text-[10px] font-mono text-white/30 mt-1">Number of AI personas to simulate (10-10,000)</p>
          </div>
        </div>

        {/* Error/Success */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/30 p-3 md:p-4 mb-4 md:mb-6">
            <p className="text-[10px] md:text-sm font-mono text-red-400">{error}</p>
          </div>
        )}

        {success && (
          <div className="bg-green-500/10 border border-green-500/30 p-3 md:p-4 mb-4 md:mb-6">
            <p className="text-[10px] md:text-sm font-mono text-green-400">Scenario updated successfully. Redirecting...</p>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center justify-between gap-3">
          <Link href={`/dashboard/projects/${projectId}`}>
            <Button
              type="button"
              variant="outline"
              className="font-mono text-[10px] md:text-xs border-white/20 text-white/60 hover:bg-white/5"
            >
              CANCEL
            </Button>
          </Link>
          <Button
            type="submit"
            disabled={updateScenario.isPending}
            className="font-mono text-[10px] md:text-xs"
          >
            {updateScenario.isPending ? (
              <Loader2 className="w-3 h-3 mr-1.5 md:mr-2 animate-spin" />
            ) : (
              <Save className="w-3 h-3 mr-1.5 md:mr-2" />
            )}
            <span className="hidden sm:inline">SAVE CHANGES</span>
            <span className="sm:hidden">SAVE</span>
          </Button>
        </div>
      </form>

      {/* Footer */}
      <div className="mt-6 md:mt-8 pt-3 md:pt-4 border-t border-white/5">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-1">
            <Terminal className="w-3 h-3" />
            <span className="hidden sm:inline">SCENARIO EDIT MODULE</span>
            <span className="sm:hidden">EDIT</span>
          </div>
          <span>AGENTVERSE v1.0.0</span>
        </div>
      </div>
    </div>
  );
}
