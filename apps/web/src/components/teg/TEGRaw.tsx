'use client';

/**
 * TEG RAW View Component
 *
 * JSON payload of selected node + manifest references.
 * Intended for debugging / audit checks.
 * Reference: docs/TEG_UNIVERSE_MAP_EXECUTION.md Section 2.2.C
 */

import { useState } from 'react';
import { Copy, Check, FileJson, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { TEGRawProps } from './types';

export function TEGRaw({ node, edges }: TEGRawProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    if (!node) return;

    const data = {
      node,
      edges: edges?.filter(
        (e) => e.from_node_id === node.node_id || e.to_node_id === node.node_id
      ),
    };

    await navigator.clipboard.writeText(JSON.stringify(data, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!node) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8 text-center">
        <FileJson className="w-12 h-12 text-white/20 mb-4" />
        <h3 className="text-sm font-medium text-white/60 mb-2">No Node Selected</h3>
        <p className="text-xs text-white/40">
          Select a node to view its raw JSON payload and manifest references.
        </p>
      </div>
    );
  }

  const relatedEdges = edges?.filter(
    (e) => e.from_node_id === node.node_id || e.to_node_id === node.node_id
  );

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-white/10">
        <div className="flex items-center gap-2">
          <FileJson className="w-4 h-4 text-cyan-400" />
          <span className="text-xs font-mono text-white/70">RAW JSON</span>
        </div>
        <button
          onClick={handleCopy}
          className={cn(
            'flex items-center gap-1.5 px-2 py-1 text-xs font-mono transition-colors',
            copied ? 'text-green-400 bg-green-500/10' : 'text-white/60 hover:text-white hover:bg-white/5'
          )}
        >
          {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>

      {/* JSON Display */}
      <div className="flex-1 overflow-auto p-4">
        {/* Node Data */}
        <div className="mb-6">
          <h4 className="text-[10px] font-mono uppercase text-cyan-400 mb-2">Node</h4>
          <pre className="text-xs font-mono text-white/70 bg-black/40 p-4 border border-white/10 overflow-x-auto">
            {JSON.stringify(node, null, 2)}
          </pre>
        </div>

        {/* Related Edges */}
        {relatedEdges && relatedEdges.length > 0 && (
          <div className="mb-6">
            <h4 className="text-[10px] font-mono uppercase text-purple-400 mb-2">
              Related Edges ({relatedEdges.length})
            </h4>
            <pre className="text-xs font-mono text-white/70 bg-black/40 p-4 border border-white/10 overflow-x-auto">
              {JSON.stringify(relatedEdges, null, 2)}
            </pre>
          </div>
        )}

        {/* Manifest Links */}
        {node.links && Object.keys(node.links).length > 0 && (
          <div className="mb-6">
            <h4 className="text-[10px] font-mono uppercase text-amber-400 mb-2">
              Manifest Links
            </h4>
            <div className="bg-black/40 p-4 border border-white/10 space-y-2">
              {node.links.run_ids?.map((runId, i) => (
                <div key={i} className="flex items-center gap-2 text-xs">
                  <span className="text-white/50 font-mono">run_id:</span>
                  <code className="text-amber-400 font-mono">{runId}</code>
                </div>
              ))}
              {node.links.manifest_hash && (
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-white/50 font-mono">manifest_hash:</span>
                  <code className="text-amber-400 font-mono">{node.links.manifest_hash}</code>
                </div>
              )}
              {node.links.persona_version && (
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-white/50 font-mono">persona_version:</span>
                  <code className="text-amber-400 font-mono">{node.links.persona_version}</code>
                </div>
              )}
              {node.links.evidence_ids?.map((evidenceId, i) => (
                <div key={i} className="flex items-center gap-2 text-xs">
                  <span className="text-white/50 font-mono">evidence_id:</span>
                  <code className="text-amber-400 font-mono">{evidenceId}</code>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Audit Info */}
        <div className="p-3 bg-blue-500/10 border border-blue-500/30">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-blue-400 mt-0.5 flex-shrink-0" />
            <div className="text-xs text-blue-400">
              <p className="font-medium mb-1">Audit Information</p>
              <p className="text-blue-400/70">
                This raw view shows the complete node data for debugging and audit purposes.
                All run manifests and persona versions are linked for reproducibility.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
