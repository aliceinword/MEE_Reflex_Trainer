# -*- coding: utf-8 -*-
"""MBE page renderer for the separate multiple-choice trainer."""

import os

import streamlit as st

from app_state import get_authed_user
from database import (
    count_mbe_cards,
    fetch_one,
    get_mbe_cards,
    get_mbe_practice_stats,
    save_bridge_attempt,
    save_mbe_practice_stats,
    upsert_mbe_cards,
)
from mbe_import_services import (
    MBE_BULK_TEMPLATE_COLUMNS,
    database_rows_to_mbe_cards,
    extra_mbe_template_columns,
    mbe_cards_from_dataframe,
    mbe_upload_metrics,
    mbe_upload_preview_rows,
    missing_mbe_template_columns,
    read_mbe_bulk_upload,
    read_mbe_template_bytes,
)

from ui_components import (
    clear_cached_data,
    render_action_button,
    render_component_html,
    render_caption,
    render_compact_note,
    render_control_row,
    render_download_button,
    session_state,
    rerun_app,
    render_text_area,
    render_selectbox,
    render_select_slider,
    render_radio,
    render_expander,
    render_error,
    render_file_uploader,
    render_html_body,
    render_import_preview,
    render_info,
    render_metric_row,
    render_primary_action_button,
    render_section_heading,
    render_success,
    TEXTAREA_HEIGHT_SM,
    TEXTAREA_HEIGHT_XS,
    render_warning,
)


def render_mbe_bulk_template_downloads():
    csv_bytes = read_mbe_template_bytes("MBE_trap_trainer_template.csv")
    xlsx_bytes = read_mbe_template_bytes("MBE_trap_trainer_template_1.xlsx")

    render_section_heading("Templates", level=4)
    if csv_bytes:
        render_download_button(
            "Download CSV Template",
            data=csv_bytes,
            file_name="MBE_trap_trainer_template.csv",
            mime="text/csv",
            key="mbe_bulk_csv_template",
        )
    else:
        render_warning("CSV template file is missing from the project folder.")

    if xlsx_bytes:
        render_download_button(
            "Download Excel Template",
            data=xlsx_bytes,
            file_name="MBE_trap_trainer_template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="mbe_bulk_xlsx_template",
        )
    else:
        render_warning("Excel template file is missing from the project folder.")

    render_caption("Required columns:")
    render_info(", ".join(MBE_BULK_TEMPLATE_COLUMNS))


def render_mbe_bulk_file_uploader():
    render_section_heading("Upload Check", level=4)
    return render_file_uploader(
        "Upload completed MBE bulk file",
        type=["csv", "xlsx", "xls"],
        key="mbe_bulk_question_upload",
        caption="CSV works offline. Excel files may need openpyxl installed.",
    )


def read_uploaded_mbe_bulk_file(uploaded_file):
    if uploaded_file is None:
        render_info("Upload a completed template to preview rows and catch missing columns before importing.")
        return None
    try:
        return read_mbe_bulk_upload(uploaded_file)
    except Exception as exc:
        render_error(str(exc))
        return None


def render_mbe_bulk_column_check(df):
    missing = missing_mbe_template_columns(df.columns)
    extra = extra_mbe_template_columns(df.columns)
    render_metric_row(mbe_upload_metrics(df, missing, extra))

    if missing:
        render_error("Missing required columns: " + ", ".join(missing))
    else:
        render_success("Column check passed. This file matches the MBE bulk template.")

    if extra:
        render_warning("Extra columns will be ignored by the trainer: " + ", ".join(extra))
    return missing, extra


def render_mbe_bulk_preview(df):
    render_import_preview(
        [],
        mbe_upload_preview_rows(df),
        empty_message="No previewable rows found.",
    )


def render_mbe_bulk_row_errors(row_errors):
    if not row_errors:
        return
    render_warning("Some rows are not importable: " + " ".join(row_errors[:5]))
    if len(row_errors) > 5:
        render_caption(f"{len(row_errors) - 5} more row issue(s) not shown.")


def render_mbe_bulk_import_actions(cards, missing):
    if missing:
        return

    if not cards:
        render_warning("No valid MBE cards found to import.")
        return

    existing_uids = {row[1] for row in get_mbe_cards()}
    new_count = sum(1 for card in cards if card["card_uid"] not in existing_uids)
    update_count = len(cards) - new_count
    render_metric_row(
        [
            ("Ready to import", len(cards)),
            ("New cards", new_count),
            ("Already in database", update_count),
        ]
    )
    if render_primary_action_button("Save Cards to Main App Database", key="save_mbe_cards_to_db"):
        result = upsert_mbe_cards(cards)
        render_success(
            "MBE import complete. "
            f"Inserted {result['inserted']} and updated {result['updated']} cards in the app database."
        )
        invalidate_mbe_trainer_session_cache()


def render_mbe_bulk_upload_page():
    render_section_heading("MBE Drills Question Bulk Upload")
    render_compact_note(
        "Use these templates for MBE trap-trainer questions. Uploaded cards are saved in the main app database, not only in this browser."
    )
    render_metric_row([("MBE cards in app database", count_mbe_cards())])

    template_col, upload_col = render_control_row([0.9, 1.35], gap="large")
    with template_col:
        render_mbe_bulk_template_downloads()

    with upload_col:
        uploaded_file = render_mbe_bulk_file_uploader()
        df = read_uploaded_mbe_bulk_file(uploaded_file)
        if df is None:
            return

        missing, _extra = render_mbe_bulk_column_check(df)
        render_mbe_bulk_preview(df)
        cards, row_errors = mbe_cards_from_dataframe(df, source_name=uploaded_file.name or "MBE bulk upload")
        render_mbe_bulk_row_errors(row_errors)
        render_mbe_bulk_import_actions(cards, missing)


def render_mbe_drills_page():
    render_mbe_trainer_page(embed_mode="drill", exclude_sources={"qbank_rules"})


def reset_mbe_flashcard_state():
    """Clear flashcard drill session state."""
    for key in list(session_state.keys()):
        if key.startswith("mbe_fc_"):
            del session_state[key]


def render_mbe_flashcard_filters(all_rows):
    """Render flashcard source/subject filters and return the matching rows."""
    source_options = ["All sources"] + sorted({row[12] or "App database" for row in all_rows})
    default_source = "qbank_rules" if "qbank_rules" in source_options else source_options[0]

    control_col, metric_col = render_control_row([1.5, 1], gap="medium")
    with control_col:
        selected_source = render_selectbox(
            "Flashcard source",
            source_options,
            index=source_options.index(default_source),
            key="mbe_flashcards_source_filter",
        )
        source_filter = None if selected_source == "All sources" else selected_source
        source_rows = _filter_mbe_card_rows(all_rows, source_filter=source_filter)
        subject_options = ["All subjects"] + sorted({row[3] for row in source_rows if row[3]})
        selected_subject = render_selectbox(
            "Subject",
            subject_options,
            key="mbe_flashcards_subject_filter",
        )
        subject_filter = None if selected_subject == "All subjects" else selected_subject

    filtered_rows = _filter_mbe_card_rows(
        all_rows,
        source_filter=source_filter,
        subject_filter=subject_filter,
    )
    with metric_col:
        render_metric_row(
            [
                ("Flashcards loaded", len(filtered_rows)),
                ("Subjects", max(len(subject_options) - 1, 0)),
            ]
        )
    return filtered_rows, selected_source, selected_subject


