'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  ArrowLeft,
  TrendingUp,
  Lightbulb,
  Users,
  Play,
  Pause,
  RotateCcw,
  Settings,
  Trash2,
  Clock,
  CheckCircle,
  XCircle,
  Globe,
  Target,
  BarChart3,
  Loader2,
  AlertTriangle,
  ChevronRight,
  Terminal,
} from 'lucide-react';
import {
  useProduct,
  useProductRuns,
  useProductResults,
  useCreateProductRun,
  useStartProductRun,
  useCancelProductRun,
  useDeleteProduct,
} from '@/hooks/useApi';
import { cn } from '@/lib/utils';
import { toast } from '@/hooks/use-toast';

const productTypeConfig = {
  predict: { name: 'Predict', icon: TrendingUp },
  insight: { name: 'Insight', icon: Lightbulb },
  simulate: { name: 'Simulate', icon: Users },
};

export default function ProductDetailPage() {
  const params = useParams();
  const router = useRouter();
  const productId = params.id as string;

  const { data: product, isLoading: productLoading, error: productError } = useProduct(productId);
  const { data: runs, isLoading: runsLoading } = useProductRuns(productId);
  const { data: results, isLoading: resultsLoading } = useProductResults(productId);

  const createRun = useCreateProductRun();
  const startRun = useStartProductRun();
  const cancelRun = useCancelProductRun();
  const deleteProduct = useDeleteProduct();

  const [activeTab, setActiveTab] = useState<'overview' | 'runs' | 'results'>('overview');
  const [isDeleting, setIsDeleting] = useState(false);

  if (productLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-black">
        <Loader2 className="w-5 h-5 animate-spin text-white/40" />
      </div>
    );
  }

  if (productError || !product) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-black">
        <AlertTriangle className="w-8 h-8 text-red-400 mb-4" />
        <h2 className="text-lg font-mono font-bold text-white mb-2">Product Not Found</h2>
        <p className="text-sm font-mono text-white/50 mb-4">The product you&apos;re looking for doesn&apos;t exist.</p>
        <Link href="/dashboard/products">
          <Button variant="outline" className="font-mono text-xs border-white/20 text-white/60 hover:bg-white/5">
            <ArrowLeft className="w-3 h-3 mr-2" />
            BACK TO PRODUCTS
          </Button>
        </Link>
      </div>
    );
  }

  const typeConfig = productTypeConfig[product.product_type as keyof typeof productTypeConfig];
  const Icon = typeConfig?.icon || BarChart3;

  const handleCreateRun = async () => {
    try {
      await createRun.mutateAsync({ productId });
      toast({
        title: 'Run Created',
        description: 'A new simulation run has been created.',
        variant: 'success',
      });
    } catch {
      toast({
        title: 'Error',
        description: 'Failed to create run. Please try again.',
        variant: 'destructive',
      });
    }
  };

  const handleStartRun = async (runId: string) => {
    try {
      await startRun.mutateAsync({ productId, runId });
      toast({
        title: 'Run Started',
        description: 'Simulation is now running...',
        variant: 'success',
      });
    } catch {
      toast({
        title: 'Error',
        description: 'Failed to start run. Please try again.',
        variant: 'destructive',
      });
    }
  };

  const handleCancelRun = async (runId: string) => {
    try {
      await cancelRun.mutateAsync({ productId, runId });
      toast({
        title: 'Run Cancelled',
        description: 'The simulation run has been cancelled.',
        variant: 'warning',
      });
    } catch {
      toast({
        title: 'Error',
        description: 'Failed to cancel run. Please try again.',
        variant: 'destructive',
      });
    }
  };

  const handleDelete = async () => {
    if (!confirm('Delete this product?')) return;
    setIsDeleting(true);
    try {
      await deleteProduct.mutateAsync(productId);
      toast({
        title: 'Product Deleted',
        description: 'The product has been deleted successfully.',
      });
      router.push('/dashboard/products');
    } catch {
      toast({
        title: 'Error',
        description: 'Failed to delete product. Please try again.',
        variant: 'destructive',
      });
      setIsDeleting(false);
    }
  };

  const latestRun = runs?.[0];
  const hasActiveRun = latestRun?.status === 'running' || latestRun?.status === 'pending';

  return (
    <div className="min-h-screen bg-black p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-3">
            <Link href="/dashboard/products" className="p-1.5 hover:bg-white/10 transition-colors mt-1">
              <ArrowLeft className="w-4 h-4 text-white/60" />
            </Link>
            <div>
              <h1 className="text-xl font-mono font-bold text-white mb-1">{product.name}</h1>
              <div className="flex items-center gap-2 text-xs font-mono text-white/40">
                <span className="px-1.5 py-0.5 bg-white/10 uppercase">{product.product_type}</span>
                {product.sub_type && (
                  <>
                    <ChevronRight className="w-3 h-3" />
                    <span className="px-1.5 py-0.5 bg-white/10 uppercase">{product.sub_type.replace('_', ' ')}</span>
                  </>
                )}
              </div>
              {product.description && (
                <p className="text-sm font-mono text-white/50 mt-2 max-w-xl">{product.description}</p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <StatusBadge status={product.status} />
            {!hasActiveRun && (
              <Button
                onClick={handleCreateRun}
                disabled={createRun.isPending}
                size="sm"
              >
                {createRun.isPending ? (
                  <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                ) : (
                  <Play className="w-3 h-3 mr-1" />
                )}
                {runs && runs.length > 0 ? 'New Run' : 'Start'}
              </Button>
            )}
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mt-6">
          {['overview', 'runs', 'results'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab as typeof activeTab)}
              className={cn(
                'px-3 py-1.5 text-xs font-mono transition-colors',
                activeTab === tab
                  ? 'bg-white/10 text-white border-b-2 border-white'
                  : 'text-white/40 hover:text-white/60'
              )}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
              {tab === 'runs' && runs && (
                <span className="ml-1 px-1 bg-white/10 text-[10px]">{runs.length}</span>
              )}
              {tab === 'results' && results && (
                <span className="ml-1 px-1 bg-white/10 text-[10px]">{results.length}</span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div>
        {activeTab === 'overview' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* Main Content */}
            <div className="lg:col-span-2 space-y-4">
              {/* Stats */}
              <div className="grid grid-cols-3 gap-3">
                <div className="bg-white/5 border border-white/10 p-4">
                  <div className="flex items-center gap-1 text-[10px] font-mono text-white/40 uppercase mb-1">
                    <Users className="w-3 h-3" />
                    Agents
                  </div>
                  <p className="text-2xl font-mono font-bold text-white">{product.persona_count.toLocaleString()}</p>
                </div>
                <div className="bg-white/5 border border-white/10 p-4">
                  <div className="flex items-center gap-1 text-[10px] font-mono text-white/40 uppercase mb-1">
                    <Target className="w-3 h-3" />
                    Confidence
                  </div>
                  <p className="text-2xl font-mono font-bold text-white">{(product.confidence_target * 100).toFixed(0)}%</p>
                </div>
                <div className="bg-white/5 border border-white/10 p-4">
                  <div className="flex items-center gap-1 text-[10px] font-mono text-white/40 uppercase mb-1">
                    <RotateCcw className="w-3 h-3" />
                    Runs
                  </div>
                  <p className="text-2xl font-mono font-bold text-white">{runs?.length || 0}</p>
                </div>
              </div>

              {/* Target Market */}
              <div className="bg-white/5 border border-white/10 p-4">
                <h3 className="text-xs font-mono font-bold text-white mb-3 flex items-center gap-2">
                  <Globe className="w-3 h-3 text-white/40" />
                  TARGET MARKET
                </h3>
                <div className="space-y-3">
                  {product.target_market?.regions && product.target_market.regions.length > 0 && (
                    <div>
                      <p className="text-[10px] font-mono text-white/40 uppercase mb-1">Regions</p>
                      <div className="flex flex-wrap gap-1">
                        {product.target_market.regions.map((region: string) => (
                          <span key={region} className="px-1.5 py-0.5 bg-white/10 text-xs font-mono text-white/60 capitalize">
                            {region.replace('_', ' ')}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {product.target_market?.countries && product.target_market.countries.length > 0 && (
                    <div>
                      <p className="text-[10px] font-mono text-white/40 uppercase mb-1">Countries</p>
                      <div className="flex flex-wrap gap-1">
                        {product.target_market.countries.map((country: string) => (
                          <span key={country} className="px-1.5 py-0.5 bg-white/10 text-xs font-mono text-white/60">
                            {country}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {product.target_market?.demographics && (
                    <div>
                      <p className="text-[10px] font-mono text-white/40 uppercase mb-1">Demographics</p>
                      <div className="text-xs font-mono text-white/60">
                        {(product.target_market.demographics as any)?.age_groups && (
                          <span>Age: {(product.target_market.demographics as any).age_groups.join(', ')}</span>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Latest Run Progress */}
              {latestRun && latestRun.status === 'running' && (
                <div className="bg-white/5 border border-white/10 p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-xs font-mono font-bold text-white">CURRENT RUN</h3>
                    <Button
                      variant="outline"
                      className="font-mono text-[10px] h-6 border-white/20 text-white/60 hover:bg-white/5"
                      onClick={() => handleCancelRun(latestRun.id)}
                      disabled={cancelRun.isPending}
                    >
                      <Pause className="w-2.5 h-2.5 mr-1" />
                      Cancel
                    </Button>
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-xs font-mono">
                      <span className="text-white/40">Progress</span>
                      <span className="text-white">{latestRun.progress}%</span>
                    </div>
                    <div className="w-full bg-white/10 h-1">
                      <div className="bg-white h-1 transition-all" style={{ width: `${latestRun.progress}%` }} />
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Sidebar */}
            <div className="space-y-4">
              {/* Details */}
              <div className="bg-white/5 border border-white/10 p-4">
                <h3 className="text-xs font-mono font-bold text-white mb-3">DETAILS</h3>
                <div className="space-y-2 text-xs font-mono">
                  <div className="flex justify-between">
                    <span className="text-white/40">Created</span>
                    <span className="text-white/60">{new Date(product.created_at).toLocaleDateString()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-white/40">Last Updated</span>
                    <span className="text-white/60">{new Date(product.updated_at).toLocaleDateString()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-white/40">Persona Source</span>
                    <span className="text-white/60 capitalize">{product.persona_source.replace('_', ' ')}</span>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="bg-white/5 border border-white/10 p-4">
                <h3 className="text-xs font-mono font-bold text-white mb-3">ACTIONS</h3>
                <div className="space-y-2">
                  <Link href={`/dashboard/products/${productId}/focus-group`} className="block">
                    <Button
                      variant="outline"
                      className="w-full justify-start font-mono text-[10px] h-8 border-blue-500/30 text-blue-400 hover:bg-blue-500/10"
                    >
                      <Users className="w-3 h-3 mr-2" />
                      Virtual Focus Group
                      <span className="ml-auto px-1 bg-blue-500/20 text-[8px]">NEW</span>
                    </Button>
                  </Link>
                  <Link href={`/dashboard/products/${productId}/edit`} className="block">
                    <Button
                      variant="outline"
                      className="w-full justify-start font-mono text-[10px] h-8 border-white/20 text-white/60 hover:bg-white/5"
                      disabled={hasActiveRun}
                    >
                      <Settings className="w-3 h-3 mr-2" />
                      Edit Configuration
                    </Button>
                  </Link>
                  <Button
                    variant="outline"
                    className="w-full justify-start font-mono text-[10px] h-8 border-red-500/30 text-red-400 hover:bg-red-500/10"
                    onClick={handleDelete}
                    disabled={isDeleting || hasActiveRun}
                  >
                    {isDeleting ? (
                      <Loader2 className="w-3 h-3 mr-2 animate-spin" />
                    ) : (
                      <Trash2 className="w-3 h-3 mr-2" />
                    )}
                    Delete Product
                  </Button>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'runs' && (
          <div className="bg-white/5 border border-white/10">
            {runsLoading ? (
              <div className="p-8 flex items-center justify-center">
                <Loader2 className="w-4 h-4 animate-spin text-white/40" />
              </div>
            ) : runs && runs.length > 0 ? (
              <div className="divide-y divide-white/5">
                {runs.map((run) => (
                  <div key={run.id} className="p-4 hover:bg-white/5 transition-colors">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <RunStatusIcon status={run.status} />
                        <div>
                          <p className="text-sm font-mono text-white">{run.name || `Run #${run.run_number}`}</p>
                          <p className="text-[10px] font-mono text-white/40">
                            {run.agents_completed} / {run.agents_total} agents
                            {run.status === 'running' && ` (${run.progress}%)`}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="text-right text-[10px] font-mono text-white/30">
                          {run.started_at ? new Date(run.started_at).toLocaleString() : new Date(run.created_at).toLocaleString()}
                        </div>
                        {run.status === 'pending' && (
                          <Button
                            size="icon-sm"
                            onClick={() => handleStartRun(run.id)}
                            disabled={startRun.isPending}
                          >
                            <Play className="w-2.5 h-2.5 mr-1" />
                            Start
                          </Button>
                        )}
                        {run.status === 'running' && (
                          <Button
                            variant="outline"
                            className="font-mono text-[10px] h-6 border-white/20 text-white/60 hover:bg-white/5"
                            onClick={() => handleCancelRun(run.id)}
                            disabled={cancelRun.isPending}
                          >
                            <Pause className="w-2.5 h-2.5 mr-1" />
                            Cancel
                          </Button>
                        )}
                      </div>
                    </div>
                    {run.status === 'running' && (
                      <div className="mt-2">
                        <div className="w-full bg-white/10 h-1">
                          <div className="bg-white h-1 transition-all" style={{ width: `${run.progress}%` }} />
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-8 text-center">
                <div className="w-10 h-10 bg-white/5 flex items-center justify-center mx-auto mb-3">
                  <Play className="w-4 h-4 text-white/30" />
                </div>
                <p className="text-sm font-mono text-white/60 mb-1">No runs yet</p>
                <p className="text-[10px] font-mono text-white/30 mb-4">Start your first study run</p>
                <Button onClick={handleCreateRun} disabled={createRun.isPending} size="sm">
                  <Play className="w-3 h-3 mr-2" />
                  START STUDY
                </Button>
              </div>
            )}
          </div>
        )}

        {activeTab === 'results' && (
          <div className="bg-white/5 border border-white/10">
            {resultsLoading ? (
              <div className="p-8 flex items-center justify-center">
                <Loader2 className="w-4 h-4 animate-spin text-white/40" />
              </div>
            ) : results && results.length > 0 ? (
              <div className="divide-y divide-white/5">
                {results.map((result) => (
                  <Link
                    key={result.id}
                    href={`/dashboard/products/${productId}/results/${result.id}`}
                    className="block p-4 hover:bg-white/5 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-mono text-white capitalize">{result.result_type.replace('_', ' ')}</p>
                        <p className="text-[10px] font-mono text-white/40">
                          Confidence: {(result.confidence_score * 100).toFixed(1)}%
                        </p>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-[10px] font-mono text-white/30">
                          {new Date(result.created_at).toLocaleDateString()}
                        </span>
                        <ChevronRight className="w-3 h-3 text-white/30" />
                      </div>
                    </div>
                    {result.executive_summary && (
                      <p className="text-xs font-mono text-white/50 mt-2 line-clamp-2">
                        {result.executive_summary}
                      </p>
                    )}
                  </Link>
                ))}
              </div>
            ) : (
              <div className="p-8 text-center">
                <div className="w-10 h-10 bg-white/5 flex items-center justify-center mx-auto mb-3">
                  <BarChart3 className="w-4 h-4 text-white/30" />
                </div>
                <p className="text-sm font-mono text-white/60 mb-1">No results yet</p>
                <p className="text-[10px] font-mono text-white/30">Results appear after running a study</p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="mt-8 pt-4 border-t border-white/5">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-1">
            <Terminal className="w-3 h-3" />
            <span>PRODUCT DETAIL</span>
          </div>
          <span>AGENTVERSE v1.0.0</span>
        </div>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { className: string; label: string }> = {
    draft: { className: 'bg-white/10 text-white/50', label: 'DRAFT' },
    configured: { className: 'bg-yellow-500/20 text-yellow-400', label: 'CONFIGURED' },
    running: { className: 'bg-blue-500/20 text-blue-400 animate-pulse', label: 'RUNNING' },
    completed: { className: 'bg-green-500/20 text-green-400', label: 'DONE' },
    failed: { className: 'bg-red-500/20 text-red-400', label: 'FAILED' },
  };

  const { className, label } = config[status] || config.draft;

  return (
    <span className={cn('px-1.5 py-0.5 text-[10px] font-mono uppercase', className)}>
      {label}
    </span>
  );
}

function RunStatusIcon({ status }: { status: string }) {
  switch (status) {
    case 'completed':
      return <div className="w-6 h-6 bg-green-500/20 flex items-center justify-center"><CheckCircle className="w-3 h-3 text-green-400" /></div>;
    case 'running':
      return <div className="w-6 h-6 bg-blue-500/20 flex items-center justify-center"><Loader2 className="w-3 h-3 text-blue-400 animate-spin" /></div>;
    case 'pending':
      return <div className="w-6 h-6 bg-yellow-500/20 flex items-center justify-center"><Clock className="w-3 h-3 text-yellow-400" /></div>;
    case 'failed':
    case 'cancelled':
      return <div className="w-6 h-6 bg-red-500/20 flex items-center justify-center"><XCircle className="w-3 h-3 text-red-400" /></div>;
    default:
      return <div className="w-6 h-6 bg-white/10 flex items-center justify-center"><Play className="w-3 h-3 text-white/60" /></div>;
  }
}
