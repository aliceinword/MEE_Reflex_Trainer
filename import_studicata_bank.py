import argparse
import re
from pathlib import Path

import fitz  # PyMuPDF

from database import init_db, add_question, get_connection
from text_cleanup import normalize_extracted_text


ACTIVE_KEYWORDS = [
    "civil procedure",
    "federal civil procedure",
    "constitutional law",
    "contracts",
    "sales",
    "criminal law",
    "criminal procedure",
    "evidence",
    "real property",
    "torts",
    "agency",
    "partnership",
    "corporations",
    "limited liability company",
    "business associations",
]

MPT_BACKGROUND_KEYWORDS = [
    "family",
    "trust",
    "future interests",
    "decedents",
    "estates",
]

RETIRED_STANDALONE_KEYWORDS = [
    "secured transactions",
    "conflict of laws",
]

HISTORICAL_KEYWORDS = [
    "commercial paper",
    "negotiable instruments",
]


def clean_text(text: str) -> str:
    return normalize_extracted_text(text)


def extract_page_text(page) -> str:
    words = page.get_text("words", sort=True)

    if not words:
        return clean_text(page.get_text("text"))

    lines = []
    current_line = None
    line_words = []

    for word in words:
        line_key = (word[5], word[6])

        if current_line is not None and line_key != current_line:
            lines.append(" ".join(line_words))
            line_words = []

        current_line = line_key
        line_words.append(word[4])

    if line_words:
        lines.append(" ".join(line_words))

    return clean_text("\n".join(lines))


