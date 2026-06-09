"""One-off, idempotent fixes for questions whose call was embedded in unusual
text and could not be auto-isolated by import_questions_docx.py.

For each listed question this sets a clean, numbered call_of_question and trims
the embedded call out of question_text so the fact pattern no longer repeats it.

Safe to re-run: it simply re-sets the same values.

Usage:
    python scripts/fix_question_calls.py
"""

import _bootstrap  # noqa: F401

from database import fetch_one, write_transaction

SOURCE = "MEE Question Bank (my import)"

FIXES = [
    {
        "subject": "Corporations & LLCs",
        "exam_name": "July 2010",
        "question_number": "9",
        "anchor": "Your law firm represents X Corporation",
        "call": (
            "Your law firm represents X Corporation. You have been asked to advise the "
            "firm's senior partner on whether the proposal received sufficient votes to "
            "be approved. Explain your conclusion."
        ),
    },
    {
        "subject": "Corporations & LLCs",
        "exam_name": "July 2021",
        "question_number": "2",
        "anchor": "Can Ethan block the merger",
        "call": (
            "1. Can Ethan block the merger of Winery Inc. into Organic Wines Corp. by "
            "voting against it? Explain.\n"
            "2. If Winery Inc. merges into Organic Wines Corp., does Ethan have a right to "
            "demand that he receive payment in cash (instead of receiving shares in Organic "
            "Wines Corp.) equal to the fair value of his shares in Winery Inc.? Explain.\n"
            "3. Assume that Ethan becomes a shareholder of Organic Wines Corp. Could Ethan "
            "successfully sue the Organic Wines Corp. directors in State A for promoting "
            "sustainable and organic practices at the expense of maximizing shareholder "
            "profits? Explain. Do not discuss whether that suit would have to be direct or "
            "derivative."
        ),
    },
    {
        "subject": "Contracts / Sales",
        "exam_name": "July 2022",
        "question_number": "2",
        "anchor": "In litigation between the parties",
        "call": (
            "Assume for all questions that, in the jurisdiction whose law governs the "
            "dispute, the sale of an ongoing business is governed by the common law of "
            "contracts, not Article 2 of the Uniform Commercial Code. In litigation "
            "between the parties:\n"
            "1. Is Seller's and Buyer's oral agreement that Buyer would use Seller's "
            "picture on red wine labels enforceable even though it was not included in the "
            "written agreement? Explain. (Do not discuss any potential statute of frauds "
            "issues.)\n"
            "2. Could Seller introduce evidence of the negotiations about what would "
            "constitute a fair share of the winery's first-year profits to help explain "
            "the meaning of that term? Explain.\n"
            "3. Assuming that Buyer is not in breach of any of his obligations under the "
            "purchase agreement, would Buyer prevail on a claim that Seller breached her "
            "obligations under the agreement by opening her new winery? Explain."
        ),
    },
    {
        "subject": "Criminal Law & Procedure",
        "exam_name": "July 2021",
        "question_number": "4",
        "anchor": "Did the officer",
        "call": (
            "1. Did the officer's warrantless seizure of the man and warrantless seizure "
            "of the purse in the man's home violate the man's Fourth Amendment rights? "
            "Explain.\n"
            "2. Would the trial court violate the man's constitutional due process rights "
            "by admitting testimony that reveals the girl's on-the-scene identification of "
            "the man or by allowing her to identify him in court? Explain.\n"
            "Do not discuss any confrontation clause issues."
        ),
    },
    {
        "subject": "Evidence",
        "exam_name": "July 2017",
        "question_number": "5",
        "anchor": "Under the Miranda doctrine and the rules of evidence",
        "call": (
            "Under the Miranda doctrine and the rules of evidence, explain how the court "
            "should rule on the admissibility of the following evidence:\n"
            "1. Testimony from the woman, offered by the defense, repeating the man's "
            "statement, \"I promise you'll be happy if you take me back, but very unhappy "
            "if you do not.\"\n"
            "2. Testimony from the police officer, offered by the prosecution, repeating "
            "the woman's statement, \"I have a can of pepper spray in my purse. Is that a "
            "weapon?\"\n"
            "3. Testimony from the police officer, offered by the prosecution, repeating "
            "the custodian's statement, \"I didn't see the shooting, but I heard some "
            "noises in the hall around 10 and then a loud bang and screaming.\""
        ),
    },
    {
        "subject": "Real Property",
        "exam_name": "February 2017",
        "question_number": "6",
        "anchor": "Identify and evaluate the arguments",
        "call": (
            "Identify and evaluate the arguments available to the landlord and the tenant "
            "regarding the landlord's claim to 17 months of unpaid rent."
        ),
    },
]


def normalize(text):
    return (
        text.replace("’", "'").replace("‘", "'")
        .replace("“", '"').replace("”", '"')
    )


def main():
    updated = 0
    trimmed = 0
    missing = 0

    for fix in FIXES:
        row = fetch_one(
            """
            SELECT id, question_text FROM questions
            WHERE subject = ? AND exam_name = ? AND question_number = ? AND source = ?
            """,
            (fix["subject"], fix["exam_name"], fix["question_number"], SOURCE),
        )
        if not row:
            print(f"  NOT FOUND: {fix['subject']} {fix['exam_name']} Q{fix['question_number']}")
            missing += 1
            continue

        qid, question_text = row
        new_qt = question_text

        # Trim the embedded call out of the fact pattern (apostrophe/quote-insensitive).
        idx = normalize(question_text or "").find(normalize(fix["anchor"]))
        if idx != -1:
            new_qt = question_text[:idx].rstrip()
            trimmed += 1

        with write_transaction() as conn:
            conn.execute(
                "UPDATE questions SET call_of_question = ?, question_text = ? WHERE id = ?",
                (fix["call"], new_qt, qid),
            )
        updated += 1
        print(f"  fixed: {fix['subject']} {fix['exam_name']} Q{fix['question_number']}")

    print(f"Updated {updated}, trimmed fact pattern on {trimmed}, missing {missing}.")


if __name__ == "__main__":
    main()
