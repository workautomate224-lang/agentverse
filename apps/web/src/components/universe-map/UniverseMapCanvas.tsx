'use client';

/**
 * UniverseMapCanvas Component
 * SVG-based visualization of the Universe Map node graph.
 * Reference: project.md §6.7 (Node/Edge), C1 (fork-not-mutate), C3 (read-only)
 * Performance: Uses incremental layout (Interaction_design.md §8.1)
 */

import { memo, useMemo, useCallback, useState, useRef } from 'react';
import { cn } from '@/lib/utils';
import type { SpecNode, SpecEdge, NodeCluster, PathAnalysis } from '@/lib/api';
import { useIncrementalLayout } from '@/hooks/useIncrementalLayout';

interface NodePosition {
  id: string;
  x: number;
  y: number;
  level: number;
  node: SpecNode;
}

interface UniverseMapCanvasProps {
  nodes: SpecNode[];
  edges: SpecEdge[];
  clusters?: NodeCluster[];
  highlightedPath?: PathAnalysis;
  selectedNodeId?: string;
  compareNodeIds?: string[];
  onNodeSelect?: (nodeId: string, shiftKey?: boolean) => void;
  onNodeHover?: (nodeId: string | null) => void;
  width?: number;
  height?: number;
  className?: string;
}

// Layout configuration
const NODE_RADIUS = 20;
const NODE_SPACING_X = 120;
const NODE_SPACING_Y = 80;
const PADDING = 60;

// Color palette
const COLORS = {
  node: {
    default: '#1a1a1a',
    stroke: 'rgba(255,255,255,0.2)',
    hover: 'rgba(255,255,255,0.1)',
    selected: 'rgba(6,182,212,0.3)',
    selectedStroke: 'rgba(6,182,212,0.8)',
    compare: 'rgba(168,85,247,0.3)',
    compareStroke: 'rgba(168,85,247,0.8)',
    root: 'rgba(6,182,212,0.2)',
    rootStroke: 'rgba(6,182,212,0.6)',
  },
  edge: {
    default: 'rgba(255,255,255,0.15)',
    highlighted: 'rgba(6,182,212,0.6)',
    mostLikely: 'rgba(34,197,94,0.6)',
  },
  cluster: {
    fill: 'rgba(139,92,246,0.1)',
    stroke: 'rgba(139,92,246,0.3)',
  },
  text: {
    primary: 'rgba(255,255,255,0.9)',
    secondary: 'rgba(255,255,255,0.5)',
  },
};

// Note: Layout calculation moved to useIncrementalLayout hook for performance

