"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useProjects, useCreateService, useServiceStatus } from "@/data/hooks";
import type { ServiceStatusValue } from "@/data/types";
import Link from "next/link";

export default function ProjectPage() {
  const { id } = useParams<{ id: string }>();
  const { data: projects, isLoading } = useProjects();
  const router = useRouter();

  // Find this project from the projects list
  // TODO: Add useProject(id) hook when Core has a single-project endpoint
  const project = projects?.find((p) => p.id === id);

  if (isLoading) {
    return (
      <div>
        <div className="h-8 w-48 bg-zinc-800 rounded animate-pulse" />
        <div className="mt-6 h-32 bg-zinc-800 rounded animate-pulse" />
      </div>
    );
  }

  if (!project) {
    return (
      <div className="text-center py-20">
        <p className="text-zinc-400">Project not found</p>
        <Link href="/dashboard" className="text-teal-400 text-sm mt-2 inline-block">
          Back to dashboard
        </Link>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold font-[family-name:var(--font-geist-mono)]">
          {project.name}
        </h1>
        {project.description && (
          <p className="text-zinc-500 mt-1 text-sm">{project.description}</p>
        )}
      </div>

      <ParseForm projectId={project.id} />

      {/* TODO: Service list will be added when Core returns services with projects */}
    </div>
  );
}

function ParseForm({ projectId }: { projectId: string }) {
  const [repoUrl, setRepoUrl] = useState("");
  const createService = useCreateService();
  const [serviceId, setServiceId] = useState<string | null>(null);
  const router = useRouter();

  const { data: status } = useServiceStatus(serviceId);

  // Auto-navigate when parsed
  if (status?.status === "parsed" && serviceId) {
    setTimeout(() => router.push(`/services/${serviceId}`), 1000);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!repoUrl.trim()) return;

    createService.mutate(
      { repo_url: repoUrl, project_id: projectId },
      {
        onSuccess: (data) => {
          setServiceId(data.serviceId);
        },
      },
    );
  }

  // Show progress if parsing
  if (serviceId && status) {
    return (
      <div className="max-w-md">
        <h3 className="text-sm font-medium text-zinc-400 mb-4">
          Parsing {repoUrl.split("/").pop()}...
        </h3>
        <ProgressSteps status={status.status} />
        {status.status === "parsed" && (
          <p className="mt-4 text-sm text-teal-400">Redirecting to mindmap...</p>
        )}
        {status.status === "failed" && (
          <div className="mt-4 p-3 bg-rose-500/10 border border-rose-500/20 rounded-md">
            <p className="text-sm text-rose-400">Parsing failed</p>
            <p className="text-xs text-rose-300/70 mt-1">{status.errorMessage}</p>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="mb-8">
      <h2 className="text-sm font-medium text-zinc-400 mb-3">Add a service</h2>
      <form onSubmit={handleSubmit} className="flex gap-3 max-w-xl">
        <input
          type="text"
          value={repoUrl}
          onChange={(e) => setRepoUrl(e.target.value)}
          placeholder="https://github.com/owner/repo"
          className="flex-1 bg-zinc-900 border border-zinc-800 rounded-lg px-4 py-3 text-sm font-[family-name:var(--font-geist-mono)] text-zinc-50 placeholder:text-zinc-600 focus:outline-none focus:ring-2 focus:ring-teal-500/50 focus:border-teal-500"
          disabled={createService.isPending}
        />
        <button
          type="submit"
          disabled={createService.isPending || !repoUrl.trim()}
          className="rounded-lg bg-teal-500 px-5 py-3 text-sm font-medium text-zinc-950 hover:bg-teal-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
        >
          {createService.isPending ? "Starting..." : "Parse"}
        </button>
      </form>
      {createService.isError && (
        <p className="mt-2 text-sm text-rose-400">
          {createService.error?.message || "Failed to start parsing"}
        </p>
      )}
    </div>
  );
}

const PARSE_STEPS = [
  { key: "cloning", label: "Cloning repository" },
  { key: "parsing", label: "Parsing routes" },
  { key: "parsed", label: "Done" },
] as const;

function ProgressSteps({ status }: { status: ServiceStatusValue }) {
  const currentIdx = PARSE_STEPS.findIndex((s) => s.key === status);

  return (
    <div className="space-y-3">
      {PARSE_STEPS.map((step, i) => {
        const isComplete = i < currentIdx || status === "parsed";
        const isActive = step.key === status && status !== "parsed";

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
            <span
              className={`text-sm ${
                isComplete ? "text-teal-400" : isActive ? "text-zinc-50" : "text-zinc-600"
              }`}
            >
              {step.label}
            </span>
          </div>
        );
      })}
    </div>
  );
}
