'use client';

/**
 * Exports Page Component
 * Reference: Interaction_design.md §5.19
 *
 * Export node summaries, compare results, reliability reports, telemetry snapshots.
 */

import { useState, useMemo } from 'react';
import {
  Download,
  FileJson,
  FileSpreadsheet,
  Database,
  Link2,
  Trash2,
  Loader2,
  AlertCircle,
  CheckCircle,
  Clock,
  FileText,
  GitCompare,
  Shield,
  Activity,
  Lock,
  Users,
  Globe,
  RefreshCw,
  Copy,
  Eye,
  EyeOff,
  Info,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  useExports,
  useExport,
  useCreateExport,
  useDeleteExport,
  useExportDownloadUrl,
  useExportShareUrl,
} from '@/hooks/useApi';
import {
  ExportType,
  ExportFormat,
  ExportPrivacy,
  ExportRequest,
  ExportJob,
  ExportListItem,
  SensitivityType,
} from '@/lib/api';
import { cn } from '@/lib/utils';

// Sensitivity type configurations for redaction controls
const SENSITIVITY_TYPES: {
  id: SensitivityType;
  label: string;
  description: string;
}[] = [
  { id: 'pii', label: 'PII', description: 'Names, emails, identifiers' },
  { id: 'financial', label: 'Financial', description: 'Income, bank accounts' },
  { id: 'health', label: 'Health', description: 'Medical information' },
  { id: 'contact', label: 'Contact', description: 'Phone, address' },
  { id: 'location', label: 'Location', description: 'Geographic data' },
  { id: 'behavioral', label: 'Behavioral', description: 'Detailed patterns' },
  { id: 'demographic', label: 'Demographic', description: 'Age, gender, etc.' },
  { id: 'prediction', label: 'Predictions', description: 'Model outputs' },
  { id: 'confidence', label: 'Confidence', description: 'Score values' },
  { id: 'internal', label: 'Internal', description: 'System data' },
];

interface ExportsPageProps {
  projectId: string;
}

// Export type configurations
const EXPORT_TYPES: {
  id: ExportType;
  label: string;
  description: string;
  icon: typeof FileText;
}[] = [
  {
    id: 'node_summary',
    label: 'Node Summary',
    description: 'Export summary of selected nodes including outcomes and probabilities',
    icon: FileText,
  },
  {
    id: 'compare_pack',
    label: 'Compare Pack',
    description: 'Export comparison data between multiple nodes for analysis',
    icon: GitCompare,
  },
  {
    id: 'reliability_report',
    label: 'Reliability Report',
    description: 'Export calibration scores, stability metrics, and confidence intervals',
    icon: Shield,
  },
  {
    id: 'telemetry_snapshot',
    label: 'Telemetry Snapshot',
    description: 'Export agent state changes and world snapshots (limited)',
    icon: Activity,
  },
];

// Format configurations
const EXPORT_FORMATS: {
  id: ExportFormat;
  label: string;
  description: string;
  icon: typeof FileJson;
}[] = [
  { id: 'json', label: 'JSON', description: 'Structured data format', icon: FileJson },
  { id: 'csv', label: 'CSV', description: 'Spreadsheet compatible', icon: FileSpreadsheet },
  { id: 'parquet', label: 'Parquet', description: 'Columnar format for analytics', icon: Database },
];

// Privacy configurations
const PRIVACY_OPTIONS: {
  id: ExportPrivacy;
  label: string;
  description: string;
  icon: typeof Lock;
}[] = [
  { id: 'private', label: 'Private', description: 'Only you can access', icon: Lock },
  { id: 'team', label: 'Team', description: 'Shared with team members', icon: Users },
  { id: 'public', label: 'Public', description: 'Anyone with link can access', icon: Globe },
];

