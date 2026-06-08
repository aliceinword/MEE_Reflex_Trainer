# -*- coding: utf-8 -*-
"""Practice page renderers for the MEE trainer."""

import streamlit as st

from database import get_question_by_id
from practice_components import (
    LADDER_LEVELS,
    ladder_goal,
    render_answer_bank_tabs,
    render_ladder_response_input,
    render_ladder_prompt_panel,
    render_mini_drill_response_input,
    render_mini_prompt_panel,
    render_model_answer_panel,
    render_plug_play_support,
    render_save_ladder_attempt,
    render_save_mini_drill_attempt,
    training_score,
)
from question_utils import unpack_question
from ui_components import (
    question_picker,
    render_caption,
    render_compact_note,
    render_control_row,
    render_divider,
    render_error,
    render_metric_row,
    render_page_title,
    render_question_identity,
    render_reveal_control,
    render_section_heading,
    render_selectbox,
    render_slider,
    render_tab_set,
    render_text_area,
)


def render_muscle_ladder_page(compact_mode=False, reading_mode=False):
    render_page_title(
        "MEE Practice",
        "Mini drills for fast reps; Muscle Ladder for gradual essay training.",
    )

    render_compact_note(
        "Use this page for daily MEE ladder work. Use MEE Question Bank to browse stored answers, "
        "and MEE Advanced Tools only for imports or manual entry."
    )

    question_id = question_picker(active_default=True, compact=True)

    if not question_id:
        return

    q = get_question_by_id(question_id)
    if q is None:
        render_error("Question not found.")
        return

    qd = unpack_question(q)

    render_question_identity(qd)

    mini_tab, ladder_tab = render_tab_set(["Mini Drill", "MEE Muscle Ladder"])

    with mini_tab:
        render_mini_drill_tab(qd, compact_mode=compact_mode, reading_mode=reading_mode)

    with ladder_tab:
        render_ladder_tab(qd, compact_mode=compact_mode, reading_mode=reading_mode)


def render_mini_drill_tab(qd, compact_mode=False, reading_mode=False):
    render_compact_note(
        "Start with the clean question. Turn highlights on only after you try to retrieve the issue, rule, and trigger facts."
    )

    prompt_col, work_col = render_control_row([1.05, 1], gap="large")

    with prompt_col:
        render_mini_prompt_panel(qd)

    with work_col:
        render_plug_play_support(qd, expanded=True)
        combined_answer = render_mini_drill_response_input()

        mini_score = render_slider("Mini Drill score", 0, 5, 0, key=f"mini_score_{qd['id']}")

        render_save_mini_drill_attempt(qd, combined_answer, mini_score)

        mini_revealed = render_reveal_control(
            "Reveal Mini Drill Answer Bank",
            f"mini_reveal_state_{qd['id']}",
            gate_text="Reveal only after writing your mini answer.",
            key=f"mini_reveal_{qd['id']}",
        )

    if mini_revealed:
        render_divider()
        render_model_answer_panel(qd, expanded=True, title="Model Answer - compare after your attempt")
        render_answer_bank_tabs(
            qd,
            expanded=True,
            title="Rule Outline + Trigger Facts",
            include_sample_answer=False,
            include_rule_support=True,
            include_highlights=False,
            compact=compact_mode,
            reading_mode=reading_mode,
        )


def render_ladder_tab(qd, compact_mode=False, reading_mode=False):
    level = render_selectbox(
        "Choose training level",
        LADDER_LEVELS,
    )

    target_minutes, goal_text = ladder_goal(level)
    render_compact_note(f"{target_minutes}-minute target: {goal_text}")

    prompt_col, work_col = render_control_row([1, 1.15], gap="large")

    with prompt_col:
        render_ladder_prompt_panel(qd)

    with work_col:
        combined_answer = render_ladder_response_input(level)

    render_divider()

    score_col, check_col = render_control_row([1, 1], gap="large")

    with score_col:
        render_section_heading("Score and Save")
        issue_score = render_slider("Issue score", 0, 5, 0)
        rule_score = render_slider("Rule score", 0, 5, 0)
        fact_score = render_slider("Fact connection score", 0, 5, 0)

        average_score = training_score(issue_score, rule_score, fact_score)
        render_metric_row([("Training score", f"{average_score}/5")])

        missed = render_text_area(
            "What did you miss?",
            placeholder="Missed issue, element, or trigger fact.",
            height=90,
        )

        notes = render_text_area(
            "Fix note for future you",
            placeholder="One useful instruction for next time.",
            height=90,
        )

        render_save_ladder_attempt(qd, level, combined_answer, average_score, missed, notes, target_minutes)

    with check_col:
        render_section_heading("Quick Answer Check")
        ladder_revealed = render_reveal_control(
            "Reveal Model Answer + Rule Outline",
            f"ladder_reveal_{qd['id']}",
            gate_text="Reveal only after writing your answer.",
        )

        render_caption("The answer bank opens full-width below this practice panel.")

    if ladder_revealed:
        render_divider()
        render_answer_bank_tabs(
            qd,
            expanded=True,
            title="Model Answer + Rule Outline",
            include_rule_support=True,
            include_highlights=False,
            compact=compact_mode,
            reading_mode=reading_mode,
        )
