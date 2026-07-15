"""Import Last Bar Prep July 2026 MEE Attack Table PDF into outline_rules.

Usage:
    python scripts/import_july_2026_attack_table.py "path/to/July 2026 MEE Attack Table.pdf"

Re-running is safe: skips rules already imported from this PDF, and skips rules whose
title already exists for the same subject (any source).
"""

import _bootstrap  # noqa: F401

import re
import sys
from pathlib import Path

import fitz

from database import fetch_all, init_db, add_outline_rule

SOURCE_FILE = "July 2026 MEE Attack Table.pdf"

SUBJECT_HEADERS = {
    "agency & partnerships": "Agency & Partnership",
    "corporations & llcs": "Corporations & LLCs",
    "civil procedure": "Civil Procedure",
    "constitutional law": "Constitutional Law",
    "contracts": "Contracts",
    "criminal law & procedure": "Criminal Law & Procedure",
    "evidence": "Evidence",
    "torts": "Torts",
    "real property": "Real Property",
}

COLUMN_HEADERS = {
    "issue trigger",
    "when you see this",
    "core black letter rule",
    "write this",
    "memorable one-liner",
    "exam tricks & tips",
}

NOISE_PATTERNS = (
    "last minute mee attack table",
    "last bar prep",
    "yourlastbarprep.com",
    "build a study schedule",
    "homestretch package",
    "new to last bar prep",
    "before you start",
    "how to read this attack table",
    "subjects in this edition",
    "prepared by last bar prep",
    "ultimate last minute",
    "july 2026 revised edition",
    "get the homestretch package",
)

RULE_START_RE = re.compile(r"^([A-Z][^:\n]{2,90}?):\s*(.*)", re.S)
NORMALIZE_TITLE_RE = re.compile(r"[^a-z0-9]+")


def clean_line(line):
    line = str(line or "").replace("\u00a0", " ").strip()
    line = re.sub(r"[ \t]+", " ", line)
    return line


def column_for(x):
    if x < 100:
        return "trigger"
    if x < 280:
        return "rule"
    if x < 430:
        return "oneliner"
    return "tips"


def is_noise_line(line):
    lowered = clean_line(line).lower()
    if not lowered:
        return True
    if lowered in COLUMN_HEADERS:
        return True
    if lowered.startswith("testing guide & summary"):
        return True
    if re.fullmatch(r"p\.?\s*\d+", lowered):
        return True
    if re.fullmatch(r"\d+", lowered):
        return True
    return any(pattern in lowered for pattern in NOISE_PATTERNS)


def is_section_header(line):
    stripped = clean_line(line)
    if not stripped:
        return False
    if stripped.upper() == stripped and len(stripped) < 60 and stripped.isascii():
        return True
    if re.match(r"^[IVX]+\.\s+[A-Z]", stripped):
        return True
    return False


def normalize_title(title):
    return NORMALIZE_TITLE_RE.sub("", str(title or "").lower())


def load_existing_titles():
    rows = fetch_all(
        """
        SELECT subject, rule_title
        FROM outline_rules
        """
    )
    by_subject = {}
    for subject, rule_title in rows:
        key = str(subject or "").strip().lower()
        by_subject.setdefault(key, set()).add(normalize_title(rule_title))
    return by_subject


def title_already_exists(existing_titles, subject, rule_title):
    normalized = normalize_title(rule_title)
    if not normalized:
        return False

    subject_key = str(subject or "").strip().lower()
    titles = set(existing_titles.get(subject_key, set()))

    business_aliases = {
        "agency & partnership",
        "corporations & llcs",
        "business associations",
    }
    if subject_key in business_aliases:
        for alias in business_aliases:
            titles.update(existing_titles.get(alias, set()))

    criminal_aliases = {
        "criminal law & procedure",
        "criminal law and procedure",
    }
    if subject_key in criminal_aliases:
        for alias in criminal_aliases:
            titles.update(existing_titles.get(alias, set()))

    contracts_aliases = {"contracts", "contracts and sales", "contracts / sales"}
    if subject_key in contracts_aliases:
        for alias in contracts_aliases:
            titles.update(existing_titles.get(alias, set()))

    return normalized in titles


def extract_rule_title(rule_text):
    match = RULE_START_RE.match(clean_line(rule_text))
    if match:
        return match.group(1).strip()
    return clean_line(rule_text)[:80]


def format_rule_text(trigger, rule, oneliner, tips):
    parts = []
    trigger = clean_line(trigger)
    rule = clean_line(rule)
    oneliner = clean_line(oneliner)
    tips = clean_line(tips)

    if trigger:
        parts.append(f"Issue trigger: {trigger}")
    if rule:
        parts.append(rule)
    if oneliner:
        parts.append(f"One-liner: {oneliner}")
    if tips:
        parts.append(f"Exam tips: {tips}")
    return "\n\n".join(parts).strip()


