# -*- coding: utf-8 -*-
"""Primary non-practice page renderers for the MEE trainer."""

from datetime import date, timedelta
from html import escape

import pandas as pd
import streamlit as st

from database import (
    DB_NAME,
    get_dashboard_stats,
    get_exam_years,
    get_question_bank_rows,
    get_question_by_id,
    get_rule_flashcards,
    get_statuses,
    get_subjects,
)
from question_utils import unpack_question
from ui_components import (
    compact_card_container,
    render_control_row,
    render_compact_card,
    render_metric_row,
    render_nav_button,
    render_page_title,
    render_preview_table,
    render_question_detail_tabs,
)


def render_dashboard_page():
    stats = get_dashboard_stats()
    render_page_title("Home", "One tiny useful rep. No overwhelm.")

    st.markdown('<div class="dashboard-wrap">', unsafe_allow_html=True)

    metric_values = [
        ("Questions", stats["total_questions"]),
        ("Active", stats["active_questions"]),
        ("Attempts", stats["total_attempts"]),
        ("Avg Score", stats["avg_score"]),
        ("Due Reviews", stats["due_reviews"]),
    ]
    render_metric_row(metric_values)

    rule_bank_cards = get_rule_flashcards()
    rule_bank_subjects = sorted({row[1] for row in rule_bank_cards if len(row) > 1 and row[1]})

    left_col, mid_col, right_col = render_control_row([1.15, 1.15, 1], gap="medium")

    with left_col:
        render_compact_card(
            "Today's Workout",
            """
            <div class="workout-step"><strong>MEE Muscle Ladder</strong><span>8 min</span></div>
            <div class="workout-step"><strong>Compare answer</strong><span>2 min</span></div>
            <div class="workout-step"><strong>Fix note</strong><span>1 min</span></div>
            <div class="workout-step"><strong>Stop or continue</strong><span>your choice</span></div>
            """,
        )
        btn1, btn2 = render_control_row(2)
        with btn1:
            render_nav_button("MEE Ladder", "MEE Muscle Ladder")
        with btn2:
            render_nav_button("MBE Drills", "MBE Drills")

    with mid_col:
        render_compact_card(
            "Tiny Win",
            """
            <div class="tiny-win">Do one Muscle Ladder rep. Save it. That counts.</div>
            <p><strong>Minimum Session:</strong></p>
            <ul>
                <li>8 min issue + rule</li>
                <li>2 min compare</li>
                <li>1 fix note</li>
            </ul>
            """,
        )

    with right_col:
        render_compact_card(
            "ADHD Guardrails",
            """
            <div class="warning-mini">No passive reading before retrieval.</div>
            <div class="warning-mini">Do not perfect the app before studying.</div>
            <div class="warning-mini">Stop after one rep if energy is low.</div>
            """,
        )

    if not rule_bank_cards:
        st.warning("No flashcards are imported yet. Add your own rule bank when you are ready.")

    bottom_left, bottom_right = render_control_row([1.5, 1], gap="medium")

    with bottom_left:
        with compact_card_container("Weakest Subjects"):
            if stats["subject_stats"]:
                subject_df = pd.DataFrame(
                    stats["subject_stats"],
                    columns=["Subject", "Average Score", "Attempts"],
                ).head(5)
                render_preview_table(subject_df, height=205)
            else:
                st.info("No attempts yet. Complete one short practice attempt to activate this view.")

    with bottom_right:
        due_reviews = stats["due_reviews"]
        next_action = (
            f"You have {due_reviews} due reviews. Do one before new work."
            if due_reviews > 0
            else "No reviews due. Do one Muscle Ladder rep."
        )
        render_compact_card(
            "Next Action",
            (
                f"<p>{escape(next_action)}</p>"
                f'<p><strong>Today:</strong> {escape(str(stats["today_attempts"]))} attempts, '
                f'{escape(str(stats["today_minutes"]))} min</p>'
                f"<p><strong>Rule bank:</strong> {len(rule_bank_cards)} cards, "
                f"{len(rule_bank_subjects)} subjects</p>"
                f'<p><strong>Unpracticed:</strong> {escape(str(stats["unpracticed_questions"]))}</p>'
            ),
        )

    with st.expander("Smart Practice Queue", expanded=False):
        if stats["recommended_queue"]:
            queue_df = pd.DataFrame(
                stats["recommended_queue"],
                columns=[
                    "ID",
                    "Exam",
                    "Q",
                    "Subject",
                    "Status",
                    "Priority",
                    "Next Review",
                    "Last Practiced",
                    "Avg Score",
                    "Attempts",
                ],
            )

            queue_df["Avg Score"] = queue_df["Avg Score"].apply(
                lambda value: "New" if value == -1 else round(value, 2)
            )
            queue_df["Next Review"] = queue_df["Next Review"].fillna("not scheduled")
            queue_df["Last Practiced"] = queue_df["Last Practiced"].fillna("never")

            render_preview_table(queue_df.head(10), height=260)
        else:
            st.info("No active questions found yet. Import or add a few questions to build the queue.")

    with st.expander("Full 35-minute session plan", expanded=False):
        st.markdown("""
        1. **5 min** - Issue spotting
        2. **7 min** - Rule flash
        3. **15 min** - IRAC paragraph
        4. **5 min** - Self-grade
        5. **3 min** - Make one weak-rule note

        **Rule:** attempt retrieval before reviewing the answer.

        Where is the sample answer? Open any drill, attempt first, then click
        **Compare With Sample Answer**.
        """)

    with st.expander("Due and Untouched by Subject", expanded=False):
        if stats["due_by_subject"]:
            due_df = pd.DataFrame(stats["due_by_subject"], columns=["Subject", "Due"])
            render_preview_table(due_df.head(10), height=260)
        elif stats["untouched_by_subject"]:
            untouched_df = pd.DataFrame(
                stats["untouched_by_subject"],
                columns=["Subject", "Untouched Active"],
            )
            render_preview_table(untouched_df.head(10), height=260)
        else:
            st.success("No due reviews and no untouched active questions.")

    st.markdown("</div>", unsafe_allow_html=True)


