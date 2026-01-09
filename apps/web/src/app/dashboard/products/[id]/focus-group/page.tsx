'use client';

import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { useProduct, useProductResults } from '@/hooks/useApi';
import { useFocusGroupSessions } from '@/hooks/useFocusGroup';
import { FocusGroupPanel } from '@/components/focus-group/FocusGroupPanel';
import { cn } from '@/lib/utils';
import {
  ArrowLeft,
  Users,
  MessageCircle,
  Loader2,
  AlertTriangle,
  Plus,
  ChevronRight,
  Clock,
  CheckCircle,
  XCircle,
  Terminal,
} from 'lucide-react';
import { useState } from 'react';

export default function FocusGroupPage() {
  const params = useParams();
  const router = useRouter();
  const productId = params.id as string;

  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [showNewSession, setShowNewSession] = useState(false);

  const { data: product, isLoading: productLoading, error: productError } = useProduct(productId);
  const { data: results } = useProductResults(productId);
  const { data: sessions, isLoading: sessionsLoading } = useFocusGroupSessions({ productId });

  // Get the latest completed run for agent selection
  const latestCompletedRun = results?.find(r => r.result_type === 'sentiment_analysis' || r.result_type === 'full');

  if (productLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-black">
        <Loader2 className="w-5 h-5 animate-spin text-white/40" />
      </div>
    );
  }

  if (productError || !product) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-black">
        <AlertTriangle className="w-8 h-8 text-red-400 mb-4" />
        <h2 className="text-lg font-mono font-bold text-white mb-2">Product Not Found</h2>
        <p className="text-sm font-mono text-white/50 mb-4">The product you&apos;re looking for doesn&apos;t exist.</p>
        <Link
          href="/dashboard/products"
          className="px-4 py-2 text-xs font-mono bg-white/10 text-white/60 hover:bg-white/20 transition-colors flex items-center gap-2"
        >
          <ArrowLeft className="w-3 h-3" />
          BACK TO PRODUCTS
        </Link>
      </div>
    );
  }

  const handleStartNewSession = () => {
    setActiveSessionId(null);
    setShowNewSession(true);
  };

  const handleClosePanel = () => {
    setShowNewSession(false);
    setActiveSessionId(null);
  };

  const handleSelectSession = (sessionId: string) => {
    setActiveSessionId(sessionId);
    setShowNewSession(false);
  };

  return (
    <div className="min-h-screen bg-black">
      {/* Header */}
      <div className="border-b border-white/10 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link
              href={`/dashboard/products/${productId}`}
              className="p-1.5 hover:bg-white/10 transition-colors"
            >
              <ArrowLeft className="w-4 h-4 text-white/60" />
            </Link>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-mono font-bold text-white">Virtual Focus Group</h1>
                <span className="px-1.5 py-0.5 bg-blue-500/20 text-blue-400 text-[10px] font-mono uppercase">
                  BETA
                </span>
              </div>
              <p className="text-xs font-mono text-white/40">
                {product.name} • Interview AI personas from your simulation
              </p>
            </div>
          </div>

          <button
            onClick={handleStartNewSession}
            className="px-4 py-2 bg-white text-black text-xs font-mono font-medium flex items-center gap-2 hover:bg-white/90 transition-colors"
          >
            <Plus className="w-3 h-3" />
            NEW SESSION
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex h-[calc(100vh-73px)]">
        {/* Sidebar - Session List */}
        <div className="w-80 border-r border-white/10 flex flex-col">
          <div className="p-4 border-b border-white/10">
            <div className="flex items-center gap-2">
              <MessageCircle className="w-4 h-4 text-white/40" />
              <span className="text-xs font-mono text-white/60 uppercase tracking-wider">
                Sessions
              </span>
              {sessions && sessions.length > 0 && (
                <span className="ml-auto px-1.5 py-0.5 bg-white/10 text-[10px] font-mono text-white/40">
                  {sessions.length}
                </span>
              )}
            </div>
          </div>

          <div className="flex-1 overflow-y-auto">
            {sessionsLoading ? (
              <div className="p-8 flex items-center justify-center">
                <Loader2 className="w-4 h-4 animate-spin text-white/40" />
              </div>
            ) : sessions && sessions.length > 0 ? (
              <div className="divide-y divide-white/5">
                {sessions.map((session) => (
                  <button
                    key={session.id}
                    onClick={() => handleSelectSession(session.id)}
                    className={cn(
                      "w-full p-4 text-left hover:bg-white/5 transition-colors",
                      activeSessionId === session.id && "bg-white/10"
                    )}
                  >
                    <div className="flex items-start justify-between mb-1">
                      <span className="text-sm font-mono text-white line-clamp-1">
                        {session.name}
                      </span>
                      <SessionStatusBadge status={session.status} />
                    </div>
                    <div className="flex items-center gap-3 text-[10px] font-mono text-white/40">
                      <span className="flex items-center gap-1">
                        <Users className="w-2.5 h-2.5" />
                        {session.agent_ids.length}
                      </span>
                      <span className="flex items-center gap-1">
                        <MessageCircle className="w-2.5 h-2.5" />
                        {session.message_count}
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock className="w-2.5 h-2.5" />
                        {new Date(session.created_at).toLocaleDateString()}
                      </span>
                    </div>
                    {session.topic && (
                      <p className="text-[10px] font-mono text-white/30 mt-1 line-clamp-1">
                        Topic: {session.topic}
                      </p>
                    )}
                  </button>
                ))}
              </div>
            ) : (
              <div className="p-8 text-center">
                <div className="w-12 h-12 bg-white/5 flex items-center justify-center mx-auto mb-3">
                  <Users className="w-5 h-5 text-white/20" />
                </div>
                <p className="text-sm font-mono text-white/50 mb-1">No sessions yet</p>
                <p className="text-[10px] font-mono text-white/30 mb-4">
                  Start a focus group session to interview your AI personas
                </p>
                <button
                  onClick={handleStartNewSession}
                  className="px-4 py-2 bg-white/10 text-white text-xs font-mono hover:bg-white/20 transition-colors"
                >
                  START SESSION
                </button>
              </div>
            )}
          </div>

          {/* Sidebar Footer */}
          <div className="p-4 border-t border-white/10">
            <div className="bg-white/5 border border-white/10 p-3">
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle className="w-3 h-3 text-yellow-400" />
                <span className="text-[10px] font-mono text-yellow-400 uppercase">Note</span>
              </div>
              <p className="text-[10px] font-mono text-white/40 leading-relaxed">
                Focus groups use AI to simulate conversations with personas from your completed simulations.
                Responses are generated based on persona profiles and previous simulation data.
              </p>
            </div>
          </div>
        </div>

        {/* Main Panel */}
        <div className="flex-1 flex flex-col">
          {showNewSession || activeSessionId ? (
            <FocusGroupPanel
              productId={productId}
              runId={latestCompletedRun?.run_id ?? undefined}
              onClose={handleClosePanel}
              className="flex-1"
            />
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center p-8">
              <div className="w-16 h-16 bg-white/5 flex items-center justify-center mb-4">
                <Users className="w-8 h-8 text-white/20" />
              </div>
              <h2 className="text-lg font-mono font-bold text-white mb-2">
                Virtual Focus Groups
              </h2>
              <p className="text-sm font-mono text-white/40 text-center max-w-md mb-6">
                Interview AI personas from your simulation. Ask follow-up questions,
                explore opinions, and gather deeper insights.
              </p>

              <div className="grid grid-cols-3 gap-4 mb-8">
                <div className="bg-white/5 border border-white/10 p-4 text-center">
                  <div className="text-2xl font-mono font-bold text-white mb-1">
                    {product.persona_count.toLocaleString()}
                  </div>
                  <div className="text-[10px] font-mono text-white/40 uppercase">
                    Available Personas
                  </div>
                </div>
                <div className="bg-white/5 border border-white/10 p-4 text-center">
                  <div className="text-2xl font-mono font-bold text-white mb-1">
                    {sessions?.length || 0}
                  </div>
                  <div className="text-[10px] font-mono text-white/40 uppercase">
                    Sessions
                  </div>
                </div>
                <div className="bg-white/5 border border-white/10 p-4 text-center">
                  <div className="text-2xl font-mono font-bold text-white mb-1">
                    {sessions?.reduce((acc, s) => acc + s.message_count, 0) || 0}
                  </div>
                  <div className="text-[10px] font-mono text-white/40 uppercase">
                    Messages
                  </div>
                </div>
              </div>

              <button
                onClick={handleStartNewSession}
                className="px-6 py-3 bg-white text-black text-sm font-mono font-medium flex items-center gap-2 hover:bg-white/90 transition-colors"
              >
                <Plus className="w-4 h-4" />
                START NEW SESSION
              </button>

              {!latestCompletedRun && (
                <p className="text-[10px] font-mono text-yellow-400 mt-4 flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3" />
                  Run a simulation first to populate agent personas
                </p>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="fixed bottom-0 left-0 right-0 bg-black border-t border-white/5 px-4 py-2">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-1">
            <Terminal className="w-3 h-3" />
            <span>VIRTUAL FOCUS GROUP</span>
          </div>
          <span>AGENTVERSE v1.0.0</span>
        </div>
      </div>
    </div>
  );
}

function SessionStatusBadge({ status }: { status: string }) {
  switch (status) {
    case 'active':
      return (
        <span className="px-1.5 py-0.5 bg-green-500/20 text-green-400 text-[10px] font-mono uppercase flex items-center gap-1">
          <span className="w-1 h-1 bg-green-400 rounded-full animate-pulse" />
          ACTIVE
        </span>
      );
    case 'completed':
      return (
        <span className="px-1.5 py-0.5 bg-white/10 text-white/50 text-[10px] font-mono uppercase flex items-center gap-1">
          <CheckCircle className="w-2.5 h-2.5" />
          DONE
        </span>
      );
    case 'cancelled':
      return (
        <span className="px-1.5 py-0.5 bg-red-500/20 text-red-400 text-[10px] font-mono uppercase flex items-center gap-1">
          <XCircle className="w-2.5 h-2.5" />
          CANCELLED
        </span>
      );
    default:
      return null;
  }
}
