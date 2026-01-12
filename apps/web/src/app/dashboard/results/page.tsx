'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  BarChart3,
  Play,
  CheckCircle,
  Clock,
  XCircle,
  Loader2,
  Users,
  Target,
  Terminal,
  Activity,
  TrendingUp,
} from 'lucide-react';
import { useProducts } from '@/hooks/useApi';
import { cn } from '@/lib/utils';

const statusOptions = [
  { value: '', label: 'All Status' },
  { value: 'completed', label: 'Completed' },
  { value: 'running', label: 'Running' },
  { value: 'draft', label: 'Draft' },
  { value: 'failed', label: 'Failed' },
];

const typeOptions = [
  { value: '', label: 'All Types' },
  { value: 'predict', label: 'Predict' },
  { value: 'insight', label: 'Insight' },
  { value: 'simulate', label: 'Simulate' },
];

export default function ResultsPage() {
  const [statusFilter, setStatusFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const { data: products, isLoading, error, refetch } = useProducts({
    status: statusFilter || undefined,
    product_type: typeFilter || undefined,
  });

  // Filter to show only products with completed runs
  const completedProducts = products?.filter(p => p.status === 'completed') || [];

  return (
    <div className="min-h-screen bg-black p-4 md:p-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6 md:mb-8">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <BarChart3 className="w-3.5 h-3.5 md:w-4 md:h-4 text-white/60" />
            <span className="text-[10px] md:text-xs font-mono text-white/40 uppercase tracking-wider">Results Module</span>
          </div>
          <h1 className="text-lg md:text-xl font-mono font-bold text-white">Product Results</h1>
          <p className="text-xs md:text-sm font-mono text-white/50 mt-1">
            View and analyze AI simulation outcomes
          </p>
        </div>
        <Link href="/dashboard/products/new">
          <Button size="sm" className="w-full sm:w-auto font-mono text-[10px] md:text-xs">
            <Play className="w-3 h-3 mr-1.5 md:mr-2" />
            <span className="hidden sm:inline">NEW PRODUCT</span>
            <span className="sm:hidden">NEW</span>
          </Button>
        </Link>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2 md:gap-3 mb-4 md:mb-6">
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="flex-1 sm:flex-none px-2.5 md:px-3 py-1.5 bg-white/5 border border-white/10 text-[10px] md:text-xs font-mono text-white appearance-none focus:outline-none focus:border-white/30"
        >
          {statusOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="flex-1 sm:flex-none px-2.5 md:px-3 py-1.5 bg-white/5 border border-white/10 text-[10px] md:text-xs font-mono text-white appearance-none focus:outline-none focus:border-white/30"
        >
          {typeOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="flex items-center justify-center py-8 md:py-12">
          <Loader2 className="w-4 h-4 md:w-5 md:h-5 animate-spin text-white/40" />
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 p-3 md:p-4">
          <p className="text-xs md:text-sm font-mono text-red-400">Failed to load products</p>
          <Button
            variant="outline"
            onClick={() => refetch()}
            className="mt-2 font-mono text-[10px] md:text-xs border-white/20 text-white/60 hover:bg-white/5"
          >
            RETRY
          </Button>
        </div>
      )}

      {/* Products List */}
      {!isLoading && !error && (
        <>
          {(!products || products.length === 0) ? (
            <div className="bg-white/5 border border-white/10">
              <div className="p-8 md:p-12 text-center">
                <div className="w-10 h-10 md:w-12 md:h-12 bg-white/5 flex items-center justify-center mx-auto mb-3 md:mb-4">
                  <BarChart3 className="w-4 h-4 md:w-5 md:h-5 text-white/30" />
                </div>
                <p className="text-xs md:text-sm font-mono text-white/60 mb-1">No results yet</p>
                <p className="text-[10px] md:text-xs font-mono text-white/30 mb-3 md:mb-4">
                  Create a product and run a simulation to see results
                </p>
                <Link href="/dashboard/products/new">
                  <Button size="sm" className="w-full sm:w-auto font-mono text-[10px] md:text-xs">
                    CREATE PRODUCT
                  </Button>
                </Link>
              </div>
            </div>
          ) : (
            <div className="space-y-2 md:space-y-3">
              {products.map((product) => (
                <ProductResultCard key={product.id} product={product} />
              ))}
            </div>
          )}
        </>
      )}

      {/* Footer Status */}
      <div className="mt-6 md:mt-8 pt-3 md:pt-4 border-t border-white/5">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-1">
            <Terminal className="w-3 h-3" />
            <span className="hidden sm:inline">RESULTS MODULE</span>
            <span className="sm:hidden">RESULTS</span>
          </div>
          <span>AGENTVERSE v1.0.0</span>
        </div>
      </div>
    </div>
  );
}

interface Product {
  id: string;
  name: string;
  description?: string | null;
  product_type: string;
  sub_type?: string | null;
  status: string;
  persona_count?: number;
  confidence_level?: number;
  created_at: string;
  updated_at: string;
}

function ProductResultCard({ product }: { product: Product }) {
  const statusConfig = getStatusConfig(product.status);
  const hasResults = product.status === 'completed';

  return (
    <Link href={`/dashboard/products/${product.id}`}>
      <div className="bg-white/5 border border-white/10 hover:bg-white/[0.07] hover:border-white/20 transition-all p-3 md:p-4">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2 sm:gap-3 mb-3">
          <div className="flex items-start gap-2 sm:gap-3 min-w-0">
            <div className="w-7 h-7 md:w-8 md:h-8 bg-white/5 flex items-center justify-center flex-shrink-0">
              <statusConfig.icon className={cn('w-3.5 h-3.5 md:w-4 md:h-4', statusConfig.color)} />
            </div>
            <div className="min-w-0 flex-1">
              <h3 className="text-xs md:text-sm font-mono font-bold text-white truncate">
                {product.name}
              </h3>
              <p className="text-[10px] font-mono text-white/40 mt-0.5 truncate">
                {product.product_type?.toUpperCase()} / {product.sub_type?.toUpperCase()}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1.5 md:gap-2 flex-wrap sm:flex-nowrap">
            {hasResults && (
              <span className="px-1 md:px-1.5 py-0.5 text-[9px] md:text-[10px] font-mono uppercase bg-blue-500/20 text-blue-400">
                HAS RESULTS
              </span>
            )}
            <span className={cn(
              'px-1 md:px-1.5 py-0.5 text-[9px] md:text-[10px] font-mono uppercase flex items-center gap-1',
              statusConfig.className
            )}>
              <statusConfig.icon className="w-2 h-2 md:w-2.5 md:h-2.5" />
              {statusConfig.label}
            </span>
          </div>
        </div>

        {product.description && (
          <p className="text-[10px] md:text-xs font-mono text-white/50 mb-3 line-clamp-2">
            {product.description}
          </p>
        )}

        {/* Stats */}
        <div className="grid grid-cols-3 gap-2 md:gap-3 pt-3 border-t border-white/5">
          <div>
            <div className="flex items-center gap-1 text-[9px] md:text-[10px] font-mono text-white/30 mb-0.5">
              <Users className="w-2 h-2 md:w-2.5 md:h-2.5" />
              <span className="hidden sm:inline">PERSONAS</span>
              <span className="sm:hidden">PRS</span>
            </div>
            <p className="text-[10px] md:text-xs font-mono text-white">{product.persona_count || 0}</p>
          </div>
          <div>
            <div className="flex items-center gap-1 text-[9px] md:text-[10px] font-mono text-white/30 mb-0.5">
              <Target className="w-2 h-2 md:w-2.5 md:h-2.5" />
              <span className="hidden sm:inline">CONFIDENCE</span>
              <span className="sm:hidden">CONF</span>
            </div>
            <p className="text-[10px] md:text-xs font-mono text-white">
              {product.confidence_level ? `${product.confidence_level}%` : '-'}
            </p>
          </div>
          <div>
            <div className="flex items-center gap-1 text-[9px] md:text-[10px] font-mono text-white/30 mb-0.5">
              <Clock className="w-2 h-2 md:w-2.5 md:h-2.5" />
              <span className="hidden sm:inline">UPDATED</span>
              <span className="sm:hidden">UPD</span>
            </div>
            <p className="text-[10px] md:text-xs font-mono text-white">
              {new Date(product.updated_at).toLocaleDateString()}
            </p>
          </div>
        </div>

        {/* Confidence bar for completed products */}
        {product.status === 'completed' && product.confidence_level && (
          <div className="mt-3 pt-3 border-t border-white/5">
            <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-1.5 sm:gap-2">
              <span className="text-[9px] md:text-[10px] font-mono text-white/40 uppercase">Overall Confidence</span>
              <div className="flex items-center gap-2">
                <div className="w-16 sm:w-20 bg-white/10 h-1">
                  <div
                    className={cn(
                      'h-1',
                      product.confidence_level >= 80 ? 'bg-green-500' :
                      product.confidence_level >= 60 ? 'bg-yellow-500' : 'bg-red-500'
                    )}
                    style={{ width: `${product.confidence_level}%` }}
                  />
                </div>
                <span className="text-[10px] md:text-xs font-mono font-bold text-white">
                  {product.confidence_level}%
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </Link>
  );
}

function getStatusConfig(status: string) {
  switch (status) {
    case 'completed':
      return {
        icon: CheckCircle,
        label: 'DONE',
        color: 'text-green-400',
        className: 'bg-green-500/20 text-green-400',
      };
    case 'running':
      return {
        icon: Activity,
        label: 'RUNNING',
        color: 'text-blue-400',
        className: 'bg-blue-500/20 text-blue-400 animate-pulse',
      };
    case 'draft':
      return {
        icon: Clock,
        label: 'DRAFT',
        color: 'text-yellow-400',
        className: 'bg-yellow-500/20 text-yellow-400',
      };
    case 'failed':
      return {
        icon: XCircle,
        label: 'FAILED',
        color: 'text-red-400',
        className: 'bg-red-500/20 text-red-400',
      };
    default:
      return {
        icon: Play,
        label: status?.toUpperCase() || 'UNKNOWN',
        color: 'text-white/60',
        className: 'bg-white/10 text-white/60',
      };
  }
}
