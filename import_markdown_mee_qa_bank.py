from __future__ import annotations

import argparse
import json
import re
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from text_cleanup import normalize_extracted_text


DB_NAME = "mee_trainer.db"
SOURCE_LABEL = "MEE Question-Answer Bank Markdown import"


SUBJECT_NORMALIZATION = {
    "AGENCY & PARTNERSHIP": "Agency & Partnership",
    "AGENCY & PARTNERSHIP/CORPORATIONS": "Agency & Partnership",
    "AGENCY & PARTNERSHIP / CORPORATIONS": "Agency & Partnership",
    "AGENCY & PARTNERSHIP/TORTS": "Agency & Partnership",
    "AGENCY & PARTNERSHIP / TORTS": "Agency & Partnership",
    "CIVIL PROCEDURE": "Civil Procedure",
    "CIVIL PROCEDURE/CONFLICT OF LAWS": "Civil Procedure",
    "CIVIL PROCEDURE / CONFLICT OF LAWS": "Civil Procedure",
    "CONSTITUTIONAL LAW": "Constitutional Law",
    "CONTRACTS": "Contracts",
    "CONTRACTS/SALES": "Contracts",
    "CONTRACTS / SALES": "Contracts",
    "CONTRACTS/NEGOTIABLE INSTRUMENTS": "Contracts",
    "CONTRACTS / NEGOTIABLE INSTRUMENTS": "Contracts",
    "CORPORATIONS": "Corporations & LLCs",
    "CORPORATIONS & LLCS": "Corporations & LLCs",
    "CORPORATIONS AND LIMITED LIABILITY COMPANIES": "Corporations & LLCs",
    "CRIMINAL LAW": "Criminal Law & Procedure",
    "CRIMINAL LAW & PROCEDURE": "Criminal Law & Procedure",
    "CRIMINAL LAW AND PROCEDURE": "Criminal Law & Procedure",
    "EVIDENCE": "Evidence",
    "EVIDENCE/CRIMINAL LAW & PROCEDURE": "Evidence",
    "EVIDENCE / CRIMINAL LAW & PROCEDURE": "Evidence",
    "REAL PROPERTY": "Real Property",
    "TORTS": "Torts",
}


@dataclass
class ParsedRecord:
    source_id: str
    exam_name: str
    exam_year: int
    exam_season: str
    question_number: str
    subject: str
    raw_subject: str
    question_text: str
    call_of_question: str
    tested_issues: str
    rules: str
    traps: str
    model_points: str
    is_truncated: bool


