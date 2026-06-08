# -*- coding: utf-8 -*-
"""Authentication helpers for the Streamlit app."""

import hashlib
import json
import os
import secrets
from pathlib import Path

import streamlit as st

from app_state import is_authenticated, set_auth_user
from database import (
    clear_user_remember_token,
    get_app_user,
    get_app_user_by_remember_token,
    list_app_users,
    set_user_remember_token,
    upsert_admin,
)
from ui_components import (
    render_control_row,
    render_checkbox,
    render_error,
    render_form,
    render_form_submit_button,
    render_html_body,
    render_text_input,
    rerun_app,
    stop_app,
)


REMEMBER_FILE = Path(__file__).resolve().parent / ".streamlit" / "remember_login.json"


def hash_password(plain):
    import bcrypt
    return bcrypt.hashpw(str(plain).encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def check_password(plain, hashed):
    try:
        import bcrypt
        return bcrypt.checkpw(str(plain).encode("utf-8"), str(hashed).encode("utf-8"))
    except Exception:
        return False


def _hash_remember_token(token):
    return hashlib.sha256(str(token).encode("utf-8")).hexdigest()


def _read_remember_file():
    try:
        return json.loads(REMEMBER_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_remember_file(username, token):
    REMEMBER_FILE.parent.mkdir(parents=True, exist_ok=True)
    REMEMBER_FILE.write_text(
        json.dumps({"username": username, "token": token}, indent=2),
        encoding="utf-8",
    )


def _delete_remember_file():
    try:
        REMEMBER_FILE.unlink()
    except FileNotFoundError:
        pass
    except Exception:
        pass


def clear_remembered_login(username=None):
    """Clear the local remember-me token and its matching database token."""
    remembered = _read_remember_file()
    target_username = username or remembered.get("username")
    if target_username:
        try:
            clear_user_remember_token(target_username)
        except Exception:
            pass

    _delete_remember_file()


def remember_login_for_user(record):
    """Create a new remember-me token for a successfully authenticated user."""
    token = secrets.token_urlsafe(32)
    username = record["username"]
    set_user_remember_token(username, _hash_remember_token(token))
    _write_remember_file(username, token)


def try_remembered_login():
    """Authenticate from the local remember-me token if it is still valid."""
    remembered = _read_remember_file()
    token = remembered.get("token")
    if not token:
        return False

    record = get_app_user_by_remember_token(_hash_remember_token(token))
    if not record:
        _delete_remember_file()
        return False

    set_auth_user(record)
    return True


def seed_admin_from_secrets():
    """Ensure the admin account from st.secrets exists."""
    try:
        adm = st.secrets["auth"]["admin"]
    except Exception:
        return

    try:
        upsert_admin(
            str(adm["username"]).strip().lower(),
            str(adm.get("email", "")).strip().lower(),
            adm.get("name", "Admin"),
            str(adm["password"]),
        )
    except Exception:
        pass


def require_login():
    if os.environ.get("MEE_DISABLE_AUTH") == "1":
        return

    seed_admin_from_secrets()

    # If no accounts exist at all, run open so local use still works.
    if not list_app_users():
        return

    if is_authenticated():
        return

    if try_remembered_login():
        return

    render_html_body(
        "<div style='max-width:400px;margin:8vh auto 0'>"
        "<h2 style='text-align:center;color:#1D4E89'>MEE Reflex Trainer</h2>"
        "<p style='text-align:center;color:#5A7A9A;font-size:0.9rem'>Please sign in to continue.</p>"
        "</div>"
    )

    _, col_m, _ = render_control_row([1, 2, 1])
    with col_m:
        with render_form("login_form"):
            login_id = render_text_input("Email or username")
            password = render_text_input("Password", type="password")
            remember_device = render_checkbox(
                "Remember this device",
                value=True,
                caption="Keeps you signed in here without saving your password.",
            )
            submitted = render_form_submit_button("Sign in")

        if submitted:
            record = get_app_user(login_id)
            if record and check_password(password, record["password_hash"]):
                set_auth_user(record)
                if remember_device:
                    remember_login_for_user(record)
                else:
                    clear_remembered_login(record["username"])
                rerun_app()
            else:
                render_error("Incorrect email/username or password.")

    stop_app()
