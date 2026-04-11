"""MultiFernet encryption for integration credentials.

Supports key rotation via comma-separated TPS_FERNET_KEYS env var.
The first key is the active encryption key; all keys are tried for decryption.
"""

from __future__ import annotations

import json
import logging

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from services.tps.config import settings

logger = logging.getLogger(__name__)

_fernet: MultiFernet | None = None


def get_fernet() -> MultiFernet:
    """Get the MultiFernet instance (lazy singleton)."""
    global _fernet
    if _fernet is None:
        if not settings.fernet_keys:
            raise RuntimeError(
                "TPS_FERNET_KEYS not set. Generate one with: "
                'python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
            )
        keys = [k.strip() for k in settings.fernet_keys.split(",") if k.strip()]
        _fernet = MultiFernet([Fernet(k.encode()) for k in keys])
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
