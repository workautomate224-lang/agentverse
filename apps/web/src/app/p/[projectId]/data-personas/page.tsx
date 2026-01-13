'use client';

/**
 * Data & Personas Page
 * Configure data sources and simulation personas
 */

import { useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
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
  Users,
  Upload,
  Database,
  Plus,
  ArrowLeft,
  ArrowRight,
  Terminal,
  FileText,
  Search,
  Zap,
  Loader2,
  CheckCircle,
  AlertCircle,
  X,
  Eye,
  Trash2,
  RefreshCw,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  usePersonaTemplates,
  useGeneratePersonas,
  useAnalyzePersonaUpload,
  useProcessPersonaUpload,
  useStartAIResearch,
  useAIResearchJob,
  usePersonas,
  useDeletePersonaTemplate,
} from '@/hooks/useApi';

// Persona source options
const personaSources = [
  {
    id: 'template',
    name: 'Use Templates',
    description: 'Start with pre-built persona templates from the library',
    icon: FileText,
    color: 'cyan',
  },
  {
    id: 'upload',
    name: 'Upload Data',
    description: 'Upload your own demographic or survey data',
    icon: Upload,
    color: 'purple',
  },
  {
    id: 'generate',
    name: 'AI Generation',
    description: 'Generate synthetic personas based on your goal',
    icon: Zap,
    color: 'amber',
  },
  {
    id: 'search',
    name: 'Deep Search',
    description: 'Advanced persona discovery from multiple sources',
    icon: Search,
    color: 'green',
  },
];