function getStatusIcon(status: string) {
  switch (status) {
    case 'completed':
      return <CheckCircle className="h-3.5 w-3.5 md:h-4 md:w-4 text-green-400 flex-shrink-0" />;
    case 'processing':
    case 'pending':
      return <Loader2 className="h-3.5 w-3.5 md:h-4 md:w-4 text-yellow-400 animate-spin flex-shrink-0" />;
    case 'failed':
      return <AlertCircle className="h-3.5 w-3.5 md:h-4 md:w-4 text-red-400 flex-shrink-0" />;
    default:
      return <Clock className="h-3.5 w-3.5 md:h-4 md:w-4 text-white/40 flex-shrink-0" />;
  }
}

function formatFileSize(bytes?: number): string {
  if (!bytes) return '-';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function ExportJobRow({
  item,
  onDownload,
  onShare,
  onDelete,
  isDownloading,
  isSharing,
}: {
  item: ExportListItem;
  onDownload: (id: string) => void;
  onShare: (id: string) => void;
  onDelete: (id: string) => void;
  isDownloading: boolean;
  isSharing: boolean;
}) {
  const typeConfig = EXPORT_TYPES.find((t) => t.id === item.export_type);
  const TypeIcon = typeConfig?.icon ?? FileText;

  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between p-2.5 md:p-3 gap-2 sm:gap-3 border border-white/10 bg-white/5 hover:border-white/20 transition-colors">
      <div className="flex items-start sm:items-center gap-2 md:gap-3 min-w-0">
        {getStatusIcon(item.status)}
        <TypeIcon className="h-3.5 w-3.5 md:h-4 md:w-4 text-white/40 flex-shrink-0 mt-0.5 sm:mt-0" />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5 md:gap-2">
            <span className="text-xs md:text-sm text-white/90 truncate">{item.label ?? typeConfig?.label}</span>
            <span className="text-[10px] md:text-xs text-white/40 uppercase">{item.format}</span>
            {item.redacted_field_count != null && item.redacted_field_count > 0 && (
              <span className="text-[10px] md:text-xs px-1 md:px-1.5 py-0.5 bg-purple-500/20 text-purple-300 border border-purple-500/30 flex items-center gap-0.5 md:gap-1">
                <EyeOff className="h-2.5 w-2.5 md:h-3 md:w-3" />
                <span className="hidden sm:inline">{item.redacted_field_count} redacted</span>
                <span className="sm:hidden">{item.redacted_field_count}</span>
              </span>
            )}
          </div>
          <div className="text-[10px] md:text-xs text-white/40">
            {new Date(item.created_at).toLocaleString()} • {formatFileSize(item.file_size_bytes)}
          </div>
        </div>
      </div>
      <div className="flex items-center gap-1.5 md:gap-2 self-end sm:self-auto flex-shrink-0">
        {item.status === 'completed' && (
          <>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onDownload(item.export_id)}
              disabled={isDownloading}
              className="text-cyan-400 hover:text-cyan-300 h-7 w-7 md:h-8 md:w-8 p-0"
            >
              {isDownloading ? (
                <Loader2 className="h-3.5 w-3.5 md:h-4 md:w-4 animate-spin" />
              ) : (
                <Download className="h-3.5 w-3.5 md:h-4 md:w-4" />
              )}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onShare(item.export_id)}
              disabled={isSharing}
              className="text-purple-400 hover:text-purple-300 h-7 w-7 md:h-8 md:w-8 p-0"
            >
              {isSharing ? <Loader2 className="h-3.5 w-3.5 md:h-4 md:w-4 animate-spin" /> : <Link2 className="h-3.5 w-3.5 md:h-4 md:w-4" />}
            </Button>
          </>
        )}
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onDelete(item.export_id)}
          className="text-red-400 hover:text-red-300 h-7 w-7 md:h-8 md:w-8 p-0"
        >
          <Trash2 className="h-3.5 w-3.5 md:h-4 md:w-4" />
        </Button>
      </div>
    </div>
  );
}

