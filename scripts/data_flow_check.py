# -*- coding: utf-8 -*-
"""Smoke-test the import/filter/practice data flow on a temporary DB.

Run from the project root:

    python scripts/data_flow_check.py
"""

import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import _bootstrap  # noqa: F401


ROOT = Path(__file__).resolve().parent.parent


SAMPLE_TEXT_BANK = """
Subject: Civil Procedure
Exam: February 2099
Year: 2099
Season: February

Question 1
Fact Pattern:
Plaintiff filed in federal court. Defendant moved to dismiss for lack of personal jurisdiction.

Call of the Question:
Should the federal court dismiss for lack of personal jurisdiction? Explain.

Answer:
The court should analyze minimum contacts, purposeful availment, and fairness before deciding whether dismissal is proper.

Rule Outline:
- Personal jurisdiction requires a statutory basis and constitutional minimum contacts.
- The defendant must purposefully avail itself of the forum.
- Exercising jurisdiction must be fair and reasonable.

Tested Issues:
- Personal jurisdiction
- Minimum contacts

Traps:
- Do not discuss subject-matter jurisdiction when the call asks personal jurisdiction.
"""


SAMPLE_PDF_BANK = """
Subject: Contracts
Exam: July 2098
Year: 2098
Season: July

Question 2
Fact Pattern:
A buyer and seller disputed whether a written agreement was modified by a later oral promise.

Call of the Question:
Is the later oral promise enforceable? Explain.

Answer:
The answer should discuss common-law modification, consideration, and whether any exception applies.

Rule Outline:
- A common-law contract modification generally requires consideration.
- A preexisting duty is not consideration.
- A later oral agreement may still matter if an exception applies.

Tested Issues:
- Contract modification
- Consideration

Traps:
- Do not apply Article 2 unless the transaction is primarily for goods.
"""


@dataclass
class UploadedBytes:
    name: str
    data: bytes

    def getvalue(self):
        return self.data


class Checker:
    def __init__(self):
        self.failures = []

    def check(self, label, condition, detail=""):
        if condition:
            print(f"OK   {label}")
            return

        suffix = f" - {detail}" if detail else ""
        print(f"FAIL {label}{suffix}")
        self.failures.append(f"{label}{suffix}")

    def exit_code(self):
        return 1 if self.failures else 0


def import_after_temp_db_is_set(temp_db_path):
    os.environ["MEE_TRAINER_DB"] = str(temp_db_path)

    import database
    from import_markdown_mee_qa_bank import parse_records
    from import_services import run_markdown_text_import, run_pdf_text_import

    return database, parse_records, run_markdown_text_import, run_pdf_text_import


def make_pdf_upload(text):
    import fitz

    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    rect = fitz.Rect(48, 48, 564, 744)
    page.insert_textbox(rect, text, fontsize=10, fontname="helv")
    data = doc.tobytes()
    doc.close()
    return UploadedBytes("sample_mini_bank.pdf", data)


