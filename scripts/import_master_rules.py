"""Import a personal MEE rule book (.docx) into the outline_rules table.

Expected document structure (styles):
  Heading 1   -> Subject            (e.g. "I. Business Associations")
  Heading 2   -> Sub-topic          (e.g. "A. Agency")
  Rule Bullet -> one rule each      (e.g. "Actual authority: ...")
  Tip         -> issue-spotter note

Usage:
    python scripts/import_master_rules.py "MEE_Master_Rules_By_Subject_July_2026.docx"

Re-running is safe: duplicates (same subject + title + source) are skipped.
"""

import _bootstrap  # noqa: F401

import re
import sys
from pathlib import Path

from docx import Document

from database import init_db, add_outline_rule

SOURCE_LABEL = "MEE Master Rules (my outline)"


def clean_heading(text):
    # Strip leading enumerators like "I. ", "VIII. ", "A. ".
    return re.sub(r"^\s*(?:[IVXLC]+|[A-Z])\.\s*", "", text).strip()


def strip_bullet(text):
    # Remove leading bullet glyphs / dashes / whitespace.
    return re.sub(r"^[•●▪\-\*\s]+", "", text).strip()


def split_title(body, subtopic):
    match = re.match(r"(.{3,80}?):\s*(.*)", body, re.S)
    leadin = match.group(1).strip() if match else body[:60].strip()
    return f"{subtopic} - {leadin}" if subtopic else leadin


def main(path):
    path = Path(path)
    if not path.exists():
        print(f"File not found: {path}")
        return

    init_db()
    doc = Document(str(path))

    subject = None
    subtopic = None
    added = 0
    skipped = 0

    for paragraph in doc.paragraphs:
        style = paragraph.style.name
        text = paragraph.text.strip()
        if not text:
            continue

        if style == "Heading 1":
            subject = clean_heading(text)
            subtopic = None
        elif style == "Heading 2":
            subtopic = clean_heading(text)
        elif style == "Rule Bullet":
            if not subject:
                continue
            body = strip_bullet(text)
            if not body:
                continue
            title = split_title(body, subtopic)
            created = add_outline_rule(subject, title, "", body, None, "", SOURCE_LABEL)
            added += 1 if created else 0
            skipped += 0 if created else 1
        elif style == "Tip":
            if not subject:
                continue
            note = re.sub(r"^Issue spotter:\s*", "", text, flags=re.IGNORECASE).strip()
            title = f"{subtopic} - Issue spotter" if subtopic else f"{subject} - Issue spotter"
            created = add_outline_rule(
                subject, title, "", "Issue spotter: " + note, None, "", SOURCE_LABEL
            )
            added += 1 if created else 0
            skipped += 0 if created else 1

    print(f"Imported {added} rule(s); skipped {skipped} duplicate(s).")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "MEE_Master_Rules_By_Subject_July_2026.docx"
    main(target)
