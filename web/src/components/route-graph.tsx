"use client";

import { useCallback, useMemo, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
} from "@xyflow/react";
import dagre from "@dagrejs/dagre";
import "@xyflow/react/dist/style.css";

import { ApiRouteNode, type ApiRouteNodeData } from "./api-route-node";

// Define nodeTypes outside component to prevent re-renders
const nodeTypes = { apiRoute: ApiRouteNode };

interface Subcommand {
  name: string;
  description?: string;
  method: string;
  endpoint: string;
  params?: Array<{ name: string; type: string; required: boolean }>;
  output?: { format?: string };
}

interface RouteGraph {
  command: string;
  subcommands: Subcommand[];
  base_url?: string;
  metadata?: Record<string, unknown>;
}

interface RouteGraphProps {
  routeGraph: RouteGraph;
  onSelectRoute?: (route: Subcommand | null) => void;
}

function buildNodesAndEdges(routeGraph: RouteGraph): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = [];
  const edges: Edge[] = [];

  // Root node
  const rootId = "root";
  nodes.push({
    id: rootId,
    type: "default",
    data: { label: routeGraph.command || "API" },
    position: { x: 0, y: 0 },
    style: {
      background: "#18181b",
      color: "#e4e4e7",
      border: "1px solid #3f3f46",
      borderRadius: "8px",
      padding: "8px 16px",
      fontSize: "14px",
      fontWeight: "bold",
      fontFamily: "var(--font-geist-mono)",
    },
  });

  // Group subcommands by path prefix
  const groups = new Map<string, Subcommand[]>();
  for (const cmd of routeGraph.subcommands) {
    const parts = cmd.endpoint.split("/").filter(Boolean);
    const prefix = parts.length > 1 ? `/${parts[0]}` : "/";
    const existing = groups.get(prefix) || [];
    existing.push(cmd);
    groups.set(prefix, existing);
  }

  // Create group nodes and route nodes
  for (const [prefix, commands] of groups) {
    const groupId = `group-${prefix}`;

    // Group node
    nodes.push({
      id: groupId,
      type: "default",
      data: { label: prefix },
      position: { x: 0, y: 0 },
      style: {
        background: "#1c1c1f",
        color: "#a1a1aa",
        border: "1px dashed #3f3f46",
        borderRadius: "6px",
        padding: "6px 12px",
        fontSize: "12px",
        fontFamily: "var(--font-geist-mono)",
      },
    });

    edges.push({
      id: `${rootId}-${groupId}`,
      source: rootId,
      target: groupId,
      style: { stroke: "#3f3f46" },
      type: "smoothstep",
    });

    // Route nodes within group
    for (const cmd of commands) {
      const nodeId = `route-${cmd.method}-${cmd.endpoint}`;
      nodes.push({
        id: nodeId,
        type: "apiRoute",
        data: {
          method: cmd.method,
          path: cmd.endpoint,
          paramCount: cmd.params?.length || 0,
          description: cmd.description,
        } satisfies ApiRouteNodeData,
        position: { x: 0, y: 0 },
      });

      edges.push({
        id: `${groupId}-${nodeId}`,
        source: groupId,
        target: nodeId,
        style: { stroke: "#3f3f46" },
        type: "smoothstep",
      });
    }
  }

  return applyDagreLayout(nodes, edges);
}

function applyDagreLayout(nodes: Node[], edges: Edge[]): { nodes: Node[]; edges: Edge[] } {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: "TB", nodesep: 60, ranksep: 100 });

  for (const node of nodes) {
    const width = node.type === "apiRoute" ? 250 : 120;
    const height = node.type === "apiRoute" ? 50 : 36;
    g.setNode(node.id, { width, height });
  }

  for (const edge of edges) {
    g.setEdge(edge.source, edge.target);
  }

  dagre.layout(g);

  const laidOut = nodes.map((node) => {
    const pos = g.node(node.id);
    const width = node.type === "apiRoute" ? 250 : 120;
    const height = node.type === "apiRoute" ? 50 : 36;
    return {
      ...node,
      position: { x: pos.x - width / 2, y: pos.y - height / 2 },
    };
  });

  return { nodes: laidOut, edges };
}

export function RouteGraph({ routeGraph, onSelectRoute }: RouteGraphProps) {
  const { nodes: initialNodes, edges: initialEdges } = useMemo(
    () => buildNodesAndEdges(routeGraph),
    [routeGraph]
  );

  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  const handleNodeClick = useCallback(
    (_: unknown, node: Node) => {
      if (node.type === "apiRoute" && onSelectRoute) {
        const cmd = routeGraph.subcommands.find(
          (c) => `route-${c.method}-${c.endpoint}` === node.id
        );
        onSelectRoute(cmd || null);
      }
    },
    [routeGraph, onSelectRoute]
  );

  return (
    <div className="w-full h-full" style={{ minHeight: "60vh" }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#27272a" gap={20} />
        <Controls
          className="!bg-zinc-800 !border-zinc-700 !shadow-lg"
          showInteractive={false}
        />
        <MiniMap
          className="!bg-zinc-900 !border-zinc-800"
          nodeColor="#3f3f46"
          maskColor="rgba(0, 0, 0, 0.6)"
        />
      </ReactFlow>
    </div>
  );
}
