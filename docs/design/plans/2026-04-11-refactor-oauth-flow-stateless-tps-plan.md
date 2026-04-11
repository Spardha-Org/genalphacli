---
title: "refactor: OAuth flow — stateless TPS, encrypted state in Core"
type: refactor
status: active
date: 2026-04-11
---

# refactor: OAuth flow — stateless TPS, encrypted state in Core

## Overview

Restructure the OAuth flow to match the Java TPS (Atomicwork) pattern. Core generates an encrypted state blob containing user/app/callback context, TPS just plugs it into the OAuth URL (stateless), the OAuth provider redirects to Core's public callback endpoint, Core decrypts state to recover context and calls TPS to exchange code for token.

## Problem Statement

Current flow has TPS managing OAuth state in a database table (`tps_oauth_states`) — this is wrong. The Java TPS is completely stateless regarding OAuth. State is an encrypted blob owned by Core (ESD equivalent) that encodes all the context needed to resume the flow after the OAuth redirect.

Current (broken):
```
Frontend → Core → TPS (stores state in DB) → OAuth URL
Provider callback → Frontend → Core → TPS (validates state from DB)
```

Target (matching Java TPS):
```
Frontend → Core (encrypts state) → TPS (builds URL, stateless) → OAuth URL
Provider callback → Core (decrypts state, recovers context) → TPS (exchanges code)
Core → redirects browser to Frontend
```

## Technical Approach

### The Encrypted State Pattern (from Java TPS)

Core creates an `OAuthState` dataclass:
```python
@dataclass
class OAuthState:
    user_id: str
    app_name: str
    app_id: str
    timestamp: float
    callback_path: str  # frontend path to redirect after success (e.g., "/integrations")
    form_data: dict | None = None  # for form-based OAuth2
```

Core serializes → encrypts (Fernet) → URL-encodes this into the `state` parameter. On callback, Core decodes → decrypts → deserializes to recover the full context without any database lookup.

### Flow Diagram

```
Step 1: Frontend clicks "Connect GitHub"
  → POST /api/integrations/github/install
    body: { redirect_uri, callback_path, form_data? }

Step 2: Core receives request
  → Builds OAuthState(user_id, app_name="github", callback_path="/integrations", ...)
  → Encrypts state with Fernet → URL-encodes
  → Calls tps.build_oauth_url(app_name, state, redirect_uri)
  → TPS handler builds: https://github.com/login/oauth/authorize?client_id=X&state=ENCRYPTED&redirect_uri=CORE_CALLBACK
  → Returns { authorize_url } to frontend

Step 3: Frontend redirects browser to authorize_url

Step 4: User authorizes on GitHub

Step 5: GitHub redirects to Core's public callback
  → GET /api/oauth/callback?code=X&state=ENCRYPTED
  → Core decrypts state → recovers user_id, app_name, callback_path
  → Calls tps.exchange_code(user_id, app_name, code, redirect_uri)
  → TPS exchanges code for token, stores integration
  → Core redirects browser (HTTP 302) to: {APP_URL}{callback_path}?connected=true

Step 6: Frontend loads with ?connected=true, shows success
```

### Key Differences from Current

| Aspect | Current | Target |
|--------|---------|--------|
| State storage | TPS DB table | Encrypted blob in URL |
| State validation | TPS validates | Core decrypts |
| OAuth callback | Frontend page | Core public endpoint |
| TPS role in install | Stores state, builds URL | Just builds URL (stateless) |
| TPS role in exchange | Validates state, exchanges code | Just exchanges code |
| Frontend callback page | Calls exchange API | Not needed — Core handles everything |
| redirect_uri sent to provider | Frontend callback URL | Core's `/api/oauth/callback` |

## Implementation Phases

### Phase 1: Core — OAuth State Encryption

**Tasks:**
- [ ] Create `services/core/oauth_state.py` with:
  - `OAuthState` dataclass (user_id, app_name, timestamp, callback_path, form_data)
  - `encode_state(state: OAuthState) -> str` — serialize → Fernet encrypt → URL-safe base64
  - `decode_state(encoded: str) -> OAuthState` — reverse
  - Uses `CORE_MAGIC_LINK_SECRET` (already exists) or a dedicated `CORE_OAUTH_STATE_SECRET`
  - State expires after 15 minutes (check timestamp on decode)

**Files:**
```
services/core/oauth_state.py (NEW)
```

**Success criteria:**
- [ ] `encode_state` → `decode_state` roundtrips correctly
- [ ] Expired state (>15 min) raises ValueError
- [ ] Tampered state raises ValueError

### Phase 2: Core — Public OAuth Callback Endpoint

**Tasks:**
- [ ] Add `GET /api/oauth/callback` to Core — public endpoint (no session required)
  - Reads `code` and `state` from query params
  - Decrypts state → recovers `user_id`, `app_name`, `callback_path`
  - Calls `tps.exchange_code(db, user_id, app_name, code, redirect_uri)`
  - On success: HTTP 302 redirect to `{APP_URL}{callback_path}?connected={app_name}`
  - On failure: HTTP 302 redirect to `{APP_URL}{callback_path}?error=oauth_failed`
