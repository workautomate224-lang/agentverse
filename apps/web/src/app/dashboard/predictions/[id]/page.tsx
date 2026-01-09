'use client';

import { useState, use } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  ArrowLeft,
  TrendingUp,
  Loader2,
  XCircle,
  CheckCircle,
  Clock,
  Activity,
  Users,
  Terminal,
  Target,
  BarChart2,
  Settings,
  Download,
  RefreshCw,
  Wifi,
  WifiOff,
} from 'lucide-react';
import {
  usePrediction,
  usePredictionResults,
  usePredictionStream,
  useCancelPrediction,
} from '@/hooks/useApi';
import { PredictionStatus, ScenarioType } from '@/lib/api';
import { cn } from '@/lib/utils';

const statusColors: Record<string, { className: string; icon: React.ReactNode; label: string }> = {
  pending: {
    className: 'bg-yellow-500/20 text-yellow-400',
    icon: <Clock className="w-3 h-3" />,
    label: 'PENDING',
  },
  running: {
    className: 'bg-blue-500/20 text-blue-400 animate-pulse',
    icon: <Activity className="w-3 h-3" />,
    label: 'RUNNING',
  },
  completed: {
    className: 'bg-green-500/20 text-green-400',
    icon: <CheckCircle className="w-3 h-3" />,
    label: 'COMPLETED',
  },
  failed: {
    className: 'bg-red-500/20 text-red-400',
    icon: <XCircle className="w-3 h-3" />,
    label: 'FAILED',
  },
  cancelled: {
    className: 'bg-white/10 text-white/50',
    icon: <XCircle className="w-3 h-3" />,
    label: 'CANCELLED',
  },
};

const scenarioLabels: Record<ScenarioType, string> = {
  election: 'Election Prediction',
  consumer: 'Consumer Behavior',
  market: 'Market Prediction',
  social: 'Social Trends',
};

type TabType = 'overview' | 'results' | 'agents' | 'calibration';

