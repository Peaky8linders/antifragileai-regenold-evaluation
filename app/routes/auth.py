"""Lexy sign-up funnel — account + API-key issuance routes.

Mounted under ``/api/v1`` alongside the Regenold Q&A route, so the wire
paths are:

* ``POST /api/v1/regenold/auth/signup`` — create an account (idempotent on
  email) and return a fresh ``lexy_sk_...`` API key.
* ``POST /api/v1/regenold/auth/signin`` — look up an existing account by
  email and return its API key.
* ``GET  /api/v1/regenold/auth/me`` — return the account behind an
  ``X-Regenold-Api-Key`` header (lets the app greet a signed-in user).

The issued key authenticates the Q&A route (``optional_regenold_api_key``
accepts it; see :mod:`app.integrations.regenold.auth`). This is a free
lead-gen funnel — the email is the identifier and the key is the usage
credential; there is no password by design (mirrors the antifragile.ai
email-capture pattern). A best-effort welcome email is sent when SendGrid
is configured; the key is always returned in the response regardless.
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

from app.integrations.regenold import email as lexy_email
from app.integrations.regenold.user_store import (
    UserRecord,
    get_user_store,
    is_valid_email,
    normalise_email,
)
from app.rate_limit import limiter

logger = logging.getLogger(__name__)

auth_router = APIRouter(tags=["regenold-auth"])

_api_key_header = APIKeyHeader(name="X-Regenold-Api-Key", auto_error=False)


# ── Wire models ───────────────────────────────────────────────────────────────


class SignupRequest(BaseModel):
    email: str = Field(..., description="Account email (the identifier).")
    name: str = Field("", description="Optional display name.")
    company: str = Field("", description="Optional company / organisation.")


class SigninRequest(BaseModel):
    email: str = Field(..., description="Account email to look up.")


class AccountResponse(BaseModel):
    api_key: str
    email: str
    name: str = ""
    company: str = ""
    created_at: str = ""
    returning: bool = Field(
        False,
        description="True when the email already had an account (key reused).",
    )
    email_sent: bool = Field(
        False, description="True when a welcome email was delivered."
    )


class MeResponse(BaseModel):
    email: str
    name: str = ""
    company: str = ""
    created_at: str = ""


def _account_response(rec: UserRecord, *, returning: bool, email_sent: bool) -> AccountResponse:
    return AccountResponse(
        api_key=rec.api_key,
        email=rec.email,
        name=rec.name,
        company=rec.company,
        created_at=rec.created_at,
        returning=returning,
        email_sent=email_sent,
    )


# ── Routes ────────────────────────────────────────────────────────────────────


@auth_router.post(
    "/regenold/auth/signup",
    response_model=AccountResponse,
    responses={400: {"description": "Invalid email"}},
)
@limiter.limit("10/minute")
def signup(request: Request, body: SignupRequest) -> AccountResponse:
    """Create a Lexy account and mint a fresh API key (idempotent on email)."""
    if not is_valid_email(body.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_email", "message": "A valid email is required."},
        )
    store = get_user_store()
    rec, created = store.create_or_get(body.email, name=body.name, company=body.company)

    email_sent = False
    if created:
        # Best-effort — never block / fail the response on email delivery.
        try:
            email_sent = lexy_email.send_welcome_email(
                to_email=rec.email, api_key=rec.api_key, name=rec.name
            )
        except Exception as exc:  # noqa: BLE001 — email is non-critical
            logger.warning("lexy.signup email send raised: %s", exc)

    logger.info(
        "lexy.signup email=%s created=%s email_sent=%s", rec.email, created, email_sent
    )
    return _account_response(rec, returning=not created, email_sent=email_sent)


@auth_router.post(
    "/regenold/auth/signin",
    response_model=AccountResponse,
    responses={404: {"description": "No account for this email"}},
)
@limiter.limit("20/minute")
def signin(request: Request, body: SigninRequest) -> AccountResponse:
    """Return the API key for an existing account (looked up by email)."""
    if not is_valid_email(body.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_email", "message": "A valid email is required."},
        )
    store = get_user_store()
    rec = store.get_by_email(body.email)
    if rec is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "account_not_found",
                "message": "No Lexy account for this email. Sign up to get a key.",
            },
        )
    # Optional convenience copy of the key by email (best-effort, no-op
    # without Resend). The key is always returned in the response too.
    email_sent = False
    try:
        if lexy_email.is_configured():
            email_sent = lexy_email.send_welcome_email(
                to_email=rec.email, api_key=rec.api_key, name=rec.name
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("lexy.signin email send raised: %s", exc)

    logger.info("lexy.signin email=%s email_sent=%s", rec.email, email_sent)
    return _account_response(rec, returning=True, email_sent=email_sent)


@auth_router.get(
    "/regenold/auth/me",
    response_model=MeResponse,
    responses={
        401: {"description": "Missing X-Regenold-Api-Key header"},
        403: {"description": "Unknown API key"},
    },
)
@limiter.limit("60/minute")
def me(
    request: Request,
    api_key: Annotated[str | None, Security(_api_key_header)] = None,
) -> MeResponse:
    """Return the account behind a Lexy API key header."""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "api_key_missing", "message": "Provide X-Regenold-Api-Key."},
        )
    rec = get_user_store().get_by_api_key(api_key.strip())
    if rec is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "api_key_unknown", "message": "Unknown API key."},
        )
    return MeResponse(
        email=rec.email,
        name=rec.name,
        company=rec.company,
        created_at=rec.created_at,
    )


__all__ = ["auth_router", "normalise_email"]
