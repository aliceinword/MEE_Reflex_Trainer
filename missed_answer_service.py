# -*- coding: utf-8 -*-
"""Record missed answers and build Daily Error Sheet reports."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from html import escape
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from daily_error_config import get_daily_error_config
from database import (
    get_missed_answer_events_for_date,
    get_user_notification_settings,
    lookup_mbe_card_by_correct_answer,
    lookup_mbe_card_row,
    record_missed_answer_event,
)

_BUILTIN_CARD_INDEX = None


@dataclass
class MissedQuestionItem:
    question_prompt: str
    user_answer: str
    correct_answer: str
    explanation: str
    retry_link: str
    source: str
    event_at: str


@dataclass
class MissedRuleGroup:
    rule_label: str
    topic: str
    subtopic: str
    correct_rule_text: str
    missed_rule_text: str
    count: int = 0
    questions: List[MissedQuestionItem] = field(default_factory=list)


@dataclass
class DailyErrorReport:
    username: str
    report_date: str
    total_missed: int
    unique_rules: int
    top_topic: str
    rule_groups: List[MissedRuleGroup]


def _parse_event_datetime(event_at: str) -> datetime:
    raw = (event_at or "").strip()
    if not raw:
        return datetime.now()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(raw, fmt)
            except ValueError:
                continue
    return datetime.now()


def event_date_for_timestamp(event_at: str, timezone_name: str) -> str:
    """Map an ISO/local timestamp to a YYYY-MM-DD date in the user's timezone."""
    dt = _parse_event_datetime(event_at)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    try:
        tz = ZoneInfo(timezone_name or "America/New_York")
    except Exception:
        tz = ZoneInfo("America/New_York")
    return dt.astimezone(tz).strftime("%Y-%m-%d")


def retry_link_for_source(source: str, question_id: Optional[str] = None) -> str:
    base = get_daily_error_config()["app_base_url"]
    routes = {
        "mbe_drill": "MBE Drills",
        "bridge_drill": "Bridge Drill",
        "mee_ladder": "MEE Muscle Ladder",
        "mee_mini_drill": "MEE Muscle Ladder",
    }
    page = routes.get(source, "Dashboard")
    link = f"{base}/?nav={page.replace(' ', '%20')}"
    if question_id and source.startswith("mee"):
        link += f"&question_id={question_id}"
    return link


def _rule_group_key(row) -> str:
    topic = row[5] or ""
    subtopic = row[6] or ""
    rule_label = row[8] or subtopic or topic or "General"
    correct_rule = row[10] or ""
    return f"{topic}|{subtopic}|{rule_label}|{correct_rule}"


def _trainer_lookup_keys(*values) -> List[str]:
    """Collect unique trainer lookup keys from stored ids and event keys."""
    keys: List[str] = []
    for raw in values:
        key = str(raw or "").strip()
        if key and key not in keys:
            keys.append(key)
    return keys


def _lookup_details_by_correct_answer(correct_answer: str) -> Dict[str, Any]:
    """Fallback: find a card whose correct option text matches the stored answer."""
    answer = (correct_answer or "").strip()
    if len(answer) < 20:
        return {}

    needle = answer.lower()
    for card in _builtin_card_index().values():
        for opt in card.get("options") or []:
            if opt.get("ok") and needle in (opt.get("t") or "").lower():
                return _details_from_builtin_card(card)

    row = lookup_mbe_card_by_correct_answer(answer)
    if row:
        return _details_from_db_row(row)
    return {}


def _question_prompt_for_event_row(row) -> str:
    """Return the best available question prompt, enriching legacy rows when needed."""
    prompt = (row[11] or "").strip()
    if prompt and prompt not in {"(no prompt)", "Fact pattern unavailable"}:
        return prompt

    lookup_keys = _trainer_lookup_keys(row[2])
    event_key = row[16] or ""
    if event_key.startswith(("mbe:", "bridge:")):
        parts = event_key.split(":", 2)
        if len(parts) > 1 and parts[1]:
            lookup_keys = _trainer_lookup_keys(*lookup_keys, parts[1])

    for lookup_key in lookup_keys:
        details = resolve_mbe_card_details(lookup_key)
        enriched = (details.get("question_prompt") or "").strip()
        if enriched:
            return enriched

    details = _lookup_details_by_correct_answer(row[13] or "")
    enriched = (details.get("question_prompt") or "").strip()
    if enriched:
        return enriched

    return prompt


