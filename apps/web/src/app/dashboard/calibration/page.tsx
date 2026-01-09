'use client';

import { useState, useCallback } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  FlaskConical,
  Play,
  RotateCcw,
  Upload,
  CheckCircle,
  AlertTriangle,
  Clock,
  Database,
  Loader2,
  ChevronRight,
  ChevronDown,
  Activity,
  Terminal,
  History,
  Settings,
  Gauge,
  Shield,
  TrendingUp,
  TrendingDown,
  Zap,
  Target,
  BarChart3,
  Layers,
  Crosshair,
  Sliders,
  Save,
  X,
  Check,
  Eye,
  RefreshCw,
} from 'lucide-react';
import {
  useAccuracyStats,
  useBenchmarks,
  useValidations,
} from '@/hooks/useApi';
import type { Benchmark, ValidationRecord, HistoricalScenario, AutoTuneResult } from '@/lib/api';
import { cn } from '@/lib/utils';

// ============================================================================
// Mock Data for UI (will be replaced with actual API calls)
// ============================================================================

const MOCK_SCENARIOS: HistoricalScenario[] = [
  {
    scenario_id: 'hs-001',
    name: '2024 Q4 Market Shift',
    description: 'Consumer behavior during Q4 2024 market correction',
    dataset_id: 'ds-001',
    time_cutoff: '2024-09-30T00:00:00Z',
    ground_truth: {
      adoption_rate: 0.42,
      churn_rate: 0.12,
      sentiment_shift: -0.15,
    },
    metadata: {
      region: 'north_america',
      segment: 'retail',
      sample_size: 10000,
    },
    created_at: '2024-10-15T00:00:00Z',
  },
  {
    scenario_id: 'hs-002',
    name: '2024 Holiday Campaign',
    description: 'Consumer response to holiday marketing campaign',
    dataset_id: 'ds-002',
    time_cutoff: '2024-11-15T00:00:00Z',
    ground_truth: {
      engagement_rate: 0.68,
      conversion_rate: 0.24,
      brand_lift: 0.18,
    },
    metadata: {
      region: 'global',
      segment: 'e-commerce',
      sample_size: 25000,
    },
    created_at: '2024-12-01T00:00:00Z',
  },
  {
    scenario_id: 'hs-003',
    name: '2024 Product Launch',
    description: 'Consumer adoption of new product line',
    dataset_id: 'ds-003',
    time_cutoff: '2024-08-01T00:00:00Z',
    ground_truth: {
      trial_rate: 0.35,
      repeat_purchase: 0.52,
      recommendation_score: 7.8,
    },
    metadata: {
      region: 'europe',
      segment: 'consumer_goods',
      sample_size: 15000,
    },
    created_at: '2024-09-01T00:00:00Z',
  },
];

const MOCK_ERROR_METRICS = {
  distribution: {
    wasserstein: 0.12,
    js_divergence: 0.08,
    kl_divergence: 0.15,
    status: 'good' as const,
  },
  ranking: {
    spearman_rho: 0.85,
    kendall_tau: 0.78,
    ndcg: 0.92,
    status: 'good' as const,
  },
  turning_point: {
    precision: 0.72,
    recall: 0.68,
    f1_score: 0.70,
    lead_time: 2.5,
    status: 'warning' as const,
  },
};

const MOCK_TUNE_RESULT: AutoTuneResult | null = null;

// ============================================================================
// Types
// ============================================================================

type CalibrationTab = 'scenarios' | 'tuning' | 'metrics' | 'sensitivity';
type TuneStatus = 'idle' | 'running' | 'complete' | 'error';

