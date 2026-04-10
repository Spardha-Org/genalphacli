---
title: "feat: Frontend Architecture Restructure"
type: feat
status: active
date: 2026-04-10
---

# feat: Frontend Architecture Restructure

## Enhancement Summary

**Deepened on:** 2026-04-10
**Review agents:** Security Sentinel, TypeScript Reviewer, Frontend Design, Performance Oracle, Code Simplicity Reviewer

### Key Changes from Original Plan
1. **Drop Axios → native fetch wrapper** — eliminates supply chain risk + saves 13KB gzipped
2. **Drop Zustand → React Query + useState + useParams** — no server state duplication needed
3. **Flatten data layer → 3 files** (api.ts, types.ts, hooks.ts) not 14 domain folders
4. **Replace SSE with React Query polling** — SSE breaks through serverless proxy, polling is simpler
5. **Proxy header allowlist** — never forward arbitrary headers (prevents X-Workspace-ID injection)
6. **Session staleTime: Infinity** — fetch once, invalidate on login/logout mutations only
7. **Add loading/error/empty states** — the original plan was "all plumbing, no pixels"
8. **3 phases, not 6** — Auth → Core Flow → Settings

### Security Fixes
- Proxy uses header allowlist (cookies + content-type only), blocks X-Workspace-ID injection
- Magic link token cleared from URL via `history.replaceState` immediately after reading
- All `href` attributes validated for `https://` protocol (blocks `javascript:` XSS)
- Custom `X-Requested-With` header on fetch calls for CSRF defense-in-depth

---

## Overview

Restructure the Next.js frontend to follow esd-frontend patterns. Remove broken Auth.js, add React Query + Axios data layer, Zustand for UI state, and wire everything to the Core/TPS backend services via API proxy routes.

## Problem Statement

The current frontend has Auth.js v5 which broke on GitHub OAuth (iss validation). The code is a mix of server components calling the DB directly and client components with no data fetching layer. No state management, no API client, no structured data layer.

## Proposed Solution

### Route Structure

```
web/src/app/
  (public)/                    # No auth required
    page.tsx                   # Landing page
    login/page.tsx             # Email input → magic link
    auth/verify/page.tsx       # Magic link landing → session → redirect
  (app)/                       # Auth required (session guard)
    layout.tsx                 # Sidebar + SessionProvider + QueryProvider
    dashboard/page.tsx         # Workspace overview
    projects/[id]/page.tsx     # Project detail + parse form
    services/[id]/page.tsx     # Mindmap + generate + download
    settings/page.tsx          # Workspace settings
    settings/integrations/page.tsx  # Connect GitHub
  api/                         # Proxy routes to Core :8000
    auth/[...path]/route.ts
    projects/[...path]/route.ts
    services/[...path]/route.ts
    integrations/[...path]/route.ts
```

### Data Layer (src/data/) — Simplified

Flat 3-file structure (not 14 domain folders — overkill for ~15 API functions):

```
src/data/
  types.ts     # All interfaces: User, Session, Workspace, Project, Service, Integration
  api.ts       # All API functions using native fetch wrapper (no Axios)
  hooks.ts     # All React Query hooks + inline query key factory
```

**No Zustand.** React Query owns all server state. UI state uses:
- `useState` in components (sidebar collapsed)
- `useParams()` from Next.js (active project/service)
- React Query cache (session, projects, services)

**No Axios.** Native fetch with a thin wrapper:
```typescript
// src/data/api.ts
const API_BASE = '/api';

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      'X-Requested-With': 'XMLHttpRequest', // CSRF defense
      ...init?.headers,
    },
    credentials: 'include', // forward cookies
  });
  if (res.status === 401 && typeof window !== 'undefined') {
    window.location.href = '/login?reason=session_expired';
    throw new Error('Session expired');
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(body.error || body.detail || 'Request failed', res.status);
  }
  return res.json();
}
```

**Query key factory with staleTime config:**
```typescript
// in src/data/hooks.ts
const keys = {
  session: () => ['session'] as const,
  projects: () => ['projects'] as const,
  project: (id: string) => ['projects', id] as const,
  service: (id: string) => ['services', id] as const,
  serviceStatus: (id: string) => ['services', id, 'status'] as const,
  integrations: () => ['integrations'] as const,
  apps: () => ['apps'] as const,
} as const;
```

