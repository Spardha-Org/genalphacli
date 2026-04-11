"use client";

import { useState, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import { useService, useGenerate, useDeleteService, useProjects } from "@/data/hooks";
import type { Subcommand } from "@/data/types";
import { Breadcrumb } from "@/components/dashboard/breadcrumb";
import { RouteMindmap } from "@/components/dashboard/route-mindmap";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

const TABS = ["Mindmap", "Routes", "Generate", "Config", "Host"] as const;
type Tab = (typeof TABS)[number];

const METHOD_COLORS: Record<string, string> = {
  GET: "bg-[var(--green)]/12 text-[var(--green)]",
  POST: "bg-[var(--blue)]/12 text-[var(--blue)]",
  PUT: "bg-[var(--amber)]/12 text-[var(--amber)]",
  PATCH: "bg-[var(--amber)]/12 text-[var(--amber)]",
  DELETE: "bg-[var(--rose)]/12 text-[var(--rose)]",
};

const STATUS_BADGE: Record<string, string> = {
  parsed: "bg-[var(--green)]/10 border-[var(--green)]/20 text-[var(--green)]",
  complete: "bg-[var(--green)]/10 border-[var(--green)]/20 text-[var(--green)]",
  failed: "bg-[var(--rose)]/10 border-[var(--rose)]/20 text-[var(--rose)]",
};

export default function ServiceDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: service, isLoading } = useService(id);
  const { data: projects } = useProjects();
  const [activeTab, setActiveTab] = useState<Tab>("Mindmap");
  const [selectedRoute, setSelectedRoute] = useState<Subcommand | null>(null);
  const deleteService = useDeleteService();
  const router = useRouter();

  if (isLoading || !service) {
    return (
      <div>
        <div className="h-4 w-48 bg-[var(--surface)] rounded animate-pulse mb-6" />
        <div className="h-8 w-64 bg-[var(--surface)] rounded animate-pulse mb-4" />
        <div className="h-[500px] bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius)] animate-pulse" />
      </div>
    );
  }

  const projectName = projects?.find((p) => p.id === service.project_id)?.name || "Project";
  const subcommands = service.route_graph?.subcommands || [];
  const routeCount = subcommands.length;

  return (
    <div>
      {/* Breadcrumb */}
      <Breadcrumb items={[
        { label: "Projects", href: "/projects" },
        { label: projectName, href: `/projects/${service.project_id}` },
        { label: service.name },
      ]} />

      {/* Service header */}
      <div className="flex items-center justify-between mb-2">
        <h1 className="font-[family-name:var(--font-jetbrains-mono)] text-xl font-bold">{service.name}</h1>
        <AlertDialog>
          <AlertDialogTrigger className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[var(--rose)] hover:bg-[var(--rose)]/10 font-[family-name:var(--font-jetbrains-mono)] text-xs cursor-pointer transition-colors border border-[var(--rose)]/20">
              <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
              </svg>
              Delete
          </AlertDialogTrigger>
          <AlertDialogContent className="bg-[var(--elevated)] border-[var(--border)]">
            <AlertDialogHeader>
              <AlertDialogTitle className="font-[family-name:var(--font-jetbrains-mono)] text-[var(--text)]">Delete {service.name}?</AlertDialogTitle>
              <AlertDialogDescription className="text-[var(--text-dim)]">This will permanently delete this service and all its data.</AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel className="text-[var(--text-dim)]">Cancel</AlertDialogCancel>
              <AlertDialogAction
                onClick={() => {
                  deleteService.mutate(service.id, { onSuccess: () => router.push(`/projects/${service.project_id}`) });
                }}
                className="bg-[var(--rose)] text-white hover:bg-[var(--rose)]/80"
              >
                Delete
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>

      {/* Service meta */}
      <div className="flex items-center gap-3 font-[family-name:var(--font-jetbrains-mono)] text-xs text-[var(--text-dim)] mb-6">
        <span className={`px-2 py-0.5 rounded-full border text-[10px] font-semibold ${STATUS_BADGE[service.status] || "bg-[var(--text-muted)]/10 border-[var(--text-muted)]/20 text-[var(--text-muted)]"}`}>
          {service.status}
        </span>
        {service.framework && (
          <span className="px-2 py-0.5 rounded bg-[var(--violet)]/10 border border-[var(--violet)]/20 text-[var(--violet)] text-[10px] font-semibold uppercase">
            {service.framework}
          </span>
        )}
        {service.repo_url && (
          <a href={service.repo_url} target="_blank" rel="noopener noreferrer" className="hover:text-[var(--accent)] transition-colors">
            {service.repo_url.replace(/^https?:\/\//, "")}
          </a>
        )}
        {routeCount > 0 && <span>{routeCount} routes</span>}
      </div>

      {/* Tabs */}
      <div className="flex gap-0 border-b border-[var(--border)] mb-6">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`font-[family-name:var(--font-jetbrains-mono)] text-[13px] font-medium px-5 py-3 border-b-2 transition-all ${
              activeTab === tab
                ? "text-[var(--accent)] border-[var(--accent)]"
                : "text-[var(--text-dim)] border-transparent hover:text-[var(--text)]"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Tab panels */}
      {activeTab === "Mindmap" && <MindmapPanel service={service} onSelectRoute={setSelectedRoute} />}
      {activeTab === "Routes" && <RoutesPanel subcommands={subcommands} />}
      {activeTab === "Generate" && <GeneratePanel serviceId={service.id} serviceName={service.name} serviceStatus={service.status} baseUrl={service.route_graph?.base_url} artifactId={service.artifact_id} />}
      {activeTab === "Config" && <ConfigPanel routeGraph={service.route_graph} />}
      {activeTab === "Host" && <HostPanel serviceName={service.name} />}
    </div>
  );
}

// ── Mindmap Tab ──
function MindmapPanel({ service, onSelectRoute }: { service: any; onSelectRoute: (r: Subcommand) => void }) {
  if (!service.route_graph || (service.status !== "parsed" && service.status !== "complete")) {
    const isFailed = service.status === "failed" || service.status === "timed_out";
    return (
      <div className="h-[500px] bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius)] flex flex-col items-center justify-center gap-3">
        {isFailed ? (
          <>
            <div className="w-10 h-10 rounded-full bg-[var(--rose)]/10 flex items-center justify-center">
              <svg className="w-5 h-5 text-[var(--rose)]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" /><path d="M15 9l-6 6M9 9l6 6" />
              </svg>
            </div>
            <p className="text-[var(--text-dim)] font-[family-name:var(--font-jetbrains-mono)] text-sm">Parsing failed</p>
            {service.error_message && (
              <p className="text-[var(--text-muted)] text-xs max-w-md text-center">{service.error_message}</p>
            )}
          </>
        ) : (
          <>
            <div className="w-10 h-10 rounded-full bg-[var(--accent)]/10 flex items-center justify-center animate-pulse">
              <svg className="w-5 h-5 text-[var(--accent)]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
              </svg>
            </div>
            <p className="text-[var(--text-dim)] font-[family-name:var(--font-jetbrains-mono)] text-sm">
              {service.status === "cloning" ? "Cloning repository..." : service.status === "parsing" ? "Parsing routes..." : "Processing..."}
            </p>
            <p className="text-[var(--text-muted)] text-xs">Polling every 3s — graph will appear automatically</p>
          </>
        )}
      </div>
    );
  }

  return <RouteMindmap routeGraph={service.route_graph} onRouteClick={onSelectRoute} />;
}

// ── Routes Tab ──
function RoutesPanel({ subcommands }: { subcommands: Subcommand[] }) {
  if (subcommands.length === 0) {
    return <p className="text-[var(--text-muted)] font-[family-name:var(--font-jetbrains-mono)] text-sm py-8 text-center">No routes parsed yet.</p>;
  }

  return (
    <div className="border border-[var(--border)] rounded-[var(--radius)] overflow-hidden">
      <table className="w-full border-collapse">
        <thead>
          <tr>
            <th className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] font-semibold text-[var(--text-muted)] text-left px-4 py-2.5 bg-[var(--surface)] border-b border-[var(--border)] uppercase tracking-wider">Method</th>
            <th className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] font-semibold text-[var(--text-muted)] text-left px-4 py-2.5 bg-[var(--surface)] border-b border-[var(--border)] uppercase tracking-wider">Path</th>
            <th className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] font-semibold text-[var(--text-muted)] text-left px-4 py-2.5 bg-[var(--surface)] border-b border-[var(--border)] uppercase tracking-wider">Params</th>
            <th className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] font-semibold text-[var(--text-muted)] text-left px-4 py-2.5 bg-[var(--surface)] border-b border-[var(--border)] uppercase tracking-wider">Description</th>
          </tr>
        </thead>
        <tbody>
          {subcommands.map((cmd, i) => (
            <tr key={i} className="hover:bg-white/[0.02]">
              <td className="px-4 py-3 border-b border-[var(--border)]">
                <span className={`font-[family-name:var(--font-jetbrains-mono)] text-[10px] font-bold px-2 py-0.5 rounded uppercase ${METHOD_COLORS[cmd.method.toUpperCase()] || "bg-[var(--text-muted)]/10 text-[var(--text-muted)]"}`}>
                  {cmd.method}
                </span>
              </td>
              <td className="font-[family-name:var(--font-jetbrains-mono)] text-xs text-[var(--text)] px-4 py-3 border-b border-[var(--border)]">{cmd.endpoint}</td>
              <td className="font-[family-name:var(--font-jetbrains-mono)] text-xs text-[var(--text-dim)] px-4 py-3 border-b border-[var(--border)]">{cmd.params?.length || 0}</td>
              <td className="text-[13px] text-[var(--text-dim)] px-4 py-3 border-b border-[var(--border)]">{cmd.description || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Generate Tab ──
function GeneratePanel({ serviceId, serviceName, serviceStatus, baseUrl, artifactId }: { serviceId: string; serviceName: string; serviceStatus: string; baseUrl?: string; artifactId?: string | null }) {
  const [outputTypes, setOutputTypes] = useState<string[]>(["cli"]);
  const [cliName, setCliName] = useState(serviceName.toLowerCase().replace(/[^a-z0-9_]/g, "_").replace(/^[^a-z]/, "a"));
  const generate = useGenerate();

  const isGenerating = ["generating", "packaging"].includes(serviceStatus);
  const isComplete = serviceStatus === "complete";
  const isBusy = generate.isPending || isGenerating;

  function toggleOutput(type: string) {
    setOutputTypes((prev) => prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]);
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {/* Config */}
      <div className="bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius)] p-6">
        <h3 className="font-[family-name:var(--font-jetbrains-mono)] text-sm font-semibold mb-5">Configuration</h3>

        <div className="mb-4">
          <label className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-[var(--text-muted)] uppercase tracking-wider block mb-2">Output Type</label>
          <div className="flex flex-col gap-2">
            {["cli", "mcp"].map((type) => (
              <label key={type} className={`flex items-center gap-2.5 cursor-pointer px-3 py-2.5 bg-[var(--surface)] border rounded-lg transition-colors ${outputTypes.includes(type) ? "border-[var(--accent)]/30" : "border-[var(--border)]"}`}>
                <input type="checkbox" checked={outputTypes.includes(type)} onChange={() => toggleOutput(type)} className="accent-[var(--accent)] w-4 h-4" />
                <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-[var(--text)]">
                  {type === "cli" ? "CLI (pip package)" : "MCP Server"}
                </span>
              </label>
            ))}
          </div>
        </div>

        <div className="mb-4">
          <label className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-[var(--text-muted)] uppercase tracking-wider block mb-1.5">CLI Name</label>
          <input value={cliName} onChange={(e) => setCliName(e.target.value)} className="w-full px-3 py-2.5 bg-[var(--surface)] border border-[var(--border)] rounded-lg text-[var(--text)] font-[family-name:var(--font-jetbrains-mono)] text-[13px] outline-none focus:border-[var(--accent)] transition-colors" />
        </div>

        <Button
          onClick={() => generate.mutate({ serviceId, outputTypes, cliName, baseUrl: baseUrl || "http://localhost:8000" })}
          disabled={isBusy || outputTypes.length === 0}
          className="w-full bg-[var(--accent)] text-[var(--bg)] hover:bg-[var(--accent-bright)] font-[family-name:var(--font-jetbrains-mono)] text-xs font-semibold justify-center"
        >
          {isBusy ? (
            <>
              <svg className="w-3.5 h-3.5 mr-1.5 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
              </svg>
              {serviceStatus === "packaging" ? "Packaging..." : "Generating..."}
            </>
          ) : (
            <>
              <svg className="w-3.5 h-3.5 mr-1.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" /></svg>
              Generate
            </>
          )}
        </Button>
      </div>

      {/* Output */}
      <div className="bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius)] p-6">
        {isBusy ? (
          <div className="flex flex-col items-center justify-center h-full gap-3 py-8">
            <div className="w-10 h-10 rounded-full bg-[var(--accent)]/10 flex items-center justify-center animate-pulse">
              <svg className="w-5 h-5 text-[var(--accent)]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
              </svg>
            </div>
            <p className="text-[var(--text)] font-[family-name:var(--font-jetbrains-mono)] text-sm">
              {serviceStatus === "packaging" ? "Packaging your CLI..." : "Generating packages..."}
            </p>
            <p className="text-[var(--text-muted)] text-xs">This usually takes a few seconds</p>
          </div>
        ) : isComplete && artifactId ? (
          <>
            <h3 className="font-[family-name:var(--font-jetbrains-mono)] text-sm font-semibold mb-1 text-[var(--text)]">Generation complete!</h3>
            <p className="text-xs text-[var(--text)] mb-4">Your package is ready to download.</p>
            <pre className="font-[family-name:var(--font-jetbrains-mono)] text-xs text-[var(--text)] bg-[var(--bg)] p-4 rounded-lg overflow-x-auto leading-relaxed">
{`# Install:
pip install ./${cliName}.zip

# Usage:
${cliName} --help`}
            </pre>
            <a
              href={`/api/artifacts/${artifactId}/download`}
              className="mt-3 w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-[var(--accent)] text-[var(--bg)] rounded-lg hover:bg-[var(--accent-bright)] transition-colors font-[family-name:var(--font-jetbrains-mono)] text-xs font-semibold"
            >
              <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" /></svg>
              Download ZIP
            </a>
          </>
        ) : (
          <>
            <h3 className="font-[family-name:var(--font-jetbrains-mono)] text-sm font-semibold mb-1 text-[var(--text)]">Output</h3>
            <p className="text-xs text-[var(--text)] mb-4">Select output types and click Generate</p>
            <pre className="font-[family-name:var(--font-jetbrains-mono)] text-xs text-[var(--text)] bg-[var(--bg)] p-4 rounded-lg overflow-x-auto leading-relaxed">
{`# After generation:
pip install ./${cliName}.zip

# Usage:
${cliName} --help`}
            </pre>
          </>
        )}
      </div>
    </div>
  );
}

// ── Config Tab ──
function ConfigPanel({ routeGraph }: { routeGraph: any }) {
  // Build detected vars from route_graph
  const detectedVars = useMemo(() => {
    const vars: { key: string; defaultValue: string; source: string }[] = [];

    if (routeGraph?.base_url) {
      vars.push({ key: "BASE_URL", defaultValue: routeGraph.base_url, source: "route_graph" });
    } else {
      vars.push({ key: "BASE_URL", defaultValue: "", source: "required" });
    }

    if (routeGraph?.auth?.env_var) {
      vars.push({ key: routeGraph.auth.env_var, defaultValue: "", source: `auth (${routeGraph.auth.type})` });
    }

    return vars;
  }, [routeGraph]);

  const [values, setValues] = useState<Record<string, string>>(() => {
    const initial: Record<string, string> = {};
    detectedVars.forEach((v) => { initial[v.key] = v.defaultValue; });
    return initial;
  });

  const [customVars, setCustomVars] = useState<{ key: string; value: string }[]>([]);

  return (
    <div className="space-y-4">
      {/* Detected variables */}
      <div className="bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius)] p-6">
        <div className="flex items-center justify-between mb-1.5">
          <h3 className="font-[family-name:var(--font-jetbrains-mono)] text-sm font-semibold">Detected Variables</h3>
          <span className="px-2 py-0.5 text-[10px] font-[family-name:var(--font-jetbrains-mono)] font-semibold rounded bg-[var(--amber)]/10 border border-[var(--amber)]/20 text-[var(--amber)]">{detectedVars.length} detected</span>
        </div>
        <p className="text-xs text-[var(--text-dim)] mb-5">These environment variables were detected from the parsed routes. Please add values if anything is missing.</p>
        <div className="flex flex-col gap-3">
          {detectedVars.map((v) => (
            <div key={v.key} className="flex gap-2 items-center">
              <input value={v.key} readOnly className="w-[200px] px-3 py-2.5 bg-[var(--surface)] border border-[var(--border)] rounded-lg text-[var(--text)] font-[family-name:var(--font-jetbrains-mono)] text-xs" />
              <input
                placeholder="Enter value..."
                value={values[v.key] || ""}
                onChange={(e) => setValues((prev) => ({ ...prev, [v.key]: e.target.value }))}
                className="flex-1 px-3 py-2.5 bg-[var(--surface)] border border-[var(--border)] rounded-lg text-[var(--text)] font-[family-name:var(--font-jetbrains-mono)] text-xs outline-none focus:border-[var(--accent)] placeholder:text-[var(--text-muted)]"
              />
              <span className="px-2 py-0.5 text-[9px] font-[family-name:var(--font-jetbrains-mono)] font-semibold rounded bg-[var(--green)]/10 border border-[var(--green)]/20 text-[var(--green)] whitespace-nowrap">detected</span>
            </div>
          ))}
        </div>
      </div>

      {/* Custom variables */}
      <div className="bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius)] p-6">
        <div className="flex items-center justify-between mb-1.5">
          <h3 className="font-[family-name:var(--font-jetbrains-mono)] text-sm font-semibold">Custom Variables</h3>
          <button
            onClick={() => setCustomVars((prev) => [...prev, { key: "", value: "" }])}
            className="inline-flex items-center gap-1 px-2 py-1 text-[var(--text-dim)] hover:text-[var(--text)] font-[family-name:var(--font-jetbrains-mono)] text-xs transition-colors"
          >
            <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M12 5v14M5 12h14" /></svg>
            Add
          </button>
        </div>
        <p className="text-xs text-[var(--text-dim)] mb-5">Add any additional key-value pairs your CLI or MCP server needs.</p>
        <div className="flex flex-col gap-3">
          {customVars.map((v, i) => (
            <div key={i} className="flex gap-2 items-center">
              <input
                placeholder="KEY"
                value={v.key}
                onChange={(e) => setCustomVars((prev) => prev.map((item, j) => j === i ? { ...item, key: e.target.value.toUpperCase() } : item))}
                className="w-[200px] px-3 py-2.5 bg-[var(--surface)] border border-[var(--border)] rounded-lg text-[var(--text)] font-[family-name:var(--font-jetbrains-mono)] text-xs uppercase outline-none focus:border-[var(--accent)] placeholder:text-[var(--text-muted)]"
              />
              <input
                placeholder="value"
                value={v.value}
                onChange={(e) => setCustomVars((prev) => prev.map((item, j) => j === i ? { ...item, value: e.target.value } : item))}
                className="flex-1 px-3 py-2.5 bg-[var(--surface)] border border-[var(--border)] rounded-lg text-[var(--text)] font-[family-name:var(--font-jetbrains-mono)] text-xs outline-none focus:border-[var(--accent)] placeholder:text-[var(--text-muted)]"
              />
              <button
                onClick={() => setCustomVars((prev) => prev.filter((_, j) => j !== i))}
                className="text-[var(--rose)] hover:text-[var(--rose)]/80 text-lg px-2 transition-colors"
              >
                &times;
              </button>
            </div>
          ))}
          {customVars.length === 0 && (
            <p className="text-[var(--text-muted)] text-xs font-[family-name:var(--font-jetbrains-mono)]">No custom variables yet.</p>
          )}
        </div>
      </div>

      <div className="flex justify-end">
        <Button className="bg-[var(--accent)] text-[var(--bg)] hover:bg-[var(--accent-bright)] font-[family-name:var(--font-jetbrains-mono)] text-xs font-semibold">
          <svg className="w-3.5 h-3.5 mr-1.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z" /><path d="M17 21v-8H7v8M7 3v5h8" /></svg>
          Save Config
        </Button>
      </div>
    </div>
  );
}

// ── Host Tab ──
function HostPanel({ serviceName }: { serviceName: string }) {
  const [selectedHost, setSelectedHost] = useState("cloudflare");
  const cliName = serviceName.toLowerCase().replace(/[^a-z0-9_-]/g, "-");

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div className="bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius)] p-6">
        <h3 className="font-[family-name:var(--font-jetbrains-mono)] text-sm font-semibold mb-1.5">Deploy</h3>
        <p className="text-xs text-[var(--text-dim)] mb-5">Deploy to a connected hosting platform or publish to a package registry.</p>

        <div className="mb-4">
          <label className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-[var(--text-muted)] uppercase tracking-wider block mb-2">Deploy To</label>
          <div className="flex gap-2 flex-wrap">
            {[
              { id: "cloudflare", label: "Cloudflare", icon: "https://cdn.simpleicons.org/cloudflare/F38020" },
              { id: "pypi", label: "PyPI", icon: "https://cdn.simpleicons.org/pypi/3775A9" },
            ].map((host) => (
              <button
                key={host.id}
                onClick={() => setSelectedHost(host.id)}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-lg border font-[family-name:var(--font-jetbrains-mono)] text-xs transition-all ${
                  selectedHost === host.id
                    ? "border-[var(--accent)] text-[var(--accent)] bg-[var(--accent)]/10"
                    : "border-[var(--border)] text-[var(--text-dim)] hover:border-[var(--text-muted)] hover:text-[var(--text)]"
                }`}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={host.icon} width={20} height={20} alt="" />
                {host.label}
              </button>
            ))}
          </div>
          <a href="/app-store" className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-[var(--text)] hover:text-[var(--accent)] no-underline mt-2 inline-block transition-colors">
            Connect more at App Store &rarr;
          </a>
        </div>

        <Button className="w-full bg-[var(--accent)] text-[var(--bg)] hover:bg-[var(--accent-bright)] font-[family-name:var(--font-jetbrains-mono)] text-xs font-semibold justify-center">
          <svg className="w-3.5 h-3.5 mr-1.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" /></svg>
          Deploy to {selectedHost === "cloudflare" ? "Cloudflare" : "PyPI"}
        </Button>
      </div>

      <div className="bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius)] p-6">
        {selectedHost === "cloudflare" ? (
          <>
            <h3 className="font-[family-name:var(--font-jetbrains-mono)] text-sm font-semibold mb-1">Hosted Endpoint</h3>
            <p className="text-xs text-[var(--text-dim)] mb-4">Your MCP server will be live at:</p>
            <pre className="font-[family-name:var(--font-jetbrains-mono)] text-xs text-[var(--text-dim)] bg-[var(--bg)] p-4 rounded-lg overflow-x-auto leading-relaxed">
{`https://${cliName}.genalpha.dev/mcp

# Add to Claude Desktop config:
{
  "mcpServers": {
    "${cliName}": {
      "url": "https://${cliName}.genalpha.dev/mcp"
    }
  }
}`}
            </pre>
          </>
        ) : (
          <>
            <h3 className="font-[family-name:var(--font-jetbrains-mono)] text-sm font-semibold mb-1">Install & Run</h3>
            <p className="text-xs text-[var(--text-dim)] mb-4">Your stdio MCP server via pip:</p>
            <pre className="font-[family-name:var(--font-jetbrains-mono)] text-xs text-[var(--text-dim)] bg-[var(--bg)] p-4 rounded-lg overflow-x-auto leading-relaxed">
{`pip install ${cliName}-mcp

# Add to Claude Desktop config:
{
  "mcpServers": {
    "${cliName}": {
      "command": "${cliName}-mcp",
      "args": ["--base-url", "https://api.example.com"]
    }
  }
}`}
            </pre>
          </>
        )}
        <div className="flex gap-2 mt-3">
          <button className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 border border-[var(--border)] rounded-lg text-[var(--text-dim)] hover:text-[var(--text)] hover:border-[var(--text-muted)] transition-colors font-[family-name:var(--font-jetbrains-mono)] text-xs">
            Copy Config
          </button>
          <button className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 border border-[var(--border)] rounded-lg text-[var(--text-dim)] hover:text-[var(--text)] hover:border-[var(--text-muted)] transition-colors font-[family-name:var(--font-jetbrains-mono)] text-xs">
            Share
          </button>
        </div>
      </div>
    </div>
  );
}
