"use client";

import { useState } from "react";
import { useInstallApp, useConnectApp, useDeleteIntegration } from "@/data/hooks";
import type { AppMarketplace, Integration } from "@/data/types";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { RenderField } from "./render-field";

// ── AuthorizationState (from ESD-frontend pattern) ──

enum AuthorizationState {
  Authorized = "authorized",
  FormBasedOAuth = "form_oauth",
  Unauthorized = "unauthorized",
}

function getAuthorizationState(
  app: AppMarketplace,
  integration?: Integration
): AuthorizationState {
  if (integration) return AuthorizationState.Authorized;
  if (app.is_install_required && app.auth_type === "form_based_oauth2")
    return AuthorizationState.FormBasedOAuth;
  return AuthorizationState.Unauthorized;
}

// ── Component ──

interface ConnectionFormProps {
  app: AppMarketplace;
  integration?: Integration;
}

export function ConnectionForm({ app, integration }: ConnectionFormProps) {
  const authState = getAuthorizationState(app, integration);
  const [formValues, setFormValues] = useState<Record<string, string>>({});
  const installApp = useInstallApp();
  const connectApp = useConnectApp();
  const deleteIntegration = useDeleteIntegration();

  const formFields = app.meta?.form_fields || [];
  const hasFormFields = formFields.length > 0;

  function updateField(key: string, value: string) {
    setFormValues((v) => ({ ...v, [key]: value }));
  }

  // ── Authorized: connected badge + disconnect ──
  if (authState === AuthorizationState.Authorized) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3 px-4 py-3 bg-[var(--accent)]/5 border border-[var(--accent)]/20 rounded-lg">
          <span className="w-2 h-2 bg-[var(--green)] rounded-full" />
          <span className="text-sm text-[var(--text)]">
            Connected{integration?.identifier ? ` as ${integration.identifier}` : ""}
          </span>
        </div>

        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button
              variant="ghost"
              className="text-[var(--rose)] hover:text-[var(--rose)] hover:bg-[var(--rose)]/10 font-[family-name:var(--font-jetbrains-mono)] text-xs"
            >
              Disconnect {app.display_name}
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent className="bg-[var(--elevated)] border-[var(--border)]">
            <AlertDialogHeader>
              <AlertDialogTitle className="font-[family-name:var(--font-jetbrains-mono)] text-[var(--text)]">
                Disconnect {app.display_name}?
              </AlertDialogTitle>
              <AlertDialogDescription className="text-[var(--text-dim)]">
                This will revoke access. You can reconnect anytime.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel className="text-[var(--text-dim)]">Cancel</AlertDialogCancel>
              <AlertDialogAction
                onClick={() => integration && deleteIntegration.mutate(integration.id)}
                className="bg-[var(--rose)] text-white hover:bg-[var(--rose)]/80"
              >
                {deleteIntegration.isPending ? "Disconnecting..." : "Disconnect"}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    );
  }

  // ── FormBasedOAuth: form fields → then OAuth redirect ──
  if (authState === AuthorizationState.FormBasedOAuth) {
    return (
      <div className="space-y-4">
        {formFields.map((field) => (
          <RenderField
            key={field.reference_key}
            field={field}
            value={formValues[field.reference_key] || ""}
            onChange={(v) => updateField(field.reference_key, v)}
          />
        ))}
        <Button
          onClick={async () => {
            const result = await installApp.mutateAsync({
              appName: app.app_name,
              callbackPath: "/app-store",
              formData: formValues,
            });
            window.location.href = result.authorize_url;
          }}
          disabled={installApp.isPending}
          className="w-full bg-[var(--accent)] text-[var(--bg)] hover:bg-[var(--accent-bright)] font-[family-name:var(--font-jetbrains-mono)] text-xs font-semibold"
        >
          {installApp.isPending ? "Connecting..." : "Connect"}
        </Button>
      </div>
    );
  }

  // ── Unauthorized ──

  // OAuth apps (no form fields needed)
  if (app.is_install_required && !hasFormFields) {
    return (
      <Button
        onClick={async () => {
          const result = await installApp.mutateAsync(app.app_name);
          window.location.href = result.authorize_url;
        }}
        disabled={installApp.isPending}
        className="w-full bg-[var(--accent)] text-[var(--bg)] hover:bg-[var(--accent-bright)] font-[family-name:var(--font-jetbrains-mono)] text-xs font-semibold"
      >
        {installApp.isPending ? "Redirecting..." : `Connect ${app.display_name}`}
      </Button>
    );
  }

  // Credential apps (form fields)
  return (
    <div className="space-y-4">
      {formFields.map((field) => (
        <RenderField
          key={field.reference_key}
          field={field}
          value={formValues[field.reference_key] || ""}
          onChange={(v) => updateField(field.reference_key, v)}
        />
      ))}
      <Button
        onClick={async () => {
          await connectApp.mutateAsync({ appName: app.app_name, credentials: formValues });
        }}
        disabled={connectApp.isPending}
        className="w-full bg-[var(--accent)] text-[var(--bg)] hover:bg-[var(--accent-bright)] font-[family-name:var(--font-jetbrains-mono)] text-xs font-semibold"
      >
        {connectApp.isPending ? "Connecting..." : "Connect"}
      </Button>
    </div>
  );
}
