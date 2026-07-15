# -*- coding: utf-8 -*-

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from issue_spotting_utils import (
    build_attack_table_card,
    build_question_bank_cards,
    canonical_subject_name,
    dedupe_spotting_cards,
    expand_subject_names,
    parse_issue_trigger_from_rule_text,
    parse_oneliner_from_rule_text,
)


class IssueSpottingUtilsTests(unittest.TestCase):
    def test_parse_issue_trigger_from_rule_text(self):
        rule_text = (
            "Issue trigger: Witness repeats what bystander shouted outside court\n\n"
            "Hearsay: out-of-court statement offered for truth.\n\n"
            "One-liner: Out-of-court + for truth = hearsay until exception\n\n"
            "Exam tips: Ask purpose first"
        )
        self.assertEqual(
            parse_issue_trigger_from_rule_text(rule_text),
            "Witness repeats what bystander shouted outside court",
        )
        self.assertEqual(
            parse_oneliner_from_rule_text(rule_text),
            "Out-of-court + for truth = hearsay until exception",
        )
        self.assertEqual(parse_issue_trigger_from_rule_text("No trigger here"), "")

    def test_subject_aliases_expand_and_canonicalize(self):
        names = expand_subject_names(["Contracts", "Criminal Law & Procedure"])
        self.assertIn("Contracts", names)
        self.assertIn("Contracts / Sales", names)
        self.assertIn("Contracts and Sales", names)
        self.assertIn("Criminal Law & Procedure", names)
        self.assertIn("Criminal Law and Procedure", names)
        self.assertEqual(canonical_subject_name("Contracts / Sales"), "Contracts")
        self.assertEqual(
            canonical_subject_name("Criminal Law and Procedure"),
            "Criminal Law & Procedure",
        )

    def test_dedupe_prefers_higher_frequency_and_attack_table(self):
        cards = [
            {
                "id": "q-1-0",
                "trigger": "A fires B without cause",
                "source": "question_bank",
                "frequency": 2,
                "rule_title": "At-will employment",
                "expected_issues": ["At-will"],
            },
            {
                "id": "or-9",
                "trigger": "A fires B without cause!",
                "source": "attack_table",
                "frequency": 5,
                "rule_title": "Employment at will",
                "expected_issues": ["Employment at will"],
            },
            {
                "id": "or-2",
                "trigger": "Completely different trigger text here",
                "source": "attack_table",
                "frequency": 1,
                "rule_title": "Other",
                "expected_issues": ["Other"],
            },
        ]
        unique = dedupe_spotting_cards(cards)
        self.assertEqual(len(unique), 2)
        self.assertEqual(unique[0]["id"], "or-9")
        self.assertEqual(unique[1]["id"], "or-2")

    def test_build_attack_table_card_requires_trigger(self):
        with_trigger = build_attack_table_card(
            (
                1,
                "Evidence",
                "Hearsay",
                "12.5%",
                "Issue trigger: Out-of-court statement for truth\n\nHearsay rule.",
                None,
                "",
                "July 2026 MEE Attack Table.pdf",
            )
        )
        self.assertIsNotNone(with_trigger)
        self.assertEqual(with_trigger["source"], "attack_table")
        self.assertEqual(with_trigger["expected_issues"], ["Hearsay"])

        without = build_attack_table_card(
            (2, "Evidence", "Relevance", "", "Evidence must be relevant.", None, "", "master")
        )
        self.assertIsNone(without)


