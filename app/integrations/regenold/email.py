"""Welcome-email delivery for the Lexy sign-up funnel — via Resend.

Matches the parent legit-ai ``app/email_service.py`` integration: the
official ``resend`` SDK, ``resend.api_key = <RESEND_API_KEY>``,
``resend.Emails.send({...})``, the Antifragile.AI brand chrome (navy /
sky palette, table-based monogram, hidden inbox preheader), and a
console no-op fallback when the key is absent so the funnel never depends
on email.

Resend is an **optional** dependency, imported lazily; every send
fail-soft (logs + returns ``False``) when ``RESEND_API_KEY`` is unset or
the package is missing. The funnel always returns the API key in the HTTP
response — this email is a best-effort convenience copy.

Environment variables (reuse the legit-ai / Railway names):
  RESEND_API_KEY     — enables delivery (unset → no-op, returns False)
  EMAIL_FROM_ADDRESS — sender (default: ``Lexy <noreply@antifragile-ai.net>``)
  REGENOLD_APP_URL / EMAIL_BASE_URL — base URL for the "Open Lexy" CTA
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

# Resend is optional — import lazily so the module loads without it.
_resend_available = False
try:  # pragma: no cover - import guard
    import resend  # type: ignore[import-not-found]

    _resend_available = True
except ImportError:  # pragma: no cover
    pass


# ── Config ────────────────────────────────────────────────────────────────────


def _get_api_key() -> str | None:
    return os.getenv("RESEND_API_KEY") or os.getenv("EMAIL_RESEND_API_KEY")


def _get_from_address() -> str:
    # Default to the verified antifragile-ai.net domain (same as legit-ai),
    # with a "Lexy" display name. Override via EMAIL_FROM_ADDRESS.
    return os.getenv("EMAIL_FROM_ADDRESS", "Lexy <noreply@antifragile-ai.net>")


def _app_url() -> str:
    raw = (
        os.getenv("REGENOLD_APP_URL", "").strip()
        or os.getenv("EMAIL_BASE_URL", "").strip()
        or "https://regenold-eu-ai-act-rag-production.up.railway.app"
    )
    return raw.rstrip("/")


def is_configured() -> bool:
    """True only when the Resend SDK is installed AND an API key is present."""
    return _resend_available and bool(_get_api_key())


# ── Brand chrome (ported from legit-ai app/email_service.py) ──────────────────
# Inline CSS only — most clients strip <style>/<link>. Palette mirrors the
# marketing site: #0f172a navy, #0284c7 sky, #374151 body, #9ca3af footer.
_BUTTON_STYLE = (
    "display:inline-block;padding:13px 28px;background:#0f172a;color:#ffffff;"
    "text-decoration:none;border-radius:8px;font-weight:600;font-size:15px;"
    "letter-spacing:-0.005em;font-family:-apple-system,BlinkMacSystemFont,"
    "'Segoe UI',sans-serif;"
)
_MUTED = "color:#9ca3af;font-size:12px;line-height:1.5;"
_FOOTER = "color:#9ca3af;font-size:11px;line-height:1.6;"
_EYEBROW_STYLE = (
    "font-size:11px;letter-spacing:0.15em;text-transform:uppercase;"
    "color:#6b7280;font-weight:600;margin:0 0 10px 0;"
    "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;"
)
_SECTION_DIVIDER = "border:none;border-top:1px solid #e5e7eb;margin:28px 0;"


def _preheader_html(text: str) -> str:
    """Hidden inbox-preview snippet — must be the first element in the body."""
    padding = "&#847;&zwnj;&nbsp;" * 60
    return (
        '<div style="display:none;max-height:0;overflow:hidden;mso-hide:all;'
        'color:transparent;opacity:0;visibility:hidden;font-size:1px;'
        f'line-height:1px;">{text}{padding}</div>'
    )


def _brand_header_html() -> str:
    """Antifragile.AI monogram + ``ANTIFRAGILE AI · LEXY`` eyebrow (table-based
    so Outlook aligns it). Text monogram, not an image (Gmail blocks data URIs;
    remote images get blocked)."""
    return (
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
        'style="width:100%;border-collapse:collapse;margin:0 0 20px 0;"><tr>'
        '<td style="width:40px;vertical-align:middle;">'
        '<div style="width:36px;height:36px;background:#0f172a;color:#ffffff;'
        'border-radius:9px;text-align:center;line-height:36px;font-weight:800;'
        'font-size:18px;letter-spacing:-0.02em;font-family:-apple-system,'
        "BlinkMacSystemFont,'Segoe UI',sans-serif;\">A</div>"
        "</td>"
        '<td style="vertical-align:middle;padding-left:12px;">'
        f'<p style="{_EYEBROW_STYLE}margin:0;">ANTIFRAGILE AI &middot; LEXY</p>'
        "</td>"
        "</tr></table>"
    )


def _welcome_key_html(*, api_key: str, name: str, app_url: str) -> str:
    """Welcome email body carrying the user's Lexy API key + an Open-Lexy CTA."""
    greeting = f"Hi {name}," if name else "Welcome,"
    preheader = _preheader_html(
        "Your Lexy API key is inside — ask the EU AI Act anything and get "
        "answers cited to the exact Articles and Annexes."
    )
    return (
        f"{preheader}"
        "<div style=\"font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',"
        'Roboto,sans-serif;max-width:560px;margin:0 auto;padding:8px 0;'
        'color:#111111;background:#ffffff;">'
        f"{_brand_header_html()}"
        '<h1 style="margin:0 0 16px 0;font-size:26px;font-weight:800;'
        'color:#0f172a;letter-spacing:-0.025em;line-height:1.2;">'
        "Your Lexy account is ready</h1>"
        f'<p style="margin:0 0 14px 0;font-size:15px;line-height:1.65;color:#374151;">'
        f"{greeting} Lexy is a free, grounded Q&amp;A assistant for the EU AI Act "
        "(Regulation (EU) 2024/1689). Ask anything and get answers cited to the "
        "exact Articles and Annexes."
        "</p>"
        f'<p style="{_EYEBROW_STYLE}">YOUR API KEY</p>'
        '<div style="font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,'
        'monospace;font-size:14px;background:#0f172a;color:#ffffff;padding:14px 16px;'
        f'border-radius:8px;word-break:break-all;margin:0 0 18px 0;">{api_key}</div>'
        f'<p style="margin:0 0 22px 0;{_MUTED}">'
        "Keep this key safe &mdash; it identifies your usage. Paste it into the "
        "Lexy app, or send it as the <code>X-Regenold-Api-Key</code> header when "
        "calling the API."
        "</p>"
        f'<p style="margin:0 0 14px 0;"><a href="{app_url}/" '
        f'style="{_BUTTON_STYLE}">Open Lexy &rarr;</a></p>'
        f'<hr style="{_SECTION_DIVIDER}">'
        f'<p style="{_EYEBROW_STYLE}">NEED HELP?</p>'
        '<p style="margin:0;font-size:14px;color:#374151;line-height:1.6;">'
        'Reply to this email or write to <a href="mailto:support@antifragile-ai.net" '
        'style="color:#0284c7;text-decoration:underline;">support@antifragile-ai.net</a>.'
        "</p>"
        f'<hr style="{_SECTION_DIVIDER}">'
        f'<p style="margin:0;{_FOOTER}">'
        "Lexy provides information about the EU AI Act for general guidance only "
        "and does not constitute legal advice. &mdash; The Antifragile.AI team"
        "</p>"
        "</div>"
    )


