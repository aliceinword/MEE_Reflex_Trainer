# -*- coding: utf-8 -*-
"""MEE Issue Spotting drill — name the issue from a fact-pattern trigger."""

from __future__ import annotations

import random
from collections import Counter
from html import escape as _esc

from database import get_issue_spotting_cards
from issue_spotting_utils import MEE_ISSUE_SPOTTING_SUBJECTS
from ui_components import (
    TEXTAREA_HEIGHT_SM,
    render_action_button,
    render_caption,
    render_checkbox,
    render_control_row,
    render_expander,
    render_html_body,
    render_info,
    render_metric_row,
    render_multiselect,
    render_number_input,
    render_page_title,
    render_primary_action_button,
    render_section_heading,
    render_success,
    render_text_area,
    render_warning,
    rerun_app,
    session_state,
)


def reset_issue_spotting_state():
    """Clear all issue-spotting session keys so the next run rebuilds the deck."""
    for key in list(session_state.keys()):
        if str(key).startswith("is_"):
            del session_state[key]


def render_issue_spotting_filters():
    """Render setup controls and return (subjects, deck_size, high_yield_only)."""
    render_caption("Choose subjects, then retrieve the issue name before revealing.")
    selected = render_multiselect(
        "Subjects",
        options=list(MEE_ISSUE_SPOTTING_SUBJECTS),
        default=list(MEE_ISSUE_SPOTTING_SUBJECTS),
        key="is_subjects",
    )

    size_col, yield_col = render_control_row([1, 1], gap="medium")
    with size_col:
        deck_size = render_number_input(
            "Deck size (0 = all)",
            min_value=0,
            max_value=500,
            value=int(session_state.get("is_deck_size_value", 40) or 40),
            key="is_deck_size",
            caption="Limits how many cards are drawn after ranking by frequency.",
        )
    with yield_col:
        high_yield_only = render_checkbox(
            "High-frequency only",
            value=bool(session_state.get("is_high_yield_value", False)),
            key="is_high_yield",
            caption="Keeps attack-table cards and question-bank issues seen 2+ times.",
        )

    session_state["is_deck_size_value"] = deck_size
    session_state["is_high_yield_value"] = high_yield_only
    return selected, int(deck_size or 0), bool(high_yield_only)


def ensure_issue_spotting_queue(deck, subjects, deck_size, high_yield_only):
    """Shuffle and cache a queue whenever the filter signature changes."""
    sig = (tuple(subjects or []), int(deck_size or 0), bool(high_yield_only))
    if session_state.get("is_sig") == sig and "is_queue" in session_state:
        return session_state["is_queue"]

    cards = list(deck or [])
    random.shuffle(cards)
    session_state.update(
        {
            "is_sig": sig,
            "is_queue": cards,
            "is_idx": 0,
            "is_show": False,
            "is_completed": 0,
            "is_misses": [],
            "is_results": [],
        }
    )
    return cards


def current_issue_spotting_card(queue):
    idx = min(int(session_state.get("is_idx", 0) or 0), len(queue) - 1)
    session_state["is_idx"] = idx
    return idx, queue[idx]


def render_issue_spotting_empty_data_state():
    render_warning(
        "No issue-spotting cards for the selected subjects yet. "
        "Import the July 2026 MEE Attack Table into Attack Outline Rules, "
        "or ensure question-bank rows have trigger facts and tested issues."
    )
    render_caption(
        'Run: python scripts/import_july_2026_attack_table.py '
        '"C:\\path\\to\\July 2026 MEE Attack Table.pdf"'
    )


def render_issue_spotting_empty_state():
    results = session_state.get("is_results", [])
    completed = int(session_state.get("is_completed", 0) or 0)
    misses = session_state.get("is_misses", [])

    render_success("Deck complete!")
    render_metric_row(
        [
            ("Cards completed", completed),
            ("Marked again / miss", len(misses)),
            ("Session cards", len(results)),
        ]
    )

    miss_counts = Counter(m.get("subject") or "Unknown" for m in misses)
    if miss_counts:
        render_section_heading("Misses by subject", level=4)
        for subject, count in miss_counts.most_common():
            render_html_body(
                "<div style='font-size:13px;margin-bottom:4px'>"
                "<span style='color:#e85d26;font-weight:600'>"
                + str(count)
                + "x</span> "
                + _esc(subject)
                + "</div>"
            )

    if render_primary_action_button("Restart deck", key="is_restart_empty"):
        reset_issue_spotting_state()
        rerun_app()