def build_daily_error_report(username: str, report_date: str) -> DailyErrorReport:
    """Build a grouped daily error report for one user and calendar date."""
    rows = get_missed_answer_events_for_date(username, report_date)
    grouped: Dict[str, MissedRuleGroup] = {}
    topic_counts: Dict[str, int] = defaultdict(int)

    for row in rows:
        key = _rule_group_key(row)
        topic = row[5] or "General"
        topic_counts[topic] += 1
        if key not in grouped:
            grouped[key] = MissedRuleGroup(
                rule_label=row[8] or row[6] or row[5] or "General",
                topic=row[5] or "",
                subtopic=row[6] or "",
                correct_rule_text=row[10] or "",
                missed_rule_text=row[9] or "",
            )
        group = grouped[key]
        group.count += 1
        group.questions.append(
            MissedQuestionItem(
                question_prompt=_question_prompt_for_event_row(row),
                user_answer=row[12] or "",
                correct_answer=row[13] or "",
                explanation=row[14] or "",
                retry_link=row[15] or retry_link_for_source(row[4], row[2]),
                source=row[4] or "",
                event_at=row[17] or "",
            )
        )

    rule_groups = sorted(
        grouped.values(),
        key=lambda g: (-g.count, g.topic, g.rule_label),
    )
    top_topic = ""
    if topic_counts:
        top_topic = max(topic_counts.items(), key=lambda item: item[1])[0]

    return DailyErrorReport(
        username=username,
        report_date=report_date,
        total_missed=len(rows),
        unique_rules=len(rule_groups),
        top_topic=top_topic,
        rule_groups=rule_groups,
    )


def render_daily_error_report_text(report: DailyErrorReport) -> str:
    lines = [
        f"Daily Error Sheet for {report.report_date}",
        "",
        "Summary:",
        f"- Total missed questions: {report.total_missed}",
        f"- Unique rules missed: {report.unique_rules}",
        f"- Top missed topic: {report.top_topic or 'N/A'}",
        "",
        "Missed Rules:",
        "",
    ]

    for index, group in enumerate(report.rule_groups, start=1):
        header = group.rule_label
        if group.topic:
            header = f"{group.topic}" + (f" — {group.subtopic}" if group.subtopic else "")
        lines.extend(
            [
                f"{index}. {header}",
                "Correct rule:",
                group.correct_rule_text or "(not recorded)",
                "",
                f"Missed {group.count} time(s).",
                "",
                "Questions missed:",
            ]
        )
        for item in group.questions:
            lines.extend(
                [
                    f"- Question: {item.question_prompt or 'Fact pattern unavailable'}",
                    f"  Your answer: {item.user_answer or '(none)'}",
                    f"  Correct answer: {item.correct_answer or '(none)'}",
                    f"  Explanation: {item.explanation or '(none)'}",
                    f"  Retry link: {item.retry_link}",
                    "",
                ]
            )
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def render_daily_error_report_html(report: DailyErrorReport) -> str:
    summary_rows = [
        ("Total missed questions", str(report.total_missed)),
        ("Unique rules missed", str(report.unique_rules)),
        ("Top missed topic", escape(report.top_topic or "N/A")),
    ]
    summary_html = "".join(
        f"<tr><td style='padding:4px 12px 4px 0;font-weight:600'>{escape(label)}</td>"
        f"<td style='padding:4px 0'>{value}</td></tr>"
        for label, value in summary_rows
    )

    sections = []
    for index, group in enumerate(report.rule_groups, start=1):
        header = escape(group.rule_label)
        if group.topic:
            header = escape(group.topic)
            if group.subtopic:
                header += f" &mdash; {escape(group.subtopic)}"

        question_blocks = []
        for item in group.questions:
            question_blocks.append(
                "<li style='margin-bottom:14px'>"
                f"<div><strong>Question:</strong> {escape(item.question_prompt or 'Fact pattern unavailable')}</div>"
                f"<div><strong>Your answer:</strong> {escape(item.user_answer or '(none)')}</div>"
                f"<div><strong>Correct answer:</strong> {escape(item.correct_answer or '(none)')}</div>"
                f"<div><strong>Explanation:</strong> {escape(item.explanation or '(none)')}</div>"
                f"<div><a href='{escape(item.retry_link)}'>Retry drill</a></div>"
                "</li>"
            )

        sections.append(
            "<section style='margin:24px 0;padding:16px;border:1px solid #D6E4FF;border-radius:12px'>"
            f"<h2 style='margin:0 0 8px;font-size:18px;color:#1D4E89'>{index}. {header}</h2>"
            "<p style='margin:0 0 8px;font-weight:700;color:#0F766E'>Correct rule</p>"
            f"<p style='margin:0 0 12px;line-height:1.5'>{escape(group.correct_rule_text or '(not recorded)')}</p>"
            f"<p style='margin:0 0 12px;color:#64748B'>Missed {group.count} time(s).</p>"
            "<p style='margin:0 0 8px;font-weight:700'>Questions missed</p>"
            f"<ul style='margin:0;padding-left:20px'>{''.join(question_blocks)}</ul>"
            "</section>"
        )

    return (
        "<!DOCTYPE html><html><body style='font-family:Segoe UI,Arial,sans-serif;"
        "color:#102033;max-width:720px;margin:0 auto;padding:16px'>"
        f"<h1 style='color:#2563EB;margin-bottom:4px'>Daily Error Sheet</h1>"
        f"<p style='color:#64748B;margin-top:0'>{escape(report.report_date)}</p>"
        "<table style='margin:16px 0 24px'>" + summary_html + "</table>"
        "<h2 style='color:#1D4E89'>Missed Rules</h2>"
        + "".join(sections)
        + "</body></html>"
    )


