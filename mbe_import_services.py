# -*- coding: utf-8 -*-
"""Service helpers for MBE trap-trainer bulk templates and uploads."""

from pathlib import Path

import pandas as pd


MBE_BULK_TEMPLATE_COLUMNS = [
    "Subject",
    "Subtopic",
    "Scenario",
    "Question",
    "Option A",
    "Option B",
    "Option C",
    "Option D",
    "Correct (A-D)",
    "Trap (A-D)",
    "Why Correct",
    "Why Trap Is Wrong",
    "Plain English",
    "Shortcut",
]

MBE_REQUIRED_QUESTION_COLUMNS = [
    "Subject",
    "Scenario",
    "Question",
    "Option A",
    "Option B",
    "Correct (A-D)",
]


def project_file_path(filename):
    """Return an absolute path to a project-local file."""
    return Path(__file__).resolve().parent / filename


def read_mbe_template_bytes(filename):
    """Read a project-local MBE template file for download buttons."""
    path = project_file_path(filename)
    if not path.exists():
        return None
    return path.read_bytes()


def read_mbe_bulk_upload(uploaded_file):
    """Read an uploaded MBE bulk CSV/XLSX file into a normalized DataFrame."""
    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(0)

    name = Path(uploaded_file.name or "").name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(uploaded_file).fillna("")

    if name.endswith((".xlsx", ".xls")):
        try:
            return pd.read_excel(uploaded_file).fillna("")
        except ImportError as exc:
            raise RuntimeError(
                "Excel upload needs the openpyxl package. Save the template as CSV and upload that instead."
            ) from exc

    raise RuntimeError("Upload a CSV, XLSX, or XLS file.")


def missing_mbe_template_columns(columns):
    """Return required MBE template columns missing from an uploaded table."""
    available = set([] if columns is None else list(columns))
    return [column for column in MBE_BULK_TEMPLATE_COLUMNS if column not in available]


def extra_mbe_template_columns(columns):
    """Return non-template columns present in an uploaded MBE table."""
    available = [] if columns is None else list(columns)
    return [column for column in available if column not in MBE_BULK_TEMPLATE_COLUMNS]


def count_valid_mbe_question_rows(df):
    """Count rows that contain the minimum fields needed for an MBE card."""
    if df is None or missing_mbe_template_columns(df.columns):
        return 0

    required = df[MBE_REQUIRED_QUESTION_COLUMNS].astype(str)
    return int(required.apply(lambda row: all(value.strip() for value in row), axis=1).sum())


def mbe_upload_metrics(df, missing_columns, extra_columns):
    """Return compact preview metrics for an uploaded MBE bulk file."""
    return [
        ("Rows", len(df)),
        ("Valid-looking rows", count_valid_mbe_question_rows(df) if not missing_columns else 0),
        ("Missing columns", len(missing_columns)),
        ("Extra columns", len(extra_columns)),
    ]


def mbe_upload_preview_rows(df, limit=8):
    """Return MBE upload preview rows in template-column order."""
    preview_columns = [column for column in MBE_BULK_TEMPLATE_COLUMNS if column in df.columns]
    if not preview_columns:
        return []
    return df[preview_columns].head(limit)
