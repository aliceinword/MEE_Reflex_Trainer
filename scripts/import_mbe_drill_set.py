# -*- coding: utf-8 -*-
"""
Import an MBE drill-set Excel file into mee_trainer.db.

Run from project root:
    python scripts/import_mbe_drill_set.py path/to/Drill_Set.xlsx
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from database import count_mbe_cards, get_mbe_cards, upsert_mbe_cards  # noqa: E402
from mbe_import_services import mbe_cards_from_dataframe  # noqa: E402


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/import_mbe_drill_set.py <path-to-xlsx>")
        return 1

    xlsx = Path(sys.argv[1])
    if not xlsx.exists():
        print(f"File not found: {xlsx}")
        return 1

    source = xlsx.name
    df = pd.read_excel(xlsx).fillna("")
    cards, errors = mbe_cards_from_dataframe(df, source_name=source)
    if errors:
        print("Import errors:")
        for err in errors:
            print(f"  - {err}")
        return 1
    if not cards:
        print("No cards parsed from workbook.")
        return 1

    subjects = sorted({c["subject"] for c in cards})
    result = upsert_mbe_cards(cards)
    imported = sum(1 for row in get_mbe_cards() if len(row) > 12 and row[12] == source)
    print(
        f"Done: inserted={result['inserted']} updated={result['updated']} "
        f"skipped={result['skipped']} skipped_builtin={result.get('skipped_builtin_duplicate', 0)}"
    )
    print(f"Source {source}: {imported} cards in database")
    print(f"Subjects: {', '.join(subjects)}")
    print(f"Total MBE cards: {count_mbe_cards()}")
    print("Refresh http://localhost:8501 → MBE Drills.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
