# -*- coding: utf-8 -*-
"""Streamlit widget-tree smoke checks for core app pages.

The script uses a disposable copy of the database and disables auth through
MEE_DISABLE_AUTH so it can inspect the app without credentials or side effects.
"""

from __future__ import annotations

import logging
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path

from streamlit.testing.v1 import AppTest
from streamlit.runtime.scriptrunner_utils import script_run_context


ROOT = Path(__file__).resolve().parent
SOURCE_DB = ROOT / "mee_trainer.db"
TIMEOUT = 20


logging.getLogger("streamlit").setLevel(logging.ERROR)
logging.getLogger("streamlit.runtime.scriptrunner_utils.script_run_context").setLevel(logging.ERROR)
script_run_context._LOGGER.disabled = True


class LayoutSmoke:
    def __init__(self) -> None:
        self.failures: list[str] = []

    def check(self, name: str, condition: bool, detail: str = "") -> None:
        if condition:
            print(f"OK   {name}")
            return

        message = f"FAIL {name}"
        if detail:
            message += f" - {detail}"
        print(message)
        self.failures.append(message)

    def finish(self) -> None:
        if self.failures:
            print("\nLayout smoke failed:")
            for failure in self.failures:
                print(f"- {failure}")
            raise SystemExit(1)

        print("\nLayout smoke passed.")


def _prepare_temp_db(tmp_dir: Path) -> Path:
    temp_db = tmp_dir / "mee_layout_smoke.db"
    shutil.copy2(SOURCE_DB, temp_db)

    conn = sqlite3.connect(temp_db)
    try:
        conn.execute("DELETE FROM app_users")
        conn.commit()
    finally:
        conn.close()

    return temp_db


def _element_label(element) -> str:
    return str(getattr(element, "label", "") or "")


def _element_value(element) -> str:
    return str(getattr(element, "value", "") or "")


def _labels(elements) -> list[str]:
    return [_element_label(element) for element in elements]


def _page_text(at: AppTest) -> str:
    chunks = []
    for collection in [
        at.markdown,
        at.button,
        at.checkbox,
        at.selectbox,
        at.text_input,
        at.text_area,
        getattr(at, "file_uploader", []),
        at.tabs,
    ]:
        for element in collection:
            chunks.append(_element_label(element))
            chunks.append(_element_value(element))
    return "\n".join(part for part in chunks if part)


def _run_page(page: str) -> AppTest:
    at = AppTest.from_file(str(ROOT / "app.py"))
    at.session_state["current_page"] = page
    at.run(timeout=TIMEOUT)
    return at


def _check_no_exceptions(checker: LayoutSmoke, page: str, at: AppTest) -> None:
    checker.check(f"{page} renders without exceptions", len(at.exception) == 0, str(at.exception))


def _check_nav(checker: LayoutSmoke, page: str, at: AppTest) -> None:
    labels = _labels(at.button)
    for nav_label in [
        "Home",
        "MEE Question Bank",
        "MEE Muscle Ladder",
        "MBE Drills",
        "MBE Drills Question Bulk Upload",
        "Import Questions",
        "Manual Entry",
        "Settings",
    ]:
        checker.check(f"{page} nav includes {nav_label}", nav_label in labels)
    checker.check(f"{page} nav group includes MEE Advanced Tools", "MEE Advanced Tools" in _page_text(at))


def _check_required_text(checker: LayoutSmoke, page: str, at: AppTest, required: list[str]) -> None:
    text = _page_text(at)
    for item in required:
        checker.check(f"{page} shows {item}", item in text)


def _check_required_labels(checker: LayoutSmoke, page: str, kind: str, actual: list[str], required: list[str]) -> None:
    for label in required:
        checker.check(f"{page} {kind} includes {label}", label in actual, ", ".join(actual))


def check_dashboard(checker: LayoutSmoke) -> None:
    page = "Dashboard"
    at = _run_page(page)
    _check_no_exceptions(checker, page, at)
    _check_nav(checker, page, at)
    _check_required_text(checker, page, at, ["Home", "Today's Workout", "Tiny Win", "ADHD Guardrails"])
    _check_required_labels(checker, page, "button", _labels(at.button), ["MEE Ladder", "MBE Drills"])


def check_question_bank(checker: LayoutSmoke) -> None:
    page = "MEE Question Bank"
    at = _run_page(page)
    _check_no_exceptions(checker, page, at)
    _check_nav(checker, page, at)
    _check_required_text(checker, page, at, ["MEE Question Bank", "Sample Answer / Model Analysis", "Trigger Facts"])
    _check_required_labels(
        checker,
        page,
        "selectbox",
        _labels(at.selectbox),
        ["Subject", "Status", "Exam year", "Added date", "Open question details"],
    )
    _check_required_labels(checker, page, "text input", _labels(at.text_input), ["Tested topic / keyword"])
    _check_required_labels(checker, page, "tab", _labels(at.tabs), ["Prompt", "Answer", "Rule Outline"])
    checker.check("MEE Question Bank hides Metadata tab", "Metadata" not in _labels(at.tabs), ", ".join(_labels(at.tabs)))


