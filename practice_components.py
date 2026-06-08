# -*- coding: utf-8 -*-
"""Shared practice-mode components for MEE drills."""

import streamlit as st

from database import find_best_outline_rules_for_question, find_best_plug_play_for_call, save_attempt
from text_rendering import (
    extract_fact_pattern_only,
    get_clean_trigger_facts,
    render_attack_rule_box,
    render_plug_play_template,
    render_question_highlights_with_fallback,
    render_readable_text,
    render_sample_answer_body,
    render_tested_issues_text,
    render_trigger_rule_map,
    render_trap_warnings,
    render_trigger_facts,
)
from ui_components import render_tab_set, render_text_area


LADDER_LEVELS = [
    "Level 1 - Issue + Rule Mini Run - 7 min",
    "Level 2 - Trigger Fact Hunt - 10 min",
    "Level 3 - Mini IRAC - 15 min",
    "Level 4 - Skeleton Essay - 20 min",
    "Level 5 - Full MEE - 30 min",
]

LADDER_GOALS = {
    "Level 1": (7, "Spot issues and write rules from memory."),
    "Level 2": (10, "Connect each issue/rule to trigger facts."),
    "Level 3": (15, "Write one strong IRAC paragraph."),
    "Level 4": (20, "Outline the entire essay."),
    "Level 5": (30, "Full timed MEE simulation."),
}


def ladder_goal(level):
    """Return the target minutes and goal text for a ladder level label."""
    for prefix, goal in LADDER_GOALS.items():
        if level.startswith(prefix):
            return goal
    return LADDER_GOALS["Level 5"]


def training_score(issue_score, rule_score, fact_score):
    """Calculate the saved practice score from the three self-score sliders."""
    return round((issue_score + rule_score + fact_score) / 3)


def save_ladder_attempt(qd, level, response_text, score, missed, notes, minutes_spent):
    """Save one MEE Muscle Ladder attempt using the shared database contract."""
    save_attempt(
        qd["id"],
        level,
        response_text,
        score,
        missed,
        notes,
        minutes_spent=minutes_spent,
    )


def render_ladder_response_input(level):
    """Render the writing prompt for a selected Muscle Ladder level."""
    st.markdown(f"### {level.split(' - ')[0]} Work")

    if level.startswith("Level 1"):
        user_issues = render_text_area(
            "Step A - What issues do you see?",
            placeholder="List each legal issue raised by this call.",
            height=120,
        )
        user_rules = render_text_area(
            "Step B - Write the rules from memory",
            placeholder="Write the governing test, elements, or standard.",
            height=140,
        )
        user_facts = render_text_area(
            "Optional - Which facts triggered those issues?",
            placeholder="Quote or summarize the facts that connect to each rule element.",
            height=90,
        )

        return f"""
ISSUES:
{user_issues}

RULES:
{user_rules}

TRIGGER FACTS:
{user_facts}
"""

    if level.startswith("Level 2"):
        return render_text_area(
            "For each issue, write: Issue -> Rule -> Trigger Facts",
            placeholder=(
                "Issue 1: ___\nRule: ___\nTrigger facts: ___\n\n"
                "Issue 2: ___\nRule: ___\nTrigger facts: ___"
            ),
            height=280,
        )

    if level.startswith("Level 3"):
        return render_text_area(
            "Write ONE strong IRAC paragraph",
            placeholder=(
                "Issue: Whether ___\nRule: Under ___\nApplication: Here, ___ because ___\n"
                "Counterargument: However, ___\nConclusion: Therefore, ___"
            ),
            height=280,
        )

    if level.startswith("Level 4"):
        return render_text_area(
            "Outline the full essay. Short bullets only.",
            placeholder=(
                "Call 1:\n- Issue:\n- Rule:\n- Facts:\n- Conclusion:\n\n"
                "Call 2:\n- Issue:\n- Rule:\n- Facts:\n- Conclusion:"
            ),
            height=300,
        )

    return render_text_area("Write the full timed essay", height=360)


