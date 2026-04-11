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
              className="group aspect-square bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius)] overflow-hidden no-underline hover:border-[var(--accent)] hover:-translate-y-0.5 hover:shadow-[0_4px_24px_rgba(0,0,0,0.3)] transition-all duration-200 relative"
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={`https://picsum.photos/seed/${project.id}/200/200`}
                alt=""
                className="absolute inset-0 w-full h-full object-cover opacity-40 group-hover:opacity-60 transition-opacity"
              />
              {/* Gradient overlay for text readability */}
              <div className="absolute inset-0 bg-gradient-to-t from-[var(--bg)] via-[var(--bg)]/40 to-transparent" />
              {/* Content overlay */}
              <div className="absolute bottom-0 left-0 right-0 p-4">
                <div className="font-[family-name:var(--font-jetbrains-mono)] text-sm font-bold text-[var(--text)] truncate">
                  {project.name}
                </div>
                {project.description && (
                  <div className="text-[11px] text-[var(--text-dim)] mt-1 line-clamp-2">
                    {project.description}
                  </div>
                )}
              </div>
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
