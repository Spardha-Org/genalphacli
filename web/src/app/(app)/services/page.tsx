"use client";

import { useState } from "react";
import Link from "next/link";
import { useAllServices, useProjects } from "@/data/hooks";

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

export default function ServicesListPage() {
  const { data: services, isLoading } = useAllServices();
  const { data: projects } = useProjects();
  const [search, setSearch] = useState("");

  const filtered = services?.filter((s) =>
    s.name.toLowerCase().includes(search.toLowerCase()) ||
    s.repo_url?.toLowerCase().includes(search.toLowerCase())
  );

  function getProjectName(projectId: string): string {
    return projects?.find((p) => p.id === projectId)?.name || "Unknown";
  }

  function shortUrl(url: string | null): string {
    if (!url) return "";
    return url.replace(/^https?:\/\//, "");
  }

  function statusLabel(status: string): string {
    if (status === "parsing") return "parsing...";
    if (status === "generating") return "generating...";
    if (status === "packaging") return "packaging...";
    if (status === "cloning") return "cloning...";
    return status;
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <h1 className="font-[family-name:var(--font-jetbrains-mono)] text-xl font-bold">Services</h1>
          <div className="relative">
            <svg className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[var(--text-muted)]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8" /><path d="m21 21-4.3-4.3" />
            </svg>
            <input
              type="text"
              placeholder="Search services..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-60 pl-8 pr-3 py-1.5 bg-[var(--surface)] border border-[var(--border)] rounded-lg text-[var(--text)] font-[family-name:var(--font-jetbrains-mono)] text-xs outline-none focus:border-[var(--accent)] transition-colors placeholder:text-[var(--text-muted)]"
            />
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="aspect-square bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius)] animate-pulse" />
          ))}
        </div>
      ) : filtered && filtered.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((service) => {
            const isInProgress = ["cloning", "parsing", "generating", "packaging"].includes(service.status);

            return (
              <Link
                key={service.id}
                href={`/services/${service.id}`}
                className={`aspect-square bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius)] p-5 flex flex-col no-underline hover:border-[rgba(20,184,166,0.2)] hover:-translate-y-0.5 hover:shadow-[0_4px_24px_rgba(0,0,0,0.3)] transition-all duration-200 ${
                  isInProgress ? "opacity-70" : ""
                }`}
              >
                {/* Header: name + status badge */}
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
                    {statusLabel(service.status)}
                  </span>
                </div>

                {/* Repo URL */}
                <div className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-[var(--text-muted)] truncate mb-3">
                  {shortUrl(service.repo_url)}
                </div>

                {/* Tags pushed to bottom */}
                <div className="flex gap-2 flex-wrap mt-auto">
                  {service.framework && (
                    <span className="px-2 py-0.5 text-[10px] font-[family-name:var(--font-jetbrains-mono)] font-semibold rounded bg-[var(--violet)]/10 border border-[var(--violet)]/20 text-[var(--violet)]">
                      {service.framework}
                    </span>
                  )}
                  <span className="px-2 py-0.5 text-[10px] font-[family-name:var(--font-jetbrains-mono)] font-semibold rounded bg-[var(--cyan)]/10 border border-[var(--cyan)]/20 text-[var(--cyan)]">
                    {getProjectName(service.project_id)}
                  </span>
                </div>
              </Link>
            );
          })}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-20">
          <p className="text-[var(--text-muted)] font-[family-name:var(--font-jetbrains-mono)] text-sm">
            {search ? "No services match your search." : "No services yet. Parse a repo from a project to get started."}
          </p>
        </div>
      )}
    </div>
  );
}
