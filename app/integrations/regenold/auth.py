from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.config import settings

_regenold_header = APIKeyHeader(name="X-Regenold-Api-Key", auto_error=False)


def _configured_key() -> str | None:
    if not settings.regenold.api_key:
        return None
    return settings.regenold.api_key.get_secret_value()


def validate_regenold_api_key(api_key: str) -> bool:
    configured = _configured_key()
    if not configured:
        return False
    return secrets.compare_digest(api_key, configured)


async def require_regenold_api_key(
    api_key: Annotated[str | None, Security(_regenold_header)] = None,
) -> str:
    """Strict-auth dep — kept for back-compat / future privileged routes.

    Not used by the public Regenold Q&A route any more (the competition
    feature is anonymous-friendly via :func:`optional_regenold_api_key`).
    Kept available so a future internal-only route can opt in to the
    fail-closed posture without re-implementing the validator.
    """
    if not _configured_key():
        # Staged-but-inactive posture (same pattern as OAuth): ship code
        # before provisioning the partner key in Railway.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "regenold_not_configured",
                "message": "Regenold integration is not configured on this deployment.",
            },
        )
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "regenold_api_key_missing",
                "message": "Missing API key. Provide it via X-Regenold-Api-Key.",
            },
        )
    if not validate_regenold_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "regenold_api_key_invalid",
                "message": "Invalid API key.",
            },
        )
    return api_key


async def optional_regenold_api_key(
    api_key: Annotated[str | None, Security(_regenold_header)] = None,
) -> str | None:
    """Optional-auth dep — returns the validated key or None.

    Powers the anonymous-friendly Regenold partner endpoint
    (``POST /regenold/eu-ai-act/ask``) — this is a competition
    deliverable, so the route must be reachable WITHOUT a partner key.

    Contract:
    - No header (key absent) → return ``None`` (anonymous tier).
    - Header present + matches configured key → return the key (privileged tier).
    - Header present but does NOT match → raise 403 (typo'd keys still fail loudly).
    - Deployment has no configured key (``_configured_key() is None``):
      header is ignored AND no 503 is raised — anonymous traffic flows
      regardless of partner-key provisioning. The route layer determines
      the tier from this dep's return value.

    The route layer combines this with two stacked rate-limit buckets
    (60/min for the privileged tier, 30/min per IP for anonymous) and
    distinct evidence-chain ``tenant_id`` stamps so an auditor can
    distinguish partner traffic from public traffic in the chain.
    """
    if not api_key:
        return None
    if not _configured_key():
        # No configured key on this deployment — treat any header as
        # anonymous instead of 403. Sending a stray header should not
        # be a hard failure on a deploy that hasn't been provisioned.
        return None
    if not validate_regenold_api_key(api_key):
        # Header present + non-matching: typo / stale key / wrong tenant.
        # Fail loudly so the partner notices instead of silently being
        # downgraded to the anonymous tier.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "regenold_api_key_invalid",
                "message": "Invalid API key.",
            },
        )
    return api_key


RequireRegenold = Depends(require_regenold_api_key)
OptionalRegenold = Depends(optional_regenold_api_key)
