# -*- coding: utf-8 -*-
"""Authentication helpers for the Streamlit app."""

import os

import streamlit as st

from database import get_app_user, list_app_users, upsert_admin


def hash_password(plain):
    import bcrypt
    return bcrypt.hashpw(str(plain).encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def check_password(plain, hashed):
    try:
        import bcrypt
        return bcrypt.checkpw(str(plain).encode("utf-8"), str(hashed).encode("utf-8"))
    except Exception:
        return False


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

    if st.session_state.get("_authed_user"):
        return

    st.markdown(
        "<div style='max-width:400px;margin:8vh auto 0'>"
        "<h2 style='text-align:center;color:#1D4E89'>MEE Reflex Trainer</h2>"
        "<p style='text-align:center;color:#5A7A9A;font-size:0.9rem'>Please sign in to continue.</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    _, col_m, _ = st.columns([1, 2, 1])
    with col_m:
        with st.form("login_form"):
            login_id = st.text_input("Email or username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", use_container_width=True)

        if submitted:
            record = get_app_user(login_id)
            if record and check_password(password, record["password_hash"]):
                st.session_state["_authed_user"] = record["username"]
                st.session_state["_authed_name"] = record.get("name") or record["username"]
                st.session_state["_is_admin"] = record["is_admin"]
                st.rerun()
            else:
                st.error("Incorrect email/username or password.")

    st.stop()