**Per-domain staleTime (from performance review):**

| Query | staleTime | Rationale |
|-------|-----------|-----------|
| session | Infinity | Never changes mid-session. Invalidate on login/logout. |
| projects | 60s | Changes infrequently |
| service detail | 30s | Can change during generation |
| service status | 3s (polling) | Replaces SSE — polls during active states only |
| integrations | 5min | Rarely changes |
| apps (marketplace) | Infinity | Static data |

**Service status polling replaces SSE:**
```typescript
export function useServiceStatus(serviceId: string | null) {
  return useQuery({
    queryKey: keys.serviceStatus(serviceId!),
    queryFn: () => api.getServiceStatus(serviceId!),
    enabled: !!serviceId,
    refetchInterval: (query) => {
      const s = query.state.data?.status;
      return TERMINAL_STATUSES.has(s) ? false : 3000;
    },
  });
}
```

## Implementation Phases (Consolidated: 3 phases, not 6)

### Phase 1: Auth + Data Layer + Proxy

**Tasks:**

- [ ] Install deps: `@tanstack/react-query` (only new dependency — no Axios, no Zustand)
- [ ] Create `src/data/types.ts` — all interfaces (User, Session, Workspace, Project, Service, Integration, ApiError)
- [ ] Create `src/data/api.ts` — native fetch wrapper with 401 redirect + all API functions
- [ ] Create `src/data/hooks.ts` — all React Query hooks with inline key factory + per-domain staleTime
- [ ] Remove Auth.js: delete `src/auth.ts`, `src/middleware.ts`, `src/app/api/auth/[...nextauth]/`
- [ ] Create proxy helper `src/lib/proxy.ts` with header allowlist (cookies + content-type only, blocks X-Workspace-ID)
- [ ] Create catch-all proxy routes: auth, projects, services, integrations → Core :8000
  - Must forward query params (critical for magic link verify `?token=xxx`)
  - Must `await params` (Next.js 15+ async params)
  - Must forward Set-Cookie headers from Core response
- [ ] Create `(public)/login/page.tsx` — email input, "Check your email" state with resend countdown, "wrong email?" link
- [ ] Create `(public)/auth/verify/page.tsx` — reads token, calls verify, `history.replaceState` to clear token, redirect to /dashboard
- [ ] Create `(app)/layout.tsx` — React Query provider inline, session check via `useSession()`, sidebar with active state + skeleton
- [ ] Create loading/error boundary component for consistent states across pages

**Success criteria:**
- [ ] Full login flow: /login → email → magic link → verify → dashboard
- [ ] `useSession()` hook returns user with staleTime: Infinity (fetched once)
- [ ] 401 from any API → redirect to /login?reason=session_expired
- [ ] Auth.js completely removed
- [ ] Proxy correctly forwards cookies and query params

### Phase 2: Core Flow (Dashboard + Mindmap + Generation)

**Tasks:**

- [ ] Create `(app)/dashboard/page.tsx`:
  - Workspace overview with project cards (from `useProjects()`)
  - Service count per project, status badges
  - "New Project" button, empty state with CTA
  - Skeleton loading state while projects fetch
- [ ] Create `(app)/projects/[id]/page.tsx`:
  - Project detail with service list
  - Parse form (updated to use React Query mutation + fetch wrapper)
  - Service status via `useServiceStatus(id)` with `refetchInterval: 3000` (replaces SSE)
- [ ] Create `(app)/services/[id]/page.tsx`:
  - Service detail with status-dependent view
  - Lazy-load React Flow mindmap: `dynamic(() => import(...), { ssr: false })`
  - Add `onlyRenderVisibleElements` prop to ReactFlow for large graph performance
  - Reuse existing components: RouteGraph, ProgressStepper, GeneratePanel, RouteDetailPanel
  - Generate button → POST /api/generate, download button → GET /api/services/{id}/download
- [ ] Update sidebar: active state via `usePathname()`, skeleton while loading, mobile drawer below `md` breakpoint
- [ ] Add loading/error/empty states to all pages

