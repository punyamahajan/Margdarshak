"""Minimal Agora Token007 builder for a browser RTC user with RTM access.

The legacy ``agora-token-builder`` PyPI package only emits Token006. Agora's
current Signaling SDK requires the Token007 multi-service envelope.
"""

import base64
import hmac
import secrets
import struct
import time
import zlib
from hashlib import sha256


def _u16(value: int) -> bytes:
    return struct.pack("<H", value)


def _u32(value: int) -> bytes:
    return struct.pack("<I", value)


def _string(value: bytes) -> bytes:
    return _u16(len(value)) + value


def _privileges(values: dict[int, int]) -> bytes:
    packed = _u16(len(values))
    for key, value in sorted(values.items()):
        packed += _u16(key) + _u32(value)
    return packed


def build_rtc_rtm_token(
    app_id: str,
    app_certificate: str,
    channel_name: str,
    user_id: str,
    expires_at: int,
) -> str:
    """Build one publisher token accepted by both RTC and RTM clients."""

    if len(app_id) != 32 or len(app_certificate) != 32:
        raise ValueError("Agora App ID and certificate must be 32 characters")

    # Service 1: RTC. Privileges are join, publish audio/video/data.
    rtc = (
        _u16(1)
        + _privileges({1: expires_at, 2: expires_at, 3: expires_at, 4: expires_at})
        + _string(channel_name.encode())
        + _string(user_id.encode())
    )
    # Service 2: RTM/Signaling login for the same user account.
    rtm = _u16(2) + _privileges({1: expires_at}) + _string(user_id.encode())

    issued_at = int(time.time())
    salt = secrets.SystemRandom().randint(1, 99_999_999)
    signing_info = (
        _string(app_id.encode())
        + _u32(issued_at)
        + _u32(expires_at)
        + _u32(salt)
        + _u16(2)
        + rtc
        + rtm
    )
    signing_key = hmac.new(_u32(issued_at), app_certificate.encode(), sha256).digest()
    signing_key = hmac.new(_u32(salt), signing_key, sha256).digest()
    signature = hmac.new(signing_key, signing_info, sha256).digest()
    payload = zlib.compress(_string(signature) + signing_info)
    return "007" + base64.b64encode(payload).decode()
