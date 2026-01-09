'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  ArrowLeft,
  ArrowRight,
  TrendingUp,
  Lightbulb,
  Users,
  Check,
  Loader2,
  Globe,
  Target,
  Settings,
  FileText,
  ChevronDown,
  Plus,
  X,
  Info,
  Terminal,
  Package,
  Sparkles,
  Eye,
  Activity,
  Gem,
} from 'lucide-react';
import { useCreateProduct, useProjects, useProductTypes, useGenerateAIContent } from '@/hooks/useApi';
import { toast } from '@/hooks/use-toast';
import type { ProductCreate, TargetMarket } from '@/lib/api';
import { cn } from '@/lib/utils';

// Product type to TypeScript type mapping
type ProductTypeKey = 'predict' | 'insight' | 'simulate' | 'oracle' | 'pulse' | 'prism';

const productTypeConfig: Record<ProductTypeKey, {
  name: string;
  icon: typeof TrendingUp;
  description: string;
  subTypes: { value: string; name: string; description: string }[];
  category?: 'basic' | 'advanced';
  badge?: string;
}> = {
  // === Standard Products ===
  predict: {
    name: 'Predict',
    icon: TrendingUp,
    description: 'Quantitative predictions with statistical confidence intervals',
    category: 'basic',
    subTypes: [
      { value: 'election', name: 'Election', description: 'Electoral outcome predictions' },
      { value: 'market_adoption', name: 'Market Adoption', description: 'Product/service adoption rates' },
      { value: 'product_launch', name: 'Product Launch', description: 'Launch success predictions' },
      { value: 'campaign_response', name: 'Campaign Response', description: 'Marketing campaign outcomes' },
      { value: 'brand_perception', name: 'Brand Perception', description: 'Brand awareness & sentiment' },
      { value: 'price_sensitivity', name: 'Price Sensitivity', description: 'Price elasticity analysis' },
      { value: 'feature_preference', name: 'Feature Preference', description: 'Feature priority ranking' },
      { value: 'purchase_intent', name: 'Purchase Intent', description: 'Buying likelihood scores' },
      { value: 'churn_risk', name: 'Churn Risk', description: 'Customer churn predictions' },
      { value: 'trend_forecast', name: 'Trend Forecast', description: 'Market trend predictions' },
      { value: 'custom', name: 'Custom', description: 'Custom prediction study' },
    ],
  },
  insight: {
    name: 'Insight',
    icon: Lightbulb,
    description: 'Qualitative deep-dive into motivations and behaviors',
    category: 'basic',
    subTypes: [
      { value: 'motivation_analysis', name: 'Motivation Analysis', description: 'Understanding why people act' },
      { value: 'decision_journey', name: 'Decision Journey', description: 'Purchase decision mapping' },
      { value: 'barrier_identification', name: 'Barrier Identification', description: 'Finding blockers & friction' },
      { value: 'value_driver', name: 'Value Driver', description: 'What matters most to users' },
      { value: 'persona_clustering', name: 'Persona Clustering', description: 'Segment identification' },
      { value: 'sentiment_analysis', name: 'Sentiment Analysis', description: 'Emotional response mapping' },
      { value: 'competitive_perception', name: 'Competitive Perception', description: 'Competitive positioning' },
      { value: 'need_gap_analysis', name: 'Need Gap Analysis', description: 'Unmet needs discovery' },
      { value: 'behavioral_pattern', name: 'Behavioral Pattern', description: 'Usage pattern analysis' },
      { value: 'cultural_context', name: 'Cultural Context', description: 'Cultural influence factors' },
      { value: 'custom', name: 'Custom', description: 'Custom insight study' },
    ],
  },
  simulate: {
    name: 'Simulate',
    icon: Users,
    description: 'Real-time interactive simulations with agent dynamics',
    category: 'basic',
    subTypes: [
      { value: 'focus_group', name: 'Focus Group', description: 'Simulated group discussion' },
      { value: 'product_test', name: 'Product Test', description: 'Product feedback simulation' },
      { value: 'campaign_test', name: 'Campaign Test', description: 'Marketing campaign testing' },
      { value: 'concept_test', name: 'Concept Test', description: 'Concept validation study' },
      { value: 'price_test', name: 'Price Test', description: 'Pricing strategy testing' },
      { value: 'message_test', name: 'Message Test', description: 'Messaging effectiveness' },
      { value: 'ux_test', name: 'UX Test', description: 'User experience testing' },
      { value: 'market_entry', name: 'Market Entry', description: 'New market simulation' },
      { value: 'competitive_scenario', name: 'Competitive Scenario', description: 'Competitive response modeling' },
      { value: 'crisis_response', name: 'Crisis Response', description: 'Crisis management testing' },
      { value: 'custom', name: 'Custom', description: 'Custom simulation' },
    ],
  },
  // === Advanced AI Models - Enterprise Intelligence Suite ===
  oracle: {
    name: 'ORACLE',
    icon: Eye,
    description: 'Market Intelligence & Consumer Prediction for corporate research',
    category: 'advanced',
    badge: 'ENTERPRISE',
    subTypes: [
      { value: 'market_share', name: 'Market Share', description: 'Market share prediction & tracking' },
      { value: 'consumer_decision', name: 'Consumer Decision', description: 'Purchase decision modeling' },
      { value: 'brand_switching', name: 'Brand Switching', description: 'Brand loyalty analysis' },
      { value: 'purchase_behavior', name: 'Purchase Behavior', description: 'Buying behavior prediction' },
      { value: 'segment_discovery', name: 'Segment Discovery', description: 'AI-powered segmentation' },
      { value: 'price_elasticity', name: 'Price Elasticity', description: 'Price sensitivity modeling' },
      { value: 'product_positioning', name: 'Product Positioning', description: 'Optimal positioning analysis' },
      { value: 'competitive_intel', name: 'Competitive Intel', description: 'Competitive intelligence' },
      { value: 'demand_forecast', name: 'Demand Forecast', description: 'Demand prediction' },
      { value: 'customer_lifetime', name: 'Customer Lifetime', description: 'CLV prediction' },
      { value: 'channel_preference', name: 'Channel Preference', description: 'Channel optimization' },
      { value: 'custom', name: 'Custom', description: 'Custom market intelligence' },
    ],
  },
  pulse: {
    name: 'PULSE',
    icon: Activity,
    description: 'Dynamic Political & Election Simulation with real-time tracking',
    category: 'advanced',
    badge: 'POLITICAL',
    subTypes: [
      { value: 'election_forecast', name: 'Election Forecast', description: 'Election outcome prediction' },
      { value: 'voter_behavior', name: 'Voter Behavior', description: 'Voter pattern analysis' },
      { value: 'campaign_impact', name: 'Campaign Impact', description: 'Campaign effectiveness' },
      { value: 'swing_voter', name: 'Swing Voter', description: 'Swing voter identification' },
      { value: 'turnout_prediction', name: 'Turnout Prediction', description: 'Voter turnout modeling' },
      { value: 'policy_response', name: 'Policy Response', description: 'Policy impact simulation' },
      { value: 'debate_impact', name: 'Debate Impact', description: 'Debate effect analysis' },
      { value: 'demographic_shift', name: 'Demographic Shift', description: 'Demographic voting trends' },
      { value: 'issue_salience', name: 'Issue Salience', description: 'Issue importance ranking' },
      { value: 'coalition_analysis', name: 'Coalition Analysis', description: 'Coalition building' },
      { value: 'real_time_tracking', name: 'Real-Time Tracking', description: 'Live sentiment tracking' },
      { value: 'custom', name: 'Custom', description: 'Custom political analysis' },
    ],
  },
  prism: {
    name: 'PRISM',
    icon: Gem,
    description: 'Policy Impact & Public Sector Analytics for government research',
    category: 'advanced',
    badge: 'PUBLIC SECTOR',
    subTypes: [
      { value: 'policy_impact', name: 'Policy Impact', description: 'Policy effect analysis' },
      { value: 'crisis_response', name: 'Crisis Response', description: 'Crisis management simulation' },
      { value: 'public_opinion', name: 'Public Opinion', description: 'Public sentiment analysis' },
      { value: 'stakeholder_mapping', name: 'Stakeholder Mapping', description: 'Stakeholder analysis' },
      { value: 'scenario_planning', name: 'Scenario Planning', description: 'What-if scenarios' },
      { value: 'regulatory_impact', name: 'Regulatory Impact', description: 'Regulation effect modeling' },
      { value: 'social_program', name: 'Social Program', description: 'Program effectiveness' },
      { value: 'infrastructure_impact', name: 'Infrastructure Impact', description: 'Infrastructure analysis' },
      { value: 'community_response', name: 'Community Response', description: 'Community feedback' },
      { value: 'cultural_sensitivity', name: 'Cultural Sensitivity', description: 'Cultural impact analysis' },
      { value: 'historical_parallel', name: 'Historical Parallel', description: 'Historical comparison' },
      { value: 'custom', name: 'Custom', description: 'Custom public sector analysis' },
    ],
  },
};

