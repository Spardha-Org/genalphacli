// ── API Error ──

export class ApiError extends Error {
  constructor(
    message: string,
    public statusCode: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// ── Auth ──

export interface User {
  id: string;
  email: string;
  name: string | null;
  email_verified: boolean;
}

export interface Workspace {
  id: string;
  name: string;
  slug: string;
  integration_id: string | null;
}

export interface Session {
  user: User;
  workspace: Workspace | null;
}

export interface MagicLinkResponse {
  message: string;
}

export interface VerifyResponse {
  message: string;
  user: User;
  is_new_user: boolean;
}

// ── Projects ──

export interface Project {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
}

// ── Services ──

export type ServiceStatusValue =
  | "pending"
  | "cloning"
  | "parsing"
  | "parsed"
  | "generating"
  | "packaging"
  | "complete"
  | "failed"
  | "timed_out";

export interface Service {
  id: string;
  project_id: string;
  name: string;
  repo_url: string | null;
  framework: string | null;
  status: ServiceStatusValue;
  route_graph: RouteGraph | null;
  error_message: string | null;
  download_url: string | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface ServiceStatus {
  status: ServiceStatusValue;
  errorMessage: string | null;
  framework: string | null;
  metadata: Record<string, unknown> | null;
}

export interface RouteGraph {
  command: string;
  subcommands: Subcommand[];
  base_url?: string;
  metadata?: Record<string, unknown>;
}

export interface Subcommand {
  name: string;
  description?: string;
  method: string;
  endpoint: string;
  params?: RouteParam[];
  output?: { format?: string; schema?: Record<string, unknown> };
}

export interface RouteParam {
  name: string;
  type: string;
  required: boolean;
  description?: string;
}

// ── Integrations ──

export interface AppMarketplace {
  id: string;
  app_name: string;
  display_name: string;
  auth_type: string;
  icon_url: string | null;
}

export interface Integration {
  id: string;
  app_name: string;
  github_username: string | null;
  status: string;
  created_at: string;
}
