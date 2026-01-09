'use client';

import { useState } from 'react';
import { X, Plus, Upload, Info, AlertCircle } from 'lucide-react';
import { MarketplaceCategory, Scenario, MarketplaceTemplateCreate } from '@/lib/api';

interface PublishTemplateFormProps {
  scenarios: Scenario[];
  categories: MarketplaceCategory[];
  onPublish: (data: MarketplaceTemplateCreate | { scenario_id: string; name: string; description?: string; short_description?: string; category_id?: string; tags?: string[] }) => Promise<void>;
  isLoading?: boolean;
  mode: 'new' | 'from-scenario';
}

export function PublishTemplateForm({
  scenarios,
  categories,
  onPublish,
  isLoading = false,
  mode,
}: PublishTemplateFormProps) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [shortDescription, setShortDescription] = useState('');
  const [categoryId, setCategoryId] = useState('');
  const [tags, setTags] = useState<string[]>([]);
  const [tagInput, setTagInput] = useState('');
  const [selectedScenarioId, setSelectedScenarioId] = useState('');
  const [error, setError] = useState<string | null>(null);

  // For new template mode (not from scenario)
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
        await onPublish({
          scenario_id: selectedScenarioId,
          name: name.trim(),
          description: description.trim() || undefined,
          short_description: shortDescription.trim() || undefined,
          category_id: categoryId || undefined,
          tags: tags.length > 0 ? tags : undefined,
        });
      } else {
        await onPublish({
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
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to publish template');
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Mode-specific: Scenario selection */}
      {mode === 'from-scenario' && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Select Scenario to Publish *
          </label>
          {scenarios.length === 0 ? (
            <div className="p-4 bg-yellow-50 text-yellow-700 rounded-lg flex items-start gap-2">
              <Info className="w-5 h-5 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium">No scenarios available</p>
                <p className="text-sm mt-1">
                  Create a scenario first to publish it as a template.
                </p>
              </div>
            </div>
          ) : (
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
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-100 focus:border-primary-500"
              required
            >
              <option value="">Select a scenario...</option>
              {scenarios.map((scenario) => (
                <option key={scenario.id} value={scenario.id}>
                  {scenario.name} ({scenario.scenario_type})
                </option>
              ))}
            </select>
          )}
        </div>
      )}

      {/* Template name */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Template Name *
        </label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Enter a descriptive name for your template"
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-100 focus:border-primary-500"
          required
        />
      </div>

      {/* Short description */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Short Description
          <span className="text-gray-400 font-normal ml-1">(max 500 characters)</span>
        </label>
        <textarea
          value={shortDescription}
          onChange={(e) => setShortDescription(e.target.value.slice(0, 500))}
          placeholder="Brief summary that appears in search results"
          rows={2}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-100 focus:border-primary-500 resize-none"
        />
        <p className="mt-1 text-xs text-gray-500 text-right">
          {shortDescription.length}/500
        </p>
      </div>

      {/* Full description */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Full Description
        </label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Detailed description of your template, its use cases, and methodology"
          rows={4}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-100 focus:border-primary-500 resize-none"
        />
      </div>

      {/* Mode-specific: New template fields */}
      {mode === 'new' && (
        <>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Scenario Type *
            </label>
            <select
              value={scenarioType}
              onChange={(e) => setScenarioType(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-100 focus:border-primary-500"
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
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Context / Background *
            </label>
            <textarea
              value={context}
              onChange={(e) => setContext(e.target.value)}
              placeholder="Provide background context that AI agents will use when responding..."
              rows={6}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-100 focus:border-primary-500 resize-none"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Recommended Population Size
            </label>
            <input
              type="number"
              value={populationSize}
              onChange={(e) => setPopulationSize(Math.max(1, parseInt(e.target.value) || 100))}
              min="1"
              max="10000"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-100 focus:border-primary-500"
            />
          </div>
        </>
      )}

      {/* Category */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Category
        </label>
        <select
          value={categoryId}
          onChange={(e) => setCategoryId(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-100 focus:border-primary-500"
        >
          <option value="">Select a category (optional)</option>
          {categories.map((category) => (
            <option key={category.id} value={category.id}>
              {category.name}
            </option>
          ))}
        </select>
      </div>

      {/* Tags */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Tags
        </label>
        <div className="flex flex-wrap gap-2 mb-2">
          {tags.map((tag) => (
            <span
              key={tag}
              className="inline-flex items-center gap-1 px-2 py-1 bg-primary-100 text-primary-700 text-sm rounded-lg"
            >
              {tag}
              <button
                type="button"
                onClick={() => handleRemoveTag(tag)}
                className="hover:text-primary-900"
              >
                <X className="w-3 h-3" />
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
            placeholder="Add a tag and press Enter"
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-100 focus:border-primary-500"
          />
          <button
            type="button"
            onClick={handleAddTag}
            className="px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
          >
            <Plus className="w-5 h-5 text-gray-600" />
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 p-3 bg-red-50 text-red-700 rounded-lg">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span className="text-sm">{error}</span>
        </div>
      )}

      {/* Submit button */}
      <div className="flex justify-end pt-4 border-t border-gray-200">
        <button
          type="submit"
          disabled={isLoading}
          className="inline-flex items-center gap-2 px-6 py-2.5 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? (
            'Publishing...'
          ) : (
            <>
              <Upload className="w-4 h-4" />
              Publish Template
            </>
          )}
        </button>
      </div>
    </form>
  );
}

export default PublishTemplateForm;
