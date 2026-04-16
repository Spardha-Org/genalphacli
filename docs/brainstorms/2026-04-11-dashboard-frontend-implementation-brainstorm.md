---
date: 2026-04-11
topic: dashboard-frontend-implementation
---

# Dashboard Frontend Implementation

## What We're Building

Port the `dashboard-preview.html` design to React/Next.js with real data from backend APIs. First layer: **Projects page** and **App Store page** with bottom nav, fully functional.

### Scope
- **Projects page** (`/`) — grid of project cards with search, create project modal, random images
- **App Store page** (`/app-store`) — app cards grouped by category, functional connect flow (OAuth + credential forms)
- **Bottom navigation** — switch between Projects and App Store (matching HTML preview)
- **NOT in scope**: Service Detail redesign (5 tabs), Project Detail page changes

### What already exists
- Backend APIs: `projectsApi`, `servicesApi`, `integrationsApi` — all working
- TanStack Query hooks: `useProjects`, `useCreateProject`, `useApps`, `useIntegrations`, `useInstallApp`
- 13 shadcn/ui components installed
- Current dashboard at `/dashboard` — basic project list (needs redesign to match preview)
- Current integrations at `/settings/integrations` — basic list (needs redesign to match preview)
- OAuth flow fully working E2E (GitHub tested)

## Why This Approach

### Projects + App Store first
These are the two main navigation destinations. Service Detail and Project Detail already work (just not redesigned). Getting the two top-level pages right with real data validates the full stack: frontend → Core → TPS.

### Bottom nav from preview
The HTML preview was iterated on with the user and finalized. The bottom nav pattern works well for the two-view layout and is mobile-friendly.

### Fully functional App Store
The OAuth flow is E2E tested. The backend returns `meta.form_fields` for dynamic modals. Building it functional now means the App Store actually works, not just looks pretty.

## Key Decisions

- **Route**: `/` for Projects (root authenticated page), `/app-store` for App Store
- **Navigation**: Bottom nav bar (from HTML preview), not sidebar or top nav links
- **Layout**: Update `(app)/layout.tsx` — keep minimal header (logo + sign out), add bottom nav
- **Project cards**: Square cards with `aspect-ratio: 1/1`, random images via picsum.photos, 3-line truncated description
- **App Store cards**: Grouped by category (Source Control, Hosting, Coming Soon), connected badge, simpleicons logos
- **Connect modals**: OAuth apps → redirect via `integrationsApi.install()`, API key apps → form modal rendered from `meta.form_fields`
- **Disconnect**: AlertDialog confirmation before disconnect
- **Create project**: shadcn Dialog modal with name + description fields
- **Search**: Client-side filter on project name

## Resolved Questions

- **Scope?** Projects + App Store. Not Service Detail redesign.
- **Navigation?** Bottom nav (from HTML preview).
- **App Store functional?** Yes — OAuth + credential forms, real connect flow.
- **Routes?** `/` for projects, `/app-store` for App Store.

## Next Steps

→ `/workflows:plan` for implementation details
