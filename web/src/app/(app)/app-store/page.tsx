"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { useApps, useIntegrations, useInstallApp, useDeleteIntegration, useConnectApp } from "@/data/hooks";
import type { AppMarketplace, Integration } from "@/data/types";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function AppStorePage() {
  const searchParams = useSearchParams();
  const connected = searchParams.get("connected");
  const error = searchParams.get("error");

  const { data: apps, isLoading: appsLoading } = useApps();
  const { data: integrations } = useIntegrations();
  const installApp = useInstallApp();
  const connectApp = useConnectApp();
  const deleteIntegration = useDeleteIntegration();

  const [disconnectApp, setDisconnectApp] = useState<{ name: string; integrationId: string } | null>(null);
  const [connectForm, setConnectForm] = useState<AppMarketplace | null>(null);
  const [formValues, setFormValues] = useState<Record<string, string>>({});

  function getIntegration(appName: string): Integration | undefined {
    return integrations?.find((i) => i.app_name === appName);
  }

  async function handleConnect(app: AppMarketplace) {
    if (app.is_install_required) {
      // OAuth flow — redirect
      const result = await installApp.mutateAsync(app.app_name);
      window.location.href = result.authorize_url;
    } else {
      // Credential flow — show form
      setConnectForm(app);
      setFormValues({});
    }
  }

  async function handleCredentialSubmit() {
    if (!connectForm) return;
    await connectApp.mutateAsync({ appName: connectForm.app_name, credentials: formValues });
    setConnectForm(null);
    setFormValues({});
  }

  async function handleDisconnect() {
    if (!disconnectApp) return;
    await deleteIntegration.mutateAsync(disconnectApp.integrationId);
    setDisconnectApp(null);
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
      {/* Success/error banners */}
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

      {appsLoading ? (
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

                  return (
                    <button
                      key={app.app_name}
                      onClick={() => {
                        if (isComingSoon) return;
                        if (isConnected) {
                          setDisconnectApp({ name: app.display_name, integrationId: integration.id });
                        } else {
                          handleConnect(app);
                        }
                      }}
                      disabled={isComingSoon}
                      className={`aspect-square bg-[var(--surface)] border rounded-[var(--radius)] flex flex-col items-center justify-center gap-3 transition-all relative ${
                        isComingSoon
                          ? "border-[var(--border)] opacity-40 cursor-not-allowed"
                          : isConnected
                            ? "border-[var(--accent)]/30 hover:border-[var(--accent)]"
                            : "border-[var(--border)] hover:border-[var(--accent)] cursor-pointer"
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
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })
      )}

      {/* Disconnect dialog */}
      <AlertDialog open={!!disconnectApp} onOpenChange={() => setDisconnectApp(null)}>
        <AlertDialogContent className="bg-[var(--elevated)] border-[var(--border)]">
          <AlertDialogHeader>
            <AlertDialogTitle className="font-[family-name:var(--font-jetbrains-mono)] text-[var(--text)]">
              Disconnect {disconnectApp?.name}
            </AlertDialogTitle>
            <AlertDialogDescription className="text-[var(--text-dim)]">
              This will revoke access. You can reconnect anytime.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="text-[var(--text-dim)]">Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDisconnect}
              className="bg-[var(--rose)] text-white hover:bg-[var(--rose)]/80"
            >
              Disconnect
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Credential connect form dialog */}
      <Dialog open={!!connectForm} onOpenChange={() => setConnectForm(null)}>
        <DialogContent className="bg-[var(--elevated)] border-[var(--border)] text-[var(--text)]">
          <DialogHeader>
            <div className="flex items-center gap-3">
              {connectForm && (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={connectForm.meta?.icon || `https://cdn.simpleicons.org/${connectForm.app_name}/white`}
                  width={28}
                  height={28}
                  alt=""
                />
              )}
              <DialogTitle className="font-[family-name:var(--font-jetbrains-mono)]">
                Connect {connectForm?.display_name}
              </DialogTitle>
            </div>
            <DialogDescription className="text-[var(--text-dim)]">
              {connectForm?.meta?.description || "Enter your credentials to connect."}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 mt-2">
            {connectForm?.meta?.form_fields?.map((field) => (
              <div key={field.reference_key}>
                <label className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-[var(--text-muted)] uppercase tracking-wider block mb-1.5">
                  {field.display_name} {field.required && <span className="text-[var(--rose)]">*</span>}
                </label>
                <Input
                  type={field.type === "password" ? "password" : "text"}
                  placeholder={field.placeholder || ""}
                  value={formValues[field.reference_key] || ""}
                  onChange={(e) => setFormValues((v) => ({ ...v, [field.reference_key]: e.target.value }))}
                  className="bg-[var(--surface)] border-[var(--border)] text-[var(--text)] font-[family-name:var(--font-jetbrains-mono)] text-sm"
                />
              </div>
            ))}
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="ghost" onClick={() => setConnectForm(null)} className="text-[var(--text-dim)]">
                Cancel
              </Button>
              <Button
                onClick={handleCredentialSubmit}
                disabled={connectApp.isPending}
                className="bg-[var(--accent)] text-[var(--bg)] hover:bg-[var(--accent-bright)]"
              >
                {connectApp.isPending ? "Connecting..." : "Connect"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
