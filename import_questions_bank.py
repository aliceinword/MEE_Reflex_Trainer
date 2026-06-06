"""Import a personal MEE question bank (.md) into the questions table.

Expected Markdown structure:

    # Subject Name
    ## February 1997 - Question 4
    **Summary:** ...                 (optional, ignored)
    **Original Question:**
    <fact pattern paragraphs and the calls>
    ---

Answers (issues, rules, traps, model points) are intentionally left blank so
they can be filled in later from a separate answer document.

Usage:
    python import_questions_bank.py "MEE_Question_Extraction_By_Compiled_Topics.md"

Re-running is safe: a question with the same exam + number + subject + source
is skipped.
"""

import re
import sys
from pathlib import Path

from database import init_db, add_question, get_connection

SOURCE_LABEL = "MEE Question Bank (my import)"

HEADING_RE = re.compile(r"^(February|July)\s+(\d{4})\s+[‒–—\-]\s*Question\s+(\S+)$")


def split_question_and_call(full_text):
    """Best-effort split of the fact pattern from the call(s)."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", full_text.strip()) if p.strip()]
    if not paragraphs:
        return full_text.strip(), ""

    # A trailing block of numbered calls (each call its own paragraph).
    call_start = None
    for i, para in enumerate(paragraphs):
        if re.match(r"^\d+\.\s+", para) and i >= max(1, len(paragraphs) * 0.3):
            call_start = i
            break

    if call_start is not None:
        fact = "\n\n".join(paragraphs[:call_start]).strip()
        call = "\n\n".join(paragraphs[call_start:]).strip()
        return fact, call

    # A single short trailing paragraph that reads like a call.
    last = paragraphs[-1]
    if len(last) < 400 and re.search(r"(Explain\.?|Discuss\.?|\?)\s*$", last):
        return "\n\n".join(paragraphs[:-1]).strip(), last

    return full_text.strip(), ""


def question_exists(conn, exam_name, question_number, subject):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT 1 FROM questions
        WHERE exam_name = ? AND question_number = ? AND subject = ? AND source = ?
        LIMIT 1
        """,
        (exam_name, question_number, subject, SOURCE_LABEL),
    )
    return cur.fetchone() is not None


def main(path):
    path = Path(path)
    if not path.exists():
        print(f"File not found: {path}")
        return

    init_db()
    conn = get_connection()

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    subject = None
    meta = None          # (exam_name, year, season, number)
    mode = None          # None | "collect"
    buffer = []
    added = skipped = 0

    def flush():
        nonlocal added, skipped, meta, buffer
        if not (subject and meta and buffer):
            meta = None
            buffer = []
            return
        exam_name, year, season, number = meta
        body = "\n".join(buffer).strip()
        if body:
            if question_exists(conn, exam_name, number, subject):
                skipped += 1
            else:
                fact_and_call, call = split_question_and_call(body)
                add_question(
                    exam_name=exam_name,
                    question_number=number,
                    subject=subject,
                    question_text=body,
                    call_of_question=call,
                    tested_issues="",
                    rules="",
                    trigger_facts="",
                    traps="",
                    model_points="",
                    active_for_july_2026=True,
                    exam_year=year,
                    exam_season=season,
                    secondary_subjects="",
                    july_2026_status="Active standalone MEE",
                    priority=3,
                    source=SOURCE_LABEL,
                )
                added += 1
        meta = None
        buffer = []

    for line in lines:
        stripped = line.strip()

        if line.startswith("## "):
            flush()
            match = HEADING_RE.match(stripped[3:].strip())
            if match:
                season, year, number = match.group(1), int(match.group(2)), match.group(3)
                meta = (f"{season} {year}", year, season, number)
            else:
                meta = None
            mode = None
        elif line.startswith("# "):
            flush()
            subject = stripped[2:].strip()
            mode = None
        elif stripped == "**Original Question:**":
            mode = "collect"
            buffer = []
        elif stripped == "---":
            flush()
            mode = None
        elif mode == "collect":
            buffer.append(line)

    flush()
    conn.close()
    print(f"Imported {added} question(s); skipped {skipped} already present.")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "MEE_Question_Extraction_By_Compiled_Topics.md"
    main(target)
