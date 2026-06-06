# -*- coding: utf-8 -*-

import argparse
import re
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path("mee_reflex.db")


SUBJECT_TRAPS = {
    "business associations": [
        "Do not confuse actual authority with apparent authority.",
        "Actual authority = principal's manifestations to the agent.",
        "Apparent authority = principal's manifestations to the third party.",
        "For partnership, profit sharing creates a presumption but exceptions may apply.",
        "Separate entity liability from personal liability.",
        "Separate director, officer, and shareholder capacities.",
        "Separate duty of care from duty of loyalty.",
    ],
    "agency": [
        "Do not confuse actual authority with apparent authority.",
        "Actual authority depends on the principal's manifestations to the agent.",
        "Apparent authority depends on the principal's manifestations to the third party.",
        "Separate entity liability from personal liability.",
    ],
    "partnership": [
        "For partnership, profit sharing creates a presumption but exceptions may apply.",
        "Separate entity liability from personal liability.",
        "Separate partner authority from partner personal liability.",
    ],
    "civil procedure": [
        "Do not confuse subject-matter jurisdiction with personal jurisdiction.",
        "Diversity is measured at filing.",
        "Citizenship is domicile for individuals; corporations have dual citizenship.",
        "Supplemental jurisdiction has special plaintiff restrictions in diversity cases.",
        "Summary judgment requires no genuine dispute of material fact.",
        "Erie: federal procedural law, state substantive law.",
    ],
    "constitutional law": [
        "Identify state action first if private conduct is involved.",
        "For speech, identify the forum before choosing the test.",
        "Do not confuse content-based with content-neutral regulation.",
        "Government safety purpose does not automatically make speech regulation content-neutral.",
        "Strict scrutiny applies to content-based speech regulations unless unprotected speech.",
        "Separate Equal Protection, procedural due process, and substantive due process.",
    ],
    "contracts": [
        "Start with governing law: UCC goods versus common law services.",
        "Do not analyze breach before formation.",
        "Statute of Frauds means unenforceability unless an exception applies.",
        "Under UCC, check merchant confirmatory memo, specially manufactured goods, admission, and part performance.",
        "Parol evidence applies only after determining integration.",
        "Common-law modifications usually require consideration.",
    ],
    "torts": [
        "Negligence per se requires protected class and protected type of harm.",
        "Statutory violation does not automatically establish the entire negligence claim.",
        "Separate actual cause from proximate cause.",
        "Do not reach comparative fault before causation.",
        "False imprisonment requires intent, confinement, and awareness or harm.",
        "IIED requires extreme and outrageous conduct.",
        "For products, separate manufacturing defect, design defect, and warning defect.",
    ],
    "criminal law": [
        "Separate substantive crime from constitutional procedure.",
        "Fourth Amendment: government action, search/seizure, warrant, exception.",
        "Miranda requires custody plus interrogation.",
        "Sixth Amendment right to counsel is offense-specific and attaches after formal charge.",
        "Attempt requires specific intent plus substantial step.",
    ],
    "evidence": [
        "Do not jump to hearsay before asking purpose.",
        "If not offered for truth, it is not hearsay.",
        "If hearsay, check exemption or exception.",
        "Relevance is the threshold issue.",
        "Impeachment is different from substantive admissibility.",
    ],
    "real property": [
        "Recording acts require classifying the statute: race, notice, or race-notice.",
        "Do not confuse notice with recording.",
        "Easement appurtenant versus in gross matters.",
        "Assignment versus sublease matters.",
        "Adverse possession requires every element for the statutory period.",
    ],
    "family law": [
        "Best interests of the child controls custody.",
        "Premarital agreement enforceability is separate from child custody/support.",
        "Classify marital vs separate property before division.",
        "Fault usually does not control custody unless it affects the child.",
    ],
    "trusts": [
        "Separate will validity, trust validity, and distribution.",
        "Capacity and undue influence are different issues.",
        "Revocation requires compliance with formalities.",
        "Separate trustee duty of loyalty, care, and impartiality.",
        "Anti-lapse requires beneficiary relationship and survival.",
    ],
    "secured transactions": [
        "Attachment, perfection, and priority are separate.",
        "A financing statement alone does not create attachment.",
        "PMSI priority has strict timing rules.",
        "Buyer in ordinary course rules require seller in business of selling goods of that kind.",
        "Proceeds and after-acquired collateral require separate analysis.",
    ],
    "conflict": [
        "Ask which law applies before deciding who wins.",
        "In federal diversity, apply forum state choice-of-law rules under Klaxon.",
        "Do not confuse procedural and substantive issues.",
    ],
}


UNIVERSAL_TRAPS = [
    "Separate each call of the question; do not answer the whole essay as one blob.",
    "Do not assume facts not given.",
    "Do not jump to the conclusion before identifying the governing relationship or threshold issue.",
    "Use the exact procedural posture if the call asks about a motion, jurisdiction, admissibility, or remedy.",
    "If the analysis turns on a standard of review, name the standard before applying facts.",
]


def normalize(text):
    return re.sub(r"\s+", " ", str(text or "")).strip()


def add_unique(traps, trap):
    trap = normalize(trap).strip(" -")
    if not trap:
        return
    key = trap.lower()
    if key not in {t.lower() for t in traps}:
        traps.append(trap)


def subject_trap_candidates(subject):
    subject_l = normalize(subject).lower()
    candidates = []
    for key, traps in SUBJECT_TRAPS.items():
        if key in subject_l or subject_l in key:
            candidates.extend(traps)
    return candidates


