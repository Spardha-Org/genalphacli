import { auth } from "@/auth";
import { redirect } from "next/navigation";
import { db } from "@/db";
import { services, workspaceMembers } from "@/db/schema";
import { eq, and } from "drizzle-orm";
import { ServiceDetail } from "./service-detail";

export default async function ServicePage({
  params,
}: {
  params: Promise<{ serviceId: string }>;
}) {
  const session = await auth();
  if (!session?.user?.id) redirect("/");

  const { serviceId } = await params;

  const service = await db.query.services.findFirst({
    where: eq(services.id, serviceId),
    with: { project: true },
  });

  if (!service) redirect("/dashboard");

  // Verify ownership
  const membership = await db.query.workspaceMembers.findFirst({
    where: and(
      eq(workspaceMembers.userId, session.user.id),
      eq(workspaceMembers.workspaceId, service.project.workspaceId)
    ),
  });

  if (!membership) redirect("/dashboard");

  return (
    <ServiceDetail
      service={{
        id: service.id,
        name: service.name,
        repoUrl: service.repoUrl,
        status: service.status,
        framework: service.framework,
        routeGraph: service.routeGraph as Record<string, unknown> | null,
        errorMessage: service.errorMessage,
        downloadUrl: service.downloadUrl,
        metadata: service.metadata as Record<string, unknown> | null,
        createdAt: service.createdAt.toISOString(),
      }}
    />
  );
}
