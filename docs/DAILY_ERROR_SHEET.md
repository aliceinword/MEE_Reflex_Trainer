# Daily Error Sheet

At the end of each day, eligible users receive an email summarizing every drill/quiz miss, grouped by rule.

## How misses are recorded

| Source | When recorded | Storage |
|--------|---------------|---------|
| MBE Drills | Incorrect answer synced from the trap trainer | `missed_answer_events` |
| Bridge Drill | Incorrect multiple-choice pick | `missed_answer_events` |
| MEE Muscle Ladder / Mini Drill | Self-score 2 or below | `missed_answer_events` |

Each row is deduplicated with an `event_key` so the same miss is not stored twice.

## Configuration

Environment variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `DAILY_ERROR_SHEET_ENABLED` | `true` | Master switch for the scheduled job |
| `DAILY_ERROR_SHEET_SEND_HOUR` | `21` | Default send hour (24h) when user has no override |
| `DAILY_ERROR_SHEET_TIMEZONE` | `America/New_York` | Default timezone when user has no override |
| `EMAIL_FROM_ADDRESS` | — | Required sender address |
| `SMTP_HOST` | — | SMTP server hostname |
| `SMTP_PORT` | `587` | SMTP port |
| `SMTP_USER` | — | SMTP username (optional) |
| `SMTP_PASSWORD` | — | SMTP password (optional) |
| `SMTP_USE_TLS` | `true` | Use STARTTLS |
| `EMAIL_DRY_RUN` | `false` | Log emails instead of sending |
| `APP_BASE_URL` | `http://localhost:8501` | Base URL for retry links |

User-specific settings live in **Settings → Daily Error Sheet** (backed by `user_notification_settings`).

## Scheduled job

Streamlit does not run background jobs. Use Windows Task Scheduler, cron, or a similar runner to execute:

```bat
cd C:\Users\Olesia\OneDrive\MEE_Reflex_Trainer
set EMAIL_FROM_ADDRESS=you@example.com
set SMTP_HOST=smtp.example.com
set SMTP_USER=you@example.com
set SMTP_PASSWORD=secret
python scripts\send_daily_error_sheets.py
```

Run hourly (recommended) so each user's local 9:00 PM window is caught reliably.

## Manual testing

Dry run (no SMTP):

```bat
set EMAIL_DRY_RUN=1
set EMAIL_FROM_ADDRESS=errors@example.com
python scripts\send_daily_error_sheets.py --user alice --date 2026-06-11 --force
```

Admins can also preview/send from **Settings → Daily Error Sheet**.

## Database tables

- `missed_answer_events` — individual misses
- `user_notification_settings` — per-user email preferences
- `daily_error_sheet_sent` — idempotent send log (`username`, `report_date`)

Tables are created automatically by `database.init_db()` on app startup.

## Tests

```bat
python -m unittest tests.test_daily_error_sheet
```
