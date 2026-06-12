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
    # Constitutional Law — calls split incorrectly by MEE_PQ_Bank.docx import
    {
        "id": 621,
        "subject": "Constitutional Law",
        "exam_name": "July 2018",
        "question_number": "1",
        "anchor": "Is Section 11 of the Federal Drug Abuse Prevention Act",
        "call": (
            "1. Is Section 11 of the Federal Drug Abuse Prevention Act a constitutional "
            "exercise of federal power? Explain.\n"
            "2. Is Section 15 of the Federal Drug Abuse Prevention Act a constitutional "
            "exercise of federal power? Explain."
        ),
    },
    {
        "id": 617,
        "subject": "Constitutional Law",
        "exam_name": "February 2014",
        "question_number": "1",
        "anchor": "",
        "call": (
            "1. Under the Fifth Amendment as applied to the states through the "
            "Fourteenth Amendment, is the city ordinance requiring the restaurant to "
            "install floodlights an unconstitutional taking? Explain.\n"
            "2. Under the Fifth Amendment as applied to the states through the "
            "Fourteenth Amendment, is the city's requirement that the restaurant grant "
            "the city an easement as a condition for obtaining the building permit an "
            "unconstitutional taking? Explain."
        ),
    },
    {
        "id": 618,
        "subject": "Constitutional Law",
        "exam_name": "February 2015",
        "question_number": "2",
        "anchor": "Does the Act violate the Equal Protection Clause",
        "call": (
            "1. Would Congress have authority under Section Five of the Fourteenth "
            "Amendment to enact a statute barring states from establishing a maximum "
            "age for firefighters? Explain.\n"
            "2. Does the Act violate the Equal Protection Clause of the Fourteenth "
            "Amendment? Explain."
        ),
    },
    {
        "id": 613,
        "subject": "Constitutional Law",
        "exam_name": "July 2010",
        "question_number": "4",
        "anchor": "Does the First Amendment, as applied to state and local governments through the Fourteenth Amendment",
        "call": (
            "Does the First Amendment, as applied to state and local governments through "
            "the Fourteenth Amendment,\n"
            "1. Preclude Homestead's enforcement of its anti-leafleting ordinance against "
            "Chapter? Explain.\n"
            "2. Preclude Principal's denial of Church Club's request to use classroom "
            "space for its meetings? Explain.\n"
            "3. Provide grounds to vacate Father's trespass conviction? Explain."
        ),
    },
    {
        "id": 728,
        "subject": "Constitutional Law",
        "exam_name": "July 2011",
        "question_number": "7",
        "anchor": "",
        "call": (
            "1. Has Private violated the man's rights under the Equal Protection Clause "
            "of the Fourteenth Amendment? Explain.\n"
            "2. Has Public violated the man's rights under the Equal Protection Clause "
            "of the Fourteenth Amendment? Explain."
        ),
    },
    {
        "id": 554,
        "subject": "Constitutional Law",
        "exam_name": "July 2020",
        "question_number": "2",
        "anchor": "Under State X law, is the shareholder entitled",
        "call": (
            "1. Under State X law, is the shareholder entitled to inspect the requested "
            "board minutes? Explain.\n"
            "2. Under State X law, is the shareholder's proposed resolution a proper "
            "subject for submission to Retailer's shareholders for their vote? Explain.\n"
            "3. Assuming that the resolution is proper for submission for shareholder "
            "action under State X law, would the resolution (if approved) infringe "
            "Retailer's First Amendment rights? Explain."
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
        if fix.get("id"):
            row = fetch_one(
                "SELECT id, question_text FROM questions WHERE id = ?",
                (fix["id"],),
            )
        else:
            row = fetch_one(
                """
                SELECT id, question_text FROM questions
                WHERE subject = ? AND exam_name = ? AND question_number = ? AND source = ?
                """,
                (fix["subject"], fix["exam_name"], fix["question_number"], SOURCE),
            )
        if not row:
            label = fix.get("id") or f"{fix['subject']} {fix['exam_name']} Q{fix['question_number']}"
            print(f"  NOT FOUND: {label}")
            missing += 1
            continue

        qid, question_text = row
        new_qt = question_text

        # Trim the embedded call out of the fact pattern (apostrophe/quote-insensitive).
        anchor = fix.get("anchor") or ""
        if anchor:
            idx = normalize(question_text or "").find(normalize(anchor))
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