def main():
    checker = Checker()
    real_db = ROOT / "mee_trainer.db"
    real_db_mtime = real_db.stat().st_mtime_ns if real_db.exists() else None

    with tempfile.TemporaryDirectory(prefix="mee_reflex_data_flow_") as tmp:
        temp_db = Path(tmp) / "flow_test.db"
        database, parse_records, run_markdown_text_import, run_pdf_text_import = import_after_temp_db_is_set(temp_db)

        database.init_db()
        checker.check("temporary DB was created", temp_db.exists())

        records = parse_records(SAMPLE_TEXT_BANK)
        checker.check("plain text import parses one record", len(records) == 1, str(len(records)))
        if records:
            record = records[0]
            checker.check("parsed record keeps subject", record.subject == "Civil Procedure", record.subject)
            checker.check("parsed record keeps answer", "minimum contacts" in record.model_points.lower(), record.model_points[:80])
            checker.check("parsed record keeps rule outline", "purposefully avail" in record.rules.lower(), record.rules[:80])

        _dry_records, dry_report = run_markdown_text_import(SAMPLE_TEXT_BANK, apply=False)
        checker.check("dry run reports one insert", dry_report.get("records_to_insert") == 1, str(dry_report))
        before_apply = database.fetch_one("SELECT COUNT(*) FROM questions")[0]
        checker.check("dry run does not write", before_apply == 0, str(before_apply))

        _apply_records, apply_report = run_markdown_text_import(SAMPLE_TEXT_BANK, apply=True)
        checker.check("apply reports one insert", apply_report.get("records_to_insert") == 1, str(apply_report))

        pdf_upload = make_pdf_upload(SAMPLE_PDF_BANK)
        pdf_text, pdf_records, pdf_report = run_pdf_text_import(pdf_upload, apply=False)
        checker.check("PDF import extracts text", "later oral promise" in pdf_text.lower(), pdf_text[:120])
        checker.check("PDF import parses one record", len(pdf_records) == 1, str(len(pdf_records)))
        checker.check("PDF dry run reports one insert", pdf_report.get("records_to_insert") == 1, str(pdf_report))

        _pdf_text_apply, _pdf_records_apply, pdf_apply_report = run_pdf_text_import(pdf_upload, apply=True)
        checker.check("PDF apply reports one insert", pdf_apply_report.get("records_to_insert") == 1, str(pdf_apply_report))

        rows = database.get_question_bank_rows(subject="Civil Procedure", topic="minimum contacts")
        checker.check("question bank filter finds imported row", len(rows) == 1, str(len(rows)))
        question_id = rows[0][0] if rows else None

        picker_rows = database.get_questions(
            active_only=True,
            subject="Civil Procedure",
            search="minimum contacts",
            practice_ready_only=True,
        )
        checker.check("practice-ready picker finds complete imported row", len(picker_rows) == 1, str(len(picker_rows)))

        database.add_question(
            exam_name="February 2099",
            question_number="99",
            subject="Civil Procedure",
            question_text="",
            call_of_question="Should this incomplete row be practiced?",
            tested_issues="Personal jurisdiction",
            rules="Minimum contacts.",
            trigger_facts="Forum contact.",
            traps="No trap.",
            model_points="Incomplete prompt row.",
            active_for_july_2026=True,
            exam_year=2099,
            exam_season="February",
            secondary_subjects="",
            july_2026_status="Active standalone MEE",
            priority=5,
            source="Data flow check",
        )
        incomplete_picker_rows = database.get_questions(
            active_only=True,
            subject="Civil Procedure",
            search="incomplete row",
            practice_ready_only=True,
        )
        checker.check("practice-ready picker skips incomplete rows", len(incomplete_picker_rows) == 0, str(len(incomplete_picker_rows)))

        if question_id:
            q = database.get_question_by_id(question_id)
            checker.check("question detail includes call", "personal jurisdiction" in (q[5] or "").lower(), q[5] if q else "")
            database.save_attempt(
                question_id,
                "Data Flow Check",
                "Issue: personal jurisdiction\nRule: minimum contacts\nConclusion: likely depends on contacts.",
                4,
                "No missed issues",
                "Smoke-test attempt",
                minutes_spent=7,
            )
            attempts = database.get_attempts(limit=5)
            checker.check("practice attempt was saved", len(attempts) == 1, str(len(attempts)))
            checker.check("attempt links to question", attempts[0][1] == question_id if attempts else False)
            refreshed = database.get_question_by_id(question_id)
            checker.check("practice updates last practiced", bool(refreshed and refreshed[19]), str(refreshed[19] if refreshed else ""))
            checker.check("practice schedules review", bool(refreshed and refreshed[20]), str(refreshed[20] if refreshed else ""))

        first_mbe_blob = {
            "version": 2,
            "cardStats": {
                "card-a": {
                    "timesSeen": 1,
                    "lastAnsweredAt": "2099-01-01T00:00:00",
                    "practiceHistory": [{"at": "2099-01-01T00:00:00", "correct": False}],
                }
            },
            "sessionLog": [{"at": "2099-01-01T00:00:00", "key": "card-a"}],
        }
        second_mbe_blob = {
            "version": 2,
            "cardStats": {
                "card-a": {
                    "timesSeen": 2,
                    "lastAnsweredAt": "2099-01-02T00:00:00",
                    "practiceHistory": [{"at": "2099-01-02T00:00:00", "correct": True}],
                },
                "card-b": {
                    "timesSeen": 1,
                    "lastAnsweredAt": "2099-01-02T01:00:00",
                    "practiceHistory": [{"at": "2099-01-02T01:00:00", "correct": True}],
                },
            },
        }
        checker.check("MBE practice stats first save succeeds", database.save_mbe_practice_stats("flow_user", first_mbe_blob))
        checker.check("MBE practice stats second save succeeds", database.save_mbe_practice_stats("flow_user", second_mbe_blob))
        saved_mbe_blob = database.get_mbe_practice_stats("flow_user") or {}
        saved_card_stats = saved_mbe_blob.get("cardStats") or {}
        checker.check("MBE practice stats preserve old card", "card-a" in saved_card_stats)
        checker.check("MBE practice stats merge new card", "card-b" in saved_card_stats)
        checker.check(
            "MBE practice stats merge history",
            len((saved_card_stats.get("card-a") or {}).get("practiceHistory") or []) == 2,
            str((saved_card_stats.get("card-a") or {}).get("practiceHistory")),
        )

    if real_db_mtime is not None and real_db.exists():
        checker.check("real mee_trainer.db was not modified", real_db.stat().st_mtime_ns == real_db_mtime)

    if checker.failures:
        print("\nData flow check failed:")
        for failure in checker.failures:
            print(f"- {failure}")
    else:
        print("\nData flow check passed.")

    return checker.exit_code()


if __name__ == "__main__":
    sys.exit(main())
