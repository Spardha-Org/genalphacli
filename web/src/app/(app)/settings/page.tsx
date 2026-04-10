"use client";

import { useSession } from "@/data/hooks";
import Link from "next/link";

export default function SettingsPage() {
  const { data: session } = useSession();

  return (
    <div>
      <h1 className="text-2xl font-bold font-[family-name:var(--font-geist-mono)] mb-8">
        Settings
      </h1>

      <div className="space-y-6">
        <div className="border border-zinc-800 rounded-lg p-6">
          <h2 className="text-sm font-medium text-zinc-400 uppercase tracking-wider mb-4">
            Workspace
          </h2>
          <div className="space-y-3">
            <div>
              <p className="text-xs text-zinc-600">Name</p>
              <p className="text-sm">{session?.workspace?.name || "—"}</p>
            </div>
            <div>
              <p className="text-xs text-zinc-600">Slug</p>
              <p className="text-sm font-[family-name:var(--font-geist-mono)]">
                {session?.workspace?.slug || "—"}
              </p>
            </div>
          </div>
        </div>

        <div className="border border-zinc-800 rounded-lg p-6">
          <h2 className="text-sm font-medium text-zinc-400 uppercase tracking-wider mb-4">
            Account
          </h2>
          <div className="space-y-3">
            <div>
              <p className="text-xs text-zinc-600">Email</p>
              <p className="text-sm">{session?.user?.email || "—"}</p>
            </div>
          </div>
        </div>

        <Link
          href="/settings/integrations"
          className="block border border-zinc-800 rounded-lg p-6 hover:bg-zinc-900 transition-colors"
        >
          <h2 className="text-sm font-medium text-zinc-400 uppercase tracking-wider mb-2">
            Integrations
          </h2>
          <p className="text-sm text-zinc-500">
            Connect GitHub, GitLab, and other services to parse private repositories.
          </p>
          <span className="text-xs text-teal-400 mt-2 inline-block">Manage integrations →</span>
        </Link>
      </div>
    </div>
  );
}
