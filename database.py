import sqlite3
import shutil
import os
import time
from contextlib import closing, contextmanager
from datetime import datetime, timedelta
from pathlib import Path

DEFAULT_DB_NAME = "mee_trainer.db"
DB_NAME = os.environ.get("MEE_TRAINER_DB", DEFAULT_DB_NAME)
LEGACY_DB_NAME = "mee_reflex.db"
PUBLIC_SEED_TABLES = (
    "questions",
    "outline_rules",
    "plug_play_templates",
    "rule_flashcards",
)
PUBLIC_SEED_COUNT_SQL = {
    "questions": 'SELECT COUNT(*) FROM "questions"',
    "outline_rules": 'SELECT COUNT(*) FROM "outline_rules"',
    "plug_play_templates": 'SELECT COUNT(*) FROM "plug_play_templates"',
    "rule_flashcards": 'SELECT COUNT(*) FROM "rule_flashcards"',
}
PUBLIC_SEED_DELETE_SQL = {
    "questions": 'DELETE FROM "questions"',
    "outline_rules": 'DELETE FROM "outline_rules"',
    "plug_play_templates": 'DELETE FROM "plug_play_templates"',
    "rule_flashcards": 'DELETE FROM "rule_flashcards"',
}
PUBLIC_SEED_INSERT_SQL = {
    "questions": 'INSERT INTO "questions" SELECT * FROM seed."questions"',
    "outline_rules": 'INSERT INTO "outline_rules" SELECT * FROM seed."outline_rules"',
    "plug_play_templates": 'INSERT INTO "plug_play_templates" SELECT * FROM seed."plug_play_templates"',
    "rule_flashcards": 'INSERT INTO "rule_flashcards" SELECT * FROM seed."rule_flashcards"',
}

_READ_CACHE = {}
_READ_CACHE_TTL_SECONDS = 45

_INDEX_STATEMENTS = (
    "CREATE INDEX IF NOT EXISTS idx_questions_subject ON questions(subject)",
    "CREATE INDEX IF NOT EXISTS idx_questions_active_july ON questions(active_for_july_2026)",
    "CREATE INDEX IF NOT EXISTS idx_questions_next_review ON questions(next_review_at)",
    "CREATE INDEX IF NOT EXISTS idx_questions_july_status ON questions(july_2026_status)",
    "CREATE INDEX IF NOT EXISTS idx_questions_exam_year ON questions(exam_year)",
    "CREATE INDEX IF NOT EXISTS idx_questions_last_practiced ON questions(last_practiced_at)",
    "CREATE INDEX IF NOT EXISTS idx_attempts_question_id ON attempts(question_id)",
    "CREATE INDEX IF NOT EXISTS idx_app_users_username ON app_users(username)",
    "CREATE INDEX IF NOT EXISTS idx_mbe_cards_card_uid ON mbe_cards(card_uid)",
    "CREATE INDEX IF NOT EXISTS idx_mbe_cards_subject ON mbe_cards(subject)",
    "CREATE INDEX IF NOT EXISTS idx_missed_answer_username_date ON missed_answer_events(username, event_date)",
    "CREATE INDEX IF NOT EXISTS idx_missed_answer_event_key ON missed_answer_events(username, event_key)",
    "CREATE INDEX IF NOT EXISTS idx_daily_error_sheet_sent_user_date ON daily_error_sheet_sent(username, report_date)",
    "CREATE INDEX IF NOT EXISTS idx_user_question_answers_user_q ON user_question_answers(username, question_id)",
)


def _read_cached(cache_key, loader):
    now = time.monotonic()
    entry = _READ_CACHE.get(cache_key)
    if entry is not None and now - entry[0] < _READ_CACHE_TTL_SECONDS:
        return entry[1]
    value = loader()
    _READ_CACHE[cache_key] = (now, value)
    return value


def invalidate_read_cache():
    _READ_CACHE.clear()
SQLITE_TIMEOUT_SECONDS = 30
SQLITE_BUSY_TIMEOUT_MS = 30000


def _connect_sqlite(db_path, *, use_wal=False):
    """Open SQLite with safe lock waiting instead of bypassing locks."""
    conn = sqlite3.connect(str(db_path), timeout=SQLITE_TIMEOUT_SECONDS)
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.execute("PRAGMA foreign_keys = ON")

    if use_wal:
        try:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
        except sqlite3.DatabaseError:
            # Some hosted/readonly filesystems may reject WAL; the timeout still helps.
            pass

    return conn


def _table_count_for_path(db_path, table_name):
    if table_name not in PUBLIC_SEED_COUNT_SQL:
        return 0
    try:
        with closing(_connect_sqlite(db_path)) as conn:
            row = conn.execute(PUBLIC_SEED_COUNT_SQL[table_name]).fetchone()
            return int(row[0] or 0)
    except Exception:
        return 0


def _seed_missing_public_content(db_path, seed_path):
    """Backfill public study content from the bundled seed DB into an empty runtime DB."""
    if not db_path.exists() or not seed_path.exists():
        return

    seed_tables = [
        table
        for table in PUBLIC_SEED_TABLES
        if _table_count_for_path(db_path, table) == 0 and _table_count_for_path(seed_path, table) > 0
    ]
    if not seed_tables:
        return

    with write_transaction(db_path) as conn:
        conn.execute("ATTACH DATABASE ? AS seed", (str(seed_path),))
        try:
            for table in seed_tables:
                conn.execute(PUBLIC_SEED_DELETE_SQL[table])
                conn.execute(PUBLIC_SEED_INSERT_SQL[table])
        finally:
            conn.execute("DETACH DATABASE seed")


# Set once per process after the runtime DB file has been created and seeded.
# Without this guard, the work below (filesystem stats plus, when the runtime DB
# already exists, up to 8 extra SQLite connections + COUNT(*) scans via
# _seed_missing_public_content) runs on *every* get_connection() call — i.e. on
# every fetch_all / fetch_one / write. The file only needs ensuring once.
_db_file_ready = False


def _ensure_database_file(force=False):
    global _db_file_ready
    if _db_file_ready and not force:
        return

    db_path = Path(DB_NAME)
    legacy_path = Path(LEGACY_DB_NAME)

    if not legacy_path.exists():
        # No seed DB to bootstrap from; nothing to do now, but check again on a
        # later call in case the seed appears (don't latch the ready flag).
        return

    if DB_NAME != DEFAULT_DB_NAME:
        _db_file_ready = True
        return

    if not db_path.exists():
        shutil.copy2(legacy_path, db_path)
        _db_file_ready = True
        return

    _seed_missing_public_content(db_path, legacy_path)
    _db_file_ready = True


def reset_database_file_cache():
    """Force the next get_connection() to re-run the file/seed setup.

    Useful after operations that recreate or replace the runtime DB file.
    """
    global _db_file_ready
    _db_file_ready = False


def get_connection():
    _ensure_database_file()
    return _connect_sqlite(DB_NAME, use_wal=True)


def fetch_all(query, params=()):
    """Run a parameterized read query and return all rows."""
    with closing(get_connection()) as conn:
        return conn.execute(query, params).fetchall()


def fetch_one(query, params=()):
    """Run a parameterized read query and return one row."""
    with closing(get_connection()) as conn:
        return conn.execute(query, params).fetchone()


def execute_write(query, params=()):
    """Run a single parameterized write query and commit it."""
    with write_transaction() as conn:
        conn.execute(query, params)


@contextmanager
def write_transaction(db_path=None):
    """Open a write transaction and always close the connection."""
    conn = _connect_sqlite(db_path, use_wal=True) if db_path is not None else get_connection()
    try:
        yield conn
        conn.commit()
        invalidate_read_cache()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def question_exists(exam_name, question_number, subject, source=None):
    """Return whether a question already exists for the identifying fields."""
    if source is None:
        return fetch_one(
            """
            SELECT 1
            FROM questions
            WHERE exam_name = ? AND question_number = ? AND subject = ?
            LIMIT 1
            """,
            (exam_name, str(question_number), subject),
        ) is not None

    return fetch_one(
        """
        SELECT 1
        FROM questions
        WHERE exam_name = ? AND question_number = ? AND subject = ? AND source = ?
        LIMIT 1
        """,
        (exam_name, str(question_number), subject, source),
    ) is not None


def question_import_key(exam_name, question_number):
    """Return the normalized key importers use to match existing questions."""
    normalized_number = str(question_number or "").strip().lower().lstrip("0") or "0"
    return (str(exam_name or "").strip().lower(), normalized_number)


def get_question_import_index(include_model_points=False):
    """Return existing questions keyed by exam name and question number for importers."""
    if include_model_points:
        rows = fetch_all("SELECT id, exam_name, question_number, subject, model_points FROM questions")
    else:
        rows = fetch_all("SELECT id, exam_name, question_number FROM questions")
    return {question_import_key(row[1], row[2]): row for row in rows}


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _add_missing_columns(cursor, table_name, column_definitions):
    """Add allowlisted columns for legacy databases without repeating migration code."""
    if table_name not in {"questions", "attempts", "app_users"}:
        raise ValueError(f"Unsupported migration table: {table_name}")

    for column_name in column_definitions:
        if not column_name.replace("_", "").isalnum():
            raise ValueError(f"Unsafe migration column: {column_name}")

    cursor.execute(f"PRAGMA table_info({table_name})")
    existing_columns = {row[1] for row in cursor.fetchall()}

    for column_name, ddl in column_definitions.items():
        if column_name not in existing_columns:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl}")


_db_ready = False


def ensure_db_initialized():
    global _db_ready
    if _db_ready:
        return
    init_db()
    _db_ready = True


