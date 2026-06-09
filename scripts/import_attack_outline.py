import _bootstrap  # noqa: F401

import re
import sys
from pathlib import Path

import fitz

from database import init_db, add_outline_rule


SOURCE_FILE = "bar_attack.pdf"

SUBJECTS = [
    "Agency and Partnership",
    "Corporations and LLCs",
    "Civil Procedure",
    "Constitutional Law",
    "Contracts",
    "Criminal Law",
    "Criminal Procedure",
    "Evidence",
    "Real Property",
    "Torts",
    "Family Law",
    "Trusts",
    "Decedents' Estates",
    "Decedents’ Estates",
    "Secured Transactions",
    "Conflict of Laws",
]

RULE_HEADING_RE = re.compile(r"^\s*\d+\s*\.\s+(.+?)\s+((?:<\s*)?\d{1,2}\.\d%)\s*$")
RULE_NUMBER_RE = re.compile(r"^\s*\d+\s*\.\s*$")
RULE_RATE_RE = re.compile(r"^\s*(?:<\s*)?\d{1,2}\.\d%\s*$")
ROMAN_HEADING_RE = re.compile(r"^\s*[IVX]+\.\s+[A-Z][A-Za-z &,'’-]+$")
FOOTER_RE = re.compile(r"^\s*(?:\d+|Page\s+\d+)\s*$", re.IGNORECASE)


def normalize_subject(line):
    stripped = line.strip()

    for subject in SUBJECTS:
        if stripped.lower() == subject.lower():
            return "Decedents' Estates" if subject == "Decedents’ Estates" else subject

    return None


def clean_line(line):
    line = line.replace("\u00a0", " ").strip()
    line = re.sub(r"[ \t]+", " ", line)
    return line


def is_noise_line(line):
    lowered = line.lower()

    if not line:
        return True

    if "legacysource.com" in lowered or "copyright" in lowered or "©" in line:
        return True

    if lowered.startswith("table of contents"):
        return True

    return False


def clean_rule_text(lines):
    cleaned = []

    for line in lines:
        line = clean_line(line)

        if is_noise_line(line):
            continue

        cleaned.append(line)

    text = "\n".join(cleaned)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def find_printed_page(lines):
    for line in reversed(lines[-8:]):
        line = clean_line(line)

        if FOOTER_RE.match(line):
            return line

    return ""


def parse_rule_heading(lines, index):
    line = clean_line(lines[index])
    single_line_match = RULE_HEADING_RE.match(line)

    if single_line_match:
        return {
            "rule_title": single_line_match.group(1).strip(),
            "appearance_rate": single_line_match.group(2).replace(" ", ""),
            "next_index": index + 1,
        }

    if not RULE_NUMBER_RE.match(line):
        return None

    title_index = index + 1

    while title_index < len(lines) and is_noise_line(clean_line(lines[title_index])):
        title_index += 1

    rate_index = title_index + 1

    while rate_index < len(lines) and is_noise_line(clean_line(lines[rate_index])):
        rate_index += 1

    if rate_index >= len(lines):
        return None

    title = clean_line(lines[title_index])
    rate = clean_line(lines[rate_index])

    if not title or not RULE_RATE_RE.match(rate):
        return None

    return {
        "rule_title": title,
        "appearance_rate": rate.replace(" ", ""),
        "next_index": rate_index + 1,
    }


def flush_rule(rule, imported_stats):
    if not rule:
        return

    rule_text = clean_rule_text(rule["lines"])

    if len(rule_text) < 25:
        return

    inserted = add_outline_rule(
        rule["subject"],
        rule["rule_title"],
        rule["appearance_rate"],
        rule_text,
        rule["pdf_page"],
        rule["printed_page"],
        SOURCE_FILE,
    )

    if inserted:
        imported_stats["imported"] += 1
    else:
        imported_stats["skipped"] += 1


def import_attack_outline(pdf_path):
    init_db()
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"Could not find {pdf_path}")

    stats = {"imported": 0, "skipped": 0}
    current_subject = ""
    current_rule = None

    with fitz.open(pdf_path) as doc:
        for page_index, page in enumerate(doc):
            text = page.get_text("text")
            raw_lines = text.splitlines()
            lines = [clean_line(line) for line in raw_lines]
            printed_page = find_printed_page(lines)

            line_index = 0

            while line_index < len(lines):
                line = lines[line_index]

                if is_noise_line(line):
                    line_index += 1
                    continue

                subject = normalize_subject(line)

                if subject:
                    if current_rule:
                        flush_rule(current_rule, stats)
                        current_rule = None

                    current_subject = subject
                    line_index += 1
                    continue

                if not current_subject:
                    line_index += 1
                    continue

                heading_match = parse_rule_heading(lines, line_index)

                if heading_match:
                    if current_rule:
                        flush_rule(current_rule, stats)

                    current_rule = {
                        "subject": current_subject,
                        "rule_title": heading_match["rule_title"],
                        "appearance_rate": heading_match["appearance_rate"],
                        "pdf_page": page_index + 1,
                        "printed_page": printed_page,
                        "lines": [],
                    }
                    line_index = heading_match["next_index"]
                    continue

                if current_rule and ROMAN_HEADING_RE.match(line):
                    flush_rule(current_rule, stats)
                    current_rule = None
                    line_index += 1
                    continue

                if current_rule:
                    current_rule["lines"].append(line)

                line_index += 1

        if current_rule:
            flush_rule(current_rule, stats)

    return stats


def main():
    pdf_arg = sys.argv[1] if len(sys.argv) > 1 else "bar attack.pdf"
    stats = import_attack_outline(pdf_arg)
    print(f"Imported {stats['imported']} rules.")
    print(f"Skipped {stats['skipped']} duplicates.")


if __name__ == "__main__":
    main()