def check_practice(checker: LayoutSmoke) -> None:
    page = "MEE Muscle Ladder"
    at = _run_page(page)
    _check_no_exceptions(checker, page, at)
    _check_nav(checker, page, at)
    _check_required_text(
        checker,
        page,
        at,
        ["MEE Practice", "Mini Drill", "MEE Muscle Ladder", "Plug & Play Template"],
    )
    _check_required_labels(
        checker,
        page,
        "tab",
        _labels(at.tabs),
        ["Mini Drill", "MEE Muscle Ladder"],
    )
    _check_required_labels(
        checker,
        page,
        "selectbox",
        _labels(at.selectbox),
        ["Subject filter", "July 2026 status", "Pick a question"],
    )
    _check_required_labels(
        checker,
        page,
        "checkbox",
        _labels(at.checkbox),
        ["Highlight relevant triggering facts"],
    )
    highlight_boxes = [box for box in at.checkbox if _element_label(box) == "Highlight relevant triggering facts"]
    checker.check("Mini Drill highlight checkbox exists", len(highlight_boxes) == 1, str(_labels(at.checkbox)))
    if highlight_boxes:
        highlighted_at = highlight_boxes[0].set_value(True).run(timeout=TIMEOUT)
        _check_no_exceptions(checker, "Mini Drill highlighted fact pattern", highlighted_at)
        _check_required_text(
            checker,
            "Mini Drill highlighted fact pattern",
            highlighted_at,
            ["Fact Pattern with Trigger Facts Highlighted"],
        )
    _check_required_labels(
        checker,
        page,
        "text area",
        _labels(at.text_area),
        [
            "Your issue",
            "Your rule",
            "Your trigger facts",
            "Your micro-conclusion",
        ],
    )
    _check_required_labels(
        checker,
        page,
        "button",
        _labels(at.button),
        ["Save Mini Drill Attempt", "Reveal Mini Drill Answer Bank"],
    )

    reveal_buttons = [button for button in at.button if _element_label(button) == "Reveal Mini Drill Answer Bank"]
    checker.check("Mini Drill reveal button exists", len(reveal_buttons) == 1, str(_labels(at.button)))
    if reveal_buttons:
        at = reveal_buttons[0].click().run(timeout=TIMEOUT)
        _check_no_exceptions(checker, "Mini Drill reveal", at)
        _check_required_labels(
            checker,
            "Mini Drill reveal",
            "tab",
            _labels(at.tabs),
            ["Rules + Issues", "Trigger Facts", "Traps", "Rule Support"],
        )
        _check_required_text(
            checker,
            "Mini Drill reveal",
            at,
            [
                "Model Answer",
                "Rule Outline + Trigger Facts",
                "Sample Answer",
            ],
        )


def check_import_questions(checker: LayoutSmoke) -> None:
    page = "Import Questions"
    at = _run_page(page)
    _check_no_exceptions(checker, page, at)
    _check_nav(checker, page, at)
    _check_required_text(checker, page, at, ["Import Questions", "CSV Import", "DOCX Import"])
    _check_required_labels(
        checker,
        page,
        "tab",
        _labels(at.tabs),
        [
            "CSV Import",
            "DOCX Import",
            "PDF Import",
            "Text / Markdown Import",
        ],
    )
    _check_required_labels(
        checker,
        page,
        "text area",
        _labels(at.text_area),
        ["Or paste Markdown/text here"],
    )


def check_manual_entry(checker: LayoutSmoke) -> None:
    page = "Manual Entry"
    at = _run_page(page)
    _check_no_exceptions(checker, page, at)
    _check_nav(checker, page, at)
    _check_required_text(checker, page, at, ["Manual Entry", "Prompt", "Answer", "Rule Outline"])
    _check_required_labels(
        checker,
        page,
        "tab",
        _labels(at.tabs),
        ["Prompt", "Answer", "Rule Outline"],
    )
    _check_required_labels(
        checker,
        page,
        "text area",
        _labels(at.text_area),
        [
            "Question text / prompt",
            "Call of the question",
            "Sample answer / model analysis",
            "Tested issues",
            "Trigger facts",
            "Rules",
            "Traps",
        ],
    )


def check_settings(checker: LayoutSmoke) -> None:
    page = "Settings"
    at = _run_page(page)
    _check_no_exceptions(checker, page, at)
    _check_nav(checker, page, at)
    _check_required_text(checker, page, at, ["Settings", "Layout", "Data", "Workflow"])


def check_mbe(checker: LayoutSmoke) -> None:
    page = "MBE Drills"
    at = _run_page(page)
    _check_no_exceptions(checker, page, at)
    _check_nav(checker, page, at)
    checker.check(
        "MBE Drills opens without extra Streamlit title",
        "MBE Drills - Trap Trainer" not in _page_text(at),
    )


def check_mbe_bulk_upload(checker: LayoutSmoke) -> None:
    page = "MBE Drills Question Bulk Upload"
    at = _run_page(page)
    _check_no_exceptions(checker, page, at)
    _check_nav(checker, page, at)
    _check_required_text(
        checker,
        page,
        at,
        ["MBE Drills Question Bulk Upload", "Templates", "Upload Check"],
    )


def main() -> None:
    if not SOURCE_DB.exists():
        raise SystemExit(f"Source database not found: {SOURCE_DB}")

    checker = LayoutSmoke()
    with tempfile.TemporaryDirectory(prefix="mee_layout_smoke_") as tmp:
        temp_db = _prepare_temp_db(Path(tmp))
        os.environ["MEE_TRAINER_DB"] = str(temp_db)
        os.environ["MEE_DISABLE_AUTH"] = "1"

        check_dashboard(checker)
        check_question_bank(checker)
        check_practice(checker)
        check_import_questions(checker)
        check_manual_entry(checker)
        check_settings(checker)
        check_mbe(checker)
        check_mbe_bulk_upload(checker)

    checker.finish()


if __name__ == "__main__":
    main()
