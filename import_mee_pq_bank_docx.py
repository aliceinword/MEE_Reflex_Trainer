# -*- coding: utf-8 -*-
"""Import questions and full analyses from MEE_PQ_Bank.docx.

The source document is a compiled Word bank with two formats:

* older exams: "February 1997 MEE" + "QUESTIONS"/"ANALYSES", then
  "SUBJECT QUESTION" / "SUBJECT ANALYSIS" headings;
* newer exams: "February 2025 MEE Questions"/"Analyses", then
  "QUESTION 1 - SUBJECT" / "ANALYSIS 1 - SUBJECT" headings.

This importer is intentionally read-only by default. Use --apply to update the
SQLite database; a timestamped backup is created before any write.
"""

from __future__ import annotations

import argparse
import io
import re
import shutil
import sqlite3
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET

from database import DB_NAME, init_db, now
from text_cleanup import normalize_extracted_text


SOURCE_LABEL = "MEE_PQ_Bank.docx"

EXAM_RE = re.compile(r"^(February|July)\s+(\d{4})\s+MEE$", re.I)
NEW_SECTION_RE = re.compile(r"^(February|July)\s+(\d{4})\s+MEE\s+(Questions|Analyses)$", re.I)
OPTIONAL_EXAM_PREFIX = r"(?:(?:February|July)\s+\d{4}\s+MEE\s+)?"
MODERN_QUESTION_RE = re.compile(
    rf"^{OPTIONAL_EXAM_PREFIX}QUESTION\s+(\d+)\s*[-\u2010-\u2015\u2212]\s*(.+)$",
    re.I,
)
MODERN_ANALYSIS_RE = re.compile(
    rf"^{OPTIONAL_EXAM_PREFIX}ANALYSIS\s+(\d+)\s*[-\u2010-\u2015\u2212]\s*(.+)$",
    re.I,
)
OLD_QUESTION_RE = re.compile(r"^([A-Z][A-Z '&/\-.]+)\s+QUESTION$")
OLD_ANALYSIS_RE = re.compile(r"^([A-Z][A-Z '&/\-.]+)\s+ANALYSIS$")
LEGACY_QUESTION_RE = re.compile(r"^(February|July)\s+(\d{4}),\s+Question\s+(\d+)$", re.I)
LEGACY_ANALYSIS_RE = re.compile(
    r"^(February|July)\s+(\d{4}),\s+Question\s+(\d+)\s+Analysis(?:\s+(.+))?$",
    re.I,
)
YEAR_PACKET_RE = re.compile(r"^\d{4}\s+MEE$", re.I)

INCLUDED_SUBJECTS = {
    "Agency & Partnership",
    "Civil Procedure",
    "Constitutional Law",
    "Contracts / Sales",
    "Corporations & LLCs",
    "Criminal Law & Procedure",
    "Evidence",
    "Real Property",
    "Torts",
}

EXCLUDED_ONLY_MARKERS = (
    "DECEDENTS",
    "ESTATES",
    "FAMILY",
    "TRUST",
    "SECURED",
    "COMMERCIAL PAPER",
    "NEGOTIABLE",
    "CONFLICT",
)


@dataclass
class Section:
    exam_name: str
    exam_year: int
    exam_season: str
    kind: str
    start: int
    content_start: int
    end: int = 0


@dataclass
class ParsedBlock:
    exam_name: str
    exam_year: int
    exam_season: str
    question_number: str
    raw_subject: str
    subject: str
    secondary_subjects: str
    question_text: str = ""
    call_of_question: str = ""
    tested_issues: str = ""
    model_points: str = ""


def clean_text(text: str) -> str:
    text = normalize_extracted_text(text or "")
    text = text.replace("\u00a0", " ")
    text = text.replace("\uf0b7", "- ")
    text = text.replace("ง", "§")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def docx_paragraphs(path: Path) -> list[str]:
    ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    with ZipFile(path) as archive:
        xml = archive.read("word/document.xml")

    paragraphs: list[str] = []
    for _event, elem in ET.iterparse(io.BytesIO(xml), events=("end",)):
        if elem.tag == ns + "p":
            text = "".join(t.text or "" for t in elem.iter(ns + "t")).strip()
            if text:
                paragraphs.append(clean_text(text))
            elem.clear()
    return paragraphs


def normalize_exam(month: str, year: str) -> str:
    month = month.lower().capitalize()
    return f"{month} {year}"


