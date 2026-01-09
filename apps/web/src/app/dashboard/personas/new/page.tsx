'use client';

import { useState, useCallback, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  ArrowLeft,
  Sparkles,
  FileSpreadsheet,
  Brain,
  Upload,
  Loader2,
  Check,
  ChevronRight,
  Globe,
  Users,
  X,
  Download,
  Terminal,
} from 'lucide-react';
import {
  useSupportedRegions,
  useGeneratePersonas,
  useCreatePersonaTemplate,
  useAnalyzePersonaUpload,
  useProcessPersonaUpload,
  useStartAIResearch,
  useAIResearchJob,
  usePersonaUploadTemplateUrl,
} from '@/hooks/useApi';
import { cn } from '@/lib/utils';

type CreationMethod = 'ai_generated' | 'file_upload' | 'ai_research';

// Form data types for each method
interface AIGeneratedFormData {
  name: string;
  region: string;
  country: string;
  topic: string;
  industry: string;
  count: number;
  includeTopicKnowledge: boolean;
}

const methods = [
  {
    id: 'ai_generated' as CreationMethod,
    name: 'AI Generated',
    description: 'Generate personas using real demographic data from census and research sources',
    icon: Sparkles,
  },
  {
    id: 'file_upload' as CreationMethod,
    name: 'Upload CSV/Excel',
    description: 'Import existing persona data from your own CSV or Excel files',
    icon: FileSpreadsheet,
  },
  {
    id: 'ai_research' as CreationMethod,
    name: 'AI Research',
    description: 'Let AI research your target market and generate accurate personas automatically',
    icon: Brain,
  },
];

export default function CreatePersonasPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [method, setMethod] = useState<CreationMethod | null>(null);
  const [formData, setFormData] = useState<AIGeneratedFormData | null>(null);

  return (
    <div className="min-h-screen bg-black p-6">
      {/* Header */}
      <div className="mb-8">
        <Link href="/dashboard/personas">
          <Button variant="ghost" size="sm" className="text-white/60 hover:text-white hover:bg-white/5 font-mono text-xs mb-4">
            <ArrowLeft className="w-3 h-3 mr-2" />
            BACK
          </Button>
        </Link>
        <div className="flex items-center gap-2 mb-1">
          <Users className="w-4 h-4 text-white/60" />
          <span className="text-xs font-mono text-white/40 uppercase tracking-wider">Persona Module</span>
        </div>
        <h1 className="text-xl font-mono font-bold text-white">Create Personas</h1>
        <p className="text-sm font-mono text-white/50 mt-1">
          Choose how you want to create your AI agent personas
        </p>
      </div>

      {/* Progress Steps */}
      <div className="flex items-center gap-2 mb-8">
        {[1, 2, 3].map((s) => (
          <div key={s} className="flex items-center">
            <div
              className={cn(
                'w-8 h-8 flex items-center justify-center text-xs font-mono',
                step >= s
                  ? 'bg-white text-black'
                  : 'bg-white/10 text-white/40'
              )}
            >
              {step > s ? <Check className="w-3 h-3" /> : s}
            </div>
            {s < 3 && (
              <div
                className={cn(
                  'w-12 h-px mx-2',
                  step > s ? 'bg-white' : 'bg-white/10'
                )}
              />
            )}
          </div>
        ))}
      </div>

      {/* Step Content */}
      {step === 1 && (
        <MethodSelection
          selectedMethod={method}
          onSelect={(m) => {
            setMethod(m);
            setStep(2);
          }}
        />
      )}

      {step === 2 && method && (
        <MethodConfiguration
          method={method}
          onBack={() => setStep(1)}
          onNext={(data: AIGeneratedFormData) => {
            setFormData(data);
            setStep(3);
          }}
        />
      )}

      {step === 3 && method && formData && (
        <MethodExecution
          method={method}
          formData={formData}
          onBack={() => setStep(2)}
          onComplete={(templateId?: string) => {
            if (templateId) {
              router.push(`/dashboard/personas/${templateId}`);
            } else {
              router.push('/dashboard/personas');
            }
          }}
        />
      )}

      {/* Footer Status */}
      <div className="mt-8 pt-4 border-t border-white/5">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-1">
            <Terminal className="w-3 h-3" />
            <span>PERSONA CREATE MODULE</span>
          </div>
          <span>AGENTVERSE v1.0.0</span>
        </div>
      </div>
    </div>
  );
}

