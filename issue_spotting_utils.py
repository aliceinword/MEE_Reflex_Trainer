# -*- coding: utf-8 -*-
"""Shared constants and helpers for MEE Issue Spotting drills."""

from __future__ import annotations

import re
from collections import Counter

MEE_ISSUE_SPOTTING_SUBJECTS = [
    "Evidence",
    "Constitutional Law",
    "Contracts",
    "Torts",
    "Civil Procedure",
    "Criminal Law & Procedure",
]

SUBJECT_ALIASES = {
    "Contracts": ["Contracts / Sales", "Contracts and Sales"],
    "Criminal Law & Procedure": ["Criminal Law and Procedure"],
}

ISSUE_TRIGGER_PREFIX_RE = re.compile(
    r"(?is)(?:^|\n)\s*Issue\s+trigger:\s*(.+?)(?=\n\s*\n|\n\s*(?:One-liner:|Exam tips:)|\Z)"
)
ONELINER_RE = re.compile(r"(?im)^\s*One-liner:\s*(.+)$")
APPEARANCE_PCT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")
NORMALIZE_TRIGGER_RE = re.compile(r"[^a-z0-9]+")

# Attack-table rows without a stored appearance rate still rank above question-bank cards.
DEFAULT_ATTACK_TABLE_FREQUENCY = 100
HIGH_YIELD_MIN_FREQUENCY = 2


def expand_subject_names(subjects):
    """Return canonical subjects plus DB naming aliases for filtering."""
    names = []
    seen = set()
    for subject in subjects or []:
        canonical = str(subject or "").strip()
        if not canonical:
            continue
        candidates = [canonical] + list(SUBJECT_ALIASES.get(canonical, []))
        for name in candidates:
            key = name.lower()
            if key in seen:
                continue
            seen.add(key)
            names.append(name)
    return names


def canonical_subject_name(subject):
    """Map a DB subject string back to a display/canonical label."""
    text = str(subject or "").strip()
    if not text:
        return ""
    for canonical in MEE_ISSUE_SPOTTING_SUBJECTS:
        if text.lower() == canonical.lower():
            return canonical
        aliases = SUBJECT_ALIASES.get(canonical, [])
        if any(text.lower() == alias.lower() for alias in aliases):
            return canonical
    return text


def normalize_trigger_key(trigger):
    """Normalize trigger text for deduplication."""
    return NORMALIZE_TRIGGER_RE.sub("", str(trigger or "").lower())


def parse_issue_trigger_from_rule_text(rule_text):
    """Extract the Issue trigger: prefix from an attack-table style rule_text."""
    text = str(rule_text or "").strip()
    if not text:
        return ""
    match = ISSUE_TRIGGER_PREFIX_RE.search(text)
    if not match:
        return ""
    return re.sub(r"\s+", " ", match.group(1)).strip()


def parse_oneliner_from_rule_text(rule_text):
    """Extract the One-liner: line from an attack-table style rule_text."""
    text = str(rule_text or "").strip()
    if not text:
        return ""
    match = ONELINER_RE.search(text)
    if not match:
        return ""
    return re.sub(r"\s+", " ", match.group(1)).strip()


def appearance_rate_to_frequency(appearance_rate):
    """Convert appearance_rate text (e.g. '12.5%' or 'High') into a sort weight."""
    text = str(appearance_rate or "").strip()
    if not text:
        return DEFAULT_ATTACK_TABLE_FREQUENCY

    pct = APPEARANCE_PCT_RE.search(text)
    if pct:
        try:
            return int(round(float(pct.group(1)) * 10))
        except ValueError:
            pass

    lowered = text.lower()
    if "high" in lowered:
        return 150
    if "medium" in lowered or "mid" in lowered:
        return 80
    if "low" in lowered:
        return 30
    return DEFAULT_ATTACK_TABLE_FREQUENCY


def issue_frequency_map(questions_rows):
    """
    Count how often each tested-issue bullet appears across question bank rows.

    Accepts:
      - (subject, tested_issues)
      - (id, subject, tested_issues, trigger_facts)
      - dicts with tested_issues
    """
    counts = Counter()
    for row in questions_rows or []:
        if isinstance(row, dict):
            tested = row.get("tested_issues") or ""
        elif len(row) >= 4:
            tested = row[2] or ""
        elif len(row) >= 2:
            tested = row[1] or ""
        else:
            tested = ""
        for issue in resolve_expected_issues(tested):
            key = re.sub(r"\s+", " ", str(issue).strip().lower())
            if key:
                counts[key] += 1
    return counts


def max_issue_frequency(expected_issues, frequency_counts):
    """Return the highest known frequency among the card's expected issues."""
    best = 0
    for issue in expected_issues or []:
        key = re.sub(r"\s+", " ", str(issue).strip().lower())
        best = max(best, int(frequency_counts.get(key, 0)))
    return best