export const UniverseMapCanvas = memo(function UniverseMapCanvas({
  nodes,
  edges,
  clusters,
  highlightedPath,
  selectedNodeId,
  compareNodeIds,
  onNodeSelect,
  onNodeHover,
  width = 800,
  height = 600,
  className,
}: UniverseMapCanvasProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const [transform, setTransform] = useState({ x: 0, y: 0, scale: 1 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  // Calculate layout incrementally for performance (NF-002)
  const { positions: nodePositions } = useIncrementalLayout(nodes, edges);

  // Calculate canvas bounds
  const bounds = useMemo(() => {
    const positions = Array.from(nodePositions.values());
    if (positions.length === 0) {
      return { minX: 0, maxX: width, minY: 0, maxY: height };
    }
    return {
      minX: Math.min(...positions.map((p) => p.x)) - PADDING,
      maxX: Math.max(...positions.map((p) => p.x)) + PADDING,
      minY: Math.min(...positions.map((p) => p.y)) - PADDING,
      maxY: Math.max(...positions.map((p) => p.y)) + PADDING,
    };
  }, [nodePositions, width, height]);

  // Calculate viewBox to fit content
  const viewBox = useMemo(() => {
    const contentWidth = bounds.maxX - bounds.minX + PADDING * 2;
    const contentHeight = bounds.maxY - bounds.minY + PADDING * 2;
    return `${bounds.minX - PADDING} ${bounds.minY - PADDING} ${contentWidth} ${contentHeight}`;
  }, [bounds]);

  // Check if edge is in highlighted path
  const isEdgeHighlighted = useCallback(
    (parentId: string, childId: string) => {
      if (!highlightedPath?.node_sequence) return false;
      const path = highlightedPath.node_sequence;
      for (let i = 0; i < path.length - 1; i++) {
        if (path[i] === parentId && path[i + 1] === childId) return true;
      }
      return false;
    },
    [highlightedPath]
  );

  // Handle node click
  const handleNodeClick = useCallback(
    (nodeId: string, e: React.MouseEvent) => {
      onNodeSelect?.(nodeId, e.shiftKey);
    },
    [onNodeSelect]
  );

  // Handle node hover
  const handleNodeHover = useCallback(
    (nodeId: string | null) => {
      setHoveredNodeId(nodeId);
      onNodeHover?.(nodeId);
    },
    [onNodeHover]
  );

  // Pan handlers
  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (e.target === svgRef.current) {
        setIsDragging(true);
        setDragStart({ x: e.clientX - transform.x, y: e.clientY - transform.y });
      }
    },
    [transform]
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (isDragging) {
        setTransform((t) => ({
          ...t,
          x: e.clientX - dragStart.x,
          y: e.clientY - dragStart.y,
        }));
      }
    },
    [isDragging, dragStart]
  );

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  // Zoom handler
  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    setTransform((t) => ({
      ...t,
      scale: Math.max(0.5, Math.min(2, t.scale * delta)),
    }));
  }, []);

  // Empty state
  if (nodes.length === 0) {
    return (
      <div
        className={cn(
          'flex items-center justify-center bg-black border border-white/10',
          className
        )}
        style={{ width, height }}
      >
        <p className="text-sm font-mono text-white/40">No nodes to display</p>
      </div>
    );
  }

  return (
    <svg
      ref={svgRef}
      width={width}
      height={height}
      viewBox={viewBox}
      className={cn(
        'bg-black border border-white/10',
        isDragging ? 'cursor-grabbing' : 'cursor-grab',
        className
      )}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      onWheel={handleWheel}
    >
      <defs>
        {/* Glow filter */}
        <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="2" result="coloredBlur" />
          <feMerge>
            <feMergeNode in="coloredBlur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>

        {/* Arrow marker for edges */}
        <marker
          id="arrowhead"
          markerWidth="6"
          markerHeight="6"
          refX="5"
          refY="3"
          orient="auto"
        >
          <path d="M0,0 L6,3 L0,6 Z" fill={COLORS.edge.default} />
        </marker>

        <marker
          id="arrowhead-highlighted"
          markerWidth="6"
          markerHeight="6"
          refX="5"
          refY="3"
          orient="auto"
        >
          <path d="M0,0 L6,3 L0,6 Z" fill={COLORS.edge.highlighted} />
        </marker>
      </defs>

      <g transform={`translate(${transform.x}, ${transform.y}) scale(${transform.scale})`}>
        {/* Cluster backgrounds */}
        {clusters?.map((cluster, index) => {
          const clusterPositions = cluster.member_node_ids
            .map((id: string) => nodePositions.get(id))
            .filter(Boolean) as NodePosition[];

          if (clusterPositions.length < 2) return null;

          const padding = 30;
          const minX = Math.min(...clusterPositions.map((p) => p.x)) - padding;
          const maxX = Math.max(...clusterPositions.map((p) => p.x)) + padding;
          const minY = Math.min(...clusterPositions.map((p) => p.y)) - padding;
          const maxY = Math.max(...clusterPositions.map((p) => p.y)) + padding;

          return (
            <rect
              key={`cluster-${index}`}
              x={minX}
              y={minY}
              width={maxX - minX}
              height={maxY - minY}
              rx={8}
              fill={COLORS.cluster.fill}
              stroke={COLORS.cluster.stroke}
              strokeWidth={1}
              strokeDasharray="4 2"
            />
          );
        })}

        {/* Edges */}
        {edges.map((edge) => {
          const parent = nodePositions.get(edge.from_node_id);
          const child = nodePositions.get(edge.to_node_id);
          if (!parent || !child) return null;

          const isHighlighted = isEdgeHighlighted(edge.from_node_id, edge.to_node_id);

          // Calculate control points for curved edge
          const midY = (parent.y + child.y) / 2;

          return (
            <path
              key={`${edge.from_node_id}-${edge.to_node_id}`}
              d={`M ${parent.x} ${parent.y + NODE_RADIUS} Q ${parent.x} ${midY} ${child.x} ${child.y - NODE_RADIUS}`}
              fill="none"
              stroke={isHighlighted ? COLORS.edge.highlighted : COLORS.edge.default}
              strokeWidth={isHighlighted ? 2 : 1}
              markerEnd={isHighlighted ? 'url(#arrowhead-highlighted)' : 'url(#arrowhead)'}
              filter={isHighlighted ? 'url(#glow)' : undefined}
            />
          );
        })}

        {/* Nodes */}
        {Array.from(nodePositions.values()).map((pos) => {
          const isRoot = !pos.node.parent_node_id;
          const isSelected = pos.id === selectedNodeId;
          const isHovered = pos.id === hoveredNodeId;
          const isInPath = highlightedPath?.node_sequence?.includes(pos.id);
          const isCompareSelected = compareNodeIds?.includes(pos.id);

          return (
            <g
              key={pos.id}
              transform={`translate(${pos.x}, ${pos.y})`}
              onClick={(e) => handleNodeClick(pos.id, e)}
              onMouseEnter={() => handleNodeHover(pos.id)}
              onMouseLeave={() => handleNodeHover(null)}
              style={{ cursor: 'pointer' }}
            >
              {/* Node background */}
              <circle
                r={NODE_RADIUS}
                fill={
                  isCompareSelected
                    ? COLORS.node.compare
                    : isSelected
                    ? COLORS.node.selected
                    : isRoot
                    ? COLORS.node.root
                    : isHovered
                    ? COLORS.node.hover
                    : COLORS.node.default
                }
                stroke={
                  isCompareSelected
                    ? COLORS.node.compareStroke
                    : isSelected
                    ? COLORS.node.selectedStroke
                    : isRoot
                    ? COLORS.node.rootStroke
                    : isInPath
                    ? COLORS.edge.highlighted
                    : COLORS.node.stroke
                }
                strokeWidth={isCompareSelected || isSelected || isInPath ? 2 : 1}
                filter={isCompareSelected || isSelected ? 'url(#glow)' : undefined}
              />

              {/* Node probability label */}
              <text
                y={-2}
                textAnchor="middle"
                fill={COLORS.text.primary}
                fontSize={11}
                fontFamily="monospace"
                fontWeight="bold"
              >
                {(pos.node.probability * 100).toFixed(0)}%
              </text>

              {/* Node label or short ID */}
              <text
                y={10}
                textAnchor="middle"
                fill={COLORS.text.secondary}
                fontSize={7}
                fontFamily="monospace"
              >
                {pos.node.label || pos.id.slice(0, 6)}
              </text>

              {/* Root indicator */}
              {isRoot && (
                <circle
                  r={4}
                  cy={-NODE_RADIUS - 8}
                  fill="transparent"
                  stroke={COLORS.node.rootStroke}
                  strokeWidth={2}
                />
              )}

              {/* Baseline indicator */}
              {pos.node.is_baseline && (
                <text
                  y={-NODE_RADIUS - 6}
                  textAnchor="middle"
                  fill="rgba(34,197,94,0.9)"
                  fontSize={8}
                  fontFamily="monospace"
                  fontWeight="bold"
                >
                  BASE
                </text>
              )}

              {/* Level and confidence indicator */}
              <text
                y={NODE_RADIUS + 14}
                textAnchor="middle"
                fill={COLORS.text.secondary}
                fontSize={8}
                fontFamily="monospace"
              >
                L{pos.level} • {pos.node.confidence?.confidence_level?.charAt(0).toUpperCase() || '?'}
              </text>
            </g>
          );
        })}
      </g>

      {/* Legend */}
      <g transform={`translate(${10}, ${height - 60})`}>
        <rect
          x={0}
          y={0}
          width={140}
          height={50}
          fill="rgba(0,0,0,0.8)"
          stroke="rgba(255,255,255,0.1)"
        />
        <circle cx={15} cy={15} r={6} fill={COLORS.node.root} stroke={COLORS.node.rootStroke} />
        <text x={30} y={18} fill={COLORS.text.secondary} fontSize={9} fontFamily="monospace">
          Root Node
        </text>
        <circle cx={15} cy={35} r={6} fill={COLORS.node.default} stroke={COLORS.node.stroke} />
        <text x={30} y={38} fill={COLORS.text.secondary} fontSize={9} fontFamily="monospace">
          Fork Node
        </text>
      </g>
    </svg>
  );
});

export default UniverseMapCanvas;
