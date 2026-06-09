# -*- coding: utf-8 -*-
"""Read-only MBE card inventory and duplicate diagnostics."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

import _bootstrap  # noqa: F401 - adds the project root to sys.path.

from database import fetch_all


ROOT = Path(__file__).resolve().parent.parent


def _norm(value):
    text = str(value or "").lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _card_fingerprint(row):
    correct = ""
    try:
        options = json.loads(row["options_json"] or "[]")
        correct = next((opt.get("t") or "" for opt in options if opt.get("ok")), "")
    except Exception:
        correct = ""

    return "|".join(
        [
            _norm(row["subject"]),
            _norm(row["subtopic"]),
            _norm(row["scenario"]),
            _norm(row["question"]),
            _norm(correct),
        ]
    )


def _rows_as_dicts(rows):
    fields = [
        "id",
        "card_uid",
        "adv_id",
        "subject",
        "subtopic",
        "title",
        "scenario",
        "question",
        "rule_hint",
        "options_json",
        "plain_english",
        "shortcut",
        "source",
        "source_row",
        "created_at",
        "updated_at",
    ]
    return [dict(zip(fields, row)) for row in rows]


def load_cards():
    rows = fetch_all(
        """
        SELECT
            id,
            card_uid,
            adv_id,
            subject,
            subtopic,
            title,
            scenario,
            question,
            rule_hint,
            options_json,
            plain_english,
            shortcut,
            source,
            source_row,
            created_at,
            updated_at
        FROM mbe_cards
        ORDER BY subject, subtopic, id
        """
    )
    return _rows_as_dicts(rows)


def load_practice_summary():
    rows = fetch_all(
        """
        SELECT username, stats_json, updated_at
        FROM mbe_practice_stats
        ORDER BY username
        """
    )
    out = []
    for username, stats_json, updated_at in rows:
        try:
            blob = json.loads(stats_json or "{}")
        except Exception:
            blob = {}
        stats = blob.get("cardStats") or {}
        practiced = sum(
            1
            for value in stats.values()
            if isinstance(value, dict)
            and (value.get("timesSeen") or value.get("practiceHistory"))
        )
        snoozed = sum(
            1
            for value in stats.values()
            if isinstance(value, dict) and value.get("snoozedUntil")
        )
        out.append(
            {
                "username": username,
                "stats_entries": len(stats),
                "practiced_cards": practiced,
                "snoozed_cards": snoozed,
                "updated_at": updated_at,
            }
        )
    return out


def summarize(cards):
    by_source = {}
    by_subject = {}
    for card in cards:
        source = card["source"] or "App database"
        subject = card["subject"] or "Uncategorized"
        by_source[source] = by_source.get(source, 0) + 1
        by_subject[subject] = by_subject.get(subject, 0) + 1

    drill_cards = [c for c in cards if (c["source"] or "") != "adaptibar_rules"]
    flashcards = [c for c in cards if c["source"] == "adaptibar_rules"]

    fingerprints = {}
    adv_ids = {}
    for card in cards:
        fp = _card_fingerprint(card)
        if fp:
            fingerprints.setdefault(fp, []).append(card)
        adv_id = str(card["adv_id"] or "").strip()
        if adv_id:
            adv_ids.setdefault(adv_id, []).append(card)

    content_dupes = [group for group in fingerprints.values() if len(group) > 1]
    adv_dupes = [group for group in adv_ids.values() if len(group) > 1]

    return {
        "total_cards": len(cards),
        "drill_cards": len(drill_cards),
        "flashcards": len(flashcards),
        "by_source": by_source,
        "by_subject": by_subject,
        "content_dupes": content_dupes,
        "adv_dupes": adv_dupes,
    }


def write_csv(path, cards):
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "id",
                "adv_id",
                "subject",
                "subtopic",
                "title",
                "question",
                "source",
                "source_row",
                "created_at",
                "updated_at",
            ],
        )
        writer.writeheader()
        for card in cards:
            writer.writerow(
                {
                    "id": card["id"],
                    "adv_id": card["adv_id"],
                    "subject": card["subject"],
                    "subtopic": card["subtopic"],
                    "title": card["title"],
                    "question": card["question"],
                    "source": card["source"],
                    "source_row": card["source_row"],
                    "created_at": card["created_at"],
                    "updated_at": card["updated_at"],
                }
            )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--csv",
        type=Path,
        help="Optional path to write a card inventory CSV.",
    )
    args = parser.parse_args()

    cards = load_cards()
    summary = summarize(cards)
    practice = load_practice_summary()

    print(f"Database: {ROOT / 'mee_trainer.db'}")
    print(f"Total MBE cards: {summary['total_cards']}")
    print(f"MBE drill cards: {summary['drill_cards']}")
    print(f"MBE flashcards/rules: {summary['flashcards']}")

    print("\nBy source:")
    for source, count in sorted(summary["by_source"].items()):
        print(f"  {source}: {count}")

    print("\nBy subject:")
    for subject, count in sorted(summary["by_subject"].items()):
        print(f"  {subject}: {count}")

    print("\nPractice rows:")
    if not practice:
        print("  none")
    for row in practice:
        print(
            "  {username}: {practiced_cards} practiced, "
            "{snoozed_cards} snoozed, {stats_entries} stat entries, updated {updated_at}".format(
                **row
            )
        )

    print("\nDuplicate checks:")
    print(f"  duplicate AdaptiBar IDs: {len(summary['adv_dupes'])}")
    print(f"  duplicate content fingerprints: {len(summary['content_dupes'])}")
    for label, groups in (
        ("AdaptiBar ID", summary["adv_dupes"]),
        ("content", summary["content_dupes"]),
    ):
        for group in groups[:10]:
            ids = ", ".join(str(card["id"]) for card in group)
            sample = group[0]
            print(
                f"  {label} dupe ids [{ids}] - "
                f"{sample['subject']} / {sample['subtopic']} - {sample['title']}"
            )

    if args.csv:
        write_csv(args.csv, cards)
        print(f"\nWrote CSV: {args.csv}")


if __name__ == "__main__":
    main()
