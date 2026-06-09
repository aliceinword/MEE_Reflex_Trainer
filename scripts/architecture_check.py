# -*- coding: utf-8 -*-
"""Fast architecture and data checks for MEE Reflex Trainer.

Run from the project root:

    python scripts/architecture_check.py
"""

import ast
import py_compile
import sqlite3
import sys
from pathlib import Path

import _bootstrap  # noqa: F401


ROOT = Path(__file__).resolve().parent.parent
APP_MODULES = [
    "app.py",
    "app_shell.py",
    "app_state.py",
    "auth.py",
    "content_tools.py",
    "database.py",
    "import_markdown_mee_qa_bank.py",
    "import_mee_pq_bank_docx.py",
    "import_services.py",
    "main_pages.py",
    "mbe_import_services.py",
    "mbe_pages.py",
    "practice_components.py",
    "practice_pages.py",
    "question_utils.py",
    "styles.py",
    "text_cleanup.py",
    "text_rendering.py",
    "ui_components.py",
    "user_pages.py",
]
PAGE_MODULES = [
    "content_tools.py",
    "main_pages.py",
    "mbe_pages.py",
    "practice_components.py",
    "practice_pages.py",
    "user_pages.py",
]
SHARED_STREAMLIT_MODULES = {
    "app.py",
    "app_state.py",
    "auth.py",
    "styles.py",
    "text_rendering.py",
    "ui_components.py",
}


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


def read_text(path):
    return (ROOT / path).read_text(encoding="utf-8")


def compile_python(checker):
    files = [ROOT / name for name in APP_MODULES]
    files.extend(sorted((ROOT / "scripts").glob("*.py")))
    failed = []
    for file_path in files:
        try:
            py_compile.compile(str(file_path), doraise=True)
        except py_compile.PyCompileError as exc:
            failed.append(f"{file_path.relative_to(ROOT)}: {exc.msg}")
    checker.check("all app and maintenance scripts compile", not failed, "; ".join(failed[:3]))


def check_database(checker):
    db_path = ROOT / "mee_trainer.db"
    seed_path = ROOT / "mee_reflex.db"
    checker.check("runtime database exists", db_path.exists())
    checker.check("public seed database exists", seed_path.exists())

    for path in [db_path, seed_path]:
        if not path.exists():
            continue
        with sqlite3.connect(path) as conn:
            integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
            checker.check(f"{path.name} integrity", integrity == "ok", str(integrity))

    if db_path.exists():
        with sqlite3.connect(db_path) as conn:
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            required = {"questions", "attempts", "mbe_cards"}
            checker.check("core tables exist", required.issubset(tables), ", ".join(sorted(required - tables)))
            if "questions" in tables:
                count = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
                checker.check("MEE question bank has rows", count > 0, str(count))


def check_navigation_and_shell(checker):
    app = read_text("app.py")
    shell = read_text("app_shell.py")
    main_pages = read_text("main_pages.py")
    tree = ast.parse(app)

    checker.check("app.py uses wide page layout", 'layout="wide"' in app)
    checker.check("app.py has no local functions/classes", not any(isinstance(n, (ast.FunctionDef, ast.ClassDef)) for n in tree.body))
    checker.check("app.py stays focused", len(app.splitlines()) <= 120, f"{len(app.splitlines())} lines")

    for label in ["Home", "MEE Question Bank", "MEE Muscle Ladder", "MBE Drills", "Import Questions", "Manual Entry", "Settings"]:
        checker.check(f"navigation includes {label}", label in shell)

    checker.check("MBE navigation is separated from MEE", '"MBE Practice"' in shell and '"MEE Practice"' in shell)
    checker.check("advanced MEE tools are grouped", '"MEE Advanced Tools"' in shell)
    checker.check(
        "Home dashboard uses modular panels",
        all(
            f"def {name}(" in main_pages
            for name in [
                "render_dashboard_metrics",
                "render_dashboard_top_cards",
                "render_dashboard_summary_cards",
                "render_dashboard_queue_expander",
                "render_dashboard_session_plan_expander",
                "render_dashboard_due_expander",
            ]
        ),
    )
    dashboard_lines = function_line_count(main_pages, "render_dashboard_page")
    checker.check(
        "Home dashboard router stays compact",
        dashboard_lines is not None and dashboard_lines <= 35,
        str(dashboard_lines),
    )


