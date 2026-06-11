# -*- coding: utf-8 -*-
"""Orchestrate Daily Error Sheet generation and delivery."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

from daily_error_config import get_daily_error_config
from database import (
    get_app_user,
    get_daily_error_sheet_sent,
    list_users_for_daily_error_sheet,
    record_daily_error_sheet_sent,
)
from email_service import send_email
from missed_answer_service import (
    build_daily_error_report,
    render_daily_error_report_html,
    render_daily_error_report_text,
)

logger = logging.getLogger(__name__)


def resolve_recipient_email(username: str, override_email: Optional[str] = None) -> Optional[str]:
    if override_email:
        return override_email.strip()
    user = get_app_user(username)
    if user and user.get("email"):
        return user["email"].strip()
    return None


def send_daily_error_sheet_for_user(
    username: str,
    report_date: str,
    *,
    recipient_email: Optional[str] = None,
    force: bool = False,
    send_if_empty: bool = False,
) -> Dict:
    """Generate and send one user's daily error sheet. Idempotent per user/date."""
    username = (username or "").strip().lower()
    if not username or not report_date:
        return {"ok": False, "status": "invalid_input", "username": username, "report_date": report_date}

    if not force and get_daily_error_sheet_sent(username, report_date):
        return {
            "ok": True,
            "status": "already_sent",
            "username": username,
            "report_date": report_date,
        }

    report = build_daily_error_report(username, report_date)
    email = resolve_recipient_email(username, recipient_email)
    if not email:
        record_daily_error_sheet_sent(
            username,
            report_date,
            status="failed",
            error_message="No recipient email configured",
        )
        return {
            "ok": False,
            "status": "failed",
            "username": username,
            "report_date": report_date,
            "error": "No recipient email configured",
        }

    if report.total_missed == 0 and not send_if_empty:
        record_daily_error_sheet_sent(
            username,
            report_date,
            status="skipped_no_misses",
            recipient_email=email,
        )
        return {
            "ok": True,
            "status": "skipped_no_misses",
            "username": username,
            "report_date": report_date,
        }

    config = get_daily_error_config()
    subject = f"Daily Error Sheet — {report_date}"
    text_body = render_daily_error_report_text(report)
    html_body = render_daily_error_report_html(report)
    result = send_email(
        to_address=email,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
        from_address=config["from_address"] or None,
    )

    if result.ok:
        record_daily_error_sheet_sent(
            username,
            report_date,
            status="sent",
            recipient_email=email,
            provider_message_id=result.message_id,
        )
        return {
            "ok": True,
            "status": "sent",
            "username": username,
            "report_date": report_date,
            "dry_run": result.dry_run,
            "message_id": result.message_id,
        }

    record_daily_error_sheet_sent(
        username,
        report_date,
        status="failed",
        recipient_email=email,
        error_message=result.error,
    )
    return {
        "ok": False,
        "status": "failed",
        "username": username,
        "report_date": report_date,
        "error": result.error,
    }


def _local_now(timezone_name: str) -> datetime:
    try:
        tz = ZoneInfo(timezone_name)
    except Exception:
        tz = ZoneInfo("America/New_York")
    return datetime.now(tz)


def run_daily_error_sheet_job(
    *,
    as_of: Optional[datetime] = None,
    force: bool = False,
) -> List[Dict]:
    """Send daily error sheets for users whose local send hour has passed."""
    config = get_daily_error_config()
    if not config["enabled"]:
        logger.info("Daily Error Sheet job disabled via DAILY_ERROR_SHEET_ENABLED")
        return []

    results = []
    for user in list_users_for_daily_error_sheet():
        timezone_name = user.get("timezone") or config["timezone"]
        send_hour = int(user.get("send_hour", config["send_hour"]))
        local_now = as_of.astimezone(ZoneInfo(timezone_name)) if as_of and as_of.tzinfo else _local_now(timezone_name)
        report_date = local_now.strftime("%Y-%m-%d")

        if not force and local_now.hour < send_hour:
            results.append(
                {
                    "ok": True,
                    "status": "skipped_before_send_hour",
                    "username": user["username"],
                    "report_date": report_date,
                }
            )
            continue

        try:
            result = send_daily_error_sheet_for_user(
                user["username"],
                report_date,
                recipient_email=user.get("email"),
                force=force,
                send_if_empty=bool(user.get("send_no_misses_email")),
            )
            results.append(result)
        except Exception:
            logger.exception("Daily error sheet failed for user=%s", user["username"])
            results.append(
                {
                    "ok": False,
                    "status": "failed",
                    "username": user["username"],
                    "report_date": report_date,
                    "error": "Unhandled exception",
                }
            )

    return results
