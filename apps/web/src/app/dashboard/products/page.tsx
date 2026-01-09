'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  Plus,
  TrendingUp,
  Lightbulb,
  Users,
  ArrowRight,
  Loader2,
  MoreVertical,
  BarChart3,
  Play,
  Pause,
  CheckCircle,
  Clock,
  XCircle,
  Search,
  Package,
  Terminal,
  Eye,
  Activity,
  Gem,
} from 'lucide-react';
import { useProducts, useProductStats, useDeleteProduct } from '@/hooks/useApi';
import type { Product } from '@/lib/api';
import { cn } from '@/lib/utils';

// Original product types
const basicProductTypes = [
  {
    type: 'predict',
    name: 'PREDICT',
    description: 'Quantitative predictions with statistical confidence intervals',
    icon: TrendingUp,
    features: ['Elections', 'Markets', 'Trends'],
    key: 'P',
    category: 'basic',
  },
  {
    type: 'insight',
    name: 'INSIGHT',
    description: 'Qualitative deep-dive analysis and sentiment studies',
    icon: Lightbulb,
    features: ['Focus Groups', 'Sentiment', 'Perception'],
    key: 'I',
    category: 'basic',
  },
  {
    type: 'simulate',
    name: 'SIMULATE',
    description: 'Real-time interactive simulations with agent behaviors',
    icon: Users,
    features: ['Scenarios', 'A/B Tests', 'What-If'],
    key: 'S',
    category: 'basic',
  },
];

// Advanced AI Models - Enterprise Intelligence Suite
const advancedProductTypes = [
  {
    type: 'oracle',
    name: 'ORACLE',
    description: 'Market Intelligence & Consumer Prediction for corporate research',
    icon: Eye,
    features: ['Market Share', 'Brand Analysis', 'Consumer Intent'],
    key: 'O',
    category: 'advanced',
    badge: 'ENTERPRISE',
  },
  {
    type: 'pulse',
    name: 'PULSE',
    description: 'Dynamic Political & Election Simulation with real-time tracking',
    icon: Activity,
    features: ['Elections', 'Voter Behavior', 'Campaign Impact'],
    key: 'U',
    category: 'advanced',
    badge: 'POLITICAL',
  },
  {
    type: 'prism',
    name: 'PRISM',
    description: 'Policy Impact & Public Sector Analytics for government research',
    icon: Gem,
    features: ['Policy Impact', 'Crisis Response', 'Public Opinion'],
    key: 'R',
    category: 'advanced',
    badge: 'PUBLIC SECTOR',
  },
];

// All product types combined
const productTypes = [...basicProductTypes, ...advancedProductTypes];

