# -*- coding: utf-8 -*-
"""User-management page renderers."""

from html import escape

from app_state import get_authed_user, is_admin
from auth import hash_password
from database import add_app_user, delete_app_user, list_app_users, set_user_password
from ui_components import (
    render_action_button,
    render_checkbox,
    render_caption,
    render_control_row,
    render_divider,
    render_error,
    render_form,
    render_form_submit_button,
    render_info,
    render_markdown_body,
    render_page_title,
    rerun_app,
    render_section_heading,
    render_success,
    render_text_input,
)


def render_manage_users_page():
    if not is_admin():
        render_error("Admins only.")
        return

    render_page_title("Manage Users", "Create or remove people who can sign in.")

    render_section_heading("Add a user", level=4)
    with render_form("add_user_form", clear_on_submit=True):
        ac1, ac2 = render_control_row(2)
        with ac1:
            nu_username = render_text_input("Username", placeholder="e.g. alice")
            nu_email = render_text_input("Email", placeholder="alice@example.com")
        with ac2:
            nu_name = render_text_input("Display name", placeholder="Alice Smith")
            nu_password = render_text_input("Temporary password", type="password")
        nu_is_admin = render_checkbox("Make this user an admin", value=False)
        add_submitted = render_form_submit_button("Add user")

        if add_submitted:
            if not nu_username.strip() or not nu_password:
                render_error("Username and password are required.")
            else:
                ok, msg = add_app_user(
                    nu_username,
                    nu_email,
                    nu_name.strip() or nu_username,
                    hash_password(nu_password),
                    is_admin=nu_is_admin,
                )
                if ok:
                    render_success(msg + " Share the username/email + this password with them.")
                else:
                    render_error(msg)

    render_divider()
    render_section_heading("Existing users", level=4)
    users = list_app_users()
    if not users:
        render_info("No users yet.")
    for user in users:
        u_username, u_email, u_name, u_is_admin, u_created = user
        uc1, uc2, uc3 = render_control_row([3, 2, 1])
        with uc1:
            badge = " (admin)" if u_is_admin else ""
            render_markdown_body(f"**{escape(u_username)}**{badge}  \n{escape(u_email or '')}")
        with uc2:
            render_caption(f"{escape(u_name or '')}\nadded {escape(str(u_created or ''))[:10]}")
        with uc3:
            is_self = u_username == get_authed_user()
            if u_is_admin or is_self:
                render_caption("-")
            elif render_action_button("Remove", key=f"del_user_{u_username}"):
                delete_app_user(u_username)
                rerun_app()

    render_divider()
    render_section_heading("Change my password", level=4)
    with render_form("change_pw_form", clear_on_submit=True):
        new_pw = render_text_input("New password", type="password")
        new_pw2 = render_text_input("Confirm new password", type="password")
        pw_submitted = render_form_submit_button("Update my password")
        if pw_submitted:
            if not new_pw or new_pw != new_pw2:
                render_error("Passwords are empty or do not match.")
            else:
                set_user_password(get_authed_user(), hash_password(new_pw))
                render_success("Password updated. Use it next time you sign in.")
