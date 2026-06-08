# -*- coding: utf-8 -*-
"""Reusable Streamlit UI components for the MEE trainer."""

import os
import random
from contextlib import contextmanager
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from database import get_questions, get_statuses, get_subjects
from text_rendering import (
    escape_display_text,
    get_clean_trigger_facts,
    render_call_text,
    render_question_text,
    render_readable_text,
    render_sample_answer_text,
    render_tested_issues,
    render_trap_warnings,
    render_trigger_facts,
)


PARAGRAPH_INPUT_TIP = "Tip: Press Enter twice between paragraphs for clean spacing when displayed."
EMBEDDED_TOOL_HEIGHT = 860
FULL_PAGE_EMBED_HEIGHT = 1120


def render_app_header():
    # The logo lives at the top of the sidebar.
    return


def render_sidebar_logo():
    logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "logo.svg")
    try:
        with open(logo_path, "r", encoding="utf-8") as logo_file:
            logo_svg = logo_file.read()
    except Exception:
        return

    st.sidebar.markdown(
        "<div style='max-width:185px;margin:0 0 0.5rem'>" + logo_svg + "</div>",
        unsafe_allow_html=True,
    )


def render_page_title(title, subtitle=None):
    subtitle_html = f'<div class="page-subtitle">{escape(str(subtitle))}</div>' if subtitle else ""
    st.markdown(
        f"""
        <div class="page-title-block">
            <div class="page-title-text">{escape(str(title))}</div>
            {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_reading_mode_notice():
    st.markdown(
        """
        <div class="reading-mode-notice">
            Reading mode is on: larger text, wider spacing, narrower reading boxes.
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_compact_metric(label, value):
    st.markdown(
        (
            '<div class="compact-metric">'
            f'<div class="metric-label">{escape(str(label))}</div>'
            f'<div class="metric-value">{escape(str(value))}</div>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


def render_compact_card(title, body_html):
    """Render a compact dashboard/settings card with a shared shell."""
    st.markdown(
        (
            '<div class="compact-card">'
            f"<h3>{escape(str(title), quote=False)}</h3>"
            f"{body_html}"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


@contextmanager
def compact_card_container(title):
    """Open a shared compact card that can contain Streamlit elements."""
    st.markdown(
        f'<div class="compact-card"><h3>{escape(str(title), quote=False)}</h3>',
        unsafe_allow_html=True,
    )
    try:
        yield
    finally:
        st.markdown("</div>", unsafe_allow_html=True)


def render_metric_row(metrics, gap="small"):
    """Render a row of consistent compact metric cards."""
    if not metrics:
        return

    cols = st.columns(len(metrics), gap=gap)
    for col, (label, value) in zip(cols, metrics):
        with col:
            render_compact_metric(label, value)


def render_preview_table(rows, empty_message="No preview rows available.", height=280):
    """Render preview rows or a DataFrame with consistent dataframe settings."""
    if isinstance(rows, pd.DataFrame):
        if rows.empty:
            if empty_message:
                st.info(empty_message)
            return

        st.dataframe(rows, use_container_width=True, hide_index=True, height=height)
        return

    if rows:
        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
            height=height,
        )
        return

    if empty_message:
        st.info(empty_message)


def render_import_preview(metrics, rows, *, empty_message, height=280):
    """Render an import preview's metric row and preview table consistently."""
    render_metric_row(metrics)
    render_preview_table(rows, empty_message=empty_message, height=height)


def render_control_row(widths, *, gap="small"):
    """Render a consistent horizontal control row for filters and metadata inputs."""
    return st.columns(widths, gap=gap)


def render_tab_set(labels):
    """Render tabs through one helper so page-level tab spacing stays consistent."""
    return st.tabs(list(labels))


def render_compact_note(text):
    """Render a short full-width instructional note with the shared compact style."""
    st.markdown(
        f'<div class="mini-drill-note">{escape_display_text(text)}</div>',
        unsafe_allow_html=True,
    )


def render_question_detail_tabs(qd, compact_mode=False):
    """Render one question's prompt, answer, outline, and metadata tabs."""
    prompt_tab, answer_tab, outline_tab = render_tab_set(["Prompt", "Answer", "Rule Outline"])

    with prompt_tab:
        render_call_text("Call of the Question", qd["call_of_question"])
        render_question_text("Question Text", qd["question_text"])

    with answer_tab:
        render_sample_answer_text("Sample Answer / Model Analysis", qd["model_points"])

    with outline_tab:
        render_tested_issues("Tested Issues", qd["tested_issues"])
        render_readable_text("Rules", qd["rules"], compact=compact_mode)
        render_trigger_facts("Trigger Facts", get_clean_trigger_facts(qd), qd)
        render_trap_warnings("Trap Warnings", qd["traps"])


def render_text_area(
    label,
    *,
    placeholder=None,
    height=160,
    key=None,
    value="",
    caption=None,
    paragraph_tip=False,
    disabled=False,
):
    """Render a text area with consistent sizing and optional helper caption."""
    kwargs = {
        "height": height,
        "disabled": disabled,
    }
    if placeholder is not None:
        kwargs["placeholder"] = placeholder
    if key is not None:
        kwargs["key"] = key
    if value:
        kwargs["value"] = value

    result = st.text_area(label, **kwargs)

    if paragraph_tip:
        st.caption(PARAGRAPH_INPUT_TIP)
    elif caption:
        st.caption(caption)

    return result


def render_html_file_embed(path, *, height=EMBEDDED_TOOL_HEIGHT, missing_message=None):
    """Render a local HTML tool in a contained, scrollable iframe."""
    html_path = Path(path)
    try:
        html = html_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        st.error(missing_message or f"{html_path.name} was not found.")
        return

    st.markdown('<div class="full-page-embed">', unsafe_allow_html=True)
    components.html(html, height=height, scrolling=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_import_success(label, *, updated, inserted, unit="records", backup_path=None):
    """Render a consistent import success message and optional backup note."""
    st.success(f"{label} import complete. Updated {updated} and inserted {inserted} {unit}.")
    if backup_path:
        st.caption(f"Backup created: {backup_path}")


def format_review_date(value):
    if not value:
        return "not scheduled"

    return str(value)[:10]


def reveal_gate_box(text):
    st.markdown(
        f'<div class="reveal-gate">{escape_display_text(text)}</div>',
        unsafe_allow_html=True,
    )


def go_to_page(page):
    """Switch the Streamlit app to a page and rerun."""
    st.session_state["current_page"] = page
    st.rerun()


def render_nav_button(label, page, *, key=None, use_container_width=True, type="secondary"):
    """Render a button that navigates through the shared current_page state."""
    if st.button(label, key=key, use_container_width=use_container_width, type=type):
        go_to_page(page)


def render_sidebar_navigation(nav_groups, menu_aliases, advanced_tool_pages=None):
    advanced_tool_pages = set(advanced_tool_pages or [])

    for group_name, pages in nav_groups:
        st.sidebar.markdown(f'<div class="nav-group-label">{escape(str(group_name))}</div>', unsafe_allow_html=True)
        for page in pages:
            current_menu = menu_aliases.get(st.session_state["current_page"], st.session_state["current_page"])
            page_menu = menu_aliases.get(page, page)
            is_active = (
                st.session_state["current_page"] == page
                or current_menu == page_menu
                or (page == "Advanced Tools" and st.session_state["current_page"] in advanced_tool_pages)
            )

            if st.sidebar.button(
                page,
                key=f"nav_btn_{page}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                go_to_page(page)

    return menu_aliases.get(st.session_state["current_page"], st.session_state["current_page"])


def _select_random_question(labels, picker_key, select_key):
    """Select a random picker label and persist both picker state keys."""
    selected_index = random.randrange(len(labels))
    st.session_state[picker_key] = selected_index
    st.session_state[select_key] = labels[selected_index]
    return selected_index


def question_picker(active_default=True, due_only=False, compact=False):
    subjects = ["All"] + get_subjects()
    statuses = ["All"] + get_statuses()

    if compact:
        st.markdown('<div class="compact-picker">', unsafe_allow_html=True)
        col1, col2, col3, col4 = st.columns([1, 1, 0.85, 1.15], gap="small")
    else:
        col1, col2, col3 = st.columns(3)

    with col1:
        subject_filter = st.selectbox("Subject filter", subjects, key=f"subject_filter_{compact}_{due_only}")

    with col2:
        status_filter = st.selectbox("July 2026 status", statuses, key=f"status_filter_{compact}_{due_only}")

    with col3:
        active_only = st.checkbox("Active July 2026 only", value=active_default, key=f"active_only_{compact}_{due_only}")

    if compact:
        with col4:
            search = st.text_input(
                "Search",
                placeholder="hearsay, PMSI, jurisdiction",
                key=f"question_search_{compact}_{due_only}",
            )
    else:
        search = st.text_input(
            "Search issues / rules / traps",
            placeholder="e.g., hearsay, PMSI, personal jurisdiction",
            key=f"question_search_{compact}_{due_only}",
        )

    questions = get_questions(
        active_only=active_only,
        subject=subject_filter,
        status=status_filter,
        search=search,
        due_only=due_only,
    )

    if not questions:
        st.warning("No matching questions. Broaden the filter or import more.")
        if compact:
            st.markdown("</div>", unsafe_allow_html=True)
        return None

    labels = []
    for row in questions:
        due = f" | Due {format_review_date(row[6])}" if row[6] else ""
        labels.append(
            f"{row[0]} - {row[1]} Q{row[2]} - {row[3]} - {row[4]} - Priority {row[5]}{due}"
        )

    picker_key = f"question_picker_{active_default}_{due_only}_{subject_filter}_{status_filter}_{search}"
    select_key = f"{picker_key}_select"

    selected_index = min(st.session_state.get(picker_key, 0), len(labels) - 1)

    if select_key not in st.session_state or st.session_state[select_key] not in labels:
        st.session_state[select_key] = labels[selected_index]
    else:
        selected_index = labels.index(st.session_state[select_key])

    if compact:
        pick_col, select_col, count_col = st.columns([0.75, 3.2, 0.8], gap="small")
    else:
        st.caption(f"{len(questions)} matching questions")
        surprise_col, count_col = st.columns([1, 3])

        with surprise_col:
            if st.button("Pick for me", key=f"{picker_key}_surprise"):
                selected_index = _select_random_question(labels, picker_key, select_key)

        with count_col:
            st.caption("Use the picker when you know what you want; use random when starting is the hard part.")

    if compact:
        with pick_col:
            if st.button("Pick for me", key=f"{picker_key}_surprise", use_container_width=True):
                selected_index = _select_random_question(labels, picker_key, select_key)
        with select_col:
            selected_label = st.selectbox("Pick a question", labels, key=select_key)
        with count_col:
            st.markdown(f'<div class="picker-count">{len(questions)} matches</div>', unsafe_allow_html=True)
    else:
        selected_label = st.selectbox("Pick a question", labels, key=select_key)

    selected_index = labels.index(selected_label)
    st.session_state[picker_key] = selected_index

    if compact:
        st.markdown("</div>", unsafe_allow_html=True)

    return questions[selected_index][0]