def generate_traps(subject, call_of_question, tested_issues, rules, trigger_facts, model_points):
    subject_l = normalize(subject).lower()
    call_l = normalize(call_of_question).lower()
    issue_l = normalize(tested_issues).lower()
    rules_l = normalize(rules).lower()
    facts_l = normalize(trigger_facts).lower()
    model_l = normalize(model_points).lower()
    blob = " ".join([subject_l, call_l, issue_l, rules_l, facts_l, model_l])
    focused_blob = " ".join([subject_l, call_l, issue_l, rules_l, facts_l])

    traps = []

    if re.search(r"\b\d+\.", call_l) or "assuming" in call_l:
        add_unique(traps, UNIVERSAL_TRAPS[0])
    if "assuming" in call_l:
        add_unique(traps, "Respect the assumption in the call; do not re-argue the assumed issue.")

    for trap in subject_trap_candidates(subject):
        if len(traps) >= 4:
            break
        add_unique(traps, trap)

    keyword_traps = [
        (["actual authority", "apparent authority"], "business associations agency partnership", "Do not confuse actual authority with apparent authority."),
        (["subject-matter jurisdiction", "personal jurisdiction"], "civil procedure", "Do not confuse subject-matter jurisdiction with personal jurisdiction."),
        (["diversity"], "civil procedure", "Diversity is measured at filing and requires complete diversity plus amount in controversy."),
        (["summary judgment"], "civil procedure torts", "Summary judgment requires no genuine dispute of material fact; draw reasonable inferences against the movant."),
        (["forum", "speech", "first amendment"], "constitutional law", "For speech, identify the forum before choosing the test."),
        (["content-based", "content neutral", "content-neutral"], "constitutional law", "Do not confuse content-based with content-neutral regulation."),
        (["statute of frauds"], "contracts", "Statute of Frauds means unenforceability unless an exception applies, not automatic nonexistence of a contract."),
        (["negligence per se"], "torts", "Negligence per se requires protected class and protected type of harm."),
        (["false imprisonment"], "torts", "False imprisonment requires intent, confinement, and awareness or harm."),
        (["proximate cause"], "torts", "Separate actual cause from proximate cause."),
        (["hearsay"], "evidence", "Do not jump to hearsay before asking the purpose for which the statement is offered."),
        (["recording", "race-notice"], "real property", "Recording acts require classifying the statute before applying notice facts."),
        (["erie"], "civil procedure", "Erie means federal procedural law and state substantive law."),
    ]

    for keywords, subject_gate, trap in keyword_traps:
        gate_terms = subject_gate.split()
        subject_matches = any(term in subject_l for term in gate_terms)
        if subject_matches and any(keyword in focused_blob for keyword in keywords):
            add_unique(traps, trap)

    if any(word in model_l for word in ["however", "although", "on the other hand"]):
        add_unique(traps, "Watch the counterargument; the model analysis signals a fact or doctrine that cuts the other way.")
    if any(word in f"{issue_l} {model_l}" for word in ["threshold", "must first"]) or re.search(r"\bfirst\b", model_l):
        add_unique(traps, "Identify the threshold issue before applying downstream rules.")
    if "notwithstanding" in model_l or "unless" in model_l:
        add_unique(traps, "Look for the exception; the rule may change when the exception is triggered.")

    for trap in UNIVERSAL_TRAPS:
        if len(traps) >= 6:
            break
        if any(word in blob for word in ["motion", "jurisdiction", "admissib", "remedy", "standard"]):
            add_unique(traps, trap)

    while len(traps) < 3:
        add_unique(traps, UNIVERSAL_TRAPS[len(traps) % len(UNIVERSAL_TRAPS)])

    return "\n".join(f"- Trap: {trap}" for trap in traps[:6])


def needs_traps(value):
    return value is None or len(normalize(value)) < 30


def backup_database():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = DB_PATH.with_name(f"mee_reflex_backup_before_traps_{timestamp}.db")
    shutil.copy2(DB_PATH, backup_path)
    return backup_path


def main():
    parser = argparse.ArgumentParser(description="Populate concise trap warnings for MEE Reflex Trainer questions.")
    parser.add_argument("--dry-run", action="store_true", help="Preview proposed trap warnings without updating the database.")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of weak-trap questions processed.")
    args = parser.parse_args()

    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    backup_path = None if args.dry_run else backup_database()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM questions")
    total_questions = cur.fetchone()[0]

    query = """
        SELECT id, exam_name, question_number, subject, call_of_question,
               tested_issues, rules, trigger_facts, model_points, traps
        FROM questions
        WHERE traps IS NULL OR TRIM(traps) = '' OR LENGTH(TRIM(traps)) < 30
        ORDER BY id
    """
    params = []
    if args.limit:
        query += " LIMIT ?"
        params.append(args.limit)

    rows = cur.execute(query, params).fetchall()
    populated = 0
    skipped = 0

    for row in rows:
        traps = generate_traps(
            row["subject"],
            row["call_of_question"],
            row["tested_issues"],
            row["rules"],
            row["trigger_facts"],
            row["model_points"],
        )

        if not traps:
            skipped += 1
            continue

        populated += 1

        if args.dry_run:
            print("=" * 80)
            print(f"{row['id']} | {row['exam_name']} Q{row['question_number']} | {row['subject']}")
            print(traps)
        else:
            cur.execute("UPDATE questions SET traps = ? WHERE id = ?", (traps, row["id"]))

    if args.dry_run:
        backup_name = "not created in dry run"
    else:
        conn.commit()
        backup_name = str(backup_path)

    conn.close()

    print("\nSummary")
    print(f"total questions checked: {total_questions}")
    print(f"weak trap rows processed: {len(rows)}")
    print(f"traps populated: {populated}")
    print(f"traps skipped: {skipped}")
    print(f"backup filename: {backup_name}")


if __name__ == "__main__":
    main()
