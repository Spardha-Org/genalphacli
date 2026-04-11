"""Tests for OAuth state encryption/decryption."""

from __future__ import annotations

import time

import pytest

from services.core.oauth_state import OAuthState, encode_state, decode_state, STATE_MAX_AGE_SECONDS


class TestOAuthStateRoundtrip:

    def test_encode_decode_roundtrip(self):
        state = OAuthState(
            user_id="user-123",
            app_name="github",
            timestamp=time.time(),
            callback_path="/integrations",
        )
        encoded = encode_state(state)
        decoded = decode_state(encoded)

        assert decoded.user_id == "user-123"
        assert decoded.app_name == "github"
        assert decoded.callback_path == "/integrations"

    def test_preserves_form_data(self):
        state = OAuthState(
            user_id="u1", app_name="jira",
            timestamp=time.time(), callback_path="/settings",
            form_data={"tenant_url": "https://acme.atlassian.net"},
        )
        decoded = decode_state(encode_state(state))
        assert decoded.form_data == {"tenant_url": "https://acme.atlassian.net"}

    def test_encoded_is_not_plaintext(self):
        state = OAuthState(
            user_id="secret-user", app_name="github",
            timestamp=time.time(), callback_path="/x",
        )
        encoded = encode_state(state)
        assert "secret-user" not in encoded
        assert "github" not in encoded


class TestOAuthStateExpiry:

    def test_fresh_state_accepted(self):
        state = OAuthState(
            user_id="u1", app_name="github",
            timestamp=time.time(), callback_path="/x",
        )
        decoded = decode_state(encode_state(state))
        assert decoded.user_id == "u1"

    def test_expired_state_rejected(self):
        state = OAuthState(
            user_id="u1", app_name="github",
            timestamp=time.time() - STATE_MAX_AGE_SECONDS - 1,
            callback_path="/x",
        )
        with pytest.raises(ValueError, match="expired"):
            decode_state(encode_state(state))


class TestOAuthStateTamper:

    def test_tampered_state_rejected(self):
        state = OAuthState(
            user_id="u1", app_name="github",
            timestamp=time.time(), callback_path="/x",
        )
        encoded = encode_state(state)
        tampered = encoded[:-5] + "XXXXX"
        with pytest.raises(ValueError, match="Invalid"):
            decode_state(tampered)

    def test_garbage_state_rejected(self):
        with pytest.raises(ValueError, match="Invalid"):
            decode_state("completely-random-garbage-string")
