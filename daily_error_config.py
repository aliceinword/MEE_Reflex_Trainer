# -*- coding: utf-8 -*-
"""Environment- and secrets-driven configuration for the Daily Error Sheet."""

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


def _secret_value(*path, default=""):
    """Read a nested value from st.secrets when Streamlit is available."""
    try:
        import streamlit as st

        node = st.secrets
        for key in path:
            node = node[key]
        if node is None:
            return default
        return str(node).strip()
    except Exception:
        return default


def _config_text(env_name, secret_section=None, secret_key=None, default=""):
    env_val = os.environ.get(env_name)
    if env_val is not None and str(env_val).strip():
        return str(env_val).strip()
    if secret_section and secret_key:
        secret_val = _secret_value(secret_section, secret_key)
        if secret_val:
            return secret_val
    return default


def _default_from_address():
    """Prefer explicit config, then admin account email, then a local placeholder."""
    explicit = _config_text("EMAIL_FROM_ADDRESS", "email", "from_address")
    if explicit:
        return explicit
    admin_email = _secret_value("auth", "admin", "email")
    if admin_email:
        return admin_email
    return "noreply@localhost"


def get_daily_error_config():
    """Return Daily Error Sheet configuration from env vars and Streamlit secrets."""
    smtp_host = _config_text("SMTP_HOST", "email", "smtp_host")
    smtp_user = _config_text("SMTP_USER", "email", "smtp_user")
    smtp_password = os.environ.get("SMTP_PASSWORD") or _secret_value("email", "smtp_password")
    from_address = _default_from_address()

    email_dry_run = _env_bool("EMAIL_DRY_RUN", False)
    if _secret_value("email", "dry_run").lower() in {"1", "true", "yes", "on"}:
        email_dry_run = True
    # Local/dev: log instead of failing when SMTP is not configured.
    if not smtp_host and not email_dry_run:
        email_dry_run = True

    secret_port = _secret_value("email", "smtp_port")
    default_port = int(secret_port) if secret_port.isdigit() else 587

    return {
        "enabled": _env_bool("DAILY_ERROR_SHEET_ENABLED", True),
        "send_hour": _env_int("DAILY_ERROR_SHEET_SEND_HOUR", 21),
        "timezone": _config_text(
            "DAILY_ERROR_SHEET_TIMEZONE",
            "email",
            "timezone",
            "America/New_York",
        ),
        "from_address": from_address,
        "app_base_url": _config_text(
            "APP_BASE_URL",
            "email",
            "app_base_url",
            "http://localhost:8501",
        ).rstrip("/"),
        "smtp_host": smtp_host,
        "smtp_port": _env_int("SMTP_PORT", default_port),
        "smtp_user": smtp_user,
        "smtp_password": smtp_password or "",
        "smtp_use_tls": _env_bool("SMTP_USE_TLS", True),
        "email_dry_run": email_dry_run,
    }


def describe_email_delivery_mode():
    """Human-readable summary of how outbound email is configured."""
    config = get_daily_error_config()
    if config["email_dry_run"]:
        return (
            f"Dry-run mode (no SMTP delivery). Messages are accepted using sender "
            f"{config['from_address']!r}. Set SMTP_HOST or EMAIL_DRY_RUN=0 for live sends."
        )
    if not config["smtp_host"]:
        return "SMTP is not configured. Add SMTP_HOST or enable EMAIL_DRY_RUN=1."
    return f"Live SMTP via {config['smtp_host']} from {config['from_address']!r}."
