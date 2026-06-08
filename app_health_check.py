# -*- coding: utf-8 -*-
"""Read-only health checks for the MEE Reflex Trainer app.

This script verifies core architecture and data invariants without starting
Streamlit and without writing to the database.
"""

from __future__ import annotations

import ast
import py_compile
import shutil
import sqlite3
import tempfile
from contextlib import contextmanager
from pathlib import Path

from audit_sample_answers import (
    audit_status,
    extract_subquestions_simple,
    load_questions,
    split_model_answer_points_simple,
)
from database import DB_NAME, get_question_bank_rows
from import_services import run_markdown_text_import


ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / DB_NAME


@contextmanager
def temporary_database_copy(prefix: str):
    """Point database.DB_NAME at a disposable copy of the real database."""
    import database

    with tempfile.TemporaryDirectory(prefix=prefix) as tmp_dir:
        temp_db = Path(tmp_dir) / DB_NAME
        shutil.copy2(DB_PATH, temp_db)

        original_db_name = database.DB_NAME
        database.DB_NAME = str(temp_db)
        try:
            yield temp_db
        finally:
            database.DB_NAME = original_db_name

CORE_MODULES = [
    "app.py",
    "app_state.py",
    "app_layout_smoke.py",
    "app_shell.py",
    "app_runtime_smoke.py",
    "auth.py",
    "content_tools.py",
    "database.py",
    "import_questions_bank.py",
    "import_questions_docx.py",
    "import_markdown_mee_qa_bank.py",
    "import_mee_pq_bank_docx.py",
    "import_services.py",
    "main_pages.py",
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

REQUIRED_QUESTION_COLUMNS = {
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
}

REQUIRED_RENDERERS = {
    "render_html_box",
    "render_text_block",
    "render_prompt",
    "render_answer",
    "render_rule_outline",
    "render_question_text",
    "render_sample_answer_text",
    "render_trigger_facts",
    "render_trap_warnings",
}

REQUIRED_DB_HELPERS = {
    "fetch_all",
    "fetch_one",
    "execute_write",
    "write_transaction",
    "question_exists",
}


class HealthCheck:
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
            print("\nHealth check failed:")
            for failure in self.failures:
                print(f"- {failure}")
            raise SystemExit(1)

        print("\nHealth check passed.")


def compile_core_modules(checker: HealthCheck) -> None:
    for module in CORE_MODULES:
        py_compile.compile(str(ROOT / module), doraise=True)
    checker.check("core modules compile", True)


def check_app_shell(checker: HealthCheck) -> None:
    from app_shell import ADVANCED_TOOL_PAGES, MENU_ALIASES, NAV_GROUPS

    nav_pages = [page for _group, pages in NAV_GROUPS for page in pages]
    checker.check("Home is in primary navigation", "Home" in nav_pages)
    checker.check("MEE Question Bank is in primary navigation", "MEE Question Bank" in nav_pages)
    checker.check("MEE practice page is in primary navigation", "MEE Muscle Ladder" in nav_pages)
    checker.check("MBE is separated from MEE navigation", "MBE Drills" in nav_pages)
    nav_groups = [group for group, _pages in NAV_GROUPS]
    checker.check("MEE Advanced Tools group is in navigation", "MEE Advanced Tools" in nav_groups)
    checker.check("Import Questions is in MEE Advanced Tools navigation", "Import Questions" in nav_pages)
    checker.check("Manual Entry is in MEE Advanced Tools navigation", "Manual Entry" in nav_pages)
    checker.check("MEE Advanced Tools is not a daily practice page", "MEE Advanced Tools" not in nav_pages)
    checker.check("Settings page is in navigation", "Settings" in nav_pages)
    checker.check("Practice Mode alias routes to practice", MENU_ALIASES.get("Practice Mode") == "MEE Muscle Ladder")
    checker.check("Question Bank alias routes to MEE Question Bank", MENU_ALIASES.get("Question Bank") == "MEE Question Bank")
    checker.check("MEE Advanced Tools alias routes to Import Questions", MENU_ALIASES.get("MEE Advanced Tools") == "Import Questions")
    checker.check("Bulk import alias routes to Import Questions", MENU_ALIASES.get("Bulk Import MEE Bank") == "Import Questions")
    checker.check("Add question alias routes to Manual Entry", MENU_ALIASES.get("Add MEE Question") == "Manual Entry")
    checker.check("Import Questions is advanced-only", "Import Questions" in ADVANCED_TOOL_PAGES)
    checker.check("Manual Entry is advanced-only", "Manual Entry" in ADVANCED_TOOL_PAGES)


def check_app_py_thin(checker: HealthCheck) -> None:
    tree = ast.parse((ROOT / "app.py").read_text(encoding="utf-8"))
    definitions = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
    checker.check("app.py has no local functions/classes", len(definitions) == 0)
    checker.check("app.py stays short", len((ROOT / "app.py").read_text(encoding="utf-8").splitlines()) <= 90)


def check_database(checker: HealthCheck) -> None:
    import database

    missing_helpers = [name for name in sorted(REQUIRED_DB_HELPERS) if not hasattr(database, name)]
    checker.check("database shared query helpers exist", not missing_helpers, ", ".join(missing_helpers))

    checker.check(
        "default SQLite backend is mee_trainer.db",
        getattr(database, "DEFAULT_DB_NAME", "") == "mee_trainer.db"
        and Path(database.DEFAULT_DB_NAME).name == "mee_trainer.db"
        and DB_PATH.name == "mee_trainer.db",
        str((getattr(database, "DEFAULT_DB_NAME", None), DB_PATH)),
    )
    checker.check("database file exists", DB_PATH.exists(), str(DB_PATH))
    health_source = (ROOT / "app_health_check.py").read_text(encoding="utf-8")
    checker.check(
        "health checks use shared temporary DB helper",
        "def temporary_database_copy(" in health_source
        and health_source.count("temporary_database_copy(") >= 3,
    )

    conn = sqlite3.connect(DB_PATH)
    try:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        checker.check("SQLite integrity", integrity == "ok", str(integrity))

        foreign_key_issues = conn.execute("PRAGMA foreign_key_check").fetchall()
        checker.check("SQLite foreign key check", not foreign_key_issues, str(foreign_key_issues[:5]))

        columns = {row[1] for row in conn.execute("PRAGMA table_info(questions)").fetchall()}
        missing_columns = sorted(REQUIRED_QUESTION_COLUMNS - columns)
        checker.check("questions table has required columns", not missing_columns, ", ".join(missing_columns))

        question_count = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
        checker.check("question bank has questions", question_count > 0, str(question_count))
    finally:
        conn.close()

    all_rows = get_question_bank_rows()
    future_rows = get_question_bank_rows(created_from="2999-01-01")
    checker.check("MEE Question Bank query returns rows", len(all_rows) > 0, str(len(all_rows)))
    checker.check("MEE Question Bank date filter can exclude future rows", len(future_rows) == 0, str(len(future_rows)))


def _sql_arg_is_dynamic_string(node: ast.AST) -> bool:
    if isinstance(node, ast.JoinedStr):
        return True

    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return True

    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        return node.func.attr == "format"

    return False


def check_database_sql_safety(checker: HealthCheck) -> None:
    tree = ast.parse((ROOT / "database.py").read_text(encoding="utf-8-sig"))
    allowed_dynamic_sql_functions = {"_add_missing_columns"}
    offenders = []
    transaction_function_nodes = {}
    dashboard_stats_node = None

    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue

        if node.name == "get_dashboard_stats":
            dashboard_stats_node = node

        if node.name in {
            "init_db",
            "execute_write",
            "save_attempt",
            "add_outline_rule",
            "add_rule_flashcard",
            "add_plug_play_template",
            "upsert_admin",
            "add_app_user",
        }:
            transaction_function_nodes[node.name] = node

        for child in ast.walk(node):
            if not isinstance(child, ast.Call):
                continue
            if not isinstance(child.func, ast.Attribute):
                continue
            if child.func.attr not in {"execute", "executemany"}:
                continue
            if not child.args:
                continue
            if _sql_arg_is_dynamic_string(child.args[0]) and node.name not in allowed_dynamic_sql_functions:
                offenders.append(f"{node.name}:line {child.lineno}")

    checker.check("database avoids dynamic SQL strings outside migrations", not offenders, ", ".join(offenders))

    manual_lifecycle_offenders = []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef) or node.name == "write_transaction":
            continue
        for child in ast.walk(node):
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                if child.func.attr in {"commit", "rollback", "close"}:
                    manual_lifecycle_offenders.append(f"{node.name}:line {child.lineno}:{child.func.attr}")

    checker.check(
        "database commit/rollback/close lifecycle is centralized",
        not manual_lifecycle_offenders,
        ", ".join(manual_lifecycle_offenders),
    )

    for function_name in [
        "init_db",
        "execute_write",
        "save_attempt",
        "add_outline_rule",
        "add_rule_flashcard",
        "add_plug_play_template",
        "upsert_admin",
        "add_app_user",
    ]:
        node = transaction_function_nodes.get(function_name)
        if node is None:
            checker.check(f"{function_name} exists", False)
            continue

        calls = {
            child.func.id
            for child in ast.walk(node)
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name)
        }
        attrs = {
            child.func.attr
            for child in ast.walk(node)
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute)
        }
        checker.check(
            f"{function_name} uses shared transaction helper",
            "write_transaction" in calls
            and "get_connection" not in calls
            and "commit" not in attrs
            and "close" not in attrs,
        )

    if dashboard_stats_node is None:
        checker.check("get_dashboard_stats exists", False)
    else:
        dashboard_calls = {
            child.func.id
            for child in ast.walk(dashboard_stats_node)
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name)
        }
        dashboard_attrs = {
            child.func.attr
            for child in ast.walk(dashboard_stats_node)
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute)
        }
        checker.check(
            "get_dashboard_stats uses context-managed connection",
            "closing" in dashboard_calls
            and "get_connection" in dashboard_calls
            and "close" not in dashboard_attrs,
        )


