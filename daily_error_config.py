# -*- coding: utf-8 -*-
"""Environment-driven configuration for the Daily Error Sheet feature."""

import os


def _env_bool(name, default=False):
    raw = os.environ.get(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name, default):
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def get_daily_error_config():
    """Return Daily Error Sheet configuration from environment variables."""
    return {
        "enabled": _env_bool("DAILY_ERROR_SHEET_ENABLED", True),
        "send_hour": _env_int("DAILY_ERROR_SHEET_SEND_HOUR", 21),
        "timezone": os.environ.get("DAILY_ERROR_SHEET_TIMEZONE", "America/New_York"),
        "from_address": (os.environ.get("EMAIL_FROM_ADDRESS") or "").strip(),
        "app_base_url": (os.environ.get("APP_BASE_URL") or "http://localhost:8501").rstrip("/"),
        "smtp_host": (os.environ.get("SMTP_HOST") or "").strip(),
        "smtp_port": _env_int("SMTP_PORT", 587),
        "smtp_user": (os.environ.get("SMTP_USER") or "").strip(),
        "smtp_password": os.environ.get("SMTP_PASSWORD") or "",
        "smtp_use_tls": _env_bool("SMTP_USE_TLS", True),
        "email_dry_run": _env_bool("EMAIL_DRY_RUN", False),
    }