def normalize_subject(raw_subject: str) -> tuple[str | None, str]:
    raw = re.sub(r"\s+", " ", raw_subject or "").strip()
    upper = raw.upper()
    upper = re.sub(r"\b[A-Z]{2,4}\s*\([^)]*\)\s*$", "", upper).strip()
    upper = re.sub(r"\([^)]*\)\s*$", "", upper).strip()
    upper = upper.replace("COROPRATIONS", "CORPORATIONS")

    found: list[str] = []
    if "AGENCY" in upper or "PARTNERSHIP" in upper:
        found.append("Agency & Partnership")
    if "CIVIL PROCEDURE" in upper or "FEDERAL CIVIL PROCEDURE" in upper:
        found.append("Civil Procedure")
    if "CONSTITUTIONAL" in upper:
        found.append("Constitutional Law")
    if "CONTRACT" in upper or "SALES" in upper:
        found.append("Contracts / Sales")
    if "CORPORATION" in upper or "LLC" in upper or "LIMITED LIABILITY" in upper:
        found.append("Corporations & LLCs")
    if "CRIMINAL" in upper:
        found.append("Criminal Law & Procedure")
    if "EVIDENCE" in upper:
        found.append("Evidence")
    if "REAL PROPERTY" in upper or upper == "PROPERTY":
        found.append("Real Property")
    if "TORT" in upper:
        found.append("Torts")

    unique = []
    for subject in found:
        if subject not in unique:
            unique.append(subject)

    if unique:
        return unique[0], ", ".join(unique[1:])

    if any(marker in upper for marker in EXCLUDED_ONLY_MARKERS):
        return None, ""

    return None, ""


def section_starts(paragraphs: list[str]) -> list[Section]:
    starts: list[Section] = []

    for index, paragraph in enumerate(paragraphs):
        if YEAR_PACKET_RE.match(paragraph):
            year = int(paragraph.split()[0])
            starts.append(
                Section(
                    exam_name=f"Packet {year}",
                    exam_year=year,
                    exam_season="",
                    kind="boundary",
                    start=index,
                    content_start=index + 1,
                )
            )
            continue

        new_match = NEW_SECTION_RE.match(paragraph)
        if new_match:
            month, year, kind = new_match.groups()
            starts.append(
                Section(
                    exam_name=normalize_exam(month, year),
                    exam_year=int(year),
                    exam_season=month.lower().capitalize(),
                    kind=kind.lower(),
                    start=index,
                    content_start=index + 1,
                )
            )
            continue

        exam_match = EXAM_RE.match(paragraph)
        if not exam_match:
            continue

        for lookahead in range(index + 1, min(index + 6, len(paragraphs))):
            marker = paragraphs[lookahead].upper()
            if marker in {"QUESTIONS", "ANALYSES"}:
                month, year = exam_match.groups()
                starts.append(
                    Section(
                        exam_name=normalize_exam(month, year),
                        exam_year=int(year),
                        exam_season=month.lower().capitalize(),
                        kind=marker.lower(),
                        start=index,
                        content_start=lookahead + 1,
                    )
                )
                break

    starts.sort(key=lambda section: section.start)
    deduped: list[Section] = []
    for section in starts:
        if deduped and deduped[-1].start == section.start and deduped[-1].kind == section.kind:
            continue
        deduped.append(section)

    for index, section in enumerate(deduped):
        section.end = deduped[index + 1].start if index + 1 < len(deduped) else len(paragraphs)

    return deduped


def is_exam_noise(line: str, raw_subject: str = "") -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if EXAM_RE.match(stripped):
        return True
    if re.match(r"^(February|July)\s+\d{4}\s+MEE\s+(Questions|Analyses|Questions and Analyses)$", stripped, re.I):
        return True
    if stripped in {"QUESTIONS", "ANALYSES", "ANALYSIS", "DISCUSSION", "Contents", "Preface", "Instructions"}:
        return True
    if raw_subject:
        subject_words = re.sub(r"[^A-Za-z&/ ]+", "", raw_subject).strip()
        page_header_re = re.compile(rf"^{re.escape(subject_words)}\s+(Question|Analysis)$", re.I)
        if page_header_re.match(stripped) and stripped != stripped.upper():
            return True
    return False


