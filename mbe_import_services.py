# -*- coding: utf-8 -*-
"""Service helpers for MBE trap-trainer bulk templates and uploads."""

import hashlib
import re
import json
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


def _clean_cell(value):
    return str(value or "").strip()


def _answer_index(value):
    value = _clean_cell(value).upper()
    if not value:
        return None
    if value in {"1", "2", "3", "4"}:
        return int(value) - 1
    if value in {"A", "B", "C", "D"}:
        return "ABCD".index(value)
    for letter in "ABCD":
        if letter in value.split():
            return "ABCD".index(letter)
    if value[-1:] in "ABCD":
        return "ABCD".index(value[-1])
    return None


def _normalize_for_uid(value):
    return " ".join(
        "".join(ch.lower() if ch.isalnum() else " " for ch in _clean_cell(value)).split()
    )


def _card_uid(subject, subtopic, title, scenario, question, correct_text):
    fingerprint = "||".join(
        [
            _normalize_for_uid(subject),
            _normalize_for_uid(subtopic),
            _normalize_for_uid(title or question),
            _normalize_for_uid(scenario),
            _normalize_for_uid(correct_text),
        ]
    )
    return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:24]


def _clean_flashcard_export_text(value):
    text = str(value or "")
    replacements = {
        "â€”": "-",
        "â€“": "-",
        "â†’": "->",
        "â€¦": "...",
        "â€œ": '"',
        "â€�": '"',
        "â€˜": "'",
        "â€™": "'",
        "Â·": "-",
        "·": "-",
        "Â": "",
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    return " ".join(text.split())


MBE_SUBJECT_ALIASES = {
    "civil procedure": "Civil Procedure",
    "civ pro": "Civil Procedure",
    "federal civil procedure": "Civil Procedure",
    "constitutional law": "Constitutional Law",
    "con law": "Constitutional Law",
    "contracts": "Contracts",
    "contract law": "Contracts",
    "criminal law": "Criminal Law and Procedure",
    "criminal procedure": "Criminal Law and Procedure",
    "criminal law and procedure": "Criminal Law and Procedure",
    "crim law": "Criminal Law and Procedure",
    "crim pro": "Criminal Law and Procedure",
    "evidence": "Evidence",
    "real property": "Real Property",
    "property": "Real Property",
    "torts": "Torts",
}


def normalize_mbe_subject(raw_subject):
    """Mirror normalizeMBESubject() from mbe_trap_trainer.html."""
    text = " ".join(str(raw_subject or "").strip().split()).lower()
    return MBE_SUBJECT_ALIASES.get(text, raw_subject or "Uncategorized")


def _title_case_known_mbe_label(value):
    text = _clean_flashcard_export_text(value).strip()
    known = {
        "CIVIL PROCEDURE": "Civil Procedure",
        "CONSTITUTIONAL LAW": "Constitutional Law",
        "CONTRACTS": "Contracts",
        "CRIMINAL LAW": "Criminal Law and Procedure",
        "CRIMINAL LAW AND PROCEDURE": "Criminal Law and Procedure",
        "EVIDENCE": "Evidence",
        "REAL PROPERTY": "Real Property",
        "TORTS": "Torts",
    }
    return known.get(text.upper(), text.title())


def _extract_text_without_label(node, label):
    if node is None:
        return ""
    text = _clean_flashcard_export_text(node.get_text(" ", strip=True))
    if label and text.lower().startswith(label.lower()):
        text = text[len(label):].strip(" :-")
    return text


def adaptibar_flashcards_from_html(path, *, source_name="adaptibar_rules"):
    """Parse exported AdaptiBar miss flashcards into app MBE card records."""
    try:
        from bs4 import BeautifulSoup
    except ImportError as exc:
        raise RuntimeError("Parsing AdaptiBar flashcards requires beautifulsoup4.") from exc

    html = Path(path).read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")
    cards = []
    errors = []

    for fallback_index, card_node in enumerate(soup.select(".card"), start=1):
        card_num_text = _clean_flashcard_export_text(
            (card_node.select_one(".card-num") or "").get_text(" ", strip=True)
            if card_node.select_one(".card-num")
            else ""
        )
        number_match = re.search(r"CARD\s+(\d+)", card_num_text, flags=re.IGNORECASE)
        card_number = int(number_match.group(1)) if number_match else fallback_index

        meta_match = re.search(r"CARD\s+\d+\s*-\s*(.+?)(?:\s*/\s*(.+))?$", card_num_text, flags=re.IGNORECASE)
        subject = normalize_mbe_subject(
            _title_case_known_mbe_label(meta_match.group(1)) if meta_match else ""
        )
        subtopic_from_meta = _title_case_known_mbe_label(meta_match.group(2)) if meta_match and meta_match.group(2) else ""

        heading = _clean_flashcard_export_text(
            card_node.select_one(".card-front h2").get_text(" ", strip=True)
            if card_node.select_one(".card-front h2")
            else ""
        )
        subtopic = heading or subtopic_from_meta or "AdaptiBar Miss"

        question_node = card_node.select_one(".card-front .question")
        small_node = question_node.select_one("small") if question_node else None
        small_text = _clean_flashcard_export_text(small_node.get_text(" ", strip=True) if small_node else "")
        if small_node:
            small_node.extract()
        question = _clean_flashcard_export_text(question_node.get_text(" ", strip=True) if question_node else "")

        answer_match = re.search(
            r"Picked\s+([A-D]):\s*(.*?)\s*(?:->|→)\s*correct\s+([A-D]):\s*(.*)$",
            small_text,
            flags=re.IGNORECASE,
        )
        if not answer_match:
            errors.append(f"Card {card_number}: could not parse picked/correct answer line.")
            continue
        picked_letter, picked_text, correct_letter, correct_text = answer_match.groups()
        picked_text = _clean_flashcard_export_text(picked_text)
        correct_text = _clean_flashcard_export_text(correct_text)

        rule = ""
        plain = ""
        for line in card_node.select(".rule-line"):
            key = _clean_flashcard_export_text(
                line.select_one(".rule-key").get_text(" ", strip=True) if line.select_one(".rule-key") else ""
            ).upper()
            val = _clean_flashcard_export_text(
                line.select_one(".rule-val").get_text(" ", strip=True) if line.select_one(".rule-val") else ""
            )
            if key == "RULE":
                rule = val
            elif key == "PLAIN":
                plain = val

        shortcut = _extract_text_without_label(card_node.select_one(".key-rule"), "Shortcut")
        trap_text = _clean_flashcard_export_text(card_node.select_one(".trap-box").get_text(" ", strip=True) if card_node.select_one(".trap-box") else "")
        trap_text = re.sub(r"^Trap\s*[-—]\s*why\s+[A-D]\s+is\s+wrong\s*", "", trap_text, flags=re.IGNORECASE).strip()

        if not question:
            question = "Which answer states the governing rule for this missed AdaptiBar question?"

        if not subject or not correct_text:
            errors.append(f"Card {card_number}: missing subject or correct answer.")
            continue

        options = [
            {"t": correct_text, "ok": True, "trap": False, "why": rule},
            {"t": picked_text or f"Picked answer {picked_letter.upper()}", "ok": False, "trap": True, "why": trap_text},
        ]
        title = subtopic or question[:90]
        public_card = {
            "subj": subject,
            "sub": subtopic,
            "title": title,
            "scenario": "",
            "q": question or "Choose the best answer.",
            "ru": shortcut,
            "options": options,
            "_b": False,
            "plain": plain,
            "source": source_name,
        }
        uid = f"{source_name}_{card_number:03d}"
        cards.append(
            {
                "card_uid": uid,
                "adv_id": uid,
                "subject": subject,
                "subtopic": subtopic,
                "title": title,
                "scenario": "",
                "question": question or "Choose the best answer.",
                "rule_hint": shortcut or rule,
                "options_json": json.dumps(options, ensure_ascii=False),
                "plain_english": plain,
                "shortcut": shortcut,
                "source": source_name,
                "source_row": card_number,
                "raw_json": json.dumps(public_card, ensure_ascii=False),
            }
        )

    return cards, errors


def mbe_cards_from_dataframe(df, *, source_name="MBE bulk upload"):
    """Convert validated MBE upload rows into database records and preview errors."""
    missing = missing_mbe_template_columns(df.columns)
    if missing:
        return [], [f"Missing required columns: {', '.join(missing)}"]

    cards = []
    errors = []

    for row_index, row in df.iterrows():
        row_no = int(row_index) + 2
        subject = normalize_mbe_subject(_clean_cell(row.get("Subject")))
        subtopic = _clean_cell(row.get("Subtopic"))
        scenario = _clean_cell(row.get("Scenario"))
        question = _clean_cell(row.get("Question"))
        title = question[:90] if question else scenario[:90]
        rule_hint = _clean_cell(row.get("Why Correct"))
        plain = _clean_cell(row.get("Plain English"))
        shortcut = _clean_cell(row.get("Shortcut"))

        option_texts = [
            _clean_cell(row.get("Option A")),
            _clean_cell(row.get("Option B")),
            _clean_cell(row.get("Option C")),
            _clean_cell(row.get("Option D")),
        ]
        correct_idx = _answer_index(row.get("Correct (A-D)"))
        trap_idx = _answer_index(row.get("Trap (A-D)"))

        if not any([subject, scenario, question] + option_texts):
            continue
        if not subject:
            errors.append(f"Row {row_no}: missing Subject.")
            continue
        if not scenario:
            errors.append(f"Row {row_no}: missing Scenario.")
            continue
        if not option_texts[0] or not option_texts[1]:
            errors.append(f"Row {row_no}: needs at least Option A and Option B.")
            continue
        if correct_idx is None or correct_idx >= len(option_texts) or not option_texts[correct_idx]:
            errors.append(f"Row {row_no}: Correct (A-D) must point to a non-empty option.")
            continue

        options = []
        for idx, option_text in enumerate(option_texts):
            if not option_text:
                continue
            is_correct = idx == correct_idx
            is_trap = trap_idx is not None and idx == trap_idx and idx != correct_idx
            if is_correct:
                why = rule_hint
            elif is_trap:
                why = _clean_cell(row.get("Why Trap Is Wrong"))
            else:
                why = ""
            options.append({"t": option_text, "ok": is_correct, "trap": is_trap, "why": why})

        correct_text = option_texts[correct_idx]
        public_card = {
            "subj": subject,
            "sub": subtopic,
            "title": title,
            "scenario": scenario,
            "q": question or "Choose the best answer.",
            "ru": shortcut,
            "options": options,
            "_b": False,
            "plain": plain,
            "source": source_name,
        }
        uid = _card_uid(subject, subtopic, title, scenario, question, correct_text)
        cards.append(
            {
                "card_uid": uid,
                "adv_id": "",
                "subject": subject,
                "subtopic": subtopic,
                "title": title,
                "scenario": scenario,
                "question": question or "Choose the best answer.",
                "rule_hint": shortcut,
                "options_json": json.dumps(options, ensure_ascii=False),
                "plain_english": plain,
                "shortcut": shortcut,
                "source": source_name,
                "source_row": row_no,
                "raw_json": json.dumps(public_card, ensure_ascii=False),
            }
        )

    return cards, errors


def _trainer_norm_text(value, limit=180):
    text = "".join(ch.lower() if ch.isalnum() else " " for ch in str(value or ""))
    return " ".join(text.split())[:limit]


def load_builtin_trap_trainer_cards():
    """Load built-in MBE cards embedded in mbe_trap_trainer.html."""
    html_path = project_file_path("mbe_trap_trainer.html")
    if not html_path.exists():
        return []
    html = html_path.read_text(encoding="utf-8")
    match = re.search(r"const BUILTIN = (\[.*?\]);\s*\n", html, re.S)
    if not match:
        return []
    return json.loads(match.group(1))


def mbe_card_content_fingerprint(
    *,
    subject,
    subtopic,
    scenario,
    question,
    options=None,
    options_json=None,
):
    """Mirror the trainer's getCardContentFingerprint() for duplicate detection."""
    opts = options
    if opts is None:
        try:
            opts = json.loads(options_json or "[]")
        except json.JSONDecodeError:
            opts = []
    correct = next((o for o in opts if o.get("ok")), {})
    return "||".join(
        [
            _trainer_norm_text(subject),
            _trainer_norm_text(subtopic),
            _trainer_norm_text(scenario),
            _trainer_norm_text(question),
            _trainer_norm_text(correct.get("t", "")),
        ]
    )


def builtin_duplicate_lookup():
    """Return lookup sets for cards already present in the built-in trainer deck."""
    content_fps = set()
    adv_ids = set()
    for card in load_builtin_trap_trainer_cards():
        # Fingerprint under both the raw and normalized subject so cards whose
        # subject gets normalized on import (e.g. "Criminal Law" ->
        # "Criminal Law and Procedure") still match the built-in deck.
        raw_subject = card.get("subj") or ""
        for subject in {raw_subject, normalize_mbe_subject(raw_subject)}:
            content_fps.add(
                mbe_card_content_fingerprint(
                    subject=subject,
                    subtopic=card.get("sub"),
                    scenario=card.get("scenario"),
                    question=card.get("q"),
                    options=card.get("options") or [],
                )
            )
        for key in (card.get("advId"), card.get("id")):
            if not key:
                continue
            adv_ids.add(str(key))
            if str(key).upper().startswith("ABX"):
                adv_ids.add(str(key)[3:])
    return {"content_fps": content_fps, "adv_ids": adv_ids}


def is_builtin_duplicate_mbe_card(card):
    """Return True when a DB/import card repeats a built-in trainer question."""
    lookup = builtin_duplicate_lookup()
    adv_id = str(card.get("adv_id") or "").strip()
    if adv_id and adv_id in lookup["adv_ids"]:
        return True
    content_fp = mbe_card_content_fingerprint(
        subject=card.get("subject"),
        subtopic=card.get("subtopic"),
        scenario=card.get("scenario"),
        question=card.get("question"),
        options_json=card.get("options_json"),
    )
    return content_fp in lookup["content_fps"]


def find_builtin_duplicate_db_rows(rows):
    """Return database rows that duplicate built-in trainer cards."""
    lookup = builtin_duplicate_lookup()
    dupes = []
    for row in rows or []:
        (
            db_id,
            _card_uid,
            adv_id,
            subject,
            subtopic,
            _title,
            scenario,
            question,
            _rule_hint,
            options_json,
            *_rest,
        ) = row
        adv = str(adv_id or "").strip()
        if adv and adv in lookup["adv_ids"]:
            dupes.append(row)
            continue
        content_fp = mbe_card_content_fingerprint(
            subject=subject,
            subtopic=subtopic,
            scenario=scenario,
            question=question,
            options_json=options_json,
        )
        if content_fp in lookup["content_fps"]:
            dupes.append(row)
    return dupes


def normalize_trainer_options(options):
    """Coerce stored option dicts to the trainer's shape ("t" = choice text)."""
    out = []
    for opt in options or []:
        if not isinstance(opt, dict):
            continue
        opt = dict(opt)
        if not opt.get("t") and opt.get("text"):
            opt["t"] = opt.pop("text")
        opt.pop("label", None)
        out.append(opt)
    return out


def database_rows_to_mbe_cards(rows):
    """Convert mbe_cards database rows into trap-trainer card dictionaries."""
    cards = []
    for row in rows or []:
        (
            db_id,
            card_uid,
            adv_id,
            subject,
            subtopic,
            title,
            scenario,
            question,
            rule_hint,
            options_json,
            plain,
            shortcut,
            source,
        ) = row
        try:
            options = json.loads(options_json or "[]")
        except json.JSONDecodeError:
            options = []
        normalized_subject = normalize_mbe_subject(subject or "")
        cards.append(
            {
                "id": f"DB{db_id}",
                "dbId": db_id,
                "cardUid": card_uid,
                "advId": adv_id or None,
                "subj": normalized_subject,
                "sub": subtopic or "",
                "title": title or question or "MBE card",
                "scenario": scenario or "",
                "q": question or "Choose the best answer.",
                "ru": rule_hint or shortcut or "",
                "options": normalize_trainer_options(options),
                "_b": False,
                "plain": plain or "",
                "source": source or "App database",
                "_db": True,
            }
        )
    return cards