function MethodSelection({
  selectedMethod,
  onSelect,
}: {
  selectedMethod: CreationMethod | null;
  onSelect: (method: CreationMethod) => void;
}) {
  return (
    <div>
      <h2 className="text-sm font-mono font-bold text-white mb-4 uppercase">Choose Creation Method</h2>
      <div className="space-y-3">
        {methods.map((method) => (
          <button
            key={method.id}
            onClick={() => onSelect(method.id)}
            className={cn(
              'w-full flex items-center gap-4 p-4 border transition-all text-left',
              selectedMethod === method.id
                ? 'border-white bg-white/10'
                : 'border-white/10 hover:border-white/30 bg-white/5'
            )}
          >
            <div className="w-10 h-10 bg-white/10 flex items-center justify-center">
              <method.icon className="w-5 h-5 text-white/60" />
            </div>
            <div className="flex-1">
              <h3 className="font-mono font-bold text-white text-sm">{method.name}</h3>
              <p className="font-mono text-white/40 text-xs mt-1">{method.description}</p>
            </div>
            <ChevronRight className="w-4 h-4 text-white/30" />
          </button>
        ))}
      </div>
    </div>
  );
}

function MethodConfiguration({
  method,
  onBack,
  onNext,
}: {
  method: CreationMethod;
  onBack: () => void;
  onNext: (data: AIGeneratedFormData) => void;
}) {
  if (method === 'ai_generated') {
    return <AIGeneratedConfig onBack={onBack} onNext={onNext} />;
  }
  if (method === 'file_upload') {
    return <FileUploadConfig onBack={onBack} onNext={() => onNext({} as AIGeneratedFormData)} />;
  }
  if (method === 'ai_research') {
    return <AIResearchConfig onBack={onBack} onNext={() => onNext({} as AIGeneratedFormData)} />;
  }
  return null;
}

