"use client";

import { useProjects } from "@/data/hooks";
import Link from "next/link";

export default function DashboardPage() {
  const { data: projects, isLoading } = useProjects();

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold font-[family-name:var(--font-geist-mono)]">
          Dashboard
        </h1>
      </div>

      {isLoading ? (
        <div className="space-y-4">
          {[1, 2].map((i) => (
            <div key={i} className="h-24 bg-zinc-900 border border-zinc-800 rounded-lg animate-pulse" />
          ))}
        </div>
      ) : !projects || projects.length === 0 ? (
        <div className="text-center py-20">
          <p className="text-4xl text-zinc-700 font-[family-name:var(--font-geist-mono)]">
            {"{ }"}
          </p>
          <p className="mt-4 text-zinc-400">No projects yet.</p>
          <p className="text-zinc-600 text-sm mt-1">
            Projects group your parsed APIs. Create one to get started.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {projects.map((project) => (
            <Link
              key={project.id}
              href={`/projects/${project.id}`}
              className="block border border-zinc-800 rounded-lg p-6 hover:bg-zinc-900 transition-colors"
            >
              <h2 className="text-lg font-medium hover:text-teal-400 transition-colors">
                {project.name}
              </h2>
              {project.description && (
                <p className="text-sm text-zinc-500 mt-1">{project.description}</p>
              )}
              <p className="text-xs text-zinc-600 mt-2">
                Created {new Date(project.created_at).toLocaleDateString()}
              </p>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
