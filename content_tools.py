# -*- coding: utf-8 -*-

import pandas as pd
import streamlit as st

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
    render_control_row,
    render_tab_set,
    render_compact_note,
    render_import_preview,
    render_import_success,
    render_page_title,
    render_text_area,
)


def render_advanced_tools_page():
    current_page = st.session_state.get("current_page", "Import Questions")
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
        st.caption("Use CSV for small batches or custom tagged questions.")

        action_col, upload_col = render_control_row([0.9, 2.4], gap="medium")
        with action_col:
            st.download_button(
                "Download CSV Template",
                data=csv_template_text(),
                file_name="mee_import_template.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with upload_col:
            uploaded_file = st.file_uploader("Upload completed CSV", type=["csv"], key="csv_import_file")

        render_compact_note("Tip: Press Enter twice between paragraphs for clean spacing when displayed.")

        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file).fillna("")
            missing = missing_csv_required_columns(df.columns)

            render_import_preview(
                csv_import_metrics(df, missing),
                csv_import_preview_rows(df),
                empty_message="The uploaded CSV has no preview rows.",
                height=260,
            )

            if missing:
                st.error(f"Missing required columns: {missing}")
            elif st.button("Import CSV Questions", type="primary", use_container_width=True):
                imported = save_questions_from_dataframe(df)

                render_import_success(
                    "CSV",
                    updated=0,
                    inserted=imported,
                    unit="questions",
                )

    with docx_tab:
        st.caption("Use this for your better formatted MEE_PQ_Bank.docx. A dry run appears before any write.")

        docx_file = st.file_uploader("Upload MEE_PQ_Bank.docx", type=["docx"], key="mee_pq_docx_file")
        overwrite_existing = st.checkbox(
            "Overwrite existing questions/answers with DOCX content",
            value=True,
            key="mee_pq_docx_overwrite",
        )

        if docx_file is not None:
            with st.spinner("Parsing DOCX dry run..."):
                entries, result, _backup_path = run_mee_pq_docx_import(
                    docx_file,
                    apply=False,
                    overwrite=overwrite_existing,
                )

            render_import_preview(
                docx_import_metrics(entries, result),
                docx_import_preview_rows(entries),
                empty_message="No DOCX records were detected.",
            )

            if st.button("Import DOCX to Database", type="primary", use_container_width=True):
                with st.spinner("Importing DOCX and creating a database backup..."):
                    _entries, applied_result, backup_path = run_mee_pq_docx_import(
                        docx_file,
                        apply=True,
                        overwrite=overwrite_existing,
                    )

                applied_stats = applied_result["stats"]
                render_import_success(
                    "DOCX",
                    updated=applied_stats.get("updated", 0),
                    inserted=applied_stats.get("inserted", 0),
                    unit="questions",
                    backup_path=backup_path,
                )

    with pdf_tab:
        st.caption(
            "Upload a PDF that contains structured MEE sections or plain Question / Answer / Rule Outline blocks. "
            "The app extracts the PDF text, previews records, then imports through the shared text pipeline."
        )

        pdf_file = st.file_uploader("Upload structured PDF bank", type=["pdf"], key="pdf_text_import_file")
        pdf_allow_truncated = st.checkbox(
            "Allow records marked as truncated",
            value=False,
            key="pdf_allow_truncated",
        )

        if pdf_file is not None:
            with st.spinner("Extracting PDF text and parsing dry run..."):
                extracted_text, records, report = run_pdf_text_import(
                    pdf_file,
                    apply=False,
                    allow_truncated=pdf_allow_truncated,
                )

            render_import_preview(
                text_import_metrics(records, report, extracted_text=extracted_text),
                text_import_preview_rows(records),
                empty_message=(
                    "No records were detected. Check that the PDF contains headings like "
                    "Question, Answer, and Rule Outline, or the fuller Fact Pattern / Questions Asked / Full Analysis format."
                ),
            )

            with st.expander("Extracted PDF text preview", expanded=False):
                render_text_area(
                    "PDF text",
                    value=extracted_text[:12000],
                    height=320,
                    disabled=True,
                    key="pdf_extracted_preview",
                )

            if records and st.button("Import PDF Text to Database", type="primary", use_container_width=True):
                with st.spinner("Importing extracted PDF text and creating a database backup..."):
                    _text, _records, applied_report = run_pdf_text_import(
                        pdf_file,
                        apply=True,
                        allow_truncated=pdf_allow_truncated,
                    )
                render_import_success(
                    "PDF",
                    updated=applied_report["records_to_update"],
                    inserted=applied_report["records_to_insert"],
                    backup_path=applied_report.get("backup"),
                )

    with text_tab:
        st.caption(
            "Paste or upload a text bank. Accepted formats include simple Question / Answer / Rule Outline blocks "
            "or fuller Fact Pattern / Questions Asked / Rules & Doctrine / Full Analysis sections."
        )

        text_upload = st.file_uploader(
            "Upload Markdown/text bank",
            type=["md", "txt"],
            key="markdown_text_import_file",
        )
        pasted_markdown = render_text_area(
            "Or paste Markdown/text here",
            height=280,
            placeholder="### MEE-2025-FEB-Q01 - February 2025\n\n**Subject:** ...\n\n## Fact Pattern\n...",
            key="markdown_text_import_paste",
        )
        allow_truncated = st.checkbox(
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
            records, report = run_markdown_text_import(
                markdown_text,
                apply=False,
                allow_truncated=allow_truncated,
            )

            render_import_preview(
                text_import_metrics(records, report),
                text_import_preview_rows(records),
                empty_message="No records were detected. Check the text headings and section labels.",
            )

            if records and st.button("Import Text / Markdown to Database", type="primary", use_container_width=True):
                _records, applied_report = run_markdown_text_import(
                    markdown_text,
                    apply=True,
                    allow_truncated=allow_truncated,
                )
                render_import_success(
                    "Text",
                    updated=applied_report["records_to_update"],
                    inserted=applied_report["records_to_insert"],
                    backup_path=applied_report.get("backup"),
                )


def render_manual_entry_tool():
    render_page_title(
        "Manual Entry",
        "Manually add one question with its call, rule bank, and answer notes.",
    )

    st.caption("Manual entry is best for high-value questions that need custom tagging.")

    with st.form("add_question_form"):
        meta_cols = render_control_row([1.05, 0.55, 0.75, 1.1, 0.75, 1.15])

        with meta_cols[0]:
            exam_name = st.text_input("Exam", placeholder="February 2021")
        with meta_cols[1]:
            question_number = st.text_input("Q", placeholder="1")
        with meta_cols[2]:
            exam_year = st.number_input("Year", min_value=1990, max_value=2035, value=2021)
        with meta_cols[3]:
            subject = st.text_input("Subject", placeholder="Civil Procedure")
        with meta_cols[4]:
            priority = st.slider("Priority", 1, 5, DEFAULT_QUESTION_PRIORITY)
        with meta_cols[5]:
            source = st.text_input("Source", placeholder="My outline / PDF")

        more_meta_cols = render_control_row([0.8, 1.1, 1.1, 1.2])
        with more_meta_cols[0]:
            exam_season = st.selectbox("Season", QUESTION_SEASON_OPTIONS)
        with more_meta_cols[1]:
            secondary_subjects = st.text_input("Secondary subjects", placeholder="Evidence, Torts")
        with more_meta_cols[2]:
            july_2026_status = st.selectbox(
                "Status",
                QUESTION_STATUS_OPTIONS,
            )
        with more_meta_cols[3]:
            active_for_july_2026 = st.checkbox("Active for July 2026", value=True)

        prompt_tab, answer_tab, outline_tab = render_tab_set(["Prompt", "Answer", "Rule Outline"])

        with prompt_tab:
            prompt_cols = render_control_row([1.45, 1], gap="medium")
            with prompt_cols[0]:
                question_text = render_text_area(
                    "Question text / prompt",
                    height=360,
                    placeholder="Paste the fact pattern here.",
                    paragraph_tip=True,
                )
            with prompt_cols[1]:
                call_of_question = render_text_area(
                    "Call of the question",
                    height=360,
                    placeholder="Paste each call or subquestion here.",
                )

        with answer_tab:
            model_points = render_text_area(
                "Sample answer / model analysis",
                placeholder="Paste the complete answer or analysis here.",
                height=420,
            )
            st.caption("This is what appears in the Answer Bank after retrieval.")

        with outline_tab:
            issue_col, rule_col = render_control_row([1, 1], gap="medium")
            with issue_col:
                tested_issues = render_text_area(
                    "Tested issues",
                    placeholder="Issue one; issue two; issue three",
                    height=170,
                )
                trigger_facts = render_text_area(
                    "Trigger facts",
                    placeholder="Facts that trigger the issues/rules.",
                    height=170,
                )
            with rule_col:
                rules = render_text_area(
                    "Rules",
                    placeholder="Paste concise rule statements here.",
                    height=170,
                )
                traps = render_text_area(
                    "Traps",
                    placeholder="Common wrong turn; missing element; misleading fact.",
                    height=170,
                )

        submitted = st.form_submit_button("Save Question")

        if submitted:
            save_question_from_mapping({
                "exam_name": exam_name,
                "question_number": question_number,
                "subject": subject,
                "question_text": question_text,
                "call_of_question": call_of_question,
                "tested_issues": tested_issues,
                "rules": rules,
                "trigger_facts": trigger_facts,
                "traps": traps,
                "model_points": model_points,
                "active_for_july_2026": active_for_july_2026,
                "exam_year": exam_year,
                "exam_season": exam_season,
                "secondary_subjects": secondary_subjects,
                "july_2026_status": july_2026_status,
                "priority": priority,
                "source": source,
            })

            st.success("Question saved.")
