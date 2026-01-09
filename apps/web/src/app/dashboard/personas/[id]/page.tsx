'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  ArrowLeft,
  UserCircle,
  Users,
  Globe,
  Calendar,
  Target,
  Briefcase,
  Brain,
  Heart,
  ShoppingBag,
  Loader2,
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
  Terminal,
  Gamepad2,
} from 'lucide-react';
import { usePersonaTemplate, usePersonas } from '@/hooks/useApi';
import { cn } from '@/lib/utils';

const sourceTypeLabels: Record<string, string> = {
  ai_generated: 'AI GENERATED',
  file_upload: 'FILE UPLOAD',
  ai_research: 'AI RESEARCH',
};

export default function PersonaDetailPage() {
  const params = useParams();
  const templateId = params.id as string;

  const { data: template, isLoading: templateLoading } = usePersonaTemplate(templateId);
  const { data: personas, isLoading: personasLoading } = usePersonas(templateId, { limit: 20 });

  if (templateLoading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-white/40" />
      </div>
    );
  }

  if (!template) {
    return (
      <div className="min-h-screen bg-black p-6">
        <div className="bg-red-500/10 border border-red-500/30 p-6">
          <p className="text-sm font-mono text-red-400">Template not found.</p>
          <Link href="/dashboard/personas">
            <Button variant="outline" className="mt-4 font-mono text-xs border-white/20 text-white/60 hover:bg-white/5">
              BACK TO PERSONAS
            </Button>
          </Link>
        </div>
      </div>
    );
  }

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
      </div>

      {/* Template Info Card */}
      <div className="bg-white/5 border border-white/10 p-6 mb-8">
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-4">
            <div className="w-14 h-14 bg-white/10 flex items-center justify-center">
              <UserCircle className="w-8 h-8 text-white/60" />
            </div>
            <div>
              <div className="flex items-center gap-2 mb-1">
                <Users className="w-4 h-4 text-white/60" />
                <span className="text-xs font-mono text-white/40 uppercase tracking-wider">Persona Template</span>
              </div>
              <h1 className="text-xl font-mono font-bold text-white">{template.name}</h1>
              <p className="text-sm font-mono text-white/50 mt-1">
                {template.description || 'No description provided'}
              </p>
              <div className="flex items-center gap-3 mt-4">
                <span className="px-2 py-0.5 bg-white/10 text-white/60 text-[10px] font-mono uppercase">
                  {template.region.toUpperCase()}
                </span>
                <span className="px-2 py-0.5 bg-white/10 text-white/60 text-[10px] font-mono uppercase">
                  {sourceTypeLabels[template.source_type] || template.source_type}
                </span>
                {template.topic && (
                  <span className="px-2 py-0.5 bg-white/10 text-white/60 text-[10px] font-mono">
                    {template.topic}
                  </span>
                )}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* Vi World Button */}
            {template.persona_count > 0 && (
              <Link href={`/dashboard/personas/${templateId}/world`}>
                <Button className="bg-gradient-to-r from-cyan-600 to-purple-600 hover:from-cyan-500 hover:to-purple-500 text-white font-mono text-xs">
                  <Gamepad2 className="w-4 h-4 mr-2" />
                  VI WORLD
                </Button>
              </Link>
            )}

            <div className="text-right">
              <div className="text-3xl font-mono font-bold text-white">{template.persona_count}</div>
              <div className="text-[10px] font-mono text-white/40 uppercase">Personas</div>
            </div>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-4 gap-6 mt-8 pt-6 border-t border-white/10">
          <div>
            <div className="flex items-center gap-2 text-white/40 text-[10px] font-mono uppercase">
              <Globe className="w-3 h-3" />
              Region
            </div>
            <div className="font-mono text-white mt-1">{template.region}</div>
            {template.country && (
              <div className="text-xs font-mono text-white/40">{template.country}</div>
            )}
          </div>
          <div>
            <div className="flex items-center gap-2 text-white/40 text-[10px] font-mono uppercase">
              <Target className="w-3 h-3" />
              Confidence
            </div>
            <div className="font-mono text-white mt-1">
              {Math.round(template.confidence_score * 100)}%
            </div>
          </div>
          <div>
            <div className="flex items-center gap-2 text-white/40 text-[10px] font-mono uppercase">
              <Briefcase className="w-3 h-3" />
              Industry
            </div>
            <div className="font-mono text-white mt-1">{template.industry || 'General'}</div>
          </div>
          <div>
            <div className="flex items-center gap-2 text-white/40 text-[10px] font-mono uppercase">
              <Calendar className="w-3 h-3" />
              Created
            </div>
            <div className="font-mono text-white mt-1">
              {new Date(template.created_at).toLocaleDateString()}
            </div>
          </div>
        </div>

        {/* Keywords */}
        {template.keywords && template.keywords.length > 0 && (
          <div className="mt-6 pt-6 border-t border-white/10">
            <div className="text-[10px] font-mono text-white/40 uppercase mb-2">Keywords</div>
            <div className="flex flex-wrap gap-2">
              {template.keywords.map((keyword: string, idx: number) => (
                <span
                  key={idx}
                  className="px-2 py-1 bg-white/5 border border-white/10 text-white/60 text-xs font-mono"
                >
                  {keyword}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Personas Section */}
      <div className="bg-white/5 border border-white/10">
        <div className="p-6 border-b border-white/10">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-mono font-bold text-white uppercase">Generated Personas</h2>
              <p className="text-xs font-mono text-white/40 mt-1">
                Sample personas from this template
              </p>
            </div>
            <div className="text-xs font-mono text-white/40">
              Showing {personas?.length || 0} of {template.persona_count}
            </div>
          </div>
        </div>

        {personasLoading ? (
          <div className="p-8 text-center">
            <Loader2 className="w-5 h-5 animate-spin text-white/40 mx-auto" />
          </div>
        ) : personas && personas.length > 0 ? (
          <div className="divide-y divide-white/5">
            {personas.map((persona: any) => (
              <PersonaCard key={persona.id} persona={persona} />
            ))}
          </div>
        ) : (
          <div className="p-8 text-center">
            <Users className="w-10 h-10 mx-auto mb-4 text-white/20" />
            <p className="text-sm font-mono text-white/40">No personas generated yet</p>
          </div>
        )}
      </div>

      {/* Footer Status */}
      <div className="mt-8 pt-4 border-t border-white/5">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-1">
            <Terminal className="w-3 h-3" />
            <span>PERSONA DETAIL MODULE</span>
          </div>
          <span>AGENTVERSE v1.0.0</span>
        </div>
      </div>
    </div>
  );
}

function PersonaCard({ persona }: { persona: any }) {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const demographics = persona.demographics || {};
  const professional = persona.professional || {};
  const psychographics = persona.psychographics || {};
  const behavioral = persona.behavioral || {};
  const interests = persona.interests || {};

  const handleCopyPrompt = async () => {
    if (persona.full_prompt) {
      await navigator.clipboard.writeText(persona.full_prompt);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="p-6">
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 bg-white/10 flex items-center justify-center font-mono font-bold text-white">
            {demographics.name?.[0] || 'P'}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-mono font-bold text-white">
                {demographics.name || 'Anonymous Persona'}
              </h3>
              <span className="text-[10px] px-1.5 py-0.5 bg-white/10 text-white/60 font-mono">
                {Math.round(persona.confidence_score * 100)}%
              </span>
            </div>
            <p className="text-xs font-mono text-white/40 mt-1">
              {demographics.age} years old, {demographics.gender} | {demographics.location || demographics.city}
            </p>
            <p className="text-xs font-mono text-white/50 mt-1">
              {professional.occupation || professional.job_title} at{' '}
              {professional.company_type || 'Unknown Company'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {persona.full_prompt && (
            <Button variant="ghost" size="sm" onClick={handleCopyPrompt} className="text-white/40 hover:text-white hover:bg-white/5">
              {copied ? (
                <Check className="w-3 h-3 text-green-400" />
              ) : (
                <Copy className="w-3 h-3" />
              )}
            </Button>
          )}
          <Button variant="ghost" size="sm" onClick={() => setExpanded(!expanded)} className="text-white/40 hover:text-white hover:bg-white/5">
            {expanded ? (
              <ChevronUp className="w-3 h-3" />
            ) : (
              <ChevronDown className="w-3 h-3" />
            )}
          </Button>
        </div>
      </div>

      {expanded && (
        <div className="mt-6 grid grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Demographics */}
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-xs font-mono font-bold text-white">
              <UserCircle className="w-3 h-3 text-white/60" />
              DEMOGRAPHICS
            </div>
            <div className="space-y-1 text-xs font-mono">
              <DetailRow label="Education" value={demographics.education} />
              <DetailRow label="Marital Status" value={demographics.marital_status} />
              <DetailRow label="Income" value={demographics.income_bracket} />
              <DetailRow label="Housing" value={demographics.housing_type} />
            </div>
          </div>

          {/* Professional */}
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-xs font-mono font-bold text-white">
              <Briefcase className="w-3 h-3 text-white/60" />
              PROFESSIONAL
            </div>
            <div className="space-y-1 text-xs font-mono">
              <DetailRow label="Industry" value={professional.industry} />
              <DetailRow label="Experience" value={professional.years_experience} />
              <DetailRow label="Role Level" value={professional.seniority_level} />
              <DetailRow label="Work Style" value={professional.work_arrangement} />
            </div>
          </div>

          {/* Psychographics */}
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-xs font-mono font-bold text-white">
              <Brain className="w-3 h-3 text-white/60" />
              PSYCHOGRAPHICS
            </div>
            <div className="space-y-1 text-xs font-mono">
              <DetailRow label="Personality" value={psychographics.mbti_type} />
              <DetailRow label="Risk Tolerance" value={psychographics.risk_tolerance} />
              <DetailRow
                label="Values"
                value={psychographics.core_values?.slice(0, 2).join(', ')}
              />
              <DetailRow label="Decision Style" value={psychographics.decision_style} />
            </div>
          </div>

          {/* Behavioral */}
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-xs font-mono font-bold text-white">
              <ShoppingBag className="w-3 h-3 text-white/60" />
              BEHAVIORAL
            </div>
            <div className="space-y-1 text-xs font-mono">
              <DetailRow label="Shopping" value={behavioral.shopping_frequency} />
              <DetailRow label="Brand Loyalty" value={behavioral.brand_loyalty} />
              <DetailRow
                label="Tech Adoption"
                value={behavioral.technology_adoption}
              />
              <DetailRow
                label="Social Platforms"
                value={behavioral.social_media_primary?.slice(0, 2).join(', ')}
              />
            </div>
          </div>

          {/* Interests - Full Width */}
          {interests.hobbies && interests.hobbies.length > 0 && (
            <div className="col-span-2 lg:col-span-4 pt-4 border-t border-white/10">
              <div className="flex items-center gap-2 text-xs font-mono font-bold text-white mb-2">
                <Heart className="w-3 h-3 text-white/60" />
                INTERESTS & HOBBIES
              </div>
              <div className="flex flex-wrap gap-2">
                {interests.hobbies.map((hobby: string, idx: number) => (
                  <span
                    key={idx}
                    className="px-2 py-1 bg-white/5 border border-white/10 text-white/60 text-[10px] font-mono"
                  >
                    {hobby}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value?: string | number }) {
  if (!value) return null;
  return (
    <div className="flex justify-between">
      <span className="text-white/40">{label}:</span>
      <span className="text-white">{value}</span>
    </div>
  );
}
