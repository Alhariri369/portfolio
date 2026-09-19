"""Email sending via the Resend SDK."""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def send_contact_email(*, to: str, from_: str, reply_to: str, subject: str, text: str) -> None:
    """Send a plain-text contact email. No-ops (with a log) when no API key is set."""
    api_key = os.getenv("RESEND_API_KEY", "")
    if not api_key:
        logger.warning("RESEND_API_KEY is not set; skipping email send")
        return

    import resend

    resend.api_key = api_key
    params = {
        "from": from_,
        "to": [to],
        "reply_to": reply_to,
        "subject": subject,
        "text": text,
    }
    resend.Emails.send(params)
