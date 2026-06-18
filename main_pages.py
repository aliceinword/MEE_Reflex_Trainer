# -*- coding: utf-8 -*-
"""Primary non-practice page renderers for the MEE trainer."""

from datetime import date, timedelta
from html import escape
from io import StringIO

import pandas as pd

from app_state import get_authed_user, is_admin
from database import (
    DB_NAME,
    add_outline_rule,
    get_dashboard_stats,
    get_exam_years,
    get_mbe_content_quality,
    get_mbe_mastery_stats,
    get_mee_content_quality,
    get_outline_rules,
    get_question_bank_rows,
    get_question_by_id,
    get_rule_flashcards,
    get_statuses,
    get_subjects,
    get_user_notification_settings,
    search_outline_rules,
    upsert_user_notification_settings,
)
from daily_error_config import describe_email_delivery_mode
from daily_error_sheet_service import send_daily_error_sheet_for_user
from missed_answer_service import build_daily_error_report, render_daily_error_report_text
from question_utils import unpack_question
from text_rendering import render_attack_rule_box
from ui_components import (
    compact_card_container,
    format_bank_question_label,
    preview_table_height,
    render_action_button,
    render_caption,
    render_checkbox,
    render_compact_card,
    render_control_row,
    render_divider,
    render_download_button,
    render_error,
    render_expander,
    render_file_uploader,
    render_form,
    render_form_submit_button,
    render_html_close,
    render_html_open,
    render_info,
    render_markdown_body,
    render_match_count,
    render_metric_row,
    render_nav_button,
    render_number_input,
    render_page_title,
    render_preview_table,
    render_question_detail_tabs,
    render_question_identity,
    render_section_heading,
    render_selectbox,
    render_success,
    render_tab_set,
    render_text_area,
    render_text_input,
    render_warning,
    rerun_app,
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
            ("QBank ID dupes", summary["adv_id_duplicates"]),
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


def render_settings_layout_panel(reading_mode, compact_mode, font_size, line_height):
    """Render current sidebar-driven reading and layout settings."""
    render_section_heading("Layout")
    layout_values = [
        ("Reading mode", "on" if reading_mode else "off"),
        ("Compact mode", "on" if compact_mode else "off"),
        ("Legal text size", f"{font_size}px"),
        ("Line height", line_height),
    ]
    render_metric_row(layout_values)

    render_info("Use the sidebar Reading Comfort controls to change these values.")


def render_settings_data_panel():
    """Render database and content-health diagnostics for Settings."""
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


def render_notification_settings_panel(username):
    """Render daily error-sheet notification settings and return send-empty choice."""
    render_divider()
    render_section_heading("Daily Error Sheet")
    render_info(describe_email_delivery_mode())
    notify_settings = get_user_notification_settings(username)
    enabled = render_checkbox(
        "Email me a daily error sheet",
        value=notify_settings["daily_error_sheet_enabled"],
        key="settings_daily_error_sheet_enabled",
    )
    email_override = render_text_input(
        "Delivery email (optional)",
        value=notify_settings["daily_error_sheet_email"] or "",
        key="settings_daily_error_sheet_email",
        caption="Defaults to your account email when left blank.",
    )
    send_hour = render_number_input(
        "Send hour (24h, local time)",
        min_value=0,
        max_value=23,
        value=int(notify_settings["daily_error_sheet_send_hour"]),
        key="settings_daily_error_sheet_send_hour",
    )
    timezone_value = render_text_input(
        "Timezone (IANA name)",
        value=notify_settings["daily_error_sheet_timezone"],
        key="settings_daily_error_sheet_timezone",
        caption="Example: America/New_York",
    )
    send_empty = render_checkbox(
        "Send email even when I had no misses",
        value=notify_settings["send_no_misses_email"],
        key="settings_daily_error_sheet_send_empty",
    )
    if render_action_button("Save notification settings", key="settings_save_notifications"):
        upsert_user_notification_settings(
            username,
            daily_error_sheet_enabled=enabled,
            daily_error_sheet_email=email_override.strip() or None,
            daily_error_sheet_send_hour=int(send_hour),
            daily_error_sheet_timezone=timezone_value.strip() or "America/New_York",
            send_no_misses_email=send_empty,
        )
        render_success("Notification settings saved.")

    return send_empty


def render_daily_error_admin_panel(username, send_empty):
    """Render admin-only preview/send controls for the daily error sheet."""
    if is_admin():
        render_caption("Admin: preview or send today's sheet for your account.")
        preview_date = render_text_input(
            "Report date (YYYY-MM-DD)",
            value=date.today().isoformat(),
            key="settings_daily_error_sheet_preview_date",
        )
        preview_col, send_col = render_control_row([1, 1], gap="medium")
        with preview_col:
            if render_action_button("Preview report", key="settings_preview_daily_error_sheet"):
                report = build_daily_error_report(username, preview_date.strip())
                render_info(
                    f"Missed {report.total_missed} question(s) across {report.unique_rules} rule(s)."
                )
                render_markdown_body(
                    "```text\n" + render_daily_error_report_text(report) + "\n```"
                )
        with send_col:
            if render_action_button("Send now (test)", key="settings_send_daily_error_sheet"):
                result = send_daily_error_sheet_for_user(
                    username,
                    preview_date.strip(),
                    force=True,
                    send_if_empty=send_empty,
                )
                if result.get("ok"):
                    if result.get("dry_run"):
                        render_success(
                            "Dry-run OK — report generated but not emailed "
                            f"(would send to {result.get('recipient_email', 'your address')}). "
                            "Add SMTP settings in .streamlit/secrets.toml to deliver for real."
                        )
                        if result.get("text_body"):
                            render_markdown_body(
                                "```text\n" + result["text_body"] + "\n```"
                            )
                    else:
                        render_success(
                            f"Email sent to {result.get('recipient_email', 'your address')}."
                        )
                else:
                    render_warning(result.get("error") or result.get("status"))


def render_settings_workflow_panel():
    """Render workflow guidance for Settings."""
    render_divider()
    render_section_heading("Workflow")
    render_info(
        "Daily MEE work lives in MEE Muscle Ladder. MBE Drills is separate because it trains multiple-choice reflexes. "
        "Use MEE Advanced Tools only when you need to import data or add a question by hand."
    )


def render_settings_page(reading_mode, compact_mode, font_size, line_height):
    render_page_title(
        "Settings",
        "Reading comfort, layout preferences, and app health.",
    )

    render_settings_layout_panel(reading_mode, compact_mode, font_size, line_height)
    render_settings_data_panel()
    username = get_authed_user()
    send_empty = render_notification_settings_panel(username)
    render_daily_error_admin_panel(username, send_empty)
    render_settings_workflow_panel()


def _outline_rule_expander_label(rule):
    """Build a readable expander title for one outline rule row."""
    _rule_id, subject, rule_title, appearance_rate, *_rest = rule
    label = f"{rule_title} — {subject}"
    if appearance_rate:
        label += f" — {appearance_rate}"
    return label


def _render_attack_outline_add_form(existing_subjects):
    """Render the single-rule add form for Attack Outline Rules."""
    with render_form("add_outline_rule_form", clear_on_submit=True):
        subject_col, rate_col = render_control_row([2, 1])
        with subject_col:
            new_subject = render_text_input(
                "Subject",
                placeholder="e.g., Evidence, Contracts, Civil Procedure",
            )
        with rate_col:
            new_appearance = render_text_input(
                "Appearance rate (optional)",
                placeholder="e.g., High",
            )

        if existing_subjects:
            render_caption("Existing subjects: " + ", ".join(existing_subjects))

        new_title = render_text_input(
            "Rule title",
            placeholder="e.g., Hearsay — definition and exceptions",
        )
        new_rule_text = render_text_area(
            "Rule text",
            placeholder="Write or paste the rule statement, elements, and any exceptions.",
            height=180,
        )
        new_source = render_text_input("Source label", value="My outline")
        submitted_rule = render_form_submit_button("Save rule")

    if not submitted_rule:
        return

    if not new_subject.strip() or not new_title.strip() or not new_rule_text.strip():
        render_error("Subject, rule title, and rule text are all required.")
        return

    created = add_outline_rule(
        new_subject.strip(),
        new_title.strip(),
        new_appearance.strip(),
        new_rule_text.strip(),
        None,
        "",
        new_source.strip() or "My outline",
    )
    if created:
        render_success("Rule added.")
        rerun_app()
    else:
        render_warning("A matching rule already exists (same subject, title, and source).")


def _render_attack_outline_bulk_import():
    """Render CSV bulk import for Attack Outline Rules."""
    render_caption(
        "Upload a CSV with columns: subject, rule_title, rule_text "
        "(optional: appearance_rate, source)."
    )

    rule_template = pd.DataFrame([
        {
            "subject": "Evidence",
            "rule_title": "Hearsay — definition",
            "rule_text": "Hearsay is an out-of-court statement offered to prove the truth of the matter asserted...",
            "appearance_rate": "High",
            "source": "My outline",
        }
    ])
    rule_buffer = StringIO()
    rule_template.to_csv(rule_buffer, index=False)
    render_download_button(
        "Download CSV template",
        data=rule_buffer.getvalue(),
        file_name="outline_rules_template.csv",
        mime="text/csv",
    )

    rules_csv = render_file_uploader("Upload rules CSV", type=["csv"], key="rules_csv")
    if rules_csv is None:
        return

    rules_df = pd.read_csv(rules_csv).fillna("")
    required = ["subject", "rule_title", "rule_text"]
    missing = [column for column in required if column not in rules_df.columns]
    if missing:
        render_error(f"Missing required columns: {missing}")
        return

    render_preview_table(rules_df, max_rows=20)

    if not render_action_button("Import rules from CSV", key="import_outline_rules_csv"):
        return

    added = 0
    skipped = 0
    for _, row in rules_df.iterrows():
        subject_value = str(row.get("subject", "")).strip()
        title_value = str(row.get("rule_title", "")).strip()
        text_value = str(row.get("rule_text", "")).strip()
        if not subject_value or not title_value or not text_value:
            skipped += 1
            continue

        created = add_outline_rule(
            subject_value,
            title_value,
            str(row.get("appearance_rate", "")).strip(),
            text_value,
            None,
            "",
            str(row.get("source", "")).strip() or "My outline (CSV)",
        )
        if created:
            added += 1
        else:
            skipped += 1

    render_success(f"Imported {added} rule(s). Skipped {skipped} (duplicate or incomplete).")
    rerun_app()


def render_attack_outline_rules_page(*, reading_mode=False):
    """Browse and search personal attack-outline rules by subject."""
    render_page_title(
        "Attack Outline Rules",
        "Search your rule outline by subject and keyword, or add your own rules.",
    )

    all_rules = get_outline_rules()
    existing_subjects = sorted({row[1] for row in all_rules if row[1]})
    outline_subjects = ["All"] + existing_subjects

    if not all_rules:
        render_info(
            'No rules yet. Use "Add your own rules" below to type or paste rules from '
            "your own outline. You can also bulk-import from a CSV."
        )

    with render_expander("Add your own rules", expanded=not all_rules):
        add_tab, bulk_tab = render_tab_set(["Add one rule", "Bulk add (CSV)"])
        with add_tab:
            _render_attack_outline_add_form(existing_subjects)
        with bulk_tab:
            _render_attack_outline_bulk_import()

    query_col, subject_col = render_control_row([2, 1])
    with query_col:
        outline_query = render_text_input(
            "Search rules",
            placeholder="personal jurisdiction, hearsay, statute of frauds",
            key="attack_outline_query",
        )
    with subject_col:
        outline_subject = render_selectbox(
            "Subject",
            outline_subjects,
            key="attack_outline_subject",
        )

    subject_filter = None if outline_subject == "All" else outline_subject
    if outline_query.strip():
        outline_results = search_outline_rules(
            outline_query.strip(),
            subject=subject_filter,
            limit=25,
        )
    else:
        outline_results = get_outline_rules(subject=subject_filter)[:25]

    render_caption(f"{len(outline_results)} result(s)")

    for rule in outline_results:
        with render_expander(_outline_rule_expander_label(rule), expanded=False):
            render_attack_rule_box(rule, reading_mode=reading_mode)
