# -*- coding: utf-8 -*-
"""Import service helpers used by the Streamlit pages."""

import csv
import tempfile
from io import StringIO
from pathlib import Path

import database
from database import add_question
from question_utils import parse_bool, parse_optional_int
from text_cleanup import normalize_extracted_text


QUESTION_SEASON_OPTIONS = ["February", "July", "Other"]
QUESTION_STATUS_OPTIONS = [
    "Active standalone MEE",
    "Retired standalone - background only",
    "MPT background only",
    "Historical / low priority",
]
DEFAULT_QUESTION_STATUS = QUESTION_STATUS_OPTIONS[0]
DEFAULT_QUESTION_PRIORITY = 3

CSV_TEMPLATE_RECORD = {
    "exam_name": "February 2021",
    "exam_year": 2021,
    "exam_season": QUESTION_SEASON_OPTIONS[0],
    "question_number": "1",
    "subject": "Civil Procedure",
    "secondary_subjects": "",
    "question_text": "[Paste private question text here]",
    "call_of_question": "What legal result should the court reach? Explain.",
    "tested_issues": "Issue one; issue two; issue three",
    "rules": "Rule one. Rule two. Rule three.",
    "trigger_facts": "Fact that triggers issue one; fact that triggers issue two; fact that creates a trap",
    "traps": "Common wrong turn; missing element; misleading fact",
    "model_points": "What a passing answer must discuss.",
    "active_for_july_2026": 1,
    "july_2026_status": DEFAULT_QUESTION_STATUS,
    "priority": 5,
    "source": "My source",
}

CSV_REQUIRED_COLUMNS = [
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
]


def missing_csv_required_columns(columns):
    """Return required CSV columns that are absent from an uploaded table."""
    available = set([] if columns is None else list(columns))
    return [column for column in CSV_REQUIRED_COLUMNS if column not in available]


def csv_import_metrics(df, missing_columns):
    """Return compact metrics for an uploaded CSV preview."""
    return [
        ("Rows", len(df)),
        ("Columns", len(df.columns)),
        ("Missing required", len(missing_columns)),
    ]


def csv_import_preview_rows(df, limit=20):
    """Return CSV preview rows using the shared preview row limit."""
    return df.head(limit)


def csv_template_text():
    """Return a one-row CSV template matching the shared question field contract."""
    buffer = StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=list(CSV_TEMPLATE_RECORD.keys()),
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerow(CSV_TEMPLATE_RECORD)
    return buffer.getvalue()


def save_question_from_mapping(values):
    """Save one question from CSV/manual-entry style field names."""
    values = dict(values or {})
    add_question(
        exam_name=values.get("exam_name", ""),
        question_number=str(values.get("question_number", "")),
        subject=values.get("subject", ""),
        question_text=values.get("question_text", ""),
        call_of_question=values.get("call_of_question", ""),
        tested_issues=values.get("tested_issues", ""),
        rules=values.get("rules", ""),
        trigger_facts=values.get("trigger_facts", ""),
        traps=values.get("traps", ""),
        model_points=values.get("model_points", ""),
        active_for_july_2026=parse_bool(values.get("active_for_july_2026", 1)),
        exam_year=parse_optional_int(values.get("exam_year", ""), default=None),
        exam_season=values.get("exam_season", ""),
        secondary_subjects=values.get("secondary_subjects", ""),
        july_2026_status=values.get("july_2026_status", DEFAULT_QUESTION_STATUS),
        priority=parse_optional_int(values.get("priority", DEFAULT_QUESTION_PRIORITY), default=DEFAULT_QUESTION_PRIORITY),
        source=values.get("source", ""),
    )


def save_questions_from_dataframe(df):
    """Save all rows from a CSV-style DataFrame and return the insert count."""
    imported = 0
    for _, row in df.iterrows():
        save_question_from_mapping(row.to_dict())
        imported += 1
    return imported


def _extract_pdf_text(pdf_path):
    import fitz

    pages = []
    with fitz.open(pdf_path) as doc:
        for page in doc:
            words = page.get_text("words", sort=True)
            if not words:
                pages.append(page.get_text("text") or "")
                continue

            lines = []
            current_key = None
            current_words = []
            for word in words:
                _x0, _y0, _x1, _y1, value, block_no, line_no, _word_no = word[:8]
                key = (block_no, line_no)
                if current_key is None:
                    current_key = key
                if key != current_key:
                    lines.append(" ".join(current_words))
                    current_words = []
                    current_key = key
                current_words.append(str(value))
            if current_words:
                lines.append(" ".join(current_words))

            pages.append("\n".join(lines))

    return normalize_extracted_text("\n\n".join(pages))