def init_db():
    with write_transaction() as conn:
        c = conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exam_name TEXT NOT NULL,
                question_number TEXT NOT NULL,
                subject TEXT NOT NULL,
                question_text TEXT,
                call_of_question TEXT,
                tested_issues TEXT,
                rules TEXT,
                trigger_facts TEXT,
                traps TEXT,
                model_points TEXT,
                active_for_july_2026 INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id INTEGER NOT NULL,
                mode TEXT NOT NULL,
                response_text TEXT,
                self_score INTEGER,
                missed_issues TEXT,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(question_id) REFERENCES questions(id)
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS outline_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT,
                rule_title TEXT,
                appearance_rate TEXT,
                rule_text TEXT,
                pdf_page INTEGER,
                printed_page TEXT,
                source_file TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS plug_play_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT,
                module_title TEXT,
                scenario_trigger TEXT,
                issue_statement TEXT,
                rule_text TEXT,
                analysis_template TEXT,
                conclusion_template TEXT,
                testing_notes TEXT,
                pdf_page INTEGER,
                source_file TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS app_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT,
                name TEXT,
                password_hash TEXT NOT NULL,
                remember_token_hash TEXT,
                remember_created_at TEXT,
                is_admin INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS rule_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT,
                rule_title TEXT,
                source_type TEXT,
                prompt TEXT,
                memory_rule TEXT,
                final_rule TEXT,
                score INTEGER,
                missed_elements TEXT,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS rule_flashcards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT,
                rule_title TEXT,
                rule_text TEXT,
                source_file TEXT,
                tags TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS mbe_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_uid TEXT UNIQUE NOT NULL,
                adv_id TEXT,
                subject TEXT,
                subtopic TEXT,
                title TEXT,
                scenario TEXT,
                question TEXT,
                rule_hint TEXT,
                options_json TEXT,
                plain_english TEXT,
                shortcut TEXT,
                source TEXT,
                source_row INTEGER,
                raw_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS mbe_practice_stats (
                username TEXT PRIMARY KEY,
                stats_json TEXT NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS bridge_drill_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                card_uid TEXT,
                subject TEXT,
                subtopic TEXT,
                rule_draft TEXT,
                picked_letter TEXT,
                correct_letter TEXT,
                draft_score INTEGER,
                pick_correct INTEGER DEFAULT 0,
                skipped_draft INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS missed_answer_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                question_id TEXT,
                session_id TEXT,
                source TEXT NOT NULL,
                topic TEXT,
                subtopic TEXT,
                rule_id TEXT,
                rule_label TEXT,
                missed_rule_text TEXT,
                correct_rule_text TEXT,
                question_prompt TEXT,
                user_answer TEXT,
                correct_answer TEXT,
                explanation TEXT,
                retry_link TEXT,
                event_key TEXT NOT NULL,
                event_at TEXT NOT NULL,
                event_date TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(username, event_key)
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS user_notification_settings (
                username TEXT PRIMARY KEY,
                daily_error_sheet_enabled INTEGER DEFAULT 1,
                daily_error_sheet_email TEXT,
                daily_error_sheet_send_hour INTEGER DEFAULT 21,
                daily_error_sheet_timezone TEXT DEFAULT 'America/New_York',
                send_no_misses_email INTEGER DEFAULT 0,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS daily_error_sheet_sent (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                report_date TEXT NOT NULL,
                sent_at TEXT NOT NULL,
                status TEXT NOT NULL,
                recipient_email TEXT,
                provider_message_id TEXT,
                error_message TEXT,
                UNIQUE(username, report_date)
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS user_question_answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                question_id INTEGER NOT NULL,
                answer_text TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL,
                FOREIGN KEY(question_id) REFERENCES questions(id),
                UNIQUE(username, question_id)
            )
        """)

        # Add new question columns safely if the old database already exists.
        question_extra_columns = {
            "exam_year": "INTEGER",
            "exam_season": "TEXT DEFAULT ''",
            "secondary_subjects": "TEXT DEFAULT ''",
            "july_2026_status": "TEXT DEFAULT 'Active standalone MEE'",
            "priority": "INTEGER DEFAULT 3",
            "source": "TEXT DEFAULT ''",
            "last_practiced_at": "TEXT",
            "next_review_at": "TEXT"
        }

        _add_missing_columns(c, "questions", question_extra_columns)

        # Add new attempt columns safely if the old database already exists.
        attempt_extra_columns = {
            "minutes_spent": "INTEGER DEFAULT 0"
        }

        _add_missing_columns(c, "attempts", attempt_extra_columns)

        user_extra_columns = {
            "remember_token_hash": "TEXT",
            "remember_created_at": "TEXT",
        }
        _add_missing_columns(c, "app_users", user_extra_columns)

        for index_sql in _INDEX_STATEMENTS:
            c.execute(index_sql)


def upsert_mbe_cards(cards):
    """Insert or update MBE drill cards in the app database."""
    if not cards:
        return {"inserted": 0, "updated": 0, "skipped": 0}

    from mbe_import_services import (
        builtin_duplicate_lookup,
        mbe_card_content_fingerprint,
        normalize_mbe_subject,
    )

    inserted = 0
    updated = 0
    skipped = 0
    skipped_builtin = 0
    timestamp = now()
    builtin_lookup = builtin_duplicate_lookup()

    with write_transaction() as conn:
        for card in cards:
            if not card or not card.get("card_uid"):
                skipped += 1
                continue
            adv_id = str(card.get("adv_id") or "").strip()
            content_fp = mbe_card_content_fingerprint(
                subject=card.get("subject"),
                subtopic=card.get("subtopic"),
                scenario=card.get("scenario"),
                question=card.get("question"),
                options_json=card.get("options_json"),
            )
            if (adv_id and adv_id in builtin_lookup["adv_ids"]) or (
                content_fp in builtin_lookup["content_fps"]
            ):
                skipped_builtin += 1
                continue

            card = {
                **card,
                "subject": normalize_mbe_subject(card.get("subject")),
            }

            existing = conn.execute(
                "SELECT id FROM mbe_cards WHERE card_uid = ? LIMIT 1",
                (card.get("card_uid"),),
            ).fetchone()

            params = (
                card.get("card_uid"),
                card.get("adv_id"),
                card.get("subject"),
                card.get("subtopic"),
                card.get("title"),
                card.get("scenario"),
                card.get("question"),
                card.get("rule_hint"),
                card.get("options_json"),
                card.get("plain_english"),
                card.get("shortcut"),
                card.get("source"),
                card.get("source_row"),
                card.get("raw_json"),
                timestamp,
                timestamp,
            )

            conn.execute(
                """
                INSERT INTO mbe_cards (
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
                    raw_json,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(card_uid) DO UPDATE SET
                    adv_id = excluded.adv_id,
                    subject = excluded.subject,
                    subtopic = excluded.subtopic,
                    title = excluded.title,
                    scenario = excluded.scenario,
                    question = excluded.question,
                    rule_hint = excluded.rule_hint,
                    options_json = excluded.options_json,
                    plain_english = excluded.plain_english,
                    shortcut = excluded.shortcut,
                    source = excluded.source,
                    source_row = excluded.source_row,
                    raw_json = excluded.raw_json,
                    updated_at = excluded.updated_at
                """,
                params,
            )

            if existing:
                updated += 1
            else:
                inserted += 1

    return {
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped,
        "skipped_builtin_duplicate": skipped_builtin,
    }


def delete_mbe_cards_by_ids(card_ids):
    """Delete MBE cards by primary key id."""
    ids = [int(card_id) for card_id in (card_ids or []) if card_id is not None]
    if not ids:
        return 0
    deleted = 0
    with write_transaction() as conn:
        for card_id in ids:
            cur = conn.execute("DELETE FROM mbe_cards WHERE id = ?", (card_id,))
            deleted += int(cur.rowcount or 0)
    return deleted


def remove_mbe_cards_duplicating_builtin(*, dry_run=False):
    """Remove app-database MBE cards that repeat the built-in trainer deck."""
    from mbe_import_services import find_builtin_duplicate_db_rows

    rows = get_mbe_cards()
    dupes = find_builtin_duplicate_db_rows(rows)
    removed = []
    for row in dupes:
        removed.append(
            {
                "id": row[0],
                "subject": row[3],
                "subtopic": row[4],
                "title": row[5],
            }
        )
    if dry_run or not removed:
        return {"removed": 0, "dry_run": dry_run, "candidates": removed}
    deleted = delete_mbe_cards_by_ids([item["id"] for item in removed])
    return {"removed": deleted, "dry_run": False, "candidates": removed}


def consolidate_mbe_card_subjects_and_remove_dupes(*, dry_run=False):
    """Normalize subject labels (e.g. Criminal Law) and delete within-DB duplicates."""
    import json

    from mbe_import_services import mbe_card_content_fingerprint, normalize_mbe_subject

    renamed = []
    with write_transaction() as conn:
        rows = conn.execute(
            """
            SELECT id, subject, raw_json
            FROM mbe_cards
            ORDER BY id
            """
        ).fetchall()
        for db_id, subject, raw_json in rows:
            normalized = normalize_mbe_subject(subject)
            if normalized == subject:
                continue
            renamed.append({"id": db_id, "from": subject, "to": normalized})
            if dry_run:
                continue
            updated_raw = raw_json
            if raw_json:
                try:
                    payload = json.loads(raw_json)
                    payload["subj"] = normalized
                    updated_raw = json.dumps(payload, ensure_ascii=False)
                except Exception:
                    updated_raw = raw_json
            conn.execute(
                """
                UPDATE mbe_cards
                SET subject = ?, raw_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (normalized, updated_raw, now(), db_id),
            )

    rows = get_mbe_cards()
    seen = {}
    duplicate_candidates = []
    for row in rows:
        (
            db_id,
            _card_uid,
            adv_id,
            subject,
            subtopic,
            title,
            scenario,
            question,
            _rule_hint,
            options_json,
            *_rest,
        ) = row
        content_fp = mbe_card_content_fingerprint(
            subject=subject,
            subtopic=subtopic,
            scenario=scenario,
            question=question,
            options_json=options_json,
        )
        if content_fp not in seen:
            seen[content_fp] = db_id
            continue
        duplicate_candidates.append(
            {
                "id": db_id,
                "keep_id": seen[content_fp],
                "subject": subject,
                "subtopic": subtopic,
                "title": (title or question or "")[:72],
            }
        )

    removed = 0
    if duplicate_candidates and not dry_run:
        removed = delete_mbe_cards_by_ids([item["id"] for item in duplicate_candidates])

    return {
        "dry_run": dry_run,
        "renamed": renamed,
        "renamed_count": len(renamed),
        "duplicate_candidates": duplicate_candidates,
        "removed_duplicates": removed,
    }


def get_mbe_cards():
    """Return app-stored MBE cards for injection into the trainer."""
    # Static seed content; cached with TTL and cleared on any write.
    return _read_cached(
        "mbe_cards",
        lambda: fetch_all(
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
                source
            FROM mbe_cards
            ORDER BY subject, subtopic, id
            """
        ),
    )


def count_mbe_cards():
    def _count():
        row = fetch_one("SELECT COUNT(*) FROM mbe_cards")
        return int(row[0] or 0) if row else 0

    return _read_cached("mbe_cards_count", _count)


def get_mbe_content_quality(limit=12):
    """Return compact read-only diagnostics for MBE card inventory and practice state."""
    import json

    from mbe_import_services import mbe_card_content_fingerprint

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
            options_json,
            source
        FROM mbe_cards
        ORDER BY subject, subtopic, id
        """
    )

    by_source = {}
    by_subject = {}
    source_rows = {}
    subject_rows = {}
    content_seen = {}
    adv_seen = {}
    content_dupes = []
    adv_dupes = []

    for row in rows:
        (
            card_id,
            _card_uid,
            adv_id,
            subject,
            subtopic,
            title,
            scenario,
            question,
            options_json,
            source,
        ) = row
        subject = subject or "Uncategorized"
        source = source or "App database"
        by_source[source] = by_source.get(source, 0) + 1
        by_subject[subject] = by_subject.get(subject, 0) + 1
        source_rows.setdefault(source, []).append(card_id)
        subject_rows.setdefault(subject, []).append(card_id)

        content_fp = mbe_card_content_fingerprint(
            subject=subject,
            subtopic=subtopic,
            scenario=scenario,
            question=question,
            options_json=options_json,
        )
        if content_fp in content_seen:
            content_dupes.append((card_id, content_seen[content_fp], subject, subtopic, title or question))
        else:
            content_seen[content_fp] = card_id

        adv_id = str(adv_id or "").strip()
        if adv_id:
            if adv_id in adv_seen:
                adv_dupes.append((card_id, adv_seen[adv_id], subject, subtopic, title or question))
            else:
                adv_seen[adv_id] = card_id

    practice_rows = []
    for username, stats_json, updated_at in fetch_all(
        """
        SELECT username, stats_json, updated_at
        FROM mbe_practice_stats
        ORDER BY username
        """
    ):
        try:
            blob = json.loads(stats_json or "{}")
        except Exception:
            blob = {}
        stats = blob.get("cardStats") or {}
        practiced = sum(
            1
            for value in stats.values()
            if isinstance(value, dict) and (value.get("timesSeen") or value.get("practiceHistory"))
        )
        snoozed = sum(
            1
            for value in stats.values()
            if isinstance(value, dict) and value.get("snoozedUntil")
        )
        practice_rows.append((username, len(stats), practiced, snoozed, updated_at))

    drill_cards = sum(count for source, count in by_source.items() if source != "qbank_rules")
    flashcards = by_source.get("qbank_rules", 0)

    return {
        "summary": {
            "total_cards": len(rows),
            "drill_cards": drill_cards,
            "flashcards": flashcards,
            "sources": len(by_source),
            "subjects": len(by_subject),
            "content_duplicates": len(content_dupes),
            "adv_id_duplicates": len(adv_dupes),
        },
        "by_source": sorted(by_source.items(), key=lambda item: (-item[1], item[0]))[:limit],
        "by_subject": sorted(by_subject.items(), key=lambda item: item[0])[:limit],
        "practice_rows": practice_rows[:limit],
        "duplicate_rows": (content_dupes + adv_dupes)[:limit],
    }


def get_mbe_practice_stats(username):
    """Return the saved MBE trap-trainer practice blob for a user, or None."""
    if not username:
        return None
    row = fetch_one(
        "SELECT stats_json FROM mbe_practice_stats WHERE username = ? LIMIT 1",
        (username,),
    )
    if not row or not row[0]:
        return None
    try:
        import json

        return json.loads(row[0])
    except Exception:
        return None


def _merge_unique_json_items(existing_items, incoming_items):
    """Merge list-like JSON records without duplicating identical entries."""
    import json

    merged = []
    seen = set()
    for item in list(existing_items or []) + list(incoming_items or []):
        try:
            sig = json.dumps(item, sort_keys=True, ensure_ascii=False)
        except TypeError:
            sig = str(item)
        if sig in seen:
            continue
        seen.add(sig)
        merged.append(item)
    return merged


def merge_mbe_practice_stats(existing_blob, incoming_blob):
    """Merge an incoming MBE practice sync payload with the saved user blob."""
    if not isinstance(existing_blob, dict):
        existing_blob = {}
    if not isinstance(incoming_blob, dict):
        incoming_blob = {}

    merged = {**existing_blob, **incoming_blob}

    existing_stats = existing_blob.get("cardStats") or {}
    incoming_stats = incoming_blob.get("cardStats") or {}
    card_stats = {}
    for key in set(existing_stats) | set(incoming_stats):
        old_value = existing_stats.get(key) or {}
        new_value = incoming_stats.get(key) or {}
        if isinstance(old_value, dict) and isinstance(new_value, dict):
            combined = {**old_value, **new_value}
            combined["practiceHistory"] = _merge_unique_json_items(
                old_value.get("practiceHistory"),
                new_value.get("practiceHistory"),
            )
            card_stats[key] = combined
        else:
            card_stats[key] = new_value or old_value
    merged["cardStats"] = card_stats

    for list_key in ("errorList", "sessionLog", "masteredCards"):
        merged[list_key] = _merge_unique_json_items(
            existing_blob.get(list_key),
            incoming_blob.get(list_key),
        )

    return merged


def get_mbe_mastery_stats(username):
    """Return MBE mastery summary for the Streamlit dashboard.

    Joins mbe_cards (for subject names) with the per-user practice JSON blob.
    Returns:
      remaining  – active (non-mastered) card count
      mastered   – mastered card count
      by_subject – list of (subject, remaining, mastered) sorted by remaining desc
    """
    blob = get_mbe_practice_stats(username) or {}
    card_stats = blob.get("cardStats") or {}
    if not card_stats:
        return {"remaining": 0, "mastered": 0, "by_subject": []}

    # Build lookup: adv_id -> subject, card_uid -> subject
    card_rows = fetch_all("SELECT card_uid, adv_id, subject FROM mbe_cards")
    uid_to_subj = {row[0]: row[2] for row in card_rows if row[0]}
    adv_to_subj = {str(row[1]): row[2] for row in card_rows if row[1]}

    subject_map = {}
    for key, stats in card_stats.items():
        if not isinstance(stats, dict) or key.startswith("__"):
            continue
        # Resolve subject: adv_id lookup, then uid lookup, then parse key
        subj = adv_to_subj.get(str(key)) or uid_to_subj.get(str(key))
        if not subj and "|" in key:
            subj = key.split("|")[0]
        subj = subj or "Unknown"
        if subj not in subject_map:
            subject_map[subj] = {"remaining": 0, "mastered": 0}
        if stats.get("isMastered"):
            subject_map[subj]["mastered"] += 1
        else:
            subject_map[subj]["remaining"] += 1

    total_remaining = sum(v["remaining"] for v in subject_map.values())
    total_mastered = sum(v["mastered"] for v in subject_map.values())
    by_subject = sorted(
        [(s, v["remaining"], v["mastered"]) for s, v in subject_map.items()],
        key=lambda row: (-row[1], row[0]),
    )
    return {
        "remaining": total_remaining,
        "mastered": total_mastered,
        "by_subject": by_subject,
    }


def save_mbe_practice_stats(username, stats_blob):
    """Persist the MBE trap-trainer practice blob for a user."""
    if not username or not isinstance(stats_blob, dict):
        return False

    import json

    merged_blob = merge_mbe_practice_stats(get_mbe_practice_stats(username), stats_blob)
    payload = json.dumps(merged_blob, ensure_ascii=False)
    timestamp = now()
    with write_transaction() as conn:
        conn.execute(
            """
            INSERT INTO mbe_practice_stats (username, stats_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(username) DO UPDATE SET
                stats_json = excluded.stats_json,
                updated_at = excluded.updated_at
            """,
            (username, payload, timestamp),
        )
    invalidate_read_cache()
    try:
        from missed_answer_service import record_mbe_practice_misses

        record_mbe_practice_misses(username, merged_blob)
    except Exception:
        pass
    return True


def add_outline_rule(subject, rule_title, appearance_rate, rule_text, pdf_page, printed_page, source_file):
    with write_transaction() as conn:
        existing = conn.execute("""
            SELECT id
            FROM outline_rules
            WHERE source_file = ?
            AND subject = ?
            AND rule_title = ?
            AND (pdf_page = ? OR (pdf_page IS NULL AND ? IS NULL))
            LIMIT 1
        """, (source_file, subject, rule_title, pdf_page, pdf_page)).fetchone()

        if existing:
            return False

        conn.execute("""
            INSERT INTO outline_rules (
                subject,
                rule_title,
                appearance_rate,
                rule_text,
                pdf_page,
                printed_page,
                source_file,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            subject,
            rule_title,
            appearance_rate,
            rule_text,
            pdf_page,
            printed_page,
            source_file,
            now()
        ))

    return True


def get_outline_rules(subject=None):
    query = """
        SELECT
            id,
            subject,
            rule_title,
            appearance_rate,
            rule_text,
            pdf_page,
            printed_page,
            source_file
        FROM outline_rules
        WHERE 1=1
    """
    params = []

    if subject and subject != "All":
        query += " AND subject = ?"
        params.append(subject)

    query += " ORDER BY subject, pdf_page, rule_title"

    # Static seed content; cached with TTL and cleared on any write.
    subject_key = "" if not subject or subject == "All" else subject
    return _read_cached(
        f"outline_rules:{subject_key}",
        lambda: fetch_all(query, params),
    )


def get_outline_rules_for_subjects(subjects):
    """Return outline_rules rows whose subject is in the given name list."""
    names = [str(name).strip() for name in (subjects or []) if str(name).strip()]
    if not names:
        return []

    placeholders = ", ".join("?" for _ in names)
    return fetch_all(
        f"""
        SELECT
            id,
            subject,
            rule_title,
            appearance_rate,
            rule_text,
            pdf_page,
            printed_page,
            source_file
        FROM outline_rules
        WHERE subject IN ({placeholders})
        ORDER BY subject, pdf_page, rule_title
        """,
        names,
    )


def get_issue_spotting_question_rows(subjects):
    """Return active July 2026 question rows used to build spotting fallback cards."""
    names = [str(name).strip() for name in (subjects or []) if str(name).strip()]
    if not names:
        return []

    placeholders = ", ".join("?" for _ in names)
    return fetch_all(
        f"""
        SELECT
            id,
            subject,
            tested_issues,
            trigger_facts
        FROM questions
        WHERE active_for_july_2026 = 1
        AND subject IN ({placeholders})
        AND COALESCE(TRIM(tested_issues), '') != ''
        AND COALESCE(TRIM(trigger_facts), '') != ''
        ORDER BY priority DESC, exam_year DESC, id ASC
        """,
        names,
    )


def parse_issue_trigger_from_rule_text(rule_text):
    """Extract Issue trigger: text from attack-table style outline rule_text."""
    from issue_spotting_utils import parse_issue_trigger_from_rule_text as _parse

    return _parse(rule_text)


def get_issue_spotting_cards(subjects, *, high_yield_only=False, limit=None):
    """
    Build normalized MEE Issue Spotting cards for the given subjects.

    Primary source: outline_rules rows that contain an Issue trigger: prefix
    (July 2026 Attack Table and similar imports). Fallback per subject: active
    July 2026 question bank trigger_facts + tested_issues when no attack-table
    cards exist for that subject.
    """
    from issue_spotting_utils import (
        build_attack_table_card,
        build_question_bank_cards,
        dedupe_spotting_cards,
        expand_subject_names,
        filter_high_yield_cards,
        issue_frequency_map,
        sort_spotting_cards,
        canonical_subject_name,
        MEE_ISSUE_SPOTTING_SUBJECTS,
    )

    selected = [str(s).strip() for s in (subjects or []) if str(s).strip()]
    if not selected:
        selected = list(MEE_ISSUE_SPOTTING_SUBJECTS)

    db_names = expand_subject_names(selected)
    question_rows = get_issue_spotting_question_rows(db_names)
    frequency_counts = issue_frequency_map(question_rows)

    outline_rows = get_outline_rules_for_subjects(db_names)
    attack_cards = []
    for row in outline_rows:
        card = build_attack_table_card(row, frequency_counts)
        if card:
            attack_cards.append(card)

    subjects_with_attack = {card["subject"] for card in attack_cards}
    question_cards = []
    for row in question_rows:
        subject = canonical_subject_name(row[1] if len(row) > 1 else "")
        if subject in subjects_with_attack:
            continue
        question_cards.extend(
            build_question_bank_cards(row, frequency_counts)
        )

    cards = dedupe_spotting_cards(attack_cards + question_cards)
    if high_yield_only:
        cards = filter_high_yield_cards(cards)
    cards = sort_spotting_cards(cards)

    if limit is not None:
        try:
            limit_n = int(limit)
        except (TypeError, ValueError):
            limit_n = None
        if limit_n is not None and limit_n > 0:
            cards = cards[:limit_n]

    return cards


def search_outline_rules(query, subject=None, limit=5):
    search_terms = [
        term.strip()
        for term in str(query or "").replace(";", " ").replace(",", " ").split()
        if len(term.strip()) >= 2
    ]

    sql = """
        SELECT
            id,
            subject,
            rule_title,
            appearance_rate,
            rule_text,
            pdf_page,
            printed_page,
            source_file
        FROM outline_rules
        WHERE 1=1
    """
    params = []

    if search_terms:
        sql += " AND ("
        term_clauses = []

        for term in search_terms:
            term_clauses.append("(rule_title LIKE ? OR rule_text LIKE ? OR subject LIKE ?)")
            like = f"%{term}%"
            params.extend([like, like, like])

        sql += " OR ".join(term_clauses)
        sql += ")"

    sql += """
        ORDER BY
            CASE WHEN ? IS NOT NULL AND subject = ? THEN 0 ELSE 1 END,
            subject,
            pdf_page,
            rule_title
        LIMIT ?
    """
    params.extend([subject, subject, limit])

    return fetch_all(sql, params)


def add_rule_flashcard(subject, rule_title, rule_text, source_file, tags=""):
    with write_transaction() as conn:
        existing = conn.execute("""
            SELECT id
            FROM rule_flashcards
            WHERE source_file = ?
            AND rule_title = ?
            LIMIT 1
        """, (source_file, rule_title)).fetchone()

        if existing:
            return False

        conn.execute("""
            INSERT INTO rule_flashcards (
                subject,
                rule_title,
                rule_text,
                source_file,
                tags,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            subject,
            rule_title,
            rule_text,
            source_file,
            tags,
            now(),
        ))

    return True


def _load_rule_flashcards(subject=None):
    query = """
        SELECT
            id,
            subject,
            rule_title,
            rule_text,
            source_file,
            tags
        FROM rule_flashcards
        WHERE 1=1
    """
    params = []

    if subject and subject != "All":
        query += " AND subject = ?"
        params.append(subject)

    query += " ORDER BY subject, rule_title"

    return fetch_all(query, params)


def get_rule_flashcards(subject=None):
    subject_key = "" if not subject or subject == "All" else subject
    return _read_cached(
        f"rule_flashcards:{subject_key}",
        lambda: _load_rule_flashcards(subject),
    )


def search_rule_flashcards(query, subject=None, limit=30):
    sql = """
        SELECT
            id,
            subject,
            rule_title,
            rule_text,
            source_file,
            tags
        FROM rule_flashcards
        WHERE 1=1
    """
    params = []

    if subject and subject != "All":
        # Keep same-subject rules preferred but include compatible nearby subjects
        # through scoring below by not filtering too aggressively.
        pass

    sql += " ORDER BY subject, rule_title"
    rows = fetch_all(sql, params)

    stopwords = {
        "about", "again", "against", "answer", "because", "could", "court",
        "does", "explain", "facts", "from", "have", "issue", "issues",
        "legal", "likely", "must", "question", "rule", "rules", "shall",
        "should", "that", "their", "there", "this", "under", "were",
        "what", "when", "where", "whether", "which", "with", "would",
    }

    words = []
    for raw_word in str(query or "").lower().replace("&", " ").split():
        word = "".join(ch for ch in raw_word if ch.isalnum())
        if len(word) >= 4 and word not in stopwords:
            words.append(word)

    seen = set()
    terms = []
    for word in words:
        if word not in seen:
            seen.add(word)
            terms.append(word)

    query_l = str(query or "").lower()
    subject_l = str(subject or "").strip().lower()
    scored = []

    for row in rows:
        row_subject = str(row[1] or "")
        title = str(row[2] or "")
        rule_text = str(row[3] or "")
        tags = str(row[5] or "")

        row_subject_l = row_subject.lower()
        title_l = title.lower()
        rule_l = rule_text.lower()
        tags_l = tags.lower()

        score = 0

        if subject_l and subject_l != "all" and row_subject_l == subject_l:
            score += 5
        elif subject_l and subject_l != "all" and (
            subject_l in row_subject_l or row_subject_l in subject_l
        ):
            score += 3

        if title_l and title_l in query_l:
            score += 8

        for word in terms:
            if word in title_l:
                score += 3
            if word in tags_l:
                score += 2
            if word in rule_l:
                score += 1

        if not terms and subject_l and row_subject_l == subject_l:
            score += 1

        if score > 0:
            scored.append((score, row))

    scored.sort(key=lambda item: (-item[0], item[1][1], item[1][2]))
    return [row for _, row in scored[:limit]]


def _keyword_set(text):
    stopwords = {
        "the", "and", "for", "with", "that", "this", "from", "into", "when",
        "where", "which", "shall", "under", "rule", "rules", "issue", "issues",
        "point", "one", "two", "three", "four", "five", "six", "may", "must",
        "are", "was", "were", "has", "have", "had", "not", "but", "because",
    }
    words = []

    for raw_word in str(text or "").lower().replace("&", " ").split():
        word = "".join(ch for ch in raw_word if ch.isalnum())

        if len(word) >= 3 and word not in stopwords:
            words.append(word)

    return set(words)


def _subjects_compatible(left, right):
    left = str(left or "").strip().lower()
    right = str(right or "").strip().lower()

    if not left or not right:
        return False

    if left == right:
        return True

    business_subjects = {
        "business associations",
        "agency and partnership",
        "agency & partnership",
        "agency and partnerships",
        "agency & partnerships",
        "corporations and llcs",
        "corporations and llc",
        "corporations & llcs",
        "corps & llc",
    }
    criminal_subjects = {
        "criminal law",
        "criminal procedure",
        "criminal law & procedure",
        "criminal law and procedure",
    }
    trusts_subjects = {
        "trusts",
        "decedents' estates",
        "decedents estates",
        "trusts & estates",
        "wills",
    }

    groups = [business_subjects, criminal_subjects, trusts_subjects]
    return any(left in group and right in group for group in groups)


def find_best_outline_rules_for_question(subject, tested_issues, rules, traps, limit=3):
    candidates = search_outline_rules(
        f"{subject or ''} {tested_issues or ''}",
        subject=subject,
        limit=100
    )

    if not candidates:
        candidates = get_outline_rules(subject=subject)[:100]

    tested_words = _keyword_set(tested_issues)
    rules_words = _keyword_set(rules)
    traps_words = _keyword_set(traps)
    scored = []

    for row in candidates:
        (
            rule_id,
            rule_subject,
            rule_title,
            appearance_rate,
            rule_text,
            pdf_page,
            printed_page,
            source_file,
        ) = row

        title_words = _keyword_set(rule_title)
        text_words = _keyword_set(rule_text)
        score = 0

        if _subjects_compatible(subject, rule_subject):
            score += 5

        score += 3 * len(title_words & tested_words)
        score += 2 * len(title_words & rules_words)
        score += len(text_words & tested_words)
        score += len(title_words & traps_words)

        if score > 0:
            scored.append((score, row))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [row for _, row in scored[:limit]]


def add_plug_play_template(
    subject,
    module_title,
    scenario_trigger,
    issue_statement,
    rule_text,
    analysis_template,
    conclusion_template,
    testing_notes,
    pdf_page,
    source_file
):
    with write_transaction() as conn:
        existing = conn.execute("""
            SELECT id
            FROM plug_play_templates
            WHERE source_file = ?
            AND subject = ?
            AND module_title = ?
            AND (pdf_page = ? OR (pdf_page IS NULL AND ? IS NULL))
            LIMIT 1
        """, (source_file, subject, module_title, pdf_page, pdf_page)).fetchone()

        if existing:
            return False

        conn.execute("""
            INSERT INTO plug_play_templates (
                subject,
                module_title,
                scenario_trigger,
                issue_statement,
                rule_text,
                analysis_template,
                conclusion_template,
                testing_notes,
                pdf_page,
                source_file,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            subject,
            module_title,
            scenario_trigger,
            issue_statement,
            rule_text,
            analysis_template,
            conclusion_template,
            testing_notes,
            pdf_page,
            source_file,
            now()
        ))

    return True


def get_plug_play_templates(subject=None):
    query = """
        SELECT
            id,
            subject,
            module_title,
            scenario_trigger,
            issue_statement,
            rule_text,
            analysis_template,
            conclusion_template,
            testing_notes,
            pdf_page,
            source_file
        FROM plug_play_templates
        WHERE 1=1
    """
    params = []

    if subject and subject != "All":
        query += " AND subject = ?"
        params.append(subject)

    query += " ORDER BY subject, pdf_page, module_title"

    # Static seed content; cached with TTL and cleared on any write.
    subject_key = "" if not subject or subject == "All" else subject
    return _read_cached(
        f"plug_play_templates:{subject_key}",
        lambda: fetch_all(query, params),
    )


def search_plug_play_templates(query, subject=None, limit=5):
    search_terms = [
        term.strip()
        for term in str(query or "").replace(";", " ").replace(",", " ").split()
        if len(term.strip()) >= 2
    ]
    query_text = str(query or "").strip().lower()

    candidates = get_plug_play_templates(subject=subject)

    if subject and not candidates:
        candidates = get_plug_play_templates()

    if not search_terms:
        return candidates[:limit]

    scored = []

    for row in candidates:
        (
            template_id,
            template_subject,
            module_title,
            scenario_trigger,
            issue_statement,
            rule_text,
            analysis_template,
            conclusion_template,
            testing_notes,
            pdf_page,
            source_file,
        ) = row

        title = str(module_title or "").lower()
        scenario = str(scenario_trigger or "").lower()
        issue = str(issue_statement or "").lower()
        rule = str(rule_text or "").lower()
        analysis = str(analysis_template or "").lower()
        subject_text = str(template_subject or "").lower()
        haystack = " ".join([title, scenario, issue, rule, analysis, subject_text])
        score = 0

        if _subjects_compatible(subject, template_subject):
            score += 20

        if query_text and query_text in title:
            score += 30

        if query_text and query_text in haystack:
            score += 10

        for term in search_terms:
            term_lower = term.lower()

            if term_lower in title:
                score += 8
            if term_lower in scenario:
                score += 5
            if term_lower in issue:
                score += 5
            if term_lower in rule:
                score += 4
            if term_lower in analysis:
                score += 3
            if term_lower in subject_text:
                score += 2

        if score > 0:
            scored.append((score, row))

    scored.sort(key=lambda item: (item[0], item[1][9] or 0), reverse=True)
    return [row for _, row in scored[:limit]]


def find_best_plug_play_for_call(subject, call_text, question_text, tested_issues="", limit=3):
    candidates = search_plug_play_templates(
        f"{subject or ''} {call_text or ''} {tested_issues or ''}",
        subject=subject,
        limit=100
    )

    if not candidates:
        candidates = get_plug_play_templates(subject=subject)[:100]

    if subject and not candidates:
        candidates = get_plug_play_templates()[:100]

    call_words = _keyword_set(call_text)
    question_words = _keyword_set(question_text)
    tested_words = _keyword_set(tested_issues)
    scored = []

    for row in candidates:
        (
            template_id,
            template_subject,
            module_title,
            scenario_trigger,
            issue_statement,
            rule_text,
            analysis_template,
            conclusion_template,
            testing_notes,
            pdf_page,
            source_file,
        ) = row

        title_words = _keyword_set(module_title)
        trigger_words = _keyword_set(scenario_trigger)
        issue_words = _keyword_set(issue_statement)
        rule_words = _keyword_set(rule_text)
        score = 0

        if _subjects_compatible(subject, template_subject):
            score += 5

        score += 4 * len(title_words & (call_words | tested_words))
        score += 3 * len(trigger_words & question_words)
        score += 3 * len(issue_words & call_words)
        score += 2 * len(rule_words & tested_words)

        if score > 0:
            scored.append((score, row))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [row for _, row in scored[:limit]]


def add_question(
    exam_name,
    question_number,
    subject,
    question_text,
    call_of_question,
    tested_issues,
    rules,
    trigger_facts,
    traps,
    model_points,
    active_for_july_2026=True,
    exam_year=None,
    exam_season="",
    secondary_subjects="",
    july_2026_status="Active standalone MEE",
    priority=3,
    source=""
):
    execute_write("""
        INSERT INTO questions (
            exam_name,
            question_number,
            subject,
            question_text,
            call_of_question,
            tested_issues,
            rules,
            trigger_facts,
            traps,
            model_points,
            active_for_july_2026,
            exam_year,
            exam_season,
            secondary_subjects,
            july_2026_status,
            priority,
            source,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        exam_name,
        question_number,
        subject,
        question_text,
        call_of_question,
        tested_issues,
        rules,
        trigger_facts,
        traps,
        model_points,
        1 if active_for_july_2026 else 0,
        exam_year,
        exam_season,
        secondary_subjects,
        july_2026_status,
        priority,
        source,
        now()
    ))


def get_questions(
    active_only=False,
    subject=None,
    status=None,
    search=None,
    due_only=False,
    practice_ready_only=False,
):
    query = """
        SELECT
            id,
            exam_name,
            question_number,
            subject,
            july_2026_status,
            priority,
            next_review_at
        FROM questions
        WHERE 1=1
    """
    params = []

    if active_only:
        query += " AND active_for_july_2026 = 1"

    if practice_ready_only:
        query += """
            AND TRIM(COALESCE(question_text, '')) <> ''
            AND TRIM(COALESCE(call_of_question, '')) <> ''
            AND TRIM(COALESCE(model_points, '')) <> ''
        """

    if subject and subject != "All":
        query += " AND subject = ?"
        params.append(subject)

    if status and status != "All":
        query += " AND july_2026_status = ?"
        params.append(status)

    if search:
        query += """
            AND (
                exam_name LIKE ?
                OR subject LIKE ?
                OR tested_issues LIKE ?
                OR rules LIKE ?
                OR traps LIKE ?
                OR trigger_facts LIKE ?
            )
        """
        like = f"%{search}%"
        params.extend([like, like, like, like, like, like])

    if due_only:
        today = datetime.now().strftime("%Y-%m-%d")
        query += """
            AND next_review_at IS NOT NULL
            AND date(next_review_at) <= date(?)
        """
        params.append(today)

    query += """
        ORDER BY
            priority DESC,
            exam_year DESC,
            exam_name DESC,
            question_number ASC
    """

    return fetch_all(query, params)


def get_question_bank_rows(
    subject=None,
    status=None,
    topic=None,
    exam_year=None,
    active_only=False,
    created_from=None,
    created_to=None,
):
    """Return rows for the browse/filter Question Bank page."""
    query = """
        SELECT
            id,
            exam_name,
            question_number,
            subject,
            exam_year,
            exam_season,
            july_2026_status,
            priority,
            source,
            next_review_at,
            created_at,
            tested_issues
        FROM questions
        WHERE 1=1
    """
    params = []

    if active_only:
        query += " AND active_for_july_2026 = 1"

    if subject and subject != "All":
        query += " AND subject = ?"
        params.append(subject)

    if status and status != "All":
        query += " AND july_2026_status = ?"
        params.append(status)

    if exam_year and exam_year != "All":
        query += " AND exam_year = ?"
        params.append(int(exam_year))

    if created_from:
        query += " AND date(created_at) >= date(?)"
        params.append(str(created_from))

    if created_to:
        query += " AND date(created_at) <= date(?)"
        params.append(str(created_to))

    if topic:
        query += """
            AND (
                tested_issues LIKE ?
                OR rules LIKE ?
                OR trigger_facts LIKE ?
                OR traps LIKE ?
                OR model_points LIKE ?
                OR question_text LIKE ?
                OR call_of_question LIKE ?
            )
        """
        like = f"%{topic}%"
        params.extend([like, like, like, like, like, like, like])

    query += """
        ORDER BY
            exam_year DESC,
            CASE exam_season WHEN 'July' THEN 2 WHEN 'February' THEN 1 ELSE 0 END DESC,
            CAST(question_number AS INTEGER) ASC,
            question_number ASC
    """

    return fetch_all(query, params)


def get_exam_years():
    return _read_cached("exam_years", lambda: [
        row[0]
        for row in fetch_all("""
            SELECT DISTINCT exam_year
            FROM questions
            WHERE exam_year IS NOT NULL
            ORDER BY exam_year DESC
        """)
    ])


def get_question_by_id(question_id):
    return fetch_one("""
        SELECT
            id,
            exam_name,
            question_number,
            subject,
            question_text,
            call_of_question,
            tested_issues,
            rules,
            trigger_facts,
            traps,
            model_points,
            active_for_july_2026,
            created_at,
            exam_year,
            exam_season,
            secondary_subjects,
            july_2026_status,
            priority,
            source,
            last_practiced_at,
            next_review_at
        FROM questions
        WHERE id = ?
    """, (question_id,))


def get_subjects():
    return _read_cached("subjects", lambda: [
        row[0]
        for row in fetch_all("""
            SELECT DISTINCT subject
            FROM questions
            WHERE subject IS NOT NULL AND subject != ''
            ORDER BY subject
        """)
    ])


def get_statuses():
    return _read_cached("statuses", lambda: [
        row[0]
        for row in fetch_all("""
            SELECT DISTINCT july_2026_status
            FROM questions
            WHERE july_2026_status IS NOT NULL AND july_2026_status != ''
            ORDER BY july_2026_status
        """)
    ])


def review_date_from_score(score):
    try:
        score = int(score)
    except (TypeError, ValueError):
        score = 0

    if score <= 2:
        days = 1
    elif score == 3:
        days = 3
    elif score == 4:
        days = 7
    else:
        days = 14

    return (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")


def save_attempt(
    question_id,
    mode,
    response_text,
    self_score,
    missed_issues,
    notes,
    minutes_spent=0
):
    practiced_at = now()
    next_review_at = review_date_from_score(self_score)

    with write_transaction() as conn:
        conn.execute("""
            INSERT INTO attempts (
                question_id,
                mode,
                response_text,
                self_score,
                missed_issues,
                notes,
                minutes_spent,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            question_id,
            mode,
            response_text,
            self_score,
            missed_issues,
            notes,
            minutes_spent,
            practiced_at
        ))

        conn.execute("""
            UPDATE questions
            SET last_practiced_at = ?, next_review_at = ?
            WHERE id = ?
        """, (practiced_at, next_review_at, question_id))


def get_attempts(limit=100):
    return fetch_all("""
        SELECT
            attempts.id,
            attempts.question_id,
            questions.subject,
            questions.exam_name,
            questions.question_number,
            attempts.mode,
            attempts.response_text,
            attempts.self_score,
            attempts.missed_issues,
            attempts.notes,
            attempts.minutes_spent,
            attempts.created_at
        FROM attempts
        JOIN questions ON attempts.question_id = questions.id
        ORDER BY attempts.created_at DESC
        LIMIT ?
    """, (limit,))


def save_rule_attempt(
    subject,
    rule_title,
    source_type,
    prompt,
    memory_rule,
    final_rule,
    score,
    missed_elements,
    notes,
):
    execute_write("""
        INSERT INTO rule_attempts (
            subject,
            rule_title,
            source_type,
            prompt,
            memory_rule,
            final_rule,
            score,
            missed_elements,
            notes,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        subject,
        rule_title,
        source_type,
        prompt,
        memory_rule,
        final_rule,
        score,
        missed_elements,
        notes,
        now(),
    ))


def get_rule_attempts(limit=50):
    return fetch_all("""
        SELECT
            id,
            subject,
            rule_title,
            source_type,
            prompt,
            memory_rule,
            final_rule,
            score,
            missed_elements,
            notes,
            created_at
        FROM rule_attempts
        ORDER BY created_at DESC
        LIMIT ?
    """, (limit,))


def get_dashboard_stats():
    today = datetime.now().strftime("%Y-%m-%d")
    cache_key = f"dashboard:{today}"
    now = time.monotonic()
    entry = _READ_CACHE.get(cache_key)
    if entry is not None and now - entry[0] < _READ_CACHE_TTL_SECONDS:
        return entry[1]

    with closing(get_connection()) as conn:
        c = conn.cursor()

        c.execute("SELECT COUNT(*) FROM questions")
        total_questions = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM questions WHERE active_for_july_2026 = 1")
        active_questions = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM attempts")
        total_attempts = c.fetchone()[0]

        c.execute("SELECT ROUND(AVG(self_score), 2) FROM attempts")
        avg_score = c.fetchone()[0] or 0

        c.execute("SELECT COALESCE(SUM(minutes_spent), 0) FROM attempts")
        total_minutes = c.fetchone()[0] or 0

        c.execute("""
            SELECT COUNT(*), COALESCE(SUM(minutes_spent), 0)
            FROM attempts
            WHERE date(created_at) = date(?)
        """, (today,))
        today_attempts, today_minutes = c.fetchone()

        c.execute("""
            SELECT COUNT(*)
            FROM questions
            WHERE next_review_at IS NOT NULL
            AND date(next_review_at) <= date(?)
        """, (today,))
        due_reviews = c.fetchone()[0]

        c.execute("""
            SELECT COUNT(*)
            FROM questions
            WHERE last_practiced_at IS NULL
        """)
        unpracticed_questions = c.fetchone()[0]

        c.execute("""
            SELECT
                questions.subject,
                ROUND(AVG(attempts.self_score), 2),
                COUNT(*)
            FROM attempts
            JOIN questions ON attempts.question_id = questions.id
            GROUP BY questions.subject
            ORDER BY AVG(attempts.self_score) ASC
        """)
        subject_stats = c.fetchall()

        c.execute("""
            SELECT
                questions.subject,
                COUNT(*) AS due_count
            FROM questions
            WHERE next_review_at IS NOT NULL
            AND date(next_review_at) <= date(?)
            GROUP BY questions.subject
            ORDER BY due_count DESC, questions.subject ASC
        """, (today,))
        due_by_subject = c.fetchall()

        c.execute("""
            SELECT
                questions.subject,
                COUNT(*) AS untouched_count
            FROM questions
            WHERE questions.active_for_july_2026 = 1
            AND questions.last_practiced_at IS NULL
            GROUP BY questions.subject
            ORDER BY untouched_count DESC, questions.subject ASC
        """)
        untouched_by_subject = c.fetchall()

        c.execute("""
            SELECT
                questions.id,
                questions.exam_name,
                questions.question_number,
                questions.subject,
                questions.july_2026_status,
                questions.priority,
                questions.next_review_at,
                questions.last_practiced_at,
                COALESCE(AVG(attempts.self_score), -1) AS avg_score,
                COUNT(attempts.id) AS attempt_count
            FROM questions
            LEFT JOIN attempts ON attempts.question_id = questions.id
            WHERE questions.active_for_july_2026 = 1
            GROUP BY questions.id
            ORDER BY
                CASE
                    WHEN questions.next_review_at IS NOT NULL
                    AND date(questions.next_review_at) <= date(?) THEN 0
                    WHEN COUNT(attempts.id) = 0 THEN 1
                    WHEN AVG(attempts.self_score) <= 3 THEN 2
                    ELSE 3
                END,
                questions.priority DESC,
                avg_score ASC,
                questions.exam_year DESC,
                questions.question_number ASC
            LIMIT 8
        """, (today,))
        recommended_queue = c.fetchall()

    result = {
        "total_questions": total_questions,
        "active_questions": active_questions,
        "total_attempts": total_attempts,
        "avg_score": avg_score,
        "total_minutes": total_minutes,
        "today_attempts": today_attempts or 0,
        "today_minutes": today_minutes or 0,
        "due_reviews": due_reviews,
        "unpracticed_questions": unpracticed_questions,
        "subject_stats": subject_stats,
        "due_by_subject": due_by_subject,
        "untouched_by_subject": untouched_by_subject,
        "recommended_queue": recommended_queue
    }
    _READ_CACHE[cache_key] = (now, result)
    return result


def get_mee_content_quality(limit=12):
    """Return compact read-only diagnostics for incomplete MEE question rows."""
    summary = fetch_one(
        """
        SELECT
            COUNT(*) AS total_questions,
            SUM(CASE WHEN active_for_july_2026 = 1 THEN 1 ELSE 0 END) AS active_questions,
            SUM(
                CASE
                    WHEN active_for_july_2026 = 1
                    AND TRIM(COALESCE(question_text, '')) <> ''
                    AND TRIM(COALESCE(call_of_question, '')) <> ''
                    AND TRIM(COALESCE(model_points, '')) <> ''
                    THEN 1 ELSE 0
                END
            ) AS practice_ready_questions,
            SUM(CASE WHEN TRIM(COALESCE(question_text, '')) = '' THEN 1 ELSE 0 END) AS missing_prompt,
            SUM(CASE WHEN TRIM(COALESCE(call_of_question, '')) = '' THEN 1 ELSE 0 END) AS missing_call,
            SUM(CASE WHEN TRIM(COALESCE(model_points, '')) = '' THEN 1 ELSE 0 END) AS missing_sample_answer,
            SUM(CASE WHEN TRIM(COALESCE(rules, '')) = '' THEN 1 ELSE 0 END) AS missing_rules,
            SUM(CASE WHEN TRIM(COALESCE(tested_issues, '')) = '' THEN 1 ELSE 0 END) AS missing_tested_issues,
            SUM(CASE WHEN TRIM(COALESCE(trigger_facts, '')) = '' THEN 1 ELSE 0 END) AS missing_trigger_facts
        FROM questions
        """
    )
    rows = fetch_all(
        """
        SELECT
            id,
            exam_name,
            question_number,
            subject,
            source,
            TRIM(COALESCE(question_text, '')) = '' AS missing_prompt,
            TRIM(COALESCE(call_of_question, '')) = '' AS missing_call,
            TRIM(COALESCE(model_points, '')) = '' AS missing_sample_answer,
            TRIM(COALESCE(rules, '')) = '' AS missing_rules,
            TRIM(COALESCE(tested_issues, '')) = '' AS missing_tested_issues,
            TRIM(COALESCE(trigger_facts, '')) = '' AS missing_trigger_facts
        FROM questions
        WHERE
            TRIM(COALESCE(question_text, '')) = ''
            OR TRIM(COALESCE(call_of_question, '')) = ''
            OR TRIM(COALESCE(model_points, '')) = ''
            OR TRIM(COALESCE(rules, '')) = ''
            OR TRIM(COALESCE(tested_issues, '')) = ''
            OR TRIM(COALESCE(trigger_facts, '')) = ''
        ORDER BY
            missing_prompt DESC,
            missing_call DESC,
            missing_sample_answer DESC,
            missing_rules DESC,
            missing_trigger_facts DESC,
            exam_year DESC,
            exam_name DESC,
            question_number ASC
        LIMIT ?
        """,
        (int(limit),),
    )
    keys = [
        "total_questions",
        "active_questions",
        "practice_ready_questions",
        "missing_prompt",
        "missing_call",
        "missing_sample_answer",
        "missing_rules",
        "missing_tested_issues",
        "missing_trigger_facts",
    ]
    return {
        "summary": dict(zip(keys, [int(value or 0) for value in (summary or [])])),
        "rows": rows,
    }


# ---------------------------------------------------------------------------
# Application users (login / admin-managed access)
# ---------------------------------------------------------------------------

def upsert_admin(username, email, name, password_hash):
    """Create or refresh the admin account (used to seed from secrets)."""
    if not username or not password_hash:
        return

    with write_transaction() as conn:
        row = conn.execute("SELECT id FROM app_users WHERE username = ?", (username,)).fetchone()
        if row:
            conn.execute(
                "UPDATE app_users SET email = ?, name = ?, password_hash = ?, is_admin = 1 WHERE id = ?",
                (email, name, password_hash, row[0]),
            )
        else:
            conn.execute(
                "INSERT INTO app_users (username, email, name, password_hash, is_admin) VALUES (?, ?, ?, ?, 1)",
                (username, email, name, password_hash),
            )


def get_app_user(login):
    """Look up a user by username OR email (case-insensitive)."""
    if not login:
        return None
    login = str(login).strip().lower()
    row = fetch_one(
        """
        SELECT username, email, name, password_hash, is_admin
        FROM app_users
        WHERE LOWER(username) = ? OR LOWER(IFNULL(email, '')) = ?
        LIMIT 1
        """,
        (login, login),
    )
    if not row:
        return None
    return {
        "username": row[0],
        "email": row[1],
        "name": row[2],
        "password_hash": row[3],
        "is_admin": bool(row[4]),
    }


def get_app_user_by_remember_token(token_hash):
    """Look up a user by a hashed remember-me token."""
    if not token_hash:
        return None

    row = fetch_one(
        """
        SELECT username, email, name, password_hash, is_admin
        FROM app_users
        WHERE remember_token_hash = ?
        LIMIT 1
        """,
        (str(token_hash),),
    )
    if not row:
        return None
    return {
        "username": row[0],
        "email": row[1],
        "name": row[2],
        "password_hash": row[3],
        "is_admin": bool(row[4]),
    }


def list_app_users():
    return fetch_all(
        "SELECT username, email, name, is_admin, created_at FROM app_users ORDER BY is_admin DESC, username"
    )


def count_app_users():
    row = fetch_one("SELECT COUNT(*) FROM app_users")
    return row[0]


def add_app_user(username, email, name, password_hash, is_admin=False):
    """Add a user. Returns (ok, message)."""
    username = (username or "").strip().lower()
    email = (email or "").strip().lower()
    if not username or not password_hash:
        return False, "Username and password are required."

    with write_transaction() as conn:
        if conn.execute("SELECT 1 FROM app_users WHERE LOWER(username) = ?", (username,)).fetchone():
            return False, f"Username '{username}' already exists."

        if email and conn.execute("SELECT 1 FROM app_users WHERE LOWER(IFNULL(email,'')) = ?", (email,)).fetchone():
            return False, f"Email '{email}' is already in use."

        conn.execute(
            "INSERT INTO app_users (username, email, name, password_hash, is_admin) VALUES (?, ?, ?, ?, ?)",
            (username, email, name, password_hash, 1 if is_admin else 0),
        )

    return True, f"Added user '{username}'."


def delete_app_user(username):
    execute_write(
        "DELETE FROM app_users WHERE LOWER(username) = ?",
        ((username or "").strip().lower(),),
    )


def set_user_password(username, password_hash):
    execute_write(
        "UPDATE app_users SET password_hash = ? WHERE LOWER(username) = ?",
        (password_hash, (username or "").strip().lower()),
    )


def set_user_remember_token(username, token_hash):
    """Persist a hashed remember-me token for a user."""
    execute_write(
        """
        UPDATE app_users
        SET remember_token_hash = ?, remember_created_at = ?
        WHERE LOWER(username) = ?
        """,
        (token_hash, now(), (username or "").strip().lower()),
    )


def clear_user_remember_token(username):
    """Clear a user's persisted remember-me token."""
    execute_write(
        """
        UPDATE app_users
        SET remember_token_hash = NULL, remember_created_at = NULL
        WHERE LOWER(username) = ?
        """,
        ((username or "").strip().lower(),),
    )


# ---------------------------------------------------------------------------
# Bridge Drill - rule-drafting practice
# ---------------------------------------------------------------------------

def save_bridge_attempt(
    username,
    card_uid,
    subject,
    subtopic,
    rule_draft,
    picked_letter,
    correct_letter,
    draft_score,
    pick_correct,
    skipped_draft=False,
):
    """Persist one Bridge Drill attempt (rule draft + MBE pick + self-score)."""
    created_at = now()
    execute_write(
        """
        INSERT INTO bridge_drill_attempts (
            username, card_uid, subject, subtopic,
            rule_draft, picked_letter, correct_letter,
            draft_score, pick_correct, skipped_draft, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            username,
            card_uid,
            subject,
            subtopic,
            rule_draft,
            picked_letter,
            correct_letter,
            int(draft_score or 0),
            1 if pick_correct else 0,
            1 if skipped_draft else 0,
            created_at,
        ),
    )
    if username and not pick_correct:
        try:
            from missed_answer_service import record_bridge_drill_miss

            record_bridge_drill_miss(
                username,
                card_uid=card_uid or "",
                subject=subject or "",
                subtopic=subtopic or "",
                picked_letter=picked_letter or "",
                correct_letter=correct_letter or "",
                event_at=created_at,
            )
        except Exception:
            pass


def get_bridge_attempts(limit=200):
    """Return recent Bridge Drill attempts, most recent first."""
    return fetch_all(
        """
        SELECT
            id, username, card_uid, subject, subtopic,
            rule_draft, picked_letter, correct_letter,
            draft_score, pick_correct, skipped_draft, created_at
        FROM bridge_drill_attempts
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (limit,),
    )


# ---------------------------------------------------------------------------
# MBE card lookup
# ---------------------------------------------------------------------------

def get_mbe_card_by_uid(card_uid):
    """Return one MBE card row by card_uid, or None."""
    if not card_uid:
        return None
    return fetch_one(
        """
        SELECT
            id, card_uid, adv_id, subject, subtopic, title,
            scenario, question, rule_hint, options_json,
            plain_english, shortcut, source
        FROM mbe_cards
        WHERE card_uid = ?
        LIMIT 1
        """,
        (str(card_uid),),
    )


_MBE_CARD_SELECT = """
    SELECT
        id, card_uid, adv_id, subject, subtopic, title,
        scenario, question, rule_hint, options_json,
        plain_english, shortcut, source
    FROM mbe_cards
"""


def lookup_mbe_card_row(lookup_key):
    """Return an mbe_cards row by trainer key (DB123, ABX123), uid, adv_id, or id."""
    if not lookup_key:
        return None
    key = str(lookup_key).strip()
    if not key:
        return None

    upper = key.upper()
    if upper.startswith("DB"):
        suffix = key[2:]
        if suffix.isdigit():
            row = fetch_one(
                _MBE_CARD_SELECT + " WHERE id = ? LIMIT 1",
                (int(suffix),),
            )
            if row:
                return row

    if upper.startswith("ABX"):
        suffix = key[3:]
        adv_variants = []
        if suffix:
            adv_variants.append(suffix)
            if suffix.isdigit():
                adv_variants.append(str(int(suffix)))
        for adv in adv_variants:
            row = fetch_one(
                _MBE_CARD_SELECT + " WHERE adv_id = ? LIMIT 1",
                (adv,),
            )
            if row:
                return row

    return fetch_one(
        _MBE_CARD_SELECT
        + " WHERE card_uid = ? OR adv_id = ? OR CAST(id AS TEXT) = ? LIMIT 1",
        (key, key, key),
    )


def lookup_mbe_card_by_correct_answer(correct_answer):
    """Best-effort lookup when only the correct answer text is known."""
    answer = (correct_answer or "").strip()
    if len(answer) < 20:
        return None
    snippet = answer[:120]
    return fetch_one(
        _MBE_CARD_SELECT + " WHERE INSTR(options_json, ?) > 0 LIMIT 1",
        (snippet,),
    )


# ---------------------------------------------------------------------------
# Missed answer events (Daily Error Sheet)
# ---------------------------------------------------------------------------

def record_missed_answer_event(
    *,
    username,
    event_key,
    source,
    event_at,
    event_date,
    question_id=None,
    session_id=None,
    topic=None,
    subtopic=None,
    rule_id=None,
    rule_label=None,
    missed_rule_text=None,
    correct_rule_text=None,
    question_prompt=None,
    user_answer=None,
    correct_answer=None,
    explanation=None,
    retry_link=None,
):
    """Persist one missed-answer event. Returns True if inserted, False if duplicate."""
    if not username or not event_key or not source or not event_at or not event_date:
        return False

    with write_transaction() as conn:
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO missed_answer_events (
                username, question_id, session_id, source, topic, subtopic,
                rule_id, rule_label, missed_rule_text, correct_rule_text,
                question_prompt, user_answer, correct_answer, explanation,
                retry_link, event_key, event_at, event_date, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(username).strip().lower(),
                question_id,
                session_id,
                source,
                topic,
                subtopic,
                rule_id,
                rule_label,
                missed_rule_text,
                correct_rule_text,
                question_prompt,
                user_answer,
                correct_answer,
                explanation,
                retry_link,
                event_key,
                event_at,
                event_date,
                now(),
            ),
        )
        return cursor.rowcount > 0


def get_missed_answer_events_for_date(username, event_date):
    """Return missed-answer rows for a user on a calendar date (YYYY-MM-DD)."""
    return fetch_all(
        """
        SELECT
            id, username, question_id, session_id, source, topic, subtopic,
            rule_id, rule_label, missed_rule_text, correct_rule_text,
            question_prompt, user_answer, correct_answer, explanation,
            retry_link, event_key, event_at, event_date, created_at
        FROM missed_answer_events
        WHERE LOWER(username) = LOWER(?)
          AND event_date = ?
        ORDER BY topic, subtopic, rule_label, event_at
        """,
        (username, event_date),
    )


def count_missed_answer_events_for_date(username, event_date):
    row = fetch_one(
        """
        SELECT COUNT(*) FROM missed_answer_events
        WHERE LOWER(username) = LOWER(?) AND event_date = ?
        """,
        (username, event_date),
    )
    return int(row[0] or 0) if row else 0


# ---------------------------------------------------------------------------
# Per-user saved MEE Question Bank answers
# ---------------------------------------------------------------------------

def get_user_question_answer(username, question_id):
    """Return the saved IRAC answer for one user/question, or None."""
    if not username or not question_id:
        return None

    row = fetch_one(
        """
        SELECT answer_text, updated_at
        FROM user_question_answers
        WHERE LOWER(username) = LOWER(?) AND question_id = ?
        LIMIT 1
        """,
        (username, int(question_id)),
    )
    if not row:
        return None

    return {
        "answer_text": row[0] or "",
        "updated_at": row[1] or "",
    }


def save_user_question_answer(username, question_id, answer_text):
    """Upsert the user's saved answer for a question. Returns updated_at."""
    normalized_username = (username or "").strip().lower()
    if not normalized_username:
        raise ValueError("username is required")

    updated_at = now()
    with write_transaction() as conn:
        conn.execute(
            """
            INSERT INTO user_question_answers (username, question_id, answer_text, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(username, question_id) DO UPDATE SET
                answer_text = excluded.answer_text,
                updated_at = excluded.updated_at
            """,
            (normalized_username, int(question_id), answer_text or "", updated_at),
        )
    return updated_at


def delete_user_question_answer(username, question_id):
    """Remove the user's saved answer for a question."""
    normalized_username = (username or "").strip().lower()
    if not normalized_username:
        return 0

    with write_transaction() as conn:
        cursor = conn.execute(
            """
            DELETE FROM user_question_answers
            WHERE LOWER(username) = LOWER(?) AND question_id = ?
            """,
            (normalized_username, int(question_id)),
        )
        return cursor.rowcount


# ---------------------------------------------------------------------------
# User notification settings
# ---------------------------------------------------------------------------

def get_user_notification_settings(username):
    """Return notification settings dict with defaults for missing rows."""
    defaults = {
        "username": (username or "").strip().lower(),
        "daily_error_sheet_enabled": True,
        "daily_error_sheet_email": None,
        "daily_error_sheet_send_hour": 21,
        "daily_error_sheet_timezone": "America/New_York",
        "send_no_misses_email": False,
    }
    if not username:
        return defaults

    row = fetch_one(
        """
        SELECT
            username,
            daily_error_sheet_enabled,
            daily_error_sheet_email,
            daily_error_sheet_send_hour,
            daily_error_sheet_timezone,
            send_no_misses_email
        FROM user_notification_settings
        WHERE LOWER(username) = LOWER(?)
        LIMIT 1
        """,
        (username,),
    )
    if not row:
        return defaults

    return {
        "username": row[0],
        "daily_error_sheet_enabled": bool(row[1]),
        "daily_error_sheet_email": row[2] or None,
        "daily_error_sheet_send_hour": int(row[3] if row[3] is not None else 21),
        "daily_error_sheet_timezone": row[4] or "America/New_York",
        "send_no_misses_email": bool(row[5]),
    }


def upsert_user_notification_settings(username, **fields):
    """Update notification settings for a user."""
    if not username:
        return False

    current = get_user_notification_settings(username)
    merged = {**current, **{k: v for k, v in fields.items() if v is not None or k in fields}}
    username_key = str(username).strip().lower()

    with write_transaction() as conn:
        conn.execute(
            """
            INSERT INTO user_notification_settings (
                username,
                daily_error_sheet_enabled,
                daily_error_sheet_email,
                daily_error_sheet_send_hour,
                daily_error_sheet_timezone,
                send_no_misses_email,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(username) DO UPDATE SET
                daily_error_sheet_enabled = excluded.daily_error_sheet_enabled,
                daily_error_sheet_email = excluded.daily_error_sheet_email,
                daily_error_sheet_send_hour = excluded.daily_error_sheet_send_hour,
                daily_error_sheet_timezone = excluded.daily_error_sheet_timezone,
                send_no_misses_email = excluded.send_no_misses_email,
                updated_at = excluded.updated_at
            """,
            (
                username_key,
                1 if merged.get("daily_error_sheet_enabled", True) else 0,
                (merged.get("daily_error_sheet_email") or "").strip() or None,
                int(merged.get("daily_error_sheet_send_hour", 21)),
                merged.get("daily_error_sheet_timezone") or "America/New_York",
                1 if merged.get("send_no_misses_email") else 0,
                now(),
            ),
        )
    return True


def list_users_for_daily_error_sheet():
    """Return users eligible for daily error sheets (enabled + email on file)."""
    rows = fetch_all(
        """
        SELECT
            u.username,
            COALESCE(NULLIF(TRIM(s.daily_error_sheet_email), ''), NULLIF(TRIM(u.email), '')) AS email,
            COALESCE(s.daily_error_sheet_send_hour, 21) AS send_hour,
            COALESCE(s.daily_error_sheet_timezone, 'America/New_York') AS timezone,
            COALESCE(s.daily_error_sheet_enabled, 1) AS enabled,
            COALESCE(s.send_no_misses_email, 0) AS send_no_misses
        FROM app_users u
        LEFT JOIN user_notification_settings s ON LOWER(s.username) = LOWER(u.username)
        WHERE COALESCE(s.daily_error_sheet_enabled, 1) = 1
        ORDER BY u.username
        """
    )
    eligible = []
    for row in rows:
        email = (row[1] or "").strip()
        if not email:
            continue
        eligible.append(
            {
                "username": row[0],
                "email": email,
                "send_hour": int(row[2] or 21),
                "timezone": row[3] or "America/New_York",
                "send_no_misses_email": bool(row[5]),
            }
        )
    return eligible


# ---------------------------------------------------------------------------
# Daily error sheet send log
# ---------------------------------------------------------------------------

def get_daily_error_sheet_sent(username, report_date):
    row = fetch_one(
        """
        SELECT username, report_date, sent_at, status, recipient_email,
               provider_message_id, error_message
        FROM daily_error_sheet_sent
        WHERE LOWER(username) = LOWER(?) AND report_date = ?
        LIMIT 1
        """,
        (username, report_date),
    )
    if not row:
        return None
    return {
        "username": row[0],
        "report_date": row[1],
        "sent_at": row[2],
        "status": row[3],
        "recipient_email": row[4],
        "provider_message_id": row[5],
        "error_message": row[6],
    }


def record_daily_error_sheet_sent(
    username,
    report_date,
    status,
    recipient_email=None,
    provider_message_id=None,
    error_message=None,
):
    """Record a daily sheet send attempt. Returns False if already recorded."""
    with write_transaction() as conn:
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO daily_error_sheet_sent (
                username, report_date, sent_at, status,
                recipient_email, provider_message_id, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(username).strip().lower(),
                report_date,
                now(),
                status,
                recipient_email,
                provider_message_id,
                error_message,
            ),
        )
        return cursor.rowcount > 0
