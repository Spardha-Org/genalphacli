import { auth } from "@/auth";
import { redirect } from "next/navigation";
import { db } from "@/db";
import { projects, services, workspaceMembers } from "@/db/schema";
import { eq, and, sql } from "drizzle-orm";
import { ParseForm } from "@/components/parse-form";

export default async function ProjectPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const session = await auth();
  if (!session?.user?.id) redirect("/");

  const { projectId } = await params;

  const membership = await db.query.workspaceMembers.findFirst({
    where: eq(workspaceMembers.userId, session.user.id),
    with: { workspace: true },
  });

  if (!membership) redirect("/");

  const project = await db.query.projects.findFirst({
    where: and(
      eq(projects.id, projectId),
      eq(projects.workspaceId, membership.workspace.id)
    ),
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
          errorMessage: true,
        },
      },
    },
  });

  if (!project) redirect("/dashboard");

  // Count active services across workspace
  const activeStatuses = ["parsed", "generating", "packaging", "complete"];
  const activeCount = await db
    .select({ count: sql<number>`count(*)` })
    .from(services)
    .innerJoin(projects, eq(services.projectId, projects.id))
    .where(
      and(
        eq(projects.workspaceId, membership.workspace.id),
        sql`${services.status} = ANY(${activeStatuses})`
      )
    );

  const activeServiceCount = Number(activeCount[0]?.count ?? 0);

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

      {/* Parse form */}
      <div className="mb-8">
        <h2 className="text-sm font-medium text-zinc-400 mb-3">
          Add a service
        </h2>
        <ParseForm
          projectId={project.id}
          activeServiceCount={activeServiceCount}
          maxServices={2}
        />
      </div>

      {/* Service list */}
      {project.services.length > 0 && (
        <div>
          <h2 className="text-sm font-medium text-zinc-400 mb-3">
            Services ({project.services.length})
          </h2>
          <div className="space-y-2">
            {project.services.map((service) => (
              <a
                key={service.id}
                href={`/dashboard/services/${service.id}`}
                className="flex items-center justify-between px-4 py-3 bg-zinc-900 rounded-lg hover:bg-zinc-800 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <StatusDot status={service.status} />
                  <div>
                    <p className="text-sm font-medium">{service.name}</p>
                    <p className="text-xs text-zinc-600 font-[family-name:var(--font-geist-mono)]">
                      {service.repoUrl}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {service.framework && (
                    <span className="text-xs text-zinc-500 bg-zinc-800 px-2 py-1 rounded">
                      {service.framework}
                    </span>
                  )}
                  <span className="text-xs text-zinc-600">{service.status}</span>
                </div>
              </a>
            ))}
          </div>
        </div>
      )}
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
      className={`inline-block w-2.5 h-2.5 rounded-full ${colors[status] || "bg-zinc-600"}`}
      title={status}
    />
  );
}
