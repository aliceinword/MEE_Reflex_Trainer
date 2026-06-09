# -*- coding: utf-8 -*-
"""Primary non-practice page renderers for the MEE trainer."""

from datetime import date, timedelta
from html import escape

import pandas as pd

from database import (
    DB_NAME,
    get_dashboard_stats,
    get_exam_years,
    get_mbe_content_quality,
    get_mbe_mastery_stats,
    get_mee_content_quality,
    get_question_bank_rows,
    get_question_by_id,
    get_rule_flashcards,
    get_statuses,
    get_subjects,
)
from question_utils import unpack_question
from ui_components import (
    compact_card_container,
    render_checkbox,
    render_caption,
    render_control_row,
    render_compact_card,
    render_divider,
    render_expander,
    render_html_close,
    render_html_open,
    render_info,
    render_markdown_body,
    render_metric_row,
    render_nav_button,
    render_page_title,
    preview_table_height,
    render_preview_table,
    format_bank_question_label,
    render_match_count,
    render_question_detail_tabs,
    render_question_identity,
    render_section_heading,
    render_selectbox,
    render_success,
    render_text_input,
    render_warning,
)


QUESTION_BANK_ADDED_DATE_OPTIONS = ["All dates", "Today", "Last 7 days", "Last 30 days", "This year"]
QUESTION_BANK_VISIBLE_ROWS = 3


def question_bank_added_date_range(selected_added_date, today=None):
    """Return created_from/created_to filters for the question-bank date menu."""
    today = today or date.today()

    if selected_added_date == "Today":
        return today.isoformat(), today.isoformat()
    if selected_added_date == "Last 7 days":
        return (today - timedelta(days=7)).isoformat(), today.isoformat()
    if selected_added_date == "Last 30 days":
        return (today - timedelta(days=30)).isoformat(), today.isoformat()
    if selected_added_date == "This year":
        return date(today.year, 1, 1).isoformat(), today.isoformat()

    return None, None


def render_question_bank_filters():
    """Render Question Bank filters and return get_question_bank_rows arguments."""
    subjects = ["All"] + get_subjects()
    statuses = ["All"] + get_statuses()
    years = ["All"] + [str(year) for year in get_exam_years()]

    filter_cols = render_control_row([1.2, 1.2, 0.85, 1.05, 0.75])
    with filter_cols[0]:
        selected_subject = render_selectbox("Subject", subjects, key="bank_subject")
    with filter_cols[1]:
        selected_status = render_selectbox("Status", statuses, key="bank_status")
    with filter_cols[2]:
        selected_year = render_selectbox("Exam year", years, key="bank_year")
    with filter_cols[3]:
        selected_added_date = render_selectbox("Added date", QUESTION_BANK_ADDED_DATE_OPTIONS, key="bank_added_date")
    with filter_cols[4]:
        active_only = render_checkbox("Active only", value=True)

    topic_query = render_text_input(
        "Tested topic / keyword",
        placeholder="personal jurisdiction, hearsay, agency",
        key="bank_topic_query",
    )

    created_from, created_to = question_bank_added_date_range(selected_added_date)

    return {
        "subject": selected_subject,
        "status": selected_status,
        "topic": topic_query,
        "exam_year": None if selected_year == "All" else selected_year,
        "active_only": active_only,
        "created_from": created_from,
        "created_to": created_to,
    }


def question_bank_rows_dataframe(rows):
    """Return a formatted DataFrame for Question Bank result rows."""
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
    return bank_df


def render_question_bank_results_table(rows):
    """Render the Question Bank results table with consistent preview sizing."""
    visible_rows = rows[:QUESTION_BANK_VISIBLE_ROWS]
    if len(rows) > QUESTION_BANK_VISIBLE_ROWS:
        render_caption(
            f"Preview shows first {QUESTION_BANK_VISIBLE_ROWS}; use the dropdown below to open any of the {len(rows)} matches."
        )
    render_preview_table(
        question_bank_rows_dataframe(visible_rows),
        height=preview_table_height(len(visible_rows), max_height=220),
    )


def select_question_bank_row(rows):
    """Render the Question Bank detail selector and return the selected row."""
    labels = [format_bank_question_label(row) for row in rows]
    selected_label = render_selectbox("Open question details", labels, key="bank_selected_question")
    return rows[labels.index(selected_label)]


def render_dashboard_metrics(stats):
    """Render dashboard headline metrics."""
    metric_values = [
        ("Questions", stats["total_questions"]),
        ("Active", stats["active_questions"]),
        ("Attempts", stats["total_attempts"]),
        ("Avg Score", stats["avg_score"]),
        ("Due Reviews", stats["due_reviews"]),
    ]
    render_metric_row(metric_values)


