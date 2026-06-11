# -*- coding: utf-8 -*-

import os
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from daily_error_sheet_service import run_daily_error_sheet_job, send_daily_error_sheet_for_user
from missed_answer_service import (
    build_daily_error_report,
    event_date_for_timestamp,
    record_bridge_drill_miss,
    record_mee_ladder_miss,
    render_daily_error_report_text,
)


class DailyErrorSheetTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._db_path = Path(self._tmpdir.name) / "test.db"
        os.environ["MEE_TRAINER_DB"] = str(self._db_path)
        os.environ["EMAIL_DRY_RUN"] = "1"
        os.environ["EMAIL_FROM_ADDRESS"] = "errors@example.com"

        import database

        self.database = database
        database.DB_NAME = str(self._db_path)
        database.reset_database_file_cache()
        database._db_ready = False
        database._db_file_ready = False
        database.invalidate_read_cache()
        database.init_db()
        self.database.execute_write(
            """
            INSERT INTO app_users (username, email, name, password_hash, is_admin)
            VALUES (?, ?, ?, ?, 0)
            """,
            ("alice", "alice@example.com", "Alice", "hash"),
        )

    def tearDown(self):
        self.database.reset_database_file_cache()
        self.database._db_ready = False
        self.database._db_file_ready = False
        self.database.invalidate_read_cache()
        self._tmpdir.cleanup()
        os.environ.pop("MEE_TRAINER_DB", None)

    def test_bridge_miss_is_recorded(self):
        recorded = record_bridge_drill_miss(
            "alice",
            card_uid="card-1",
            subject="Contracts",
            subtopic="Consideration",
            picked_letter="B",
            correct_letter="A",
            event_at="2026-06-11 20:15:00",
        )
        self.assertTrue(recorded)
        rows = self.database.get_missed_answer_events_for_date("alice", "2026-06-11")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][4], "bridge_drill")

    def test_mee_weak_score_is_recorded(self):
        recorded = record_mee_ladder_miss(
            "alice",
            question_id=42,
            subject="Torts",
            mode="Mini Drill",
            self_score=2,
            missed_issues="Duty",
            response_text="No duty",
            rules_text="A duty exists when...",
            question_prompt="Did defendant owe a duty?",
            event_at="2026-06-11 18:00:00",
        )
        self.assertTrue(recorded)
        rows = self.database.get_missed_answer_events_for_date("alice", "2026-06-11")
        self.assertEqual(len(rows), 1)
        self.assertIn("duty exists", (rows[0][10] or "").lower())

    def test_high_mee_score_is_not_recorded(self):
        recorded = record_mee_ladder_miss(
            "alice",
            question_id=43,
            subject="Torts",
            mode="Level 1",
            self_score=5,
            missed_issues="",
            response_text="Strong answer",
            rules_text="Rule text",
            question_prompt="Question",
            event_at="2026-06-11 18:05:00",
        )
        self.assertFalse(recorded)

    def test_report_groups_by_rule(self):
        record_bridge_drill_miss(
            "alice",
            card_uid="card-1",
            subject="Contracts",
            subtopic="Consideration",
            picked_letter="B",
            correct_letter="A",
            event_at="2026-06-11 10:00:00",
        )
        record_bridge_drill_miss(
            "alice",
            card_uid="card-2",
            subject="Contracts",
            subtopic="Consideration",
            picked_letter="C",
            correct_letter="A",
            event_at="2026-06-11 11:00:00",
        )
        report = build_daily_error_report("alice", "2026-06-11")
        self.assertEqual(report.total_missed, 2)
        self.assertEqual(len(report.rule_groups), 1)
        self.assertEqual(report.rule_groups[0].count, 2)
        body = render_daily_error_report_text(report)
        self.assertIn("Correct rule:", body)
        self.assertIn("Missed 2 time(s).", body)
        self.assertIn("Total missed questions: 2", body)

    def test_email_not_sent_twice(self):
        record_bridge_drill_miss(
            "alice",
            card_uid="card-1",
            subject="Contracts",
            subtopic="Consideration",
            picked_letter="B",
            correct_letter="A",
            event_at="2026-06-11 10:00:00",
        )
        first = send_daily_error_sheet_for_user("alice", "2026-06-11", force=True)
        second = send_daily_error_sheet_for_user("alice", "2026-06-11", force=False)
        self.assertEqual(first["status"], "sent")
        self.assertEqual(second["status"], "already_sent")

    def test_user_with_no_misses_is_skipped(self):
        result = send_daily_error_sheet_for_user("alice", "2026-06-11", force=True)
        self.assertEqual(result["status"], "skipped_no_misses")

    def test_manual_trigger_sends_when_forced(self):
        record_bridge_drill_miss(
            "alice",
            card_uid="card-1",
            subject="Contracts",
            subtopic="Consideration",
            picked_letter="B",
            correct_letter="A",
            event_at="2026-06-11 10:00:00",
        )
        result = send_daily_error_sheet_for_user("alice", "2026-06-11", force=True)
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "sent")

    def test_timezone_date_boundary(self):
        utc_evening = "2026-06-12T02:30:00+00:00"
        ny_date = event_date_for_timestamp(utc_evening, "America/New_York")
        self.assertEqual(ny_date, "2026-06-11")

    @patch("daily_error_sheet_service.list_users_for_daily_error_sheet")
    def test_job_skips_before_send_hour(self, mock_users):
        mock_users.return_value = [
            {
                "username": "alice",
                "email": "alice@example.com",
                "send_hour": 21,
                "timezone": "America/New_York",
                "send_no_misses_email": False,
            }
        ]
        early = datetime(2026, 6, 11, 15, 0, tzinfo=ZoneInfo("America/New_York"))
        results = run_daily_error_sheet_job(as_of=early, force=False)
        self.assertEqual(results[0]["status"], "skipped_before_send_hour")


if __name__ == "__main__":
    unittest.main()