def legacy_clean_text(text: str) -> str:
    replacements = {
        "\u00a0": " ",
        "\uf0a7": "",
        "’": "'",
        "“": '"',
        "”": '"',
        "–": "-",
        "—": "-",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    lines = []
    for line in text.splitlines():
        stripped = line.strip()

        if not stripped:
            continue

        # Remove common PDF noise.
        if stripped.isdigit():
            continue

        if stripped.startswith("© 2025 Studicata"):
            continue

        if stripped.startswith("Studicata |"):
            continue

        if stripped.startswith("www.studicata.com"):
            continue

        if stripped.startswith("Copyright ©"):
            continue

        lines.append(stripped)

    return "\n".join(lines)


def normalize_subject(raw_subject: str) -> str:
    s = raw_subject.lower()

    if "civil procedure" in s:
        return "Civil Procedure"

    if "constitutional law" in s:
        return "Constitutional Law"

    if "contracts" in s or "sales" in s:
        return "Contracts"

    if "criminal" in s:
        return "Criminal Law & Procedure"

    if "evidence" in s:
        return "Evidence"

    if "real property" in s:
        return "Real Property"

    if "torts" in s:
        return "Torts"

    if (
        "agency" in s
        or "partnership" in s
        or "corporations" in s
        or "business associations" in s
        or "limited liability" in s
    ):
        return "Business Associations"

    if "secured transactions" in s:
        return "Secured Transactions"

    if "conflict of laws" in s:
        return "Conflict of Laws"

    if "family" in s:
        return "Family Law"

    if "trust" in s or "decedents" in s or "estates" in s or "future interests" in s:
        return "Trusts & Estates"

    if "commercial paper" in s or "negotiable" in s:
        return "Commercial Paper"

    return raw_subject.strip() or "Unknown"


def july_2026_status(raw_subject: str) -> tuple[bool, str]:
    s = raw_subject.lower()

    if any(k in s for k in HISTORICAL_KEYWORDS):
        return False, "Historical / low priority"

    if any(k in s for k in RETIRED_STANDALONE_KEYWORDS):
        return False, "Retired standalone - background only"

    if any(k in s for k in MPT_BACKGROUND_KEYWORDS):
        return False, "MPT background only"

    if any(k in s for k in ACTIVE_KEYWORDS):
        return True, "Active standalone MEE"

    return False, "Needs manual review"


def priority_for(year: int | None, active: bool, status: str) -> int:
    if year is None:
        return 3

    if active and year >= 2009:
        return 5

    if active and year < 2009:
        return 4

    if status == "MPT background only" and year >= 2009:
        return 3

    if status == "Retired standalone - background only" and year >= 2009:
        return 3

    if status == "Historical / low priority":
        return 1

    return 2


def extract_subjects_from_title_page(text: str) -> list[str]:
    """
    Finds the subject list on pages like:
    February 2021 MEE
    ►QUESTIONS
    Agency & Partnership
    Civil Procedure
    ...
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    subjects = []
    capture = False

    for line in lines:
        upper = line.upper()

        if (
            "►QUESTIONS" in upper
            or upper == "QUESTIONS"
            or re.search(r"\bMEE\s+QUESTIONS\b", upper)
        ):
            capture = True
            continue

        if capture:
            if (
                "►ANALYSES" in upper
                or upper == "ANALYSES"
                or re.search(r"\bMEE\s+ANALYSES\b", upper)
            ):
                break

            if re.search(r"\bMEE\b", line, re.IGNORECASE):
                continue

            if line.lower() in ["questions", "analyses"]:
                continue

            # Avoid generic intro/navigation lines.
            if len(line) > 120:
                continue

            subjects.append(line)

    # Keep only likely subject lines.
    cleaned = []
    for s in subjects:
        if any(k in s.lower() for k in ACTIVE_KEYWORDS + MPT_BACKGROUND_KEYWORDS + RETIRED_STANDALONE_KEYWORDS + HISTORICAL_KEYWORDS):
            cleaned.append(s)

    return cleaned


def read_pdf_sections(pdf_path: Path):
    doc = fitz.open(pdf_path)

    current_exam = None
    current_year = None
    current_season = None
    mode = None

    sections = {}
    subject_lists = {}

    exam_re = re.compile(r"\b(February|July)\s+(\d{4})\s+MEE\b", re.IGNORECASE)

    for page_num in range(len(doc)):
        page_text = extract_page_text(doc[page_num])

        exam_match = exam_re.search(page_text)
        if exam_match:
            season = exam_match.group(1).title()
            year = int(exam_match.group(2))
            current_exam = f"{season} {year}"
            current_year = year
            current_season = season

        upper_text = page_text.upper()

        if current_exam and (
            "►QUESTIONS" in upper_text
            or "\nQUESTIONS\n" in upper_text
            or re.search(r"\bMEE\s+QUESTIONS\b", upper_text)
        ):
            mode = "questions"
            subjects = extract_subjects_from_title_page(page_text)
            if subjects:
                subject_lists[current_exam] = subjects

        elif current_exam and (
            "►ANALYSES" in upper_text
            or "\nANALYSES\n" in upper_text
            or re.search(r"\bMEE\s+ANALYSES\b", upper_text)
        ):
            mode = "analyses"

        if current_exam and mode in ["questions", "analyses"]:
            key = (current_exam, current_year, current_season, mode)
            sections.setdefault(key, [])
            sections[key].append(page_text)

    doc.close()
    return sections, subject_lists


QUESTION_MARKER_RE = re.compile(
    r"(?m)^\s*(?:MEE\s+)?(?:QUESTION|Q)\s*(\d+)\s*"
    r"(?:[-\u2012\u2013\u2014\u2212:]\s*([A-Z][A-Z0-9 &'?/.,()\-]+))?\s*$"
    r"|^\s*([A-Z][A-Z0-9 &'?/.,()\-]+?)\s+QUESTION\s*$"
    r"|^\s*MEE\s+(\d+)\s*$"
)

ANALYSIS_MARKER_RE = re.compile(
    r"(?m)^\s*(?:MEE\s+)?QUESTION\s+(\d+)\s+ANALYSIS\s*$"
    r"|^\s*ANALYSIS\s+(\d+)(?:\s*[-\u2012\u2013\u2014\u2212:]\s*(.+))?\s*$"
    r"|^\s*([A-Z][A-Z0-9 &'?/\-.,]+?)\s+ANALYSIS\s*$"
)

SECTION_STOP_RE = re.compile(
    r"(?m)^\s*(?:ANALYSES|MPT|[-]{5,})\s*$"
)

SUBJECT_HEADING_RE = re.compile(
    r"(?m)^\s*(?:AGENCY\s*&?\s*PARTNERSHIP|BUSINESS ASSOCIATIONS|CONSTITUTIONAL LAW|"
    r"CIVIL PROCEDURE|TORTS|CONTRACTS|CRIMINAL LAW(?:\s*&\s*PROCEDURE)?|"
    r"EVIDENCE|REAL PROPERTY|FAMILY LAW|SECURED TRANSACTIONS|CONFLICT OF LAWS|"
    r"TRUSTS|DECEDENTS'? ESTATES)\s*$",
    re.IGNORECASE,
)


def remove_exam_junk(text: str) -> str:
    junk_patterns = [
        r"(?mi)^\s*(?:FEBRUARY|JULY)\s+\d{4}\s+MEE\s*$",
        r"(?mi)^.*\d{4}.*copyright.*$",
        r"(?mi)^\s*Copyright.*$",
        r"(?mi)^\s*Studicata.*$",
        r"(?mi)^\s*www\..*$",
        r"(?mi)^\s*These materials are copyrighted.*$",
    ]

    for pattern in junk_patterns:
        text = re.sub(pattern, "", text)

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.strip().isdigit()
    ]
    return "\n".join(lines).strip()


def stop_at_section_boundary(text: str) -> str:
    stops = []

    for regex in [QUESTION_MARKER_RE, SECTION_STOP_RE]:
        match = regex.search(text)
        if match:
            stops.append(match.start())

    if stops:
        text = text[:min(stops)]

    return text.strip()


def looks_like_merged_question(question_text: str) -> bool:
    text = str(question_text or "")

    if len(text) > 18000:
        return True

    later_text = text[500:]

    if QUESTION_MARKER_RE.search(later_text):
        return True

    if SUBJECT_HEADING_RE.search(later_text):
        return True

    if re.search(r"(?m)^\s*1\.\s+", later_text) and len(text) > 5000:
        return True

    return False

def split_questions(section_text: str, subject_list: list[str]) -> list[dict]:
    matches = list(QUESTION_MARKER_RE.finditer(section_text))
    questions = []

    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(section_text)
        body = stop_at_section_boundary(section_text[start:end]).strip()
        body = remove_exam_junk(body)

        if len(body) < 100:
            continue

        if match.group(1) is not None:
            question_number = int(match.group(1))
            if match.group(2):
                raw_subject = match.group(2).strip()
            elif question_number - 1 < len(subject_list):
                raw_subject = subject_list[question_number - 1]
            else:
                raw_subject = "Unknown"
        else:
            if match.group(4) is not None:
                question_number = int(match.group(4))
                raw_subject = subject_list[question_number - 1] if question_number - 1 < len(subject_list) else "Unknown"
            else:
                question_number = len(questions) + 1
                raw_subject = match.group(3).strip()

        call = extract_call_of_question(body)

        questions.append({
            "question_number": question_number,
            "raw_subject": raw_subject,
            "question_text": body,
            "call_of_question": call,
        })

    return questions


def split_analyses(section_text: str) -> dict[int, dict]:
    matches = list(ANALYSIS_MARKER_RE.finditer(section_text))
    analyses = {}

    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(section_text)
        body = section_text[start:end].strip()

        if len(body) < 100:
            continue

        if match.group(1) is not None:
            question_number = int(match.group(1))
            raw_subject = "Unknown"
        elif match.group(2) is not None:
            question_number = int(match.group(2))
            raw_subject = match.group(3).strip() if match.group(3) else "Unknown"
        else:
            question_number = len(analyses) + 1
            raw_subject = match.group(4).strip()

        analyses[question_number] = {
            "raw_subject": raw_subject,
            "analysis_text": body,
            "tested_issues": extract_legal_problems(body),
            "rules": extract_ruleish_points(body),
            "model_points": body,
        }

    return analyses


def extract_call_of_question(question_text: str) -> str:
    """
    Captures numbered calls near the end of a single question.
    If it cannot confidently find calls, it returns the last few clean lines.
    """
    question_text = remove_exam_junk(stop_at_section_boundary(question_text))
    lines = [line.strip() for line in question_text.splitlines() if line.strip()]

    if not lines:
        return ""

    call_start_index = None

    for index in range(len(lines) - 1, -1, -1):
        if re.match(r"^1\.\s+", lines[index]):
            trailing = "\n".join(lines[index:])
            # Avoid grabbing an early enumerated fact list unless it looks like calls.
            if re.search(r"\b(Explain|Discuss|Analyze|Determine|Should|Would|What|Is|Can|May)\b", trailing, re.IGNORECASE):
                call_start_index = index
                break

    if call_start_index is None:
        for index in range(max(0, len(lines) - 20), len(lines)):
            if re.match(r"^\d+\.\s+", lines[index]):
                call_start_index = index
                break

    if call_start_index is not None:
        return remove_exam_junk("\n".join(lines[call_start_index:]))

    # fallback: last few lines
    return remove_exam_junk("\n".join(lines[-6:]))


def extract_legal_problems(analysis_text: str) -> str:
    m = re.search(
        r"Legal Problems:\s*(.*?)(?:DISCUSSION|Point One|POINT ONE)",
        analysis_text,
        re.IGNORECASE | re.DOTALL
    )

    if m:
        return m.group(1).strip()

    # fallback
    return ""


def extract_ruleish_points(analysis_text: str) -> str:
    """
    Pulls a compact rules/analysis preview.
    This is intentionally imperfect; the full analysis remains in model_points.
    """
    chunks = []

    for pattern in [
        r"Point One.*?(?=Point Two|POINT TWO|$)",
        r"POINT ONE.*?(?=POINT TWO|Point Two|$)",
    ]:
        m = re.search(pattern, analysis_text, re.IGNORECASE | re.DOTALL)
        if m:
            chunks.append(m.group(0).strip())
            break

    if not chunks:
        return analysis_text[:1500].strip()

    return "\n\n".join(chunks)[:2500].strip()


def guess_trigger_facts(question_text: str) -> str:
    """
    Leaves a lightweight fact-trigger preview.
    You will clean this manually for important essays.
    """
    lines = [line.strip() for line in question_text.splitlines() if line.strip()]
    useful = []

    for line in lines:
        if any(token in line.lower() for token in [
            "signed",
            "agreed",
            "contract",
            "negligently",
            "filed",
            "served",
            "notice",
            "died",
            "will",
            "trust",
            "loan",
            "security interest",
            "possession",
            "purchase",
            "diversity",
            "jurisdiction",
            "hearsay",
            "search",
            "warrant",
            "deed",
            "lease",
        ]):
            useful.append(line)

    return "\n".join(useful[:12])


def default_traps(raw_subject: str, status: str) -> str:
    traps = []

    if status != "Active standalone MEE":
        traps.append("July 2026 trap: this subject is not a priority for standalone MEE practice.")

    s = raw_subject.lower()

    if "agency" in s or "partnership" in s:
        traps.append("Profit sharing alone is not always enough; distinguish partnership, employee, and independent contractor.")

    if "civil procedure" in s:
        traps.append("Always check subject-matter jurisdiction, personal jurisdiction, venue, Erie, and finality/posture.")

    if "secured" in s:
        traps.append("Attachment, perfection, and priority are separate steps.")

    if "evidence" in s:
        traps.append("Do not jump to hearsay; first ask relevance, purpose, and non-hearsay use.")

    if "real property" in s:
        traps.append("Track recording, notice, covenants/equitable servitudes, and landlord-tenant posture.")

    if "contracts" in s or "sales" in s:
        traps.append("Classify common law vs UCC first; then formation, performance, breach, remedies.")

    if "torts" in s:
        traps.append("Separate duty, breach, causation, damages, and defenses.")

    return "\n".join(traps)


def question_exists(exam_name: str, question_number: int, source: str) -> bool:
    conn = get_connection()
    c = conn.cursor()

    c.execute(
        """
        SELECT COUNT(*)
        FROM questions
        WHERE exam_name = ?
        AND question_number = ?
        AND source = ?
        """,
        (exam_name, str(question_number), source)
    )

    count = c.fetchone()[0]
    conn.close()

    return count > 0


def import_bank(
    pdf_path: Path,
    year_from: int,
    year_to: int,
    active_only: bool,
    dry_run: bool,
    limit: int | None,
    allow_suspicious: bool = False
):
    init_db()

    sections, subject_lists = read_pdf_sections(pdf_path)

    imported = 0
    skipped = 0
    reviewed = 0

    for (exam_name, year, season, mode), pages in sections.items():
        if mode != "questions":
            continue

        if year < year_from or year > year_to:
            continue

        question_text = "\n".join(pages)
        subject_list = subject_lists.get(exam_name, [])
        questions = split_questions(question_text, subject_list)

        analysis_key = (exam_name, year, season, "analyses")
        analysis_text = "\n".join(sections.get(analysis_key, []))
        analyses = split_analyses(analysis_text)

        for q in questions:
            question_number = q["question_number"]

            analysis = analyses.get(question_number, {})
            raw_subject = q["raw_subject"]

            if raw_subject == "Unknown" and analysis.get("raw_subject"):
                raw_subject = analysis["raw_subject"]

            subject = normalize_subject(raw_subject)
            active, status = july_2026_status(raw_subject)
            priority = priority_for(year, active, status)

            if active_only and not active:
                skipped += 1
                continue

            if looks_like_merged_question(q["question_text"]):
                print(f"WARNING: possible merged question: {exam_name} Q{question_number}")

                if not allow_suspicious:
                    skipped += 1
                    continue

            if not dry_run and question_exists(exam_name, question_number, pdf_path.name):
                skipped += 1
                continue

            reviewed += 1

            print(
                f"{'[DRY RUN] ' if dry_run else ''}"
                f"{exam_name} Q{question_number}: {raw_subject} -> {subject} | {status} | priority {priority}"
            )

            if not dry_run:
                add_question(
                    exam_name=exam_name,
                    question_number=str(question_number),
                    subject=subject,
                    question_text=q["question_text"],
                    call_of_question=q["call_of_question"],
                    tested_issues=analysis.get("tested_issues", ""),
                    rules=analysis.get("rules", ""),
                    trigger_facts=guess_trigger_facts(q["question_text"]),
                    traps=default_traps(raw_subject, status),
                    model_points=analysis.get("model_points", ""),
                    active_for_july_2026=active,
                    exam_year=year,
                    exam_season=season,
                    secondary_subjects=raw_subject,
                    july_2026_status=status,
                    priority=priority,
                    source=pdf_path.name,
                )

                imported += 1

            if limit is not None and reviewed >= limit:
                print("\nLimit reached.")
                print_summary(imported, skipped, reviewed, dry_run)
                return

    print_summary(imported, skipped, reviewed, dry_run)


def print_summary(imported: int, skipped: int, reviewed: int, dry_run: bool):
    print("\n========== IMPORT SUMMARY ==========")

    if dry_run:
        print(f"Reviewed rows: {reviewed}")
        print("Dry run only. Nothing was inserted.")
    else:
        print(f"Imported: {imported}")

    print(f"Skipped: {skipped}")
    print("====================================")


def main():
    parser = argparse.ArgumentParser(
        description="Import Studicata MEE Question Bank into MEE Reflex Trainer."
    )

    parser.add_argument(
        "pdf",
        help="Path to Studicata_MEE_PQ_Bank_July_2025.pdf"
    )

    parser.add_argument(
        "--year-from",
        type=int,
        default=2009,
        help="First exam year to import. Default: 2009"
    )

    parser.add_argument(
        "--year-to",
        type=int,
        default=2025,
        help="Last exam year to import. Default: 2025"
    )

    parser.add_argument(
        "--active-only",
        action="store_true",
        help="Import only July 2026 active standalone MEE subjects."
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview import without writing to the database."
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of reviewed questions."
    )

    parser.add_argument(
        "--allow-suspicious",
        action="store_true",
        help="Import rows flagged as possible merged questions."
    )

    args = parser.parse_args()

    pdf_path = Path(args.pdf)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    import_bank(
        pdf_path=pdf_path,
        year_from=args.year_from,
        year_to=args.year_to,
        active_only=args.active_only,
        dry_run=args.dry_run,
        limit=args.limit,
        allow_suspicious=args.allow_suspicious
    )


if __name__ == "__main__":
    main()