def _builtin_card_index() -> Dict[str, Dict[str, Any]]:
    """Index built-in trainer cards by id, advId, and subject|subtopic keys."""
    global _BUILTIN_CARD_INDEX
    if _BUILTIN_CARD_INDEX is not None:
        return _BUILTIN_CARD_INDEX

    from mbe_import_services import load_builtin_trap_trainer_cards, normalize_mbe_subject

    index: Dict[str, Dict[str, Any]] = {}
    for card in load_builtin_trap_trainer_cards():
        keys = set()
        for raw_key in (card.get("advId"), card.get("id")):
            if not raw_key:
                continue
            key = str(raw_key).strip()
            keys.add(key)
            if key.upper().startswith("ABX"):
                keys.add(key[3:])
        subject = normalize_mbe_subject(card.get("subj") or "")
        subtopic = card.get("sub") or ""
        if subject:
            keys.add(f"{subject}|{subtopic}")
        for key in keys:
            if key:
                index[key] = card
    _BUILTIN_CARD_INDEX = index
    return index


def _format_mbe_question_prompt(
    *,
    scenario: str = "",
    question: str = "",
    title: str = "",
    subtopic: str = "",
) -> str:
    """Build a readable prompt from MBE card fields (scenario is the fact pattern)."""
    scenario = (scenario or "").strip()
    question = (question or "").strip()
    title = (title or "").strip()
    subtopic = (subtopic or "").strip()

    parts = []
    if scenario:
        parts.append(scenario)
    if question:
        parts.append(question)
    elif subtopic and subtopic.lower() not in title.lower():
        parts.append(subtopic)
    elif title and len(title) > 24:
        parts.append(title)
    return "\n\n".join(parts)


def _details_from_db_row(row) -> Dict[str, Any]:
    options = []
    try:
        options = json.loads(row[9] or "[]")
    except Exception:
        options = []

    correct_opt = next((opt for opt in options if opt.get("ok")), {})
    trap_opt = next((opt for opt in options if opt.get("trap")), {})
    scenario = row[6] or ""
    question = row[7] or ""
    title = row[5] or ""

    return {
        "card_uid": row[1],
        "subject": row[3] or "",
        "subtopic": row[4] or "",
        "title": title,
        "scenario": scenario,
        "question": question,
        "rule_hint": row[8] or "",
        "plain_english": row[10] or "",
        "correct_answer": correct_opt.get("t") or "",
        "explanation": correct_opt.get("why") or trap_opt.get("why") or row[10] or "",
        "question_prompt": _format_mbe_question_prompt(
            scenario=scenario,
            question=question,
            title=title,
            subtopic=row[4] or "",
        ),
    }