def check_renderers_and_ui(checker: HealthCheck) -> None:
    import text_rendering

    missing_renderers = [name for name in sorted(REQUIRED_RENDERERS) if not hasattr(text_rendering, name)]
    checker.check("shared long-text renderers exist", not missing_renderers, ", ".join(missing_renderers))
    paragraphs = text_rendering.split_paragraphs(
        "First sentence. Second Sentence\n\nThird paragraph continues."
    )
    checker.check(
        "shared renderer splits explicit and implicit paragraphs",
        paragraphs[:3]
        == [
            "First sentence.",
            "Second Sentence",
            "Third paragraph continues.",
        ],
        str(paragraphs),
    )

    renderer_tree = ast.parse((ROOT / "text_rendering.py").read_text(encoding="utf-8-sig"))
    text_rendering_source = (ROOT / "text_rendering.py").read_text(encoding="utf-8-sig")
    checker.check(
        "shared text blocks use full-width paragraph wrapper",
        'style="margin-bottom:1.2em"' in text_rendering_source
        and "'width: 100%;'" in text_rendering_source
        and "render_html_box(title, body, class_name" in text_rendering_source,
    )
    renderer_calls = {}
    for node in renderer_tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        calls = {
            child.func.id
            for child in ast.walk(node)
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name)
        }
        renderer_calls[node.name] = calls

    shared_renderer_expectations = {
        "render_prompt": "render_text_block",
        "render_answer": "render_text_block",
        "render_rule_outline": "render_text_block",
        "render_question_text": "render_text_block",
        "render_sample_answer_text": "render_html_box",
        "render_structured_model_analysis": "render_html_box",
    }
    renderer_offenders = [
        f"{function}->{expected}"
        for function, expected in shared_renderer_expectations.items()
        if expected not in renderer_calls.get(function, set())
    ]
    checker.check("public long-text renderers share core box/render helpers", not renderer_offenders, ", ".join(renderer_offenders))

    active_modules = [
        "app.py",
        "app_shell.py",
        "content_tools.py",
        "main_pages.py",
        "mbe_pages.py",
        "practice_components.py",
        "practice_pages.py",
        "ui_components.py",
        "user_pages.py",
    ]
    active_page_modules = [
        "app_shell.py",
        "content_tools.py",
        "main_pages.py",
        "mbe_pages.py",
        "practice_components.py",
        "practice_pages.py",
        "user_pages.py",
    ]
    streamlit_import_offenders = []
    for module in active_page_modules:
        text = (ROOT / module).read_text(encoding="utf-8")
        if "import streamlit as st" in text or "from streamlit" in text:
            streamlit_import_offenders.append(module)

    checker.check(
        "active page modules avoid direct Streamlit imports",
        not streamlit_import_offenders,
        ", ".join(streamlit_import_offenders),
    )

    forbidden_patterns = ["st.write(", "st.text(", "st.json("]
    offenders = []
    for module in active_modules:
        text = (ROOT / module).read_text(encoding="utf-8")
        for pattern in forbidden_patterns:
            if pattern in text:
                offenders.append(f"{module}:{pattern}")

    checker.check("active modules avoid raw text/code display helpers", not offenders, ", ".join(offenders))

    heading_offenders = []
    direct_heading_patterns = [
        'st.markdown("###',
        "st.markdown('###",
        'st.markdown(f"###',
        "st.markdown(f'###",
        'st.markdown("####',
        "st.markdown('####",
        'st.markdown(f"####',
        "st.markdown(f'####",
        "st.subheader(",
    ]
    for module in active_modules:
        if module == "ui_components.py":
            continue
        text = (ROOT / module).read_text(encoding="utf-8")
        for pattern in direct_heading_patterns:
            if pattern in text:
                heading_offenders.append(f"{module}:{pattern}")

    checker.check(
        "page section headings use shared helper",
        "def render_section_heading(" in (ROOT / "ui_components.py").read_text(encoding="utf-8")
        and not heading_offenders,
        ", ".join(heading_offenders),
    )

    markdown_offenders = []
    for module in active_modules:
        if module == "ui_components.py":
            continue
        text = (ROOT / module).read_text(encoding="utf-8")
        if "st.markdown(" in text:
            markdown_offenders.append(module)

    checker.check(
        "active pages use shared markdown/html helpers",
        not markdown_offenders,
        ", ".join(markdown_offenders),
    )

    table_offenders = []
    for module in active_modules:
        if module == "ui_components.py":
            continue
        text = (ROOT / module).read_text(encoding="utf-8")
        if "st.dataframe(" in text:
            table_offenders.append(module)

    checker.check("active pages use shared dataframe/table helper", not table_offenders, ", ".join(table_offenders))
    checker.check(
        "preview tables centralize adaptive height and row limiting",
        "def preview_table_height(" in (ROOT / "ui_components.py").read_text(encoding="utf-8")
        and "max_rows=None" in (ROOT / "ui_components.py").read_text(encoding="utf-8")
        and "rows.head(max_rows)" in (ROOT / "ui_components.py").read_text(encoding="utf-8")
        and "rows = rows[:max_rows]" in (ROOT / "ui_components.py").read_text(encoding="utf-8")
        and ".head(10)" not in (ROOT / "main_pages.py").read_text(encoding="utf-8")
        and "height=min(" not in (ROOT / "main_pages.py").read_text(encoding="utf-8"),
    )

    text_area_offenders = []
    for module in active_modules:
        if module == "ui_components.py":
            continue
        text = (ROOT / module).read_text(encoding="utf-8")
        if "st.text_area(" in text:
            text_area_offenders.append(module)

    checker.check("active pages use shared text-area helper", not text_area_offenders, ", ".join(text_area_offenders))
    ui_components_source = (ROOT / "ui_components.py").read_text(encoding="utf-8")
    text_area_height_literal_offenders = []
    for module in active_page_modules:
        module_path = ROOT / module
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Name) or node.func.id != "render_text_area":
                continue
            for keyword in node.keywords:
                if keyword.arg == "height" and isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, int):
                    text_area_height_literal_offenders.append(f"{module}:{keyword.value.value}")

    checker.check(
        "active pages use shared text-area sizing tokens",
        not text_area_height_literal_offenders
        and "TEXTAREA_HEIGHT_XL" in ui_components_source
        and "TEXTAREA_HEIGHT_PREVIEW" in ui_components_source,
        ", ".join(text_area_height_literal_offenders),
    )
    checker.check(
        "shared input helpers explicitly stretch to container width",
        '"width": "stretch"' in ui_components_source
        and ui_components_source.count('"width": "stretch"') >= 6
        and "st.text_area(label, **kwargs)" in ui_components_source
        and "st.text_input(label, **kwargs)" in ui_components_source
        and "st.selectbox(label, options, **kwargs)" in ui_components_source
        and "st.file_uploader(label, **kwargs)" in ui_components_source,
    )
    input_control_offenders = []
    direct_input_patterns = [
        "st.text_input(",
        "st.selectbox(",
        "st.checkbox(",
        "st.slider(",
        "st.number_input(",
        "st.file_uploader(",
        "st.download_button(",
    ]
    for module in active_modules:
        if module == "ui_components.py":
            continue
        text = (ROOT / module).read_text(encoding="utf-8")
        for pattern in direct_input_patterns:
            if pattern in text:
                input_control_offenders.append(f"{module}:{pattern}")

    checker.check(
        "active pages use shared input control helpers",
        not input_control_offenders,
        ", ".join(input_control_offenders),
    )
    feedback_offenders = []
    direct_feedback_patterns = [
        "st.info(",
        "st.success(",
        "st.error(",
        "st.warning(",
        "st.caption(",
        "st.divider(",
    ]
    for module in active_modules:
        if module == "ui_components.py":
            continue
        text = (ROOT / module).read_text(encoding="utf-8")
        for pattern in direct_feedback_patterns:
            if pattern in text:
                feedback_offenders.append(f"{module}:{pattern}")

    checker.check(
        "active pages use shared feedback helpers",
        not feedback_offenders,
        ", ".join(feedback_offenders),
    )
    shell_offenders = []
    direct_shell_patterns = [
        "st.expander(",
        "st.form(",
    ]
    for module in active_modules:
        if module == "ui_components.py":
            continue
        text = (ROOT / module).read_text(encoding="utf-8")
        for pattern in direct_shell_patterns:
            if pattern in text:
                shell_offenders.append(f"{module}:{pattern}")

    checker.check(
        "active pages use shared expander/form helpers",
        not shell_offenders,
        ", ".join(shell_offenders),
    )
    action_offenders = []
    direct_action_patterns = [
        "st.button(",
        "st.rerun(",
        "st.sidebar.button(",
        "st.sidebar.checkbox(",
        "st.sidebar.slider(",
        "st.sidebar.markdown(",
    ]
    for module in active_modules:
        if module == "ui_components.py":
            continue
        text = (ROOT / module).read_text(encoding="utf-8")
        for pattern in direct_action_patterns:
            if pattern in text:
                action_offenders.append(f"{module}:{pattern}")

    checker.check(
        "active pages use shared button/rerun/sidebar helpers",
        not action_offenders,
        ", ".join(action_offenders),
    )
    content_tools = (ROOT / "content_tools.py").read_text(encoding="utf-8")
    main_pages = (ROOT / "main_pages.py").read_text(encoding="utf-8")
    practice_components = (ROOT / "practice_components.py").read_text(encoding="utf-8")
    practice_pages = (ROOT / "practice_pages.py").read_text(encoding="utf-8")
    user_pages = (ROOT / "user_pages.py").read_text(encoding="utf-8")
    ui_components = (ROOT / "ui_components.py").read_text(encoding="utf-8")
    auth = (ROOT / "auth.py").read_text(encoding="utf-8")
    checker.check(
        "import previews use shared preview helper",
        "render_import_preview(" in content_tools
        and "def render_import_preview(" in ui_components
        and "def render_import_dry_run_preview(" in ui_components
        and "render_import_dry_run_preview(" in content_tools
        and "max_rows=8" in ui_components
        and "render_preview_table(rows, empty_message=empty_message, height=height, max_rows=max_rows)" in ui_components
        and "render_metric_row(" not in content_tools
        and "render_preview_table(" not in content_tools,
    )
    checker.check(
        "metric rows use responsive shared grid",
        "def render_metric_row(" in ui_components
        and "metric-grid" in ui_components
        and "st.columns(len(metrics)" not in ui_components
        and ".metric-grid" in (ROOT / "styles.py").read_text(encoding="utf-8"),
    )
    text_rendering = (ROOT / "text_rendering.py").read_text(encoding="utf-8")
    checker.check(
        "text renderer centralizes notices and debug expanders",
        "def render_text_info(" in text_rendering
        and "def render_text_warning(" in text_rendering
        and "def render_text_expander(" in text_rendering
        and text_rendering.count("st.info(") == 1
        and text_rendering.count("st.warning(") == 1
        and text_rendering.count("st.expander(") == 1,
    )
    checker.check(
        "page control rows use shared layout helper",
        "def render_control_row(" in ui_components
        and "render_control_row(" in content_tools
        and "render_control_row(" in main_pages
        and "render_control_row(" in practice_pages
        and "render_control_row(" in user_pages
        and 'width="stretch"' in ui_components
        and "vertical_alignment=vertical_alignment" in ui_components
        and "st.columns(" not in content_tools
        and "st.columns(" not in main_pages
        and "st.columns(" not in practice_pages
        and "st.columns(" not in user_pages,
    )
    checker.check(
        "page tabs use shared tab helper",
        "def render_tab_set(" in ui_components
        and "render_tab_set(" in content_tools
        and "render_tab_set(" in practice_components
        and "st.tabs(" not in content_tools
        and "st.tabs(" not in main_pages
        and "st.tabs(" not in practice_pages
        and "st.tabs(" not in practice_components,
    )
    checker.check(
        "compact instructional notes use shared helper",
        "def render_compact_note(" in ui_components
        and "render_compact_note(" in content_tools
        and "render_compact_note(" in practice_pages,
    )
    checker.check("import page avoids direct dataframe rendering", "st.dataframe(" not in content_tools)
    checker.check("import page uses shared question save helper", "save_question_from_mapping(" in content_tools and "add_question(" not in content_tools)
    checker.check(
        "import page uses shared CSV field contract",
        "csv_template_text(" in content_tools and "missing_csv_required_columns(" in content_tools,
    )
    checker.check(
        "manual entry uses shared question field options",
        "QUESTION_SEASON_OPTIONS" in content_tools
        and "QUESTION_STATUS_OPTIONS" in content_tools
        and "DEFAULT_QUESTION_PRIORITY" in content_tools
        and '"Retired standalone - background only"' not in content_tools
        and '["February", "July", "Other"]' not in content_tools,
    )
    checker.check(
        "manual entry form is split into field helpers",
        "def render_manual_entry_metadata_fields(" in content_tools
        and "def render_manual_entry_content_fields(" in content_tools
        and "values.update(render_manual_entry_metadata_fields())" in content_tools
        and "values.update(render_manual_entry_content_fields())" in content_tools
        and "save_question_from_mapping(values)" in content_tools,
    )
    checker.check(
        "CSV import uses service helpers",
        "csv_import_metrics(" in content_tools
        and "csv_import_preview_rows(" in content_tools
        and "save_questions_from_dataframe(" in content_tools
        and "df.head(" not in content_tools
        and ".iterrows(" not in content_tools,
    )
    checker.check(
        "import completion messages use shared helper",
        "def render_import_success(" in ui_components
        and "def render_import_apply_action(" in ui_components
        and "render_import_apply_action(" in content_tools
        and "render_import_success(" not in content_tools
        and "Imported {imported}" not in content_tools
        and "Backup created:" not in content_tools,
    )
    checker.check(
        "import actions use shared primary button helper",
        "def render_primary_action_button(" in ui_components
        and "def render_import_apply_action(" in ui_components
        and "render_import_apply_action(" in content_tools
        and "render_primary_action_button(" not in content_tools
        and 'st.button("Import' not in content_tools,
    )
    form_submit_offenders = []
    for module_name, module_text in {
        "content_tools.py": content_tools,
        "main_pages.py": main_pages,
        "practice_pages.py": practice_pages,
        "practice_components.py": practice_components,
        "user_pages.py": user_pages,
    }.items():
        if "st.form_submit_button(" in module_text:
            form_submit_offenders.append(module_name)

    checker.check(
        "forms use shared submit button helper",
        "def render_form_submit_button(" in ui_components
        and "render_form_submit_button(" in content_tools
        and "render_form_submit_button(" in user_pages
        and not form_submit_offenders,
        ", ".join(form_submit_offenders),
    )
    shell_primitive_offenders = []
    for module_name, module_text in {
        "auth.py": auth,
        "content_tools.py": content_tools,
        "main_pages.py": main_pages,
        "practice_pages.py": practice_pages,
        "practice_components.py": practice_components,
        "user_pages.py": user_pages,
    }.items():
        if "st.spinner(" in module_text or "st.stop(" in module_text:
            shell_primitive_offenders.append(module_name)

    checker.check(
        "active modules use shared spinner/stop helpers",
        "def render_spinner(" in ui_components
        and "def stop_app(" in ui_components
        and "render_import_dry_run_preview(" in content_tools
        and "render_import_apply_action(" in content_tools
        and "render_spinner(" not in content_tools
        and "stop_app(" in auth
        and not shell_primitive_offenders,
        ", ".join(shell_primitive_offenders),
    )
    checker.check(
        "MEE Question Bank uses shared question detail tabs",
        "render_question_detail_tabs(" in main_pages
        and "def render_question_detail_tabs" in ui_components
        and "render_call_text(" not in main_pages,
    )
    checker.check(
        "MEE Question Bank filters are helper-driven",
        "def render_question_bank_filters(" in main_pages
        and "def question_bank_added_date_range(" in main_pages
        and "def question_bank_rows_dataframe(" in main_pages
        and "def render_question_bank_results_table(" in main_pages
        and "def select_question_bank_row(" in main_pages
        and "QUESTION_BANK_ADDED_DATE_OPTIONS" in main_pages
        and "get_question_bank_rows(**render_question_bank_filters())" in main_pages
        and "render_question_bank_results_table(rows)" in main_pages
        and "select_question_bank_row(rows)" in main_pages
        and "selected_added_date = render_selectbox" in main_pages
        and "created_from = None" not in main_pages,
    )
    checker.check(
        "question identity display uses shared helper",
        "def render_question_identity(" in ui_components
        and "render_question_identity(" in main_pages
        and "render_question_identity(" in practice_pages
        and "st.subheader(f\"{qd['exam_name']}" not in main_pages
        and "st.caption(\n        f\"{qd['exam_name']}" not in practice_pages,
    )
    checker.check(
        "page navigation uses shared helpers",
        "def go_to_page(" in ui_components
        and "def render_nav_button(" in ui_components
        and 'st.session_state["current_page"] =' not in main_pages,
    )
    app_state = (ROOT / "app_state.py").read_text(encoding="utf-8")
    shared_state_key_offenders = []
    shared_state_keys = [
        '"current_page"',
        '"_authed_user"',
        '"_authed_name"',
        '"_is_admin"',
        '"adhd_mode"',
    ]
    for module_name, module_text in {
        "app_shell.py": (ROOT / "app_shell.py").read_text(encoding="utf-8"),
        "auth.py": (ROOT / "auth.py").read_text(encoding="utf-8"),
        "content_tools.py": content_tools,
        "main_pages.py": main_pages,
        "practice_pages.py": practice_pages,
        "practice_components.py": practice_components,
        "ui_components.py": ui_components,
        "user_pages.py": user_pages,
    }.items():
        for key in shared_state_keys:
            if key in module_text:
                shared_state_key_offenders.append(f"{module_name}:{key}")

    checker.check(
        "shared session-state keys use app_state helpers",
        all(key in app_state for key in shared_state_keys)
        and "def get_current_page(" in app_state
        and "def set_auth_user(" in app_state
        and not shared_state_key_offenders,
        ", ".join(shared_state_key_offenders),
    )
    checker.check(
        "question picker random choice is centralized",
        "def _select_random_question(" in ui_components
        and ui_components.count("random.randrange(") == 1,
    )
    checker.check(
        "question selector labels use shared format helpers",
        "def format_picker_question_label(" in ui_components
        and "def format_bank_question_label(" in ui_components
        and "format_picker_question_label(" in ui_components
        and "format_bank_question_label(" in main_pages
        and "Q{row[" not in main_pages
        and "Priority {row[" not in main_pages,
    )
    checker.check(
        "matching counts use shared helper",
        "def render_match_count(" in ui_components
        and "def format_match_count(" in ui_components
        and "render_match_count(" in main_pages
        and 'st.caption(f"{len(' not in main_pages
        and 'st.caption(f"{len(' not in ui_components,
    )
    checker.check(
        "practice ladder metadata and save use shared helpers",
        "LADDER_LEVELS" in practice_components
        and "def ladder_goal(" in practice_components
        and "def training_score(" in practice_components
        and "def save_ladder_attempt(" in practice_components
        and "def render_save_attempt_button(" in practice_components
        and "def render_save_mini_drill_attempt(" in practice_components
        and "def render_save_ladder_attempt(" in practice_components
        and "def render_ladder_response_input(" in practice_components
        and "render_save_mini_drill_attempt(" in practice_pages
        and "render_save_ladder_attempt(" in practice_pages
        and "save_ladder_attempt(" not in practice_pages.replace("render_save_ladder_attempt(", "")
        and "render_ladder_response_input(" in practice_pages
        and "save_attempt(" not in practice_pages
        and '"Save Mini Drill Attempt"' not in practice_pages
        and '"Save Muscle Ladder Attempt"' not in practice_pages
        and "def _ladder_goal(" not in practice_pages,
    )
    checker.check(
        "practice ladder input rendering is shared",
        "def render_ladder_response_input(" in practice_components
        and "def _render_ladder_response_input(" not in practice_pages,
    )
    checker.check(
        "practice mini drill exposes manual trigger highlighting and plug-play support",
        "def render_mini_drill_tab(" in practice_pages
        and "render_mini_prompt_panel(" in practice_pages
        and "render_ladder_prompt_panel(" in practice_pages
        and "render_plug_play_support(" in practice_pages
        and "render_practice_review_panel(" in practice_pages
        and "render_mini_drill_response_input(" in practice_pages
        and "def render_mini_prompt_panel(" in practice_components
        and "def render_ladder_prompt_panel(" in practice_components
        and '"Highlight relevant triggering facts"' in practice_components
        and "def render_mini_drill_response_input(" in practice_components
        and "def render_plug_play_support(" in practice_components
        and "def render_model_answer_panel(" in practice_components
        and "def render_practice_review_panel(" in practice_components
        and "render_divider()" in practice_components
        and "render_divider()" not in practice_pages
        and "render_question_highlights_with_fallback(" in practice_components
        and "render_trigger_rule_map(" in practice_components
        and "def render_trigger_rule_map(" in (ROOT / "text_rendering.py").read_text(encoding="utf-8"),
    )
    checker.check(
        "practice reveal controls use shared helper",
        "def render_reveal_control(" in ui_components
        and "render_reveal_control(" in practice_pages
        and "reveal_gate_box(" not in practice_pages
        and 'st.session_state[f"mini_reveal_state_' not in practice_pages
        and 'st.session_state[f"ladder_reveal_' not in practice_pages,
    )
    styles = (ROOT / "styles.py").read_text(encoding="utf-8")
    text_rendering = (ROOT / "text_rendering.py").read_text(encoding="utf-8")
    checker.check(
        "plug-play templates use LBP-inspired style tokens",
        "#D91B2E" in styles
        and "#AEE3BD" in styles
        and "#3B3434" in styles
        and "plug-placeholder" in styles
        and "plug-meta-pill" in styles
        and "format_plug_text_html(" in text_rendering,
    )

    legacy_import_offenders = []
    for module in ["import_questions_bank.py", "import_questions_docx.py"]:
        text = (ROOT / module).read_text(encoding="utf-8")
        if (
            "save_question_from_mapping(" not in text
            or "add_question(" in text
            or "def question_exists" in text
        ):
            legacy_import_offenders.append(module)

    checker.check(
        "legacy question importers use shared DB helpers",
        not legacy_import_offenders,
        ", ".join(legacy_import_offenders),
    )
    markdown_importer = (ROOT / "import_markdown_mee_qa_bank.py").read_text(encoding="utf-8")
    docx_bank_importer = (ROOT / "import_mee_pq_bank_docx.py").read_text(encoding="utf-8")
    database_source = (ROOT / "database.py").read_text(encoding="utf-8")
    checker.check(
        "bank importers use shared question import index",
        "def get_question_import_index(" in database_source
        and "def question_import_key(" in database_source
        and "database.get_question_import_index()" in markdown_importer
        and "database.get_question_import_index(include_model_points=True)" in docx_bank_importer
        and "def existing_question_map(" not in markdown_importer
        and "SELECT id, exam_name, question_number" not in markdown_importer
        and "SELECT id, exam_name, question_number" not in docx_bank_importer,
    )


