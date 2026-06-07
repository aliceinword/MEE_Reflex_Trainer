# -*- coding: utf-8 -*-

import csv
import re
import sqlite3
from pathlib import Path


DB_PATH = Path("mee_trainer.db")
CSV_PATH = Path("sample_answer_audit.csv")


POINT_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}


def extract_subquestions_simple(call_text):
    text = str(call_text or "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\s+", " ", text).strip()

    if not text:
        return 0

    top_level = re.findall(r"(?:^|\s)(\d+)\.\s+", text)
    top_numbers = []

    for raw in top_level:
        try:
            num = int(raw)
        except ValueError:
            continue
        if num not in top_numbers:
            top_numbers.append(num)

    if top_numbers:
        return len(top_numbers)

    # Subparts alone still indicate at least one call.
    if re.search(r"(?:^|\s)[a-z]\.\s+", text, flags=re.IGNORECASE):
        return 1

    return 1


def split_model_answer_points_simple(model_text):
    text = str(model_text or "")
    pattern = re.compile(
        r"(?i)(Point\s+(One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten)|Point\s+(\d+))(?:\s*\([^)]*\))?"
    )

    points = []

    for match in pattern.finditer(text):
        word_num = match.group(2)
        digit_num = match.group(3)

        if word_num:
            num = POINT_WORDS.get(word_num.lower())
        else:
            try:
                num = int(digit_num)
            except (TypeError, ValueError):
                num = None

        if num is not None:
            points.append(num)

    return points


def audit_status(subquestion_count, points, model_points_length, has_structured_bank=False):
    point_count = len(points)
    unique_points = sorted(set(points))
    missing_specific_points = [
        str(num) for num in range(1, subquestion_count + 1)
        if num not in unique_points
    ]

    if model_points_length < 100:
        if has_structured_bank:
            return (
                "STRUCTURED_FALLBACK",
                "No usable model_points, but issue/rule/fact fields can render structured model analysis.",
                missing_specific_points,
                "YES_STRUCTURED_FALLBACK",
            )
        return "MISSING_MODEL", "No usable model_points.", missing_specific_points, "NO"

    if subquestion_count > 1 and point_count == 0:
        return (
            "NO_POINT_SPLIT",
            "Multiple calls but model answer has no Point headings. App will show full available model analysis for each call.",
            missing_specific_points,
            "YES_FULL_FALLBACK",
        )

    if unique_points in ([2], [3]):
        return (
            "PARTIAL_MODEL",
            "Only later point detected; likely split/import issue. App will show full available model analysis for missing calls.",
            missing_specific_points,
            "YES_FULL_FALLBACK",
        )

    if subquestion_count > point_count:
        return (
            "POSSIBLY_INCOMPLETE",
            "Fewer model answer points than subquestions. App will show full available model analysis for missing calls.",
            missing_specific_points,
            "YES_FULL_FALLBACK",
        )

    return "OK", "", missing_specific_points, "YES_EXACT_POINTS"


def load_questions(db_path):
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                id,
                exam_name,
                question_number,
                subject,
                call_of_question,
                model_points,
                rules,
                tested_issues,
                trigger_facts,
                traps,
                source
            FROM questions
            ORDER BY id
            """
        )
        return cur.fetchall()
    finally:
        conn.close()


def main():
    if not DB_PATH.exists():
        raise SystemExit(f"Database not found: {DB_PATH.resolve()}")

    rows = load_questions(DB_PATH)
    audit_rows = []
    counts = {
        "OK": 0,
        "MISSING_MODEL": 0,
        "STRUCTURED_FALLBACK": 0,
        "NO_POINT_SPLIT": 0,
        "POSSIBLY_INCOMPLETE": 0,
        "PARTIAL_MODEL": 0,
    }

    for row in rows:
        (
            question_id,
            exam_name,
            question_number,
            subject,
            call_of_question,
            model_points,
            rules,
            tested_issues,
            trigger_facts,
            traps,
            source,
        ) = row

        model_points = model_points or ""
        structured_text = " ".join(
            str(value or "")
            for value in (tested_issues, rules, trigger_facts, traps)
        )
        has_structured_bank = bool(structured_text.strip())
        subquestion_count = extract_subquestions_simple(call_of_question)
        points = split_model_answer_points_simple(model_points)
        model_points_length = len(model_points.strip())
        status, notes, missing_specific_points, display_answer_coverage = audit_status(
            subquestion_count,
            points,
            model_points_length,
            has_structured_bank=has_structured_bank,
        )
        counts[status] = counts.get(status, 0) + 1

        audit_rows.append(
            {
                "question_id": question_id,
                "exam_name": exam_name,
                "question_number": question_number,
                "subject": subject,
                "source": source,
                "subquestion_count": subquestion_count,
                "point_count": len(points),
                "detected_points": ",".join(str(p) for p in points),
                "model_points_length": model_points_length,
                "status": status,
                "notes": notes,
                "missing_specific_points": ",".join(missing_specific_points),
                "display_answer_coverage": display_answer_coverage,
            }
        )

    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "question_id",
                "exam_name",
                "question_number",
                "subject",
                "source",
                "subquestion_count",
                "point_count",
                "detected_points",
                "model_points_length",
                "status",
                "notes",
                "missing_specific_points",
                "display_answer_coverage",
            ],
        )
        writer.writeheader()
        writer.writerows(audit_rows)

    print("Sample Answer Audit")
    print("===================")
    print(f"Total questions checked: {len(audit_rows)}")
    for status in [
        "OK",
        "MISSING_MODEL",
        "STRUCTURED_FALLBACK",
        "NO_POINT_SPLIT",
        "POSSIBLY_INCOMPLETE",
        "PARTIAL_MODEL",
    ]:
        print(f"{status}: {counts.get(status, 0)}")
    covered = sum(1 for row in audit_rows if row["display_answer_coverage"] != "NO")
    exact = sum(1 for row in audit_rows if row["display_answer_coverage"] == "YES_EXACT_POINTS")
    fallback = sum(1 for row in audit_rows if row["display_answer_coverage"] == "YES_FULL_FALLBACK")
    missing = sum(1 for row in audit_rows if row["display_answer_coverage"] == "NO")
    print(f"Display-covered questions: {covered}")
    print(f"Exact point coverage: {exact}")
    print(f"Covered by full-answer fallback: {fallback}")
    print(f"Missing display coverage: {missing}")
    print(f"CSV written to: {CSV_PATH.resolve()}")


if __name__ == "__main__":
    main()
