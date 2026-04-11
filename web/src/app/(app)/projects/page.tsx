"use client";

import { useState } from "react";
import { useProjects, useCreateProject } from "@/data/hooks";
import Link from "next/link";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function ProjectsPage() {
  const { data: projects, isLoading } = useProjects();
  const [search, setSearch] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const createProject = useCreateProject();

  const filtered = projects?.filter((p) =>
    p.name.toLowerCase().includes(search.toLowerCase())
  );

  async function handleCreate() {
    if (!newName.trim()) return;
    await createProject.mutateAsync({ name: newName, description: newDesc || undefined });
    setNewName("");
    setNewDesc("");
    setShowCreate(false);
  }

  return (
    <div>
      {/* Page header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <h1 className="font-[family-name:var(--font-jetbrains-mono)] text-xl font-bold">
            Projects
          </h1>
          <div className="relative">
            <svg className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[var(--text-muted)]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8" /><path d="m21 21-4.3-4.3" />
            </svg>
            <input
              type="text"
              placeholder="Search projects..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-60 pl-8 pr-3 py-1.5 bg-[var(--surface)] border border-[var(--border)] rounded-lg text-[var(--text)] font-[family-name:var(--font-jetbrains-mono)] text-xs outline-none focus:border-[var(--accent)] transition-colors placeholder:text-[var(--text-muted)]"
            />
          </div>
        </div>
        <Button
          onClick={() => setShowCreate(true)}
          className="bg-[var(--accent)] text-[var(--bg)] hover:bg-[var(--accent-bright)] font-[family-name:var(--font-jetbrains-mono)] text-xs font-semibold"
        >
          <svg className="w-3.5 h-3.5 mr-1.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M12 5v14M5 12h14" />
          </svg>
          New Project
        </Button>
      </div>

      {/* Project grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="aspect-square bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius)] animate-pulse" />
          ))}
        </div>
      ) : filtered && filtered.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {filtered.map((project) => (
            <Link
              key={project.id}
              href={`/projects/${project.id}`}
              className="group aspect-square bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius)] p-5 flex flex-col no-underline hover:border-[rgba(20,184,166,0.2)] hover:-translate-y-0.5 hover:shadow-[0_4px_24px_rgba(0,0,0,0.3)] transition-all duration-200"
            >
              {/* Centered icon + name */}
              <div className="flex-1 flex flex-col items-center justify-center gap-3">
                <div
                  className="shrink-0 rounded-xl flex items-center justify-center"
                  style={{ width: 56, height: 56, backgroundColor: "rgba(20,184,166,0.1)", color: "var(--accent)" }}
                >
                  <svg className="w-7 h-7" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
                  </svg>
                </div>
                <span className="font-[family-name:var(--font-jetbrains-mono)] text-sm font-semibold text-[var(--text)] text-center">
                  {project.name}
                </span>
              </div>

              {/* Bottom: description */}
              {project.description && (
                <div className="mt-auto text-[11px] text-[var(--text-dim)] line-clamp-2 text-center">
                  {project.description}
                </div>
              )}
            </Link>
          ))}

          {/* New project card */}
          <button
            onClick={() => setShowCreate(true)}
            className="aspect-square bg-[var(--surface)] border border-dashed border-[var(--border)] rounded-[var(--radius)] flex flex-col items-center justify-center gap-2 hover:border-[var(--accent)] transition-colors cursor-pointer"
          >
            <span className="text-2xl text-[var(--text-muted)]">+</span>
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-xs text-[var(--text-muted)]">
              New Project
            </span>
          </button>
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-20">
          <p className="text-[var(--text-muted)] font-[family-name:var(--font-jetbrains-mono)] text-sm mb-4">
            {search ? "No projects match your search." : "No projects yet. Create your first project."}
          </p>
          {!search && (
            <Button
              onClick={() => setShowCreate(true)}
              className="bg-[var(--accent)] text-[var(--bg)] hover:bg-[var(--accent-bright)] font-[family-name:var(--font-jetbrains-mono)] text-xs"
            >
              Create Project
            </Button>
          )}
        </div>
      )}

      {/* Create project dialog */}
      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent className="bg-[var(--elevated)] border-[var(--border)] text-[var(--text)]">
          <DialogHeader>
            <DialogTitle className="font-[family-name:var(--font-jetbrains-mono)]">New Project</DialogTitle>
            <DialogDescription className="text-[var(--text-dim)]">
              Create a project to organize your parsed services.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 mt-2">
            <div>
              <label className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-[var(--text-muted)] uppercase tracking-wider block mb-1.5">
                Project Name
              </label>
              <Input
                placeholder="e.g. API v2 Migration"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                className="bg-[var(--surface)] border-[var(--border)] text-[var(--text)] font-[family-name:var(--font-jetbrains-mono)] text-sm"
                onKeyDown={(e) => e.key === "Enter" && handleCreate()}
              />
            </div>
            <div>
              <label className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-[var(--text-muted)] uppercase tracking-wider block mb-1.5">
                Description
              </label>
              <Input
                placeholder="Optional description"
                value={newDesc}
                onChange={(e) => setNewDesc(e.target.value)}
                className="bg-[var(--surface)] border-[var(--border)] text-[var(--text)] font-[family-name:var(--font-jetbrains-mono)] text-sm"
                onKeyDown={(e) => e.key === "Enter" && handleCreate()}
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="ghost" onClick={() => setShowCreate(false)} className="text-[var(--text-dim)]">
                Cancel
              </Button>
              <Button
                onClick={handleCreate}
                disabled={!newName.trim() || createProject.isPending}
                className="bg-[var(--accent)] text-[var(--bg)] hover:bg-[var(--accent-bright)]"
              >
                {createProject.isPending ? "Creating..." : "Create Project"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
