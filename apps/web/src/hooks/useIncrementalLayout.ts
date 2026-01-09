'use client';

/**
 * useIncrementalLayout - Performance-optimized graph layout hook
 * Caches node positions and only recalculates when necessary.
 * Reference: Interaction_design.md §8.1 (incremental rendering)
 */

import { useRef, useMemo, useCallback } from 'react';
import type { SpecNode, SpecEdge } from '@/lib/api';

interface NodePosition {
  id: string;
  x: number;
  y: number;
  level: number;
  node: SpecNode;
}

// Layout configuration
const NODE_SPACING_X = 120;
const NODE_SPACING_Y = 80;
const PADDING = 60;

interface LayoutCache {
  positions: Map<string, NodePosition>;
  nodeIds: Set<string>;
  edgeKeys: Set<string>;
}

interface IncrementalLayoutResult {
  positions: Map<string, NodePosition>;
  isIncremental: boolean;
  newNodeIds: string[];
}

/**
 * Calculate which nodes are new since last layout
 */
function findNewNodes(
  currentNodes: SpecNode[],
  cachedNodeIds: Set<string>
): SpecNode[] {
  return currentNodes.filter(node => !cachedNodeIds.has(node.node_id));
}

/**
 * Calculate positions for new nodes only (incremental)
 */
function calculateIncrementalPositions(
  newNodes: SpecNode[],
  allNodes: SpecNode[],
  edges: SpecEdge[],
  existingPositions: Map<string, NodePosition>
): Map<string, NodePosition> {
  const positions = new Map(existingPositions);
  const nodeMap = new Map(allNodes.map(n => [n.node_id, n]));

  // Build parent-child relationships
  const childMap = new Map<string, string[]>();
  edges.forEach(edge => {
    const children = childMap.get(edge.from_node_id) || [];
    children.push(edge.to_node_id);
    childMap.set(edge.from_node_id, children);
  });

  // Process each new node
  newNodes.forEach(newNode => {
    // Skip if already positioned
    if (positions.has(newNode.node_id)) return;

    // Find parent position
    const parentPos = newNode.parent_node_id
      ? positions.get(newNode.parent_node_id)
      : null;

    // Get siblings (other children of same parent)
    const siblings = newNode.parent_node_id
      ? (childMap.get(newNode.parent_node_id) || [])
          .filter(id => id !== newNode.node_id && positions.has(id))
      : [];

    let x: number;
    let y: number;

    if (parentPos) {
      // Position relative to parent
      y = parentPos.y + NODE_SPACING_Y;

      if (siblings.length > 0) {
        // Place after last sibling
        const siblingPositions = siblings
          .map(id => positions.get(id))
          .filter(Boolean) as NodePosition[];
        const maxSiblingX = Math.max(...siblingPositions.map(p => p.x));
        x = maxSiblingX + NODE_SPACING_X;
      } else {
        // First child - place under parent
        x = parentPos.x;
      }
    } else {
      // Root node - find rightmost existing root
      const existingRoots = Array.from(positions.values()).filter(
        p => !p.node.parent_node_id
      );
      if (existingRoots.length > 0) {
        const maxRootX = Math.max(...existingRoots.map(p => p.x));
        x = maxRootX + NODE_SPACING_X;
      } else {
        x = PADDING;
      }
      y = PADDING;
    }

    positions.set(newNode.node_id, {
      id: newNode.node_id,
      x,
      y,
      level: parentPos ? parentPos.level + 1 : 0,
      node: newNode,
    });
  });

  return positions;
}

/**
 * Calculate full layout from scratch
 */