def _details_from_builtin_card(card: Dict[str, Any]) -> Dict[str, Any]:
    options = card.get("options") or []
    correct_opt = next((opt for opt in options if opt.get("ok")), {})
    trap_opt = next((opt for opt in options if opt.get("trap")), {})
    scenario = card.get("scenario") or ""
    question = card.get("q") or ""
    title = card.get("title") or ""

    return {
        "card_uid": str(card.get("id") or card.get("advId") or ""),
        "subject": card.get("subj") or "",
        "subtopic": card.get("sub") or "",
        "title": title,
        "scenario": scenario,
        "question": question,
        "rule_hint": card.get("ru") or "",
        "plain_english": card.get("plain") or "",
        "correct_answer": correct_opt.get("t") or "",
        "explanation": correct_opt.get("why") or trap_opt.get("why") or card.get("plain") or "",
        "question_prompt": _format_mbe_question_prompt(
            scenario=scenario,
            question=question,
            title=title,
            subtopic=card.get("sub") or "",
        ),
    }


def resolve_mbe_card_details(lookup_key: str, *, correct_answer: str = "") -> Dict[str, Any]:
    """Resolve MBE card content from a practice-stats key (DB123, ABX123, uid, etc.)."""
    for key in _trainer_lookup_keys(lookup_key):
        row = lookup_mbe_card_row(key)
        if row:
            return _details_from_db_row(row)

        builtin = _builtin_card_index().get(key)
        if builtin:
            return _details_from_builtin_card(builtin)

        upper = key.upper()
        if upper.startswith("ABX"):
            builtin = _builtin_card_index().get(key[3:])
            if builtin:
                return _details_from_builtin_card(builtin)
            if key[3:].isdigit():
                builtin = _builtin_card_index().get(str(int(key[3:])))
                if builtin:
                    return _details_from_builtin_card(builtin)

    if correct_answer:
        return _lookup_details_by_correct_answer(correct_answer)
    return {}


def record_mbe_practice_misses(username: str, stats_blob: dict):
    """Ingest incorrect MBE drill answers from a synced practice stats blob."""
    if not username or not isinstance(stats_blob, dict):
        return 0

    settings = get_user_notification_settings(username)
    timezone_name = settings["daily_error_sheet_timezone"]
    card_stats = stats_blob.get("cardStats") or {}
    inserted = 0

    for card_key, stats in card_stats.items():
        if not isinstance(stats, dict) or card_key.startswith("__"):
            continue
        history = stats.get("practiceHistory") or []
        for entry in history:
            if not isinstance(entry, dict):
                continue
            if entry.get("correct") or entry.get("wasCorrect"):
                continue

            event_at = entry.get("at") or entry.get("practicedAt") or ""
            event_key = f"mbe:{card_key}:{event_at}:{entry.get('selectedAnswerText', '')}"
            details = resolve_mbe_card_details(
                card_key,
                correct_answer=entry.get("correctAnswerText") or "",
            )
            card_uid = details.get("card_uid") or card_key
            rule_label = details.get("title") or details.get("subtopic") or card_key
            question_prompt = details.get("question_prompt") or ""

            if record_missed_answer_event(
                username=username,
                event_key=event_key,
                source="mbe_drill",
                event_at=event_at or datetime.now().isoformat(),
                event_date=event_date_for_timestamp(event_at, timezone_name),
                question_id=card_uid,
                session_id=entry.get("sessionId"),
                topic=details.get("subject") or (card_key.split("|")[0] if "|" in card_key else ""),
                subtopic=details.get("subtopic") or "",
                rule_id=card_uid,
                rule_label=rule_label,
                missed_rule_text=entry.get("selectedAnswerText") or "",
                correct_rule_text=details.get("rule_hint") or details.get("correct_answer") or "",
                question_prompt=question_prompt,
                user_answer=entry.get("selectedAnswerText") or "",
                correct_answer=entry.get("correctAnswerText") or details.get("correct_answer") or "",
                explanation=details.get("explanation") or entry.get("autopsy") or "",
                retry_link=retry_link_for_source("mbe_drill", card_uid),
            ):
                inserted += 1

    return inserted


