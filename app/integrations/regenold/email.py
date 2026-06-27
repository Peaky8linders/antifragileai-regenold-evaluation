"""Welcome-email delivery for the Lexy sign-up funnel — via SendGrid.

Ported from the antifragile.ai ``server/email.py`` pattern: SendGrid is an
**optional** dependency, imported lazily, and every send fails soft
(logs + returns ``False``) when ``SENDGRID_API_KEY`` is unset or the
package is absent. The funnel never depends on email — the API key is
always shown on the page; the email is a best-effort convenience copy so
the user can find their key later.

Environment variables:
  SENDGRID_API_KEY    — enables delivery (unset → no-op, returns False)
  SENDGRID_FROM_EMAIL — sender address (default: lexy@antifragile-ai.net)
  SENDGRID_FROM_NAME  — sender name (default: Lexy — EU AI Act Assistant)
  REGENOLD_APP_URL    — base URL used in the email CTA (default: "/")
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

# SendGrid is optional — import lazily so the module loads without it.
_sendgrid_available = False
try:  # pragma: no cover - import guard
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Category, HtmlContent, Mail

    _sendgrid_available = True
except ImportError:  # pragma: no cover
    pass


def _get_api_key() -> str | None:
    return os.getenv("SENDGRID_API_KEY")


def _get_from_email() -> str:
    return os.getenv("SENDGRID_FROM_EMAIL", "lexy@antifragile-ai.net")


def _get_from_name() -> str:
    return os.getenv("SENDGRID_FROM_NAME", "Lexy — EU AI Act Assistant")


def _app_url() -> str:
    return os.getenv("REGENOLD_APP_URL", "").strip() or "/"


def is_configured() -> bool:
    """True only when SendGrid is installed AND an API key is present."""
    return _sendgrid_available and bool(_get_api_key())


def _welcome_html(*, api_key: str, name: str) -> str:
    greeting = f"Hi {name}," if name else "Welcome,"
    app_url = _app_url()
    return f"""\
<div style="font-family:system-ui,-apple-system,sans-serif;max-width:560px;margin:0 auto;padding:32px;color:#0f172a;">
  <h2 style="font-size:22px;margin:0 0 8px;">{greeting}</h2>
  <p style="color:#475569;line-height:1.6;margin:0 0 20px;">
    Your Lexy account is ready. Lexy is a free, grounded Q&amp;A assistant for the
    EU AI Act (Regulation (EU) 2024/1689) — ask anything and get answers cited to
    the exact Articles and Annexes.
  </p>
  <p style="color:#475569;line-height:1.6;margin:0 0 8px;font-weight:600;">Your API key</p>
  <div style="font-family:ui-monospace,'JetBrains Mono',monospace;font-size:14px;
              background:#0d1226;color:#00f0ff;padding:14px 16px;border-radius:10px;
              word-break:break-all;margin:0 0 20px;">{api_key}</div>
  <p style="color:#64748b;line-height:1.6;font-size:13px;margin:0 0 24px;">
    Keep this key safe — it identifies your usage. Paste it into the Lexy app, or
    send it as the <code>X-Regenold-Api-Key</code> header when calling the API.
  </p>
  <p style="margin:0 0 24px;">
    <a href="{app_url}" style="display:inline-block;background:#00f0ff;color:#050814;
       text-decoration:none;font-weight:700;padding:12px 22px;border-radius:10px;">
      Open Lexy
    </a>
  </p>
  <p style="color:#94a3b8;font-size:12px;line-height:1.6;margin:0;border-top:1px solid #e2e8f0;padding-top:16px;">
    Lexy provides information, not legal advice. Consult qualified counsel for binding
    compliance decisions.
  </p>
</div>
"""


def send_welcome_email(*, to_email: str, api_key: str, name: str = "") -> bool:
    """Send the welcome email containing the user's API key.

    Returns True on a 2xx SendGrid response, False on any failure /
    unconfigured deploy. Never raises.
    """
    api_sg = _get_api_key()
    if not api_sg or not _sendgrid_available:
        logger.info("lexy.email_skipped sendgrid_not_configured to=%s", to_email)
        return False

    try:
        message = Mail(
            from_email=(_get_from_email(), _get_from_name()),
            to_emails=to_email,
            subject="Your Lexy API key — EU AI Act assistant",
            html_content=HtmlContent(_welcome_html(api_key=api_key, name=name)),
        )
        message.category = [Category("lexy-signup")]
        sg = SendGridAPIClient(api_sg)
        response = sg.send(message)
        ok = response.status_code in (200, 201, 202)
        logger.info("lexy.email_sent to=%s status=%s", to_email, response.status_code)
        return ok
    except Exception as exc:  # noqa: BLE001 — email is best-effort
        logger.warning("lexy.email_failed to=%s err=%s", to_email, exc)
        return False
