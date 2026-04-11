"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useSession, useLogout } from "@/data/hooks";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { staleTime: 30_000, retry: 1, refetchOnWindowFocus: true } },
  });
}

let browserQueryClient: QueryClient | undefined;
function getQueryClient() {
  if (typeof window === "undefined") return makeQueryClient();
  if (!browserQueryClient) browserQueryClient = makeQueryClient();
  return browserQueryClient;
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={getQueryClient()}>
      <AuthenticatedLayout>{children}</AuthenticatedLayout>
    </QueryClientProvider>
  );
}

function AuthenticatedLayout({ children }: { children: React.ReactNode }) {
  const { data: session, isLoading, isError } = useSession();
  const router = useRouter();
  const pathname = usePathname();
  const logout = useLogout();

  if (isError) {
    if (typeof window !== "undefined") router.replace("/login");
    return null;
  }

  if (isLoading || !session) {
    return (
      <div className="min-h-screen bg-[var(--bg)] flex items-center justify-center">
        <div className="text-[var(--text-muted)] font-[family-name:var(--font-jetbrains-mono)] text-sm animate-pulse">
          loading...
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--text)] pb-16">
      {/* Minimal top bar */}
      <header className="flex items-center justify-between px-6 py-3 border-b border-[var(--border)] sticky top-0 z-50 bg-[var(--bg)]/80 backdrop-blur-xl">
        <Link href="/projects" className="font-[family-name:var(--font-jetbrains-mono)] font-extrabold text-sm tracking-wider text-[var(--text)] no-underline">
          <span className="text-[var(--accent)]">//</span> GenAlpha
        </Link>
        <button
          onClick={() => logout.mutate()}
          disabled={logout.isPending}
          className="text-[11px] text-[var(--text-muted)] hover:text-[var(--accent)] transition-colors font-[family-name:var(--font-jetbrains-mono)]"
        >
          Sign out
        </button>
      </header>

      <main className="p-6 max-w-[1200px] mx-auto">{children}</main>

      {/* Floating bottom nav pill */}
      <nav className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 flex gap-1 bg-[var(--elevated)] border border-[var(--border)] rounded-xl p-1.5 shadow-[0_8px_32px_rgba(0,0,0,0.4)]">
        <Link
          href="/projects"
          className={`font-[family-name:var(--font-jetbrains-mono)] text-[11px] font-semibold px-4 py-2 rounded-lg transition-all no-underline ${
            pathname.startsWith("/projects")
              ? "bg-[var(--accent)] text-[var(--bg)]"
              : "text-[var(--text-dim)] hover:text-[var(--text)]"
          }`}
        >
          Projects
        </Link>
        <Link
          href="/app-store"
          className={`font-[family-name:var(--font-jetbrains-mono)] text-[11px] font-semibold px-4 py-2 rounded-lg transition-all no-underline ${
            pathname.startsWith("/app-store")
              ? "bg-[var(--accent)] text-[var(--bg)]"
              : "text-[var(--text-dim)] hover:text-[var(--text)]"
          }`}
        >
          App Store
        </Link>
      </nav>
    </div>
  );
}