def check_layout_width_styles(checker: HealthCheck) -> None:
    styles = (ROOT / "styles.py").read_text(encoding="utf-8")
    app_shell = (ROOT / "app_shell.py").read_text(encoding="utf-8")
    ui_components = (ROOT / "ui_components.py").read_text(encoding="utf-8")
    mbe_pages = (ROOT / "mbe_pages.py").read_text(encoding="utf-8")
    mbe_html = (ROOT / "mbe_trap_trainer.html").read_text(encoding="utf-8")

    checker.check("page container is configured for full width", "max-width: none !important" in styles)
    checker.check("sample answer box is not globally narrow capped", ".sample-answer-box" in styles and "max-width: 980px" not in styles)
    checker.check("question boxes are not globally narrow capped", ".question-box" in styles and "max-width: 1000px" not in styles)
    checker.check("normal reading width uses full-width constant", "FULL_WIDTH_TEXT_MAX" in app_shell and "max_width = FULL_WIDTH_TEXT_MAX" in app_shell)
    checker.check("reading styles govern sample-answer width", ".sample-answer-box," in styles and "max-width: min({max_width}px, 100%)" in styles)
    checker.check("embedded HTML tools use shared contained height", "EMBEDDED_TOOL_HEIGHT = 860" in ui_components)
    checker.check(
        "MBE page uses full-page viewport HTML embed",
        "FULL_PAGE_EMBED_HEIGHT" in ui_components
        and "FULL_PAGE_EMBED_HEIGHT" in mbe_pages
        and "render_page_title(" not in mbe_pages
        and "height=2400" not in mbe_pages
        and "height: calc(100vh" in styles
        and "height: calc(100vh" in mbe_pages
        and 'div[data-testid="stElementContainer"]:has(iframe)' in mbe_pages
        and 'iframe[srcdoc]' in mbe_pages
        and ".full-page-embed" in styles,
    )
    checker.check(
        "HTML embed marker does not reserve vertical space",
        'class="full-page-embed" aria-hidden="true"' in ui_components
        and 'components.html(html, height=height, scrolling=True)\n    st.markdown("</div>"' not in ui_components
        and "height: 0 !important" in styles
        and "height: 0 !important" in mbe_pages,
    )
    checker.check(
        "MBE drill screen is viewport-fitted",
        "function setViewportMode" in mbe_html
        and "body.drill-screen #app" in mbe_html
        and "grid-template-columns:repeat(2,minmax(0,1fr))" in mbe_html
        and "display:none" in mbe_html
        and "function renderDrill()" in mbe_html
        and "setViewportMode('drill')" in mbe_html,
    )
    readability_marker = "/* larger, more readable question + answers */"
    aesthetic_marker = "/* ================= END AESTHETIC UPGRADE ================= */"
    checker.check(
        "MBE question and answer text uses readable override sizes",
        readability_marker in mbe_html
        and aesthetic_marker in mbe_html
        and mbe_html.index(readability_marker) < mbe_html.index(aesthetic_marker)
        and ".call-text{font-size:19px !important;line-height:1.45 !important}" in mbe_html
        and ".facts-text{font-size:16.5px !important;line-height:1.7 !important}" in mbe_html
        and ".facts-label, .call-tag{font-size:10px !important}" in mbe_html
        and ".qtitle{font-size:17px !important;line-height:1.6 !important}" in mbe_html
        and ".opts .opt{font-size:16px !important;line-height:1.5 !important;padding:14px 16px !important}" in mbe_html
        and ".opts .opt .key{font-size:14px !important}" in mbe_html,
    )