def render_issue_spotting_prompt(card, idx, queue):
    pct = (idx / max(len(queue), 1)) * 100
    source_label = "Attack Table" if card.get("source") == "attack_table" else "Question Bank"
    render_html_body(
        "<div style='background:#e8e7e1;border-radius:3px;height:5px;margin-bottom:8px'>"
        "<div style='background:#e85d26;height:5px;border-radius:3px;width:"
        + f"{pct:.1f}"
        + "%'></div></div>"
        "<div style='font-size:11px;color:#888;font-family:monospace;margin-bottom:12px'>"
        "Card "
        + str(idx + 1)
        + " of "
        + str(len(queue))
        + " · "
        + _esc(source_label)
        + "</div>"
    )
    render_html_body(
        "<div style='background:#1a1a1a;border-left:3px solid #e85d26;"
        "padding:20px 22px;border-radius:4px;margin-bottom:14px'>"
        "<p style='color:#fdba74;font-size:12px;font-weight:700;letter-spacing:.1em;"
        "text-transform:uppercase;margin:0 0 8px 0'>Issue Spotting</p>"
        "<p style='font-weight:700;font-size:20px;color:#ffffff;margin:0;line-height:1.4'>"
        + _esc(card.get("subject") or "")
        + "</p>"
        "<p style='color:#9ca3af;font-size:14px;margin:10px 0 0 0'>"
        "Name the MEE issue(s) this fact pattern triggers.</p>"
        "<div style='margin-top:16px;padding:14px 16px;background:#111;border-radius:4px;"
        "border:1px solid #333'>"
        "<div style='font-size:10px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;"
        "color:#e85d26;margin-bottom:8px'>Trigger</div>"
        "<div style='font-size:18px;font-weight:500;color:#f5f5f4;line-height:1.55'>"
        + _esc(card.get("trigger") or "")
        + "</div></div></div>"
    )


def render_issue_spotting_retrieval_controls(queue, idx):
    render_text_area(
        "What issue(s) does this trigger?",
        key="is_draft_" + str(idx),
        height=TEXTAREA_HEIGHT_SM,
        placeholder="e.g., Hearsay — present sense impression; Confrontation",
    )
    render_caption("Retrieve first. Then reveal to compare.")

    reveal_col, shuffle_col, skip_col = render_control_row([1.2, 0.9, 0.7], gap="small")
    with reveal_col:
        if render_primary_action_button("Reveal answer", key="is_btn_reveal"):
            session_state["is_show"] = True
            rerun_app()
    with shuffle_col:
        if render_action_button("Shuffle deck", key="is_btn_shuffle"):
            random.shuffle(queue)
            session_state.update({"is_queue": queue, "is_idx": 0, "is_show": False})
            rerun_app()
    with skip_col:
        if render_action_button("Skip", key="is_btn_skip"):
            if len(queue) > 1:
                queue.append(queue.pop(idx))
            session_state.update(
                {"is_queue": queue, "is_idx": idx % len(queue), "is_show": False}
            )
            rerun_app()


