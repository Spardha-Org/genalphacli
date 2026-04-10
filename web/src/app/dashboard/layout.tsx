import { auth, signOut } from "@/auth";
import { redirect } from "next/navigation";
import { db } from "@/db";
import { workspaceMembers, projects } from "@/db/schema";
import { eq } from "drizzle-orm";

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await auth();
  if (!session?.user?.id) redirect("/");

  const membership = await db.query.workspaceMembers.findFirst({
    where: eq(workspaceMembers.userId, session.user.id),
    with: {
      workspace: {
        with: {
          projects: true,
        },
      },
    },
  });

  if (!membership) redirect("/");

  const workspace = membership.workspace;

  return (
    <div className="flex min-h-screen bg-zinc-950 text-zinc-50">
      {/* Sidebar */}
      <aside className="w-64 border-r border-zinc-800 bg-zinc-950 flex flex-col">
        <div className="p-4 border-b border-zinc-800">
          <div className="flex items-center gap-3">
            {session.user.image && (
              <img
                src={session.user.image}
                alt=""
                className="w-8 h-8 rounded-full"
              />
            )}
            <div className="min-w-0">
              <p className="text-sm font-medium truncate">{workspace.name}</p>
              <p className="text-xs text-zinc-500 truncate">
                {session.user.email}
              </p>
            </div>
          </div>
        </div>

        <nav className="flex-1 p-3 space-y-1">
          <a
            href="/dashboard"
            className="flex items-center gap-2 px-3 py-2 text-sm rounded-md hover:bg-zinc-800 text-zinc-300 hover:text-zinc-50 transition-colors"
          >
            Dashboard
          </a>

          <div className="pt-3">
            <p className="px-3 text-xs font-medium text-zinc-600 uppercase tracking-wider">
              Projects
            </p>
            {workspace.projects.map((project: { id: string; name: string }) => (
              <a
                key={project.id}
                href={`/dashboard/projects/${project.id}`}
                className="flex items-center gap-2 px-3 py-2 text-sm rounded-md hover:bg-zinc-800 text-zinc-400 hover:text-zinc-50 transition-colors mt-1"
              >
                {project.name}
              </a>
            ))}
          </div>
        </nav>

        <div className="p-3 border-t border-zinc-800">
          <form
            action={async () => {
              "use server";
              await signOut({ redirectTo: "/" });
            }}
          >
            <button
              type="submit"
              className="w-full text-left px-3 py-2 text-sm text-zinc-500 hover:text-zinc-300 transition-colors"
            >
              Sign out
            </button>
          </form>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 p-8">{children}</main>
    </div>
  );
}
