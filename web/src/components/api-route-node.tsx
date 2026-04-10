"use client";

import { memo } from "react";
import { type NodeProps, type Node } from "@xyflow/react";

export type ApiRouteNodeData = {
  method: string;
  path: string;
  paramCount: number;
  description?: string;
};

type ApiRouteNodeType = Node<ApiRouteNodeData, "apiRoute">;

const METHOD_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  GET: { bg: "bg-emerald-500/10", text: "text-emerald-400", border: "border-l-emerald-400" },
  POST: { bg: "bg-blue-500/10", text: "text-blue-400", border: "border-l-blue-400" },
  PUT: { bg: "bg-amber-500/10", text: "text-amber-400", border: "border-l-amber-400" },
  DELETE: { bg: "bg-rose-500/10", text: "text-rose-400", border: "border-l-rose-400" },
  PATCH: { bg: "bg-violet-500/10", text: "text-violet-400", border: "border-l-violet-400" },
};

function ApiRouteNodeComponent({ data }: NodeProps<ApiRouteNodeType>) {
  const colors = METHOD_COLORS[data.method.toUpperCase()] || METHOD_COLORS.GET;

  return (
    <div
      className={`bg-zinc-800 border border-zinc-700 border-l-4 ${colors.border} rounded-md px-3 py-2 min-w-[200px] max-w-[320px] shadow-md hover:shadow-lg transition-shadow`}
    >
      <div className="flex items-center gap-2">
        <span
          className={`text-[10px] font-bold ${colors.text} ${colors.bg} px-1.5 py-0.5 rounded font-[family-name:var(--font-geist-mono)]`}
        >
          {data.method.toUpperCase()}
        </span>
        <span className="text-xs text-zinc-300 font-[family-name:var(--font-geist-mono)] truncate">
          {data.path}
        </span>
      </div>
      {data.paramCount > 0 && (
        <p className="text-[10px] text-zinc-500 mt-1">
          {data.paramCount} param{data.paramCount !== 1 ? "s" : ""}
        </p>
      )}
    </div>
  );
}

export const ApiRouteNode = memo(ApiRouteNodeComponent);
