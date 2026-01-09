'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SessionProvider } from 'next-auth/react';
import { useState } from 'react';
import { ApiStatusProvider } from '@/components/providers/ApiStatusProvider';

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 5 * 60 * 1000, // 5 minutes - reduces unnecessary refetches
            gcTime: 30 * 60 * 1000, // 30 minutes garbage collection
            refetchOnWindowFocus: false,
            refetchOnReconnect: false,
            retry: 1, // Only retry once on failure
            retryDelay: 1000, // 1 second delay between retries
          },
          mutations: {
            retry: 1,
          },
        },
      })
  );

  return (
    <SessionProvider>
      <QueryClientProvider client={queryClient}>
        <ApiStatusProvider>
          {children}
        </ApiStatusProvider>
      </QueryClientProvider>
    </SessionProvider>
  );
}
