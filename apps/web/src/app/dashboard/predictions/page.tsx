'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  Plus,
  TrendingUp,
  MoreVertical,
  Loader2,
  Search,
  XCircle,
  CheckCircle,
  Clock,
  Activity,
  Users,
  Eye,
  Terminal,
  Target,
  Brain,
  Gauge,
  BarChart2,
} from 'lucide-react';
import { usePredictions, useCancelPrediction } from '@/hooks/useApi';
import { PredictionResponse, ScenarioType } from '@/lib/api';
import { cn } from '@/lib/utils';

const statusColors: Record<string, { className: string; icon: React.ReactNode; label: string }> = {
  pending: {
    className: 'bg-yellow-500/20 text-yellow-400',
    icon: <Clock className="w-2.5 h-2.5" />,
    label: 'PENDING',
  },
  running: {
    className: 'bg-blue-500/20 text-blue-400 animate-pulse',
    icon: <Activity className="w-2.5 h-2.5" />,
    label: 'RUNNING',
  },
  completed: {
    className: 'bg-green-500/20 text-green-400',
    icon: <CheckCircle className="w-2.5 h-2.5" />,
    label: 'DONE',
  },
  failed: {
    className: 'bg-red-500/20 text-red-400',
    icon: <XCircle className="w-2.5 h-2.5" />,
    label: 'FAILED',
  },
  cancelled: {
    className: 'bg-white/10 text-white/50',
    icon: <XCircle className="w-2.5 h-2.5" />,
    label: 'CANCELLED',
  },
};

const scenarioColors: Record<ScenarioType, { className: string; label: string }> = {
  election: {
    className: 'bg-purple-500/20 text-purple-400',
    label: 'ELECTION',
  },
  consumer: {
    className: 'bg-cyan-500/20 text-cyan-400',
    label: 'CONSUMER',
  },
  market: {
    className: 'bg-orange-500/20 text-orange-400',
    label: 'MARKET',
  },
  social: {
    className: 'bg-pink-500/20 text-pink-400',
    label: 'SOCIAL',
  },
};

