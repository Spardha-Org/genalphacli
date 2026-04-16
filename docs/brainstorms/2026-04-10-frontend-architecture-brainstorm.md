---
date: 2026-04-10
topic: frontend-architecture
---

# Frontend Architecture — ESD-Inspired Restructure

## What We're Building

Restructure the genalphacli Next.js frontend to follow esd-frontend's battle-tested patterns. Remove the broken Auth.js, wire to the new Core/TPS backend, and add a proper data layer with React Query + Axios.

**Key changes from current state:**
- Remove Auth.js entirely → magic link auth via Core API
- Add React Query + Axios data layer (domain-structured like esd-frontend)
- Add Zustand for UI state (session, sidebar, active workspace)
- Grouped App Router routes: `(public)` for landing/login, `(app)` for protected dashboard
- Settings page with integrations tab for GitHub OAuth via TPS
- Keep existing: Tailwind styling, dark theme, sidebar layout, React Flow mindmap

## Why This Approach

The esd-frontend patterns are proven at scale (large enterprise app) and the user is familiar with them. Adapting them for genalphacli gives:
- **Scalable data layer**: `src/data/{domain}/` with types, api, constants, store per domain
- **Clean state split**: React Query for server state, Zustand for UI state (never duplicate)
- **Familiar patterns**: Same conventions as the work codebase → faster development
- **Auth that works**: Server-side sessions via Core API, no broken Auth.js

We keep it lean vs esd-frontend: no Styled Components (Tailwind instead), no i18n, no Sentry, no custom DS. MVP-appropriate.

## Key Decisions

- **Data fetching**: React Query v5 + Axios (pinned to known-safe version due to supply chain concerns)
- **UI state**: Zustand for session, sidebar state, active workspace context
- **Styling**: Tailwind CSS (already set up, keep it)
- **Login UX**: Separate /login page. Email input → "Check your email" → magic link opens → redirects to /dashboard
- **Navigation**: Keep existing sidebar layout (workspace, projects, settings, sign out)
- **GitHub integration**: Settings page → Integrations tab → "Connect GitHub" button → OAuth flow via Core → TPS
- **Route structure**: `(public)/` for landing + login + auth verify, `(app)/` for protected dashboard routes
- **Domain data structure** (adapted from esd-frontend):
  ```
  src/data/
    auth/
      types.ts        # Session, User interfaces
      api.ts          # login, verify, logout, getSession
      constants.ts    # React Query keys
      store.ts        # useSession, useLogin hooks
    services/
      types.ts        # Service, RouteGraph interfaces
      api.ts          # createService, getService, deleteService
      constants.ts    # Query keys
      store.ts        # useServices, useServiceStatus hooks
    projects/
      types.ts, api.ts, constants.ts, store.ts
    integrations/
      types.ts, api.ts, constants.ts, store.ts
  ```

## ESD-Frontend Pattern Mapping

| ESD Pattern | GenAlpha Adaptation |
|---|---|
| `src/data/{domain}/` (types, api, store) | Same structure, same convention |
| React Query v5 + Axios | Same (pin Axios version) |
| Zustand + immer | Zustand (skip immer for MVP simplicity) |
| `(app)/` grouped routes | Same — `(app)/` for protected, `(public)/` for landing/login |
| OIDC auth wrapper (`AuthContextWrapper`) | Session context provider checking Core `/auth/session` |
| `StaleTime.Longest\|Short` constants | Same pattern for query cache config |
| Conditional queries `enabled: !!id` | Same pattern |
| Obsidian DS + Styled Components | Tailwind CSS (already set up) |
| Domain-specific query key constants | Same — `QUERY_KEYS.services.list`, `QUERY_KEYS.services.detail(id)` |

## Pages Overview

```
(public)/
  page.tsx                    # Landing page (hero + "Get Started" CTA)
  login/page.tsx              # Email input → request magic link
  auth/verify/page.tsx        # Magic link landing → set session → redirect

(app)/
  layout.tsx                  # Sidebar + auth guard + session provider
  dashboard/page.tsx          # Workspace overview (projects + services)
  projects/[id]/page.tsx      # Project detail + parse form + service list
  services/[id]/page.tsx      # Service detail: mindmap + generate + download
  settings/page.tsx           # Workspace settings
  settings/integrations/page.tsx  # Connect GitHub / manage integrations
```

## Auth Flow (Frontend Perspective)

```
1. User visits /login → enters email → POST /api/auth/magic-link
2. "Check your email" message shown
3. User clicks magic link → /auth/verify?token=xxx
4. Verify page calls Core GET /auth/verify?token=xxx
5. Core returns session cookie (httpOnly, set by Core)
6. Frontend redirects to /dashboard
7. Every page load: GET /auth/session → validates cookie → returns user + workspace
8. If 401 → redirect to /login
```

## API Proxy Pattern

Next.js API routes proxy to Core (:8000). Frontend only calls /api/* on :3000.

```
Next.js /api/auth/*          → Core :8000/auth/*
Next.js /api/projects/*      → Core :8000/projects/*
Next.js /api/services/*      → Core :8000/services/*
Next.js /api/integrations/*  → Core :8000/integrations/*  (Core proxies to TPS)
```

## Open Questions

_None — all resolved during brainstorm._

## Next Steps

→ `/workflows:plan` for implementation details
→ Remove Auth.js + old auth routes
→ Install React Query + Axios + Zustand
→ Create data layer structure
→ Build login/verify pages
→ Wire dashboard to Core API via proxy routes
