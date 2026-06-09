# -*- coding: utf-8 -*-
"""MBE page renderer for the separate multiple-choice trainer."""

import os

import streamlit as st

from app_state import get_authed_user
from database import (
    count_mbe_cards,
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
    render_caption,
    render_compact_note,
    render_control_row,
    render_download_button,
    render_error,
    render_file_uploader,
    render_html_body,
    render_import_preview,
    render_info,
    render_metric_row,
    render_primary_action_button,
    render_section_heading,
    render_success,
    render_warning,
)


def render_mbe_bulk_upload_page():
    render_section_heading("MBE Drills Question Bulk Upload")
    render_compact_note(
        "Use these templates for MBE trap-trainer questions. Uploaded cards are saved in the main app database, not only in this browser."
    )
    render_metric_row([("MBE cards in app database", count_mbe_cards())])

    csv_bytes = read_mbe_template_bytes("MBE_trap_trainer_template.csv")
    xlsx_bytes = read_mbe_template_bytes("MBE_trap_trainer_template_1.xlsx")

    template_col, upload_col = render_control_row([0.9, 1.35], gap="large")

    with template_col:
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

    with upload_col:
        render_section_heading("Upload Check", level=4)
        uploaded_file = render_file_uploader(
            "Upload completed MBE bulk file",
            type=["csv", "xlsx", "xls"],
            key="mbe_bulk_question_upload",
            caption="CSV works offline. Excel files may need openpyxl installed.",
        )

        if uploaded_file is None:
            render_info("Upload a completed template to preview rows and catch missing columns before importing.")
            return

        try:
            df = read_mbe_bulk_upload(uploaded_file)
        except Exception as exc:
            render_error(str(exc))
            return

        missing = missing_mbe_template_columns(df.columns)
        extra = extra_mbe_template_columns(df.columns)
        render_metric_row(mbe_upload_metrics(df, missing, extra))

        if missing:
            render_error("Missing required columns: " + ", ".join(missing))
        else:
            render_success("Column check passed. This file matches the MBE bulk template.")

        if extra:
            render_warning("Extra columns will be ignored by the trainer: " + ", ".join(extra))

        render_import_preview(
            [],
            mbe_upload_preview_rows(df),
            empty_message="No previewable rows found.",
        )

        cards, row_errors = mbe_cards_from_dataframe(df, source_name=uploaded_file.name or "MBE bulk upload")
        if row_errors:
            render_warning("Some rows are not importable: " + " ".join(row_errors[:5]))
            if len(row_errors) > 5:
                render_caption(f"{len(row_errors) - 5} more row issue(s) not shown.")

        if not missing and cards:
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
                st.cache_data.clear()
        elif not missing:
            render_warning("No valid MBE cards found to import.")


def render_mbe_drills_page():
    render_mbe_trainer_page(embed_mode="drill", exclude_sources={"adaptibar_rules"})