export function ExportsPage({ projectId }: ExportsPageProps) {
  // Form state
  const [selectedType, setSelectedType] = useState<ExportType>('node_summary');
  const [selectedFormat, setSelectedFormat] = useState<ExportFormat>('json');
  const [selectedPrivacy, setSelectedPrivacy] = useState<ExportPrivacy>('private');
  const [exportLabel, setExportLabel] = useState('');
  const [includeAgentDetails, setIncludeAgentDetails] = useState(false);

  // Redaction state
  const [showRedactionOptions, setShowRedactionOptions] = useState(false);
  const [enableRedaction, setEnableRedaction] = useState(true);
  const [selectedSensitivityTypes, setSelectedSensitivityTypes] = useState<Set<SensitivityType>>(
    new Set(['pii', 'financial', 'health', 'contact'])
  );
  const [includeRedactionSummary, setIncludeRedactionSummary] = useState(true);
  const [includePii, setIncludePii] = useState(false);
  const [includeRaw, setIncludeRaw] = useState(false);

  // Track which export is being processed
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [sharingId, setSharingId] = useState<string | null>(null);
  const [copiedUrl, setCopiedUrl] = useState<string | null>(null);

  // Toggle sensitivity type selection
  const toggleSensitivityType = (type: SensitivityType) => {
    const newSet = new Set(selectedSensitivityTypes);
    if (newSet.has(type)) {
      newSet.delete(type);
    } else {
      newSet.add(type);
    }
    setSelectedSensitivityTypes(newSet);
  };

  // API hooks
  const { data: exports, isLoading, refetch } = useExports({ project_id: projectId });
  const createExport = useCreateExport();
  const deleteExport = useDeleteExport();
  const getDownloadUrl = useExportDownloadUrl();
  const getShareUrl = useExportShareUrl();

  // Handle create export
  const handleCreateExport = async () => {
    const request: ExportRequest = {
      project_id: projectId,
      export_type: selectedType,
      format: selectedFormat,
      privacy: selectedPrivacy,
      include_agent_details: includeAgentDetails,
      label: exportLabel || undefined,
      // Redaction options
      enable_redaction: enableRedaction,
      redact_types: enableRedaction ? Array.from(selectedSensitivityTypes) : undefined,
      include_redaction_summary: includeRedactionSummary,
      include_pii: includePii,
      include_raw: includeRaw && selectedType === 'telemetry_snapshot',
    };

    try {
      await createExport.mutateAsync(request);
      setExportLabel('');
    } catch {
      // Error handled by mutation
    }
  };

  // Handle download
  const handleDownload = async (exportId: string) => {
    setDownloadingId(exportId);
    try {
      const response = await getDownloadUrl.mutateAsync(exportId);
      window.open(response.download_url, '_blank');
    } finally {
      setDownloadingId(null);
    }
  };

  // Handle share
  const handleShare = async (exportId: string) => {
    setSharingId(exportId);
    try {
      const response = await getShareUrl.mutateAsync({ exportId });
      await navigator.clipboard.writeText(response.share_url);
      setCopiedUrl(exportId);
      setTimeout(() => setCopiedUrl(null), 2000);
    } finally {
      setSharingId(null);
    }
  };

  // Handle delete
  const handleDelete = async (exportId: string) => {
    if (confirm('Delete this export?')) {
      await deleteExport.mutateAsync(exportId);
    }
  };

  // Group exports by status
  const groupedExports = useMemo(() => {
    if (!exports) return { active: [], completed: [], failed: [] };
    return {
      active: exports.filter((e) => e.status === 'pending' || e.status === 'processing'),
      completed: exports.filter((e) => e.status === 'completed'),
      failed: exports.filter((e) => e.status === 'failed'),
    };
  }, [exports]);

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex-none border-b border-white/10 bg-black/40 p-3 md:p-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center gap-2 md:gap-3">
            <Download className="h-4 w-4 md:h-5 md:w-5 text-cyan-400 flex-shrink-0" />
            <h1 className="text-base md:text-lg font-semibold">Exports</h1>
            <span className="hidden sm:inline text-xs md:text-sm text-white/60">
              Export simulation data, telemetry, and results
            </span>
          </div>
          <Button variant="ghost" size="sm" onClick={() => refetch()} className="text-xs self-end sm:self-auto">
            <RefreshCw className="h-3 w-3 md:h-4 md:w-4 mr-1 md:mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto p-3 md:p-6">
        <div className="max-w-4xl mx-auto space-y-6 md:space-y-8">
          {/* Create Export Section */}
          <div className="border border-white/10 bg-white/5 p-4 md:p-6">
            <h2 className="text-base md:text-lg font-medium mb-3 md:mb-4">Generate New Export</h2>

            {/* Export Type */}
            <div className="mb-4 md:mb-6">
              <label className="text-xs md:text-sm text-white/60 mb-2 block">Export Type</label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 md:gap-3">
                {EXPORT_TYPES.map((type) => (
                  <button
                    key={type.id}
                    onClick={() => setSelectedType(type.id)}
                    className={cn(
                      'p-2.5 md:p-3 border text-left transition-colors',
                      selectedType === type.id
                        ? 'border-cyan-500/50 bg-cyan-500/10'
                        : 'border-white/10 hover:border-white/20'
                    )}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <type.icon
                        className={cn(
                          'h-3.5 w-3.5 md:h-4 md:w-4',
                          selectedType === type.id ? 'text-cyan-400' : 'text-white/40'
                        )}
                      />
                      <span
                        className={cn(
                          'text-xs md:text-sm font-medium',
                          selectedType === type.id ? 'text-cyan-300' : 'text-white/80'
                        )}
                      >
                        {type.label}
                      </span>
                    </div>
                    <p className="text-[10px] md:text-xs text-white/40 line-clamp-2">{type.description}</p>
                  </button>
                ))}
              </div>
            </div>

            {/* Format and Privacy */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 md:gap-6 mb-4 md:mb-6">
              {/* Format */}
              <div>
                <label className="text-xs md:text-sm text-white/60 mb-2 block">Format</label>
                <div className="flex gap-1.5 md:gap-2">
                  {EXPORT_FORMATS.map((format) => (
                    <button
                      key={format.id}
                      onClick={() => setSelectedFormat(format.id)}
                      className={cn(
                        'flex-1 py-1.5 md:py-2 px-2 md:px-3 border flex items-center justify-center gap-1 md:gap-2 transition-colors',
                        selectedFormat === format.id
                          ? 'border-cyan-500/50 bg-cyan-500/10 text-cyan-300'
                          : 'border-white/10 text-white/60 hover:border-white/20'
                      )}
                    >
                      <format.icon className="h-3 w-3 md:h-4 md:w-4" />
                      <span className="text-[10px] md:text-sm">{format.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Privacy */}
              <div>
                <label className="text-xs md:text-sm text-white/60 mb-2 block">Privacy</label>
                <div className="flex gap-1.5 md:gap-2">
                  {PRIVACY_OPTIONS.map((privacy) => (
                    <button
                      key={privacy.id}
                      onClick={() => setSelectedPrivacy(privacy.id)}
                      className={cn(
                        'flex-1 py-1.5 md:py-2 px-2 md:px-3 border flex items-center justify-center gap-1 md:gap-2 transition-colors',
                        selectedPrivacy === privacy.id
                          ? 'border-purple-500/50 bg-purple-500/10 text-purple-300'
                          : 'border-white/10 text-white/60 hover:border-white/20'
                      )}
                    >
                      <privacy.icon className="h-3 w-3 md:h-4 md:w-4" />
                      <span className="text-[10px] md:text-sm">{privacy.label}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Optional Settings */}
            <div className="mb-4 md:mb-6 space-y-3 md:space-y-4">
              {/* Label */}
              <div>
                <label className="text-xs md:text-sm text-white/60 mb-1.5 md:mb-2 block">Label (optional)</label>
                <input
                  type="text"
                  value={exportLabel}
                  onChange={(e) => setExportLabel(e.target.value)}
                  placeholder="e.g., Q4 Analysis Export"
                  className="w-full px-2.5 md:px-3 py-1.5 md:py-2 text-sm bg-white/5 border border-white/10 text-white/90 placeholder:text-white/30"
                />
              </div>

              {/* Include agent details (for telemetry) */}
              {selectedType === 'telemetry_snapshot' && (
                <label className="flex items-start sm:items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={includeAgentDetails}
                    onChange={(e) => setIncludeAgentDetails(e.target.checked)}
                    className="w-4 h-4 bg-white/10 border-white/20 mt-0.5 sm:mt-0 flex-shrink-0"
                  />
                  <span className="text-xs md:text-sm text-white/80">Include detailed agent states</span>
                  <span className="text-[10px] md:text-xs text-white/40">(larger file size)</span>
                </label>
              )}
            </div>

            {/* Data Redaction Controls (project.md §11 Phase 9) */}
            <div className="mb-4 md:mb-6 border border-white/10 bg-white/5">
              <button
                type="button"
                onClick={() => setShowRedactionOptions(!showRedactionOptions)}
                className="w-full px-3 md:px-4 py-2.5 md:py-3 flex items-center justify-between text-left hover:bg-white/5 transition-colors"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <Shield className="h-3.5 w-3.5 md:h-4 md:w-4 text-purple-400 flex-shrink-0" />
                  <span className="text-sm md:text-base font-medium truncate">Data Redaction</span>
                  {enableRedaction && (
                    <span className="text-[10px] md:text-xs px-1.5 md:px-2 py-0.5 bg-purple-500/20 text-purple-300 border border-purple-500/30 whitespace-nowrap">
                      {selectedSensitivityTypes.size} protected
                    </span>
                  )}
                </div>
                {showRedactionOptions ? (
                  <ChevronUp className="h-4 w-4 text-white/40 flex-shrink-0" />
                ) : (
                  <ChevronDown className="h-4 w-4 text-white/40 flex-shrink-0" />
                )}
              </button>

              {showRedactionOptions && (
                <div className="px-3 md:px-4 pb-3 md:pb-4 pt-2 border-t border-white/10 space-y-3 md:space-y-4">
                  {/* Enable Redaction Toggle */}
                  <label className="flex items-center justify-between cursor-pointer gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                      {enableRedaction ? (
                        <EyeOff className="h-3.5 w-3.5 md:h-4 md:w-4 text-purple-400 flex-shrink-0" />
                      ) : (
                        <Eye className="h-3.5 w-3.5 md:h-4 md:w-4 text-white/40 flex-shrink-0" />
                      )}
                      <span className="text-xs md:text-sm text-white/80">Enable automatic redaction</span>
                    </div>
                    <input
                      type="checkbox"
                      checked={enableRedaction}
                      onChange={(e) => setEnableRedaction(e.target.checked)}
                      className="w-4 h-4 bg-white/10 border-white/20 flex-shrink-0"
                    />
                  </label>

                  {enableRedaction && (
                    <>
                      {/* Sensitivity Types Grid */}
                      <div>
                        <label className="text-[10px] md:text-xs text-white/40 mb-1.5 md:mb-2 block">
                          Sensitivity types to redact
                        </label>
                        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-1.5 md:gap-2">
                          {SENSITIVITY_TYPES.map((type) => (
                            <button
                              key={type.id}
                              type="button"
                              onClick={() => toggleSensitivityType(type.id)}
                              className={cn(
                                'px-1.5 md:px-2 py-1 md:py-1.5 text-[10px] md:text-xs border transition-colors text-left',
                                selectedSensitivityTypes.has(type.id)
                                  ? 'border-purple-500/50 bg-purple-500/10 text-purple-300'
                                  : 'border-white/10 text-white/50 hover:border-white/20'
                              )}
                              title={type.description}
                            >
                              {type.label}
                            </button>
                          ))}
                        </div>
                      </div>

                      {/* Include Redaction Summary */}
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={includeRedactionSummary}
                          onChange={(e) => setIncludeRedactionSummary(e.target.checked)}
                          className="w-4 h-4 bg-white/10 border-white/20 flex-shrink-0"
                        />
                        <span className="text-xs md:text-sm text-white/80">Include redaction summary</span>
                        <Info className="h-3 w-3 text-white/30 flex-shrink-0" />
                      </label>
                    </>
                  )}

                  {/* Advanced: Include PII (Admin Only) */}
                  <div className="pt-2 md:pt-3 border-t border-white/10">
                    <label className="flex items-start sm:items-center justify-between cursor-pointer gap-2">
                      <div className="flex items-start sm:items-center gap-2 flex-wrap min-w-0">
                        <AlertCircle className="h-3.5 w-3.5 md:h-4 md:w-4 text-yellow-400 flex-shrink-0 mt-0.5 sm:mt-0" />
                        <span className="text-xs md:text-sm text-white/80">Include PII without redaction</span>
                        <span className="text-[10px] md:text-xs px-1 md:px-1.5 py-0.5 bg-yellow-500/20 text-yellow-300 border border-yellow-500/30">
                          Admin
                        </span>
                      </div>
                      <input
                        type="checkbox"
                        checked={includePii}
                        onChange={(e) => setIncludePii(e.target.checked)}
                        className="w-4 h-4 bg-white/10 border-white/20 flex-shrink-0"
                      />
                    </label>
                    {includePii && (
                      <div className="mt-2 ml-5 md:ml-6 text-[10px] md:text-xs text-yellow-400/80 flex items-start gap-1">
                        <AlertCircle className="h-3 w-3 mt-0.5 flex-shrink-0" />
                        <span>
                          Warning: Exported data will contain personally identifiable information.
                          Ensure compliance with data protection regulations.
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Include Raw Telemetry (Telemetry exports only) */}
                  {selectedType === 'telemetry_snapshot' && (
                    <label className="flex items-start sm:items-center justify-between cursor-pointer gap-2">
                      <div className="flex items-start sm:items-center gap-2 flex-wrap min-w-0">
                        <Activity className="h-3.5 w-3.5 md:h-4 md:w-4 text-cyan-400 flex-shrink-0 mt-0.5 sm:mt-0" />
                        <span className="text-xs md:text-sm text-white/80">Include raw telemetry data</span>
                        <span className="text-[10px] md:text-xs px-1 md:px-1.5 py-0.5 bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                          Permission
                        </span>
                      </div>
                      <input
                        type="checkbox"
                        checked={includeRaw}
                        onChange={(e) => setIncludeRaw(e.target.checked)}
                        className="w-4 h-4 bg-white/10 border-white/20 flex-shrink-0"
                      />
                    </label>
                  )}
                </div>
              )}
            </div>

            {/* Generate Button */}
            <Button
              className="w-full text-xs md:text-sm"
              onClick={handleCreateExport}
              disabled={createExport.isPending}
            >
              {createExport.isPending ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 md:h-4 md:w-4 mr-1.5 md:mr-2 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Download className="h-3.5 w-3.5 md:h-4 md:w-4 mr-1.5 md:mr-2" />
                  Generate Export
                </>
              )}
            </Button>

            {createExport.isError && (
              <div className="mt-2 md:mt-3 flex items-center gap-1.5 md:gap-2 text-red-400 text-xs md:text-sm">
                <AlertCircle className="h-3.5 w-3.5 md:h-4 md:w-4 flex-shrink-0" />
                <span>Failed to create export. Please try again.</span>
              </div>
            )}
          </div>

          {/* Export History */}
          <div>
            <h2 className="text-base md:text-lg font-medium mb-3 md:mb-4">Export History</h2>

            {isLoading ? (
              <div className="flex items-center justify-center py-8 md:py-12">
                <Loader2 className="h-5 w-5 md:h-6 md:w-6 animate-spin text-cyan-400" />
              </div>
            ) : !exports?.length ? (
              <div className="text-center py-8 md:py-12 border border-white/10 bg-white/5">
                <Download className="h-8 w-8 md:h-10 md:w-10 mx-auto mb-2 md:mb-3 text-white/20" />
                <p className="text-sm md:text-base text-white/60">No exports yet</p>
                <p className="text-xs md:text-sm text-white/40">
                  Create your first export using the form above
                </p>
              </div>
            ) : (
              <div className="space-y-4 md:space-y-6">
                {/* Active exports */}
                {groupedExports.active.length > 0 && (
                  <div>
                    <h3 className="text-xs md:text-sm text-white/40 mb-1.5 md:mb-2 flex items-center gap-1.5 md:gap-2">
                      <Loader2 className="h-2.5 w-2.5 md:h-3 md:w-3 animate-spin" />
                      Processing
                    </h3>
                    <div className="space-y-1.5 md:space-y-2">
                      {groupedExports.active.map((item) => (
                        <ExportJobRow
                          key={item.export_id}
                          item={item}
                          onDownload={handleDownload}
                          onShare={handleShare}
                          onDelete={handleDelete}
                          isDownloading={downloadingId === item.export_id}
                          isSharing={sharingId === item.export_id}
                        />
                      ))}
                    </div>
                  </div>
                )}

                {/* Completed exports */}
                {groupedExports.completed.length > 0 && (
                  <div>
                    <h3 className="text-xs md:text-sm text-white/40 mb-1.5 md:mb-2 flex items-center gap-1.5 md:gap-2">
                      <CheckCircle className="h-2.5 w-2.5 md:h-3 md:w-3 text-green-400" />
                      Completed ({groupedExports.completed.length})
                    </h3>
                    <div className="space-y-1.5 md:space-y-2">
                      {groupedExports.completed.map((item) => (
                        <ExportJobRow
                          key={item.export_id}
                          item={item}
                          onDownload={handleDownload}
                          onShare={handleShare}
                          onDelete={handleDelete}
                          isDownloading={downloadingId === item.export_id}
                          isSharing={sharingId === item.export_id}
                        />
                      ))}
                    </div>
                  </div>
                )}

                {/* Failed exports */}
                {groupedExports.failed.length > 0 && (
                  <div>
                    <h3 className="text-xs md:text-sm text-white/40 mb-1.5 md:mb-2 flex items-center gap-1.5 md:gap-2">
                      <AlertCircle className="h-2.5 w-2.5 md:h-3 md:w-3 text-red-400" />
                      Failed ({groupedExports.failed.length})
                    </h3>
                    <div className="space-y-1.5 md:space-y-2">
                      {groupedExports.failed.map((item) => (
                        <ExportJobRow
                          key={item.export_id}
                          item={item}
                          onDownload={handleDownload}
                          onShare={handleShare}
                          onDelete={handleDelete}
                          isDownloading={downloadingId === item.export_id}
                          isSharing={sharingId === item.export_id}
                        />
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Copied Toast */}
          {copiedUrl && (
            <div className="fixed bottom-3 md:bottom-4 right-3 md:right-4 flex items-center gap-1.5 md:gap-2 px-3 md:px-4 py-1.5 md:py-2 bg-green-500/20 border border-green-500/30 text-green-300 text-xs md:text-sm">
              <Copy className="h-3.5 w-3.5 md:h-4 md:w-4" />
              <span className="hidden sm:inline">Share link copied to clipboard</span>
              <span className="sm:hidden">Link copied</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