def question_heading(line: str) -> tuple[str | None, str | None]:
    modern = MODERN_QUESTION_RE.match(line)
    if modern:
        return modern.group(1), modern.group(2)

    old = OLD_QUESTION_RE.match(line)
    if old:
        return None, old.group(1)

    return None, None


def analysis_heading(line: str) -> tuple[str | None, str | None]:
    modern = MODERN_ANALYSIS_RE.match(line)
    if modern:
        return modern.group(1), modern.group(2)

    old = OLD_ANALYSIS_RE.match(line)
    if old:
        return None, old.group(1)

    return None, None


def legacy_analysis_heading(line: str) -> tuple[str | None, str | None, str | None, str | None]:
    match = LEGACY_ANALYSIS_RE.match(line)
    if not match:
        return None, None, None, None
    month, year, number, raw_subject = match.groups()
    return month, year, number, raw_subject


def call_like(line: str) -> bool:
    line = line.strip()
    if not line:
        return False
    if len(line) > 650:
        return False
    if re.search(r"(Explain\.?|Discuss\.?|\?)$", line):
        return True
    if re.match(r"^\(?[a-z0-9]+\)?[.)]\s+", line, re.I) and len(line) < 350:
        return True
    return False


def split_question_and_call(lines: list[str]) -> tuple[str, str]:
    lines = [line.strip() for line in lines if line.strip()]
    if not lines:
        return "", ""

    call_start = len(lines)
    index = len(lines) - 1
    while index >= 0 and call_like(lines[index]):
        call_start = index
        index -= 1

    while call_start > 0 and re.match(
        r"^(Assuming|In answering|Evaluate|For each|If|When)\b", lines[call_start - 1], re.I
    ) and len(lines[call_start - 1]) < 350:
        call_start -= 1

    if call_start == len(lines):
        joined = "\n\n".join(lines)
        inline = re.search(r"(?<![\w.])1\.\s+", joined)
        if inline and inline.start() > len(joined) * 0.45:
            return joined[: inline.start()].strip(), joined[inline.start() :].strip()
        return joined, ""

    return "\n\n".join(lines[:call_start]).strip(), "\n".join(lines[call_start:]).strip()


def extract_legal_problems(analysis_text: str) -> str:
    match = re.search(
        r"(?is)\bLegal Problems:?\s*(.*?)(?:\n\s*(?:DISCUSSION|Summary|Point\s+One|Point\s+1)\b)",
        analysis_text,
    )
    if not match:
        return ""
    text = clean_text(match.group(1))
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def clean_block_lines(lines: list[str], raw_subject: str) -> list[str]:
    cleaned: list[str] = []
    for line in lines:
        if is_exam_noise(line, raw_subject):
            continue
        cleaned.append(line)
    return cleaned


def parse_question_section(section: Section, paragraphs: list[str]) -> list[ParsedBlock]:
    indices: list[tuple[int, str | None, str]] = []
    for index in range(section.content_start, section.end):
        number, raw_subject = question_heading(paragraphs[index])
        if raw_subject:
            indices.append((index, number, raw_subject))

    blocks: list[ParsedBlock] = []
    ordinal = 0
    for item_index, (start, number, raw_subject) in enumerate(indices):
        ordinal += 1
        end = indices[item_index + 1][0] if item_index + 1 < len(indices) else section.end
        subject, secondary_subjects = normalize_subject(raw_subject)
        if subject not in INCLUDED_SUBJECTS:
            continue

        question_number = str(number or ordinal)
        body_lines = clean_block_lines(paragraphs[start + 1 : end], raw_subject)
        question_text, call_text = split_question_and_call(body_lines)
        blocks.append(
            ParsedBlock(
                exam_name=section.exam_name,
                exam_year=section.exam_year,
                exam_season=section.exam_season,
                question_number=question_number,
                raw_subject=raw_subject,
                subject=subject,
                secondary_subjects=secondary_subjects,
                question_text=question_text,
                call_of_question=call_text,
            )
        )
    return blocks


