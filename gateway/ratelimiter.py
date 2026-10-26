# ratelimit.py

import time
import uuid
from threading import Lock

from sqlalchemy import and_, or_, select

from db import SessionLocal
from models import McpTool, RateLimitPolicy


class InMemoryLimiter:
    """Thread-safe fixed-window rate limiter.

    Counters are stored in memory. Replace this implementation with Redis
    later if multiple gateway replicas need to share rate-limit counters.
    """

    def __init__(self):
        # bucket key -> (window_start, request_count, window_seconds)
        self._buckets: dict[tuple, tuple[int, int, int]] = {}
        self._lock = Lock()

    def acquire(self, checks):
        """Check all limits, then increment all counters atomically.

        Args:
            checks: Iterable of (bucket_key, max_requests, window_seconds).

        Returns:
            (True, 0) if allowed.
            (False, retry_after_seconds) if any limit is exceeded.

        A denied request consumes no quota from any other bucket.
        """
        now = int(time.time())
        checks = list(checks)

        # Validate every policy before modifying counters.
        for key, limit, window in checks:
            if limit < 1:
                raise ValueError(f"Rate limit must be >= 1; got {limit}")
            if window < 1:
                raise ValueError(
                    f"Window duration must be >= 1 second; got {window}"
                )

        with self._lock:
            state = []

            # First pass: check all limits without incrementing anything.
            for key, limit, window in checks:
                window_start = now - (now % window)
                entry = self._buckets.get(key)

                if entry is None or entry[0] != window_start:
                    count = 0
                else:
                    count = entry[1]

                if count >= limit:
                    retry_after = max(1, window_start + window - now)
                    return False, retry_after

                state.append((key, window_start, count, window))

            # Second pass: increment only if every check passed.
            for key, window_start, count, window in state:
                self._buckets[key] = (window_start, count + 1, window)

            # Drop only windows that have actually ended.
            if len(self._buckets) > 10_000:
                self._buckets = {
                    key: value
                    for key, value in self._buckets.items()
                    if value[0] + value[2] > now
                }

            return True, 0


limiter = InMemoryLimiter()


def bucket_for(policy, identity: dict, public_name: str) -> str:
    """Build the counter key for a policy's scope."""

    server_id = public_name.split("__", 1)[0]

    bucket_builders = {
        "global": lambda: "global",
        "user": lambda: f"user:{identity['user_id']}",
        "api_key": lambda: f"key:{identity['api_key_id']}",
        "server": lambda: f"server:{server_id}",
        "tool": lambda: f"tool:{public_name}",
    }

    try:
        return bucket_builders[policy.scope_type]()
    except KeyError as exc:
        raise ValueError(
            f"Unsupported rate-limit scope: {policy.scope_type}"
        ) from exc


def check_rate_limit(
    identity: dict,
    public_name: str,
) -> tuple[bool, int]:
    """Apply every enabled policy matching this request.

    The identity must contain user_id. api_key_id is optional; identities
    without it still match user, global, server, and tool policies.
    """

    if not identity:
        raise ValueError("Authenticated identity is required")

    try:
        user_id = uuid.UUID(str(identity["user_id"]))
        api_key_id = (
            uuid.UUID(str(identity["api_key_id"]))
            if identity.get("api_key_id") else None
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise ValueError(
            "Identity must contain a valid user_id and optional valid api_key_id UUID"
        ) from exc

    if not isinstance(public_name, str) or "__" not in public_name:
        raise ValueError(
            "public_name must use the server_id__tool_name format"
        )

    server_id = public_name.split("__", 1)[0]

    with SessionLocal() as db:
        tool = db.scalars(
            select(McpTool).where(McpTool.public_name == public_name)
        ).first()

        tool_id = tool.id if tool is not None else None

        conditions = [
            RateLimitPolicy.scope_type == "global",
            and_(
                RateLimitPolicy.scope_type == "user",
                RateLimitPolicy.user_id == user_id,
            ),
            and_(
                RateLimitPolicy.scope_type == "server",
                RateLimitPolicy.server_id == server_id,
            ),
        ]
        if api_key_id is not None:
            conditions.append(and_(
                RateLimitPolicy.scope_type == "api_key",
                RateLimitPolicy.api_key_id == api_key_id,
            ))

        # Match tool policies only when the requested tool exists.
        if tool_id is not None:
            conditions.append(
                and_(
                    RateLimitPolicy.scope_type == "tool",
                    RateLimitPolicy.tool_id == tool_id,
                )
            )

        policies = db.scalars(
            select(RateLimitPolicy).where(
                RateLimitPolicy.enabled.is_(True),
                or_(*conditions),
            )
        ).all()

        checks = [
            (
                (
                    str(policy.id),
                    policy.scope_type,
                    bucket_for(policy, identity, public_name),
                ),
                policy.max_requests,
                policy.window_seconds,
            )
            for policy in policies
        ]

    if not checks:
        return True, 0

    return limiter.acquire(checks)
