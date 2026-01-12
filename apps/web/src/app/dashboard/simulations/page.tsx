'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  Plus,
  Play,
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
} from 'lucide-react';
import { useSimulations, useCancelSimulation } from '@/hooks/useApi';
import { SimulationRun } from '@/lib/api';
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

export default function SimulationsPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const { data: simulations, isLoading, error, refetch } = useSimulations({
    status: statusFilter || undefined
  });

  const filteredSimulations = simulations?.filter(sim =>
    !searchQuery ||
    sim.scenario_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
    sim.model_used.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="min-h-screen bg-black p-4 md:p-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6 md:mb-8">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Play className="w-3.5 h-3.5 md:w-4 md:h-4 text-white/60" />
            <span className="text-[10px] md:text-xs font-mono text-white/40 uppercase tracking-wider">Simulation Module</span>
          </div>
          <h1 className="text-lg md:text-xl font-mono font-bold text-white">Simulations</h1>
          <p className="text-xs md:text-sm font-mono text-white/50 mt-1">
            Run and manage AI agent simulations
          </p>
        </div>
        <Link href="/dashboard/simulations/new">
          <Button size="sm" className="w-full sm:w-auto font-mono text-[10px] md:text-xs">
            <Plus className="w-3 h-3 mr-1.5 md:mr-2" />
            <span className="hidden sm:inline">NEW SIMULATION</span>
            <span className="sm:hidden">NEW</span>
          </Button>
        </Link>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2 md:gap-3 mb-4 md:mb-6">
        <div className="relative flex-1 min-w-[120px] sm:max-w-xs">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-white/30" />
          <input
            type="text"
            placeholder="Search..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-7 pr-3 py-1.5 bg-white/5 border border-white/10 text-[10px] md:text-xs font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-white/30"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="flex-1 sm:flex-none px-2.5 md:px-3 py-1.5 bg-white/5 border border-white/10 text-[10px] md:text-xs font-mono text-white appearance-none focus:outline-none focus:border-white/30"
        >
          <option value="">All Status</option>
          <option value="pending">Pending</option>
          <option value="running">Running</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
          <option value="cancelled">Cancelled</option>
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
          <p className="text-xs md:text-sm font-mono text-red-400">Failed to load simulations</p>
          <Button
            variant="outline"
            onClick={() => refetch()}
            className="mt-2 font-mono text-[10px] md:text-xs border-white/20 text-white/60 hover:bg-white/5"
          >
            RETRY
          </Button>
        </div>
      )}

      {/* Simulations List */}
      {!isLoading && !error && (
        <>
          {(!filteredSimulations || filteredSimulations.length === 0) ? (
            <div className="bg-white/5 border border-white/10">
              <div className="p-8 md:p-12 text-center">
                <div className="w-10 h-10 md:w-12 md:h-12 bg-white/5 flex items-center justify-center mx-auto mb-3 md:mb-4">
                  <Play className="w-4 h-4 md:w-5 md:h-5 text-white/30" />
                </div>
                <p className="text-xs md:text-sm font-mono text-white/60 mb-1">No simulations</p>
                <p className="text-[10px] md:text-xs font-mono text-white/30 mb-3 md:mb-4">
                  Create a project and run your first simulation
                </p>
                <Link href="/dashboard/simulations/new">
                  <Button size="sm" className="font-mono text-[10px] md:text-xs">
                    NEW SIMULATION
                  </Button>
                </Link>
              </div>
            </div>
          ) : (
            <>
              {/* Mobile Card View */}
              <div className="md:hidden space-y-2">
                {filteredSimulations.map((simulation) => (
                  <SimulationCard
                    key={simulation.id}
                    simulation={simulation}
                    onUpdate={() => refetch()}
                  />
                ))}
              </div>

              {/* Desktop Table View */}
              <div className="hidden md:block bg-white/5 border border-white/10 overflow-x-auto">
                <table className="w-full min-w-[600px]">
                  <thead className="border-b border-white/10">
                    <tr>
                      <th className="text-left px-4 py-3 text-[10px] font-mono text-white/40 uppercase tracking-wider">
                        Status
                      </th>
                      <th className="text-left px-4 py-3 text-[10px] font-mono text-white/40 uppercase tracking-wider">
                        Model
                      </th>
                      <th className="text-left px-4 py-3 text-[10px] font-mono text-white/40 uppercase tracking-wider">
                        Agents
                      </th>
                      <th className="text-left px-4 py-3 text-[10px] font-mono text-white/40 uppercase tracking-wider">
                        Progress
                      </th>
                      <th className="text-left px-4 py-3 text-[10px] font-mono text-white/40 uppercase tracking-wider">
                        Created
                      </th>
                      <th className="text-right px-4 py-3 text-[10px] font-mono text-white/40 uppercase tracking-wider">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {filteredSimulations.map((simulation) => (
                      <SimulationRow
                        key={simulation.id}
                        simulation={simulation}
                        onUpdate={() => refetch()}
                      />
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </>
      )}

      {/* Footer Status */}
      <div className="mt-6 md:mt-8 pt-3 md:pt-4 border-t border-white/5">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-1">
            <Terminal className="w-3 h-3" />
            <span className="hidden sm:inline">SIMULATION MODULE</span>
            <span className="sm:hidden">SIMULATIONS</span>
          </div>
          <span>AGENTVERSE v1.0.0</span>
        </div>
      </div>
    </div>
  );
}

function SimulationRow({ simulation, onUpdate }: { simulation: SimulationRun; onUpdate: () => void }) {
  const [showMenu, setShowMenu] = useState(false);
  const cancelSimulation = useCancelSimulation();

  const status = statusColors[simulation.status] || statusColors.pending;
  const progress = simulation.progress || 0;

  const handleCancel = async () => {
    if (confirm('Cancel this simulation?')) {
      try {
        await cancelSimulation.mutateAsync(simulation.id);
        onUpdate();
      } catch {
        // Cancel failed - mutation error is handled by react-query
      }
    }
    setShowMenu(false);
  };

  return (
    <tr className="hover:bg-white/5 transition-colors">
      <td className="px-4 py-3">
        <span className={cn('inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-mono uppercase', status.className)}>
          {status.icon}
          {status.label}
        </span>
      </td>
      <td className="px-4 py-3 text-xs font-mono text-white/60">
        {simulation.model_used}
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-1 text-xs font-mono text-white/60">
          <Users className="w-3 h-3" />
          {simulation.agent_count}
        </div>
      </td>
      <td className="px-4 py-3">
        <div className="w-full max-w-[100px]">
          <div className="flex items-center gap-2">
            <div className="flex-1 bg-white/10 h-1">
              <div
                className={cn(
                  'h-1 transition-all',
                  progress === 100 ? 'bg-green-500' : 'bg-white/60'
                )}
                style={{ width: `${progress}%` }}
              />
            </div>
            <span className="text-[10px] font-mono text-white/40 w-6">{progress}%</span>
          </div>
        </div>
      </td>
      <td className="px-4 py-3 text-[10px] font-mono text-white/30">
        {new Date(simulation.created_at).toLocaleDateString()}
      </td>
      <td className="px-4 py-3 text-right">
        <div className="relative inline-block">
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
                  href={`/dashboard/results/${simulation.id}`}
                  className="flex items-center gap-2 px-3 py-1.5 text-xs font-mono text-white/60 hover:bg-white/10"
                  onClick={() => setShowMenu(false)}
                >
                  <Eye className="w-3 h-3" />
                  Results
                </Link>
                {simulation.status === 'running' && (
                  <button
                    onClick={handleCancel}
                    disabled={cancelSimulation.isPending}
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
      </td>
    </tr>
  );
}

function SimulationCard({ simulation, onUpdate }: { simulation: SimulationRun; onUpdate: () => void }) {
  const [showMenu, setShowMenu] = useState(false);
  const cancelSimulation = useCancelSimulation();

  const status = statusColors[simulation.status] || statusColors.pending;
  const progress = simulation.progress || 0;

  const handleCancel = async () => {
    if (confirm('Cancel this simulation?')) {
      try {
        await cancelSimulation.mutateAsync(simulation.id);
        onUpdate();
      } catch {
        // Cancel failed - mutation error is handled by react-query
      }
    }
    setShowMenu(false);
  };

  return (
    <div className="bg-white/5 border border-white/10 p-3">
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className={cn('inline-flex items-center gap-1 px-1 py-0.5 text-[9px] font-mono uppercase flex-shrink-0', status.className)}>
            {status.icon}
            {status.label}
          </span>
          <span className="text-[10px] font-mono text-white/60 truncate">{simulation.model_used}</span>
        </div>
        <div className="relative">
          <button
            onClick={() => setShowMenu(!showMenu)}
            className="p-1 hover:bg-white/10 transition-colors"
          >
            <MoreVertical className="w-3 h-3 text-white/40" />
          </button>
          {showMenu && (
            <>
              <div
                className="fixed inset-0 z-10"
                onClick={() => setShowMenu(false)}
              />
              <div className="absolute right-0 mt-1 w-28 bg-black border border-white/20 py-1 z-20">
                <Link
                  href={`/dashboard/results/${simulation.id}`}
                  className="flex items-center gap-2 px-2 py-1.5 text-[10px] font-mono text-white/60 hover:bg-white/10"
                  onClick={() => setShowMenu(false)}
                >
                  <Eye className="w-2.5 h-2.5" />
                  Results
                </Link>
                {simulation.status === 'running' && (
                  <button
                    onClick={handleCancel}
                    disabled={cancelSimulation.isPending}
                    className="flex items-center gap-2 w-full px-2 py-1.5 text-[10px] font-mono text-red-400 hover:bg-white/10 disabled:opacity-50"
                  >
                    <XCircle className="w-2.5 h-2.5" />
                    Cancel
                  </button>
                )}
              </div>
            </>
          )}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2 text-[9px] font-mono">
        <div>
          <span className="text-white/30 uppercase">Agents</span>
          <div className="flex items-center gap-1 text-white/60 mt-0.5">
            <Users className="w-2.5 h-2.5" />
            {simulation.agent_count}
          </div>
        </div>
        <div>
          <span className="text-white/30 uppercase">Progress</span>
          <div className="flex items-center gap-1 mt-0.5">
            <div className="flex-1 bg-white/10 h-1">
              <div
                className={cn(
                  'h-1 transition-all',
                  progress === 100 ? 'bg-green-500' : 'bg-white/60'
                )}
                style={{ width: `${progress}%` }}
              />
            </div>
            <span className="text-white/40">{progress}%</span>
          </div>
        </div>
        <div>
          <span className="text-white/30 uppercase">Created</span>
          <p className="text-white/40 mt-0.5">{new Date(simulation.created_at).toLocaleDateString()}</p>
        </div>
      </div>
    </div>
  );
}
