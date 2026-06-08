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

from app_state import get_current_page, set_current_page
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
TEXTAREA_HEIGHT_XS = 90
TEXTAREA_HEIGHT_SM = 120
TEXTAREA_HEIGHT_MD = 160
TEXTAREA_HEIGHT_OUTLINE = 170
TEXTAREA_HEIGHT_LG = 280
TEXTAREA_HEIGHT_XL = 360
TEXTAREA_HEIGHT_XXL = 420
TEXTAREA_HEIGHT_PREVIEW = 320


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

    render_sidebar_html("<div style='max-width:185px;margin:0 0 0.5rem'>" + logo_svg + "</div>")


def render_sidebar_html(html):
    """Render trusted sidebar HTML through the shared UI layer."""
    st.sidebar.markdown(html, unsafe_allow_html=True)


def render_sidebar_markdown(markdown_text):
    """Render sidebar Markdown through the shared UI layer."""
    st.sidebar.markdown(markdown_text)


def render_sidebar_action_button(label, *, key=None, type="secondary", use_container_width=True):
    """Render a sidebar action button through the shared UI layer."""
    return st.sidebar.button(label, key=key, use_container_width=use_container_width, type=type)


def render_sidebar_checkbox(label, *, value=False, key=None):
    """Render a sidebar checkbox through the shared UI layer."""
    kwargs = {"value": value}
    if key is not None:
        kwargs["key"] = key
    return st.sidebar.checkbox(label, **kwargs)


def render_sidebar_slider(label, min_value, max_value, value, *, key=None):
    """Render a sidebar slider through the shared UI layer."""
    kwargs = {}
    if key is not None:
        kwargs["key"] = key
    return st.sidebar.slider(label, min_value, max_value, value, **kwargs)


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


def render_section_heading(title, *, level=3):
    """Render a consistent section heading without page-local Markdown heading syntax."""
    safe_level = min(max(int(level), 2), 4)
    tag = f"h{safe_level}"
    st.markdown(
        f'<{tag} class="section-heading section-heading-level-{safe_level}">{escape(str(title))}</{tag}>',
        unsafe_allow_html=True,
    )


def render_question_identity(qd, *, show_heading=False, show_source=False):
    """Render a question's exam/subject identity with one shared format."""
    exam = qd.get("exam_name") or "Unknown exam"
    question_number = qd.get("question_number") or "-"
    subject = qd.get("subject") or "Unknown subject"
    priority = qd.get("priority") or "-"

    if show_heading:
        render_section_heading(f"{exam} Q{question_number} - {subject}", level=3)

    caption_parts = [f"{exam} Q{question_number}", subject, f"Priority {priority}"]
    status = qd.get("july_2026_status")
    if status:
        caption_parts.insert(2, status)
    if show_source:
        caption_parts.append(f"Source: {qd.get('source') or '-'}")

    render_caption(" | ".join(str(part) for part in caption_parts))


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
    """Render a responsive row of consistent compact metric cards."""
    if not metrics:
        return

    gap_rem = {"small": "0.55rem", "medium": "0.8rem", "large": "1rem"}.get(gap, "0.55rem")
    cards = []
    for label, value in metrics:
        cards.append(
            '<div class="compact-metric">'
            f'<div class="metric-label">{escape(str(label))}</div>'
            f'<div class="metric-value">{escape(str(value))}</div>'
            "</div>"
        )

    st.markdown(
        f'<div class="metric-grid" style="--metric-grid-gap:{gap_rem}">' + "".join(cards) + "</div>",
        unsafe_allow_html=True,
    )


def preview_table_height(row_count, *, min_height=150, max_height=360, row_height=32, header_height=78):
    """Return a compact table height based on the number of displayed rows."""
    if row_count <= 0:
        return min_height
    return min(max_height, max(min_height, header_height + (int(row_count) * row_height)))


def render_preview_table(rows, empty_message="No preview rows available.", height=None, max_rows=None):
    """Render preview rows or a DataFrame with adaptive, consistent dataframe settings."""
    if isinstance(rows, pd.DataFrame):
        if rows.empty:
            if empty_message:
                render_info(empty_message)
            return

        if max_rows is not None:
            rows = rows.head(max_rows)
        height = height or preview_table_height(len(rows))
        st.dataframe(rows, use_container_width=True, hide_index=True, height=height)
        return

    if rows:
        rows = list(rows)
        if max_rows is not None:
            rows = rows[:max_rows]
        height = height or preview_table_height(len(rows))
        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
            height=height,
        )
        return

    if empty_message:
        render_info(empty_message)


