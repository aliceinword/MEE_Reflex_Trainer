"""Import a personal MEE question bank (.docx) into the questions table.

This reader uses Word paragraph styles to separate the call(s) from the fact
pattern, which the plain-Markdown reader could not always do:

    Heading 1        -> Subject
    Heading 2        -> "February 1997 - Question 4"
    First Paragraph  -> "Summary: ..." (first one per question; ignored)
                        and occasional fact-pattern continuation paragraphs
    Body Text        -> "Original Question:" label + fact-pattern paragraphs
    Compact          -> fact-pattern continuation
    Normal           -> the call(s) of the question (one per paragraph)

When a question has no Normal call paragraphs, the call is inline in the last
fact paragraph and is split off heuristically.

Usage:
    python import_questions_docx.py "MEE_Question_Extraction_By_Compiled_Topics.docx"

Re-running is safe: questions already present (same exam + number + subject +
source) are skipped.
"""

import re
import sys
from pathlib import Path

from docx import Document

from database import init_db, add_question, get_connection

SOURCE_LABEL = "MEE Question Bank (my import)"

HEADING_RE = re.compile(r"^(February|July)\s+(\d{4})\s+[‒–—\-]\s*Question\s+(\S+)$")
QUESTION_ARTIFACT_RE = re.compile(r"^Question\s+\d+$", re.IGNORECASE)


def split_question_and_call(full_text):
    """Fallback split for questions whose call is inline in the fact text."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", full_text.strip()) if p.strip()]
    if not paragraphs:
        return full_text.strip(), ""

    last = paragraphs[-1]

    # 1) Inline numbered call list ("... 1. ... 2. ...") in the latter part of
    #    the paragraph. Require a following "2." so we don't grab stray "1."s
    #    from the fact pattern (dates, dollar amounts, section numbers).
    num = re.search(r"(?<![\w.])1\.\s+\S", last)
    if num and num.start() > len(last) * 0.25 and re.search(r"(?<![\w.])2\.\s", last[num.end():]):
        call = last[num.start():].strip()
        fact_tail = last[: num.start()].strip()
        head = paragraphs[:-1] + ([fact_tail] if fact_tail else [])
        return "\n\n".join(head).strip(), call

    # 2) Trailing call sentences (each ends with Explain./Discuss./?).
    sentences = re.split(r"(?<=[.?!])\s+", last)
    call_run = []
    for sentence in reversed(sentences):
        stripped = sentence.strip()
        if stripped and len(stripped) < 400 and re.search(r"(Explain\.?|Discuss\.?|\?)$", stripped):
            call_run.insert(0, stripped)
        else:
            break
    if call_run:
        call = " ".join(call_run)
        kept = " ".join(s.strip() for s in sentences[: len(sentences) - len(call_run)]).strip()
        head = paragraphs[:-1] + ([kept] if kept else [])
        return "\n\n".join(head).strip(), call

    return full_text.strip(), ""


def number_calls(calls):
    cleaned = [re.sub(r"^\s*\d+[\.\)]\s*", "", c).strip() for c in calls if c.strip()]
    if not cleaned:
        return ""
    if len(cleaned) == 1:
        return cleaned[0]
    return "\n".join(f"{i}. {c}" for i, c in enumerate(cleaned, 1))


def question_exists(conn, exam_name, number, subject):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT 1 FROM questions
        WHERE exam_name = ? AND question_number = ? AND subject = ? AND source = ?
        LIMIT 1
        """,
        (exam_name, number, subject, SOURCE_LABEL),
    )
    return cur.fetchone() is not None


def main(path):
    path = Path(path)
    if not path.exists():
        print(f"File not found: {path}")
        return

    init_db()
    conn = get_connection()
    doc = Document(str(path))

    subject = None
    meta = None
    facts = []
    calls = []
    seen_summary = False
    added = skipped = 0

    def flush():
        nonlocal added, skipped, meta, facts, calls, seen_summary
        if subject and meta:
            exam_name, year, season, number = meta
            if facts or calls:
                if question_exists(conn, exam_name, number, subject):
                    skipped += 1
                else:
                    if calls:
                        question_text = "\n\n".join(facts).strip()
                        call_text = number_calls(calls)
                    else:
                        question_text, call_text = split_question_and_call("\n\n".join(facts))
                    add_question(
                        exam_name=exam_name,
                        question_number=number,
                        subject=subject,
                        question_text=question_text,
                        call_of_question=call_text,
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
        facts = []
        calls = []
        seen_summary = False

    for paragraph in doc.paragraphs:
        style = paragraph.style.name
        text = paragraph.text.strip()
        if not text:
            continue

        if style == "Heading 1":
            flush()
            subject = text
        elif style == "Heading 2":
            flush()
            match = HEADING_RE.match(text)
            meta = (f"{match.group(1)} {match.group(2)}", int(match.group(2)), match.group(1), match.group(3)) if match else None
        elif meta is None:
            continue
        elif style == "First Paragraph":
            if not seen_summary and text.lower().startswith("summary:"):
                seen_summary = True
            else:
                facts.append(text)
        elif style == "Normal":
            calls.append(text)
        elif style in ("Body Text", "Compact"):
            if text == "Original Question:" or QUESTION_ARTIFACT_RE.match(text):
                continue
            facts.append(text)

    flush()
    conn.close()
    print(f"Imported {added} question(s); skipped {skipped} already present.")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "MEE_Question_Extraction_By_Compiled_Topics.docx"
    main(target)
