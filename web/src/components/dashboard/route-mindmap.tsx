"use client";

import { useMemo, useState, useCallback, useRef } from "react";
import type { RouteGraph, Subcommand } from "@/data/types";

const METHOD_COLORS: Record<string, { bg: string; text: string }> = {
  GET: { bg: "rgba(34,197,94,0.15)", text: "var(--green)" },
  POST: { bg: "rgba(59,130,246,0.15)", text: "var(--blue)" },
  PUT: { bg: "rgba(245,158,11,0.15)", text: "var(--amber)" },
  PATCH: { bg: "rgba(245,158,11,0.15)", text: "var(--amber)" },
  DELETE: { bg: "rgba(244,63,94,0.15)", text: "var(--rose)" },
};

interface GroupedRoutes {
  prefix: string;
  endpoints: { method: string; path: string; subcommand: Subcommand }[];
}

function groupRoutes(subcommands: Subcommand[]): GroupedRoutes[] {
  const groups: Record<string, GroupedRoutes> = {};

  for (const cmd of subcommands) {
    // Extract first path segment as group: /users/{id} → /users
    const parts = cmd.endpoint.split("/").filter(Boolean);
    const prefix = parts.length > 0 ? `/${parts[0]}` : "/";

    if (!groups[prefix]) {
      groups[prefix] = { prefix, endpoints: [] };
    }
    groups[prefix].endpoints.push({
      method: cmd.method.toUpperCase(),
      path: cmd.endpoint,
      subcommand: cmd,
    });
  }

  return Object.values(groups).slice(0, 8); // Max 8 groups to fit
}

interface RouteMindmapProps {
  routeGraph: RouteGraph;
  onRouteClick?: (subcommand: Subcommand) => void;
}

