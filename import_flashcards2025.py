# -*- coding: utf-8 -*-

import html
import re
import sys
from pathlib import Path

from database import add_rule_flashcard, init_db


SUBJECT_KEYWORDS = {
    "Business Associations": [
        "agency", "agent", "principal", "authority", "partnership", "partner",
        "corporation", "shareholder", "director", "officer", "llc", "promoter",
        "stock", "bylaws", "merger", "derivative",
    ],
    "Civil Procedure": [
        "jurisdiction", "diversity", "domicile", "venue", "complaint", "answer",
        "motion", "joinder", "discovery", "sanctions", "summary judgment", "jmol",
        "res judicata", "collateral estoppel", "appeal", "mandamus",
    ],
    "Constitutional Law": [
        "standing", "mootness", "ripeness", "advisory opinions", "political questions",
        "commerce", "taxing", "spending", "president", "executive", "dormant commerce",
        "supremacy", "preemption", "state action", "due process", "equal protection",
        "takings", "speech", "first amendment",
    ],
    "Contracts": [
        "offer", "acceptance", "consideration", "statute of frauds", "ucc",
        "parol evidence", "breach", "damages", "cover", "modification", "condition",
    ],
    "Criminal Law & Procedure": [
        "murder", "manslaughter", "larceny", "robbery", "burglary", "attempt",
        "conspiracy", "search", "seizure", "miranda", "confession", "warrant", "arrest",
    ],
    "Evidence": [
        "hearsay", "relevance", "character", "impeachment", "witness", "privilege",
        "expert", "authentication",
    ],
    "Real Property": [
        "deed", "mortgage", "easement", "covenant", "lease", "landlord", "tenant",
        "adverse possession", "recording", "title",
    ],
    "Torts": [
        "negligence", "battery", "assault", "false imprisonment", "defamation",
        "strict liability", "products", "causation", "duty",
    ],
}

SUBJECT_NAMES = list(SUBJECT_KEYWORDS.keys())


BAD_HEADINGS = {
    "FLASHCARDS",
    "JULY 2025",
}


def strip_rtf(text):
    text = re.sub(r"\\'[0-9a-fA-F]{2}", lambda m: bytes.fromhex(m.group(0)[2:]).decode("cp1252", errors="ignore"), text)
    text = re.sub(r"\\u(-?\d+)\??", lambda m: chr(int(m.group(1)) % 65536), text)
    text = re.sub(r"\\(?:par|line)\b", "\n", text)
    text = re.sub(r"\\tab\b", "\t", text)
    text = re.sub(r"{\\fonttbl.*?}", "", text, flags=re.DOTALL)
    text = re.sub(r"{\\colortbl.*?}", "", text, flags=re.DOTALL)
    text = re.sub(r"\\[a-zA-Z]+-?\d* ?", "", text)
    text = text.replace("{", "").replace("}", "")
    text = text.replace("\\~", " ")
    text = text.replace("\\-", "-")
    text = text.replace("\\_", "_")
    text = text.replace("\\", "")
    return html.unescape(text)


def clean_rtf_artifacts(line):
    line = line.replace("*", "")
    line = re.sub(r"-\d+(?:-\d+)*", "", line)
    line = re.sub(r"\s+", " ", line).strip()

    for subject in SUBJECT_NAMES:
        compact = subject.replace("&", "And")
        line = re.sub(rf"^(?:{re.escape(subject)}|{re.escape(compact)})\s*", "", line, flags=re.IGNORECASE)
        line = re.sub(rf"^(?:{re.escape(subject)}|{re.escape(compact)})\s*", "", line, flags=re.IGNORECASE)

    return line.strip()


def normalize_text(text):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    lines = [clean_rtf_artifacts(line.strip()) for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def is_heading(line):
    candidate = line.strip()

    if not (4 <= len(candidate) <= 90):
        return False

    if candidate.upper() in BAD_HEADINGS:
        return False

    if re.search(r"[.!?]$", candidate):
        return False

    letters = [ch for ch in candidate if ch.isalpha()]

    if not letters:
        return False

    uppercase_ratio = sum(1 for ch in letters if ch.isupper()) / len(letters)
    if uppercase_ratio < 0.82:
        return False

    if re.search(r"\b(?:PAGE|COPYRIGHT|WWW|HTTP)\b", candidate, flags=re.IGNORECASE):
        return False

    return True


def infer_subject(title, rule_text):
    blob = f"{title} {rule_text}".lower()
    scores = []

    for subject, keywords in SUBJECT_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            if keyword in blob:
                score += 2 if " " in keyword else 1
        scores.append((score, subject))

    scores.sort(reverse=True)
    return scores[0][1] if scores and scores[0][0] > 0 else "Unknown"


def make_tags(subject, title):
    clean_subject = re.sub(r"[^A-Za-z0-9]+", "", subject or "Unknown")
    clean_title = re.sub(r"[^A-Za-z0-9]+", "", title.title())
    tags = []

    if clean_subject:
        tags.append(f"#{clean_subject}")
    if clean_title:
        tags.append(f"#{clean_title}")

    return " ".join(tags)


def parse_flashcards(text):
    lines = normalize_text(strip_rtf(text)).splitlines()
    cards = []
    current_title = None
    current_body = []

    for line in lines:
        if is_heading(line):
            if current_title and current_body:
                body = "\n".join(current_body).strip()
                if body:
                    cards.append((current_title.title(), body))
            current_title = re.sub(r"\s+", " ", line.strip()).title()
            current_body = []
        elif current_title:
            current_body.append(line)

    if current_title and current_body:
        body = "\n".join(current_body).strip()
        if body:
            cards.append((current_title.title(), body))

    return cards


def import_flashcards(path):
    init_db()
    source_path = Path(path)
    raw = source_path.read_text(encoding="utf-8", errors="ignore")
    cards = parse_flashcards(raw)
    imported = 0
    skipped = 0

    for title, rule_text in cards:
        subject = infer_subject(title, rule_text)
        tags = make_tags(subject, title)

        if add_rule_flashcard(subject, title, rule_text, source_path.name, tags=tags):
            imported += 1
        else:
            skipped += 1

    return imported, skipped


def main():
    if len(sys.argv) < 2:
        print('Usage: python import_flashcards2025.py Flashcards2025.rtf')
        return 1

    imported, skipped = import_flashcards(sys.argv[1])
    print(f"Imported {imported} flashcards.")
    print(f"Skipped {skipped} duplicates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
