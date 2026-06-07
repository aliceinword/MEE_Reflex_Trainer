# -*- coding: utf-8 -*-
"""User-management page renderers."""

from html import escape

import streamlit as st

from auth import hash_password
from database import add_app_user, delete_app_user, list_app_users, set_user_password
from ui_components import render_page_title


def render_manage_users_page():
    if not st.session_state.get("_is_admin"):
        st.error("Admins only.")
        return

    render_page_title("Manage Users", "Create or remove people who can sign in.")

    st.markdown("#### Add a user")
    with st.form("add_user_form", clear_on_submit=True):
        ac1, ac2 = st.columns(2)
        with ac1:
            nu_username = st.text_input("Username", placeholder="e.g. alice")
            nu_email = st.text_input("Email", placeholder="alice@example.com")
        with ac2:
            nu_name = st.text_input("Display name", placeholder="Alice Smith")
            nu_password = st.text_input("Temporary password", type="password")
        nu_is_admin = st.checkbox("Make this user an admin", value=False)
        add_submitted = st.form_submit_button("Add user")

        if add_submitted:
            if not nu_username.strip() or not nu_password:
                st.error("Username and password are required.")
            else:
                ok, msg = add_app_user(
                    nu_username,
                    nu_email,
                    nu_name.strip() or nu_username,
                    hash_password(nu_password),
                    is_admin=nu_is_admin,
                )
                if ok:
                    st.success(msg + " Share the username/email + this password with them.")
                else:
                    st.error(msg)

    st.divider()
    st.markdown("#### Existing users")
    users = list_app_users()
    if not users:
        st.info("No users yet.")
    for user in users:
        u_username, u_email, u_name, u_is_admin, u_created = user
        uc1, uc2, uc3 = st.columns([3, 2, 1])
        with uc1:
            badge = " (admin)" if u_is_admin else ""
            st.markdown(f"**{escape(u_username)}**{badge}  \n{escape(u_email or '')}")
        with uc2:
            st.caption(f"{escape(u_name or '')}\nadded {escape(str(u_created or ''))[:10]}")
        with uc3:
            is_self = u_username == st.session_state.get("_authed_user")
            if u_is_admin or is_self:
                st.caption("-")
            elif st.button("Remove", key=f"del_user_{u_username}"):
                delete_app_user(u_username)
                st.rerun()

    st.divider()
    st.markdown("#### Change my password")
    with st.form("change_pw_form", clear_on_submit=True):
        new_pw = st.text_input("New password", type="password")
        new_pw2 = st.text_input("Confirm new password", type="password")
        pw_submitted = st.form_submit_button("Update my password")
        if pw_submitted:
            if not new_pw or new_pw != new_pw2:
                st.error("Passwords are empty or do not match.")
            else:
                set_user_password(st.session_state["_authed_user"], hash_password(new_pw))
                st.success("Password updated. Use it next time you sign in.")
