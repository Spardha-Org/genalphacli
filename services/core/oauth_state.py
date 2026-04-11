"""OAuth state encryption — encodes user/app context into an encrypted URL-safe blob.

Core generates this before redirecting to the OAuth provider. On callback,
Core decodes it to recover the user/app context without any database lookup.
TPS never sees or validates the state — it just passes it through.

Pattern copied from: Atomicwork ESD AtomicAppIntegrationState + SecretKeeper
"""

from __future__ import annotations

import json
import time
import logging
from dataclasses import dataclass, asdict
from urllib.parse import quote, unquote

from cryptography.fernet import Fernet, InvalidToken

from services.core.config import settings

logger = logging.getLogger(__name__)

STATE_MAX_AGE_SECONDS = 900  # 15 minutes

# Reuse the magic link secret for state encryption (already exists in config)
_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        key = settings.magic_link_secret
        # Fernet requires a 32-byte URL-safe base64-encoded key.
        # If the secret isn't a valid Fernet key, derive one.
        try:
            _fernet = Fernet(key.encode())
        except (ValueError, Exception):
            # Derive a Fernet key from the secret using padding
            import base64
            import hashlib
            derived = base64.urlsafe_b64encode(hashlib.sha256(key.encode()).digest())
            _fernet = Fernet(derived)
    return _fernet


@dataclass
class OAuthState:
    """Context needed to resume the OAuth flow after provider redirect."""
    user_id: str
    app_name: str
    timestamp: float
    callback_path: str  # frontend path, e.g. "/integrations"
    form_data: dict | None = None  # for form-based OAuth2 (tenant URL, etc.)


def encode_state(state: OAuthState) -> str:
    """Serialize → encrypt → URL-encode the state for use as OAuth state param."""
    payload = json.dumps(asdict(state))
    encrypted = _get_fernet().encrypt(payload.encode()).decode()
    return quote(encrypted, safe="")


def decode_state(encoded: str) -> OAuthState:
    """URL-decode → decrypt → deserialize the state. Validates expiry.

    Raises ValueError if state is invalid, tampered, or expired.
    """
    try:
        decoded = unquote(encoded)
        payload = _get_fernet().decrypt(decoded.encode()).decode()
        data = json.loads(payload)
    except (InvalidToken, json.JSONDecodeError, Exception) as e:
        logger.warning("Failed to decode OAuth state: %s", e)
        raise ValueError("Invalid or tampered OAuth state")

    # Check expiry
    timestamp = data.get("timestamp", 0)
    if time.time() - timestamp > STATE_MAX_AGE_SECONDS:
        raise ValueError("OAuth state expired")

    return OAuthState(
        user_id=data["user_id"],
        app_name=data["app_name"],
        timestamp=data["timestamp"],
        callback_path=data["callback_path"],
        form_data=data.get("form_data"),
    )
