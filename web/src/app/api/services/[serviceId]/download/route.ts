import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/auth";
import { db } from "@/db";
import { services, workspaceMembers } from "@/db/schema";
import { eq, and } from "drizzle-orm";
import { readFile, stat } from "fs/promises";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ serviceId: string }> }
) {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { serviceId } = await params;

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

  if (service.status !== "complete" || !service.downloadUrl) {
    return NextResponse.json(
      { error: "Download not available. Generate the package first." },
      { status: 400 }
    );
  }

  // Serve the zip file
  try {
    const fileStat = await stat(service.downloadUrl);
    const fileBuffer = await readFile(service.downloadUrl);

    return new Response(fileBuffer, {
      headers: {
        "Content-Type": "application/zip",
        "Content-Disposition": `attachment; filename="${service.name}.zip"`,
        "Content-Length": fileStat.size.toString(),
      },
    });
  } catch {
    return NextResponse.json(
      { error: "Download file not found. Please regenerate." },
      { status: 404 }
    );
  }
}