def render_dashboard_top_cards():
    """Render the compact daily-work cards on Home."""
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


def render_dashboard_summary_cards(stats, rule_bank_cards, rule_bank_subjects):
    """Render weakest-subject and next-action cards."""
    bottom_left, bottom_right = render_control_row([1.5, 1], gap="medium")

    with bottom_left:
        with compact_card_container("Weakest Subjects"):
            if stats["subject_stats"]:
                subject_df = pd.DataFrame(
                    stats["subject_stats"],
                    columns=["Subject", "Average Score", "Attempts"],
                )
                render_preview_table(subject_df, max_rows=5)
            else:
                render_info("No attempts yet. Complete one short practice attempt to activate this view.")

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


def render_dashboard_queue_expander(stats):
    """Render the smart practice queue expander."""
    with render_expander("Smart Practice Queue", expanded=False):
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
                lambda value: "New" if value == -1 else f"{round(value, 2):g}"
            )
            queue_df["Next Review"] = queue_df["Next Review"].fillna("not scheduled")
            queue_df["Last Practiced"] = queue_df["Last Practiced"].fillna("never")

            render_preview_table(queue_df, max_rows=10)
        else:
            render_info("No active questions found yet. Import or add a few questions to build the queue.")


def render_dashboard_session_plan_expander():
    """Render the full session-plan expander."""
    with render_expander("Full 35-minute session plan", expanded=False):
        render_markdown_body("""
        1. **5 min** - Issue spotting
        2. **7 min** - Rule flash
        3. **15 min** - IRAC paragraph
        4. **5 min** - Self-grade
        5. **3 min** - Make one weak-rule note

        **Rule:** attempt retrieval before reviewing the answer.

        Where is the sample answer? Open any drill, attempt first, then click
        **Compare With Sample Answer**.
        """)


def render_dashboard_due_expander(stats):
    """Render due/untouched subject diagnostics."""
    with render_expander("Due and Untouched by Subject", expanded=False):
        if stats["due_by_subject"]:
            due_df = pd.DataFrame(stats["due_by_subject"], columns=["Subject", "Due"])
            render_preview_table(due_df, max_rows=10)
        elif stats["untouched_by_subject"]:
            untouched_df = pd.DataFrame(
                stats["untouched_by_subject"],
                columns=["Subject", "Untouched Active"],
            )
            render_preview_table(untouched_df, max_rows=10)
        else:
            render_success("No due reviews and no untouched active questions.")


def render_mbe_mastery_block(username):
    """Render MBE mastery summary on the home dashboard."""
    from app_state import get_authed_user
    mbe = get_mbe_mastery_stats(username or get_authed_user())
    if not mbe["remaining"] and not mbe["mastered"]:
        return
    render_section_heading("MBE Mastery Progress", level=4)
    render_metric_row([
        ("Remaining (target 0)", mbe["remaining"]),
        ("Mastered", mbe["mastered"]),
    ])
    if mbe["by_subject"]:
        with render_expander("Per-subject breakdown", expanded=False):
            subj_df = pd.DataFrame(
                mbe["by_subject"],
                columns=["Subject", "Remaining", "Mastered"],
            )
            render_preview_table(subj_df, max_rows=20)


def render_dashboard_page():
    stats = get_dashboard_stats()
    rule_bank_cards = get_rule_flashcards()
    rule_bank_subjects = sorted({row[1] for row in rule_bank_cards if len(row) > 1 and row[1]})

    render_page_title("Home", "One tiny useful rep. No overwhelm.")
    render_html_open("dashboard-wrap")
    render_dashboard_metrics(stats)
    render_dashboard_top_cards()

    if not rule_bank_cards:
        render_warning("No flashcards are imported yet. Add your own rule bank when you are ready.")

    render_dashboard_summary_cards(stats, rule_bank_cards, rule_bank_subjects)
    render_mbe_mastery_block(None)
    render_dashboard_queue_expander(stats)
    render_dashboard_session_plan_expander()
    render_dashboard_due_expander(stats)
    render_html_close()


def render_question_bank_page(compact_mode=False):
    render_page_title(
        "MEE Question Bank",
        "Browse, filter, and inspect stored MEE questions.",
    )

    rows = get_question_bank_rows(**render_question_bank_filters())

    render_match_count(len(rows))

    if not rows:
        render_info("No questions match those filters.")
        return

    render_question_bank_results_table(rows)

    selected_row = select_question_bank_row(rows)
    q = get_question_by_id(selected_row[0])

    if not q:
        return

    qd = unpack_question(q)
    if not qd.get("active_for_july_2026"):
        render_warning(
            "This saved row is inactive. It may be an older duplicate import; use the active version for practice."
        )
    render_question_identity(qd, show_heading=True, show_source=True)

    render_question_detail_tabs(qd, compact_mode=compact_mode)


