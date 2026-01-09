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
    <div className="min-h-screen bg-black p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <BarChart3 className="w-4 h-4 text-white/60" />
            <span className="text-xs font-mono text-white/40 uppercase tracking-wider">Results Module</span>
          </div>
          <h1 className="text-xl font-mono font-bold text-white">Product Results</h1>
          <p className="text-sm font-mono text-white/50 mt-1">
            View and analyze AI simulation outcomes
          </p>
        </div>
        <Link href="/dashboard/products/new">
          <Button size="sm">
            <Play className="w-3 h-3 mr-2" />
            NEW PRODUCT
          </Button>
        </Link>
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-6">
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-1.5 bg-white/5 border border-white/10 text-xs font-mono text-white appearance-none focus:outline-none focus:border-white/30"
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
          className="px-3 py-1.5 bg-white/5 border border-white/10 text-xs font-mono text-white appearance-none focus:outline-none focus:border-white/30"
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
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-4 h-4 animate-spin text-white/40" />
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 p-4">
          <p className="text-sm font-mono text-red-400">Failed to load products</p>
          <Button
            variant="outline"
            onClick={() => refetch()}
            className="mt-2 font-mono text-xs border-white/20 text-white/60 hover:bg-white/5"
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
              <div className="p-12 text-center">
                <div className="w-12 h-12 bg-white/5 flex items-center justify-center mx-auto mb-4">
                  <BarChart3 className="w-5 h-5 text-white/30" />
                </div>
                <p className="text-sm font-mono text-white/60 mb-1">No results yet</p>
                <p className="text-xs font-mono text-white/30 mb-4">
                  Create a product and run a simulation to see results
                </p>
                <Link href="/dashboard/products/new">
                  <Button size="sm">
                    CREATE PRODUCT
                  </Button>
                </Link>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              {products.map((product) => (
                <ProductResultCard key={product.id} product={product} />
              ))}
            </div>
          )}
        </>
      )}

      {/* Footer Status */}
      <div className="mt-8 pt-4 border-t border-white/5">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1">
              <Terminal className="w-3 h-3" />
              <span>RESULTS MODULE</span>
            </div>
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
      <div className="bg-white/5 border border-white/10 hover:bg-white/[0.07] hover:border-white/20 transition-all p-4">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 bg-white/5 flex items-center justify-center">
              <statusConfig.icon className={cn('w-4 h-4', statusConfig.color)} />
            </div>
            <div>
              <h3 className="text-sm font-mono font-bold text-white">
                {product.name}
              </h3>
              <p className="text-[10px] font-mono text-white/40 mt-0.5">
                {product.product_type?.toUpperCase()} / {product.sub_type?.toUpperCase()}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {hasResults && (
              <span className="px-1.5 py-0.5 text-[10px] font-mono uppercase bg-blue-500/20 text-blue-400">
                HAS RESULTS
              </span>
            )}
            <span className={cn(
              'px-1.5 py-0.5 text-[10px] font-mono uppercase flex items-center gap-1',
              statusConfig.className
            )}>
              <statusConfig.icon className="w-2.5 h-2.5" />
              {statusConfig.label}
            </span>
          </div>
        </div>

        {product.description && (
          <p className="text-xs font-mono text-white/50 mb-3 line-clamp-2">
            {product.description}
          </p>
        )}

        {/* Stats */}
        <div className="grid grid-cols-3 gap-3 pt-3 border-t border-white/5">
          <div>
            <div className="flex items-center gap-1 text-[10px] font-mono text-white/30 mb-0.5">
              <Users className="w-2.5 h-2.5" />
              PERSONAS
            </div>
            <p className="text-xs font-mono text-white">{product.persona_count || 0}</p>
          </div>
          <div>
            <div className="flex items-center gap-1 text-[10px] font-mono text-white/30 mb-0.5">
              <Target className="w-2.5 h-2.5" />
              CONFIDENCE
            </div>
            <p className="text-xs font-mono text-white">
              {product.confidence_level ? `${product.confidence_level}%` : '-'}
            </p>
          </div>
          <div>
            <div className="flex items-center gap-1 text-[10px] font-mono text-white/30 mb-0.5">
              <Clock className="w-2.5 h-2.5" />
              UPDATED
            </div>
            <p className="text-xs font-mono text-white">
              {new Date(product.updated_at).toLocaleDateString()}
            </p>
          </div>
        </div>

        {/* Confidence bar for completed products */}
        {product.status === 'completed' && product.confidence_level && (
          <div className="mt-3 pt-3 border-t border-white/5">
            <div className="flex justify-between items-center">
              <span className="text-[10px] font-mono text-white/40 uppercase">Overall Confidence</span>
              <div className="flex items-center gap-2">
                <div className="w-20 bg-white/10 h-1">
                  <div
                    className={cn(
                      'h-1',
                      product.confidence_level >= 80 ? 'bg-green-500' :
                      product.confidence_level >= 60 ? 'bg-yellow-500' : 'bg-red-500'
                    )}
                    style={{ width: `${product.confidence_level}%` }}
                  />
                </div>
                <span className="text-xs font-mono font-bold text-white">
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
