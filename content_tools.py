# -*- coding: utf-8 -*-

import pandas as pd

from app_state import get_current_page
from import_services import (
    DEFAULT_QUESTION_PRIORITY,
    QUESTION_SEASON_OPTIONS,
    QUESTION_STATUS_OPTIONS,
    csv_import_metrics,
    csv_import_preview_rows,
    csv_template_text,
    docx_import_metrics,
    docx_import_preview_rows,
    missing_csv_required_columns,
    run_markdown_text_import,
    run_mee_pq_docx_import,
    run_pdf_text_import,
    save_questions_from_dataframe,
    save_question_from_mapping,
    text_import_metrics,
    text_import_preview_rows,
)
from ui_components import (
    TEXTAREA_HEIGHT_LG,
    TEXTAREA_HEIGHT_OUTLINE,
    TEXTAREA_HEIGHT_PREVIEW,
    TEXTAREA_HEIGHT_XL,
    TEXTAREA_HEIGHT_XXL,
    render_checkbox,
    render_caption,
    render_control_row,
    render_download_button,
    render_error,
    render_expander,
    render_file_uploader,
    render_compact_note,
    render_form,
    render_import_apply_action,
    render_import_dry_run_preview,
    render_import_preview,
    render_form_submit_button,
    render_number_input,
    render_page_title,
    render_selectbox,
    render_slider,
    render_success,
    render_tab_set,
    render_text_area,
    render_text_input,
)


def render_advanced_tools_page():
    current_page = get_current_page("Import Questions")
    if current_page in {"Manual Entry", "Add MEE Question"}:
        render_manual_entry_tool()
        return

    render_import_questions_tool()


