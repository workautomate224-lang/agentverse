'use client';

import { Users, Plus, Search, Filter, Download, Upload } from 'lucide-react';

// Dummy persona data
const dummyPersonas = [
  {
    id: '1',
    name: 'Tech Enthusiast',
    description: 'Early adopter interested in latest technology trends',
    traits: ['Curious', 'Tech-savvy', 'Innovation-driven'],
    demographics: { age: '25-34', income: 'High', education: 'Graduate' },
    usageCount: 45,
  },
  {
    id: '2',
    name: 'Budget Conscious',
    description: 'Price-sensitive consumer focused on value',
    traits: ['Practical', 'Research-oriented', 'Deal-seeker'],
    demographics: { age: '35-44', income: 'Medium', education: 'College' },
    usageCount: 32,
  },
  {
    id: '3',
    name: 'Health Advocate',
    description: 'Wellness-focused individual prioritizing health',
    traits: ['Health-conscious', 'Active', 'Informed'],
    demographics: { age: '30-45', income: 'Medium-High', education: 'Graduate' },
    usageCount: 28,
  },
  {
    id: '4',
    name: 'Eco Warrior',
    description: 'Environmentally conscious consumer',
    traits: ['Sustainable', 'Ethical', 'Community-minded'],
    demographics: { age: '20-35', income: 'Variable', education: 'College+' },
    usageCount: 19,
  },
];

export default function PersonasLibraryPage() {
  return (
    <div className="space-y-6">
      {/* Action Bar */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3 flex-1">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
            <input
              type="text"
              placeholder="Search personas..."
              className="w-full bg-white/5 border border-white/10 px-10 py-2 text-sm font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-cyan-500/50"
            />
          </div>
          <button className="flex items-center gap-2 px-3 py-2 text-xs font-mono text-white/60 bg-white/5 border border-white/10 hover:bg-white/10 transition-colors">
            <Filter className="w-3.5 h-3.5" />
            <span>Filters</span>
          </button>
        </div>
        <div className="flex items-center gap-2">
          <button className="flex items-center gap-2 px-3 py-2 text-xs font-mono text-white/60 bg-white/5 border border-white/10 hover:bg-white/10 transition-colors">
            <Upload className="w-3.5 h-3.5" />
            <span>Import</span>
          </button>
          <button className="flex items-center gap-2 px-3 py-2 text-xs font-mono text-white/60 bg-white/5 border border-white/10 hover:bg-white/10 transition-colors">
            <Download className="w-3.5 h-3.5" />
            <span>Export</span>
          </button>
          <button className="flex items-center gap-2 px-4 py-2 text-xs font-mono text-black bg-cyan-400 hover:bg-cyan-300 transition-colors">
            <Plus className="w-3.5 h-3.5" />
            <span>New Persona</span>
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="text-2xl font-mono font-bold text-white mb-1">
            {dummyPersonas.length}
          </div>
          <div className="text-xs font-mono text-white/40">Total Personas</div>
        </div>
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="text-2xl font-mono font-bold text-cyan-400 mb-1">124</div>
          <div className="text-xs font-mono text-white/40">Total Simulations</div>
        </div>
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="text-2xl font-mono font-bold text-green-400 mb-1">89%</div>
          <div className="text-xs font-mono text-white/40">Avg Accuracy</div>
        </div>
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="text-2xl font-mono font-bold text-purple-400 mb-1">12</div>
          <div className="text-xs font-mono text-white/40">Active Projects</div>
        </div>
      </div>

      {/* Personas Grid */}
      <div className="grid grid-cols-2 gap-4">
        {dummyPersonas.map((persona) => (
          <div
            key={persona.id}
            className="bg-white/5 border border-white/10 p-5 hover:border-cyan-500/30 transition-colors cursor-pointer group"
          >
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-gradient-to-br from-cyan-500 to-purple-500 flex items-center justify-center">
                  <Users className="w-5 h-5 text-black" />
                </div>
                <div>
                  <h3 className="text-sm font-mono font-bold text-white group-hover:text-cyan-400 transition-colors">
                    {persona.name}
                  </h3>
                  <p className="text-xs font-mono text-white/40">
                    Used in {persona.usageCount} simulations
                  </p>
                </div>
              </div>
              <div className="text-[10px] font-mono text-white/30 bg-white/5 px-2 py-1">
                ID: {persona.id}
              </div>
            </div>
            <p className="text-xs font-mono text-white/60 mb-4">{persona.description}</p>
            <div className="flex flex-wrap gap-1.5 mb-4">
              {persona.traits.map((trait) => (
                <span
                  key={trait}
                  className="text-[10px] font-mono text-cyan-400 bg-cyan-400/10 px-2 py-0.5"
                >
                  {trait}
                </span>
              ))}
            </div>
            <div className="flex items-center gap-4 text-[10px] font-mono text-white/30">
              <span>Age: {persona.demographics.age}</span>
              <span>Income: {persona.demographics.income}</span>
              <span>Education: {persona.demographics.education}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Placeholder Message */}
      <div className="text-center py-8 border border-dashed border-white/10">
        <Users className="w-8 h-8 text-white/20 mx-auto mb-3" />
        <p className="text-sm font-mono text-white/40 mb-2">
          This is a preview of the Personas Library
        </p>
        <p className="text-xs font-mono text-white/30">
          Full functionality coming soon. Create and manage AI personas for your simulations.
        </p>
      </div>
    </div>
  );
}
