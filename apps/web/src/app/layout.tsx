import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Providers } from '@/components/providers';
import { Toaster } from '@/components/ui/toaster';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  metadataBase: new URL('http://localhost:3002'),
  title: 'AgentVerse - AI Agent Simulation Platform',
  description: 'Simulate human decisions at scale with AI-powered agents',
  keywords: ['AI', 'simulation', 'market research', 'prediction', 'agents'],
  authors: [{ name: 'AgentVerse Team' }],
  icons: {
    icon: '/favicon.svg',
  },
  openGraph: {
    title: 'AgentVerse - AI Agent Simulation Platform',
    description: 'Simulate human decisions at scale with AI-powered agents',
    type: 'website',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <Providers>
          {children}
          <Toaster />
        </Providers>
      </body>
    </html>
  );
}
