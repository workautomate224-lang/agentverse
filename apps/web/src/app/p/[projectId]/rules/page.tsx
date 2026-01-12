'use client';

/**
 * Rules & Logic Page (Placeholder)
 * Define decision rules and behavioral patterns
 */

import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  ScrollText,
  Plus,
  ArrowLeft,
  Terminal,
  GitBranch,
  Sparkles,
  FileCode,
  Library,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Rule template categories
const ruleCategories = [
  {
    id: 'decision',
    name: 'Decision Rules',
    description: 'Define how agents make choices',
    icon: GitBranch,
    count: 0,
  },
  {
    id: 'behavioral',
    name: 'Behavioral Patterns',
    description: 'Social influence and interaction rules',
    icon: Sparkles,
    count: 0,
  },
  {
    id: 'custom',
    name: 'Custom Rules',
    description: 'Write custom logic expressions',
    icon: FileCode,
    count: 0,
  },
];

export default function RulesPage() {
  const params = useParams();
  const projectId = params.projectId as string;

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
          <span className="text-[10px] md:text-xs font-mono text-white/40 uppercase tracking-wider">Rules & Logic</span>
        </div>
        <h1 className="text-lg md:text-xl font-mono font-bold text-white">Configure Rules</h1>
        <p className="text-xs md:text-sm font-mono text-white/50 mt-1">
          Define decision rules and behavioral patterns for your simulation
        </p>
      </div>

      {/* Status Banner */}
      <div className="max-w-3xl mb-6 p-4 bg-yellow-500/10 border border-yellow-500/30">
        <div className="flex items-center gap-2">
          <ScrollText className="w-4 h-4 text-yellow-400" />
          <span className="text-sm font-mono text-yellow-400">No rules defined yet</span>
        </div>
        <p className="text-xs font-mono text-white/50 mt-1">
          Add rules to control how agents behave and make decisions.
        </p>
      </div>

      {/* Rule Categories */}
      <div className="max-w-3xl">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xs font-mono text-white/40 uppercase tracking-wider">Rule Categories</h2>
          <Link href="/dashboard/library/rulesets">
            <Button variant="outline" size="sm" className="text-xs">
              <Library className="w-3 h-3 mr-2" />
              BROWSE LIBRARY
            </Button>
          </Link>
        </div>
        <div className="space-y-2">
          {ruleCategories.map((category) => {
            const Icon = category.icon;
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
                  <span className="text-xs font-mono text-white/40">{category.count} rules</span>
                  <Button size="sm" variant="secondary" className="text-xs">
                    <Plus className="w-3 h-3 mr-1" />
                    ADD
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Empty State */}
      <div className="max-w-3xl mt-8">
        <div className="bg-white/5 border border-white/10 p-8 text-center">
          <div className="w-16 h-16 bg-white/5 flex items-center justify-center mx-auto mb-4">
            <GitBranch className="w-8 h-8 text-white/20" />
          </div>
          <h3 className="text-sm font-mono text-white/60 mb-2">Rules will appear here</h3>
          <p className="text-xs font-mono text-white/40 mb-4">
            Start by adding decision rules or importing from the library
          </p>
          <Button size="sm" className="text-xs font-mono">
            <Plus className="w-3 h-3 mr-2" />
            CREATE RULE
          </Button>
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
    </div>
  );
}
