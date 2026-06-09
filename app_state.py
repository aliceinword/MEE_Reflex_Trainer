# -*- coding: utf-8 -*-
"""Shared Streamlit session-state helpers for app shell, auth, and navigation."""

import streamlit as st


CURRENT_PAGE_KEY = "current_page"
AUTHED_USER_KEY = "_authed_user"
AUTHED_NAME_KEY = "_authed_name"
IS_ADMIN_KEY = "_is_admin"
ADHD_MODE_KEY = "adhd_mode"

DEFAULT_PAGE = "Dashboard"


def get_state(key, default=None):
    """Read a Streamlit session-state value."""
    return st.session_state.get(key, default)


def set_state(key, value):
    """Set a Streamlit session-state value."""
    st.session_state[key] = value
    return value


def pop_state(key):
    """Remove a Streamlit session-state value if present."""
    return st.session_state.pop(key, None)


def ensure_state(key, default):
    """Ensure a session-state key exists and return its value."""
    if key not in st.session_state:
        st.session_state[key] = default
    return st.session_state[key]


def get_current_page(default=DEFAULT_PAGE):
    """Return the current app page."""
    return get_state(CURRENT_PAGE_KEY, default)


def ensure_current_page(default=DEFAULT_PAGE):
    """Ensure the current-page key exists."""
    return ensure_state(CURRENT_PAGE_KEY, default)


def set_current_page(page):
    """Store the current app page."""
    return set_state(CURRENT_PAGE_KEY, page)


def is_authenticated():
    """Return whether a user is signed in."""
    return bool(get_state(AUTHED_USER_KEY))


def get_authed_user():
    """Return the signed-in username."""
    return get_state(AUTHED_USER_KEY)


def get_authed_display_name():
    """Return the signed-in display name or username."""
    return get_state(AUTHED_NAME_KEY, get_authed_user())


def is_admin():
    """Return whether the signed-in user is an admin."""
    return bool(get_state(IS_ADMIN_KEY))


def set_auth_user(record):
    """Persist authenticated user details from a database record."""
    username = record["username"]
    set_state(AUTHED_USER_KEY, username)
    set_state(AUTHED_NAME_KEY, record.get("name") or username)
    set_state(IS_ADMIN_KEY, record["is_admin"])


def clear_auth_user():
    """Clear signed-in user details."""
    pop_state(AUTHED_USER_KEY)
    pop_state(AUTHED_NAME_KEY)
    pop_state(IS_ADMIN_KEY)


def get_reading_mode(default=False):
    """Return the persisted reading-mode flag."""
    return bool(get_state(ADHD_MODE_KEY, default))


def ensure_reading_mode(default=False):
    """Ensure the persisted reading-mode flag exists."""
    return bool(ensure_state(ADHD_MODE_KEY, default))


def set_reading_mode(enabled):
    """Persist the reading-mode flag."""
    return bool(set_state(ADHD_MODE_KEY, bool(enabled)))