def ensure_mbe_flashcard_queue(filtered_rows, selected_source, selected_subject):
    """Initialize or reuse the flashcard queue for the selected filters."""
    import random

    sig = ("flashcards", selected_source, selected_subject, len(filtered_rows))
    if session_state.get("mbe_fc_sig") == sig and "mbe_fc_queue" in session_state:
        return session_state["mbe_fc_queue"]

    cards = database_rows_to_mbe_cards(filtered_rows)
    random.shuffle(cards)
    session_state.update(
        {
            "mbe_fc_sig": sig,
            "mbe_fc_queue": cards,
            "mbe_fc_idx": 0,
            "mbe_fc_show_answer": False,
        }
    )
    return cards


def render_mbe_flashcard_empty_state():
    """Render deck-complete state for flashcards."""
    render_success("Deck complete. No cards left in this filtered session.")
    if render_primary_action_button("Restart Deck", key="mbe_fc_restart_empty"):
        reset_mbe_flashcard_state()
        rerun_app()


def current_mbe_flashcard(queue):
    """Return current flashcard drill context."""
    idx = min(session_state.get("mbe_fc_idx", 0), max(len(queue) - 1, 0))
    session_state["mbe_fc_idx"] = idx
    card = queue[idx]
    card_uid = card.get("cardUid") or card.get("id") or str(idx)
    answer_key = f"mbe_fc_answer_{card_uid}"
    options = card.get("options") or []
    correct = next((option for option in options if option.get("ok")), {})
    trap = next((option for option in options if option.get("trap") and not option.get("ok")), {})
    return idx, card, answer_key, correct, trap


def render_mbe_flashcard_prompt(card, idx, queue_len):
    """Render the flashcard front side."""
    from html import escape as _esc

    progress = round(((idx + 1) / max(queue_len, 1)) * 100)
    render_html_body(
        f"""
        <div style="height:6px;background:#dbeafe;border-radius:999px;margin:12px 0 10px;">
            <div style="width:{progress}%;height:6px;background:#4169e1;border-radius:999px;"></div>
        </div>
        <div style="font-size:0.9rem;color:#64748b;margin-bottom:12px;">
            Card {idx + 1} of {queue_len}
        </div>
        <div style="background:#111827;color:#f8fafc;border-radius:10px;padding:18px 20px;margin-bottom:14px;border-left:5px solid #f97316;">
            <div style="font-size:0.78rem;letter-spacing:0.08em;text-transform:uppercase;color:#fdba74;margin-bottom:8px;">
                {_esc(card.get("subj", ""))} / {_esc(card.get("sub", ""))}
            </div>
            <div style="font-size:1.2rem;font-weight:800;line-height:1.35;margin-bottom:10px;">
                {_esc(card.get("title") or card.get("sub") or "Rule Flashcard")}
            </div>
            <div style="font-size:1.02rem;line-height:1.6;color:#e5e7eb;">
                {_esc(card.get("q") or "Recall the governing rule.")}
            </div>
        </div>
        """
    )


def render_mbe_flashcard_retrieval_controls(queue, idx, answer_key):
    """Render flashcard retrieval input and pre-answer actions."""
    import random

    render_text_area(
        "Write the rule from memory",
        key=answer_key,
        height=TEXTAREA_HEIGHT_SM,
        placeholder="State the rule, elements, exception, or shortcut before revealing.",
    )
    render_caption("Retrieve first. Then compare with the rule card.")
    c1, c2, c3 = render_control_row([1, 1, 1], gap="small")
    with c1:
        if render_primary_action_button("Show Answer", key="mbe_fc_show"):
            session_state["mbe_fc_show_answer"] = True
            rerun_app()
    with c2:
        if render_action_button("Shuffle Deck", key="mbe_fc_shuffle"):
            random.shuffle(queue)
            session_state.update({"mbe_fc_queue": queue, "mbe_fc_idx": 0, "mbe_fc_show_answer": False})
            rerun_app()
    with c3:
        if render_action_button("Next Card", key="mbe_fc_next_unseen"):
            if len(queue) > 1:
                queue.append(queue.pop(idx))
            session_state.update(
                {
                    "mbe_fc_queue": queue,
                    "mbe_fc_idx": idx % len(queue),
                    "mbe_fc_show_answer": False,
                }
            )
            rerun_app()


def render_mbe_flashcard_answer(card, correct, trap, answer_key):
    """Render the flashcard answer side."""
    from html import escape as _esc

    rule_text = correct.get("why") or card.get("ru") or ""
    plain_text = card.get("plain") or ""
    shortcut = card.get("ru") or ""
    correct_text = correct.get("t") or ""
    trap_text = trap.get("why") or ""
    trap_choice = trap.get("t") or ""
    user_answer = session_state.get(answer_key, "")

    render_html_body(
        f"""
        <div style="background:#ffffff;border:1px solid #bfdbfe;border-radius:10px;padding:18px 20px;margin-bottom:12px;">
            <div style="font-size:0.82rem;font-weight:800;color:#2563eb;text-transform:uppercase;margin-bottom:8px;">Rule</div>
            <div style="font-size:1.03rem;line-height:1.7;color:#111827;">{_esc(rule_text)}</div>
        </div>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px;margin-bottom:12px;">
            <div style="background:#f0fdf4;border-left:4px solid #16a34a;border-radius:8px;padding:14px;">
                <div style="font-weight:800;color:#166534;margin-bottom:6px;">Plain English</div>
                <div style="line-height:1.6;color:#14532d;">{_esc(plain_text or "No plain-English version stored.")}</div>
            </div>
            <div style="background:#fff7ed;border-left:4px solid #f97316;border-radius:8px;padding:14px;">
                <div style="font-weight:800;color:#9a3412;margin-bottom:6px;">Shortcut</div>
                <div style="line-height:1.6;color:#7c2d12;">{_esc(shortcut or "No shortcut stored.")}</div>
            </div>
        </div>
        <div style="background:#f8fafc;border:1px solid #dbeafe;border-radius:10px;padding:14px 16px;margin-bottom:12px;">
            <div style="font-weight:800;color:#1d4ed8;margin-bottom:6px;">Correct Answer</div>
            <div style="line-height:1.6;color:#111827;">{_esc(correct_text or "No correct-answer text stored.")}</div>
        </div>
        """
    )
    if trap_text or trap_choice:
        render_html_body(
            f"""
            <div style="background:#fff7ed;border:1px solid #fed7aa;border-radius:10px;padding:14px 16px;margin-bottom:12px;">
                <div style="font-weight:800;color:#c2410c;margin-bottom:6px;">Trap to Avoid</div>
                <div style="line-height:1.6;color:#7c2d12;"><strong>{_esc(trap_choice)}</strong></div>
                <div style="line-height:1.6;color:#7c2d12;margin-top:6px;">{_esc(trap_text)}</div>
            </div>
            """
        )
    if user_answer:
        with render_expander("Your retrieval answer", expanded=False):
            render_html_body("<div class=\"draft-answer-box\">" + _esc(user_answer) + "</div>")


