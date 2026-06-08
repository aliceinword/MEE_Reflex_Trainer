# -*- coding: utf-8 -*-
"""MBE page renderer for the separate multiple-choice trainer."""

import os

from mbe_import_services import (
    MBE_BULK_TEMPLATE_COLUMNS,
    extra_mbe_template_columns,
    mbe_upload_metrics,
    mbe_upload_preview_rows,
    missing_mbe_template_columns,
    read_mbe_bulk_upload,
    read_mbe_template_bytes,
)

from ui_components import (
    FULL_PAGE_EMBED_HEIGHT,
    render_caption,
    render_compact_note,
    render_control_row,
    render_download_button,
    render_error,
    render_file_uploader,
    render_html_body,
    render_html_file_embed,
    render_import_preview,
    render_info,
    render_metric_row,
    render_section_heading,
    render_success,
    render_tab_set,
    render_warning,
)


def _render_mbe_bulk_upload_tab():
    render_section_heading("MBE Drills Question Bulk Upload")
    render_compact_note(
        "Use these templates for MBE trap-trainer questions. Fill one question per row, then upload it here to check the format."
    )

    csv_bytes = read_mbe_template_bytes("MBE_trap_trainer_template.csv")
    xlsx_bytes = read_mbe_template_bytes("MBE_trap_trainer_template_1.xlsx")

    template_col, upload_col = render_control_row([0.9, 1.35], gap="large")

    with template_col:
        render_section_heading("Templates", level=4)
        if csv_bytes:
            render_download_button(
                "Download CSV Template",
                data=csv_bytes,
                file_name="MBE_trap_trainer_template.csv",
                mime="text/csv",
                key="mbe_bulk_csv_template",
            )
        else:
            render_warning("CSV template file is missing from the project folder.")

        if xlsx_bytes:
            render_download_button(
                "Download Excel Template",
                data=xlsx_bytes,
                file_name="MBE_trap_trainer_template.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="mbe_bulk_xlsx_template",
            )
        else:
            render_warning("Excel template file is missing from the project folder.")

        render_caption("Required columns:")
        render_info(", ".join(MBE_BULK_TEMPLATE_COLUMNS))

    with upload_col:
        render_section_heading("Upload Check", level=4)
        uploaded_file = render_file_uploader(
            "Upload completed MBE bulk file",
            type=["csv", "xlsx", "xls"],
            key="mbe_bulk_question_upload",
            caption="CSV works offline. Excel files may need openpyxl installed.",
        )

        if uploaded_file is None:
            render_info("Upload a completed template to preview rows and catch missing columns before importing.")
            return

        try:
            df = read_mbe_bulk_upload(uploaded_file)
        except Exception as exc:
            render_error(str(exc))
            return

        missing = missing_mbe_template_columns(df.columns)
        extra = extra_mbe_template_columns(df.columns)
        render_metric_row(mbe_upload_metrics(df, missing, extra))

        if missing:
            render_error("Missing required columns: " + ", ".join(missing))
        else:
            render_success("Column check passed. This file matches the MBE bulk template.")

        if extra:
            render_warning("Extra columns will be ignored by the trainer: " + ", ".join(extra))

        render_import_preview(
            [],
            mbe_upload_preview_rows(df),
            empty_message="No previewable rows found.",
        )

        render_compact_note(
            "To add these cards to the browser-based MBE trainer, open the MBE Drills tab, use Bulk CSV/Excel, and select this same file."
        )


def render_mbe_drills_page():
    render_html_body("""
    <style>
    .block-container {
        padding: 0 !important;
        margin: 0 !important;
        height: 100vh !important;
        overflow: auto !important;
    }

    header[data-testid="stHeader"],
    div[data-testid="stToolbar"],
    div[data-testid="stDecoration"] {
        display: none !important;
        height: 0 !important;
        min-height: 0 !important;
    }

    .full-page-embed {
        width: 100% !important;
        height: 0 !important;
        min-height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow: hidden !important;
    }

    div[data-testid="stElementContainer"]:has(iframe),
    div[data-testid="stIFrame"],
    .stIFrame,
    .full-page-embed iframe,
    iframe[title*="streamlit"],
    iframe[title*="component"],
    iframe[srcdoc] {
        height: calc(100vh - 3.75rem) !important;
        min-height: calc(100vh - 3.75rem) !important;
        max-height: calc(100vh - 3.75rem) !important;
    }

    iframe[title*="streamlit"],
    iframe[title*="component"],
    iframe[srcdoc],
    div[data-testid="stIFrame"] iframe,
    .stIFrame iframe {
        width: 100% !important;
        border: 0 !important;
        display: block !important;
    }

    div[data-testid="stElementContainer"],
    .element-container {
        margin: 0 !important;
        padding: 0 !important;
    }

    .main,
    section.main,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"] {
        overflow: auto !important;
    }
    </style>
    """)
    drill_tab, bulk_tab = render_tab_set(["MBE Drills", "MBE Drills Question Bulk Upload"])

    with drill_tab:
        mbe_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mbe_trap_trainer.html")
        render_html_file_embed(
            mbe_path,
            height=FULL_PAGE_EMBED_HEIGHT,
            missing_message=(
                "mbe_trap_trainer.html was not found next to app.py. "
                "Make sure the file is in the project folder."
            ),
        )

    with bulk_tab:
        _render_mbe_bulk_upload_tab()
