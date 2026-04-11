"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { useApps, useIntegrations } from "@/data/hooks";
import { ConnectionForm } from "@/components/app-store/connection-form";

export default function AppDetailPage() {
  const { appName } = useParams<{ appName: string }>();
  const { data: apps, isLoading: appsLoading } = useApps();
  const { data: integrations } = useIntegrations();

  const app = apps?.find((a) => a.app_name === appName);
  const integration = integrations?.find((i) => i.app_name === appName);

  if (appsLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-[var(--text-muted)] font-[family-name:var(--font-jetbrains-mono)] text-sm animate-pulse">
          loading...
        </div>
      </div>
    );
  }

  if (!app) {
    return (
      <div className="py-20 text-center">
        <p className="text-[var(--text-muted)] font-[family-name:var(--font-jetbrains-mono)] text-sm">
          App not found
        </p>
        <Link href="/app-store" className="text-[var(--accent)] text-sm mt-2 inline-block">
          Back to App Store
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-lg mx-auto">
      {/* Back link */}
      <Link
        href="/app-store"
        className="text-[var(--text-dim)] text-xs font-[family-name:var(--font-jetbrains-mono)] hover:text-[var(--accent)] transition-colors no-underline mb-6 inline-block"
      >
        &larr; App Store
      </Link>

      {/* App header */}
      <div className="flex items-center gap-4 mb-2">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={app.meta?.icon || `https://cdn.simpleicons.org/${app.app_name}/white`}
          width={48}
          height={48}
          alt={app.display_name}
          className="opacity-90"
        />
        <div>
          <h1 className="font-[family-name:var(--font-jetbrains-mono)] text-xl font-bold">
            {app.display_name}
          </h1>
          <p className="text-sm text-[var(--text-dim)] mt-0.5">
            {app.meta?.description || `Connect your ${app.display_name} account`}
          </p>
        </div>
      </div>

      {/* Meta badges */}
      <div className="flex items-center gap-2 mb-8">
        <span className="px-2 py-0.5 text-[9px] font-[family-name:var(--font-jetbrains-mono)] font-semibold rounded bg-[var(--surface)] border border-[var(--border)] text-[var(--text-dim)]">
          {app.auth_type}
        </span>
        <span className="px-2 py-0.5 text-[9px] font-[family-name:var(--font-jetbrains-mono)] font-semibold rounded bg-[var(--surface)] border border-[var(--border)] text-[var(--text-dim)]">
          {app.category}
        </span>
      </div>

      {/* Connection form */}
      <div className="bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius)] p-6">
        <ConnectionForm app={app} integration={integration} />
      </div>
    </div>
  );
}
