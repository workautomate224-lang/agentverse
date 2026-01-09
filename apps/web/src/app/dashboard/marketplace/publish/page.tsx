'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  ArrowLeft,
  Upload,
  Terminal,
  FileText,
  Plus,
  X,
  Info,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import {
  useScenarios,
  useMarketplaceCategories,
  useCreateMarketplaceTemplate,
} from '@/hooks/useApi';
import { cn } from '@/lib/utils';

export default function PublishTemplatePage() {
  const router = useRouter();
  const [mode, setMode] = useState<'from-scenario' | 'new'>('from-scenario');
  const [error, setError] = useState<string | null>(null);

  const { data: scenarios, isLoading: loadingScenarios } = useScenarios();
  const { data: categories, isLoading: loadingCategories } = useMarketplaceCategories();
  const createTemplate = useCreateMarketplaceTemplate();

  // Form state
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [shortDescription, setShortDescription] = useState('');
  const [categoryId, setCategoryId] = useState('');
  const [tags, setTags] = useState<string[]>([]);
  const [tagInput, setTagInput] = useState('');
  const [selectedScenarioId, setSelectedScenarioId] = useState('');

  // For new template mode
  const [scenarioType, setScenarioType] = useState('market_research');
  const [context, setContext] = useState('');
  const [populationSize, setPopulationSize] = useState(100);

  const handleAddTag = () => {
    const trimmedTag = tagInput.trim().toLowerCase();
    if (trimmedTag && !tags.includes(trimmedTag)) {
      setTags([...tags, trimmedTag]);
      setTagInput('');
    }
  };

  const handleRemoveTag = (tagToRemove: string) => {
    setTags(tags.filter((tag) => tag !== tagToRemove));
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAddTag();
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!name.trim()) {
      setError('Template name is required');
      return;
    }

    if (mode === 'from-scenario' && !selectedScenarioId) {
      setError('Please select a scenario to publish');
      return;
    }

    if (mode === 'new' && !context.trim()) {
      setError('Context is required for new templates');
      return;
    }

    try {
      if (mode === 'from-scenario') {
        await createTemplate.mutateAsync({
          scenario_id: selectedScenarioId,
          name: name.trim(),
          description: description.trim() || undefined,
          short_description: shortDescription.trim() || undefined,
          category_id: categoryId || undefined,
          tags: tags.length > 0 ? tags : undefined,
        } as any);
      } else {
        await createTemplate.mutateAsync({
          name: name.trim(),
          description: description.trim() || undefined,
          short_description: shortDescription.trim() || undefined,
          category_id: categoryId || undefined,
          tags: tags.length > 0 ? tags : undefined,
          scenario_type: scenarioType,
          context: context.trim(),
          recommended_population_size: populationSize,
          questions: [],
          variables: {},
          demographics: {},
          model_config: {},
        });
      }
      router.push('/dashboard/marketplace/my-templates');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to publish template');
    }
  };

  return (
    <div className="min-h-screen bg-black p-6">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <Link href="/dashboard/marketplace">
          <button className="p-2 hover:bg-white/5 transition-colors">
            <ArrowLeft className="w-4 h-4 text-white/60" />
          </button>
        </Link>
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-white/40" />
          <span className="text-xs font-mono text-white/40 uppercase tracking-wider">
            Marketplace / Publish
          </span>
        </div>
      </div>

      <div className="max-w-2xl mx-auto">
        <div className="mb-8">
          <h1 className="text-xl font-mono font-bold text-white mb-2">
            Publish Template
          </h1>
          <p className="text-sm font-mono text-white/50">
            Share your scenario as a reusable template in the marketplace
          </p>
        </div>

        {/* Mode Selection */}
        <div className="mb-6">
          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={() => setMode('from-scenario')}
              className={cn(
                'p-4 border text-left transition-colors',
                mode === 'from-scenario'
                  ? 'border-white/40 bg-white/10'
                  : 'border-white/10 hover:bg-white/5'
              )}
            >
              <FileText className="w-5 h-5 text-white/60 mb-2" />
              <h3 className="text-sm font-mono font-medium text-white mb-1">
                From Scenario
              </h3>
              <p className="text-xs font-mono text-white/40">
                Publish an existing scenario
              </p>
            </button>
            <button
              onClick={() => setMode('new')}
              className={cn(
                'p-4 border text-left transition-colors',
                mode === 'new'
                  ? 'border-white/40 bg-white/10'
                  : 'border-white/10 hover:bg-white/5'
              )}
            >
              <Plus className="w-5 h-5 text-white/60 mb-2" />
              <h3 className="text-sm font-mono font-medium text-white mb-1">
                New Template
              </h3>
              <p className="text-xs font-mono text-white/40">
                Create from scratch
              </p>
            </button>
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Scenario Selection (from-scenario mode) */}
          {mode === 'from-scenario' && (
            <div className="bg-white/5 border border-white/10 p-6">
              <label className="block text-xs font-mono text-white/60 uppercase tracking-wider mb-3">
                Select Scenario *
              </label>
              {loadingScenarios ? (
                <div className="flex items-center justify-center py-4">
                  <Loader2 className="w-4 h-4 animate-spin text-white/40" />
                </div>
              ) : scenarios && scenarios.length > 0 ? (
                <select
                  value={selectedScenarioId}
                  onChange={(e) => {
                    setSelectedScenarioId(e.target.value);
                    const scenario = scenarios.find((s) => s.id === e.target.value);
                    if (scenario && !name) {
                      setName(scenario.name);
                      setDescription(scenario.description || '');
                    }
                  }}
                  className="w-full px-3 py-2 bg-white/5 border border-white/10 text-sm font-mono text-white focus:outline-none focus:border-white/30"
                  required
                >
                  <option value="">Select a scenario...</option>
                  {scenarios.map((scenario) => (
                    <option key={scenario.id} value={scenario.id}>
                      {scenario.name} ({scenario.scenario_type})
                    </option>
                  ))}
                </select>
              ) : (
                <div className="p-4 bg-yellow-500/10 border border-yellow-500/30 text-yellow-400">
                  <div className="flex items-start gap-2">
                    <Info className="w-4 h-4 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-sm font-mono font-medium">
                        No scenarios available
                      </p>
                      <p className="text-xs font-mono mt-1 opacity-80">
                        Create a scenario first to publish it as a template.
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Template Details */}
          <div className="bg-white/5 border border-white/10 p-6 space-y-4">
            <h2 className="text-xs font-mono text-white/60 uppercase tracking-wider mb-4">
              Template Details
            </h2>

            {/* Name */}
            <div>
              <label className="block text-xs font-mono text-white/60 mb-2">
                Template Name *
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Enter a descriptive name"
                className="w-full px-3 py-2 bg-white/5 border border-white/10 text-sm font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-white/30"
                required
              />
            </div>

            {/* Short Description */}
            <div>
              <label className="block text-xs font-mono text-white/60 mb-2">
                Short Description
                <span className="text-white/30 ml-1">(max 500 chars)</span>
              </label>
              <textarea
                value={shortDescription}
                onChange={(e) => setShortDescription(e.target.value.slice(0, 500))}
                placeholder="Brief summary for search results"
                rows={2}
                className="w-full px-3 py-2 bg-white/5 border border-white/10 text-sm font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-white/30 resize-none"
              />
              <p className="text-[10px] font-mono text-white/30 text-right mt-1">
                {shortDescription.length}/500
              </p>
            </div>

            {/* Full Description */}
            <div>
              <label className="block text-xs font-mono text-white/60 mb-2">
                Full Description
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Detailed description of your template"
                rows={4}
                className="w-full px-3 py-2 bg-white/5 border border-white/10 text-sm font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-white/30 resize-none"
              />
            </div>

            {/* Category */}
            <div>
              <label className="block text-xs font-mono text-white/60 mb-2">
                Category
              </label>
              <select
                value={categoryId}
                onChange={(e) => setCategoryId(e.target.value)}
                className="w-full px-3 py-2 bg-white/5 border border-white/10 text-sm font-mono text-white focus:outline-none focus:border-white/30"
              >
                <option value="">Select category (optional)</option>
                {categories?.map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Tags */}
            <div>
              <label className="block text-xs font-mono text-white/60 mb-2">
                Tags
              </label>
              <div className="flex flex-wrap gap-2 mb-2">
                {tags.map((tag) => (
                  <span
                    key={tag}
                    className="inline-flex items-center gap-1 px-2 py-1 bg-white/10 text-xs font-mono text-white/60"
                  >
                    {tag}
                    <button type="button" onClick={() => handleRemoveTag(tag)}>
                      <X className="w-3 h-3 hover:text-white" />
                    </button>
                  </span>
                ))}
              </div>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Add tag and press Enter"
                  className="flex-1 px-3 py-2 bg-white/5 border border-white/10 text-sm font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-white/30"
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleAddTag}
                  className="font-mono border-white/20 text-white/60 hover:bg-white/5 hover:text-white"
                >
                  <Plus className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </div>

          {/* New Template Fields */}
          {mode === 'new' && (
            <div className="bg-white/5 border border-white/10 p-6 space-y-4">
              <h2 className="text-xs font-mono text-white/60 uppercase tracking-wider mb-4">
                Scenario Configuration
              </h2>

              <div>
                <label className="block text-xs font-mono text-white/60 mb-2">
                  Scenario Type *
                </label>
                <select
                  value={scenarioType}
                  onChange={(e) => setScenarioType(e.target.value)}
                  className="w-full px-3 py-2 bg-white/5 border border-white/10 text-sm font-mono text-white focus:outline-none focus:border-white/30"
                >
                  <option value="market_research">Market Research</option>
                  <option value="product_feedback">Product Feedback</option>
                  <option value="consumer_behavior">Consumer Behavior</option>
                  <option value="political_polling">Political Polling</option>
                  <option value="social_research">Social Research</option>
                  <option value="ad_testing">Ad Testing</option>
                  <option value="brand_perception">Brand Perception</option>
                  <option value="custom">Custom</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-mono text-white/60 mb-2">
                  Context / Background *
                </label>
                <textarea
                  value={context}
                  onChange={(e) => setContext(e.target.value)}
                  placeholder="Provide context that AI agents will use when responding..."
                  rows={6}
                  className="w-full px-3 py-2 bg-white/5 border border-white/10 text-sm font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-white/30 resize-none"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-mono text-white/60 mb-2">
                  Recommended Population Size
                </label>
                <input
                  type="number"
                  value={populationSize}
                  onChange={(e) =>
                    setPopulationSize(Math.max(1, parseInt(e.target.value) || 100))
                  }
                  min="1"
                  max="10000"
                  className="w-full px-3 py-2 bg-white/5 border border-white/10 text-sm font-mono text-white focus:outline-none focus:border-white/30"
                />
              </div>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="flex items-center gap-2 p-4 bg-red-500/10 border border-red-500/30 text-red-400">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span className="text-sm font-mono">{error}</span>
            </div>
          )}

          {/* Submit */}
          <div className="flex justify-end gap-3 pt-4 border-t border-white/10">
            <Link href="/dashboard/marketplace">
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="font-mono border-white/20 text-white/60 hover:bg-white/5 hover:text-white"
              >
                CANCEL
              </Button>
            </Link>
            <Button type="submit" size="sm" disabled={createTemplate.isPending}>
              {createTemplate.isPending ? (
                <>
                  <Loader2 className="w-3 h-3 mr-2 animate-spin" />
                  PUBLISHING...
                </>
              ) : (
                <>
                  <Upload className="w-3 h-3 mr-2" />
                  PUBLISH TEMPLATE
                </>
              )}
            </Button>
          </div>
        </form>
      </div>

      {/* Footer */}
      <div className="mt-8 pt-4 border-t border-white/5">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1">
              <Terminal className="w-3 h-3" />
              <span>MARKETPLACE MODULE</span>
            </div>
          </div>
          <span>AGENTVERSE v1.0.0</span>
        </div>
      </div>
    </div>
  );
}