def check_shared_rendering(checker):
    text_rendering = read_text("text_rendering.py")
    ui_components = read_text("ui_components.py")
    styles = read_text("styles.py")

    for name in [
        "split_paragraphs",
        "render_text_block",
        "render_question_text",
        "render_sample_answer_text",
        "render_trigger_facts",
        "render_trap_warnings",
        "render_call_text",
    ]:
        checker.check(f"shared renderer has {name}", f"def {name}" in text_rendering)

    checker.check("text renderer preserves paragraph spacing", 'style="margin-bottom:1.2em"' in text_rendering)
    checker.check("text renderer uses styled boxes", '"sample-answer"' in text_rendering and "render_html_box" in text_rendering)
    checker.check("shared controls stretch to width", '"width": "stretch"' in ui_components)
    checker.check("global page CSS uses wide containers", "max-width: 100%" in styles or "max-width:100%" in styles)


def check_no_page_local_streamlit(checker):
    offenders = []
    for module in PAGE_MODULES:
        source = read_text(module)
        if "import streamlit" in source or "from streamlit" in source:
            offenders.append(f"{module}: streamlit import")
        for token in ["st.text_area(", "st.write(", "st.button(", "st.selectbox(", "st.expander(", "st.dataframe("]:
            if token in source:
                offenders.append(f"{module}: {token}")
    checker.check("page modules use shared UI helpers", not offenders, "; ".join(offenders[:6]))

    allowed = set(SHARED_STREAMLIT_MODULES)
    unexpected = []
    for module_path in ROOT.glob("*.py"):
        module = module_path.name
        if module in allowed:
            continue
        source = module_path.read_text(encoding="utf-8")
        if "import streamlit" in source or "from streamlit" in source:
            unexpected.append(module)
    checker.check("Streamlit is centralized in shell/helper modules", not unexpected, ", ".join(unexpected))


def check_sql_and_scripts(checker):
    database = read_text("database.py")
    checker.check("default database is mee_trainer.db", 'DEFAULT_DB_NAME = "mee_trainer.db"' in database)
    checker.check("shared read helper exists", "def fetch_all(" in database and "def fetch_one(" in database)
    checker.check("shared write transaction exists", "def write_transaction(" in database)
    checker.check("MEE content quality helper exists", "def get_mee_content_quality(" in database)
    checker.check("MBE content quality helper exists", "def get_mbe_content_quality(" in database)
    checker.check("MBE practice stats merge helper exists", "def merge_mbe_practice_stats(" in database)
    checker.check("raw SQL writes use parameters", "DELETE FROM mbe_cards WHERE id = ?" in database)

    script_offenders = []
    for script_path in sorted((ROOT / "scripts").glob("*.py")):
        if script_path.name in {"_bootstrap.py", "architecture_check.py"}:
            continue
        source = script_path.read_text(encoding="utf-8")
        for token in ["sqlite3.connect", "conn.commit()", "conn.close()"]:
            if token in source:
                script_offenders.append(f"{script_path.name}: {token}")
    checker.check("maintenance scripts use shared DB helpers", not script_offenders, "; ".join(script_offenders[:6]))


def slice_between(source, start_marker, end_marker):
    start = source.find(start_marker)
    if start < 0:
        return ""
    end = source.find(end_marker, start + len(start_marker))
    if end < 0:
        return source[start:]
    return source[start:end]


def function_line_count(source, function_name):
    """Return the physical line count for a top-level function in source."""
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            return node.end_lineno - node.lineno + 1
    return None


