# -*- coding: utf-8 -*-

import argparse
import re
import shutil
import sqlite3
from collections import Counter
from datetime import datetime
from pathlib import Path

import fitz

from database import DB_NAME, init_db
from text_cleanup import normalize_extracted_text


ENTRY_HEADER_RE = re.compile(
    r"(?m)^(February|July)\s+(\d{4})\s+[\u2014\u2013-]\s+Question\s+(\d+)\s*$"
)


def clean_pdf_text(text):
    text = normalize_extracted_text(text or "")
    text = text.replace("\uf0b7", "\n- ")
    text = text.replace("", "\n- ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def read_pdf_text(pdf_path):
    doc = fitz.open(pdf_path)
    return "\n".join(page.get_text("text") for page in doc)


def normalize_exam(month, year):
    return f"{month} {year}"


def compact_lines(text):
    lines = []

    for line in clean_pdf_text(text).splitlines():
        line = line.strip()

        if not line:
            continue

        if re.fullmatch(r"[—\-–_ ]{5,}", line):
            continue

        lines.append(line)

    return "\n".join(lines).strip()


def extract_between(text, start_label, end_labels):
    start = re.search(re.escape(start_label), text, flags=re.IGNORECASE)

    if not start:
        return ""

    start_index = start.end()
    end_index = len(text)

    for label in end_labels:
        found = re.search(re.escape(label), text[start_index:], flags=re.IGNORECASE)
        if found:
            end_index = min(end_index, start_index + found.start())

    return compact_lines(text[start_index:end_index])


def extract_rules(answer_path):
    chunks = []
    pattern = re.compile(
        r"Rule\(s\):\s*(.*?)(?=\nFact-based analysis:|\nConclusion:|\n\d+\.\s+Point|\Z)",
        flags=re.IGNORECASE | re.DOTALL,
    )

    for match in pattern.finditer(answer_path):
        chunk = compact_lines(match.group(1))
        if chunk:
            chunks.append(chunk)

    if not chunks:
        short_answers = re.findall(
            r"Short answer:\s*(.*?)(?=\nRule\(s\):|\nFact-based analysis:|\nConclusion:|\n\d+\.\s+Point|\Z)",
            answer_path,
            flags=re.IGNORECASE | re.DOTALL,
        )
        chunks = [compact_lines(chunk) for chunk in short_answers if compact_lines(chunk)]

    legal_keywords = [
        "authority", "agent", "principal", "partner", "partnership", "corporation",
        "director", "shareholder", "liable", "liability", "duty", "fiduciary",
        "jurisdiction", "venue", "removal", "diversity", "claim", "joinder",
        "contract", "breach", "ucc", "offer", "acceptance", "consideration",
        "evidence", "hearsay", "admissible", "relevance", "privilege",
        "negligence", "duty", "causation", "damages", "tort", "property",
        "mortgage", "easement", "covenant", "warrant", "search", "seizure",
        "speech", "scrutiny", "constitutional", "rule", "requires", "must",
        "may", "unless", "if", "when", "standard", "elements", "test",
    ]

    seen = set()
    unique = []

    for chunk in chunks:
        cleaned_lines = []

        for line in chunk.splitlines():
            line = re.sub(r"^-\s*", "", line).strip()

            if not line:
                continue

            lower = line.lower()

            if line[0].islower():
                continue

            if re.search(r"\bPoint\s+(One|Two|Three|Four|Five|Six|\d+)\b", line):
                continue

            if lower.startswith(("thus,", "therefore,", "since ", "in this case,", "here,")):
                continue

            if not any(keyword in lower for keyword in legal_keywords):
                continue

            cleaned_lines.append(line)

        cleaned = "\n".join(cleaned_lines).strip()

        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            unique.append(cleaned)

    return "\n\n".join(unique)


def clean_tested_issues_for_import(text):
    issue_starters = (
        "whether", "what", "which", "who", "can", "may", "should", "would",
        "did", "does", "do", "is", "are", "was", "were", "under", "the admissibility",
    )
    cleaned = []

    for line in compact_lines(text).splitlines():
        line = re.sub(r"^-\s*", "", line).strip()

        if not line:
            continue

        lower = line.lower()

        if "point " in lower or "rule(s)" in lower or "fact-based analysis" in lower:
            continue

        if "?" in line or lower.startswith(issue_starters):
            cleaned.append(f"- {line}")

    return "\n".join(cleaned)


def parse_entries(raw_text):
    text = raw_text or ""
    matches = list(ENTRY_HEADER_RE.finditer(text))
    entries = []

    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end].strip()

        exam_name = normalize_exam(match.group(1), match.group(2))
        question_number = match.group(3)

        primary_subject = extract_between(
            body,
            "Primary source subject:",
            ["Question summary:", "Issues tested:"],
        )
        question_summary = extract_between(
            body,
            "Question summary:",
            ["Issues tested:"],
        )
        tested_issues = extract_between(
            body,
            "Issues tested:",
            [
                "Relevant facts to use:",
                "Condensed sample-answer path:",
                "Short answer:",
                "Rule(s):",
                "Fact-based analysis:",
                "Conclusion:",
                "Point One",
                "1. Point",
            ],
        )
        tested_issues = clean_tested_issues_for_import(tested_issues)

        trigger_facts = extract_between(
            body,
            "Relevant facts to use:",
            ["Condensed sample-answer path:"],
        )
        model_points = extract_between(
            body,
            "Condensed sample-answer path:",
            ["Question call(s):"],
        )
        rules = extract_rules(model_points)

        if question_summary:
            model_points = f"Question summary:\n{question_summary}\n\nCondensed sample-answer path:\n{model_points}".strip()

        entries.append(
            {
                "exam_name": exam_name,
                "question_number": question_number,
                "primary_subject": primary_subject,
                "tested_issues": tested_issues,
                "rules": rules,
                "trigger_facts": trigger_facts,
                "model_points": model_points,
                "traps": "",
            }
        )

    return entries


