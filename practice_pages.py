# -*- coding: utf-8 -*-
"""Practice page renderers for the MEE trainer."""

import streamlit as st

from database import get_question_by_id
from practice_components import (
    LADDER_LEVELS,
    ladder_goal,
    render_answer_bank_tabs,
    render_ladder_response_input,
    render_mini_drill_response_input,
    render_model_answer_panel,
    render_plug_play_support,
    save_ladder_attempt,
    training_score,
)
from question_utils import unpack_question
from text_rendering import (
    extract_fact_pattern_only,
    render_call_text,
    render_fact_pattern_text,
    render_question_highlights_with_fallback,
)
from ui_components import (
    question_picker,
    render_compact_note,
    render_control_row,
    render_metric_row,
    render_page_title,
    render_tab_set,
    render_text_area,
    reveal_gate_box,
)


def render_muscle_ladder_page(compact_mode=False, reading_mode=False):
    render_page_title(
        "MEE Practice",
        "Mini drills for fast reps; Muscle Ladder for gradual essay training.",
    )

    render_compact_note(
        "Use this page for daily MEE ladder work. Use Question Bank to browse stored answers, "
        "and Advanced Tools only for imports or manual entry."
    )

    question_id = question_picker(active_default=True, compact=True)

    if not question_id:
        return

    q = get_question_by_id(question_id)
    if q is None:
        st.error("Question not found.")
        return

    qd = unpack_question(q)

    st.caption(
        f"{qd['exam_name']} Q{qd['question_number']} | {qd['subject']} | "
        f"Priority {qd['priority'] or '-'}"
    )

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
    fact_only = extract_fact_pattern_only(qd["question_text"], qd["call_of_question"])

    with prompt_col:
        with st.expander("Call of the Question", expanded=True):
            render_call_text("Call of the Question", qd["call_of_question"])

        highlight_facts = st.checkbox(
            "Highlight relevant triggering facts",
            value=False,
            key=f"mini_highlight_{qd['id']}",
        )
        st.caption("Leave this off for retrieval. Turn it on when you are ready to compare.")

        if highlight_facts:
            render_question_highlights_with_fallback(
                "Fact Pattern with Trigger Facts Highlighted",
                qd,
                text=fact_only,
                show_explanations=True,
            )
        else:
            render_fact_pattern_text("Fact Pattern", fact_only)

    with work_col:
        render_plug_play_support(qd, expanded=True)
        combined_answer = render_mini_drill_response_input()

        mini_score = st.slider("Mini Drill score", 0, 5, 0, key=f"mini_score_{qd['id']}")

        if st.button("Save Mini Drill Attempt", use_container_width=True, key=f"mini_save_{qd['id']}"):
            save_ladder_attempt(
                qd,
                "Mini Drill",
                combined_answer,
                mini_score,
                "",
                "",
                8,
            )
            st.success("Mini Drill saved.")

        reveal_gate_box("Reveal only after writing your mini answer.")
        if st.button("Reveal Mini Drill Answer Bank", use_container_width=True, key=f"mini_reveal_{qd['id']}"):
            st.session_state[f"mini_reveal_state_{qd['id']}"] = True

    if st.session_state.get(f"mini_reveal_state_{qd['id']}", False):
        st.divider()
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
    level = st.selectbox(
        "Choose training level",
        LADDER_LEVELS,
    )

    target_minutes, goal_text = ladder_goal(level)
    render_compact_note(f"{target_minutes}-minute target: {goal_text}")

    prompt_col, work_col = render_control_row([1, 1.15], gap="large")

    with prompt_col:
        with st.expander("Call of the Question", expanded=True):
            render_call_text("Call of the Question", qd["call_of_question"])

        with st.expander("Fact Pattern", expanded=True):
            fact_only = extract_fact_pattern_only(qd["question_text"], qd["call_of_question"])
            render_fact_pattern_text("Fact Pattern", fact_only)

    with work_col:
        combined_answer = render_ladder_response_input(level)

    st.divider()

    score_col, check_col = render_control_row([1, 1], gap="large")

    with score_col:
        st.markdown("### Score and Save")
        issue_score = st.slider("Issue score", 0, 5, 0)
        rule_score = st.slider("Rule score", 0, 5, 0)
        fact_score = st.slider("Fact connection score", 0, 5, 0)

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

        if st.button("Save Muscle Ladder Attempt", use_container_width=True):
            save_ladder_attempt(
                qd,
                level,
                combined_answer,
                average_score,
                missed,
                notes,
                target_minutes,
            )

            st.success("Saved. This question is now scheduled for review based on your score.")

    with check_col:
        st.markdown("### Quick Answer Check")
        reveal_gate_box("Reveal only after writing your answer.")

        if st.button("Reveal Model Answer + Rule Outline", use_container_width=True):
            st.session_state[f"ladder_reveal_{qd['id']}"] = True

        st.caption("The answer bank opens full-width below this practice panel.")

    if st.session_state.get(f"ladder_reveal_{qd['id']}", False):
        st.divider()
        render_answer_bank_tabs(
            qd,
            expanded=True,
            title="Model Answer + Rule Outline",
            include_rule_support=True,
            include_highlights=False,
            compact=compact_mode,
            reading_mode=reading_mode,
        )
