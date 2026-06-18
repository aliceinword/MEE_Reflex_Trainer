# -*- coding: utf-8 -*-

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class UserQuestionAnswerTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._db_path = Path(self._tmpdir.name) / "test.db"
        os.environ["MEE_TRAINER_DB"] = str(self._db_path)

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
            INSERT INTO questions (
                exam_name, question_number, subject, question_text, call_of_question
            ) VALUES (?, ?, ?, ?, ?)
            """,
            ("July 2018", "1", "Constitutional Law", "Facts", "Call"),
        )
        self.question_id = self.database.fetch_one("SELECT id FROM questions")[0]

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_save_and_reload_user_answer(self):
        text = "Issue:\nThe issue is whether Section 11 is valid.\n\nConclusion:\nNo."
        updated_at = self.database.save_user_question_answer("alice", self.question_id, text)
        self.assertTrue(updated_at)

        saved = self.database.get_user_question_answer("alice", self.question_id)
        self.assertEqual(saved["answer_text"], text)
        self.assertEqual(saved["updated_at"], updated_at)

    def test_upsert_overwrites_previous_answer(self):
        self.database.save_user_question_answer("alice", self.question_id, "Draft one")
        self.database.save_user_question_answer("alice", self.question_id, "Draft two")

        saved = self.database.get_user_question_answer("alice", self.question_id)
        self.assertEqual(saved["answer_text"], "Draft two")

    def test_delete_user_answer(self):
        self.database.save_user_question_answer("alice", self.question_id, "Draft")
        deleted = self.database.delete_user_question_answer("alice", self.question_id)
        self.assertEqual(deleted, 1)
        self.assertIsNone(self.database.get_user_question_answer("alice", self.question_id))


if __name__ == "__main__":
    unittest.main()
