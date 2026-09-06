"""Authentication and profile token services for Margdarshak."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

from app.core.config import get_settings


def hash_password(password: str) -> str:
    """Hash a plaintext password with PBKDF2-HMAC-SHA256 and salt."""
    salt = secrets.token_bytes(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    salt_str = base64.b64encode(salt).decode("ascii")
    key_str = base64.b64encode(key).decode("ascii")
    return f"pbkdf2_sha256$100000${salt_str}${key_str}"


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plaintext password against a stored PBKDF2-HMAC-SHA256 hash."""
    try:
        algorithm, iterations, salt_b64, hash_b64 = password_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.b64decode(salt_b64.encode("ascii"))
        expected_key = base64.b64decode(hash_b64.encode("ascii"))
        key = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, int(iterations)
        )
        return hmac.compare_digest(key, expected_key)
    except Exception:
        return False


def _get_signing_secret() -> str:
    settings = get_settings()
    cert = settings.agora_app_certificate.get_secret_value()
    return cert.strip() if cert.strip() else "margdarshak-auth-secret-key-2026"


def create_access_token(data: dict[str, Any], expires_in_seconds: int = 86400 * 30) -> str:
    """Create a standard HMAC-SHA256 signed JWT token."""
    secret = _get_signing_secret()
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {**data, "exp": int(time.time()) + expires_in_seconds}

    h_b64 = (
        base64.urlsafe_b64encode(json.dumps(header).encode("utf-8"))
        .decode("ascii")
        .rstrip("=")
    )
    p_b64 = (
        base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8"))
        .decode("ascii")
        .rstrip("=")
    )
    signing_input = f"{h_b64}.{p_b64}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    s_b64 = base64.urlsafe_b64encode(sig).decode("ascii").rstrip("=")
    return f"{h_b64}.{p_b64}.{s_b64}"


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Validate and decode a signed JWT token."""
    secret = _get_signing_secret()
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        h_b64, p_b64, s_b64 = parts
        signing_input = f"{h_b64}.{p_b64}".encode("utf-8")
        expected_sig = hmac.new(
            secret.encode("utf-8"), signing_input, hashlib.sha256
        ).digest()
        s_bytes = base64.urlsafe_b64decode(s_b64 + "=" * (-len(s_b64) % 4))
        if not hmac.compare_digest(s_bytes, expected_sig):
            return None
        payload_bytes = base64.urlsafe_b64decode(p_b64 + "=" * (-len(p_b64) % 4))
        payload = json.loads(payload_bytes.decode("utf-8"))
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None
