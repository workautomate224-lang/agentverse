'use client';

/**
 * Rules & Logic Page
 * Define decision rules and behavioral patterns
 */

import { useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  ScrollText,
  Plus,
  ArrowLeft,
  ArrowRight,
  Terminal,
  GitBranch,
  Sparkles,
  FileCode,
  Library,
  Loader2,
  AlertCircle,
  CheckCircle,
  Code,
  Trash2,
  Eye,
  Search,
  Filter,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { GuidancePanel } from '@/components/pil';
import { isMvpMode } from '@/lib/feature-flags';
import { FeatureDisabled } from '@/components/mvp';

// Rule template categories
const ruleCategories = [
  {
    id: 'decision',
    name: 'Decision Rules',
    description: 'Define how agents make choices',
    icon: GitBranch,
  },
  {
    id: 'behavioral',
    name: 'Behavioral Patterns',
    description: 'Social influence and interaction rules',
    icon: Sparkles,
  },
  {
    id: 'custom',
    name: 'Custom Rules',
    description: 'Write custom logic expressions',
    icon: FileCode,
  },
];

// Sample rulesets from library (to be replaced with API data when available)
const sampleRulesets = [
  {
    id: '1',
    name: 'Consumer Behavior Rules',
    description: 'Standard rules governing consumer decision-making patterns',
    rulesCount: 24,
    status: 'active',
    category: 'Behavior',
  },
  {
    id: '2',
    name: 'Price Sensitivity Model',
    description: 'Rules for simulating price-based purchasing decisions',
    rulesCount: 18,
    status: 'active',
    category: 'Economics',
  },
  {
    id: '3',
    name: 'Brand Loyalty Factors',
    description: 'Rules determining brand switching and loyalty behavior',
    rulesCount: 31,
    status: 'draft',
    category: 'Brand',
  },
  {
    id: '4',
    name: 'Social Influence Rules',
    description: 'Rules for word-of-mouth and social proof effects',
    rulesCount: 15,
    status: 'active',
    category: 'Social',
  },
];

// Browse Library Modal
function BrowseLibraryModal({
  open,
  onOpenChange,
  onSelectRuleset,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelectRuleset: (ruleset: typeof sampleRulesets[0]) => void;
}) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRulesets, setSelectedRulesets] = useState<string[]>([]);

  // For now, using sample data. When backend endpoint is available, replace with useRulesets hook
  const rulesets = sampleRulesets;
  const isLoading = false;
  const hasEndpoint = false; // Set to true when backend endpoint is available

  const filteredRulesets = rulesets.filter((r) =>
    r.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    r.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleToggleRuleset = (rulesetId: string) => {
    setSelectedRulesets((prev) =>
      prev.includes(rulesetId)
        ? prev.filter((id) => id !== rulesetId)
        : [...prev, rulesetId]
    );
  };

  const handleAddToProject = () => {
    const selected = rulesets.filter((r) => selectedRulesets.includes(r.id));
    selected.forEach((ruleset) => onSelectRuleset(ruleset));
    onOpenChange(false);
    setSelectedRulesets([]);
    setSearchQuery('');
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="font-mono">Rulesets Library</DialogTitle>
          <DialogDescription className="font-mono">
            Browse and import pre-built rulesets for your simulation
          </DialogDescription>
        </DialogHeader>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search rulesets..."
            className="pl-10"
          />
        </div>

        <div className="flex-1 overflow-y-auto py-4 space-y-3">
          {!hasEndpoint && (
            <div className="p-3 bg-yellow-500/10 border border-yellow-500/30 text-yellow-400 text-xs font-mono mb-4">
              <AlertCircle className="w-4 h-4 inline mr-2" />
              Showing sample rulesets. Backend integration coming soon.
            </div>
          )}

          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 animate-spin text-cyan-400" />
              <span className="ml-2 text-sm font-mono text-white/60">Loading rulesets...</span>
            </div>
          ) : filteredRulesets.length > 0 ? (
            filteredRulesets.map((ruleset) => (
              <button
                key={ruleset.id}
                onClick={() => handleToggleRuleset(ruleset.id)}
                className={cn(
                  'w-full flex items-start gap-3 p-4 border transition-all text-left',
                  selectedRulesets.includes(ruleset.id)
                    ? 'bg-purple-500/10 border-purple-500/50'
                    : 'bg-white/5 border-white/10 hover:border-white/20'
                )}
              >
                <div className="w-10 h-10 bg-gradient-to-br from-orange-500 to-red-500 flex items-center justify-center flex-shrink-0">
                  <Code className="w-5 h-5 text-white" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-mono font-bold text-white truncate">
                      {ruleset.name}
                    </h3>
                    <div className="flex items-center gap-2">
                      <span
                        className={cn(
                          'text-[10px] font-mono px-2 py-0.5',
                          ruleset.status === 'active'
                            ? 'bg-green-500/20 text-green-400'
                            : 'bg-yellow-500/20 text-yellow-400'
                        )}
                      >
                        {ruleset.status}
                      </span>
                      {selectedRulesets.includes(ruleset.id) && (
                        <CheckCircle className="w-4 h-4 text-purple-400" />
                      )}
                    </div>
                  </div>
                  <p className="text-xs font-mono text-white/50 mt-1 line-clamp-2">
                    {ruleset.description}
                  </p>
                  <div className="flex items-center gap-3 mt-2 text-[10px] font-mono text-white/30">
                    <span>{ruleset.rulesCount} rules</span>
                    <span>Category: {ruleset.category}</span>
                  </div>
                </div>
              </button>
            ))
          ) : (
            <div className="text-center py-12">
              <ScrollText className="w-10 h-10 text-white/20 mx-auto mb-3" />
              <p className="text-sm font-mono text-white/40">No rulesets found</p>
            </div>
          )}
        </div>

        <DialogFooter className="border-t border-white/10 pt-4">
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleAddToProject}
            disabled={selectedRulesets.length === 0}
            className="bg-purple-500 hover:bg-purple-600 text-white"
          >
            Import {selectedRulesets.length > 0 ? `(${selectedRulesets.length})` : ''} Rulesets
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// Create Rule Modal
function CreateRuleModal({
  open,
  onOpenChange,
  category,
  onSuccess,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  category: string;
  onSuccess: (rule: { name: string; description: string; category: string; expression: string }) => void;
}) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [expression, setExpression] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Backend endpoint not available yet
  const hasEndpoint = false;

  const handleSubmit = async () => {
    if (!name.trim()) return;

    setIsSubmitting(true);
    // Simulate API call delay
    await new Promise((resolve) => setTimeout(resolve, 500));

    onSuccess({
      name: name.trim(),
      description: description.trim(),
      category,
      expression: expression.trim(),
    });

    setIsSubmitting(false);
    onOpenChange(false);
    resetForm();
  };

  const resetForm = () => {
    setName('');
    setDescription('');
    setExpression('');
  };

  const getCategoryInfo = () => {
    switch (category) {
      case 'decision':
        return {
          title: 'Create Decision Rule',
          placeholder: 'if preference.price_sensitive > 0.7 then choose_lowest_price()',
        };
      case 'behavioral':
        return {
          title: 'Create Behavioral Pattern',
          placeholder: 'influence = social_proximity * trust_score * 0.5',
        };
      case 'custom':
        return {
          title: 'Create Custom Rule',
          placeholder: 'agent.state.satisfaction = weighted_average(factors)',
        };
      default:
        return {
          title: 'Create Rule',
          placeholder: 'Enter rule expression...',
        };
    }
  };

  const categoryInfo = getCategoryInfo();

  return (
    <Dialog open={open} onOpenChange={(o) => { onOpenChange(o); if (!o) resetForm(); }}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="font-mono">{categoryInfo.title}</DialogTitle>
          <DialogDescription className="font-mono">
            Define a new rule for your simulation
          </DialogDescription>
        </DialogHeader>

        <div className="py-4 space-y-4">
          {!hasEndpoint && (
            <div className="p-3 bg-yellow-500/10 border border-yellow-500/30 text-yellow-400 text-xs font-mono">
              <AlertCircle className="w-4 h-4 inline mr-2" />
              Rules will be stored locally. Backend persistence coming soon.
            </div>
          )}

          <div>
            <label className="block text-xs font-mono text-white/40 uppercase mb-2">
              Rule Name *
            </label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Price Sensitivity Factor"
            />
          </div>

          <div>
            <label className="block text-xs font-mono text-white/40 uppercase mb-2">
              Description
            </label>
            <Input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe what this rule does..."
            />
          </div>

          <div>
            <label className="block text-xs font-mono text-white/40 uppercase mb-2">
              Rule Expression
            </label>
            <textarea
              value={expression}
              onChange={(e) => setExpression(e.target.value)}
              placeholder={categoryInfo.placeholder}
              className="w-full h-32 px-3 py-2 bg-black border border-white/20 text-white font-mono text-sm placeholder:text-white/30 focus:border-white/40 focus:outline-none resize-none"
            />
            <p className="text-[10px] font-mono text-white/30 mt-1">
              Use the rule expression syntax. Variables and functions will be validated.
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="secondary" onClick={() => { onOpenChange(false); resetForm(); }}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={!name.trim() || isSubmitting}
            className="bg-purple-500 hover:bg-purple-600 text-white"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
                Creating...
              </>
            ) : (
              'Create Rule'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// Rule Details Modal
function RuleDetailsModal({
  open,
  onOpenChange,
  rule,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  rule: { name: string; description: string; category: string; expression?: string } | null;
}) {
  if (!rule) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="font-mono">{rule.name}</DialogTitle>
          <DialogDescription className="font-mono">
            {rule.category} Rule
          </DialogDescription>
        </DialogHeader>

        <div className="py-4 space-y-4">
          <div>
            <label className="block text-xs font-mono text-white/40 uppercase mb-1">
              Description
            </label>
            <p className="text-sm font-mono text-white">
              {rule.description || 'No description'}
            </p>
          </div>

          {rule.expression && (
            <div>
              <label className="block text-xs font-mono text-white/40 uppercase mb-1">
                Expression
              </label>
              <pre className="p-3 bg-white/5 border border-white/10 text-sm font-mono text-cyan-400 overflow-x-auto">
                {rule.expression}
              </pre>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface ProjectRule {
  id: string;
  name: string;
  description: string;
  category: string;
  rulesCount?: number;
  expression?: string;
}

export default function RulesPage() {
  // MVP Mode gate - show disabled message for advanced features
  if (isMvpMode()) {
    return (
      <FeatureDisabled
        featureName="Rules & Assumptions"
        description="The rule builder for defining decision logic and behavioral patterns will be available in a future release. Personas in MVP mode use default realistic behaviors."
      />
    );
  }

  const params = useParams();
  const projectId = params.projectId as string;

  // Modal states
  const [libraryModalOpen, setLibraryModalOpen] = useState(false);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [detailsModalOpen, setDetailsModalOpen] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState('custom');
  const [selectedRule, setSelectedRule] = useState<ProjectRule | null>(null);

  // Local rules state (would be replaced with API hook when available)
  const [projectRules, setProjectRules] = useState<ProjectRule[]>([]);

  // Count rules per category
  const getRuleCount = (categoryId: string) => {
    return projectRules.filter((r) => r.category === categoryId).length;
  };

  const totalRulesCount = projectRules.reduce(
    (acc, r) => acc + (r.rulesCount || 1),
    0
  );
  const hasRules = projectRules.length > 0;

  const handleAddCategory = (categoryId: string) => {
    setSelectedCategory(categoryId);
    setCreateModalOpen(true);
  };

  const handleSelectRuleset = (ruleset: typeof sampleRulesets[0]) => {
    // Add the ruleset to project rules
    const newRule: ProjectRule = {
      id: `imported-${ruleset.id}-${Date.now()}`,
      name: ruleset.name,
      description: ruleset.description,
      category: ruleset.category.toLowerCase(),
      rulesCount: ruleset.rulesCount,
    };
    setProjectRules((prev) => [...prev, newRule]);
  };

  const handleCreateRule = (rule: { name: string; description: string; category: string; expression: string }) => {
    const newRule: ProjectRule = {
      id: `rule-${Date.now()}`,
      name: rule.name,
      description: rule.description,
      category: rule.category,
      expression: rule.expression,
      rulesCount: 1,
    };
    setProjectRules((prev) => [...prev, newRule]);
  };

  const handleViewRule = (rule: ProjectRule) => {
    setSelectedRule(rule);
    setDetailsModalOpen(true);
  };

  const handleRemoveRule = (ruleId: string) => {
    setProjectRules((prev) => prev.filter((r) => r.id !== ruleId));
  };

  return (
    <div className="min-h-screen bg-black p-4 md:p-6">
      {/* Header */}
      <div className="mb-6 md:mb-8">
        <Link href={`/p/${projectId}/overview`}>
          <Button variant="ghost" size="sm" className="mb-3 text-[10px] md:text-xs">
            <ArrowLeft className="w-3 h-3 mr-1 md:mr-2" />
            BACK TO OVERVIEW
          </Button>
        </Link>
        <div className="flex items-center gap-2 mb-1">
          <ScrollText className="w-3.5 h-3.5 md:w-4 md:h-4 text-purple-400" />
          <span className="text-[10px] md:text-xs font-mono text-white/40 uppercase tracking-wider">
            Rules & Logic
          </span>
        </div>
        <h1 className="text-lg md:text-xl font-mono font-bold text-white">Configure Rules</h1>
        <p className="text-xs md:text-sm font-mono text-white/50 mt-1">
          Define decision rules and behavioral patterns for your simulation
        </p>
      </div>

      {/* Guidance Panel (blueprint.md §7) */}
      <div className="max-w-3xl mb-6">
        <GuidancePanel
          sectionId="rules"
          projectId={projectId}
          defaultExpanded={false}
        />
      </div>

      {/* Status Banner */}
      <div
        className={cn(
          'max-w-3xl mb-6 p-4 border',
          hasRules
            ? 'bg-green-500/10 border-green-500/30'
            : 'bg-yellow-500/10 border-yellow-500/30'
        )}
      >
        <div className="flex items-center gap-2">
          {hasRules ? (
            <CheckCircle className="w-4 h-4 text-green-400" />
          ) : (
            <ScrollText className="w-4 h-4 text-yellow-400" />
          )}
          <span
            className={cn(
              'text-sm font-mono',
              hasRules ? 'text-green-400' : 'text-yellow-400'
            )}
          >
            {hasRules
              ? `${projectRules.length} ruleset(s) with ${totalRulesCount} rules configured`
              : 'No rules defined yet'}
          </span>
        </div>
        <p className="text-xs font-mono text-white/50 mt-1">
          {hasRules
            ? 'You can add more rules or proceed to the Run Center.'
            : 'Add rules to control how agents behave and make decisions.'}
        </p>
      </div>

      {/* Rule Categories */}
      <div className="max-w-3xl">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xs font-mono text-white/40 uppercase tracking-wider">Rule Categories</h2>
          <Button
            variant="outline"
            size="sm"
            className="text-xs"
            onClick={() => setLibraryModalOpen(true)}
          >
            <Library className="w-3 h-3 mr-2" />
            BROWSE LIBRARY
          </Button>
        </div>
        <div className="space-y-2">
          {ruleCategories.map((category) => {
            const Icon = category.icon;
            const count = getRuleCount(category.id);
            return (
              <div
                key={category.id}
                className="flex items-center justify-between p-4 bg-white/5 border border-white/10 hover:border-white/20 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-white/5 flex items-center justify-center">
                    <Icon className="w-5 h-5 text-purple-400" />
                  </div>
                  <div>
                    <h3 className="text-sm font-mono font-bold text-white">{category.name}</h3>
                    <p className="text-xs font-mono text-white/50">{category.description}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs font-mono text-white/40">{count} rules</span>
                  <Button
                    size="sm"
                    variant="secondary"
                    className="text-xs"
                    onClick={() => handleAddCategory(category.id)}
                  >
                    <Plus className="w-3 h-3 mr-1" />
                    ADD
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Rules Display */}
      <div className="max-w-3xl mt-8">
        {hasRules ? (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-mono text-white/40 uppercase tracking-wider">
                Project Rules ({projectRules.length})
              </h2>
            </div>
            {projectRules.map((rule) => (
              <div
                key={rule.id}
                className="flex items-center justify-between p-4 bg-white/5 border border-white/10 hover:border-white/20 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-gradient-to-br from-orange-500 to-red-500 flex items-center justify-center">
                    <Code className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h3 className="text-sm font-mono font-bold text-white">{rule.name}</h3>
                    <p className="text-xs font-mono text-white/50">
                      {rule.rulesCount || 1} rule(s) • {rule.category}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleViewRule(rule)}
                    className="text-xs"
                  >
                    <Eye className="w-3 h-3 mr-1" />
                    View
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleRemoveRule(rule.id)}
                    className="text-xs text-red-400 hover:text-red-300"
                  >
                    <Trash2 className="w-3 h-3" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="bg-white/5 border border-white/10 p-8 text-center">
            <div className="w-16 h-16 bg-white/5 flex items-center justify-center mx-auto mb-4">
              <GitBranch className="w-8 h-8 text-white/20" />
            </div>
            <h3 className="text-sm font-mono text-white/60 mb-2">Rules will appear here</h3>
            <p className="text-xs font-mono text-white/40 mb-4">
              Start by adding decision rules or importing from the library
            </p>
            <Button
              size="sm"
              className="text-xs font-mono"
              onClick={() => {
                setSelectedCategory('custom');
                setCreateModalOpen(true);
              }}
            >
              <Plus className="w-3 h-3 mr-2" />
              CREATE RULE
            </Button>
          </div>
        )}
      </div>

      {/* Navigation CTA */}
      <div className="max-w-3xl mt-8 pt-6 border-t border-white/10">
        <div className="flex items-center justify-between">
          <Link href={`/p/${projectId}/data-personas`}>
            <Button variant="ghost" className="text-xs font-mono">
              <ArrowLeft className="w-3 h-3 mr-2" />
              Back: Data & Personas
            </Button>
          </Link>
          <Link href={`/p/${projectId}/run-center`}>
            <Button
              className={cn(
                'text-xs font-mono',
                hasRules
                  ? 'bg-cyan-500 hover:bg-cyan-600 text-black'
                  : 'bg-white/10 text-white/40'
              )}
            >
              Next: Run Center
              <ArrowRight className="w-3 h-3 ml-2" />
            </Button>
          </Link>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-8 pt-4 border-t border-white/5 max-w-3xl">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-1">
            <Terminal className="w-3 h-3" />
            <span>RULES & LOGIC</span>
          </div>
          <span>AGENTVERSE v1.0</span>
        </div>
      </div>

      {/* Modals */}
      <BrowseLibraryModal
        open={libraryModalOpen}
        onOpenChange={setLibraryModalOpen}
        onSelectRuleset={handleSelectRuleset}
      />
      <CreateRuleModal
        open={createModalOpen}
        onOpenChange={setCreateModalOpen}
        category={selectedCategory}
        onSuccess={handleCreateRule}
      />
      <RuleDetailsModal
        open={detailsModalOpen}
        onOpenChange={setDetailsModalOpen}
        rule={selectedRule}
      />
    </div>
  );
}
