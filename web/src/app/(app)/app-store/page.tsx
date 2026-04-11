"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { useApps, useIntegrations } from "@/data/hooks";
import type { AppMarketplace, Integration } from "@/data/types";
import Link from "next/link";

function AppStoreContent() {
  const searchParams = useSearchParams();
  const connected = searchParams.get("connected");
  const error = searchParams.get("error");

  const { data: apps, isLoading } = useApps();
  const { data: integrations } = useIntegrations();

  function getIntegration(appName: string): Integration | undefined {
    return integrations?.find((i) => i.app_name === appName);
  }

  // Group apps by category
  const grouped = apps?.reduce<Record<string, AppMarketplace[]>>((acc, app) => {
    const cat = app.category;
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(app);
    return acc;
  }, {}) ?? {};

  const categoryLabels: Record<string, string> = {
    source_control: "Source Control",
    hosting: "Hosting & Distribution",
    distribution: "Distribution",
    coming_soon: "Coming Soon",
  };

  const categoryOrder = ["source_control", "hosting", "distribution", "coming_soon"];

  return (
    <div>
      {connected && (
        <div className="mb-6 px-4 py-3 bg-[var(--accent)]/10 border border-[var(--accent)]/20 rounded-lg text-[var(--accent)] text-sm font-[family-name:var(--font-jetbrains-mono)]">
          Successfully connected {connected}!
        </div>
      )}
      {error && (
        <div className="mb-6 px-4 py-3 bg-[var(--rose)]/10 border border-[var(--rose)]/20 rounded-lg text-[var(--rose)] text-sm font-[family-name:var(--font-jetbrains-mono)]">
          Connection failed. Please try again.
        </div>
      )}

      <div className="mb-8">
        <h1 className="font-[family-name:var(--font-jetbrains-mono)] text-xl font-bold">App Store</h1>
        <p className="text-sm text-[var(--text-dim)] mt-1">Connect your code hosting and deployment platforms</p>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="aspect-square bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius)] animate-pulse" />
          ))}
        </div>
      ) : (
        categoryOrder.map((cat) => {
          const catApps = grouped[cat];
          if (!catApps || catApps.length === 0) return null;
          const isComingSoon = cat === "coming_soon";

          return (
            <div key={cat} className="mb-8">
              <h3 className="font-[family-name:var(--font-jetbrains-mono)] text-xs text-[var(--text-muted)] uppercase tracking-wider mb-3">
                {categoryLabels[cat] || cat}
              </h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
                {catApps.map((app) => {
                  const integration = getIntegration(app.app_name);
                  const isConnected = !!integration;

                  const card = (
                    <div
                      className={`aspect-square bg-[var(--surface)] border rounded-[var(--radius)] flex flex-col items-center justify-center gap-3 relative ${
                        isComingSoon
                          ? "border-[var(--border)] opacity-40 cursor-not-allowed"
                          : isConnected
                            ? "border-[var(--accent)]/30 hover:border-[var(--accent)] hover:-translate-y-0.5 hover:shadow-[0_4px_24px_rgba(0,0,0,0.3)] transition-all duration-200"
                            : "border-[var(--border)] hover:border-[rgba(20,184,166,0.2)] hover:-translate-y-0.5 hover:shadow-[0_4px_24px_rgba(0,0,0,0.3)] transition-all duration-200"
                      }`}
                    >
                      {isConnected && (
                        <span className="absolute top-2.5 right-2.5 flex items-center gap-1 px-2 py-0.5 bg-[var(--green)]/10 border border-[var(--green)]/20 rounded-full">
                          <span className="w-1.5 h-1.5 bg-[var(--green)] rounded-full" />
                          <span className="text-[9px] text-[var(--green)] font-[family-name:var(--font-jetbrains-mono)] font-semibold">
                            connected
                          </span>
                        </span>
                      )}
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={app.meta?.icon || `https://cdn.simpleicons.org/${app.app_name}/white`}
                        width={56}
                        height={56}
                        alt={app.display_name}
                        className="opacity-80"
                      />
                      <span className="font-[family-name:var(--font-jetbrains-mono)] text-xs text-[var(--text)]">
                        {app.display_name}
                      </span>
                    </div>
                  );

                  if (isComingSoon) {
                    return <div key={app.app_name}>{card}</div>;
                  }

                  return (
                    <Link key={app.app_name} href={`/app-store/${app.app_name}`} className="no-underline">
                      {card}
                    </Link>
                  );
                })}
              </div>
            </div>
          );
        })
      )}
    </div>
  );
}

export default function AppStorePage() {
  return (
    <Suspense>
      <AppStoreContent />
    </Suspense>
  );
}
