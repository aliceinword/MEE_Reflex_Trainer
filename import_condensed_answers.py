# -*- coding: utf-8 -*-

import argparse
import re
import shutil
import sqlite3
from collections import Counter
from datetime import datetime
from pathlib import Path

import fitz

from database import DB_NAME, init_db
from text_cleanup import normalize_extracted_text


ENTRY_HEADER_RE = re.compile(
    r"(?m)^(February|July)\s+(\d{4})\s+[\u2014\u2013-]\s+Question\s+(\d+)\s*$"
)


def clean_text(text):
    text = normalize_extracted_text(text or "")
    text = text.replace("\uf0b7", "\n- ")
    text = text.replace("ï‚·", "\n- ")
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def compact_lines(text):
    lines = []
    for line in clean_text(text).splitlines():
        line = line.strip()
        if not line:
            continue
        if re.fullmatch(r"[-\u2014\u2013_ ]{5,}", line):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


SUBJECT_TAILS = [
    "Agency & Partnership",
    "Agency and Partnership",
    "Corporations & LLCs",
    "Civil Procedure",
    "Constitutional Law",
    "Contracts / Sales",
    "Contracts",
    "Criminal Law & Procedure",
    "Evidence",
    "Real Property",
    "Torts",
]


POINT_WORDS = {
    "1": "One",
    "2": "Two",
    "3": "Three",
    "4": "Four",
    "5": "Five",
    "6": "Six",
    "7": "Seven",
    "8": "Eight",
    "9": "Nine",
    "10": "Ten",
}


def read_pdf_text(pdf_path):
    doc = fitz.open(pdf_path)
    return "\n".join(page.get_text("text") for page in doc)


def extract_between(text, start_label, end_labels):
    start = re.search(re.escape(start_label), text, flags=re.IGNORECASE)
    if not start:
        return ""

    start_index = start.end()
    end_index = len(text)
    for label in end_labels:
        found = re.search(re.escape(label), text[start_index:], flags=re.IGNORECASE)
        if found:
            end_index = min(end_index, start_index + found.start())

    return compact_lines(text[start_index:end_index])


def normalize_exam(month, year):
    return f"{month} {year}"


def normalize_answer_text(text):
    text = clean_text(text)
    text = text.replace("Full Model Answer / Analysis", "")
    text = re.sub(r"(?i)Condensed sample-answer path:\s*", "", text)
    text = re.sub(r"(?i)\bcontentbased\b", "content-based", text)
    text = re.sub(r"(?i)\bcontentneutral\b", "content-neutral", text)
    text = re.sub(r"(?i)\bover-\s+inclusive\b", "over-inclusive", text)
    text = re.sub(r"(?i)\be\.\s*g\.\s*,", "e.g.,", text)
    text = re.sub(r"(?i)\bFact-based\s+analysis\s*:", "Fact-based analysis:", text)
    text = re.sub(r"(?i)\bRule\s*\(\s*s\s*\)\s*:", "Rules:", text)
    text = re.sub(r"(?i)\bShort\s+answer\s*:", "Short answer:", text)
    text = re.sub(r"(?i)\bConclusion\s*:", "Conclusion:", text)
    text = re.sub(r"(?i)\bShort answer:\s*Summary\s+", "Short answer: ", text)

    # Repair words split by a PDF line break after a hyphen.
    text = re.sub(r"([A-Za-z])-\n([A-Za-z])", r"\1-\2", text)

    # Normalize point headings.
    text = re.sub(
        r"(?im)^\s*(\d+)\.\s+Point\s+(One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten)"
        r"(\([a-z]\))?\s*(?:\([^)]*\))?\s*",
        lambda m: f"Point {m.group(2)}{m.group(3) or ''}: ",
        text,
    )
    text = re.sub(
        r"(?im)^\s*(\d+)\.\s+Point\s+(\d+)(\([a-z]\))?\s*(?:\([^)]*\))?\s*",
        lambda m: f"Point {POINT_WORDS.get(m.group(2), m.group(2))}{m.group(3) or ''}: ",
        text,
    )
    text = re.sub(
        r"(?im)^\s*(\d+)\.\s+Condensed\s+Analysis\s*",
        lambda m: f"Point {POINT_WORDS.get(m.group(1), m.group(1))}: Condensed Analysis\n",
        text,
    )
    text = re.sub(
        r"(?i)\bPoint\s+(One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten)"
        r"(\([a-z]\))?\s*(?:\([^)]*\))?\s+(?!:)",
        lambda m: f"\n\nPoint {m.group(1)}{m.group(2) or ''}: ",
        text,
    )
    text = re.sub(
        r"(?i)^Condensed\s+Analysis\s+",
        "Point One: Condensed Analysis\n",
        text,
    )

    # Put section labels and point headings on their own paragraph boundary.
    text = re.sub(
        r"(?i)\s+(Short answer:|Rules:|Fact-based analysis:|Conclusion:)",
        r"\n\1",
        text,
    )
    text = re.sub(r"(?i)\s+(Point\s+(?:One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten)(?:\([a-z]\))?:)", r"\n\n\1", text)

    # Drop subject-name bleed at the end.
    for subject in SUBJECT_TAILS:
        text = re.sub(rf"\s+{re.escape(subject)}\s*$", "", text, flags=re.IGNORECASE)

    return text.strip()