function AIGeneratedConfig({
  onBack,
  onNext,
}: {
  onBack: () => void;
  onNext: (data: AIGeneratedFormData) => void;
}) {
  const { data: regions } = useSupportedRegions();
  const [formData, setFormData] = useState<AIGeneratedFormData>({
    name: '',
    region: 'us',
    country: '',
    topic: '',
    industry: '',
    count: 100,
    includeTopicKnowledge: true,
  });

  return (
    <div className="space-y-6">
      <h2 className="text-sm font-mono font-bold text-white uppercase">Configure AI Generation</h2>

      <div className="bg-white/5 border border-white/10 p-6 space-y-4">
        <div>
          <label className="block text-[10px] font-mono text-white/40 uppercase mb-2">
            Template Name *
          </label>
          <input
            type="text"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            placeholder="e.g., US Tech Consumers Q1 2026"
            className="w-full px-3 py-2 bg-black border border-white/10 text-xs font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-white/30"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-[10px] font-mono text-white/40 uppercase mb-2">
              Region *
            </label>
            <select
              value={formData.region}
              onChange={(e) => setFormData({ ...formData, region: e.target.value })}
              className="w-full px-3 py-2 bg-black border border-white/10 text-xs font-mono text-white focus:outline-none focus:border-white/30"
            >
              {regions?.map((region) => (
                <option key={region.code} value={region.code}>
                  {region.name}
                </option>
              )) || (
                <>
                  <option value="us">United States</option>
                  <option value="europe">Europe</option>
                  <option value="asia">Southeast Asia</option>
                  <option value="china">China</option>
                </>
              )}
            </select>
          </div>

          <div>
            <label className="block text-[10px] font-mono text-white/40 uppercase mb-2">
              Persona Count
            </label>
            <input
              type="number"
              value={formData.count}
              onChange={(e) =>
                setFormData({ ...formData, count: parseInt(e.target.value) || 100 })
              }
              min={10}
              max={1000}
              className="w-full px-3 py-2 bg-black border border-white/10 text-xs font-mono text-white focus:outline-none focus:border-white/30"
            />
          </div>
        </div>

        <div>
          <label className="block text-[10px] font-mono text-white/40 uppercase mb-2">
            Topic/Context
          </label>
          <input
            type="text"
            value={formData.topic}
            onChange={(e) => setFormData({ ...formData, topic: e.target.value })}
            placeholder="e.g., Electric Vehicles, Smartphone Purchase, Health Insurance"
            className="w-full px-3 py-2 bg-black border border-white/10 text-xs font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-white/30"
          />
          <p className="text-[10px] font-mono text-white/30 mt-1">
            Personas will have specialized knowledge and opinions about this topic
          </p>
        </div>

        <div>
          <label className="block text-[10px] font-mono text-white/40 uppercase mb-2">
            Industry
          </label>
          <input
            type="text"
            value={formData.industry}
            onChange={(e) => setFormData({ ...formData, industry: e.target.value })}
            placeholder="e.g., Automotive, Healthcare, Finance, Technology"
            className="w-full px-3 py-2 bg-black border border-white/10 text-xs font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-white/30"
          />
        </div>

        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="topicKnowledge"
            checked={formData.includeTopicKnowledge}
            onChange={(e) =>
              setFormData({ ...formData, includeTopicKnowledge: e.target.checked })
            }
            className="w-4 h-4 bg-black border-white/30"
          />
          <label htmlFor="topicKnowledge" className="text-xs font-mono text-white/60">
            Include topic-specific knowledge and opinions
          </label>
        </div>
      </div>

      {/* Info Box */}
      <div className="bg-white/5 border border-white/20 p-4">
        <div className="flex items-start gap-3">
          <Globe className="w-4 h-4 text-white/60 mt-0.5" />
          <div>
            <h4 className="font-mono text-xs font-bold text-white">REAL DATA SOURCES</h4>
            <p className="text-[10px] font-mono text-white/40 mt-1">
              Personas will be generated using real census data, demographic research, and
              psychographic correlations from the selected region.
            </p>
          </div>
        </div>
      </div>

      <div className="flex justify-between">
        <Button variant="outline" onClick={onBack} className="font-mono text-xs border-white/20 text-white/60 hover:bg-white/5">
          <ArrowLeft className="w-3 h-3 mr-2" />
          BACK
        </Button>
        <Button onClick={() => onNext(formData)} disabled={!formData.name} >
          CONTINUE
          <ChevronRight className="w-3 h-3 ml-2" />
        </Button>
      </div>
    </div>
  );
}

