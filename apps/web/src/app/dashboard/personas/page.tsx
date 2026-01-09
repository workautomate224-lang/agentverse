'use client';

import { useState, useMemo } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  UserCircle,
  Search,
  Users,
  FileSpreadsheet,
  Brain,
  Sparkles,
  Upload,
  Plus,
  CheckCircle,
  ChevronRight,
  FolderOpen,
  Tag,
  X,
  MoreVertical,
  Trash2,
  Eye,
  Gamepad2,
} from 'lucide-react';
import { usePersonaTemplates, useInfinitePersonas, useDeletePersonaTemplate } from '@/hooks/useApi';
import { PersonaTemplate, PersonaRecord } from '@/lib/api';
import { cn } from '@/lib/utils';
import { InfiniteScroll } from '@/components/ui/virtualized-list';
import { SkeletonList } from '@/components/ui/skeleton';

// Source types with icons
const sourceConfig: Record<string, { icon: React.ReactNode; label: string; color: string }> = {
  ai_generated: { icon: <Sparkles className="w-3 h-3" />, label: 'GENERATED', color: 'text-cyan-400' },
  file_upload: { icon: <FileSpreadsheet className="w-3 h-3" />, label: 'UPLOADED', color: 'text-yellow-400' },
  ai_research: { icon: <Brain className="w-3 h-3" />, label: 'DEEP SEARCH', color: 'text-purple-400' },
};

// Segment type for UI
interface Segment {
  id: string;
  name: string;
  count: number;
}