def check_mbe_invariants(checker):
    mbe_pages = read_text("mbe_pages.py")
    trainer = read_text("mbe_trap_trainer.html")
    sync_bridge = read_text("mbe_stats_sync/index.html")

    checker.check(
        "MBE drills exclude rule flashcards",
        'render_mbe_trainer_page(embed_mode="drill", exclude_sources={"adaptibar_rules"})' in mbe_pages,
    )
    checker.check(
        "MBE bulk upload uses modular helpers",
        all(
            f"def {name}(" in mbe_pages
            for name in [
                "render_mbe_bulk_template_downloads",
                "render_mbe_bulk_file_uploader",
                "read_uploaded_mbe_bulk_file",
                "render_mbe_bulk_column_check",
                "render_mbe_bulk_preview",
                "render_mbe_bulk_import_actions",
            ]
        ),
    )
    bulk_upload_lines = function_line_count(mbe_pages, "render_mbe_bulk_upload_page")
    checker.check(
        "MBE bulk upload router stays compact",
        bulk_upload_lines is not None and bulk_upload_lines <= 35,
        str(bulk_upload_lines),
    )
    checker.check(
        "Flashcards Drill defaults to rule cards",
        'default_source = "adaptibar_rules"' in mbe_pages,
    )
    checker.check(
        "Flashcards Drill uses modular helpers",
        all(
            f"def {name}(" in mbe_pages
            for name in [
                "render_mbe_flashcard_filters",
                "ensure_mbe_flashcard_queue",
                "render_mbe_flashcard_prompt",
                "render_mbe_flashcard_retrieval_controls",
                "render_mbe_flashcard_answer",
                "render_mbe_flashcard_answer_actions",
            ]
        ),
    )
    flashcard_page_lines = function_line_count(mbe_pages, "render_mbe_flashcards_drill_page")
    checker.check(
        "Flashcards Drill router stays compact",
        flashcard_page_lines is not None and flashcard_page_lines <= 40,
        str(flashcard_page_lines),
    )
    checker.check(
        "Rule Recall uses modular helpers",
        all(
            f"def {name}(" in mbe_pages
            for name in [
                "render_rule_recall_filters",
                "ensure_rule_recall_queue",
                "render_rule_recall_prompt",
                "render_rule_recall_retrieval_controls",
                "render_rule_recall_answer",
                "render_rule_recall_answer_actions",
            ]
        ),
    )
    rule_recall_page_lines = function_line_count(mbe_pages, "render_rule_recall_page")
    checker.check(
        "Rule Recall router stays compact",
        rule_recall_page_lines is not None and rule_recall_page_lines <= 45,
        str(rule_recall_page_lines),
    )
    checker.check(
        "Bridge Drill uses modular helpers",
        all(
            f"def {name}(" in mbe_pages
            for name in [
                "render_bridge_drill_filters",
                "ensure_bridge_drill_queue",
                "current_bridge_drill_context",
                "render_bridge_drill_progress",
                "render_bridge_drill_phase",
            ]
        ),
    )
    bridge_page_lines = function_line_count(mbe_pages, "render_bridge_drill_page")
    checker.check(
        "Bridge Drill router stays compact",
        bridge_page_lines is not None and bridge_page_lines <= 45,
        str(bridge_page_lines),
    )
    checker.check(
        "Bridge Drill reveal phase uses modular helpers",
        all(
            f"def {name}(" in mbe_pages
            for name in [
                "_bd_render_rule_teaching",
                "_bd_render_pick_result",
                "_bd_render_correct_answer",
                "_bd_render_trap_explanation",
                "_bd_render_user_draft",
                "_bd_save_attempt_and_advance",
            ]
        ),
    )
    bridge_reveal_lines = function_line_count(mbe_pages, "_bd_reveal_phase")
    checker.check(
        "Bridge Drill reveal phase stays compact",
        bridge_reveal_lines is not None and bridge_reveal_lines <= 35,
        str(bridge_reveal_lines),
    )
    checker.check(
        "MBE embed injects database card store",
        "window.APP_MBE_CARD_STORE = 'database';" in mbe_pages,
    )
    checker.check(
        "MBE trainer embed uses modular helpers",
        all(
            f"def {name}(" in mbe_pages
            for name in [
                "render_mbe_embed_layout_css",
                "read_mbe_trainer_html",
                "mbe_database_cards_payload",
                "mbe_practice_blob_payload",
                "build_mbe_trainer_injection",
                "inject_mbe_trainer_bootstrap",
                "render_mbe_stats_sync_bridge",
            ]
        ),
    )
    trainer_page_lines = function_line_count(mbe_pages, "render_mbe_trainer_page")
    trainer_embed_lines = function_line_count(mbe_pages, "render_mbe_trainer_embed")
    checker.check(
        "MBE trainer page router stays compact",
        trainer_page_lines is not None and trainer_page_lines <= 25,
        str(trainer_page_lines),
    )
    checker.check(
        "MBE trainer embed router stays compact",
        trainer_embed_lines is not None and trainer_embed_lines <= 35,
        str(trainer_embed_lines),
    )

    all_cards_fn = slice_between(trainer, "function allCards(){", "// Single source of truth")
    checker.check(
        "database MBE deck does not mix built-ins",
        "window.APP_MBE_CARD_STORE === 'database'" in all_cards_fn
        and "_allCardsCache = dedupeCards(userCards.map(withCategory));" in all_cards_fn,
    )

    record_fn = slice_between(trainer, "function recordCardAnswer(", "function updateErrorListOnCorrect")
    checker.check(
        "MBE answer recording saves practice fields",
        "stats.timesSeen" in record_fn
        and "stats.lastAnsweredAt" in record_fn
        and "stats.practiceHistory.push" in record_fn
        and "setCardStats(card, stats)" in record_fn,
    )
    checker.check(
        "MBE answer recording pushes server sync",
        "pushPracticeStatsToServer()" in record_fn,
    )

    merge_fn = slice_between(trainer, "function mergeCardStatRecords(", "function migrateLocalStatsToDatabaseCards")
    checker.check(
        "MBE stat merge preserves recent/snooze fields",
        "merged.lastShown" in merge_fn
        and "merged.snoozedUntil" in merge_fn
        and "merged.nextReviewAt" in merge_fn,
    )

    checker.check(
        "MBE sync writes latest payload to parent storage",
        'trapSetItem("trapTrainer.practiceSync.latest", sig)' in trainer,
    )
    checker.check(
        "MBE sync bridge polls latest practice payload",
        "function pollAndSend()" in sync_bridge
        and '"trapTrainer.practiceSync.latest"' in sync_bridge
        and "setInterval(pollAndSend" in sync_bridge,
    )
    checker.check(
        "MBE sync bridge avoids stale parent listener",
        "__mbeTrapStatsSyncBound" not in sync_bridge
        and "__mbeTrapStatsSyncToken" not in sync_bridge,
    )
    send_ready_fn = slice_between(sync_bridge, "function sendReady()", "function startReadyHandshake()")
    checker.check(
        "MBE sync bridge waits for render before height/value messages",
        "setComponentReady" in send_ready_fn
        and "setFrameHeight" not in send_ready_fn
        and "readyAck = true" in sync_bridge
        and "Streamlit.setFrameHeight(0);" in sync_bridge,
    )


