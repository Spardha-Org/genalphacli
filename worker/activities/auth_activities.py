"""Auth endpoint detection activity — framework-agnostic.

Works on the route graph (not source code). Any parser that produces
a CommandGraph-compatible dict gets auth detection for free.
"""

from __future__ import annotations

import logging

from temporalio import activity

from worker.activities.schemas import DetectAuthInput, DetectAuthOutput

logger = logging.getLogger(__name__)

# Credential-like param names (from AuthREST paper, validated on 100 APIs)
CRED_PARAMS = frozenset({
    "password", "passwd", "pass", "secret", "pin", "otp", "code",
    "token", "refresh_token", "grant_type",
})

# Identity-like param names
IDENTITY_PARAMS = frozenset({
    "username", "email", "login", "user", "phone", "account",
})

# Auth path segments (fallback when no credential params found)
AUTH_PATH_SEGMENTS = frozenset({
    "login", "signin", "sign-in", "authenticate", "auth",
    "token", "session", "oauth", "access-token",
})


# Response model names that strongly indicate a token endpoint
TOKEN_RESPONSE_MODELS = frozenset({
    "token", "tokenresponse", "tokendata", "authresponse", "loginresponse",
    "accesstoken", "authtoken", "bearer",
})


def _filter_auth_candidates(route_graph: dict) -> list[dict]:
    """Filter POST routes that could be auth endpoints.

    Uses three signals (any match qualifies):
    1. Has credential-like or identity-like params (password, username, email)
    2. Path contains auth-related segments (login, signin, auth, token)
    3. Response model name looks token-like (Token, AuthResponse, etc.)

    Frameworks like FastAPI strip DI params (OAuth2PasswordRequestForm),
    so we can't rely on params alone — path + response model are critical.
    """
    seen = set()
    candidates = []

    for cmd in route_graph.get("subcommands", []):
        if cmd.get("method", "").upper() != "POST":
            continue

        endpoint = cmd.get("endpoint", "")
        if endpoint in seen:
            continue

        param_names = {p["name"].lower() for p in cmd.get("params", [])}
        path_lower = endpoint.lower()
        response_model = (cmd.get("output", {}).get("response_model", "") or "").lower()
        description = (cmd.get("description", "") or "").lower()

        # Signal 1: credential/identity params
        has_creds = bool(param_names & CRED_PARAMS)
        has_identity = bool(param_names & IDENTITY_PARAMS)

        # Signal 2: auth-related path
        has_auth_path = any(seg in path_lower for seg in AUTH_PATH_SEGMENTS)

        # Signal 3: token-like response model
        has_token_response = response_model.replace("_", "").replace("-", "") in TOKEN_RESPONSE_MODELS

        # Signal 4: description mentions auth/login/token
        has_auth_description = any(
            kw in description
            for kw in ("login", "authenticate", "sign in", "access token", "auth token")
        )

        if has_creds or has_identity or has_auth_path or has_token_response or has_auth_description:
            seen.add(endpoint)
            candidates.append({
                "endpoint": endpoint,
                "method": cmd["method"],
                "name": cmd.get("name", ""),
                "params": [p["name"] for p in cmd.get("params", [])],
                "response_model": cmd.get("output", {}).get("response_model", ""),
                "description": cmd.get("description", ""),
            })

    return candidates


@activity.defn
def detect_auth_activity(input: DetectAuthInput) -> DetectAuthOutput:
    """Detect auth endpoints from route graph. Framework-agnostic.

    Uses heuristic filtering (no LLM call). Results are shown to user
    in a confirmation modal where they assign roles.
    """
    logger.info("Detecting auth endpoints for service %s", input.service_id)

    candidates = _filter_auth_candidates(input.route_graph)
    auth_type = input.route_graph.get("auth", {}).get("type", "none")

    logger.info(
        "Found %d auth candidates (auth_type: %s)",
        len(candidates),
        auth_type,
    )

    return DetectAuthOutput(candidates=candidates, auth_type=auth_type)