def parse_analysis_section(section: Section, paragraphs: list[str]) -> dict[str, ParsedBlock]:
    indices: list[tuple[int, str | None, str]] = []
    for index in range(section.content_start, section.end):
        number, raw_subject = analysis_heading(paragraphs[index])
        if raw_subject:
            indices.append((index, number, raw_subject))

    blocks: dict[str, ParsedBlock] = {}
    ordinal = 0
    for item_index, (start, number, raw_subject) in enumerate(indices):
        ordinal += 1
        end = indices[item_index + 1][0] if item_index + 1 < len(indices) else section.end
        subject, secondary_subjects = normalize_subject(raw_subject)
        if subject not in INCLUDED_SUBJECTS:
            continue

        question_number = str(number or ordinal)
        body_lines = [paragraphs[start]] + clean_block_lines(paragraphs[start + 1 : end], raw_subject)
        model_points = clean_text("\n\n".join(body_lines))
        blocks[question_number] = ParsedBlock(
            exam_name=section.exam_name,
            exam_year=section.exam_year,
            exam_season=section.exam_season,
            question_number=question_number,
            raw_subject=raw_subject,
            subject=subject,
            secondary_subjects=secondary_subjects,
            model_points=model_points,
            tested_issues=extract_legal_problems(model_points),
        )
    return blocks


def parse_legacy_question_blocks(paragraphs: list[str]) -> dict[tuple[str, str], tuple[str, str]]:
    indices: list[tuple[int, str, str, str]] = []
    for index, paragraph in enumerate(paragraphs):
        match = LEGACY_QUESTION_RE.match(paragraph)
        if match:
            month, year, number = match.groups()
            indices.append((index, month, year, number))

    analysis_starts = [index for index, paragraph in enumerate(paragraphs) if LEGACY_ANALYSIS_RE.match(paragraph)]
    blocks: dict[tuple[str, str], tuple[str, str]] = {}

    for item_index, (start, month, year, number) in enumerate(indices):
        next_question = indices[item_index + 1][0] if item_index + 1 < len(indices) else len(paragraphs)
        next_analysis = min((idx for idx in analysis_starts if idx > start), default=len(paragraphs))
        end = min(next_question, next_analysis)
        lines = paragraphs[start + 1 : end]
        lines = [
            line
            for line in lines
            if line.strip()
            and not re.fullmatch(rf"{re.escape(month)}\s+{year}", line, re.I)
            and not re.fullmatch(rf"Question\s+{number}", line, re.I)
        ]
        question_text, call_text = split_question_and_call(lines)
        blocks[db_key(normalize_exam(month, year), number)] = (question_text, call_text)

    return blocks


def parse_legacy_analysis_blocks(paragraphs: list[str]) -> dict[tuple[str, str], ParsedBlock]:
    indices: list[tuple[int, str, str, str, str]] = []
    current_month: str | None = None
    current_year: str | None = None
    next_number: int | None = None

    for index, paragraph in enumerate(paragraphs):
        month, year, number, raw_subject = legacy_analysis_heading(paragraph)
        if month and year and number:
            if not raw_subject:
                for probe in paragraphs[index + 1 : min(index + 5, len(paragraphs))]:
                    if re.fullmatch(r"Question\s+\d+\s+Analysis", probe, re.I):
                        continue
                    subject, _secondary = normalize_subject(probe)
                    has_excluded_marker = any(marker in probe.upper() for marker in EXCLUDED_ONLY_MARKERS)
                    if subject in INCLUDED_SUBJECTS or has_excluded_marker:
                        raw_subject = probe
                    break
                if not raw_subject:
                    continue

            indices.append((index, month, year, number, raw_subject or ""))
            current_month = month
            current_year = year
            next_number = int(number) + 1
            continue

        # Some legacy conversions omit "Question N Analysis" before later
        # blocks and leave only "SUBJECT ROMAN-NUMERAL OUTLINE" + "ANALYSIS".
        if (
            current_month
            and current_year
            and next_number
            and next_number <= 9
            and index + 1 < len(paragraphs)
            and paragraphs[index + 1].strip().upper() == "ANALYSIS"
            and paragraph == paragraph.upper()
            and "QUESTION" not in paragraph.upper()
        ):
            subject, _secondary = normalize_subject(paragraph)
            if subject in INCLUDED_SUBJECTS:
                indices.append((index, current_month, current_year, str(next_number), paragraph))
                next_number += 1

    blocks: dict[tuple[str, str], ParsedBlock] = {}
    for item_index, (start, month, year, number, raw_subject) in enumerate(indices):
        end = indices[item_index + 1][0] if item_index + 1 < len(indices) else len(paragraphs)
        if not raw_subject:
            for probe in paragraphs[start + 1 : min(start + 4, end)]:
                if probe.strip() and not re.fullmatch(r"Question\s+\d+\s+Analysis", probe, re.I):
                    raw_subject = probe
                    break

        subject, secondary_subjects = normalize_subject(raw_subject)
        if subject not in INCLUDED_SUBJECTS:
            continue

        body_lines = clean_block_lines(paragraphs[start:end], raw_subject)
        model_points = clean_text("\n\n".join(body_lines))
        exam_name = normalize_exam(month, year)
        blocks[db_key(exam_name, number)] = ParsedBlock(
            exam_name=exam_name,
            exam_year=int(year),
            exam_season=month.lower().capitalize(),
            question_number=number,
            raw_subject=raw_subject,
            subject=subject,
            secondary_subjects=secondary_subjects,
            model_points=model_points,
            tested_issues=extract_legal_problems(model_points),
        )
    return blocks