export function RouteMindmap({ routeGraph, onRouteClick }: RouteMindmapProps) {
  const [scale, setScale] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const isDragging = useRef(false);
  const dragStart = useRef({ x: 0, y: 0 });
  const panStart = useRef({ x: 0, y: 0 });

  const groups = useMemo(() => groupRoutes(routeGraph.subcommands || []), [routeGraph]);

  const zoom = useCallback((delta: number) => {
    setScale((s) => Math.max(0.5, Math.min(2, s + delta)));
  }, []);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    // Only drag on background, not on nodes
    if ((e.target as HTMLElement).closest(".mindmap-node-click")) return;
    isDragging.current = true;
    dragStart.current = { x: e.clientX, y: e.clientY };
    panStart.current = { ...pan };
  }, [pan]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isDragging.current) return;
    setPan({
      x: panStart.current.x + (e.clientX - dragStart.current.x) / scale,
      y: panStart.current.y + (e.clientY - dragStart.current.y) / scale,
    });
  }, [scale]);

  const handleMouseUp = useCallback(() => {
    isDragging.current = false;
  }, []);

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.05 : 0.05;
    setScale((s) => Math.max(0.5, Math.min(2, s + delta)));
  }, []);

  const resetView = useCallback(() => {
    setScale(1);
    setPan({ x: 0, y: 0 });
  }, []);

  // Layout calculations — dynamic spacing based on endpoint count per group
  const rootX = 40;
  const groupX = 340;
  const endpointX = 580;
  const endpointH = 32; // height per endpoint node
  const endpointGap = 6; // gap between endpoint nodes
  const groupGap = 30; // gap between groups

  // Calculate each group's Y center and total height
  const groupLayouts = useMemo(() => {
    const layouts: { gy: number; endpointStartY: number; endpointCount: number }[] = [];
    let currentY = 40;

    for (const group of groups) {
      const count = Math.min(group.endpoints.length, 5);
      const blockHeight = count * (endpointH + endpointGap) - endpointGap;
      const gy = currentY + blockHeight / 2;
      layouts.push({ gy, endpointStartY: currentY, endpointCount: count });
      currentY += blockHeight + groupGap;
    }
    return layouts;
  }, [groups]);

  const totalHeight = groupLayouts.length > 0
    ? groupLayouts[groupLayouts.length - 1].endpointStartY + groupLayouts[groupLayouts.length - 1].endpointCount * (endpointH + endpointGap) + 40
    : 500;
  const rootY = totalHeight / 2;

  return (
    <div
      className="h-[500px] bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius)] relative overflow-hidden select-none"
      style={{ cursor: isDragging.current ? "grabbing" : "grab" }}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      onWheel={handleWheel}
    >
      {/* Controls */}
      <div className="absolute bottom-3 right-3 flex gap-1 z-10">
        <button
          onClick={() => zoom(0.1)}
          className="w-7 h-7 flex items-center justify-center bg-[var(--elevated)] border border-[var(--border)] rounded-md text-[var(--text-dim)] hover:text-[var(--text)] transition-colors font-[family-name:var(--font-jetbrains-mono)] text-xs"
        >
          +
        </button>
        <button
          onClick={() => zoom(-0.1)}
          className="w-7 h-7 flex items-center justify-center bg-[var(--elevated)] border border-[var(--border)] rounded-md text-[var(--text-dim)] hover:text-[var(--text)] transition-colors font-[family-name:var(--font-jetbrains-mono)] text-xs"
        >
          −
        </button>
        <button
          onClick={resetView}
          className="w-7 h-7 flex items-center justify-center bg-[var(--elevated)] border border-[var(--border)] rounded-md text-[var(--text-dim)] hover:text-[var(--text)] transition-colors font-[family-name:var(--font-jetbrains-mono)] text-[10px]"
        >
          [ ]
        </button>
      </div>

      <div
        className="absolute inset-0"
        style={{ transform: `scale(${scale}) translate(${pan.x}px, ${pan.y}px)`, transformOrigin: "center center", transition: isDragging.current ? "none" : "transform 0.2s" }}
      >
        {/* SVG Edges */}
        <svg className="absolute top-0 left-0" style={{ width: "100%", height: totalHeight, minHeight: "100%" }}>
          {groups.map((group, gi) => {
            const layout = groupLayouts[gi];
            const rootCx = rootX + 200;
            const groupCx = groupX - 10;

            return (
              <g key={group.prefix}>
                <path
                  d={`M ${rootCx},${rootY} C ${(rootCx + groupCx) / 2},${rootY} ${(rootCx + groupCx) / 2},${layout.gy} ${groupCx},${layout.gy}`}
                  fill="none"
                  stroke="rgba(20, 184, 166, 0.25)"
                  strokeWidth="1.5"
                />
                {group.endpoints.slice(0, 5).map((_ep, ei) => {
                  const ey = layout.endpointStartY + ei * (endpointH + endpointGap) + endpointH / 2;
                  const gRightX = groupX + 120;
                  const eLeftX = endpointX - 10;
                  return (
                    <path
                      key={ei}
                      d={`M ${gRightX},${layout.gy} C ${(gRightX + eLeftX) / 2},${layout.gy} ${(gRightX + eLeftX) / 2},${ey} ${eLeftX},${ey}`}
                      fill="none"
                      stroke="rgba(255,255,255,0.06)"
                      strokeWidth="1.5"
                    />
                  );
                })}
              </g>
            );
          })}
        </svg>

        {/* Root node */}
        <div
          className="absolute px-4 py-2 rounded-lg font-[family-name:var(--font-jetbrains-mono)] text-[13px] font-bold whitespace-nowrap bg-[var(--accent)] text-[var(--bg)] border border-[var(--accent)] hover:shadow-[0_0_12px_rgba(20,184,166,0.3)] transition-shadow"
          style={{ left: rootX, top: rootY - 16 }}
        >
          {routeGraph.command || "api"}
        </div>

        {/* Groups + Endpoints */}
        {groups.map((group, gi) => {
          const layout = groupLayouts[gi];

          return (
            <div key={group.prefix}>
              <div
                className="absolute px-3.5 py-2 rounded-lg font-[family-name:var(--font-jetbrains-mono)] text-[11px] font-semibold whitespace-nowrap bg-[var(--elevated)] text-[var(--text)] border border-white/10 hover:shadow-[0_0_12px_rgba(20,184,166,0.3)] transition-shadow"
                style={{ left: groupX, top: layout.gy - 14 }}
              >
                {group.prefix}
              </div>

              {group.endpoints.slice(0, 5).map((ep, ei) => {
                const ey = layout.endpointStartY + ei * (endpointH + endpointGap);
                const mc = METHOD_COLORS[ep.method] || { bg: "rgba(255,255,255,0.1)", text: "var(--text-muted)" };

                return (
                  <div
                    key={ei}
                    onClick={() => onRouteClick?.(ep.subcommand)}
                    className="mindmap-node-click absolute px-3 py-1.5 rounded-lg font-[family-name:var(--font-jetbrains-mono)] text-[10px] font-semibold whitespace-nowrap bg-[var(--bg)] text-[var(--text-dim)] border border-[var(--border)] flex items-center gap-1.5 cursor-pointer hover:shadow-[0_0_12px_rgba(20,184,166,0.3)] transition-shadow"
                    style={{ left: endpointX, top: ey }}
                  >
                    <span
                      className="text-[9px] font-bold px-1.5 py-px rounded uppercase"
                      style={{ background: mc.bg, color: mc.text }}
                    >
                      {ep.method === "DELETE" ? "DEL" : ep.method}
                    </span>
                    {ep.path}
                  </div>
                );
              })}
              {group.endpoints.length > 5 && (
                <div
                  className="absolute px-3 py-1 font-[family-name:var(--font-jetbrains-mono)] text-[9px] text-[var(--text-muted)]"
                  style={{ left: endpointX, top: layout.endpointStartY + 5 * (endpointH + endpointGap) }}
                >
                  +{group.endpoints.length - 5} more
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
