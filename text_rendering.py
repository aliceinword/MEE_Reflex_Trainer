# -*- coding: utf-8 -*-
"""Shared long-text rendering helpers for the MEE trainer app."""

import re
from contextlib import contextmanager
from html import escape

import streamlit as st

from text_cleanup import normalize_extracted_text


def render_text_info(text):
    """Render an informational text-rendering notice from one place."""
    st.info(text)


def render_text_warning(text):
    """Render a warning text-rendering notice from one place."""
    st.warning(text)


@contextmanager
def render_text_expander(label, *, expanded=False):
    """Open a text-rendering expander without importing the app UI layer."""
    with st.expander(label, expanded=expanded):
        yield


def escape_display_text(value):
    """Escape text for safe HTML display while preserving literal dollar signs."""
    return escape(str(value or "")).replace("$", "&#36;")


def normalize_long_text(text):
    """Normalize imported legal text before paragraph splitting/rendering."""
    if not text:
        return ""

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    paragraph_marker = "ZXQPARABREAKZXQ"
    text = re.sub(r"\n\s*\n+", f"\n{paragraph_marker}\n", str(text))
    text = normalize_extracted_text(text)
    text = text.replace(paragraph_marker, "\n\n")
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def split_paragraphs(text):
    """Split text into readable paragraphs, including implicit sentence breaks."""
    text = normalize_long_text(text)
    if not text:
        return []

    text = re.sub(r"(?<=[a-z0-9][.!?])\s*(?=[A-Z])", "\n\n", text)
    return [part.strip() for part in re.split(r"\n+", text) if part.strip()]