def parse_docx(path: Path) -> list[ParsedBlock]:
    paragraphs = docx_paragraphs(path)
    sections = section_starts(paragraphs)
    analyses_by_exam: dict[str, dict[str, ParsedBlock]] = {}
    questions: list[ParsedBlock] = []
    legacy_questions = parse_legacy_question_blocks(paragraphs)
    legacy_analyses = parse_legacy_analysis_blocks(paragraphs)

    for section in sections:
        if section.kind == "questions":
            questions.extend(parse_question_section(section, paragraphs))
        elif section.kind == "analyses":
            analyses_by_exam.setdefault(section.exam_name.lower(), {}).update(
                parse_analysis_section(section, paragraphs)
            )

    merged: list[ParsedBlock] = []
    seen_keys: set[tuple[str, str]] = set()
    for question in questions:
        analysis = analyses_by_exam.get(question.exam_name.lower(), {}).get(question.question_number)
        if analysis:
            question.model_points = analysis.model_points
            question.tested_issues = analysis.tested_issues
            if not question.secondary_subjects:
                question.secondary_subjects = analysis.secondary_subjects
        merged.append(question)
        seen_keys.add(db_key(question.exam_name, question.question_number))

    # Several newer Word conversions preserve the analysis headings but lose the
    # matching question headings. Existing rows already have those fact patterns,
    # so analysis-only entries are still valuable for repairing model_points.
    for exam_key, analyses in analyses_by_exam.items():
        for question_number, analysis in analyses.items():
            key = db_key(analysis.exam_name, question_number)
            if key in seen_keys:
                continue
            merged.append(analysis)
            seen_keys.add(key)

    for key, analysis in legacy_analyses.items():
        question_parts = legacy_questions.get(key)
        if question_parts:
            analysis.question_text = question_parts[0]
            analysis.call_of_question = question_parts[1]
        for existing in merged:
            if db_key(existing.exam_name, existing.question_number) == key:
                existing.model_points = analysis.model_points
                existing.tested_issues = analysis.tested_issues
                existing.raw_subject = analysis.raw_subject
                existing.subject = analysis.subject
                existing.secondary_subjects = analysis.secondary_subjects
                if analysis.question_text:
                    existing.question_text = analysis.question_text
                if analysis.call_of_question:
                    existing.call_of_question = analysis.call_of_question
                break
        else:
            merged.append(analysis)
            seen_keys.add(key)

    return merged


