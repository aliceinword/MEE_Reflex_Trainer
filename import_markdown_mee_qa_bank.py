from __future__ import annotations

import argparse
import json
import re
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import database
from text_cleanup import normalize_extracted_text


SOURCE_LABEL = "MEE Question-Answer Bank Markdown import"


SUBJECT_NORMALIZATION = {
    "AGENCY & PARTNERSHIP": "Agency & Partnership",
    "AGENCY & PARTNERSHIP/CORPORATIONS": "Agency & Partnership",
    "AGENCY & PARTNERSHIP / CORPORATIONS": "Agency & Partnership",
    "AGENCY & PARTNERSHIP/TORTS": "Agency & Partnership",
    "AGENCY & PARTNERSHIP / TORTS": "Agency & Partnership",
    "CIVIL PROCEDURE": "Civil Procedure",
    "FEDERAL CIVIL PROCEDURE": "Civil Procedure",
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
    exam_year: int | None
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


def _canonical_simple_label(label: str) -> str:
    label = clean_text(label).lower()
    label = re.sub(r"^#+\s*", "", label)
    label = re.sub(r"\s+", " ", label).strip(" :.-\u2013\u2014")

    if re.fullmatch(r"q\s*\d+|question(?:\s+(?:no\.?|number|#))?\s*\d*|prompt", label):
        return "question"
    if label in {"fact pattern", "facts"}:
        return "question"
    if label in {"call", "call of the question", "questions asked", "question asked"}:
        return "call"
    if label in {"answer", "sample answer", "model answer", "model analysis", "full analysis", "analysis"}:
        return "answer"
    if label in {"rule outline", "rules", "rule", "rule(s)", "rules & doctrine", "rules and doctrine"}:
        return "rules"
    if label in {"tested issues", "key legal issues", "issues", "issue outline"}:
        return "issues"
    if label in {"traps", "exam traps", "exam traps & examiner notes", "exam traps and examiner notes"}:
        return "traps"
    if label in {"subject", "exam", "exam name", "year", "season"}:
        return label.replace("exam name", "exam")
    return ""


def _restore_simple_heading_breaks(text: str) -> str:
    """Restore line breaks before plain import headings that PDF cleanup may join."""
    heading = (
        r"Subject|Exam Name|Exam|Year|Season|"
        r"Question(?:\s+(?:No\.?|Number|#)?\s*\d+)?|Q\s*\d+|"
        r"Prompt|Fact Pattern|Call(?: of the Question)?|Questions Asked|"
        r"Answer|Sample Answer|Model Answer|Model Analysis|Full Analysis|Analysis|"
        r"Rule Outline|Rules?|Rule\(s\)|Rules & Doctrine|Rules and Doctrine|"
        r"Tested Issues|Key Legal Issues|Issues|Issue Outline|"
        r"Traps|Exam Traps(?: & Examiner Notes| and Examiner Notes)?"
    )
    restored = re.sub(
        rf"(?<!^)\s+(?=(?:{heading})\s*[:\-\u2013\u2014])",
        "\n",
        str(text or ""),
    )
    composite_repairs = [
        (r"\b(Tested)\n(Issues\s*[:\-\u2013\u2014])", r"\1 \2"),
        (r"\b(Key Legal)\n(Issues\s*[:\-\u2013\u2014])", r"\1 \2"),
        (r"\b(Issue)\n(Outline\s*[:\-\u2013\u2014])", r"\1 \2"),
        (r"\b(Sample|Model)\n(Answer\s*[:\-\u2013\u2014])", r"\1 \2"),
        (r"\b(Model|Full)\n(Analysis\s*[:\-\u2013\u2014])", r"\1 \2"),
        (r"\b(Exam)\n(Traps\s*[:\-\u2013\u2014])", r"\1 \2"),
        (r"\b(Call of the)\n(Question\s*[:\-\u2013\u2014])", r"\1 \2"),
    ]
    for pattern, replacement in composite_repairs:
        restored = re.sub(pattern, replacement, restored, flags=re.IGNORECASE)

    return restored


def _split_simple_labelled_sections(text: str) -> tuple[dict[str, str], dict[str, str]]:
    """Split a plain Question/Answer/Rule Outline block into sections."""
    text = _restore_simple_heading_breaks(text)
    sections: dict[str, list[str]] = {}
    metadata: dict[str, str] = {}
    current_label = ""
    heading_re = re.compile(
        r"^\s*(?:#{1,6}\s*)?"
        r"(?P<label>"
        r"Q\s*\d+|Question(?:\s+(?:No\.?|Number|#)?\s*\d+)?|Prompt|Fact Pattern|Facts|"
        r"Call(?: of the Question)?|Questions Asked|Question Asked|"
        r"Answer|Sample Answer|Model Answer|Model Analysis|Full Analysis|Analysis|"
        r"Rule Outline|Rules?|\bRule\(s\)|Rules & Doctrine|Rules and Doctrine|"
        r"Tested Issues|Key Legal Issues|Issues|Issue Outline|"
        r"Traps|Exam Traps(?: & Examiner Notes| and Examiner Notes)?|"
        r"Subject|Exam Name|Exam|Year|Season"
        r")"
        r"\s*(?:[:\-\u2013\u2014]\s*(?P<rest>.*))?$",
        flags=re.IGNORECASE,
    )

    for raw_line in str(text or "").replace("\r\n", "\n").replace("\r", "\n").splitlines():
        line = raw_line.strip()
        match = heading_re.match(line)

        if match and (match.group("rest") is not None or line.startswith("#") or len(line.split()) <= 6):
            canonical = _canonical_simple_label(match.group("label"))
            if canonical:
                current_label = canonical
                rest = clean_text(match.group("rest") or "")
                if canonical in {"subject", "exam", "year", "season"}:
                    if rest:
                        metadata[canonical] = rest
                        current_label = ""
                    else:
                        sections.setdefault(canonical, [])
                else:
                    sections.setdefault(canonical, [])
                    if rest:
                        sections[canonical].append(rest)
                continue

        if current_label:
            sections.setdefault(current_label, []).append(raw_line)

    collapsed = {label: clean_text("\n".join(lines)) for label, lines in sections.items()}

    for label in ("subject", "exam", "year", "season"):
        if label not in metadata and collapsed.get(label):
            metadata[label] = collapsed[label]

    return collapsed, metadata


def _extract_simple_metadata(text: str) -> dict[str, str]:
    _sections, metadata = _split_simple_labelled_sections(text)
    return metadata


def _parse_exam_year(value: str) -> int | None:
    match = re.search(r"\b(19\d{2}|20\d{2})\b", str(value or ""))
    return int(match.group(1)) if match else None


def _parse_exam_season(value: str) -> str:
    if re.search(r"\bFeb(?:ruary)?\b", str(value or ""), flags=re.IGNORECASE):
        return "February"
    if re.search(r"\bJul(?:y)?\b", str(value or ""), flags=re.IGNORECASE):
        return "July"
    return "Other"


def _simple_question_blocks(text: str) -> list[tuple[str | None, str]]:
    """Return plain records that begin with Question/Q headings."""
    text = _restore_simple_heading_breaks(text)
    start_re = re.compile(
        r"(?im)^\s*(?:#{1,6}\s*)?(?:Question(?:\s+(?:No\.?|Number|#)?)?|Q)\s*(?P<num>\d+)?\s*(?::|[-\u2013\u2014])?.*$"
    )
    starts = list(start_re.finditer(text))

    if not starts:
        sections, _metadata = _split_simple_labelled_sections(text)
        if sections.get("question") and (sections.get("answer") or sections.get("rules")):
            return [(None, text)]
        return []

    blocks: list[tuple[str | None, str]] = []
    for index, start in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        blocks.append((start.group("num"), text[start.start():end]))

    return blocks


def parse_simple_qa_records(text: str) -> list[ParsedRecord]:
    """Parse plain text/PDF banks that use Question -> Answer -> Rule Outline headings."""
    text = _restore_simple_heading_breaks(normalize_extracted_text(str(text or "")))
    if not text.strip():
        return []

    blocks = _simple_question_blocks(text)
    if not blocks:
        return []

    first_start = text.find(blocks[0][1]) if blocks and blocks[0][1] else 0
    global_metadata = _extract_simple_metadata(text[:max(first_start, 0)])
    records: list[ParsedRecord] = []

    for index, (detected_number, block) in enumerate(blocks, start=1):
        sections, metadata = _split_simple_labelled_sections(block)
        merged_metadata = {**global_metadata, **metadata}

        question_text = clean_text(sections.get("question", ""))
        model_points = clean_text(sections.get("answer", ""))
        rules = markdown_list_to_lines(sections.get("rules", ""))

        if not question_text or not (model_points or rules):
            continue

        subject = normalize_subject(merged_metadata.get("subject", "")) if merged_metadata.get("subject") else "Uncategorized"
        exam_name = clean_text(merged_metadata.get("exam", "")) or "Imported Text Bank"
        exam_year = _parse_exam_year(merged_metadata.get("year", "") or exam_name)
        exam_season = clean_text(merged_metadata.get("season", "")) or _parse_exam_season(exam_name)
        question_number = str(int(detected_number or index))

        records.append(
            ParsedRecord(
                source_id=f"TEXT-Q{int(question_number):02d}",
                exam_name=exam_name,
                exam_year=exam_year,
                exam_season=exam_season,
                question_number=question_number,
                subject=subject,
                raw_subject=merged_metadata.get("subject", subject),
                question_text=question_text,
                call_of_question=clean_text(sections.get("call", "")),
                tested_issues=markdown_list_to_lines(sections.get("issues", "")),
                rules=rules,
                traps=markdown_list_to_lines(sections.get("traps", "")),
                model_points=model_points,
                is_truncated=False,
            )
        )

    return records


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

    if records:
        return records

    return parse_simple_qa_records(markdown)


def backup_db(db_path: Path) -> Path:
    backup = db_path.with_name(f"{db_path.stem}_backup_before_markdown_qa_import_{datetime.now():%Y%m%d_%H%M%S}{db_path.suffix}")
    shutil.copy2(db_path, backup)
    return backup


def current_db_path() -> Path:
    """Return the currently configured app database path."""
    return Path(database.DB_NAME)


def import_records(records: list[ParsedRecord], apply: bool, allow_truncated: bool) -> dict:
    db_path = current_db_path()
    question_map = database.get_question_import_index()
    skipped_truncated = [record for record in records if record.is_truncated and not allow_truncated]
    importable_records = [record for record in records if allow_truncated or not record.is_truncated]

    updates = []
    inserts = []
    for record in importable_records:
        existing_row = question_map.get(database.question_import_key(record.exam_name, record.question_number))
        if existing_row:
            updates.append((existing_row[0], record))
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
        return report

    report["backup"] = str(backup_db(db_path))
    conn = sqlite3.connect(db_path)

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
