"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useProjects, useCreateService, useServiceStatus, useServicesByProject, useDeleteService } from "@/data/hooks";
import type { ServiceStatusValue } from "@/data/types";
import Link from "next/link";
import { Breadcrumb } from "@/components/dashboard/breadcrumb";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";

const STATUS_BADGE: Record<string, string> = {
  parsed: "bg-[var(--green)]/10 border-[var(--green)]/20 text-[var(--green)]",
  complete: "bg-[var(--green)]/10 border-[var(--green)]/20 text-[var(--green)]",
  cloning: "bg-[var(--amber)]/10 border-[var(--amber)]/20 text-[var(--amber)]",
  parsing: "bg-[var(--amber)]/10 border-[var(--amber)]/20 text-[var(--amber)]",
  generating: "bg-[var(--amber)]/10 border-[var(--amber)]/20 text-[var(--amber)]",
  packaging: "bg-[var(--amber)]/10 border-[var(--amber)]/20 text-[var(--amber)]",
  failed: "bg-[var(--rose)]/10 border-[var(--rose)]/20 text-[var(--rose)]",
  timed_out: "bg-[var(--rose)]/10 border-[var(--rose)]/20 text-[var(--rose)]",
  pending: "bg-[var(--text-muted)]/10 border-[var(--text-muted)]/20 text-[var(--text-muted)]",
};