def mee_quality_table_rows(rows):
    """Return compact table rows for incomplete MEE question diagnostics."""
    quality_rows = []
    for row in rows:
        (
            question_id,
            exam_name,
            question_number,
            subject,
            source,
            missing_prompt,
            missing_call,
            missing_sample_answer,
            missing_rules,
            missing_tested_issues,
            missing_trigger_facts,
        ) = row
        missing_fields = [
            label
            for label, is_missing in [
                ("prompt", missing_prompt),
                ("call", missing_call),
                ("sample answer", missing_sample_answer),
                ("rules", missing_rules),
                ("tested issues", missing_tested_issues),
                ("trigger facts", missing_trigger_facts),
            ]
            if is_missing
        ]
        quality_rows.append({
            "ID": question_id,
            "Question": f"{exam_name} Q{question_number}",
            "Subject": subject,
            "Missing": ", ".join(missing_fields),
            "Source": source,
        })
    return quality_rows


def render_mee_content_quality_panel():
    """Render compact MEE data-quality diagnostics in Settings."""
    with render_expander("MEE Content Quality", expanded=False):
        quality = get_mee_content_quality(limit=12)
        summary = quality["summary"]
        render_metric_row([
            ("Practice-ready", summary["practice_ready_questions"]),
            ("Missing prompt", summary["missing_prompt"]),
            ("Missing call", summary["missing_call"]),
            ("Missing rules", summary["missing_rules"]),
            ("Missing trigger facts", summary["missing_trigger_facts"]),
        ])

        if quality["rows"]:
            render_preview_table(mee_quality_table_rows(quality["rows"]), max_rows=12)
        else:
            render_success("All MEE rows have the core practice fields.")


def render_mbe_content_quality_panel():
    """Render compact MBE card and practice diagnostics in Settings."""
    with render_expander("MBE Content Quality", expanded=False):
        quality = get_mbe_content_quality(limit=12)
        summary = quality["summary"]
        render_metric_row([
            ("Total cards", summary["total_cards"]),
            ("Drill cards", summary["drill_cards"]),
            ("Flashcards", summary["flashcards"]),
            ("Content dupes", summary["content_duplicates"]),
            ("AdaptiBar ID dupes", summary["adv_id_duplicates"]),
        ])

        source_rows = [
            {"Source": source, "Cards": count}
            for source, count in quality["by_source"]
        ]
        render_preview_table(source_rows, empty_message="No MBE cards loaded.", max_rows=12)

        if quality["practice_rows"]:
            practice_rows = [
                {
                    "User": username,
                    "Stat entries": stats_entries,
                    "Practiced": practiced,
                    "Snoozed": snoozed,
                    "Updated": updated_at,
                }
                for username, stats_entries, practiced, snoozed, updated_at in quality["practice_rows"]
            ]
            render_preview_table(practice_rows, max_rows=12)
        else:
            render_warning("No MBE practice stats have been saved yet.")

        if quality["duplicate_rows"]:
            duplicate_rows = [
                {
                    "ID": card_id,
                    "Keep ID": keep_id,
                    "Subject": subject,
                    "Subtopic": subtopic,
                    "Title": title,
                }
                for card_id, keep_id, subject, subtopic, title in quality["duplicate_rows"]
            ]
            render_preview_table(duplicate_rows, max_rows=12)
        else:
            render_success("No MBE duplicate fingerprints detected.")


def render_settings_page(reading_mode, compact_mode, font_size, line_height):
    render_page_title(
        "Settings",
        "Reading comfort, layout preferences, and app health.",
    )

    render_section_heading("Layout")
    layout_values = [
        ("Reading mode", "on" if reading_mode else "off"),
        ("Compact mode", "on" if compact_mode else "off"),
        ("Legal text size", f"{font_size}px"),
        ("Line height", line_height),
    ]
    render_metric_row(layout_values)

    render_info("Use the sidebar Reading Comfort controls to change these values.")

    stats = get_dashboard_stats()
    render_section_heading("Data")
    data_values = [
        ("Questions", stats["total_questions"]),
        ("Attempts", stats["total_attempts"]),
        ("Due reviews", stats["due_reviews"]),
        ("Database", DB_NAME),
    ]
    render_metric_row(data_values)

    render_mee_content_quality_panel()
    render_mbe_content_quality_panel()

    render_divider()
    render_section_heading("Workflow")
    render_info(
        "Daily MEE work lives in MEE Muscle Ladder. MBE Drills is separate because it trains multiple-choice reflexes. "
        "Use MEE Advanced Tools only when you need to import data or add a question by hand."
    )