def build_attack_table_card(row, frequency_counts=None):
    """
    Build a spotting card from an outline_rules row.

    row: (id, subject, rule_title, appearance_rate, rule_text, ...)
    """
    if not row or len(row) < 5:
        return None

    rule_id, subject, rule_title, appearance_rate, rule_text = row[:5]
    trigger = parse_issue_trigger_from_rule_text(rule_text)
    if not trigger:
        return None

    expected = [str(rule_title or "").strip()] if str(rule_title or "").strip() else []
    freq = appearance_rate_to_frequency(appearance_rate)
    if frequency_counts:
        freq = max(freq, max_issue_frequency(expected, frequency_counts))

    return {
        "id": f"or-{rule_id}",
        "subject": canonical_subject_name(subject),
        "trigger": trigger,
        "expected_issues": expected,
        "oneliner": parse_oneliner_from_rule_text(rule_text),
        "rule_text": str(rule_text or "").strip(),
        "source": "attack_table",
        "frequency": freq,
        "rule_title": str(rule_title or "").strip(),
    }


def fallback_issue_labels(tested_issues_text):
    """Split short semicolon/newline issue labels when extract_issue_bullets finds none."""
    text = str(tested_issues_text or "").strip()
    if not text:
        return []

    parts = re.split(r"[\n;|•]+", text)
    labels = []
    seen = set()
    for part in parts:
        part = re.sub(r"\s+", " ", part).strip(" -•\t")
        part = re.sub(r"^\d+[.)]\s*", "", part)
        if len(part) < 3:
            continue
        key = part.lower()
        if key in seen:
            continue
        seen.add(key)
        labels.append(part)
    return labels


def resolve_expected_issues(tested_issues_text):
    """Prefer extract_issue_bullets; fall back to simple label splitting."""
    from text_rendering import extract_issue_bullets

    issues = extract_issue_bullets(tested_issues_text)
    if issues:
        return issues
    return fallback_issue_labels(tested_issues_text)


def build_question_bank_cards(question_row, frequency_counts=None, *, max_triggers=3):
    """
    Build spotting cards from one active July 2026 question.

    question_row: (id, subject, tested_issues, trigger_facts) or compatible dict.
    """
    from text_rendering import extract_trigger_fact_items

    if isinstance(question_row, dict):
        question_id = question_row.get("id")
        subject = question_row.get("subject") or ""
        tested_issues = question_row.get("tested_issues") or ""
        trigger_facts = question_row.get("trigger_facts") or ""
    else:
        question_id = question_row[0]
        subject = question_row[1] if len(question_row) > 1 else ""
        tested_issues = question_row[2] if len(question_row) > 2 else ""
        trigger_facts = question_row[3] if len(question_row) > 3 else ""

    triggers = extract_trigger_fact_items(trigger_facts)[:max_triggers]
    issues = resolve_expected_issues(tested_issues)
    if not triggers or not issues:
        return []

    frequency_counts = frequency_counts or {}
    freq = max_issue_frequency(issues, frequency_counts)
    canonical = canonical_subject_name(subject)
    cards = []
    for idx, trigger in enumerate(triggers):
        cards.append(
            {
                "id": f"q-{question_id}-{idx}",
                "subject": canonical,
                "trigger": trigger,
                "expected_issues": issues,
                "oneliner": "",
                "rule_text": "",
                "source": "question_bank",
                "frequency": freq,
                "rule_title": issues[0] if issues else "",
            }
        )
    return cards


def dedupe_spotting_cards(cards):
    """Drop cards with duplicate normalized triggers (keep higher frequency / attack_table)."""
    ranked = sorted(
        cards or [],
        key=lambda card: (
            -int(card.get("frequency") or 0),
            0 if card.get("source") == "attack_table" else 1,
            str(card.get("rule_title") or card.get("expected_issues") or ""),
        ),
    )
    seen = set()
    unique = []
    for card in ranked:
        key = normalize_trigger_key(card.get("trigger"))
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(card)
    return unique


def sort_spotting_cards(cards):
    """frequency DESC, attack_table before question_bank, then title."""
    return sorted(
        cards or [],
        key=lambda card: (
            -int(card.get("frequency") or 0),
            0 if card.get("source") == "attack_table" else 1,
            str(card.get("rule_title") or ""),
            str(card.get("id") or ""),
        ),
    )


def filter_high_yield_cards(cards, *, min_frequency=HIGH_YIELD_MIN_FREQUENCY):
    """Keep attack-table cards and question-bank cards at/above the frequency floor."""
    kept = []
    for card in cards or []:
        if card.get("source") == "attack_table":
            kept.append(card)
            continue
        if int(card.get("frequency") or 0) >= min_frequency:
            kept.append(card)
    return kept
