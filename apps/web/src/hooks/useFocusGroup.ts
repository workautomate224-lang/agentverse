/**
 * Focus Group Hooks
 * React Query hooks for Virtual Focus Group functionality.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState, useCallback, useRef, useEffect } from 'react';
import api, {
  FocusGroupSession,
  FocusGroupSessionCreate,
  FocusGroupSessionUpdate,
  FocusGroupMessage,
  InterviewRequest,
  InterviewResponse,
  GroupDiscussionRequest,
  GroupDiscussionResponse,
  SessionSummaryResponse,
  AvailableAgent,
  StreamingInterviewChunk,
} from '@/lib/api';
import { useApiAuth } from './useApi';

// ========== Session Hooks ==========

// Cache times for focus group hooks
const FOCUS_GROUP_CACHE = {
  SHORT: 60 * 1000,      // 1 minute
  MEDIUM: 5 * 60 * 1000, // 5 minutes
} as const;

export function useFocusGroupSessions(params?: {
  productId?: string;
  status?: string;
  limit?: number;
}) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['focusGroupSessions', params],
    queryFn: () => api.listFocusGroupSessions({
      product_id: params?.productId,
      status: params?.status,
      limit: params?.limit,
    }),
    enabled: isReady,
    staleTime: FOCUS_GROUP_CACHE.MEDIUM,
  });
}

export function useFocusGroupSession(sessionId: string | null) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['focusGroupSession', sessionId],
    queryFn: () => api.getFocusGroupSession(sessionId!),
    enabled: isReady && !!sessionId,
    staleTime: FOCUS_GROUP_CACHE.SHORT,
  });
}

export function useCreateFocusGroupSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: FocusGroupSessionCreate) => api.createFocusGroupSession(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['focusGroupSessions'] });
    },
  });
}

export function useUpdateFocusGroupSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ sessionId, data }: { sessionId: string; data: FocusGroupSessionUpdate }) =>
      api.updateFocusGroupSession(sessionId, data),
    onSuccess: (_, { sessionId }) => {
      queryClient.invalidateQueries({ queryKey: ['focusGroupSession', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['focusGroupSessions'] });
    },
  });
}

export function useEndFocusGroupSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (sessionId: string) => api.endFocusGroupSession(sessionId),
    onSuccess: (_, sessionId) => {
      queryClient.invalidateQueries({ queryKey: ['focusGroupSession', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['focusGroupSessions'] });
    },
  });
}

// ========== Interview Hooks ==========

export function useInterviewAgent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ sessionId, data }: { sessionId: string; data: InterviewRequest }) =>
      api.interviewAgent(sessionId, data),
    onSuccess: (_, { sessionId }) => {
      queryClient.invalidateQueries({ queryKey: ['focusGroupMessages', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['focusGroupSession', sessionId] });
    },
  });
}

export function useStreamingInterview(sessionId: string | null) {
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamedContent, setStreamedContent] = useState('');
  const [currentAgent, setCurrentAgent] = useState<{ id: string; name: string } | null>(null);
  const [sentiment, setSentiment] = useState<{ score: number; emotion: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const queryClient = useQueryClient();

  const startStream = useCallback(async (question: string, targetAgentIds?: string[]) => {
    if (!sessionId) return;

    setIsStreaming(true);
    setStreamedContent('');
    setCurrentAgent(null);
    setSentiment(null);
    setError(null);

    abortControllerRef.current = new AbortController();

    try {
      const token = api.getAccessToken();
      const response = await fetch(api.getStreamInterviewUrl(sessionId), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          question,
          target_agent_ids: targetAgentIds,
        }),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        throw new Error('Failed to start interview stream');
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('No response body');
      }

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const text = decoder.decode(value);
        const lines = text.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') {
              continue;
            }

            try {
              const chunk: StreamingInterviewChunk = JSON.parse(data);

              if (chunk.agent_id && chunk.agent_name && !currentAgent) {
                setCurrentAgent({ id: chunk.agent_id, name: chunk.agent_name });
              }

              if (chunk.chunk) {
                setStreamedContent(prev => prev + chunk.chunk);
              }

              if (chunk.is_final && chunk.sentiment_score !== undefined) {
                setSentiment({
                  score: chunk.sentiment_score,
                  emotion: chunk.emotion || 'neutral',
                });
              }
            } catch {
              // Ignore parse errors
            }
          }
        }
      }
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        setError((err as Error).message);
      }
    } finally {
      setIsStreaming(false);
      queryClient.invalidateQueries({ queryKey: ['focusGroupMessages', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['focusGroupSession', sessionId] });
    }
  }, [sessionId, queryClient]);

  const stopStream = useCallback(() => {
    abortControllerRef.current?.abort();
    setIsStreaming(false);
  }, []);

  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  return {
    isStreaming,
    streamedContent,
    currentAgent,
    sentiment,
    error,
    startStream,
    stopStream,
  };
}

// ========== Group Discussion Hooks ==========

export function useGroupDiscussion() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ sessionId, data }: { sessionId: string; data: GroupDiscussionRequest }) =>
      api.groupDiscussion(sessionId, data),
    onSuccess: (_, { sessionId }) => {
      queryClient.invalidateQueries({ queryKey: ['focusGroupMessages', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['focusGroupSession', sessionId] });
    },
  });
}

// ========== Message Hooks ==========

export function useFocusGroupMessages(sessionId: string | null, limit?: number, isStreaming = false) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['focusGroupMessages', sessionId, limit],
    queryFn: () => api.getFocusGroupMessages(sessionId!, { limit }),
    enabled: isReady && !!sessionId,
    staleTime: 30 * 1000, // 30 seconds
    // Only poll when actively streaming, otherwise rely on cache
    refetchInterval: isStreaming ? 5000 : false,
  });
}

// ========== Summary Hooks ==========

export function useSessionSummary(sessionId: string | null) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['focusGroupSummary', sessionId],
    queryFn: () => api.getSessionSummary(sessionId!),
    enabled: isReady && !!sessionId,
    staleTime: FOCUS_GROUP_CACHE.MEDIUM,
  });
}

// ========== Agent Selection Hooks ==========

export function useAvailableAgents(productId: string | null, runId?: string) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['availableAgents', productId, runId],
    queryFn: () => api.getAvailableAgents(productId!, runId),
    enabled: isReady && !!productId,
    staleTime: FOCUS_GROUP_CACHE.MEDIUM,
  });
}
