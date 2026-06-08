# Data Availability

This app ships with a public seed database:

- `mee_reflex.db`

On first run, the app copies that seed database to the local runtime database:

- `mee_trainer.db`

`mee_trainer.db` is intentionally ignored by Git. It is where each local/deployed instance stores user activity, attempts, login users, and other runtime changes.

## Bundled Study Content

The seed database currently includes:

- MEE questions with model analysis
- MEE outline rules
- Plug-and-play essay templates
- Rule flashcards
- MBE drill content embedded in `mbe_trap_trainer.html`
- MBE bulk-upload templates

## Privacy / User Accounts

The shared seed database does not include personal login users, remember-me tokens, or attempts.

For a deployed private app, create the admin account through Streamlit secrets using `.streamlit/secrets.toml.example` as the template. If no users or auth secrets exist, the app runs without a login so new users can still access the bundled study content.

## Runtime Recovery

If a deployed runtime database exists but is missing public study content, `database.py` backfills the public content tables from `mee_reflex.db` without overwriting users or attempts.
