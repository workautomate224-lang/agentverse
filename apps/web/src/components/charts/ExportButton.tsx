'use client';

import { useState } from 'react';
import { Download, FileText, Image, Table, Loader2, ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ExportButtonProps {
  onExport: (format: 'pdf' | 'png' | 'csv' | 'json') => Promise<void>;
  availableFormats?: ('pdf' | 'png' | 'csv' | 'json')[];
  disabled?: boolean;
  className?: string;
}

const formatConfig = {
  pdf: { icon: FileText, label: 'PDF Report', description: 'Full report with charts' },
  png: { icon: Image, label: 'PNG Image', description: 'Chart screenshot' },
  csv: { icon: Table, label: 'CSV Data', description: 'Raw data export' },
  json: { icon: FileText, label: 'JSON Data', description: 'Structured data' },
};

export function ExportButton({
  onExport,
  availableFormats = ['pdf', 'csv', 'json'],
  disabled = false,
  className,
}: ExportButtonProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [exportingFormat, setExportingFormat] = useState<string | null>(null);

  const handleExport = async (format: 'pdf' | 'png' | 'csv' | 'json') => {
    setIsExporting(true);
    setExportingFormat(format);
    try {
      await onExport(format);
    } catch {
      // Export failed - caller should handle the error
    } finally {
      setIsExporting(false);
      setExportingFormat(null);
      setIsOpen(false);
    }
  };

  return (
    <div className={cn("relative", className)}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={disabled || isExporting}
        className={cn(
          "px-3 py-1.5 bg-white/10 text-white text-xs font-mono flex items-center gap-2 transition-colors",
          "hover:bg-white/20 disabled:opacity-50 disabled:cursor-not-allowed"
        )}
      >
        {isExporting ? (
          <Loader2 className="w-3 h-3 animate-spin" />
        ) : (
          <Download className="w-3 h-3" />
        )}
        EXPORT
        <ChevronDown className={cn("w-3 h-3 transition-transform", isOpen && "rotate-180")} />
      </button>

      {isOpen && !isExporting && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />

          {/* Dropdown */}
          <div className="absolute right-0 mt-1 w-48 bg-black border border-white/20 z-50">
            {availableFormats.map(format => {
              const config = formatConfig[format];
              const Icon = config.icon;

              return (
                <button
                  key={format}
                  onClick={() => handleExport(format)}
                  disabled={exportingFormat === format}
                  className={cn(
                    "w-full px-3 py-2 text-left hover:bg-white/5 transition-colors",
                    "flex items-center gap-3"
                  )}
                >
                  {exportingFormat === format ? (
                    <Loader2 className="w-4 h-4 animate-spin text-white/40" />
                  ) : (
                    <Icon className="w-4 h-4 text-white/40" />
                  )}
                  <div>
                    <p className="text-xs font-mono text-white">{config.label}</p>
                    <p className="text-[10px] font-mono text-white/40">{config.description}</p>
                  </div>
                </button>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
