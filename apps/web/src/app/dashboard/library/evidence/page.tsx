'use client';

import {
  FileSearch,
  Plus,
  Search,
  Filter,
  Database,
  FileText,
  Globe,
  Link2,
  Calendar,
  CheckCircle,
  AlertCircle,
} from 'lucide-react';

// Dummy evidence source data
const dummyEvidenceSources = [
  {
    id: '1',
    name: 'Nielsen Consumer Panel',
    description: 'Consumer purchasing data from Nielsen panel surveys',
    type: 'dataset',
    status: 'connected',
    lastSync: '2 hours ago',
    records: '2.4M',
    reliability: 95,
  },
  {
    id: '2',
    name: 'Internal CRM Data',
    description: 'Customer relationship management data export',
    type: 'database',
    status: 'connected',
    lastSync: '1 day ago',
    records: '156K',
    reliability: 98,
  },
  {
    id: '3',
    name: 'Social Media Sentiment',
    description: 'Aggregated sentiment data from Twitter and Instagram',
    type: 'api',
    status: 'syncing',
    lastSync: 'In progress',
    records: '890K',
    reliability: 82,
  },
  {
    id: '4',
    name: 'Market Research Reports',
    description: 'Collection of industry market research PDFs',
    type: 'document',
    status: 'connected',
    lastSync: '1 week ago',
    records: '847',
    reliability: 91,
  },
  {
    id: '5',
    name: 'Competitor Analysis Feed',
    description: 'Real-time competitor pricing and product data',
    type: 'api',
    status: 'error',
    lastSync: 'Failed 3 days ago',
    records: '45K',
    reliability: 75,
  },
  {
    id: '6',
    name: 'Survey Responses Archive',
    description: 'Historical survey data from consumer studies',
    type: 'dataset',
    status: 'connected',
    lastSync: '5 days ago',
    records: '320K',
    reliability: 94,
  },
];

const getTypeIcon = (type: string) => {
  switch (type) {
    case 'dataset':
      return Database;
    case 'database':
      return Database;
    case 'api':
      return Globe;
    case 'document':
      return FileText;
    default:
      return Link2;
  }
};

