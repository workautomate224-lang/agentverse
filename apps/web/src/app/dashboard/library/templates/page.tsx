'use client';

import { LayoutTemplate, Plus, Search, Filter, Star, Copy } from 'lucide-react';

// Dummy template data
const dummyTemplates = [
  {
    id: '1',
    name: 'Product Launch Survey',
    description: 'Standard template for testing new product concepts with target consumers',
    category: 'Product Research',
    rating: 4.8,
    uses: 156,
    author: 'AgentVerse Team',
    isOfficial: true,
  },
  {
    id: '2',
    name: 'Brand Perception Study',
    description: 'Comprehensive template for measuring brand awareness and sentiment',
    category: 'Brand Research',
    rating: 4.6,
    uses: 98,
    author: 'AgentVerse Team',
    isOfficial: true,
  },
  {
    id: '3',
    name: 'Price Sensitivity Analysis',
    description: 'Template for determining optimal pricing strategies',
    category: 'Pricing Research',
    rating: 4.5,
    uses: 73,
    author: 'Community',
    isOfficial: false,
  },
  {
    id: '4',
    name: 'Feature Prioritization',
    description: 'Help prioritize features based on consumer preferences',
    category: 'Product Development',
    rating: 4.7,
    uses: 112,
    author: 'AgentVerse Team',
    isOfficial: true,
  },
  {
    id: '5',
    name: 'Market Entry Assessment',
    description: 'Evaluate market readiness for new product categories',
    category: 'Market Research',
    rating: 4.4,
    uses: 45,
    author: 'Community',
    isOfficial: false,
  },
  {
    id: '6',
    name: 'Customer Journey Mapping',
    description: 'Map and analyze customer touchpoints and experiences',
    category: 'UX Research',
    rating: 4.9,
    uses: 201,
    author: 'AgentVerse Team',
    isOfficial: true,
  },
];

export default function TemplatesPage() {
  return (
    <div className="space-y-4 md:space-y-6">
      {/* Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 md:gap-4">
        <div className="flex items-center gap-2 md:gap-3 flex-1">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
            <input
              type="text"
              placeholder="Search templates..."
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
          <span>Create Template</span>
        </button>
      </div>

      {/* Category Tabs */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2 -mx-4 md:mx-0 px-4 md:px-0 scrollbar-hide">
        {['All', 'Product Research', 'Brand Research', 'Pricing Research', 'Market Research', 'UX Research'].map(
          (category) => (
            <button
              key={category}
              className={`px-3 py-1.5 text-[10px] md:text-xs font-mono whitespace-nowrap transition-colors flex-shrink-0 ${
                category === 'All'
                  ? 'bg-white text-black'
                  : 'text-white/50 bg-white/5 hover:bg-white/10'
              }`}
            >
              {category}
            </button>
          )
        )}
      </div>

      {/* Templates Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 md:gap-4">
        {dummyTemplates.map((template) => (
          <div
            key={template.id}
            className="bg-white/5 border border-white/10 p-4 md:p-5 hover:border-cyan-500/30 transition-colors cursor-pointer group"
          >
            <div className="flex items-start justify-between mb-3">
              <div className="w-8 h-8 md:w-10 md:h-10 bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center flex-shrink-0">
                <LayoutTemplate className="w-4 h-4 md:w-5 md:h-5 text-white" />
              </div>
              {template.isOfficial && (
                <span className="text-[9px] md:text-[10px] font-mono text-cyan-400 bg-cyan-400/10 px-1.5 md:px-2 py-0.5">
                  Official
                </span>
              )}
            </div>
            <h3 className="text-xs md:text-sm font-mono font-bold text-white group-hover:text-cyan-400 transition-colors mb-2 truncate">
              {template.name}
            </h3>
            <p className="text-[10px] md:text-xs font-mono text-white/50 mb-3 md:mb-4 line-clamp-2">
              {template.description}
            </p>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 md:gap-3 text-[9px] md:text-[10px] font-mono text-white/30">
                <span className="flex items-center gap-1">
                  <Star className="w-3 h-3 text-yellow-500" />
                  {template.rating}
                </span>
                <span className="flex items-center gap-1">
                  <Copy className="w-3 h-3" />
                  {template.uses}
                </span>
              </div>
              <span className="text-[9px] md:text-[10px] font-mono text-white/20 truncate ml-2">{template.category}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Placeholder Message */}
      <div className="text-center py-8 border border-dashed border-white/10">
        <LayoutTemplate className="w-8 h-8 text-white/20 mx-auto mb-3" />
        <p className="text-sm font-mono text-white/40 mb-2">
          This is a preview of the Templates Library
        </p>
        <p className="text-xs font-mono text-white/30">
          Full functionality coming soon. Browse and create simulation templates.
        </p>
      </div>
    </div>
  );
}
