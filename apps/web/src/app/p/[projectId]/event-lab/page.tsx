'use client';

/**
 * Event Lab Page
 * Design "what-if" scenarios and inject events into simulations
 */

import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  Sparkles,
  ArrowLeft,
  Terminal,
  Plus,
  Zap,
  Calendar,
  Clock,
  Play,
  MessageSquare,
} from 'lucide-react';

export default function EventLabPage() {
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
          <Sparkles className="w-3.5 h-3.5 md:w-4 md:h-4 text-amber-400" />
          <span className="text-[10px] md:text-xs font-mono text-white/40 uppercase tracking-wider">Event Lab</span>
        </div>
        <h1 className="text-lg md:text-xl font-mono font-bold text-white">Event Lab (Ask)</h1>
        <p className="text-xs md:text-sm font-mono text-white/50 mt-1">
          Design events and &quot;what-if&quot; scenarios to inject into your simulations
        </p>
      </div>

      {/* Event Types */}
      <div className="max-w-4xl mb-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <button className="p-4 bg-white/5 border border-white/10 hover:border-amber-500/30 transition-all text-left group">
            <div className="w-10 h-10 bg-amber-500/20 flex items-center justify-center mb-3 group-hover:bg-amber-500/30 transition-colors">
              <Zap className="w-5 h-5 text-amber-400" />
            </div>
            <h3 className="text-sm font-mono font-bold text-white mb-1">Market Event</h3>
            <p className="text-[10px] font-mono text-white/40">
              Inject market changes, competitor actions, or economic shifts
            </p>
          </button>
          <button className="p-4 bg-white/5 border border-white/10 hover:border-purple-500/30 transition-all text-left group">
            <div className="w-10 h-10 bg-purple-500/20 flex items-center justify-center mb-3 group-hover:bg-purple-500/30 transition-colors">
              <MessageSquare className="w-5 h-5 text-purple-400" />
            </div>
            <h3 className="text-sm font-mono font-bold text-white mb-1">Communication</h3>
            <p className="text-[10px] font-mono text-white/40">
              Add marketing campaigns, news, or social media triggers
            </p>
          </button>
          <button className="p-4 bg-white/5 border border-white/10 hover:border-cyan-500/30 transition-all text-left group">
            <div className="w-10 h-10 bg-cyan-500/20 flex items-center justify-center mb-3 group-hover:bg-cyan-500/30 transition-colors">
              <Calendar className="w-5 h-5 text-cyan-400" />
            </div>
            <h3 className="text-sm font-mono font-bold text-white mb-1">Scheduled</h3>
            <p className="text-[10px] font-mono text-white/40">
              Create time-based events at specific ticks or conditions
            </p>
          </button>
        </div>
      </div>

      {/* Empty State / Events List */}
      <div className="max-w-4xl">
        <div className="bg-white/5 border border-white/10">
          <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
            <h2 className="text-sm font-mono font-bold text-white">Configured Events</h2>
            <Button size="sm" className="text-xs">
              <Plus className="w-3 h-3 mr-1" />
              ADD EVENT
            </Button>
          </div>
          <div className="p-12 text-center">
            <div className="w-16 h-16 bg-white/5 flex items-center justify-center mx-auto mb-4">
              <Sparkles className="w-8 h-8 text-white/20" />
            </div>
            <h3 className="text-sm font-mono text-white/60 mb-2">No events configured</h3>
            <p className="text-xs font-mono text-white/40 mb-4 max-w-sm mx-auto">
              Create events to inject into your simulation runs. Events can trigger at specific times or conditions.
            </p>
            <Button size="sm" variant="secondary">
              <Plus className="w-3 h-3 mr-2" />
              Create First Event
            </Button>
          </div>
        </div>
      </div>

      {/* Ask Section */}
      <div className="max-w-4xl mt-6">
        <div className="bg-amber-500/5 border border-amber-500/20 p-4">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 bg-amber-500/20 flex items-center justify-center flex-shrink-0">
              <MessageSquare className="w-4 h-4 text-amber-400" />
            </div>
            <div className="flex-1">
              <h3 className="text-sm font-mono font-bold text-amber-400 mb-1">Ask Feature</h3>
              <p className="text-xs font-mono text-white/50 mb-3">
                Describe a scenario in natural language and we&apos;ll help you configure the right events.
              </p>
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="e.g., What if a competitor launches a 20% discount next month?"
                  className="flex-1 px-3 py-2 bg-black border border-white/10 text-xs font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-amber-500/50"
                />
                <Button size="sm" className="text-xs bg-amber-500 hover:bg-amber-600 text-black">
                  <Play className="w-3 h-3 mr-1" />
                  ASK
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-8 pt-4 border-t border-white/5 max-w-4xl">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-1">
            <Terminal className="w-3 h-3" />
            <span>EVENT LAB</span>
          </div>
          <span>AGENTVERSE v1.0</span>
        </div>
      </div>
    </div>
  );
}