def clean_text(text: str) -> str:
    if not text:
        return ""

    text = normalize_extracted_text(str(text))
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ")
    text = re.sub(r"(?m)^\s*\d{1,4}\s*$", "", text)
    text = re.sub(r"(?m)^[A-Za-z &/]+ Analysis\s+\d+\s*$", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_subject(subject: str) -> str:
    subject = clean_text(subject).upper()
    subject = re.sub(r"\s*/\s*", "/", subject)
    subject = re.sub(r"\s+", " ", subject).strip()
    return SUBJECT_NORMALIZATION.get(subject, subject.title())


def split_sections(body: str) -> dict[str, str]:
    matches = list(re.finditer(r"(?m)^####\s+(.+?)\s*$", body))
    sections: dict[str, str] = {}

    for idx, match in enumerate(matches):
        title = match.group(1).strip()
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(body)
        sections[title] = body[start:end].strip()

    return sections


def markdown_list_to_lines(text: str) -> str:
    text = clean_text(text)
    lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        line = re.sub(r"^[-*]\s+", "- ", line)
        line = re.sub(r"^>\s*", "- ", line)
        lines.append(line)
    return "\n".join(lines).strip()


def extract_subject(body: str) -> str:
    match = re.search(r"\*\*Subject:\*\*\s*(.*?)\s*\|", body, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    return clean_text(match.group(1))


def parse_records(markdown: str) -> list[ParsedRecord]:
    header_pattern = re.compile(
        r"(?ms)^###\s+"
        r"(?P<source_id>MEE-(?P<year>\d{4})-(?P<season>FEB|JUL)-Q(?P<qnum>\d{2}))"
        r"\s+(?:\u2014|-)\s+(?P<exam_name>[^\n]+)\n"
        r"(?P<body>.*?)(?=^###\s+MEE-|\Z)"
    )

    records: list[ParsedRecord] = []
    for match in header_pattern.finditer(markdown):
        body = match.group("body")
        sections = split_sections(body)
        raw_subject = extract_subject(body)
        subject = normalize_subject(raw_subject)
        model_points = clean_text(sections.get("Full Analysis", ""))
        is_truncated = bool(re.search(r"\bcontinued\b.*\bsee JSONL\b", model_points, flags=re.IGNORECASE))

        records.append(
            ParsedRecord(
                source_id=match.group("source_id"),
                exam_name=clean_text(match.group("exam_name")),
                exam_year=int(match.group("year")),
                exam_season="February" if match.group("season") == "FEB" else "July",
                question_number=str(int(match.group("qnum"))),
                subject=subject,
                raw_subject=raw_subject,
                question_text=clean_text(sections.get("Fact Pattern", "")),
                call_of_question=clean_text(sections.get("Questions Asked", "")),
                tested_issues=markdown_list_to_lines(sections.get("Key Legal Issues", "")),
                rules=markdown_list_to_lines(sections.get("Rules & Doctrine", "")),
                traps=markdown_list_to_lines(sections.get("Exam Traps & Examiner Notes", "")),
                model_points=model_points,
                is_truncated=is_truncated,
            )
        )

    return records


def existing_question_map(conn: sqlite3.Connection) -> dict[tuple[str, str], int]:
    rows = conn.execute("SELECT id, exam_name, question_number FROM questions").fetchall()
    result: dict[tuple[str, str], int] = {}
    for question_id, exam_name, question_number in rows:
        key = (str(exam_name).strip().lower(), str(question_number).strip().lstrip("0") or "0")
        result[key] = int(question_id)
    return result


def backup_db(db_path: Path) -> Path:
    backup = db_path.with_name(f"{db_path.stem}_backup_before_markdown_qa_import_{datetime.now():%Y%m%d_%H%M%S}{db_path.suffix}")
    shutil.copy2(db_path, backup)
    return backup


def import_records(records: list[ParsedRecord], apply: bool, allow_truncated: bool) -> dict:
    db_path = Path(DB_NAME)
    conn = sqlite3.connect(db_path)
    question_map = existing_question_map(conn)
    skipped_truncated = [record for record in records if record.is_truncated and not allow_truncated]
    importable_records = [record for record in records if allow_truncated or not record.is_truncated]

    updates = []
    inserts = []
    for record in importable_records:
        key = (record.exam_name.strip().lower(), record.question_number)
        existing_id = question_map.get(key)
        if existing_id:
            updates.append((existing_id, record))
        else:
            inserts.append(record)

    report = {
        "records_parsed": len(records),
        "records_skipped_truncated": len(skipped_truncated),
        "records_to_update": len(updates),
        "records_to_insert": len(inserts),
        "insert_preview": [r.source_id for r in inserts[:25]],
        "skipped_truncated_preview": [r.source_id for r in skipped_truncated[:25]],
        "backup": None,
    }

    if not apply:
        conn.close()
        return report

    report["backup"] = str(backup_db(db_path))

    for question_id, record in updates:
        conn.execute(
            """
            UPDATE questions
            SET
                subject = ?,
                question_text = ?,
                call_of_question = ?,
                tested_issues = ?,
                rules = CASE WHEN ? != '' THEN ? ELSE rules END,
                traps = CASE WHEN ? != '' THEN ? ELSE traps END,
                model_points = ?,
                active_for_july_2026 = 1,
                exam_year = ?,
                exam_season = ?,
                july_2026_status = 'Active standalone MEE',
                priority = 3,
                source = ?
            WHERE id = ?
            """,
            (
                record.subject,
                record.question_text,
                record.call_of_question,
                record.tested_issues,
                record.rules,
                record.rules,
                record.traps,
                record.traps,
                record.model_points,
                record.exam_year,
                record.exam_season,
                SOURCE_LABEL,
                question_id,
            ),
        )

    for record in inserts:
        conn.execute(
            """
            INSERT INTO questions (
                exam_name,
                question_number,
                subject,
                question_text,
                call_of_question,
                tested_issues,
                rules,
                trigger_facts,
                traps,
                model_points,
                active_for_july_2026,
                exam_year,
                exam_season,
                secondary_subjects,
                july_2026_status,
                priority,
                source
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, '', ?, ?, 1, ?, ?, '', 'Active standalone MEE', 3, ?)
            """,
            (
                record.exam_name,
                record.question_number,
                record.subject,
                record.question_text,
                record.call_of_question,
                record.tested_issues,
                record.rules,
                record.traps,
                record.model_points,
                record.exam_year,
                record.exam_season,
                SOURCE_LABEL,
            ),
        )

    conn.commit()
    conn.close()
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import a Markdown MEE Q&A bank into mee_trainer.db.")
    parser.add_argument("source", help="Path to the Markdown/text bank.")
    parser.add_argument("--apply", action="store_true", help="Write changes. Without this, runs a dry-run.")
    parser.add_argument(
        "--allow-truncated",
        action="store_true",
        help="Import records even when the pasted Markdown says the answer continues in JSONL.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source = Path(args.source)
    markdown = source.read_text(encoding="utf-8", errors="replace")
    records = parse_records(markdown)
    report = import_records(records, apply=args.apply, allow_truncated=args.allow_truncated)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
