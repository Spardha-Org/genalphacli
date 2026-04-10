import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/auth";
import { db } from "@/db";
import { services, projects, workspaceMembers } from "@/db/schema";
import { eq, and, notInArray, sql } from "drizzle-orm";
import { parseGitHubUrl } from "@/lib/github-url";
import { getTemporalClient, TASK_QUEUES } from "@/lib/temporal";

export async function POST(request: NextRequest) {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const body = await request.json();
  const { repoUrl, projectId } = body;

  // Validate GitHub URL (SSRF prevention)
  if (!repoUrl || typeof repoUrl !== "string") {
    return NextResponse.json({ error: "repoUrl is required" }, { status: 400 });
  }

  const parsed = parseGitHubUrl(repoUrl);
  if (!parsed) {
    return NextResponse.json(
      { error: "Invalid GitHub URL. Format: https://github.com/owner/repo" },
      { status: 400 }
    );
  }

  // Validate project belongs to user's workspace
  if (!projectId || typeof projectId !== "string") {
    return NextResponse.json({ error: "projectId is required" }, { status: 400 });
  }

  const membership = await db.query.workspaceMembers.findFirst({
    where: eq(workspaceMembers.userId, session.user.id),
    with: { workspace: true },
  });

  if (!membership) {
    return NextResponse.json({ error: "No workspace found" }, { status: 403 });
  }

  const project = await db.query.projects.findFirst({
    where: and(
      eq(projects.id, projectId),
      eq(projects.workspaceId, membership.workspace.id)
    ),
  });

  if (!project) {
    return NextResponse.json({ error: "Project not found" }, { status: 404 });
  }

  // Check service limit (2 per workspace)
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

  if (Number(activeCount[0]?.count ?? 0) >= 2) {
    return NextResponse.json(
      { error: "Service limit reached (2 per workspace). Delete a service to free up a slot." },
      { status: 429 }
    );
  }

  // Create service record
  const serviceName = parsed.repo;
  const serviceId = crypto.randomUUID().replace(/-/g, "").slice(0, 24);

  const [service] = await db
    .insert(services)
    .values({
      id: serviceId,
      projectId,
      name: serviceName,
      repoUrl,
      status: "cloning",
    })
    .returning();

  // Start ParseWorkflow with deterministic ID for idempotency
  const workflowId = `parse-${service.id}`;

  try {
    const client = await getTemporalClient();
    await client.workflow.start("ParseWorkflow", {
      taskQueue: TASK_QUEUES.PARSE,
      workflowId,
      args: [
        {
          owner: parsed.owner,
          repo: parsed.repo,
          user_id: session.user.id,
          service_id: service.id,
          command_name: parsed.repo,
        },
      ],
      workflowExecutionTimeout: "5 minutes",
    });

    // Update service with workflow ID
    await db
      .update(services)
      .set({ parseWorkflowId: workflowId })
      .where(eq(services.id, service.id));
  } catch (error) {
    // If workflow start fails, mark service as failed
    await db
      .update(services)
      .set({
        status: "failed",
        errorMessage: `Failed to start parse workflow: ${error instanceof Error ? error.message : "Unknown error"}`,
      })
      .where(eq(services.id, service.id));

    return NextResponse.json(
      { error: "Failed to start parsing. Please try again." },
      { status: 503 }
    );
  }

  return NextResponse.json({
    serviceId: service.id,
    workflowId,
    status: "cloning",
  });
}