def check_mbe_drill_workflow_controls(checker: HealthCheck) -> None:
    mbe_html = (ROOT / "mbe_trap_trainer.html").read_text(encoding="utf-8")

    checker.check(
        "MBE note button uses user-facing label",
        "Add A Note to Myself" in mbe_html
        and "Note to myself (saved for later):" in mbe_html
        and "Add Future Change" not in mbe_html
        and "Future change idea" not in mbe_html,
    )
    checker.check(
        "MBE two-week skip control is present",
        "Don't ask this question again for 2 weeks" in mbe_html
        and 'id="snoozeTwoWeeks"' in mbe_html
        and "function snoozeCardForTwoWeeks(card, btnEl)" in mbe_html,
    )
    checker.check(
        "MBE two-week skip persists scheduling state",
        "snoozedUntil: null" in mbe_html
        and "stats.snoozedUntil = until" in mbe_html
        and "stats.nextReviewAt = until" in mbe_html
        and "item.snoozedUntil = until" in mbe_html,
    )
    checker.check(
        "MBE queues exclude snoozed cards",
        "function isCardSnoozed(card)" in mbe_html
        and "if (isCardSnoozed(c)) return false;" in mbe_html
        and "dueKeys.has(cardKey(card)) && !isCardSnoozed(card)" in mbe_html
        and 'passesDateFilter(d, state.dateFilter || "all") && !isCardSnoozed(d)' in mbe_html,
    )
    checker.check(
        "MBE trigger highlighting has doctrine-agnostic fallback",
        "function extractGenericSignalPhrases(text)" in mbe_html
        and "extractGenericSignalPhrases(stem)" in mbe_html
        and "let result = limitTriggerPhrases(matched, null, doctrine);" in mbe_html
        and "if (!result || result.length === 0)" in mbe_html
        and "\\bchallenge the constitutionality\\b" in mbe_html
        and "\\bFirst Amendment\\b" in mbe_html
        and "\\bordinance\\b" in mbe_html,
    )