def render_mini_drill_response_input():
    """Render the compact issue-rule-fact answer builder for Mini Drill."""
    st.markdown("### Mini Drill Work")
    issue = render_text_area(
        "Your issue",
        placeholder="Whether the facts satisfy the doctrine tested by this call.",
        height=95,
    )
    rule = render_text_area(
        "Your rule",
        placeholder="State the test, elements, standard, and important exception.",
        height=120,
    )
    trigger_facts = render_text_area(
        "Your trigger facts",
        placeholder="Which exact facts triggered this issue or rule?",
        height=105,
    )
    conclusion = render_text_area(
        "Your micro-conclusion",
        placeholder="Therefore, likely yes/no because...",
        height=85,
    )

    return f"""
ISSUE:
{issue}

RULE:
{rule}

TRIGGER FACTS:
{trigger_facts}

MICRO-CONCLUSION:
{conclusion}
"""


def render_plug_play_support(qd, *, expanded=True):
    """Render matched Plug & Play templates for active answer drafting."""
    plug_matches = find_best_plug_play_for_call(
        qd.get("subject", ""),
        qd.get("call_of_question", ""),
        qd.get("question_text", ""),
        qd.get("tested_issues", ""),
        limit=2,
    )

    with st.expander("Plug & Play Template - use while answering", expanded=expanded):
        if not plug_matches:
            st.info("No Plug & Play template matched this question yet.")
            return

        for template in plug_matches:
            render_plug_play_template(template)


def render_model_answer_panel(qd, *, expanded=True, title="Model Answer"):
    """Render the model answer as a prominent full-width reveal panel."""
    with st.expander(title, expanded=expanded):
        st.markdown("### Model Answer")
        render_sample_answer_body(qd)


def render_answer_bank_tabs(
    qd,
    expanded=False,
    title="Answer Bank - open after retrieval",
    include_sample_answer=True,
    include_rule_support=True,
    include_highlights=True,
    compact=False,
    reading_mode=False,
):
    """Render the shared post-retrieval answer bank for practice surfaces."""
    with st.expander(title, expanded=expanded):
        st.markdown(f"### {title}")
        tab_names = []
        if include_sample_answer:
            tab_names.append("Sample Answer")

        tab_names.extend(["Rules + Issues", "Trigger Facts", "Traps"])
        if include_rule_support:
            tab_names.append("Rule Support")

        tabs = render_tab_set(tab_names)
        tab_index = 0

        if include_sample_answer:
            with tabs[tab_index]:
                render_sample_answer_body(qd)
            tab_index += 1

        with tabs[tab_index]:
            render_tested_issues_text("Tested Issues", qd.get("tested_issues", ""))
            render_readable_text("Rules", qd.get("rules", ""), compact=compact)
        tab_index += 1

        with tabs[tab_index]:
            render_trigger_facts("Trigger Facts", get_clean_trigger_facts(qd), qd)
            if include_highlights:
                render_trigger_rule_map("Trigger Identifier Map", qd)
                fact_only = extract_fact_pattern_only(
                    qd.get("question_text", ""),
                    qd.get("call_of_question", ""),
                )
                render_question_highlights_with_fallback(
                    "Fact Pattern with Trigger Facts Highlighted",
                    qd,
                    text=fact_only,
                    show_explanations=True,
                )
        tab_index += 1

        with tabs[tab_index]:
            render_trap_warnings("Trap Warnings", qd.get("traps", ""))
        tab_index += 1

        if include_rule_support:
            with tabs[tab_index]:
                outline_matches = find_best_outline_rules_for_question(
                    qd.get("subject", ""),
                    qd.get("tested_issues", ""),
                    qd.get("rules", ""),
                    qd.get("traps", ""),
                    limit=3,
                )
                plug_matches = find_best_plug_play_for_call(
                    qd.get("subject", ""),
                    qd.get("call_of_question", ""),
                    qd.get("question_text", ""),
                    qd.get("tested_issues", ""),
                    limit=2,
                )

                if outline_matches:
                    st.markdown("#### Attack Outline Rules")
                    for rule in outline_matches:
                        render_attack_rule_box(rule, reading_mode=reading_mode)

                if plug_matches:
                    st.markdown("#### Plug & Play Templates")
                    for template in plug_matches:
                        render_plug_play_template(template)

                if not outline_matches and not plug_matches:
                    st.info("No extra rule support matched this question yet.")