- [ ] This endpoint does NOT require session cookie (it's the OAuth redirect target)
- [ ] Register in `services/core/main.py`

**Files:**
```
services/core/routes/oauth_callback.py (NEW)
services/core/main.py (register router)
```

**Success criteria:**
- [ ] GitHub redirects to this endpoint after authorization
- [ ] Decrypts state, exchanges code, redirects to frontend
- [ ] Invalid/expired state redirects with error

### Phase 3: Update Core Install Endpoint

**Tasks:**
- [ ] Rewrite `POST /api/integrations/{app_name}/install` in Core:
  - Receives: `{ callback_path, form_data? }` from frontend
  - Builds `OAuthState(user_id, app_name, callback_path, ...)`
  - Encrypts state
  - `redirect_uri` = Core's own callback URL: `{APP_URL}/api/oauth/callback`
  - Calls `tps.build_oauth_url(app_name, state, redirect_uri)`
  - Returns `{ authorize_url }` to frontend
- [ ] Frontend no longer sends `state` — Core generates it

**Files:**
```
services/core/routes/integrations.py (update install endpoint)
```

### Phase 4: TPS — Simplify to Stateless

**Tasks:**
- [ ] TPS `install` endpoint: receives `{ state, redirect_uri }`, builds OAuth URL, returns it. No DB writes.
- [ ] TPS `exchange` endpoint: receives `{ code }`, exchanges with provider, stores integration. No state validation.
- [ ] Remove `OAuthState` model from `services/tps/models.py` (already done)
- [ ] Remove `tps_oauth_states` table from migration (already done)
- [ ] Update `tps_client.py` SDK:
  - `build_oauth_url(app_name, state, redirect_uri)` → returns authorize URL
  - `exchange_code(user_id, app_name, code, redirect_uri)` → exchanges and stores

**Files:**
```
services/tps/routes/integrations.py (simplify install/exchange)
services/core/tps_client.py (update SDK methods)
```

### Phase 5: Frontend — Simplify

**Tasks:**
- [ ] Remove callback page (`web/src/app/(app)/settings/integrations/callback/page.tsx`)
  - No longer needed — Core handles the callback and redirects
- [ ] Update install flow:
  - `POST /api/integrations/github/install` with `{ callback_path: "/integrations" }`
  - Receive `{ authorize_url }`
  - `window.location.href = authorize_url`
- [ ] Handle `?connected=github` query param on integrations page to show success toast
- [ ] Remove `sessionStorage` state management — not needed anymore
- [ ] Update `integrationsApi` — remove `exchange()`, simplify `install()`

**Files:**
```
web/src/app/(app)/settings/integrations/callback/page.tsx (DELETE)
web/src/data/api.ts (simplify)
web/src/app/(app)/integrations/page.tsx or equivalent (handle ?connected param)
```

### Phase 6: Tests

**Tasks:**
- [ ] Test: `encode_state` → `decode_state` roundtrip
- [ ] Test: expired state (>15 min) rejected
- [ ] Test: tampered state rejected
- [ ] Test: Core install endpoint returns authorize_url with encrypted state
- [ ] Test: Core callback endpoint decrypts state, calls TPS exchange
- [ ] Test: Core callback redirects to frontend on success/failure
- [ ] Test: TPS install just builds URL (no DB side effects)
- [ ] Test: TPS exchange just exchanges code (no state validation)
- [ ] Update existing TPS tests (remove state-related assertions)

**Files:**
```
tests/core/test_oauth_state.py (NEW)
tests/core/test_oauth_callback.py (NEW)
tests/tps/test_tps.py (update)
```

## Acceptance Criteria

### Functional
- [ ] Full OAuth flow works: click Connect → GitHub → callback → integration saved
- [ ] TPS has zero OAuth state — no DB table, no state validation
- [ ] Core generates encrypted state, Core validates it on callback
- [ ] Frontend has no callback page — Core handles redirect
- [ ] Expired state (>15 min) is rejected gracefully
- [ ] Non-OAuth apps (API Key, Basic Auth) are unaffected

### Security
- [ ] State is Fernet-encrypted — cannot be forged or tampered
- [ ] State includes timestamp — expires after 15 minutes
- [ ] Callback endpoint is public but only processes valid encrypted state
- [ ] No user session required at callback (context is in the encrypted state)

## References

- Java TPS state generation: `Atomicwork/esd/.../AtomicMarketplaceServiceImpl.java:444-528`
- Java TPS state validation: `Atomicwork/esd/.../ExternalOauthApiFilter.java:52-87`
- Java TPS state POJO: `Atomicwork/esd/.../AtomicAppIntegrationState.java`
- Java TPS stateless handler: `Atomicwork/third-party-app-integration/.../GithubHandler.java:42-51`
- Current Core integrations: `services/core/routes/integrations.py`
- Current TPS routes: `services/tps/routes/integrations.py`
- Current TPS client SDK: `services/core/tps_client.py`