function FileUploadConfig({
  onBack,
  onNext,
}: {
  onBack: () => void;
  onNext: () => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const analyzeUpload = useAnalyzePersonaUpload();
  const templateUrl = usePersonaUploadTemplateUrl();

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  return (
    <div className="space-y-6">
      <h2 className="text-sm font-mono font-bold text-white uppercase">Upload Persona Data</h2>

      {/* Download Template */}
      <div className="bg-white/5 border border-white/10 p-4">
        <div className="flex items-center justify-between">
          <div>
            <h4 className="font-mono text-xs font-bold text-white">DOWNLOAD TEMPLATE</h4>
            <p className="text-[10px] font-mono text-white/40 mt-1">
              Use our template to format your persona data correctly
            </p>
          </div>
          <a href={templateUrl} download>
            <Button variant="outline" size="sm" className="font-mono text-[10px] border-white/20 text-white/60 hover:bg-white/5">
              <Download className="w-3 h-3 mr-2" />
              CSV TEMPLATE
            </Button>
          </a>
        </div>
      </div>

      {/* Upload Zone */}
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        className={cn(
          'border-2 border-dashed p-12 text-center transition-colors',
          dragActive
            ? 'border-white bg-white/10'
            : file
            ? 'border-green-500/50 bg-green-500/10'
            : 'border-white/20 hover:border-white/40'
        )}
      >
        {file ? (
          <div className="space-y-2">
            <div className="flex items-center justify-center gap-2 text-green-400">
              <Check className="w-5 h-5" />
              <span className="font-mono text-sm">{file.name}</span>
            </div>
            <p className="text-xs font-mono text-white/40">
              {(file.size / 1024).toFixed(1)} KB
            </p>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setFile(null)}
              className="text-red-400 hover:text-red-300 font-mono text-xs"
            >
              <X className="w-3 h-3 mr-1" />
              REMOVE
            </Button>
          </div>
        ) : (
          <>
            <Upload className="w-10 h-10 text-white/30 mx-auto mb-4" />
            <p className="font-mono text-white/60 text-sm mb-2">
              Drag and drop your file here, or{' '}
              <label className="text-white hover:underline cursor-pointer">
                browse
                <input
                  type="file"
                  accept=".csv,.xlsx,.xls"
                  onChange={handleFileChange}
                  className="hidden"
                />
              </label>
            </p>
            <p className="text-[10px] font-mono text-white/30">
              Supports CSV and Excel files (max 10MB)
            </p>
          </>
        )}
      </div>

      {/* Analysis Result Preview */}
      {analyzeUpload.data && (
        <div className="bg-white/5 border border-white/10 p-4">
          <h4 className="font-mono text-xs font-bold text-white mb-2">FILE ANALYSIS</h4>
          <div className="grid grid-cols-3 gap-4 text-xs font-mono">
            <div>
              <span className="text-white/40">Rows:</span>{' '}
              <span className="text-white">{analyzeUpload.data.row_count}</span>
            </div>
            <div>
              <span className="text-white/40">Columns:</span>{' '}
              <span className="text-white">{analyzeUpload.data.column_count}</span>
            </div>
            <div>
              <span className="text-white/40">Mappable:</span>{' '}
              <span className="text-white">
                {Object.keys(analyzeUpload.data.suggested_mappings).length}
              </span>
            </div>
          </div>
        </div>
      )}

      <div className="flex justify-between">
        <Button variant="outline" onClick={onBack} className="font-mono text-xs border-white/20 text-white/60 hover:bg-white/5">
          <ArrowLeft className="w-3 h-3 mr-2" />
          BACK
        </Button>
        <Button
          onClick={onNext}
          disabled={!file || analyzeUpload.isPending}
          
        >
          {analyzeUpload.isPending ? (
            <>
              <Loader2 className="w-3 h-3 mr-2 animate-spin" />
              ANALYZING...
            </>
          ) : (
            <>
              CONTINUE
              <ChevronRight className="w-3 h-3 ml-2" />
            </>
          )}
        </Button>
      </div>
    </div>
  );
}

