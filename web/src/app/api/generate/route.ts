import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/auth";
import { db } from "@/db";
import { services, workspaceMembers } from "@/db/schema";
import { eq, and } from "drizzle-orm";
import { getTemporalClient, TASK_QUEUES } from "@/lib/temporal";

export async function POST(request: NextRequest) {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const body = await request.json();
  const { serviceId, outputTypes, cliName, baseUrl } = body;

  if (!serviceId || !outputTypes?.length || !cliName || !baseUrl) {
    return NextResponse.json({ error: "Missing required fields" }, { status: 400 });
  }

  // Validate CLI name
  if (!/^[a-z][a-z0-9_]*$/.test(cliName)) {
    return NextResponse.json(
      { error: "CLI name must start with a letter and contain only lowercase letters, numbers, and underscores" },
      { status: 400 }
    );
  }

  // Get service with ownership check
  const service = await db.query.services.findFirst({
    where: eq(services.id, serviceId),
    with: { project: true },
  });

  if (!service) {
    return NextResponse.json({ error: "Service not found" }, { status: 404 });
  }

  const membership = await db.query.workspaceMembers.findFirst({
    where: and(
      eq(workspaceMembers.userId, session.user.id),
      eq(workspaceMembers.workspaceId, service.project.workspaceId)
    ),
  });

  if (!membership) {
    return NextResponse.json({ error: "Not authorized" }, { status: 403 });
  }

  // Must be in "parsed" or "complete" status to generate
  if (!["parsed", "complete"].includes(service.status)) {
    return NextResponse.json(
      { error: `Cannot generate from status: ${service.status}` },
      { status: 400 }
    );
  }

  if (!service.routeGraph) {
    return NextResponse.json({ error: "No route graph available" }, { status: 400 });
  }

  // Start GenerateWorkflow with deterministic ID
  const workflowId = `generate-${service.id}`;

  try {
    // Update status to generating
    await db
      .update(services)
      .set({
        status: "generating",
        generateWorkflowId: workflowId,
        updatedAt: new Date(),
      })
      .where(eq(services.id, service.id));

    const client = await getTemporalClient();
    await client.workflow.start("GenerateWorkflow", {
      taskQueue: TASK_QUEUES.GENERATE,
      workflowId,
      args: [
        {
          route_graph: service.routeGraph,
          cli_name: cliName,
          base_url: baseUrl,
          output_types: outputTypes,
          service_id: service.id,
        },
      ],
      workflowExecutionTimeout: "5 minutes",
    });

    return NextResponse.json({
      serviceId: service.id,
      workflowId,
      status: "generating",
    });
  } catch (error) {
    await db
      .update(services)
      .set({
        status: "failed",
        errorMessage: `Failed to start generation: ${error instanceof Error ? error.message : "Unknown error"}`,
        updatedAt: new Date(),
      })
      .where(eq(services.id, service.id));

    return NextResponse.json(
      { error: "Failed to start generation. Please try again." },
      { status: 503 }
    );
  }
}
