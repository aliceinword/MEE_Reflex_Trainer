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
    conn.execute(f"PRAGMA busy_timeout = {SQLITE_BUSY_TIMEOUT_MS}")
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
    try:
        with closing(_connect_sqlite(db_path)) as conn:
            row = conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()
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

    with _connect_sqlite(db_path, use_wal=True) as conn:
        conn.execute("ATTACH DATABASE ? AS seed", (str(seed_path),))
        try:
            for table in seed_tables:
                conn.execute(f'DELETE FROM "{table}"')
                conn.execute(f'INSERT INTO "{table}" SELECT * FROM seed."{table}"')
            conn.commit()
        finally:
            conn.execute("DETACH DATABASE seed")


def _ensure_database_file():
    db_path = Path(DB_NAME)
    legacy_path = Path(LEGACY_DB_NAME)

    if not legacy_path.exists():
        return

    if DB_NAME != DEFAULT_DB_NAME:
        return

    if not db_path.exists():
        shutil.copy2(legacy_path, db_path)
        return

    _seed_missing_public_content(db_path, legacy_path)


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
def write_transaction():
    """Open a write transaction and always close the connection."""
    conn = get_connection()
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
    placeholders = ",".join("?" for _ in ids)
    with write_transaction() as conn:
        cur = conn.execute(
            f"DELETE FROM mbe_cards WHERE id IN ({placeholders})",
            ids,
        )
        return int(cur.rowcount or 0)


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
    return fetch_all(
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
    )


def count_mbe_cards():
    row = fetch_one("SELECT COUNT(*) FROM mbe_cards")
    return int(row[0] or 0) if row else 0


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


def save_mbe_practice_stats(username, stats_blob):
    """Persist the MBE trap-trainer practice blob for a user."""
    if not username or not isinstance(stats_blob, dict):
        return False

    import json

    payload = json.dumps(stats_blob, ensure_ascii=False)
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

    return fetch_all(query, params)


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

    return fetch_all(query, params)


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


def get_questions(active_only=False, subject=None, status=None, search=None, due_only=False):
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
            now(),
        ),
    )


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
