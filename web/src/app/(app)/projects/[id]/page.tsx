"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useProjects, useCreateService, useServiceStatus, useServicesByProject, useDeleteService } from "@/data/hooks";
import type { ServiceStatusValue } from "@/data/types";
import Link from "next/link";

export default function ProjectPage() {
  const { id } = useParams<{ id: string }>();
  const { data: projects, isLoading } = useProjects();
  const { data: services, isLoading: servicesLoading } = useServicesByProject(id);
  const router = useRouter();

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

  const activeCount = services?.filter(
    (s) => ["parsed", "generating", "packaging", "complete"].includes(s.status)
  ).length ?? 0;

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

      <ParseForm projectId={project.id} activeServiceCount={activeCount} />

      {/* Service list */}
      {servicesLoading ? (
        <div className="space-y-2 mt-6">
          {[1, 2].map((i) => (
            <div key={i} className="h-16 bg-zinc-900 rounded-lg animate-pulse" />
          ))}
        </div>
      ) : services && services.length > 0 ? (
        <div className="mt-8">
          <h2 className="text-sm font-medium text-zinc-400 mb-3">
            Services ({services.length})
          </h2>
          <div className="space-y-2">
            {services.map((service) => (
              <ServiceRow key={service.id} service={service} />
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function ServiceRow({ service }: { service: { id: string; name: string; repo_url: string | null; status: string; framework: string | null; error_message: string | null; created_at: string } }) {
  const deleteService = useDeleteService();
  const [confirmDelete, setConfirmDelete] = useState(false);

  function handleDelete() {
    if (!confirmDelete) {
      setConfirmDelete(true);
      setTimeout(() => setConfirmDelete(false), 3000);
      return;
    }
    deleteService.mutate(service.id);
  }

  return (
    <div className="flex items-center justify-between px-4 py-3 bg-zinc-900 rounded-lg">
      <Link
        href={`/services/${service.id}`}
        className="flex items-center gap-3 flex-1 min-w-0 hover:text-teal-400 transition-colors"
      >
        <StatusDot status={service.status} />
        <div className="min-w-0">
          <p className="text-sm font-medium truncate">{service.name}</p>
          {service.repo_url && (
            <p className="text-xs text-zinc-600 font-[family-name:var(--font-geist-mono)] truncate">
              {service.repo_url}
            </p>
          )}
        </div>
      </Link>
      <div className="flex items-center gap-3 ml-4">
        {service.framework && (
          <span className="text-xs text-zinc-500 bg-zinc-800 px-2 py-0.5 rounded">
            {service.framework}
          </span>
        )}
        <span className="text-xs text-zinc-600">{service.status}</span>
        <button
          onClick={handleDelete}
          disabled={deleteService.isPending}
          className={`text-xs px-2 py-1 rounded transition-colors ${
            confirmDelete
              ? "bg-rose-500/20 text-rose-400"
              : "text-zinc-600 hover:text-rose-400 hover:bg-zinc-800"
          }`}
        >
          {confirmDelete ? "Confirm?" : deleteService.isPending ? "..." : "Delete"}
        </button>
      </div>
    </div>
  );
}

function ParseForm({ projectId, activeServiceCount }: { projectId: string; activeServiceCount: number }) {
  const [repoUrl, setRepoUrl] = useState("");
  const createService = useCreateService();
  const [serviceId, setServiceId] = useState<string | null>(null);
  const router = useRouter();

  const { data: status } = useServiceStatus(serviceId);
  const atLimit = activeServiceCount >= 2;

  if (status?.status === "parsed" && serviceId) {
    setTimeout(() => router.push(`/services/${serviceId}`), 1000);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!repoUrl.trim()) return;

    createService.mutate(
      { repo_url: repoUrl, project_id: projectId },
      {
        onSuccess: (data) => setServiceId(data.serviceId),
      },
    );
  }

  if (serviceId && status) {
    return (
      <div className="max-w-md">
        <h3 className="text-sm font-medium text-zinc-400 mb-4">
          Parsing {repoUrl.split("/").pop()}...
        </h3>
        <ProgressSteps status={status.status as ServiceStatusValue} />
        {status.status === "parsed" && (
          <p className="mt-4 text-sm text-teal-400">Redirecting to mindmap...</p>
        )}
        {status.status === "failed" && (
          <div className="mt-4 p-3 bg-rose-500/10 border border-rose-500/20 rounded-md">
            <p className="text-sm text-rose-400">Parsing failed</p>
            <p className="text-xs text-rose-300/70 mt-1">{status.error_message}</p>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="mb-4">
      <h2 className="text-sm font-medium text-zinc-400 mb-3">Add a service</h2>
      <form onSubmit={handleSubmit} className="flex gap-3 max-w-xl">
        <input
          type="text"
          value={repoUrl}
          onChange={(e) => setRepoUrl(e.target.value)}
          placeholder="https://github.com/owner/repo"
          className="flex-1 bg-zinc-900 border border-zinc-800 rounded-lg px-4 py-3 text-sm font-[family-name:var(--font-geist-mono)] text-zinc-50 placeholder:text-zinc-600 focus:outline-none focus:ring-2 focus:ring-teal-500/50 focus:border-teal-500"
          disabled={createService.isPending || atLimit}
        />
        <button
          type="submit"
          disabled={createService.isPending || !repoUrl.trim() || atLimit}
          className="rounded-lg bg-teal-500 px-5 py-3 text-sm font-medium text-zinc-950 hover:bg-teal-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
        >
          {createService.isPending ? "Starting..." : "Parse"}
        </button>
      </form>
      <p className="mt-2 text-xs text-zinc-600">
        {activeServiceCount}/2 service slots used
        {atLimit && " — delete a service to free up a slot"}
      </p>
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

function StatusDot({ status }: { status: string }) {
  const colors: Record<string, string> = {
    pending: "bg-zinc-600",
    cloning: "bg-amber-500 animate-pulse",
    parsing: "bg-amber-500 animate-pulse",
    parsed: "bg-teal-500",
    generating: "bg-blue-500 animate-pulse",
    packaging: "bg-blue-500 animate-pulse",
    complete: "bg-emerald-500",
    failed: "bg-rose-500",
    timed_out: "bg-rose-500",
  };

  return (
    <span
      className={`inline-block w-2.5 h-2.5 rounded-full flex-shrink-0 ${colors[status] || "bg-zinc-600"}`}
      title={status}
    />
  );
}
