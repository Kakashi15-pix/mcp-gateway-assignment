from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from sqlalchemy import func, select

from db import SessionLocal
from models import ApiKey, Invitation, SessionToken, User

KEY_PREFIX = "mcp_"
LAST_USED_UPDATE_INTERVAL = timedelta(minutes=1)
_session_ttl_minutes = int(os.getenv("SESSION_TTL_MINUTES", "60"))
if _session_ttl_minutes < 1:
    raise ValueError("SESSION_TTL_MINUTES must be at least 1")
SESSION_TTL = timedelta(minutes=_session_ttl_minutes)
INVITATION_TTL = timedelta(days=7)


def hash_api_key(raw_key: str) -> str:
    """Store a one-way hash of an API key."""
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def generate_api_key() -> str:
    """Generate a high-entropy gateway API key."""
    return KEY_PREFIX + secrets.token_urlsafe(32)


def hash_password(password: str) -> str:
    if len(password) < 12:
        raise ValueError("Password must be at least 12 characters")
    if len(password.encode("utf-8")) > 72:
        raise ValueError("Password must be at most 72 UTF-8 bytes")
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("ascii")


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    return bcrypt.checkpw(
        password.encode("utf-8"),
        password_hash.encode("ascii"),
    )


def _generate_opaque_token() -> str:
    return secrets.token_urlsafe(32)