export default function ProductsPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState<string>('all');
  const { data: products, isLoading } = useProducts();
  const { data: stats } = useProductStats();
  const deleteProduct = useDeleteProduct();

  const filteredProducts = products?.filter((product) => {
    const matchesSearch = product.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      product.description?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesType = filterType === 'all' || product.product_type === filterType;
    return matchesSearch && matchesType;
  }) || [];

  const handleDelete = async (productId: string) => {
    if (confirm('Delete this product?')) {
      await deleteProduct.mutateAsync(productId);
    }
  };

  return (
    <div className="min-h-screen bg-black p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Package className="w-4 h-4 text-white/60" />
            <span className="text-xs font-mono text-white/40 uppercase tracking-wider">Product Module</span>
          </div>
          <h1 className="text-xl font-mono font-bold text-white">Products</h1>
          <p className="text-sm font-mono text-white/50 mt-1">
            AI-powered research products
          </p>
        </div>
        <Link href="/dashboard/products/new">
          <Button size="sm">
            <Plus className="w-3 h-3 mr-2" />
            NEW PRODUCT
          </Button>
        </Link>
      </div>

      {/* Stats Overview */}
      {stats && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-8">
          <div className="bg-white/5 border border-white/10 p-4">
            <p className="text-[10px] font-mono text-white/40 uppercase tracking-wider">TOTAL</p>
            <p className="text-2xl font-mono font-bold text-white mt-1">{stats.total_products}</p>
          </div>
          <div className="bg-white/5 border border-white/10 p-4">
            <p className="text-[10px] font-mono text-white/40 uppercase tracking-wider">ACTIVE</p>
            <p className="text-2xl font-mono font-bold text-white mt-1">{stats.active_runs}</p>
          </div>
          <div className="bg-white/5 border border-white/10 p-4">
            <p className="text-[10px] font-mono text-white/40 uppercase tracking-wider">COMPLETED</p>
            <p className="text-2xl font-mono font-bold text-green-400 mt-1">{stats.completed_runs}</p>
          </div>
          <div className="bg-white/5 border border-white/10 p-4">
            <p className="text-[10px] font-mono text-white/40 uppercase tracking-wider">AGENTS</p>
            <p className="text-2xl font-mono font-bold text-white mt-1">{formatNumber(stats.total_agents)}</p>
          </div>
        </div>
      )}

      {/* Advanced AI Models - Enterprise Suite */}
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-3">
          <Gem className="w-3 h-3 text-purple-400" />
          <h2 className="text-xs font-mono text-purple-400 uppercase tracking-wider">Advanced AI Models</h2>
          <span className="text-[8px] font-mono bg-purple-500/20 text-purple-400 px-1.5 py-0.5 uppercase">Enterprise</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {advancedProductTypes.map((product) => (
            <Link
              key={product.type}
              href={`/dashboard/products/new?type=${product.type}`}
              className="group bg-gradient-to-br from-purple-500/10 to-blue-500/5 border border-purple-500/20 p-4 hover:bg-purple-500/[0.15] hover:border-purple-500/40 transition-all"
            >
              <div className="flex items-start justify-between mb-3">
                <product.icon className="w-4 h-4 text-purple-400" />
                <div className="flex items-center gap-2">
                  <span className="text-[8px] font-mono bg-purple-500/30 text-purple-300 px-1.5 py-0.5 uppercase">{product.badge}</span>
                  <span className="text-[10px] font-mono text-white/30">[{product.key}]</span>
                  <ArrowRight className="w-3 h-3 text-purple-400/50 group-hover:text-purple-400 transition-colors" />
                </div>
              </div>
              <h3 className="text-sm font-mono font-bold text-white mb-1">{product.name}</h3>
              <p className="text-xs font-mono text-white/50 mb-3">{product.description}</p>
              <div className="flex flex-wrap gap-1">
                {product.features.map((feature) => (
                  <span
                    key={feature}
                    className="text-[10px] font-mono text-purple-300/60 px-1.5 py-0.5 bg-purple-500/10"
                  >
                    {feature}
                  </span>
                ))}
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* Basic Product Types */}
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-3">
          <Terminal className="w-3 h-3 text-white/40" />
          <h2 className="text-xs font-mono text-white/40 uppercase tracking-wider">Standard Products</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {basicProductTypes.map((product) => (
            <Link
              key={product.type}
              href={`/dashboard/products/new?type=${product.type}`}
              className="group bg-white/5 border border-white/10 p-4 hover:bg-white/[0.07] hover:border-white/20 transition-all"
            >
              <div className="flex items-start justify-between mb-3">
                <product.icon className="w-4 h-4 text-white/60" />
                <div className="flex items-center gap-1">
                  <span className="text-[10px] font-mono text-white/30">[{product.key}]</span>
                  <ArrowRight className="w-3 h-3 text-white/30 group-hover:text-white/60 transition-colors" />
                </div>
              </div>
              <h3 className="text-sm font-mono font-bold text-white mb-1">{product.name}</h3>
              <p className="text-xs font-mono text-white/40 mb-3">{product.description}</p>
              <div className="flex flex-wrap gap-1">
                {product.features.map((feature) => (
                  <span
                    key={feature}
                    className="text-[10px] font-mono text-white/40 px-1.5 py-0.5 bg-white/5"
                  >
                    {feature}
                  </span>
                ))}
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* Products List */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <BarChart3 className="w-3 h-3 text-white/40" />
            <h2 className="text-xs font-mono text-white/40 uppercase tracking-wider">Your Products</h2>
          </div>
          <div className="flex items-center gap-2">
            {/* Search */}
            <div className="relative">
              <Search className="w-3 h-3 absolute left-2 top-1/2 -translate-y-1/2 text-white/30" />
              <input
                type="text"
                placeholder="Search..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-7 pr-3 py-1.5 bg-white/5 border border-white/10 text-xs font-mono text-white placeholder:text-white/30 w-48 focus:outline-none focus:border-white/30"
              />
            </div>
            {/* Filter */}
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="px-2 py-1.5 bg-white/5 border border-white/10 text-xs font-mono text-white appearance-none focus:outline-none focus:border-white/30"
            >
              <option value="all">All Types</option>
              <optgroup label="Standard">
                <option value="predict">Predict</option>
                <option value="insight">Insight</option>
                <option value="simulate">Simulate</option>
              </optgroup>
              <optgroup label="Advanced AI">
                <option value="oracle">Oracle</option>
                <option value="pulse">Pulse</option>
                <option value="prism">Prism</option>
              </optgroup>
            </select>
          </div>
        </div>

        <div className="bg-white/5 border border-white/10">
          {isLoading ? (
            <div className="p-8 flex items-center justify-center">
              <Loader2 className="w-4 h-4 animate-spin text-white/40" />
            </div>
          ) : filteredProducts.length > 0 ? (
            <div className="divide-y divide-white/5">
              {filteredProducts.map((product) => (
                <ProductRow
                  key={product.id}
                  product={product}
                  onDelete={() => handleDelete(product.id)}
                />
              ))}
            </div>
          ) : (
            <div className="p-8 text-center">
              <div className="w-12 h-12 bg-white/5 flex items-center justify-center mx-auto mb-4">
                <Package className="w-5 h-5 text-white/30" />
              </div>
              <p className="text-sm font-mono text-white/60 mb-1">No products</p>
              <p className="text-xs font-mono text-white/30 mb-4">
                Create your first product to start
              </p>
              <Link href="/dashboard/products/new">
                <Button variant="outline" size="sm" className="font-mono text-xs border-white/20 text-white/60 hover:bg-white/5 hover:text-white">
                  CREATE PRODUCT
                </Button>
              </Link>
            </div>
          )}
        </div>
      </div>

      {/* Footer Status */}
      <div className="mt-8 pt-4 border-t border-white/5">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1">
              <Terminal className="w-3 h-3" />
              <span>PRODUCT MODULE</span>
            </div>
          </div>
          <span>AGENTVERSE v1.0.0</span>
        </div>
      </div>
    </div>
  );
}

function ProductRow({ product, onDelete }: { product: Product; onDelete: () => void }) {
  const [showMenu, setShowMenu] = useState(false);

  const typeConfig = productTypes.find((t) => t.type === product.product_type);
  const Icon = typeConfig?.icon || BarChart3;

  return (
    <div className="flex items-center justify-between p-4 hover:bg-white/5 transition-colors">
      <div className="flex items-center gap-4">
        <div className="w-8 h-8 bg-white/5 flex items-center justify-center">
          <Icon className="w-4 h-4 text-white/60" />
        </div>
        <div>
          <Link
            href={`/dashboard/products/${product.id}`}
            className="text-sm font-mono text-white hover:text-white/80"
          >
            {product.name}
          </Link>
          <div className="flex items-center gap-2 text-[10px] font-mono text-white/40">
            <span className="uppercase">{product.product_type}</span>
            {product.sub_type && (
              <>
                <span>/</span>
                <span className="uppercase">{product.sub_type.replace('_', ' ')}</span>
              </>
            )}
            <span>/</span>
            <span>{product.persona_count} agents</span>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <StatusBadge status={product.status} />
        <span className="text-[10px] font-mono text-white/30">
          {new Date(product.created_at).toLocaleDateString()}
        </span>
        <div className="relative">
          <button
            onClick={() => setShowMenu(!showMenu)}
            className="p-1.5 hover:bg-white/10 transition-colors"
          >
            <MoreVertical className="w-3 h-3 text-white/40" />
          </button>
          {showMenu && (
            <div className="absolute right-0 mt-1 w-36 bg-black border border-white/20 py-1 z-10">
              <Link
                href={`/dashboard/products/${product.id}`}
                className="block px-3 py-1.5 text-xs font-mono text-white/60 hover:bg-white/10"
              >
                View Details
              </Link>
              <Link
                href={`/dashboard/products/${product.id}/runs`}
                className="block px-3 py-1.5 text-xs font-mono text-white/60 hover:bg-white/10"
              >
                View Runs
              </Link>
              <button
                onClick={onDelete}
                className="block w-full text-left px-3 py-1.5 text-xs font-mono text-red-400 hover:bg-white/10"
              >
                Delete
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { icon: typeof CheckCircle; className: string; label: string }> = {
    draft: {
      icon: Clock,
      className: 'bg-white/10 text-white/50',
      label: 'DRAFT',
    },
    active: {
      icon: Play,
      className: 'bg-blue-500/20 text-blue-400',
      label: 'ACTIVE',
    },
    running: {
      icon: Play,
      className: 'bg-blue-500/20 text-blue-400 animate-pulse',
      label: 'RUNNING',
    },
    paused: {
      icon: Pause,
      className: 'bg-yellow-500/20 text-yellow-400',
      label: 'PAUSED',
    },
    completed: {
      icon: CheckCircle,
      className: 'bg-green-500/20 text-green-400',
      label: 'DONE',
    },
    failed: {
      icon: XCircle,
      className: 'bg-red-500/20 text-red-400',
      label: 'FAILED',
    },
  };

  const { icon: Icon, className, label } = config[status] || config.draft;

  return (
    <span className={cn('inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-mono uppercase', className)}>
      <Icon className="w-2.5 h-2.5" />
      {label}
    </span>
  );
}

function formatNumber(num: number): string {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M';
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K';
  }
  return String(num);
}
