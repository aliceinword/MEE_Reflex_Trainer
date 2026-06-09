import _bootstrap  # noqa: F401

import re
import sys
from pathlib import Path

import fitz

from database import init_db, add_plug_play_template


DEFAULT_SOURCE_FILE = "LBP Plug and Play-Essay Templates to Help You Write Faster Score Higher.pdf"

SUBJECT_MAP = {
    "AGENCY & PARTNERSHIPS": "Business Associations",
    "AGENCY AND PARTNERSHIPS": "Business Associations",
    "CORPS & LLC": "Business Associations",
    "CORPORATIONS & LLC": "Business Associations",
    "CORPORATIONS AND LLC": "Business Associations",
    "CIVIL PROCEDURE": "Civil Procedure",
    "CONFLICTS": "Conflict of Laws",
    "CONFLICT OF LAWS": "Conflict of Laws",
    "CONTRACTS": "Contracts",
    "CRIMINAL LAW & PROCEDURE": "Criminal Law & Procedure",
    "CRIMINAL LAW AND PROCEDURE": "Criminal Law & Procedure",
    "CONSTITUTIONAL LAW": "Constitutional Law",
    "EVIDENCE": "Evidence",
    "REAL PROPERTY": "Real Property",
    "TORTS": "Torts",
    "FAMILY LAW": "Family Law",
    "TRUSTS": "Trusts & Estates",
    "WILLS": "Trusts & Estates",
    "DECEDENTS": "Trusts & Estates",
    "TRUSTS / WILLS / DECEDENTS": "Trusts & Estates",
    "SECURED": "Secured Transactions",
    "SECURED TRANSACTIONS": "Secured Transactions",
}

SECTION_ALIASES = {
    "scenario_trigger": [
        "Scenario Trigger",
        "Scenario Triggers",
    ],
    "issue_statement": [
        "Issue Statement",
        "Issue",
    ],
    "rule_text": [
        "Rule:",
        "Rule",
    ],
    "analysis_template": [
        "Analysis Template",
        "Analysis",
    ],
    "conclusion_template": [
        "Conclusion",
    ],
    "testing_notes": [
        "How This Subject Is Tested on the MEE:",
        "How This Subject Is Tested on the MEE",
        "How This Subject is Tested on the MEE",
        "How",
    ],
}

SECTION_ORDER = [
    "scenario_trigger",
    "issue_statement",
    "rule_text",
    "analysis_template",
    "conclusion_template",
    "testing_notes",
]


def clean_line(line):
    line = str(line or "").replace("\u00a0", " ").strip()
    line = re.sub(r"[ \t]+", " ", line)
    return line


def is_noise_line(line):
    lowered = line.lower()

    if not line:
        return True

    if "copyright" in lowered or "all rights reserved" in lowered:
        return True


    if "plug and play essay templates" in lowered:
        return True

    if re.fullmatch(r"\d+", line):
        return True

    return False


def clean_text(text):
    lines = []

    for raw_line in str(text or "").splitlines():
        line = clean_line(raw_line)

        if is_noise_line(line):
            continue

        lines.append(line)

    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_subject(raw_subject):
    normalized = re.sub(r"\s+", " ", str(raw_subject or "").upper()).strip()
    normalized = normalized.replace(" PLUG & PLAY TEMPLATE", "")
    normalized = normalized.replace(" PLUG AND PLAY TEMPLATE", "")

    for key, value in SUBJECT_MAP.items():
        if key in normalized:
            return value

    return raw_subject.title() if raw_subject else ""


def detect_subject(line):
    normalized = re.sub(r"\s+", " ", line.upper()).strip()

    if "PLUG" not in normalized or "TEMPLATE" not in normalized:
        return None

    for key, value in SUBJECT_MAP.items():
        if key in normalized:
            return value

    subject = re.sub(r"PLUG\s*(?:&|AND)\s*PLAY\s*TEMPLATE", "", normalized).strip()
    return normalize_subject(subject)


def section_from_line(line):
    compact_line = clean_line(line).rstrip(":")
    lowered = compact_line.lower()

    for section_key, labels in SECTION_ALIASES.items():
        for label in labels:
            label_clean = label.rstrip(":").lower()

            if lowered == label_clean:
                return section_key, ""

            if lowered.startswith(label_clean + ":"):
                return section_key, compact_line[len(label.rstrip(":")) + 1:].strip()

    if lowered.startswith("how ") and "tested" in lowered and "mee" in lowered:
        return "testing_notes", ""

    return None, ""


def append_section(module, section_key, text):
    if not section_key or not text:
        return

    existing = module.get(section_key, "")
    module[section_key] = f"{existing}\n{text}".strip() if existing else text.strip()


def flush_module(module, stats, source_file):
    if not module:
        return

    module_title = clean_text(module.get("module_title", ""))

    if not module_title:
        return

    inserted = add_plug_play_template(
        module.get("subject", ""),
        module_title,
        clean_text(module.get("scenario_trigger", "")),
        clean_text(module.get("issue_statement", "")),
        clean_text(module.get("rule_text", "")),
        clean_text(module.get("analysis_template", "")),
        clean_text(module.get("conclusion_template", "")),
        clean_text(module.get("testing_notes", "")),
        module.get("pdf_page"),
        source_file,
    )

    if inserted:
        stats["imported"] += 1
    else:
        stats["skipped"] += 1


def extract_templates(pdf_path):
    init_db()
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"Could not find {pdf_path}")

    stats = {"imported": 0, "skipped": 0}
    current_subject = ""
    current_module = None
    current_section = None
    pending_module_number = False
    source_file = pdf_path.name

    with fitz.open(pdf_path) as doc:
        for page_index, page in enumerate(doc):
            text = page.get_text("text")
            lines = [clean_line(line) for line in text.splitlines()]

            for line in lines:
                if is_noise_line(line):
                    continue

                subject = detect_subject(line)

                if subject:
                    flush_module(current_module, stats, source_file)
                    current_module = None
                    current_section = None
                    pending_module_number = False
                    current_subject = subject
                    continue

                module_match = re.match(r"^ISSUE\s+MODULE\s+\d+\s*:?\s*(.*)$", line, re.IGNORECASE)

                if module_match:
                    flush_module(current_module, stats, source_file)
                    title = module_match.group(1).strip()
                    current_module = {
                        "subject": current_subject,
                        "module_title": title,
                        "scenario_trigger": "",
                        "issue_statement": "",
                        "rule_text": "",
                        "analysis_template": "",
                        "conclusion_template": "",
                        "testing_notes": "",
                        "pdf_page": page_index + 1,
                    }
                    current_section = None
                    pending_module_number = not bool(title)
                    continue

                if pending_module_number and current_module:
                    current_module["module_title"] = line
                    pending_module_number = False
                    continue

                section_key, inline_text = section_from_line(line)

                if section_key:
                    current_section = section_key
                    append_section(current_module, current_section, inline_text)
                    continue

                if current_module and current_section:
                    append_section(current_module, current_section, line)
                elif current_module and not current_module.get("module_title"):
                    current_module["module_title"] = line

        flush_module(current_module, stats, source_file)

    return stats


def main():
    pdf_arg = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SOURCE_FILE
    stats = extract_templates(pdf_arg)
    print(f"Imported {stats['imported']} plug-and-play templates.")
    print(f"Skipped {stats['skipped']} duplicates.")


if __name__ == "__main__":
    main()