def render_mbe_flashcard_answer_actions(queue, idx):
    """Render post-answer flashcard navigation controls."""
    c1, c2, c3, c4 = render_control_row([1, 1, 1, 1], gap="small")
    with c1:
        if render_action_button("Again", key="mbe_fc_again"):
            if len(queue) > 1:
                queue.append(queue.pop(idx))
            session_state.update({"mbe_fc_queue": queue, "mbe_fc_idx": idx % len(queue), "mbe_fc_show_answer": False})
            rerun_app()
    with c2:
        if render_primary_action_button("Got It", key="mbe_fc_got_it"):
            queue.pop(idx)
            next_idx = idx % len(queue) if queue else 0
            session_state.update({"mbe_fc_queue": queue, "mbe_fc_idx": next_idx, "mbe_fc_show_answer": False})
            rerun_app()
    with c3:
        if render_action_button("Previous", key="mbe_fc_prev"):
            session_state.update({"mbe_fc_idx": (idx - 1) % len(queue), "mbe_fc_show_answer": False})
            rerun_app()
    with c4:
        if render_action_button("Restart Deck", key="mbe_fc_restart"):
            reset_mbe_flashcard_state()
            rerun_app()


def render_mbe_flashcards_drill_page():
    all_rows = get_mbe_cards()

    render_section_heading("Flashcards Drill")
    filtered_rows, selected_source, selected_subject = render_mbe_flashcard_filters(all_rows)

    if not filtered_rows:
        render_warning("No MBE flashcards match this filter yet.")
        return

    queue = ensure_mbe_flashcard_queue(filtered_rows, selected_source, selected_subject)
    if not queue:
        render_mbe_flashcard_empty_state()
        return

    idx, card, answer_key, correct, trap = current_mbe_flashcard(queue)
    render_mbe_flashcard_prompt(card, idx, len(queue))

    if not session_state.get("mbe_fc_show_answer"):
        render_mbe_flashcard_retrieval_controls(queue, idx, answer_key)
        return

    render_mbe_flashcard_answer(card, correct, trap, answer_key)
    render_mbe_flashcard_answer_actions(queue, idx)


def _filter_mbe_card_rows(rows, *, source_filter=None, subject_filter=None, exclude_sources=None):
    from mbe_import_services import normalize_mbe_subject

    filtered = list(rows or [])
    excluded = set(exclude_sources or [])
    if excluded:
        filtered = [row for row in filtered if (row[12] or "App database") not in excluded]
    if source_filter:
        filtered = [row for row in filtered if (row[12] or "App database") == source_filter]
    if subject_filter:
        wanted = normalize_mbe_subject(subject_filter)
        filtered = [
            row for row in filtered if normalize_mbe_subject(row[3]) == wanted
        ]
    return filtered


def mbe_embed_header_css():
    """Return CSS that removes Streamlit chrome around the embedded trainer."""
    return """
    header[data-testid="stHeader"],
    div[data-testid="stToolbar"],
    div[data-testid="stDecoration"] {
        display: none !important;
        height: 0 !important;
        min-height: 0 !important;
    }
    """


def mbe_embed_streamlit_shell_css():
    """Return CSS that lets the trainer use the full Streamlit viewport."""
    return """
    .main,
    section.main,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"] {
        height: 100vh !important;
        min-height: 100vh !important;
        max-height: 100vh !important;
        overflow: hidden !important;
    }

    [data-testid="stMain"] > div,
    section.main > div,
    [data-testid="stMain"] .block-container {
        padding: 0 !important;
        margin: 0 !important;
        max-width: 100% !important;
        height: 100vh !important;
        min-height: 100vh !important;
        max-height: 100vh !important;
    }

    [data-testid="stMain"] [data-testid="stVerticalBlock"],
    [data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"] {
        padding: 0 !important;
        margin: 0 !important;
        gap: 0 !important;
        height: 100vh !important;
        min-height: 100vh !important;
        max-height: 100vh !important;
        display: flex !important;
        flex-direction: column !important;
    }
    """


def mbe_embed_iframe_css():
    """Return CSS for the iframe chain that hosts the trainer."""
    return """
    /* Trainer iframe chain grows to fill the main pane */
    div[data-testid="stElementContainer"]:has(iframe[srcdoc]) {
        flex: 1 1 auto !important;
        height: auto !important;
        min-height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow: hidden !important;
    }

    div[data-testid="stIFrame"]:has(iframe[srcdoc]),
    .stIFrame:has(iframe[srcdoc]) {
        height: 100% !important;
        min-height: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow: hidden !important;
    }

    iframe[srcdoc],
    div[data-testid="stIFrame"] iframe[srcdoc],
    .stIFrame iframe[srcdoc] {
        width: 100% !important;
        height: 100vh !important;
        min-height: 100vh !important;
        max-height: 100vh !important;
        border: 0 !important;
        display: block !important;
    }
    """


def mbe_embed_sync_bridge_css():
    """Return CSS that keeps hidden sync helpers from taking page space."""
    return """
    /* Embed CSS + hidden stats sync bridge must not steal vertical space */
    [data-testid="stMain"] div[data-testid="stElementContainer"]:has([data-testid="stMarkdown"]),
    div[data-testid="stElementContainer"]:has(iframe[title*="mbe_stats_sync"]),
    iframe[title*="mbe_stats_sync"],
    div[data-testid="stIFrame"]:has(iframe[title*="mbe_stats_sync"]) {
        flex: 0 0 auto !important;
        height: 0 !important;
        min-height: 0 !important;
        max-height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow: hidden !important;
        border: 0 !important;
    }

    div[data-testid="stElementContainer"],
    .element-container {
        margin: 0 !important;
        padding: 0 !important;
    }
    """


def build_mbe_embed_layout_css():
    """Build the full CSS payload for the embedded MBE trainer."""
    return "\n".join(
        [
            mbe_embed_header_css(),
            mbe_embed_streamlit_shell_css(),
            mbe_embed_iframe_css(),
            mbe_embed_sync_bridge_css(),
        ]
    )


def render_mbe_embed_layout_css():
    """Apply full-width Streamlit layout overrides for the embedded MBE trainer."""
    render_html_body(f"""
    <style>
    {build_mbe_embed_layout_css()}
    </style>
    """)


