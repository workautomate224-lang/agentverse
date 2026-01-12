'use client';

import { ScrollText, Plus, Search, Filter, Code, AlertTriangle, CheckCircle } from 'lucide-react';

// Dummy ruleset data
const dummyRulesets = [
  {
    id: '1',
    name: 'Consumer Behavior Rules',
    description: 'Standard rules governing consumer decision-making patterns',
    rulesCount: 24,
    status: 'active',
    lastModified: '2 days ago',
    category: 'Behavior',
  },
  {
    id: '2',
    name: 'Price Sensitivity Model',
    description: 'Rules for simulating price-based purchasing decisions',
    rulesCount: 18,
    status: 'active',
    lastModified: '1 week ago',
    category: 'Economics',
  },
  {
    id: '3',
    name: 'Brand Loyalty Factors',
    description: 'Rules determining brand switching and loyalty behavior',
    rulesCount: 31,
    status: 'draft',
    lastModified: '3 days ago',
    category: 'Brand',
  },
  {
    id: '4',
    name: 'Social Influence Rules',
    description: 'Rules for word-of-mouth and social proof effects',
    rulesCount: 15,
    status: 'active',
    lastModified: '5 days ago',
    category: 'Social',
  },
  {
    id: '5',
    name: 'Purchase Journey Rules',
    description: 'Rules governing the stages of consumer purchase journey',
    rulesCount: 42,
    status: 'active',
    lastModified: '1 day ago',
    category: 'Journey',
  },
  {
    id: '6',
    name: 'Seasonal Adjustment Rules',
    description: 'Time-based adjustments for seasonal purchasing patterns',
    rulesCount: 12,
    status: 'deprecated',
    lastModified: '2 weeks ago',
    category: 'Temporal',
  },
];

