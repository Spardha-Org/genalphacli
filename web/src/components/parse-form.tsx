"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useServiceStatus } from "@/hooks/use-service-status";
import { ProgressStepper } from "@/components/progress-stepper";

interface ParseFormProps {
  projectId: string;
  activeServiceCount: number;
  maxServices: number;
}

type SourceTab = "github" | "pypi";

export function ParseForm({ projectId, activeServiceCount, maxServices }: ParseFormProps) {
  const [tab, setTab] = useState<SourceTab>("github");
  const [repoUrl, setRepoUrl] = useState("");
  const [packageName, setPackageName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [serviceId, setServiceId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const router = useRouter();

  const { status } = useServiceStatus(serviceId);

  const atLimit = activeServiceCount >= maxServices;

  // Auto-navigate to service detail when parsing completes
  if (status?.status === "parsed" && serviceId) {
    setTimeout(() => {
      router.push(`/dashboard/services/${serviceId}`);
    }, 1000);
  }

  async function handleGitHubSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      const res = await fetch("/api/parse", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repoUrl, projectId }),
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.error || "Failed to start parsing");
        return;
      }

      setServiceId(data.serviceId);
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handlePyPISubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      const res = await fetch("/api/parse/pypi", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ packageName: packageName.trim(), projectId }),
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.error || data.detail || "Failed to start parsing");
        return;
      }

      setServiceId(data.serviceId);
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  // Show progress if parsing started
  if (serviceId && status) {
    const label = tab === "github"
      ? repoUrl.split("/").pop()
      : packageName;

    return (
      <div className="max-w-md">
        <h3 className="text-sm font-medium text-zinc-400 mb-4">
          Parsing {label}...
        </h3>
        <ProgressStepper
          currentStatus={status.status}
          errorMessage={status.errorMessage}
          mode="parse"
          sourceType={tab}
        />
        {status.status === "parsed" && (
          <p className="mt-4 text-sm text-teal-400">
            Redirecting to mindmap view...
          </p>
        )}
      </div>
    );
  }

  return (
    <div className="max-w-xl">
      {/* Source type tabs */}
      <div className="flex gap-1 mb-4 bg-zinc-900 rounded-lg p-1 w-fit">
        <button
          type="button"
          onClick={() => { setTab("github"); setError(null); }}
          className={`px-4 py-1.5 text-sm rounded-md transition-colors ${
            tab === "github"
              ? "bg-zinc-800 text-zinc-50"
              : "text-zinc-500 hover:text-zinc-300"
          }`}
        >
          GitHub
        </button>
        <button
          type="button"
          onClick={() => { setTab("pypi"); setError(null); }}
          className={`px-4 py-1.5 text-sm rounded-md transition-colors ${
            tab === "pypi"
              ? "bg-zinc-800 text-zinc-50"
              : "text-zinc-500 hover:text-zinc-300"
          }`}
        >
          PyPI
        </button>
      </div>

      {/* GitHub form */}
      {tab === "github" && (
        <form onSubmit={handleGitHubSubmit}>
          <div className="flex gap-3">
            <input
              type="text"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              placeholder="https://github.com/owner/repo"
              className="flex-1 bg-zinc-900 border border-zinc-800 rounded-lg px-4 py-3 text-sm font-[family-name:var(--font-geist-mono)] text-zinc-50 placeholder:text-zinc-600 focus:outline-none focus:ring-2 focus:ring-teal-500/50 focus:border-teal-500"
              disabled={submitting || atLimit}
            />
            <button
              type="submit"
              disabled={submitting || !repoUrl.trim() || atLimit}
              className="rounded-lg bg-teal-500 px-5 py-3 text-sm font-medium text-zinc-950 hover:bg-teal-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
            >
              {submitting ? "Starting..." : "Parse"}
            </button>
          </div>
        </form>
      )}

      {/* PyPI form */}
      {tab === "pypi" && (
        <form onSubmit={handlePyPISubmit}>
          <div className="flex gap-3">
            <input
              type="text"
              value={packageName}
              onChange={(e) => setPackageName(e.target.value)}
              placeholder="e.g., fastapi"
              className="flex-1 bg-zinc-900 border border-zinc-800 rounded-lg px-4 py-3 text-sm font-[family-name:var(--font-geist-mono)] text-zinc-50 placeholder:text-zinc-600 focus:outline-none focus:ring-2 focus:ring-teal-500/50 focus:border-teal-500"
              disabled={submitting || atLimit}
            />
            <button
              type="submit"
              disabled={submitting || !packageName.trim() || atLimit}
              className="rounded-lg bg-teal-500 px-5 py-3 text-sm font-medium text-zinc-950 hover:bg-teal-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
            >
              {submitting ? "Starting..." : "Parse"}
            </button>
          </div>
        </form>
      )}

      <p className="mt-2 text-xs text-zinc-600">
        {activeServiceCount}/{maxServices} service slots used
        {atLimit && " — delete a service to free up a slot"}
      </p>

      {error && (
        <p className="mt-2 text-sm text-rose-400">{error}</p>
      )}
    </div>
  );
}