const regions = [
  { value: 'north_america', name: 'North America' },
  { value: 'europe', name: 'Europe' },
  { value: 'asia_pacific', name: 'Asia Pacific' },
  { value: 'latin_america', name: 'Latin America' },
  { value: 'middle_east', name: 'Middle East' },
  { value: 'africa', name: 'Africa' },
];

const countries = [
  { value: 'USA', region: 'north_america', name: 'United States' },
  { value: 'Canada', region: 'north_america', name: 'Canada' },
  { value: 'Mexico', region: 'latin_america', name: 'Mexico' },
  { value: 'UK', region: 'europe', name: 'United Kingdom' },
  { value: 'Germany', region: 'europe', name: 'Germany' },
  { value: 'France', region: 'europe', name: 'France' },
  { value: 'Spain', region: 'europe', name: 'Spain' },
  { value: 'Italy', region: 'europe', name: 'Italy' },
  { value: 'China', region: 'asia_pacific', name: 'China' },
  { value: 'Japan', region: 'asia_pacific', name: 'Japan' },
  { value: 'India', region: 'asia_pacific', name: 'India' },
  { value: 'Australia', region: 'asia_pacific', name: 'Australia' },
  { value: 'Singapore', region: 'asia_pacific', name: 'Singapore' },
  { value: 'Brazil', region: 'latin_america', name: 'Brazil' },
  { value: 'UAE', region: 'middle_east', name: 'UAE' },
  { value: 'South Africa', region: 'africa', name: 'South Africa' },
];