def check_import_parser(checker: HealthCheck) -> None:
    import import_services
    import mbe_import_services

    missing_template_columns = import_services.missing_csv_required_columns(import_services.CSV_TEMPLATE_RECORD.keys())
    checker.check("CSV template includes all required columns", not missing_template_columns, ", ".join(missing_template_columns))
    checker.check(
        "question import field constants exist",
        import_services.QUESTION_SEASON_OPTIONS[0] == "February"
        and import_services.DEFAULT_QUESTION_STATUS == import_services.QUESTION_STATUS_OPTIONS[0]
        and import_services.DEFAULT_QUESTION_PRIORITY == 3,
    )
    checker.check(
        "CSV template uses shared question defaults",
        import_services.CSV_TEMPLATE_RECORD["exam_season"] == import_services.QUESTION_SEASON_OPTIONS[0]
        and import_services.CSV_TEMPLATE_RECORD["july_2026_status"] == import_services.DEFAULT_QUESTION_STATUS,
    )
    template_header = import_services.csv_template_text().splitlines()[0].split(",")
    missing_generated_template_columns = import_services.missing_csv_required_columns(template_header)
    checker.check(
        "generated CSV template includes all required columns",
        not missing_generated_template_columns,
        ", ".join(missing_generated_template_columns),
    )
    try:
        import pandas as pd

        sample_df = pd.DataFrame([import_services.CSV_TEMPLATE_RECORD])
        csv_missing = import_services.missing_csv_required_columns(sample_df.columns)
        csv_metrics = import_services.csv_import_metrics(sample_df, csv_missing)
        csv_preview = import_services.csv_import_preview_rows(sample_df)
    except Exception as exc:
        checker.check("CSV service helpers run", False, str(exc))
    else:
        checker.check("CSV service helpers run", True)
        checker.check("CSV service metrics include row count", ("Rows", 1) in csv_metrics, str(csv_metrics))
        checker.check("CSV service preview returns first row", len(csv_preview) == 1, str(len(csv_preview)))

    try:
        import fitz

        pdf_doc = fitz.open()
        pdf_page = pdf_doc.new_page()
        pdf_page.insert_text(
            (72, 72),
            "\n".join([
                "Subject: Contracts",
                "Exam: July 2019",
                "Question 1: Is the oral modification binding?",
                "Answer: Likely no under common law without consideration.",
                "Rule Outline: Common law modifications require consideration.",
            ]),
            fontsize=12,
        )
        pdf_bytes = pdf_doc.tobytes()
        pdf_doc.close()

        class _HealthPdfUpload:
            name = "health-check.pdf"

            def getvalue(self):
                return pdf_bytes

        pdf_text, pdf_records, pdf_report = import_services.run_pdf_text_import(
            _HealthPdfUpload(),
            apply=False,
            allow_truncated=True,
        )
    except Exception as exc:
        checker.check("PDF import dry run parses upload-like file", False, str(exc))
    else:
        checker.check("PDF import dry run extracts text", "Question 1:" in pdf_text, pdf_text[:120])
        checker.check(
            "PDF import dry run parses one record",
            len(pdf_records) == 1 and pdf_report["records_parsed"] == 1,
            str((len(pdf_records), pdf_report)),
        )
        if pdf_records:
            checker.check("PDF import dry run captures answer", bool(pdf_records[0].model_points.strip()))
            checker.check("PDF import dry run captures rule outline", bool(pdf_records[0].rules.strip()))

    mbe_pages = (ROOT / "mbe_pages.py").read_text(encoding="utf-8")
    checker.check(
        "MBE bulk upload parsing uses service helpers",
        "pd.read_csv(" not in mbe_pages
        and "pd.read_excel(" not in mbe_pages
        and "read_mbe_bulk_upload(" in mbe_pages
        and "mbe_upload_metrics(" in mbe_pages,
    )
    try:
        import pandas as pd

        mbe_sample = pd.DataFrame([{column: "x" for column in mbe_import_services.MBE_BULK_TEMPLATE_COLUMNS}])
        mbe_missing = mbe_import_services.missing_mbe_template_columns(mbe_sample.columns)
        mbe_extra = mbe_import_services.extra_mbe_template_columns(mbe_sample.columns)
        mbe_metrics = mbe_import_services.mbe_upload_metrics(mbe_sample, mbe_missing, mbe_extra)
        mbe_preview = mbe_import_services.mbe_upload_preview_rows(mbe_sample)
    except Exception as exc:
        checker.check("MBE bulk service helpers run", False, str(exc))
    else:
        checker.check("MBE bulk service helpers run", True)
        checker.check("MBE bulk service metrics include row count", ("Rows", 1) in mbe_metrics, str(mbe_metrics))
        checker.check("MBE bulk service preview returns first row", len(mbe_preview) == 1, str(len(mbe_preview)))

    simple_text = """
Subject: Contracts
Exam: July 2019

Question 1: Is the oral modification binding?
Answer: Likely no under common law without consideration.
Rule Outline: Common law modifications require consideration.
"""
    jammed_text = (
        "Subject: Contracts Exam: July 2019 Question 1: Is the oral modification binding? "
        "Answer: Likely no. Rule Outline: Modifications require consideration. "
        "Tested Issues: Modification. Traps: Do not assume UCC."
    )

    for label, sample in [("simple", simple_text), ("jammed", jammed_text)]:
        records, report = run_markdown_text_import(sample, apply=False)
        checker.check(f"{label} text import parses one record", len(records) == 1 and report["records_parsed"] == 1)
        if records:
            record = records[0]
            checker.check(f"{label} text import captures subject", record.subject == "Contracts", record.subject)
            checker.check(f"{label} text import captures exam", record.exam_name == "July 2019", record.exam_name)
            checker.check(f"{label} text import captures answer", bool(record.model_points.strip()))
            checker.check(f"{label} text import captures rule outline", bool(record.rules.strip()))


