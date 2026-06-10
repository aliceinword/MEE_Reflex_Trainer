# -*- coding: utf-8 -*-
"""
Import the 57-card Civ Pro MBE drill set into mee_trainer.db (mbe_cards).

Run from project root:
    python scripts/import_civpro_drill_set.py

Optional path to the Excel file:
    python scripts/import_civpro_drill_set.py "C:\\path\\to\\CivPro_Drill_Set.xlsx"
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from database import get_mbe_cards, upsert_mbe_cards  # noqa: E402
from mbe_import_services import mbe_cards_from_dataframe  # noqa: E402

DEFAULT_XLSX = ROOT / "data" / "CivPro_Drill_Set.xlsx"
FALLBACK_XLSX = Path(
    r"C:\Users\olesi\OneDrive\Desktop\Adapti Bar q\CivPro_Drill_Set.xlsx"
)
SOURCE = "CivPro_Drill_Set.xlsx"


def resolve_xlsx(cli_path: str | None) -> Path:
    if cli_path:
        path = Path(cli_path)
        if not path.exists():
            raise FileNotFoundError(f"Excel file not found: {path}")
        return path
    if DEFAULT_XLSX.exists():
        return DEFAULT_XLSX
    if FALLBACK_XLSX.exists():
        return FALLBACK_XLSX
    raise FileNotFoundError(
        f"Place CivPro_Drill_Set.xlsx at {DEFAULT_XLSX} or pass a path argument."
    )


def count_civpro_source(cards) -> int:
    return sum(1 for row in cards if len(row) > 12 and row[12] == SOURCE)


def main() -> int:
    xlsx = resolve_xlsx(sys.argv[1] if len(sys.argv) > 1 else None)
    df = pd.read_excel(xlsx).fillna("")
    cards, errors = mbe_cards_from_dataframe(df, source_name=SOURCE)
    if errors:
        print("Import errors:")
        for err in errors:
            print(f"  - {err}")
        return 1
    if not cards:
        print("No cards parsed from workbook.")
        return 1

    result = upsert_mbe_cards(cards)
    civpro = count_civpro_source(get_mbe_cards())
    print(
        f"Done: inserted={result['inserted']} updated={result['updated']} "
        f"skipped={result['skipped']} skipped_builtin={result.get('skipped_builtin_duplicate', 0)}"
    )
    print(f"Civ Pro drill cards in database (source={SOURCE}): {civpro}")
    print("Refresh http://localhost:8501 → MBE Drills → check Civil Procedure.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
