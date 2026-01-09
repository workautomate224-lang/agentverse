'use client';

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { api } from '@/lib/api';
import { AlertCircle, RefreshCw } from 'lucide-react';

interface ApiStatusContextType {
  isOnline: boolean;
  isChecking: boolean;
  lastChecked: Date | null;
  checkNow: () => void;
}

const ApiStatusContext = createContext<ApiStatusContextType>({
  isOnline: true,
  isChecking: false,
  lastChecked: null,
  checkNow: () => {},
});

export function useApiStatus() {
  return useContext(ApiStatusContext);
}

interface ApiStatusProviderProps {
  children: ReactNode;
}

export function ApiStatusProvider({ children }: ApiStatusProviderProps) {
  const [isOnline, setIsOnline] = useState(true);
  const [isChecking, setIsChecking] = useState(true);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  const checkHealth = async () => {
    setIsChecking(true);
    try {
      const result = await api.checkHealth();
      setIsOnline(result.healthy);
    } catch {
      setIsOnline(false);
    } finally {
      setIsChecking(false);
      setLastChecked(new Date());
    }
  };

  useEffect(() => {
    // Initial check
    checkHealth();

    // Check every 30 seconds when offline, every 5 minutes when online
    const interval = setInterval(() => {
      checkHealth();
    }, isOnline ? 5 * 60 * 1000 : 30 * 1000);

    return () => clearInterval(interval);
  }, [isOnline]);

  return (
    <ApiStatusContext.Provider
      value={{
        isOnline,
        isChecking,
        lastChecked,
        checkNow: checkHealth,
      }}
    >
      {!isOnline && !isChecking && (
        <div className="fixed top-0 left-0 right-0 z-50 bg-red-600 text-white px-4 py-2 text-center font-mono text-sm">
          <div className="flex items-center justify-center gap-2">
            <AlertCircle className="w-4 h-4" />
            <span>Unable to connect to server. Some features may not work.</span>
            <button
              onClick={checkHealth}
              className="ml-4 px-2 py-0.5 bg-white/20 hover:bg-white/30 rounded text-xs flex items-center gap-1 transition-colors"
            >
              <RefreshCw className="w-3 h-3" />
              Retry
            </button>
          </div>
        </div>
      )}
      <div className={!isOnline && !isChecking ? 'pt-8' : ''}>
        {children}
      </div>
    </ApiStatusContext.Provider>
  );
}