export default function ProjectPage() {
  const { id } = useParams<{ id: string }>();
  const { data: projects, isLoading } = useProjects();
  const { data: services, isLoading: servicesLoading } = useServicesByProject(id);
  const [showAddService, setShowAddService] = useState(false);
  const [repoUrl, setRepoUrl] = useState("");
  const createService = useCreateService();
  const router = useRouter();

  const project = projects?.find((p) => p.id === id);

  if (isLoading) {
    return (
      <div>
        <div className="h-4 w-48 bg-[var(--surface)] rounded animate-pulse mb-6" />
        <div className="h-8 w-64 bg-[var(--surface)] rounded animate-pulse mb-8" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2].map((i) => (
            <div key={i} className="aspect-square bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius)] animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="text-center py-20">
        <p className="text-[var(--text-muted)]">Project not found</p>
        <Link href="/projects" className="text-[var(--accent)] text-sm mt-2 inline-block">
          Back to projects
        </Link>
      </div>
    );
  }

  const activeCount = services?.filter(
    (s) => ["parsed", "generating", "packaging", "complete"].includes(s.status)
  ).length ?? 0;

  async function handleAddService() {
    if (!repoUrl.trim()) return;
    createService.mutate(
      { repo_url: repoUrl, project_id: id },
      {
        onSuccess: (data) => {
          setShowAddService(false);
          setRepoUrl("");
          router.push(`/services/${data.serviceId}`);
        },
      },
    );
  }

  return (
    <div>
      <Breadcrumb items={[
        { label: "Projects", href: "/projects" },
        { label: project.name },
      ]} />

      {/* Page header — matches HTML preview */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="font-[family-name:var(--font-jetbrains-mono)] text-xl font-bold">
            {project.name}
          </h1>
          {project.description && (
            <p className="text-sm text-[var(--text-dim)] mt-1">{project.description}</p>
          )}
        </div>
        <div className="flex items-center gap-4">
          {/* Slot indicator */}
          <div className="flex items-center gap-2 font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-[var(--text-muted)]">
            <span>{activeCount}/{services?.length ?? 0} slots</span>
            <div className="w-[60px] h-1 bg-[var(--border)] rounded-full overflow-hidden">
              <div
                className="h-full bg-[var(--accent)] rounded-full transition-all"
                style={{ width: services?.length ? `${(activeCount / Math.max(services.length, 1)) * 100}%` : "0%" }}
              />
            </div>
          </div>
          <Button
            onClick={() => setShowAddService(true)}
            className="bg-[var(--accent)] text-[var(--bg)] hover:bg-[var(--accent-bright)] font-[family-name:var(--font-jetbrains-mono)] text-xs font-semibold"
          >
            <svg className="w-3.5 h-3.5 mr-1.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M12 5v14M5 12h14" />
            </svg>
            Add Service
          </Button>
        </div>
      </div>

      {/* Service cards grid — matches HTML preview */}
      {servicesLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2].map((i) => (
            <div key={i} className="aspect-square bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius)] animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {services?.map((service) => {
            const isInProgress = ["cloning", "parsing", "generating", "packaging"].includes(service.status);

            return (
              <Link
                key={service.id}
                href={`/services/${service.id}`}
                className={`aspect-square bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius)] p-5 flex flex-col no-underline hover:border-[rgba(20,184,166,0.2)] hover:-translate-y-0.5 hover:shadow-[0_4px_24px_rgba(0,0,0,0.3)] transition-all duration-200 ${
                  isInProgress ? "opacity-70" : ""
                }`}
              >
                {/* Header: name + status */}
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <svg className="w-4 h-4 shrink-0 text-[var(--text-dim)]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22" />
                    </svg>
                    <span className="font-[family-name:var(--font-jetbrains-mono)] text-sm font-semibold text-[var(--text)] truncate">
                      {service.name}
                    </span>
                  </div>
                  <span className={`shrink-0 px-2 py-0.5 text-[10px] font-[family-name:var(--font-jetbrains-mono)] font-semibold rounded-full border ${STATUS_BADGE[service.status] || STATUS_BADGE.pending}`}>
                    {isInProgress ? `${service.status}...` : service.status}
                  </span>
                </div>

                {/* Repo URL */}
                {service.repo_url && (
                  <div className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-[var(--text-muted)] truncate mb-3">
                    {service.repo_url.replace(/^https?:\/\//, "")}
                  </div>
                )}

                {/* Tags at bottom */}
                <div className="flex gap-2 flex-wrap mt-auto">
                  {service.framework && (
                    <span className="px-2 py-0.5 text-[10px] font-[family-name:var(--font-jetbrains-mono)] font-semibold rounded bg-[var(--violet)]/10 border border-[var(--violet)]/20 text-[var(--violet)] uppercase">
                      {service.framework}
                    </span>
                  )}
                  {isInProgress && !service.framework && (
                    <span className="px-2 py-0.5 text-[10px] font-[family-name:var(--font-jetbrains-mono)] font-semibold rounded bg-[var(--text-muted)]/10 border border-[var(--text-muted)]/20 text-[var(--text-muted)]">
                      detecting framework...
                    </span>
                  )}
                </div>
              </Link>
            );
          })}

          {/* Dashed "Parse a repo" card */}
          <button
            onClick={() => setShowAddService(true)}
            className="aspect-square bg-[var(--surface)] border border-dashed border-[var(--border)] rounded-[var(--radius)] flex flex-col items-center justify-center gap-2 hover:border-[var(--accent)] transition-colors cursor-pointer"
          >
            <span className="text-xl text-[var(--text-muted)]">+</span>
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-[var(--text-muted)]">
              Parse a repo
            </span>
          </button>
        </div>
      )}

      {/* Add Service Dialog */}
      <Dialog open={showAddService} onOpenChange={setShowAddService}>
        <DialogContent className="bg-[var(--elevated)] border-[var(--border)] text-[var(--text)]">
          <DialogHeader>
            <DialogTitle className="font-[family-name:var(--font-jetbrains-mono)]">Add Service</DialogTitle>
            <DialogDescription className="text-[var(--text-dim)]">
              Parse a repository to extract API routes.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 mt-2">
            <div>
              <label className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-[var(--text-muted)] uppercase tracking-wider block mb-1.5">
                Repository URL
              </label>
              <Input
                placeholder="https://github.com/owner/repo"
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
                className="bg-[var(--surface)] border-[var(--border)] text-[var(--text)] font-[family-name:var(--font-jetbrains-mono)] text-sm"
                onKeyDown={(e) => e.key === "Enter" && handleAddService()}
              />
            </div>

            {createService.isError && (
              <p className="text-sm text-[var(--rose)]">
                {createService.error?.message || "Failed to start parsing"}
              </p>
            )}

            <div className="flex justify-end gap-2 pt-2">
              <Button variant="ghost" onClick={() => setShowAddService(false)} className="text-[var(--text-dim)]">
                Cancel
              </Button>
              <Button
                onClick={handleAddService}
                disabled={!repoUrl.trim() || createService.isPending}
                className="bg-[var(--accent)] text-[var(--bg)] hover:bg-[var(--accent-bright)]"
              >
                {createService.isPending ? "Starting..." : "Parse"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
