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


def clean_text(text):
    text = normalize_extracted_text(text or "")
    text = text.replace("\uf0b7", "\n- ")
    text = text.replace("ï‚·", "\n- ")
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def compact_lines(text):
    lines = []
    for line in clean_text(text).splitlines():
        line = line.strip()
        if not line:
            continue
        if re.fullmatch(r"[-\u2014\u2013_ ]{5,}", line):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def read_pdf_text(pdf_path):
    doc = fitz.open(pdf_path)
    return "\n".join(page.get_text("text") for page in doc)


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


def normalize_exam(month, year):
    return f"{month} {year}"


def extract_answer_path(body):
    question_summary = extract_between(
        body,
        "Question summary:",
        ["Issues tested:"],
    )

    answer_path = extract_between(
        body,
        "Condensed sample-answer path:",
        ["Question call(s):"],
    )

    if not answer_path:
        return ""

    if question_summary:
        return (
            f"Question summary:\n{question_summary}\n\n"
            f"Condensed sample-answer path:\n{answer_path}"
        ).strip()

    return f"Condensed sample-answer path:\n{answer_path}".strip()


def parse_entries(raw_text):
    text = raw_text or ""
    matches = list(ENTRY_HEADER_RE.finditer(text))
    entries = []

    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        model_points = extract_answer_path(body)

        entries.append(
            {
                "exam_name": normalize_exam(match.group(1), match.group(2)),
                "question_number": match.group(3),
                "model_points": model_points,
            }
        )

    return entries


def backup_db(db_path):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.with_name(
        f"{db_path.stem}_backup_before_condensed_answer_overwrite_{timestamp}{db_path.suffix}"
    )
    shutil.copy2(db_path, backup_path)
    return backup_path


def db_key(exam_name, question_number):
    return (str(exam_name or "").strip().lower(), str(question_number or "").strip().lower())


def update_database(entries, apply=False, overwrite=False):
    init_db()
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, exam_name, question_number, model_points
        FROM questions
        """
    )
    question_rows = cur.fetchall()
    questions_by_key = {}
    duplicate_db_keys = []

    for question_id, exam_name, question_number, model_points in question_rows:
        key = db_key(exam_name, question_number)
        if key in questions_by_key:
            duplicate_db_keys.append((exam_name, question_number))
        questions_by_key[key] = (question_id, model_points or "")

    stats = Counter()
    unmatched = []
    skipped_existing = []
    empty_entries = []

    entry_counts = Counter(db_key(e["exam_name"], e["question_number"]) for e in entries)
    duplicate_entry_keys = [key for key, count in entry_counts.items() if count > 1]

    for entry in entries:
        key = db_key(entry["exam_name"], entry["question_number"])
        target = questions_by_key.get(key)

        if not target:
            unmatched.append((entry["exam_name"], entry["question_number"]))
            stats["unmatched"] += 1
            continue

        model_points = entry["model_points"].strip()
        if len(model_points) < 100:
            empty_entries.append((entry["exam_name"], entry["question_number"]))
            stats["empty_or_short"] += 1
            continue

        question_id, existing_model_points = target
        if existing_model_points.strip() and not overwrite:
            skipped_existing.append((entry["exam_name"], entry["question_number"], question_id))
            stats["skipped_existing"] += 1
            continue

        if apply:
            cur.execute(
                "UPDATE questions SET model_points = ? WHERE id = ?",
                (model_points, question_id),
            )

        stats["updated" if apply else "would_update"] += 1

    if apply:
        conn.commit()

    conn.close()

    return {
        "stats": stats,
        "unmatched": unmatched,
        "skipped_existing": skipped_existing,
        "empty_entries": empty_entries,
        "duplicate_entry_keys": duplicate_entry_keys,
        "duplicate_db_keys": duplicate_db_keys,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Import condensed sample answers into questions.model_points."
    )
    parser.add_argument("pdf", help="Path to MEE_Condensed_Sample_Answers_By_Subject.pdf")
    parser.add_argument("--apply", action="store_true", help="Write changes to the database.")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing model_points. Without this, only blank model_points are filled.",
    )
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)

    raw_text = read_pdf_text(pdf_path)
    entries = parse_entries(raw_text)

    print("Condensed Answer Import")
    print("=======================")
    print(f"Parsed answer blocks: {len(entries)}")

    backup_path = None
    if args.apply:
        backup_path = backup_db(Path(DB_NAME))
        print(f"Backup created: {backup_path}")

    result = update_database(entries, apply=args.apply, overwrite=args.overwrite)
    stats = result["stats"]

    print(f"Would update: {stats.get('would_update', 0)}")
    print(f"Updated: {stats.get('updated', 0)}")
    print(f"Skipped existing: {stats.get('skipped_existing', 0)}")
    print(f"Unmatched: {stats.get('unmatched', 0)}")
    print(f"Empty/short skipped: {stats.get('empty_or_short', 0)}")

    if result["duplicate_entry_keys"]:
        print("Duplicate PDF keys:")
        for exam_name, question_number in result["duplicate_entry_keys"][:20]:
            print(f"  {exam_name} Q{question_number}")

    if result["duplicate_db_keys"]:
        print("Duplicate DB keys:")
        for exam_name, question_number in result["duplicate_db_keys"][:20]:
            print(f"  {exam_name} Q{question_number}")

    if result["unmatched"]:
        print("Unmatched entries:")
        for exam_name, question_number in result["unmatched"][:30]:
            print(f"  {exam_name} Q{question_number}")

    if result["empty_entries"]:
        print("Empty/short entries:")
        for exam_name, question_number in result["empty_entries"][:30]:
            print(f"  {exam_name} Q{question_number}")

    if not args.apply:
        print("Dry run only. Re-run with --apply to write changes.")


if __name__ == "__main__":
    main()
