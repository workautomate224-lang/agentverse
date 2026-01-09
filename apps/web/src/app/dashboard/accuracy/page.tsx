'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  Target,
  CheckCircle,
  AlertTriangle,
  Award,
  Database,
  Plus,
  Loader2,
  ChevronRight,
  Activity,
  Terminal,
} from 'lucide-react';
import {
  useAccuracyStats,
  useBenchmarks,
  useValidations,
  useSeedElectionBenchmarks,
} from '@/hooks/useApi';
import { Benchmark, ValidationRecord } from '@/lib/api';
import { cn } from '@/lib/utils';

export default function AccuracyPage() {
  const [categoryFilter, setCategoryFilter] = useState<string>('');

  const { data: stats, isLoading: statsLoading } = useAccuracyStats(categoryFilter || undefined);
  const { data: benchmarks, isLoading: benchmarksLoading } = useBenchmarks();
  const { data: validations, isLoading: validationsLoading } = useValidations();
  const seedBenchmarks = useSeedElectionBenchmarks();

  const isLoading = statsLoading || benchmarksLoading || validationsLoading;

  const handleSeedBenchmarks = async () => {
    try {
      await seedBenchmarks.mutateAsync();
    } catch {
      // Seed failed - mutation error is handled by react-query
    }
  };

  return (
    <div className="min-h-screen bg-black p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Target className="w-4 h-4 text-white/60" />
            <span className="text-xs font-mono text-white/40 uppercase tracking-wider">Validation Module</span>
          </div>
          <h1 className="text-xl font-mono font-bold text-white">Accuracy Tracking</h1>
          <p className="text-sm font-mono text-white/50 mt-1">
            Validate predictions against real-world outcomes
          </p>
        </div>
        <div className="flex gap-2">
          {(!benchmarks || benchmarks.length === 0) && (
            <Button
              onClick={handleSeedBenchmarks}
              disabled={seedBenchmarks.isPending}
              className="bg-white/10 border border-white/20 text-white hover:bg-white/20 font-mono text-xs h-8"
            >
              {seedBenchmarks.isPending ? (
                <Loader2 className="w-3 h-3 mr-2 animate-spin" />
              ) : (
                <Database className="w-3 h-3 mr-2" />
              )}
              SEED DATA
            </Button>
          )}
          <Link href="/dashboard/accuracy/benchmarks/new">
            <Button size="sm">
              <Plus className="w-3 h-3 mr-2" />
              ADD BENCHMARK
            </Button>
          </Link>
        </div>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-5 h-5 animate-spin text-white/40" />
        </div>
      )}

      {!isLoading && (
        <>
          {/* Stats Overview */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-8">
            <StatCard
              icon={Target}
              label="AVG ACCURACY"
              value={stats?.average_accuracy ? `${(stats.average_accuracy * 100).toFixed(1)}%` : '--'}
              subtext={stats?.total_validations ? `${stats.total_validations} validations` : 'No validations'}
            />
            <StatCard
              icon={CheckCircle}
              label="WITHIN CI"
              value={stats?.within_ci_rate ? `${(stats.within_ci_rate * 100).toFixed(1)}%` : '--'}
              subtext="Within confidence interval"
            />
            <StatCard
              icon={Award}
              label="BEST CATEGORY"
              value={stats?.best_performing_category?.toUpperCase() || '--'}
              subtext={stats?.best_performing_category && stats.accuracy_by_category?.[stats.best_performing_category]
                ? `${(stats.accuracy_by_category[stats.best_performing_category] * 100).toFixed(1)}% accuracy`
                : 'No data'}
            />
            <StatCard
              icon={Database}
              label="BENCHMARKS"
              value={benchmarks?.length?.toString() || '0'}
              subtext="Available for validation"
            />
          </div>

          {/* Accuracy by Category */}
          {stats?.accuracy_by_category && Object.keys(stats.accuracy_by_category).length > 0 && (
            <div className="bg-white/5 border border-white/10 p-6 mb-8">
              <div className="flex items-center gap-2 mb-4">
                <Activity className="w-3 h-3 text-white/40" />
                <h2 className="text-xs font-mono text-white/40 uppercase tracking-wider">Accuracy by Category</h2>
              </div>
              <div className="space-y-4">
                {Object.entries(stats.accuracy_by_category).map(([category, accuracy]) => (
                  <div key={category} className="flex items-center gap-4">
                    <span className="w-24 text-xs font-mono text-white/60 uppercase">{category}</span>
                    <div className="flex-1">
                      <div className="w-full bg-white/10 h-2">
                        <div
                          className={cn(
                            'h-2 transition-all',
                            accuracy >= 0.9 ? 'bg-green-500' :
                            accuracy >= 0.7 ? 'bg-yellow-500' : 'bg-red-500'
                          )}
                          style={{ width: `${accuracy * 100}%` }}
                        />
                      </div>
                    </div>
                    <span className="w-16 text-right text-sm font-mono font-bold text-white">
                      {(accuracy * 100).toFixed(1)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Areas for Improvement */}
          {stats?.areas_for_improvement && stats.areas_for_improvement.length > 0 && (
            <div className="bg-yellow-500/10 border border-yellow-500/30 p-4 mb-8">
              <div className="flex items-start gap-3">
                <AlertTriangle className="w-4 h-4 text-yellow-500 mt-0.5" />
                <div>
                  <h3 className="text-sm font-mono font-bold text-yellow-400 mb-2">AREAS FOR IMPROVEMENT</h3>
                  <ul className="space-y-1">
                    {stats.areas_for_improvement.map((area, i) => (
                      <li key={i} className="text-xs font-mono text-yellow-400/70">{area}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}

          {/* Two Column Layout */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Benchmarks List */}
            <div className="bg-white/5 border border-white/10">
              <div className="p-4 border-b border-white/10">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Database className="w-3 h-3 text-white/40" />
                    <h2 className="text-xs font-mono text-white/40 uppercase tracking-wider">Benchmarks</h2>
                  </div>
                  <Link href="/dashboard/accuracy/benchmarks" className="text-[10px] font-mono text-white/30 hover:text-white/60 transition-colors">
                    VIEW ALL &rarr;
                  </Link>
                </div>
              </div>
              <div className="divide-y divide-white/5">
                {(!benchmarks || benchmarks.length === 0) ? (
                  <div className="p-8 text-center">
                    <div className="w-10 h-10 bg-white/5 flex items-center justify-center mx-auto mb-3">
                      <Database className="w-4 h-4 text-white/30" />
                    </div>
                    <p className="text-xs font-mono text-white/40 mb-3">No benchmarks yet</p>
                    <Button
                      size="sm"
                      onClick={handleSeedBenchmarks}
                      disabled={seedBenchmarks.isPending}
                      className="bg-white/10 border border-white/20 text-white hover:bg-white/20 font-mono text-[10px] h-7"
                    >
                      SEED DATA
                    </Button>
                  </div>
                ) : (
                  benchmarks.slice(0, 5).map((benchmark) => (
                    <BenchmarkItem key={benchmark.id} benchmark={benchmark} />
                  ))
                )}
              </div>
            </div>

            {/* Recent Validations */}
            <div className="bg-white/5 border border-white/10">
              <div className="p-4 border-b border-white/10">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Activity className="w-3 h-3 text-white/40" />
                    <h2 className="text-xs font-mono text-white/40 uppercase tracking-wider">Recent Validations</h2>
                  </div>
                  <Link href="/dashboard/accuracy/validations" className="text-[10px] font-mono text-white/30 hover:text-white/60 transition-colors">
                    VIEW ALL &rarr;
                  </Link>
                </div>
              </div>
              <div className="divide-y divide-white/5">
                {(!validations || validations.length === 0) ? (
                  <div className="p-8 text-center">
                    <div className="w-10 h-10 bg-white/5 flex items-center justify-center mx-auto mb-3">
                      <Activity className="w-4 h-4 text-white/30" />
                    </div>
                    <p className="text-xs font-mono text-white/40 mb-1">No validations yet</p>
                    <p className="text-[10px] font-mono text-white/30">
                      Validate a prediction against a benchmark
                    </p>
                  </div>
                ) : (
                  validations.slice(0, 5).map((validation) => (
                    <ValidationItem key={validation.id} validation={validation} />
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Accuracy Trend */}
          {stats?.accuracy_trend && stats.accuracy_trend.length > 0 && (
            <div className="bg-white/5 border border-white/10 p-6 mt-8">
              <div className="flex items-center gap-2 mb-4">
                <Activity className="w-3 h-3 text-white/40" />
                <h2 className="text-xs font-mono text-white/40 uppercase tracking-wider">Accuracy Trend</h2>
              </div>
              <div className="h-32 flex items-end gap-1">
                {stats.accuracy_trend.map((point, i) => (
                  <div key={i} className="flex-1 flex flex-col items-center">
                    <div
                      className={cn(
                        'w-full transition-all',
                        point.accuracy >= 0.9 ? 'bg-green-500' :
                        point.accuracy >= 0.7 ? 'bg-yellow-500' : 'bg-red-500'
                      )}
                      style={{ height: `${point.accuracy * 100}%` }}
                    />
                    <span className="text-[8px] font-mono text-white/30 mt-2 rotate-45 origin-left whitespace-nowrap">
                      {point.date}
                    </span>
                  </div>
                ))}
              </div>
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
              <span>VALIDATION MODULE</span>
            </div>
          </div>
          <span>AGENTVERSE v1.0.0</span>
        </div>
      </div>
    </div>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  subtext,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  subtext: string;
}) {
  return (
    <div className="bg-white/5 border border-white/10 p-4 hover:bg-white/[0.07] transition-colors">
      <div className="flex items-start justify-between mb-2">
        <Icon className="w-4 h-4 text-white/40" />
      </div>
      <p className="text-[10px] font-mono text-white/40 uppercase tracking-wider">{label}</p>
      <p className="text-2xl font-mono font-bold text-white mt-1">{value}</p>
      <p className="text-[10px] font-mono text-white/30 mt-1">{subtext}</p>
    </div>
  );
}

function BenchmarkItem({ benchmark }: { benchmark: Benchmark }) {
  return (
    <div className="p-4 hover:bg-white/5 transition-colors">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <h4 className="text-sm font-mono text-white">{benchmark.name}</h4>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-[10px] font-mono text-white/40 uppercase px-1.5 py-0.5 bg-white/10">
              {benchmark.category}
            </span>
            <span className="text-[10px] font-mono text-white/30">{benchmark.region.toUpperCase()}</span>
            {benchmark.event_date && (
              <span className="text-[10px] font-mono text-white/20">
                {new Date(benchmark.event_date).toLocaleDateString()}
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className={cn(
            'text-[10px] font-mono uppercase px-1.5 py-0.5',
            benchmark.verification_status === 'verified'
              ? 'bg-green-500/20 text-green-400'
              : 'bg-yellow-500/20 text-yellow-400'
          )}>
            {benchmark.verification_status}
          </span>
          <ChevronRight className="w-3 h-3 text-white/30" />
        </div>
      </div>
    </div>
  );
}

function ValidationItem({ validation }: { validation: ValidationRecord }) {
  const accuracyColor = validation.accuracy_score >= 0.9 ? 'text-green-400' :
                        validation.accuracy_score >= 0.7 ? 'text-yellow-400' : 'text-red-400';

  return (
    <div className="p-4 hover:bg-white/5 transition-colors">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            {validation.within_confidence_interval ? (
              <CheckCircle className="w-3 h-3 text-green-500" />
            ) : (
              <AlertTriangle className="w-3 h-3 text-yellow-500" />
            )}
            <span className="text-xs font-mono text-white/60">
              VAL_{validation.id.slice(0, 8).toUpperCase()}
            </span>
          </div>
          <p className="text-[10px] font-mono text-white/30 mt-1">
            {new Date(validation.validated_at).toLocaleString()}
          </p>
        </div>
        <div className="text-right">
          <p className={cn('text-lg font-mono font-bold', accuracyColor)}>
            {(validation.accuracy_score * 100).toFixed(1)}%
          </p>
          <p className="text-[10px] font-mono text-white/30">
            {validation.within_confidence_interval ? 'WITHIN CI' : 'OUTSIDE CI'}
          </p>
        </div>
      </div>
    </div>
  );
}