def record_bridge_drill_miss(
    username: str,
    *,
    card_uid: str,
    subject: str,
    subtopic: str,
    picked_letter: str,
    correct_letter: str,
    event_at: Optional[str] = None,
):
    """Record a missed Bridge Drill multiple-choice pick."""
    if not username:
        return False

    settings = get_user_notification_settings(username)
    timezone_name = settings["daily_error_sheet_timezone"]
    event_at = event_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    details = resolve_mbe_card_details(card_uid)
    options = []
    row = lookup_mbe_card_row(card_uid)
    if row:
        try:
            options = json.loads(row[9] or "[]")
        except Exception:
            options = []

    def _option_text(letter: str) -> str:
        letters = ["A", "B", "C", "D"]
        if letter in letters:
            idx = letters.index(letter)
            if idx < len(options):
                return options[idx].get("t") or ""
        return ""

    correct_opt = next((opt for opt in options if opt.get("ok")), {})
    picked_opt = None
    if picked_letter in {"A", "B", "C", "D"}:
        picked_opt = options[["A", "B", "C", "D"].index(picked_letter)] if options else None

    event_key = f"bridge:{card_uid}:{event_at}:{picked_letter}"
    return record_missed_answer_event(
        username=username,
        event_key=event_key,
        source="bridge_drill",
        event_at=event_at,
        event_date=event_date_for_timestamp(event_at, timezone_name),
        question_id=card_uid,
        topic=subject or details.get("subject") or "",
        subtopic=subtopic or details.get("subtopic") or "",
        rule_id=card_uid,
        rule_label=details.get("title") or subtopic or subject or "Bridge Drill",
        missed_rule_text=picked_opt.get("t") if picked_opt else picked_letter,
        correct_rule_text=details.get("rule_hint") or correct_opt.get("t") or "",
        question_prompt=details.get("question_prompt") or "",
        user_answer=_option_text(picked_letter) or picked_letter,
        correct_answer=_option_text(correct_letter) or correct_opt.get("t") or correct_letter,
        explanation=correct_opt.get("why") or details.get("explanation") or "",
        retry_link=retry_link_for_source("bridge_drill", card_uid),
    )


def record_mee_ladder_miss(
    username: str,
    *,
    question_id: int,
    subject: str,
    mode: str,
    self_score: int,
    missed_issues: str,
    response_text: str,
    rules_text: str,
    question_prompt: str,
    event_at: Optional[str] = None,
):
    """Record a weak MEE practice attempt (self-score 2 or below) as a missed rule event."""
    if not username:
        return False
    try:
        score = int(self_score)
    except (TypeError, ValueError):
        score = 0
    if score > 2:
        return False

    settings = get_user_notification_settings(username)
    timezone_name = settings["daily_error_sheet_timezone"]
    event_at = event_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    source = "mee_mini_drill" if "mini" in (mode or "").lower() else "mee_ladder"
    rule_label = subject or "MEE Practice"
    if missed_issues:
        first_issue = re.split(r"[\n;,]+", missed_issues.strip())[0].strip()
        if first_issue:
            rule_label = first_issue

    event_key = f"mee:{question_id}:{event_at}:{score}"
    return record_missed_answer_event(
        username=username,
        event_key=event_key,
        source=source,
        event_at=event_at,
        event_date=event_date_for_timestamp(event_at, timezone_name),
        question_id=str(question_id),
        topic=subject or "",
        rule_label=rule_label,
        missed_rule_text=missed_issues or response_text or "",
        correct_rule_text=rules_text or "",
        question_prompt=question_prompt or "",
        user_answer=response_text or "",
        correct_answer=rules_text or "",
        explanation=missed_issues or "Self-score indicated missed issues or rules.",
        retry_link=retry_link_for_source(source, str(question_id)),
    )
