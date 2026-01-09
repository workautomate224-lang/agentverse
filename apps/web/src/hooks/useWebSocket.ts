/**
 * WebSocket Hook for Real-time Simulation Updates
 * Handles connection management, subscriptions, and message handling.
 */

import { useCallback, useEffect, useRef, useState } from 'react';

// ============= Types =============

export interface ProgressData {
  run_id: string;
  progress: number;
  agents_completed: number;
  agents_failed: number;
  agents_total: number;
  status: string;
  extra?: Record<string, unknown>;
}

export interface AgentCompleteData {
  run_id: string;
  agent_index: number;
  tokens_used: number;
  response_preview?: string;
}

export interface RunCompleteData {
  run_id: string;
  result_id: string;
  summary: {
    confidence_score: number;
    executive_summary: string;
    key_takeaways: string[];
  };
}

export interface RunFailedData {
  run_id: string;
  error: string;
}

export interface WebSocketMessage {
  type: string;
  data?: ProgressData | AgentCompleteData | RunCompleteData | RunFailedData | Record<string, unknown>;
  run_id?: string;
  error?: string;
  message?: string;
}

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

export interface UseWebSocketOptions {
  /** Run ID to subscribe to */
  runId?: string;
  /** Auto-reconnect on disconnect */
  autoReconnect?: boolean;
  /** Reconnect delay in ms */
  reconnectDelay?: number;
  /** Max reconnect attempts */
  maxReconnectAttempts?: number;
  /** Callback for progress updates */
  onProgress?: (data: ProgressData) => void;
  /** Callback when an agent completes */
  onAgentComplete?: (data: AgentCompleteData) => void;
  /** Callback when run completes */
  onRunComplete?: (data: RunCompleteData) => void;
  /** Callback when run fails */
  onRunFailed?: (data: RunFailedData) => void;
  /** Callback for any message */
  onMessage?: (message: WebSocketMessage) => void;
  /** Callback for connection status changes */
  onStatusChange?: (status: ConnectionStatus) => void;
}

export interface UseWebSocketReturn {
  /** Current connection status */
  status: ConnectionStatus;
  /** Latest progress data */
  progress: ProgressData | null;
  /** Subscribe to a run */
  subscribe: (runId: string) => void;
  /** Unsubscribe from a run */
  unsubscribe: (runId: string) => void;
  /** Send a message */
  send: (message: Record<string, unknown>) => void;
  /** Manually connect */
  connect: () => void;
  /** Manually disconnect */
  disconnect: () => void;
  /** Error message if any */
  error: string | null;
}

// ============= Hook =============

