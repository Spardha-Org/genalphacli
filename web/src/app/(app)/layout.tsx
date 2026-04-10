"use client";

import { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useSession, useLogout, useProjects } from "@/data/hooks";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        retry: 1,
        refetchOnWindowFocus: true,
      },
    },
  });
}

let browserQueryClient: QueryClient | undefined;

function getQueryClient() {
  if (typeof window === "undefined") return makeQueryClient();
  if (!browserQueryClient) browserQueryClient = makeQueryClient();
  return browserQueryClient;
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const queryClient = getQueryClient();

  return (
    <QueryClientProvider client={queryClient}>
      <AuthenticatedLayout>{children}</AuthenticatedLayout>
    </QueryClientProvider>
  );
}

function AuthenticatedLayout({ children }: { children: React.ReactNode }) {
  const { data: session, isLoading, isError } = useSession();
  const router = useRouter();

  // Redirect to login if not authenticated
  if (isError) {
    if (typeof window !== "undefined") {
      router.replace("/login");
    }
    return null;
  }

  // Loading skeleton
  if (isLoading || !session) {
    return (
      <div className="flex min-h-screen bg-zinc-950 text-zinc-50">
        <aside className="w-64 border-r border-zinc-800 bg-zinc-950 p-4">
          <div className="h-8 w-32 bg-zinc-800 rounded animate-pulse" />
          <div className="mt-6 space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-8 bg-zinc-800 rounded animate-pulse" />
            ))}
          </div>
        </aside>
        <main className="flex-1 p-8">
          <div className="h-8 w-48 bg-zinc-800 rounded animate-pulse" />
          <div className="mt-6 h-32 bg-zinc-800 rounded animate-pulse" />
        </main>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-zinc-950 text-zinc-50">
      <Sidebar session={session} />
      <main className="flex-1 p-8">{children}</main>
    </div>
  );
}

function Sidebar({ session }: { session: { user: { email: string; name: string | null }; workspace: { id: string; name: string } | null } }) {
  const pathname = usePathname();
  const { data: projects } = useProjects();
  const logout = useLogout();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  if (sidebarCollapsed) {
    return (
      <aside className="w-12 border-r border-zinc-800 bg-zinc-950 flex flex-col items-center py-4">
        <button
          onClick={() => setSidebarCollapsed(false)}
          className="text-zinc-500 hover:text-zinc-300"
          title="Expand sidebar"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7M5 5l7 7-7 7" />
          </svg>
        </button>
      </aside>
    );
  }

  return (
    <aside className="w-64 border-r border-zinc-800 bg-zinc-950 flex flex-col">
      <div className="p-4 border-b border-zinc-800 flex items-center justify-between">
        <div className="min-w-0">
          <p className="text-sm font-medium truncate">
            {session.workspace?.name || "My Workspace"}
          </p>
          <p className="text-xs text-zinc-500 truncate">{session.user.email}</p>
        </div>
        <button
          onClick={() => setSidebarCollapsed(true)}
          className="text-zinc-600 hover:text-zinc-400 ml-2"
          title="Collapse sidebar"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
          </svg>
        </button>
      </div>

      <nav className="flex-1 p-3 space-y-1">
        <NavLink href="/dashboard" active={pathname === "/dashboard"}>
          Dashboard
        </NavLink>

        <div className="pt-3">
          <p className="px-3 text-xs font-medium text-zinc-600 uppercase tracking-wider">
            Projects
          </p>
          {!projects ? (
            <div className="mt-2 space-y-1">
              {[1, 2].map((i) => (
                <div key={i} className="h-7 mx-3 bg-zinc-800 rounded animate-pulse" />
              ))}
            </div>
          ) : projects.length === 0 ? (
            <p className="px-3 mt-2 text-xs text-zinc-700">No projects yet</p>
          ) : (
            projects.map((project) => (
              <NavLink
                key={project.id}
                href={`/projects/${project.id}`}
                active={pathname === `/projects/${project.id}`}
              >
                {project.name}
              </NavLink>
            ))
          )}
        </div>

        <div className="pt-3">
          <NavLink href="/settings" active={pathname.startsWith("/settings")}>
            Settings
          </NavLink>
        </div>
      </nav>

      <div className="p-3 border-t border-zinc-800">
        <button
          onClick={() => logout.mutate()}
          disabled={logout.isPending}
          className="w-full text-left px-3 py-2 text-sm text-zinc-500 hover:text-zinc-300 transition-colors"
        >
          {logout.isPending ? "Signing out..." : "Sign out"}
        </button>
      </div>
    </aside>
  );
}

function NavLink({
  href,
  active,
  children,
}: {
  href: string;
  active: boolean;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className={`flex items-center gap-2 px-3 py-2 text-sm rounded-md transition-colors mt-1 ${
        active
          ? "bg-zinc-800 text-zinc-50 border-l-2 border-teal-500"
          : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-50"
      }`}
    >
      {children}
    </Link>
  );
}
