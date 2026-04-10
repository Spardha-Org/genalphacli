"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import dynamic from "next/dynamic";
import { useService, useServiceStatus, useGenerate } from "@/data/hooks";
import type { Subcommand, ServiceStatusValue } from "@/data/types";
import { RouteDetailPanel } from "@/components/route-detail-panel";
import Link from "next/link";

// Lazy-load React Flow — saves ~80KB gzipped from initial bundle
const RouteGraph = dynamic(
  () => import("@/components/route-graph").then((m) => ({ default: m.RouteGraph })),
  {
    ssr: false,
    loading: () => (
      <div className="w-full h-[60vh] bg-zinc-900 rounded-lg flex items-center justify-center">
        <p className="text-zinc-600 animate-pulse">Loading graph...</p>
      </div>
    ),
  },
);

export default function ServicePage() {
  const { id } = useParams<{ id: string }>();
  const { data: service, isLoading, isError } = useService(id);
  const [selectedRoute, setSelectedRoute] = useState<Subcommand | null>(null);
  const [showGenerate, setShowGenerate] = useState(false);

  // Poll status for active services
  const isActive = service && ["cloning", "parsing", "generating", "packaging"].includes(service.status);
  const { data: liveStatus } = useServiceStatus(isActive ? id : null);

  const currentStatus = (liveStatus?.status || service?.status || "pending") as ServiceStatusValue;

  if (isLoading) {
    return (
      <div>
        <div className="h-8 w-48 bg-zinc-800 rounded animate-pulse" />
        <div className="mt-6 h-[60vh] bg-zinc-800 rounded-lg animate-pulse" />
      </div>
    );
  }

  if (isError || !service) {
    return (
      <div className="text-center py-20">
        <p className="text-zinc-400">Service not found</p>
        <Link href="/dashboard" className="text-teal-400 text-sm mt-2 inline-block">
          Back to dashboard
        </Link>
      </div>
    );
  }

  const routeCount = service.route_graph?.subcommands?.length || 0;

  return (
    <div className="flex flex-col h-[calc(100vh-64px)]">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-zinc-800">
        <div>
          <h1 className="text-xl font-bold font-[family-name:var(--font-geist-mono)]">
            {service.name}
          </h1>
          <div className="flex items-center gap-3 mt-1">
            {service.repo_url && (
              <a
                href={service.repo_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-zinc-500 hover:text-teal-400 transition-colors font-[family-name:var(--font-geist-mono)]"
              >
                {service.repo_url}
              </a>
            )}
            <StatusBadge status={currentStatus} />
            {service.framework && (
              <span className="text-xs text-zinc-500 bg-zinc-800 px-2 py-0.5 rounded">
                {service.framework}
              </span>
            )}
            {routeCount > 0 && (
              <span className="text-xs text-zinc-600">{routeCount} routes</span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {["parsed", "complete"].includes(currentStatus) && (
            <button
              onClick={() => setShowGenerate(!showGenerate)}
              className="bg-zinc-800 text-zinc-200 px-4 py-2 rounded-lg text-sm font-medium hover:bg-zinc-700 transition-colors border border-zinc-700"
            >
              {showGenerate ? "Close" : "Generate"}
            </button>
          )}
          {currentStatus === "complete" && (
            <a
              href={service.artifact_id ? `/api/artifacts/${service.artifact_id}/download` : `/api/services/${service.id}/download`}
              className="inline-flex items-center gap-2 bg-teal-500 text-zinc-950 px-4 py-2 rounded-lg text-sm font-medium hover:bg-teal-400 transition-colors"
            >
              Download
            </a>
          )}
        </div>
      </div>

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden mt-4">
        {/* Progress for active states */}
        {["cloning", "parsing"].includes(currentStatus) && (
          <div className="flex-1 flex items-center justify-center">
            <ActiveProgress status={currentStatus} errorMessage={service.error_message} />
          </div>
        )}

        {["generating", "packaging"].includes(currentStatus) && (
          <div className="flex-1 flex items-center justify-center">
            <ActiveProgress status={currentStatus} errorMessage={service.error_message} mode="generate" />
          </div>
        )}

        {/* Failed state */}
        {currentStatus === "failed" && (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center max-w-md">
              <p className="text-rose-400 font-medium">
                {service.error_message || "Something went wrong"}
              </p>
              <Link
                href="/dashboard"
                className="text-teal-400 text-sm mt-4 inline-block"
              >
                Back to dashboard
              </Link>
            </div>
          </div>
        )}

        {/* Mindmap for parsed/complete */}
        {service.route_graph && ["parsed", "complete"].includes(currentStatus) && (
          <>
            <div className="flex-1 bg-zinc-950 rounded-lg overflow-hidden border border-zinc-800">
              <RouteGraph
                routeGraph={service.route_graph}
                onSelectRoute={(route) => setSelectedRoute(route as Subcommand | null)}
              />
            </div>
            {selectedRoute && (
              <RouteDetailPanel
                route={selectedRoute}
                onClose={() => setSelectedRoute(null)}
              />
            )}
          </>
        )}

        {/* Generate panel */}
        {showGenerate && ["parsed", "complete"].includes(currentStatus) && (
          <GeneratePanel
            serviceId={service.id}
            serviceName={service.name}
            baseUrl={service.route_graph?.base_url}
            onClose={() => setShowGenerate(false)}
          />
        )}
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    pending: "bg-zinc-700 text-zinc-300",
    cloning: "bg-amber-500/20 text-amber-400",
    parsing: "bg-amber-500/20 text-amber-400",
    parsed: "bg-teal-500/20 text-teal-400",
    generating: "bg-blue-500/20 text-blue-400",
    packaging: "bg-blue-500/20 text-blue-400",
    complete: "bg-emerald-500/20 text-emerald-400",
    failed: "bg-rose-500/20 text-rose-400",
    timed_out: "bg-rose-500/20 text-rose-400",
  };

  return (
    <span className={`text-[10px] px-2 py-0.5 rounded-full ${styles[status] || styles.pending}`}>
      {status}
    </span>
  );
}

function ActiveProgress({
  status,
  errorMessage,
  mode = "parse",
}: {
  status: string;
  errorMessage: string | null;
  mode?: "parse" | "generate";
}) {
  const steps =
    mode === "parse"
      ? [
          { key: "cloning", label: "Cloning repository" },
          { key: "parsing", label: "Parsing routes" },
          { key: "parsed", label: "Done" },
        ]
      : [
          { key: "generating", label: "Generating packages" },
          { key: "packaging", label: "Packaging" },
          { key: "complete", label: "Done" },
        ];

  const currentIdx = steps.findIndex((s) => s.key === status);

  return (
    <div className="max-w-sm space-y-3">
      {steps.map((step, i) => {
        const isComplete = i < currentIdx;
        const isActive = step.key === status;
        return (
          <div key={step.key} className="flex items-center gap-3">
            <div
              className={`w-6 h-6 rounded-full flex items-center justify-center border-2 text-xs ${
                isComplete
                  ? "bg-teal-500 border-teal-500 text-zinc-950"
                  : isActive
                    ? "border-teal-500 text-teal-500 animate-pulse"
                    : "border-zinc-700 text-zinc-700"
              }`}
            >
              {isComplete ? "✓" : i + 1}
            </div>
            <span className={`text-sm ${isComplete ? "text-teal-400" : isActive ? "text-zinc-50" : "text-zinc-600"}`}>
              {step.label}
            </span>
          </div>
        );
      })}
      {errorMessage && (
        <div className="mt-4 p-3 bg-rose-500/10 border border-rose-500/20 rounded-md">
          <p className="text-xs text-rose-300/70 font-mono">{errorMessage}</p>
        </div>
      )}
    </div>
  );
}

function GeneratePanel({
  serviceId,
  serviceName,
  baseUrl,
  onClose,
}: {
  serviceId: string;
  serviceName: string;
  baseUrl?: string;
  onClose: () => void;
}) {
  const [outputTypes, setOutputTypes] = useState<string[]>(["cli", "mcp"]);
  const [cliName, setCliName] = useState(serviceName.toLowerCase().replace(/[^a-z0-9_]/g, "_"));
  const [baseUrlInput, setBaseUrlInput] = useState(baseUrl || "http://localhost:8000");
  const generate = useGenerate();

  function toggleType(type: string) {
    setOutputTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type],
    );
  }

  return (
    <div className="w-[320px] border-l border-zinc-800 bg-zinc-900 flex flex-col">
      <div className="p-4 border-b border-zinc-800 flex items-center justify-between">
        <h3 className="text-sm font-medium">Generate Package</h3>
        <button onClick={onClose} className="text-zinc-500 hover:text-zinc-300">
          ✕
        </button>
      </div>

      <div className="p-4 space-y-4 flex-1">
        <div>
          <p className="text-xs text-zinc-500 uppercase tracking-wider mb-2">Output type</p>
          <div className="flex gap-2">
            {["cli", "mcp"].map((type) => (
              <button
                key={type}
                onClick={() => toggleType(type)}
                className={`px-4 py-2 text-sm rounded-md border transition-colors ${
                  outputTypes.includes(type)
                    ? "bg-teal-500/10 border-teal-500 text-teal-400"
                    : "bg-zinc-800 border-zinc-700 text-zinc-500 hover:border-zinc-600"
                }`}
              >
                {type.toUpperCase()}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="text-xs text-zinc-500 uppercase tracking-wider mb-1 block">CLI name</label>
          <input
            type="text"
            value={cliName}
            onChange={(e) => setCliName(e.target.value)}
            className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-3 py-2 text-sm font-[family-name:var(--font-geist-mono)] text-zinc-200 focus:outline-none focus:ring-1 focus:ring-teal-500/50"
          />
        </div>

        <div>
          <label className="text-xs text-zinc-500 uppercase tracking-wider mb-1 block">Base URL</label>
          <input
            type="text"
            value={baseUrlInput}
            onChange={(e) => setBaseUrlInput(e.target.value)}
            className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-3 py-2 text-sm font-[family-name:var(--font-geist-mono)] text-zinc-200 focus:outline-none focus:ring-1 focus:ring-teal-500/50"
          />
        </div>

        <button
          onClick={() =>
            generate.mutate({
              serviceId,
              outputTypes,
              cliName,
              baseUrl: baseUrlInput,
            })
          }
          disabled={generate.isPending || outputTypes.length === 0 || !cliName.trim()}
          className="w-full bg-teal-500 text-zinc-950 py-2.5 rounded-lg text-sm font-medium hover:bg-teal-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {generate.isPending ? "Starting..." : "Generate"}
        </button>

        {generate.isError && (
          <p className="text-sm text-rose-400">{generate.error?.message}</p>
        )}
        {generate.isSuccess && (
          <p className="text-sm text-teal-400">Generation started! Check status above.</p>
        )}
      </div>
    </div>
  );
}
