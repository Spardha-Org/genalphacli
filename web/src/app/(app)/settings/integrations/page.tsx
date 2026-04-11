"use client";

import { useState } from "react";
import { useApps, useIntegrations, useInstallApp, useDeleteIntegration } from "@/data/hooks";

export default function IntegrationsPage() {
  const { data: apps, isLoading: appsLoading } = useApps();
  const { data: integrations, isLoading: integrationsLoading } = useIntegrations();
  const installApp = useInstallApp();
  const deleteIntegration = useDeleteIntegration();
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  async function handleConnect(appName: string) {
    try {
      const data = await installApp.mutateAsync(appName);
      // Redirect to OAuth provider
      if (data.authorize_url) {
        window.location.href = data.authorize_url;
      }
    } catch (err) {
      console.error("Install failed:", err);
    }
  }

  async function handleDisconnect(integrationId: string) {
    if (confirmDelete !== integrationId) {
      setConfirmDelete(integrationId);
      // Auto-revert after 3 seconds
      setTimeout(() => setConfirmDelete(null), 3000);
      return;
    }
    deleteIntegration.mutate(integrationId, {
      onSuccess: () => setConfirmDelete(null),
    });
  }

  const isLoading = appsLoading || integrationsLoading;

  return (
    <div>
      <h1 className="text-2xl font-bold font-[family-name:var(--font-geist-mono)] mb-8">
        Integrations
      </h1>

      {isLoading ? (
        <div className="space-y-4">
          {[1, 2].map((i) => (
            <div key={i} className="h-20 bg-zinc-900 border border-zinc-800 rounded-lg animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="space-y-8">
          {/* Connected integrations */}
          {integrations && integrations.length > 0 && (
            <div>
              <h2 className="text-sm font-medium text-zinc-400 uppercase tracking-wider mb-4">
                Connected
              </h2>
              <div className="space-y-3">
                {integrations.map((integration) => (
                  <div
                    key={integration.id}
                    className="flex items-center justify-between px-4 py-3 bg-zinc-900 border border-zinc-800 rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-zinc-800 rounded-full flex items-center justify-center text-xs">
                        {integration.app_name === "github" ? "GH" : integration.app_name[0].toUpperCase()}
                      </div>
                      <div>
                        <p className="text-sm font-medium capitalize">{integration.app_name}</p>
                        {integration.identifier && (
                          <p className="text-xs text-zinc-500">@{integration.identifier}</p>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full">
                        {integration.status}
                      </span>
                      <button
                        onClick={() => handleDisconnect(integration.id)}
                        disabled={deleteIntegration.isPending}
                        className={`text-xs px-3 py-1.5 rounded-md transition-colors ${
                          confirmDelete === integration.id
                            ? "bg-rose-500/20 text-rose-400 border border-rose-500/30"
                            : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800"
                        }`}
                      >
                        {confirmDelete === integration.id
                          ? "Confirm disconnect?"
                          : deleteIntegration.isPending
                            ? "Disconnecting..."
                            : "Disconnect"}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Available apps */}
          <div>
            <h2 className="text-sm font-medium text-zinc-400 uppercase tracking-wider mb-4">
              Available
            </h2>
            {!apps || apps.length === 0 ? (
              <p className="text-sm text-zinc-600">No apps available.</p>
            ) : (
              <div className="space-y-3">
                {apps
                  .filter((app) => !integrations?.some((i) => i.app_name === app.app_name))
                  .map((app) => (
                    <div
                      key={app.id}
                      className="flex items-center justify-between px-4 py-3 border border-zinc-800 rounded-lg"
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 bg-zinc-800 rounded-full flex items-center justify-center">
                          <span className="text-xs">{app.display_name[0]}</span>
                        </div>
                        <div>
                          <p className="text-sm font-medium">{app.display_name}</p>
                          <p className="text-xs text-zinc-600">{app.auth_type}</p>
                        </div>
                      </div>
                      <button
                        onClick={() => handleConnect(app.app_name)}
                        disabled={installApp.isPending}
                        className="text-xs bg-teal-500 text-zinc-950 px-3 py-1.5 rounded-md font-medium hover:bg-teal-400 transition-colors disabled:opacity-50"
                      >
                        {installApp.isPending ? "Connecting..." : "Connect"}
                      </button>
                    </div>
                  ))}
              </div>
            )}
          </div>
        </div>
      )}

      {installApp.isError && (
        <div className="mt-4 p-3 bg-rose-500/10 border border-rose-500/20 rounded-md">
          <p className="text-sm text-rose-400">
            {installApp.error?.message || "Failed to start connection"}
          </p>
        </div>
      )}
    </div>
  );
}