export default function EvidenceSourcePage() {
  return (
    <div className="space-y-4 md:space-y-6">
      {/* Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 md:gap-4">
        <div className="flex items-center gap-2 md:gap-3 flex-1">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
            <input
              type="text"
              placeholder="Search sources..."
              className="w-full bg-white/5 border border-white/10 px-10 py-2 text-sm font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-cyan-500/50"
            />
          </div>
          <button className="flex items-center gap-2 px-3 py-2 text-xs font-mono text-white/60 bg-white/5 border border-white/10 hover:bg-white/10 transition-colors">
            <Filter className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Filters</span>
          </button>
        </div>
        <button className="flex items-center gap-2 px-3 md:px-4 py-2 text-xs font-mono text-black bg-cyan-400 hover:bg-cyan-300 transition-colors whitespace-nowrap">
          <Plus className="w-3.5 h-3.5" />
          <span>Add Source</span>
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
        <div className="bg-white/5 border border-white/10 p-3 md:p-4">
          <div className="text-xl md:text-2xl font-mono font-bold text-white mb-1">
            {dummyEvidenceSources.length}
          </div>
          <div className="text-[10px] md:text-xs font-mono text-white/40">Total Sources</div>
        </div>
        <div className="bg-white/5 border border-white/10 p-3 md:p-4">
          <div className="text-xl md:text-2xl font-mono font-bold text-green-400 mb-1">
            {dummyEvidenceSources.filter((s) => s.status === 'connected').length}
          </div>
          <div className="text-[10px] md:text-xs font-mono text-white/40">Connected</div>
        </div>
        <div className="bg-white/5 border border-white/10 p-3 md:p-4">
          <div className="text-xl md:text-2xl font-mono font-bold text-cyan-400 mb-1">4.8M+</div>
          <div className="text-[10px] md:text-xs font-mono text-white/40">Total Records</div>
        </div>
        <div className="bg-white/5 border border-white/10 p-3 md:p-4">
          <div className="text-xl md:text-2xl font-mono font-bold text-purple-400 mb-1">89%</div>
          <div className="text-[10px] md:text-xs font-mono text-white/40">Avg Reliability</div>
        </div>
      </div>

      {/* Evidence Sources Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-4">
        {dummyEvidenceSources.map((source) => {
          const TypeIcon = getTypeIcon(source.type);
          return (
            <div
              key={source.id}
              className="bg-white/5 border border-white/10 p-4 md:p-5 hover:border-cyan-500/30 transition-colors cursor-pointer group"
            >
              <div className="flex items-start justify-between mb-3 gap-2">
                <div className="flex items-center gap-2 md:gap-3 min-w-0">
                  <div
                    className={`w-8 h-8 md:w-10 md:h-10 flex items-center justify-center flex-shrink-0 ${
                      source.type === 'api'
                        ? 'bg-gradient-to-br from-blue-500 to-cyan-500'
                        : source.type === 'database'
                          ? 'bg-gradient-to-br from-green-500 to-emerald-500'
                          : source.type === 'document'
                            ? 'bg-gradient-to-br from-yellow-500 to-orange-500'
                            : 'bg-gradient-to-br from-purple-500 to-pink-500'
                    }`}
                  >
                    <TypeIcon className="w-4 h-4 md:w-5 md:h-5 text-white" />
                  </div>
                  <div className="min-w-0">
                    <h3 className="text-xs md:text-sm font-mono font-bold text-white group-hover:text-cyan-400 transition-colors truncate">
                      {source.name}
                    </h3>
                    <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                      <span className="text-[9px] md:text-[10px] font-mono text-white/30 uppercase">
                        {source.type}
                      </span>
                      <span
                        className={`inline-flex items-center gap-1 text-[9px] md:text-[10px] font-mono px-1.5 py-0.5 ${
                          source.status === 'connected'
                            ? 'text-green-400 bg-green-400/10'
                            : source.status === 'syncing'
                              ? 'text-yellow-400 bg-yellow-400/10'
                              : 'text-red-400 bg-red-400/10'
                        }`}
                      >
                        {source.status === 'connected' ? (
                          <CheckCircle className="w-2.5 h-2.5" />
                        ) : source.status === 'error' ? (
                          <AlertCircle className="w-2.5 h-2.5" />
                        ) : (
                          <div className="w-2.5 h-2.5 border border-current border-t-transparent rounded-full animate-spin" />
                        )}
                        {source.status}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="text-right flex-shrink-0">
                  <div className="text-xs md:text-sm font-mono font-bold text-cyan-400">{source.records}</div>
                  <div className="text-[9px] md:text-[10px] font-mono text-white/30">records</div>
                </div>
              </div>
              <p className="text-[10px] md:text-xs font-mono text-white/50 mb-3 md:mb-4 line-clamp-2">{source.description}</p>
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 text-[9px] md:text-[10px] font-mono">
                <div className="flex items-center gap-1.5 text-white/30">
                  <Calendar className="w-3 h-3" />
                  <span>{source.lastSync}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="text-white/30">Reliability:</span>
                  <div className="w-12 md:w-16 h-1.5 bg-white/10 overflow-hidden">
                    <div
                      className={`h-full ${
                        source.reliability >= 90
                          ? 'bg-green-500'
                          : source.reliability >= 80
                            ? 'bg-yellow-500'
                            : 'bg-red-500'
                      }`}
                      style={{ width: `${source.reliability}%` }}
                    />
                  </div>
                  <span className="text-white/50">{source.reliability}%</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Placeholder Message */}
      <div className="text-center py-8 border border-dashed border-white/10">
        <FileSearch className="w-8 h-8 text-white/20 mx-auto mb-3" />
        <p className="text-sm font-mono text-white/40 mb-2">
          This is a preview of the Evidence Sources Library
        </p>
        <p className="text-xs font-mono text-white/30">
          Full functionality coming soon. Connect and manage data sources for simulation evidence.
        </p>
      </div>
    </div>
  );
}