def check_shared_question_save_path(checker: HealthCheck) -> None:
    """Verify CSV/manual-entry question saving uses one helper and can write safely."""
    import database
    import import_services
    import pandas as pd

    with temporary_database_copy("mee_question_save_health_") as temp_db:
        import_services.save_question_from_mapping({
            "exam_name": "July 2098",
            "question_number": "88",
            "subject": "Evidence",
            "question_text": "Health-check prompt.",
            "call_of_question": "Should this disposable record save? Explain.",
            "tested_issues": "Shared save helper",
            "rules": "A shared save helper should preserve rule text.",
            "trigger_facts": "Temporary DB copy",
            "traps": "Do not touch the real database.",
            "model_points": "This model answer is stored only in the temp DB.",
            "active_for_july_2026": "true",
            "exam_year": "2098",
            "exam_season": "July",
            "secondary_subjects": "",
            "july_2026_status": "Active standalone MEE",
            "priority": "4",
            "source": "health-check",
        })
        bulk_df = pd.DataFrame([{
            **import_services.CSV_TEMPLATE_RECORD,
            "exam_name": "February 2098",
            "question_number": "89",
            "subject": "Contracts",
            "source": "health-check-bulk",
        }])
        bulk_count = import_services.save_questions_from_dataframe(bulk_df)

        temp_conn = sqlite3.connect(temp_db)
        try:
            temp_row = temp_conn.execute(
                """
                SELECT subject, rules, active_for_july_2026, exam_year, priority, source
                FROM questions
                WHERE exam_name = ? AND question_number = ?
                """,
                ("July 2098", "88"),
            ).fetchone()
            bulk_row = temp_conn.execute(
                """
                SELECT subject, source
                FROM questions
                WHERE exam_name = ? AND question_number = ?
                """,
                ("February 2098", "89"),
            ).fetchone()
        finally:
            temp_conn.close()

        real_conn = sqlite3.connect(DB_PATH)
        try:
            real_count = real_conn.execute(
                "SELECT COUNT(*) FROM questions WHERE exam_name = ? AND question_number = ?",
                ("July 2098", "88"),
            ).fetchone()[0]
            real_bulk_count = real_conn.execute(
                "SELECT COUNT(*) FROM questions WHERE exam_name = ? AND question_number = ?",
                ("February 2098", "89"),
            ).fetchone()[0]
        finally:
            real_conn.close()

    checker.check("shared question save helper writes to configured DB", bool(temp_row), str(temp_row))
    checker.check(
        "shared question save helper preserves typed fields",
        bool(temp_row) and temp_row == ("Evidence", "A shared save helper should preserve rule text.", 1, 2098, 4, "health-check"),
        str(temp_row),
    )
    checker.check("bulk CSV save helper writes rows", bulk_count == 1 and bulk_row == ("Contracts", "health-check-bulk"), str((bulk_count, bulk_row)))
    checker.check("shared question save helper leaves real DB untouched", real_count == 0, str(real_count))
    checker.check("bulk CSV save helper leaves real DB untouched", real_bulk_count == 0, str(real_bulk_count))


