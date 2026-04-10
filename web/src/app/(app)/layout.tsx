"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useSession, useLogout } from "@/data/hooks";
import { useRouter } from "next/navigation";
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
    <div className="min-h-screen bg-[var(--bg)] text-[var(--text)]">
      {/* Minimal top bar */}
      <header className="flex items-center justify-between px-6 py-3 border-b border-[var(--border)]">
        <Link href="/dashboard" className="font-[family-name:var(--font-jetbrains-mono)] font-extrabold text-sm tracking-wider text-[var(--text)] no-underline">
          <span className="text-[var(--accent)]">//</span> GenAlpha
        </Link>
        <div className="flex items-center gap-4">
          <Link href="/integrations" className="text-[12px] text-[var(--text-dim)] hover:text-[var(--accent)] transition-colors no-underline font-[family-name:var(--font-jetbrains-mono)]">
            Integrations
          </Link>
          <span className="text-[11px] text-[var(--text-muted)]">{session.user.email}</span>
          <button
            onClick={() => logout.mutate()}
            disabled={logout.isPending}
            className="text-[11px] text-[var(--text-muted)] hover:text-[var(--accent)] transition-colors font-[family-name:var(--font-jetbrains-mono)]"
          >
            Sign out
          </button>
        </div>
      </header>

      <main className="p-6">{children}</main>
    </div>
  );
}
