'use client';

import { useState, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { AgentSelector } from './AgentSelector';
import { InterviewChat } from './InterviewChat';
import {
  useAvailableAgents,
  useCreateFocusGroupSession,
  useFocusGroupSession,
  useFocusGroupMessages,
  useStreamingInterview,
  useEndFocusGroupSession,
} from '@/hooks/useFocusGroup';
import {
  Users,
  MessageCircle,
  Settings,
  Play,
  Square,
  Loader2,
  X,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';

interface FocusGroupPanelProps {
  productId: string;
  runId?: string;
  onClose?: () => void;
  className?: string;
}

type ViewMode = 'setup' | 'interview';

export function FocusGroupPanel({
  productId,
  runId,
  onClose,
  className,
}: FocusGroupPanelProps) {
  const [viewMode, setViewMode] = useState<ViewMode>('setup');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [selectedAgents, setSelectedAgents] = useState<string[]>([]);
  const [sessionName, setSessionName] = useState('Focus Group Session');
  const [sessionTopic, setSessionTopic] = useState('');
  const [showSettings, setShowSettings] = useState(false);
  const [settings, setSettings] = useState({
    modelPreset: 'balanced',
    temperature: 0.7,
    moderatorStyle: 'neutral',
  });

  // Fetch available agents
  const { data: availableAgents, isLoading: agentsLoading } = useAvailableAgents(productId, runId);

  // Session management
  const createSession = useCreateFocusGroupSession();
  const { data: session, isLoading: sessionLoading } = useFocusGroupSession(sessionId);
  const { data: messages = [], isLoading: messagesLoading } = useFocusGroupMessages(sessionId);
  const endSession = useEndFocusGroupSession();

  // Streaming interview
  const {
    isStreaming,
    streamedContent,
    currentAgent,
    sentiment,
    startStream,
    stopStream,
  } = useStreamingInterview(sessionId);

  const handleStartSession = async () => {
    if (selectedAgents.length === 0) return;

    try {
      const newSession = await createSession.mutateAsync({
        product_id: productId,
        run_id: runId,
        name: sessionName,
        agent_ids: selectedAgents,
        topic: sessionTopic || undefined,
        model_preset: settings.modelPreset,
        temperature: settings.temperature,
        moderator_style: settings.moderatorStyle,
      });

      setSessionId(newSession.id);
      setViewMode('interview');
    } catch {
      // Session creation failed - mutation error is handled by react-query
    }
  };

  const handleEndSession = async () => {
    if (!sessionId) return;

    try {
      await endSession.mutateAsync(sessionId);
      setSessionId(null);
      setViewMode('setup');
    } catch {
      // End session failed - mutation error is handled by react-query
    }
  };

  const handleSendMessage = (message: string) => {
    if (!sessionId) return;
    startStream(message);
  };

  return (
    <div className={cn(
      "bg-black border border-white/10 flex flex-col h-full",
      className
    )}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-white/10">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-white/5 flex items-center justify-center">
            <Users className="w-4 h-4 text-white/60" />
          </div>
          <div>
            <h2 className="text-sm font-mono font-bold text-white">
              Virtual Focus Group
            </h2>
            <p className="text-[10px] font-mono text-white/40">
              {viewMode === 'setup' ? 'Select agents to interview' : session?.name || 'Interview Session'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {viewMode === 'interview' && (
            <>
              <button
                onClick={() => setShowSettings(!showSettings)}
                className="p-2 text-white/40 hover:text-white/60 transition-colors"
              >
                <Settings className="w-4 h-4" />
              </button>
              <button
                onClick={handleEndSession}
                disabled={endSession.isPending}
                className="px-3 py-1.5 text-xs font-mono bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-colors flex items-center gap-1"
              >
                {endSession.isPending ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : (
                  <Square className="w-3 h-3" />
                )}
                END
              </button>
            </>
          )}
          {onClose && (
            <button
              onClick={onClose}
              className="p-2 text-white/40 hover:text-white/60 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 flex overflow-hidden">
        {viewMode === 'setup' ? (
          <div className="flex-1 flex flex-col p-4 overflow-hidden">
            {/* Session Name */}
            <div className="mb-4">
              <label className="block text-[10px] font-mono text-white/40 uppercase mb-1">
                Session Name
              </label>
              <input
                type="text"
                value={sessionName}
                onChange={(e) => setSessionName(e.target.value)}
                className="w-full px-3 py-2 bg-white/5 border border-white/10 text-sm font-mono text-white focus:outline-none focus:border-white/30"
              />
            </div>

            {/* Topic */}
            <div className="mb-4">
              <label className="block text-[10px] font-mono text-white/40 uppercase mb-1">
                Topic (Optional)
              </label>
              <input
                type="text"
                value={sessionTopic}
                onChange={(e) => setSessionTopic(e.target.value)}
                placeholder="e.g., Product feedback, Brand perception..."
                className="w-full px-3 py-2 bg-white/5 border border-white/10 text-sm font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-white/30"
              />
            </div>

            {/* Settings */}
            <div className="mb-4 p-3 bg-white/5 border border-white/10">
              <div className="text-[10px] font-mono text-white/40 uppercase mb-3">
                Settings
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-[10px] font-mono text-white/30 mb-1">
                    Model
                  </label>
                  <select
                    value={settings.modelPreset}
                    onChange={(e) => setSettings(s => ({ ...s, modelPreset: e.target.value }))}
                    className="w-full px-2 py-1 bg-white/5 border border-white/10 text-xs font-mono text-white appearance-none focus:outline-none"
                  >
                    <option value="fast">Fast</option>
                    <option value="balanced">Balanced</option>
                    <option value="quality">Quality</option>
                  </select>
                </div>
                <div>
                  <label className="block text-[10px] font-mono text-white/30 mb-1">
                    Temperature
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="2"
                    step="0.1"
                    value={settings.temperature}
                    onChange={(e) => setSettings(s => ({ ...s, temperature: parseFloat(e.target.value) }))}
                    className="w-full px-2 py-1 bg-white/5 border border-white/10 text-xs font-mono text-white focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-mono text-white/30 mb-1">
                    Style
                  </label>
                  <select
                    value={settings.moderatorStyle}
                    onChange={(e) => setSettings(s => ({ ...s, moderatorStyle: e.target.value }))}
                    className="w-full px-2 py-1 bg-white/5 border border-white/10 text-xs font-mono text-white appearance-none focus:outline-none"
                  >
                    <option value="neutral">Neutral</option>
                    <option value="probing">Probing</option>
                    <option value="supportive">Supportive</option>
                    <option value="challenging">Challenging</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Agent Selector */}
            <div className="flex-1 overflow-hidden">
              <AgentSelector
                agents={availableAgents || []}
                selectedAgents={selectedAgents}
                onSelectionChange={setSelectedAgents}
                isLoading={agentsLoading}
                maxSelection={10}
              />
            </div>

            {/* Start Button */}
            <div className="mt-4">
              <button
                onClick={handleStartSession}
                disabled={selectedAgents.length === 0 || createSession.isPending}
                className={cn(
                  "w-full py-3 text-sm font-mono font-medium flex items-center justify-center gap-2 transition-all",
                  selectedAgents.length > 0
                    ? "bg-white text-black hover:bg-white/90"
                    : "bg-white/10 text-white/40 cursor-not-allowed"
                )}
              >
                {createSession.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Play className="w-4 h-4" />
                )}
                START SESSION ({selectedAgents.length} agents)
              </button>
            </div>
          </div>
        ) : (
          <div className="flex-1 flex overflow-hidden">
            {/* Interview Chat */}
            <div className="flex-1 flex flex-col">
              <InterviewChat
                messages={messages}
                isLoading={messagesLoading}
                isStreaming={isStreaming}
                streamedContent={streamedContent}
                currentAgent={currentAgent}
                onSendMessage={handleSendMessage}
                disabled={!session || session.status !== 'active'}
              />
            </div>

            {/* Side Panel - Selected Agents */}
            {showSettings && (
              <div className="w-64 border-l border-white/10 p-4 overflow-y-auto">
                <h3 className="text-xs font-mono text-white/60 uppercase mb-3">
                  Session Info
                </h3>

                {session && (
                  <div className="space-y-3">
                    <div>
                      <span className="text-[10px] font-mono text-white/30 uppercase">
                        Status
                      </span>
                      <p className="text-xs font-mono text-white">
                        {session.status}
                      </p>
                    </div>
                    <div>
                      <span className="text-[10px] font-mono text-white/30 uppercase">
                        Messages
                      </span>
                      <p className="text-xs font-mono text-white">
                        {session.message_count}
                      </p>
                    </div>
                    <div>
                      <span className="text-[10px] font-mono text-white/30 uppercase">
                        Tokens
                      </span>
                      <p className="text-xs font-mono text-white">
                        {session.total_tokens.toLocaleString()}
                      </p>
                    </div>
                    <div>
                      <span className="text-[10px] font-mono text-white/30 uppercase">
                        Est. Cost
                      </span>
                      <p className="text-xs font-mono text-white">
                        ${session.estimated_cost.toFixed(4)}
                      </p>
                    </div>
                  </div>
                )}

                <h3 className="text-xs font-mono text-white/60 uppercase mt-6 mb-3">
                  Participants ({session?.agent_ids.length || 0})
                </h3>

                <div className="space-y-1">
                  {Object.entries(session?.agent_contexts || {}).map(([agentId, context]) => {
                    const persona = context.persona || {};
                    const name = (persona.name as string) || `Agent ${agentId.slice(0, 8)}`;

                    return (
                      <div
                        key={agentId}
                        className="p-2 bg-white/5 border border-white/10 text-xs font-mono text-white"
                      >
                        {name}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