def check_text_import_apply_path(checker: HealthCheck) -> None:
    """Verify text import apply writes to a disposable DB copy, not the real DB."""
    import database
    import import_markdown_mee_qa_bank
    import import_mee_pq_bank_docx

    sample_text = """
Subject: Contracts
Exam: July 2099

Question 77: Is this health-check import isolated?
Answer: Yes. This answer exists only inside a disposable database copy.
Rule Outline: A safe import test writes to the configured database path only.
"""

    with temporary_database_copy("mee_import_health_") as temp_db:
        before_real = sqlite3.connect(DB_PATH)
        try:
            real_before_count = before_real.execute(
                "SELECT COUNT(*) FROM questions WHERE exam_name = ? AND question_number = ?",
                ("July 2099", "77"),
            ).fetchone()[0]
        finally:
            before_real.close()

        records, report = run_markdown_text_import(sample_text, apply=True, allow_truncated=False)

        temp_conn = sqlite3.connect(temp_db)
        try:
            temp_row = temp_conn.execute(
                """
                SELECT subject, model_points, rules
                FROM questions
                WHERE exam_name = ? AND question_number = ?
                """,
                ("July 2099", "77"),
            ).fetchone()
        finally:
            temp_conn.close()

        after_real = sqlite3.connect(DB_PATH)
        try:
            real_after_count = after_real.execute(
                "SELECT COUNT(*) FROM questions WHERE exam_name = ? AND question_number = ?",
                ("July 2099", "77"),
            ).fetchone()[0]
        finally:
            after_real.close()

    checker.check("text import apply parses one record", len(records) == 1 and report["records_parsed"] == 1)
    checker.check("text import apply reports insert", report["records_to_insert"] == 1, str(report))
    checker.check("text import apply writes to configured DB", bool(temp_row), str(temp_row))
    checker.check(
        "text import apply preserves answer and rule fields",
        bool(temp_row) and "disposable database copy" in temp_row[1] and "configured database path" in temp_row[2],
    )
    checker.check("text import apply leaves real DB untouched", real_before_count == real_after_count == 0)
    checker.check(
        "markdown importer uses dynamic app DB path",
        import_markdown_mee_qa_bank.current_db_path() == Path(database.DB_NAME),
    )
    checker.check(
        "DOCX importer uses dynamic app DB path",
        import_mee_pq_bank_docx.current_db_path() == Path(database.DB_NAME),
    )


def check_answer_display_coverage(checker: HealthCheck) -> None:
    rows = load_questions(DB_PATH)
    missing = []

    for row in rows:
        (
            question_id,
            _exam_name,
            _question_number,
            _subject,
            call_of_question,
            model_points,
            rules,
            tested_issues,
            trigger_facts,
            traps,
            _source,
        ) = row
        structured_text = " ".join(str(value or "") for value in (tested_issues, rules, trigger_facts, traps))
        subquestion_count = extract_subquestions_simple(call_of_question)
        points = split_model_answer_points_simple(model_points)
        _status, _notes, _missing_points, coverage = audit_status(
            subquestion_count,
            points,
            len(str(model_points or "").strip()),
            has_structured_bank=bool(structured_text.strip()),
        )
        if coverage == "NO":
            missing.append(question_id)

    checker.check("all questions have answer display coverage", not missing, ", ".join(map(str, missing[:20])))


def check_practice_save_path(checker: HealthCheck) -> None:
    """Verify practice attempts save and schedule review using a disposable DB copy."""
    import database
    from practice_components import ladder_goal, save_ladder_attempt, training_score

    checker.check("ladder goal helper returns Level 1 timing", ladder_goal("Level 1 - Issue + Rule Mini Run - 7 min")[0] == 7)
    checker.check("training score helper averages scores", training_score(5, 4, 3) == 4)

    with tempfile.TemporaryDirectory(prefix="mee_health_") as tmp_dir:
        temp_db = Path(tmp_dir) / DB_NAME
        shutil.copy2(DB_PATH, temp_db)
        original_db_name = database.DB_NAME
        database.DB_NAME = str(temp_db)

        try:
            conn = database.get_connection()
            try:
                question_id = conn.execute("SELECT id FROM questions ORDER BY id LIMIT 1").fetchone()[0]
                before_attempts = conn.execute("SELECT COUNT(*) FROM attempts").fetchone()[0]
            finally:
                conn.close()

            save_ladder_attempt(
                {"id": question_id},
                "Health Check",
                "Test response",
                4,
                "",
                "Disposable health-check attempt.",
                7,
            )

            conn = database.get_connection()
            try:
                after_attempts = conn.execute("SELECT COUNT(*) FROM attempts").fetchone()[0]
                last_practiced_at, next_review_at = conn.execute(
                    "SELECT last_practiced_at, next_review_at FROM questions WHERE id = ?",
                    (question_id,),
                ).fetchone()
            finally:
                conn.close()

            attempts = database.get_attempts(limit=1)
        finally:
            database.DB_NAME = original_db_name

    checker.check("practice save inserts one attempt", after_attempts == before_attempts + 1)
    checker.check("practice save updates last practiced date", bool(last_practiced_at))
    checker.check("practice save schedules review date", bool(next_review_at))
    checker.check(
        "practice attempt retrieval includes saved attempt",
        bool(attempts) and attempts[0][1] == question_id and attempts[0][5] == "Health Check",
    )


def check_outline_rule_save_path(checker: HealthCheck) -> None:
    """Verify outline rules use the configured DB and preserve duplicate behavior."""
    import database

    with tempfile.TemporaryDirectory(prefix="mee_outline_rule_health_") as tmp_dir:
        temp_db = Path(tmp_dir) / DB_NAME
        shutil.copy2(DB_PATH, temp_db)
        original_db_name = database.DB_NAME
        database.DB_NAME = str(temp_db)

        try:
            created = database.add_outline_rule(
                "Evidence",
                "Health Check Rule",
                "Medium",
                "This temporary rule exists only in a disposable database copy.",
                9999,
                "9999",
                "health-check-outline",
            )
            duplicate = database.add_outline_rule(
                "Evidence",
                "Health Check Rule",
                "Medium",
                "This temporary rule exists only in a disposable database copy.",
                9999,
                "9999",
                "health-check-outline",
            )

            conn = database.get_connection()
            try:
                temp_count = conn.execute(
                    """
                    SELECT COUNT(*)
                    FROM outline_rules
                    WHERE source_file = ? AND rule_title = ?
                    """,
                    ("health-check-outline", "Health Check Rule"),
                ).fetchone()[0]
            finally:
                conn.close()

            real_conn = sqlite3.connect(DB_PATH)
            try:
                real_count = real_conn.execute(
                    """
                    SELECT COUNT(*)
                    FROM outline_rules
                    WHERE source_file = ? AND rule_title = ?
                    """,
                    ("health-check-outline", "Health Check Rule"),
                ).fetchone()[0]
            finally:
                real_conn.close()
        finally:
            database.DB_NAME = original_db_name

    checker.check("outline rule save inserts into configured DB", created and temp_count == 1, str(temp_count))
    checker.check("outline rule save skips duplicate", duplicate is False and temp_count == 1, str((duplicate, temp_count)))
    checker.check("outline rule save leaves real DB untouched", real_count == 0, str(real_count))


def check_rule_flashcard_save_path(checker: HealthCheck) -> None:
    """Verify rule flashcards use the configured DB and preserve duplicate behavior."""
    import database

    with tempfile.TemporaryDirectory(prefix="mee_flashcard_health_") as tmp_dir:
        temp_db = Path(tmp_dir) / DB_NAME
        shutil.copy2(DB_PATH, temp_db)
        original_db_name = database.DB_NAME
        database.DB_NAME = str(temp_db)

        try:
            created = database.add_rule_flashcard(
                "Evidence",
                "Health Check Flashcard",
                "This temporary flashcard exists only in a disposable database copy.",
                "health-check-flashcard",
                "health-check",
            )
            duplicate = database.add_rule_flashcard(
                "Evidence",
                "Health Check Flashcard",
                "This temporary flashcard exists only in a disposable database copy.",
                "health-check-flashcard",
                "health-check",
            )

            conn = database.get_connection()
            try:
                temp_count = conn.execute(
                    """
                    SELECT COUNT(*)
                    FROM rule_flashcards
                    WHERE source_file = ? AND rule_title = ?
                    """,
                    ("health-check-flashcard", "Health Check Flashcard"),
                ).fetchone()[0]
            finally:
                conn.close()

            real_conn = sqlite3.connect(DB_PATH)
            try:
                real_count = real_conn.execute(
                    """
                    SELECT COUNT(*)
                    FROM rule_flashcards
                    WHERE source_file = ? AND rule_title = ?
                    """,
                    ("health-check-flashcard", "Health Check Flashcard"),
                ).fetchone()[0]
            finally:
                real_conn.close()
        finally:
            database.DB_NAME = original_db_name

    checker.check("rule flashcard save inserts into configured DB", created and temp_count == 1, str(temp_count))
    checker.check("rule flashcard save skips duplicate", duplicate is False and temp_count == 1, str((duplicate, temp_count)))
    checker.check("rule flashcard save leaves real DB untouched", real_count == 0, str(real_count))