export default function RulesetsPage() {
  return (
    <div className="space-y-4 md:space-y-6">
      {/* Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 md:gap-4">
        <div className="flex items-center gap-2 md:gap-3 flex-1">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
            <input
              type="text"
              placeholder="Search rulesets..."
              className="w-full bg-white/5 border border-white/10 px-10 py-2 text-sm font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-cyan-500/50"
            />
          </div>
          <button className="flex items-center gap-2 px-3 py-2 text-xs font-mono text-white/60 bg-white/5 border border-white/10 hover:bg-white/10 transition-colors">
            <Filter className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Filters</span>
          </button>
        </div>
        <button className="flex items-center gap-2 px-3 md:px-4 py-2 text-xs font-mono text-black bg-cyan-400 hover:bg-cyan-300 transition-colors whitespace-nowrap">
          <Plus className="w-3.5 h-3.5" />
          <span>New Ruleset</span>
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
        <div className="bg-white/5 border border-white/10 p-3 md:p-4">
          <div className="text-xl md:text-2xl font-mono font-bold text-white mb-1">
            {dummyRulesets.length}
          </div>
          <div className="text-[10px] md:text-xs font-mono text-white/40">Total Rulesets</div>
        </div>
        <div className="bg-white/5 border border-white/10 p-3 md:p-4">
          <div className="text-xl md:text-2xl font-mono font-bold text-green-400 mb-1">
            {dummyRulesets.filter((r) => r.status === 'active').length}
          </div>
          <div className="text-[10px] md:text-xs font-mono text-white/40">Active</div>
        </div>
        <div className="bg-white/5 border border-white/10 p-3 md:p-4">
          <div className="text-xl md:text-2xl font-mono font-bold text-yellow-400 mb-1">
            {dummyRulesets.filter((r) => r.status === 'draft').length}
          </div>
          <div className="text-[10px] md:text-xs font-mono text-white/40">Draft</div>
        </div>
        <div className="bg-white/5 border border-white/10 p-3 md:p-4">
          <div className="text-xl md:text-2xl font-mono font-bold text-cyan-400 mb-1">
            {dummyRulesets.reduce((acc, r) => acc + r.rulesCount, 0)}
          </div>
          <div className="text-[10px] md:text-xs font-mono text-white/40">Total Rules</div>
        </div>
      </div>

      {/* Rulesets Table - Desktop */}
      <div className="hidden md:block bg-white/5 border border-white/10">
        <table className="w-full">
          <thead>
            <tr className="border-b border-white/10">
              <th className="text-left text-[10px] font-mono text-white/40 uppercase tracking-wider px-4 py-3">
                Ruleset
              </th>
              <th className="text-left text-[10px] font-mono text-white/40 uppercase tracking-wider px-4 py-3">
                Category
              </th>
              <th className="text-left text-[10px] font-mono text-white/40 uppercase tracking-wider px-4 py-3">
                Rules
              </th>
              <th className="text-left text-[10px] font-mono text-white/40 uppercase tracking-wider px-4 py-3">
                Status
              </th>
              <th className="text-left text-[10px] font-mono text-white/40 uppercase tracking-wider px-4 py-3">
                Modified
              </th>
            </tr>
          </thead>
          <tbody>
            {dummyRulesets.map((ruleset) => (
              <tr
                key={ruleset.id}
                className="border-b border-white/5 hover:bg-white/5 cursor-pointer transition-colors"
              >
                <td className="px-4 py-3">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-gradient-to-br from-orange-500 to-red-500 flex items-center justify-center flex-shrink-0">
                      <Code className="w-4 h-4 text-white" />
                    </div>
                    <div>
                      <div className="text-sm font-mono text-white">{ruleset.name}</div>
                      <div className="text-[10px] font-mono text-white/40 line-clamp-1">
                        {ruleset.description}
                      </div>
                    </div>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <span className="text-xs font-mono text-white/50">{ruleset.category}</span>
                </td>
                <td className="px-4 py-3">
                  <span className="text-xs font-mono text-cyan-400">{ruleset.rulesCount}</span>
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`inline-flex items-center gap-1.5 text-[10px] font-mono px-2 py-0.5 ${
                      ruleset.status === 'active'
                        ? 'text-green-400 bg-green-400/10'
                        : ruleset.status === 'draft'
                          ? 'text-yellow-400 bg-yellow-400/10'
                          : 'text-white/30 bg-white/5'
                    }`}
                  >
                    {ruleset.status === 'active' ? (
                      <CheckCircle className="w-3 h-3" />
                    ) : ruleset.status === 'draft' ? (
                      <AlertTriangle className="w-3 h-3" />
                    ) : null}
                    {ruleset.status}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className="text-xs font-mono text-white/30">{ruleset.lastModified}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Rulesets Cards - Mobile */}
      <div className="md:hidden space-y-3">
        {dummyRulesets.map((ruleset) => (
          <div
            key={ruleset.id}
            className="bg-white/5 border border-white/10 p-4 hover:border-cyan-500/30 transition-colors cursor-pointer"
          >
            <div className="flex items-start gap-3 mb-3">
              <div className="w-8 h-8 bg-gradient-to-br from-orange-500 to-red-500 flex items-center justify-center flex-shrink-0">
                <Code className="w-4 h-4 text-white" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <div className="text-xs font-mono text-white font-bold truncate">{ruleset.name}</div>
                  <span
                    className={`inline-flex items-center gap-1 text-[9px] font-mono px-1.5 py-0.5 flex-shrink-0 ${
                      ruleset.status === 'active'
                        ? 'text-green-400 bg-green-400/10'
                        : ruleset.status === 'draft'
                          ? 'text-yellow-400 bg-yellow-400/10'
                          : 'text-white/30 bg-white/5'
                    }`}
                  >
                    {ruleset.status === 'active' ? (
                      <CheckCircle className="w-2.5 h-2.5" />
                    ) : ruleset.status === 'draft' ? (
                      <AlertTriangle className="w-2.5 h-2.5" />
                    ) : null}
                    {ruleset.status}
                  </span>
                </div>
                <div className="text-[10px] font-mono text-white/40 line-clamp-1 mt-0.5">
                  {ruleset.description}
                </div>
              </div>
            </div>
            <div className="flex items-center justify-between text-[10px] font-mono">
              <div className="flex items-center gap-3 text-white/40">
                <span>{ruleset.category}</span>
                <span className="text-cyan-400">{ruleset.rulesCount} rules</span>
              </div>
              <span className="text-white/30">{ruleset.lastModified}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Placeholder Message */}
      <div className="text-center py-8 border border-dashed border-white/10">
        <ScrollText className="w-8 h-8 text-white/20 mx-auto mb-3" />
        <p className="text-sm font-mono text-white/40 mb-2">
          This is a preview of the Rulesets Library
        </p>
        <p className="text-xs font-mono text-white/30">
          Full functionality coming soon. Define and manage simulation rules.
        </p>
      </div>
    </div>
  );
}
