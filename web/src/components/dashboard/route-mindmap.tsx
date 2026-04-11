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

  // Layout calculations
  const rootX = 60;
  const rootY = 240;
  const groupX = 280;
  const endpointX = 500;
  const groupSpacing = Math.min(100, 480 / Math.max(groups.length, 1));
  const groupStartY = rootY - ((groups.length - 1) * groupSpacing) / 2;

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
        <svg className="absolute inset-0 w-full h-full pointer-events-none">
          {groups.map((group, gi) => {
            const gy = groupStartY + gi * groupSpacing;
            // Root → Group
            const rootCx = rootX + 120;
            const groupCx = groupX - 20;
            const endpointStartY = gy - ((group.endpoints.length - 1) * 40) / 2;

            return (
              <g key={group.prefix}>
                {/* Root → Group edge */}
                <path
                  d={`M ${rootCx},${rootY} C ${(rootCx + groupCx) / 2},${rootY} ${(rootCx + groupCx) / 2},${gy} ${groupCx},${gy}`}
                  fill="none"
                  stroke="rgba(20, 184, 166, 0.25)"
                  strokeWidth="1.5"
                />
                {/* Group → Endpoint edges */}
                {group.endpoints.slice(0, 5).map((ep, ei) => {
                  const ey = endpointStartY + ei * 40;
                  const gRightX = groupX + 80;
                  const eLeftX = endpointX - 10;
                  return (
                    <path
                      key={ei}
                      d={`M ${gRightX},${gy} C ${(gRightX + eLeftX) / 2},${gy} ${(gRightX + eLeftX) / 2},${ey} ${eLeftX},${ey}`}
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
          const gy = groupStartY + gi * groupSpacing;
          const endpointStartY = gy - ((group.endpoints.length - 1) * 40) / 2;

          return (
            <div key={group.prefix}>
              {/* Group node */}
              <div
                className="absolute px-3.5 py-2 rounded-lg font-[family-name:var(--font-jetbrains-mono)] text-[11px] font-semibold whitespace-nowrap bg-[var(--elevated)] text-[var(--text)] border border-white/10 hover:shadow-[0_0_12px_rgba(20,184,166,0.3)] transition-shadow"
                style={{ left: groupX, top: gy - 14 }}
              >
                {group.prefix}
              </div>

              {/* Endpoint nodes */}
              {group.endpoints.slice(0, 5).map((ep, ei) => {
                const ey = endpointStartY + ei * 40;
                const mc = METHOD_COLORS[ep.method] || { bg: "rgba(255,255,255,0.1)", text: "var(--text-muted)" };

                return (
                  <div
                    key={ei}
                    onClick={() => onRouteClick?.(ep.subcommand)}
                    className="mindmap-node-click absolute px-3 py-1.5 rounded-lg font-[family-name:var(--font-jetbrains-mono)] text-[10px] font-semibold whitespace-nowrap bg-[var(--bg)] text-[var(--text-dim)] border border-[var(--border)] flex items-center gap-1.5 cursor-pointer hover:shadow-[0_0_12px_rgba(20,184,166,0.3)] transition-shadow"
                    style={{ left: endpointX, top: ey - 12 }}
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
                  style={{ left: endpointX, top: endpointStartY + 5 * 40 - 12 }}
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