def check_plug_play_template_save_path(checker: HealthCheck) -> None:
    """Verify Plug & Play templates use the configured DB and preserve duplicate behavior."""
    import database

    with tempfile.TemporaryDirectory(prefix="mee_plug_play_health_") as tmp_dir:
        temp_db = Path(tmp_dir) / DB_NAME
        shutil.copy2(DB_PATH, temp_db)
        original_db_name = database.DB_NAME
        database.DB_NAME = str(temp_db)

        try:
            created = database.add_plug_play_template(
                "Evidence",
                "Health Check Template",
                "When a temporary health-check trigger appears.",
                "Whether the temporary template should save.",
                "A disposable test should write only to the configured DB.",
                "Apply the temporary rule to the temporary facts.",
                "Therefore, the temporary test passes.",
                "health-check",
                9999,
                "health-check-plug-play",
            )
            duplicate = database.add_plug_play_template(
                "Evidence",
                "Health Check Template",
                "When a temporary health-check trigger appears.",
                "Whether the temporary template should save.",
                "A disposable test should write only to the configured DB.",
                "Apply the temporary rule to the temporary facts.",
                "Therefore, the temporary test passes.",
                "health-check",
                9999,
                "health-check-plug-play",
            )

            conn = database.get_connection()
            try:
                temp_count = conn.execute(
                    """
                    SELECT COUNT(*)
                    FROM plug_play_templates
                    WHERE source_file = ? AND module_title = ?
                    """,
                    ("health-check-plug-play", "Health Check Template"),
                ).fetchone()[0]
            finally:
                conn.close()

            real_conn = sqlite3.connect(DB_PATH)
            try:
                real_count = real_conn.execute(
                    """
                    SELECT COUNT(*)
                    FROM plug_play_templates
                    WHERE source_file = ? AND module_title = ?
                    """,
                    ("health-check-plug-play", "Health Check Template"),
                ).fetchone()[0]
            finally:
                real_conn.close()
        finally:
            database.DB_NAME = original_db_name

    checker.check("plug-play template save inserts into configured DB", created and temp_count == 1, str(temp_count))
    checker.check("plug-play template save skips duplicate", duplicate is False and temp_count == 1, str((duplicate, temp_count)))
    checker.check("plug-play template save leaves real DB untouched", real_count == 0, str(real_count))


def check_admin_upsert_path(checker: HealthCheck) -> None:
    """Verify admin seeding creates and refreshes users in the configured DB."""
    import database

    with tempfile.TemporaryDirectory(prefix="mee_admin_health_") as tmp_dir:
        temp_db = Path(tmp_dir) / DB_NAME
        shutil.copy2(DB_PATH, temp_db)
        original_db_name = database.DB_NAME
        database.DB_NAME = str(temp_db)

        try:
            database.upsert_admin(
                "health-admin",
                "health-admin@example.com",
                "Health Admin",
                "hash-one",
            )
            database.upsert_admin(
                "health-admin",
                "updated-health-admin@example.com",
                "Updated Health Admin",
                "hash-two",
            )

            conn = database.get_connection()
            try:
                temp_rows = conn.execute(
                    """
                    SELECT username, email, name, password_hash, is_admin
                    FROM app_users
                    WHERE username = ?
                    """,
                    ("health-admin",),
                ).fetchall()
            finally:
                conn.close()

            real_conn = sqlite3.connect(DB_PATH)
            try:
                real_count = real_conn.execute(
                    "SELECT COUNT(*) FROM app_users WHERE username = ?",
                    ("health-admin",),
                ).fetchone()[0]
            finally:
                real_conn.close()
        finally:
            database.DB_NAME = original_db_name

    checker.check("admin upsert creates one configured-DB row", len(temp_rows) == 1, str(temp_rows))
    checker.check(
        "admin upsert refreshes existing admin",
        bool(temp_rows)
        and temp_rows[0] == (
            "health-admin",
            "updated-health-admin@example.com",
            "Updated Health Admin",
            "hash-two",
            1,
        ),
        str(temp_rows),
    )
    checker.check("admin upsert leaves real DB untouched", real_count == 0, str(real_count))


def check_app_user_save_path(checker: HealthCheck) -> None:
    """Verify managed app users save to the configured DB and preserve duplicate messages."""
    import database

    with tempfile.TemporaryDirectory(prefix="mee_app_user_health_") as tmp_dir:
        temp_db = Path(tmp_dir) / DB_NAME
        shutil.copy2(DB_PATH, temp_db)
        original_db_name = database.DB_NAME
        database.DB_NAME = str(temp_db)

        try:
            database.init_db()
            created_ok, created_msg = database.add_app_user(
                "HealthUser",
                "HealthUser@example.com",
                "Health User",
                "hash-one",
                is_admin=False,
            )
            duplicate_user_ok, duplicate_user_msg = database.add_app_user(
                "healthuser",
                "different@example.com",
                "Duplicate User",
                "hash-two",
                is_admin=False,
            )
            duplicate_email_ok, duplicate_email_msg = database.add_app_user(
                "another-health-user",
                "healthuser@example.com",
                "Duplicate Email",
                "hash-three",
                is_admin=True,
            )
            database.set_user_remember_token("healthuser", "remember-hash")
            remembered_user = database.get_app_user_by_remember_token("remember-hash")
            database.clear_user_remember_token("healthuser")
            cleared_user = database.get_app_user_by_remember_token("remember-hash")

            conn = database.get_connection()
            try:
                temp_rows = conn.execute(
                    """
                    SELECT username, email, name, password_hash, is_admin
                    FROM app_users
                    WHERE username = ?
                    """,
                    ("healthuser",),
                ).fetchall()
            finally:
                conn.close()

            real_conn = sqlite3.connect(DB_PATH)
            try:
                real_count = real_conn.execute(
                    "SELECT COUNT(*) FROM app_users WHERE username = ?",
                    ("healthuser",),
                ).fetchone()[0]
            finally:
                real_conn.close()
        finally:
            database.DB_NAME = original_db_name

    checker.check("app user save creates normalized configured-DB row", created_ok and len(temp_rows) == 1, str((created_msg, temp_rows)))
    checker.check(
        "app user save preserves fields",
        bool(temp_rows)
        and temp_rows[0] == ("healthuser", "healthuser@example.com", "Health User", "hash-one", 0),
        str(temp_rows),
    )
    checker.check(
        "app user save rejects duplicate username",
        duplicate_user_ok is False and "already exists" in duplicate_user_msg,
        duplicate_user_msg,
    )
    checker.check(
        "app user save rejects duplicate email",
        duplicate_email_ok is False and "already in use" in duplicate_email_msg,
        duplicate_email_msg,
    )
    checker.check(
        "remember token lookup returns the configured user",
        bool(remembered_user) and remembered_user["username"] == "healthuser",
        str(remembered_user),
    )
    checker.check(
        "remember token clear removes saved login token",
        cleared_user is None,
        str(cleared_user),
    )
    checker.check("app user save leaves real DB untouched", real_count == 0, str(real_count))


def main() -> None:
    checker = HealthCheck()
    compile_core_modules(checker)
    check_app_shell(checker)
    check_app_py_thin(checker)
    check_database(checker)
    check_database_sql_safety(checker)
    check_renderers_and_ui(checker)
    check_layout_width_styles(checker)
    check_mbe_drill_workflow_controls(checker)
    check_import_parser(checker)
    check_shared_question_save_path(checker)
    check_text_import_apply_path(checker)
    check_answer_display_coverage(checker)
    check_practice_save_path(checker)
    check_outline_rule_save_path(checker)
    check_rule_flashcard_save_path(checker)
    check_plug_play_template_save_path(checker)
    check_admin_upsert_path(checker)
    check_app_user_save_path(checker)
    checker.finish()


if __name__ == "__main__":
    main()
