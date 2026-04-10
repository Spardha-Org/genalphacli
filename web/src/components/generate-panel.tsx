"use client";

import { useState } from "react";
import { useServiceStatus } from "@/hooks/use-service-status";
import { ProgressStepper } from "./progress-stepper";

interface GeneratePanelProps {
  serviceId: string;
  serviceName: string;
  detectedBaseUrl?: string;
  onGenerated?: () => void;
}

export function GeneratePanel({
  serviceId,
  serviceName,
  detectedBaseUrl,
  onGenerated,
}: GeneratePanelProps) {
  const [outputTypes, setOutputTypes] = useState<string[]>(["cli", "mcp"]);
  const [cliName, setCliName] = useState(
    serviceName.toLowerCase().replace(/[^a-z0-9_]/g, "_")
  );
  const [baseUrl, setBaseUrl] = useState(detectedBaseUrl || "http://localhost:8000");
  const [generating, setGenerating] = useState(false);
  const [generatingServiceId, setGeneratingServiceId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);

  const { status } = useServiceStatus(generatingServiceId);

  // Check if generation completed
  if (status?.status === "complete" && !downloadUrl) {
    setDownloadUrl(`/api/services/${serviceId}/download`);
    onGenerated?.();
  }

  async function handleGenerate() {
    setError(null);
    setGenerating(true);

    try {
      const res = await fetch("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          serviceId,
          outputTypes,
          cliName,
          baseUrl,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.error || "Failed to start generation");
        return;
      }

      setGeneratingServiceId(serviceId);
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setGenerating(false);
    }
  }

  function toggleOutputType(type: string) {
    setOutputTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    );
  }

  // Show progress if generating
  if (generatingServiceId && status && !["complete", "failed"].includes(status.status)) {
    return (
      <div className="p-4">
        <ProgressStepper
          currentStatus={status.status}
          errorMessage={status.errorMessage}
          mode="generate"
        />
      </div>
    );
  }

  // Show download button if complete
  if (downloadUrl) {
    return (
      <div className="p-4 text-center">
        <p className="text-teal-400 text-sm mb-3">Generation complete!</p>
        <a
          href={downloadUrl}
          className="inline-flex items-center gap-2 bg-teal-500 text-zinc-950 px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-teal-400 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          Download {cliName}.zip
        </a>
      </div>
    );
  }

  return (
    <div className="p-4 space-y-4">
      {/* Output type selector */}
      <div>
        <p className="text-xs text-zinc-500 uppercase tracking-wider mb-2">Output type</p>
        <div className="flex gap-2">
          {["cli", "mcp"].map((type) => (
            <button
              key={type}
              onClick={() => toggleOutputType(type)}
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

      {/* CLI name */}
      <div>
        <label className="text-xs text-zinc-500 uppercase tracking-wider mb-1 block">
          CLI name
        </label>
        <input
          type="text"
          value={cliName}
          onChange={(e) => setCliName(e.target.value)}
          className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-3 py-2 text-sm font-[family-name:var(--font-geist-mono)] text-zinc-200 focus:outline-none focus:ring-1 focus:ring-teal-500/50"
        />
      </div>

      {/* Base URL */}
      <div>
        <label className="text-xs text-zinc-500 uppercase tracking-wider mb-1 block">
          Base URL
        </label>
        <input
          type="text"
          value={baseUrl}
          onChange={(e) => setBaseUrl(e.target.value)}
          className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-3 py-2 text-sm font-[family-name:var(--font-geist-mono)] text-zinc-200 focus:outline-none focus:ring-1 focus:ring-teal-500/50"
        />
      </div>

      {/* Generate button */}
      <button
        onClick={handleGenerate}
        disabled={generating || outputTypes.length === 0 || !cliName.trim()}
        className="w-full bg-teal-500 text-zinc-950 py-2.5 rounded-lg text-sm font-medium hover:bg-teal-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {generating ? "Starting..." : "Generate"}
      </button>

      {error && <p className="text-sm text-rose-400">{error}</p>}
    </div>
  );
}
