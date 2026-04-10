import { ApiError } from "./types";
import type {
  MagicLinkResponse,
  VerifyResponse,
  Session,
  Project,
  Service,
  ServiceStatus,
  AppMarketplace,
  Integration,
} from "./types";

// ── Fetch Wrapper ──

const API_BASE = "/api";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-Requested-With": "XMLHttpRequest",
      ...init?.headers,
    },
    credentials: "include",
  });

  if (res.status === 401 && typeof window !== "undefined") {
    if (!window.location.pathname.startsWith("/login") && !window.location.pathname.startsWith("/auth")) {
      window.location.href = "/login?reason=session_expired";
    }
    throw new ApiError("Session expired", 401);
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(
      body.error || body.detail || body.message || "Request failed",
      res.status,
    );
  }

  // Handle 204 No Content
  if (res.status === 204) return {} as T;

  return res.json();
}

// ── Auth API ──

export const authApi = {
  requestMagicLink: (email: string) =>
    apiFetch<MagicLinkResponse>("/auth/magic-link", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),

  verify: (token: string) =>
    apiFetch<VerifyResponse>(`/auth/verify?token=${encodeURIComponent(token)}`),

  getSession: () => apiFetch<Session>("/auth/session"),

  logout: () =>
    apiFetch<{ message: string }>("/auth/logout", { method: "POST" }),
};

// ── Projects API ──

export const projectsApi = {
  list: () => apiFetch<Project[]>("/projects"),

  create: (payload: { name: string; description?: string }) =>
    apiFetch<Project>("/projects", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  delete: (id: string) =>
    apiFetch<{ ok: boolean }>(`/projects/${id}`, { method: "DELETE" }),
};

// ── Services API ──

export const servicesApi = {
  get: (id: string) => apiFetch<Service>(`/services/${id}`),

  create: (payload: { repo_url: string; project_id: string }) =>
    apiFetch<{ serviceId: string; workflowId: string; status: string }>(
      "/parse",
      { method: "POST", body: JSON.stringify({ repoUrl: payload.repo_url, projectId: payload.project_id }) },
    ),

  delete: (id: string) =>
    apiFetch<{ ok: boolean }>(`/services/${id}`, { method: "DELETE" }),

  getStatus: (id: string) => apiFetch<Service>(`/services/${id}`),

  generate: (payload: {
    serviceId: string;
    outputTypes: string[];
    cliName: string;
    baseUrl: string;
  }) =>
    apiFetch<{ serviceId: string; workflowId: string; status: string }>(
      "/generate",
      { method: "POST", body: JSON.stringify(payload) },
    ),
};

// ── Integrations API ──

export const integrationsApi = {
  listApps: () => apiFetch<AppMarketplace[]>("/integrations/apps"),

  list: () => apiFetch<Integration[]>("/integrations"),

  install: (appName: string) =>
    apiFetch<{ authorize_url: string; state: string }>(
      `/integrations/${appName}/install`,
      { method: "POST" },
    ),

  delete: (id: string) =>
    apiFetch<{ ok: boolean }>(`/integrations/${id}`, { method: "DELETE" }),
};
