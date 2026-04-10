"use client";

import { Suspense, useEffect, useRef } from "react";
import { useSearchParams, useRouter } from "next/navigation";

export default function OAuthCallbackPage() {
  return (
    <Suspense fallback={<Loading />}>
      <CallbackHandler />
    </Suspense>
  );
}

function CallbackHandler() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const hasRun = useRef(false);

  const code = searchParams.get("code");
  const state = searchParams.get("state");

  useEffect(() => {
    if (!code || !state || hasRun.current) return;
    hasRun.current = true;

    // Clear sensitive params from URL
    window.history.replaceState({}, "", "/settings/integrations/callback");

    // Send code+state to Core backend
    fetch("/api/integrations/github/exchange", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
      },
      credentials: "include",
      body: JSON.stringify({ code, state }),
    })
      .then((res) => {
        if (res.ok) {
          router.replace("/settings/integrations?connected=github");
        } else {
          router.replace("/settings/integrations?error=oauth_failed");
        }
      })
      .catch(() => {
        router.replace("/settings/integrations?error=oauth_failed");
      });
  }, [code, state, router]);

  return <Loading />;
}

function Loading() {
  return (
    <div className="flex items-center justify-center h-96">
      <div className="text-center">
        <h2 className="text-xl font-bold font-[family-name:var(--font-geist-mono)]">
          Connecting GitHub...
        </h2>
        <p className="text-zinc-500 mt-2 animate-pulse">Please wait</p>
      </div>
    </div>
  );
}