def render_import_questions_tool():
    render_page_title(
        "Import Questions",
        "Import CSV batches or a user-owned MEE_PQ_Bank.docx file.",
    )

    csv_tab, docx_tab, pdf_tab, text_tab = render_tab_set([
        "CSV Import",
        "DOCX Import",
        "PDF Import",
        "Text / Markdown Import",
    ])

    with csv_tab:
        render_caption("Use CSV for small batches or custom tagged questions.")

        action_col, upload_col = render_control_row([0.9, 2.4], gap="medium")
        with action_col:
            render_download_button(
                "Download CSV Template",
                data=csv_template_text(),
                file_name="mee_import_template.csv",
                mime="text/csv",
            )
        with upload_col:
            uploaded_file = render_file_uploader("Upload completed CSV", type=["csv"], key="csv_import_file")

        render_compact_note("Tip: Press Enter twice between paragraphs for clean spacing when displayed.")

        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file).fillna("")
            missing = missing_csv_required_columns(df.columns)

            render_import_preview(
                csv_import_metrics(df, missing),
                csv_import_preview_rows(df),
                empty_message="The uploaded CSV has no preview rows.",
            )

            if missing:
                render_error(f"Missing required columns: {missing}")
            else:
                render_import_apply_action(
                    "Import CSV Questions",
                    action=lambda: save_questions_from_dataframe(df),
                    success_label="CSV",
                    spinner_text="Importing CSV questions...",
                    stats_from_result=lambda imported: {
                        "updated": 0,
                        "inserted": imported,
                    },
                )

    with docx_tab:
        render_caption("Use this for your better formatted MEE_PQ_Bank.docx. A dry run appears before any write.")

        docx_file = render_file_uploader("Upload MEE_PQ_Bank.docx", type=["docx"], key="mee_pq_docx_file")
        overwrite_existing = render_checkbox(
            "Overwrite existing questions/answers with DOCX content",
            value=True,
            key="mee_pq_docx_overwrite",
        )

        if docx_file is not None:
            entries, result, _backup_path = render_import_dry_run_preview(
                action=lambda: run_mee_pq_docx_import(
                    docx_file,
                    apply=False,
                    overwrite=overwrite_existing,
                ),
                metrics_from_result=lambda dry_run: docx_import_metrics(dry_run[0], dry_run[1]),
                rows_from_result=lambda dry_run: docx_import_preview_rows(dry_run[0]),
                empty_message="No DOCX records were detected.",
                spinner_text="Parsing DOCX dry run...",
            )

            render_import_apply_action(
                "Import DOCX to Database",
                action=lambda: run_mee_pq_docx_import(
                    docx_file,
                    apply=True,
                    overwrite=overwrite_existing,
                ),
                success_label="DOCX",
                spinner_text="Importing DOCX and creating a database backup...",
                stats_from_result=lambda result: {
                    "updated": result[1]["stats"].get("updated", 0),
                    "inserted": result[1]["stats"].get("inserted", 0),
                    "backup_path": result[2],
                },
            )

    with pdf_tab:
        render_caption(
            "Upload a PDF that contains structured MEE sections or plain Question / Answer / Rule Outline blocks. "
            "The app extracts the PDF text, previews records, then imports through the shared text pipeline."
        )

        pdf_file = render_file_uploader("Upload structured PDF bank", type=["pdf"], key="pdf_text_import_file")
        pdf_allow_truncated = render_checkbox(
            "Allow records marked as truncated",
            value=False,
            key="pdf_allow_truncated",
        )

        if pdf_file is not None:
            extracted_text, records, report = render_import_dry_run_preview(
                action=lambda: run_pdf_text_import(
                    pdf_file,
                    apply=False,
                    allow_truncated=pdf_allow_truncated,
                ),
                metrics_from_result=lambda dry_run: text_import_metrics(
                    dry_run[1],
                    dry_run[2],
                    extracted_text=dry_run[0],
                ),
                rows_from_result=lambda dry_run: text_import_preview_rows(dry_run[1]),
                empty_message=(
                    "No records were detected. Check that the PDF contains headings like "
                    "Question, Answer, and Rule Outline, or the fuller Fact Pattern / Questions Asked / Full Analysis format."
                ),
                spinner_text="Extracting PDF text and parsing dry run...",
            )

            with render_expander("Extracted PDF text preview", expanded=False):
                render_text_area(
                    "PDF text",
                    value=extracted_text[:12000],
                    height=TEXTAREA_HEIGHT_PREVIEW,
                    disabled=True,
                    key="pdf_extracted_preview",
                )

            if records:
                render_import_apply_action(
                    "Import PDF Text to Database",
                    action=lambda: run_pdf_text_import(
                        pdf_file,
                        apply=True,
                        allow_truncated=pdf_allow_truncated,
                    ),
                    success_label="PDF",
                    spinner_text="Importing extracted PDF text and creating a database backup...",
                    stats_from_result=lambda result: {
                        "updated": result[2]["records_to_update"],
                        "inserted": result[2]["records_to_insert"],
                        "backup_path": result[2].get("backup"),
                    },
                )

    with text_tab:
        render_caption(
            "Paste or upload a text bank. Accepted formats include simple Question / Answer / Rule Outline blocks "
            "or fuller Fact Pattern / Questions Asked / Rules & Doctrine / Full Analysis sections."
        )

        text_upload = render_file_uploader(
            "Upload Markdown/text bank",
            type=["md", "txt"],
            key="markdown_text_import_file",
        )
        pasted_markdown = render_text_area(
            "Or paste Markdown/text here",
            height=TEXTAREA_HEIGHT_LG,
            placeholder="### MEE-2025-FEB-Q01 - February 2025\n\n**Subject:** ...\n\n## Fact Pattern\n...",
            key="markdown_text_import_paste",
        )
        allow_truncated = render_checkbox(
            "Allow records marked as truncated",
            value=False,
            key="markdown_allow_truncated",
        )

        markdown_text = ""
        if text_upload is not None:
            markdown_text = text_upload.getvalue().decode("utf-8", errors="replace")
        elif pasted_markdown.strip():
            markdown_text = pasted_markdown

        if markdown_text:
            records, report = render_import_dry_run_preview(
                action=lambda: run_markdown_text_import(
                    markdown_text,
                    apply=False,
                    allow_truncated=allow_truncated,
                ),
                metrics_from_result=lambda dry_run: text_import_metrics(dry_run[0], dry_run[1]),
                rows_from_result=lambda dry_run: text_import_preview_rows(dry_run[0]),
                empty_message="No records were detected. Check the text headings and section labels.",
            )

            if records:
                render_import_apply_action(
                    "Import Text / Markdown to Database",
                    action=lambda: run_markdown_text_import(
                        markdown_text,
                        apply=True,
                        allow_truncated=allow_truncated,
                    ),
                    success_label="Text",
                    spinner_text="Importing text and creating a database backup...",
                    stats_from_result=lambda result: {
                        "updated": result[1]["records_to_update"],
                        "inserted": result[1]["records_to_insert"],
                        "backup_path": result[1].get("backup"),
                    },
                )


