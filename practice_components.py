# -*- coding: utf-8 -*-
"""Shared practice-mode components for MEE drills."""

from app_state import get_state, set_state
from database import find_best_outline_rules_for_question, find_best_plug_play_for_call, save_attempt
from text_rendering import (
    extract_fact_pattern_only,
    get_clean_trigger_facts,
    render_attack_rule_box,
    render_call_text,
    render_fact_pattern_text,
    render_plug_play_template,
    render_question_highlights_with_fallback,
    render_readable_text,
    render_sample_answer_body,
    render_tested_issues_text,
    render_trigger_rule_map,
    render_trap_warnings,
    render_trigger_facts,
)
from ui_components import (
    TEXTAREA_HEIGHT_LG,
    TEXTAREA_HEIGHT_SM,
    TEXTAREA_HEIGHT_XL,
    TEXTAREA_HEIGHT_XS,
    render_action_button,
    render_caption,
    render_checkbox,
    render_divider,
    render_expander,
    render_info,
    render_section_heading,
    render_success,
    render_tab_set,
    render_text_area,
)


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


def render_save_attempt_button(
    label,
    qd,
    level,
    response_text,
    score,
    missed,
    notes,
    minutes_spent,
    *,
    success_message,
    key=None,
):
    """Render a consistent practice-save button and success message."""
    if render_action_button(label, key=key):
        save_ladder_attempt(
            qd,
            level,
            response_text,
            score,
            missed,
            notes,
            minutes_spent,
        )
        render_success(success_message)
        return True

    return False


def render_save_mini_drill_attempt(qd, response_text, score):
    """Render the Mini Drill save action using the shared attempt contract."""
    return render_save_attempt_button(
        "Save Mini Drill Attempt",
        qd,
        "Mini Drill",
        response_text,
        score,
        "",
        "",
        8,
        success_message="Mini Drill saved.",
        key=f"mini_save_{qd['id']}",
    )


def render_save_ladder_attempt(qd, level, response_text, score, missed, notes, minutes_spent):
    """Render the Muscle Ladder save action using the shared attempt contract."""
    return render_save_attempt_button(
        "Save Muscle Ladder Attempt",
        qd,
        level,
        response_text,
        score,
        missed,
        notes,
        minutes_spent,
        success_message="Saved. This question is now scheduled for review based on your score.",
    )


def render_call_prompt(qd, *, expanded=True):
    """Render the call of the question in the shared practice prompt style."""
    with render_expander("Call of the Question", expanded=expanded):
        render_call_text("Call of the Question", qd.get("call_of_question", ""))


def render_fact_prompt(qd, *, highlighted=False, show_explanations=True, expanded=True, in_expander=True):
    """Render the cleaned fact pattern, optionally with trigger highlighting."""
    fact_only = extract_fact_pattern_only(
        qd.get("question_text", ""),
        qd.get("call_of_question", ""),
    )

    if highlighted:
        render_question_highlights_with_fallback(
            "Fact Pattern with Trigger Facts Highlighted",
            qd,
            text=fact_only,
            show_explanations=show_explanations,
        )
        return

    if not in_expander:
        render_fact_pattern_text("Fact Pattern", fact_only)
        return

    with render_expander("Fact Pattern", expanded=expanded):
        render_fact_pattern_text("Fact Pattern", fact_only)


def render_mini_prompt_panel(qd):
    """Render Mini Drill prompt controls and return whether facts are highlighted."""
    render_call_prompt(qd)
    highlight_facts = render_checkbox(
        "Highlight relevant triggering facts",
        value=False,
        key=f"mini_highlight_{qd['id']}",
    )
    render_caption("Leave this off for retrieval. Turn it on when you are ready to compare.")
    render_fact_prompt(qd, highlighted=highlight_facts, in_expander=False)
    return highlight_facts


def render_ladder_prompt_panel(qd):
    """Render the standard Muscle Ladder prompt panel."""
    render_call_prompt(qd)
    render_fact_prompt(qd)