def render_import_preview(metrics, rows, *, empty_message, height=None, max_rows=8):
    """Render an import preview's metric row and adaptive preview table consistently."""
    render_metric_row(metrics)
    render_preview_table(rows, empty_message=empty_message, height=height, max_rows=max_rows)


def render_import_dry_run_preview(
    *,
    action,
    metrics_from_result,
    rows_from_result,
    empty_message,
    spinner_text=None,
    height=None,
    max_rows=8,
):
    """Run one import dry run and render its standard preview table."""
    if spinner_text:
        with render_spinner(spinner_text):
            result = action()
    else:
        result = action()

    render_import_preview(
        metrics_from_result(result),
        rows_from_result(result),
        empty_message=empty_message,
        height=height,
        max_rows=max_rows,
    )
    return result


def render_control_row(widths, *, gap="small", vertical_alignment="top"):
    """Render a full-width, consistently aligned horizontal row for page controls."""
    return st.columns(widths, gap=gap, vertical_alignment=vertical_alignment, width="stretch")


def render_tab_set(labels):
    """Render tabs through one helper so page-level tab spacing stays consistent."""
    return st.tabs(list(labels))


@contextmanager
def render_expander(label, *, expanded=False):
    """Open a standard Streamlit expander through the shared UI layer."""
    with st.expander(label, expanded=expanded):
        yield


@contextmanager
def render_form(form_key, *, clear_on_submit=False):
    """Open a standard Streamlit form through the shared UI layer."""
    with st.form(form_key, clear_on_submit=clear_on_submit):
        yield


def render_compact_note(text):
    """Render a short full-width instructional note with the shared compact style."""
    st.markdown(
        f'<div class="mini-drill-note">{escape_display_text(text)}</div>',
        unsafe_allow_html=True,
    )


def render_html_open(class_name):
    """Open a simple HTML layout wrapper through the shared UI layer."""
    st.markdown(f'<div class="{escape(str(class_name), quote=True)}">', unsafe_allow_html=True)


def render_html_close():
    """Close a simple HTML layout wrapper opened through the shared UI layer."""
    st.markdown("</div>", unsafe_allow_html=True)


def render_markdown_body(markdown_text):
    """Render page-level Markdown prose through the shared UI layer."""
    st.markdown(markdown_text)


def render_html_body(html):
    """Render trusted HTML through the shared UI layer."""
    st.markdown(html, unsafe_allow_html=True)


def render_caption(text):
    """Render supporting caption text through the shared UI layer."""
    st.caption(text)


def render_info(text):
    """Render an informational message through the shared UI layer."""
    st.info(text)


def render_success(text):
    """Render a success message through the shared UI layer."""
    st.success(text)


def render_warning(text):
    """Render a warning message through the shared UI layer."""
    st.warning(text)


def render_error(text):
    """Render an error message through the shared UI layer."""
    st.error(text)


def render_spinner(text):
    """Return a spinner context from the shared UI layer."""
    return st.spinner(text)


def render_divider():
    """Render the app's standard section divider."""
    st.divider()


def irac_answer_template():
    """Return a compact IRAC starter for question-bank drafting."""
    return """Issue:
The issue is whether ___.

Rule:
Under ___, ___.

Application:
Here, ___ because ___.

Conclusion:
Therefore, ___."""


def render_question_detail_tabs(qd, compact_mode=False):
    """Render one question's prompt, answer, outline, and metadata tabs."""
    prompt_tab, answer_tab, outline_tab = render_tab_set(["Prompt", "Answer", "Rule Outline"])

    with prompt_tab:
        render_call_text("Call of the Question", qd["call_of_question"])
        question_col, answer_col = render_control_row([1.08, 0.92], gap="large")
        with question_col:
            render_question_text("Question Text", qd["question_text"])
        with answer_col:
            render_text_area(
                "Your IRAC Answer",
                value=irac_answer_template(),
                height=TEXTAREA_HEIGHT_XXL,
                key=f"question_bank_irac_answer_{qd['id']}",
            )

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
        "width": "stretch",
    }
    if placeholder is not None:
        kwargs["placeholder"] = placeholder
    if key is not None:
        kwargs["key"] = key
    if value:
        kwargs["value"] = value

    result = st.text_area(label, **kwargs)

    if paragraph_tip:
        render_caption(PARAGRAPH_INPUT_TIP)
    elif caption:
        render_caption(caption)

    return result


def render_text_input(label, *, placeholder=None, key=None, value="", type="default", caption=None):
    """Render a text input with consistent optional caption handling."""
    kwargs = {"type": type, "width": "stretch"}
    if placeholder is not None:
        kwargs["placeholder"] = placeholder
    if key is not None:
        kwargs["key"] = key
    if value:
        kwargs["value"] = value

    result = st.text_input(label, **kwargs)
    if caption:
        render_caption(caption)
    return result


