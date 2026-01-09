'use client';

import { useState } from 'react';
import { cn } from '@/lib/utils';
import { AvailableAgent } from '@/lib/api';
import {
  Users,
  User,
  Check,
  Loader2,
  Search,
} from 'lucide-react';

interface AgentSelectorProps {
  agents: AvailableAgent[];
  selectedAgents: string[];
  onSelectionChange: (agentIds: string[]) => void;
  isLoading?: boolean;
  maxSelection?: number;
  className?: string;
}

export function AgentSelector({
  agents,
  selectedAgents,
  onSelectionChange,
  isLoading = false,
  maxSelection = 10,
  className,
}: AgentSelectorProps) {
  const [searchQuery, setSearchQuery] = useState('');

  const filteredAgents = agents.filter(agent => {
    if (!searchQuery) return true;

    const persona = agent.persona_summary || {};
    const name = (persona.name as string) || '';
    const occupation = (persona.occupation as string) || '';

    return (
      name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      occupation.toLowerCase().includes(searchQuery.toLowerCase())
    );
  });

  const toggleAgent = (agentId: string) => {
    if (selectedAgents.includes(agentId)) {
      onSelectionChange(selectedAgents.filter(id => id !== agentId));
    } else if (selectedAgents.length < maxSelection) {
      onSelectionChange([...selectedAgents, agentId]);
    }
  };

  const selectAll = () => {
    const allIds = filteredAgents.slice(0, maxSelection).map(a => a.agent_id);
    onSelectionChange(allIds);
  };

  const clearAll = () => {
    onSelectionChange([]);
  };

  if (isLoading) {
    return (
      <div className={cn("flex items-center justify-center p-8", className)}>
        <Loader2 className="w-5 h-5 animate-spin text-white/40" />
      </div>
    );
  }

  return (
    <div className={cn("space-y-3", className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Users className="w-4 h-4 text-white/60" />
          <span className="text-xs font-mono text-white/60 uppercase tracking-wider">
            Select Agents
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono text-white/40">
            {selectedAgents.length}/{maxSelection} selected
          </span>
          <button
            onClick={selectAll}
            className="px-2 py-0.5 text-[10px] font-mono text-white/40 hover:text-white/60 transition-colors"
          >
            ALL
          </button>
          <button
            onClick={clearAll}
            className="px-2 py-0.5 text-[10px] font-mono text-white/40 hover:text-white/60 transition-colors"
          >
            CLEAR
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3 h-3 text-white/30" />
        <input
          type="text"
          placeholder="Search agents..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-8 pr-3 py-2 bg-white/5 border border-white/10 text-xs font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-white/30"
        />
      </div>

      {/* Agent List */}
      <div className="max-h-[300px] overflow-y-auto space-y-1 pr-1">
        {filteredAgents.length === 0 ? (
          <div className="p-4 text-center text-xs font-mono text-white/40">
            No agents found
          </div>
        ) : (
          filteredAgents.map((agent) => {
            const isSelected = selectedAgents.includes(agent.agent_id);
            const persona = agent.persona_summary || {};
            const name = (persona.name as string) || `Agent ${agent.agent_index + 1}`;
            const age = persona.age as number;
            const occupation = (persona.occupation as string) || 'Unknown';
            const sentiment = agent.original_sentiment;

            return (
              <button
                key={agent.agent_id}
                onClick={() => toggleAgent(agent.agent_id)}
                disabled={!isSelected && selectedAgents.length >= maxSelection}
                className={cn(
                  "w-full flex items-center gap-3 p-2 transition-all",
                  isSelected
                    ? "bg-blue-500/20 border border-blue-500/40"
                    : "bg-white/5 border border-white/10 hover:bg-white/[0.07]",
                  !isSelected && selectedAgents.length >= maxSelection && "opacity-50 cursor-not-allowed"
                )}
              >
                <div className={cn(
                  "w-6 h-6 flex items-center justify-center",
                  isSelected ? "bg-blue-500" : "bg-white/10"
                )}>
                  {isSelected ? (
                    <Check className="w-3 h-3 text-white" />
                  ) : (
                    <User className="w-3 h-3 text-white/40" />
                  )}
                </div>

                <div className="flex-1 text-left">
                  <div className="text-xs font-mono text-white">
                    {name}
                  </div>
                  <div className="text-[10px] font-mono text-white/40">
                    {age && `${age}y • `}{occupation}
                  </div>
                </div>

                {sentiment !== null && sentiment !== undefined && (
                  <div className={cn(
                    "px-1.5 py-0.5 text-[10px] font-mono",
                    sentiment > 0.3 ? "bg-green-500/20 text-green-400" :
                    sentiment < -0.3 ? "bg-red-500/20 text-red-400" :
                    "bg-white/10 text-white/40"
                  )}>
                    {sentiment > 0 ? '+' : ''}{(sentiment * 100).toFixed(0)}%
                  </div>
                )}
              </button>
            );
          })
        )}
      </div>
    </div>
  );
}