function AIResearchConfig({
  onBack,
  onNext,
}: {
  onBack: () => void;
  onNext: () => void;
}) {
  const { data: regions } = useSupportedRegions();
  const [formData, setFormData] = useState({
    topic: '',
    region: 'us',
    country: '',
    industry: '',
    keywords: '',
    researchDepth: 'standard' as 'quick' | 'standard' | 'comprehensive',
    targetCount: 100,
  });

  return (
    <div className="space-y-6">
      <h2 className="text-sm font-mono font-bold text-white uppercase">Configure AI Research</h2>

      <div className="bg-white/5 border border-white/10 p-6 space-y-4">
        <div>
          <label className="block text-[10px] font-mono text-white/40 uppercase mb-2">
            Research Topic *
          </label>
          <input
            type="text"
            value={formData.topic}
            onChange={(e) => setFormData({ ...formData, topic: e.target.value })}
            placeholder="e.g., Electric Vehicle Adoption, Healthcare Spending Habits"
            className="w-full px-3 py-2 bg-black border border-white/10 text-xs font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-white/30"
          />
          <p className="text-[10px] font-mono text-white/30 mt-1">
            AI will research this topic to understand the target audience
          </p>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-[10px] font-mono text-white/40 uppercase mb-2">
              Target Region *
            </label>
            <select
              value={formData.region}
              onChange={(e) => setFormData({ ...formData, region: e.target.value })}
              className="w-full px-3 py-2 bg-black border border-white/10 text-xs font-mono text-white focus:outline-none focus:border-white/30"
            >
              {regions?.map((region) => (
                <option key={region.code} value={region.code}>
                  {region.name}
                </option>
              )) || (
                <>
                  <option value="us">United States</option>
                  <option value="europe">Europe</option>
                  <option value="asia">Southeast Asia</option>
                  <option value="china">China</option>
                </>
              )}
            </select>
          </div>

          <div>
            <label className="block text-[10px] font-mono text-white/40 uppercase mb-2">
              Industry
            </label>
            <input
              type="text"
              value={formData.industry}
              onChange={(e) => setFormData({ ...formData, industry: e.target.value })}
              placeholder="e.g., Automotive, Healthcare"
              className="w-full px-3 py-2 bg-black border border-white/10 text-xs font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-white/30"
            />
          </div>
        </div>

        <div>
          <label className="block text-[10px] font-mono text-white/40 uppercase mb-2">
            Research Keywords
          </label>
          <input
            type="text"
            value={formData.keywords}
            onChange={(e) => setFormData({ ...formData, keywords: e.target.value })}
            placeholder="Comma-separated keywords, e.g., sustainability, premium, budget"
            className="w-full px-3 py-2 bg-black border border-white/10 text-xs font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-white/30"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-[10px] font-mono text-white/40 uppercase mb-2">
              Research Depth
            </label>
            <select
              value={formData.researchDepth}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  researchDepth: e.target.value as 'quick' | 'standard' | 'comprehensive',
                })
              }
              className="w-full px-3 py-2 bg-black border border-white/10 text-xs font-mono text-white focus:outline-none focus:border-white/30"
            >
              <option value="quick">Quick (~2 min)</option>
              <option value="standard">Standard (~5 min)</option>
              <option value="comprehensive">Comprehensive (~10 min)</option>
            </select>
          </div>

          <div>
            <label className="block text-[10px] font-mono text-white/40 uppercase mb-2">
              Target Persona Count
            </label>
            <input
              type="number"
              value={formData.targetCount}
              onChange={(e) =>
                setFormData({ ...formData, targetCount: parseInt(e.target.value) || 100 })
              }
              min={10}
              max={500}
              className="w-full px-3 py-2 bg-black border border-white/10 text-xs font-mono text-white focus:outline-none focus:border-white/30"
            />
          </div>
        </div>
      </div>

      {/* Info Box */}
      <div className="bg-white/5 border border-white/20 p-4">
        <div className="flex items-start gap-3">
          <Brain className="w-4 h-4 text-white/60 mt-0.5" />
          <div>
            <h4 className="font-mono text-xs font-bold text-white">AI-POWERED RESEARCH</h4>
            <p className="text-[10px] font-mono text-white/40 mt-1">
              Our AI will analyze market data, consumer trends, and demographic research to
              create highly accurate personas tailored to your specific topic and region.
            </p>
          </div>
        </div>
      </div>

      <div className="flex justify-between">
        <Button variant="outline" onClick={onBack} className="font-mono text-xs border-white/20 text-white/60 hover:bg-white/5">
          <ArrowLeft className="w-3 h-3 mr-2" />
          BACK
        </Button>
        <Button onClick={onNext} disabled={!formData.topic} >
          START RESEARCH
          <ChevronRight className="w-3 h-3 ml-2" />
        </Button>
      </div>
    </div>
  );
}

