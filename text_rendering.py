# -*- coding: utf-8 -*-
"""Shared long-text rendering helpers for the MEE trainer app."""

import re
from html import escape

import streamlit as st

from text_cleanup import normalize_extracted_text


def escape_display_text(value):
    """Escape text for safe HTML display while preserving literal dollar signs."""
    return escape(str(value or "")).replace("$", "&#36;")


def normalize_long_text(text):
    """Normalize imported legal text before paragraph splitting/rendering."""
    if not text:
        return ""

    text = normalize_extracted_text(str(text))
    text = text.replace("\r\n", "\n").replace("\r", "\n")
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
    safe_title = escape_display_text(title)
    compact_class = " compact" if compact else ""
    body = "".join(
        f'<p style="margin-bottom:1.2em">{escape_display_text(paragraph)}</p>'
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

    st.markdown(
        (
            f'<div class="{class_name}-box{compact_class}">'
            f'<div class="{class_name}-title">{safe_title}</div>'
            f'<div class="{class_name}-text">{body}</div>'
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
        st.info("No sample answer/model analysis available for this question yet.")
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

    st.markdown(
        (
            '<div class="sample-answer-box">'
            f'<div class="sample-answer-title">{escape_display_text(title)}</div>'
            f'<div class="sample-answer-text">{"".join(blocks)}</div>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )
