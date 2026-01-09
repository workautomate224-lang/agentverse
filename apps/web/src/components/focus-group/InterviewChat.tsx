'use client';

import { useState, useRef, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { FocusGroupMessage } from '@/lib/api';
import {
  Send,
  Loader2,
  User,
  Bot,
  MessageCircle,
  TrendingUp,
  TrendingDown,
  Minus,
} from 'lucide-react';

interface InterviewChatProps {
  messages: FocusGroupMessage[];
  isLoading?: boolean;
  isStreaming?: boolean;
  streamedContent?: string;
  currentAgent?: { id: string; name: string } | null;
  onSendMessage: (message: string) => void;
  disabled?: boolean;
  className?: string;
}

export function InterviewChat({
  messages,
  isLoading = false,
  isStreaming = false,
  streamedContent = '',
  currentAgent = null,
  onSendMessage,
  disabled = false,
  className,
}: InterviewChatProps) {
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamedContent]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || disabled || isStreaming) return;

    onSendMessage(inputValue.trim());
    setInputValue('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const getSentimentIcon = (score: number | null) => {
    if (score === null) return null;
    if (score > 0.2) return <TrendingUp className="w-3 h-3 text-green-400" />;
    if (score < -0.2) return <TrendingDown className="w-3 h-3 text-red-400" />;
    return <Minus className="w-3 h-3 text-white/40" />;
  };

  const getEmotionColor = (emotion: string | null) => {
    switch (emotion?.toLowerCase()) {
      case 'positive':
      case 'happy':
      case 'excited':
        return 'text-green-400';
      case 'negative':
      case 'frustrated':
      case 'angry':
        return 'text-red-400';
      case 'concerned':
      case 'worried':
        return 'text-yellow-400';
      default:
        return 'text-white/40';
    }
  };

  return (
    <div className={cn("flex flex-col h-full", className)}>
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && !isStreaming && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <MessageCircle className="w-8 h-8 text-white/20 mb-3" />
            <p className="text-sm font-mono text-white/40 mb-1">No messages yet</p>
            <p className="text-xs font-mono text-white/30">
              Start the interview by asking a question
            </p>
          </div>
        )}

        {messages.map((message) => (
          <div
            key={message.id}
            className={cn(
              "flex gap-3",
              message.role === 'moderator' ? "justify-end" : "justify-start"
            )}
          >
            {message.role !== 'moderator' && (
              <div className="w-8 h-8 bg-blue-500/20 flex items-center justify-center flex-shrink-0">
                <User className="w-4 h-4 text-blue-400" />
              </div>
            )}

            <div
              className={cn(
                "max-w-[80%] p-3",
                message.role === 'moderator'
                  ? "bg-white/10"
                  : "bg-blue-500/10 border border-blue-500/20"
              )}
            >
              {message.role !== 'moderator' && message.agent_name && (
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-mono font-bold text-blue-400">
                    {message.agent_name}
                  </span>
                  {message.sentiment_score !== null && (
                    <div className="flex items-center gap-1">
                      {getSentimentIcon(message.sentiment_score)}
                      <span className={cn(
                        "text-[10px] font-mono",
                        getEmotionColor(message.emotion)
                      )}>
                        {message.emotion}
                      </span>
                    </div>
                  )}
                </div>
              )}

              <p className="text-sm font-mono text-white whitespace-pre-wrap">
                {message.content}
              </p>

              {message.key_points && message.key_points.length > 0 && (
                <div className="mt-2 pt-2 border-t border-white/5">
                  <span className="text-[10px] font-mono text-white/30 uppercase">
                    Key Points:
                  </span>
                  <ul className="mt-1 space-y-0.5">
                    {message.key_points.map((point, i) => (
                      <li key={i} className="text-[10px] font-mono text-white/50">
                        • {point}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="mt-1 text-[10px] font-mono text-white/20">
                {new Date(message.created_at).toLocaleTimeString()}
              </div>
            </div>

            {message.role === 'moderator' && (
              <div className="w-8 h-8 bg-white/10 flex items-center justify-center flex-shrink-0">
                <Bot className="w-4 h-4 text-white/60" />
              </div>
            )}
          </div>
        ))}

        {/* Streaming Response */}
        {isStreaming && streamedContent && (
          <div className="flex gap-3 justify-start">
            <div className="w-8 h-8 bg-blue-500/20 flex items-center justify-center flex-shrink-0 animate-pulse">
              <User className="w-4 h-4 text-blue-400" />
            </div>

            <div className="max-w-[80%] p-3 bg-blue-500/10 border border-blue-500/20">
              {currentAgent && (
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-mono font-bold text-blue-400">
                    {currentAgent.name}
                  </span>
                  <span className="text-[10px] font-mono text-white/30 animate-pulse">
                    typing...
                  </span>
                </div>
              )}

              <p className="text-sm font-mono text-white whitespace-pre-wrap">
                {streamedContent}
                <span className="inline-block w-1.5 h-4 bg-blue-400 ml-0.5 animate-pulse" />
              </p>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <form onSubmit={handleSubmit} className="p-4 border-t border-white/10">
        <div className="flex gap-2">
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={disabled ? "Select agents to start interviewing..." : "Ask a question..."}
              disabled={disabled || isStreaming}
              rows={2}
              className={cn(
                "w-full px-3 py-2 bg-white/5 border border-white/10 text-sm font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-white/30 resize-none",
                (disabled || isStreaming) && "opacity-50 cursor-not-allowed"
              )}
            />
          </div>

          <button
            type="submit"
            disabled={!inputValue.trim() || disabled || isStreaming}
            className={cn(
              "px-4 py-2 bg-white text-black text-sm font-mono font-medium transition-all",
              "hover:bg-white/90 disabled:opacity-50 disabled:cursor-not-allowed"
            )}
          >
            {isStreaming ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </button>
        </div>

        <div className="mt-2 flex items-center gap-4 text-[10px] font-mono text-white/30">
          <span>Press Enter to send</span>
          <span>•</span>
          <span>Shift+Enter for new line</span>
        </div>
      </form>
    </div>
  );
}
