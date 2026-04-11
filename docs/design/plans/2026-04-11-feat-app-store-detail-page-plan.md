---
title: "feat: App Store detail page with AuthorizationState pattern"
type: feat
status: active
date: 2026-04-11
---

# feat: App Store detail page with AuthorizationState pattern

## Overview

Restructure the App Store to match the ESD-frontend pattern: app list page shows cards that link to `/app-store/{appName}`, where a detail page renders the connection form based on `AuthorizationState` (Authorized, Unauthorized, FormBasedOAuth). Dynamic form fields from `meta.form_fields`, Test & Connect for credential apps, disconnect/update for connected apps.

## Problem Statement

Current App Store has inline modals for connect/disconnect — all logic crammed into one page. The ESD-frontend uses a separate detail page per app with cleaner state management via `AuthorizationState` enum. This also enables:
- Form-based OAuth2 (show form fields → then redirect to OAuth provider)
- Update credentials for connected apps (re-submit form values)
- Better UX for apps with many configuration fields

## Technical Approach

### AuthorizationState Pattern (from ESD-frontend)

```typescript
enum AuthorizationState {
  Authorized = "authorized",        // App is connected → show disconnect + update
  FormBasedOAuth = "form_oauth",     // Needs form fields before OAuth redirect
  Unauthorized = "unauthorized",     // Not connected → show form + Test & Connect
}

function getAuthorizationState(app: AppMarketplace, integration?: Integration): AuthorizationState {
  if (integration) return AuthorizationState.Authorized;
  if (app.is_install_required && app.auth_type === "form_based_oauth2") return AuthorizationState.FormBasedOAuth;
  return AuthorizationState.Unauthorized;
}
```

### Page Flow

```
/app-store                          → List page: cards grouped by category, click → detail
/app-store/[appName]                → Detail page: connection form based on AuthorizationState

AuthorizationState.Authorized:
  - Shows "Connected as {identifier}" badge
  - Form fields pre-filled with current config (if credential app)
  - "Update" button (re-submits form) + "Disconnect" button (AlertDialog)

AuthorizationState.FormBasedOAuth:
  - Shows form fields from meta.form_fields (e.g., tenant URL)
  - "Connect" button → submits form data + triggers OAuth redirect

AuthorizationState.Unauthorized:
  - OAuth apps (is_install_required=true): "Connect" button → OAuth redirect
  - Credential apps (is_install_required=false): form from meta.form_fields + "Connect" button
```

### Rendering Logic (per auth_type)

| auth_type | is_install_required | Detail Page Behavior |
|-----------|--------------------|--------------------|
| `oauth2` | true | "Connect" button → OAuth redirect. No form fields. |
| `form_based_oauth2` | true | Show form fields → "Connect" → submit fields + OAuth redirect |
| `api_key` | false | Form from meta.form_fields → "Connect" stores credentials |
| `basic_auth` | false | Username + Password form → "Connect" stores credentials |
| `mtls` | false | Cert + Key upload → "Connect" stores credentials |

## Implementation Phases

### Phase 1: App Store List Page — Cards Link to Detail

**Tasks:**
- [ ] Update `/app-store/page.tsx`:
  - Remove inline connect/disconnect modals
  - Cards now link to `/app-store/{appName}` instead of triggering actions
  - Connected badge stays on cards
  - Coming soon cards remain disabled (no link)
- [ ] Keep category grouping and search if added

**Files:**
```
web/src/app/(app)/app-store/page.tsx (simplify — remove modals)
```

### Phase 2: App Detail Page

**Tasks:**
- [ ] Create `web/src/app/(app)/app-store/[appName]/page.tsx`:
  - Fetches app via `useApps()` + filters by appName (matching ESD pattern — no single-app API)
  - Fetches integration via `useIntegrations()` + filters by app_name
  - Computes `AuthorizationState` from app + integration
  - Renders header: app icon (large) + display name + description from meta
  - Back link to `/app-store`
- [ ] Create `components/app-store/connection-form.tsx`:
  - Receives `app`, `integration`, `authorizationState`
  - **Authorized**: connected badge, pre-filled form (if credential app), Update + Disconnect buttons
  - **FormBasedOAuth**: form fields from meta.form_fields, Connect button → submit + redirect
  - **Unauthorized + OAuth**: just a Connect button → OAuth redirect
  - **Unauthorized + Credential**: form fields from meta.form_fields, Connect button
- [ ] Create `components/app-store/render-field.tsx`:
  - Generic field renderer: reads `type` (SHORT_TEXT, password, url, email) and renders appropriate Input
  - Handles required validation
  - Maps to shadcn Input with correct type prop

**Files:**
```
web/src/app/(app)/app-store/[appName]/page.tsx (NEW)
web/src/components/app-store/connection-form.tsx (NEW)
web/src/components/app-store/render-field.tsx (NEW)
```

### Phase 3: Connect Flows

**Tasks:**
- [ ] **OAuth flow** (Unauthorized + oauth2):
  - Click "Connect" → `integrationsApi.install(appName)` → `window.location.href = authorize_url`
- [ ] **Form-based OAuth flow** (FormBasedOAuth):
  - Fill form → Click "Connect" → `integrationsApi.install(appName, "/app-store", formValues)` → redirect
  - Core encrypts form_data into state, TPS builds URL with it
- [ ] **Credential flow** (Unauthorized + api_key/basic_auth):
  - Fill form → Click "Connect" → `integrationsApi.connect(appName, credentials)`
  - On success → invalidate queries → show connected state
- [ ] **Disconnect flow** (Authorized):
  - Click "Disconnect" → AlertDialog → `integrationsApi.delete(integrationId)`
  - On success → invalidate queries → show unauthorized state

**Files:**
```
web/src/components/app-store/connection-form.tsx (implement flows)
web/src/data/hooks.ts (may need useUpdateIntegration for update flow — future)
```

### Phase 4: Polish

**Tasks:**
- [ ] Success/error toast on `/app-store` when redirected from OAuth (`?connected=github`)
- [ ] Loading states on detail page
- [ ] Back navigation from detail to list
- [ ] App icon consistent sizing (56px like HTML preview)
- [ ] Dark theme consistency

**Files:**
```
web/src/app/(app)/app-store/page.tsx (toast handling)
web/src/app/(app)/app-store/[appName]/page.tsx (loading states)
```

## Acceptance Criteria

### Functional
- [ ] App Store list page shows cards linking to detail pages
- [ ] Detail page shows correct form based on AuthorizationState
- [ ] OAuth connect flow works (GitHub tested E2E)
- [ ] Credential connect flow works (form → store → show connected)
- [ ] Disconnect flow works with confirmation
- [ ] Connected apps show identifier and connected badge
- [ ] Coming soon apps are not clickable

### Visual
- [ ] Matches HTML preview design (dark theme, square cards, simpleicons logos)
- [ ] Detail page has app icon, name, description, connection form
- [ ] Form fields rendered dynamically from meta.form_fields

## References

- ESD-frontend connection form: `Atomicwork/esd-frontend/src/components/modules/settings/apps/detail/form/connection-form.tsx`
- ESD-frontend AuthorizationState: `Atomicwork/esd-frontend/src/components/modules/settings/apps/detail/form/utils.ts`
- ESD-frontend merge logic: `Atomicwork/esd-frontend/src/data/integration/store/use-marketplace-apps.ts`
- Current App Store: `web/src/app/(app)/app-store/page.tsx`
- HTML preview: `web/dashboard-preview.html`
- API types: `web/src/data/types.ts`
