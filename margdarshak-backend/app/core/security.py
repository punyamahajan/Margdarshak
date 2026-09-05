"""Small role boundary for the coordinator API.

Production deployments should replace the development key with a Supabase/JWT
identity provider while keeping this dependency contract.
"""
import secrets

from fastapi import Header, HTTPException

from app.core.config import get_settings


async def require_coordinator(authorization: str | None = Header(default=None)) -> None:
    expected = get_settings().admin_api_key.get_secret_value()
    supplied = authorization.removeprefix("Bearer ").strip() if authorization else ""
    if not expected or not secrets.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="coordinator authentication required")