def render_question_bank_page(compact_mode=False):
    render_page_title(
        "Question Bank",
        "Browse, filter, and inspect stored MEE questions.",
    )

    subjects = ["All"] + get_subjects()
    statuses = ["All"] + get_statuses()
    years = ["All"] + [str(year) for year in get_exam_years()]
    added_date_options = ["All dates", "Today", "Last 7 days", "Last 30 days", "This year"]

    filter_cols = render_control_row([1.2, 1.2, 0.85, 1.05, 0.75])
    with filter_cols[0]:
        selected_subject = st.selectbox("Subject", subjects, key="bank_subject")
    with filter_cols[1]:
        selected_status = st.selectbox("Status", statuses, key="bank_status")
    with filter_cols[2]:
        selected_year = st.selectbox("Exam year", years, key="bank_year")
    with filter_cols[3]:
        selected_added_date = st.selectbox("Added date", added_date_options, key="bank_added_date")
    with filter_cols[4]:
        active_only = st.checkbox("Active only", value=False)

    topic_query = st.text_input(
        "Tested topic / keyword",
        placeholder="personal jurisdiction, hearsay, agency",
        key="bank_topic_query",
    )

    today = date.today()
    created_from = None
    created_to = None
    if selected_added_date == "Today":
        created_from = today.isoformat()
        created_to = today.isoformat()
    elif selected_added_date == "Last 7 days":
        created_from = (today - timedelta(days=7)).isoformat()
        created_to = today.isoformat()
    elif selected_added_date == "Last 30 days":
        created_from = (today - timedelta(days=30)).isoformat()
        created_to = today.isoformat()
    elif selected_added_date == "This year":
        created_from = date(today.year, 1, 1).isoformat()
        created_to = today.isoformat()

    rows = get_question_bank_rows(
        subject=selected_subject,
        status=selected_status,
        topic=topic_query,
        exam_year=None if selected_year == "All" else selected_year,
        active_only=active_only,
        created_from=created_from,
        created_to=created_to,
    )

    st.caption(f"{len(rows)} matching questions")

    if not rows:
        st.info("No questions match those filters.")
        return

    bank_df = pd.DataFrame(
        rows,
        columns=[
            "ID",
            "Exam",
            "Q",
            "Subject",
            "Year",
            "Season",
            "Status",
            "Priority",
            "Source",
            "Next Review",
            "Added",
            "Tested Issues",
        ],
    )
    bank_df["Added"] = bank_df["Added"].fillna("").astype(str).str.slice(0, 10)
    bank_df["Next Review"] = bank_df["Next Review"].fillna("").astype(str).str.slice(0, 10)
    bank_df["Tested Issues"] = (
        bank_df["Tested Issues"].fillna("").astype(str).str.replace(r"\s+", " ", regex=True).str.slice(0, 180)
    )
    render_preview_table(
        bank_df,
        height=min(420, 80 + (len(bank_df) * 32)),
    )

    labels = [
        f"{row[0]} - {row[1]} Q{row[2]} - {row[3]} - Priority {row[7] or '-'}"
        for row in rows
    ]
    selected_label = st.selectbox("Open question details", labels, key="bank_selected_question")
    selected_question_id = rows[labels.index(selected_label)][0]
    q = get_question_by_id(selected_question_id)

    if not q:
        return

    qd = unpack_question(q)
    st.subheader(f"{qd['exam_name']} Q{qd['question_number']} - {qd['subject']}")
    st.caption(
        f"Status: {qd['july_2026_status']} | Priority: {qd['priority'] or '-'} | Source: {qd['source'] or '-'}"
    )

    render_question_detail_tabs(qd, compact_mode=compact_mode)


def render_settings_page(reading_mode, compact_mode, font_size, line_height):
    render_page_title(
        "Settings",
        "Reading comfort, layout preferences, and app health.",
    )

    st.markdown("### Layout")
    layout_values = [
        ("Reading mode", "on" if reading_mode else "off"),
        ("Compact mode", "on" if compact_mode else "off"),
        ("Legal text size", f"{font_size}px"),
        ("Line height", line_height),
    ]
    render_metric_row(layout_values)

    st.info("Use the sidebar Reading Comfort controls to change these values.")

    stats = get_dashboard_stats()
    st.markdown("### Data")
    data_values = [
        ("Questions", stats["total_questions"]),
        ("Attempts", stats["total_attempts"]),
        ("Due reviews", stats["due_reviews"]),
        ("Database", DB_NAME),
    ]
    render_metric_row(data_values)

    st.divider()
    st.markdown("### Workflow")
    st.info(
        "Daily MEE work lives in MEE Muscle Ladder. MBE Drills is separate because it trains multiple-choice reflexes. "
        "Use Advanced Tools only when you need to import data or add a question by hand."
    )
