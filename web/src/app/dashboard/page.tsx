import { auth } from "@/auth";
import { redirect } from "next/navigation";
import { db } from "@/db";
import { workspaceMembers, services } from "@/db/schema";
import { eq, and, notInArray } from "drizzle-orm";

export default async function DashboardPage() {
  const session = await auth();
  if (!session?.user?.id) redirect("/");

  const membership = await db.query.workspaceMembers.findFirst({
    where: eq(workspaceMembers.userId, session.user.id),
    with: {
      workspace: {
        with: {
          projects: {
            with: {
              services: {
                columns: {
                  id: true,
                  name: true,
                  repoUrl: true,
                  status: true,
                  framework: true,
                  metadata: true,
                  createdAt: true,
                },
              },
            },
          },
        },
      },
    },
  });

  if (!membership) redirect("/");

  const workspace = membership.workspace;
  const allServices = workspace.projects.flatMap((p) => p.services);
  const activeServiceCount = allServices.filter(
    (s) => !["failed", "timed_out", "pending", "cloning", "parsing"].includes(s.status)
  ).length;

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold font-[family-name:var(--font-geist-mono)]">
            Dashboard
          </h1>
          <p className="text-zinc-500 mt-1">
            {activeServiceCount}/2 service slots used
          </p>
        </div>
      </div>

      {workspace.projects.length === 0 ? (
        <div className="text-center py-20">
          <p className="text-4xl text-zinc-700 font-[family-name:var(--font-geist-mono)]">
            {"{ }"}
          </p>
          <p className="mt-4 text-zinc-400">No projects yet.</p>
          <p className="text-zinc-600 text-sm mt-1">
            Create a project to start parsing API repos.
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          {workspace.projects.map((project) => (
            <div
              key={project.id}
              className="border border-zinc-800 rounded-lg p-6"
            >
              <div className="flex items-center justify-between mb-4">
                <a
                  href={`/dashboard/projects/${project.id}`}
                  className="text-lg font-medium hover:text-teal-400 transition-colors"
                >
                  {project.name}
                </a>
                <span className="text-xs text-zinc-600">
                  {project.services.length} service
                  {project.services.length !== 1 ? "s" : ""}
                </span>
              </div>

              {project.services.length === 0 ? (
                <p className="text-sm text-zinc-600">
                  No services yet. Paste a GitHub URL to get started.
                </p>
              ) : (
                <div className="space-y-2">
                  {project.services.map((service) => (
                    <div
                      key={service.id}
                      className="flex items-center justify-between px-4 py-3 bg-zinc-900 rounded-md"
                    >
                      <div className="flex items-center gap-3">
                        <StatusBadge status={service.status} />
                        <div>
                          <p className="text-sm font-medium">{service.name}</p>
                          {service.repoUrl && (
                            <p className="text-xs text-zinc-600 font-[family-name:var(--font-geist-mono)]">
                              {service.repoUrl}
                            </p>
                          )}
                        </div>
                      </div>
                      {service.framework && (
                        <span className="text-xs text-zinc-500 bg-zinc-800 px-2 py-1 rounded">
                          {service.framework}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    pending: "bg-zinc-600",
    cloning: "bg-amber-500",
    parsing: "bg-amber-500",
    parsed: "bg-teal-500",
    generating: "bg-blue-500",
    packaging: "bg-blue-500",
    complete: "bg-emerald-500",
    failed: "bg-rose-500",
    timed_out: "bg-rose-500",
  };

  return (
    <span
      className={`inline-block w-2 h-2 rounded-full ${colors[status] || "bg-zinc-600"}`}
      title={status}
    />
  );
}
