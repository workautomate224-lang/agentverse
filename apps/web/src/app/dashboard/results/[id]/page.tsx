'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  ArrowLeft,
  Download,
  CheckCircle,
  Clock,
  XCircle,
  Loader2,
  Users,
  DollarSign,
  BarChart3,
  Timer,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Terminal,
  type LucideIcon,
} from 'lucide-react';
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { useSimulation, useSimulationResults, useAgentResponses, useExportSimulation } from '@/hooks/useApi';
import { cn } from '@/lib/utils';

const COLORS = ['#ffffff', '#a3a3a3', '#737373', '#525252', '#404040', '#262626', '#171717', '#0a0a0a'];

export default function ResultDetailPage() {
  const params = useParams();
  const runId = params.id as string;

  const { data: simulation, isLoading: simulationLoading } = useSimulation(runId);
  const { data: results, isLoading: resultsLoading } = useSimulationResults(runId);
  const { data: responses, isLoading: responsesLoading } = useAgentResponses(runId, { limit: 20 });
  const exportSimulation = useExportSimulation();

  const [activeTab, setActiveTab] = useState<'overview' | 'demographics' | 'responses'>('overview');

  const handleExport = async (format: 'csv' | 'json') => {
    try {
      const blob = await exportSimulation.mutateAsync({ runId, format });

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `simulation_${runId.slice(0, 8)}.${format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch {
      // Export failed silently
    }
  };

  if (simulationLoading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-white/40" />
      </div>
    );
  }

  if (!simulation) {
    return (
      <div className="min-h-screen bg-black p-6">
        <div className="bg-red-500/10 border border-red-500/30 p-6 text-center">
          <h2 className="text-lg font-mono font-bold text-red-400 mb-2">SIMULATION NOT FOUND</h2>
          <Link href="/dashboard/results">
            <Button variant="outline" className="mt-4 font-mono text-xs border-white/20 text-white/60 hover:bg-white/5">
              <ArrowLeft className="w-3 h-3 mr-2" />
              BACK TO RESULTS
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  const statusConfig = getStatusConfig(simulation.status);

  return (
    <div className="min-h-screen bg-black p-6">
      {/* Header */}
      <div className="mb-8">
        <Link href="/dashboard/results">
          <Button variant="ghost" size="sm" className="text-white/60 hover:text-white hover:bg-white/5 font-mono text-xs mb-4">
            <ArrowLeft className="w-3 h-3 mr-2" />
            BACK TO RESULTS
          </Button>
        </Link>

        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-mono font-bold text-white">
                Simulation #{simulation.id.slice(0, 8)}
              </h1>
              <span className={cn(
                'px-2 py-0.5 text-[10px] font-mono uppercase',
                statusConfig.bg,
                statusConfig.color
              )}>
                {statusConfig.label}
              </span>
            </div>
            <p className="text-xs font-mono text-white/40 mt-1">
              {simulation.model_used} &bull; Created {new Date(simulation.created_at).toLocaleString()}
            </p>
          </div>

          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleExport('csv')}
              disabled={exportSimulation.isPending || simulation.status !== 'completed'}
              className="font-mono text-[10px] border-white/20 text-white/60 hover:bg-white/5"
            >
              <Download className="w-3 h-3 mr-2" />
              EXPORT CSV
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleExport('json')}
              disabled={exportSimulation.isPending || simulation.status !== 'completed'}
              className="font-mono text-[10px] border-white/20 text-white/60 hover:bg-white/5"
            >
              EXPORT JSON
            </Button>
          </div>
        </div>
      </div>

      {/* Progress for running simulations */}
      {simulation.status === 'running' && (
        <div className="bg-white/5 border border-white/10 p-6 mb-8">
          <div className="flex items-center gap-3 mb-4">
            <Loader2 className="w-4 h-4 animate-spin text-white" />
            <span className="font-mono text-xs text-white">SIMULATION IN PROGRESS...</span>
          </div>
          <div className="w-full bg-white/10 h-2">
            <div
              className="bg-white h-2 transition-all"
              style={{ width: `${simulation.progress}%` }}
            />
          </div>
          <p className="text-[10px] font-mono text-white/40 mt-2">{simulation.progress}% complete</p>
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
        <StatCard
          icon={Users}
          label="Agents"
          value={String(simulation.agent_count)}
        />
        <StatCard
          icon={DollarSign}
          label="Cost"
          value={`$${simulation.cost_usd.toFixed(4)}`}
        />
        <StatCard
          icon={BarChart3}
          label="Tokens Used"
          value={formatNumber(simulation.tokens_used)}
        />
        <StatCard
          icon={Timer}
          label="Duration"
          value={simulation.completed_at && simulation.started_at
            ? formatDuration(new Date(simulation.completed_at).getTime() - new Date(simulation.started_at).getTime())
            : '--'
          }
        />
      </div>

      {/* Tabs */}
      <div className="border-b border-white/10 mb-6">
        <nav className="flex gap-8">
          <TabButton
            active={activeTab === 'overview'}
            onClick={() => setActiveTab('overview')}
          >
            OVERVIEW
          </TabButton>
          <TabButton
            active={activeTab === 'demographics'}
            onClick={() => setActiveTab('demographics')}
          >
            DEMOGRAPHICS
          </TabButton>
          <TabButton
            active={activeTab === 'responses'}
            onClick={() => setActiveTab('responses')}
          >
            AGENT RESPONSES
          </TabButton>
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <OverviewTab results={results} isLoading={resultsLoading} />
      )}
      {activeTab === 'demographics' && (
        <DemographicsTab results={results} isLoading={resultsLoading} />
      )}
      {activeTab === 'responses' && (
        <ResponsesTab responses={responses} isLoading={responsesLoading} runId={runId} />
      )}

      {/* Footer Status */}
      <div className="mt-8 pt-4 border-t border-white/5">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-1">
            <Terminal className="w-3 h-3" />
            <span>RESULT DETAIL MODULE</span>
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
}: {
  icon: LucideIcon;
  label: string;
  value: string;
}) {
  return (
    <div className="bg-white/5 border border-white/10 p-4">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-white/10 flex items-center justify-center">
          <Icon className="w-5 h-5 text-white/60" />
        </div>
        <div>
          <p className="text-[10px] font-mono text-white/40 uppercase">{label}</p>
          <p className="text-lg font-mono font-bold text-white">{value}</p>
        </div>
      </div>
    </div>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'pb-3 text-xs font-mono border-b-2 transition-colors',
        active
          ? 'border-white text-white'
          : 'border-transparent text-white/40 hover:text-white/60'
      )}
    >
      {children}
    </button>
  );
}

function OverviewTab({ results, isLoading }: { results: any; isLoading: boolean }) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-5 h-5 animate-spin text-white/40" />
      </div>
    );
  }

  if (!results?.results_summary) {
    return (
      <div className="text-center py-12 text-white/40 font-mono text-xs">
        NO RESULTS AVAILABLE YET
      </div>
    );
  }

  const { results_summary } = results;
  const responseData = Object.entries(results_summary.response_distribution || {}).map(([name, value]) => ({
    name,
    value: value as number,
    percentage: results_summary.response_percentages?.[name] || 0,
  }));

  return (
    <div className="space-y-6">
      {/* Summary */}
      <div className="bg-white/5 border border-white/10 p-6">
        <h3 className="font-mono text-sm font-bold text-white mb-4 uppercase">Results Summary</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          <div>
            <p className="text-[10px] font-mono text-white/40 uppercase">Total Responses</p>
            <p className="text-2xl font-mono font-bold text-white">{results_summary.total_agents}</p>
          </div>
          <div>
            <p className="text-[10px] font-mono text-white/40 uppercase">Top Response</p>
            <p className="text-2xl font-mono font-bold text-white">
              {results_summary.top_response || 'N/A'}
            </p>
          </div>
          <div>
            <p className="text-[10px] font-mono text-white/40 uppercase">Confidence Score</p>
            <p className="text-2xl font-mono font-bold text-white">
              {results_summary.confidence_score
                ? `${(results_summary.confidence_score * 100).toFixed(0)}%`
                : 'N/A'
              }
            </p>
          </div>
          <div>
            <p className="text-[10px] font-mono text-white/40 uppercase">Response Types</p>
            <p className="text-2xl font-mono font-bold text-white">{responseData.length}</p>
          </div>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pie Chart */}
        <div className="bg-white/5 border border-white/10 p-6">
          <h3 className="font-mono text-sm font-bold text-white mb-4 uppercase">Response Distribution</h3>
          {responseData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={responseData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percentage }) => `${name}: ${percentage.toFixed(1)}%`}
                  outerRadius={100}
                  fill="#ffffff"
                  dataKey="value"
                >
                  {responseData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#000',
                    border: '1px solid rgba(255,255,255,0.2)',
                    borderRadius: 0,
                    fontFamily: 'monospace',
                    fontSize: '12px',
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[300px] flex items-center justify-center text-white/40 font-mono text-xs">
              NO RESPONSE DATA AVAILABLE
            </div>
          )}
        </div>

        {/* Bar Chart */}
        <div className="bg-white/5 border border-white/10 p-6">
          <h3 className="font-mono text-sm font-bold text-white mb-4 uppercase">Response Counts</h3>
          {responseData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={responseData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                <XAxis dataKey="name" stroke="rgba(255,255,255,0.4)" tick={{ fontFamily: 'monospace', fontSize: 10 }} />
                <YAxis stroke="rgba(255,255,255,0.4)" tick={{ fontFamily: 'monospace', fontSize: 10 }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#000',
                    border: '1px solid rgba(255,255,255,0.2)',
                    borderRadius: 0,
                    fontFamily: 'monospace',
                    fontSize: '12px',
                  }}
                />
                <Bar dataKey="value" fill="#ffffff" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[300px] flex items-center justify-center text-white/40 font-mono text-xs">
              NO RESPONSE DATA AVAILABLE
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function DemographicsTab({ results, isLoading }: { results: any; isLoading: boolean }) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-5 h-5 animate-spin text-white/40" />
      </div>
    );
  }

  if (!results?.results_summary?.demographics_breakdown) {
    return (
      <div className="text-center py-12 text-white/40 font-mono text-xs">
        NO DEMOGRAPHIC DATA AVAILABLE
      </div>
    );
  }

  const { demographics_breakdown } = results.results_summary;

  return (
    <div className="space-y-6">
      {Object.entries(demographics_breakdown).map(([demographic, responses]) => (
        <DemographicSection
          key={demographic}
          title={formatDemographicTitle(demographic)}
          data={responses as Record<string, Record<string, number>>}
        />
      ))}
    </div>
  );
}

function DemographicSection({
  title,
  data,
}: {
  title: string;
  data: Record<string, Record<string, number>>;
}) {
  const [expanded, setExpanded] = useState(true);

  // Transform data for chart
  const chartData = Object.entries(data).map(([category, responses]) => {
    const total = Object.values(responses).reduce((a, b) => a + b, 0);
    return {
      category,
      ...responses,
      total,
    };
  });

  const responseKeys = [...new Set(Object.values(data).flatMap(r => Object.keys(r)))];

  return (
    <div className="bg-white/5 border border-white/10">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-6 text-left"
      >
        <h3 className="font-mono text-sm font-bold text-white uppercase">{title}</h3>
        {expanded ? (
          <ChevronUp className="w-4 h-4 text-white/40" />
        ) : (
          <ChevronDown className="w-4 h-4 text-white/40" />
        )}
      </button>

      {expanded && (
        <div className="px-6 pb-6">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
              <XAxis type="number" stroke="rgba(255,255,255,0.4)" tick={{ fontFamily: 'monospace', fontSize: 10 }} />
              <YAxis dataKey="category" type="category" width={100} stroke="rgba(255,255,255,0.4)" tick={{ fontFamily: 'monospace', fontSize: 10 }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#000',
                  border: '1px solid rgba(255,255,255,0.2)',
                  borderRadius: 0,
                  fontFamily: 'monospace',
                  fontSize: '12px',
                }}
              />
              <Legend wrapperStyle={{ fontFamily: 'monospace', fontSize: '10px' }} />
              {responseKeys.map((key, index) => (
                <Bar
                  key={key}
                  dataKey={key}
                  stackId="a"
                  fill={COLORS[index % COLORS.length]}
                />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

function ResponsesTab({
  responses,
  isLoading,
  runId,
}: {
  responses: any[] | undefined;
  isLoading: boolean;
  runId: string;
}) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-5 h-5 animate-spin text-white/40" />
      </div>
    );
  }

  if (!responses || responses.length === 0) {
    return (
      <div className="text-center py-12 text-white/40 font-mono text-xs">
        NO AGENT RESPONSES AVAILABLE
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {responses.map((response) => (
        <div
          key={response.id}
          className="bg-white/5 border border-white/10 overflow-hidden"
        >
          <button
            onClick={() => setExpandedId(expandedId === response.id ? null : response.id)}
            className="w-full flex items-center justify-between p-4 text-left hover:bg-white/[0.03]"
          >
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 bg-white/10 flex items-center justify-center">
                <span className="text-xs font-mono font-bold text-white">
                  #{response.agent_index + 1}
                </span>
              </div>
              <div>
                <p className="font-mono text-xs font-bold text-white">Agent #{response.agent_index + 1}</p>
                <p className="text-[10px] font-mono text-white/40">
                  {response.response_time_ms}ms &bull; {response.tokens_used} tokens
                </p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-xs font-mono text-white/60 max-w-[200px] truncate">
                {typeof response.response === 'object'
                  ? JSON.stringify(response.response).slice(0, 50) + '...'
                  : String(response.response).slice(0, 50) + '...'
                }
              </span>
              {expandedId === response.id ? (
                <ChevronUp className="w-4 h-4 text-white/40" />
              ) : (
                <ChevronDown className="w-4 h-4 text-white/40" />
              )}
            </div>
          </button>

          {expandedId === response.id && (
            <div className="border-t border-white/10 px-4 py-4 bg-white/[0.02]">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Persona */}
                <div>
                  <h4 className="font-mono text-[10px] text-white/40 uppercase mb-2">Persona</h4>
                  <div className="bg-black border border-white/10 p-3 text-xs font-mono">
                    <pre className="whitespace-pre-wrap overflow-x-auto text-white/60">
                      {JSON.stringify(response.persona, null, 2)}
                    </pre>
                  </div>
                </div>

                {/* Response */}
                <div>
                  <h4 className="font-mono text-[10px] text-white/40 uppercase mb-2">Response</h4>
                  <div className="bg-black border border-white/10 p-3 text-xs font-mono">
                    <pre className="whitespace-pre-wrap overflow-x-auto text-white/60">
                      {JSON.stringify(response.response, null, 2)}
                    </pre>
                  </div>
                </div>
              </div>

              {/* Reasoning */}
              {response.reasoning && (
                <div className="mt-4">
                  <h4 className="font-mono text-[10px] text-white/40 uppercase mb-2">Reasoning</h4>
                  <div className="bg-black border border-white/10 p-3 text-xs font-mono text-white/60">
                    {response.reasoning}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function getStatusConfig(status: string) {
  switch (status) {
    case 'completed':
      return {
        icon: CheckCircle,
        label: 'COMPLETED',
        color: 'text-green-400',
        bg: 'bg-green-500/20',
      };
    case 'running':
      return {
        icon: Loader2,
        label: 'RUNNING',
        color: 'text-yellow-400',
        bg: 'bg-yellow-500/20',
      };
    case 'pending':
      return {
        icon: Clock,
        label: 'PENDING',
        color: 'text-white/60',
        bg: 'bg-white/10',
      };
    case 'failed':
      return {
        icon: XCircle,
        label: 'FAILED',
        color: 'text-red-400',
        bg: 'bg-red-500/20',
      };
    default:
      return {
        icon: Clock,
        label: status.toUpperCase(),
        color: 'text-white/60',
        bg: 'bg-white/10',
      };
  }
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

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
}

function formatDemographicTitle(key: string): string {
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (l) => l.toUpperCase());
}