def extract_pdf_text_from_upload(uploaded_file):
    """Extract readable text from an uploaded PDF using word-level PyMuPDF output."""
    suffix = Path(uploaded_file.name or "upload.pdf").suffix or ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = Path(tmp.name)

    try:
        return _extract_pdf_text(tmp_path)
    finally:
        try:
            tmp_path.unlink()
        except OSError:
            pass


def run_mee_pq_docx_import(uploaded_file, apply=False, overwrite=False):
    """Parse/import a user-owned MEE_PQ_Bank.docx upload through the shared importer."""
    from import_mee_pq_bank_docx import (
        backup_db as backup_mee_pq_db,
        parse_docx as parse_mee_pq_docx,
        upsert_database as upsert_mee_pq_database,
    )

    suffix = Path(uploaded_file.name or "upload.docx").suffix or ".docx"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = Path(tmp.name)

    try:
        entries = parse_mee_pq_docx(tmp_path)
        backup_path = backup_mee_pq_db(Path(database.DB_NAME)) if apply else None
        result = upsert_mee_pq_database(entries, apply=apply, overwrite=overwrite)
    finally:
        try:
            tmp_path.unlink()
        except OSError:
            pass

    return entries, result, backup_path


def docx_import_metrics(entries, result):
    """Return compact metric labels for a DOCX import preview/apply result."""
    stats = result.get("stats", {}) if isinstance(result, dict) else {}
    usable_answers = sum(1 for entry in entries if len(getattr(entry, "model_points", "") or "") >= 500)
    return [
        ("Parsed", len(entries)),
        ("Usable answers", usable_answers),
        ("Would update", stats.get("would_update", stats.get("updated", 0))),
        ("Would insert", stats.get("would_insert", stats.get("inserted", 0))),
        ("Skipped", stats.get("skipped_existing", 0) + stats.get("skipped_short_insert", 0)),
    ]


def docx_import_preview_rows(entries, limit=40):
    """Return table rows for a DOCX import preview without Streamlit dependencies."""
    return [
        {
            "Exam": entry.exam_name,
            "Q": entry.question_number,
            "Subject": entry.subject,
            "Question chars": len(entry.question_text or ""),
            "Answer chars": len(entry.model_points or ""),
        }
        for entry in entries[:limit]
    ]


def run_markdown_text_import(markdown_text, apply=False, allow_truncated=False):
    """Parse/import a pasted Markdown/text MEE bank through the shared importer."""
    from import_markdown_mee_qa_bank import (
        import_records as import_markdown_records,
        parse_records as parse_markdown_records,
    )

    records = parse_markdown_records(markdown_text or "")
    report = import_markdown_records(records, apply=apply, allow_truncated=allow_truncated)
    return records, report


def text_import_metrics(records, report, extracted_text=None):
    """Return compact metric labels for text/PDF import previews."""
    metrics = []
    if extracted_text is not None:
        metrics.append(("Extracted chars", len(extracted_text)))

    metrics.extend([
        ("Parsed", report["records_parsed"]),
        ("Would update", report["records_to_update"]),
        ("Would insert", report["records_to_insert"]),
        ("Skipped truncated", report["records_skipped_truncated"]),
    ])

    if extracted_text is None:
        metrics.append(("Subjects", len({record.subject for record in records if record.subject})))

    return metrics


def text_import_preview_rows(records, limit=40):
    """Return table rows for text/PDF import previews without Streamlit dependencies."""
    return [
        {
            "Source ID": record.source_id,
            "Exam": record.exam_name,
            "Q": record.question_number,
            "Subject": record.subject,
            "Answer chars": len(record.model_points or ""),
            "Truncated": record.is_truncated,
        }
        for record in records[:limit]
    ]


def run_pdf_text_import(uploaded_file, apply=False, allow_truncated=False):
    """Extract a structured PDF to text, then import through the text-bank importer."""
    extracted_text = extract_pdf_text_from_upload(uploaded_file)
    records, report = run_markdown_text_import(
        extracted_text,
        apply=apply,
        allow_truncated=allow_truncated,
    )
    return extracted_text, records, report
