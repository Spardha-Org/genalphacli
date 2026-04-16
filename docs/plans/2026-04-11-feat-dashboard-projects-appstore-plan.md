---
title: "feat: Dashboard — Projects page + App Store with bottom nav"
type: feat
status: active
date: 2026-04-11
---

# feat: Dashboard — Projects page + App Store with bottom nav

## Overview

Port the finalized `dashboard-preview.html` design to React/Next.js. First layer: Projects page (`/`) and App Store page (`/app-store`) with bottom navigation, connected to real backend APIs. Fully functional — projects CRUD, GitHub OAuth connect, credential-based app connect.

## Design Reference

`web/dashboard-preview.html` — open in browser for the exact design. Key design tokens:
- `--bg: #050507`, `--surface: #0a0a0e`, `--elevated: #0f0f14`, `--accent: #14b8a6`
- Fonts: JetBrains Mono (headings, code), Inter (body)
- Square cards: `aspect-ratio: 1/1`
- simpleicons CDN for app logos: `https://cdn.simpleicons.org/{brand}/{color}`
- picsum.photos for project images: `https://picsum.photos/seed/{id}/200/200`

## Implementation Phases

### Phase 1: Layout + Bottom Nav + Routes

**Tasks:**
- [ ] Update `(app)/layout.tsx`:
  - Keep minimal header: `// GenAlpha` logo (left) + sign out button (right)
  - Remove `Integrations` nav link and email from header
  - Add bottom nav bar with 2 buttons: Projects, App Store
  - Bottom nav highlights active route via `usePathname()`
  - Style matching HTML preview: fixed bottom, `--surface` background, `--accent` active color
- [ ] Create route `(app)/page.tsx` — Projects page (root `/`)
- [ ] Create route `(app)/app-store/page.tsx` — App Store page
- [ ] Remove or redirect `/dashboard` to `/`
- [ ] Remove `/settings` and `/settings/integrations` routes (merged into App Store)

**Files:**
```
web/src/app/(app)/layout.tsx (update)
web/src/app/(app)/page.tsx (NEW — projects)
web/src/app/(app)/app-store/page.tsx (NEW)
web/src/app/(app)/dashboard/page.tsx (DELETE or redirect)
web/src/app/(app)/settings/ (DELETE)
```

**Success criteria:**
- [ ] Bottom nav switches between `/` and `/app-store`
- [ ] Active route highlighted with accent color
- [ ] Header is minimal (logo + sign out only)

### Phase 2: Projects Page

**Tasks:**
- [ ] Build `components/dashboard/project-card.tsx`:
  - Square card (`aspect-ratio: 1/1`) with shadcn Card
  - Random image from `picsum.photos/seed/{project.id}/200/200`
  - Project name (bold), 3-line truncated description
  - Service count badge at top-right
  - Click → navigates to `/projects/{id}`
- [ ] Build Projects page (`(app)/page.tsx`):
  - Search bar (client-side filter on project name)
  - "New Project" button → opens create dialog
  - Grid of project cards (responsive: 1-4 columns)
  - Empty state: "No projects yet. Create your first project."
  - Uses `useProjects()` hook (already exists)
- [ ] Build `components/dashboard/create-project-dialog.tsx`:
  - shadcn Dialog with name + description fields
  - Uses `useCreateProject()` hook (already exists)
  - Auto-closes on success, invalidates query cache

**Files:**
```
web/src/components/dashboard/project-card.tsx (NEW)
web/src/components/dashboard/create-project-dialog.tsx (NEW)
web/src/app/(app)/page.tsx (implement)
```

**Success criteria:**
- [ ] Project cards render with real data from API
- [ ] Search filters projects by name
- [ ] Create project dialog works E2E
- [ ] Click card navigates to project detail

### Phase 3: App Store Page

**Tasks:**
- [ ] Build `components/dashboard/app-card.tsx`:
  - Square card matching HTML preview design
  - App logo from `meta.icon` (simpleicons CDN), centered, 70% size
  - App name below logo
  - Connected badge at top-right (green dot + "Connected")
  - Click connected app → disconnect dialog
  - Click unconnected OAuth app → `integrationsApi.install()` → redirect
  - Click unconnected credential app → open connect form modal
  - Coming soon apps → grayed out, no click action