def parse_page_lines(page):
    items = []
    for block in page.get_text("dict").get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            text = clean_line("".join(span.get("text", "") for span in line.get("spans", [])))
            if not text or is_noise_line(text):
                continue
            x0 = min(span["bbox"][0] for span in line["spans"])
            y0 = min(span["bbox"][1] for span in line["spans"])
            items.append((y0, x0, text))
    items.sort()
    return items


def detect_subject(line):
    return SUBJECT_HEADERS.get(clean_line(line).lower())


def find_rule_anchors(items):
    by_y = {}
    for y, x, text in items:
        y_key = round(y, 1)
        by_y.setdefault(y_key, {"trigger": [], "rule": [], "oneliner": [], "tips": []})
        by_y[y_key][column_for(x)].append(text)

    anchors = []
    for y_key in sorted(by_y.keys()):
        row = by_y[y_key]
        rule_text = " ".join(row.get("rule", [])).strip()
        trigger_text = " ".join(row.get("trigger", [])).strip()
        if not rule_text or not RULE_START_RE.match(rule_text):
            continue
        if not trigger_text or is_section_header(trigger_text):
            continue

        title = extract_rule_title(rule_text)
        if title.lower().startswith("testing guide"):
            continue

        anchors.append(y_key)

    return anchors


def collect_row(items, anchor_y, next_anchor_y):
    row = {"trigger": [], "rule": [], "oneliner": [], "tips": []}
    for y, x, text in items:
        if y < anchor_y - 1:
            continue
        if next_anchor_y is not None and y >= next_anchor_y - 0.5:
            break
        col = column_for(x)
        if col == "trigger" and is_section_header(text):
            continue
        row[col].append(text)
    return row


def flush_row(row, subject, pdf_page, existing_titles, stats):
    trigger = " ".join(row.get("trigger", [])).strip()
    rule = " ".join(row.get("rule", [])).strip()
    oneliner = " ".join(row.get("oneliner", [])).strip()
    tips = " ".join(row.get("tips", [])).strip()

    if not rule or not RULE_START_RE.match(rule):
        return

    rule_title = extract_rule_title(rule)
    if rule_title.lower().startswith("testing guide"):
        return

    rule_text = format_rule_text(trigger, rule, oneliner, tips)
    if len(rule_text) < 40:
        return

    if title_already_exists(existing_titles, subject, rule_title):
        stats["skipped_existing"] += 1
        return

    inserted = add_outline_rule(
        subject,
        rule_title,
        "",
        rule_text,
        pdf_page,
        "",
        SOURCE_FILE,
    )
    if inserted:
        stats["imported"] += 1
        subject_key = subject.strip().lower()
        existing_titles.setdefault(subject_key, set()).add(normalize_title(rule_title))
    else:
        stats["skipped_duplicate"] += 1


def parse_page_rules(items, subject, pdf_page, existing_titles, stats):
    anchors = find_rule_anchors(items)
    for anchor_pos, anchor_y in enumerate(anchors):
        next_anchor_y = anchors[anchor_pos + 1] if anchor_pos + 1 < len(anchors) else None
        row = collect_row(items, anchor_y, next_anchor_y)
        flush_row(row, subject, pdf_page, existing_titles, stats)


def import_attack_table(pdf_path):
    init_db()
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"Could not find {pdf_path}")

    stats = {
        "imported": 0,
        "skipped_existing": 0,
        "skipped_duplicate": 0,
    }
    existing_titles = load_existing_titles()
    current_subject = ""

    with fitz.open(pdf_path) as doc:
        for page_index, page in enumerate(doc):
            items = parse_page_lines(page)
            page_subject = ""

            for _, _, text in items:
                subject = detect_subject(text)
                if subject:
                    page_subject = subject
                    break

            if page_subject:
                current_subject = page_subject

            if not current_subject:
                continue

            parse_page_rules(
                items,
                current_subject,
                page_index + 1,
                existing_titles,
                stats,
            )

    return stats


def main():
    pdf_arg = (
        sys.argv[1]
        if len(sys.argv) > 1
        else r"c:\Users\olesi\Downloads\July 2026 MEE Attack Table.pdf"
    )
    stats = import_attack_table(pdf_arg)
    print(f"Imported {stats['imported']} rules.")
    print(f"Skipped {stats['skipped_existing']} already-existing titles.")
    print(f"Skipped {stats['skipped_duplicate']} duplicates from this PDF.")


if __name__ == "__main__":
    main()