def render_mbe_flashcards_drill_page():
    from html import escape as _esc
    import random

    all_rows = get_mbe_cards()
    source_options = ["All sources"] + sorted({row[12] or "App database" for row in all_rows})
    default_source = "adaptibar_rules" if "adaptibar_rules" in source_options else source_options[0]

    render_section_heading("Flashcards Drill")
    control_col, metric_col = render_control_row([1.5, 1], gap="medium")
    with control_col:
        selected_source = st.selectbox(
            "Flashcard source",
            source_options,
            index=source_options.index(default_source),
            key="mbe_flashcards_source_filter",
        )
        source_filter = None if selected_source == "All sources" else selected_source
        source_rows = _filter_mbe_card_rows(all_rows, source_filter=source_filter)
        subject_options = ["All subjects"] + sorted({row[3] for row in source_rows if row[3]})
        selected_subject = st.selectbox(
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

    if not filtered_rows:
        render_warning("No MBE flashcards match this filter yet.")
        return

    sig = ("flashcards", selected_source, selected_subject, len(filtered_rows))
    if st.session_state.get("mbe_fc_sig") != sig or "mbe_fc_queue" not in st.session_state:
        cards = database_rows_to_mbe_cards(filtered_rows)
        random.shuffle(cards)
        st.session_state.update(
            {
                "mbe_fc_sig": sig,
                "mbe_fc_queue": cards,
                "mbe_fc_idx": 0,
                "mbe_fc_show_answer": False,
            }
        )

    queue = st.session_state["mbe_fc_queue"]
    if not queue:
        render_success("Deck complete. No cards left in this filtered session.")
        if render_primary_action_button("Restart Deck", key="mbe_fc_restart_empty"):
            for key in list(st.session_state.keys()):
                if key.startswith("mbe_fc_"):
                    del st.session_state[key]
            st.rerun()
        return
    idx = min(st.session_state.get("mbe_fc_idx", 0), max(len(queue) - 1, 0))
    st.session_state["mbe_fc_idx"] = idx
    card = queue[idx]
    card_uid = card.get("cardUid") or card.get("id") or str(idx)
    answer_key = f"mbe_fc_answer_{card_uid}"
    options = card.get("options") or []
    correct = next((option for option in options if option.get("ok")), {})
    trap = next((option for option in options if option.get("trap") and not option.get("ok")), {})

    progress = round(((idx + 1) / max(len(queue), 1)) * 100)
    render_html_body(
        f"""
        <div style="height:6px;background:#dbeafe;border-radius:999px;margin:12px 0 10px;">
            <div style="width:{progress}%;height:6px;background:#4169e1;border-radius:999px;"></div>
        </div>
        <div style="font-size:0.9rem;color:#64748b;margin-bottom:12px;">
            Card {idx + 1} of {len(queue)}
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

    if not st.session_state.get("mbe_fc_show_answer"):
        answer = st.text_area(
            "Write the rule from memory",
            key=answer_key,
            height=130,
            placeholder="State the rule, elements, exception, or shortcut before revealing.",
        )
        render_caption("Retrieve first. Then compare with the rule card.")
        c1, c2, c3 = render_control_row([1, 1, 1], gap="small")
        with c1:
            if render_primary_action_button("Show Answer", key="mbe_fc_show"):
                st.session_state["mbe_fc_show_answer"] = True
                st.rerun()
        with c2:
            if st.button("Shuffle Deck", key="mbe_fc_shuffle"):
                random.shuffle(queue)
                st.session_state.update({"mbe_fc_queue": queue, "mbe_fc_idx": 0, "mbe_fc_show_answer": False})
                st.rerun()
        with c3:
            if st.button("Next Card", key="mbe_fc_next_unseen"):
                if len(queue) > 1:
                    queue.append(queue.pop(idx))
                st.session_state.update(
                    {
                        "mbe_fc_queue": queue,
                        "mbe_fc_idx": idx % len(queue),
                        "mbe_fc_show_answer": False,
                    }
                )
                st.rerun()
        return

    rule_text = correct.get("why") or card.get("ru") or ""
    plain_text = card.get("plain") or ""
    shortcut = card.get("ru") or ""
    correct_text = correct.get("t") or ""
    trap_text = trap.get("why") or ""
    trap_choice = trap.get("t") or ""
    user_answer = st.session_state.get(answer_key, "")

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
        with st.expander("Your retrieval answer", expanded=False):
            st.write(user_answer)

    c1, c2, c3, c4 = render_control_row([1, 1, 1, 1], gap="small")
    with c1:
        if st.button("Again", key="mbe_fc_again"):
            if len(queue) > 1:
                queue.append(queue.pop(idx))
            st.session_state.update({"mbe_fc_queue": queue, "mbe_fc_idx": idx % len(queue), "mbe_fc_show_answer": False})
            st.rerun()
    with c2:
        if render_primary_action_button("Got It", key="mbe_fc_got_it"):
            queue.pop(idx)
            next_idx = idx % len(queue) if queue else 0
            st.session_state.update({"mbe_fc_queue": queue, "mbe_fc_idx": next_idx, "mbe_fc_show_answer": False})
            st.rerun()
    with c3:
        if st.button("Previous", key="mbe_fc_prev"):
            st.session_state.update({"mbe_fc_idx": (idx - 1) % len(queue), "mbe_fc_show_answer": False})
            st.rerun()
    with c4:
        if st.button("Restart Deck", key="mbe_fc_restart"):
            for key in list(st.session_state.keys()):
                if key.startswith("mbe_fc_"):
                    del st.session_state[key]
            st.rerun()


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


def render_mbe_trainer_page(*, embed_mode="drill", source_filter=None, subject_filter=None, exclude_sources=None):
    render_html_body("""
    <style>
    .block-container {
        padding: 0 !important;
        margin: 0 !important;
        max-width: 100% !important;
        height: auto !important;
        overflow: visible !important;
    }

    header[data-testid="stHeader"],
    div[data-testid="stToolbar"],
    div[data-testid="stDecoration"] {
        display: none !important;
        height: 0 !important;
        min-height: 0 !important;
    }

    .full-page-embed {
        width: 100% !important;
        height: auto !important;
        min-height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow: visible !important;
    }

    div[data-testid="stElementContainer"]:has(iframe),
    div[data-testid="stIFrame"],
    .stIFrame,
    .full-page-embed iframe,
    iframe[title*="streamlit"],
    iframe[title*="component"],
    iframe[srcdoc] {
        height: 4200px !important;
        min-height: 4200px !important;
        max-height: none !important;
        overflow: hidden !important;
    }

    iframe[title*="streamlit"],
    iframe[title*="component"],
    iframe[srcdoc],
    div[data-testid="stIFrame"] iframe,
    .stIFrame iframe {
        width: 100% !important;
        border: 0 !important;
        display: block !important;
    }

    div[data-testid="stElementContainer"],
    .element-container {
        margin: 0 !important;
        padding: 0 !important;
    }

    .main,
    section.main,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"] {
        overflow-x: hidden !important;
        overflow-y: auto !important;
    }

    [data-testid="stMain"] > div,
    section.main > div {
        padding-left: 0 !important;
        padding-right: 0 !important;
        max-width: 100% !important;
    }
    </style>
    """)
    mbe_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mbe_trap_trainer.html")
    render_mbe_trainer_embed(
        mbe_path,
        embed_mode=embed_mode,
        source_filter=source_filter,
        subject_filter=subject_filter,
        exclude_sources=exclude_sources,
    )


def _save_synced_mbe_practice_stats(username, sync_payload):
    """Persist trainer stats from the hidden sync bridge when the payload changes."""
    import json

    if not username or not sync_payload:
        return
    payload_sig = json.dumps(sync_payload, sort_keys=True, ensure_ascii=False)
    if st.session_state.get("_mbe_practice_stats_sig") == payload_sig:
        return
    save_mbe_practice_stats(username, sync_payload)
    st.session_state["_mbe_practice_stats_sig"] = payload_sig


def render_mbe_trainer_embed(
    mbe_path,
    *,
    embed_mode="drill",
    source_filter=None,
    subject_filter=None,
    exclude_sources=None,
):
    """Render the trainer with app-database MBE cards injected as the shared card store."""
    import json
    from pathlib import Path

    import streamlit.components.v1 as components

    from ui_components import _read_html_embed_file

    username = get_authed_user()

    html_path = Path(mbe_path)
    try:
        html = _read_html_embed_file(str(html_path.resolve()), html_path.stat().st_mtime)
    except FileNotFoundError:
        render_error(
            "mbe_trap_trainer.html was not found next to app.py. "
            "Make sure the file is in the project folder."
        )
        return

    db_rows = _filter_mbe_card_rows(
        get_mbe_cards(),
        source_filter=source_filter,
        subject_filter=subject_filter,
        exclude_sources=exclude_sources,
    )
    db_cards = database_rows_to_mbe_cards(db_rows)
    cards_json = json.dumps(db_cards, ensure_ascii=False).replace("</", "<\\/")
    practice_blob = get_mbe_practice_stats(username) if username else None
    practice_json = json.dumps(practice_blob or {}, ensure_ascii=False).replace("</", "<\\/")
    injection = (
        "<script>"
        f"window.APP_MBE_CARDS = {cards_json};"
        "window.APP_MBE_CARD_STORE = 'database';"
        f"window.APP_TRAP_PRACTICE_BLOB = {practice_json};"
        f"window.APP_MBE_START_MODE = {json.dumps(embed_mode)};"
        "</script>"
    )
    if "</head>" in html:
        html = html.replace("</head>", injection + "</head>", 1)
    else:
        html = injection + html

    render_html_body('<div class="full-page-embed" aria-hidden="true"></div>')
    components.html(html, height=4200, scrolling=False)

    # Mount the stats sync bridge only after the trainer iframe has rendered once.
    # Running it before the iframe can trigger Streamlit rerun loops and block the page.
    if st.session_state.get("_mbe_trainer_visible"):
        try:
            from mbe_stats_sync import render_mbe_stats_sync

            sync_payload = render_mbe_stats_sync(key="mbe_stats_sync")
            _save_synced_mbe_practice_stats(username, sync_payload)
        except Exception:
            pass
    st.session_state["_mbe_trainer_visible"] = True


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
    st.session_state.update({
        "bd_queue": cards,
        "bd_idx": 0,
        "bd_phase": "draft",
        "bd_draft": "",
        "bd_pick_idx": None,
        "bd_draft_score": 3,
        "bd_results": [],
        "bd_sig": sig,
    })


def render_bridge_drill_page():
    """Bridge Drill: draft the MEE rule before seeing MBE answer choices."""
    from html import escape as _esc

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
            "Import your AdaptiBar questions first via MBE Drills Question Bulk Upload."
        )
        return

    source_options = ["All sources"] + sorted({row[12] or "App database" for row in all_rows})
    default_src = "adaptibar_misses" if "adaptibar_misses" in source_options else source_options[0]

    fc, sc = render_control_row([1, 1], gap="medium")
    with fc:
        source_sel = st.selectbox(
            "Source", source_options,
            index=source_options.index(default_src),
            key="bd_src",
        )
    src_filter = None if source_sel == "All sources" else source_sel
    src_rows = _filter_mbe_card_rows(all_rows, source_filter=src_filter)
    subj_opts = ["All subjects"] + sorted({r[3] for r in src_rows if r[3]})
    with sc:
        subj_sel = st.selectbox("Subject", subj_opts, key="bd_subj")
    subj_filter = None if subj_sel == "All subjects" else subj_sel

    deck = _filter_mbe_card_rows(all_rows, source_filter=src_filter, subject_filter=subj_filter)
    render_metric_row([("Cards in deck", len(deck))])

    if not deck:
        render_warning("No cards match this filter.")
        return

    sig = (source_sel, subj_sel)
    if st.session_state.get("bd_sig") != sig or "bd_queue" not in st.session_state:
        _bd_reset(deck, sig)

    queue = st.session_state["bd_queue"]
    idx = st.session_state.get("bd_idx", 0)
    phase = st.session_state.get("bd_phase", "draft")

    if idx >= len(queue):
        _bd_done_screen()
        return

    card = queue[idx]
    opts = _bd_options(card)
    correct_idx = next((i for i, o in enumerate(opts) if o.get("ok")), None)
    trap_idx = next((i for i, o in enumerate(opts) if o.get("trap") and not o.get("ok")), None)

    # Progress bar + card label
    pct = (idx / max(len(queue), 1)) * 100
    render_html_body(
        "<div style='background:#e8e7e1;border-radius:3px;height:5px;margin-bottom:8px'>"
        "<div style='background:#e85d26;height:5px;border-radius:3px;width:" + f"{pct:.1f}" + "%'></div></div>"
        "<div style='font-size:11px;color:#888;font-family:monospace;margin-bottom:12px'>"
        "Card " + str(idx + 1) + " of " + str(len(queue)) +
        " &nbsp;&middot;&nbsp; " + _esc(card.get('subj', '')).upper() +
        " / " + _esc(card.get('sub', '')).upper() + "</div>"
    )

    if phase == "draft":
        # Draft phase: only show subject/subtopic — no question yet
        subj = _esc(card.get("subj", ""))
        sub = _esc(card.get("sub", ""))
        render_html_body(
            "<div style='background:#1a1a1a;border-left:3px solid #e85d26;"
            "padding:20px 22px;border-radius:4px;margin-bottom:14px'>"
            "<p style='color:#fdba74;font-size:12px;font-weight:700;letter-spacing:.1em;"
            "text-transform:uppercase;margin:0 0 8px 0'>Rule Recall</p>"
            "<p style='font-weight:700;font-size:20px;color:#ffffff;margin:0;line-height:1.5'>"
            + subj + " &mdash; " + sub + "</p>"
            "<p style='color:#9ca3af;font-size:14px;margin:10px 0 0 0'>"
            "State the governing rule before seeing the question.</p></div>"
        )
        _bd_draft_phase(card, idx)
    elif phase == "pick":
        # Pick phase: now reveal the question
        scenario = _esc(card.get("scenario") or "")
        question = _esc(card.get("q") or "Choose the best answer.")
        sc_html = (
            "<p style='color:#d4d0cb;font-size:16px;font-style:italic;margin:0 0 12px 0;line-height:1.6'>"
            + scenario + "</p>"
            if scenario else ""
        )
        render_html_body(
            "<div style='background:#1a1a1a;border-left:3px solid #e85d26;"
            "padding:20px 22px;border-radius:4px;margin-bottom:14px'>"
            + sc_html +
            "<p style='font-weight:600;font-size:20px;color:#ffffff;margin:0;line-height:1.6'>"
            + question + "</p></div>"
        )
        _bd_pick_phase(card, idx, opts)
    elif phase == "reveal":
        scenario = _esc(card.get("scenario") or "")
        question = _esc(card.get("q") or "Choose the best answer.")
        sc_html = (
            "<p style='color:#d4d0cb;font-size:16px;font-style:italic;margin:0 0 12px 0;line-height:1.6'>"
            + scenario + "</p>"
            if scenario else ""
        )
        render_html_body(
            "<div style='background:#1a1a1a;border-left:3px solid #e85d26;"
            "padding:20px 22px;border-radius:4px;margin-bottom:14px'>"
            + sc_html +
            "<p style='font-weight:600;font-size:20px;color:#ffffff;margin:0;line-height:1.6'>"
            + question + "</p></div>"
        )
        _bd_reveal_phase(card, idx, opts, correct_idx, trap_idx)


def _bd_draft_phase(card, idx):
    from html import escape as _esc

    draft_key = "bd_t_" + str(idx)
    hint_key = "bd_hint_" + str(idx)
    hint_level = st.session_state.get(hint_key, 0)

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

    st.text_area(
        _BD_DRAFT_HINT,
        key=draft_key,
        height=100,
    )

    # Button row: reveal | hints | skip
    b1, b2, b3 = render_control_row([1.2, 0.9, 0.7], gap="small")
    with b1:
        if render_primary_action_button("Reveal answer choices", key="bd_btn_rev"):
            st.session_state["bd_draft"] = st.session_state.get(draft_key, "")
            st.session_state["bd_phase"] = "pick"
            st.rerun()
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
                if st.button(btn_label, key="bd_hint_btn_" + str(idx)):
                    st.session_state[hint_key] = hint_level + 1
                    st.rerun()
            else:
                st.button(btn_label, key="bd_hint_btn_" + str(idx), disabled=True)
    with b3:
        if st.button("Skip", key="bd_btn_skip"):
            st.session_state["bd_draft"] = ""
            st.session_state["bd_phase"] = "pick"
            st.rerun()


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
        if st.button("Next card", key="bd_skip_empty"):
            st.session_state.update({"bd_idx": idx + 1, "bd_phase": "draft",
                                     "bd_draft": "", "bd_pick_idx": None})
            st.rerun()
        return

    chosen = st.radio("Options", labels, index=None, key="bd_radio_" + str(idx),
                      label_visibility="collapsed")
    if chosen:
        if render_primary_action_button("Lock in answer", key="bd_btn_lock"):
            st.session_state["bd_pick_idx"] = labels.index(chosen)
            st.session_state["bd_phase"] = "reveal"
            st.rerun()
    else:
        render_caption("Select an answer above to continue.")


def _bd_reveal_phase(card, idx, opts, correct_idx, trap_idx):
    from html import escape as _esc
    pick_idx = st.session_state.get("bd_pick_idx")
    draft = st.session_state.get("bd_draft", "")
    pick_correct = pick_idx is not None and pick_idx == correct_idx

    # ── THE RULE (shown first — this is the teaching moment) ──────────────
    plain = _esc(card.get("plain") or card.get("plain_english") or "")
    shortcut = _esc(card.get("ru") or card.get("shortcut") or "")
    rule_why = ""
    if correct_idx is not None and correct_idx < len(opts):
        rule_why = _esc(opts[correct_idx].get("why") or "")

    rule_text = plain or rule_why or shortcut
    if rule_text:
        render_html_body(
            "<div style='background:#0f2027;border-left:4px solid #f97316;"
            "padding:16px 20px;border-radius:4px;margin-bottom:14px'>"
            "<div style='font-size:10px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;"
            "color:#f97316;margin-bottom:8px'>The Rule</div>"
            "<div style='font-size:17px;font-weight:600;color:#ffffff;line-height:1.65'>"
            + rule_text + "</div></div>"
        )
    if shortcut and shortcut != rule_text:
        render_html_body(
            "<div style='background:#f5f0fa;border-left:3px solid #6b3aa0;padding:9px 14px;margin-bottom:8px'>"
            "<div style='font-size:10px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;"
            "color:#6b3aa0;margin-bottom:3px'>Shortcut / Mnemonic</div>"
            "<div style='font-size:13px;color:#333'>" + shortcut + "</div></div>"
        )

    # ── Result banner + correct answer ─────────────────────────────────────
    if pick_idx is not None and pick_idx < len(_BD_LETTERS):
        letter = _BD_LETTERS[pick_idx]
        if pick_correct:
            icon, color, verdict = "✓", "#2a7a2a", "Correct!"
        else:
            icon, color, verdict = "✗", "#c0392b", "Incorrect"
        render_html_body(
            "<div style='font-size:14px;font-weight:700;color:" + color + ";margin-bottom:10px'>"
            + icon + " You picked (" + letter + ") — " + verdict + "</div>"
        )

    if correct_idx is not None and correct_idx < len(opts):
        co = opts[correct_idx]
        why = _esc(co.get("why") or "")
        why_html = "<div style='font-size:13px;color:#333;margin-top:6px'>" + why + "</div>" if why else ""
        render_html_body(
            "<div style='background:#f0f9f0;border-left:3px solid #2a7a2a;padding:11px 14px;margin-bottom:8px'>"
            "<div style='font-size:10px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;"
            "color:#2a7a2a;margin-bottom:4px'>Correct answer</div>"
            "<div style='font-size:14px;font-weight:600'>"
            "(" + _BD_LETTERS[correct_idx] + ") " + _esc(co.get("t", "")) + "</div>"
            + why_html + "</div>"
        )

    # Trap explanation
    if trap_idx is not None and trap_idx < len(opts):
        to = opts[trap_idx]
        trap_why = _esc(to.get("why") or "")
        if trap_why:
            picked_trap = pick_idx == trap_idx
            header = (
                "Why (" + _BD_LETTERS[trap_idx] + ") is the trap"
                + (" - you picked this" if picked_trap else "")
            )
            render_html_body(
                "<div style='background:#fff8f5;border-left:3px solid #e85d26;padding:9px 14px;margin-bottom:8px'>"
                "<div style='font-size:10px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;"
                "color:#e85d26;margin-bottom:3px'>" + header + "</div>"
                "<div style='font-size:12px;color:#663300'>" + trap_why + "</div></div>"
            )

    # User's rule draft
    render_html_body(
        "<div style='margin-top:14px;margin-bottom:5px;font-size:11px;font-weight:600;"
        "letter-spacing:.08em;text-transform:uppercase;color:#555'>Your Rule Draft</div>"
    )
    if draft:
        render_html_body(
            "<div style='background:#f5f4f0;border:1px solid #d0cfc9;padding:10px 14px;"
            "border-radius:3px;font-size:13px;font-style:italic;color:#333;margin-bottom:10px'>"
            "\"" + _esc(draft) + "\"</div>"
        )
    else:
        render_html_body(
            "<div style='color:#aaa;font-size:12px;font-style:italic;margin-bottom:10px'>"
            "No rule draft - you skipped this step.</div>"
        )

    # Self-score
    score = st.select_slider(
        "Rate your rule draft:",
        options=[1, 2, 3, 4, 5],
        value=st.session_state.get("bd_draft_score", 3),
        format_func=lambda x: {
            1: "1 - Off base", 2: "2 - Partial", 3: "3 - Decent",
            4: "4 - Solid", 5: "5 - Perfect"
        }[x],
        key="bd_score_" + str(idx),
    )
    st.session_state["bd_draft_score"] = score

    if render_primary_action_button("Save & Next", key="bd_save_next"):
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
            pass  # never block navigation on a save error

        results = st.session_state.get("bd_results", [])
        results.append({
            "subj": card.get("subj", ""),
            "sub": card.get("sub", ""),
            "pick_correct": pick_correct,
            "draft_score": score,
            "skipped_draft": not bool(draft),
        })
        st.session_state.update({
            "bd_results": results,
            "bd_idx": idx + 1,
            "bd_phase": "draft",
            "bd_draft": "",
            "bd_pick_idx": None,
            "bd_draft_score": 3,
        })
        st.rerun()


def render_rule_recall_page():
    """Rule Recall: see the building block hint, write the rule, reveal it."""
    from html import escape as _esc
    import random

    render_section_heading("Rule Recall Drill")
    render_info(
        "See the building block hint. Write the governing rule from memory. "
        "Then reveal and compare."
    )

    all_rows = get_mbe_cards()
    if not all_rows:
        render_warning(
            "No MBE cards in the database yet. "
            "Import your AdaptiBar questions first via MBE Drills Question Bulk Upload."
        )
        return

    source_options = ["All sources"] + sorted({row[12] or "App database" for row in all_rows})
    default_src = "adaptibar_rules" if "adaptibar_rules" in source_options else source_options[0]

    fc, sc = render_control_row([1, 1], gap="medium")
    with fc:
        source_sel = st.selectbox(
            "Source", source_options,
            index=source_options.index(default_src),
            key="rr_src",
        )
    src_filter = None if source_sel == "All sources" else source_sel
    src_rows = _filter_mbe_card_rows(all_rows, source_filter=src_filter)
    subj_opts = ["All subjects"] + sorted({r[3] for r in src_rows if r[3]})
    with sc:
        subj_sel = st.selectbox("Subject", subj_opts, key="rr_subj")
    subj_filter = None if subj_sel == "All subjects" else subj_sel

    deck = _filter_mbe_card_rows(all_rows, source_filter=src_filter, subject_filter=subj_filter)
    render_metric_row([("Cards in deck", len(deck))])

    if not deck:
        render_warning("No cards match this filter.")
        return

    sig = (source_sel, subj_sel)
    if st.session_state.get("rr_sig") != sig or "rr_queue" not in st.session_state:
        cards = database_rows_to_mbe_cards(deck)
        random.shuffle(cards)
        st.session_state.update({
            "rr_sig": sig,
            "rr_queue": cards,
            "rr_idx": 0,
            "rr_show": False,
        })

    queue = st.session_state["rr_queue"]
    if not queue:
        render_success("Deck complete!")
        if render_primary_action_button("Restart", key="rr_restart_empty"):
            for k in list(st.session_state.keys()):
                if k.startswith("rr_"):
                    del st.session_state[k]
            st.rerun()
        return

    idx = min(st.session_state.get("rr_idx", 0), len(queue) - 1)
    st.session_state["rr_idx"] = idx
    card = queue[idx]

    shortcut = (card.get("ru") or card.get("shortcut") or "").strip()
    plain = (card.get("plain") or card.get("plain_english") or "").strip()
    opts = _bd_options(card)
    correct_opt = next((o for o in opts if o.get("ok")), {})
    rule_why = (correct_opt.get("why") or "").strip()
    full_rule = plain or rule_why or shortcut

    # Progress bar
    pct = (idx / max(len(queue), 1)) * 100
    render_html_body(
        "<div style='background:#e8e7e1;border-radius:3px;height:5px;margin-bottom:8px'>"
        "<div style='background:#e85d26;height:5px;border-radius:3px;width:" + f"{pct:.1f}" + "%'></div></div>"
        "<div style='font-size:11px;color:#888;font-family:monospace;margin-bottom:12px'>"
        "Card " + str(idx + 1) + " of " + str(len(queue)) + "</div>"
    )

    # Card header — subject / subtopic
    subj = _esc(card.get("subj", ""))
    sub = _esc(card.get("sub", ""))
    render_html_body(
        "<div style='background:#1a1a1a;border-left:3px solid #e85d26;"
        "padding:20px 22px;border-radius:4px;margin-bottom:14px'>"
        "<p style='color:#fdba74;font-size:12px;font-weight:700;letter-spacing:.1em;"
        "text-transform:uppercase;margin:0 0 8px 0'>Rule Recall</p>"
        "<p style='font-weight:700;font-size:22px;color:#ffffff;margin:0;line-height:1.4'>"
        + subj + " &mdash; " + sub + "</p>"
        "<p style='color:#9ca3af;font-size:15px;margin:10px 0 0 0'>"
        "State the governing rule before revealing.</p>"
        + (
            "<div style='background:#fff8f0;border-left:3px solid #e85d26;"
            "padding:10px 14px;margin-top:14px;border-radius:3px'>"
            "<div style='font-size:10px;font-weight:600;letter-spacing:.08em;"
            "text-transform:uppercase;color:#e85d26;margin-bottom:6px'>Building Block</div>"
            "<div style='font-size:22px;font-weight:600;color:#333;line-height:1.5'>" + _esc(shortcut) + "</div></div>"
            if shortcut else ""
        )
        + "</div>"
    )

    if not st.session_state.get("rr_show"):
        st.text_area(
            "Write the rule (1–3 sentences, MEE style)",
            key="rr_draft_" + str(idx),
            height=110,
        )
        render_caption("Retrieve first. Then reveal to compare.")
        c1, c2, c3 = render_control_row([1.2, 0.9, 0.7], gap="small")
        with c1:
            if render_primary_action_button("Reveal rule", key="rr_btn_reveal"):
                st.session_state["rr_show"] = True
                st.rerun()
        with c2:
            if st.button("Shuffle deck", key="rr_btn_shuffle"):
                random.shuffle(queue)
                st.session_state.update({"rr_queue": queue, "rr_idx": 0, "rr_show": False})
                st.rerun()
        with c3:
            if st.button("Skip", key="rr_btn_skip"):
                if len(queue) > 1:
                    queue.append(queue.pop(idx))
                st.session_state.update({"rr_queue": queue, "rr_idx": idx % len(queue), "rr_show": False})
                st.rerun()
    else:
        # Show the rule
        if full_rule:
            render_html_body(
                "<div style='background:#0f2027;border-left:4px solid #f97316;"
                "padding:18px 22px;border-radius:4px;margin-bottom:12px'>"
                "<div style='font-size:10px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;"
                "color:#f97316;margin-bottom:10px'>The Rule</div>"
                "<div style='font-size:19px;font-weight:600;color:#ffffff;line-height:1.7'>"
                + _esc(full_rule) + "</div></div>"
            )
        if shortcut and shortcut != full_rule:
            render_html_body(
                "<div style='background:#f5f0fa;border-left:3px solid #6b3aa0;padding:10px 14px;margin-bottom:10px'>"
                "<div style='font-size:10px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;"
                "color:#6b3aa0;margin-bottom:6px'>Shortcut / Mnemonic</div>"
                "<div style='font-size:22px;font-weight:600;color:#333;line-height:1.5'>" + _esc(shortcut) + "</div></div>"
            )

        draft = st.session_state.get("rr_draft_" + str(idx), "")
        if draft:
            with st.expander("Your draft", expanded=True):
                st.write(draft)

        c1, c2, c3 = render_control_row([1, 1, 1], gap="small")
        with c1:
            if render_primary_action_button("Got it — next", key="rr_got_it"):
                queue.pop(idx)
                next_idx = idx % len(queue) if queue else 0
                st.session_state.update({"rr_queue": queue, "rr_idx": next_idx, "rr_show": False})
                st.rerun()
        with c2:
            if st.button("Again later", key="rr_again"):
                if len(queue) > 1:
                    queue.append(queue.pop(idx))
                st.session_state.update({"rr_queue": queue, "rr_idx": idx % len(queue), "rr_show": False})
                st.rerun()
        with c3:
            if st.button("Restart deck", key="rr_restart"):
                for k in list(st.session_state.keys()):
                    if k.startswith("rr_"):
                        del st.session_state[k]
                st.rerun()


def _bd_done_screen():
    from collections import Counter
    from html import escape as _esc

    results = st.session_state.get("bd_results", [])
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
        for k in [k for k in list(st.session_state.keys()) if k.startswith("bd_")]:
            del st.session_state[k]
        st.rerun()