def render_ladder_level_1_response():
    """Render Level 1 issue/rule/fact retrieval fields."""
    user_issues = render_text_area(
        "Step A - What issues do you see?",
        placeholder="List each legal issue raised by this call.",
        height=TEXTAREA_HEIGHT_SM,
    )
    user_rules = render_text_area(
        "Step B - Write the rules from memory",
        placeholder="Write the governing test, elements, or standard.",
        height=TEXTAREA_HEIGHT_SM,
    )
    user_facts = render_text_area(
        "Optional - Which facts triggered those issues?",
        placeholder="Quote or summarize the facts that connect to each rule element.",
        height=TEXTAREA_HEIGHT_XS,
    )

    return f"""
ISSUES:
{user_issues}

RULES:
{user_rules}

TRIGGER FACTS:
{user_facts}
"""


def render_ladder_level_2_response():
    """Render Level 2 trigger-fact hunt field."""
    return render_text_area(
        "For each issue, write: Issue -> Rule -> Trigger Facts",
        placeholder=(
            "Issue 1: ___\nRule: ___\nTrigger facts: ___\n\n"
            "Issue 2: ___\nRule: ___\nTrigger facts: ___"
        ),
        height=TEXTAREA_HEIGHT_LG,
    )


def render_ladder_level_3_response():
    """Render Level 3 mini-IRAC field."""
    return render_text_area(
        "Write ONE strong IRAC paragraph",
        placeholder=(
            "Issue: Whether ___\nRule: Under ___\nApplication: Here, ___ because ___\n"
            "Counterargument: However, ___\nConclusion: Therefore, ___"
        ),
        height=TEXTAREA_HEIGHT_LG,
    )


def render_ladder_level_4_response():
    """Render Level 4 skeleton essay field."""
    return render_text_area(
        "Outline the full essay. Short bullets only.",
        placeholder=(
            "Call 1:\n- Issue:\n- Rule:\n- Facts:\n- Conclusion:\n\n"
            "Call 2:\n- Issue:\n- Rule:\n- Facts:\n- Conclusion:"
        ),
        height=TEXTAREA_HEIGHT_LG,
    )


def render_ladder_level_5_response():
    """Render Level 5 full timed essay field."""
    return render_text_area("Write the full timed essay", height=TEXTAREA_HEIGHT_XL)


LADDER_RESPONSE_RENDERERS = {
    "Level 1": render_ladder_level_1_response,
    "Level 2": render_ladder_level_2_response,
    "Level 3": render_ladder_level_3_response,
    "Level 4": render_ladder_level_4_response,
    "Level 5": render_ladder_level_5_response,
}


def render_ladder_response_input(level):
    """Render the writing prompt for a selected Muscle Ladder level."""
    render_section_heading(f"{level.split(' - ')[0]} Work")
    for prefix, renderer in LADDER_RESPONSE_RENDERERS.items():
        if level.startswith(prefix):
            return renderer()
    return render_ladder_level_5_response()