// Persona Template Modal
function PersonaTemplatesModal({
  open,
  onOpenChange,
  projectId,
  onSuccess,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId: string;
  onSuccess: () => void;
}) {
  const { data: templates, isLoading, error } = usePersonaTemplates({ limit: 50 });
  const [selectedTemplates, setSelectedTemplates] = useState<string[]>([]);

  const handleToggleTemplate = (templateId: string) => {
    setSelectedTemplates((prev) =>
      prev.includes(templateId)
        ? prev.filter((id) => id !== templateId)
        : [...prev, templateId]
    );
  };

  const handleAddToProject = () => {
    // In a real implementation, this would call an API to associate templates with the project
    // For now, we close the modal and trigger success
    onSuccess();
    onOpenChange(false);
    setSelectedTemplates([]);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="font-mono">Persona Templates</DialogTitle>
          <DialogDescription className="font-mono">
            Browse and select persona templates to add to your project
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto py-4 space-y-3">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 animate-spin text-cyan-400" />
              <span className="ml-2 text-sm font-mono text-white/60">Loading templates...</span>
            </div>
          ) : error ? (
            <div className="flex items-center justify-center py-12 text-red-400">
              <AlertCircle className="w-5 h-5 mr-2" />
              <span className="text-sm font-mono">Failed to load templates</span>
            </div>
          ) : templates && templates.length > 0 ? (
            templates.map((template) => (
              <button
                key={template.id}
                onClick={() => handleToggleTemplate(template.id)}
                className={cn(
                  'w-full flex items-start gap-3 p-4 border transition-all text-left',
                  selectedTemplates.includes(template.id)
                    ? 'bg-cyan-500/10 border-cyan-500/50'
                    : 'bg-white/5 border-white/10 hover:border-white/20'
                )}
              >
                <div className="w-10 h-10 bg-gradient-to-br from-cyan-500 to-blue-500 flex items-center justify-center flex-shrink-0">
                  <FileText className="w-5 h-5 text-white" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-mono font-bold text-white truncate">
                      {template.name}
                    </h3>
                    {selectedTemplates.includes(template.id) && (
                      <CheckCircle className="w-4 h-4 text-cyan-400 flex-shrink-0" />
                    )}
                  </div>
                  <p className="text-xs font-mono text-white/50 mt-1 line-clamp-2">
                    {template.description || 'No description'}
                  </p>
                  <div className="flex items-center gap-3 mt-2 text-[10px] font-mono text-white/30">
                    <span>Region: {template.region || 'Global'}</span>
                    <span>Source: {template.source_type || 'Manual'}</span>
                  </div>
                </div>
              </button>
            ))
          ) : (
            <div className="text-center py-12">
              <FileText className="w-10 h-10 text-white/20 mx-auto mb-3" />
              <p className="text-sm font-mono text-white/40">No templates available</p>
              <p className="text-xs font-mono text-white/30 mt-1">
                Create templates in the Global Library first
              </p>
            </div>
          )}
        </div>

        <DialogFooter className="border-t border-white/10 pt-4">
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleAddToProject}
            disabled={selectedTemplates.length === 0}
            className="bg-cyan-500 hover:bg-cyan-600 text-black"
          >
            Add {selectedTemplates.length > 0 ? `(${selectedTemplates.length})` : ''} to Project
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// Upload Data Modal
function UploadDataModal({
  open,
  onOpenChange,
  onSuccess,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const analyzeUpload = useAnalyzePersonaUpload();
  const processUpload = useProcessPersonaUpload();
  const [analysisResult, setAnalysisResult] = useState<{ columns: { name: string; data_type: string; sample_values: string[] }[] } | null>(null);
  const [columnMapping, setColumnMapping] = useState<Record<string, string>>({});

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
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.name.endsWith('.csv') || droppedFile.name.endsWith('.json')) {
        setFile(droppedFile);
        handleAnalyze(droppedFile);
      }
    }
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      handleAnalyze(e.target.files[0]);
    }
  };

  const handleAnalyze = async (fileToAnalyze: File) => {
    try {
      const result = await analyzeUpload.mutateAsync(fileToAnalyze);
      setAnalysisResult({
        columns: result.columns?.map(c => ({
          name: c.name,
          data_type: c.data_type,
          sample_values: c.sample_values,
        })) || [],
      });
    } catch {
      // Error handled by React Query
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    try {
      await processUpload.mutateAsync({
        file,
        mapping: columnMapping,
      });
      onSuccess();
      onOpenChange(false);
      resetState();
    } catch {
      // Error handled by React Query
    }
  };

  const resetState = () => {
    setFile(null);
    setAnalysisResult(null);
    setColumnMapping({});
  };

  const isEndpointAvailable = !analyzeUpload.error || (analyzeUpload.error as Error)?.message !== 'Network Error';

  return (
    <Dialog open={open} onOpenChange={(o) => { onOpenChange(o); if (!o) resetState(); }}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="font-mono">Upload Personas/Data</DialogTitle>
          <DialogDescription className="font-mono">
            Upload CSV or JSON files with persona data
          </DialogDescription>
        </DialogHeader>

        <div className="py-4 space-y-4">
          {/* Drop Zone */}
          <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            className={cn(
              'relative border-2 border-dashed p-8 text-center transition-colors',
              dragActive ? 'border-cyan-500 bg-cyan-500/10' : 'border-white/20 hover:border-white/40'
            )}
          >
            <Upload className="w-10 h-10 text-white/30 mx-auto mb-3" />
            <p className="text-sm font-mono text-white/60 mb-2">
              Drag & drop your file here, or
            </p>
            <label className="cursor-pointer">
              <span className="text-sm font-mono text-cyan-400 hover:text-cyan-300">browse files</span>
              <input
                type="file"
                accept=".csv,.json"
                onChange={handleFileChange}
                className="hidden"
              />
            </label>
            <p className="text-xs font-mono text-white/30 mt-2">
              Supports CSV and JSON formats
            </p>
          </div>

          {/* File Info */}
          {file && (
            <div className="flex items-center justify-between p-3 bg-white/5 border border-white/10">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-white/40" />
                <span className="text-sm font-mono text-white">{file.name}</span>
                <span className="text-xs font-mono text-white/30">
                  ({(file.size / 1024).toFixed(1)} KB)
                </span>
              </div>
              <button onClick={() => { setFile(null); setAnalysisResult(null); }}>
                <X className="w-4 h-4 text-white/40 hover:text-white" />
              </button>
            </div>
          )}

          {/* Analysis Status */}
          {analyzeUpload.isPending && (
            <div className="flex items-center gap-2 text-sm font-mono text-white/60">
              <Loader2 className="w-4 h-4 animate-spin" />
              Analyzing file...
            </div>
          )}

          {analyzeUpload.isError && (
            <div className="p-3 bg-red-500/10 border border-red-500/30 text-red-400 text-sm font-mono">
              <AlertCircle className="w-4 h-4 inline mr-2" />
              {isEndpointAvailable ? 'Failed to analyze file' : 'Upload endpoint not connected yet'}
            </div>
          )}

          {/* Column Preview */}
          {analysisResult && analysisResult.columns.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-mono text-white/40 uppercase">Detected Columns</p>
              <div className="flex flex-wrap gap-2">
                {analysisResult.columns.map((col) => (
                  <span key={col.name} className="px-2 py-1 bg-white/5 border border-white/10 text-xs font-mono text-white/60">
                    {col.name}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="secondary" onClick={() => { onOpenChange(false); resetState(); }}>
            Cancel
          </Button>
          <Button
            onClick={handleUpload}
            disabled={!file || processUpload.isPending || !isEndpointAvailable}
            className="bg-purple-500 hover:bg-purple-600 text-white"
          >
            {processUpload.isPending ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
                Uploading...
              </>
            ) : (
              'Upload Data'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// Generated persona type
interface GeneratedPersona {
  id: string;
  name: string;
  age: number;
  gender: string;
  occupation: string;
  income_bracket: string;
  education_level: string;
  location: string;
  personality_traits: string[];
  values: string[];
  interests: string[];
  pain_points: string[];
  goals: string[];
  communication_style: string;
  decision_making_style: string;
  brand_preferences?: string[];
  media_consumption?: string[];
  cultural_context?: string;
  behavioral_patterns?: string[];
}

// AI Generation Modal
function GeneratePersonasModal({
  open,
  onOpenChange,
  projectId,
  onGenerated,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId: string;
  onGenerated: (personas: GeneratedPersona[]) => void;
}) {
  const [count, setCount] = useState(10);
  const [ageRange, setAgeRange] = useState('');
  const [region, setRegion] = useState('');
  const [language, setLanguage] = useState('');
  const [context, setContext] = useState('');
  const generatePersonas = useGeneratePersonas();

  const handleGenerate = async () => {
    try {
      // Build keywords from optional fields
      const keywords: string[] = [];
      if (ageRange) keywords.push(`age: ${ageRange}`);
      if (language) keywords.push(`language: ${language}`);

      const result = await generatePersonas.mutateAsync({
        count,
        region: region || 'US',
        topic: context || undefined,
        keywords: keywords.length > 0 ? keywords : undefined,
      });
      // Pass generated personas to parent
      if (result.sample_personas && result.sample_personas.length > 0) {
        onGenerated(result.sample_personas as unknown as GeneratedPersona[]);
      }
      onOpenChange(false);
      resetForm();
    } catch {
      // Error handled by React Query
    }
  };

  const resetForm = () => {
    setCount(100);
    setAgeRange('');
    setRegion('');
    setLanguage('');
    setContext('');
  };

  const isEndpointAvailable = !generatePersonas.error || (generatePersonas.error as Error)?.message !== 'Network Error';

  return (
    <Dialog open={open} onOpenChange={(o) => { onOpenChange(o); if (!o) resetForm(); }}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="font-mono">Generate Personas</DialogTitle>
          <DialogDescription className="font-mono">
            AI will generate synthetic personas based on your parameters
          </DialogDescription>
        </DialogHeader>

        <div className="py-4 space-y-4">
          {/* Count */}
          <div>
            <label className="block text-xs font-mono text-white/40 uppercase mb-2">
              Number of Personas
            </label>
            <Input
              type="number"
              value={count}
              onChange={(e) => setCount(parseInt(e.target.value) || 0)}
              min={1}
              max={10000}
              placeholder="100"
            />
          </div>

          {/* Context */}
          <div>
            <label className="block text-xs font-mono text-white/40 uppercase mb-2">
              Context (optional)
            </label>
            <textarea
              value={context}
              onChange={(e) => setContext(e.target.value)}
              placeholder="Describe the target audience or use case..."
              className="w-full h-20 px-3 py-2 bg-black border border-white/20 text-white font-mono text-sm placeholder:text-white/30 focus:border-white/40 focus:outline-none resize-none"
            />
          </div>

          {/* Constraints */}
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-mono text-white/40 uppercase mb-2">
                Age Range
              </label>
              <Input
                value={ageRange}
                onChange={(e) => setAgeRange(e.target.value)}
                placeholder="18-65"
              />
            </div>
            <div>
              <label className="block text-xs font-mono text-white/40 uppercase mb-2">
                Region
              </label>
              <Input
                value={region}
                onChange={(e) => setRegion(e.target.value)}
                placeholder="US"
              />
            </div>
            <div>
              <label className="block text-xs font-mono text-white/40 uppercase mb-2">
                Language
              </label>
              <Input
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                placeholder="English"
              />
            </div>
          </div>

          {generatePersonas.isError && (
            <div className="p-3 bg-red-500/10 border border-red-500/30 text-red-400 text-sm font-mono">
              <AlertCircle className="w-4 h-4 inline mr-2" />
              {isEndpointAvailable ? 'Failed to generate personas' : 'Generation endpoint coming soon'}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="secondary" onClick={() => { onOpenChange(false); resetForm(); }}>
            Cancel
          </Button>
          <Button
            onClick={handleGenerate}
            disabled={count <= 0 || generatePersonas.isPending || !isEndpointAvailable}
            className="bg-amber-500 hover:bg-amber-600 text-black"
          >
            {generatePersonas.isPending ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
                Generating...
              </>
            ) : !isEndpointAvailable ? (
              'Coming Soon'
            ) : (
              'Generate Personas'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// Deep Search Modal
function DeepSearchModal({
  open,
  onOpenChange,
  projectId,
  onSuccess,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId: string;
  onSuccess: () => void;
}) {
  const [region, setRegion] = useState('');
  const [keywords, setKeywords] = useState('');
  const [researchDepth, setResearchDepth] = useState<'quick' | 'standard' | 'comprehensive'>('standard');
  const [jobId, setJobId] = useState<string | null>(null);
  const startResearch = useStartAIResearch();
  const { data: jobStatus } = useAIResearchJob(jobId || '');

  const handleSearch = async () => {
    try {
      const keywordList = keywords.split(',').map((k) => k.trim()).filter(Boolean);
      const result = await startResearch.mutateAsync({
        topic: keywordList.join(' ') || 'Consumer research',
        region: region || 'US',
        keywords: keywordList.length > 0 ? keywordList : undefined,
        research_depth: researchDepth,
      });
      setJobId(result.id);
    } catch {
      // Error handled by React Query
    }
  };

  const handleAddResults = () => {
    onSuccess();
    onOpenChange(false);
    resetForm();
  };

  const resetForm = () => {
    setRegion('');
    setKeywords('');
    setResearchDepth('standard');
    setJobId(null);
  };

  const isEndpointAvailable = !startResearch.error || (startResearch.error as Error)?.message !== 'Network Error';

  return (
    <Dialog open={open} onOpenChange={(o) => { onOpenChange(o); if (!o) resetForm(); }}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="font-mono">Deep Search</DialogTitle>
          <DialogDescription className="font-mono">
            Search for personas from multiple data sources
          </DialogDescription>
        </DialogHeader>

        <div className="py-4 space-y-4">
          {/* Region */}
          <div>
            <label className="block text-xs font-mono text-white/40 uppercase mb-2">
              Region
            </label>
            <Input
              value={region}
              onChange={(e) => setRegion(e.target.value)}
              placeholder="US, UK, Germany..."
            />
          </div>

          {/* Keywords */}
          <div>
            <label className="block text-xs font-mono text-white/40 uppercase mb-2">
              Topic Keywords (comma-separated)
            </label>
            <Input
              value={keywords}
              onChange={(e) => setKeywords(e.target.value)}
              placeholder="technology, early adopters, urban..."
            />
          </div>

          {/* Job Status */}
          {jobStatus && (
            <div className="p-3 bg-white/5 border border-white/10">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-mono text-white/40">Search Status</span>
                <span
                  className={cn(
                    'text-xs font-mono px-2 py-0.5',
                    jobStatus.status === 'completed'
                      ? 'bg-green-500/20 text-green-400'
                      : jobStatus.status === 'failed'
                        ? 'bg-red-500/20 text-red-400'
                        : 'bg-yellow-500/20 text-yellow-400'
                  )}
                >
                  {jobStatus.status}
                </span>
              </div>
              {jobStatus.status === 'completed' && (
                <p className="text-sm font-mono text-white/60">
                  Found {jobStatus.personas_generated || 0} candidate personas
                </p>
              )}
            </div>
          )}

          {startResearch.isError && (
            <div className="p-3 bg-red-500/10 border border-red-500/30 text-red-400 text-sm font-mono">
              <AlertCircle className="w-4 h-4 inline mr-2" />
              {isEndpointAvailable ? 'Search failed' : 'Deep Search endpoint coming soon'}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="secondary" onClick={() => { onOpenChange(false); resetForm(); }}>
            Cancel
          </Button>
          {jobStatus?.status === 'completed' ? (
            <Button
              onClick={handleAddResults}
              className="bg-green-500 hover:bg-green-600 text-black"
            >
              Add Selected to Project
            </Button>
          ) : (
            <Button
              onClick={handleSearch}
              disabled={startResearch.isPending || !isEndpointAvailable}
              className="bg-green-500 hover:bg-green-600 text-black"
            >
              {startResearch.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  Searching...
                </>
              ) : !isEndpointAvailable ? (
                'Coming Soon'
              ) : (
                'Start Search'
              )}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// Persona Details Modal
function PersonaDetailsModal({
  open,
  onOpenChange,
  persona,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  persona: Record<string, unknown> | null;
}) {
  if (!persona) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="font-mono">Persona Details</DialogTitle>
        </DialogHeader>

        <div className="py-4 space-y-4 max-h-[60vh] overflow-y-auto">
          {Object.entries(persona).map(([key, value]) => (
            <div key={key} className="border-b border-white/10 pb-2">
              <label className="block text-xs font-mono text-white/40 uppercase mb-1">
                {key.replace(/_/g, ' ')}
              </label>
              <p className="text-sm font-mono text-white">
                {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
              </p>
            </div>
          ))}
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

export default function DataPersonasPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.projectId as string;

  // Modal states
  const [templateModalOpen, setTemplateModalOpen] = useState(false);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [generateModalOpen, setGenerateModalOpen] = useState(false);
  const [searchModalOpen, setSearchModalOpen] = useState(false);
  const [detailsModalOpen, setDetailsModalOpen] = useState(false);
  const [selectedPersona, setSelectedPersona] = useState<Record<string, unknown> | null>(null);

  // AI-generated personas (preview, not yet saved)
  const [generatedPersonas, setGeneratedPersonas] = useState<GeneratedPersona[]>([]);

  // Data hooks
  const { data: templates, isLoading: loadingTemplates, refetch: refetchTemplates } = usePersonaTemplates({ limit: 100 });
  const deleteTemplate = useDeletePersonaTemplate();

  // Count personas from templates + generated
  const totalPersonas = (templates?.reduce((acc, t) => acc + (t.persona_count || 0), 0) || 0) + generatedPersonas.length;
  const hasPersonas = (templates && templates.length > 0) || generatedPersonas.length > 0;

  const handleSourceClick = (sourceId: string) => {
    switch (sourceId) {
      case 'template':
        setTemplateModalOpen(true);
        break;
      case 'upload':
        setUploadModalOpen(true);
        break;
      case 'generate':
        setGenerateModalOpen(true);
        break;
      case 'search':
        setSearchModalOpen(true);
        break;
    }
  };

  const handleRefresh = () => {
    refetchTemplates();
  };

  const handleViewPersona = (persona: Record<string, unknown>) => {
    setSelectedPersona(persona);
    setDetailsModalOpen(true);
  };

  const handleRemoveTemplate = async (templateId: string) => {
    try {
      await deleteTemplate.mutateAsync(templateId);
    } catch {
      // Error handled by React Query
    }
  };

  // Handle AI-generated personas
  const handleGeneratedPersonas = (personas: GeneratedPersona[]) => {
    setGeneratedPersonas((prev) => [...prev, ...personas]);
  };

  const handleRemoveGeneratedPersona = (personaId: string) => {
    setGeneratedPersonas((prev) => prev.filter((p) => p.id !== personaId));
  };

  const handleClearGeneratedPersonas = () => {
    setGeneratedPersonas([]);
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
          <Users className="w-3.5 h-3.5 md:w-4 md:h-4 text-cyan-400" />
          <span className="text-[10px] md:text-xs font-mono text-white/40 uppercase tracking-wider">
            Data & Personas
          </span>
        </div>
        <h1 className="text-lg md:text-xl font-mono font-bold text-white">Configure Personas</h1>
        <p className="text-xs md:text-sm font-mono text-white/50 mt-1">
          Define and configure the agents that will participate in your simulation
        </p>
      </div>

      {/* Status Banner */}
      <div
        className={cn(
          'max-w-3xl mb-6 p-4 border',
          hasPersonas
            ? 'bg-green-500/10 border-green-500/30'
            : 'bg-yellow-500/10 border-yellow-500/30'
        )}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {hasPersonas ? (
              <CheckCircle className="w-4 h-4 text-green-400" />
            ) : (
              <Database className="w-4 h-4 text-yellow-400" />
            )}
            <span
              className={cn(
                'text-sm font-mono',
                hasPersonas ? 'text-green-400' : 'text-yellow-400'
              )}
            >
              {hasPersonas
                ? `${templates?.length} template(s) with ${totalPersonas} personas`
                : 'No personas configured yet'}
            </span>
          </div>
          {hasPersonas && (
            <Button variant="ghost" size="sm" onClick={handleRefresh} className="text-xs">
              <RefreshCw className={cn('w-3 h-3 mr-1', loadingTemplates && 'animate-spin')} />
              Refresh
            </Button>
          )}
        </div>
        <p className="text-xs font-mono text-white/50 mt-1">
          {hasPersonas
            ? 'You can add more personas or proceed to define rules.'
            : 'Choose a method below to add personas to your project.'}
        </p>
      </div>

      {/* Persona Source Options */}
      <div className="max-w-3xl">
        <h2 className="text-xs font-mono text-white/40 uppercase tracking-wider mb-4">
          Select Persona Source
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {personaSources.map((source) => {
            const Icon = source.icon;
            const colorClasses = {
              cyan: 'hover:bg-cyan-500/10 hover:border-cyan-500/30',
              purple: 'hover:bg-purple-500/10 hover:border-purple-500/30',
              amber: 'hover:bg-amber-500/10 hover:border-amber-500/30',
              green: 'hover:bg-green-500/10 hover:border-green-500/30',
            }[source.color];

            const iconColor = {
              cyan: 'text-cyan-400',
              purple: 'text-purple-400',
              amber: 'text-amber-400',
              green: 'text-green-400',
            }[source.color];

            return (
              <button
                key={source.id}
                onClick={() => handleSourceClick(source.id)}
                className={cn(
                  'flex items-start gap-3 p-4 bg-white/5 border border-white/10 transition-all text-left',
                  colorClasses
                )}
              >
                <div className="w-10 h-10 bg-white/5 flex items-center justify-center flex-shrink-0">
                  <Icon className={cn('w-5 h-5', iconColor)} />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-sm font-mono font-bold text-white">{source.name}</h3>
                  <p className="text-xs font-mono text-white/50 mt-1">{source.description}</p>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Personas Display */}
      <div className="max-w-3xl mt-8">
        {loadingTemplates ? (
          <div className="bg-white/5 border border-white/10 p-8 text-center">
            <Loader2 className="w-8 h-8 animate-spin text-cyan-400 mx-auto mb-4" />
            <p className="text-sm font-mono text-white/60">Loading personas...</p>
          </div>
        ) : hasPersonas ? (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-mono text-white/40 uppercase tracking-wider">
                Persona Templates ({templates?.length})
              </h2>
              <Button
                size="sm"
                onClick={() => setTemplateModalOpen(true)}
                className="text-xs"
              >
                <Plus className="w-3 h-3 mr-2" />
                ADD MORE
              </Button>
            </div>
            {templates?.map((template) => (
              <div
                key={template.id}
                className="flex items-center justify-between p-4 bg-white/5 border border-white/10 hover:border-white/20 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-gradient-to-br from-cyan-500 to-blue-500 flex items-center justify-center">
                    <Users className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h3 className="text-sm font-mono font-bold text-white">{template.name}</h3>
                    <p className="text-xs font-mono text-white/50">
                      {template.persona_count || 0} personas • {template.region || 'Global'}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() =>
                      handleViewPersona({
                        id: template.id,
                        name: template.name,
                        description: template.description,
                        region: template.region,
                        source_type: template.source_type,
                        persona_count: template.persona_count,
                      })
                    }
                    className="text-xs"
                  >
                    <Eye className="w-3 h-3 mr-1" />
                    View
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleRemoveTemplate(template.id)}
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
              <Users className="w-8 h-8 text-white/20" />
            </div>
            <h3 className="text-sm font-mono text-white/60 mb-2">Personas will appear here</h3>
            <p className="text-xs font-mono text-white/40 mb-4">
              Select a source above to start building your persona pool
            </p>
            <Button size="sm" className="text-xs font-mono" onClick={() => setTemplateModalOpen(true)}>
              <Plus className="w-3 h-3 mr-2" />
              ADD PERSONAS
            </Button>
          </div>
        )}

        {/* AI Generated Personas Section */}
        {generatedPersonas.length > 0 && (
          <div className="mt-6 space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-mono text-amber-400 uppercase tracking-wider flex items-center gap-2">
                <Zap className="w-3 h-3" />
                AI Generated Personas ({generatedPersonas.length})
              </h2>
              <Button
                size="sm"
                variant="ghost"
                onClick={handleClearGeneratedPersonas}
                className="text-xs text-red-400 hover:text-red-300"
              >
                <Trash2 className="w-3 h-3 mr-2" />
                Clear All
              </Button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {generatedPersonas.map((persona) => (
                <div
                  key={persona.id}
                  className="p-4 bg-amber-500/5 border border-amber-500/20 hover:border-amber-500/40 transition-colors"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <h4 className="text-sm font-mono font-bold text-white">{persona.name}</h4>
                      <p className="text-xs font-mono text-white/50">
                        {persona.age} • {persona.gender} • {persona.occupation}
                      </p>
                    </div>
                    <div className="flex gap-1">
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-6 w-6 p-0"
                        onClick={() => handleViewPersona(persona as unknown as Record<string, unknown>)}
                      >
                        <Eye className="w-3 h-3" />
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-6 w-6 p-0 text-red-400 hover:text-red-300"
                        onClick={() => handleRemoveGeneratedPersona(persona.id)}
                      >
                        <X className="w-3 h-3" />
                      </Button>
                    </div>
                  </div>
                  <div className="space-y-1">
                    <p className="text-xs font-mono text-white/40">
                      <span className="text-white/60">Location:</span> {persona.location}
                    </p>
                    <p className="text-xs font-mono text-white/40">
                      <span className="text-white/60">Income:</span> {persona.income_bracket} • <span className="text-white/60">Education:</span> {persona.education_level}
                    </p>
                    {persona.personality_traits && persona.personality_traits.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {persona.personality_traits.slice(0, 3).map((trait, i) => (
                          <span key={i} className="px-1.5 py-0.5 text-[10px] font-mono bg-amber-500/10 text-amber-400 border border-amber-500/20">
                            {trait}
                          </span>
                        ))}
                      </div>
                    )}
                    {persona.cultural_context && (
                      <p className="text-[10px] font-mono text-white/40 mt-2 italic line-clamp-2">
                        {persona.cultural_context}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
            <p className="text-[10px] font-mono text-amber-400/60 mt-2">
              Note: These personas are previews. Backend integration coming soon.
            </p>
          </div>
        )}
      </div>

      {/* Navigation CTA */}
      <div className="max-w-3xl mt-8 pt-6 border-t border-white/10">
        <div className="flex items-center justify-between">
          <p className="text-xs font-mono text-white/40">
            {hasPersonas ? 'Ready to define rules?' : 'Add personas first, then define rules'}
          </p>
          <Link href={`/p/${projectId}/rules`}>
            <Button
              className={cn(
                'text-xs font-mono',
                hasPersonas
                  ? 'bg-cyan-500 hover:bg-cyan-600 text-black'
                  : 'bg-white/10 text-white/40'
              )}
            >
              Next: Rules & Assumptions
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
            <span>DATA & PERSONAS</span>
          </div>
          <span>AGENTVERSE v1.0</span>
        </div>
      </div>

      {/* Modals */}
      <PersonaTemplatesModal
        open={templateModalOpen}
        onOpenChange={setTemplateModalOpen}
        projectId={projectId}
        onSuccess={refetchTemplates}
      />
      <UploadDataModal
        open={uploadModalOpen}
        onOpenChange={setUploadModalOpen}
        onSuccess={refetchTemplates}
      />
      <GeneratePersonasModal
        open={generateModalOpen}
        onOpenChange={setGenerateModalOpen}
        projectId={projectId}
        onGenerated={handleGeneratedPersonas}
      />
      <DeepSearchModal
        open={searchModalOpen}
        onOpenChange={setSearchModalOpen}
        projectId={projectId}
        onSuccess={refetchTemplates}
      />
      <PersonaDetailsModal
        open={detailsModalOpen}
        onOpenChange={setDetailsModalOpen}
        persona={selectedPersona}
      />
    </div>
  );
}
