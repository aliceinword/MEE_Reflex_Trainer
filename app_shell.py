# -*- coding: utf-8 -*-
"""Application shell setup: navigation, sidebar session controls, and reading settings."""

from html import escape

import streamlit as st

from styles import render_control_text_styles, render_global_styles, render_reading_styles
from ui_components import (
    render_app_header,
    render_reading_mode_notice,
    render_sidebar_logo,
    render_sidebar_navigation,
)

NAV_GROUPS = [
    ("MEE Practice", ["Home", "Question Bank", "MEE Muscle Ladder"]),
    ("MBE Practice", ["MBE Drills"]),
    ("Advanced Tools", ["Import Questions", "Manual Entry"]),
    ("App", ["Settings"]),
]

MENU_ALIASES = {
    "Daily Workout": "Dashboard",
    "Home": "Dashboard",
    "Practice Mode": "MEE Muscle Ladder",
    "Muscle Ladder": "MEE Muscle Ladder",
    "Mini Essay Drill": "MEE Muscle Ladder",
    "Issue Spotting Drill": "MEE Muscle Ladder",
    "Rule Flashcards": "MEE Muscle Ladder",
    "Rule Learning Portal": "MEE Muscle Ladder",
    "Rule Flash Drill": "MEE Muscle Ladder",
    "Rule Retrieval Drill": "MEE Muscle Ladder",
    "Timed IRAC Drill": "MEE Muscle Ladder",
    "Due Review Queue": "MEE Muscle Ladder",
    "Attack Outline Rules": "Question Bank",
    "Plug & Play Templates": "Question Bank",
    "Review Attempts": "Settings",
    "Advanced Tools": "Import Questions",
    "Bulk Import MEE Bank": "Import Questions",
    "Add MEE Question": "Manual Entry",
    "CSV Import": "Import Questions",
    "DOCX Import": "Import Questions",
    "PDF Import": "Import Questions",
    "Text / Markdown Import": "Import Questions",
    "MBE": "MBE Drills",
    "MBE Practice": "MBE Drills",
    "Trap Trainer": "MBE Drills",
}

ADVANCED_TOOL_PAGES = {
    "Bulk Import MEE Bank",
    "Add MEE Question",
    "Import Questions",
    "Manual Entry",
}

FULL_WIDTH_TEXT_MAX = 9999


def _render_session_controls():
    if not st.session_state.get("_authed_user"):
        return

    st.sidebar.markdown(
        f"<div style='font-size:0.8rem;color:#4A6585;margin-top:0.6rem'>Signed in as "
        f"<b>{escape(str(st.session_state.get('_authed_name', st.session_state['_authed_user'])))}</b></div>",
        unsafe_allow_html=True,
    )
    if st.sidebar.button("Sign out", key="logout_btn", use_container_width=True):
        st.session_state.pop("_authed_user", None)
        st.session_state.pop("_authed_name", None)
        st.rerun()


def _render_reading_controls():
    st.sidebar.markdown("### Reading Comfort")
    if "adhd_mode" not in st.session_state:
        st.session_state["adhd_mode"] = False

    reading_mode = st.sidebar.checkbox(
        "Reading mode (larger text)",
        value=st.session_state["adhd_mode"],
        key="adhd_checkbox",
    )
    st.session_state["adhd_mode"] = reading_mode

    if reading_mode:
        font_size = 20
        line_height = 2.05
        max_width = 820
        box_padding = "1.6rem 1.8rem"
        compact_mode = False
    else:
        font_size = st.sidebar.slider("Legal text size", 15, 24, 18)
        line_height = 1.55
        max_width = FULL_WIDTH_TEXT_MAX
        box_padding = "0.9rem 1rem"
        compact_mode = st.sidebar.checkbox("Compact mode", value=False)

    if compact_mode and not reading_mode:
        font_size = 16
        line_height = 1.5
        box_padding = "0.85rem 1rem"

    render_reading_styles(font_size, line_height, max_width, box_padding)
    render_control_text_styles()

    if reading_mode:
        render_reading_mode_notice()

    return {
        "reading_mode": reading_mode,
        "compact_mode": compact_mode,
        "font_size": font_size,
        "line_height": line_height,
        "max_width": max_width,
        "box_padding": box_padding,
    }


def render_app_shell():
    render_global_styles()

    if st.session_state.get("current_page", "Daily Workout") != "MBE Drills":
        render_app_header()

    nav_groups = NAV_GROUPS
    if st.session_state.get("_is_admin"):
        nav_groups = nav_groups + [("ADMIN", ["Manage Users"])]

    if "current_page" not in st.session_state:
        st.session_state["current_page"] = "Dashboard"

    render_sidebar_logo()
    menu = render_sidebar_navigation(nav_groups, MENU_ALIASES, ADVANCED_TOOL_PAGES)
    _render_session_controls()
    reading_settings = _render_reading_controls()

    return menu, reading_settings