def is_section_line(line):
    return bool(
        re.match(r"^Point\s+(One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten)(\([a-z]\))?:", line, re.I)
        or re.match(r"^(Short answer:|Rules:|Fact-based analysis:|Conclusion:)$", line, re.I)
        or re.match(r"^(Short answer:|Rules:|Fact-based analysis:|Conclusion:)\s+", line, re.I)
    )


def format_answer_path(answer_path):
    text = normalize_answer_text(answer_path)

    output = []
    pending_bullet = False
    current_section = None

    for raw_line in text.splitlines():
        line = re.sub(r"[ \t]+", " ", raw_line).strip()
        if not line:
            continue

        if line in {"-", "•", "â€¢"}:
            pending_bullet = True
            continue

        line = re.sub(r"^[-•â€¢]\s*", "", line).strip()
        line = re.sub(r"\s+([,.;:!?])", r"\1", line)
        line = re.sub(r"\(\s+", "(", line)
        line = re.sub(r"\s+\)", ")", line)
        line = re.sub(r"(?i)^Summary\s+", "", line)

        section_match = re.match(r"^(Short answer:|Rules:|Fact-based analysis:|Conclusion:)\s*(.*)$", line, flags=re.I)
        point_match = re.match(r"^(Point\s+(One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten)(\([a-z]\))?:)\s*(.*)$", line, flags=re.I)

        if point_match:
            if output:
                output.append("")
                output.append("---")
                output.append("")
            output.append(f"{point_match.group(1)} {point_match.group(4).strip()}".strip())
            current_section = "point"
            pending_bullet = False
            continue

        if section_match:
            label = section_match.group(1)
            body = section_match.group(2).strip()
            canonical = {
                "short answer:": "Short answer:",
                "rules:": "Rules:",
                "fact-based analysis:": "Fact-based analysis:",
                "conclusion:": "Conclusion:",
            }[label.lower()]
            output.append("")
            output.append(canonical)
            current_section = canonical.lower().rstrip(":")
            pending_bullet = False
            if body:
                if current_section in {"rules", "fact-based analysis"}:
                    output.append(f"- {body}")
                else:
                    output.append(body)
            continue

        if pending_bullet or current_section in {"rules", "fact-based analysis"}:
            if output and output[-1].startswith("- ") and not pending_bullet:
                output[-1] = f"{output[-1]} {line}".strip()
            else:
                output.append(f"- {line}")
            pending_bullet = False
            continue

        if output and output[-1] and not is_section_line(output[-1]) and output[-1] != "---":
            output[-1] = f"{output[-1]} {line}".strip()
        else:
            output.append(line)

    cleaned = "\n".join(output)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"(?m)^Rules:\n(?!- )", "Rules:\n", cleaned)
    return cleaned.strip()


def extract_answer_path(body):
    answer_path = extract_between(
        body,
        "Condensed sample-answer path:",
        ["Question call(s):"],
    )

    if not answer_path:
        return ""

    return format_answer_path(answer_path)


def parse_entries(raw_text):
    text = raw_text or ""
    matches = list(ENTRY_HEADER_RE.finditer(text))
    entries = []

    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        model_points = extract_answer_path(body)

        entries.append(
            {
                "exam_name": normalize_exam(match.group(1), match.group(2)),
                "question_number": match.group(3),
                "model_points": model_points,
            }
        )

    return entries


