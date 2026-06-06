"""Import a personal Plug & Play essay-template book (.docx) into plug_play_templates.

Expected document structure (Word paragraph styles):
    Heading 1   -> Subject               ("AGENCY & PARTNERSHIPS")
    Heading 2   -> Module title          ("ISSUE MODULE 1: AGENCY CONTRACT LIABILITY")
    Heading 3   -> "SCENARIO TRIGGER"
    Normal      -> body, using inline label lines:
                     Issue: ...          -> issue statement
                     Rule                -> rule section
                     Analysis Template   -> analysis section
                     Conclusion          -> conclusion section

Usage:
    python import_plug_play_docx.py "MEE_Plug_and_Play_Essay_Templates.docx"

Re-running is safe: a template with the same subject + title + source is skipped.
"""

import re
import sys
from pathlib import Path

from docx import Document

from database import init_db, add_plug_play_template

SOURCE_LABEL = "MEE Plug & Play Templates (my outline)"

# Align template subjects with the question/rule subjects used elsewhere.
SUBJECT_MAP = {
    "AGENCY & PARTNERSHIPS": "Agency & Partnership",
    "CORPORATIONS & LLCS": "Corporations & LLCs",
    "CIVIL PROCEDURE": "Civil Procedure",
    "CONTRACTS": "Contracts / Sales",
    "CONTRACTS / SALES": "Contracts / Sales",
    "CRIMINAL LAW & PROCEDURE": "Criminal Law & Procedure",
    "CONSTITUTIONAL LAW": "Constitutional Law",
    "EVIDENCE": "Evidence",
    "REAL PROPERTY": "Real Property",
    "TORTS": "Torts",
}


def normalize_subject(heading):
    key = heading.strip().upper()
    return SUBJECT_MAP.get(key, heading.strip().title())


def clean_module_title(heading):
    title = re.sub(r"^\s*ISSUE\s+MODULE\s+\d+\s*:\s*", "", heading.strip(), flags=re.IGNORECASE)
    return title.title() if title.isupper() else title


def is_label(text, label):
    return text.strip().lower().rstrip(":") == label


def main(path):
    path = Path(path)
    if not path.exists():
        print(f"File not found: {path}")
        return

    init_db()
    doc = Document(str(path))

    subject = None
    module = None        # dict being built
    section = None       # scenario | rule | analysis | conclusion
    added = skipped = 0

    def flush():
        nonlocal added, skipped, module
        if not (subject and module and module.get("title")):
            module = None
            return
        created = add_plug_play_template(
            module["subject"],
            module["title"],
            "\n".join(module["scenario"]).strip(),
            module["issue"].strip(),
            "\n".join(module["rule"]).strip(),
            "\n".join(module["analysis"]).strip(),
            "\n".join(module["conclusion"]).strip(),
            "",          # testing_notes
            None,        # pdf_page
            SOURCE_LABEL,
        )
        added += 1 if created else 0
        skipped += 0 if created else 1
        module = None

    def new_module(title):
        return {
            "subject": subject,
            "title": clean_module_title(title),
            "scenario": [],
            "issue": "",
            "rule": [],
            "analysis": [],
            "conclusion": [],
        }

    for paragraph in doc.paragraphs:
        style = paragraph.style.name
        text = paragraph.text.strip()
        if not text:
            continue

        if style == "Heading 1":
            flush()
            subject = normalize_subject(text)
            section = None
        elif style == "Heading 2":
            flush()
            module = new_module(text)
            section = None
        elif style == "Heading 3":
            if module is not None and "scenario trigger" in text.lower():
                section = "scenario"
        elif module is not None:
            if text.lower().startswith("issue:"):
                module["issue"] = re.sub(r"^issue:\s*", "", text, flags=re.IGNORECASE).strip()
                section = None
            elif is_label(text, "rule"):
                section = "rule"
            elif is_label(text, "analysis template"):
                section = "analysis"
            elif is_label(text, "conclusion"):
                section = "conclusion"
            elif section in ("scenario", "rule", "analysis", "conclusion"):
                module[section].append(text)

    flush()
    print(f"Imported {added} template(s); skipped {skipped} already present.")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "MEE_Plug_and_Play_Essay_Templates.docx"
    main(target)