class IssueSpottingDatabaseTests(unittest.TestCase):
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

        database.add_outline_rule(
            "Evidence",
            "Hearsay",
            "12.5%",
            "Issue trigger: Witness repeats what bystander shouted\n\n"
            "Hearsay definition.\n\nOne-liner: Out of court + truth",
            1,
            "",
            "July 2026 MEE Attack Table.pdf",
        )
        database.add_outline_rule(
            "Contracts / Sales",
            "Offer and acceptance",
            "High",
            "Issue trigger: Email says I accept your quote for widgets\n\n"
            "Mutual assent required.\n\nOne-liner: Mirror the offer",
            2,
            "",
            "July 2026 MEE Attack Table.pdf",
        )
        database.add_outline_rule(
            "Torts",
            "Negligence duty",
            "",
            "General duty of reasonable care — no issue trigger prefix.",
            3,
            "",
            "MEE Master Rules (my outline)",
        )

        database.execute_write(
            """
            INSERT INTO questions (
                exam_name, question_number, subject, question_text, call_of_question,
                tested_issues, rules, trigger_facts, traps, model_points,
                active_for_july_2026, priority
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 5)
            """,
            (
                "July 2024 MEE",
                "1",
                "Constitutional Law",
                "Fact pattern about standing.",
                "Discuss standing.",
                "Does the plaintiff have standing to sue?",
                "Standing requires injury, causation, redressability.",
                "Plaintiff has not yet been harmed; Plaintiff fears future enforcement",
                "",
                "1. Standing requires injury in fact.",
            ),
        )
        database.execute_write(
            """
            INSERT INTO questions (
                exam_name, question_number, subject, question_text, call_of_question,
                tested_issues, rules, trigger_facts, traps, model_points,
                active_for_july_2026, priority
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 3)
            """,
            (
                "July 2023 MEE",
                "2",
                "Evidence",
                "Should remain unused because Evidence already has attack cards.",
                "Is the statement hearsay?",
                "Is the bystander statement hearsay?",
                "Hearsay rule",
                "Bystander shouted stop as the crash happened",
                "",
                "1. Hearsay analysis.",
            ),
        )

    def tearDown(self):
        self.database.reset_database_file_cache()
        self.database._db_ready = False
        self.database._db_file_ready = False
        self.database.invalidate_read_cache()
        self._tmpdir.cleanup()
        os.environ.pop("MEE_TRAINER_DB", None)

    def test_get_issue_spotting_cards_respects_aliases_and_filters(self):
        cards = self.database.get_issue_spotting_cards(
            ["Evidence", "Contracts", "Constitutional Law", "Torts"]
        )
        subjects = {card["subject"] for card in cards}
        self.assertIn("Evidence", subjects)
        self.assertIn("Contracts", subjects)
        self.assertIn("Constitutional Law", subjects)
        # Master rules without Issue trigger should not appear
        self.assertTrue(all(card.get("trigger") for card in cards))

        # Subject filter excludes non-selected subjects
        evidence_only = self.database.get_issue_spotting_cards(["Evidence"])
        self.assertTrue(evidence_only)
        self.assertTrue(all(card["subject"] == "Evidence" for card in evidence_only))
        self.assertTrue(all(card["source"] == "attack_table" for card in evidence_only))

        # Contracts alias on outline_rules is found when asking for Contracts
        contracts = self.database.get_issue_spotting_cards(["Contracts"])
        self.assertTrue(any(card["subject"] == "Contracts" for card in contracts))

        # Evidence has attack-table cards, so question-bank Evidence fallback is skipped
        self.assertFalse(
            any(
                card["source"] == "question_bank" and card["subject"] == "Evidence"
                for card in cards
            )
        )
        # Con Law has no attack table -> question bank fallback
        self.assertTrue(
            any(
                card["source"] == "question_bank"
                and card["subject"] == "Constitutional Law"
                for card in cards
            )
        )

    def test_database_parse_wrapper(self):
        text = "Issue trigger: Foo bar\n\nRule body"
        self.assertEqual(
            self.database.parse_issue_trigger_from_rule_text(text),
            "Foo bar",
        )

    def test_question_bank_card_builder(self):
        cards = build_question_bank_cards(
            {
                "id": 10,
                "subject": "Civil Procedure",
                "tested_issues": "Personal jurisdiction; Minimum contacts",
                "trigger_facts": "Defendant never visited the forum state; Lawsuit filed where plaintiff lives",
            },
            {"personal jurisdiction": 3, "minimum contacts": 2},
        )
        self.assertEqual(len(cards), 2)
        self.assertEqual(cards[0]["source"], "question_bank")
        self.assertGreaterEqual(cards[0]["frequency"], 2)


if __name__ == "__main__":
    unittest.main()