def _as_utc(dt: datetime) -> datetime:
    """Treat naive datetimes as UTC so comparisons never raise TypeError."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def create_api_key(
    user_id: Any,
    name: str,
    expires_at: datetime | None = None,
) -> tuple[str, str]:
    """
    Create a key for an existing, active user.

    Returns (raw_key, key_id). The raw key is shown only once.
    """
    now = datetime.now(timezone.utc)

    if expires_at is not None:
        expires_at = _as_utc(expires_at)
        if expires_at <= now:
            raise ValueError("expires_at must be in the future")

    raw_key = generate_api_key()
    digest = hash_api_key(raw_key)
    prefix = raw_key[:12]

    with SessionLocal() as db:
        user = db.get(User, user_id)

        if user is None:
            raise ValueError("User does not exist")

        if not user.is_active:
            raise ValueError("Cannot create a key for an inactive user")

        key = ApiKey(
            user_id=user_id,
            name=name,
            key_hash=digest,
            key_prefix=prefix,
            expires_at=expires_at,
        )
        db.add(key)
        db.commit()
        db.refresh(key)

        return raw_key, str(key.id)


def create_session(user_id: Any) -> tuple[str, datetime]:
    raw_token = _generate_opaque_token()
    expires_at = datetime.now(timezone.utc) + SESSION_TTL

    with SessionLocal() as db:
        user = db.get(User, user_id)
        if user is None or not user.is_active:
            raise ValueError("User does not exist or is inactive")
        db.add(
            SessionToken(
                user_id=user.id,
                token_hash=hash_api_key(raw_token),
                expires_at=expires_at,
            )
        )
        db.commit()

    return raw_token, expires_at


def authenticate_session(raw_token: str) -> dict[str, Any] | None:
    if not raw_token:
        return None

    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        session = db.scalars(
            select(SessionToken).where(
                SessionToken.token_hash == hash_api_key(raw_token),
                SessionToken.revoked_at.is_(None),
            )
        ).first()
        if session is None or _as_utc(session.expires_at) <= now:
            return None

        user = db.get(User, session.user_id)
        if user is None or not user.is_active:
            return None
        return {
            "id": str(user.id),
            "user_id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
            "role": user.role,
        }


def revoke_session(raw_token: str) -> bool:
    with SessionLocal() as db:
        session = db.scalars(
            select(SessionToken).where(
                SessionToken.token_hash == hash_api_key(raw_token),
                SessionToken.revoked_at.is_(None),
            )
        ).first()
        if session is None:
            return False
        session.revoked_at = datetime.now(timezone.utc)
        db.commit()
        return True


def create_invitation(
    email: str,
    role: str,
    invited_by: Any,
) -> tuple[str, str, datetime]:
    if role not in {"admin", "member"}:
        raise ValueError("Invalid invitation role")

    raw_token = _generate_opaque_token()
    expires_at = datetime.now(timezone.utc) + INVITATION_TTL
    normalized_email = email.strip().lower()

    with SessionLocal() as db:
        inviter = db.get(User, invited_by)
        if inviter is None or inviter.role != "admin" or not inviter.is_active:
            raise ValueError("Only an active admin can create invitations")
        invitation = Invitation(
            email=normalized_email,
            role=role,
            token_hash=hash_api_key(raw_token),
            invited_by=inviter.id,
            expires_at=expires_at,
        )
        db.add(invitation)
        db.commit()

    return raw_token, str(invitation.id), expires_at


def accept_invitation(raw_token: str, password: str, display_name: str | None):
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        invitation = db.scalars(
            select(Invitation).where(
                Invitation.token_hash == hash_api_key(raw_token),
                Invitation.accepted_at.is_(None),
                Invitation.revoked_at.is_(None),
            )
        ).first()
        if invitation is None or _as_utc(invitation.expires_at) <= now:
            raise ValueError("Invitation is invalid or expired")

        normalized_email = invitation.email.strip().lower()
        invitation.email = normalized_email
        existing = db.scalars(
            select(User).where(func.lower(User.email) == normalized_email)
        ).first()
        if existing is not None:
            raise ValueError("An account already exists for this email")

        user = User(
            email=invitation.email,
            display_name=display_name,
            role=invitation.role,
            password_hash=hash_password(password),
        )
        db.add(user)
        invitation.accepted_at = now
        db.commit()
        db.refresh(user)
        return str(user.id)


def revoke_invitation(invitation_id: Any, actor_user_id: Any) -> bool:
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        invitation = db.get(Invitation, invitation_id)
        if invitation is None:
            return False

        actor = db.get(User, actor_user_id)
        if actor is None or actor.role != "admin" or not actor.is_active:
            return False
        if invitation.accepted_at is None and invitation.revoked_at is None:
            invitation.revoked_at = now
            db.commit()
        return True


def authenticate_api_key(raw_key: str) -> dict[str, Any] | None:
    """
    Validate a key and return its active user identity.

    Returns None for every failure so callers cannot tell
    "unknown key" from "expired" or "revoked".
    """
    if not raw_key or not raw_key.startswith(KEY_PREFIX):
        return None

    digest = hash_api_key(raw_key)
    now = datetime.now(timezone.utc)

    with SessionLocal() as db:
        key = db.scalars(
            select(ApiKey).where(
                ApiKey.key_hash == digest,
                ApiKey.revoked_at.is_(None),
            )
        ).first()

        if key is None:
            return None

        if key.expires_at is not None and _as_utc(key.expires_at) <= now:
            return None

        user = db.get(User, key.user_id)

        if user is None or not user.is_active:
            return None

        # Avoid a DB write on every request.
        if (
            key.last_used_at is None
            or now - _as_utc(key.last_used_at) > LAST_USED_UPDATE_INTERVAL
        ):
            key.last_used_at = now
            db.commit()

        return {
            "user_id": str(user.id),
            "email": user.email,
            "role": user.role,
            "api_key_id": str(key.id),
        }


def revoke_api_key(
    key_id: Any,
    actor_user_id: Any,
    actor_role: str = "member",
) -> bool:
    """
    Revoke a key. Members can revoke their own keys; admins can
    revoke any key.
    """
    with SessionLocal() as db:
        key = db.get(ApiKey, key_id)
        if key is None:
            return False

        actor_id = str(actor_user_id)
        if actor_role != "admin" and str(key.user_id) != actor_id:
            return False

        if key.revoked_at is None:
            key.revoked_at = datetime.now(timezone.utc)
            db.commit()

        return True