def render_mini_drill_response_input():
    """Render the compact issue-rule-fact answer builder for Mini Drill."""
    render_section_heading("Mini Drill Work")
    issue = render_text_area(
        "Your issue",
        placeholder="Whether the facts satisfy the doctrine tested by this call.",
        height=TEXTAREA_HEIGHT_XS,
    )
    rule = render_text_area(
        "Your rule",
        placeholder="State the test, elements, standard, and important exception.",
        height=TEXTAREA_HEIGHT_SM,
    )
    trigger_facts = render_text_area(
        "Your trigger facts",
        placeholder="Which exact facts triggered this issue or rule?",
        height=TEXTAREA_HEIGHT_XS,
    )
    conclusion = render_text_area(
        "Your micro-conclusion",
        placeholder="Therefore, likely yes/no because...",
        height=TEXTAREA_HEIGHT_XS,
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


def _cached_plug_play_matches(qd, *, limit=2):
    cache_key = f"_plug_play_{qd.get('id')}_{limit}"
    cached = get_state(cache_key)
    if cached is not None:
        return cached
    matches = find_best_plug_play_for_call(
        qd.get("subject", ""),
        qd.get("call_of_question", ""),
        qd.get("question_text", ""),
        qd.get("tested_issues", ""),
        limit=limit,
    )
    set_state(cache_key, matches)
    return matches


def _cached_outline_rule_matches(qd, *, limit=3):
    cache_key = f"_outline_rules_{qd.get('id')}_{limit}"
    cached = get_state(cache_key)
    if cached is not None:
        return cached
    matches = find_best_outline_rules_for_question(
        qd.get("subject", ""),
        qd.get("tested_issues", ""),
        qd.get("rules", ""),
        qd.get("traps", ""),
        limit=limit,
    )
    set_state(cache_key, matches)
    return matches


def render_plug_play_support(qd, *, expanded=True):
    """Render matched Plug & Play templates for active answer drafting."""
    plug_matches = _cached_plug_play_matches(qd, limit=2)

    with render_expander("Plug & Play Template - use while answering", expanded=expanded):
        if not plug_matches:
            render_info("No Plug & Play template matched this question yet.")
            return

        for template in plug_matches:
            render_plug_play_template(template)


def render_model_answer_panel(qd, *, expanded=True, title="Model Answer"):
    """Render the model answer as a prominent full-width reveal panel."""
    with render_expander(title, expanded=expanded):
        render_section_heading("Model Answer")
        render_sample_answer_body(qd)


def render_practice_section_break():
    """Render the standard separator between practice work and review controls."""
    render_divider()


def answer_bank_tab_names(include_sample_answer=True, include_rule_support=True):
    """Return the tab labels for the shared answer bank."""
    names = []
    if include_sample_answer:
        names.append("Sample Answer")
    names.extend(["Rules + Issues", "Trigger Facts", "Traps"])
    if include_rule_support:
        names.append("Rule Support")
    return names


def render_rules_issues_tab(qd, *, compact=False):
    """Render the rules and tested issues answer-bank tab."""
    render_tested_issues_text("Tested Issues", qd.get("tested_issues", ""))
    render_readable_text("Rules", qd.get("rules", ""), compact=compact)


def render_trigger_facts_tab(qd, *, include_highlights=True):
    """Render trigger facts and optional fact-pattern highlights."""
    render_trigger_facts("Trigger Facts", get_clean_trigger_facts(qd), qd)
    if not include_highlights:
        return
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


def render_traps_tab(qd):
    """Render trap warnings for the answer bank."""
    render_trap_warnings("Trap Warnings", qd.get("traps", ""))


def render_rule_support_tab(qd, *, reading_mode=False):
    """Render attack-outline and Plug & Play support for the answer bank."""
    outline_matches = _cached_outline_rule_matches(qd, limit=3)
    plug_matches = _cached_plug_play_matches(qd, limit=2)

    if outline_matches:
        render_section_heading("Attack Outline Rules", level=4)
        for rule in outline_matches:
            render_attack_rule_box(rule, reading_mode=reading_mode)

    if plug_matches:
        render_section_heading("Plug & Play Templates", level=4)
        for template in plug_matches:
            render_plug_play_template(template)

    if not outline_matches and not plug_matches:
        render_info("No extra rule support matched this question yet.")


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
    with render_expander(title, expanded=expanded):
        render_section_heading(title)
        tab_names = answer_bank_tab_names(include_sample_answer, include_rule_support)
        tabs = render_tab_set(tab_names)
        tab_index = 0

        if include_sample_answer:
            with tabs[tab_index]:
                render_sample_answer_body(qd)
            tab_index += 1

        with tabs[tab_index]:
            render_rules_issues_tab(qd, compact=compact)
        tab_index += 1

        with tabs[tab_index]:
            render_trigger_facts_tab(qd, include_highlights=include_highlights)
        tab_index += 1

        with tabs[tab_index]:
            render_traps_tab(qd)
        tab_index += 1

        if include_rule_support:
            with tabs[tab_index]:
                render_rule_support_tab(qd, reading_mode=reading_mode)


def render_practice_review_panel(
    qd,
    *,
    bank_title,
    model_answer_title=None,
    include_sample_answer=True,
    include_rule_support=True,
    include_highlights=False,
    compact=False,
    reading_mode=False,
):
    """Render the standard post-retrieval review area for practice drills."""
    render_divider()
    if model_answer_title:
        render_model_answer_panel(qd, expanded=True, title=model_answer_title)

    render_answer_bank_tabs(
        qd,
        expanded=True,
        title=bank_title,
        include_sample_answer=include_sample_answer,
        include_rule_support=include_rule_support,
        include_highlights=include_highlights,
        compact=compact,
        reading_mode=reading_mode,
    )
