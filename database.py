import sqlite3
from datetime import datetime, timedelta

DB_NAME = "mee_reflex.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def init_db():
    conn = get_connection()
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

    c.execute("PRAGMA table_info(questions)")
    existing_question_columns = {row[1] for row in c.fetchall()}

    for column_name, ddl in question_extra_columns.items():
        if column_name not in existing_question_columns:
            c.execute(f"ALTER TABLE questions ADD COLUMN {column_name} {ddl}")

    # Add new attempt columns safely if the old database already exists.
    attempt_extra_columns = {
        "minutes_spent": "INTEGER DEFAULT 0"
    }

    c.execute("PRAGMA table_info(attempts)")
    existing_attempt_columns = {row[1] for row in c.fetchall()}

    for column_name, ddl in attempt_extra_columns.items():
        if column_name not in existing_attempt_columns:
            c.execute(f"ALTER TABLE attempts ADD COLUMN {column_name} {ddl}")

    conn.commit()
    conn.close()


def add_outline_rule(subject, rule_title, appearance_rate, rule_text, pdf_page, printed_page, source_file):
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        SELECT id
        FROM outline_rules
        WHERE source_file = ?
        AND subject = ?
        AND rule_title = ?
        AND (pdf_page = ? OR (pdf_page IS NULL AND ? IS NULL))
        LIMIT 1
    """, (source_file, subject, rule_title, pdf_page, pdf_page))

    existing = c.fetchone()

    if existing:
        conn.close()
        return False

    c.execute("""
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

    conn.commit()
    conn.close()
    return True


def get_outline_rules(subject=None):
    conn = get_connection()
    c = conn.cursor()

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

    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return rows


def search_outline_rules(query, subject=None, limit=5):
    conn = get_connection()
    c = conn.cursor()

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

    c.execute(sql, params)
    rows = c.fetchall()
    conn.close()
    return rows


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
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        SELECT id
        FROM plug_play_templates
        WHERE source_file = ?
        AND subject = ?
        AND module_title = ?
        AND pdf_page = ?
        LIMIT 1
    """, (source_file, subject, module_title, pdf_page))

    existing = c.fetchone()

    if existing:
        conn.close()
        return False

    c.execute("""
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

    conn.commit()
    conn.close()
    return True


def get_plug_play_templates(subject=None):
    conn = get_connection()
    c = conn.cursor()

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

    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return rows


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


def _unused_sql_search_plug_play_templates(query, subject=None, limit=5):
    conn = get_connection()
    c = conn.cursor()

    search_terms = [
        term.strip()
        for term in str(query or "").replace(";", " ").replace(",", " ").split()
        if len(term.strip()) >= 2
    ]

    sql = """
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

    if search_terms:
        sql += " AND ("
        term_clauses = []

        for term in search_terms:
            term_clauses.append("""
                (
                    module_title LIKE ?
                    OR scenario_trigger LIKE ?
                    OR issue_statement LIKE ?
                    OR rule_text LIKE ?
                    OR analysis_template LIKE ?
                    OR subject LIKE ?
                )
            """)
            like = f"%{term}%"
            params.extend([like, like, like, like, like, like])

        sql += " OR ".join(term_clauses)
        sql += ")"

    sql += """
        ORDER BY
            CASE WHEN ? IS NOT NULL AND subject = ? THEN 0 ELSE 1 END,
            subject,
            pdf_page,
            module_title
        LIMIT ?
    """
    params.extend([subject, subject, limit])

    c.execute(sql, params)
    rows = c.fetchall()
    conn.close()
    return rows


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
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
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

    conn.commit()
    conn.close()


def get_questions(active_only=False, subject=None, status=None, search=None, due_only=False):
    conn = get_connection()
    c = conn.cursor()

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

    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return rows


def get_question_by_id(question_id):
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
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

    row = c.fetchone()
    conn.close()
    return row


def get_subjects():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        SELECT DISTINCT subject
        FROM questions
        WHERE subject IS NOT NULL AND subject != ''
        ORDER BY subject
    """)

    rows = [row[0] for row in c.fetchall()]
    conn.close()
    return rows


def get_statuses():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        SELECT DISTINCT july_2026_status
        FROM questions
        WHERE july_2026_status IS NOT NULL AND july_2026_status != ''
        ORDER BY july_2026_status
    """)

    rows = [row[0] for row in c.fetchall()]
    conn.close()
    return rows


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
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
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
        now()
    ))

    next_review_at = review_date_from_score(self_score)

    c.execute("""
        UPDATE questions
        SET last_practiced_at = ?, next_review_at = ?
        WHERE id = ?
    """, (now(), next_review_at, question_id))

    conn.commit()
    conn.close()


def get_attempts(limit=100):
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        SELECT
            attempts.id,
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

    rows = c.fetchall()
    conn.close()
    return rows


def get_dashboard_stats():
    conn = get_connection()
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

    today = datetime.now().strftime("%Y-%m-%d")
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

    conn.close()

    return {
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
