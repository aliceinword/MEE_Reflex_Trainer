import shutil
import sqlite3
from datetime import datetime
from pathlib import Path


DB_NAME = "mee_reflex.db"
STUDICATA_SOURCE = "Studicata_MEE_PQ_Bank_July_2025.pdf"


def main():
    db_path = Path(DB_NAME)

    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = Path(f"mee_reflex_backup_{timestamp}.db")
    shutil.copy2(db_path, backup_path)

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    c.execute(
        """
        SELECT COUNT(*)
        FROM attempts
        WHERE question_id IN (
            SELECT id FROM questions WHERE source = ?
        )
        """,
        (STUDICATA_SOURCE,),
    )
    attempts_to_delete = c.fetchone()[0]

    c.execute(
        """
        SELECT COUNT(*)
        FROM questions
        WHERE source = ?
        """,
        (STUDICATA_SOURCE,),
    )
    questions_to_delete = c.fetchone()[0]

    c.execute(
        """
        DELETE FROM attempts
        WHERE question_id IN (
            SELECT id FROM questions WHERE source = ?
        )
        """,
        (STUDICATA_SOURCE,),
    )

    c.execute(
        """
        DELETE FROM questions
        WHERE source = ?
        """,
        (STUDICATA_SOURCE,),
    )

    conn.commit()
    conn.close()

    print(f"Backed up database to: {backup_path}")
    print(f"Deleted attempts linked to Studicata questions: {attempts_to_delete}")
    print(f"Deleted Studicata questions: {questions_to_delete}")
    print("No manually added questions, Attack Outline rules, or Plug & Play templates were deleted.")


if __name__ == "__main__":
    main()