def render_issue_spotting_answer(card, idx):
    issues = card.get("expected_issues") or []
    issues_html = "".join(
        "<li style='margin:0 0 6px 0;line-height:1.5'>" + _esc(issue) + "</li>"
        for issue in issues
    )
    if issues_html:
        render_html_body(
            "<div style='background:#0f2027;border-left:4px solid #f97316;"
            "padding:18px 22px;border-radius:4px;margin-bottom:12px'>"
            "<div style='font-size:10px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;"
            "color:#f97316;margin-bottom:10px'>Expected Issue(s)</div>"
            "<ul style='margin:0;padding-left:18px;color:#ffffff;font-size:17px;font-weight:600'>"
            + issues_html
            + "</ul></div>"
        )

    oneliner = (card.get("oneliner") or "").strip()
    if oneliner:
        render_html_body(
            "<div style='background:#fff8f0;border-left:3px solid #e85d26;"
            "padding:10px 14px;margin-bottom:10px;border-radius:3px'>"
            "<div style='font-size:10px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;"
            "color:#e85d26;margin-bottom:6px'>One-liner</div>"
            "<div style='font-size:18px;font-weight:600;color:#333;line-height:1.5'>"
            + _esc(oneliner)
            + "</div></div>"
        )

    rule_text = (card.get("rule_text") or "").strip()
    if rule_text:
        with render_expander("Full rule text", expanded=False):
            render_html_body(
                "<div style='white-space:pre-wrap;font-size:14px;line-height:1.55;color:#333'>"
                + _esc(rule_text)
                + "</div>"
            )

    draft = session_state.get("is_draft_" + str(idx), "")
    if draft:
        with render_expander("Your draft", expanded=True):
            render_html_body(
                '<div class="draft-answer-box">' + _esc(draft) + "</div>"
            )


def _record_result(card, *, missed):
    results = list(session_state.get("is_results", []))
    results.append(
        {
            "id": card.get("id"),
            "subject": card.get("subject") or "",
            "missed": bool(missed),
        }
    )
    session_state["is_results"] = results
    if missed:
        misses = list(session_state.get("is_misses", []))
        misses.append({"subject": card.get("subject") or "", "id": card.get("id")})
        session_state["is_misses"] = misses
    else:
        session_state["is_completed"] = int(session_state.get("is_completed", 0) or 0) + 1


def render_issue_spotting_answer_actions(queue, idx, card):
    got_col, again_col, restart_col = render_control_row([1, 1, 1], gap="small")
    with got_col:
        if render_primary_action_button("Got it - next", key="is_got_it"):
            _record_result(card, missed=False)
            queue.pop(idx)
            next_idx = idx % len(queue) if queue else 0
            session_state.update(
                {"is_queue": queue, "is_idx": next_idx, "is_show": False}
            )
            rerun_app()
    with again_col:
        if render_action_button("Again later", key="is_again"):
            _record_result(card, missed=True)
            if len(queue) > 1:
                queue.append(queue.pop(idx))
            session_state.update(
                {"is_queue": queue, "is_idx": idx % len(queue), "is_show": False}
            )
            rerun_app()
    with restart_col:
        if render_action_button("Restart deck", key="is_restart"):
            reset_issue_spotting_state()
            rerun_app()


def render_issue_spotting_page():
    """Issue spotting: see a trigger, name the issue, reveal and compare."""
    render_page_title(
        "MEE Issue Spotting",
        "Drill the most frequently tested MEE issues from fact-pattern triggers.",
    )
    render_info(
        "You see a trigger. Name the issue(s) from memory. Reveal to compare with the "
        "Attack Table / question-bank answer key. Self-grade with Got it or Again later."
    )

    subjects, deck_size, high_yield_only = render_issue_spotting_filters()
    if not subjects:
        render_warning("Select at least one subject to build a deck.")
        return

    limit = deck_size if deck_size > 0 else None
    deck = get_issue_spotting_cards(
        subjects,
        high_yield_only=high_yield_only,
        limit=limit,
    )
    render_metric_row(
        [
            ("Cards in deck", len(deck)),
            ("Subjects", len(subjects)),
            (
                "Sources",
                f"{sum(1 for c in deck if c.get('source') == 'attack_table')} attack / "
                f"{sum(1 for c in deck if c.get('source') == 'question_bank')} bank",
            ),
        ]
    )
    if not deck:
        render_issue_spotting_empty_data_state()
        return

    queue = ensure_issue_spotting_queue(deck, subjects, deck_size, high_yield_only)
    if not queue:
        render_issue_spotting_empty_state()
        return

    idx, card = current_issue_spotting_card(queue)
    render_issue_spotting_prompt(card, idx, queue)
    if session_state.get("is_show"):
        render_issue_spotting_answer(card, idx)
        render_issue_spotting_answer_actions(queue, idx, card)
    else:
        render_issue_spotting_retrieval_controls(queue, idx)
