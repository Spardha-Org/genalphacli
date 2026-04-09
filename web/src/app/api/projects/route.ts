import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/auth";
import { db } from "@/db";
import { projects, workspaceMembers } from "@/db/schema";
import { eq } from "drizzle-orm";

export async function POST(request: NextRequest) {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const body = await request.json();
  const { name, description } = body;

  if (!name || typeof name !== "string" || name.trim().length === 0) {
    return NextResponse.json({ error: "Project name is required" }, { status: 400 });
  }

  const membership = await db.query.workspaceMembers.findFirst({
    where: eq(workspaceMembers.userId, session.user.id),
    with: { workspace: true },
  });

  if (!membership) {
    return NextResponse.json({ error: "No workspace found" }, { status: 403 });
  }

  const [project] = await db
    .insert(projects)
    .values({
      workspaceId: membership.workspace.id,
      name: name.trim(),
      description: description?.trim() || null,
    })
    .returning();

  return NextResponse.json(project, { status: 201 });
}
