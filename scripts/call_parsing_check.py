# -*- coding: utf-8 -*-
"""Read-only audit of MEE call-of-the-question parsing plus parser regression fixtures.

For every question in the database this compares:
  - cleaned line count (clean_call_text)
  - extracted call count (extract_subquestions)
  - tested-issue bullet count (extract_issue_bullets)

and classifies any mismatch so we know whether the parser or the stored data
needs fixing.

Run from the project root:

    python scripts/call_parsing_check.py [--csv offenders.csv] [--all]

Exit code is non-zero when a regression fixture fails or an unexpected
mismatch exists among practice-ready questions.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

import _bootstrap  # noqa: F401 - adds the project root to sys.path.

from database import fetch_all
from text_rendering import clean_call_text, extract_issue_bullets, extract_subquestions


ROOT = Path(__file__).resolve().parent.parent

NUMBERED_LINE = re.compile(r"^(\d+)[.)]\s*")
SUBPART_LINE = re.compile(r"^([a-z][.)]|\(?[a-z]\)|\d+\([a-z]\)\.)\s*", re.IGNORECASE)
MULTI_CALL_SEGMENT = re.compile(r"\?\s*Explain\.", re.IGNORECASE)


def analyze_call(call_text):
    """Return parsing metrics and a mismatch classification for one call blob."""
    cleaned = clean_call_text(call_text or "")
    lines = [line for line in cleaned.splitlines() if line.strip()]
    subquestions = extract_subquestions(call_text or "")
    extracted = len(subquestions)

    has_numbered = any(NUMBERED_LINE.match(line) for line in lines)
    multi_call_lines = [
        line for line in lines if len(MULTI_CALL_SEGMENT.findall(line)) > 1
    ]

    mismatch = None
    if not lines:
        mismatch = "empty_call"
    elif multi_call_lines:
        mismatch = "multi_call_one_line"
    elif has_numbered:
        # Continuation and subpart lines fold into their parent question, so
        # only flag rows where a numbered call is lost or a preamble line
        # becomes its own question card.
        top_level = len({NUMBERED_LINE.match(line).group(1) for line in lines if NUMBERED_LINE.match(line)})
        if extracted < top_level:
            mismatch = "numbered_call_dropped"
        elif extracted > top_level:
            mismatch = "numbered_preamble_as_question"
    else:
        # Dropping context-only preamble lines is fine; flag only when a line
        # that itself contains a question fails to surface as a call.
        question_lines = sum(1 for line in lines if "?" in line)
        shared_assumptions = sum(
            1 for line in lines if line.endswith(":") and "?" not in line
        )
        if question_lines and extracted < question_lines:
            mismatch = "dropped_unnumbered_question"
        elif extracted > question_lines + shared_assumptions and question_lines:
            mismatch = "over_split_unnumbered"

    return {
        "cleaned_line_count": len(lines),
        "extracted_call_count": extracted,
        "mismatch_type": mismatch,
        "lines": lines,
        "subquestions": subquestions,
    }


def load_questions():
    rows = fetch_all(
        """
        SELECT id, exam_name, question_number, subject,
               call_of_question, tested_issues,
               active_for_july_2026, july_2026_status,
               question_text, model_points
        FROM questions
        ORDER BY id
        """
    )
    fields = [
        "id", "exam_name", "question_number", "subject",
        "call_of_question", "tested_issues",
        "active_for_july_2026", "july_2026_status",
        "question_text", "model_points",
    ]
    return [dict(zip(fields, row)) for row in rows]


def is_practice_ready(question):
    return bool(
        question["active_for_july_2026"]
        and str(question["question_text"] or "").strip()
        and str(question["call_of_question"] or "").strip()
        and str(question["model_points"] or "").strip()
    )


def audit(questions, include_all=False):
    offenders = []
    for question in questions:
        call = question["call_of_question"]
        if not str(call or "").strip():
            continue

        result = analyze_call(call)
        issue_count = len(extract_issue_bullets(question["tested_issues"] or ""))

        issues_mismatch = (
            issue_count > 0
            and result["extracted_call_count"] > 0
            and issue_count != result["extracted_call_count"]
        )

        if result["mismatch_type"] or (include_all and issues_mismatch):
            offenders.append(
                {
                    "id": question["id"],
                    "exam_name": question["exam_name"],
                    "question_number": question["question_number"],
                    "subject": question["subject"],
                    "practice_ready": is_practice_ready(question),
                    "cleaned_line_count": result["cleaned_line_count"],
                    "extracted_call_count": result["extracted_call_count"],
                    "issue_bullet_count": issue_count,
                    "mismatch_type": result["mismatch_type"]
                    or ("issues_calls_mismatch" if issues_mismatch else ""),
                    "first_line": (result["lines"][0][:120] if result["lines"] else ""),
                }
            )
    return offenders


def write_csv(path, offenders):
    fieldnames = [
        "id", "exam_name", "question_number", "subject", "practice_ready",
        "cleaned_line_count", "extracted_call_count", "issue_bullet_count",
        "mismatch_type", "first_line",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(offenders)


# --- Regression fixtures -----------------------------------------------------

FIXTURES = [
    {
        "name": "Q712-style 3-call unnumbered Torts (context-first opener)",
        "call": (
            "In a negligence action against Alan, can Brenda establish that Alan "
            "breached his duty of care based solely on his violation of the "
            "school-bus law? Explain.\n"
            "Can Brenda establish Alan's liability based on Alan's allegedly "
            "detaining her against her will? Explain.\n"
            "Is Alan's admission sufficient for the patient's family to prevail "
            "in a motion for partial summary judgment establishing that Alan is "
            "liable on the family's wrongful-death claim? Explain."
        ),
        "expected_count": 3,
    },
    {
        "name": "'On what basis' contextual opener",
        "call": (
            "On what basis, if any, could the XYZ limited partners challenge the "
            "actions of Gem Corp in selling the blue diamonds? Explain.\n"
            "Can the XYZ limited partners hold Gem Corp liable for the loss? Explain."
        ),
        "expected_count": 2,
    },
    {
        "name": "numbered calls with subparts must not over-split",
        "call": (
            "1. Did the officer's warrantless seizure violate the man's Fourth "
            "Amendment rights? Explain.\n"
            "2. Was the search valid under:\n"
            "a. the automobile exception? Explain.\n"
            "b. the search-incident-to-arrest exception? Explain."
        ),
        "expected_count": 2,
    },
    {
        "name": "multiple '? Explain.' calls mashed onto one line",
        "call": (
            "Funworld falsely imprisoned Paul? Explain. Funworld was negligent "
            "because Employee failed to take action to stop the boys? Explain. "
            "Funworld is vicariously liable for Employee's failure to act? Explain."
        ),
        "expected_count": 3,
    },
    {
        "name": "single call ending with '?' only (no Explain.)",
        "call": "Who is entitled to possession of Whiteacre?",
        "expected_count": 1,
    },
]


def run_fixtures():
    failures = []
    for fixture in FIXTURES:
        got = len(extract_subquestions(fixture["call"]))
        if got != fixture["expected_count"]:
            failures.append(
                f"{fixture['name']}: expected {fixture['expected_count']}, got {got}"
            )
    return failures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, help="Optional path to write the offender CSV.")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Also report issue-count/call-count mismatches (informational).",
    )
    args = parser.parse_args()

    fixture_failures = run_fixtures()
    print(f"Regression fixtures: {len(FIXTURES) - len(fixture_failures)}/{len(FIXTURES)} passed")
    for failure in fixture_failures:
        print(f"  FAIL {failure}")

    questions = load_questions()
    offenders = audit(questions, include_all=args.all)
    practice_ready_offenders = [
        o for o in offenders if o["practice_ready"] and o["mismatch_type"] != "issues_calls_mismatch"
    ]

    print(f"\nQuestions scanned: {len(questions)}")
    print(f"Offenders: {len(offenders)}")
    print(f"Practice-ready parse offenders: {len(practice_ready_offenders)}")

    by_type = {}
    for offender in offenders:
        by_type[offender["mismatch_type"]] = by_type.get(offender["mismatch_type"], 0) + 1
    for mismatch_type, count in sorted(by_type.items()):
        print(f"  {mismatch_type}: {count}")

    for offender in offenders:
        print(
            "  #{id} {exam_name} Q{question_number} [{subject}] "
            "lines={cleaned_line_count} calls={extracted_call_count} "
            "issues={issue_bullet_count} type={mismatch_type}\n"
            "      {first_line}".format(**offender)
        )

    if args.csv:
        write_csv(args.csv, offenders)
        print(f"\nWrote CSV: {args.csv}")

    if fixture_failures or practice_ready_offenders:
        sys.exit(1)


if __name__ == "__main__":
    main()
