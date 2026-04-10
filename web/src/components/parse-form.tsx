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

export function ParseForm({ projectId, activeServiceCount, maxServices }: ParseFormProps) {
  const [repoUrl, setRepoUrl] = useState("");
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

  async function handleSubmit(e: React.FormEvent) {
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

  // Show progress if parsing started
  if (serviceId && status) {
    return (
      <div className="max-w-md">
        <h3 className="text-sm font-medium text-zinc-400 mb-4">
          Parsing {repoUrl.split("/").pop()}...
        </h3>
        <ProgressStepper
          currentStatus={status.status}
          errorMessage={status.errorMessage}
          mode="parse"
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
    <form onSubmit={handleSubmit} className="max-w-xl">
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

      <p className="mt-2 text-xs text-zinc-600">
        {activeServiceCount}/{maxServices} service slots used
        {atLimit && " — delete a service to free up a slot"}
      </p>

      {error && (
        <p className="mt-2 text-sm text-rose-400">{error}</p>
      )}
    </form>
  );
}
