"""Disable test policies and ensure the permanent per-user dashboard limit."""

from sqlalchemy import func, select

from db import SessionLocal
from models import RateLimitPolicy, User

POLICY_NAME = "dashboard-per-user"
REQUESTS_PER_MINUTE = 60
WINDOW_SECONDS = 60


def configure_rate_limits() -> tuple[int, int]:
    """Disable test policies and create/update the policy for every active user."""
    disabled_count = 0
    configured_count = 0

    with SessionLocal() as db:
        test_policies = db.scalars(
            select(RateLimitPolicy).where(
                func.lower(RateLimitPolicy.name).contains("test"),
                RateLimitPolicy.enabled.is_(True),
            )
        ).all()
        for policy in test_policies:
            policy.enabled = False
            disabled_count += 1

        active_users = db.scalars(
            select(User).where(User.is_active.is_(True))
        ).all()
        for user in active_users:
            policy = db.scalars(
                select(RateLimitPolicy).where(
                    RateLimitPolicy.name == POLICY_NAME,
                    RateLimitPolicy.scope_type == "user",
                    RateLimitPolicy.user_id == user.id,
                )
            ).first()
            if policy is None:
                db.add(
                    RateLimitPolicy(
                        name=POLICY_NAME,
                        scope_type="user",
                        user_id=user.id,
                        max_requests=REQUESTS_PER_MINUTE,
                        window_seconds=WINDOW_SECONDS,
                        enabled=True,
                    )
                )
            else:
                policy.max_requests = REQUESTS_PER_MINUTE
                policy.window_seconds = WINDOW_SECONDS
                policy.enabled = True
            configured_count += 1

        db.commit()

    return disabled_count, configured_count


if __name__ == "__main__":
    disabled, configured = configure_rate_limits()
    print(f"Disabled {disabled} test rate-limit polic{'y' if disabled == 1 else 'ies'}.")
    print(f"Configured {configured} permanent per-user polic{'y' if configured == 1 else 'ies'}.")
