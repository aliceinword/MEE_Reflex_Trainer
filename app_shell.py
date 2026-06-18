# -*- coding: utf-8 -*-
"""Application shell setup: navigation, sidebar session controls, and reading settings."""

from html import escape

from app_state import (
    clear_auth_user,
    ensure_current_page,
    ensure_reading_mode,
    get_authed_display_name,
    get_authed_user,
    get_current_page,
    is_admin,
    is_authenticated,
    set_reading_mode,
)
from auth import clear_remembered_login
from styles import render_control_text_styles, render_global_styles, render_reading_styles
from ui_components import (
    render_app_header,
    render_reading_mode_notice,
    render_sidebar_action_button,
    render_sidebar_checkbox,
    render_sidebar_html,
    render_sidebar_logo,
    render_sidebar_markdown,
    render_sidebar_navigation,
    render_sidebar_slider,
    rerun_app,
)

NAV_GROUPS = [
    ("MEE Practice", ["Home", "MEE Question Bank", "Attack Outline Rules", "MEE Muscle Ladder"]),
    ("MBE Practice", ["MBE Drills", "Bridge Drill", "Rule Recall", "Flashcards Drill", "MBE Drills Question Bulk Upload"]),
    ("MEE Advanced Tools", ["Import Questions", "Manual Entry"]),
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
    "Question Bank": "MEE Question Bank",
    "Attack Outline Rules": "Attack Outline Rules",
    "Plug & Play Templates": "MEE Question Bank",
    "Review Attempts": "Settings",
    "MEE Advanced Tools": "Import Questions",
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
    "MBE Flashcards": "Flashcards Drill",
    "Flashcards": "Flashcards Drill",
    "Flashcard Drill": "Flashcards Drill",
    "MBE Bulk Upload": "MBE Drills Question Bulk Upload",
    "MBE Question Bulk Upload": "MBE Drills Question Bulk Upload",
}

ADVANCED_TOOL_PAGES = {
    "Bulk Import MEE Bank",
    "Add MEE Question",
    "Import Questions",
    "Manual Entry",
}

FULL_WIDTH_TEXT_MAX = 9999


def _render_session_controls():
    if not is_authenticated():
        return

    render_sidebar_html(
        f"<div style='font-size:0.8rem;color:#4A6585;margin-top:0.6rem'>Signed in as "
        f"<b>{escape(str(get_authed_display_name()))}</b></div>"
    )
    if render_sidebar_action_button("Sign out", key="logout_btn"):
        clear_remembered_login(get_authed_user())
        clear_auth_user()
        rerun_app()


def _render_reading_controls():
    render_sidebar_markdown("### Reading Comfort")
    persisted_reading_mode = ensure_reading_mode(False)

    reading_mode = render_sidebar_checkbox(
        "Reading mode (larger text)",
        value=persisted_reading_mode,
        key="adhd_checkbox",
    )
    set_reading_mode(reading_mode)

    if reading_mode:
        font_size = 20
        line_height = 2.05
        max_width = 820
        box_padding = "1.6rem 1.8rem"
        compact_mode = False
    else:
        font_size = render_sidebar_slider("Legal text size", 15, 24, 18)
        line_height = 1.55
        max_width = FULL_WIDTH_TEXT_MAX
        box_padding = "0.9rem 1rem"
        compact_mode = render_sidebar_checkbox("Compact mode", value=False)

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

    if get_current_page("Daily Workout") != "MBE Drills":
        render_app_header()

    nav_groups = NAV_GROUPS
    if is_admin():
        nav_groups = nav_groups + [("ADMIN", ["Manage Users"])]

    ensure_current_page()

    render_sidebar_logo()
    menu = render_sidebar_navigation(nav_groups, MENU_ALIASES, ADVANCED_TOOL_PAGES)
    _render_session_controls()
    reading_settings = _render_reading_controls()

    return menu, reading_settings
