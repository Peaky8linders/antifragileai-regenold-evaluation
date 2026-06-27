from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.config import settings
from app.integrations.regenold.user_store import is_registered_user_key

_regenold_header = APIKeyHeader(name="X-Regenold-Api-Key", auto_error=False)


def _configured_key() -> str | None:
    if not settings.regenold.api_key:
        return None
    return settings.regenold.api_key.get_secret_value()


def is_known_regenold_key(api_key: str | None) -> bool:
    """True for the configured partner key OR any key minted by the Lexy
    sign-up funnel (see :mod:`app.integrations.regenold.user_store`).

    Used by the anonymous-friendly Q&A route's optional-auth dep + the
    rate-limit key func so a freshly-issued ``lexy_sk_...`` key is honoured
    (and gets the privileged tier) instead of being 403'd / downgraded.
    Kept SEPARATE from :func:`validate_regenold_api_key` so the strict
    partner-only :func:`require_regenold_api_key` is unaffected.
    """
    if not api_key:
        return False
    if validate_regenold_api_key(api_key):
        return True
    return is_registered_user_key(api_key)


def validate_regenold_api_key(api_key: str) -> bool:
    configured = _configured_key()
    if not configured:
        return False
    # R112 — never let a malformed header crash the route.
    # ``secrets.compare_digest`` raises TypeError on non-ASCII str input;
    # HTTP header bytes are latin-1-decoded by Starlette, so a raw
    # 0x80-0xFF octet in X-Regenold-Api-Key arrives here as a non-ASCII
    # str and previously 500'd every request on a configured deploy.
    # Compare as UTF-8 bytes (timing-safe for bytes of any content) and
    # fail closed on any residual encode/compare error — the dependency
    # then raises the documented 403 instead of an unhandled 500.
    try:
        return secrets.compare_digest(
            api_key.encode("utf-8"), configured.encode("utf-8")
        )
    except Exception:  # noqa: BLE001 — fail-closed, never 500 the route
        return False


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

    Lexy funnel (R-signup): a header matching the configured partner key
    OR any key minted by the sign-up funnel is accepted (privileged tier).
    """
    if not api_key:
        return None
    if is_known_regenold_key(api_key):
        # Partner key OR a funnel-issued user key → privileged tier.
        return api_key
    if not _configured_key():
        # No configured partner key on this deployment AND the header is
        # not a known user key — treat any stray header as anonymous
        # instead of 403 (back-compat: provisioning shouldn't hard-fail
        # an otherwise-anonymous deploy).
        return None
    # A partner key IS configured but the header matches neither it nor
    # any user key: typo / stale key / wrong tenant. Fail loudly so the
    # caller notices instead of being silently downgraded.
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "code": "regenold_api_key_invalid",
            "message": "Invalid API key.",
        },
    )


RequireRegenold = Depends(require_regenold_api_key)
OptionalRegenold = Depends(optional_regenold_api_key)
