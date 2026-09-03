import base64
import zlib

from app.services.agora_token007 import build_rtc_rtm_token


def test_combined_token_has_token007_envelope_and_both_services() -> None:
    token = build_rtc_rtm_token(
        "a" * 32, "b" * 32, "test-channel", "42", 2_000_000_000
    )

    assert token.startswith("007")
    payload = zlib.decompress(base64.b64decode(token[3:]))
    assert b"test-channel" in payload
    assert payload.count(b"42") == 2