function calculateFullLayout(
  nodes: SpecNode[],
  edges: SpecEdge[]
): Map<string, NodePosition> {
  const positions = new Map<string, NodePosition>();
  const nodeMap = new Map(nodes.map(n => [n.node_id, n]));
  const childMap = new Map<string, string[]>();

  // Build child map from edges
  edges.forEach(edge => {
    const children = childMap.get(edge.from_node_id) || [];
    children.push(edge.to_node_id);
    childMap.set(edge.from_node_id, children);
  });

  // Find root nodes (nodes without parents)
  const rootNodes = nodes.filter(n => !n.parent_node_id);

  // Calculate positions level by level
  const processLevel = (nodeIds: string[], level: number, startX: number) => {
    let x = startX;

    nodeIds.forEach(nodeId => {
      const node = nodeMap.get(nodeId);
      if (!node) return;

      const children = childMap.get(nodeId) || [];
      let nodeX = x;

      if (children.length > 0) {
        // Process children first to get their span
        const childStartX = x;
        processLevel(children, level + 1, childStartX);

        // Center parent over children
        const childPositions = children
          .map(id => positions.get(id))
          .filter(Boolean) as NodePosition[];

        if (childPositions.length > 0) {
          const minX = Math.min(...childPositions.map(p => p.x));
          const maxX = Math.max(...childPositions.map(p => p.x));
          nodeX = (minX + maxX) / 2;
        }

        // Update x for next sibling
        x = Math.max(
          x,
          ...children.map(id => {
            const pos = positions.get(id);
            return pos ? pos.x + NODE_SPACING_X : x;
          })
        );
      } else {
        x += NODE_SPACING_X;
      }

      positions.set(nodeId, {
        id: nodeId,
        x: nodeX,
        y: PADDING + level * NODE_SPACING_Y,
        level,
        node,
      });
    });

    return x;
  };

  processLevel(
    rootNodes.map(n => n.node_id),
    0,
    PADDING
  );

  return positions;
}

/**
 * Hook for incremental graph layout
 * Maintains position cache and only recalculates when necessary
 */
export function useIncrementalLayout(
  nodes: SpecNode[],
  edges: SpecEdge[]
): IncrementalLayoutResult {
  const cacheRef = useRef<LayoutCache>({
    positions: new Map(),
    nodeIds: new Set(),
    edgeKeys: new Set(),
  });

  const result = useMemo(() => {
    const cache = cacheRef.current;
    const currentNodeIds = new Set(nodes.map(n => n.node_id));
    const currentEdgeKeys = new Set(
      edges.map(e => `${e.from_node_id}-${e.to_node_id}`)
    );

    // Check if edges changed (structure change requires full relayout)
    const edgesChanged =
      cache.edgeKeys.size !== currentEdgeKeys.size ||
      [...cache.edgeKeys].some(key => !currentEdgeKeys.has(key)) ||
      [...currentEdgeKeys].some(key => !cache.edgeKeys.has(key));

    // Check if nodes were removed (requires full relayout)
    const nodesRemoved = [...cache.nodeIds].some(id => !currentNodeIds.has(id));

    // Find new nodes
    const newNodes = findNewNodes(nodes, cache.nodeIds);
    const newNodeIds = newNodes.map(n => n.node_id);

    let positions: Map<string, NodePosition>;
    let isIncremental: boolean;

    if (edgesChanged || nodesRemoved || cache.positions.size === 0) {
      // Full layout needed
      positions = calculateFullLayout(nodes, edges);
      isIncremental = false;
    } else if (newNodes.length > 0) {
      // Incremental layout - only position new nodes
      positions = calculateIncrementalPositions(
        newNodes,
        nodes,
        edges,
        cache.positions
      );
      isIncremental = true;
    } else {
      // No changes - return cached positions
      positions = cache.positions;
      isIncremental = true;
    }

    // Update cache
    cache.positions = positions;
    cache.nodeIds = currentNodeIds;
    cache.edgeKeys = currentEdgeKeys;

    return { positions, isIncremental, newNodeIds };
  }, [nodes, edges]);

  return result;
}

/**
 * Hook for tracking layout performance
 */
export function useLayoutPerformance() {
  const metricsRef = useRef({
    totalLayouts: 0,
    incrementalLayouts: 0,
    lastLayoutTime: 0,
  });

  const recordLayout = useCallback((isIncremental: boolean, duration: number) => {
    metricsRef.current.totalLayouts++;
    if (isIncremental) {
      metricsRef.current.incrementalLayouts++;
    }
    metricsRef.current.lastLayoutTime = duration;
  }, []);

  const getMetrics = useCallback(() => {
    return {
      ...metricsRef.current,
      incrementalRatio:
        metricsRef.current.totalLayouts > 0
          ? metricsRef.current.incrementalLayouts /
            metricsRef.current.totalLayouts
          : 0,
    };
  }, []);

  return { recordLayout, getMetrics };
}