def backup_db(db_path):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.with_name(
        f"{db_path.stem}_backup_before_condensed_answer_overwrite_{timestamp}{db_path.suffix}"
    )
    shutil.copy2(db_path, backup_path)
    return backup_path


def db_key(exam_name, question_number):
    return (str(exam_name or "").strip().lower(), str(question_number or "").strip().lower())


def update_database(entries, apply=False, overwrite=False):
    init_db()
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, exam_name, question_number, model_points
        FROM questions
        """
    )
    question_rows = cur.fetchall()
    questions_by_key = {}
    duplicate_db_keys = []

    for question_id, exam_name, question_number, model_points in question_rows:
        key = db_key(exam_name, question_number)
        if key in questions_by_key:
            duplicate_db_keys.append((exam_name, question_number))
        questions_by_key[key] = (question_id, model_points or "")

    stats = Counter()
    unmatched = []
    skipped_existing = []
    empty_entries = []

    entry_counts = Counter(db_key(e["exam_name"], e["question_number"]) for e in entries)
    duplicate_entry_keys = [key for key, count in entry_counts.items() if count > 1]

    for entry in entries:
        key = db_key(entry["exam_name"], entry["question_number"])
        target = questions_by_key.get(key)

        if not target:
            unmatched.append((entry["exam_name"], entry["question_number"]))
            stats["unmatched"] += 1
            continue

        model_points = entry["model_points"].strip()
        if len(model_points) < 100:
            empty_entries.append((entry["exam_name"], entry["question_number"]))
            stats["empty_or_short"] += 1
            if apply and overwrite:
                question_id, _existing_model_points = target
                cur.execute("UPDATE questions SET model_points = '' WHERE id = ?", (question_id,))
            continue

        question_id, existing_model_points = target
        if existing_model_points.strip() and not overwrite:
            skipped_existing.append((entry["exam_name"], entry["question_number"], question_id))
            stats["skipped_existing"] += 1
            continue

        if apply:
            cur.execute(
                "UPDATE questions SET model_points = ? WHERE id = ?",
                (model_points, question_id),
            )

        stats["updated" if apply else "would_update"] += 1

    if apply:
        conn.commit()

    conn.close()

    return {
        "stats": stats,
        "unmatched": unmatched,
        "skipped_existing": skipped_existing,
        "empty_entries": empty_entries,
        "duplicate_entry_keys": duplicate_entry_keys,
        "duplicate_db_keys": duplicate_db_keys,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Import condensed sample answers into questions.model_points."
    )
    parser.add_argument("pdf", help="Path to MEE_Condensed_Sample_Answers_By_Subject.pdf")
    parser.add_argument("--apply", action="store_true", help="Write changes to the database.")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing model_points. Without this, only blank model_points are filled.",
    )
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)

    raw_text = read_pdf_text(pdf_path)
    entries = parse_entries(raw_text)

    print("Condensed Answer Import")
    print("=======================")
    print(f"Parsed answer blocks: {len(entries)}")

    backup_path = None
    if args.apply:
        backup_path = backup_db(Path(DB_NAME))
        print(f"Backup created: {backup_path}")

    result = update_database(entries, apply=args.apply, overwrite=args.overwrite)
    stats = result["stats"]

    print(f"Would update: {stats.get('would_update', 0)}")
    print(f"Updated: {stats.get('updated', 0)}")
    print(f"Skipped existing: {stats.get('skipped_existing', 0)}")
    print(f"Unmatched: {stats.get('unmatched', 0)}")
    print(f"Empty/short skipped: {stats.get('empty_or_short', 0)}")

    if result["duplicate_entry_keys"]:
        print("Duplicate PDF keys:")
        for exam_name, question_number in result["duplicate_entry_keys"][:20]:
            print(f"  {exam_name} Q{question_number}")

    if result["duplicate_db_keys"]:
        print("Duplicate DB keys:")
        for exam_name, question_number in result["duplicate_db_keys"][:20]:
            print(f"  {exam_name} Q{question_number}")

    if result["unmatched"]:
        print("Unmatched entries:")
        for exam_name, question_number in result["unmatched"][:30]:
            print(f"  {exam_name} Q{question_number}")

    if result["empty_entries"]:
        print("Empty/short entries:")
        for exam_name, question_number in result["empty_entries"][:30]:
            print(f"  {exam_name} Q{question_number}")

    if not args.apply:
        print("Dry run only. Re-run with --apply to write changes.")


if __name__ == "__main__":
    main()
