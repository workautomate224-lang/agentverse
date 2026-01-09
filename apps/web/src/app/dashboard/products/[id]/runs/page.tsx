'use client';

import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  ArrowLeft,
  Play,
  Pause,
  Clock,
  CheckCircle,
  XCircle,
  Loader2,
  Terminal,
  BarChart3,
  Users,
  Coins,
  type LucideIcon,
} from 'lucide-react';
import { useProduct, useProductRuns, useStartProductRun, useCancelProductRun, useCreateProductRun } from '@/hooks/useApi';
import { cn } from '@/lib/utils';

export default function ProductRunsPage() {
  const params = useParams();
  const productId = params.id as string;

  const { data: product, isLoading: productLoading } = useProduct(productId);
  const { data: runs, isLoading: runsLoading } = useProductRuns(productId);
  const createRun = useCreateProductRun();
  const startRun = useStartProductRun();
  const cancelRun = useCancelProductRun();

  if (productLoading || runsLoading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-white/40" />
      </div>
    );
  }

  const handleCreateRun = async () => {
    try {
      await createRun.mutateAsync({ productId });
    } catch {
      // Create failed - mutation error is handled by react-query
    }
  };

  const handleStartRun = async (runId: string) => {
    try {
      await startRun.mutateAsync({ productId, runId });
    } catch {
      // Start failed - mutation error is handled by react-query
    }
  };

  const handleCancelRun = async (runId: string) => {
    try {
      await cancelRun.mutateAsync({ productId, runId });
    } catch {
      // Cancel failed - mutation error is handled by react-query
    }
  };

  const statusConfig: Record<string, { icon: LucideIcon; className: string; label: string }> = {
    pending: { icon: Clock, className: 'bg-white/10 text-white/50', label: 'PENDING' },
    running: { icon: Play, className: 'bg-yellow-500/20 text-yellow-400 animate-pulse', label: 'RUNNING' },
    completed: { icon: CheckCircle, className: 'bg-green-500/20 text-green-400', label: 'COMPLETED' },
    failed: { icon: XCircle, className: 'bg-red-500/20 text-red-400', label: 'FAILED' },
    cancelled: { icon: Pause, className: 'bg-white/10 text-white/40', label: 'CANCELLED' },
  };

  return (
    <div className="min-h-screen bg-black p-6">
      {/* Header */}
      <div className="mb-8">
        <Link href={`/dashboard/products/${productId}`}>
          <Button variant="ghost" size="sm" className="text-white/60 hover:text-white hover:bg-white/5 font-mono text-xs mb-4">
            <ArrowLeft className="w-3 h-3 mr-2" />
            BACK TO PRODUCT
          </Button>
        </Link>

        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <BarChart3 className="w-4 h-4 text-white/60" />
              <span className="text-xs font-mono text-white/40 uppercase tracking-wider">Product Runs</span>
            </div>
            <h1 className="text-xl font-mono font-bold text-white">{product?.name || 'Product'}</h1>
            <p className="text-sm font-mono text-white/50 mt-1">View and manage simulation runs</p>
          </div>
          <Button
            onClick={handleCreateRun}
            disabled={createRun.isPending}
            size="sm"
          >
            {createRun.isPending ? (
              <Loader2 className="w-3 h-3 mr-2 animate-spin" />
            ) : (
              <Play className="w-3 h-3 mr-2" />
            )}
            NEW RUN
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-8">
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-white/10 flex items-center justify-center">
              <BarChart3 className="w-5 h-5 text-white/60" />
            </div>
            <div>
              <p className="text-[10px] font-mono text-white/40 uppercase">Total Runs</p>
              <p className="text-xl font-mono font-bold text-white">{runs?.length || 0}</p>
            </div>
          </div>
        </div>
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-white/10 flex items-center justify-center">
              <CheckCircle className="w-5 h-5 text-white/60" />
            </div>
            <div>
              <p className="text-[10px] font-mono text-white/40 uppercase">Completed</p>
              <p className="text-xl font-mono font-bold text-white">
                {runs?.filter((r: any) => r.status === 'completed').length || 0}
              </p>
            </div>
          </div>
        </div>
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-white/10 flex items-center justify-center">
              <Users className="w-5 h-5 text-white/60" />
            </div>
            <div>
              <p className="text-[10px] font-mono text-white/40 uppercase">Total Agents</p>
              <p className="text-xl font-mono font-bold text-white">
                {runs?.reduce((acc: number, r: any) => acc + (r.agents_completed || 0), 0).toLocaleString() || '0'}
              </p>
            </div>
          </div>
        </div>
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-white/10 flex items-center justify-center">
              <Coins className="w-5 h-5 text-white/60" />
            </div>
            <div>
              <p className="text-[10px] font-mono text-white/40 uppercase">Total Cost</p>
              <p className="text-xl font-mono font-bold text-white">
                ${runs?.reduce((acc: number, r: any) => acc + (r.estimated_cost || 0), 0).toFixed(2) || '0.00'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Runs List */}
      <div className="bg-white/5 border border-white/10">
        <div className="p-4 border-b border-white/10">
          <h2 className="text-sm font-mono font-bold text-white uppercase">All Runs</h2>
        </div>

        {!runs || runs.length === 0 ? (
          <div className="p-12 text-center">
            <div className="w-12 h-12 bg-white/5 flex items-center justify-center mx-auto mb-4">
              <Play className="w-5 h-5 text-white/30" />
            </div>
            <h3 className="font-mono font-bold text-white text-sm mb-1">NO RUNS YET</h3>
            <p className="text-xs font-mono text-white/40 mb-4">Start your first simulation run</p>
            <Button
              onClick={handleCreateRun}
              
            >
              <Play className="w-3 h-3 mr-2" />
              CREATE RUN
            </Button>
          </div>
        ) : (
          <div className="divide-y divide-white/5">
            {runs.map((run: any) => {
              const status = statusConfig[run.status] || statusConfig.pending;
              const StatusIcon = status.icon;
              return (
                <div key={run.id} className="p-4 hover:bg-white/[0.02] transition-colors">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 bg-white/10 flex items-center justify-center">
                        <StatusIcon className="w-5 h-5 text-white/60" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="font-mono font-bold text-white text-sm">
                            {run.name || `Run #${run.run_number}`}
                          </h3>
                          <span className={cn('px-1.5 py-0.5 text-[10px] font-mono uppercase', status.className)}>
                            {status.label}
                          </span>
                        </div>
                        <div className="flex items-center gap-4 mt-1 text-[10px] font-mono text-white/40">
                          <span>{run.agents_completed || 0} / {run.agents_total || 0} agents</span>
                          <span>{run.tokens_used?.toLocaleString() || 0} tokens</span>
                          <span>${run.estimated_cost?.toFixed(2) || '0.00'}</span>
                          {run.started_at && (
                            <span>{new Date(run.started_at).toLocaleString()}</span>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {run.status === 'pending' && (
                        <Button
                          size="sm"
                          onClick={() => handleStartRun(run.id)}
                        >
                          <Play className="w-3 h-3 mr-1" />
                          START
                        </Button>
                      )}
                      {run.status === 'running' && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleCancelRun(run.id)}
                          className="border-red-500/30 text-red-400 hover:bg-red-500/10 font-mono text-[10px] h-7"
                        >
                          <Pause className="w-3 h-3 mr-1" />
                          CANCEL
                        </Button>
                      )}
                      {run.status === 'completed' && (
                        <Link href={`/dashboard/products/${productId}/results/${run.id}`}>
                          <Button
                            size="sm"
                            variant="outline"
                            className="border-white/20 text-white/60 hover:bg-white/5 font-mono text-[10px] h-7"
                          >
                            VIEW RESULTS
                          </Button>
                        </Link>
                      )}
                    </div>
                  </div>
                  {run.status === 'running' && run.progress > 0 && (
                    <div className="mt-3 ml-14">
                      <div className="h-1 bg-white/10 overflow-hidden">
                        <div
                          className="h-full bg-white/60 transition-all duration-300"
                          style={{ width: `${run.progress}%` }}
                        />
                      </div>
                      <p className="text-[10px] font-mono text-white/40 mt-1">{run.progress}% complete</p>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="mt-8 pt-4 border-t border-white/5">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-1">
            <Terminal className="w-3 h-3" />
            <span>PRODUCT RUNS MODULE</span>
          </div>
          <span>AGENTVERSE v1.0.0</span>
        </div>
      </div>
    </div>
  );
}