def render_manual_entry_metadata_fields():
    """Render manual-entry metadata controls and return save-ready values."""
    meta_cols = render_control_row([1.05, 0.55, 0.75, 1.1, 0.75, 1.15])

    with meta_cols[0]:
        exam_name = render_text_input("Exam", placeholder="February 2021")
    with meta_cols[1]:
        question_number = render_text_input("Q", placeholder="1")
    with meta_cols[2]:
        exam_year = render_number_input("Year", min_value=1990, max_value=2035, value=2021)
    with meta_cols[3]:
        subject = render_text_input("Subject", placeholder="Civil Procedure")
    with meta_cols[4]:
        priority = render_slider("Priority", 1, 5, DEFAULT_QUESTION_PRIORITY)
    with meta_cols[5]:
        source = render_text_input("Source", placeholder="My outline / PDF")

    more_meta_cols = render_control_row([0.8, 1.1, 1.1, 1.2])
    with more_meta_cols[0]:
        exam_season = render_selectbox("Season", QUESTION_SEASON_OPTIONS)
    with more_meta_cols[1]:
        secondary_subjects = render_text_input("Secondary subjects", placeholder="Evidence, Torts")
    with more_meta_cols[2]:
        july_2026_status = render_selectbox("Status", QUESTION_STATUS_OPTIONS)
    with more_meta_cols[3]:
        active_for_july_2026 = render_checkbox("Active for July 2026", value=True)

    return {
        "exam_name": exam_name,
        "question_number": question_number,
        "subject": subject,
        "active_for_july_2026": active_for_july_2026,
        "exam_year": exam_year,
        "exam_season": exam_season,
        "secondary_subjects": secondary_subjects,
        "july_2026_status": july_2026_status,
        "priority": priority,
        "source": source,
    }


def render_manual_entry_content_fields():
    """Render manual-entry prompt/answer/outline tabs and return save-ready values."""
    prompt_tab, answer_tab, outline_tab = render_tab_set(["Prompt", "Answer", "Rule Outline"])

    with prompt_tab:
        prompt_cols = render_control_row([1.45, 1], gap="medium")
        with prompt_cols[0]:
            question_text = render_text_area(
                "Question text / prompt",
                height=TEXTAREA_HEIGHT_XL,
                placeholder="Paste the fact pattern here.",
                paragraph_tip=True,
            )
        with prompt_cols[1]:
            call_of_question = render_text_area(
                "Call of the question",
                height=TEXTAREA_HEIGHT_XL,
                placeholder="Paste each call or subquestion here.",
            )

    with answer_tab:
        model_points = render_text_area(
            "Sample answer / model analysis",
            placeholder="Paste the complete answer or analysis here.",
            height=TEXTAREA_HEIGHT_XXL,
        )
        render_caption("This is what appears in the Answer Bank after retrieval.")

    with outline_tab:
        issue_col, rule_col = render_control_row([1, 1], gap="medium")
        with issue_col:
            tested_issues = render_text_area(
                "Tested issues",
                placeholder="Issue one; issue two; issue three",
                height=TEXTAREA_HEIGHT_OUTLINE,
            )
            trigger_facts = render_text_area(
                "Trigger facts",
                placeholder="Facts that trigger the issues/rules.",
                height=TEXTAREA_HEIGHT_OUTLINE,
            )
        with rule_col:
            rules = render_text_area(
                "Rules",
                placeholder="Paste concise rule statements here.",
                height=TEXTAREA_HEIGHT_OUTLINE,
            )
            traps = render_text_area(
                "Traps",
                placeholder="Common wrong turn; missing element; misleading fact.",
                height=TEXTAREA_HEIGHT_OUTLINE,
            )

    return {
        "question_text": question_text,
        "call_of_question": call_of_question,
        "tested_issues": tested_issues,
        "rules": rules,
        "trigger_facts": trigger_facts,
        "traps": traps,
        "model_points": model_points,
    }


def render_manual_entry_tool():
    render_page_title(
        "Manual Entry",
        "Manually add one question with its call, rule bank, and answer notes.",
    )

    render_caption("Manual entry is best for high-value questions that need custom tagging.")

    with render_form("add_question_form"):
        values = {}
        values.update(render_manual_entry_metadata_fields())
        values.update(render_manual_entry_content_fields())

        if render_form_submit_button("Save Question"):
            save_question_from_mapping(values)
            render_success("Question saved.")