# ── Send ──────────────────────────────────────────────────────────────────────


def send_welcome_email(*, to_email: str, api_key: str, name: str = "") -> bool:
    """Send the Lexy welcome email (with the API key) via Resend.

    Returns True on a successful Resend send, False on any failure or
    unconfigured deploy. Never raises (best-effort; the key is always in
    the HTTP response too).
    """
    if not is_configured():
        logger.info("lexy.email_skipped resend_not_configured to=%s", to_email)
        return False

    try:
        resend.api_key = _get_api_key()  # type: ignore[union-attr]
        resend.Emails.send(  # type: ignore[union-attr]
            {
                "from": _get_from_address(),
                "to": to_email,
                "subject": "Your Lexy API key — EU AI Act assistant",
                "html": _welcome_key_html(
                    api_key=api_key, name=name, app_url=_app_url()
                ),
                "tags": [{"name": "category", "value": "lexy_signup"}],
            }
        )
        logger.info("lexy.email_sent to=%s provider=resend", to_email)
        return True
    except Exception as exc:  # noqa: BLE001 — email is best-effort, never raise
        logger.warning("lexy.email_failed to=%s err=%s", to_email, exc)
        return False


# ── Diagnostics (for /healthz/email — never returns the API key) ───────────────


def diagnostics() -> dict[str, object]:
    """Config-only health snapshot for the ``/healthz/email`` probe.

    Booleans + the (non-secret) from-address / app-url only — NEVER the
    ``RESEND_API_KEY``. Lets an operator tell apart "resend package not
    installed" vs "key not set" vs "configured" without a live send.
    """
    return {
        "provider": "resend",
        "resend_available": _resend_available,
        "api_key_present": bool(_get_api_key()),
        "configured": is_configured(),
        "from_address": _get_from_address(),
        "app_url": _app_url(),
    }


def probe_send(to_email: str) -> tuple[bool, str]:
    """Attempt ONE real Resend send for diagnostics; return ``(ok, detail)``.

    ``detail`` is the Resend message id on success, or a truncated
    exception string on failure (e.g. a domain-not-verified / 403 from
    Resend) — no secrets. Surfaces WHY delivery fails to the operator via
    ``/healthz/email?probe=1``. Never raises.
    """
    if not _resend_available:
        return False, "resend package not installed"
    key = _get_api_key()
    if not key:
        return False, "RESEND_API_KEY not set"
    try:
        resend.api_key = key  # type: ignore[union-attr]
        resp = resend.Emails.send(  # type: ignore[union-attr]
            {
                "from": _get_from_address(),
                "to": to_email,
                "subject": "Lexy email health probe",
                "html": "<p>Lexy /healthz/email probe — please ignore.</p>",
                "tags": [{"name": "category", "value": "lexy_health_probe"}],
            }
        )
        if isinstance(resp, dict):
            msg_id = str(resp.get("id") or resp.get("data") or "")
        else:
            msg_id = str(getattr(resp, "id", "") or "")
        return True, (f"sent id={msg_id}" if msg_id else "sent")
    except Exception as exc:  # noqa: BLE001 — diagnostic only, never raise
        return False, f"{type(exc).__name__}: {exc}"[:400]
