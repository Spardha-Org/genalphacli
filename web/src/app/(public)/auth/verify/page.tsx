"use client";

import { Suspense, useEffect, useRef } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useVerify } from "@/data/hooks";
import Link from "next/link";

export default function VerifyPage() {
  return (
    <Suspense
      fallback={
        <main className="flex min-h-screen flex-col items-center justify-center bg-zinc-950 text-zinc-50">
          <p className="text-zinc-400 animate-pulse">Loading...</p>
        </main>
      }
    >
      <VerifyContent />
    </Suspense>
  );
}

function VerifyContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const verify = useVerify();
  const hasRun = useRef(false);

  const token = searchParams.get("token");

  useEffect(() => {
    if (!token || hasRun.current) return;
    hasRun.current = true;

    // Clear token from URL immediately (security: prevents it lingering in history)
    window.history.replaceState({}, "", "/auth/verify");

    verify.mutate(token, {
      onSuccess: () => {
        router.replace("/dashboard");
      },
    });
  }, [token]);

  // Loading state
  if (verify.isPending || (!verify.isError && !verify.isSuccess)) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center bg-zinc-950 text-zinc-50">
        <div className="text-center">
          <h1 className="text-2xl font-bold font-[family-name:var(--font-geist-mono)]">
            GenAlpha
          </h1>
          <p className="mt-4 text-zinc-400 animate-pulse">Verifying...</p>
        </div>
      </main>
    );
  }

  // Error state
  if (verify.isError) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center bg-zinc-950 text-zinc-50">
        <div className="max-w-md text-center px-6">
          <h1 className="text-2xl font-bold font-[family-name:var(--font-geist-mono)]">
            Link expired
          </h1>
          <p className="mt-3 text-zinc-400">
            {verify.error?.message || "This magic link is invalid or has expired."}
          </p>
          <Link
            href="/login"
            className="mt-6 inline-block rounded-lg bg-teal-500 px-6 py-3 text-sm font-medium text-zinc-950 hover:bg-teal-400 transition-colors"
          >
            Request a new link
          </Link>
        </div>
      </main>
    );
  }

  // Success — redirecting
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-zinc-950 text-zinc-50">
      <div className="text-center">
        <p className="text-teal-400">Redirecting to dashboard...</p>
      </div>
    </main>
  );
}
