---
date: 2026-04-11
topic: dashboard-ui-redesign
---

# Dashboard UI Redesign — Developer Command Center

## What We're Building

Redesign all dashboard pages (7 pages) with a clean developer dashboard style inspired by Linear/Vercel. Using shadcn/ui components, collapsible sidebar, and a drill-down hierarchy: Workspaces → Projects → Services.

## Key Decisions

- **Style**: Clean developer dashboard (Linear/Vercel), NOT cinematic like the landing page. Dark theme carries over but the dashboard prioritizes usability and clarity.
- **Sidebar**: Collapsible like Linear — workspace switcher at top, project tree, icons, collapse to icon-only mode
- **Component library**: shadcn/ui + Tailwind (Radix primitives, copy-paste, fully customizable)
- **Dashboard home (/dashboard)**: Shows workspace cards. One real workspace + one locked placeholder card ("Only 1 workspace supported per user"). Click workspace → shows projects.
- **Project view**: Click project → shows service cards (repos). Parse form lives here.
- **Service detail**: Tabbed view — Mindmap | Routes (table) | Generate | Settings. One view at a time.
- **Hierarchy**: Dashboard → Workspace cards → Projects → Services (repos). Parsing happens at the service level within a project.

## Page Breakdown

### 1. Dashboard (/dashboard)
- Workspace cards in a grid
- Active workspace card: name, slug, service count, "Open" button
- Locked workspace card: grayed out, lock icon, "Coming soon — 1 workspace per user"
- Top bar: "Your Workspaces" heading + user avatar/menu

### 2. Workspace/Projects view (/dashboard or /projects)
- Breadcrumb: Dashboard > Workspace Name
- Project cards grid: name, description, service count, last activity
- "New Project" button (shadcn Dialog for creation form)
- Empty state when no projects

### 3. Project Detail (/projects/[id])
- Breadcrumb: Dashboard > Workspace > Project Name
- Parse form at top: GitHub URL input + Parse button
- Service cards below: name, repo URL, status badge, framework tag, route count
- Delete service with confirmation (shadcn AlertDialog)
- Service limit indicator (X/2 slots)

### 4. Service Detail (/services/[id])
- Breadcrumb: Dashboard > Workspace > Project > Service Name
- Header: service name, repo URL, status badge, framework
- **Tabs** (shadcn Tabs):
  - **Mindmap**: React Flow graph (full width within tab)
  - **Routes**: Table view of all routes with method badges, path, params count
  - **Generate**: CLI name, base URL, output type selector, generate button, download
  - **Settings**: Delete service, re-parse option

### 5. Settings (/settings)
- Workspace info (name, slug)
- Account info (email)
- Link to integrations

### 6. Integrations (/settings/integrations)
- Connected apps list with disconnect
- Available apps with connect button

## Design Tokens (shared with landing page)

```
Background: --bg (#050507), --surface (#0a0a0e), --elevated (#0f0f14)
Text: --text (#e4e4e7), --text-dim (#71717a), --text-muted (#3f3f46)
Accent: --accent (#14b8a6)
Font: JetBrains Mono for headings/code, Inter for body
```

## Sidebar Structure

```
┌─────────────────────┐
│ // GENALPHA    [<>]  │  ← collapse toggle
├─────────────────────┤
│ 🏠 Dashboard         │
│ 📁 Projects          │
│   └ Default Project  │
│   └ API v2           │
│ ⚙️ Settings          │
│   └ Integrations     │
├─────────────────────┤
│ 👤 nandish@...       │
│    Sign out           │
└─────────────────────┘
```

## Open Questions

_None — all resolved during brainstorm._

## Next Steps

→ `/workflows:plan` for implementation phases
→ Install shadcn/ui
→ Build sidebar, then page by page