export default function PredictionsPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [scenarioFilter, setScenarioFilter] = useState<string>('');

  const { data: predictionsData, isLoading, error, refetch } = usePredictions({
    status: statusFilter as 'pending' | 'running' | 'completed' | 'failed' | 'cancelled' | undefined,
    scenario_type: scenarioFilter || undefined,
  });

  const predictions = predictionsData?.predictions || [];
  const totalCount = predictionsData?.total || 0;

  const filteredPredictions = predictions.filter(pred =>
    !searchQuery ||
    pred.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    pred.description?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="min-h-screen bg-black p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <TrendingUp className="w-4 h-4 text-white/60" />
            <span className="text-xs font-mono text-white/40 uppercase tracking-wider">Predictive AI Module</span>
          </div>
          <h1 className="text-xl font-mono font-bold text-white">Predictions</h1>
          <p className="text-sm font-mono text-white/50 mt-1">
            Run future behavior predictions with 80%+ accuracy
          </p>
        </div>
        <Link href="/dashboard/predictions/new">
          <Button size="sm">
            <Plus className="w-3 h-3 mr-2" />
            NEW PREDICTION
          </Button>
        </Link>
      </div>

      {/* Stats Bar */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex items-center gap-2 mb-2">
            <Target className="w-4 h-4 text-cyan-400" />
            <span className="text-[10px] font-mono text-white/40 uppercase">Total</span>
          </div>
          <div className="text-2xl font-mono font-bold text-white">{totalCount}</div>
        </div>
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex items-center gap-2 mb-2">
            <Activity className="w-4 h-4 text-blue-400" />
            <span className="text-[10px] font-mono text-white/40 uppercase">Running</span>
          </div>
          <div className="text-2xl font-mono font-bold text-white">
            {predictions.filter(p => p.status === 'running').length}
          </div>
        </div>
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle className="w-4 h-4 text-green-400" />
            <span className="text-[10px] font-mono text-white/40 uppercase">Completed</span>
          </div>
          <div className="text-2xl font-mono font-bold text-white">
            {predictions.filter(p => p.status === 'completed').length}
          </div>
        </div>
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex items-center gap-2 mb-2">
            <Gauge className="w-4 h-4 text-purple-400" />
            <span className="text-[10px] font-mono text-white/40 uppercase">Avg Accuracy</span>
          </div>
          <div className="text-2xl font-mono font-bold text-white">---%</div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-6">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-white/30" />
          <input
            type="text"
            placeholder="Search predictions..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-7 pr-3 py-1.5 bg-white/5 border border-white/10 text-xs font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-white/30"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-1.5 bg-white/5 border border-white/10 text-xs font-mono text-white appearance-none focus:outline-none focus:border-white/30"
        >
          <option value="">All Status</option>
          <option value="pending">Pending</option>
          <option value="running">Running</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
          <option value="cancelled">Cancelled</option>
        </select>
        <select
          value={scenarioFilter}
          onChange={(e) => setScenarioFilter(e.target.value)}
          className="px-3 py-1.5 bg-white/5 border border-white/10 text-xs font-mono text-white appearance-none focus:outline-none focus:border-white/30"
        >
          <option value="">All Scenarios</option>
          <option value="election">Election</option>
          <option value="consumer">Consumer</option>
          <option value="market">Market</option>
          <option value="social">Social</option>
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
          <p className="text-sm font-mono text-red-400">Failed to load predictions</p>
          <Button
            variant="outline"
            onClick={() => refetch()}
            className="mt-2 font-mono text-xs border-white/20 text-white/60 hover:bg-white/5"
          >
            RETRY
          </Button>
        </div>
      )}

      {/* Predictions List */}
      {!isLoading && !error && (
        <>
          {filteredPredictions.length === 0 ? (
            <div className="bg-white/5 border border-white/10">
              <div className="p-12 text-center">
                <div className="w-12 h-12 bg-white/5 flex items-center justify-center mx-auto mb-4">
                  <Brain className="w-5 h-5 text-white/30" />
                </div>
                <p className="text-sm font-mono text-white/60 mb-1">No predictions</p>
                <p className="text-xs font-mono text-white/30 mb-4">
                  Create your first prediction with behavioral economics
                </p>
                <Link href="/dashboard/predictions/new">
                  <Button size="sm">
                    NEW PREDICTION
                  </Button>
                </Link>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredPredictions.map((prediction) => (
                <PredictionCard
                  key={prediction.id}
                  prediction={prediction}
                  onUpdate={() => refetch()}
                />
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
              <span>PREDICTIVE AI MODULE</span>
            </div>
          </div>
          <span>AGENTVERSE v1.0.0</span>
        </div>
      </div>
    </div>
  );
}

function PredictionCard({ prediction, onUpdate }: { prediction: PredictionResponse; onUpdate: () => void }) {
  const [showMenu, setShowMenu] = useState(false);
  const cancelPrediction = useCancelPrediction();

  const status = statusColors[prediction.status] || statusColors.pending;
  const scenario = scenarioColors[prediction.scenario_type as ScenarioType] || scenarioColors.election;
  const progress = prediction.progress || 0;
  const agentCount = prediction.config?.agent_config?.count || 0;
  const monteCarloRuns = prediction.config?.monte_carlo_runs || 1;

  const handleCancel = async () => {
    if (confirm('Cancel this prediction?')) {
      try {
        await cancelPrediction.mutateAsync(prediction.id);
        onUpdate();
      } catch {
        // Cancel failed - mutation error is handled by react-query
      }
    }
    setShowMenu(false);
  };

  return (
    <div className="bg-white/5 border border-white/10 hover:border-white/20 transition-colors">
      {/* Header */}
      <div className="p-4 border-b border-white/5">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className={cn('px-1.5 py-0.5 text-[10px] font-mono uppercase', scenario.className)}>
              {scenario.label}
            </span>
            <span className={cn('inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-mono uppercase', status.className)}>
              {status.icon}
              {status.label}
            </span>
          </div>
          <div className="relative">
            <button
              onClick={() => setShowMenu(!showMenu)}
              className="p-1.5 hover:bg-white/10 transition-colors"
            >
              <MoreVertical className="w-3 h-3 text-white/40" />
            </button>
            {showMenu && (
              <>
                <div
                  className="fixed inset-0 z-10"
                  onClick={() => setShowMenu(false)}
                />
                <div className="absolute right-0 mt-1 w-32 bg-black border border-white/20 py-1 z-20">
                  <Link
                    href={`/dashboard/predictions/${prediction.id}`}
                    className="flex items-center gap-2 px-3 py-1.5 text-xs font-mono text-white/60 hover:bg-white/10"
                    onClick={() => setShowMenu(false)}
                  >
                    <Eye className="w-3 h-3" />
                    View Details
                  </Link>
                  {prediction.status === 'completed' && (
                    <Link
                      href={`/dashboard/predictions/${prediction.id}`}
                      className="flex items-center gap-2 px-3 py-1.5 text-xs font-mono text-white/60 hover:bg-white/10"
                      onClick={() => setShowMenu(false)}
                    >
                      <BarChart2 className="w-3 h-3" />
                      View Results
                    </Link>
                  )}
                  {(prediction.status === 'running' || prediction.status === 'pending') && (
                    <button
                      onClick={handleCancel}
                      disabled={cancelPrediction.isPending}
                      className="flex items-center gap-2 w-full px-3 py-1.5 text-xs font-mono text-red-400 hover:bg-white/10 disabled:opacity-50"
                    >
                      <XCircle className="w-3 h-3" />
                      Cancel
                    </button>
                  )}
                </div>
              </>
            )}
          </div>
        </div>
        <h3 className="text-sm font-mono font-bold text-white truncate mb-1">{prediction.name}</h3>
        {prediction.description && (
          <p className="text-xs font-mono text-white/40 line-clamp-2">{prediction.description}</p>
        )}
      </div>

      {/* Stats */}
      <div className="p-4 grid grid-cols-3 gap-3">
        <div>
          <div className="text-[10px] font-mono text-white/30 uppercase mb-1">Agents</div>
          <div className="flex items-center gap-1 text-sm font-mono text-white">
            <Users className="w-3 h-3 text-white/40" />
            {agentCount.toLocaleString()}
          </div>
        </div>
        <div>
          <div className="text-[10px] font-mono text-white/30 uppercase mb-1">Monte Carlo</div>
          <div className="text-sm font-mono text-white">{monteCarloRuns} runs</div>
        </div>
        <div>
          <div className="text-[10px] font-mono text-white/30 uppercase mb-1">Categories</div>
          <div className="text-sm font-mono text-white">
            {prediction.config?.categories?.length || 0}
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      {(prediction.status === 'running' || prediction.status === 'pending') && (
        <div className="px-4 pb-4">
          <div className="flex items-center gap-2">
            <div className="flex-1 bg-white/10 h-1.5">
              <div
                className={cn(
                  'h-1.5 transition-all',
                  progress === 100 ? 'bg-green-500' : 'bg-cyan-500'
                )}
                style={{ width: `${progress}%` }}
              />
            </div>
            <span className="text-[10px] font-mono text-white/40 w-8">{progress}%</span>
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="px-4 py-3 bg-white/[0.02] border-t border-white/5">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <span>{new Date(prediction.created_at).toLocaleDateString()}</span>
          {prediction.config?.use_calibration && (
            <span className="flex items-center gap-1 text-cyan-400">
              <Target className="w-2.5 h-2.5" />
              CALIBRATED
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