def render_selectbox(label, options, *, key=None, index=0, caption=None):
    """Render a selectbox through the shared control layer."""
    kwargs = {"index": index, "width": "stretch"}
    if key is not None:
        kwargs["key"] = key

    result = st.selectbox(label, options, **kwargs)
    if caption:
        render_caption(caption)
    return result


def render_checkbox(label, *, value=False, key=None, caption=None):
    """Render a checkbox through the shared control layer."""
    kwargs = {"value": value}
    if key is not None:
        kwargs["key"] = key

    result = st.checkbox(label, **kwargs)
    if caption:
        render_caption(caption)
    return result


def render_slider(label, min_value, max_value, value, *, key=None, caption=None):
    """Render a slider through the shared control layer."""
    kwargs = {"width": "stretch"}
    if key is not None:
        kwargs["key"] = key

    result = st.slider(label, min_value, max_value, value, **kwargs)
    if caption:
        render_caption(caption)
    return result


def render_number_input(label, *, min_value=None, max_value=None, value=None, key=None, caption=None):
    """Render a number input through the shared control layer."""
    kwargs = {"width": "stretch"}
    if min_value is not None:
        kwargs["min_value"] = min_value
    if max_value is not None:
        kwargs["max_value"] = max_value
    if value is not None:
        kwargs["value"] = value
    if key is not None:
        kwargs["key"] = key

    result = st.number_input(label, **kwargs)
    if caption:
        render_caption(caption)
    return result


def render_file_uploader(label, *, type=None, key=None, caption=None):
    """Render a file uploader through the shared control layer."""
    kwargs = {"width": "stretch"}
    if type is not None:
        kwargs["type"] = type
    if key is not None:
        kwargs["key"] = key

    result = st.file_uploader(label, **kwargs)
    if caption:
        render_caption(caption)
    return result


def render_download_button(label, *, data, file_name, mime=None, key=None, use_container_width=True):
    """Render a download button with the app's default full-width behavior."""
    kwargs = {
        "data": data,
        "file_name": file_name,
        "use_container_width": use_container_width,
    }
    if mime is not None:
        kwargs["mime"] = mime
    if key is not None:
        kwargs["key"] = key

    return st.download_button(label, **kwargs)


def render_html_file_embed(path, *, height=EMBEDDED_TOOL_HEIGHT, missing_message=None, scrolling=True):
    """Render a local HTML tool in an iframe."""
    html_path = Path(path)
    try:
        html = html_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        render_error(missing_message or f"{html_path.name} was not found.")
        return

    st.markdown('<div class="full-page-embed" aria-hidden="true"></div>', unsafe_allow_html=True)
    components.html(html, height=height, scrolling=scrolling)


def render_import_success(label, *, updated, inserted, unit="records", backup_path=None):
    """Render a consistent import success message and optional backup note."""
    render_success(f"{label} import complete. Updated {updated} and inserted {inserted} {unit}.")
    if backup_path:
        render_caption(f"Backup created: {backup_path}")


def render_import_apply_action(
    label,
    *,
    action,
    success_label,
    stats_from_result,
    spinner_text=None,
    unit="questions",
):
    """Run one import apply action and render the standard success feedback."""
    if not render_primary_action_button(label):
        return None

    if spinner_text:
        with render_spinner(spinner_text):
            result = action()
    else:
        result = action()

    stats = stats_from_result(result) or {}
    render_import_success(
        success_label,
        updated=stats.get("updated", 0),
        inserted=stats.get("inserted", 0),
        unit=stats.get("unit", unit),
        backup_path=stats.get("backup_path") or stats.get("backup"),
    )
    return result


def format_review_date(value):
    if not value:
        return "not scheduled"

    return str(value)[:10]


def format_picker_question_label(row):
    """Format a get_questions row for question picker controls."""
    due = f" | Due {format_review_date(row[6])}" if row[6] else ""
    return f"{row[0]} - {row[1]} Q{row[2]} - {row[3]} - {row[4]} - Priority {row[5]}{due}"


def format_bank_question_label(row):
    """Format a get_question_bank_rows row for the bank detail selector."""
    return f"{row[0]} - {row[1]} Q{row[2]} - {row[3]} - Priority {row[7] or '-'}"


def format_match_count(count, *, noun="question", compact=False):
    """Format result-count text consistently for pickers and banks."""
    suffix = "" if int(count) == 1 else "s"
    if compact:
        return f"{count} match{suffix}"
    return f"{count} matching {noun}{suffix}"


