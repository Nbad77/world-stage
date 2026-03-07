"""
Clerk JWT Authentication — FastAPI dependency

Verifies Bearer tokens issued by Clerk using their JWKS endpoint.
Looks up or creates a User record in the database on each request.

Usage:
    @app.post("/game/new")
    def new_game(user: User = Depends(get_current_user)):
        ...

Environment:
    CLERK_SECRET_KEY  — Clerk secret key (sk_...)
    CLERK_ISSUER      — optional, defaults to https://<instance>.clerk.accounts.dev
"""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Union

import httpx
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, Request
from jose import JWTError, jwt
from sqlmodel import Session, select

from database import User, engine

# ── Load env ────────────────────────────────────────────────────────────────
_ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=False)

CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY", "")
CLERK_ISSUER = os.getenv("CLERK_ISSUER", "")

# ── JWKS cache ──────────────────────────────────────────────────────────────
# Clerk publishes public keys at /.well-known/jwks.json under the issuer URL.
# We cache the JWKS after first fetch to avoid hitting the endpoint every request.
_jwks_cache: Optional[dict] = None


async def _fetch_jwks(issuer: str) -> dict:
    """Fetch Clerk's JWKS from the issuer's well-known endpoint."""
    global _jwks_cache
    if _jwks_cache is not None:
        return _jwks_cache

    url = f"{issuer.rstrip('/')}/.well-known/jwks.json"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=10)
        resp.raise_for_status()
        _jwks_cache = resp.json()
        return _jwks_cache


def _get_signing_key(jwks: dict, token: str) -> dict:
    """Extract the correct signing key from JWKS based on the token's kid header."""
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    raise HTTPException(status_code=401, detail="Signing key not found in JWKS")


# ── FastAPI dependency ──────────────────────────────────────────────────────

async def get_current_user(request: Request) -> User:
    """
    FastAPI dependency: extracts Bearer token, verifies Clerk JWT,
    looks up or creates User record, returns User.

    Raises 401 if:
    - No Authorization header
    - Token is invalid or expired
    - Clerk JWKS cannot be fetched
    """
    # Extract token
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = auth_header[len("Bearer "):]

    if not CLERK_ISSUER:
        raise HTTPException(
            status_code=500,
            detail="CLERK_ISSUER not configured — cannot verify JWT",
        )

    # Fetch JWKS and find signing key
    try:
        jwks = await _fetch_jwks(CLERK_ISSUER)
        signing_key = _get_signing_key(jwks, token)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Failed to fetch JWKS: {e}")

    # Verify JWT
    try:
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            issuer=CLERK_ISSUER,
            options={"verify_aud": False},  # Clerk tokens don't always include aud
        )
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

    # Extract Clerk user ID and email from claims
    clerk_user_id = payload.get("sub")
    if not clerk_user_id:
        raise HTTPException(status_code=401, detail="Token missing 'sub' claim")

    # Clerk stores email in various claim locations
    email = (
        payload.get("email")
        or payload.get("email_address")
        or payload.get("primary_email_address", "")
    )

    # Look up or create User
    # is_test comes from custom session token claim (top-level) or nested public_metadata
    is_test = bool(payload.get("is_test", False))
    if not is_test:
        # Fallback: check nested public_metadata (in case full object is included)
        public_metadata = payload.get("public_metadata", {}) or {}
        is_test = bool(public_metadata.get("is_test", False))
    print(f"[AUTH] JWT is_test claim: {payload.get('is_test')}, resolved is_test={is_test}")

    with Session(engine) as session:
        stmt = select(User).where(User.clerk_user_id == clerk_user_id)
        user = session.exec(stmt).first()

        if user is None:
            user = User(
                clerk_user_id=clerk_user_id,
                email=email or "",
                is_test=is_test,
                created_at=datetime.now(timezone.utc),
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            print(f"[AUTH] New user created: {user.id}, clerk_id={clerk_user_id}")
        else:
            # Sync is_test flag from Clerk metadata on every login
            if user.is_test != is_test:
                user.is_test = is_test
                session.add(user)
                session.commit()
                session.refresh(user)
                print(f"[AUTH] User is_test synced: {user.id}, is_test={user.is_test}")

        print(f"[AUTH] User authenticated: {user.id}, is_test={user.is_test}")
        return user


async def get_optional_user(request: Request) -> Optional[User]:
    """
    FastAPI dependency: same as get_current_user but returns None
    instead of raising 401 when no auth is provided.
    Used to allow guest (anonymous) play while still supporting
    authenticated sessions when a Clerk JWT is present.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        print("[AUTH] No auth header — guest mode")
        return None

    # Token is present — delegate to full verification
    try:
        return await get_current_user(request)
    except Exception as e:
        print(f"[AUTH] Token verification failed, falling back to guest: {e}")
        return None
