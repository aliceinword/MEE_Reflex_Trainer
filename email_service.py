# -*- coding: utf-8 -*-
"""Email delivery abstraction for Daily Error Sheet and future notifications."""

from __future__ import annotations

import logging
import smtplib
import uuid
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from daily_error_config import get_daily_error_config

logger = logging.getLogger(__name__)


@dataclass
class EmailSendResult:
    ok: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    dry_run: bool = False


def send_email(*, to_address, subject, text_body, html_body=None, from_address=None):
    """Send a multipart email via SMTP or dry-run mode."""
    config = get_daily_error_config()
    sender = from_address or config["from_address"]
    if not to_address:
        return EmailSendResult(ok=False, error="Missing recipient address")
    if not sender:
        return EmailSendResult(ok=False, error="Missing EMAIL_FROM_ADDRESS")

    message_id = f"local-{uuid.uuid4().hex}"

    if config["email_dry_run"]:
        logger.info("EMAIL_DRY_RUN: would send to %s subject=%r", to_address, subject)
        return EmailSendResult(ok=True, message_id=message_id, dry_run=True)

    if not config["smtp_host"]:
        return EmailSendResult(ok=False, error="Missing SMTP_HOST")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to_address
    msg.attach(MIMEText(text_body or "", "plain", "utf-8"))
    if html_body:
        msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(config["smtp_host"], config["smtp_port"], timeout=30) as smtp:
            if config["smtp_use_tls"]:
                smtp.starttls()
            if config["smtp_user"]:
                smtp.login(config["smtp_user"], config["smtp_password"])
            smtp.sendmail(sender, [to_address], msg.as_string())
        return EmailSendResult(ok=True, message_id=message_id)
    except Exception as exc:
        logger.exception("Email send failed")
        return EmailSendResult(ok=False, error=str(exc))