function MethodExecution({
  method,
  formData,
  onBack,
  onComplete,
}: {
  method: CreationMethod;
  formData: AIGeneratedFormData;
  onBack: () => void;
  onComplete: (templateId?: string) => void;
}) {
  const [isProcessing, setIsProcessing] = useState(true);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState('Initializing...');
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{
    templateId: string;
    personaCount: number;
    confidence: number;
  } | null>(null);

  const createTemplate = useCreatePersonaTemplate();
  const generatePersonas = useGeneratePersonas();

  // Actual API call
  useEffect(() => {
    let cancelled = false;

    const executeCreation = async () => {
      try {
        // Step 1: Create template
        setProgress(10);
        setStatus('Creating persona template...');

        const template = await createTemplate.mutateAsync({
          name: formData.name,
          description: `AI-generated personas for ${formData.topic || 'general'} in ${formData.industry || 'various industries'}`,
          source_type: 'ai_generated',
          region: formData.region,
          topic: formData.topic || undefined,
          industry: formData.industry || undefined,
        });

        if (cancelled) return;

        // Step 2: Generate personas
        setProgress(30);
        setStatus('Fetching demographic data...');

        await new Promise((r) => setTimeout(r, 500));
        if (cancelled) return;

        setProgress(50);
        setStatus('Generating persona traits...');

        const response = await generatePersonas.mutateAsync({
          template_id: template.id,
          region: formData.region,
          country: formData.country || undefined,
          topic: formData.topic || undefined,
          industry: formData.industry || undefined,
          count: formData.count,
          include_topic_knowledge: formData.includeTopicKnowledge,
          include_psychographics: true,
          include_behavioral: true,
          include_cultural: true,
        });

        if (cancelled) return;

        setProgress(80);
        setStatus('Building psychographic profiles...');

        await new Promise((r) => setTimeout(r, 500));
        if (cancelled) return;

        setProgress(100);
        setStatus('Complete!');

        setResult({
          templateId: template.id,
          personaCount: response.count || formData.count,
          confidence: 95, // Default confidence score
        });

        setIsProcessing(false);
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : 'Failed to create personas');
        setIsProcessing(false);
      }
    };

    executeCreation();

    return () => {
      cancelled = true;
    };
  }, [formData]);

  return (
    <div className="space-y-6">
      <h2 className="text-sm font-mono font-bold text-white uppercase">
        {isProcessing ? 'Creating Personas...' : error ? 'Error' : 'Personas Created!'}
      </h2>

      <div className="bg-white/5 border border-white/10 p-8">
        {error ? (
          <div className="text-center space-y-6">
            <div className="w-14 h-14 bg-red-500/20 flex items-center justify-center mx-auto">
              <X className="w-6 h-6 text-red-400" />
            </div>
            <div>
              <h3 className="text-lg font-mono font-bold text-red-400">
                CREATION FAILED
              </h3>
              <p className="font-mono text-white/50 text-sm mt-2">
                {error}
              </p>
            </div>
          </div>
        ) : isProcessing ? (
          <div className="text-center space-y-6">
            <Loader2 className="w-12 h-12 animate-spin text-white/60 mx-auto" />
            <div>
              <p className="font-mono text-white text-sm">{status}</p>
              <div className="mt-4 w-full bg-white/10 h-1">
                <div
                  className="bg-white h-1 transition-all duration-300"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <p className="text-xs font-mono text-white/40 mt-2">{progress}% complete</p>
            </div>
          </div>
        ) : result ? (
          <div className="text-center space-y-6">
            <div className="w-14 h-14 bg-green-500/20 flex items-center justify-center mx-auto">
              <Check className="w-6 h-6 text-green-400" />
            </div>
            <div>
              <h3 className="text-lg font-mono font-bold text-white">
                SUCCESSFULLY CREATED!
              </h3>
              <p className="font-mono text-white/50 text-sm mt-2">
                Your personas have been generated and are ready to use in simulations.
              </p>
            </div>

            {/* Summary Stats */}
            <div className="grid grid-cols-3 gap-4 max-w-md mx-auto">
              <div className="bg-white/5 border border-white/10 p-4">
                <p className="text-xl font-mono font-bold text-white">{result.personaCount}</p>
                <p className="text-[10px] font-mono text-white/40 uppercase">Personas</p>
              </div>
              <div className="bg-white/5 border border-white/10 p-4">
                <p className="text-xl font-mono font-bold text-white">100+</p>
                <p className="text-[10px] font-mono text-white/40 uppercase">Traits Each</p>
              </div>
              <div className="bg-white/5 border border-white/10 p-4">
                <p className="text-xl font-mono font-bold text-white">{result.confidence}%</p>
                <p className="text-[10px] font-mono text-white/40 uppercase">Confidence</p>
              </div>
            </div>
          </div>
        ) : null}
      </div>

      <div className="flex justify-between">
        <Button variant="outline" onClick={onBack} disabled={isProcessing} className="font-mono text-xs border-white/20 text-white/60 hover:bg-white/5">
          <ArrowLeft className="w-3 h-3 mr-2" />
          BACK
        </Button>
        <Button onClick={() => onComplete(result?.templateId)} disabled={isProcessing || !!error} >
          {isProcessing ? (
            'PROCESSING...'
          ) : error ? (
            'TRY AGAIN'
          ) : (
            <>
              VIEW PERSONAS
              <ChevronRight className="w-3 h-3 ml-2" />
            </>
          )}
        </Button>
      </div>
    </div>
  );
}