def backup_db(db_path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.with_name(f"{db_path.stem}_backup_before_mee_pq_bank_{timestamp}{db_path.suffix}")
    shutil.copy2(db_path, backup_path)
    return backup_path


def db_key(exam_name: str, question_number: str) -> tuple[str, str]:
    return (str(exam_name or "").strip().lower(), str(question_number or "").strip().lower())


def upsert_database(entries: list[ParsedBlock], apply: bool, overwrite: bool) -> dict[str, object]:
    init_db()
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT id, exam_name, question_number, subject, model_points
        FROM questions
        """
    ).fetchall()
    existing = {db_key(row[1], row[2]): row for row in rows}

    stats = Counter()
    short_answers: list[ParsedBlock] = []
    unmatched_without_answer: list[ParsedBlock] = []

    for entry in entries:
        key = db_key(entry.exam_name, entry.question_number)
        target = existing.get(key)

        short_model = len(entry.model_points or "") < 500
        if short_model:
            short_answers.append(entry)

        if target:
            question_id, _exam_name, _question_number, _subject, old_model = target
            if short_model:
                stats["skipped_short_update"] += 1
                continue

            if old_model and old_model.strip() and not overwrite:
                stats["skipped_existing"] += 1
                continue

            if apply:
                cur.execute(
                    """
                    UPDATE questions
                    SET
                        subject = ?,
                        question_text = COALESCE(NULLIF(?, ''), question_text),
                        call_of_question = COALESCE(NULLIF(?, ''), call_of_question),
                        tested_issues = COALESCE(NULLIF(?, ''), tested_issues),
                        model_points = COALESCE(NULLIF(?, ''), model_points),
                        exam_year = ?,
                        exam_season = ?,
                        secondary_subjects = ?,
                        july_2026_status = ?,
                        active_for_july_2026 = 1,
                        priority = CASE WHEN priority IS NULL OR priority < 3 THEN 3 ELSE priority END,
                        source = ?
                    WHERE id = ?
                    """,
                    (
                        entry.subject,
                        entry.question_text,
                        entry.call_of_question,
                        entry.tested_issues,
                        entry.model_points,
                        entry.exam_year,
                        entry.exam_season,
                        entry.secondary_subjects,
                        "Active standalone MEE",
                        SOURCE_LABEL,
                        question_id,
                    ),
                )
            stats["updated" if apply else "would_update"] += 1
            continue

        if not entry.model_points:
            unmatched_without_answer.append(entry)

        if short_model:
            stats["skipped_short_insert"] += 1
            continue

        if apply:
            cur.execute(
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
                    source,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.exam_name,
                    entry.question_number,
                    entry.subject,
                    entry.question_text,
                    entry.call_of_question,
                    entry.tested_issues,
                    "",
                    "",
                    "",
                    entry.model_points,
                    1,
                    entry.exam_year,
                    entry.exam_season,
                    entry.secondary_subjects,
                    "Active standalone MEE",
                    3,
                    SOURCE_LABEL,
                    now(),
                ),
            )
        stats["inserted" if apply else "would_insert"] += 1

    if apply:
        conn.commit()
    conn.close()

    return {
        "stats": stats,
        "short_answers": short_answers,
        "unmatched_without_answer": unmatched_without_answer,
    }


def print_report(entries: list[ParsedBlock], result: dict[str, object], apply: bool) -> None:
    stats: Counter = result["stats"]  # type: ignore[assignment]
    with_answers = sum(1 for entry in entries if len(entry.model_points or "") >= 500)
    subject_counts = Counter(entry.subject for entry in entries)
    short_answers: list[ParsedBlock] = result["short_answers"]  # type: ignore[assignment]

    print("MEE PQ Bank DOCX Import")
    print("======================")
    print(f"Parsed included questions: {len(entries)}")
    print(f"Questions with usable analyses: {with_answers}")
    print(f"Would update: {stats.get('would_update', 0)}")
    print(f"Would insert: {stats.get('would_insert', 0)}")
    print(f"Updated: {stats.get('updated', 0)}")
    print(f"Inserted: {stats.get('inserted', 0)}")
    print(f"Skipped existing: {stats.get('skipped_existing', 0)}")
    print(f"Skipped short updates: {stats.get('skipped_short_update', 0)}")
    print(f"Skipped short inserts: {stats.get('skipped_short_insert', 0)}")
    print("Subjects:")
    for subject, count in subject_counts.most_common():
        print(f"  {subject}: {count}")

    if short_answers:
        print("Short/missing analyses:")
        for entry in short_answers[:25]:
            print(
                f"  {entry.exam_name} Q{entry.question_number} "
                f"{entry.subject}: {len(entry.model_points or '')} chars"
            )

    if not apply:
        print("Dry run only. Re-run with --apply to write changes.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Import MEE_PQ_Bank.docx into mee_trainer.db.")
    parser.add_argument("docx", nargs="?", default="MEE_PQ_Bank.docx")
    parser.add_argument("--apply", action="store_true", help="Write changes to the database.")
    parser.add_argument("--overwrite", action="store_true", help="Replace existing model_points.")
    args = parser.parse_args()

    docx_path = Path(args.docx)
    if not docx_path.exists():
        raise FileNotFoundError(docx_path)

    entries = parse_docx(docx_path)
    backup_path = None
    if args.apply:
        backup_path = backup_db(Path(DB_NAME))
        print(f"Backup created: {backup_path}")

    result = upsert_database(entries, apply=args.apply, overwrite=args.overwrite)
    print_report(entries, result, args.apply)
    if backup_path:
        print(f"Backup path: {backup_path}")


if __name__ == "__main__":
    main()
