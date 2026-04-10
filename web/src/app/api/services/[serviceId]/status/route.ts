import { NextRequest } from "next/server";
import { auth } from "@/auth";
import { db } from "@/db";
import { services, workspaceMembers } from "@/db/schema";
import { eq, and } from "drizzle-orm";

const TERMINAL_STATES = ["parsed", "complete", "failed", "timed_out"];
const POLL_INTERVAL_MS = 3000;

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ serviceId: string }> }
) {
  const session = await auth();
  if (!session?.user?.id) {
    return new Response("Unauthorized", { status: 401 });
  }

  const { serviceId } = await params;

  // Verify ownership before streaming
  const service = await db.query.services.findFirst({
    where: eq(services.id, serviceId),
    columns: { id: true, projectId: true, status: true },
    with: { project: { columns: { workspaceId: true } } },
  });

  if (!service) {
    return new Response("Not found", { status: 404 });
  }

  const membership = await db.query.workspaceMembers.findFirst({
    where: and(
      eq(workspaceMembers.userId, session.user.id),
      eq(workspaceMembers.workspaceId, service.project.workspaceId)
    ),
  });

  if (!membership) {
    return new Response("Forbidden", { status: 403 });
  }

  // SSE stream — polls DB for status changes
  const encoder = new TextEncoder();

  const stream = new ReadableStream({
    async start(controller) {
      let lastStatus = "";

      const poll = async () => {
        try {
          const current = await db.query.services.findFirst({
            where: eq(services.id, serviceId),
            columns: {
              status: true,
              errorMessage: true,
              framework: true,
              metadata: true,
            },
          });

          if (!current) {
            controller.enqueue(
              encoder.encode(`data: ${JSON.stringify({ status: "deleted" })}\n\n`)
            );
            controller.close();
            return;
          }

          const data = JSON.stringify({
            status: current.status,
            errorMessage: current.errorMessage,
            framework: current.framework,
            metadata: current.metadata,
          });

          // Always emit on first connect, then only on changes
          if (data !== lastStatus) {
            controller.enqueue(encoder.encode(`data: ${data}\n\n`));
            lastStatus = data;
          }

          // Stop on terminal states
          if (TERMINAL_STATES.includes(current.status)) {
            controller.close();
            return;
          }
        } catch {
          controller.close();
          return;
        }

        // Schedule next poll if not aborted
        if (!request.signal.aborted) {
          setTimeout(poll, POLL_INTERVAL_MS);
        }
      };

      // Start polling
      await poll();

      // Clean up on client disconnect
      request.signal.addEventListener("abort", () => {
        controller.close();
      });
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-store",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