def backup_db(db_path):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.with_name(f"{db_path.stem}_backup_before_condensed_answers_{timestamp}{db_path.suffix}")
    shutil.copy2(db_path, backup_path)
    return backup_path


def update_database(entries, dry_run=False):
    init_db()
    db_path = Path(DB_NAME)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    stats = Counter()
    unmatched = []
    duplicate_keys = []

    entry_counts = Counter((e["exam_name"], e["question_number"]) for e in entries)

    for key, count in entry_counts.items():
        if count > 1:
            duplicate_keys.append((key, count))

    for entry in entries:
        key = (entry["exam_name"], entry["question_number"])

        cur.execute(
            """
            SELECT id, subject
            FROM questions
            WHERE exam_name = ?
            AND question_number = ?
            """,
            key,
        )
        rows = cur.fetchall()

        if len(rows) != 1:
            unmatched.append((entry["exam_name"], entry["question_number"], entry["primary_subject"], len(rows)))
            stats["unmatched"] += 1
            continue

        question_id, subject = rows[0]

        if not dry_run:
            cur.execute(
                """
                UPDATE questions
                SET tested_issues = ?,
                    rules = ?,
                    trigger_facts = ?,
                    traps = ?,
                    model_points = ?
                WHERE id = ?
                """,
                (
                    entry["tested_issues"],
                    entry["rules"],
                    entry["trigger_facts"],
                    entry["traps"],
                    entry["model_points"],
                    question_id,
                ),
            )

        stats["matched"] += 1

    backup_path = None

    if not dry_run:
        conn.commit()

    conn.close()

    return stats, unmatched, duplicate_keys, backup_path


def main():
    parser = argparse.ArgumentParser(
        description="Import user-owned condensed MEE sample answers into existing MEE Reflex Trainer questions."
    )
    parser.add_argument("pdf", help="Path to MEE_Condensed_Sample_Answers_By_Subject.pdf")
    parser.add_argument("--apply", action="store_true", help="Actually update the database. Omit for dry run.")
    args = parser.parse_args()

    pdf_path = Path(args.pdf)

    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)

    raw_text = read_pdf_text(pdf_path)
    entries = parse_entries(raw_text)

    print(f"Parsed entries: {len(entries)}")

    db_path = Path(DB_NAME)
    backup_path = None

    if args.apply:
        backup_path = backup_db(db_path)
        print(f"Backup created: {backup_path}")

    stats, unmatched, duplicate_keys, _ = update_database(entries, dry_run=not args.apply)

    print(f"Matched entries: {stats['matched']}")
    print(f"Unmatched entries: {stats['unmatched']}")

    if duplicate_keys:
        print("Duplicate entry keys in PDF:")
        for key, count in duplicate_keys[:20]:
            print(f"  {key[0]} Q{key[1]}: {count}")

    if unmatched:
        print("Unmatched entries:")
        for exam_name, question_number, subject, row_count in unmatched[:50]:
            print(f"  {exam_name} Q{question_number} ({subject or 'unknown subject'}) -> {row_count} DB rows")

    if not args.apply:
        print("Dry run only. Re-run with --apply to update the database.")
    else:
        print("Database updated with condensed sample answers.")


if __name__ == "__main__":
    main()
