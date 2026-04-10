"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import { RouteDetailPanel } from "@/components/route-detail-panel";
import { GeneratePanel } from "@/components/generate-panel";
import { ProgressStepper } from "@/components/progress-stepper";
import { useServiceStatus } from "@/hooks/use-service-status";

// Lazy load React Flow — saves ~150KB from initial bundle
const RouteGraph = dynamic(
  () => import("@/components/route-graph").then((m) => ({ default: m.RouteGraph })),
  { ssr: false, loading: () => <div className="flex items-center justify-center h-96 text-zinc-600">Loading graph...</div> }
);

interface ServiceData {
  id: string;
  name: string;
  repoUrl: string | null;
  status: string;
  framework: string | null;
  routeGraph: Record<string, unknown> | null;
  errorMessage: string | null;
  downloadUrl: string | null;
  metadata: Record<string, unknown> | null;
  createdAt: string;
}

interface ServiceDetailProps {
  service: ServiceData;
}

export function ServiceDetail({ service: initialService }: ServiceDetailProps) {
  const [selectedRoute, setSelectedRoute] = useState<unknown>(null);
  const [showGeneratePanel, setShowGeneratePanel] = useState(false);

  // SSE for live updates when service is in active state
  const isActive = ["cloning", "parsing", "generating", "packaging"].includes(
    initialService.status
  );
  const { status: liveStatus } = useServiceStatus(
    isActive ? initialService.id : null
  );

  const currentStatus = liveStatus?.status || initialService.status;
  const routeGraph = initialService.routeGraph as {
    command: string;
    subcommands: Array<{
      name: string;
      description?: string;
      method: string;
      endpoint: string;
      params?: Array<{ name: string; type: string; required: boolean }>;
      output?: { format?: string };
    }>;
    base_url?: string;
  } | null;

  const routeCount =
    (initialService.metadata as { total_routes?: number } | null)?.total_routes ||
    routeGraph?.subcommands?.length ||
    0;

  return (
    <div className="flex flex-col h-[calc(100vh-64px)]">
      {/* Header */}
      <div className="flex items-center justify-between px-0 pb-4 border-b border-zinc-800">
        <div>
          <h1 className="text-xl font-bold font-[family-name:var(--font-geist-mono)]">
            {initialService.name}
          </h1>
          <div className="flex items-center gap-3 mt-1">
            {initialService.repoUrl && (
              <a
                href={initialService.repoUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-zinc-500 hover:text-teal-400 transition-colors font-[family-name:var(--font-geist-mono)]"
              >
                {initialService.repoUrl}
              </a>
            )}
            <StatusBadge status={currentStatus} />
            {initialService.framework && (
              <span className="text-xs text-zinc-500 bg-zinc-800 px-2 py-0.5 rounded">
                {initialService.framework}
              </span>
            )}
            <span className="text-xs text-zinc-600">{routeCount} routes</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {currentStatus === "parsed" && (
            <button
              onClick={() => setShowGeneratePanel(!showGeneratePanel)}
              className="bg-teal-500 text-zinc-950 px-4 py-2 rounded-lg text-sm font-medium hover:bg-teal-400 transition-colors"
            >
              Generate
            </button>
          )}
          {(currentStatus === "complete" && initialService.downloadUrl) && (
            <a
              href={`/api/services/${initialService.id}/download`}
              className="inline-flex items-center gap-2 bg-teal-500 text-zinc-950 px-4 py-2 rounded-lg text-sm font-medium hover:bg-teal-400 transition-colors"
            >
              Download
            </a>
          )}
        </div>
      </div>

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden mt-4">
        {/* Active parse/generate — show progress */}
        {["cloning", "parsing"].includes(currentStatus) && (
          <div className="flex-1 flex items-center justify-center">
            <div className="max-w-sm">
              <ProgressStepper
                currentStatus={currentStatus}
                errorMessage={liveStatus?.errorMessage || initialService.errorMessage}
                mode="parse"
              />
            </div>
          </div>
        )}

        {["generating", "packaging"].includes(currentStatus) && (
          <div className="flex-1 flex items-center justify-center">
            <div className="max-w-sm">
              <ProgressStepper
                currentStatus={currentStatus}
                errorMessage={liveStatus?.errorMessage || initialService.errorMessage}
                mode="generate"
              />
            </div>
          </div>
        )}

        {/* Failed state */}
        {currentStatus === "failed" && (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center max-w-md">
              <p className="text-rose-400 font-medium">Parsing failed</p>
              {initialService.errorMessage && (
                <p className="text-sm text-zinc-500 mt-2 font-[family-name:var(--font-geist-mono)]">
                  {initialService.errorMessage}
                </p>
              )}
            </div>
          </div>
        )}

        {/* Mindmap — shown when parsed or complete */}
        {routeGraph && ["parsed", "complete"].includes(currentStatus) && (
          <>
            <div className="flex-1 bg-zinc-950 rounded-lg overflow-hidden border border-zinc-800">
              <RouteGraph
                routeGraph={routeGraph}
                onSelectRoute={(route) => setSelectedRoute(route)}
              />
            </div>

            {/* Route detail panel */}
            {selectedRoute && (
              <RouteDetailPanel
                route={selectedRoute as {
                  name: string;
                  method: string;
                  endpoint: string;
                  params?: Array<{ name: string; type: string; required: boolean }>;
                  output?: { format?: string };
                }}
                onClose={() => setSelectedRoute(null)}
              />
            )}
          </>
        )}

        {/* Generate panel */}
        {showGeneratePanel && currentStatus === "parsed" && (
          <div className="w-[320px] border-l border-zinc-800 bg-zinc-900">
            <div className="p-4 border-b border-zinc-800">
              <h3 className="text-sm font-medium">Generate Package</h3>
            </div>
            <GeneratePanel
              serviceId={initialService.id}
              serviceName={initialService.name}
              detectedBaseUrl={routeGraph?.base_url}
              onGenerated={() => setShowGeneratePanel(false)}
            />
          </div>
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