def make_readable_legal_text(text):
    """Add stable paragraph breaks around common legal-analysis labels."""
    text = normalize_long_text(text)
    if not text:
        return "No text available."

    text = re.sub(r'\.["”](?=[A-Z])', '.\n\n"', text)
    text = re.sub(r'([a-zA-Z])["”]([a-zA-Z])', r'\1 "\2', text)
    text = re.sub(r"§\s+(\d+)\.\s+(\d+)", r"§ \1.\2", text)
    text = re.sub(r"\bId\.\s+§\s+(\d+)\.\s+(\d+)", r"Id. § \1.\2", text)

    text = re.sub(
        r"\b(Point One|Point Two|Point Three|Point Four|Point Five|Point Six|Point Seven|Point Eight|Point Nine)"
        r"\s*(\([^)]*\))?",
        lambda m: f"\n\n{m.group(1)} {m.group(2) or ''}\n",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"(?im)^\s*DISCUSSION\s*$", "\n\nDiscussion:\n", text)
    text = re.sub(r"(?im)^\s*ANALYSIS\s*$", "\n\nAnalysis:\n", text)
    text = re.sub(r"(?im)^\s*Summary\s*$", "\n\nSummary:\n", text)
    text = re.sub(
        r"\b(Legal Problems:|Short answer:|Rules?:|Rule\(s\):|"
        r"Fact-based analysis:|Conclusion:)\b",
        r"\n\n\1\n",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s+(\(\d+\))\s+", r"\n\n\1 ", text)
    text = re.sub(r"\s+(\d+\.)\s+", r"\n\n\1 ", text)
    text = re.sub(r"\s+([a-z]\.)\s+", r"\n\n\1 ", text)

    for word in (
        "Here,",
        "However,",
        "Therefore,",
        "Thus,",
        "Because",
        "On the other hand,",
        "By contrast,",
        "Moreover,",
        "In addition,",
        "Nevertheless,",
        "The issue is",
        "The rule is",
    ):
        text = re.sub(rf"\s+({re.escape(word)})", r"\n\n\1", text)

    return re.sub(r"\n{3,}", "\n\n", text).strip()


def render_text_block(title, text, class_name="readable", compact=False, empty_message="No text available."):
    """Render a full-width styled text block with paragraph spacing."""
    paragraphs = split_paragraphs(text) or [empty_message]
    paragraph_margin = "0.65em" if class_name == "question" else "1.2em"
    body = "".join(
        f'<p style="margin-bottom:{paragraph_margin}">{escape_display_text(paragraph)}</p>'
        for paragraph in paragraphs
    )

    if class_name == "prompt":
        st.markdown(
            (
                '<div style="'
                'font-size: 1.05rem;'
                'line-height: 1.9;'
                'color: #1a1a2e;'
                'background: #f8f9fa;'
                'padding: 1.2rem 1.5rem;'
                'border-radius: 8px;'
                'border-left: 4px solid #4a90d9;'
                'white-space: pre-wrap;'
                'width: 100%;'
                '">'
                f"{body}"
                "</div>"
            ),
            unsafe_allow_html=True,
        )
        return

    render_html_box(title, body, class_name, compact=compact)


def render_html_box(title, body_html, class_name, compact=False, body_class=None):
    """Render a shared full-width styled box shell around escaped/controlled HTML."""
    compact_class = " compact" if compact else ""
    body_class = body_class or f"{class_name}-text"
    st.markdown(
        (
            f'<div class="{class_name}-box{compact_class}">'
            f'<div class="{class_name}-title">{escape_display_text(title)}</div>'
            f'<div class="{body_class}">{body_html}</div>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_readable_text(title, text, compact=False):
    render_text_block(title, make_readable_legal_text(text), "readable", compact=compact)


def render_prompt(text):
    render_text_block("Prompt", text, "prompt", empty_message="No prompt available.")


def render_answer(title, text, compact=False):
    render_text_block(title, make_readable_legal_text(text), "readable", compact=compact)


def render_rule_outline(title, text, compact=False):
    render_text_block(title, make_readable_legal_text(text), "readable", compact=compact)


def clean_sample_answer_text(text):
    """Clean imported sample/model answers without truncating content."""
    text = normalize_long_text(text)
    if not text:
        return ""

    text = re.sub(
        r"(?is)^Question summary:\s*.*?(?=Condensed sample-answer path:|Point\s+(?:One|Two|Three|Four|Five|Six)|\d+\.\s+Point|\Z)",
        "",
        text,
    )
    text = re.sub(r"(?i)Condensed sample-answer path:\s*", "Sample Answer:\n", text)
    text = re.sub(r"(?i)\bLegal\s+Problems\s*:", "Legal Problems:", text)
    text = re.sub(r"(?im)^\s*DISCUSSION\s*$", "Discussion:", text)
    text = re.sub(r"(?i)(?<![A-Za-z])Summary\s+(?=[A-Z])", "Summary:\n", text)
    text = re.sub(r"(?i)\bFact-based\s*\n*\s*analysis\s*\n*\s*:", "Fact-based analysis:", text)
    text = re.sub(r"(?i)\bRule\s*\(\s*s\s*\)\s*:", "Rule(s):", text)
    text = re.sub(r"(?i)\bShort\s+answer\s*:", "Short answer:", text)
    text = re.sub(r"(?i)\bConclusion\s*:", "Conclusion:", text)
    text = re.sub(r"\b([a-z])\s+Short answer:", "Short answer:", text)
    text = re.sub(r"\b([a-z])\s+Rule\(s\):", "Rule(s):", text)
    text = re.sub(
        r"(?i)(?:^|\s)(\d+\.\s*)?(Point\s+(?:One|Two|Three|Four|Five|Six|Seven|Eight|Nine)(?:\s*\([^)]*\))?)\s+",
        r"\n\n\2\n",
        text,
    )
    text = re.sub(
        r"(?i)\s+(Legal Problems:|Summary:|Discussion:|Short answer:|Rule\(s\):|Rules:|Fact-based analysis:|Conclusion:)",
        r"\n\n\1",
        text,
    )

    lines = []
    for raw_line in text.splitlines():
        line = re.sub(r"[ \t]+", " ", raw_line).strip()
        if not line:
            lines.append("")
            continue
        if line in {"-", "*"}:
            continue
        line = re.sub(r"^[-*]\s*", "", line).strip()
        line = re.sub(r"\s+([,.;:!?])", r"\1", line)
        line = re.sub(r"([.!?])([A-Z])", r"\1 \2", line)
        if line:
            lines.append(line)

    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def render_sample_answer_text(title, text):
    formatted = clean_sample_answer_text(text)
    if not formatted:
        render_text_info("No sample answer/model analysis available for this question yet.")
        return

    label_classes = {
        "Sample Answer:": "sample-label-main",
        "Legal Problems:": "sample-label-main",
        "Summary:": "sample-label-main",
        "Discussion:": "sample-label-main",
        "Short answer:": "sample-label",
        "Rule(s):": "sample-label",
        "Rules:": "sample-label",
        "Fact-based analysis:": "sample-label",
        "Conclusion:": "sample-label",
    }
    blocks = []

    for paragraph in [p.strip() for p in formatted.split("\n\n") if p.strip()]:
        if re.fullmatch(
            r"Point\s+(One|Two|Three|Four|Five|Six|Seven|Eight|Nine)(\s*\([^)]*\))?",
            paragraph,
            flags=re.IGNORECASE,
        ):
            blocks.append(f'<div class="sample-point">{escape_display_text(paragraph)}</div>')
            continue

        label_match = re.match(
            r"^(Sample Answer:|Legal Problems:|Summary:|Discussion:|Short answer:|Rule\(s\):|Rules:|Fact-based analysis:|Conclusion:)\s*(.*)$",
            paragraph,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if label_match:
            label = label_match.group(1)
            body = label_match.group(2).strip()
            canonical = next((known for known in label_classes if known.lower() == label.lower()), label)
            blocks.append(f'<div class="{label_classes.get(canonical, "sample-label")}">{escape_display_text(canonical)}</div>')
            if body:
                body_html = "<br>".join(escape_display_text(line) for line in body.splitlines() if line.strip())
                blocks.append(f"<p>{body_html}</p>")
            continue

        paragraph_html = "<br>".join(escape_display_text(line) for line in paragraph.splitlines() if line.strip())
        blocks.append(f"<p>{paragraph_html}</p>")

    render_html_box(title, "".join(blocks), "sample-answer")


def extract_question_sentences_for_call(text):
    if not text:
        return []

    text = normalize_extracted_text(str(text))
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\s+", " ", text)
    questions = []

    for match in re.finditer(r"([^?]+?\?)", text):
        question = re.sub(r"\s+", " ", match.group(1)).strip()
        question = re.sub(r"^\d+\s*[\).\s-]*", "", question).strip()
        question = re.sub(r"^\(?[a-z]\)?[.)-]\s*", "", question).strip()
        if question and question[0].islower():
            question = question[0].upper() + question[1:]

        if len(question) >= 18 and question not in questions:
            questions.append(question)

    return questions


def extract_model_legal_problem_questions(model_text):
    if not model_text:
        return []

    text = normalize_extracted_text(str(model_text))
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    match = re.search(
        r"Legal\s+Problems\s*:\s*(.*?)(?=\n\s*(?:Summary\b|Discussion\b|Point\s+One\b|ANALYSIS\b)|\Z)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if not match:
        return []

    return extract_question_sentences_for_call(match.group(1))


def model_point_labels(model_text, limit):
    number_words = {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
    }
    labels = []
    pattern = re.compile(
        r"Point\s+(One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten|\d+)\s*(?:\(([a-z])\))?",
        flags=re.IGNORECASE,
    )

    for match in pattern.finditer(str(model_text or "")):
        raw_num = match.group(1)
        num = int(raw_num) if raw_num.isdigit() else number_words.get(raw_num.lower())

        if not num:
            continue

        subpart = match.group(2)
        label = f"{num}({subpart.lower()})." if subpart else f"{num}."

        if label not in labels:
            labels.append(label)

        if len(labels) >= limit:
            break

    if len(labels) < limit:
        labels = [f"{index}." for index in range(1, limit + 1)]

    return labels[:limit]


def recover_call_text_from_model(call_text, model_text):
    stored_call = normalize_extracted_text(call_text)
    stored_questions = extract_question_sentences_for_call(stored_call)
    model_questions = extract_model_legal_problem_questions(model_text)

    if len(model_questions) <= len(stored_questions):
        return stored_call

    labels = model_point_labels(model_text, len(model_questions))
    return "\n".join(
        f"{label} {question}" for label, question in zip(labels, model_questions)
    )


def split_model_answer_points(model_text):
    if not model_text:
        return []

    text = str(model_text).replace("\r\n", "\n").replace("\r", "\n")
    number_words = {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
    }
    pattern = re.compile(
        r"(?i)(Point\s+(One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten)|Point\s+(\d+))\s*(\([a-z]\))?\s*(?:\([^)]*%\))?"
    )
    matches = list(pattern.finditer(text))
    sections = []

    for idx, match in enumerate(matches):
        word_num = match.group(2)
        digit_num = match.group(3)
        raw_subpart = match.group(4)

        if word_num:
            num = number_words.get(word_num.lower())
        else:
            try:
                num = int(digit_num)
            except (TypeError, ValueError):
                num = None

        if not num:
            continue

        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        heading = match.group(0).strip()
        section_text = text[start:end].strip()
        subpart = (
            raw_subpart.replace("(", "").replace(")", "").strip().lower()
            if raw_subpart
            else None
        )

        sections.append({
            "num": num,
            "subpart": subpart,
            "heading": heading,
            "text": section_text,
        })

    return sections


def flatten_subquestions_for_answer_mapping(qd):
    subquestions = extract_subquestions(qd.get("call_of_question", ""))
    flat = []

    for q in subquestions:
        label = q.get("label", "Question")
        text = q.get("text", "")
        label_match = re.search(r"(\d+)", label)
        num = int(label_match.group(1)) if label_match else len(flat) + 1

        if q.get("subparts"):
            for sp in q["subparts"]:
                raw_sp_label = sp.get("label", "")
                subpart = raw_sp_label.replace(".", "").replace("(", "").replace(")", "").strip().lower()
                flat.append({
                    "label": f"{label}({subpart})" if subpart else label,
                    "num": num,
                    "subpart": subpart or None,
                    "text": f"{text} {sp.get('text', '')}".strip(),
                    "subparts": [],
                })
        else:
            flat.append({
                "label": label,
                "num": num,
                "subpart": None,
                "text": text,
                "subparts": [],
            })

    return flat


def count_question_calls(qd):
    call_text = str(qd.get("call_of_question", "") or "") if isinstance(qd, dict) else ""
    numbered = re.findall(r"(?:^|\s)(\d+)\.\s+", call_text)
    if numbered:
        return max(1, len(set(numbered)))

    try:
        flat = flatten_subquestions_for_answer_mapping(qd)
        return max(1, len(flat))
    except Exception:
        try:
            subquestions = extract_subquestions(qd.get("call_of_question", ""))
            return max(1, len(subquestions))
        except Exception:
            return 1


def model_answer_quality(qd):
    model_text = str(qd.get("model_points", "") or "") if isinstance(qd, dict) else ""
    cleaned = clean_sample_answer_text(model_text)

    if len(cleaned.strip()) < 250:
        return "missing"

    damaged_patterns = [
        r"\bAssuming\s+t\b",
        r"Point\s+Two\s*\(a\).*?\bAssuming\s+t\b",
        r"\bs\s+Short answer:",
        r"\bking\s+to\s+recover\b",
        r"\bCondensed Analysis\b",
        r"Condensed sample-answer path:\s*$",
    ]
    if any(re.search(pattern, model_text, flags=re.IGNORECASE) for pattern in damaged_patterns):
        return "damaged"

    try:
        points = split_model_answer_points(model_text)
    except Exception:
        points = []

    call_count = count_question_calls(qd)
    point_numbers = {p.get("num") for p in points if p.get("num")}

    if call_count > 1 and not points:
        return "unsplit"

    if points and min(point_numbers or {1}) > 1:
        return "partial"

    if call_count > 1 and len(point_numbers) < call_count:
        return "partial"

    return "usable"


def split_structured_lines(text):
    text = make_readable_legal_text(text)
    items = []

    for raw_line in str(text or "").splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        line = re.sub(r"^[-*\u2022]\s*", "", line).strip()
        if line and line not in items:
            items.append(line)

    return items


def build_structured_model_sections(qd, call_text=None):
    sections = []

    call_source = str(call_text or qd.get("call_of_question", "") or "").strip()
    if call_source:
        sections.append(("Call", split_structured_lines(call_source)))

    for heading, text in [
        ("Issues to Cover", qd.get("tested_issues", "")),
        ("Rules", qd.get("rules", "")),
        ("Trigger Facts", qd.get("trigger_facts", "")),
        ("Trap Warnings", qd.get("traps", "")),
    ]:
        items = split_structured_lines(text)
        if items:
            sections.append((heading, items))

    return sections


def render_structured_model_analysis(qd, call_text=None, title="Structured Model Analysis"):
    sections = build_structured_model_sections(qd, call_text=call_text)
    if not sections:
        render_text_info("No structured answer material is available for this question yet.")
        return

    section_html = []
    for heading, items in sections:
        if len(items) == 1:
            body_html = f'<div class="structured-section-body">{escape_display_text(items[0])}</div>'
        else:
            body_html = (
                '<ul class="structured-list">'
                + "".join(f"<li>{escape_display_text(item)}</li>" for item in items)
                + "</ul>"
            )

        section_html.append(
            '<div class="structured-section">'
            f'<div class="structured-section-title">{escape_display_text(heading)}</div>'
            f'{body_html}'
            '</div>'
        )

    render_html_box(
        title,
        (
            '<div class="structured-answer-note">'
            'The imported model answer for this question is incomplete or not cleanly split, '
            'so this view uses the clean answer-bank fields.'
            '</div>'
            f'{"".join(section_html)}'
        ),
        "structured-answer",
        body_class="structured-answer-content",
    )


def render_sample_answer_body(qd):
    if not isinstance(qd, dict):
        render_text_info("No sample answer/model analysis available for this question yet.")
        return

    model_points = qd.get("model_points", "") if isinstance(qd, dict) else ""
    quality = model_answer_quality(qd) if isinstance(qd, dict) else "missing"

    if not model_points and quality == "missing" and not (
        qd.get("tested_issues") or qd.get("rules") or qd.get("trigger_facts")
    ):
        render_text_info("No sample answer/model analysis available for this question yet.")
        return

    render_text_warning("Open this only after you attempted the issue/rule. No passive reading.")
    if quality == "usable":
        render_sample_answer_text("Sample Answer / Model Analysis", model_points)
    else:
        render_structured_model_analysis(qd, title="Structured Model Analysis")


def compact_question_paragraphs(lines, *, max_sentences=3, max_chars=620):
    """Group imported one-sentence-per-line question text into compact paragraphs."""
    paragraphs = []
    current = []
    sentence_count = 0
    marker_pattern = re.compile(r"^(\d+\.|[a-z]\.|\(\d+\)|\([a-z]\)|\([ivx]+\))\s+", re.IGNORECASE)

    def flush():
        nonlocal current, sentence_count
        if current:
            paragraphs.append(" ".join(current).strip())
        current = []
        sentence_count = 0

    for line in lines:
        line = line.strip()
        if not line:
            flush()
            continue

        if marker_pattern.match(line):
            flush()
            paragraphs.append(line)
            continue

        current.append(line)
        sentence_count += len(re.findall(r"[.!?](?:\"|')?$", line)) or 1

        if sentence_count >= max_sentences or len(" ".join(current)) >= max_chars:
            flush()

    flush()
    return paragraphs


def clean_question_text(question_text):
    if not question_text:
        return "No question text available."

    text = str(question_text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ")

    junk_patterns = [
        r"\bFEBRUARY\s+\d{4}\s+MEE\b",
        r"\bJULY\s+\d{4}\s+MEE\b",
        r"\bMEE\s+QUESTION\s+\d+\b",
        r"\bQUESTION\s+\d+\s*[-\u2013\u2014].*",
        r"Ã‚Â©\s*\d{4}.*",
        r"National Conference of Bar Examiners.*",
        r"These materials are copyrighted.*",
        r".*Question Bank.*",
        r"www\..*",
    ]

    for pattern in junk_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    text = re.sub(r',"\s*', ', "', text)
    text = re.sub(r'\."\s*', '." ', text)
    text = re.sub(r'([a-zA-Z])["â€]([A-Z])', r'\1" \2', text)

    raw_lines = text.splitlines()
    lines = []

    for line in raw_lines:
        line = re.sub(r"[ \t]+", " ", line).strip()
        if line:
            lines.append(line)

    text = " ".join(lines)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"([.!?])([A-Z])", r"\1 \2", text)
    text = re.sub(r"([,;:])([A-Za-z])", r"\1 \2", text)
    text = _normalize_quote_spacing(text)
    text = re.sub(r'([A-Za-z]),\s+"\s*([a-z])', r'\1," \2', text)
    text = re.sub(r'([A-Za-z])"([A-Za-z])', r'\1 "\2', text)

    # Keep list labels visible, but avoid the huge model-answer spacing.
    text = re.sub(r"\s+(\(\d+\))\s+", r"\n\1 ", text)
    text = re.sub(r"\s+(\([a-z]\))\s+", r"\n   \1 ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+(\([ivx]+\))\s+", r"\n      \1 ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+(\d+\.)\s+", r"\n\1 ", text)
    text = re.sub(r"\s+([a-z]\.)\s+", r"\n   \1 ", text)

    # Break long fact patterns at sentence boundaries when a new sentence starts.
    text = re.sub(r"(?<=[.!?])\s+(?=[A-Z][a-z])", "\n", text)

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    joined_lines = []
    index = 0
    standalone_label_pattern = re.compile(
        r"^(\d+\.|[a-z]\.|\(\d+\)|\([a-z]\)|\([ivx]+\))$",
        re.IGNORECASE,
    )

    while index < len(lines):
        line = lines[index]

        if standalone_label_pattern.match(line) and index + 1 < len(lines):
            joined_lines.append(f"{line} {lines[index + 1]}")
            index += 2
        else:
            joined_lines.append(line)
            index += 1

    text = "\n\n".join(compact_question_paragraphs(joined_lines))
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def render_question_text(title, question_text):
    formatted = clean_question_text(question_text)
    render_text_block(title, formatted, "question")


def _normalize_quote_spacing(text):
    """Pair straight double-quotes by order so opening/closing spacing is correct.

    PDF extraction glues quotes to neighboring words (gym,"Comet, a"going).
    A plain regex cannot tell an opening quote from a closing one, but walking
    the text and toggling an in-quote flag pairs them deterministically:
    opening quotes get a space before (none after), closing quotes get a space
    after (none before).
    """
    out = []
    in_quote = False
    chars = list(text)
    n = len(chars)

    for i, ch in enumerate(chars):
        if ch == '"':
            while out and out[-1] == " ":
                out.pop()
            if not in_quote:
                if out and out[-1] not in "([{":
                    out.append(" ")
                out.append('"')
                in_quote = True
            else:
                out.append('"')
                in_quote = False
                if i + 1 < n and chars[i + 1].isalpha():
                    out.append(" ")
        else:
            out.append(ch)

    return "".join(out)


def clean_fact_pattern_text(text):
    if not text:
        return "No fact pattern available."

    text = str(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("Â ", " ")

    # Remove exam/copyright/footer junk
    junk_patterns = [
        r"\bFEBRUARY\s+\d{4}\s+MEE\b",
        r"\bJULY\s+\d{4}\s+MEE\b",
        r"\bMEE\s+QUESTION\s+\d+\b",
        r"\bQUESTION\s+\d+\s*[-â€“â€”].*",
        r"Â©\s*\d{4}.*",
        r"National Conference of Bar Examiners.*",
        r"These materials are copyrighted.*",
        r".*Question Bank.*",
        r"www\..*",
    ]

    for pattern in junk_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    # Fix broken hyphenated line breaks: going-\nout-of-business -> going-out-of-business
    text = re.sub(r"(\w)-\s*\n+\s*(\w)", r"\1-\2", text)

    # Quote spacing is normalized after line-collapse (see _normalize_quote_spacing).

    # Collapse all line breaks to spaces -- PDF extraction creates fake paragraphs
    lines = []
    for line in text.splitlines():
        line = re.sub(r"[ \t]+", " ", line).strip()
        if line:
            lines.append(line)

    text = " ".join(lines)
    text = re.sub(r"\s+", " ", text)

    # Fix spacing around punctuation
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"([.!?])([A-Z])", r"\1 \2", text)
    text = re.sub(r"([,;:])([A-Za-z])", r"\1 \2", text)

    # Pair and space straight double-quotes correctly
    text = _normalize_quote_spacing(text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def split_fact_pattern_paragraphs(text, max_sentences_per_paragraph=4):
    cleaned = clean_fact_pattern_text(text)

    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z\"'])", cleaned)

    paragraphs = []
    current = []

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        current.append(sentence)

        if len(current) >= max_sentences_per_paragraph:
            paragraphs.append(" ".join(current))
            current = []

    if current:
        paragraphs.append(" ".join(current))

    return paragraphs


def render_fact_pattern_text(title, text, max_chars=None):
    paragraphs = split_fact_pattern_paragraphs(text)

    if max_chars:
        joined = "\n\n".join(paragraphs)

        if len(joined) > max_chars:
            joined = (
                joined[:max_chars].rsplit(" ", 1)[0]
                + "... [mini packet ends - open full question if needed]"
            )

        paragraphs = [p.strip() for p in joined.split("\n\n") if p.strip()]

    safe_title = escape_display_text(title)
    paragraph_html = "".join(f"<p>{escape_display_text(p)}</p>" for p in paragraphs)

    st.markdown(
        (
            '<div class="fact-box">'
            f'<div class="fact-title">{safe_title}</div>'
            f'<div class="fact-text">{paragraph_html}</div>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


def clean_trap_text(text):
    if not text:
        return ""

    text = str(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ")
    text = re.sub(r"(?<!\d)(\d)([A-Z])", r"\1. \2", text)
    text = re.sub(r"\bTrap\s*:\s*", "Trap: ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*-\s*Trap:\s*", "\nTrap: ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+Trap:\s*", "\nTrap: ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+(\d+[.)])\s+", r"\n\1 ", text)

    junk_patterns = [
        r"\bFEBRUARY\s+\d{4}\s+MEE\b",
        r"\bJULY\s+\d{4}\s+MEE\b",
        r"Â©\s*\d{4}.*",
        r".*Question Bank.*",
        r"National Conference of Bar Examiners.*",
    ]

    for pat in junk_patterns:
        text = re.sub(pat, "", text, flags=re.IGNORECASE)

    lines = []
    for line in text.splitlines():
        line = re.sub(r"[ \t]+", " ", line).strip()
        if line:
            lines.append(line)

    return "\n".join(lines).strip()


def extract_trap_items(traps_text):
    text = clean_trap_text(traps_text)

    if not text:
        return []

    text = re.sub(r"\bTrap\s*:\s*", "\nTrap: ", text, flags=re.IGNORECASE)
    text = re.sub(r"(?:^|\n)\s*[-â€¢]?\s*Trap\s*:\s*", "\nTrap: ", text, flags=re.IGNORECASE)

    raw_parts = re.split(
        r"(?:\n+|(?:^|\s)-\s+|(?:^|\s)\d+[.)]\s+|(?=\bTrap\s*:))",
        text,
    )

    items = []

    for part in raw_parts:
        part = part.strip(" -â€¢\t")
        part = re.sub(r"^(?:Trap\s*:\s*)+", "", part, flags=re.IGNORECASE).strip()
        part = re.sub(r"^\d+[.)]?\s*", "", part).strip()
        part = re.sub(r"\s+", " ", part).strip()

        if len(part) < 8:
            continue

        subparts = re.split(r"\s+Trap:\s+", part, flags=re.IGNORECASE)
        for sp in subparts:
            sp = sp.strip(" -â€¢\t")
            sp = re.sub(r"^(?:Trap\s*:\s*)+", "", sp, flags=re.IGNORECASE).strip()
            sp = re.sub(r"\bTrap\s*:\s*", "", sp, flags=re.IGNORECASE).strip()
            sp = re.sub(r"\s+", " ", sp).strip()

            if len(sp) >= 8:
                items.append(sp)

    clean = []
    seen = set()

    for item in items:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            clean.append(item)

    return clean


def clean_trigger_facts_text(text):
    if not text:
        return ""

    text = str(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ").replace("Ã‚Â ", " ")

    text = re.sub(r"\bTrigger Facts:\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bRelevant Facts:\s*", "", text, flags=re.IGNORECASE)

    junk_patterns = [
        r"\bFEBRUARY\s+\d{4}\s+MEE\b",
        r"\bJULY\s+\d{4}\s+MEE\b",
        r"\bMEE\s+QUESTION\s+\d+\b",
        r"Ã‚Â©\s*\d{4}.*",
        r"National Conference of Bar Examiners.*",
        r".*Question Bank.*",
        r"www\..*",
    ]

    for pattern in junk_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    citation_patterns = [
        r"\b[A-Z][A-Za-z.]+ v\. [A-Z][A-Za-z. ]+,?\s*[^.]*\(\d{4}\)",
        r"\b\d+\s+[A-Z][A-Za-z. ]+\s+\d+[,\s]*\d*\s*\([A-Za-z. ]*\d{4}\)",
        r"\bId\.\s*;?",
        r"\bsee also\b.*?(?=\.|$)",
    ]

    for pattern in citation_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    text = re.sub(r"(\w)-\s*\n+\s*(\w)", r"\1-\2", text)
    text = re.sub(r',"\s*', ', "', text)
    text = re.sub(r'\."\s*', '." ', text)

    lines = []
    for line in text.splitlines():
        line = re.sub(r"[ \t]+", " ", line).strip()
        if line:
            lines.append(line)

    text = "\n".join(lines)
    text = re.sub(r"\n{2,}", "\n", text)

    return text.strip()


def extract_trigger_fact_items(trigger_facts_text):
    text = clean_trigger_facts_text(trigger_facts_text)

    if not text:
        return []

    parts = re.split(r"(?:\n|;|\||â€¢|(?:\s+-\s+))", text)
    items = []

    for part in parts:
        part = part.strip(" -â€¢\t")
        part = re.sub(r"^\d+[.)]\s*", "", part)
        part = re.sub(r"^[a-z][.)]\s*", "", part, flags=re.IGNORECASE)
        part = re.sub(r"\s+", " ", part).strip()

        if len(part) < 8:
            continue

        citation_noise = (
            re.search(r"\b[A-Z][A-Za-z.]+\s+v\.\s+[A-Z]", part)
            or re.search(r"\b\d+\s*(?:So\.|P\.|F\.|N\.?W\.?|U\.S\.)", part, flags=re.IGNORECASE)
        )
        if citation_noise:
            continue

        if len(part) > 260:
            sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z\"'])", part)
            for sentence in sentences:
                sentence = sentence.strip()
                if 8 <= len(sentence) <= 260:
                    items.append(sentence)
        else:
            items.append(part)

    clean = []
    seen = set()

    for item in items:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            clean.append(item)

    return clean


def clean_tested_issues_text(text):
    if not text:
        return "No tested issues available."

    text = str(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ").replace("Ã‚Â ", " ")
    text = re.sub(r"[ \t]+", " ", text)

    text = re.sub(r"\bLegal Problems:\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bDISCUSSION\b.*", "", text, flags=re.IGNORECASE | re.DOTALL)

    citation_patterns = [
        r"\b\d+\s+[A-Z][A-Za-z. ]+\s+\d+[,\s]*\d*\s*\([A-Za-z. ]*\d{4}\)",
        r"\b[A-Z][A-Za-z.]+ v\. [A-Z][A-Za-z. ]+,?\s*[^.]*\(\d{4}\)",
        r"\bId\.\s*;?",
        r"\bsee also\b.*?(?=\.|$)",
        r"\bP\.\s*W\.",
        r"\bSo\.\s*\d+d\b",
        r"\bN\.?W\.?\d?d\b",
        r"\bF\.\s?\d+d\b",
        r"\bU\.S\.\b",
    ]

    for pattern in citation_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        if re.fullmatch(r"[\d\s.,;()A-Za-z]*\d{4}[\d\s.,;()A-Za-z]*", line) and len(line) < 90:
            continue

        if len(line) < 4:
            continue

        lines.append(line)

    text = " ".join(lines)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"([.!?])([A-Z])", r"\1 \2", text)

    return text.strip() or "No tested issues available."


def extract_issue_bullets(tested_issues_text):
    if not tested_issues_text:
        return []

    text = clean_tested_issues_text(tested_issues_text)

    if not text or text == "No tested issues available.":
        return []

    issues = []

    if re.search(r"(?:^|\s)-\s+", text):
        dash_parts = re.split(r"(?:^|\s)-\s+", text)
        for part in dash_parts:
            part = part.strip(" -;")
            if len(part) >= 10:
                issues.append(part)

    if not issues:
        numbered = re.findall(
            r"(?:^|\s)\(?(\d+)\)?[.)]\s+(.*?)(?=(?:\s\(?\d+\)?[.)]\s+)|$)",
            text,
            flags=re.DOTALL,
        )

        if numbered:
            for _, body in numbered:
                body = body.strip(" -;")
                if body:
                    issues.append(body)

    if not issues:
        question_sentences = re.findall(r"([^?]+\?)", text)
        for question in question_sentences:
            question = question.strip(" -;")
            if len(question) >= 10:
                issues.append(question)

    if not issues:
        sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)
        issue_starters = (
            "whether", "can", "could", "does", "did", "is", "are",
            "may", "must", "should", "was", "were",
        )

        for sentence in sentences:
            sentence = sentence.strip(" -;")
            if len(sentence) < 15:
                continue
            if sentence.lower().startswith(issue_starters):
                issues.append(sentence)

    clean = []
    seen = set()

    for issue in issues:
        issue = re.sub(r"\s+", " ", issue).strip()
        issue = issue.strip(" -;.")

        citation_noise = (
            re.search(r"\b[A-Z][A-Za-z.]+\s+v\.\s+[A-Z]", issue)
            or re.search(r"\b\d+\s*(?:So\.|P\.|F\.|N\.?W\.?|U\.S\.)", issue, flags=re.IGNORECASE)
            or re.search(r"\b(?:Washington|Schmanski|Casimir|Nat\.?|Gas|Co\.)\b", issue, flags=re.IGNORECASE)
        )
        if citation_noise:
            continue

        split_issue = re.split(r",\s+and\s+(?=(?:is|are|can|could|does|did|may|must|should|was|were)\b)", issue, flags=re.IGNORECASE)
        if len(split_issue) > 1:
            for piece in split_issue:
                piece = piece.strip(" -;.")
                if len(piece) < 10:
                    continue
                piece = piece[:1].upper() + piece[1:]
                if not piece.endswith("?") and issue.endswith("?"):
                    piece += "?"
                key = piece.lower()
                if key not in seen:
                    seen.add(key)
                    clean.append(piece)
            continue

        if len(issue) > 320:
            issue = issue[:320].rsplit(" ", 1)[0] + "..."

        if len(issue) < 10:
            continue

        key = issue.lower()
        if key not in seen:
            seen.add(key)
            clean.append(issue)

    return clean


def render_trap_warnings(title, traps_text):
    traps = extract_trap_items(traps_text)

    if not traps:
        render_text_info("No trap warnings available yet.")
        return

    cards_html = ""
    for idx, trap in enumerate(traps, start=1):
        cards_html += (
            '<div class="trap-card">'
            f'<div class="trap-number">{idx}</div>'
            f'<div class="trap-text">{escape_display_text(trap)}</div>'
            '</div>'
        )

    st.markdown(
        (
            '<div class="trap-warning-box">'
            f'<div class="trap-warning-title">{escape_display_text(title)}</div>'
            f'{cards_html}'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


def infer_fact_relevance(fact, qd=None):
    qd = qd or {}
    fact_l = str(fact or "").lower()
    subject = (qd.get("subject", "") or "").lower()
    tested = (qd.get("tested_issues", "") or "").lower()
    rules = (qd.get("rules", "") or "").lower()
    blob = tested + " " + rules

    relevance = []

    if any(w in fact_l for w in ["filed", "served", "complaint", "motion", "summary judgment", "federal court", "state court"]):
        relevance.append("procedure / posture")

    if any(w in fact_l for w in [
        "injured", "damaged", "hit", "collision", "negligent", "violated",
        "statute", "foreseeable", "bus", "stop sign", "emergency", "truck",
        "honked", "scraped", "bumper",
    ]):
        relevance.append("duty / breach / causation")

    if any(w in fact_l for w in ["blocked", "locked", "confined", "detained", "restroom", "leave"]):
        relevance.append("false imprisonment / confinement")

    if any(w in fact_l for w in ["offer", "accept", "agreed", "signed", "oral", "writing", "price", "goods", "delivery"]):
        relevance.append("contract formation / statute of frauds")

    if any(w in fact_l for w in ["citizen", "domicile", "incorporated", "principal place", "amount", "75,000", "minimum contacts", "venue"]):
        relevance.append("jurisdiction / venue")

    if (
        ("constitutional" in subject or "first amendment" in blob)
        and any(w in fact_l for w in ["ordinance", "speech", "sign", "public", "forum", "content", "government", "town"])
    ):
        relevance.append("First Amendment / constitutional scrutiny")

    if any(w in fact_l for w in ["agent", "principal", "authority", "partner", "profits", "corporation", "director", "board"]):
        relevance.append("relationship / authority / fiduciary duty")

    if any(w in fact_l for w in ["statement", "testified", "hearsay", "objected", "witness", "expert", "character"]):
        relevance.append("admissibility / evidence rule")

    if any(w in fact_l for w in ["deed", "recorded", "mortgage", "lease", "tenant", "easement", "covenant", "title"]):
        relevance.append("property interest / notice / priority")

    if any(w in fact_l for w in ["police", "warrant", "search", "arrest", "miranda", "confession", "weapon", "killed"]):
        relevance.append("criminal procedure / offense element")

    if "foreseeability" in blob and any(w in fact_l for w in ["death", "patient", "foreseeable", "summary judgment", "surgery", "hospital"]):
        relevance.append("foreseeability / proximate cause")

    if relevance:
        return "Why it matters: " + "; ".join(dict.fromkeys(relevance)) + "."

    if subject:
        return f"Why it matters: likely relevant to {qd.get('subject', 'the tested subject')}."

    return "Why it matters: this fact likely triggers a legal issue or rule element."


def render_trigger_facts(title, facts, qd=None):
    if isinstance(facts, dict) and qd is None:
        qd = facts
        facts = extract_trigger_fact_items(qd.get("trigger_facts", ""))

    facts = list(facts or [])

    if not facts:
        render_text_info("No trigger facts available yet.")
        return

    cards_html = ""

    for idx, fact in enumerate(facts, start=1):
        cards_html += (
            '<div class="trigger-card">'
            f'<div class="trigger-number">{idx}</div>'
            '<div class="trigger-content">'
            f'<div class="trigger-fact-text">{escape_display_text(fact)}</div>'
            f'<div class="trigger-why">{escape_display_text(infer_fact_relevance(fact, qd))}</div>'
            '</div>'
            '</div>'
        )

    st.markdown(
        (
            '<div class="triggers-box">'
            f'<div class="triggers-title">{escape_display_text(str(title))}</div>'
            f'{cards_html}'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


def render_tested_issues(title, tested_issues_text):
    issues = extract_issue_bullets(tested_issues_text)

    if not issues:
        cleaned = clean_tested_issues_text(tested_issues_text)
        render_readable_text(title, cleaned)
        return

    issue_cards_html = ""

    for idx, issue in enumerate(issues, start=1):
        issue_cards_html += (
            '<div class="issue-card">'
            f'<div class="issue-number">{idx}</div>'
            f'<div class="issue-text">{escape_display_text(issue)}</div>'
            '</div>'
        )

    st.markdown(
        (
            '<div class="issues-box">'
            f'<div class="issues-title">{escape_display_text(str(title))}</div>'
            f'{issue_cards_html}'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


def render_tested_issues_text(title, text):
    render_tested_issues(title, text)


def clean_call_text(call_text):
    if not call_text:
        return "No call of the question available."

    text = str(call_text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ")

    junk_patterns = [
        r"\bFEBRUARY\s+\d{4}\s+MEE\b",
        r"\bJULY\s+\d{4}\s+MEE\b",
        r"\bMEE\s+QUESTION\s+\d+\b",
        r"\bQUESTION\s+\d+\s*[-\u2013\u2014].*",
        r"(?:©|Â©|Ãƒâ€šÃ‚Â©)\s*\d{4}.*",
        r"National Conference of Bar Examiners.*",
        r"These materials are copyrighted.*",
        r".*Question Bank.*",
        r"www\..*",
    ]

    for pattern in junk_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    text = re.sub(r',"\s*', ', "', text)
    text = re.sub(r'\."\s*', '." ', text)

    raw_lines = text.splitlines()
    lines = []

    for line in raw_lines:
        line = re.sub(r"[ \t]+", " ", line).strip()
        if line:
            lines.append(line)

    text = " ".join(lines)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"([.!?])([A-Z])", r"\1 \2", text)
    text = re.sub(r"([,;:])([A-Za-z])", r"\1 \2", text)
    text = _normalize_quote_spacing(text)
    text = re.sub(r'([A-Za-z]),\s+"\s*([a-z])', r'\1," \2', text)
    text = re.sub(r'([A-Za-z])"([A-Za-z])', r'\1 "\2', text)
    text = re.sub(
        r"\s+((?:If|What|Was|Were|Is|Are|Did|Does|Do|Can|Could|Should|Will|Would|May|Assuming that)\b)",
        r"\n\1",
        text,
    )
    text = re.sub(r"\s+(\d+\([a-z]\)\.)\s*", r"\n\1 ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+(\d+\.)\s+", r"\n\1 ", text)
    text = re.sub(r"\s+([a-z]\.)\s+", r"\n\1 ", text)
    text = re.sub(r"\n{2,}", "\n", text)

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    text = "\n".join(lines)

    return text.strip()


def extract_subquestions(call_text):
    text = clean_call_text(call_text)

    if not text:
        return [{"label": "Question", "text": "No call of the question available.", "subparts": []}]

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    subquestions = []
    current = None
    unnumbered_count = 0

    numbered_subpart_pattern = re.compile(r"^(\d+)\(([a-z])\)\.\s*(.*)", re.IGNORECASE)
    top_level_pattern = re.compile(r"^(\d+)\.\s*(.*)")
    subpart_pattern = re.compile(r"^([a-z]\.)\s*(.*)", re.IGNORECASE)
    call_start_pattern = re.compile(
        r"^(If|What|Was|Were|Is|Are|Did|Does|Do|Can|Could|Should|Will|Would|May|Assuming that)\b",
    )

    has_numbered_call = any(top_level_pattern.match(line) for line in lines)

    if not has_numbered_call:
        while lines and not call_start_pattern.match(lines[0]):
            lines.pop(0)

    for line in lines:
        numbered_subpart = numbered_subpart_pattern.match(line)
        top = top_level_pattern.match(line)
        sub = subpart_pattern.match(line)

        if numbered_subpart:
            question_number = numbered_subpart.group(1)
            subpart_label = f"{numbered_subpart.group(2).lower()}."
            subpart_text = numbered_subpart.group(3).strip()
            expected_label = f"Question {question_number}"

            if current and current.get("label") != expected_label:
                subquestions.append(current)
                current = None

            if not current:
                current = {
                    "label": expected_label,
                    "text": "",
                    "subparts": [],
                }

            current["subparts"].append({
                "label": subpart_label,
                "text": subpart_text,
            })

        elif top:
            if current:
                subquestions.append(current)

            current = {
                "label": f"Question {top.group(1)}",
                "text": top.group(2).strip(),
                "subparts": [],
            }

        elif not has_numbered_call and call_start_pattern.match(line):
            if current:
                subquestions.append(current)

            unnumbered_count += 1
            current = {
                "label": f"Question {unnumbered_count}",
                "text": line.strip(),
                "subparts": [],
            }

        elif sub and current:
            current["subparts"].append({
                "label": sub.group(1).strip(),
                "text": sub.group(2).strip(),
            })

        else:
            if current:
                if current["subparts"]:
                    current["subparts"][-1]["text"] += " " + line
                else:
                    current["text"] += " " + line
            else:
                current = {
                    "label": "Question",
                    "text": line,
                    "subparts": [],
                }

    if current:
        subquestions.append(current)

    cleaned = []

    for question in subquestions:
        question["text"] = re.sub(r"\s+", " ", question.get("text", "")).strip()
        fixed_subparts = []

        for subpart in question.get("subparts", []):
            subpart["text"] = re.sub(r"\s+", " ", subpart.get("text", "")).strip()
            if subpart["text"]:
                fixed_subparts.append(subpart)

        question["subparts"] = fixed_subparts

        if question["text"] or question["subparts"]:
            cleaned.append(question)

    if not cleaned:
        return [{"label": "Question", "text": text, "subparts": []}]

    return cleaned


def render_call_text(title, call_text):
    subquestions = extract_subquestions(call_text)
    safe_title = escape_display_text(title)
    cards_html = ""

    for index, question in enumerate(subquestions, start=1):
        raw_label = question.get("label", "Question")
        label_match = re.search(r"(\d+)", raw_label)
        if len(subquestions) == 1:
            display_label = "Call"
        elif label_match:
            display_label = f"Call {label_match.group(1)}"
        else:
            display_label = f"Call {index}"

        label = escape_display_text(display_label)
        question_text = escape_display_text(question.get("text", ""))
        subparts_html = ""

        for subpart in question.get("subparts", []):
            subpart_label = escape_display_text(subpart.get("label", ""))
            subpart_text = escape_display_text(subpart.get("text", ""))
            subparts_html += (
                '<div class="call-subpart">'
                f'<span class="call-subpart-label">{subpart_label} </span>'
                f'<span>{subpart_text}</span>'
                '</div>'
            )

        cards_html += (
            '<div class="call-card">'
            f'<div class="call-card-label">{label}</div>'
            f'<div class="call-card-text">{question_text}</div>'
            f'{subparts_html}'
            '</div>'
        )

    st.markdown(
        (
            '<div class="call-box">'
            f'<div class="call-title">{safe_title}</div>'
            f'{cards_html}'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


def extract_fact_pattern_only(question_text, call_text=None):
    import re

    if not question_text:
        return "No fact pattern available."

    text = str(question_text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ")

    # Remove exam/footer junk.
    junk_patterns = [
        r"\bFEBRUARY\s+\d{4}\s+MEE\b",
        r"\bJULY\s+\d{4}\s+MEE\b",
        r"\bMEE\s+QUESTION\s+\d+\b",
        r"\bQUESTION\s+\d+\s*[-–—].*",
        r"©\s*\d{4}.*",
        r".*Question Bank.*",
        r"National Conference of Bar Examiners.*",
    ]

    for pat in junk_patterns:
        text = re.sub(pat, "", text, flags=re.IGNORECASE)

    # If exact call text appears, cut before it.
    if call_text:
        raw_call = str(call_text).strip()
        if raw_call and raw_call in text:
            text = text.split(raw_call)[0]

        # Try cleaned call as well.
        try:
            cleaned_call = clean_call_text(call_text)
            if cleaned_call and cleaned_call in text:
                text = text.split(cleaned_call)[0]
        except Exception:
            pass

    # Normalize lines for call detection but preserve original text length roughly.
    # Find first top-level numbered call near the back half of the question.
    # Examples:
    # 1. If the woman sues...
    # 1. What type...
    # 1. Can Brenda...
    # 1. Was Kim...
    numbered_call_patterns = [
        r"(?m)^\s*1\.\s+(If|What|Can|Could|Is|Are|Was|Were|Will|Would|Should|May|Does|Did|Do)\b",
        r"(?m)^\s*1\.\s+\([a-z]\)\s+",
    ]

    cut_positions = []

    for pat in numbered_call_patterns:
        for m in re.finditer(pat, text, flags=re.IGNORECASE):
            if m.start() > len(text) * 0.35:
                cut_positions.append(m.start())

    # Also detect inline call starts after a sentence where PDF extraction lost line break:
    # "... considering suing the potter. If the woman sues..."
    inline_call_patterns = [
        r"\.\s+(If\s+the\s+[^.]{0,120}?\s+sues\b)",
        r"\.\s+(Assuming\s+that\b)",
        r"\.\s+(What\s+type\b)",
        r"\.\s+(Can\s+[A-Z][A-Za-z]+\b)",
        r"\.\s+(Could\s+a\s+court\b)",
        r"\.\s+(Is\s+the\b)",
        r"\.\s+(Was\s+[A-Z][A-Za-z]+\b)",
        r"\.\s+(Should\s+the\b)",
        r"\.\s+(Should\s+[A-Z][A-Za-z]+\b)",
        r"\.\s+(Would\s+the\b)",
        r"\.\s+(Will\s+the\b)",
        r"\.\s+(Does\s+the\b)",
        r"\.\s+(Did\s+the\b)",
        r"\.\s+(May\s+the\b)",
    ]

    for pat in inline_call_patterns:
        for m in re.finditer(pat, text, flags=re.IGNORECASE):
            # Only cut if the detected call is in the latter part of the question.
            if m.start() > len(text) * 0.45:
                # cut after the period before the call, preserving the factual sentence.
                cut_positions.append(m.start() + 1)

    # Detect "Explain. 2." patterns and cut at the first call if possible.
    # If " 2." appears, find the previous " 1." or inline call before it.
    two_match = re.search(r"\s+2\.\s+", text)
    if two_match:
        prior_ones = list(re.finditer(r"\s+1\.\s+", text))
        for one in prior_ones:
            if one.start() > len(text) * 0.35 and one.start() < two_match.start():
                cut_positions.append(one.start())
        if not prior_ones:
            late_intro_pattern = (
                r"\.\s+(If|Assuming|What|Can|Could|Is|Are|Was|Were|Will|Would|"
                r"Should|May|Does|Did|Do)\b"
            )
            for m in re.finditer(late_intro_pattern, text[:two_match.start()], flags=re.IGNORECASE):
                if m.start() > len(text) * 0.45:
                    cut_positions.append(m.start() + 1)

    if cut_positions:
        cutoff = min(cut_positions)
        text = text[:cutoff]

    # Final cleanup with fact cleaner if available.
    if "clean_fact_pattern_text" in globals():
        return clean_fact_pattern_text(text)

    return text.strip()



QUESTION_HIGHLIGHT_CLASSES = [
    "q-highlight-1",
    "q-highlight-2",
    "q-highlight-3",
    "q-highlight-4",
    "q-highlight-5",
    "q-highlight-6",
]

QUESTION_HIGHLIGHT_LABELS = [
    "Q1",
    "Q2",
    "Q3",
    "Q4",
    "Q5",
    "Q6",
]

SUBJECT_TRIGGER_KEYWORDS = {
    "Business Associations": [
        "agent", "principal", "authority", "actual authority", "apparent authority",
        "ratified", "partnership", "partner", "profits", "losses", "co-owner",
        "ordinary course", "corporation", "director", "officer", "shareholder",
        "board", "fiduciary", "duty of care", "duty of loyalty", "LLC", "member",
    ],
    "Civil Procedure": [
        "filed", "served", "complaint", "answer", "motion", "dismiss",
        "federal court", "state court", "diversity", "citizen", "domicile",
        "incorporated", "principal place of business", "amount in controversy",
        "personal jurisdiction", "minimum contacts", "venue", "transfer",
        "summary judgment", "claim preclusion", "issue preclusion", "joinder",
    ],
    "Constitutional Law": [
        "ordinance", "statute", "government", "state", "town", "city",
        "speech", "sign", "public forum", "content", "viewpoint", "religion",
        "equal protection", "due process", "fundamental right", "suspect class",
        "commerce", "tax", "taking", "search", "seizure", "First Amendment",
    ],
    "Contracts": [
        "offer", "accept", "agreement", "promise", "consideration", "signed",
        "writing", "oral", "merchant", "goods", "sale", "price", "quantity",
        "delivery", "breach", "repudiated", "damages", "cover", "installment",
        "UCC", "common law", "modification", "condition", "performance",
    ],
    "Criminal Law & Procedure": [
        "police", "officer", "arrest", "warrant", "search", "seized", "stop",
        "frisk", "Miranda", "custody", "interrogation", "confession",
        "statement", "probable cause", "reasonable suspicion", "intent",
        "killed", "weapon", "conspiracy", "attempt", "theft", "robbery",
    ],
    "Evidence": [
        "witness", "testified", "statement", "offered", "objected",
        "hearsay", "truth of the matter", "impeach", "character", "prior",
        "expert", "lay opinion", "authentication", "privilege", "relevance",
        "probative", "prejudice",
    ],
    "Real Property": [
        "deed", "recorded", "conveyed", "buyer", "seller", "mortgage",
        "lease", "tenant", "landlord", "easement", "covenant", "servitude",
        "adverse possession", "title", "notice", "bona fide purchaser",
        "foreclosure", "zoning",
    ],
    "Torts": [
        "negligent", "negligently", "duty", "breach", "injury", "harm",
        "caused", "proximate", "foreseeable", "damages", "reasonable person",
        "statute", "violation", "battery", "assault", "false imprisonment",
        "defamation", "strict liability", "product", "defect", "res ipsa",
    ],
    "Family Law": [
        "married", "divorce", "custody", "child", "support", "alimony",
        "premarital", "property", "best interests", "adoption", "parent",
    ],
    "Trusts & Estates": [
        "will", "trust", "settlor", "beneficiary", "trustee", "estate",
        "devise", "bequest", "heir", "intestate", "probate", "revocation",
        "capacity", "undue influence", "fiduciary",
    ],
    "Secured Transactions": [
        "security interest", "collateral", "debtor", "secured party",
        "financing statement", "perfected", "attachment", "priority",
        "PMSI", "inventory", "equipment", "buyer", "default",
    ],
    "Conflict of Laws": [
        "state", "forum", "law of", "choice of law", "diversity",
        "domicile", "most significant relationship", "place of injury",
        "place of contracting", "recognize", "judgment",
    ],
}


def split_fact_sentences(text):
    if not text:
        return []

    text = clean_fact_pattern_text(text) if "clean_fact_pattern_text" in globals() else str(text)
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z\"'])", text)
    return [s.strip() for s in sentences if len(s.strip()) > 20]


def extract_trigger_phrases(text):
    return extract_trigger_fact_items(text)


def get_universal_trigger_candidates(qd, max_candidates=18):
    subject = qd.get("subject", "") or ""
    question_text = qd.get("question_text", "") or ""
    call_text = qd.get("call_of_question", "") or ""
    tested_issues = qd.get("tested_issues", "") or ""
    stored_triggers = qd.get("trigger_facts", "") or ""
    rules = qd.get("rules", "") or ""
    traps = qd.get("traps", "") or ""

    candidates = []
    candidates.extend(extract_trigger_phrases(stored_triggers))

    keywords = []
    for subj, words in SUBJECT_TRIGGER_KEYWORDS.items():
        if subj.lower() in subject.lower() or subject.lower() in subj.lower():
            keywords.extend(words)

    source_blob = f"{tested_issues} {call_text} {rules} {traps}"
    raw_terms = re.findall(r"\b[A-Za-z][A-Za-z\-]{4,}\b", source_blob)
    stopwords = {
        "because", "therefore", "however", "explain", "whether", "would",
        "should", "could", "court", "likely", "under", "where", "which",
        "their", "there", "about", "against", "action", "claim", "issue",
        "question", "answer", "facts", "rules", "legal",
    }

    for term in raw_terms:
        if term.lower() not in stopwords:
            keywords.append(term.lower())

    seen_kw = set()
    clean_keywords = []
    for kw in keywords:
        kw = kw.lower().strip()
        if kw and kw not in seen_kw:
            seen_kw.add(kw)
            clean_keywords.append(kw)

    fact_only = extract_fact_pattern_only(question_text, call_text)
    sentences = split_fact_sentences(fact_only)
    scored = []

    for sent in sentences:
        lower = sent.lower()
        score = sum(1 for kw in clean_keywords if kw in lower)

        if any(x in lower for x in [
            "signed", "filed", "served", "told", "said", "agreed",
            "refused", "objected", "moved", "sued", "charged",
            "ordinance", "statute", "contract", "injured", "damages",
            "police", "warrant", "arrest", "recorded", "delivered",
        ]):
            score += 2

        if score > 0:
            scored.append((score, sent))

    scored.sort(key=lambda x: x[0], reverse=True)
    candidates.extend(sent for _, sent in scored[:max_candidates])

    clean = []
    seen = set()
    for candidate in candidates:
        candidate = re.sub(r"\s+", " ", str(candidate)).strip()
        if not (5 <= len(candidate) <= 260):
            continue

        key = candidate.lower()
        if key not in seen:
            seen.add(key)
            clean.append(candidate)

    return clean[:max_candidates]


def get_clean_trigger_facts(qd, max_items=12):
    items = extract_trigger_fact_items(qd.get("trigger_facts", ""))

    if len(items) < 3:
        candidates = get_universal_trigger_candidates(qd, max_candidates=max_items)
        items.extend(candidates)

    if not items:
        question_text = qd.get("question_text", "")
        call_text = qd.get("call_of_question", "")
        fact_only = extract_fact_pattern_only(question_text, call_text)
        sentences = split_fact_sentences(fact_only)

        signal_words = [
            "said", "told", "agreed", "signed", "filed", "served", "sued",
            "violated", "injured", "damaged", "refused", "ordinance",
            "contract", "police", "warrant", "recorded", "delivered",
            "hit", "collision", "blocked", "locked", "confined",
        ]

        for sentence in sentences:
            if any(word in sentence.lower() for word in signal_words):
                items.append(sentence.strip())
            if len(items) >= max_items:
                break

    clean = []
    seen = set()

    for item in items:
        item = re.sub(r"\s+", " ", str(item).strip())

        if len(item) < 8:
            continue
        if len(item) > 280:
            item = item[:280].rsplit(" ", 1)[0] + "..."

        citation_noise = (
            re.search(r"\b[A-Z][A-Za-z.]+\s+v\.\s+[A-Z]", item)
            or re.search(r"\b\d+\s*(?:So\.|P\.|F\.|N\.?W\.?|U\.S\.)", item, flags=re.IGNORECASE)
        )
        if citation_noise:
            continue

        if item and item[0].islower():
            item = item[0].upper() + item[1:]

        key = item.lower()
        if key not in seen:
            seen.add(key)
            clean.append(item)

        if len(clean) >= max_items:
            break

    return clean


def highlight_universal_triggers(question_text, qd):
    if not question_text:
        return "No fact pattern available."

    base_text = clean_fact_pattern_text(question_text) if "clean_fact_pattern_text" in globals() else str(question_text)
    escaped_text = escape(base_text)
    candidates = get_clean_trigger_facts(qd)

    if len(candidates) < 5:
        candidates.extend(get_universal_trigger_candidates(qd, max_candidates=12))

    if not candidates:
        return escaped_text

    for phrase in sorted(candidates, key=len, reverse=True):
        phrase_clean = clean_fact_pattern_text(phrase) if "clean_fact_pattern_text" in globals() else str(phrase)
        phrase_clean = re.sub(r"\s+", " ", phrase_clean).strip()
        if len(phrase_clean) < 5:
            continue

        escaped_phrase = escape(phrase_clean)
        pattern = re.escape(escaped_phrase).replace(r"\ ", r"\s+")

        try:
            escaped_text = re.sub(
                pattern,
                lambda m: f'<span class="trigger-highlight">{m.group(0)}</span>',
                escaped_text,
                flags=re.IGNORECASE,
            )
        except re.error:
            continue

    return escaped_text


def render_universal_highlighted_fact_pattern(title, qd, text=None):
    question_text = qd.get("question_text", "")
    call_text = qd.get("call_of_question", "")

    if text is None:
        text = extract_fact_pattern_only(question_text, call_text)
    else:
        text = extract_fact_pattern_only(text, call_text)

    paragraphs = split_fact_pattern_paragraphs(text)
    highlighted_paragraphs = "".join(
        f"<p>{highlight_universal_triggers(paragraph, qd)}</p>" for paragraph in paragraphs
    )

    st.markdown(
        f"""
        <div class="fact-highlight-legend">
            Highlighted text marks likely trigger facts. Use it for review after retrieval, not before the first attempt.
        </div>
        <div class="fact-box highlighted-fact-box">
            <div class="fact-title">{escape(str(title))}</div>
            <div class="fact-text">
                {highlighted_paragraphs}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def keywords_for_subquestion(subq):
    text = subq.get("text", "") or ""

    for sp in subq.get("subparts", []):
        text += " " + sp.get("text", "")

    text = text.lower()

    stopwords = {
        "explain", "whether", "would", "could", "should", "under", "assuming",
        "question", "court", "claim", "claims", "issue", "issues", "based",
        "establish", "liability", "liable", "rights", "rule", "rules", "legal",
        "against", "with", "from", "that", "this", "there", "their", "when",
        "what", "does", "did", "can", "may", "was", "were", "have", "has",
    }

    words = re.findall(r"\b[a-z][a-z\-]{3,}\b", text)
    keywords = [w for w in words if w not in stopwords]
    synonyms = []

    if "forum" in text or "first amendment" in text or "speech" in text:
        synonyms += ["ordinance", "speech", "sign", "median", "public", "sidewalk", "communicate", "solicit", "content"]

    if "content-based" in text or "content neutral" in text or "content-neutral" in text:
        synonyms += ["ordinance", "communicate", "vehicles", "traffic", "safety", "preamble", "solicit"]

    if "negligence" in text or "breach" in text or "duty" in text:
        synonyms += ["violated", "statute", "law", "school bus", "collision", "damaged", "injury", "foreseeable"]

    if "false imprisonment" in text or "detaining" in text or "detained" in text:
        synonyms += ["blocked", "restroom", "locked", "leave", "pounded", "shouting", "fear", "confined"]

    if "summary judgment" in text:
        synonyms += ["admitted", "foreseeable", "causation", "likely", "patient", "survived", "material fact"]

    if "agency" in text or "agent" in text:
        synonyms += ["agent", "principal", "acting on behalf", "control", "consent", "manifest", "authority"]

    if "actual authority" in text:
        synonyms += ["told", "instructions", "express", "implied", "reasonable belief"]

    if "apparent authority" in text:
        synonyms += ["third party", "held out", "store owner", "believed", "appearance"]

    if "partnership" in text or "partners" in text:
        synonyms += ["profits", "co-owners", "business", "losses", "management", "ordinary course"]

    if "contract" in text:
        synonyms += ["offer", "accept", "agreement", "signed", "price", "goods", "writing", "breach"]

    if "jurisdiction" in text:
        synonyms += ["citizen", "domicile", "federal court", "state court", "served", "minimum contacts"]

    if "hearsay" in text:
        synonyms += ["statement", "truth", "declarant", "testified", "offered", "objected"]

    clean = []
    seen = set()

    for kw in keywords + synonyms:
        kw = kw.lower().strip()
        if kw and kw not in seen:
            seen.add(kw)
            clean.append(kw)

    return clean[:30]


def get_fact_sentences_for_subquestions(qd, max_per_question=8):
    question_text = qd.get("question_text", "") or ""
    call_text = qd.get("call_of_question", "") or ""

    fact_only = (
        extract_fact_pattern_only(question_text, call_text)
        if "extract_fact_pattern_only" in globals()
        else question_text
    )

    sentences = (
        split_fact_sentences(fact_only)
        if "split_fact_sentences" in globals()
        else re.split(r"(?<=[.!?])\s+(?=[A-Z\"'])", str(fact_only))
    )

    subquestions = (
        extract_subquestions(call_text)
        if "extract_subquestions" in globals()
        else [{"label": "Question 1", "text": call_text, "subparts": []}]
    )

    mapping = []

    for idx, subq in enumerate(subquestions):
        keywords = keywords_for_subquestion(subq)
        scored = []

        for sent in sentences:
            sent_clean = re.sub(r"\s+", " ", str(sent)).strip()
            lower = sent_clean.lower()
            score = sum(1 for kw in keywords if kw in lower)

            if any(x in lower for x in [
                "said", "told", "agreed", "signed", "filed", "served", "sued",
                "violated", "ordinance", "statute", "law", "injured", "damaged",
                "blocked", "locked", "refused", "admitted", "charged",
            ]):
                score += 1

            if score > 0:
                scored.append((score, sent_clean))

        scored.sort(key=lambda x: x[0], reverse=True)
        selected = []
        seen = set()

        for _, sent in scored:
            key = sent.lower()
            if key not in seen:
                seen.add(key)
                selected.append(sent)
            if len(selected) >= max_per_question:
                break

        mapping.append({
            "label": subq.get("label", f"Question {idx + 1}"),
            "call": subq,
            "class": QUESTION_HIGHLIGHT_CLASSES[idx % len(QUESTION_HIGHLIGHT_CLASSES)],
            "facts": selected,
            "keywords": keywords,
        })

    return mapping


def explain_fact_for_subquestion(fact, subq, qd):
    text = subq.get("text", "") or ""

    for sp in subq.get("subparts", []):
        text += " " + sp.get("text", "")

    fact_l = str(fact).lower()
    call_l = text.lower()
    subject_l = (qd.get("subject", "") or "").lower()

    if "forum" in call_l:
        return "This fact helps classify the forum because location, public access, and historical use matter for First Amendment forum analysis."
    if "content" in call_l and ("content-based" in call_l or "content neutral" in call_l or "content-neutral" in call_l):
        return "This fact helps decide whether the ordinance regulates speech because of its message or instead regulates conduct, time, place, or manner."
    if "first amendment" in subject_l or "speech" in call_l:
        return "This fact is relevant to the speech restriction, government interest, forum, or level of scrutiny."

    if "negligence" in call_l or "breach" in call_l:
        if any(w in fact_l for w in ["statute", "law", "violated", "school bus", "stop sign"]):
            return "This fact may trigger negligence per se because a statutory violation can establish breach if the statute was designed to prevent this type of harm and protect this class of persons."
        return "This fact is relevant to duty, breach, causation, or damages."
    if "false imprisonment" in call_l or "detain" in call_l or "detaining" in call_l:
        return "This fact may support false imprisonment because it bears on intentional confinement, lack of consent, and awareness of confinement."
    if "summary judgment" in call_l:
        return "This fact matters because summary judgment is proper only if there is no genuine dispute of material fact and the movant is entitled to judgment as a matter of law."
    if "wrongful death" in call_l or "proximate cause" in call_l or "causation" in call_l:
        return "This fact is relevant to causation and foreseeability, including whether the defendant's conduct was an actual and proximate cause of the death."

    if "agency" in call_l or "agent" in call_l:
        return "This fact bears on agency creation: consent, acting on behalf of the principal, and the principal's right to control."
    if "actual authority" in call_l:
        return "This fact bears on actual authority because actual authority depends on the principal's manifestations to the agent and the agent's reasonable belief."
    if "apparent authority" in call_l:
        return "This fact bears on apparent authority because apparent authority depends on the principal's manifestations to the third party and the third party's reasonable belief."
    if "partnership" in call_l:
        return "This fact bears on partnership formation or liability, including co-ownership, profit sharing, control, ordinary course, or partner authority."

    if "contract" in call_l or "offer" in call_l or "accept" in call_l:
        return "This fact bears on contract formation, interpretation, performance, breach, or defenses."
    if "statute of frauds" in call_l:
        return "This fact matters because Statute of Frauds analysis turns on the type of contract, writing, signature, and exceptions."

    if "jurisdiction" in call_l:
        return "This fact bears on jurisdiction, such as citizenship, domicile, contacts with the forum, or amount in controversy."
    if "venue" in call_l:
        return "This fact bears on venue because venue depends on residence, location of events, or property."
    if "preclusion" in call_l:
        return "This fact bears on preclusion because prior judgment, same parties, same claim or issue, and finality matter."

    if "hearsay" in call_l:
        return "This fact matters because hearsay depends on whether an out-of-court statement is offered for its truth or for another purpose."
    if "character" in call_l or "impeach" in call_l:
        return "This fact bears on admissibility, impeachment, character evidence, or a specific evidence exception."

    if "deed" in call_l or "record" in call_l or "title" in call_l:
        return "This fact bears on property ownership, recording, notice, priority, or title."
    if "easement" in call_l or "covenant" in call_l:
        return "This fact bears on whether a property interest runs with the land or binds successors."

    if "search" in call_l or "seizure" in call_l:
        return "This fact bears on Fourth Amendment analysis: government action, reasonable expectation of privacy, warrant, probable cause, or exception."
    if "miranda" in call_l or "custody" in call_l or "interrogation" in call_l:
        return "This fact bears on Miranda because warnings are required only for custodial interrogation."

    return "This fact likely triggers a rule element for this call. Ask: what legal element does this fact prove or weaken?"


def build_highlight_span(match_text, css_class, label, reason, show_explanations=True):
    if not show_explanations:
        return f'<span class="{css_class}">{match_text}</span>'

    try:
        safe_label = escape(str(label))
        safe_reason = escape(str(reason))
        return (
            f'<span class="tooltip-highlight {css_class}" tabindex="0">'
            f'{match_text}'
            '<span class="tooltip-bubble">'
            f'<span class="tooltip-title">{safe_label}</span>'
            f'<span class="tooltip-reason">{safe_reason}</span>'
            '<span class="tooltip-hint">Ask: which rule element does this fact prove?</span>'
            '</span>'
            '</span>'
        )
    except Exception:
        return f'<span class="{css_class}">{match_text}</span>'


def highlight_facts_by_question(qd, show_explanations=True, fact_text=None):
    question_text = qd.get("question_text", "") or ""
    call_text = qd.get("call_of_question", "") or ""

    if fact_text is None:
        fact_only = (
            extract_fact_pattern_only(question_text, call_text)
            if "extract_fact_pattern_only" in globals()
            else question_text
        )
    else:
        fact_only = extract_fact_pattern_only(fact_text, call_text)

    base_text = (
        clean_fact_pattern_text(fact_only)
        if "clean_fact_pattern_text" in globals()
        else str(fact_only)
    )

    escaped_text = escape(base_text)
    mapping = get_fact_sentences_for_subquestions(qd)

    phrase_items = []
    for item in mapping:
        for fact in item["facts"]:
            phrase_items.append((fact, item["class"], item["label"], item["call"]))

    if not phrase_items:
        raise ValueError("No question-specific trigger facts detected.")

    phrase_items.sort(key=lambda x: len(x[0]), reverse=True)
    already_highlighted_patterns = set()

    for phrase, css_class, label, subq in phrase_items:
        phrase_clean = (
            clean_fact_pattern_text(phrase)
            if "clean_fact_pattern_text" in globals()
            else str(phrase)
        )
        phrase_clean = re.sub(r"\s+", " ", phrase_clean).strip()

        if len(phrase_clean) < 12:
            continue

        pattern_key = phrase_clean.lower()
        if pattern_key in already_highlighted_patterns:
            continue
        already_highlighted_patterns.add(pattern_key)

        escaped_phrase = escape(phrase_clean)
        pattern = re.escape(escaped_phrase).replace(r"\ ", r"\s+")

        try:
            reason = explain_fact_for_subquestion(phrase, subq, qd)
            escaped_text = re.sub(
                pattern,
                lambda m: build_highlight_span(
                    m.group(0),
                    css_class,
                    label,
                    reason,
                    show_explanations=show_explanations,
                ),
                escaped_text,
                count=1,
                flags=re.IGNORECASE,
            )
        except re.error:
            continue

    return escaped_text, mapping


def render_detected_facts_by_question(mapping):
    """Render detected trigger facts with the same compact card style as fact lists."""
    sections = []

    for item in mapping:
        label = escape_display_text(item.get("label") or "Question")
        facts = item.get("facts") or []

        if facts:
            cards = "".join(
                (
                    '<div class="trigger-card">'
                    f'<div class="trigger-number">{index}</div>'
                    '<div class="trigger-content">'
                    f'<div class="trigger-fact-text">{escape_display_text(fact)}</div>'
                    '</div>'
                    '</div>'
                )
                for index, fact in enumerate(facts, start=1)
            )
        else:
            cards = '<div class="trigger-card"><div class="trigger-content">No specific facts detected for this call.</div></div>'

        sections.append(
            '<div class="triggers-box">'
            f'<div class="triggers-title">{label}</div>'
            f'{cards}'
            '</div>'
        )

    st.markdown("".join(sections), unsafe_allow_html=True)


def render_trigger_rule_map(title, qd):
    """Render a compact map from each call to its trigger facts and rule connection."""
    try:
        mapping = get_fact_sentences_for_subquestions(qd, max_per_question=4)
    except Exception:
        mapping = []

    if not mapping:
        render_text_info("No trigger identifiers could be detected for this question yet.")
        return

    shared_rules = split_structured_lines(qd.get("rules", ""))[:6]
    sections = []

    for item in mapping:
        label = escape_display_text(item.get("label") or "Question")
        call = item.get("call") or {}
        call_text = escape_display_text(call.get("text") or "")
        facts = item.get("facts") or []

        fact_cards = []
        for index, fact in enumerate(facts, start=1):
            reason = explain_fact_for_subquestion(fact, call, qd)
            fact_cards.append(
                '<div class="trigger-card trigger-map-card">'
                f'<div class="trigger-number">{index}</div>'
                '<div class="trigger-content">'
                f'<div class="trigger-fact-text">{escape_display_text(fact)}</div>'
                f'<div class="trigger-rule-link">{escape_display_text(reason)}</div>'
                '</div>'
                '</div>'
            )

        if not fact_cards:
            fact_cards.append(
                '<div class="trigger-card trigger-map-card">'
                '<div class="trigger-content">No specific trigger sentence detected for this call.</div>'
                '</div>'
            )

        rule_html = ""
        if shared_rules:
            rule_html = (
                '<div class="trigger-rule-bank">'
                '<div class="trigger-rule-bank-title">Rules to connect</div>'
                '<ul>'
                + "".join(f"<li>{escape_display_text(rule)}</li>" for rule in shared_rules)
                + "</ul>"
                "</div>"
            )

        sections.append(
            '<div class="triggers-box trigger-map-box">'
            f'<div class="triggers-title">{label}</div>'
            f'<div class="trigger-call-text">{call_text}</div>'
            f'{"".join(fact_cards)}'
            f'{rule_html}'
            '</div>'
        )

    st.markdown(
        (
            '<div class="fact-box trigger-map-shell">'
            f'<div class="fact-title">{escape_display_text(title)}</div>'
            '<div class="fact-text">'
            f'{"".join(sections)}'
            '</div>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


def render_question_specific_highlighted_facts(title, qd, show_explanations=True):
    question_text = qd.get("question_text", "")
    call_text = qd.get("call_of_question", "")
    fact_only = extract_fact_pattern_only(question_text, call_text)
    highlighted_html, mapping = highlight_facts_by_question(
        qd,
        show_explanations=show_explanations,
        fact_text=fact_only,
    )

    legend_html = '<div class="question-highlight-legend"><div class="legend-row">'

    for idx, item in enumerate(mapping):
        label = escape(item.get("label") or QUESTION_HIGHLIGHT_LABELS[idx % len(QUESTION_HIGHLIGHT_LABELS)])
        css_class = item["class"]
        legend_html += f'<span class="legend-chip {css_class}">{label}</span>'

    legend_html += '</div></div>'

    render_text_info("Colors show which facts likely support each call of the question.")
    if show_explanations:
        render_text_info("Hover over or click a highlighted fact to see why it matters.")
    st.markdown(legend_html, unsafe_allow_html=True)
    st.markdown(
        (
            '<div class="fact-box highlighted-fact-box">'
            f'<div class="fact-title">{escape(str(title))}</div>'
            f'<div class="fact-text"><p>{highlighted_html}</p></div>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )

    with render_text_expander("Detected facts by question", expanded=False):
        render_detected_facts_by_question(mapping)


def render_question_highlights_with_fallback(title, qd, text=None, show_explanations=True):
    try:
        render_question_specific_highlighted_facts(title, qd, show_explanations=show_explanations)
    except Exception:
        render_text_warning("Question-specific highlighting failed; showing universal highlights instead.")
        render_universal_highlighted_fact_pattern(title, qd, text=text)

def clean_outline_text(text):
    if not text:
        return "No outline text available."

    text = normalize_extracted_text(str(text))
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ")

    junk_patterns = [
        r"(?:©|Â©|Ã‚Â©)\s*\d{4}\s+LegacySource.*",
        r".*\.com.*",
        r"Business Associations\s*\|.*",
        r"Civil Procedure\s*\d+",
        r"Constitutional Law\s*\d+",
        r"Contracts\s*\d+",
        r"Evidence\s*\d+",
        r"Real Property\s*\d+",
        r"Torts\s*\d+",
    ]

    for pattern in junk_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"(?:§|Â§|Ã‚Â§)\s+(\d+)\.\s+(\d+)", r"§ \1.\2", text)
    text = re.sub(r"(?<=[a-z0-9])\.(?=[A-Z])", ". ", text)

    text = re.sub(r"\s+([a-z]\))\s+", r"\n\1 ", text)
    text = re.sub(r"\s+(\(\d+\))\s+", r"\n\1 ", text)
    text = re.sub(r"\s+(\([a-z]\))\s+", r"\n   \1 ", text)
    text = re.sub(r"\s+(\([ivx]+\))\s+", r"\n      \1 ", text, flags=re.IGNORECASE)

    transitions = [
        "However,",
        "Generally,",
        "For example:",
        "NOTE.",
        "Exception.",
    ]

    for word in transitions:
        text = re.sub(rf"\s+({re.escape(word)})", r"\n\1", text)

    cleaned_lines = []
    for raw_line in text.splitlines():
        line = re.sub(r"[ \t]+", " ", raw_line).strip()
        if line:
            cleaned_lines.append(line)

    compact_lines = []
    index = 0
    standalone_label_pattern = re.compile(r"^(?:[a-z]\)|\(\d+\)|\([a-z]\)|\([ivx]+\))$", re.IGNORECASE)
    section_heading_pattern = re.compile(r"^[A-Z]\.$")

    while index < len(cleaned_lines):
        line = cleaned_lines[index]

        if section_heading_pattern.match(line):
            index += 2 if index + 1 < len(cleaned_lines) and cleaned_lines[index + 1] else 1
            continue

        if (
            standalone_label_pattern.match(line)
            and index + 1 < len(cleaned_lines)
            and cleaned_lines[index + 1]
        ):
            compact_lines.append(f"{line} {cleaned_lines[index + 1]}")
            index += 2
            continue

        compact_lines.append(line)
        index += 1

    text = "\n".join(compact_lines)
    text = re.sub(r"\n{2,}", "\n", text)
    text = re.sub(r"(?<!\n)\s+(Rule:|Exception:|Example:|Note:)", r"\n\1", text, flags=re.IGNORECASE)

    return text.strip()


def render_outline_rule_text(title, text, reading_mode=False):
    formatted = clean_outline_text(text)
    safe_title = escape_display_text(title or "Attack Outline Rule")
    safe_text = escape_display_text(formatted)
    reading_class = " reading-mode" if reading_mode else ""

    st.markdown(
        (
            f'<div class="outline-rule-box{reading_class}">'
            f'<div class="outline-rule-title">{safe_title}</div>'
            f'<div class="outline-rule-text">{safe_text}</div>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


def format_plug_text_html(text):
    """Format Plug & Play template text with readable paragraphs and placeholder emphasis."""
    safe_text = escape_display_text(str(text or "").strip())
    safe_text = re.sub(
        r"(\[[^\]]+\])",
        r'<span class="plug-placeholder">\1</span>',
        safe_text,
    )
    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(r"\n+", safe_text)
        if paragraph.strip()
    ]

    if not paragraphs:
        return ""

    return "".join(f"<p>{paragraph}</p>" for paragraph in paragraphs)


def plug_section_class(title):
    title_key = re.sub(r"[^a-z0-9]+", "-", str(title or "").lower()).strip("-")
    return f" plug-section-{title_key}" if title_key else ""


def render_plug_section(title, text):
    if not text:
        return ""

    safe_title = escape_display_text(title)
    body_html = format_plug_text_html(text)

    return (
        f'<div class="plug-section{plug_section_class(title)}">'
        f'<div class="plug-section-title">{safe_title}</div>'
        f'<div class="plug-text">{body_html}</div>'
        '</div>'
    )


def render_plug_play_template(template):
    (
        template_id,
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
    ) = template

    safe_title = escape_display_text(module_title or "Plug & Play Template")
    safe_meta = escape_display_text(f"{subject or 'n/a'}")
    sections = [
        render_plug_section("Scenario Trigger", scenario_trigger),
        render_plug_section("Issue Statement", issue_statement),
        render_plug_section("Rule", rule_text),
        render_plug_section("Analysis Template", analysis_template),
        render_plug_section("Conclusion", conclusion_template),
        render_plug_section("How This Subject Is Tested", testing_notes),
    ]
    section_html = "".join(section for section in sections if section)

    st.markdown(
        (
            '<div class="plug-box">'
            '<div class="plug-kicker">Plug & Play Template</div>'
            f'<div class="plug-title">{safe_title}</div>'
            f'<div class="plug-meta-pill">{safe_meta}</div>'
            f'<div class="plug-grid">{section_html}</div>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


def outline_pdf_link(pdf_page):
    if not pdf_page:
        return None

    return f"app/static/bar_attack.pdf#page={int(pdf_page)}"


def render_attack_rule_box(rule, reading_mode=False):
    (
        rule_id,
        subject,
        rule_title,
        appearance_rate,
        rule_text,
        pdf_page,
        printed_page,
        source_file,
    ) = rule

    caption_parts = []
    if subject:
        caption_parts.append(f"Subject: {subject}")
    if appearance_rate:
        caption_parts.append(f"Appearance Rate: {appearance_rate}")
    if pdf_page:
        caption_parts.append(f"PDF Page: {pdf_page}")

    if caption_parts:
        st.caption(" | ".join(caption_parts))

    render_outline_rule_text(rule_title or "Attack Outline Rule", rule_text, reading_mode=reading_mode)

    if pdf_page:
        link = outline_pdf_link(pdf_page)
        if link:
            st.markdown(
                f'<a href="{link}" target="_blank">Open Outline Page</a>',
                unsafe_allow_html=True,
            )
