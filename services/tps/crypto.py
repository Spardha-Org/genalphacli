"""Fernet encryption for integration credentials."""

from __future__ import annotations

import json
import logging

from cryptography.fernet import Fernet, InvalidToken

from services.tps.config import settings

logger = logging.getLogger(__name__)

_fernet: Fernet | None = None


def get_fernet() -> Fernet:
    """Get the Fernet instance (lazy singleton)."""
    global _fernet
    if _fernet is None:
        if not settings.fernet_key:
            raise RuntimeError(
                "TPS_FERNET_KEY not set. Generate one with: "
                'python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
            )
        _fernet = Fernet(settings.fernet_key.encode())
    return _fernet


def encrypt_config(config: dict) -> str:
    """Encrypt a config dict to a Fernet ciphertext string."""
    plaintext = json.dumps(config)
    return get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_config(ciphertext: str) -> dict:
    """Decrypt a Fernet ciphertext string to a config dict."""
    try:
        plaintext = get_fernet().decrypt(ciphertext.encode()).decode()
        return json.loads(plaintext)
    except InvalidToken:
        logger.error("Failed to decrypt integration config — invalid key or corrupted data")
        raise ValueError("Failed to decrypt integration config")
