---
title: "feat: Dashboard UI Redesign"
type: feat
status: active
date: 2026-04-11
---

# feat: Dashboard UI Redesign

## Overview

Redesign all 7 dashboard pages with shadcn/ui components, collapsible Linear-style sidebar, and drill-down navigation: Workspaces → Projects → Services. Clean developer dashboard aesthetic.

## Implementation Phases

### Phase 1: Foundation (shadcn/ui + sidebar)

**Tasks:**

- [ ] Initialize shadcn/ui: `npx shadcn@latest init`
- [ ] Install core components: Button, Card, Badge, Tabs, Dialog, AlertDialog, Table, DropdownMenu, Separator, Tooltip, Avatar
- [ ] Build `components/dashboard/sidebar.tsx`:
  - Collapsible (full → icon-only) with toggle button
  - Workspace name at top
  - Navigation: Dashboard, Projects (with sub-items), Integrations
  - Active state highlighting via `usePathname()`
  - User info + sign out at bottom
  - Persist collapsed state in localStorage
- [ ] Build `components/dashboard/breadcrumb.tsx`: dynamic breadcrumb from route segments
- [ ] Build `components/dashboard/page-header.tsx`: reusable heading + description + action buttons
- [ ] Update `(app)/layout.tsx` to use new sidebar (replace current one)

**Files:**
```
web/src/components/dashboard/sidebar.tsx
web/src/components/dashboard/breadcrumb.tsx
web/src/components/dashboard/page-header.tsx
web/src/app/(app)/layout.tsx
web/src/components/ui/  (shadcn generated)
```

**Success criteria:**
- [ ] Sidebar collapses/expands with animation
- [ ] Active page highlighted in sidebar
- [ ] Breadcrumbs show on all pages

### Phase 2: Dashboard Home (workspace cards)

**Tasks:**

- [ ] Redesign `(app)/dashboard/page.tsx`:
  - PageHeader: "Your Workspaces"
  - Grid of workspace cards (shadcn Card)
  - Active workspace: name, slug, service count, last activity, "Open" button
  - Locked workspace: grayed out, lock icon, "Coming soon" badge
- [ ] Build `components/dashboard/workspace-card.tsx`
- [ ] Click workspace → navigate to projects view

**Success criteria:**
- [ ] Shows 1 real workspace + 1 locked placeholder
- [ ] Click active workspace → navigates to projects

### Phase 3: Projects View

**Tasks:**

- [ ] Redesign project listing (inside workspace):
  - Breadcrumb: Dashboard > Workspace Name
  - "New Project" button → shadcn Dialog with name/description form
  - Project cards grid: name, description, service count, last activity
  - Empty state with CTA
- [ ] May need a new route `/workspaces/[id]` or reuse `/dashboard` with workspace context

**Success criteria:**
- [ ] Project cards with service counts
- [ ] Create project dialog works
- [ ] Empty state guides new users

### Phase 4: Project Detail (services + add service modal)

**Tasks:**

- [ ] Redesign `(app)/projects/[id]/page.tsx`:
  - Breadcrumb: Dashboard > Workspace > Project Name
  - PageHeader with project name + "+ Add Service" button
  - Service cards grid: shadcn Card with Badge for status, framework tag, route count
  - Delete service: shadcn AlertDialog confirmation
  - Empty state: "No services yet. Click + to parse your first repo."
  - Service limit indicator: "X/2 slots used" badge
- [ ] Build `components/dashboard/service-card.tsx`
- [ ] Build `components/dashboard/add-service-dialog.tsx` (shadcn Dialog modal):
  - Source dropdown (shadcn Select): shows only connected integrations (GitHub, GitLab, etc.)
  - URL input for the selected source
  - "Or" divider with alternative options: Upload ZIP, Paste OpenAPI Spec (disabled for MVP, coming soon badges)
  - Service limit indicator in the modal
  - Parse button triggers workflow, modal closes, card appears with progress
- [ ] The dialog takes `source_type` + `source_value` + `integration_id` — extensible for future sources

**Success criteria:**
- [ ] "+ Add Service" button opens modal
- [ ] Source dropdown shows connected integrations only
- [ ] Parse starts from modal → service card appears with live status
- [ ] Delete confirmation dialog
- [ ] Upload ZIP / Paste OpenAPI show as "coming soon"

### Phase 5: Service Detail (tabbed view)

**Tasks:**

- [ ] Redesign `(app)/services/[id]/page.tsx`:
  - Header: service name, repo URL, status, framework, route count
  - shadcn Tabs component with 4 tabs:
    - **Mindmap**: React Flow graph (full width in tab panel)
    - **Routes**: shadcn Table with method badge, path, param count, description
    - **Generate**: output type selector, CLI name, base URL, generate button, download link
    - **Settings**: delete service button, re-parse button
- [ ] Build `components/dashboard/routes-table.tsx` (table view of all routes)
- [ ] Fix React Flow edge warnings (sanitize node IDs)
- [ ] Restyle generate panel with shadcn inputs

**Success criteria:**
- [ ] 4 tabs work with proper content
- [ ] Routes table shows all parsed routes with sorting
- [ ] Generate works from the Generate tab
- [ ] React Flow renders without edge warnings

### Phase 6: Integrations (/integrations)

**Tasks:**

- [ ] Move integrations to top-level route: `(app)/integrations/page.tsx`
- [ ] Remove `/settings` pages (merge workspace info into integrations page)
- [ ] Redesign integrations page:
  - PageHeader: "Integrations"
  - Connected apps section: shadcn Card per app, Badge for status, disconnect with AlertDialog
  - Available apps section: app cards with Connect button
  - Workspace info section at bottom: name, slug, email (shadcn Card)
- [ ] Update sidebar: replace "Settings > Integrations" with direct "Integrations" nav item
- [ ] Update OAuth callback redirect to `/integrations`

**Success criteria:**
- [ ] Integrations is a top-level sidebar item (not nested under settings)
- [ ] Connect/disconnect GitHub works
- [ ] Workspace info visible on the page

## Tech Stack

| Library | Purpose |
|---------|---------|
| shadcn/ui | Button, Card, Badge, Tabs, Dialog, AlertDialog, Table, etc. |
| Radix Primitives | Headless components underneath shadcn |
| Tailwind CSS | Styling (already set up) |
| Framer Motion | Page transitions, hover effects (already installed) |
| React Flow | Mindmap tab (already installed) |

## Component Structure

```
web/src/components/
  dashboard/
    sidebar.tsx           # Collapsible sidebar
    breadcrumb.tsx        # Dynamic breadcrumbs
    page-header.tsx       # Reusable page header
    workspace-card.tsx    # Workspace card (active + locked)
    service-card.tsx      # Service card with status
    parse-form.tsx        # GitHub URL parse form
    routes-table.tsx      # Routes table view
  ui/                     # shadcn/ui generated components
    button.tsx
    card.tsx
    badge.tsx
    tabs.tsx
    dialog.tsx
    alert-dialog.tsx
    table.tsx
    input.tsx
    separator.tsx
    tooltip.tsx
    avatar.tsx
    dropdown-menu.tsx
```

## References

- Brainstorm: `docs/design/brainstorms/2026-04-11-dashboard-ui-brainstorm.md`
- [shadcn/ui docs](https://ui.shadcn.com/)
- [Linear app](https://linear.app/) — sidebar, breadcrumbs, card patterns