interface ErrorMetrics {
  distribution: {
    wasserstein: number;
    js_divergence: number;
    kl_divergence: number;
    status: 'good' | 'warning' | 'error';
  };
  ranking: {
    spearman_rho: number;
    kendall_tau: number;
    ndcg: number;
    status: 'good' | 'warning' | 'error';
  };
  turning_point: {
    precision: number;
    recall: number;
    f1_score: number;
    lead_time: number;
    status: 'good' | 'warning' | 'error';
  };
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * Calibration Lab Page (Enhanced)
 * Per Interaction_design.md §5.16 + Phase 7 Backend Integration:
 * - Historical scenario runner with time cutoffs
 * - Error metrics suite (distribution, ranking, turning point)
 * - Bounded auto-tune with cross-validation
 * - Sensitivity scanner
 * - Leakage prevention indicators
 */
export default function CalibrationLabPage() {
  const [activeTab, setActiveTab] = useState<CalibrationTab>('scenarios');
  const [selectedScenario, setSelectedScenario] = useState<string | null>(null);
  const [isCalibrating, setIsCalibrating] = useState(false);
  const [tuneStatus, setTuneStatus] = useState<TuneStatus>('idle');
  const [tuneProgress, setTuneProgress] = useState(0);
  const [expandedMetric, setExpandedMetric] = useState<string | null>(null);

  // Parameters for bounded tuning
  const [parameters, setParameters] = useState({
    base_probability_scale: 1.0,
    confidence_threshold: 0.75,
    drift_sensitivity: 0.5,
    stability_window: 30,
  });

  // Use existing hooks
  const { data: stats, isLoading: statsLoading } = useAccuracyStats();
  const { data: benchmarks, isLoading: benchmarksLoading } = useBenchmarks();
  const { data: validations, isLoading: validationsLoading } = useValidations();

  const isLoading = statsLoading || benchmarksLoading || validationsLoading;

  // Mock data for now - will be replaced with API calls
  const scenarios = MOCK_SCENARIOS;
  const errorMetrics = MOCK_ERROR_METRICS;
  const tuneResult = MOCK_TUNE_RESULT;

  const handleRunCalibration = useCallback(async () => {
    if (!selectedScenario) return;
    setIsCalibrating(true);
    // Simulated API call - replace with actual calibration run
    await new Promise((resolve) => setTimeout(resolve, 3000));
    setIsCalibrating(false);
  }, [selectedScenario]);

  const handleAutoTune = useCallback(async () => {
    setTuneStatus('running');
    setTuneProgress(0);

    // Simulate auto-tune progress
    for (let i = 0; i <= 100; i += 10) {
      await new Promise((resolve) => setTimeout(resolve, 500));
      setTuneProgress(i);
    }

    setTuneStatus('complete');
  }, []);

  const handleRollbackTune = useCallback(() => {
    setParameters({
      base_probability_scale: 1.0,
      confidence_threshold: 0.75,
      drift_sensitivity: 0.5,
      stability_window: 30,
    });
    setTuneStatus('idle');
    setTuneProgress(0);
  }, []);

  const handlePublishProfile = useCallback(async () => {
    // API call to publish calibration profile
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }, []);

  const selectedScenarioData = scenarios.find((s) => s.scenario_id === selectedScenario);

  return (
    <div className="min-h-screen bg-black p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <FlaskConical className="w-4 h-4 text-cyan-400" />
            <span className="text-xs font-mono text-white/40 uppercase tracking-wider">
              Calibration Lab
            </span>
          </div>
          <h1 className="text-xl font-mono font-bold text-white">
            Historical Calibration & Tuning
          </h1>
          <p className="text-sm font-mono text-white/50 mt-1">
            Run historical scenarios, measure errors, auto-tune parameters
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            className="font-mono text-xs border-white/20 text-white/60 hover:bg-white/5 hover:text-white"
          >
            <Upload className="w-3 h-3 mr-2" />
            IMPORT SCENARIO
          </Button>
          <Button
            size="sm"
            onClick={handlePublishProfile}
            disabled={tuneStatus !== 'complete'}
            className="font-mono text-xs"
          >
            <Save className="w-3 h-3 mr-2" />
            PUBLISH PROFILE
          </Button>
        </div>
      </div>

      {/* Overview Stats */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-3 mb-6">
        <StatCard
          icon={Gauge}
          label="CALIBRATION"
          value={stats?.average_accuracy ? `${(stats.average_accuracy * 100).toFixed(0)}%` : '78%'}
          status={stats?.average_accuracy && stats.average_accuracy >= 0.8 ? 'good' : 'warning'}
        />
        <StatCard
          icon={Target}
          label="DISTRIBUTION"
          value={`${(errorMetrics.distribution.wasserstein * 100).toFixed(0)}%`}
          status={errorMetrics.distribution.status}
        />
        <StatCard
          icon={BarChart3}
          label="RANKING"
          value={`${(errorMetrics.ranking.spearman_rho * 100).toFixed(0)}%`}
          status={errorMetrics.ranking.status}
        />
        <StatCard
          icon={TrendingUp}
          label="TURNING PT"
          value={`${(errorMetrics.turning_point.f1_score * 100).toFixed(0)}%`}
          status={errorMetrics.turning_point.status}
        />
        <StatCard
          icon={Database}
          label="SCENARIOS"
          value={scenarios.length.toString()}
          status={undefined}
        />
      </div>

      {/* Leakage Warning */}
      <div className="bg-yellow-500/10 border border-yellow-500/30 p-3 mb-6">
        <div className="flex items-center gap-3">
          <AlertTriangle className="w-4 h-4 text-yellow-500" />
          <div className="flex-1">
            <span className="text-xs font-mono font-bold text-yellow-400">
              LEAKAGE PREVENTION ACTIVE
            </span>
            <span className="text-xs font-mono text-yellow-400/70 ml-2">
              All runs use strict time cutoffs. Future data is masked.
            </span>
          </div>
          <div className="text-right">
            <span className="text-xs font-mono text-yellow-400/60">Current Cutoff: </span>
            <span className="text-xs font-mono text-yellow-400 font-bold">
              {selectedScenarioData
                ? new Date(selectedScenarioData.time_cutoff).toLocaleDateString()
                : '---'}
            </span>
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-1 mb-6 border-b border-white/10">
        {(['scenarios', 'tuning', 'metrics', 'sensitivity'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={cn(
              'px-4 py-2 text-xs font-mono uppercase transition-colors border-b-2 -mb-[2px]',
              activeTab === tab
                ? 'text-cyan-400 border-cyan-400'
                : 'text-white/40 border-transparent hover:text-white/60'
            )}
          >
            {tab === 'scenarios' && <History className="w-3 h-3 inline mr-1.5" />}
            {tab === 'tuning' && <Sliders className="w-3 h-3 inline mr-1.5" />}
            {tab === 'metrics' && <Activity className="w-3 h-3 inline mr-1.5" />}
            {tab === 'sensitivity' && <Crosshair className="w-3 h-3 inline mr-1.5" />}
            {tab}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'scenarios' && (
        <ScenariosTab
          scenarios={scenarios}
          selectedScenario={selectedScenario}
          onSelectScenario={setSelectedScenario}
          isCalibrating={isCalibrating}
          onRunCalibration={handleRunCalibration}
        />
      )}

      {activeTab === 'tuning' && (
        <TuningTab
          parameters={parameters}
          onParameterChange={(key, value) =>
            setParameters((prev) => ({ ...prev, [key]: value }))
          }
          tuneStatus={tuneStatus}
          tuneProgress={tuneProgress}
          onAutoTune={handleAutoTune}
          onRollback={handleRollbackTune}
          tuneResult={tuneResult}
        />
      )}

      {activeTab === 'metrics' && (
        <MetricsTab
          metrics={errorMetrics}
          expandedMetric={expandedMetric}
          onToggleMetric={(id) =>
            setExpandedMetric(expandedMetric === id ? null : id)
          }
          validations={validations || []}
        />
      )}

      {activeTab === 'sensitivity' && <SensitivityTab />}

      {/* Footer */}
      <div className="mt-8 pt-4 border-t border-white/5">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1">
              <Terminal className="w-3 h-3" />
              <span>CALIBRATION LAB</span>
            </div>
            <span>Phase 7 • Reliability & Calibration</span>
          </div>
          <span>AGENTVERSE v1.0.0</span>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Tab Components
// ============================================================================

function ScenariosTab({
  scenarios,
  selectedScenario,
  onSelectScenario,
  isCalibrating,
  onRunCalibration,
}: {
  scenarios: HistoricalScenario[];
  selectedScenario: string | null;
  onSelectScenario: (id: string | null) => void;
  isCalibrating: boolean;
  onRunCalibration: () => void;
}) {
  const selected = scenarios.find((s) => s.scenario_id === selectedScenario);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Scenario List */}
      <div className="lg:col-span-1 bg-white/5 border border-white/10">
        <div className="p-4 border-b border-white/10 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <History className="w-3 h-3 text-white/40" />
            <h2 className="text-xs font-mono text-white/40 uppercase tracking-wider">
              Historical Scenarios
            </h2>
          </div>
          <span className="text-[10px] font-mono text-white/30">{scenarios.length} loaded</span>
        </div>
        <div className="divide-y divide-white/5 max-h-[500px] overflow-y-auto">
          {scenarios.map((scenario) => (
            <button
              key={scenario.scenario_id}
              onClick={() => onSelectScenario(
                selectedScenario === scenario.scenario_id ? null : scenario.scenario_id
              )}
              className={cn(
                'w-full p-4 text-left transition-colors',
                selectedScenario === scenario.scenario_id
                  ? 'bg-cyan-500/10 border-l-2 border-l-cyan-400'
                  : 'hover:bg-white/5'
              )}
            >
              <h4 className="text-sm font-mono text-white">{scenario.name}</h4>
              <p className="text-[10px] font-mono text-white/40 mt-1">{scenario.description}</p>
              <div className="flex items-center gap-2 mt-2">
                <span className="text-[10px] font-mono text-white/30 uppercase px-1.5 py-0.5 bg-white/10">
                  {scenario.metadata?.region}
                </span>
                <span className="text-[10px] font-mono text-white/30">
                  Cutoff: {new Date(scenario.time_cutoff).toLocaleDateString()}
                </span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Scenario Details */}
      <div className="lg:col-span-2 bg-white/5 border border-white/10">
        {selected ? (
          <>
            <div className="p-4 border-b border-white/10 flex items-center justify-between">
              <div>
                <h2 className="text-sm font-mono text-white font-bold">{selected.name}</h2>
                <p className="text-xs font-mono text-white/40 mt-1">{selected.description}</p>
              </div>
              <Button
                size="sm"
                onClick={onRunCalibration}
                disabled={isCalibrating}
                className="font-mono text-xs"
              >
                {isCalibrating ? (
                  <>
                    <Loader2 className="w-3 h-3 mr-2 animate-spin" />
                    RUNNING...
                  </>
                ) : (
                  <>
                    <Play className="w-3 h-3 mr-2" />
                    RUN SCENARIO
                  </>
                )}
              </Button>
            </div>
            <div className="p-4">
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <span className="text-[10px] font-mono text-white/40 uppercase">Time Cutoff</span>
                  <p className="text-sm font-mono text-white">
                    {new Date(selected.time_cutoff).toLocaleDateString()}
                  </p>
                </div>
                <div>
                  <span className="text-[10px] font-mono text-white/40 uppercase">Sample Size</span>
                  <p className="text-sm font-mono text-white">
                    {selected.metadata?.sample_size?.toLocaleString() || 'N/A'}
                  </p>
                </div>
                <div>
                  <span className="text-[10px] font-mono text-white/40 uppercase">Region</span>
                  <p className="text-sm font-mono text-white uppercase">
                    {selected.metadata?.region || 'N/A'}
                  </p>
                </div>
                <div>
                  <span className="text-[10px] font-mono text-white/40 uppercase">Segment</span>
                  <p className="text-sm font-mono text-white uppercase">
                    {selected.metadata?.segment || 'N/A'}
                  </p>
                </div>
              </div>

              <div className="border-t border-white/10 pt-4">
                <h3 className="text-xs font-mono text-white/40 uppercase mb-3">Ground Truth Values</h3>
                <div className="grid grid-cols-3 gap-3">
                  {Object.entries(selected.ground_truth).map(([key, value]) => (
                    <div key={key} className="bg-white/5 p-3">
                      <span className="text-[10px] font-mono text-white/40 uppercase">
                        {key.replace(/_/g, ' ')}
                      </span>
                      <p className="text-lg font-mono text-white font-bold">
                        {typeof value === 'number'
                          ? value < 1
                            ? `${(value * 100).toFixed(1)}%`
                            : value.toFixed(1)
                          : value}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <Database className="w-8 h-8 text-white/20 mx-auto mb-3" />
              <p className="text-xs font-mono text-white/40">Select a scenario to view details</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function TuningTab({
  parameters,
  onParameterChange,
  tuneStatus,
  tuneProgress,
  onAutoTune,
  onRollback,
  tuneResult,
}: {
  parameters: Record<string, number>;
  onParameterChange: (key: string, value: number) => void;
  tuneStatus: TuneStatus;
  tuneProgress: number;
  onAutoTune: () => void;
  onRollback: () => void;
  tuneResult: AutoTuneResult | null;
}) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Parameter Tuning */}
      <div className="bg-white/5 border border-white/10">
        <div className="p-4 border-b border-white/10 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sliders className="w-3 h-3 text-white/40" />
            <h2 className="text-xs font-mono text-white/40 uppercase tracking-wider">
              Parameter Tuning
            </h2>
          </div>
          <span className="text-[10px] font-mono text-cyan-400 uppercase">BOUNDED</span>
        </div>
        <div className="p-4 space-y-5">
          <ParameterSlider
            label="Base Probability Scale"
            value={parameters.base_probability_scale}
            min={0.8}
            max={1.2}
            step={0.01}
            onChange={(v) => onParameterChange('base_probability_scale', v)}
          />
          <ParameterSlider
            label="Confidence Threshold"
            value={parameters.confidence_threshold}
            min={0.5}
            max={0.95}
            step={0.01}
            onChange={(v) => onParameterChange('confidence_threshold', v)}
          />
          <ParameterSlider
            label="Drift Sensitivity"
            value={parameters.drift_sensitivity}
            min={0.1}
            max={1.0}
            step={0.1}
            onChange={(v) => onParameterChange('drift_sensitivity', v)}
          />
          <ParameterSlider
            label="Stability Window"
            value={parameters.stability_window}
            min={7}
            max={90}
            step={1}
            unit=" days"
            onChange={(v) => onParameterChange('stability_window', v)}
          />

          <div className="pt-4 border-t border-white/10 space-y-2">
            <Button
              variant="outline"
              size="sm"
              className="w-full font-mono text-xs border-white/20 text-white/60 hover:bg-white/5 hover:text-white"
              onClick={onAutoTune}
              disabled={tuneStatus === 'running'}
            >
              {tuneStatus === 'running' ? (
                <>
                  <Loader2 className="w-3 h-3 mr-2 animate-spin" />
                  AUTO-TUNING... {tuneProgress}%
                </>
              ) : (
                <>
                  <Zap className="w-3 h-3 mr-2" />
                  AUTO-TUNE (BOUNDED)
                </>
              )}
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="w-full font-mono text-xs border-white/20 text-white/60 hover:bg-white/5 hover:text-white"
              onClick={onRollback}
              disabled={tuneStatus === 'idle'}
            >
              <RotateCcw className="w-3 h-3 mr-2" />
              ROLLBACK TUNE
            </Button>
          </div>
        </div>
      </div>

      {/* Tune Progress & Results */}
      <div className="bg-white/5 border border-white/10">
        <div className="p-4 border-b border-white/10">
          <div className="flex items-center gap-2">
            <Activity className="w-3 h-3 text-white/40" />
            <h2 className="text-xs font-mono text-white/40 uppercase tracking-wider">
              Tuning Status
            </h2>
          </div>
        </div>
        <div className="p-4">
          {/* Progress Bar */}
          {tuneStatus === 'running' && (
            <div className="mb-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-mono text-white/60">Cross-Validation Progress</span>
                <span className="text-xs font-mono text-cyan-400">{tuneProgress}%</span>
              </div>
              <div className="w-full bg-white/10 h-2">
                <div
                  className="h-2 bg-cyan-400 transition-all duration-300"
                  style={{ width: `${tuneProgress}%` }}
                />
              </div>
              <div className="flex justify-between mt-2 text-[10px] font-mono text-white/30">
                <span>Fold 1/5</span>
                <span>Grid Search: 24/100 combinations</span>
              </div>
            </div>
          )}

          {tuneStatus === 'complete' && (
            <div className="space-y-4">
              <div className="bg-green-500/10 border border-green-500/30 p-3 flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-green-400" />
                <span className="text-xs font-mono text-green-400">
                  Auto-tune complete. Improvement: +4.2% accuracy
                </span>
              </div>

              <div>
                <h4 className="text-xs font-mono text-white/40 uppercase mb-2">Optimized Parameters</h4>
                <div className="space-y-2">
                  <div className="flex justify-between text-xs font-mono">
                    <span className="text-white/60">Base Probability Scale</span>
                    <span className="text-white">1.05 <span className="text-green-400">(+0.05)</span></span>
                  </div>
                  <div className="flex justify-between text-xs font-mono">
                    <span className="text-white/60">Confidence Threshold</span>
                    <span className="text-white">0.72 <span className="text-yellow-400">(-0.03)</span></span>
                  </div>
                  <div className="flex justify-between text-xs font-mono">
                    <span className="text-white/60">Drift Sensitivity</span>
                    <span className="text-white">0.6 <span className="text-green-400">(+0.1)</span></span>
                  </div>
                </div>
              </div>

              <div>
                <h4 className="text-xs font-mono text-white/40 uppercase mb-2">Cross-Validation Scores</h4>
                <div className="flex gap-2">
                  {[0.82, 0.79, 0.84, 0.81, 0.83].map((score, i) => (
                    <div key={i} className="flex-1 bg-white/5 p-2 text-center">
                      <span className="text-[10px] font-mono text-white/30">Fold {i + 1}</span>
                      <p className="text-sm font-mono text-white font-bold">{(score * 100).toFixed(0)}%</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {tuneStatus === 'idle' && (
            <div className="text-center py-8">
              <Sliders className="w-8 h-8 text-white/20 mx-auto mb-3" />
              <p className="text-xs font-mono text-white/40 mb-1">No active tuning session</p>
              <p className="text-[10px] font-mono text-white/30">
                Run auto-tune to optimize parameters with cross-validation
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function MetricsTab({
  metrics,
  expandedMetric,
  onToggleMetric,
  validations,
}: {
  metrics: ErrorMetrics;
  expandedMetric: string | null;
  onToggleMetric: (id: string) => void;
  validations: ValidationRecord[];
}) {
  return (
    <div className="space-y-6">
      {/* Error Metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <ErrorMetricCard
          id="distribution"
          title="Distribution Error"
          icon={Layers}
          metrics={[
            { label: 'Wasserstein', value: metrics.distribution.wasserstein },
            { label: 'JS Divergence', value: metrics.distribution.js_divergence },
            { label: 'KL Divergence', value: metrics.distribution.kl_divergence },
          ]}
          status={metrics.distribution.status}
          isExpanded={expandedMetric === 'distribution'}
          onToggle={() => onToggleMetric('distribution')}
        />
        <ErrorMetricCard
          id="ranking"
          title="Ranking Error"
          icon={BarChart3}
          metrics={[
            { label: 'Spearman ρ', value: metrics.ranking.spearman_rho },
            { label: 'Kendall τ', value: metrics.ranking.kendall_tau },
            { label: 'NDCG', value: metrics.ranking.ndcg },
          ]}
          status={metrics.ranking.status}
          isExpanded={expandedMetric === 'ranking'}
          onToggle={() => onToggleMetric('ranking')}
        />
        <ErrorMetricCard
          id="turning_point"
          title="Turning Point Detection"
          icon={TrendingUp}
          metrics={[
            { label: 'Precision', value: metrics.turning_point.precision },
            { label: 'Recall', value: metrics.turning_point.recall },
            { label: 'F1 Score', value: metrics.turning_point.f1_score },
          ]}
          status={metrics.turning_point.status}
          isExpanded={expandedMetric === 'turning_point'}
          onToggle={() => onToggleMetric('turning_point')}
          extra={
            <div className="text-xs font-mono text-white/40 mt-2">
              Lead Time: {metrics.turning_point.lead_time.toFixed(1)} days
            </div>
          }
        />
      </div>

      {/* Recent Validations */}
      <div className="bg-white/5 border border-white/10">
        <div className="p-4 border-b border-white/10 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle className="w-3 h-3 text-white/40" />
            <h2 className="text-xs font-mono text-white/40 uppercase tracking-wider">
              Recent Validations
            </h2>
          </div>
          <span className="text-[10px] font-mono text-white/30">{validations.length} total</span>
        </div>
        <div className="divide-y divide-white/5">
          {validations.length === 0 ? (
            <div className="p-8 text-center">
              <Activity className="w-6 h-6 text-white/20 mx-auto mb-2" />
              <p className="text-xs font-mono text-white/40">No validations yet</p>
            </div>
          ) : (
            validations.slice(0, 5).map((v) => (
              <div key={v.id} className="p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {v.within_confidence_interval ? (
                    <CheckCircle className="w-4 h-4 text-green-400" />
                  ) : (
                    <X className="w-4 h-4 text-red-400" />
                  )}
                  <div>
                    <p className="text-xs font-mono text-white">VAL_{v.id.slice(0, 8).toUpperCase()}</p>
                    <p className="text-[10px] font-mono text-white/30">
                      {new Date(v.validated_at).toLocaleString()}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className={cn(
                    'text-lg font-mono font-bold',
                    v.accuracy_score >= 0.8 ? 'text-green-400' :
                    v.accuracy_score >= 0.6 ? 'text-yellow-400' : 'text-red-400'
                  )}>
                    {(v.accuracy_score * 100).toFixed(1)}%
                  </p>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

function SensitivityTab() {
  const mockSensitivity = [
    { variable: 'media_exposure', impact: 0.85, elasticity: 1.2, direction: 'positive' as const },
    { variable: 'price_change', impact: 0.72, elasticity: -0.8, direction: 'negative' as const },
    { variable: 'social_influence', impact: 0.68, elasticity: 0.9, direction: 'positive' as const },
    { variable: 'trust_level', impact: 0.55, elasticity: 0.6, direction: 'positive' as const },
    { variable: 'economic_indicator', impact: 0.42, elasticity: 0.4, direction: 'positive' as const },
  ];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Variable Impact Ranking */}
      <div className="bg-white/5 border border-white/10">
        <div className="p-4 border-b border-white/10">
          <div className="flex items-center gap-2">
            <Crosshair className="w-3 h-3 text-white/40" />
            <h2 className="text-xs font-mono text-white/40 uppercase tracking-wider">
              Variable Impact Ranking
            </h2>
          </div>
        </div>
        <div className="p-4 space-y-4">
          {mockSensitivity.map((v, i) => (
            <div key={v.variable}>
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono text-white/30">#{i + 1}</span>
                  <span className="text-xs font-mono text-white uppercase">
                    {v.variable.replace(/_/g, ' ')}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  {v.direction === 'positive' ? (
                    <TrendingUp className="w-3 h-3 text-green-400" />
                  ) : (
                    <TrendingDown className="w-3 h-3 text-red-400" />
                  )}
                  <span className="text-xs font-mono text-white font-bold">
                    {(v.impact * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
              <div className="w-full bg-white/10 h-2">
                <div
                  className={cn(
                    'h-2 transition-all',
                    v.impact >= 0.7 ? 'bg-cyan-400' :
                    v.impact >= 0.5 ? 'bg-yellow-400' : 'bg-white/30'
                  )}
                  style={{ width: `${v.impact * 100}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Elasticity Analysis */}
      <div className="bg-white/5 border border-white/10">
        <div className="p-4 border-b border-white/10">
          <div className="flex items-center gap-2">
            <Activity className="w-3 h-3 text-white/40" />
            <h2 className="text-xs font-mono text-white/40 uppercase tracking-wider">
              Elasticity Analysis
            </h2>
          </div>
        </div>
        <div className="p-4">
          <div className="space-y-3">
            {mockSensitivity.map((v) => (
              <div key={v.variable} className="flex items-center justify-between py-2 border-b border-white/5 last:border-0">
                <span className="text-xs font-mono text-white/60 uppercase">
                  {v.variable.replace(/_/g, ' ')}
                </span>
                <div className="flex items-center gap-4">
                  <span className={cn(
                    'text-xs font-mono',
                    v.elasticity > 0 ? 'text-green-400' : 'text-red-400'
                  )}>
                    {v.elasticity > 0 ? '+' : ''}{v.elasticity.toFixed(2)}
                  </span>
                  <span className={cn(
                    'text-[10px] font-mono uppercase px-1.5 py-0.5',
                    Math.abs(v.elasticity) > 1 ? 'bg-cyan-500/20 text-cyan-400' :
                    Math.abs(v.elasticity) > 0.5 ? 'bg-yellow-500/20 text-yellow-400' :
                    'bg-white/10 text-white/40'
                  )}>
                    {Math.abs(v.elasticity) > 1 ? 'ELASTIC' :
                     Math.abs(v.elasticity) > 0.5 ? 'MODERATE' : 'INELASTIC'}
                  </span>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-4 pt-4 border-t border-white/10">
            <Button
              variant="outline"
              size="sm"
              className="w-full font-mono text-xs border-white/20 text-white/60 hover:bg-white/5 hover:text-white"
            >
              <RefreshCw className="w-3 h-3 mr-2" />
              RUN SENSITIVITY SCAN
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Helper Components
// ============================================================================

function StatCard({
  icon: Icon,
  label,
  value,
  status,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  status?: 'good' | 'warning' | 'error';
}) {
  return (
    <div className={cn(
      'bg-white/5 border p-3 hover:bg-white/[0.07] transition-colors',
      status === 'good' ? 'border-green-500/30' :
      status === 'warning' ? 'border-yellow-500/30' :
      status === 'error' ? 'border-red-500/30' : 'border-white/10'
    )}>
      <div className="flex items-center gap-2 mb-1">
        <Icon className={cn(
          'w-3 h-3',
          status === 'good' ? 'text-green-400' :
          status === 'warning' ? 'text-yellow-400' :
          status === 'error' ? 'text-red-400' : 'text-white/40'
        )} />
        <span className="text-[10px] font-mono text-white/40 uppercase tracking-wider">{label}</span>
      </div>
      <p className={cn(
        'text-xl font-mono font-bold',
        status === 'good' ? 'text-green-400' :
        status === 'warning' ? 'text-yellow-400' :
        status === 'error' ? 'text-red-400' : 'text-white'
      )}>{value}</p>
    </div>
  );
}

function ParameterSlider({
  label,
  value,
  min,
  max,
  step,
  unit = '',
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  unit?: string;
  onChange: (value: number) => void;
}) {
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-mono text-white/60">{label}</span>
        <span className="text-xs font-mono text-white font-bold">
          {value.toFixed(step < 1 ? 2 : 0)}{unit}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full h-1 bg-white/10 appearance-none cursor-pointer accent-cyan-500"
      />
      <div className="flex justify-between mt-1">
        <span className="text-[10px] font-mono text-white/30">{min}{unit}</span>
        <span className="text-[10px] font-mono text-white/30">{max}{unit}</span>
      </div>
    </div>
  );
}

function ErrorMetricCard({
  id,
  title,
  icon: Icon,
  metrics,
  status,
  isExpanded,
  onToggle,
  extra,
}: {
  id: string;
  title: string;
  icon: React.ElementType;
  metrics: { label: string; value: number }[];
  status: 'good' | 'warning' | 'error';
  isExpanded: boolean;
  onToggle: () => void;
  extra?: React.ReactNode;
}) {
  return (
    <div className={cn(
      'bg-white/5 border transition-colors',
      status === 'good' ? 'border-green-500/30' :
      status === 'warning' ? 'border-yellow-500/30' : 'border-red-500/30'
    )}>
      <button
        onClick={onToggle}
        className="w-full p-4 flex items-center justify-between text-left"
      >
        <div className="flex items-center gap-2">
          <Icon className={cn(
            'w-4 h-4',
            status === 'good' ? 'text-green-400' :
            status === 'warning' ? 'text-yellow-400' : 'text-red-400'
          )} />
          <span className="text-sm font-mono text-white">{title}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className={cn(
            'text-[10px] font-mono uppercase px-1.5 py-0.5',
            status === 'good' ? 'bg-green-500/20 text-green-400' :
            status === 'warning' ? 'bg-yellow-500/20 text-yellow-400' :
            'bg-red-500/20 text-red-400'
          )}>
            {status}
          </span>
          {isExpanded ? (
            <ChevronDown className="w-3 h-3 text-white/40" />
          ) : (
            <ChevronRight className="w-3 h-3 text-white/40" />
          )}
        </div>
      </button>
      {isExpanded && (
        <div className="px-4 pb-4 pt-0">
          <div className="border-t border-white/10 pt-3 space-y-2">
            {metrics.map((m) => (
              <div key={m.label} className="flex justify-between text-xs font-mono">
                <span className="text-white/60">{m.label}</span>
                <span className="text-white font-bold">
                  {m.value < 1 ? (m.value * 100).toFixed(1) + '%' : m.value.toFixed(2)}
                </span>
              </div>
            ))}
            {extra}
          </div>
        </div>
      )}
    </div>
  );
}
