# MEE Reflex Trainer

A focused, ADHD-friendly study tool for the **Multistate Essay Examination (MEE)**
portion of the Uniform Bar Exam (UBE). It turns past MEE questions into small,
repeatable drills that train the core reflex:

> **Call → Issue → Rule → Trigger Facts → Conclusion**

Instead of writing a full essay every time, you build reliable recall one tiny
rep at a time, then ladder up to full timed essays.

---

## Features

- **Daily Workout dashboard** – see what to practice next and your weak subjects.
- **Mini Essay Drill** – break a question into its calls and answer one at a time.
- **MEE Muscle Ladder** – five intensity levels, from issue-spotting to a full timed MEE.
- **Issue Spotting / Rule Retrieval / Timed IRAC** drills.
- **Due Review Queue** – spaced repetition based on your self-scores.
- **Live stopwatch** on every drill so you can see how long an answer took.
- **Progressive hints** that reveal help gradually, never the full answer first.
- **Attack Outline rules** and **Plug & Play essay templates** searchable in-app.
- **Reading comfort mode** – larger text and wider spacing for dyslexia/ADHD.

---

## Important: bring your own study materials

This repository contains **only the application code**. It does **not** include any
exam questions, model answers, attack outlines, or essay templates, because those
materials are copyrighted by their respective publishers (e.g. the NCBE, and
commercial bar-prep providers).

To use the app you supply your own legally-obtained materials and import them
locally. The database file the app creates on your machine stays on your machine.

---

## Setup

You need **Python 3.11+** installed.

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd MEE_Reflex_Trainer

# 2. (Recommended) create a virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
streamlit run app.py
```

On Windows you can also double-click **`run_app.bat`**.

The app opens in your browser at `http://localhost:8501`.

---

## Importing your own questions

You have two options:

### Option A — CSV bulk import (in-app)
Open the **Question Bank** page, download the CSV template, fill it in with your
own questions, and upload it.

### Option B — PDF import scripts (command line)
If you have your own materials as PDFs, the helper scripts can parse them into the
local database. Point them at *your* files:

```bash
python import_studicata_bank.py "path/to/your-question-bank.pdf"
python import_attack_outline.py "path/to/your-attack-outline.pdf"
python import_plug_play_templates.py "path/to/your-templates.pdf"
```

These scripts write to a local SQLite database (`mee_reflex.db`) that is ignored
by git and never leaves your computer.

## Adding your own rules

You do not need a PDF for rules. On the **Attack Outline Rules** page, open
**"Add your own rules"** to:

- **Add one rule** at a time (subject, title, rule text) — handy whenever you
  notice something missing.
- **Bulk add from CSV** — download the template, fill in your own
  (non-copyrighted) outline rules, and upload it.

Everything you add stays in your local database.

### Importing a Word (.docx) rule book

If you keep your rules in a Word document, `import_master_rules.py` can load them
in bulk. It expects this structure (Word paragraph styles):

| Style | Meaning |
|-------|---------|
| `Heading 1` | Subject (e.g. "I. Business Associations") |
| `Heading 2` | Sub-topic (e.g. "A. Agency") |
| `Rule Bullet` | One rule each (e.g. "Actual authority: ...") |
| `Tip` | Issue-spotter note |

```bash
python import_master_rules.py "path/to/your-rule-book.docx"
```

Re-running is safe — duplicate rules (same subject + title + source) are skipped,
so you can edit your document and re-import anytime.

---

## Project structure

| File | Purpose |
|------|---------|
| `app.py` | The Streamlit application (all pages and UI). |
| `database.py` | SQLite schema and data-access functions. |
| `text_cleanup.py` | Normalizes messy text extracted from PDFs. |
| `import_studicata_bank.py` | Imports MEE questions from a PDF question bank. |
| `import_attack_outline.py` | Imports rules from an attack-outline PDF. |
| `import_plug_play_templates.py` | Imports essay templates from a PDF. |
| `reset_studicata_import.py` | Backs up and resets imported question data. |
| `.streamlit/config.toml` | Theme and server settings. |

---

## Disclaimer

This is an independent study aid. It is not affiliated with, endorsed by, or
sponsored by the NCBE or any bar-prep company. "MEE" and "UBE" are referenced
descriptively. You are responsible for ensuring you have the right to use any
materials you import.

---

## License

Released under the [MIT License](LICENSE). The license covers the application
code only — not any study materials you import.
