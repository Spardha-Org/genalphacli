"""Magic link token generation and verification using itsdangerous."""

from __future__ import annotations

import logging

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from services.core.config import settings

logger = logging.getLogger(__name__)

_serializer = URLSafeTimedSerializer(settings.magic_link_secret, salt="magic-link-v1")


def create_magic_token(email: str) -> str:
    """Create a signed magic link token containing the user's email."""
    return _serializer.dumps({"email": email})


def verify_magic_token(token: str) -> str | None:
    """Verify a magic link token. Returns email if valid, None if expired/tampered."""
    try:
        data = _serializer.loads(token, max_age=settings.magic_link_max_age)
        return data["email"]
    except SignatureExpired:
        logger.warning("Magic link token expired")
        return None
    except BadSignature:
        logger.warning("Magic link token has invalid signature")
        return None