def check_mee_invariants(checker):
    main_pages = read_text("main_pages.py")
    content_tools = read_text("content_tools.py")
    practice_pages = read_text("practice_pages.py")
    practice_components = read_text("practice_components.py")
    database = read_text("database.py")

    checker.check(
        "Question Bank preview is capped at 3 rows",
        "QUESTION_BANK_VISIBLE_ROWS = 3" in main_pages,
    )
    for field in ["subject", "status", "topic", "exam_year", "created_from", "created_to"]:
        checker.check(
            f"Question Bank supports {field} filter",
            field in database and field in main_pages,
        )
    checker.check(
        "Question Bank detail uses shared tabs renderer",
        "render_question_detail_tabs(qd" in main_pages,
    )

    checker.check(
        "Import Questions exposes CSV DOCX PDF text tabs",
        all(label in content_tools for label in ["CSV Import", "DOCX Import", "PDF Import", "Text / Markdown Import"]),
    )
    checker.check(
        "Import Questions uses per-format tab helpers",
        all(
            f"def {name}(" in content_tools
            for name in [
                "render_csv_import_tab",
                "render_docx_import_tab",
                "render_pdf_import_tab",
                "render_text_markdown_import_tab",
            ]
        ),
    )
    checker.check(
        "PDF and text imports use modular pipeline helpers",
        all(
            f"def {name}(" in content_tools
            for name in [
                "render_pdf_import_inputs",
                "render_pdf_import_dry_run",
                "render_pdf_import_apply_action",
                "render_markdown_import_inputs",
                "render_markdown_import_dry_run",
                "render_markdown_import_apply_action",
            ]
        ),
    )
    for import_fn in ["render_pdf_import_tab", "render_text_markdown_import_tab"]:
        import_page_lines = function_line_count(content_tools, import_fn)
        checker.check(
            f"{import_fn} stays compact",
            import_page_lines is not None and import_page_lines <= 30,
            str(import_page_lines),
        )
    import_tool_lines = function_line_count(content_tools, "render_import_questions_tool")
    checker.check(
        "Import Questions router stays compact",
        import_tool_lines is not None and import_tool_lines <= 40,
        str(import_tool_lines),
    )
    checker.check(
        "DOCX/PDF/text imports use dry-run preview",
        content_tools.count("render_import_dry_run_preview(") >= 3,
    )
    checker.check(
        "Manual Entry captures prompt answer and rule outline",
        all(label in content_tools for label in ["Question text / prompt", "Sample answer / model analysis", "Rule Outline"]),
    )
    checker.check(
        "Manual Entry content uses modular helpers",
        all(
            f"def {name}(" in content_tools
            for name in [
                "render_manual_prompt_fields",
                "render_manual_answer_fields",
                "render_manual_outline_fields",
            ]
        ),
    )
    manual_content_lines = function_line_count(content_tools, "render_manual_entry_content_fields")
    checker.check(
        "Manual Entry content router stays compact",
        manual_content_lines is not None and manual_content_lines <= 25,
        str(manual_content_lines),
    )
    checker.check(
        "Manual Entry prompt gives paragraph-spacing tip",
        "paragraph_tip=True" in content_tools,
    )
    checker.check(
        "Manual Entry saves through import service",
        "save_question_from_mapping(values)" in content_tools,
    )

    checker.check(
        "MEE Practice uses shared question picker",
        "question_picker(active_default=True, compact=True, practice_ready_only=True)" in practice_pages,
    )
    checker.check(
        "MEE practice picker skips incomplete rows",
        "practice_ready_only=False" in read_text("ui_components.py")
        and "practice_ready_only=practice_ready_only" in read_text("ui_components.py")
        and "TRIM(COALESCE(question_text" in database
        and "TRIM(COALESCE(call_of_question" in database
        and "TRIM(COALESCE(model_points" in database,
    )
    checker.check(
        "MEE Practice has Mini Drill and Muscle Ladder tabs",
        'render_tab_set(["Mini Drill", "MEE Muscle Ladder"])' in practice_pages,
    )
    checker.check(
        "MEE Practice gates answer reveal after retrieval",
        "render_reveal_control(" in practice_pages and "Reveal only after writing" in practice_pages,
    )
    checker.check(
        "MEE Practice saves mini and ladder attempts",
        "render_save_mini_drill_attempt(" in practice_pages
        and "render_save_ladder_attempt(" in practice_pages,
    )
    checker.check(
        "MEE Muscle Ladder uses modular helpers",
        all(
            f"def {name}(" in practice_pages
            for name in [
                "render_ladder_level_selector",
                "render_ladder_work_area",
                "render_ladder_score_save_panel",
                "render_ladder_reveal_panel",
                "render_ladder_score_and_check",
            ]
        ),
    )
    ladder_tab_lines = function_line_count(practice_pages, "render_ladder_tab")
    checker.check(
        "MEE Muscle Ladder router stays compact",
        ladder_tab_lines is not None and ladder_tab_lines <= 35,
        str(ladder_tab_lines),
    )
    checker.check(
        "MEE Muscle Ladder response levels use modular helpers",
        all(
            f"def {name}(" in practice_components
            for name in [
                "render_ladder_level_1_response",
                "render_ladder_level_2_response",
                "render_ladder_level_3_response",
                "render_ladder_level_4_response",
                "render_ladder_level_5_response",
            ]
        )
        and "LADDER_RESPONSE_RENDERERS" in practice_components,
    )
    ladder_response_lines = function_line_count(practice_components, "render_ladder_response_input")
    checker.check(
        "MEE Muscle Ladder response router stays compact",
        ladder_response_lines is not None and ladder_response_lines <= 20,
        str(ladder_response_lines),
    )
    checker.check(
        "MEE Practice prompt and review use shared renderers",
        "render_call_text(" in practice_components
        and "render_trigger_facts(" in practice_components
        and "render_trap_warnings(" in practice_components,
    )
    checker.check(
        "MEE answer bank uses modular tab helpers",
        all(
            f"def {name}(" in practice_components
            for name in [
                "answer_bank_tab_names",
                "render_rules_issues_tab",
                "render_trigger_facts_tab",
                "render_traps_tab",
                "render_rule_support_tab",
            ]
        ),
    )
    answer_bank_lines = function_line_count(practice_components, "render_answer_bank_tabs")
    checker.check(
        "MEE answer bank router stays compact",
        answer_bank_lines is not None and answer_bank_lines <= 45,
        str(answer_bank_lines),
    )
    checker.check(
        "Settings exposes MEE content quality",
        "def render_mee_content_quality_panel(" in main_pages
        and "MEE Content Quality" in main_pages
        and "get_mee_content_quality(limit=12)" in main_pages,
    )
    checker.check(
        "Settings shows practice-ready count",
        "Practice-ready" in main_pages and "practice_ready_questions" in main_pages,
    )
    checker.check(
        "Settings keeps incomplete rows compact",
        "def mee_quality_table_rows(" in main_pages
        and "render_preview_table(mee_quality_table_rows(quality[\"rows\"]), max_rows=12)" in main_pages,
    )
    checker.check(
        "Settings exposes MBE content quality",
        "def render_mbe_content_quality_panel(" in main_pages
        and "MBE Content Quality" in main_pages
        and "get_mbe_content_quality(limit=12)" in main_pages,
    )
    checker.check(
        "Settings shows MBE deck split",
        "Drill cards" in main_pages and "Flashcards" in main_pages,
    )
    checker.check(
        "Settings shows MBE practice rows",
        "practice_rows" in main_pages and "Practiced" in main_pages,
    )


def main():
    checker = Checker()
    compile_python(checker)
    check_database(checker)
    check_navigation_and_shell(checker)
    check_shared_rendering(checker)
    check_no_page_local_streamlit(checker)
    check_sql_and_scripts(checker)
    check_mee_invariants(checker)
    check_mbe_invariants(checker)

    if checker.failures:
        print("\nArchitecture check failed:")
        for failure in checker.failures:
            print(f"- {failure}")
    else:
        print("\nArchitecture check passed.")

    return checker.exit_code()


if __name__ == "__main__":
    sys.exit(main())
