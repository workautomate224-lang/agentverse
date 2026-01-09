'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  LayoutTemplate,
  ArrowLeft,
  Plus,
  Save,
  Loader2,
  FileCode,
  Layers,
  Users,
  AlertCircle,
  Info,
  Terminal,
  ChevronDown,
  ChevronUp,
  X,
} from 'lucide-react';
import { useCreateMarketplaceTemplate, useMarketplaceCategories } from '@/hooks/useApi';
import { cn } from '@/lib/utils';

type TemplateType = 'domain' | 'rules' | 'personas';

/**
 * Create Template Page
 * Per Interaction_design.md §5.6:
 * - New Template wizard
 * - Domain, Rule Pack, or Persona Collection types
 */
export default function CreateTemplatePage() {
  const router = useRouter();

  const [step, setStep] = useState(1);
  const [templateType, setTemplateType] = useState<TemplateType>('domain');
  const [name, setName] = useState('');
  const [shortDescription, setShortDescription] = useState('');
  const [description, setDescription] = useState('');
  const [categoryId, setCategoryId] = useState<string>('');
  const [tags, setTags] = useState<string[]>([]);
  const [tagInput, setTagInput] = useState('');
  const [context, setContext] = useState('');
  const [isPremium, setIsPremium] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const { data: categories } = useMarketplaceCategories();
  const createMutation = useCreateMarketplaceTemplate();

  const handleAddTag = () => {
    const trimmedTag = tagInput.trim().toLowerCase().replace(/[^a-z0-9-]/g, '-');
    if (trimmedTag && !tags.includes(trimmedTag) && tags.length < 10) {
      setTags([...tags, trimmedTag]);
      setTagInput('');
    }
  };

  const handleRemoveTag = (tag: string) => {
    setTags(tags.filter((t) => t !== tag));
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAddTag();
    }
  };

  const canProceed = () => {
    if (step === 1) return !!templateType;
    if (step === 2) return name.length >= 3 && shortDescription.length >= 10;
    return true;
  };

  const handleCreate = () => {
    createMutation.mutate(
      {
        name,
        description: description || undefined,
        short_description: shortDescription,
        category_id: categoryId || undefined,
        tags: tags.length > 0 ? tags : undefined,
        context: context || '',
        is_premium: isPremium,
        scenario_type: templateType,
      },
      {
        onSuccess: (template) => {
          router.push(`/dashboard/templates/${template.slug}`);
        },
      }
    );
  };

  return (
    <div className="min-h-screen bg-black p-6">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <Link href="/dashboard/templates">
          <Button
            variant="outline"
            size="sm"
            className="font-mono text-xs border-white/20 text-white/60 hover:bg-white/5 hover:text-white"
          >
            <ArrowLeft className="w-3 h-3 mr-2" />
            TEMPLATES
          </Button>
        </Link>
      </div>

      <div className="max-w-2xl mx-auto">
        {/* Title */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-2 mb-2">
            <Plus className="w-4 h-4 text-cyan-400" />
            <span className="text-xs font-mono text-white/40 uppercase tracking-wider">
              Create Template
            </span>
          </div>
          <h1 className="text-xl font-mono font-bold text-white">New Template</h1>
          <p className="text-sm font-mono text-white/50 mt-1">
            Share your configuration as a reusable template
          </p>
        </div>

        {/* Progress Steps */}
        <div className="flex items-center justify-center gap-4 mb-8">
          {[1, 2, 3].map((s) => (
            <div key={s} className="flex items-center gap-2">
              <div
                className={cn(
                  'w-8 h-8 flex items-center justify-center font-mono text-sm border transition-colors',
                  step === s
                    ? 'bg-cyan-500/20 border-cyan-500 text-cyan-400'
                    : step > s
                    ? 'bg-green-500/20 border-green-500 text-green-400'
                    : 'bg-white/5 border-white/10 text-white/30'
                )}
              >
                {step > s ? '✓' : s}
              </div>
              {s < 3 && (
                <div
                  className={cn(
                    'w-12 h-px',
                    step > s ? 'bg-green-500' : 'bg-white/10'
                  )}
                />
              )}
            </div>
          ))}
        </div>

        {/* Step Content */}
        <div className="bg-white/5 border border-white/10 p-8">
          {/* Step 1: Template Type */}
          {step === 1 && (
            <div className="space-y-6">
              <div>
                <h2 className="text-sm font-mono font-bold text-white mb-2">
                  What type of template?
                </h2>
                <p className="text-xs font-mono text-white/50">
                  Choose the template type that best fits your content
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <button
                  onClick={() => setTemplateType('domain')}
                  className={cn(
                    'p-6 border text-left transition-all',
                    templateType === 'domain'
                      ? 'bg-cyan-500/10 border-cyan-500/50'
                      : 'bg-white/5 border-white/10 hover:border-white/30'
                  )}
                >
                  <LayoutTemplate
                    className={cn(
                      'w-8 h-8 mb-3',
                      templateType === 'domain' ? 'text-cyan-400' : 'text-white/40'
                    )}
                  />
                  <h3 className="text-sm font-mono font-bold text-white mb-1">
                    Domain Template
                  </h3>
                  <p className="text-xs font-mono text-white/40">
                    Pre-configured project setup with personas and rules
                  </p>
                </button>

                <button
                  onClick={() => setTemplateType('rules')}
                  className={cn(
                    'p-6 border text-left transition-all',
                    templateType === 'rules'
                      ? 'bg-purple-500/10 border-purple-500/50'
                      : 'bg-white/5 border-white/10 hover:border-white/30'
                  )}
                >
                  <FileCode
                    className={cn(
                      'w-8 h-8 mb-3',
                      templateType === 'rules' ? 'text-purple-400' : 'text-white/40'
                    )}
                  />
                  <h3 className="text-sm font-mono font-bold text-white mb-1">
                    Rule Pack
                  </h3>
                  <p className="text-xs font-mono text-white/40">
                    Society mode rules for specific domains or scenarios
                  </p>
                </button>

                <button
                  onClick={() => setTemplateType('personas')}
                  className={cn(
                    'p-6 border text-left transition-all',
                    templateType === 'personas'
                      ? 'bg-green-500/10 border-green-500/50'
                      : 'bg-white/5 border-white/10 hover:border-white/30'
                  )}
                >
                  <Users
                    className={cn(
                      'w-8 h-8 mb-3',
                      templateType === 'personas' ? 'text-green-400' : 'text-white/40'
                    )}
                  />
                  <h3 className="text-sm font-mono font-bold text-white mb-1">
                    Persona Collection
                  </h3>
                  <p className="text-xs font-mono text-white/40">
                    Curated set of personas for specific markets or segments
                  </p>
                </button>
              </div>
            </div>
          )}

          {/* Step 2: Basic Info */}
          {step === 2 && (
            <div className="space-y-6">
              <div>
                <h2 className="text-sm font-mono font-bold text-white mb-2">
                  Template Details
                </h2>
                <p className="text-xs font-mono text-white/50">
                  Provide basic information about your template
                </p>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-mono text-white/50 mb-2">
                    Name <span className="text-red-400">*</span>
                  </label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g., Healthcare Consumer Simulation"
                    className="w-full px-4 py-3 bg-white/5 border border-white/10 text-sm font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-white/30"
                    maxLength={100}
                  />
                  <p className="text-[10px] font-mono text-white/30 mt-1">
                    {name.length}/100 characters
                  </p>
                </div>

                <div>
                  <label className="block text-xs font-mono text-white/50 mb-2">
                    Short Description <span className="text-red-400">*</span>
                  </label>
                  <input
                    type="text"
                    value={shortDescription}
                    onChange={(e) => setShortDescription(e.target.value)}
                    placeholder="A brief summary of what this template provides"
                    className="w-full px-4 py-3 bg-white/5 border border-white/10 text-sm font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-white/30"
                    maxLength={200}
                  />
                  <p className="text-[10px] font-mono text-white/30 mt-1">
                    {shortDescription.length}/200 characters
                  </p>
                </div>

                <div>
                  <label className="block text-xs font-mono text-white/50 mb-2">
                    Full Description
                  </label>
                  <textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="Detailed description of the template, its use cases, and what's included..."
                    rows={5}
                    className="w-full px-4 py-3 bg-white/5 border border-white/10 text-sm font-mono text-white placeholder:text-white/30 resize-none focus:outline-none focus:border-white/30"
                    maxLength={2000}
                  />
                  <p className="text-[10px] font-mono text-white/30 mt-1">
                    {description.length}/2000 characters
                  </p>
                </div>

                <div>
                  <label className="block text-xs font-mono text-white/50 mb-2">
                    Category
                  </label>
                  <select
                    value={categoryId}
                    onChange={(e) => setCategoryId(e.target.value)}
                    className="w-full px-4 py-3 bg-white/5 border border-white/10 text-sm font-mono text-white appearance-none focus:outline-none focus:border-white/30"
                  >
                    <option value="">Select a category</option>
                    {categories?.map((cat) => (
                      <option key={cat.id} value={cat.id}>
                        {cat.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>
          )}

          {/* Step 3: Tags & Settings */}
          {step === 3 && (
            <div className="space-y-6">
              <div>
                <h2 className="text-sm font-mono font-bold text-white mb-2">
                  Tags & Settings
                </h2>
                <p className="text-xs font-mono text-white/50">
                  Add tags to help users discover your template
                </p>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-mono text-white/50 mb-2">
                    Tags (up to 10)
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={tagInput}
                      onChange={(e) => setTagInput(e.target.value)}
                      onKeyDown={handleKeyDown}
                      placeholder="Type a tag and press Enter"
                      className="flex-1 px-4 py-3 bg-white/5 border border-white/10 text-sm font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-white/30"
                      maxLength={30}
                    />
                    <Button
                      variant="outline"
                      onClick={handleAddTag}
                      disabled={!tagInput.trim() || tags.length >= 10}
                      className="font-mono text-xs border-white/20 text-white/60 hover:bg-white/5 hover:text-white"
                    >
                      ADD
                    </Button>
                  </div>
                  {tags.length > 0 && (
                    <div className="flex flex-wrap gap-2 mt-3">
                      {tags.map((tag) => (
                        <span
                          key={tag}
                          className="flex items-center gap-1 text-xs font-mono px-2 py-1 bg-white/10 text-white/60 border border-white/10"
                        >
                          #{tag}
                          <button
                            onClick={() => handleRemoveTag(tag)}
                            className="text-white/30 hover:text-white/60"
                          >
                            <X className="w-3 h-3" />
                          </button>
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {/* Advanced Settings */}
                <button
                  onClick={() => setShowAdvanced(!showAdvanced)}
                  className="flex items-center gap-2 text-xs font-mono text-white/50 hover:text-white/70"
                >
                  {showAdvanced ? (
                    <ChevronUp className="w-3 h-3" />
                  ) : (
                    <ChevronDown className="w-3 h-3" />
                  )}
                  Advanced Settings
                </button>

                {showAdvanced && (
                  <div className="space-y-4 pt-4 border-t border-white/10">
                    <div>
                      <label className="block text-xs font-mono text-white/50 mb-2">
                        Context / Setup Instructions
                      </label>
                      <textarea
                        value={context}
                        onChange={(e) => setContext(e.target.value)}
                        placeholder="Instructions for using this template..."
                        rows={3}
                        className="w-full px-4 py-3 bg-white/5 border border-white/10 text-sm font-mono text-white placeholder:text-white/30 resize-none focus:outline-none focus:border-white/30"
                      />
                    </div>

                    <div className="flex items-center gap-3">
                      <input
                        type="checkbox"
                        id="isPremium"
                        checked={isPremium}
                        onChange={(e) => setIsPremium(e.target.checked)}
                        className="w-4 h-4 accent-purple-500"
                      />
                      <label
                        htmlFor="isPremium"
                        className="text-sm font-mono text-white/60"
                      >
                        Premium Template (requires subscription)
                      </label>
                    </div>
                  </div>
                )}

                {/* Info Box */}
                <div className="flex items-start gap-3 p-4 bg-cyan-500/10 border border-cyan-500/20">
                  <Info className="w-4 h-4 text-cyan-400 flex-shrink-0 mt-0.5" />
                  <p className="text-xs font-mono text-cyan-300/80">
                    Your template will be reviewed before being published to the
                    public library. You can edit it anytime from your Templates page.
                  </p>
                </div>
              </div>

              {/* Summary */}
              <div className="border border-white/10 p-4 bg-black/30">
                <h3 className="text-xs font-mono text-white/40 uppercase tracking-wider mb-3">
                  Summary
                </h3>
                <div className="space-y-2 text-sm font-mono">
                  <div className="flex justify-between">
                    <span className="text-white/40">Type</span>
                    <span className="text-white capitalize">{templateType}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-white/40">Name</span>
                    <span className="text-white truncate max-w-[200px]">{name}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-white/40">Tags</span>
                    <span className="text-white">{tags.length} tags</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-white/40">Premium</span>
                    <span className={isPremium ? 'text-purple-400' : 'text-white/40'}>
                      {isPremium ? 'Yes' : 'No'}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Error */}
          {createMutation.isError && (
            <div className="flex items-center gap-2 p-4 bg-red-500/10 border border-red-500/20 mt-6">
              <AlertCircle className="w-4 h-4 text-red-400" />
              <p className="text-sm font-mono text-red-300">
                Failed to create template. Please try again.
              </p>
            </div>
          )}

          {/* Navigation */}
          <div className="flex items-center justify-between mt-8 pt-6 border-t border-white/10">
            <Button
              variant="ghost"
              onClick={() => setStep(Math.max(1, step - 1))}
              disabled={step === 1}
              className="font-mono text-xs text-white/50"
            >
              <ArrowLeft className="w-3 h-3 mr-2" />
              BACK
            </Button>

            {step < 3 ? (
              <Button
                onClick={() => setStep(step + 1)}
                disabled={!canProceed()}
                className="font-mono text-xs"
              >
                CONTINUE
              </Button>
            ) : (
              <Button
                onClick={handleCreate}
                disabled={!canProceed() || createMutation.isPending}
                className="font-mono text-xs"
              >
                {createMutation.isPending ? (
                  <Loader2 className="w-3 h-3 animate-spin mr-2" />
                ) : (
                  <Save className="w-3 h-3 mr-2" />
                )}
                CREATE TEMPLATE
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-8 pt-4 border-t border-white/5">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1">
              <Terminal className="w-3 h-3" />
              <span>CREATE TEMPLATE</span>
            </div>
          </div>
          <span>AGENTVERSE v1.0.0</span>
        </div>
      </div>
    </div>
  );
}