def mbe_trainer_html_path():
    """Return the local trainer HTML path."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "mbe_trap_trainer.html")


def render_mbe_trainer_page(*, embed_mode="drill", source_filter=None, subject_filter=None, exclude_sources=None):
    render_mbe_embed_layout_css()
    render_mbe_trainer_embed(
        mbe_trainer_html_path(),
        embed_mode=embed_mode,
        source_filter=source_filter,
        subject_filter=subject_filter,
        exclude_sources=exclude_sources,
    )


def _slim_practice_blob_for_embed(blob):
    """Strip bulky trigger-analysis payloads before injecting into the trainer iframe."""
    if not isinstance(blob, dict):
        return {}
    out = {
        "version": blob.get("version", 2),
        "errorList": blob.get("errorList") or [],
        "sessionLog": blob.get("sessionLog") or [],
        "masteredCards": blob.get("masteredCards") or [],
        "schedulerSettings": blob.get("schedulerSettings") or {},
        "uiState": blob.get("uiState") or {},
        "cardStats": {},
    }
    for key, stats in (blob.get("cardStats") or {}).items():
        if not key or not isinstance(stats, dict):
            continue
        if str(key).startswith("__"):
            out["cardStats"][key] = stats
            continue
        slim = dict(stats)
        has_practice = bool(
            slim.get("timesSeen")
            or slim.get("lastAnsweredAt")
            or slim.get("lastPracticedAt")
            or slim.get("practiceHistory")
        )
        if not has_practice:
            slim.pop("triggerAnalysis", None)
            slim.pop("triggerAnalysisVersion", None)
        if has_practice or slim.get("isMastered") or slim.get("isInErrorList"):
            slim.pop("triggerAnalysis", None)
            slim.pop("triggerAnalysisVersion", None)
            out["cardStats"][key] = slim
        elif slim.get("triggerAnalysisOverride"):
            out["cardStats"][key] = {
                "triggerAnalysisOverride": slim["triggerAnalysisOverride"]
            }
    return out


def _save_synced_mbe_practice_stats(username, sync_payload):
    """Persist trainer stats from the hidden sync bridge when the payload changes."""
    import json

    if not username or not sync_payload:
        return
    # Ignore the syncedAt timestamp so identical practice states don't trigger
    # repeated saves and rerun loops (the trainer stamps every push with "now").
    sig_payload = {k: v for k, v in sync_payload.items() if k != "syncedAt"}
    payload_sig = json.dumps(sig_payload, sort_keys=True, ensure_ascii=False)
    if session_state.get("_mbe_practice_stats_sig") == payload_sig:
        return
    save_mbe_practice_stats(username, sync_payload)
    session_state["_mbe_practice_stats_sig"] = payload_sig


def read_mbe_trainer_html(mbe_path):
    """Read the MBE trainer HTML with cached file access."""
    from pathlib import Path

    from ui_components import _read_html_embed_file

    html_path = Path(mbe_path)
    try:
        return _read_html_embed_file(str(html_path.resolve()), html_path.stat().st_mtime)
    except FileNotFoundError:
        render_error(
            "mbe_trap_trainer.html was not found next to app.py. "
            "Make sure the file is in the project folder."
        )
        return None


def _exclude_sources_tuple(exclude_sources):
    if not exclude_sources:
        return tuple()
    return tuple(sorted(exclude_sources))


def invalidate_mbe_trainer_session_cache():
    """Clear cached trainer iframe payloads after imports or deck changes."""
    for key in (
        "_mbe_iframe_doc",
        "_mbe_iframe_doc_key",
        "_mbe_practice_embed_blob",
        "_mbe_practice_stats_sig",
    ):
        session_state.pop(key, None)
    clear_cached_data()


@st.cache_data(show_spinner=False)
def _cached_mbe_embed_cards(
    source_filter,
    subject_filter,
    exclude_sources_tuple,
    card_revision,
):
    exclude_sources = set(exclude_sources_tuple) if exclude_sources_tuple else None
    db_rows = _filter_mbe_card_rows(
        get_mbe_cards(),
        source_filter=source_filter,
        subject_filter=subject_filter,
        exclude_sources=exclude_sources,
    )
    return database_rows_to_mbe_cards(db_rows)


def mbe_cards_cache_revision():
    """Return a cheap revision token that changes when the MBE deck changes."""
    row = fetch_one("SELECT COUNT(*), COALESCE(MAX(updated_at), ''), COALESCE(MAX(id), 0) FROM mbe_cards")
    if not row:
        return (0, "", 0)
    return (int(row[0] or 0), str(row[1] or ""), int(row[2] or 0))


def mbe_database_cards_payload(*, source_filter=None, subject_filter=None, exclude_sources=None):
    """Return JSON-safe database cards for the trainer iframe."""
    revision = mbe_cards_cache_revision()
    return _cached_mbe_embed_cards(
        source_filter,
        subject_filter,
        _exclude_sources_tuple(exclude_sources),
        revision,
    )


def mbe_practice_blob_payload(username):
    """Return the slim practice blob injected into the trainer iframe.

    Pinned per session: if the injected blob changed after every sync save,
    the iframe HTML would change too, remounting the trainer on each rerun
    (visible flicker + restart loop).
    """
    cache_key = "_mbe_practice_embed_blob"
    if cache_key not in session_state:
        practice_blob = get_mbe_practice_stats(username) if username else None
        session_state[cache_key] = _slim_practice_blob_for_embed(practice_blob or {})
    return session_state[cache_key]


def build_mbe_trainer_injection(cards, practice_blob, embed_mode):
    """Build the iframe bootstrap script for cards, practice stats, and start mode."""
    import json

    cards_json = json.dumps(cards, ensure_ascii=False).replace("</", "<\\/")
    practice_json = json.dumps(practice_blob, ensure_ascii=False).replace("</", "<\\/")
    return (
        "<script>"
        f"window.APP_MBE_CARDS = {cards_json};"
        "window.APP_MBE_CARD_STORE = 'database';"
        f"window.APP_TRAP_PRACTICE_BLOB = {practice_json};"
        f"window.APP_MBE_START_MODE = {json.dumps(embed_mode)};"
        "</script>"
    )


def inject_mbe_trainer_bootstrap(html, injection):
    """Insert the bootstrap script into the trainer HTML."""
    if "</head>" in html:
        return html.replace("</head>", injection + "</head>", 1)
    return injection + html


def _mbe_iframe_cache_key(embed_mode, source_filter, subject_filter, exclude_sources):
    return (
        embed_mode,
        source_filter,
        subject_filter,
        _exclude_sources_tuple(exclude_sources),
        mbe_cards_cache_revision(),
    )


def build_mbe_trainer_iframe_document(
    mbe_path,
    *,
    embed_mode="drill",
    source_filter=None,
    subject_filter=None,
    exclude_sources=None,
    username=None,
):
    """Build or reuse the injected trainer HTML for the current deck and filters."""
    cache_key = _mbe_iframe_cache_key(embed_mode, source_filter, subject_filter, exclude_sources)
    if (
        session_state.get("_mbe_iframe_doc_key") == cache_key
        and session_state.get("_mbe_iframe_doc")
    ):
        return session_state["_mbe_iframe_doc"]

    html = read_mbe_trainer_html(mbe_path)
    if html is None:
        return None

    cards = mbe_database_cards_payload(
        source_filter=source_filter,
        subject_filter=subject_filter,
        exclude_sources=exclude_sources,
    )
    practice_blob = mbe_practice_blob_payload(username)
    injection = build_mbe_trainer_injection(cards, practice_blob, embed_mode)
    document = inject_mbe_trainer_bootstrap(html, injection)
    session_state["_mbe_iframe_doc"] = document
    session_state["_mbe_iframe_doc_key"] = cache_key
    return document


def render_mbe_trainer_iframe(html):
    """Render the trainer iframe in the wide page surface."""
    # Height is overridden to 100vh via embed CSS; use a large fallback for Streamlit's wrapper.
    render_component_html(html, height=1200, scrolling=True)


def render_mbe_stats_sync_bridge(username):
    """Render hidden stats bridge and persist any payload sent from the iframe."""
    try:
        from mbe_stats_sync import render_mbe_stats_sync

        sync_payload = render_mbe_stats_sync(key="mbe_stats_sync")
        if isinstance(sync_payload, dict) and sync_payload.get("__storageDiag"):
            return
        _save_synced_mbe_practice_stats(username, sync_payload)
    except Exception:
        pass


def render_mbe_trainer_embed(
    mbe_path,
    *,
    embed_mode="drill",
    source_filter=None,
    subject_filter=None,
    exclude_sources=None,
):
    """Render the trainer with app-database MBE cards injected as the shared card store."""
    username = get_authed_user()
    document = build_mbe_trainer_iframe_document(
        mbe_path,
        embed_mode=embed_mode,
        source_filter=source_filter,
        subject_filter=subject_filter,
        exclude_sources=exclude_sources,
        username=username,
    )
    if document is None:
        return

    render_mbe_trainer_iframe(document)
    render_mbe_stats_sync_bridge(username)


# ---------------------------------------------------------------------------
# Bridge Drill - draft the MEE rule, then pick the MBE answer
# ---------------------------------------------------------------------------

_BD_LETTERS = ["A", "B", "C", "D"]
_BD_DRAFT_HINT = (
    "What is the rule that decides this question? "
    "Write it in 1-3 sentences as you would in an MEE answer."
)


def _bd_options(card):
    """Return the options list from a db card dict (handles both list and JSON string)."""
    import json as _json
    opts = card.get("options") or []
    if isinstance(opts, str):
        try:
            opts = _json.loads(opts)
        except Exception:
            opts = []
    return opts


def _bd_reset(deck, sig):
    import random
    cards = database_rows_to_mbe_cards(deck)
    random.shuffle(cards)
    session_state.update({
        "bd_queue": cards,
        "bd_idx": 0,
        "bd_phase": "draft",
        "bd_draft": "",
        "bd_pick_idx": None,
        "bd_draft_score": 3,
        "bd_results": [],
        "bd_sig": sig,
    })


def render_bridge_drill_filters(all_rows):
    source_options = ["All sources"] + sorted({row[12] or "App database" for row in all_rows})
    default_source = "qbank_misses" if "qbank_misses" in source_options else source_options[0]

    source_col, subject_col = render_control_row([1, 1], gap="medium")
    with source_col:
        source_sel = render_selectbox(
            "Source",
            source_options,
            index=source_options.index(default_source),
            key="bd_src",
        )
    source_filter = None if source_sel == "All sources" else source_sel
    source_rows = _filter_mbe_card_rows(all_rows, source_filter=source_filter)
    subject_options = ["All subjects"] + sorted({row[3] for row in source_rows if row[3]})
    with subject_col:
        subject_sel = render_selectbox("Subject", subject_options, key="bd_subj")

    subject_filter = None if subject_sel == "All subjects" else subject_sel
    deck = _filter_mbe_card_rows(all_rows, source_filter=source_filter, subject_filter=subject_filter)
    return source_sel, subject_sel, deck


def ensure_bridge_drill_queue(deck, source_sel, subject_sel):
    sig = (source_sel, subject_sel)
    if session_state.get("bd_sig") != sig or "bd_queue" not in session_state:
        _bd_reset(deck, sig)
    return session_state["bd_queue"]


def current_bridge_drill_context(queue):
    idx = session_state.get("bd_idx", 0)
    if idx >= len(queue):
        return idx, None, [], None, None, session_state.get("bd_phase", "draft")

    card = queue[idx]
    opts = _bd_options(card)
    correct_idx = next((i for i, opt in enumerate(opts) if opt.get("ok")), None)
    trap_idx = next((i for i, opt in enumerate(opts) if opt.get("trap") and not opt.get("ok")), None)
    return idx, card, opts, correct_idx, trap_idx, session_state.get("bd_phase", "draft")


def render_bridge_drill_progress(card, idx, queue):
    from html import escape as _esc

    pct = (idx / max(len(queue), 1)) * 100
    render_html_body(
        "<div style='background:#e8e7e1;border-radius:3px;height:5px;margin-bottom:8px'>"
        "<div style='background:#e85d26;height:5px;border-radius:3px;width:" + f"{pct:.1f}" + "%'></div></div>"
        "<div style='font-size:11px;color:#888;font-family:monospace;margin-bottom:12px'>"
        "Card " + str(idx + 1) + " of " + str(len(queue)) +
        " &nbsp;&middot;&nbsp; " + _esc(card.get("subj", "")).upper() +
        " / " + _esc(card.get("sub", "")).upper() + "</div>"
    )


def render_bridge_rule_recall_card(card):
    from html import escape as _esc

    render_html_body(
        "<div style='background:#1a1a1a;border-left:3px solid #e85d26;"
        "padding:20px 22px;border-radius:4px;margin-bottom:14px'>"
        "<p style='color:#fdba74;font-size:12px;font-weight:700;letter-spacing:.1em;"
        "text-transform:uppercase;margin:0 0 8px 0'>Rule Recall</p>"
        "<p style='font-weight:700;font-size:20px;color:#ffffff;margin:0;line-height:1.5'>"
        + _esc(card.get("subj", "")) + " &mdash; " + _esc(card.get("sub", "")) + "</p>"
        "<p style='color:#9ca3af;font-size:14px;margin:10px 0 0 0'>"
        "State the governing rule before seeing the question.</p></div>"
    )


def render_bridge_question_card(card):
    from html import escape as _esc

    scenario = _esc(card.get("scenario") or "")
    question = _esc(card.get("q") or "Choose the best answer.")
    scenario_html = (
        "<p style='color:#d4d0cb;font-size:16px;font-style:italic;margin:0 0 12px 0;line-height:1.6'>"
        + scenario + "</p>"
        if scenario else ""
    )
    render_html_body(
        "<div style='background:#1a1a1a;border-left:3px solid #e85d26;"
        "padding:20px 22px;border-radius:4px;margin-bottom:14px'>"
        + scenario_html +
        "<p style='font-weight:600;font-size:20px;color:#ffffff;margin:0;line-height:1.6'>"
        + question + "</p></div>"
    )


def render_bridge_drill_phase(card, idx, opts, correct_idx, trap_idx, phase):
    if phase == "draft":
        render_bridge_rule_recall_card(card)
        _bd_draft_phase(card, idx)
    elif phase == "pick":
        render_bridge_question_card(card)
        _bd_pick_phase(card, idx, opts)
    elif phase == "reveal":
        render_bridge_question_card(card)
        _bd_reveal_phase(card, idx, opts, correct_idx, trap_idx)


def render_bridge_drill_page():
    """Bridge Drill: draft the MEE rule before seeing MBE answer choices."""
    render_section_heading("Bridge Drill - Rule Draft to MBE Pick")
    render_info(
        "Step 1: Read the question and draft the governing rule as a MEE sentence. "
        "Step 2: Reveal answer choices and pick. "
        "Step 3: Score your rule draft against the correct answer."
    )

    all_rows = get_mbe_cards()
    if not all_rows:
        render_warning(
            "No MBE cards in the database yet. "
            "Import your QBank questions first via MBE Drills Question Bulk Upload."
        )
        return

    source_sel, subject_sel, deck = render_bridge_drill_filters(all_rows)
    render_metric_row([("Cards in deck", len(deck))])
    if not deck:
        render_warning("No cards match this filter.")
        return

    queue = ensure_bridge_drill_queue(deck, source_sel, subject_sel)
    idx, card, opts, correct_idx, trap_idx, phase = current_bridge_drill_context(queue)
    if card is None:
        _bd_done_screen()
        return

    render_bridge_drill_progress(card, idx, queue)
    render_bridge_drill_phase(card, idx, opts, correct_idx, trap_idx, phase)


def _bd_draft_phase(card, idx):
    from html import escape as _esc

    draft_key = "bd_t_" + str(idx)
    hint_key = "bd_hint_" + str(idx)
    hint_level = session_state.get(hint_key, 0)

    shortcut = (card.get("ru") or card.get("shortcut") or "").strip()
    plain = (card.get("plain") or card.get("plain_english") or "").strip()
    has_hints = bool(shortcut or plain)

    # Progressive building-block hints (shown above the text area)
    if has_hints and hint_level > 0:
        if hint_level >= 1 and shortcut:
            render_html_body(
                "<div style='background:#fff8f0;border-left:3px solid #e85d26;"
                "padding:10px 14px;margin-bottom:10px;border-radius:3px'>"
                "<div style='font-size:10px;font-weight:600;letter-spacing:.08em;"
                "text-transform:uppercase;color:#e85d26;margin-bottom:6px'>Building Block</div>"
                "<div style='font-size:22px;font-weight:600;color:#333;line-height:1.5'>" + _esc(shortcut) + "</div></div>"
            )
        if hint_level >= 2 and plain:
            render_html_body(
                "<div style='background:#f0f9f0;border-left:3px solid #2a7a2a;"
                "padding:10px 14px;margin-bottom:10px;border-radius:3px'>"
                "<div style='font-size:10px;font-weight:600;letter-spacing:.08em;"
                "text-transform:uppercase;color:#2a7a2a;margin-bottom:4px'>Plain English Rule</div>"
                "<div style='font-size:13px;color:#333'>" + _esc(plain) + "</div></div>"
            )

    render_text_area(
        _BD_DRAFT_HINT,
        key=draft_key,
        height=TEXTAREA_HEIGHT_XS,
    )

    # Button row: reveal | hints | skip
    b1, b2, b3 = render_control_row([1.2, 0.9, 0.7], gap="small")
    with b1:
        if render_primary_action_button("Reveal answer choices", key="bd_btn_rev"):
            session_state["bd_draft"] = session_state.get(draft_key, "")
            session_state["bd_phase"] = "pick"
            rerun_app()
    with b2:
        if has_hints:
            if hint_level == 0:
                btn_label = "Building blocks"
            elif hint_level == 1 and plain:
                btn_label = "More help"
            else:
                btn_label = "Hints shown"
            can_show_more = hint_level == 0 or (hint_level == 1 and plain)
            if can_show_more:
                if render_action_button(btn_label, key="bd_hint_btn_" + str(idx)):
                    session_state[hint_key] = hint_level + 1
                    rerun_app()
            else:
                render_action_button(btn_label, key="bd_hint_btn_" + str(idx), disabled=True)
    with b3:
        if render_action_button("Skip", key="bd_btn_skip"):
            session_state["bd_draft"] = ""
            session_state["bd_phase"] = "pick"
            rerun_app()


def _bd_pick_phase(card, idx, opts):
    from html import escape as _esc
    render_section_heading("Choose the correct answer", level=4)
    labels = [
        "(" + _BD_LETTERS[i] + ")  " + _esc(o.get("t", ""))
        for i, o in enumerate(opts)
        if i < 4
    ]
    if not labels:
        render_warning("This card has no answer options stored. Skipping.")
        if render_action_button("Next card", key="bd_skip_empty"):
            session_state.update({"bd_idx": idx + 1, "bd_phase": "draft",
                                     "bd_draft": "", "bd_pick_idx": None})
            rerun_app()
        return

    chosen = render_radio("Options", labels, index=None, key="bd_radio_" + str(idx),
                      label_visibility="collapsed")
    if chosen:
        if render_primary_action_button("Lock in answer", key="bd_btn_lock"):
            session_state["bd_pick_idx"] = labels.index(chosen)
            session_state["bd_phase"] = "reveal"
            rerun_app()
    else:
        render_caption("Select an answer above to continue.")



def _bd_reveal_rule_text(card, opts, correct_idx):
    shortcut = (card.get("ru") or card.get("shortcut") or "").strip()
    plain = (card.get("plain") or card.get("plain_english") or "").strip()
    rule_why = ""
    if correct_idx is not None and correct_idx < len(opts):
        rule_why = (opts[correct_idx].get("why") or "").strip()
    return shortcut, plain or rule_why or shortcut


def _bd_render_rule_teaching(card, opts, correct_idx):
    from html import escape as _esc

    shortcut, rule_text = _bd_reveal_rule_text(card, opts, correct_idx)
    if rule_text:
        render_html_body(
            "<div style='background:#0f2027;border-left:4px solid #f97316;"
            "padding:16px 20px;border-radius:4px;margin-bottom:14px'>"
            "<div style='font-size:10px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;"
            "color:#f97316;margin-bottom:8px'>The Rule</div>"
            "<div style='font-size:17px;font-weight:600;color:#ffffff;line-height:1.65'>"
            + _esc(rule_text) + "</div></div>"
        )
    if shortcut and shortcut != rule_text:
        render_html_body(
            "<div style='background:#f5f0fa;border-left:3px solid #6b3aa0;padding:9px 14px;margin-bottom:8px'>"
            "<div style='font-size:10px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;"
            "color:#6b3aa0;margin-bottom:3px'>Shortcut / Mnemonic</div>"
            "<div style='font-size:13px;color:#333'>" + _esc(shortcut) + "</div></div>"
        )


def _bd_render_pick_result(pick_idx, pick_correct):
    if pick_idx is None or pick_idx >= len(_BD_LETTERS):
        return
    letter = _BD_LETTERS[pick_idx]
    icon, color, verdict = ("OK", "#2a7a2a", "Correct!") if pick_correct else ("X", "#c0392b", "Incorrect")
    render_html_body(
        "<div style='font-size:14px;font-weight:700;color:" + color + ";margin-bottom:10px'>"
        + icon + " You picked (" + letter + ") - " + verdict + "</div>"
    )


def _bd_render_correct_answer(opts, correct_idx):
    from html import escape as _esc

    if correct_idx is None or correct_idx >= len(opts):
        return
    correct_opt = opts[correct_idx]
    why = _esc(correct_opt.get("why") or "")
    why_html = "<div style='font-size:13px;color:#333;margin-top:6px'>" + why + "</div>" if why else ""
    render_html_body(
        "<div style='background:#f0f9f0;border-left:3px solid #2a7a2a;padding:11px 14px;margin-bottom:8px'>"
        "<div style='font-size:10px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;"
        "color:#2a7a2a;margin-bottom:4px'>Correct answer</div>"
        "<div style='font-size:14px;font-weight:600'>(" + _BD_LETTERS[correct_idx] + ") "
        + _esc(correct_opt.get("t", "")) + "</div>" + why_html + "</div>"
    )


def _bd_render_trap_explanation(opts, trap_idx, pick_idx):
    from html import escape as _esc

    if trap_idx is None or trap_idx >= len(opts):
        return
    trap_opt = opts[trap_idx]
    trap_why = _esc(trap_opt.get("why") or "")
    if not trap_why:
        return
    header = "Why (" + _BD_LETTERS[trap_idx] + ") is the trap"
    if pick_idx == trap_idx:
        header += " - you picked this"
    render_html_body(
        "<div style='background:#fff8f5;border-left:3px solid #e85d26;padding:9px 14px;margin-bottom:8px'>"
        "<div style='font-size:10px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;"
        "color:#e85d26;margin-bottom:3px'>" + header + "</div>"
        "<div style='font-size:12px;color:#663300'>" + trap_why + "</div></div>"
    )


def _bd_render_user_draft(draft):
    from html import escape as _esc

    render_html_body(
        "<div style='margin-top:14px;margin-bottom:5px;font-size:11px;font-weight:600;"
        "letter-spacing:.08em;text-transform:uppercase;color:#555'>Your Rule Draft</div>"
    )
    if draft:
        render_html_body(
            "<div style='background:#f5f4f0;border:1px solid #d0cfc9;padding:10px 14px;"
            "border-radius:3px;font-size:13px;font-style:italic;color:#333;margin-bottom:10px'>"
            "&quot;" + _esc(draft) + "&quot;</div>"
        )
    else:
        render_html_body(
            "<div style='color:#aaa;font-size:12px;font-style:italic;margin-bottom:10px'>"
            "No rule draft - you skipped this step.</div>"
        )


def _bd_render_draft_score(idx):
    score = render_select_slider(
        "Rate your rule draft:",
        options=[1, 2, 3, 4, 5],
        value=session_state.get("bd_draft_score", 3),
        format_func=lambda value: {
            1: "1 - Off base",
            2: "2 - Partial",
            3: "3 - Decent",
            4: "4 - Solid",
            5: "5 - Perfect",
        }[value],
        key="bd_score_" + str(idx),
    )
    session_state["bd_draft_score"] = score
    return score


def _bd_save_attempt_and_advance(card, idx, correct_idx, pick_idx, pick_correct, draft, score):
    correct_letter = _BD_LETTERS[correct_idx] if correct_idx is not None and correct_idx < 4 else ""
    pick_letter = _BD_LETTERS[pick_idx] if pick_idx is not None and pick_idx < 4 else "-"
    try:
        save_bridge_attempt(
            username=get_authed_user(),
            card_uid=card.get("cardUid") or card.get("card_uid") or "",
            subject=card.get("subj", ""),
            subtopic=card.get("sub", ""),
            rule_draft=draft,
            picked_letter=pick_letter,
            correct_letter=correct_letter,
            draft_score=score,
            pick_correct=pick_correct,
            skipped_draft=not bool(draft),
        )
    except Exception:
        pass

    results = session_state.get("bd_results", [])
    results.append({
        "subj": card.get("subj", ""),
        "sub": card.get("sub", ""),
        "pick_correct": pick_correct,
        "draft_score": score,
        "skipped_draft": not bool(draft),
    })
    session_state.update({
        "bd_results": results,
        "bd_idx": idx + 1,
        "bd_phase": "draft",
        "bd_draft": "",
        "bd_pick_idx": None,
        "bd_draft_score": 3,
    })
    rerun_app()


def _bd_reveal_phase(card, idx, opts, correct_idx, trap_idx):
    pick_idx = session_state.get("bd_pick_idx")
    draft = session_state.get("bd_draft", "")
    pick_correct = pick_idx is not None and pick_idx == correct_idx

    _bd_render_rule_teaching(card, opts, correct_idx)
    _bd_render_pick_result(pick_idx, pick_correct)
    _bd_render_correct_answer(opts, correct_idx)
    _bd_render_trap_explanation(opts, trap_idx, pick_idx)
    _bd_render_user_draft(draft)
    score = _bd_render_draft_score(idx)

    if render_primary_action_button("Save & Next", key="bd_save_next"):
        _bd_save_attempt_and_advance(card, idx, correct_idx, pick_idx, pick_correct, draft, score)


def reset_rule_recall_state():
    for key in list(session_state.keys()):
        if key.startswith("rr_"):
            del session_state[key]


def render_rule_recall_filters(all_rows):
    source_options = ["All sources"] + sorted({row[12] or "App database" for row in all_rows})
    default_source = "qbank_rules" if "qbank_rules" in source_options else source_options[0]

    source_col, subject_col = render_control_row([1, 1], gap="medium")
    with source_col:
        source_sel = render_selectbox(
            "Source",
            source_options,
            index=source_options.index(default_source),
            key="rr_src",
        )

    source_filter = None if source_sel == "All sources" else source_sel
    source_rows = _filter_mbe_card_rows(all_rows, source_filter=source_filter)
    subject_options = ["All subjects"] + sorted({row[3] for row in source_rows if row[3]})
    with subject_col:
        subject_sel = render_selectbox("Subject", subject_options, key="rr_subj")

    subject_filter = None if subject_sel == "All subjects" else subject_sel
    deck = _filter_mbe_card_rows(all_rows, source_filter=source_filter, subject_filter=subject_filter)
    return source_sel, subject_sel, deck


def ensure_rule_recall_queue(deck, source_sel, subject_sel):
    import random

    sig = (source_sel, subject_sel)
    if session_state.get("rr_sig") == sig and "rr_queue" in session_state:
        return session_state["rr_queue"]

    cards = database_rows_to_mbe_cards(deck)
    random.shuffle(cards)
    session_state.update({
        "rr_sig": sig,
        "rr_queue": cards,
        "rr_idx": 0,
        "rr_show": False,
    })
    return cards


def render_rule_recall_empty_state():
    render_success("Deck complete!")
    if render_primary_action_button("Restart", key="rr_restart_empty"):
        reset_rule_recall_state()
        rerun_app()


def current_rule_recall_card(queue):
    idx = min(session_state.get("rr_idx", 0), len(queue) - 1)
    session_state["rr_idx"] = idx
    return idx, queue[idx]


def rule_recall_card_rule(card):
    shortcut = (card.get("ru") or card.get("shortcut") or "").strip()
    plain = (card.get("plain") or card.get("plain_english") or "").strip()
    correct_opt = next((opt for opt in _bd_options(card) if opt.get("ok")), {})
    rule_why = (correct_opt.get("why") or "").strip()
    return shortcut, plain or rule_why or shortcut


def render_rule_recall_building_block(shortcut):
    from html import escape as _esc

    if not shortcut:
        return ""
    return (
        "<div style='background:#fff8f0;border-left:3px solid #e85d26;"
        "padding:10px 14px;margin-top:14px;border-radius:3px'>"
        "<div style='font-size:10px;font-weight:600;letter-spacing:.08em;"
        "text-transform:uppercase;color:#e85d26;margin-bottom:6px'>Building Block</div>"
        "<div style='font-size:22px;font-weight:600;color:#333;line-height:1.5'>"
        + _esc(shortcut)
        + "</div></div>"
    )


def render_rule_recall_prompt(card, idx, queue):
    from html import escape as _esc

    shortcut, _full_rule = rule_recall_card_rule(card)
    pct = (idx / max(len(queue), 1)) * 100
    render_html_body(
        "<div style='background:#e8e7e1;border-radius:3px;height:5px;margin-bottom:8px'>"
        "<div style='background:#e85d26;height:5px;border-radius:3px;width:" + f"{pct:.1f}" + "%'></div></div>"
        "<div style='font-size:11px;color:#888;font-family:monospace;margin-bottom:12px'>"
        "Card " + str(idx + 1) + " of " + str(len(queue)) + "</div>"
    )
    render_html_body(
        "<div style='background:#1a1a1a;border-left:3px solid #e85d26;"
        "padding:20px 22px;border-radius:4px;margin-bottom:14px'>"
        "<p style='color:#fdba74;font-size:12px;font-weight:700;letter-spacing:.1em;"
        "text-transform:uppercase;margin:0 0 8px 0'>Rule Recall</p>"
        "<p style='font-weight:700;font-size:22px;color:#ffffff;margin:0;line-height:1.4'>"
        + _esc(card.get("subj", "")) + " &mdash; " + _esc(card.get("sub", "")) + "</p>"
        "<p style='color:#9ca3af;font-size:15px;margin:10px 0 0 0'>"
        "State the governing rule before revealing.</p>"
        + render_rule_recall_building_block(shortcut)
        + "</div>"
    )


def render_rule_recall_retrieval_controls(queue, idx):
    import random

    render_text_area(
        "Write the rule (1-3 sentences, MEE style)",
        key="rr_draft_" + str(idx),
        height=TEXTAREA_HEIGHT_SM,
    )
    render_caption("Retrieve first. Then reveal to compare.")
    reveal_col, shuffle_col, skip_col = render_control_row([1.2, 0.9, 0.7], gap="small")
    with reveal_col:
        if render_primary_action_button("Reveal rule", key="rr_btn_reveal"):
            session_state["rr_show"] = True
            rerun_app()
    with shuffle_col:
        if render_action_button("Shuffle deck", key="rr_btn_shuffle"):
            random.shuffle(queue)
            session_state.update({"rr_queue": queue, "rr_idx": 0, "rr_show": False})
            rerun_app()
    with skip_col:
        if render_action_button("Skip", key="rr_btn_skip"):
            if len(queue) > 1:
                queue.append(queue.pop(idx))
            session_state.update({"rr_queue": queue, "rr_idx": idx % len(queue), "rr_show": False})
            rerun_app()


def render_rule_recall_answer(card, idx):
    from html import escape as _esc

    shortcut, full_rule = rule_recall_card_rule(card)
    if full_rule:
        render_html_body(
            "<div style='background:#0f2027;border-left:4px solid #f97316;"
            "padding:18px 22px;border-radius:4px;margin-bottom:12px'>"
            "<div style='font-size:10px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;"
            "color:#f97316;margin-bottom:10px'>The Rule</div>"
            "<div style='font-size:19px;font-weight:600;color:#ffffff;line-height:1.7'>"
            + _esc(full_rule)
            + "</div></div>"
        )
    if shortcut and shortcut != full_rule:
        render_html_body(
            "<div style='background:#f5f0fa;border-left:3px solid #6b3aa0;padding:10px 14px;margin-bottom:10px'>"
            "<div style='font-size:10px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;"
            "color:#6b3aa0;margin-bottom:6px'>Shortcut / Mnemonic</div>"
            "<div style='font-size:22px;font-weight:600;color:#333;line-height:1.5'>"
            + _esc(shortcut)
            + "</div></div>"
        )

    draft = session_state.get("rr_draft_" + str(idx), "")
    if draft:
        with render_expander("Your draft", expanded=True):
            render_html_body("<div class=\"draft-answer-box\">" + _esc(draft) + "</div>")


def render_rule_recall_answer_actions(queue, idx):
    got_col, again_col, restart_col = render_control_row([1, 1, 1], gap="small")
    with got_col:
        if render_primary_action_button("Got it - next", key="rr_got_it"):
            queue.pop(idx)
            next_idx = idx % len(queue) if queue else 0
            session_state.update({"rr_queue": queue, "rr_idx": next_idx, "rr_show": False})
            rerun_app()
    with again_col:
        if render_action_button("Again later", key="rr_again"):
            if len(queue) > 1:
                queue.append(queue.pop(idx))
            session_state.update({"rr_queue": queue, "rr_idx": idx % len(queue), "rr_show": False})
            rerun_app()
    with restart_col:
        if render_action_button("Restart deck", key="rr_restart"):
            reset_rule_recall_state()
            rerun_app()


def render_rule_recall_page():
    """Rule Recall: see the building block hint, write the rule, reveal it."""
    render_section_heading("Rule Recall Drill")
    render_info(
        "See the building block hint. Write the governing rule from memory. "
        "Then reveal and compare."
    )

    all_rows = get_mbe_cards()
    if not all_rows:
        render_warning(
            "No MBE cards in the database yet. "
            "Import your QBank questions first via MBE Drills Question Bulk Upload."
        )
        return

    source_sel, subject_sel, deck = render_rule_recall_filters(all_rows)
    render_metric_row([("Cards in deck", len(deck))])
    if not deck:
        render_warning("No cards match this filter.")
        return

    queue = ensure_rule_recall_queue(deck, source_sel, subject_sel)
    if not queue:
        render_rule_recall_empty_state()
        return

    idx, card = current_rule_recall_card(queue)
    render_rule_recall_prompt(card, idx, queue)
    if session_state.get("rr_show"):
        render_rule_recall_answer(card, idx)
        render_rule_recall_answer_actions(queue, idx)
    else:
        render_rule_recall_retrieval_controls(queue, idx)


def _bd_done_screen():
    from collections import Counter
    from html import escape as _esc

    results = session_state.get("bd_results", [])
    total = len(results)
    correct = sum(1 for r in results if r.get("pick_correct"))
    avg_score = sum(r.get("draft_score", 0) for r in results) / max(total, 1)
    skipped = sum(1 for r in results if r.get("skipped_draft"))

    render_section_heading("Session Complete!")
    render_metric_row([
        ("Cards drilled", total),
        ("MBE picks correct", str(correct) + "/" + str(total) + "  (" + str(correct * 100 // max(total, 1)) + "%)"),
        ("Avg rule score", str(round(avg_score, 1)) + " / 5"),
        ("Skipped drafts", skipped),
    ])

    wrong = Counter(r["subj"] for r in results if not r.get("pick_correct"))
    if wrong:
        render_section_heading("Misses by subject", level=4)
        for subj, count in wrong.most_common():
            render_html_body(
                "<div style='font-size:13px;margin-bottom:4px'>"
                "<span style='color:#e85d26;font-weight:600'>" + str(count) + "x</span>"
                " " + _esc(subj) + "</div>"
            )

    if render_primary_action_button("New session (reshuffle)", key="bd_restart"):
        for k in [k for k in list(session_state.keys()) if k.startswith("bd_")]:
            del session_state[k]
        rerun_app()