**Success criteria:**
- [ ] Full flow: dashboard → project → parse → progress polling → mindmap → generate → download
- [ ] Loading skeletons on every page, error boundaries with retry
- [ ] React Flow lazy-loaded (saves ~80KB gzipped from initial bundle)

### Phase 3: Settings + Integrations (can be deferred)

**Tasks:**

- [ ] Create `(app)/settings/page.tsx` — workspace name, link to integrations
- [ ] Create `(app)/settings/integrations/page.tsx`:
  - Lists apps from TPS marketplace, shows connected integrations
  - "Connect GitHub" → OAuth flow via Core → TPS
  - "Disconnect" with inline confirmation (button text changes, auto-reverts 3s)
  - Success/error banners on OAuth return
- [ ] Handle OAuth callback proxy route

**Success criteria:**
- [ ] Connect/disconnect GitHub from settings
- [ ] Connected status shown with GitHub username

## Acceptance Criteria

### Functional
- [ ] Magic link login works end-to-end (email → verify → session → dashboard)
- [ ] All pages fetch data via React Query + Axios through Next.js proxy
- [ ] No direct database access from frontend (all via Core API)
- [ ] Auth.js completely removed
- [ ] Sidebar shows projects and services from API
- [ ] Mindmap visualization works with API-fetched data
- [ ] GitHub integration connect/disconnect via settings

### Non-Functional
- [ ] 401 from any API call → automatic redirect to /login
- [ ] React Query cache: stale time 30s for active data, 5min for stable data
- [ ] No server state duplicated in Zustand (React Query owns server data)
- [ ] Axios pinned to safe version (v1.7.9)

## Tech Stack

| Library | Version | Purpose |
|---------|---------|---------|
| @tanstack/react-query | v5 | Server state + data fetching + polling |
| native fetch | built-in | HTTP client (no Axios — zero supply chain risk) |
| @xyflow/react | 12.x | Mindmap (already installed, lazy-loaded) |
| @dagrejs/dagre | 1.x | Graph layout (already installed) |

**Removed:** Axios (supply chain concern + 13KB saved), Zustand (React Query + useState covers everything)

## File Structure (Simplified — 8 new files, not 22)

```
web/src/
  app/
    (public)/
      page.tsx                    # Landing
      login/page.tsx              # Magic link login
      auth/verify/page.tsx        # Token verify + redirect
    (app)/
      layout.tsx                  # React Query provider + session check + sidebar (all inline)
      dashboard/page.tsx
      projects/[id]/page.tsx
      services/[id]/page.tsx
      settings/page.tsx
      settings/integrations/page.tsx
    api/
      auth/[...path]/route.ts     # Proxy → Core (header allowlist)
      projects/[...path]/route.ts
      services/[...path]/route.ts
      integrations/[...path]/route.ts
  data/
    types.ts                     # All interfaces (User, Project, Service, Integration, etc.)
    api.ts                       # All API functions (native fetch wrapper, 401 redirect)
    hooks.ts                     # All React Query hooks + inline key factory
  components/
    route-graph.tsx              # Existing (lazy-loaded with next/dynamic)
    api-route-node.tsx           # Existing (memoized)
    progress-stepper.tsx         # Existing
    generate-panel.tsx           # Existing (updated to use hooks)
    route-detail-panel.tsx       # Existing
    parse-form.tsx               # Updated to use React Query mutations
    query-boundary.tsx           # NEW: loading skeleton + error card + empty state wrapper
  lib/
    proxy.ts                     # Shared proxy helper (header allowlist, query param forwarding)
```

**Removed vs original plan:** ~14 files eliminated (domain folders, Zustand stores, Axios client, separate providers, query-keys.ts)

## References

- Brainstorm: `docs/design/brainstorms/2026-04-10-frontend-architecture-brainstorm.md`
- Backend auth plan: `docs/design/plans/2026-04-10-feat-backend-auth-two-service-plan.md`
- ESD-frontend reference: `/Users/nandisha/Desktop/Atomicwork/esd-frontend/`
- Existing components: `web/src/components/` (route-graph, progress-stepper, etc.)