def render_match_count(count, *, noun="question", compact=False):
    """Render a result count with either compact-picker or caption styling."""
    label = format_match_count(count, noun=noun, compact=compact)
    if compact:
        st.markdown(f'<div class="picker-count">{escape_display_text(label)}</div>', unsafe_allow_html=True)
        return

    render_caption(label)


def reveal_gate_box(text):
    st.markdown(
        f'<div class="reveal-gate">{escape_display_text(text)}</div>',
        unsafe_allow_html=True,
    )


def render_reveal_control(label, state_key, *, gate_text, key=None):
    """Render a retrieval gate plus reveal button and return whether content is revealed."""
    reveal_gate_box(gate_text)
    if st.button(label, use_container_width=True, key=key or state_key):
        st.session_state[state_key] = True

    return st.session_state.get(state_key, False)


def render_primary_action_button(label, *, key=None):
    """Render a consistent full-width primary action button."""
    return st.button(label, type="primary", use_container_width=True, key=key)


def render_action_button(label, *, key=None, type="secondary", use_container_width=True):
    """Render a standard action button through the shared UI layer."""
    return st.button(label, key=key, type=type, use_container_width=use_container_width)


def render_form_submit_button(label, *, type="primary", use_container_width=True):
    """Render a consistent form submit button."""
    return st.form_submit_button(label, type=type, use_container_width=use_container_width)


def rerun_app():
    """Rerun Streamlit through the shared UI layer."""
    st.rerun()


def stop_app():
    """Stop Streamlit execution through the shared UI layer."""
    st.stop()


def go_to_page(page):
    """Switch the Streamlit app to a page and rerun."""
    set_current_page(page)
    rerun_app()


def render_nav_button(label, page, *, key=None, use_container_width=True, type="secondary"):
    """Render a button that navigates through the shared current_page state."""
    if render_action_button(label, key=key, use_container_width=use_container_width, type=type):
        go_to_page(page)


def render_sidebar_navigation(nav_groups, menu_aliases, advanced_tool_pages=None):
    advanced_tool_pages = set(advanced_tool_pages or [])

    for group_name, pages in nav_groups:
        render_sidebar_html(f'<div class="nav-group-label">{escape(str(group_name))}</div>')
        for page in pages:
            current_page = get_current_page()
            current_menu = menu_aliases.get(current_page, current_page)
            page_menu = menu_aliases.get(page, page)
            is_active = (
                current_page == page
                or current_menu == page_menu
                or (page in {"Advanced Tools", "MEE Advanced Tools"} and current_page in advanced_tool_pages)
            )

            if render_sidebar_action_button(
                page,
                key=f"nav_btn_{page}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                go_to_page(page)

    current_page = get_current_page()
    return menu_aliases.get(current_page, current_page)


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
        subject_filter = render_selectbox("Subject filter", subjects, key=f"subject_filter_{compact}_{due_only}")

    with col2:
        status_filter = render_selectbox("July 2026 status", statuses, key=f"status_filter_{compact}_{due_only}")

    with col3:
        active_only = render_checkbox(
            "Active July 2026 only",
            value=active_default,
            key=f"active_only_{compact}_{due_only}",
        )

    if compact:
        with col4:
            search = render_text_input(
                "Search",
                placeholder="hearsay, PMSI, jurisdiction",
                key=f"question_search_{compact}_{due_only}",
            )
    else:
        search = render_text_input(
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
        render_warning("No matching questions. Broaden the filter or import more.")
        if compact:
            st.markdown("</div>", unsafe_allow_html=True)
        return None

    labels = [format_picker_question_label(row) for row in questions]

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
        render_match_count(len(questions))
        surprise_col, count_col = st.columns([1, 3])

        with surprise_col:
            if render_action_button("Pick for me", key=f"{picker_key}_surprise", use_container_width=False):
                selected_index = _select_random_question(labels, picker_key, select_key)

        with count_col:
            render_caption("Use the picker when you know what you want; use random when starting is the hard part.")

    if compact:
        with pick_col:
            if render_action_button("Pick for me", key=f"{picker_key}_surprise"):
                selected_index = _select_random_question(labels, picker_key, select_key)
        with select_col:
            selected_label = render_selectbox("Pick a question", labels, key=select_key)
        with count_col:
            render_match_count(len(questions), compact=True)
    else:
        selected_label = render_selectbox("Pick a question", labels, key=select_key)

    selected_index = labels.index(selected_label)
    st.session_state[picker_key] = selected_index

    if compact:
        st.markdown("</div>", unsafe_allow_html=True)

    return questions[selected_index][0]
