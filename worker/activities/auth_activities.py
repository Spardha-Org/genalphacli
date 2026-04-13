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


def _filter_auth_candidates(route_graph: dict) -> list[dict]:
    """Filter POST routes that could be auth endpoints.

    Two-pass approach:
    1. First pass: POST routes with credential-like or identity-like params
    2. Fallback pass: POST routes with auth-related path segments
    """
    candidates = []

    for cmd in route_graph.get("subcommands", []):
        if cmd.get("method", "").upper() != "POST":
            continue

        param_names = {p["name"].lower() for p in cmd.get("params", [])}

        has_creds = bool(param_names & CRED_PARAMS)
        has_identity = bool(param_names & IDENTITY_PARAMS)

        if has_creds or has_identity:
            candidates.append({
                "endpoint": cmd["endpoint"],
                "method": cmd["method"],
                "name": cmd.get("name", ""),
                "params": [p["name"] for p in cmd.get("params", [])],
                "response_model": cmd.get("output", {}).get("response_model", ""),
                "description": cmd.get("description", ""),
            })

    # Fallback: path-based detection if no param matches
    if not candidates:
        for cmd in route_graph.get("subcommands", []):
            if cmd.get("method", "").upper() != "POST":
                continue
            path_lower = cmd.get("endpoint", "").lower()
            if any(seg in path_lower for seg in AUTH_PATH_SEGMENTS):
                candidates.append({
                    "endpoint": cmd["endpoint"],
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
