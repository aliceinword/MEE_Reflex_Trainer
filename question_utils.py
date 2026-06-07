# -*- coding: utf-8 -*-
"""Question row parsing and primitive value helpers."""

from text_cleanup import normalize_extracted_text
from text_rendering import recover_call_text_from_model


def parse_optional_int(value, default=None):
    try:
        if value is None:
            return default
        value = str(value).strip()
        if value == "":
            return default
        return int(float(value))
    except ValueError:
        return default


def parse_bool(value):
    if isinstance(value, bool):
        return value

    value = str(value).strip().lower()

    if value in ["0", "false", "no", "n", "inactive"]:
        return False

    return True


def unpack_question(q):
    model_points = normalize_extracted_text(q[10])
    call_of_question = recover_call_text_from_model(q[5], model_points)

    return {
        "id": q[0],
        "exam_name": q[1],
        "question_number": q[2],
        "subject": q[3],
        "question_text": normalize_extracted_text(q[4]),
        "call_of_question": call_of_question,
        "tested_issues": normalize_extracted_text(q[6]),
        "rules": normalize_extracted_text(q[7]),
        "trigger_facts": normalize_extracted_text(q[8]),
        "traps": normalize_extracted_text(q[9]),
        "model_points": model_points,
        "active_for_july_2026": q[11],
        "created_at": q[12],
        "exam_year": q[13],
        "exam_season": q[14],
        "secondary_subjects": q[15],
        "july_2026_status": q[16],
        "priority": q[17],
        "source": q[18],
        "last_practiced_at": q[19],
        "next_review_at": q[20],
    }
