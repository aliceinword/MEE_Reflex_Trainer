# -*- coding: utf-8 -*-
"""Scheduled job: send Daily Error Sheets to eligible users.

Run from the project root:

    python scripts/send_daily_error_sheets.py

Manual send for one user/date:

    python scripts/send_daily_error_sheets.py --user alice --date 2026-06-11 --force

Dry-run email (no SMTP delivery):

    set EMAIL_DRY_RUN=1
    python scripts/send_daily_error_sheets.py --user alice --date 2026-06-11 --force
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import _bootstrap  # noqa: F401

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database import ensure_db_initialized
from daily_error_sheet_service import run_daily_error_sheet_job, send_daily_error_sheet_for_user


def main() -> int:
    parser = argparse.ArgumentParser(description="Send Daily Error Sheets")
    parser.add_argument("--user", help="Send for one username instead of running the full job")
    parser.add_argument("--date", help="Report date YYYY-MM-DD (with --user)")
    parser.add_argument("--force", action="store_true", help="Ignore send-hour gate and duplicate-send guard")
    parser.add_argument("--send-if-empty", action="store_true", help="Send even when there are no misses")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    ensure_db_initialized()

    if args.user:
        if not args.date:
            print("ERROR: --date is required with --user", file=sys.stderr)
            return 2
        result = send_daily_error_sheet_for_user(
            args.user,
            args.date,
            force=args.force,
            send_if_empty=args.send_if_empty,
        )
        print(json.dumps(result, indent=2))
        return 0 if result.get("ok") else 1

    results = run_daily_error_sheet_job(force=args.force)
    print(json.dumps(results, indent=2))
    failed = [item for item in results if not item.get("ok")]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