export default function PredictionDetailPage({
  params,
}: {
  params: Promise<{ id: string }> | { id: string };
}) {
  // Handle both Promise and resolved params (varies by Next.js version/mode)
  const resolvedParams = params instanceof Promise ? use(params) : params;
  const predictionId = resolvedParams.id;

  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const { data: prediction, isLoading, error, refetch } = usePrediction(predictionId);
  const { data: results } = usePredictionResults(predictionId);
  const cancelPrediction = useCancelPrediction();

  // Stream for real-time progress
  const stream = usePredictionStream(
    predictionId,
    prediction?.status === 'running' || prediction?.status === 'pending'
  );

  const handleCancel = async () => {
    if (confirm('Cancel this prediction?')) {
      await cancelPrediction.mutateAsync(predictionId);
      refetch();
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-black p-6 flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-white/40" />
      </div>
    );
  }

  if (error || !prediction) {
    return (
      <div className="min-h-screen bg-black p-6">
        <div className="bg-red-500/10 border border-red-500/30 p-6">
          <p className="text-sm font-mono text-red-400 mb-4">Failed to load prediction</p>
          <Link href="/dashboard/predictions">
            <Button variant="outline" className="font-mono text-xs">
              <ArrowLeft className="w-3 h-3 mr-2" />
              Back to Predictions
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  const status = statusColors[prediction.status] || statusColors.pending;
  const isRunning = prediction.status === 'running' || prediction.status === 'pending';
  const isCompleted = prediction.status === 'completed';
  const progress = stream.progress || prediction.progress || 0;

  return (
    <div className="min-h-screen bg-black p-6">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <Link href="/dashboard/predictions" className="p-2 hover:bg-white/10 transition-colors">
          <ArrowLeft className="w-4 h-4 text-white/60" />
        </Link>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <TrendingUp className="w-4 h-4 text-white/60" />
            <span className="text-xs font-mono text-white/40 uppercase tracking-wider">
              {scenarioLabels[prediction.scenario_type as ScenarioType]}
            </span>
          </div>
          <h1 className="text-xl font-mono font-bold text-white">{prediction.name}</h1>
        </div>
        <div className="flex items-center gap-3">
          <span className={cn('inline-flex items-center gap-1.5 px-2 py-1 text-xs font-mono uppercase', status.className)}>
            {status.icon}
            {status.label}
          </span>
          {isRunning && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleCancel}
              disabled={cancelPrediction.isPending}
              className="font-mono text-xs border-red-500/30 text-red-400 hover:bg-red-500/10"
            >
              <XCircle className="w-3 h-3 mr-2" />
              CANCEL
            </Button>
          )}
          {isCompleted && (
            <Button variant="outline" size="sm" className="font-mono text-xs">
              <Download className="w-3 h-3 mr-2" />
              EXPORT
            </Button>
          )}
        </div>
      </div>

      {/* Progress Bar (if running) */}
      {isRunning && (
        <div className="bg-white/5 border border-white/10 p-4 mb-6">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 text-xs font-mono text-white/60">
                {stream.isConnected ? (
                  <Wifi className="w-3 h-3 text-green-400" />
                ) : (
                  <WifiOff className="w-3 h-3 text-yellow-400" />
                )}
                <span>{stream.isConnected ? 'Live' : 'Connecting...'}</span>
              </div>
              {stream.message && (
                <span className="text-xs font-mono text-white/40">{stream.message}</span>
              )}
            </div>
            <div className="text-sm font-mono text-cyan-400">{progress}%</div>
          </div>
          <div className="w-full bg-white/10 h-2">
            <div
              className="h-2 bg-cyan-500 transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className="flex items-center justify-between mt-2 text-[10px] font-mono text-white/40">
            <span>Step {stream.currentStep} of {stream.totalSteps}</span>
            <span>Run {stream.currentRun} of {stream.totalRuns}</span>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center gap-1 mb-6 border-b border-white/10">
        {(['overview', 'results', 'agents', 'calibration'] as TabType[]).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={cn(
              'px-4 py-2 text-xs font-mono uppercase tracking-wider transition-colors',
              activeTab === tab
                ? 'bg-white text-black'
                : 'text-white/50 hover:text-white hover:bg-white/5'
            )}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="mb-8">
        {activeTab === 'overview' && (
          <OverviewTab prediction={prediction} />
        )}
        {activeTab === 'results' && (
          <ResultsTab prediction={prediction} results={results} />
        )}
        {activeTab === 'agents' && (
          <AgentsTab prediction={prediction} />
        )}
        {activeTab === 'calibration' && (
          <CalibrationTab prediction={prediction} />
        )}
      </div>

      {/* Footer */}
      <div className="pt-4 border-t border-white/5">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1">
              <Terminal className="w-3 h-3" />
              <span>PREDICTION DETAIL</span>
            </div>
            <span>ID: {prediction.id.slice(0, 8)}...</span>
          </div>
          <span>Created: {new Date(prediction.created_at).toLocaleString()}</span>
        </div>
      </div>
    </div>
  );
}

// Overview Tab
function OverviewTab({ prediction }: { prediction: NonNullable<ReturnType<typeof usePrediction>['data']> }) {
  const config = prediction.config || {};
  const agentConfig = config.agent_config || {};
  const behavioralParams = agentConfig.behavioral_params || {};

  return (
    <div className="grid grid-cols-2 gap-6">
      {/* Config Summary */}
      <div className="bg-white/5 border border-white/10 p-6">
        <h3 className="text-sm font-mono font-bold text-white mb-4 flex items-center gap-2">
          <Settings className="w-4 h-4 text-white/40" />
          Configuration
        </h3>
        <div className="space-y-3">
          <div className="flex justify-between">
            <span className="text-xs font-mono text-white/40">Scenario Type</span>
            <span className="text-xs font-mono text-white uppercase">{prediction.scenario_type}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-xs font-mono text-white/40">Agent Count</span>
            <span className="text-xs font-mono text-white">{(agentConfig.count || 0).toLocaleString()}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-xs font-mono text-white/40">Simulation Steps</span>
            <span className="text-xs font-mono text-white">{config.num_steps || 0}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-xs font-mono text-white/40">Monte Carlo Runs</span>
            <span className="text-xs font-mono text-white">{config.monte_carlo_runs || 0}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-xs font-mono text-white/40">Network Type</span>
            <span className="text-xs font-mono text-white capitalize">{(config.social_network_type || 'small_world').replace('_', ' ')}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-xs font-mono text-white/40">Confidence Level</span>
            <span className="text-xs font-mono text-white">{((config.confidence_level || 0.95) * 100).toFixed(0)}%</span>
          </div>
        </div>
      </div>

      {/* Categories */}
      <div className="bg-white/5 border border-white/10 p-6">
        <h3 className="text-sm font-mono font-bold text-white mb-4 flex items-center gap-2">
          <BarChart2 className="w-4 h-4 text-white/40" />
          Categories
        </h3>
        <div className="space-y-2">
          {(config.categories || []).map((cat, i) => (
            <div key={i} className="flex items-center gap-3">
              <div
                className="w-4 h-4"
                style={{ backgroundColor: cat.color || '#FF6B6B' }}
              />
              <span className="text-xs font-mono text-white">{cat.name}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Behavioral Params */}
      <div className="bg-white/5 border border-white/10 p-6 col-span-2">
        <h3 className="text-sm font-mono font-bold text-white mb-4 flex items-center gap-2">
          <Target className="w-4 h-4 text-white/40" />
          Behavioral Economics Parameters
        </h3>
        <div className="grid grid-cols-3 gap-4">
          {[
            { key: 'loss_aversion', label: 'Loss Aversion (λ)' },
            { key: 'status_quo_bias', label: 'Status Quo Bias' },
            { key: 'bandwagon_effect', label: 'Bandwagon Effect' },
            { key: 'social_influence_weight', label: 'Social Influence' },
            { key: 'confirmation_bias', label: 'Confirmation Bias' },
          ].map(({ key, label }) => (
            <div key={key} className="p-3 bg-white/[0.02]">
              <div className="text-[10px] font-mono text-white/30 uppercase mb-1">{label}</div>
              <div className="text-sm font-mono text-cyan-400">
                {(behavioralParams[key as keyof typeof behavioralParams] ?? 0).toFixed(2)}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Timestamps */}
      <div className="bg-white/5 border border-white/10 p-6 col-span-2">
        <h3 className="text-sm font-mono font-bold text-white mb-4">Timeline</h3>
        <div className="flex items-center gap-8">
          <div>
            <div className="text-[10px] font-mono text-white/30 uppercase mb-1">Created</div>
            <div className="text-xs font-mono text-white">{new Date(prediction.created_at).toLocaleString()}</div>
          </div>
          {prediction.started_at && (
            <div>
              <div className="text-[10px] font-mono text-white/30 uppercase mb-1">Started</div>
              <div className="text-xs font-mono text-white">{new Date(prediction.started_at).toLocaleString()}</div>
            </div>
          )}
          {prediction.completed_at && (
            <div>
              <div className="text-[10px] font-mono text-white/30 uppercase mb-1">Completed</div>
              <div className="text-xs font-mono text-white">{new Date(prediction.completed_at).toLocaleString()}</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Results Tab
function ResultsTab({
  prediction,
  results,
}: {
  prediction: NonNullable<ReturnType<typeof usePrediction>['data']>;
  results: ReturnType<typeof usePredictionResults>['data'];
}) {
  if (prediction.status !== 'completed') {
    return (
      <div className="bg-white/5 border border-white/10 p-12 text-center">
        <BarChart2 className="w-8 h-8 text-white/20 mx-auto mb-4" />
        <p className="text-sm font-mono text-white/50 mb-2">Results not available yet</p>
        <p className="text-xs font-mono text-white/30">
          Results will appear here once the prediction completes
        </p>
      </div>
    );
  }

  if (!results) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-4 h-4 animate-spin text-white/40" />
      </div>
    );
  }

  const distributions = results.category_distributions || {};
  const confidenceIntervals = results.confidence_intervals || {};
  const categories = prediction.config?.categories || [];

  return (
    <div className="space-y-6">
      {/* Distribution Chart */}
      <div className="bg-white/5 border border-white/10 p-6">
        <h3 className="text-sm font-mono font-bold text-white mb-4">Predicted Distribution</h3>
        <div className="space-y-4">
          {categories.map((cat) => {
            const mean = distributions[cat.name] || 0;
            // Confidence intervals are stored as [lower, upper] tuples
            const ciTuple = confidenceIntervals[cat.name] || [0, 0];
            const ciLower = ciTuple[0];
            const ciUpper = ciTuple[1];
            const percentage = mean * 100;

            return (
              <div key={cat.name}>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3" style={{ backgroundColor: cat.color }} />
                    <span className="text-xs font-mono text-white">{cat.name}</span>
                  </div>
                  <div className="text-right">
                    <span className="text-sm font-mono font-bold text-white">{percentage.toFixed(1)}%</span>
                    <span className="text-[10px] font-mono text-white/40 ml-2">
                      ({(ciLower * 100).toFixed(1)}% - {(ciUpper * 100).toFixed(1)}%)
                    </span>
                  </div>
                </div>
                <div className="relative h-6 bg-white/5">
                  {/* Confidence interval background */}
                  <div
                    className="absolute h-full opacity-30"
                    style={{
                      left: `${ciLower * 100}%`,
                      width: `${(ciUpper - ciLower) * 100}%`,
                      backgroundColor: cat.color,
                    }}
                  />
                  {/* Mean bar */}
                  <div
                    className="absolute h-full"
                    style={{ width: `${percentage}%`, backgroundColor: cat.color }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="text-[10px] font-mono text-white/40 uppercase mb-1">Total Agents</div>
          <div className="text-xl font-mono font-bold text-white">
            {(results.agent_statistics?.total_agents || 0).toLocaleString()}
          </div>
        </div>
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="text-[10px] font-mono text-white/40 uppercase mb-1">Monte Carlo Runs</div>
          <div className="text-xl font-mono font-bold text-white">
            {results.monte_carlo_stats?.runs || 0}
          </div>
        </div>
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="text-[10px] font-mono text-white/40 uppercase mb-1">Brier Score</div>
          <div className="text-xl font-mono font-bold text-white">
            {results.accuracy_metrics?.brier_score?.toFixed(3) || 'N/A'}
          </div>
        </div>
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="text-[10px] font-mono text-white/40 uppercase mb-1">Coverage Prob</div>
          <div className="text-xl font-mono font-bold text-cyan-400">
            {results.accuracy_metrics?.coverage_probability
              ? `${(results.accuracy_metrics.coverage_probability * 100).toFixed(1)}%`
              : 'N/A'}
          </div>
        </div>
      </div>
    </div>
  );
}

// Agents Tab
function AgentsTab({ prediction }: { prediction: NonNullable<ReturnType<typeof usePrediction>['data']> }) {
  const agentConfig = prediction.config?.agent_config || {};
  const demographics = agentConfig.demographics || {};
  const ageDistribution = demographics.age_distribution || {};

  return (
    <div className="grid grid-cols-2 gap-6">
      <div className="bg-white/5 border border-white/10 p-6">
        <h3 className="text-sm font-mono font-bold text-white mb-4 flex items-center gap-2">
          <Users className="w-4 h-4 text-white/40" />
          Agent Population
        </h3>
        <div className="text-4xl font-mono font-bold text-white mb-2">
          {(agentConfig.count || 0).toLocaleString()}
        </div>
        <p className="text-xs font-mono text-white/40">Total simulated agents</p>
      </div>

      <div className="bg-white/5 border border-white/10 p-6">
        <h3 className="text-sm font-mono font-bold text-white mb-4">Age Distribution</h3>
        <div className="space-y-2">
          {Object.entries(ageDistribution).map(([key, value]) => (
            <div key={key} className="flex items-center gap-3">
              <span className="text-xs font-mono text-white/40 w-16">
                {key.replace('_', '-').replace('plus', '+')}
              </span>
              <div className="flex-1 h-4 bg-white/5">
                <div
                  className="h-full bg-cyan-500"
                  style={{ width: `${(value as number) * 100}%` }}
                />
              </div>
              <span className="text-xs font-mono text-white w-10 text-right">
                {((value as number) * 100).toFixed(0)}%
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// Calibration Tab
function CalibrationTab({ prediction }: { prediction: NonNullable<ReturnType<typeof usePrediction>['data']> }) {
  const isCalibrated = prediction.config?.use_calibration;

  if (!isCalibrated) {
    return (
      <div className="bg-white/5 border border-white/10 p-12 text-center">
        <Target className="w-8 h-8 text-white/20 mx-auto mb-4" />
        <p className="text-sm font-mono text-white/50 mb-2">Calibration not enabled</p>
        <p className="text-xs font-mono text-white/30">
          Enable calibration in settings to achieve &gt;80% prediction accuracy
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white/5 border border-white/10 p-6">
      <h3 className="text-sm font-mono font-bold text-white mb-4 flex items-center gap-2">
        <Target className="w-4 h-4 text-cyan-400" />
        Calibration Status
      </h3>
      <div className="flex items-center gap-2 mb-4">
        <CheckCircle className="w-4 h-4 text-green-400" />
        <span className="text-sm font-mono text-green-400">Calibration Enabled</span>
      </div>
      <p className="text-xs font-mono text-white/50">
        This prediction uses Bayesian optimization to calibrate behavioral parameters
        against ground truth data, targeting &gt;80% prediction accuracy.
      </p>
    </div>
  );
}