- [ ] Build `components/dashboard/connect-form-dialog.tsx`:
  - Dynamic form rendered from `app.meta.form_fields`
  - Each field: label, input (type from field.type), required indicator
  - Submit → `integrationsApi.connect(appName, credentials)`
  - Uses shadcn Dialog + Input components
- [ ] Build `components/dashboard/disconnect-dialog.tsx`:
  - shadcn AlertDialog: "Disconnect {app_name}?"
  - Confirm → `integrationsApi.delete(integrationId)`
- [ ] Build App Store page (`(app)/app-store/page.tsx`):
  - Fetches apps via `useApps()` + integrations via `useIntegrations()`
  - Groups apps by `category`: Source Control, Hosting & Distribution, Coming Soon
  - Each group: header + row of app cards
  - Connected apps show connected badge
  - Uses new hooks: `useConnectApp()` for credential flow

**Files:**
```
web/src/components/dashboard/app-card.tsx (NEW)
web/src/components/dashboard/connect-form-dialog.tsx (NEW)
web/src/components/dashboard/disconnect-dialog.tsx (NEW)
web/src/app/(app)/app-store/page.tsx (implement)
web/src/data/hooks.ts (add useConnectApp hook)
```

**Success criteria:**
- [ ] Apps grouped by category with correct headers
- [ ] Connected apps show badge, unconnected show connect action
- [ ] GitHub OAuth flow works: click Connect → GitHub → callback → connected
- [ ] Credential form renders dynamically from meta.form_fields
- [ ] Disconnect works with confirmation

### Phase 4: Data Hooks + API Updates

**Tasks:**
- [ ] Add `useConnectApp` hook in `data/hooks.ts` — calls `integrationsApi.connect()`
- [ ] Add `useGetApp` hook for single app lookup
- [ ] Verify `useInstallApp` hook works with new install endpoint (callback_path param)
- [ ] Handle `?connected={app_name}` query param on App Store page (show success toast)
- [ ] Handle `?error=oauth_failed` query param (show error toast)

**Files:**
```
web/src/data/hooks.ts (update)
```

### Phase 5: Polish + Responsive

**Tasks:**
- [ ] Responsive grid: 1 col mobile, 2 col tablet, 3-4 col desktop
- [ ] Loading skeletons for project cards and app cards
- [ ] Error states for failed API calls
- [ ] Smooth transitions between views (Framer Motion already installed)
- [ ] Ensure dark theme consistency with design tokens

**Files:**
```
web/src/app/(app)/page.tsx (polish)
web/src/app/(app)/app-store/page.tsx (polish)
web/src/components/dashboard/*.tsx (polish)
```

## Acceptance Criteria

### Functional
- [ ] `/` shows project cards grid with real data
- [ ] Create project dialog works, new project appears in grid
- [ ] Click project card → navigates to `/projects/{id}`
- [ ] `/app-store` shows apps grouped by category
- [ ] GitHub Connect → OAuth flow → redirects back with `?connected=github`
- [ ] Credential app connect → form modal → stores credentials
- [ ] Disconnect → confirmation → removes integration
- [ ] Bottom nav switches between routes, highlights active
- [ ] Search filters projects by name

### Visual
- [ ] Matches `dashboard-preview.html` design
- [ ] Square cards with correct proportions
- [ ] Dark theme with design tokens
- [ ] App logos from simpleicons CDN
- [ ] Project images from picsum.photos

## Dependencies

- All backend APIs working (projects, integrations, apps) ✓
- TanStack Query hooks exist for all operations ✓
- shadcn/ui components installed (Card, Dialog, AlertDialog, Input, Badge, Button) ✓
- OAuth flow E2E tested ✓

## References

- Design reference: `web/dashboard-preview.html`
- Current dashboard: `web/src/app/(app)/dashboard/page.tsx`
- Current integrations: `web/src/app/(app)/settings/integrations/page.tsx`
- API client: `web/src/data/api.ts`
- Hooks: `web/src/data/hooks.ts`
- Layout: `web/src/app/(app)/layout.tsx`
- Brainstorm: `docs/design/brainstorms/2026-04-11-dashboard-frontend-implementation-brainstorm.md`
