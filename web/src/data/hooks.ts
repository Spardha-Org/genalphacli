"use client";

import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryOptions,
} from "@tanstack/react-query";
import { authApi, projectsApi, servicesApi, integrationsApi } from "./api";
import type {
  Session,
  Project,
  Service,
  ServiceStatus,
  ServiceStatusValue,
  AppMarketplace,
  Integration,
  ApiError,
} from "./types";

// ── Query Keys ──

export const keys = {
  session: () => ["session"] as const,
  projects: () => ["projects"] as const,
  project: (id: string) => ["projects", id] as const,
  service: (id: string) => ["services", id] as const,
  serviceStatus: (id: string) => ["services", id, "status"] as const,
  integrations: () => ["integrations"] as const,
  apps: () => ["apps"] as const,
} as const;

// ── Terminal Statuses ──

const TERMINAL_STATUSES: ReadonlySet<ServiceStatusValue> = new Set([
  "parsed",
  "complete",
  "failed",
  "timed_out",
]);

// ── Auth Hooks ──

export function useSession() {
  return useQuery<Session>({
    queryKey: keys.session(),
    queryFn: authApi.getSession,
    staleTime: Infinity, // Fetch once, invalidate on login/logout
    gcTime: 30 * 60_000,
    retry: false,
  });
}

export function useLogin() {
  return useMutation({
    mutationFn: (email: string) => authApi.requestMagicLink(email),
  });
}

export function useVerify() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (token: string) => authApi.verify(token),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: keys.session() });
    },
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: authApi.logout,
    onSuccess: () => {
      queryClient.clear();
      if (typeof window !== "undefined") {
        window.location.href = "/";
      }
    },
  });
}

// ── Project Hooks ──

export function useProjects() {
  return useQuery<Project[]>({
    queryKey: keys.projects(),
    queryFn: projectsApi.list,
    staleTime: 60_000,
    gcTime: 10 * 60_000,
  });
}

export function useCreateProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: projectsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: keys.projects() });
    },
  });
}

export function useDeleteProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: projectsApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: keys.projects() });
    },
  });
}

// ── Service Hooks ──

export function useServicesByProject(projectId: string) {
  return useQuery({
    queryKey: [...keys.projects(), projectId, "services"] as const,
    queryFn: () => servicesApi.listByProject(projectId),
    enabled: Boolean(projectId),
    staleTime: 10_000,
  });
}

export function useService(id: string) {
  return useQuery<Service>({
    queryKey: keys.service(id),
    queryFn: () => servicesApi.get(id),
    enabled: Boolean(id),
    staleTime: 30_000,
    gcTime: 5 * 60_000,
  });
}

export function useServiceStatus(serviceId: string | null) {
  return useQuery<Service>({
    queryKey: keys.serviceStatus(serviceId!),
    queryFn: () => servicesApi.getStatus(serviceId!),
    enabled: Boolean(serviceId),
    refetchInterval: (query: { state: { data?: Service } }) => {
      const status = query.state.data?.status;
      if (!status) return 3000;
      return TERMINAL_STATUSES.has(status) ? false : 3000;
    },
    staleTime: 0, // Always refetch when polling
  });
}

export function useCreateService() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: servicesApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: keys.projects() });
    },
  });
}

export function useDeleteService() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: servicesApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: keys.projects() });
    },
  });
}

export function useGenerate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: servicesApi.generate,
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: keys.service(variables.serviceId),
      });
    },
  });
}

// ── Integration Hooks ──

export function useApps() {
  return useQuery<AppMarketplace[]>({
    queryKey: keys.apps(),
    queryFn: integrationsApi.listApps,
    staleTime: Infinity, // Marketplace is static
    gcTime: 60 * 60_000,
  });
}

export function useIntegrations() {
  return useQuery<Integration[]>({
    queryKey: keys.integrations(),
    queryFn: integrationsApi.list,
    staleTime: 5 * 60_000,
    gcTime: 30 * 60_000,
  });
}

export function useInstallApp() {
  return useMutation({
    mutationFn: (args: string | { appName: string; callbackPath?: string; formData?: Record<string, unknown> }) => {
      if (typeof args === "string") return integrationsApi.install(args);
      return integrationsApi.install(args.appName, args.callbackPath, args.formData);
    },
  });
}

export function useConnectApp() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ appName, credentials }: { appName: string; credentials: Record<string, string> }) =>
      integrationsApi.connect(appName, credentials),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: keys.integrations() });
    },
  });
}

export function useDeleteIntegration() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: integrationsApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: keys.integrations() });
      queryClient.invalidateQueries({ queryKey: keys.session() });
    },
  });
}
