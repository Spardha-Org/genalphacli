"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { useApps, useIntegrations } from "@/data/hooks";
import { ConnectionForm } from "@/components/app-store/connection-form";

export default function AppDetailPage() {
  const { appName } = useParams<{ appName: string }>();
  const { data: apps, isLoading } = useApps();
  const { data: integrations } = useIntegrations();

  const app = apps?.find((a) => a.app_name === appName);
  const integration = integrations?.find((i) => i.app_name === appName);

  if (isLoading) {
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
        <p className="text-[var(--text-muted)] font-[family-name:var(--font-jetbrains-mono)] text-sm mb-4">
          App not found
        </p>
        <Link href="/app-store" className="text-[var(--accent)] text-sm">
          &larr; Back to App Store
        </Link>
      </div>
    );
  }

  return (
    <div className="flex items-start justify-center pt-8 animate-in fade-in slide-in-from-bottom-2 duration-300">
      <div className="w-full max-w-md">
        {/* Back link */}
        <Link
          href="/app-store"
          className="text-[var(--text-dim)] text-xs font-[family-name:var(--font-jetbrains-mono)] hover:text-[var(--accent)] transition-colors no-underline mb-8 inline-flex items-center gap-1"
        >
          <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M19 12H5M12 19l-7-7 7-7" />
          </svg>
          App Store
        </Link>

        {/* App card — matches the HTML modal design */}
        <div className="bg-[var(--elevated)] border border-[var(--border)] rounded-[var(--radius)] p-8 mt-4 shadow-[0_8px_32px_rgba(0,0,0,0.3)]">
          {/* App header with icon */}
          <div className="flex items-center gap-4 mb-2">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={app.meta?.icon || `https://cdn.simpleicons.org/${app.app_name}/white`}
              width={36}
              height={36}
              alt={app.display_name}
              className="opacity-90"
            />
            <h2 className="font-[family-name:var(--font-jetbrains-mono)] text-lg font-bold">
              {integration ? app.display_name : `Connect ${app.display_name}`}
            </h2>
          </div>

          {/* Description */}
          <p className="text-sm text-[var(--text-dim)] mb-6 ml-[52px]">
            {integration
              ? `Manage your ${app.display_name} connection.`
              : app.meta?.description || `Connect your ${app.display_name} account to get started.`}
          </p>

          {/* Connection form */}
          <ConnectionForm app={app} integration={integration} />
        </div>
      </div>
    </div>
  );
}
