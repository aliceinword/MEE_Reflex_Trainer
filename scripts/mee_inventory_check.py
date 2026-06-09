# -*- coding: utf-8 -*-
"""Read-only MEE question-bank inventory and content diagnostics."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

import _bootstrap  # noqa: F401 - adds the project root to sys.path.

from database import fetch_all


ROOT = Path(__file__).resolve().parent.parent


QUESTION_FIELDS = [
    "id",
    "exam_name",
    "question_number",
    "subject",
    "question_text",
    "call_of_question",
    "tested_issues",
    "rules",
    "trigger_facts",
    "traps",
    "model_points",
    "active_for_july_2026",
    "created_at",
    "exam_year",
    "exam_season",
    "secondary_subjects",
    "july_2026_status",
    "priority",
    "source",
    "last_practiced_at",
    "next_review_at",
]


def _norm(value):
    text = str(value or "").lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _short(value, limit=100):
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[: limit - 3] + "..." if len(text) > limit else text


def _rows_as_dicts(rows):
    return [dict(zip(QUESTION_FIELDS, row)) for row in rows]


def load_questions():
    rows = fetch_all(
        """
        SELECT
            id,
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
            created_at,
            exam_year,
            exam_season,
            secondary_subjects,
            july_2026_status,
            priority,
            source,
            last_practiced_at,
            next_review_at
        FROM questions
        ORDER BY exam_year DESC, exam_season DESC, question_number, id
        """
    )
    return _rows_as_dicts(rows)


def identity_key(question):
    return "|".join(
        [
            _norm(question["exam_name"]),
            _norm(question["question_number"]),
            _norm(question["subject"]),
        ]
    )


def content_fingerprint(question):
    return "|".join(
        [
            _norm(question["question_text"])[:500],
            _norm(question["call_of_question"])[:300],
            _norm(question["model_points"])[:500],
        ]
    )


def summarize(questions):
    by_subject = {}
    by_status = {}
    by_source = {}
    missing = {
        "prompt": [],
        "call": [],
        "sample_answer": [],
        "rules": [],
        "tested_issues": [],
        "trigger_facts": [],
    }

    identity_groups = {}
    content_groups = {}

    for question in questions:
        subject = question["subject"] or "Uncategorized"
        status = question["july_2026_status"] or "No status"
        source = question["source"] or "App database"
        by_subject[subject] = by_subject.get(subject, 0) + 1
        by_status[status] = by_status.get(status, 0) + 1
        by_source[source] = by_source.get(source, 0) + 1

        checks = {
            "prompt": question["question_text"],
            "call": question["call_of_question"],
            "sample_answer": question["model_points"],
            "rules": question["rules"],
            "tested_issues": question["tested_issues"],
            "trigger_facts": question["trigger_facts"],
        }
        for label, value in checks.items():
            if not str(value or "").strip():
                missing[label].append(question)

        ident = identity_key(question)
        if ident:
            identity_groups.setdefault(ident, []).append(question)
        fp = content_fingerprint(question)
        if fp and fp != "||":
            content_groups.setdefault(fp, []).append(question)

    return {
        "total_questions": len(questions),
        "active_questions": sum(1 for q in questions if q["active_for_july_2026"]),
        "practice_ready_questions": sum(
            1
            for q in questions
            if q["active_for_july_2026"]
            and str(q["question_text"] or "").strip()
            and str(q["call_of_question"] or "").strip()
            and str(q["model_points"] or "").strip()
        ),
        "by_subject": by_subject,
        "by_status": by_status,
        "by_source": by_source,
        "missing": missing,
        "identity_dupes": [group for group in identity_groups.values() if len(group) > 1],
        "content_dupes": [group for group in content_groups.values() if len(group) > 1],
    }


def print_grouped_counts(title, counts):
    print(f"\n{title}:")
    if not counts:
        print("  none")
        return
    for label, count in sorted(counts.items()):
        print(f"  {label}: {count}")


def print_missing(summary):
    print("\nMissing field checks:")
    for label, rows in summary["missing"].items():
        print(f"  missing {label}: {len(rows)}")
        for question in rows[:5]:
            print(
                "    #{id} {exam_name} Q{question_number} - {subject} - {source}".format(
                    **question
                )
            )


def print_dupes(summary):
    print("\nDuplicate checks:")
    print(f"  duplicate exam/question/subject identities: {len(summary['identity_dupes'])}")
    print(f"  duplicate content fingerprints: {len(summary['content_dupes'])}")

    for label, groups in (
        ("identity", summary["identity_dupes"]),
        ("content", summary["content_dupes"]),
    ):
        for group in groups[:10]:
            ids = ", ".join(str(q["id"]) for q in group)
            sample = group[0]
            print(
                f"  {label} dupe ids [{ids}] - "
                f"{sample['exam_name']} Q{sample['question_number']} - "
                f"{sample['subject']} - {_short(sample['source'])}"
            )


def write_csv(path, questions):
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "id",
                "exam_name",
                "question_number",
                "subject",
                "exam_year",
                "exam_season",
                "status",
                "priority",
                "source",
                "has_prompt",
                "has_call",
                "has_sample_answer",
                "has_rules",
                "has_tested_issues",
                "has_trigger_facts",
            ],
        )
        writer.writeheader()
        for question in questions:
            writer.writerow(
                {
                    "id": question["id"],
                    "exam_name": question["exam_name"],
                    "question_number": question["question_number"],
                    "subject": question["subject"],
                    "exam_year": question["exam_year"],
                    "exam_season": question["exam_season"],
                    "status": question["july_2026_status"],
                    "priority": question["priority"],
                    "source": question["source"],
                    "has_prompt": bool(str(question["question_text"] or "").strip()),
                    "has_call": bool(str(question["call_of_question"] or "").strip()),
                    "has_sample_answer": bool(str(question["model_points"] or "").strip()),
                    "has_rules": bool(str(question["rules"] or "").strip()),
                    "has_tested_issues": bool(str(question["tested_issues"] or "").strip()),
                    "has_trigger_facts": bool(str(question["trigger_facts"] or "").strip()),
                }
            )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, help="Optional path to write a question inventory CSV.")
    args = parser.parse_args()

    questions = load_questions()
    summary = summarize(questions)

    print(f"Database: {ROOT / 'mee_trainer.db'}")
    print(f"Total MEE questions: {summary['total_questions']}")
    print(f"Active MEE questions: {summary['active_questions']}")
    print(f"Practice-ready MEE questions: {summary['practice_ready_questions']}")

    print_grouped_counts("By subject", summary["by_subject"])
    print_grouped_counts("By status", summary["by_status"])
    print_grouped_counts("By source", summary["by_source"])
    print_missing(summary)
    print_dupes(summary)

    if args.csv:
        write_csv(args.csv, questions)
        print(f"\nWrote CSV: {args.csv}")


if __name__ == "__main__":
    main()