export function useWebSocket(options: UseWebSocketOptions = {}): UseWebSocketReturn {
  const {
    runId,
    autoReconnect = true,
    reconnectDelay = 3000,
    maxReconnectAttempts = 5,
    onProgress,
    onAgentComplete,
    onRunComplete,
    onRunFailed,
    onMessage,
    onStatusChange,
  } = options;

  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const [progress, setProgress] = useState<ProgressData | null>(null);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isUnmountedRef = useRef(false);

  // Get WebSocket URL
  const getWsUrl = useCallback(() => {
    // Use dedicated WS URL if available, otherwise extract from API URL
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL;
    if (wsUrl) {
      const path = runId ? `/ws/${runId}` : '/ws';
      return `${wsUrl}${path}`;
    }

    // Fallback: extract host from API URL or use localhost
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    const host = apiUrl?.replace(/^https?:\/\//, '') || 'localhost:8000';
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const path = runId ? `/ws/${runId}` : '/ws';
    return `${protocol}//${host}${path}`;
  }, [runId]);

  // Update status
  const updateStatus = useCallback((newStatus: ConnectionStatus) => {
    setStatus(newStatus);
    onStatusChange?.(newStatus);
  }, [onStatusChange]);

  // Handle incoming messages
  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const message: WebSocketMessage = JSON.parse(event.data);
      onMessage?.(message);

      switch (message.type) {
        case 'progress':
          if (message.data) {
            const progressData = message.data as ProgressData;
            setProgress(progressData);
            onProgress?.(progressData);
          }
          break;

        case 'agent_complete':
          if (message.data) {
            onAgentComplete?.(message.data as AgentCompleteData);
          }
          break;

        case 'run_complete':
          if (message.data) {
            onRunComplete?.(message.data as RunCompleteData);
          }
          break;

        case 'run_failed':
          if (message.data) {
            onRunFailed?.(message.data as RunFailedData);
          }
          break;

        case 'subscribed':
          // Successfully subscribed to run
          break;

        case 'unsubscribed':
          // Successfully unsubscribed from run
          break;

        case 'pong':
          // Heartbeat response
          break;

        case 'error':
          setError(message.message || 'Unknown WebSocket error');
          break;
      }
    } catch {
      // Failed to parse WebSocket message - ignore invalid messages
    }
  }, [onMessage, onProgress, onAgentComplete, onRunComplete, onRunFailed]);

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (isUnmountedRef.current) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    updateStatus('connecting');
    setError(null);

    try {
      const url = getWsUrl();
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        updateStatus('connected');
        reconnectAttemptsRef.current = 0;
      };

      ws.onmessage = handleMessage;

      ws.onerror = () => {
        setError('WebSocket connection error');
        updateStatus('error');
      };

      ws.onclose = (event) => {
        updateStatus('disconnected');

        // Auto-reconnect if enabled and not intentionally closed
        if (
          autoReconnect &&
          !isUnmountedRef.current &&
          event.code !== 1000 &&
          reconnectAttemptsRef.current < maxReconnectAttempts
        ) {
          reconnectAttemptsRef.current++;
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, reconnectDelay);
        }
      };
    } catch {
      setError('Failed to connect to WebSocket');
      updateStatus('error');
    }
  }, [getWsUrl, handleMessage, updateStatus, autoReconnect, reconnectDelay, maxReconnectAttempts]);

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close(1000, 'Client disconnect');
      wsRef.current = null;
    }

    updateStatus('disconnected');
  }, [updateStatus]);

  // Send a message
  const send = useCallback((message: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
    // Silently ignore if not connected - the connection status is exposed via status state
  }, []);

  // Subscribe to a run
  const subscribe = useCallback((subscribeRunId: string) => {
    send({ type: 'subscribe', run_id: subscribeRunId });
  }, [send]);

  // Unsubscribe from a run
  const unsubscribe = useCallback((unsubscribeRunId: string) => {
    send({ type: 'unsubscribe', run_id: unsubscribeRunId });
  }, [send]);

  // Connect on mount
  useEffect(() => {
    isUnmountedRef.current = false;
    connect();

    return () => {
      isUnmountedRef.current = true;
      disconnect();
    };
  }, [connect, disconnect]);

  // Heartbeat ping every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        send({ type: 'ping' });
      }
    }, 30000);

    return () => clearInterval(interval);
  }, [send]);

  return {
    status,
    progress,
    subscribe,
    unsubscribe,
    send,
    connect,
    disconnect,
    error,
  };
}

// ============= Convenience Hook for Run Progress =============

export interface UseRunProgressOptions {
  runId: string;
  onComplete?: (data: RunCompleteData) => void;
  onFailed?: (data: RunFailedData) => void;
}

export interface UseRunProgressReturn {
  status: ConnectionStatus;
  progress: number;
  agentsCompleted: number;
  agentsFailed: number;
  agentsTotal: number;
  runStatus: string;
  isComplete: boolean;
  isFailed: boolean;
  error: string | null;
  resultId: string | null;
}

export function useRunProgress(options: UseRunProgressOptions): UseRunProgressReturn {
  const { runId, onComplete, onFailed } = options;

  const [runStatus, setRunStatus] = useState<string>('pending');
  const [isComplete, setIsComplete] = useState(false);
  const [isFailed, setIsFailed] = useState(false);
  const [resultId, setResultId] = useState<string | null>(null);

  const handleRunComplete = useCallback((data: RunCompleteData) => {
    setIsComplete(true);
    setRunStatus('completed');
    setResultId(data.result_id);
    onComplete?.(data);
  }, [onComplete]);

  const handleRunFailed = useCallback((data: RunFailedData) => {
    setIsFailed(true);
    setRunStatus('failed');
    onFailed?.(data);
  }, [onFailed]);

  const { status, progress, error } = useWebSocket({
    runId,
    onProgress: (data) => {
      setRunStatus(data.status);
    },
    onRunComplete: handleRunComplete,
    onRunFailed: handleRunFailed,
  });

  return {
    status,
    progress: progress?.progress ?? 0,
    agentsCompleted: progress?.agents_completed ?? 0,
    agentsFailed: progress?.agents_failed ?? 0,
    agentsTotal: progress?.agents_total ?? 0,
    runStatus,
    isComplete,
    isFailed,
    error,
    resultId,
  };
}

export default useWebSocket;