export default function PersonasStudioPage() {
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);
  const [selectedPersonaId, setSelectedPersonaId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [sourceFilter, setSourceFilter] = useState<string>('');
  const [regionFilter, setRegionFilter] = useState<string>('');
  const [showInspector, setShowInspector] = useState(false);

  // Fetch templates (sources)
  const { data: templates, isLoading: templatesLoading, refetch } = usePersonaTemplates({
    region: regionFilter || undefined,
    source_type: sourceFilter || undefined,
  });

  // Fetch personas for selected template with infinite scroll
  const {
    data: personasData,
    isLoading: personasLoading,
    isFetchingNextPage,
    hasNextPage,
    fetchNextPage,
  } = useInfinitePersonas(selectedTemplateId || '', 50);

  // Flatten paginated personas
  const personas = personasData?.pages.flatMap(page => page.items) || [];

  // Derive segments from templates (placeholder - will be API-driven later)
  const segments: Segment[] = useMemo(() => {
    if (!templates) return [];
    // Group by region for now as pseudo-segments
    const regionCounts: Record<string, number> = {};
    templates.forEach((t) => {
      regionCounts[t.region] = (regionCounts[t.region] || 0) + t.persona_count;
    });
    return Object.entries(regionCounts).map(([region, count]) => ({
      id: region,
      name: region.toUpperCase(),
      count,
    }));
  }, [templates]);

  // Filter templates
  const filteredTemplates = templates?.filter((t) =>
    t.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    t.description?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Stats
  const totalPersonas = templates?.reduce((sum, t) => sum + t.persona_count, 0) || 0;
  const generatedCount = templates?.filter((t) => t.source_type === 'ai_generated')
    .reduce((sum, t) => sum + t.persona_count, 0) || 0;
  const uploadedCount = templates?.filter((t) => t.source_type === 'file_upload')
    .reduce((sum, t) => sum + t.persona_count, 0) || 0;
  const researchCount = templates?.filter((t) => t.source_type === 'ai_research')
    .reduce((sum, t) => sum + t.persona_count, 0) || 0;

  const handleSelectTemplate = (templateId: string) => {
    setSelectedTemplateId(templateId);
    setSelectedPersonaId(null);
    setShowInspector(false);
  };

  const handleSelectPersona = (personaId: string) => {
    setSelectedPersonaId(personaId);
    setShowInspector(true);
  };

  const selectedPersona = personas?.find((p) => p.id === selectedPersonaId);
  const selectedTemplate = templates?.find((t) => t.id === selectedTemplateId);

  return (
    <div className="min-h-screen bg-black flex">
      {/* Left Panel - Sources & Segments */}
      <div className="w-64 border-r border-white/10 flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-white/10">
          <div className="flex items-center gap-2 mb-1">
            <UserCircle className="w-4 h-4 text-white/60" />
            <span className="text-xs font-mono text-white/40 uppercase tracking-wider">Personas Studio</span>
          </div>
          <h1 className="text-lg font-mono font-bold text-white">Sources</h1>
        </div>

        {/* Quick Stats */}
        <div className="p-3 border-b border-white/10">
          <div className="grid grid-cols-2 gap-2 text-xs font-mono">
            <div className="bg-white/5 p-2">
              <span className="text-white/40">Total</span>
              <p className="text-white font-bold">{totalPersonas}</p>
            </div>
            <div className="bg-white/5 p-2">
              <span className="text-white/40">Sources</span>
              <p className="text-white font-bold">{templates?.length || 0}</p>
            </div>
          </div>
        </div>

        {/* Source Types */}
        <div className="p-3 border-b border-white/10">
          <p className="text-[10px] font-mono text-white/40 uppercase mb-2">By Source</p>
          <div className="space-y-1">
            <button
              onClick={() => setSourceFilter('')}
              className={cn(
                "w-full flex items-center justify-between px-2 py-1.5 text-xs font-mono transition-colors",
                sourceFilter === '' ? "bg-white/10 text-white" : "text-white/60 hover:bg-white/5"
              )}
            >
              <div className="flex items-center gap-2">
                <FolderOpen className="w-3 h-3" />
                <span>All Sources</span>
              </div>
              <span className="text-white/40">{totalPersonas}</span>
            </button>
            <button
              onClick={() => setSourceFilter('file_upload')}
              className={cn(
                "w-full flex items-center justify-between px-2 py-1.5 text-xs font-mono transition-colors",
                sourceFilter === 'file_upload' ? "bg-white/10 text-yellow-400" : "text-white/60 hover:bg-white/5"
              )}
            >
              <div className="flex items-center gap-2">
                <FileSpreadsheet className="w-3 h-3" />
                <span>Uploaded</span>
              </div>
              <span className="text-white/40">{uploadedCount}</span>
            </button>
            <button
              onClick={() => setSourceFilter('ai_generated')}
              className={cn(
                "w-full flex items-center justify-between px-2 py-1.5 text-xs font-mono transition-colors",
                sourceFilter === 'ai_generated' ? "bg-white/10 text-cyan-400" : "text-white/60 hover:bg-white/5"
              )}
            >
              <div className="flex items-center gap-2">
                <Sparkles className="w-3 h-3" />
                <span>Generated</span>
              </div>
              <span className="text-white/40">{generatedCount}</span>
            </button>
            <button
              onClick={() => setSourceFilter('ai_research')}
              className={cn(
                "w-full flex items-center justify-between px-2 py-1.5 text-xs font-mono transition-colors",
                sourceFilter === 'ai_research' ? "bg-white/10 text-purple-400" : "text-white/60 hover:bg-white/5"
              )}
            >
              <div className="flex items-center gap-2">
                <Brain className="w-3 h-3" />
                <span>Deep Search</span>
              </div>
              <span className="text-white/40">{researchCount}</span>
            </button>
          </div>
        </div>

        {/* Segments */}
        <div className="flex-1 overflow-auto p-3">
          <div className="flex items-center justify-between mb-2">
            <p className="text-[10px] font-mono text-white/40 uppercase">Segments</p>
            <Button
              variant="ghost"
              size="sm"
              className="h-5 px-1.5 text-[10px] font-mono text-white/40 hover:text-white"
            >
              <Plus className="w-2.5 h-2.5 mr-1" />
              NEW
            </Button>
          </div>
          <div className="space-y-1">
            {segments.map((segment) => (
              <button
                key={segment.id}
                onClick={() => setRegionFilter(segment.id)}
                className={cn(
                  "w-full flex items-center justify-between px-2 py-1.5 text-xs font-mono transition-colors",
                  regionFilter === segment.id ? "bg-white/10 text-white" : "text-white/60 hover:bg-white/5"
                )}
              >
                <div className="flex items-center gap-2">
                  <Tag className="w-3 h-3" />
                  <span>{segment.name}</span>
                </div>
                <span className="text-white/40">{segment.count}</span>
              </button>
            ))}
            {regionFilter && (
              <button
                onClick={() => setRegionFilter('')}
                className="w-full flex items-center gap-2 px-2 py-1.5 text-xs font-mono text-white/40 hover:text-white hover:bg-white/5"
              >
                <X className="w-3 h-3" />
                <span>Clear filter</span>
              </button>
            )}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="p-3 border-t border-white/10 space-y-2">
          <Link href="/dashboard/personas/new?mode=upload" className="block">
            <Button size="sm" variant="outline" className="w-full justify-start text-xs font-mono">
              <Upload className="w-3 h-3 mr-2" />
              IMPORT PERSONAS
            </Button>
          </Link>
          <Link href="/dashboard/personas/new?mode=generate" className="block">
            <Button size="sm" variant="outline" className="w-full justify-start text-xs font-mono">
              <Sparkles className="w-3 h-3 mr-2" />
              GENERATE
            </Button>
          </Link>
          <Link href="/dashboard/personas/new?mode=research" className="block">
            <Button size="sm" variant="outline" className="w-full justify-start text-xs font-mono">
              <Brain className="w-3 h-3 mr-2" />
              DEEP SEARCH
            </Button>
          </Link>
        </div>
      </div>

      {/* Center Panel - Persona List */}
      <div className="flex-1 flex flex-col">
        {/* Top Bar */}
        <div className="p-4 border-b border-white/10 flex items-center gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3 h-3 text-white/30" />
            <input
              type="text"
              placeholder="Search personas..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-2 bg-white/5 border border-white/10 text-xs font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-white/30"
            />
          </div>
          <select
            value={regionFilter}
            onChange={(e) => setRegionFilter(e.target.value)}
            className="px-3 py-2 bg-white/5 border border-white/10 text-xs font-mono text-white appearance-none focus:outline-none focus:border-white/30"
          >
            <option value="">All Regions</option>
            <option value="us">United States</option>
            <option value="europe">Europe</option>
            <option value="asia">Southeast Asia</option>
            <option value="china">China</option>
          </select>
          <Button size="sm" variant="outline" className="text-xs font-mono">
            <CheckCircle className="w-3 h-3 mr-2" />
            VALIDATE SET
          </Button>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-auto p-4">
          {templatesLoading ? (
            <SkeletonList items={6} />
          ) : !templates || templates.length === 0 ? (
            <EmptyState />
          ) : (
            <div className="space-y-4">
              {/* Template/Source List */}
              {!selectedTemplateId ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {filteredTemplates?.map((template) => (
                    <SourceCard
                      key={template.id}
                      template={template}
                      onSelect={() => handleSelectTemplate(template.id)}
                      onDelete={() => refetch()}
                    />
                  ))}
                </div>
              ) : (
                /* Persona List for Selected Template */
                <div>
                  {/* Breadcrumb */}
                  <div className="flex items-center gap-2 mb-4">
                    <button
                      onClick={() => setSelectedTemplateId(null)}
                      className="text-xs font-mono text-white/60 hover:text-white"
                    >
                      Sources
                    </button>
                    <ChevronRight className="w-3 h-3 text-white/30" />
                    <span className="text-xs font-mono text-white">
                      {selectedTemplate?.name}
                    </span>
                    <span className="text-xs font-mono text-white/40">
                      ({selectedTemplate?.persona_count} personas)
                    </span>
                  </div>

                  {personasLoading && personas.length === 0 ? (
                    <SkeletonList items={8} className="space-y-1" />
                  ) : personas.length === 0 ? (
                    <div className="bg-white/5 border border-white/10 p-8 text-center">
                      <p className="text-sm font-mono text-white/60">No personas in this source</p>
                    </div>
                  ) : (
                    <div className="space-y-1">
                      {/* Header Row */}
                      <div className="grid grid-cols-12 gap-2 px-3 py-2 text-[10px] font-mono text-white/40 uppercase border-b border-white/10">
                        <div className="col-span-4">Persona</div>
                        <div className="col-span-2">Source</div>
                        <div className="col-span-2">Confidence</div>
                        <div className="col-span-2">Region</div>
                        <div className="col-span-2">Updated</div>
                      </div>
                      {/* Persona Rows with Infinite Scroll */}
                      <InfiniteScroll
                        onLoadMore={() => fetchNextPage()}
                        hasMore={hasNextPage || false}
                        isLoading={isFetchingNextPage}
                        endMessage="All personas loaded"
                      >
                        {personas.map((persona) => (
                          <PersonaRow
                            key={persona.id}
                            persona={persona}
                            isSelected={selectedPersonaId === persona.id}
                            onSelect={() => handleSelectPersona(persona.id)}
                          />
                        ))}
                      </InfiniteScroll>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Right Panel - Inspector Drawer */}
      {showInspector && selectedPersona && (
        <div className="w-80 border-l border-white/10 flex flex-col">
          <div className="p-4 border-b border-white/10 flex items-center justify-between">
            <h2 className="text-sm font-mono font-bold text-white">Persona Inspector</h2>
            <button
              onClick={() => setShowInspector(false)}
              className="p-1 hover:bg-white/10 transition-colors"
            >
              <X className="w-4 h-4 text-white/60" />
            </button>
          </div>
          <div className="flex-1 overflow-auto p-4">
            <PersonaInspector persona={selectedPersona} template={selectedTemplate} />
          </div>
        </div>
      )}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="bg-white/5 border border-white/10">
      <div className="p-12 text-center">
        <div className="w-16 h-16 bg-white/5 flex items-center justify-center mx-auto mb-4">
          <Users className="w-8 h-8 text-white/30" />
        </div>
        <h3 className="text-lg font-mono font-bold text-white mb-2">No Personas Yet</h3>
        <p className="text-sm font-mono text-white/60 mb-6 max-w-md mx-auto">
          Start building your persona set by importing data, generating from goals, or using deep search.
        </p>
        <div className="flex items-center justify-center gap-3">
          <Link href="/dashboard/personas/new?mode=upload">
            <Button size="sm">
              <Upload className="w-3 h-3 mr-2" />
              IMPORT
            </Button>
          </Link>
          <Link href="/dashboard/personas/new?mode=generate">
            <Button size="sm" variant="outline">
              <Sparkles className="w-3 h-3 mr-2" />
              GENERATE
            </Button>
          </Link>
          <Link href="/dashboard/personas/new?mode=research">
            <Button size="sm" variant="outline">
              <Brain className="w-3 h-3 mr-2" />
              DEEP SEARCH
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}

function SourceCard({
  template,
  onSelect,
  onDelete,
}: {
  template: PersonaTemplate;
  onSelect: () => void;
  onDelete: () => void;
}) {
  const [showMenu, setShowMenu] = useState(false);
  const deleteTemplate = useDeletePersonaTemplate();

  const config = sourceConfig[template.source_type] || sourceConfig.file_upload;

  const handleDelete = async () => {
    if (confirm('Delete this persona source?')) {
      try {
        await deleteTemplate.mutateAsync(template.id);
        onDelete();
      } catch {
        // Error handled by mutation
      }
    }
    setShowMenu(false);
  };

  return (
    <div
      className="bg-white/5 border border-white/10 hover:bg-white/[0.07] hover:border-white/20 transition-all cursor-pointer"
      onClick={onSelect}
    >
      <div className="p-4">
        <div className="flex items-start justify-between mb-3">
          <div className={cn("flex items-center gap-2 text-xs font-mono", config.color)}>
            {config.icon}
            <span>{config.label}</span>
          </div>
          <div className="relative" onClick={(e) => e.stopPropagation()}>
            <button
              onClick={() => setShowMenu(!showMenu)}
              className="p-1.5 hover:bg-white/10 transition-colors"
            >
              <MoreVertical className="w-3 h-3 text-white/40" />
            </button>
            {showMenu && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setShowMenu(false)} />
                <div className="absolute right-0 mt-1 w-32 bg-black border border-white/20 py-1 z-20">
                  <Link
                    href={`/dashboard/personas/${template.id}`}
                    className="flex items-center gap-2 px-3 py-1.5 text-xs font-mono text-white/60 hover:bg-white/10"
                    onClick={() => setShowMenu(false)}
                  >
                    <Eye className="w-3 h-3" />
                    Details
                  </Link>
                  {template.persona_count > 0 && (
                    <Link
                      href={`/dashboard/personas/${template.id}/world`}
                      className="flex items-center gap-2 px-3 py-1.5 text-xs font-mono text-cyan-400 hover:bg-white/10"
                      onClick={() => setShowMenu(false)}
                    >
                      <Gamepad2 className="w-3 h-3" />
                      Vi World
                    </Link>
                  )}
                  <button
                    onClick={handleDelete}
                    disabled={deleteTemplate.isPending}
                    className="flex items-center gap-2 w-full px-3 py-1.5 text-xs font-mono text-red-400 hover:bg-white/10 disabled:opacity-50"
                  >
                    <Trash2 className="w-3 h-3" />
                    Delete
                  </button>
                </div>
              </>
            )}
          </div>
        </div>

        <h3 className="text-sm font-mono font-bold text-white mb-1">{template.name}</h3>
        <p className="text-xs font-mono text-white/40 mb-3 line-clamp-2">
          {template.description || 'No description'}
        </p>

        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-white/60 px-2 py-0.5 bg-white/5">
            {template.persona_count} personas
          </span>
          <span className={cn(
            "text-xs font-mono px-2 py-0.5",
            template.confidence_score >= 0.8 ? "text-green-400 bg-green-500/10" :
            template.confidence_score >= 0.5 ? "text-yellow-400 bg-yellow-500/10" :
            "text-red-400 bg-red-500/10"
          )}>
            {Math.round(template.confidence_score * 100)}% conf
          </span>
          <span className="text-xs font-mono text-white/40 px-2 py-0.5 bg-white/5 uppercase">
            {template.region}
          </span>
        </div>
      </div>
    </div>
  );
}

function PersonaRow({
  persona,
  isSelected,
  onSelect,
}: {
  persona: PersonaRecord;
  isSelected: boolean;
  onSelect: () => void;
}) {
  const config = sourceConfig[persona.source_type] || sourceConfig.file_upload;
  const demographics = persona.demographics as Record<string, unknown>;

  return (
    <button
      onClick={onSelect}
      className={cn(
        "w-full grid grid-cols-12 gap-2 px-3 py-2 text-xs font-mono text-left transition-colors",
        isSelected ? "bg-white/10 text-white" : "text-white/60 hover:bg-white/5"
      )}
    >
      <div className="col-span-4 flex items-center gap-2">
        <UserCircle className="w-4 h-4 text-white/30" />
        <span className="truncate">
          {String(demographics?.name || demographics?.occupation || `Persona ${persona.id.slice(0, 8)}`)}
        </span>
      </div>
      <div className={cn("col-span-2 flex items-center gap-1", config.color)}>
        {config.icon}
        <span>{config.label}</span>
      </div>
      <div className="col-span-2">
        <span className={cn(
          persona.confidence_score >= 0.8 ? "text-green-400" :
          persona.confidence_score >= 0.5 ? "text-yellow-400" :
          "text-red-400"
        )}>
          {Math.round(persona.confidence_score * 100)}%
        </span>
      </div>
      <div className="col-span-2 text-white/40 uppercase">
        {String(demographics?.region || demographics?.country || 'N/A')}
      </div>
      <div className="col-span-2 text-white/30">
        {new Date(persona.created_at).toLocaleDateString()}
      </div>
    </button>
  );
}

function PersonaInspector({
  persona,
  template,
}: {
  persona: PersonaRecord;
  template?: PersonaTemplate;
}) {
  const demographics = persona.demographics as Record<string, unknown>;
  const psychographics = persona.psychographics as Record<string, unknown>;
  const behavioral = persona.behavioral as Record<string, unknown>;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-white/10 flex items-center justify-center">
          <UserCircle className="w-6 h-6 text-white/60" />
        </div>
        <div>
          <h3 className="text-sm font-mono font-bold text-white">
            {String(demographics?.name || demographics?.occupation || 'Persona')}
          </h3>
          <p className="text-xs font-mono text-white/40">
            {template?.name || 'Unknown source'}
          </p>
        </div>
      </div>

      {/* Confidence */}
      <div className="bg-white/5 p-3">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[10px] font-mono text-white/40 uppercase">Confidence</span>
          <span className={cn(
            "text-xs font-mono font-bold",
            persona.confidence_score >= 0.8 ? "text-green-400" :
            persona.confidence_score >= 0.5 ? "text-yellow-400" :
            "text-red-400"
          )}>
            {Math.round(persona.confidence_score * 100)}%
          </span>
        </div>
        <div className="w-full h-1 bg-white/10">
          <div
            className={cn(
              "h-full",
              persona.confidence_score >= 0.8 ? "bg-green-400" :
              persona.confidence_score >= 0.5 ? "bg-yellow-400" :
              "bg-red-400"
            )}
            style={{ width: `${persona.confidence_score * 100}%` }}
          />
        </div>
      </div>

      {/* Demographics */}
      <div>
        <h4 className="text-[10px] font-mono text-white/40 uppercase mb-2">Demographics</h4>
        <div className="bg-white/5 p-3 space-y-2">
          {Object.entries(demographics).map(([key, value]) => (
            <div key={key} className="flex items-center justify-between text-xs font-mono">
              <span className="text-white/40 capitalize">{key.replace(/_/g, ' ')}</span>
              <span className="text-white">{String(value)}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Psychographics */}
      {psychographics && Object.keys(psychographics).length > 0 && (
        <div>
          <h4 className="text-[10px] font-mono text-white/40 uppercase mb-2">Psychographics</h4>
          <div className="bg-white/5 p-3 space-y-2">
            {Object.entries(psychographics).slice(0, 5).map(([key, value]) => (
              <div key={key} className="flex items-center justify-between text-xs font-mono">
                <span className="text-white/40 capitalize">{key.replace(/_/g, ' ')}</span>
                <span className="text-white">{typeof value === 'object' ? JSON.stringify(value) : String(value)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Behavioral */}
      {behavioral && Object.keys(behavioral).length > 0 && (
        <div>
          <h4 className="text-[10px] font-mono text-white/40 uppercase mb-2">Behavioral</h4>
          <div className="bg-white/5 p-3 space-y-2">
            {Object.entries(behavioral).slice(0, 5).map(([key, value]) => (
              <div key={key} className="flex items-center justify-between text-xs font-mono">
                <span className="text-white/40 capitalize">{key.replace(/_/g, ' ')}</span>
                <span className="text-white">{typeof value === 'object' ? JSON.stringify(value) : String(value)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="pt-4 border-t border-white/10 space-y-2">
        <Button size="sm" variant="outline" className="w-full text-xs font-mono">
          <Eye className="w-3 h-3 mr-2" />
          VIEW FULL DETAILS
        </Button>
        {template?.persona_count && template.persona_count > 0 && (
          <Link href={`/dashboard/personas/${template?.id}/world`} className="block">
            <Button size="sm" variant="outline" className="w-full text-xs font-mono text-cyan-400 border-cyan-400/30 hover:bg-cyan-400/10">
              <Gamepad2 className="w-3 h-3 mr-2" />
              OPEN VI WORLD
            </Button>
          </Link>
        )}
      </div>
    </div>
  );
}
