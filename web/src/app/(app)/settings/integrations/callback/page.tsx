"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";

export default function OAuthCallbackPage() {
  return (
    <Suspense fallback={<Loading appName="app" />}>
      <CallbackHandler />
    </Suspense>
  );
}

function CallbackHandler() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const hasRun = useRef(false);
  const [appName, setAppName] = useState<string>("app");

  const code = searchParams.get("code");
  const state = searchParams.get("state");

  useEffect(() => {
    if (!code || !state || hasRun.current) return;
    hasRun.current = true;

    // Clear sensitive params from URL
    window.history.replaceState({}, "", "/settings/integrations/callback");

    // Step 1: Resolve state to get the app_name (no longer hardcoded to github)
    fetch(`/api/integrations/resolve-state?state=${encodeURIComponent(state)}`, {
      credentials: "include",
    })
      .then((res) => {
        if (!res.ok) throw new Error("State resolution failed");
        return res.json();
      })
      .then((data) => {
        const resolvedApp = data.app_name || "app";
        setAppName(resolvedApp);

        // Step 2: Exchange code+state for token using resolved app_name
        return fetch(`/api/integrations/${resolvedApp}/exchange`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
          },
          credentials: "include",
          body: JSON.stringify({ code, state }),
        });
      })
      .then((res) => {
        if (res.ok) {
          router.replace("/integrations?connected=true");
        } else {
          router.replace("/integrations?error=oauth_failed");
        }
      })
      .catch(() => {
        router.replace("/integrations?error=oauth_failed");
      });
  }, [code, state, router]);

  return <Loading appName={appName} />;
}

function Loading({ appName }: { appName: string }) {
  return (
    <div className="flex items-center justify-center h-96">
      <div className="text-center">
        <h2 className="text-xl font-bold font-[family-name:var(--font-geist-mono)]">
          Connecting {appName}...
        </h2>
        <p className="text-zinc-500 mt-2 animate-pulse">Please wait</p>
      </div>
    </div>
  );
}