const ageGroups = [
  { value: '18-24', name: '18-24' },
  { value: '25-34', name: '25-34' },
  { value: '35-44', name: '35-44' },
  { value: '45-54', name: '45-54' },
  { value: '55-64', name: '55-64' },
  { value: '65+', name: '65+' },
];

const incomeGroups = [
  { value: 'low', name: 'Low Income' },
  { value: 'middle', name: 'Middle Income' },
  { value: 'upper_middle', name: 'Upper Middle' },
  { value: 'high', name: 'High Income' },
];

type Step = 'type' | 'details' | 'target' | 'config' | 'review';

export default function NewProductPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const createProduct = useCreateProduct();
  const generateContent = useGenerateAIContent();
  const { data: projects, isLoading: projectsLoading } = useProjects();

  const [currentStep, setCurrentStep] = useState<Step>('type');
  const [productType, setProductType] = useState<ProductTypeKey | null>(
    (searchParams.get('type') as ProductTypeKey) || null
  );
  const [subType, setSubType] = useState<string | null>(null);

  // Form state
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [projectId, setProjectId] = useState<string>('');
  const [personaCount, setPersonaCount] = useState(100);
  const [confidenceTarget, setConfidenceTarget] = useState(0.9);

  // Target market
  const [selectedRegions, setSelectedRegions] = useState<string[]>([]);
  const [selectedCountries, setSelectedCountries] = useState<string[]>([]);
  const [selectedAgeGroups, setSelectedAgeGroups] = useState<string[]>([]);
  const [selectedIncomeGroups, setSelectedIncomeGroups] = useState<string[]>([]);
  const [genderSplit, setGenderSplit] = useState({ male: 50, female: 50 });

  // Configuration (type-specific)
  const [configuration, setConfiguration] = useState<Record<string, unknown>>({});
  const [stimulusMaterials, setStimulusMaterials] = useState<Record<string, unknown>>({});

  // Auto-set type from URL
  useEffect(() => {
    const typeFromUrl = searchParams.get('type') as ProductTypeKey;
    if (typeFromUrl && productTypeConfig[typeFromUrl]) {
      setProductType(typeFromUrl);
      setCurrentStep('details');
    }
  }, [searchParams]);

  // Auto-select first project
  useEffect(() => {
    if (projects && projects.length > 0 && !projectId) {
      setProjectId(projects[0].id);
    }
  }, [projects, projectId]);

  const steps: { id: Step; name: string; icon: typeof Settings }[] = [
    { id: 'type', name: 'Type', icon: Target },
    { id: 'details', name: 'Details', icon: FileText },
    { id: 'target', name: 'Target', icon: Globe },
    { id: 'config', name: 'Config', icon: Settings },
    { id: 'review', name: 'Review', icon: Check },
  ];

  const currentStepIndex = steps.findIndex((s) => s.id === currentStep);

  const canProceed = () => {
    switch (currentStep) {
      case 'type':
        return productType !== null;
      case 'details':
        return name.trim() !== '' && projectId !== '' && subType !== null;
      case 'target':
        return selectedRegions.length > 0 || selectedCountries.length > 0;
      case 'config':
        return personaCount >= 1 && personaCount <= 10000;
      case 'review':
        return true;
      default:
        return false;
    }
  };

  const handleNext = () => {
    const stepOrder: Step[] = ['type', 'details', 'target', 'config', 'review'];
    const currentIndex = stepOrder.indexOf(currentStep);
    if (currentIndex < stepOrder.length - 1) {
      setCurrentStep(stepOrder[currentIndex + 1]);
    }
  };

  const handleBack = () => {
    const stepOrder: Step[] = ['type', 'details', 'target', 'config', 'review'];
    const currentIndex = stepOrder.indexOf(currentStep);
    if (currentIndex > 0) {
      setCurrentStep(stepOrder[currentIndex - 1]);
    }
  };

  const handleSubmit = async () => {
    if (!productType || !projectId) return;

    const targetMarket: TargetMarket = {
      regions: selectedRegions,
      countries: selectedCountries,
      demographics: {
        age_groups: selectedAgeGroups,
        income_groups: selectedIncomeGroups,
        gender_split: genderSplit,
      },
      sample_size: personaCount,
    };

    const productData: ProductCreate = {
      project_id: projectId,
      name,
      description: description || undefined,
      product_type: productType,
      sub_type: subType || undefined,
      target_market: targetMarket,
      persona_count: personaCount,
      persona_source: 'ai_generated',
      configuration,
      stimulus_materials: Object.keys(stimulusMaterials).length > 0 ? stimulusMaterials : undefined,
      confidence_target: confidenceTarget,
    };

    try {
      const product = await createProduct.mutateAsync(productData);
      router.push(`/dashboard/products/${product.id}`);
    } catch {
      // Create failed - mutation error is handled by react-query
    }
  };

  const typeConfig = productType ? productTypeConfig[productType] : null;
  const Icon = typeConfig?.icon || Target;

  return (
    <div className="min-h-screen bg-black">
      {/* Header */}
      <div className="bg-black border-b border-white/10 sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link href="/dashboard/products" className="p-2 hover:bg-white/5 text-white/60 hover:text-white">
                <ArrowLeft className="w-5 h-5" />
              </Link>
              <div>
                <div className="flex items-center gap-2">
                  <Package className="w-4 h-4 text-white/60" />
                  <span className="text-xs font-mono text-white/40 uppercase tracking-wider">Product Module</span>
                </div>
                <h1 className="text-xl font-mono font-bold text-white">Create New Product</h1>
              </div>
            </div>

            {/* Progress Steps */}
            <div className="hidden md:flex items-center gap-2">
              {steps.map((step, index) => (
                <div key={step.id} className="flex items-center">
                  <button
                    onClick={() => index <= currentStepIndex && setCurrentStep(step.id)}
                    disabled={index > currentStepIndex}
                    className={cn(
                      'flex items-center gap-2 px-3 py-1.5 text-xs font-mono transition-colors',
                      step.id === currentStep
                        ? 'bg-white text-black'
                        : index < currentStepIndex
                        ? 'bg-white/20 text-white hover:bg-white/30'
                        : 'bg-white/5 text-white/30'
                    )}
                  >
                    {index < currentStepIndex ? (
                      <Check className="w-3 h-3" />
                    ) : (
                      <span className="w-4 h-4 flex items-center justify-center text-[10px]">
                        {index + 1}
                      </span>
                    )}
                    <span className="hidden lg:inline uppercase">{step.name}</span>
                  </button>
                  {index < steps.length - 1 && (
                    <ChevronDown className="w-3 h-3 text-white/20 rotate-[-90deg] mx-1" />
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-5xl mx-auto px-8 py-8">
        {/* Step 1: Choose Type */}
        {currentStep === 'type' && (
          <div>
            <h2 className="text-sm font-mono font-bold text-white mb-2 uppercase">Choose Product Type</h2>
            <p className="text-xs font-mono text-white/40 mb-6">
              Select the type of research study you want to create
            </p>

            {/* Advanced AI Models Section */}
            <div className="mb-8">
              <div className="flex items-center gap-2 mb-4">
                <Gem className="w-4 h-4 text-purple-400" />
                <span className="text-xs font-mono text-purple-400 uppercase tracking-wider">Advanced AI Models</span>
                <span className="text-[8px] font-mono bg-purple-500/20 text-purple-400 px-1.5 py-0.5 uppercase">Enterprise</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {Object.entries(productTypeConfig)
                  .filter(([, config]) => config.category === 'advanced')
                  .map(([type, config]) => (
                    <button
                      key={type}
                      onClick={() => setProductType(type as ProductTypeKey)}
                      className={cn(
                        'text-left p-6 border transition-all',
                        productType === type
                          ? 'border-purple-400 bg-purple-500/20'
                          : 'border-purple-500/20 hover:border-purple-500/40 bg-gradient-to-br from-purple-500/10 to-blue-500/5'
                      )}
                    >
                      <div className="flex items-start justify-between mb-4">
                        <div className="w-12 h-12 bg-purple-500/20 flex items-center justify-center">
                          <config.icon className="w-6 h-6 text-purple-400" />
                        </div>
                        {config.badge && (
                          <span className="text-[8px] font-mono bg-purple-500/30 text-purple-300 px-1.5 py-0.5 uppercase">
                            {config.badge}
                          </span>
                        )}
                      </div>
                      <h3 className="text-sm font-mono font-bold text-white mb-1">{config.name}</h3>
                      <p className="text-xs font-mono text-white/50">{config.description}</p>
                      {productType === type && (
                        <div className="mt-4 flex items-center gap-2 text-purple-400">
                          <Check className="w-3 h-3" />
                          <span className="text-[10px] font-mono uppercase">Selected</span>
                        </div>
                      )}
                    </button>
                  ))}
              </div>
            </div>

            {/* Standard Products Section */}
            <div>
              <div className="flex items-center gap-2 mb-4">
                <Terminal className="w-4 h-4 text-white/40" />
                <span className="text-xs font-mono text-white/40 uppercase tracking-wider">Standard Products</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {Object.entries(productTypeConfig)
                  .filter(([, config]) => config.category === 'basic')
                  .map(([type, config]) => (
                    <button
                      key={type}
                      onClick={() => setProductType(type as ProductTypeKey)}
                      className={cn(
                        'text-left p-6 border transition-all',
                        productType === type
                          ? 'border-white bg-white/10'
                          : 'border-white/10 hover:border-white/30 bg-white/5'
                      )}
                    >
                      <div className="w-12 h-12 bg-white/10 flex items-center justify-center mb-4">
                        <config.icon className="w-6 h-6 text-white/60" />
                      </div>
                      <h3 className="text-sm font-mono font-bold text-white mb-1">{config.name}</h3>
                      <p className="text-xs font-mono text-white/40">{config.description}</p>
                      {productType === type && (
                        <div className="mt-4 flex items-center gap-2 text-white">
                          <Check className="w-3 h-3" />
                          <span className="text-[10px] font-mono uppercase">Selected</span>
                        </div>
                      )}
                    </button>
                  ))}
              </div>
            </div>
          </div>
        )}

        {/* Step 2: Details */}
        {currentStep === 'details' && typeConfig && (
          <div>
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 bg-white/10 flex items-center justify-center">
                <Icon className="w-5 h-5 text-white/60" />
              </div>
              <div>
                <h2 className="text-sm font-mono font-bold text-white uppercase">{typeConfig.name} Details</h2>
                <p className="text-xs font-mono text-white/40">Define your study parameters</p>
              </div>
            </div>

            <div className="bg-white/5 border border-white/10 p-6 space-y-6">
              {/* Project Selection */}
              <div>
                <label className="block text-[10px] font-mono text-white/40 uppercase mb-2">
                  Project <span className="text-red-400">*</span>
                </label>
                {projectsLoading ? (
                  <div className="flex items-center gap-2 text-white/40 text-xs font-mono">
                    <Loader2 className="w-3 h-3 animate-spin" />
                    Loading projects...
                  </div>
                ) : projects && projects.length > 0 ? (
                  <select
                    value={projectId}
                    onChange={(e) => setProjectId(e.target.value)}
                    className="w-full px-3 py-2 bg-black border border-white/10 text-xs font-mono text-white focus:outline-none focus:border-white/30"
                  >
                    {projects.map((project) => (
                      <option key={project.id} value={project.id}>
                        {project.name}
                      </option>
                    ))}
                  </select>
                ) : (
                  <div className="bg-yellow-500/10 border border-yellow-500/30 p-4">
                    <p className="text-xs font-mono text-yellow-400">
                      No projects found.{' '}
                      <Link href="/dashboard/projects/new" className="underline hover:text-yellow-300">
                        Create a project
                      </Link>{' '}
                      first.
                    </p>
                  </div>
                )}
              </div>

              {/* Name */}
              <div>
                <label className="block text-[10px] font-mono text-white/40 uppercase mb-2">
                  Product Name <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder={`e.g., Q1 ${typeConfig.name} Study`}
                  className="w-full px-3 py-2 bg-black border border-white/10 text-xs font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-white/30"
                />
              </div>

              {/* Description with AI Generate */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="block text-[10px] font-mono text-white/40 uppercase">
                    Description
                  </label>
                  <Button
                    onClick={async () => {
                      if (!name.trim()) {
                        toast({
                          title: 'Name Required',
                          description: 'Please enter a product name first.',
                          variant: 'warning',
                        });
                        return;
                      }
                      try {
                        const result = await generateContent.mutateAsync({
                          title: name,
                          product_type: productType || undefined,
                          sub_type: subType || undefined,
                        });
                        if (result.success && result.content?.description) {
                          setDescription(result.content.description);
                          toast({
                            title: 'Description Generated',
                            description: 'AI has generated a description. You can edit it.',
                            variant: 'success',
                          });
                        }
                      } catch (error) {
                        toast({
                          title: 'Generation Failed',
                          description: 'Failed to generate description. Please try again.',
                          variant: 'destructive',
                        });
                      }
                    }}
                    disabled={generateContent.isPending || !name.trim()}
                    variant="ghost"
                    size="sm"
                    className="h-6 text-[10px] font-mono text-purple-400 hover:text-purple-300 hover:bg-purple-500/10"
                  >
                    {generateContent.isPending ? (
                      <>
                        <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                        GENERATING...
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-3 h-3 mr-1" />
                        GENERATE WITH AI
                      </>
                    )}
                  </Button>
                </div>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={3}
                  placeholder="Describe the objective of this study..."
                  className="w-full px-3 py-2 bg-black border border-white/10 text-xs font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-white/30 resize-none"
                />
                <p className="text-[10px] font-mono text-white/30 mt-1">
                  All AI-generated content is fully editable
                </p>
              </div>

              {/* Sub-Type Selection */}
              <div>
                <label className="block text-[10px] font-mono text-white/40 uppercase mb-2">
                  Study Type <span className="text-red-400">*</span>
                </label>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {typeConfig.subTypes.map((st) => (
                    <button
                      key={st.value}
                      onClick={() => setSubType(st.value)}
                      className={cn(
                        'text-left p-3 border transition-all',
                        subType === st.value
                          ? 'border-white bg-white/10'
                          : 'border-white/10 hover:border-white/30 bg-white/5'
                      )}
                    >
                      <p className="font-mono text-xs text-white">{st.name}</p>
                      <p className="text-[10px] font-mono text-white/40 mt-0.5">{st.description}</p>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Step 3: Target Market */}
        {currentStep === 'target' && typeConfig && (
          <div>
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 bg-white/10 flex items-center justify-center">
                <Globe className="w-5 h-5 text-white/60" />
              </div>
              <div>
                <h2 className="text-sm font-mono font-bold text-white uppercase">Target Market</h2>
                <p className="text-xs font-mono text-white/40">Define your target audience</p>
              </div>
            </div>

            <div className="bg-white/5 border border-white/10 p-6 space-y-6">
              {/* Regions */}
              <div>
                <label className="block text-[10px] font-mono text-white/40 uppercase mb-2">
                  Regions
                </label>
                <div className="flex flex-wrap gap-2">
                  {regions.map((region) => (
                    <button
                      key={region.value}
                      onClick={() => {
                        if (selectedRegions.includes(region.value)) {
                          setSelectedRegions(selectedRegions.filter((r) => r !== region.value));
                        } else {
                          setSelectedRegions([...selectedRegions, region.value]);
                        }
                      }}
                      className={cn(
                        'px-3 py-1.5 text-xs font-mono transition-colors border',
                        selectedRegions.includes(region.value)
                          ? 'bg-white text-black border-white'
                          : 'bg-white/5 text-white/60 border-white/10 hover:border-white/30'
                      )}
                    >
                      {region.name}
                    </button>
                  ))}
                </div>
              </div>

              {/* Countries */}
              <div>
                <label className="block text-[10px] font-mono text-white/40 uppercase mb-2">
                  Countries
                </label>
                <div className="flex flex-wrap gap-2">
                  {countries.map((country) => (
                    <button
                      key={country.value}
                      onClick={() => {
                        if (selectedCountries.includes(country.value)) {
                          setSelectedCountries(selectedCountries.filter((c) => c !== country.value));
                        } else {
                          setSelectedCountries([...selectedCountries, country.value]);
                        }
                      }}
                      className={cn(
                        'px-3 py-1.5 text-xs font-mono transition-colors border',
                        selectedCountries.includes(country.value)
                          ? 'bg-white text-black border-white'
                          : 'bg-white/5 text-white/60 border-white/10 hover:border-white/30'
                      )}
                    >
                      {country.name}
                    </button>
                  ))}
                </div>
              </div>

              {/* Demographics */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Age Groups */}
                <div>
                  <label className="block text-[10px] font-mono text-white/40 uppercase mb-2">
                    Age Groups
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {ageGroups.map((age) => (
                      <button
                        key={age.value}
                        onClick={() => {
                          if (selectedAgeGroups.includes(age.value)) {
                            setSelectedAgeGroups(selectedAgeGroups.filter((a) => a !== age.value));
                          } else {
                            setSelectedAgeGroups([...selectedAgeGroups, age.value]);
                          }
                        }}
                        className={cn(
                          'px-3 py-1.5 text-xs font-mono transition-colors border',
                          selectedAgeGroups.includes(age.value)
                            ? 'bg-white text-black border-white'
                            : 'bg-white/5 text-white/60 border-white/10 hover:border-white/30'
                        )}
                      >
                        {age.name}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Income Groups */}
                <div>
                  <label className="block text-[10px] font-mono text-white/40 uppercase mb-2">
                    Income Groups
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {incomeGroups.map((income) => (
                      <button
                        key={income.value}
                        onClick={() => {
                          if (selectedIncomeGroups.includes(income.value)) {
                            setSelectedIncomeGroups(selectedIncomeGroups.filter((i) => i !== income.value));
                          } else {
                            setSelectedIncomeGroups([...selectedIncomeGroups, income.value]);
                          }
                        }}
                        className={cn(
                          'px-3 py-1.5 text-xs font-mono transition-colors border',
                          selectedIncomeGroups.includes(income.value)
                            ? 'bg-white text-black border-white'
                            : 'bg-white/5 text-white/60 border-white/10 hover:border-white/30'
                        )}
                      >
                        {income.name}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Gender Split */}
              <div>
                <label className="block text-[10px] font-mono text-white/40 uppercase mb-2">
                  Gender Distribution
                </label>
                <div className="flex items-center gap-4">
                  <div className="flex-1">
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={genderSplit.male}
                      onChange={(e) => {
                        const male = parseInt(e.target.value);
                        setGenderSplit({ male, female: 100 - male });
                      }}
                      className="w-full accent-white"
                    />
                  </div>
                  <div className="flex items-center gap-4 text-xs font-mono">
                    <span className="text-white">{genderSplit.male}% Male</span>
                    <span className="text-white/60">{genderSplit.female}% Female</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Step 4: Configuration */}
        {currentStep === 'config' && typeConfig && (
          <div>
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 bg-white/10 flex items-center justify-center">
                <Settings className="w-5 h-5 text-white/60" />
              </div>
              <div>
                <h2 className="text-sm font-mono font-bold text-white uppercase">Configuration</h2>
                <p className="text-xs font-mono text-white/40">Fine-tune your study parameters</p>
              </div>
            </div>

            <div className="bg-white/5 border border-white/10 p-6 space-y-6">
              {/* Persona Count */}
              <div>
                <label className="block text-[10px] font-mono text-white/40 uppercase mb-2">
                  Number of AI Agents
                </label>
                <div className="flex items-center gap-4">
                  <input
                    type="number"
                    min="1"
                    max="10000"
                    value={personaCount}
                    onChange={(e) => setPersonaCount(parseInt(e.target.value) || 100)}
                    className="w-32 px-3 py-2 bg-black border border-white/10 text-xs font-mono text-white focus:outline-none focus:border-white/30"
                  />
                  <div className="flex gap-2">
                    {[100, 500, 1000, 5000].map((count) => (
                      <button
                        key={count}
                        onClick={() => setPersonaCount(count)}
                        className={cn(
                          'px-3 py-1 text-xs font-mono border',
                          personaCount === count
                            ? 'bg-white text-black border-white'
                            : 'bg-white/5 text-white/60 border-white/10 hover:border-white/30'
                        )}
                      >
                        {count.toLocaleString()}
                      </button>
                    ))}
                  </div>
                </div>
                <p className="text-[10px] font-mono text-white/30 mt-1">
                  More agents = higher statistical confidence (recommended: 100+ for insights, 1000+ for predictions)
                </p>
              </div>

              {/* Confidence Target */}
              <div>
                <label className="block text-[10px] font-mono text-white/40 uppercase mb-2">
                  Confidence Target
                </label>
                <div className="flex items-center gap-4">
                  <input
                    type="range"
                    min="50"
                    max="99"
                    value={confidenceTarget * 100}
                    onChange={(e) => setConfidenceTarget(parseInt(e.target.value) / 100)}
                    className="flex-1 accent-white"
                  />
                  <span className="text-sm font-mono text-white w-16">
                    {(confidenceTarget * 100).toFixed(0)}%
                  </span>
                </div>
                <p className="text-[10px] font-mono text-white/30 mt-1">
                  Higher confidence requires more agents and may increase costs
                </p>
              </div>

              {/* Estimated Cost */}
              <div className="bg-white/5 border border-white/10 p-4">
                <div className="flex items-start gap-3">
                  <Info className="w-4 h-4 text-white/60 mt-0.5" />
                  <div>
                    <p className="text-xs font-mono font-bold text-white">Estimated Cost</p>
                    <p className="text-xs font-mono text-white/60 mt-1">
                      ~${((personaCount * 0.02) * (confidenceTarget / 0.9)).toFixed(2)} based on {personaCount} agents at {(confidenceTarget * 100).toFixed(0)}% confidence
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Step 5: Review */}
        {currentStep === 'review' && typeConfig && (
          <div>
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 bg-green-500/20 flex items-center justify-center">
                <Check className="w-5 h-5 text-green-400" />
              </div>
              <div>
                <h2 className="text-sm font-mono font-bold text-white uppercase">Review & Create</h2>
                <p className="text-xs font-mono text-white/40">Confirm your study configuration</p>
              </div>
            </div>

            <div className="bg-white/5 border border-white/10 divide-y divide-white/10">
              {/* Product Type */}
              <div className="p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-white/10 flex items-center justify-center">
                    <Icon className="w-5 h-5 text-white/60" />
                  </div>
                  <div>
                    <p className="text-[10px] font-mono text-white/40 uppercase">Product Type</p>
                    <p className="text-xs font-mono text-white">{typeConfig.name}</p>
                  </div>
                </div>
                <button
                  onClick={() => setCurrentStep('type')}
                  className="text-[10px] font-mono text-white/40 hover:text-white uppercase"
                >
                  Edit
                </button>
              </div>

              {/* Details */}
              <div className="p-4">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-[10px] font-mono text-white/40 uppercase">Study Details</p>
                  <button
                    onClick={() => setCurrentStep('details')}
                    className="text-[10px] font-mono text-white/40 hover:text-white uppercase"
                  >
                    Edit
                  </button>
                </div>
                <p className="text-xs font-mono text-white">{name}</p>
                {description && <p className="text-xs font-mono text-white/60 mt-1">{description}</p>}
                <p className="text-xs font-mono text-white/40 mt-2">
                  Type: {typeConfig.subTypes.find((s) => s.value === subType)?.name || subType}
                </p>
              </div>

              {/* Target Market */}
              <div className="p-4">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-[10px] font-mono text-white/40 uppercase">Target Market</p>
                  <button
                    onClick={() => setCurrentStep('target')}
                    className="text-[10px] font-mono text-white/40 hover:text-white uppercase"
                  >
                    Edit
                  </button>
                </div>
                <div className="flex flex-wrap gap-2">
                  {selectedRegions.map((r) => (
                    <span key={r} className="px-2 py-1 bg-white/10 text-white/60 text-[10px] font-mono">
                      {regions.find((reg) => reg.value === r)?.name}
                    </span>
                  ))}
                  {selectedCountries.map((c) => (
                    <span key={c} className="px-2 py-1 bg-white/10 text-white/60 text-[10px] font-mono">
                      {c}
                    </span>
                  ))}
                </div>
              </div>

              {/* Configuration */}
              <div className="p-4">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-[10px] font-mono text-white/40 uppercase">Configuration</p>
                  <button
                    onClick={() => setCurrentStep('config')}
                    className="text-[10px] font-mono text-white/40 hover:text-white uppercase"
                  >
                    Edit
                  </button>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-[10px] font-mono text-white/40">AI Agents</p>
                    <p className="text-xs font-mono text-white">{personaCount.toLocaleString()}</p>
                  </div>
                  <div>
                    <p className="text-[10px] font-mono text-white/40">Confidence Target</p>
                    <p className="text-xs font-mono text-white">{(confidenceTarget * 100).toFixed(0)}%</p>
                  </div>
                </div>
              </div>

              {/* Cost Estimate */}
              <div className="p-4 bg-white/5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-[10px] font-mono text-white/40 uppercase">Estimated Cost</p>
                    <p className="text-2xl font-mono font-bold text-white">
                      ${((personaCount * 0.02) * (confidenceTarget / 0.9)).toFixed(2)}
                    </p>
                  </div>
                  <Button
                    onClick={handleSubmit}
                    disabled={createProduct.isPending}
                    
                  >
                    {createProduct.isPending ? (
                      <>
                        <Loader2 className="w-3 h-3 mr-2 animate-spin" />
                        CREATING...
                      </>
                    ) : (
                      <>
                        <Plus className="w-3 h-3 mr-2" />
                        CREATE PRODUCT
                      </>
                    )}
                  </Button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Navigation */}
        {currentStep !== 'review' && (
          <div className="flex items-center justify-between mt-8">
            <Button
              variant="outline"
              onClick={handleBack}
              disabled={currentStep === 'type'}
              className="font-mono text-xs border-white/20 text-white/60 hover:bg-white/5"
            >
              <ArrowLeft className="w-3 h-3 mr-2" />
              BACK
            </Button>
            <Button
              onClick={handleNext}
              disabled={!canProceed()}
              
            >
              CONTINUE
              <ArrowRight className="w-3 h-3 ml-2" />
            </Button>
          </div>
        )}
      </div>

      {/* Footer Status */}
      <div className="max-w-5xl mx-auto px-8 pb-8">
        <div className="pt-4 border-t border-white/5">
          <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
            <div className="flex items-center gap-1">
              <Terminal className="w-3 h-3" />
              <span>PRODUCT CREATE MODULE</span>
            </div>
            <span>AGENTVERSE v1.0.0</span>
          </div>
        </div>
      </div>
    </div>
  );
}
