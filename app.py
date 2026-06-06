# -*- coding: utf-8 -*-

import streamlit as st
import pandas as pd
import random
import re
from html import escape
from io import StringIO

from database import (
    init_db,
    add_question,
    get_questions,
    get_question_by_id,
    save_attempt,
    get_attempts,
    get_subjects,
    get_statuses,
    get_dashboard_stats,
    get_outline_rules,
    search_outline_rules,
    find_best_outline_rules_for_question,
    get_plug_play_templates,
    search_plug_play_templates,
    find_best_plug_play_for_call
)
from text_cleanup import normalize_extracted_text


st.set_page_config(
    page_title="MEE Reflex Trainer",
    layout="wide"
)

init_db()


st.title("MEE Reflex Trainer")
st.caption("Focused MEE training: issue spotting -> rule retrieval -> IRAC under pressure.")

st.markdown("""
<style>
/* Main app background */
.stApp {
    background: linear-gradient(135deg, #F7FBFF 0%, #EEF6FF 48%, #ECFEFF 100%);
    color: #102033;
}

/* Main content container */
.block-container {
    width: 100%;
    max-width: 1760px;
    padding-top: 0.75rem;
    padding-right: clamp(1rem, 2vw, 2rem);
    padding-bottom: 2rem;
    padding-left: clamp(1rem, 2vw, 2rem);
}

.main .block-container > div:first-child {
    padding-top: 0;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #EAF4FF 0%, #E8FFF9 100%);
    border-right: 2px solid #CDEBFF;
    min-width: 320px !important;
    width: 320px !important;
}

[data-testid="stSidebar"] * {
    color: #102033 !important;
}

[data-testid="stSidebar"] {
    font-size: 16px !important;
}

[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span {
    font-size: 16px !important;
}

[data-testid="stSidebar"] > div {
    min-width: 320px !important;
}

/* Headers */
h1, h2, h3 {
    color: #1D4E89 !important;
    font-weight: 800 !important;
}

h1 {
    background: none !important;
    color: #2563EB !important;
    -webkit-text-fill-color: #2563EB !important;
    text-align: center !important;
    line-height: 1.22 !important;
    padding-top: 0.35rem !important;
    margin-bottom: 0.25rem !important;
}

[data-testid="stHeading"]:has(h1),
[data-testid="stHeading"] h1 {
    width: 100% !important;
    text-align: center !important;
    overflow: visible !important;
}

[data-testid="stHeading"]:has(h1),
[data-testid="stHeadingWithActionElements"]:has(h1),
[data-testid="stHeading"] [data-testid="stMarkdownContainer"]:has(h1) {
    min-height: 4.8rem !important;
    overflow: visible !important;
}

h2, h3 {
    margin-top: 0.75rem !important;
    margin-bottom: 0.35rem !important;
}

div[data-testid="stCaptionContainer"],
div[data-testid="stMarkdownContainer"] p {
    margin-bottom: 0.35rem;
}

/* Cute cards */
div[data-testid="stMetric"] {
    background: rgba(255, 255, 255, 0.85);
    border: 1.5px solid #CDEBFF;
    border-radius: 14px;
    padding: 18px;
    box-shadow: 0 8px 24px rgba(29, 78, 137, 0.08);
}

div[data-testid="stMetric"] *,
div[data-testid="stAlert"] *,
div[data-testid="stExpander"] *,
[data-testid="stDataFrame"] * {
    color: #102033 !important;
}

/* Expanders */
.streamlit-expanderHeader {
    background-color: #FFFFFF !important;
    border-radius: 14px !important;
    color: #1D4E89 !important;
    font-weight: 700 !important;
}

div[data-testid="stExpander"] {
    background-color: rgba(255, 255, 255, 0.82) !important;
    border: 1.5px solid #CDEBFF !important;
    border-radius: 14px !important;
    overflow: hidden;
}

div[data-testid="stExpander"] details,
div[data-testid="stExpander"] summary,
div[data-testid="stExpander"] button,
div[data-testid="stExpander"] [role="button"] {
    background-color: #EAF4FF !important;
    color: #102033 !important;
    -webkit-text-fill-color: #102033 !important;
}

div[data-testid="stExpander"] summary {
    border-bottom: 1px solid #CDEBFF !important;
    min-height: 44px !important;
}

div[data-testid="stExpander"] summary *,
div[data-testid="stExpander"] button *,
div[data-testid="stExpander"] [role="button"] * {
    color: #102033 !important;
    fill: #102033 !important;
    stroke: #102033 !important;
    -webkit-text-fill-color: #102033 !important;
}

div[data-testid="stExpander"] summary p,
div[data-testid="stExpander"] summary span,
div[data-testid="stExpander"] summary div {
    color: #102033 !important;
    opacity: 1 !important;
    visibility: visible !important;
    -webkit-text-fill-color: #102033 !important;
}

div[data-testid="stExpander"] summary svg,
div[data-testid="stExpander"] summary svg * {
    color: #102033 !important;
    fill: #102033 !important;
    stroke: #102033 !important;
}

div[data-testid="stExpander"] summary:hover,
div[data-testid="stExpander"] button:hover,
div[data-testid="stExpander"] [role="button"]:hover {
    background-color: #DDF4FF !important;
    color: #102033 !important;
}

/* Text areas and inputs */
textarea, input {
    background-color: #FFFFFF !important;
    color: #102033 !important;
    border: 1.5px solid #93C5FD !important;
    border-radius: 14px !important;
}

textarea::placeholder, input::placeholder {
    color: #58708A !important;
    opacity: 1 !important;
}

[data-testid="stTextInput"] *,
[data-testid="stTextArea"] *,
[data-testid="stNumberInput"] *,
[data-testid="stSlider"] *,
[data-testid="stCheckbox"] *,
[data-testid="stSelectbox"] * {
    color: #102033 !important;
}

[data-baseweb="input"] *,
[data-baseweb="textarea"] *,
[data-baseweb="base-input"] * {
    color: #102033 !important;
    -webkit-text-fill-color: #102033 !important;
}

/* Select boxes */
div[data-baseweb="select"] > div {
    background-color: #FFFFFF !important;
    border-radius: 14px !important;
    border: 1.5px solid #93C5FD !important;
}

div[data-baseweb="select"] span,
div[data-baseweb="select"] div,
div[data-baseweb="popover"] span,
div[data-baseweb="popover"] div {
    color: #102033 !important;
}

/* Buttons */
.stButton > button,
.stFormSubmitButton > button,
div[data-testid="stFormSubmitButton"] button {
    background: linear-gradient(90deg, #2563EB, #0D9488);
    color: white !important;
    -webkit-text-fill-color: white !important;
    border: none;
    border-radius: 999px;
    padding: 0.6rem 1.2rem;
    font-weight: 800;
    box-shadow: 0 6px 16px rgba(37, 99, 235, 0.25);
    transition: all 0.2s ease-in-out;
}

.stButton > button *,
.stFormSubmitButton > button *,
div[data-testid="stFormSubmitButton"] button * {
    color: white !important;
    -webkit-text-fill-color: white !important;
}

.stButton > button:hover,
.stFormSubmitButton > button:hover,
div[data-testid="stFormSubmitButton"] button:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 22px rgba(37, 99, 235, 0.35);
}

.stButton > button:disabled,
.stFormSubmitButton > button:disabled,
div[data-testid="stFormSubmitButton"] button:disabled {
    background: #D7E7F7 !important;
    color: #4B647C !important;
    -webkit-text-fill-color: #4B647C !important;
    box-shadow: none;
    opacity: 1;
}

.stButton > button:disabled *,
.stFormSubmitButton > button:disabled *,
div[data-testid="stFormSubmitButton"] button:disabled * {
    color: #4B647C !important;
    -webkit-text-fill-color: #4B647C !important;
}

/* Number inputs */
div[data-testid="stNumberInput"] {
    color: #102033 !important;
}

div[data-testid="stNumberInput"] input,
div[data-testid="stNumberInput"] [data-baseweb="input"],
div[data-testid="stNumberInput"] [data-baseweb="base-input"] {
    background-color: #FFFFFF !important;
    color: #102033 !important;
    -webkit-text-fill-color: #102033 !important;
    border-color: #93C5FD !important;
}

div[data-testid="stNumberInput"] button,
div[data-testid="stNumberInput"] button:hover,
div[data-testid="stNumberInput"] button:focus,
div[data-testid="stNumberInput"] button:disabled {
    background: #EAF4FF !important;
    color: #102033 !important;
    -webkit-text-fill-color: #102033 !important;
    border: 1px solid #93C5FD !important;
    box-shadow: none !important;
    opacity: 1 !important;
    transform: none !important;
}

div[data-testid="stNumberInput"] button *,
div[data-testid="stNumberInput"] button svg,
div[data-testid="stNumberInput"] button svg * {
    color: #102033 !important;
    fill: #102033 !important;
    stroke: #102033 !important;
    -webkit-text-fill-color: #102033 !important;
}

/* Download button */
.stDownloadButton > button {
    background: linear-gradient(90deg, #80ED99, #56CFE1);
    color: #1B4332 !important;
    border: none;
    border-radius: 999px;
    font-weight: 800;
}

/* Info/success/warning boxes */
div[data-testid="stAlert"] {
    border-radius: 14px;
    border: 1.5px solid #CDEBFF;
}

/* Dataframes */
[data-testid="stDataFrame"] {
    border-radius: 16px;
    overflow: hidden;
    border: 1.5px solid #CDEBFF;
}

/* Radio buttons */
[role="radiogroup"] label {
    background-color: rgba(255, 255, 255, 0.65);
    color: #102033 !important;
    padding: 10px 13px;
    border-radius: 12px;
    margin-bottom: 7px;
    min-height: 44px;
    width: 100%;
    white-space: normal !important;
    overflow: visible !important;
}

[role="radiogroup"] label *,
[role="radio"] *,
[data-testid="stSidebar"] [role="radiogroup"] * {
    color: #102033 !important;
    -webkit-text-fill-color: #102033 !important;
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: clip !important;
    line-height: 1.3 !important;
}

[data-testid="stSidebar"] [role="radiogroup"] label,
[data-testid="stSidebar"] [role="radiogroup"] label div,
[data-testid="stSidebar"] [role="radiogroup"] label p,
[data-testid="stSidebar"] [role="radiogroup"] label span {
    font-size: 18px !important;
    line-height: 1.32 !important;
}

[data-testid="stSidebar"] [role="radiogroup"] label {
    min-height: 50px !important;
    padding: 11px 14px !important;
}

[role="radio"][aria-checked="true"],
[role="radio"][aria-checked="true"] + div,
[role="radiogroup"] label:has([aria-checked="true"]) {
    background-color: #DDF4FF !important;
    color: #102033 !important;
}

/* Streamlit toolbar/menu can render as a dark strip in custom themes */
header {
    background: rgba(247, 251, 255, 0.96) !important;
}

header,
[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
[data-testid="stMainMenu"],
[data-baseweb="menu"],
[role="listbox"] {
    background-color: #F7FBFF !important;
    color: #102033 !important;
}

header *,
[data-testid="stHeader"] *,
[data-testid="stToolbar"] *,
[data-testid="stDecoration"] *,
[data-testid="stStatusWidget"] *,
[data-testid="stMainMenu"] *,
[data-baseweb="menu"] *,
[role="listbox"] *,
[role="option"] * {
    color: #102033 !important;
    -webkit-text-fill-color: #102033 !important;
}

[role="option"],
[role="menuitem"],
[data-baseweb="menu"] li,
[data-baseweb="popover"] {
    background-color: #FFFFFF !important;
    color: #102033 !important;
}

[role="option"]:hover,
[role="menuitem"]:hover,
[data-baseweb="menu"] li:hover {
    background-color: #DDF4FF !important;
    color: #102033 !important;
}

/* Readable legal text boxes */
.readable-box {
    background: rgba(255, 255, 255, 0.92);
    border: 1.5px solid #CDEBFF;
    border-radius: 14px;
    padding: 0.9rem 1rem;
    margin: 0.55rem 0 0.8rem 0;
    box-shadow: 0 4px 14px rgba(29, 78, 137, 0.07);
    max-width: 100%;
}

.readable-box.compact {
    padding: 0.85rem 1rem;
    margin: 0.55rem 0 0.8rem 0;
}

.readable-title {
    color: #1D4E89;
    font-weight: 850;
    font-size: 1rem;
    margin-bottom: 0.4rem;
    padding-bottom: 0.25rem;
    border-bottom: 2px solid #DBEAFE;
}

.readable-box.compact .readable-title {
    margin-bottom: 0.45rem;
    padding-bottom: 0.3rem;
}

.readable-text {
    color: #102033;
    font-size: 16.5px;
    line-height: 1.5;
    letter-spacing: 0;
    white-space: pre-line;
    word-break: normal;
    overflow-wrap: break-word;
}

.readable-box.compact .readable-text {
    line-height: 1.5;
}

.readable-text::selection {
    background: #DDF4FF;
}

/* Compact question/fact pattern boxes */
.question-box {
    background: rgba(255, 255, 255, 0.96);
    border: 1.5px solid #CDEBFF;
    border-radius: 14px;
    padding: 0.9rem 1rem;
    margin: 0.55rem 0 0.8rem 0;
    box-shadow: 0 4px 14px rgba(29, 78, 137, 0.07);
    max-width: 100%;
}

.question-title {
    color: #1D4E89;
    font-weight: 850;
    font-size: 1rem;
    margin-bottom: 0.4rem;
    padding-bottom: 0.25rem;
    border-bottom: 2px solid #DBEAFE;
}

.question-text {
    color: #102033;
    font-size: 16.5px;
    line-height: 1.45;
    white-space: pre-line;
    word-break: normal;
    overflow-wrap: break-word;
}

.question-text::selection {
    background: #DDF4FF;
}

.trigger-facts-text {
    color: #102033;
    font-size: 16.5px;
    line-height: 1.38;
    white-space: pre-line;
    word-break: normal;
    overflow-wrap: break-word;
}

.trigger-facts-text::selection {
    background: #DDF4FF;
}

.hint-box {
    background: rgba(255, 255, 255, 0.97);
    border: 1.5px solid #BDE0FE;
    border-radius: 14px;
    padding: 0.8rem 1rem;
    margin: 0.45rem 0 0.65rem 0;
    box-shadow: 0 4px 14px rgba(29, 78, 137, 0.06);
    width: 100%;
    box-sizing: border-box;
}

.hint-title {
    color: #1D4E89;
    font-weight: 850;
    font-size: 1rem;
    margin-bottom: 0.35rem;
    padding-bottom: 0.25rem;
    border-bottom: 2px solid #DBEAFE;
}

.hint-text {
    color: #102033;
    font-size: 16.5px;
    line-height: 1.38;
    white-space: pre-line;
    word-break: normal;
    overflow-wrap: break-word;
}

/* Compact calls of the question */
.call-box {
    background: rgba(255, 255, 255, 0.96);
    border: 1.5px solid #BDE0FE;
    border-radius: 14px;
    padding: 0.9rem 1rem;
    margin: 0.55rem 0 0.8rem 0;
    box-shadow: 0 4px 14px rgba(29, 78, 137, 0.07);
    max-width: 100%;
}

.call-title {
    color: #2563EB;
    font-weight: 850;
    font-size: 1rem;
    margin-bottom: 0.4rem;
    padding-bottom: 0.25rem;
    border-bottom: 2px solid #DBEAFE;
}

.call-card {
    background: #F8FBFF;
    border: 1px solid #DBEAFE;
    border-radius: 12px;
    padding: 0.65rem 0.8rem;
    margin: 0.45rem 0;
}

.call-card-label {
    color: #1D4ED8;
    font-weight: 850;
    font-size: 0.95rem;
    margin-bottom: 0.25rem;
}

.call-card-text {
    color: #1E293B;
    font-size: 16.5px;
    line-height: 1.4;
    margin: 0;
}

.call-subpart {
    color: #1E293B;
    font-size: 16px;
    line-height: 1.4;
    margin-top: 0.35rem;
    padding-left: 0.65rem;
    border-left: 3px solid #BFDBFE;
}

.call-subpart-label {
    color: #2563EB;
    font-weight: 800;
    margin-right: 0.35rem;
}

/* Compact Attack Outline rule boxes */
.outline-rule-box {
    background: rgba(255, 255, 255, 0.97);
    border: 1.5px solid #BDE0FE;
    border-radius: 14px;
    padding: 0.8rem 1rem;
    margin: 0.45rem 0 0.65rem 0;
    box-shadow: 0 4px 14px rgba(29, 78, 137, 0.07);
    max-width: 100%;
}

.outline-rule-title {
    color: #1D4E89;
    font-weight: 850;
    font-size: 1rem;
    margin-bottom: 0.35rem;
    padding-bottom: 0.25rem;
    border-bottom: 2px solid #DBEAFE;
}

.outline-rule-text {
    color: #102033;
    font-size: 16.5px;
    line-height: 1.38;
    letter-spacing: 0;
    white-space: pre-line;
    word-break: normal;
    overflow-wrap: break-word;
}

.outline-rule-box.reading-mode .outline-rule-text {
    font-size: 18px;
    line-height: 1.55;
}

.outline-rule-text::selection {
    background: #F3E8FF;
}

/* Plug & Play template boxes */
.plug-box {
    background: rgba(255, 255, 255, 0.97);
    border: 1.5px solid #BDE0FE;
    border-radius: 14px;
    padding: 0.9rem 1rem;
    margin: 0.55rem 0 0.8rem 0;
    box-shadow: 0 4px 14px rgba(29, 78, 137, 0.07);
    box-sizing: border-box;
    display: block;
    width: 100%;
    max-width: none;
}

.plug-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.75rem 1rem;
    width: 100%;
}

.plug-section {
    min-width: 0;
}

.plug-title {
    color: #1D4E89;
    font-weight: 850;
    font-size: 1.02rem;
    margin-bottom: 0.35rem;
    padding-bottom: 0.3rem;
    border-bottom: 2px solid #DBEAFE;
}

.plug-section-title {
    color: #0F766E;
    font-weight: 800;
    margin-top: 0.15rem;
    margin-bottom: 0.25rem;
}

.plug-text {
    color: #102033;
    font-size: 16px;
    line-height: 1.42;
    white-space: pre-line;
    word-break: normal;
    overflow-wrap: break-word;
}

.plug-meta {
    margin-bottom: 0.75rem;
}

@media (max-width: 900px) {
    .plug-grid {
        grid-template-columns: 1fr;
    }
}

/* Little soft divider vibe */
hr {
    border: none;
    height: 2px;
    background: linear-gradient(90deg, #2563EB, #14B8A6, #7DD3FC);
    border-radius: 999px;
}

/* Practice page — thin metadata strip metric labels */
[data-testid="stMetricLabel"] p,
[data-testid="stMetricLabel"] {
    font-size: 0.72rem !important;
    line-height: 1.2 !important;
}
</style>
""", unsafe_allow_html=True)


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
    return {
        "id": q[0],
        "exam_name": q[1],
        "question_number": q[2],
        "subject": q[3],
        "question_text": normalize_extracted_text(q[4]),
        "call_of_question": normalize_extracted_text(q[5]),
        "tested_issues": normalize_extracted_text(q[6]),
        "rules": normalize_extracted_text(q[7]),
        "trigger_facts": normalize_extracted_text(q[8]),
        "traps": normalize_extracted_text(q[9]),
        "model_points": normalize_extracted_text(q[10]),
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


def escape_display_text(value):
    return escape(str(value)).replace("$", "&#36;")


def make_readable_legal_text(text):
    if not text:
        return "No text available."

    text = str(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ")

    # Fix PDF quote squashing: serve."Agency -> serve.\n\n"Agency
    text = re.sub(r'\.["”](?=[A-Z])', '.\n\n"', text)

    # through"written -> through "written
    text = re.sub(r'([a-zA-Z])["”]([a-zA-Z])', r'\1 "\2', text)

    # Fix section-symbol spacing.
    text = re.sub(r"§\s+(\d+)\.\s+(\d+)", r"§ \1.\2", text)
    text = re.sub(r"Â§\s+(\d+)\.\s+(\d+)", r"§ \1.\2", text)
    text = re.sub(r"\bId\.\s+§\s+(\d+)\.\s+(\d+)", r"Id. § \1.\2", text)
    text = re.sub(r"\bId\.\s+Â§\s+(\d+)\.\s+(\d+)", r"Id. § \1.\2", text)

    # Normalize spaces but preserve newlines.
    text = re.sub(r"[ \t]+", " ", text)

    text = re.sub(
        r"\b(Point One|Point Two|Point Three|Point Four|Point Five|Point Six)\s*(\([^)]*\))",
        r"\n\n\1 \2\n",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"\b(Legal Problems:|DISCUSSION|ANALYSIS)\b",
        r"\n\n\1\n",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(r"\s+(\(\d+\))\s+", r"\n\n\1 ", text)
    text = re.sub(r"\s+(\d+\.)\s+", r"\n\n\1 ", text)
    text = re.sub(r"\s+([a-z]\.)\s+", r"\n\n\1 ", text)

    transition_words = [
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
        "But ",
        "The issue is",
        "The rule is",
    ]

    for word in transition_words:
        text = re.sub(rf"\s+({re.escape(word)})", r"\n\n\1", text)

    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def render_readable_text(title, text, font_size=None):
    formatted = make_readable_legal_text(text)
    safe_title = escape_display_text(title)
    safe_text = escape_display_text(formatted)
    compact_class = " compact" if globals().get("COMPACT_MODE", False) else ""

    st.markdown(
        (
            f'<div class="readable-box{compact_class}">'
            f'<div class="readable-title">{safe_title}</div>'
            f'<div class="readable-text">'
            f'{safe_text}'
            f'</div></div>'
        ),
        unsafe_allow_html=True,
    )


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
        r"Â©\s*\d{4}.*",
        r"National Conference of Bar Examiners.*",
        r"These materials are copyrighted.*",
        r"Studicata.*",
        r"www\..*",
    ]

    for pattern in junk_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    text = re.sub(r',"\s*', ', "', text)
    text = re.sub(r'\."\s*', '." ', text)
    text = re.sub(r'([a-zA-Z])["”]([A-Z])', r'\1" \2', text)

    raw_lines = text.splitlines()
    lines = []

    for line in raw_lines:
        line = re.sub(r"[ \t]+", " ", line).strip()
        if line:
            lines.append(line)

    text = " ".join(lines)

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

    text = "\n".join(joined_lines)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def render_question_text(title, question_text):
    formatted = clean_question_text(question_text)
    safe_title = escape_display_text(title)
    safe_text = escape_display_text(formatted)

    st.markdown(
        (
            '<div class="question-box">'
            f'<div class="question-title">{safe_title}</div>'
            f'<div class="question-text">{safe_text}</div>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


def render_prompt(text):
    if not text:
        paragraphs = ["No prompt available."]
    else:
        formatted = str(text).replace("\r\n", "\n").replace("\r", "\n").replace("\u00a0", " ")
        formatted = re.sub(r"(?<=[a-z0-9][.!?])\s*(?=[A-Z])", "\n\n", formatted)
        paragraphs = [
            paragraph.strip()
            for paragraph in re.split(r"\n+", formatted)
            if paragraph.strip()
        ]

    paragraph_html = "".join(
        f'<p style="margin-bottom:1.2em">{escape_display_text(paragraph)}</p>'
        for paragraph in paragraphs
    )

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
            '">'
            f'{paragraph_html}'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


def clean_trigger_facts_text(text):
    if not text:
        return "No trigger facts available."

    text = str(text).replace("\r\n", "\n").replace("\r", "\n").replace("\u00a0", " ")
    raw_lines = text.splitlines()
    lines = []

    for line in raw_lines:
        line = re.sub(r"[ \t]+", " ", line).strip()
        if line:
            lines.append(line)

    text = " ".join(lines)
    text = re.sub(r"\s*;\s*", ";\n", text)
    text = re.sub(r"\s+(\(\d+\)|\d+\.)\s+", r"\n\1 ", text)

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines).strip()


def render_trigger_facts_text(title, text):
    formatted = clean_trigger_facts_text(text)
    safe_title = escape_display_text(title)
    safe_text = escape_display_text(formatted)

    st.markdown(
        (
            '<div class="question-box">'
            f'<div class="question-title">{safe_title}</div>'
            f'<div class="trigger-facts-text">{safe_text}</div>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


def clean_tested_issues_text(text):
    if not text:
        return "No tested issues available."

    text = str(text).replace("\r\n", "\n").replace("\r", "\n").replace("\u00a0", " ")
    raw_lines = text.splitlines()
    lines = []

    for line in raw_lines:
        line = re.sub(r"[ \t]+", " ", line).strip()
        if line:
            lines.append(line)

    text = " ".join(lines)
    text = re.sub(r"\s+(\(\d+\))\s+", r"\n\1 ", text)
    text = re.sub(r"\s+(\d+\.)\s+", r"\n\1 ", text)
    text = re.sub(r"\s+([a-z]\.)\s+", r"\n   \1 ", text, flags=re.IGNORECASE)

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines).strip()


def render_tested_issues_text(title, text):
    render_question_text(title, clean_tested_issues_text(text))


def extract_fact_pattern_only(question_text, call_text=None):
    if not question_text:
        return "No fact pattern available."

    text = str(question_text)
    text = re.sub(r"(?mi)^\s*(?:FEBRUARY|JULY)\s+\d{4}\s+MEE\s*$", "", text)
    text = re.sub(r"(?mi)^\s*MEE\s+QUESTION\s+\d+\s*$", "", text)
    text = re.sub(r"(?mi)^\s*QUESTION\s+\d+\s*[-\u2012\u2013\u2014\u2212:].*$", "", text)
    text = re.sub(r"(?mi)^\s*Studicata.*$", "", text)
    text = re.sub(r"(?mi)^\s*www\..*$", "", text)

    if call_text:
        cleaned_call = clean_call_text(call_text)
        direct_call = str(call_text).strip()

        for candidate in [direct_call, cleaned_call]:
            if candidate and candidate in text:
                text = text.replace(candidate, "")
                break

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    first_call_index = None

    for index in range(max(0, len(lines) - 30), len(lines)):
        if re.match(r"^1\.\s+", lines[index]):
            tail = "\n".join(lines[index:])
            if re.search(r"\b(Explain|Discuss|Analyze|Determine|Should|Would|What|Is|Can|May)\b", tail, re.IGNORECASE):
                first_call_index = index
                break

    if first_call_index is not None:
        lines = lines[:first_call_index]

    question_marker_index = None
    marker_pattern = re.compile(
        r"^(?:MEE\s+)?(?:QUESTION|Q)\s*\d+\s*(?:[-\u2012\u2013\u2014\u2212:].*)?$",
        re.IGNORECASE,
    )

    for index, line in enumerate(lines[1:], start=1):
        if marker_pattern.match(line):
            question_marker_index = index
            break

    if question_marker_index is not None:
        lines = lines[:question_marker_index]

    return "\n".join(lines).strip() or "No fact pattern available."


def question_looks_suspicious(qd):
    question_text = str(qd.get("question_text", "") or "")
    call_text = str(qd.get("call_of_question", "") or "")

    if len(question_text) > 18000:
        return True

    if re.search(r"(?mi)^\s*(?:MEE\s+)?(?:QUESTION|Q)\s*\d+\s*(?:[-\u2012\u2013\u2014\u2212:].*)?$", question_text[500:]):
        return True

    subject_headings = re.findall(
        r"(?mi)^\s*(CONSTITUTIONAL LAW|CIVIL PROCEDURE|TORTS|CONTRACTS|EVIDENCE|REAL PROPERTY|BUSINESS ASSOCIATIONS|AGENCY\s*&?\s*PARTNERSHIP)\s*$",
        question_text[500:],
    )

    if len(set(subject_headings)) >= 2:
        return True

    if re.search(r"\b(FEBRUARY|JULY)\b", call_text, re.IGNORECASE):
        return True

    return False


def render_data_health_warning(qd):
    if question_looks_suspicious(qd):
        st.error("Possible import problem: this question may contain multiple MEE questions. Reimport needed.")


def clean_call_text(call_text):
    if not call_text:
        return "No call of the question available."

    text = str(call_text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ")

    junk_patterns = [
        r"FEBRUARY\s+\d{4}\s+MEE",
        r"JULY\s+\d{4}\s+MEE",
        r"MEE\s+QUESTION\s+\d+",
        r"QUESTION\s+\d+\s*[-\u2013\u2014].*",
        r"Â©\s*\d{4}.*",
        r"©\s*\d{4}.*",
        r"National Conference of Bar Examiners.*",
        r"Studicata.*",
    ]

    for pattern in junk_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s+(\d+\([a-z]\)\.)\s+", r"\n\1 ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+(\d+\.)\s+", r"\n\1 ", text)
    text = re.sub(r"\s+([a-z]\.)\s+", r"\n   \1 ", text)

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    text = "\n".join(lines)

    return text.strip()


def clean_outline_text(text):
    if not text:
        return "No outline text available."

    text = str(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ")
    text = text.replace("Ãƒâ€šÃ‚Â§", "§").replace("Ã‚Â§", "§").replace("Â§", "§")
    text = text.replace("Ãƒâ€šÃ‚Â©", "©").replace("Ã‚Â©", "©").replace("Â©", "©")

    junk_patterns = [
        r"Ã‚Â©\s*\d{4}\s+Studicata.*",
        r"Â©\s*\d{4}\s+Studicata.*",
        r"Studicata\.com.*",
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
    text = re.sub(r"§\s+(\d+)\.\s+(\d+)", r"§ \1.\2", text)
    text = re.sub(r"(?<=[a-z0-9])\.(?=[A-Z])", ". ", text)
    text = re.sub(r"Ã‚Â§\s+(\d+)\.\s+(\d+)", r"Â§ \1.\2", text)
    text = re.sub(r"Â§\s+(\d+)\.\s+(\d+)", r"Â§ \1.\2", text)

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

    lines = [line.rstrip() for line in text.splitlines()]
    cleaned_lines = []

    for line in lines:
        line = line.strip()

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


def render_outline_rule_text(title, text):
    formatted = clean_outline_text(text)
    safe_title = escape_display_text(title or "Attack Outline Rule")
    safe_text = escape_display_text(formatted)
    reading_class = " reading-mode" if globals().get("ADHD_READING_MODE", False) else ""

    st.markdown(
        (
            f'<div class="outline-rule-box{reading_class}">'
            f'<div class="outline-rule-title">{safe_title}</div>'
            f'<div class="outline-rule-text">{safe_text}</div>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


def render_plug_section(title, text):
    if not text:
        return ""

    safe_title = escape_display_text(title)
    safe_text = escape_display_text(str(text).strip())

    return (
        '<div class="plug-section">'
        f'<div class="plug-section-title">{safe_title}</div>'
        f'<div class="plug-text">{safe_text}</div>'
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
    safe_meta = escape_display_text(f"{subject or 'n/a'} | Source page: {pdf_page or 'n/a'}")
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
            f'<div class="plug-title">Plug & Play Template: {safe_title}</div>'
            f'<div class="plug-text plug-meta"><strong>{safe_meta}</strong></div>'
            f'<div class="plug-grid">{section_html}</div>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


def outline_pdf_link(pdf_page):
    if not pdf_page:
        return None

    return f"app/static/bar_attack.pdf#page={int(pdf_page)}"


def render_attack_rule_box(rule):
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

    st.caption(
        f"Subject: {subject or 'n/a'} | Appearance Rate: {appearance_rate or 'n/a'} | "
        f"PDF Page: {pdf_page or 'n/a'}"
    )

    render_outline_rule_text(rule_title or "Attack Outline Rule", rule_text)

    try:
        link = outline_pdf_link(pdf_page)
        st.markdown(
            f'<a href="{link}" target="_blank">Open Outline Page</a>',
            unsafe_allow_html=True,
        )
    except Exception:
        st.info("No page link available.")


def first_nonempty_lines(text, n=3):
    if not text:
        return "No hint available yet."

    formatted = make_readable_legal_text(text)
    lines = [line.strip() for line in formatted.splitlines() if line.strip()]

    if not lines:
        return "No hint available yet."

    return "\n".join(lines[:n])


def make_rule_skeleton(rules):
    if not rules:
        return "No rule hint available yet."

    text = make_readable_legal_text(rules)
    text = re.sub(r"^Point One\s*\([^)]*\)\s*", "", text, flags=re.IGNORECASE)
    sentences = split_into_sentences(text)

    rule_sentences = []
    rule_keywords = [
        "rule",
        "requires",
        "must",
        "may",
        "is",
        "arises",
        "exists",
        "elements",
        "when",
        "if",
    ]

    for sentence in sentences:
        lower = sentence.lower()

        if any(keyword in lower for keyword in rule_keywords):
            rule_sentences.append(sentence)

        if len(rule_sentences) >= 3:
            break

    if rule_sentences:
        return "\n".join(rule_sentences)

    return make_short_hint(text, max_sentences=3, max_chars=800)


def split_into_sentences(text):
    if not text:
        return []

    text = make_readable_legal_text(text)
    text = text.replace("\n", " ")
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z\"'])", text)

    cleaned = []

    for sentence in sentences:
        sentence = sentence.strip()

        if len(sentence) >= 25:
            cleaned.append(sentence)

    return cleaned


def make_short_hint(text, max_sentences=3, max_chars=900):
    if not text:
        return "No hint available yet."

    sentences = split_into_sentences(text)

    if not sentences:
        cleaned = make_readable_legal_text(text)
        return cleaned[:max_chars] + ("..." if len(cleaned) > max_chars else "")

    selected = []
    total = 0

    for sentence in sentences:
        if len(selected) >= max_sentences:
            break

        if total + len(sentence) > max_chars:
            break

        selected.append(sentence)
        total += len(sentence)

    result = "\n".join(selected)

    if len(result) < len(make_readable_legal_text(text)):
        result += "\n..."

    return result


def make_trigger_fact_hint(qd):
    trigger_text = qd.get("trigger_facts", "")

    if trigger_text:
        return first_nonempty_lines(clean_trigger_facts_text(trigger_text), n=5)

    question_text = extract_fact_pattern_only(
        qd.get("question_text", ""),
        qd.get("call_of_question", ""),
    )

    if not question_text:
        return "No trigger facts available yet."

    sentences = split_into_sentences(question_text)
    keywords = [
        "signed",
        "said",
        "told",
        "agreed",
        "contract",
        "purchased",
        "authority",
        "agent",
        "principal",
        "manifested",
        "control",
        "notice",
        "filed",
        "served",
        "negligently",
        "loan",
        "security interest",
        "possession",
        "delivered",
    ]

    picked = []

    for sentence in sentences:
        lower = sentence.lower()

        if any(keyword in lower for keyword in keywords):
            picked.append(sentence)

        if len(picked) >= 5:
            break

    if picked:
        return "\n".join(picked)

    return make_short_hint(question_text, max_sentences=4, max_chars=900)


def make_progressive_hints(qd):
    outline_matches = find_best_outline_rules_for_question(
        qd.get("subject", ""),
        qd.get("tested_issues", ""),
        qd.get("rules", ""),
        qd.get("traps", ""),
        limit=1,
    )

    if outline_matches:
        rule_hint = "Try writing the rule from memory, then compare with the Attack Outline rule above."
    else:
        rule_hint = make_rule_skeleton(qd.get("rules", ""))

    return {
        "Hint 1 - Read the call": clean_call_text(qd.get("call_of_question", "")),
        "Hint 2 - Subject bucket": (
            f"Primary subject: {qd.get('subject', 'Unknown')}.\n"
            "Ask: which doctrine inside this subject controls the answer?"
        ),
        "Hint 3 - Rule skeleton": rule_hint,
        "Hint 4 - Trigger facts": make_trigger_fact_hint(qd),
        "Hint 5 - Trap warning": make_short_hint(qd.get("traps", ""), max_sentences=3, max_chars=700),
    }


def clean_hint_display_text(text):
    if not text:
        return "No hint available yet."

    lines = []

    for line in str(text).replace("\r\n", "\n").replace("\r", "\n").splitlines():
        line = re.sub(r"[ \t]+", " ", line).strip()

        if not line:
            continue

        if re.match(r"^\d+\.\s*(?:\.\.\.)?$", line):
            continue

        if re.match(r"^\d+\.\s+", line) and re.search(
            r"\b(Explain|Should|Would|Did|Does|Is|Are|Can|May|Assuming)\b",
            line,
            flags=re.IGNORECASE,
        ):
            continue

        lines.append(line)

    cleaned = "\n".join(lines)
    cleaned = re.sub(r"\n{2,}", "\n", cleaned)
    cleaned = re.sub(r"^[A-Z]\.\s+(?=[A-Z][a-z])", "", cleaned)
    return cleaned.strip() or "No hint available yet."


def render_hint_text(title, text):
    safe_title = escape_display_text(title)
    safe_text = escape_display_text(clean_hint_display_text(text))

    st.markdown(
        (
            '<div class="hint-box">'
            f'<div class="hint-title">{safe_title}</div>'
            f'<div class="hint-text">{safe_text}</div>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


def render_progressive_hints(qd):
    st.markdown("### Progressive Hints")
    st.caption("Use the smallest hint possible. A hint is not the answer.")

    hints = make_progressive_hints(qd)
    outline_matches = find_best_outline_rules_for_question(
        qd.get("subject", ""),
        qd.get("tested_issues", ""),
        qd.get("rules", ""),
        qd.get("traps", ""),
        limit=3,
    )

    for hint_title, hint_text in hints.items():
        with st.expander(hint_title, expanded=False):
            if hint_title.startswith("Hint 1"):
                render_call_text("Call of the Question", qd.get("call_of_question", ""))
            elif hint_title.startswith("Hint 4"):
                render_hint_text(hint_title, clean_trigger_facts_text(hint_text))
            else:
                render_hint_text(hint_title, hint_text)
            st.warning("Try to write again before opening the next hint.")

        if hint_title.startswith("Hint 2"):
            with st.expander("Plug & Play Writing Template", expanded=False):
                plug_matches = find_best_plug_play_for_call(
                    qd.get("subject", ""),
                    qd.get("call_of_question", ""),
                    qd.get("question_text", ""),
                    qd.get("tested_issues", ""),
                    limit=2,
                )

                if plug_matches:
                    for template in plug_matches:
                        render_plug_play_template(template)
                else:
                    st.info("No Plug & Play template matched yet.")

            with st.expander("Exact Attack Outline Rule", expanded=False):
                if outline_matches:
                    for rule in outline_matches:
                        render_attack_rule_box(rule)
                else:
                    st.info("No matching outline rule found yet. Use model-rule hint instead.")

    hints_used = st.slider("How many hints did you use?", 0, 5, 0)
    return hints_used


def make_mini_fact_packet(question_text, max_chars=1800):
    if not question_text:
        return "No question text available."

    paragraphs = [
        paragraph.strip()
        for paragraph in str(question_text).splitlines()
        if len(paragraph.strip()) >= 25
    ]

    if not paragraphs:
        return "No question text available."

    packet = []
    current_length = 0
    truncated = False

    for paragraph in paragraphs:
        next_length = current_length + len(paragraph) + (2 if packet else 0)

        if next_length > max_chars:
            truncated = True
            break

        packet.append(paragraph)
        current_length = next_length

    if not packet:
        packet.append(paragraphs[0][:max_chars].strip())
        truncated = len(paragraphs[0]) > max_chars

    result = "\n\n".join(packet)

    if truncated:
        result += "\n\n... [mini packet ends - open full question if needed]"

    return result


def extract_subquestions(call_text):
    text = clean_call_text(call_text)

    if not text:
        return [{"label": "Question", "text": "No call of the question available.", "subparts": []}]

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    subquestions = []
    current = None

    top_level_pattern = re.compile(r"^(\d+)\.\s*(.*)")
    numbered_subpart_pattern = re.compile(r"^(\d+)\(([a-z])\)\.\s*(.*)", re.IGNORECASE)
    subpart_pattern = re.compile(r"^([a-z]\.)\s*(.*)", re.IGNORECASE)

    for line in lines:
        numbered_subpart = numbered_subpart_pattern.match(line)
        top = top_level_pattern.match(line)
        sub = subpart_pattern.match(line)

        if numbered_subpart:
            question_number = numbered_subpart.group(1)
            subpart_label = f"{numbered_subpart.group(2)}."
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

            label = f"Question {top.group(1)}"
            body = top.group(2).strip()

            current = {
                "label": label,
                "text": body,
                "subparts": [],
            }

        elif sub and current:
            current["subparts"].append({
                "label": sub.group(1),
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
        question["text"] = question.get("text", "").strip()
        question["subparts"] = [
            subpart
            for subpart in question.get("subparts", [])
            if subpart.get("text", "").strip()
        ]

        if question["text"] or question["subparts"]:
            cleaned.append(question)

    if not cleaned:
        return [{"label": "Question", "text": text, "subparts": []}]

    return cleaned


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
        r"Â©\s*\d{4}.*",
        r"National Conference of Bar Examiners.*",
        r"These materials are copyrighted.*",
        r"Studicata.*",
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
    text = re.sub(
        r"\s+((?:Was|Is|Are|Did|Does|Do|Can|Could|Should|Will|Would|Assuming that)\b)",
        r"\n\1",
        text,
    )
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

    top_level_pattern = re.compile(r"^(\d+)\.\s*(.*)")
    subpart_pattern = re.compile(r"^([a-z]\.)\s*(.*)", re.IGNORECASE)
    call_start_pattern = re.compile(
        r"^(Was|Is|Are|Did|Does|Do|Can|Could|Should|Will|Would|Assuming that)\b",
    )

    has_numbered_call = any(top_level_pattern.match(line) for line in lines)

    if not has_numbered_call:
        while lines and not call_start_pattern.match(lines[0]):
            lines.pop(0)

    for line in lines:
        top = top_level_pattern.match(line)
        sub = subpart_pattern.match(line)

        if top:
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

    for question in subquestions:
        label = escape_display_text(question.get("label", "Question"))
        question_text = escape_display_text(question.get("text", ""))
        subparts_html = ""

        for subpart in question.get("subparts", []):
            subpart_label = escape_display_text(subpart.get("label", ""))
            subpart_text = escape_display_text(subpart.get("text", ""))
            subparts_html += (
                '<div class="call-subpart">'
                f'<span class="call-subpart-label">{subpart_label}</span>'
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


def render_subquestion_card(qd, subq, index, hints_used=0):
    label = subq.get("label") or f"Call {index}"
    call_text = subq.get("text", "").strip()
    if subq.get("subparts"):
        subpart_text = "\n".join(
            [f"{part['label']} {part['text']}" for part in subq["subparts"]]
        )
        full_call = f"{call_text}\n{subpart_text}".strip()
    else:
        full_call = call_text or "No call text available."

    key_prefix = f"mini_{qd['id']}_{index}_{re.sub(r'[^A-Za-z0-9]+', '_', label)}"

    st.markdown(f"#### {label}")
    render_call_text("Mini Call", full_call)

    with st.expander(f"Plug & Play Template for {label}", expanded=False):
        plug_matches = find_best_plug_play_for_call(
            qd.get("subject", ""),
            full_call,
            qd.get("question_text", ""),
            qd.get("tested_issues", ""),
            limit=2,
        )

        if plug_matches:
            for template in plug_matches:
                render_plug_play_template(template)
        else:
            st.info("No matching Plug & Play template found yet.")

        plug_search_term = st.text_input(
            f"Search Plug & Play templates for {label}",
            placeholder="personal jurisdiction, hearsay, statute of frauds",
            key=f"plug_search_{qd['id']}_{index}",
        )

        if plug_search_term:
            plug_results = search_plug_play_templates(
                plug_search_term,
                subject=qd.get("subject", ""),
                limit=5,
            )

            if plug_results:
                for template in plug_results:
                    render_plug_play_template(template)
            else:
                st.info("No Plug & Play templates matched that search.")

    if (
        "find_best_outline_rules_for_question" in globals()
        and "render_attack_rule_box" in globals()
    ):
        search_blob = "\n\n".join(
            [
                full_call,
                qd.get("tested_issues", ""),
                qd.get("rules", ""),
                qd.get("traps", ""),
            ]
        )
        outline_matches = find_best_outline_rules_for_question(
            qd.get("subject", ""),
            search_blob,
            qd.get("rules", ""),
            qd.get("traps", ""),
            limit=2,
        )

        with st.expander(f"Exact Rule Support for {label}", expanded=False):
            if outline_matches:
                for rule in outline_matches:
                    render_attack_rule_box(rule)
            else:
                st.info("No exact outline rule found for this call yet.")

    issue_spotted = st.text_area(
        f"{label} - Your issue",
        placeholder="Example: Whether the facts satisfy the legal test asked by this call.",
        height=90,
        key=f"{key_prefix}_issue",
    )

    rule_from_memory = st.text_area(
        f"{label} - Your rule",
        placeholder="Write the rule from memory before opening answers or hints.",
        height=120,
        key=f"{key_prefix}_rule",
    )

    trigger_facts = st.text_area(
        f"{label} - Trigger facts",
        placeholder="Which facts made this issue appear?",
        height=90,
        key=f"{key_prefix}_facts",
    )

    micro_conclusion = st.text_area(
        f"{label} - Micro-conclusion",
        placeholder="Therefore, likely yes/no because...",
        height=80,
        key=f"{key_prefix}_conclusion",
    )

    use_template = st.checkbox(
        f"Use Plug & Play answer structure for {label}",
        value=True,
        key=f"use_plug_template_{qd['id']}_{index}",
    )

    issue_sentence = ""
    rule_sentence = ""
    application = ""
    counterargument = ""
    conclusion = ""

    if use_template:
        st.markdown("##### Plug & Play Structured Mini-Answer")
        issue_sentence = st.text_area(
            f"{label} - Issue sentence",
            placeholder="The issue is whether...",
            height=70,
            key=f"{key_prefix}_plug_issue",
        )
        rule_sentence = st.text_area(
            f"{label} - Rule sentence",
            placeholder="Under the rule...",
            height=90,
            key=f"{key_prefix}_plug_rule",
        )
        application = st.text_area(
            f"{label} - Application paragraph",
            placeholder="Here, ... because ...",
            height=130,
            key=f"{key_prefix}_plug_application",
        )
        counterargument = st.text_area(
            f"{label} - Counterargument / trap",
            placeholder="However, ...",
            height=90,
            key=f"{key_prefix}_plug_counter",
        )
        conclusion = st.text_area(
            f"{label} - Conclusion",
            placeholder="Therefore...",
            height=70,
            key=f"{key_prefix}_plug_conclusion",
        )

    return f"""
CALL {label}:
{full_call}

ISSUE:
{issue_spotted}

RULE:
{rule_from_memory}

TRIGGER FACTS:
{trigger_facts}

MICRO-CONCLUSION:
{micro_conclusion}

PLUG & PLAY STRUCTURE USED:
{use_template}

ISSUE SENTENCE:
{issue_sentence}

RULE SENTENCE:
{rule_sentence}

APPLICATION:
{application}

COUNTERARGUMENT / TRAP:
{counterargument}

CONCLUSION:
{conclusion}

HINTS USED AT TIME OF DRILL:
{hints_used}/5
"""


def format_review_date(value):
    if not value:
        return "not scheduled"

    return str(value)[:10]


def render_question_overview(qd):
    st.subheader(f"{qd['exam_name']} - Question {qd['question_number']}")
    st.caption(
        f"Subject: {qd['subject']} | July 2026 status: {qd['july_2026_status']} | "
        f"Priority: {qd['priority']} | Source: {qd['source']} | "
        f"Next review: {format_review_date(qd['next_review_at'])}"
    )
    render_data_health_warning(qd)


def question_picker(active_default=True, due_only=False):
    subjects = ["All"] + get_subjects()
    statuses = ["All"] + get_statuses()

    col1, col2, col3 = st.columns(3)

    with col1:
        subject_filter = st.selectbox("Subject filter", subjects)

    with col2:
        status_filter = st.selectbox("July 2026 status", statuses)

    with col3:
        active_only = st.checkbox("Active July 2026 only", value=active_default)

    search = st.text_input(
        "Search issues / rules / traps",
        placeholder="e.g., hearsay, PMSI, personal jurisdiction"
    )

    questions = get_questions(
        active_only=active_only,
        subject=subject_filter,
        status=status_filter,
        search=search,
        due_only=due_only
    )

    if not questions:
        st.warning("No matching questions. Broaden the filter or import more.")
        return None

    st.caption(f"{len(questions)} matching questions")

    labels = []
    for row in questions:
        due = f" | Due {format_review_date(row[6])}" if row[6] else ""
        labels.append(
            f"{row[0]} - {row[1]} Q{row[2]} - {row[3]} - {row[4]} - Priority {row[5]}{due}"
        )

    picker_key = f"question_picker_{active_default}_{due_only}_{subject_filter}_{status_filter}_{search}"
    select_key = f"{picker_key}_select"

    selected_index = min(st.session_state.get(picker_key, 0), len(labels) - 1)

    if select_key not in st.session_state or st.session_state[select_key] not in labels:
        st.session_state[select_key] = labels[selected_index]
    else:
        selected_index = labels.index(st.session_state[select_key])

    surprise_col, count_col = st.columns([1, 3])

    with surprise_col:
        if st.button("Pick for me", key=f"{picker_key}_surprise"):
            selected_index = random.randrange(len(questions))
            st.session_state[picker_key] = selected_index
            st.session_state[select_key] = labels[selected_index]

    with count_col:
        st.write("Use the picker when you know what you want; use random when starting is the hard part.")

    selected_label = st.selectbox("Pick a question", labels, key=select_key)
    selected_index = labels.index(selected_label)
    st.session_state[picker_key] = selected_index

    return questions[selected_index][0]


menu = st.sidebar.radio(
    "Choose Mode",
    [
        "Dashboard",
        "Bulk Import MEE Bank",
        "Add MEE Question",
        "MEE Muscle Ladder",
        "Mini Essay Drill",
        "Issue Spotting Drill",
        "Rule Retrieval Drill",
        "Timed IRAC Drill",
        "Due Review Queue",
        "Review Attempts",
        "Attack Outline Rules",
        "Plug & Play Templates"
    ]
)

st.sidebar.markdown("### Reading Comfort")
ADHD_READING_MODE = st.sidebar.checkbox("Dyslexia / ADHD reading mode", value=False)

if ADHD_READING_MODE:
    READING_FONT_SIZE = 20
    READING_LINE_HEIGHT = 2.05
    READING_MAX_WIDTH = 820
    READING_BOX_PADDING = "1.6rem 1.8rem"
    COMPACT_MODE = False
else:
    READING_FONT_SIZE = st.sidebar.slider("Legal text size", 15, 24, 18)
    READING_LINE_HEIGHT = 1.55
    READING_MAX_WIDTH = 1280
    READING_BOX_PADDING = "0.9rem 1rem"
    COMPACT_MODE = st.sidebar.checkbox("Compact mode", value=False)

if COMPACT_MODE and not ADHD_READING_MODE:
    READING_FONT_SIZE = 16
    READING_LINE_HEIGHT = 1.5
    READING_BOX_PADDING = "0.85rem 1rem"

st.markdown(f"""
<style>
.readable-box {{
    background: rgba(255, 255, 255, 0.96) !important;
    border: 1.5px solid #CDEBFF !important;
    border-radius: 14px !important;
    padding: {READING_BOX_PADDING} !important;
    margin: 0.55rem 0 0.8rem 0 !important;
    box-shadow: 0 4px 14px rgba(29, 78, 137, 0.07) !important;
    max-width: min({READING_MAX_WIDTH}px, 100%) !important;
}}

.readable-title {{
    color: #1D4E89 !important;
    font-weight: 850 !important;
    font-size: 1rem !important;
    margin-bottom: 0.4rem !important;
    padding-bottom: 0.25rem !important;
    border-bottom: 2px solid #DBEAFE !important;
}}

.readable-text {{
    color: #102033 !important;
    font-size: {READING_FONT_SIZE}px !important;
    line-height: {READING_LINE_HEIGHT} !important;
    letter-spacing: 0 !important;
    white-space: pre-line !important;
    word-break: normal !important;
    overflow-wrap: break-word !important;
}}

.readable-text p {{
    margin-bottom: 0.6rem !important;
}}

.readable-text::selection {{
    background: #DDF4FF !important;
}}

textarea {{
    font-size: {READING_FONT_SIZE}px !important;
    line-height: {READING_LINE_HEIGHT} !important;
}}

[data-testid="stTextArea"] textarea {{
    min-height: 120px;
}}

.stMarkdown {{
    line-height: {READING_LINE_HEIGHT};
}}

{" .block-container { max-width: 980px !important; } " if ADHD_READING_MODE else ""}
</style>
""", unsafe_allow_html=True)

if ADHD_READING_MODE:
    st.info("ADHD Reading Mode is on: bigger text, wider spacing, and less visual crowding.")


if menu == "Dashboard":
    st.header("Today's Training Mission")

    stats = get_dashboard_stats()

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Questions", stats["total_questions"])
    col2.metric("July 2026 Active", stats["active_questions"])
    col3.metric("Attempts", stats["total_attempts"])
    col4.metric("Average Score", stats["avg_score"])
    col5.metric("Due Reviews", stats["due_reviews"])

    col1, col2, col3 = st.columns(3)
    col1.metric("Today", f"{stats['today_attempts']} attempts", f"{stats['today_minutes']} min")
    col2.metric("Total Practice Time", f"{stats['total_minutes']} min")
    col3.metric("Unpracticed Questions", stats["unpracticed_questions"])

    st.markdown("""
    ### Minimum Practice Session: 35 minutes

    1. **5 min** - Issue spotting
    2. **7 min** - Rule retrieval
    3. **15 min** - IRAC paragraph
    4. **5 min** - Self-grade
    5. **3 min** - Make one weak-rule note

    **Rule:** attempt retrieval before reviewing the answer.
    """)

    st.info("The goal is to build reliable recall, not to wait until the question feels easy.")

    st.subheader("Today's Quick Win")
    st.markdown("""
    - **Do one Level 1 Mini Run**
    - **Save the attempt**
    - **Stop after 7 minutes if energy is low**
    """)

    st.subheader("Today's Plug & Play Rep")
    st.markdown("""
    1. Pick one Mini Essay Drill.
    2. Answer one call without looking.
    3. Open Plug & Play template.
    4. Rewrite your answer using the template.
    5. Save the attempt.
    """)

    st.subheader("Smart Practice Queue")

    if stats["recommended_queue"]:
        queue_df = pd.DataFrame(
            stats["recommended_queue"],
            columns=[
                "ID",
                "Exam",
                "Q",
                "Subject",
                "Status",
                "Priority",
                "Next Review",
                "Last Practiced",
                "Avg Score",
                "Attempts"
            ]
        )

        queue_df["Avg Score"] = queue_df["Avg Score"].apply(
            lambda value: "New" if value == -1 else round(value, 2)
        )
        queue_df["Next Review"] = queue_df["Next Review"].fillna("not scheduled")
        queue_df["Last Practiced"] = queue_df["Last Practiced"].fillna("never")

        st.dataframe(queue_df, use_container_width=True, hide_index=True)
    else:
        st.info("No active questions found yet. Import or add a few questions to build the queue.")

    col1, col2 = st.columns(2)

    with col1:
        if stats["subject_stats"]:
            st.subheader("Weakest Subjects First")

            subject_df = pd.DataFrame(
                stats["subject_stats"],
                columns=["Subject", "Average Score", "Attempts"]
            )

            st.dataframe(subject_df, use_container_width=True, hide_index=True)
        else:
            st.subheader("Weakest Subjects First")
            st.info("No attempts yet. Complete one short practice attempt to activate this view.")

    with col2:
        st.subheader("Due and Untouched")

        if stats["due_by_subject"]:
            due_df = pd.DataFrame(stats["due_by_subject"], columns=["Subject", "Due"])
            st.dataframe(due_df, use_container_width=True, hide_index=True)
        elif stats["untouched_by_subject"]:
            untouched_df = pd.DataFrame(
                stats["untouched_by_subject"],
                columns=["Subject", "Untouched Active"]
            )
            st.dataframe(untouched_df, use_container_width=True, hide_index=True)
        else:
            st.success("No due reviews and no untouched active questions.")

    st.success("Start with retrieval. Polish after the first attempt.")


elif menu == "Bulk Import MEE Bank":
    st.header("Bulk Import MEE Bank")

    st.markdown("""
    Use this page to import previous MEE questions from CSV.

    **Best workflow:**  
    1. Extract or paste question data into CSV.  
    2. Tag subject, issues, rules, trigger facts, and traps.  
    3. Mark July 2026 relevance.  
    4. Practice from the app.

    **Practice rule:** import 10-20 questions at a time, then return to training.
    """)

    template = pd.DataFrame([
        {
            "exam_name": "February 2021",
            "exam_year": 2021,
            "exam_season": "February",
            "question_number": "1",
            "subject": "Civil Procedure",
            "secondary_subjects": "",
            "question_text": "[Paste private question text here]",
            "call_of_question": "What legal result should the court reach? Explain.",
            "tested_issues": "Issue one; issue two; issue three",
            "rules": "Rule one. Rule two. Rule three.",
            "trigger_facts": "Fact that triggers issue one; fact that triggers issue two; fact that creates a trap",
            "traps": "Common wrong turn; missing element; misleading fact",
            "model_points": "What a passing answer must discuss.",
            "active_for_july_2026": 1,
            "july_2026_status": "Active standalone MEE",
            "priority": 5,
            "source": "FEB2021QA.pdf"
        }
    ])

    csv_buffer = StringIO()
    template.to_csv(csv_buffer, index=False)

    st.download_button(
        "Download CSV Template",
        data=csv_buffer.getvalue(),
        file_name="mee_import_template.csv",
        mime="text/csv"
    )
    st.caption("💡 Tip: Press Enter twice between paragraphs for clean spacing when displayed.")

    uploaded_file = st.file_uploader("Upload completed CSV", type=["csv"])

    required_columns = [
        "exam_name",
        "question_number",
        "subject",
        "question_text",
        "call_of_question",
        "tested_issues",
        "rules",
        "trigger_facts",
        "traps",
        "model_points"
    ]

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file).fillna("")

        st.subheader("Preview")
        st.dataframe(df.head(20), use_container_width=True)

        missing = [col for col in required_columns if col not in df.columns]

        if missing:
            st.error(f"Missing required columns: {missing}")
        else:
            st.success(f"Ready to import {len(df)} rows.")

            if st.button("Import Questions"):
                imported = 0

                for _, row in df.iterrows():
                    add_question(
                        exam_name=row.get("exam_name", ""),
                        question_number=str(row.get("question_number", "")),
                        subject=row.get("subject", ""),
                        question_text=row.get("question_text", ""),
                        call_of_question=row.get("call_of_question", ""),
                        tested_issues=row.get("tested_issues", ""),
                        rules=row.get("rules", ""),
                        trigger_facts=row.get("trigger_facts", ""),
                        traps=row.get("traps", ""),
                        model_points=row.get("model_points", ""),
                        active_for_july_2026=parse_bool(row.get("active_for_july_2026", 1)),
                        exam_year=parse_optional_int(row.get("exam_year", ""), default=None),
                        exam_season=row.get("exam_season", ""),
                        secondary_subjects=row.get("secondary_subjects", ""),
                        july_2026_status=row.get("july_2026_status", "Active standalone MEE"),
                        priority=parse_optional_int(row.get("priority", 3), default=3),
                        source=row.get("source", "")
                    )

                    imported += 1

                st.success(f"Imported {imported} MEE questions.")


elif menu == "Add MEE Question":
    st.header("Add MEE Question")

    st.markdown("Manual entry is best for high-value questions that need custom tagging.")

    with st.form("add_question_form"):
        col1, col2, col3 = st.columns(3)

        with col1:
            exam_name = st.text_input("Exam name", placeholder="February 2021")
            exam_year = st.number_input("Exam year", min_value=1990, max_value=2030, value=2021)
            exam_season = st.selectbox("Exam season", ["February", "July", "Other"])

        with col2:
            question_number = st.text_input("Question number", placeholder="1")
            subject = st.text_input("Primary subject", placeholder="Civil Procedure")
            secondary_subjects = st.text_input("Secondary subjects", placeholder="Evidence, Torts")

        with col3:
            july_2026_status = st.selectbox(
                "July 2026 status",
                [
                    "Active standalone MEE",
                    "Retired standalone - background only",
                    "MPT background only",
                    "Historical / low priority"
                ]
            )
            priority = st.slider("Priority", 1, 5, 3)
            source = st.text_input("Source", placeholder="FEB2021QA.pdf")

        active_for_july_2026 = st.checkbox(
            "Active for July 2026 standalone MEE",
            value=True
        )

        question_text = st.text_area("Question text", height=250)
        st.caption("💡 Tip: Press Enter twice between paragraphs for clean spacing when displayed.")
        call_of_question = st.text_area("Call of the question", height=100)

        tested_issues = st.text_area(
            "Tested issues",
            placeholder="Issue one; issue two; issue three",
            height=120
        )

        rules = st.text_area(
            "Rules",
            placeholder="Paste concise rule statements here.",
            height=150
        )

        trigger_facts = st.text_area(
            "Trigger facts",
            placeholder="Fact that triggers issue one; fact that triggers issue two; fact that creates a trap",
            height=120
        )

        traps = st.text_area(
            "Traps",
            placeholder="Common wrong turn; missing element; misleading fact.",
            height=120
        )

        model_points = st.text_area(
            "Model answer points",
            placeholder="What a passing answer must discuss.",
            height=150
        )

        submitted = st.form_submit_button("Save Question")

        if submitted:
            add_question(
                exam_name=exam_name,
                question_number=question_number,
                subject=subject,
                question_text=question_text,
                call_of_question=call_of_question,
                tested_issues=tested_issues,
                rules=rules,
                trigger_facts=trigger_facts,
                traps=traps,
                model_points=model_points,
                active_for_july_2026=active_for_july_2026,
                exam_year=exam_year,
                exam_season=exam_season,
                secondary_subjects=secondary_subjects,
                july_2026_status=july_2026_status,
                priority=priority,
                source=source
            )

            st.success("Question saved.")


elif menu == "MEE Muscle Ladder":
    st.header("MEE Muscle Ladder")
    st.caption("Train gradually: issue -> rule -> trigger facts -> IRAC -> full essay.")

    st.markdown("""
    ### How this works

    You are not trying to write a perfect essay immediately.

    You are training the reflex:

    **Call -> Issue -> Rule -> Facts -> Conclusion**

    Fact without rule = story. Rule without fact = flashcard. We need both.
    """)

    question_id = question_picker(active_default=True)

    if question_id:
        q = get_question_by_id(question_id)

        if q is None:
            st.error("Question not found.")
        else:
            qd = unpack_question(q)

            st.subheader(f"{qd['exam_name']} Q{qd['question_number']} - {qd['subject']}")
            st.caption(
                f"July 2026 status: {qd['july_2026_status']} | "
                f"Priority: {qd['priority']} | Source: {qd['source']}"
            )
            render_data_health_warning(qd)

            level = st.selectbox(
                "Choose training level",
                [
                    "Level 1 - Issue + Rule Mini Run - 7 min",
                    "Level 2 - Trigger Fact Hunt - 10 min",
                    "Level 3 - Mini IRAC - 15 min",
                    "Level 4 - Skeleton Essay - 20 min",
                    "Level 5 - Full MEE - 30 min"
                ]
            )

            if level.startswith("Level 1"):
                target_minutes = 7
                st.success("Goal: spot the issues and write the rules from memory. No full essay.")
            elif level.startswith("Level 2"):
                target_minutes = 10
                st.success("Goal: connect each issue/rule to trigger facts.")
            elif level.startswith("Level 3"):
                target_minutes = 15
                st.success("Goal: write one strong IRAC paragraph.")
            elif level.startswith("Level 4"):
                target_minutes = 20
                st.success("Goal: outline the entire essay.")
            else:
                target_minutes = 30
                st.success("Goal: full timed MEE simulation.")

            st.info(f"Set a timer for {target_minutes} minutes and complete the attempt before polishing.")
            st.warning("Attempt retrieval before revealing the answer bank.")

            with st.expander("Call of the Question", expanded=True):
                render_call_text("Call of the Question", qd["call_of_question"])

            with st.expander("Question Text", expanded=True):
                render_prompt(extract_fact_pattern_only(qd["question_text"], qd["call_of_question"]))

            hints_used = render_progressive_hints(qd)

            st.divider()

            if level.startswith("Level 1"):
                st.markdown("## Level 1: Issue + Rule Mini Run")

                user_issues = st.text_area(
                    "Step A - What issues do you see?",
                    placeholder="Example: list each legal issue raised by this call.",
                    height=120
                )

                user_rules = st.text_area(
                    "Step B - Write the rules from memory",
                    placeholder="Example: write the governing test, elements, or standard from memory.",
                    height=160
                )

                user_facts = st.text_area(
                    "Optional - Which facts triggered those issues?",
                    placeholder="Example: quote or summarize the facts that connect to each rule element.",
                    height=100
                )

                combined_answer = f"""
ISSUES:
{user_issues}

RULES:
{user_rules}

TRIGGER FACTS:
{user_facts}
"""

            elif level.startswith("Level 2"):
                st.markdown("## Level 2: Trigger Fact Hunt")

                combined_answer = st.text_area(
                    "For each issue, write: Issue -> Rule -> Trigger Facts",
                    placeholder=(
                        "Issue 1: ___\n"
                        "Rule: ___\n"
                        "Trigger facts: ___\n\n"
                        "Issue 2: ___\n"
                        "Rule: ___\n"
                        "Trigger facts: ___"
                    ),
                    height=260
                )

            elif level.startswith("Level 3"):
                st.markdown("## Level 3: Mini IRAC")

                combined_answer = st.text_area(
                    "Write ONE strong IRAC paragraph",
                    placeholder=(
                        "Issue: Whether ___\n"
                        "Rule: Under ___\n"
                        "Application: Here, ___ because ___\n"
                        "Counterargument: However, ___\n"
                        "Conclusion: Therefore, ___"
                    ),
                    height=280
                )

            elif level.startswith("Level 4"):
                st.markdown("## Level 4: Skeleton Essay")

                combined_answer = st.text_area(
                    "Outline the full essay. Short bullets only.",
                    placeholder=(
                        "Call 1:\n"
                        "- Issue:\n"
                        "- Rule:\n"
                        "- Facts:\n"
                        "- Conclusion:\n\n"
                        "Call 2:\n"
                        "- Issue:\n"
                        "- Rule:\n"
                        "- Facts:\n"
                        "- Conclusion:"
                    ),
                    height=320
                )

            else:
                st.markdown("## Level 5: Full MEE")

                combined_answer = st.text_area(
                    "Write the full timed essay",
                    height=420
                )

            st.divider()

            st.warning("Reveal only after you have attempted retrieval.")

            if st.button("Reveal Answer Bank"):
                render_tested_issues_text("Tested Issues", qd["tested_issues"])
                render_readable_text("Rules", qd["rules"], READING_FONT_SIZE)
                render_trigger_facts_text("Trigger Facts", qd["trigger_facts"])
                render_readable_text("Traps", qd["traps"], READING_FONT_SIZE)

                with st.expander("Model Points - open after self-grading", expanded=False):
                    render_readable_text("Model Points", qd["model_points"], READING_FONT_SIZE)

            st.divider()

            col1, col2, col3 = st.columns(3)

            with col1:
                issue_score = st.slider("Issue score", 0, 5, 0)

            with col2:
                rule_score = st.slider("Rule score", 0, 5, 0)

            with col3:
                fact_score = st.slider("Fact connection score", 0, 5, 0)

            average_score = round((issue_score + rule_score + fact_score) / 3)
            adjusted_score = max(0, average_score - (1 if hints_used >= 3 else 0))

            score_col1, score_col2 = st.columns(2)
            score_col1.metric("Raw self-score", f"{average_score}/5")
            score_col2.metric("Adjusted training score", f"{adjusted_score}/5")

            missed = st.text_area(
                "What did you miss?",
                placeholder="Example: I spotted the broad issue but missed one required element.",
                height=100
            )

            notes = st.text_area(
                "Fix note for future you",
                placeholder="Example: Next time ask which rule element each fact proves.",
                height=100
            )

            notes_with_hints = f"Hints used: {hints_used}/5\n\n{notes}"

            if st.button("Save Muscle Ladder Attempt"):
                save_attempt(
                    qd["id"],
                    level,
                    combined_answer,
                    adjusted_score,
                    missed,
                    notes_with_hints,
                    minutes_spent=target_minutes
                )

                st.success("Saved. This question is now scheduled for review based on your score.")
                st.balloons()


elif menu == "Mini Essay Drill":
    st.header("Mini Essay Drill")
    st.caption("Previous exam question -> issue -> rule -> trigger facts. No full essay.")
    st.info("This is an 8-minute drill focused on recognition, rule recall, and fact connection.")

    question_id = question_picker(active_default=True)

    if question_id:
        q = get_question_by_id(question_id)

        if q is None:
            st.error("Question not found.")
        else:
            qd = unpack_question(q)

            st.subheader(f"{qd['exam_name']} Q{qd['question_number']} - {qd['subject']}")
            st.caption(
                f"July 2026 status: {qd['july_2026_status']} | "
                f"Priority: {qd['priority']} | Source: {qd['source']}"
            )
            render_data_health_warning(qd)
            subquestions = extract_subquestions(qd["call_of_question"])

            with st.expander("1. Call of the Question - read this first", expanded=True):
                render_call_text("Call of the Question", qd["call_of_question"])

            st.markdown("### Mini Fact Packet")
            render_prompt(make_mini_fact_packet(extract_fact_pattern_only(qd["question_text"], qd["call_of_question"])))

            with st.expander("Open full question if needed", expanded=False):
                render_prompt(extract_fact_pattern_only(qd["question_text"], qd["call_of_question"]))

            try:
                hints_used = render_progressive_hints(qd)
            except NameError:
                hints_used = 0

            st.markdown("### Breakout Calls")
            st.caption("Answer one call at a time. Compact call formatting is intentional.")

            all_subanswers = []

            for index, subq in enumerate(subquestions, start=1):
                with st.container():
                    st.markdown("---")
                    answer_piece = render_subquestion_card(qd, subq, index, hints_used)
                    all_subanswers.append(answer_piece)

            combined_answer = "\n\n====================\n\n".join(all_subanswers)

            with st.expander("Search Attack Outline rules manually", expanded=False):
                search_term = st.text_input(
                    "Search Attack Outline rules",
                    placeholder="personal jurisdiction, hearsay, statute of frauds"
                )

                if search_term:
                    results = search_outline_rules(search_term, subject=qd["subject"], limit=5)

                    if results:
                        for rule in results:
                            render_attack_rule_box(rule)
                    else:
                        st.info("No Attack Outline rules matched that search.")

            st.divider()
            st.warning("Reveal only after you have written at least one issue and one rule.")

            if st.button("Reveal Issues + Rules"):
                render_tested_issues_text("Tested Issues", qd["tested_issues"])
                render_readable_text("Rules", qd["rules"], READING_FONT_SIZE)
                render_trigger_facts_text("Trigger Facts", qd["trigger_facts"])
                render_readable_text("Traps", qd["traps"], READING_FONT_SIZE)

                with st.expander("Model Points - open only after self-grading", expanded=False):
                    render_readable_text("Model Points", qd["model_points"], READING_FONT_SIZE)

            st.divider()
            st.info(
                "Score the whole mini drill honestly. If you needed hints or only got one call right, "
                "reserve a 5 for a complete, mostly independent answer."
            )

            col1, col2, col3 = st.columns(3)

            with col1:
                issue_score = st.slider("Issue spotting score", 0, 5, 0)

            with col2:
                rule_score = st.slider("Rule recall score", 0, 5, 0)

            with col3:
                fact_score = st.slider("Fact trigger score", 0, 5, 0)

            raw_score = round((issue_score + rule_score + fact_score) / 3)
            adjusted_score = max(0, raw_score - 1) if hints_used >= 3 else raw_score

            score_col1, score_col2 = st.columns(2)
            score_col1.metric("Raw score", f"{raw_score}/5")
            score_col2.metric("Adjusted training score", f"{adjusted_score}/5")

            missed = st.text_area(
                "What did you miss?",
                placeholder="Example: I spotted the broad issue but missed one required element.",
                height=100
            )

            notes = st.text_area(
                "Fix note for future you",
                placeholder="Example: Next time map issue -> rule -> trigger fact before writing.",
                height=100
            )

            if st.button("Save Mini Essay Attempt"):
                notes_with_hints = f"Hints used: {hints_used}/5\n\n{notes}"

                save_attempt(
                    qd["id"],
                    "Mini Essay Drill - Broken Out by Calls",
                    combined_answer,
                    adjusted_score,
                    missed,
                    notes_with_hints,
                    minutes_spent=8
                )

                st.success("Mini essay attempt saved.")
                st.balloons()

            st.info(
                "Mini Essay Rule: if you can spot the issue and write the rule from memory, "
                "the full essay becomes much easier."
            )


elif menu == "Issue Spotting Drill":
    st.header("Issue Spotting Drill")

    question_id = question_picker()

    if question_id:
        q = get_question_by_id(question_id)

        if q is None:
            st.error("Question not found.")
        else:
            qd = unpack_question(q)

            render_question_overview(qd)

            st.info("Timer target: 5 minutes. Read the call first, then identify the legal triggers.")

            with st.expander("Call of the Question", expanded=True):
                render_call_text("Call of the Question", qd["call_of_question"])

            with st.expander("Question Text", expanded=True):
                render_prompt(extract_fact_pattern_only(qd["question_text"], qd["call_of_question"]))

            hints_used = render_progressive_hints(qd)

            user_issues = st.text_area(
                "Your issue list",
                placeholder="List each issue in short phrases.",
                height=180
            )

            confidence = st.slider("Confidence", 1, 5, 3)

            st.warning("Reveal only after you have attempted retrieval.")

            if st.button("Reveal Tested Issues"):
                render_tested_issues_text("Tested Issues", qd["tested_issues"])
                render_trigger_facts_text("Trigger Facts", qd["trigger_facts"])
                render_readable_text("Traps", qd["traps"], READING_FONT_SIZE)

            col1, col2 = st.columns(2)

            with col1:
                self_score = st.slider("Self-score: issue spotting", 0, 5, 0)

            with col2:
                minutes_spent = st.number_input("Minutes spent", min_value=0, max_value=60, value=5)

            missed_issues = st.text_area("Missed issues", height=100)
            notes = st.text_area("Notes for future you", height=100)

            if st.button("Save Issue Spotting Attempt"):
                notes_with_hints = f"Hints used: {hints_used}/5\nConfidence: {confidence}/5\n\n{notes}"

                save_attempt(
                    qd["id"],
                    "Issue Spotting",
                    user_issues,
                    self_score,
                    missed_issues,
                    notes_with_hints,
                    minutes_spent=minutes_spent
                )

                st.success("Attempt saved.")


elif menu == "Rule Retrieval Drill":
    st.header("Rule Retrieval Drill")

    question_id = question_picker()

    if question_id:
        q = get_question_by_id(question_id)

        if q is None:
            st.error("Question not found.")
        else:
            qd = unpack_question(q)

            render_question_overview(qd)

            st.markdown("### Tested Issue Bank")
            render_tested_issues_text("Tested Issues", qd["tested_issues"])

            st.warning("Write the rule from memory before opening the answer.")

            hints_used = render_progressive_hints(qd)

            user_rule = st.text_area(
                "Write the rule from memory",
                placeholder="Under the rule..., elements are...",
                height=180
            )

            st.warning("Reveal only after you have attempted retrieval.")

            if st.button("Reveal Rule"):
                render_readable_text("Rules", qd["rules"], READING_FONT_SIZE)
                render_readable_text("Traps", qd["traps"], READING_FONT_SIZE)

            col1, col2 = st.columns(2)

            with col1:
                self_score = st.slider("Self-score: rule retrieval", 0, 5, 0)

            with col2:
                minutes_spent = st.number_input("Minutes spent", min_value=0, max_value=60, value=7)

            missed_issues = st.text_area("Which rule/element did you miss?", height=100)
            notes = st.text_area("Fix note", height=100)

            if st.button("Save Rule Retrieval Attempt"):
                notes_with_hints = f"Hints used: {hints_used}/5\n\n{notes}"

                save_attempt(
                    qd["id"],
                    "Rule Retrieval",
                    user_rule,
                    self_score,
                    missed_issues,
                    notes_with_hints,
                    minutes_spent=minutes_spent
                )

                st.success("Attempt saved.")


elif menu == "Timed IRAC Drill":
    st.header("Timed IRAC Drill")

    question_id = question_picker()

    if question_id:
        q = get_question_by_id(question_id)

        if q is None:
            st.error("Question not found.")
        else:
            qd = unpack_question(q)

            render_data_health_warning(qd)

            # Thin 4-column metadata strip
            _mc1, _mc2, _mc3, _mc4 = st.columns(4)
            _mc1.metric("Exam", f"{qd['exam_name']} Q{qd['question_number']}")
            _mc2.metric("Subject", qd["subject"])
            _mc3.metric("Status", qd["july_2026_status"] or "—")
            _mc4.metric("Priority", qd["priority"] or "—")

            # Persist hints_used across renders via session state
            _hints_key = f"timed_irac_hints_{question_id}"
            hints_used = st.session_state.get(_hints_key, 0)

            # ── Two-column split layout ──────────────────────────────────────
            left_col, right_col = st.columns([1, 1])

            with left_col:
                st.markdown(
                    '<p style="font-size:0.88rem;font-weight:700;color:#58708A;margin-bottom:0.35rem">📄 Question Prompt</p>',
                    unsafe_allow_html=True,
                )

                _prompt_text = extract_fact_pattern_only(qd["question_text"], qd["call_of_question"])

                if _prompt_text:
                    _fmt = str(_prompt_text).replace("\r\n", "\n").replace("\r", "\n").replace(" ", " ")
                    _fmt = re.sub(r"(?<=[a-z0-9][.!?])\s*(?=[A-Z])", "\n\n", _fmt)
                    _paras = [p.strip() for p in re.split(r"\n+", _fmt) if p.strip()]
                    _inner = "".join(
                        f'<p style="margin-bottom:1.2em">{escape_display_text(p)}</p>'
                        for p in _paras
                    )
                else:
                    _inner = '<p style="color:#58708A;font-style:italic">No prompt stored — retrieve from your materials.</p>'

                st.markdown(
                    f'<div style="height:520px;overflow-y:auto;background:#f8f9fa;padding:1rem;'
                    f'border-left:4px solid #c9a84c;line-height:1.6;font-size:1rem;border-radius:4px">'
                    f'{_inner}</div>',
                    unsafe_allow_html=True,
                )

                # Issue tags as colored pills
                _issues_raw = qd.get("tested_issues", "") or ""
                if _issues_raw:
                    _tags = [t.strip() for t in re.split(r"[;\n]", _issues_raw) if t.strip()]
                    if _tags:
                        _pills = "".join(
                            f'<span style="display:inline-block;background:#dbeafe;color:#1e40af;'
                            f'border-radius:999px;padding:3px 10px;margin:2px 3px 2px 0;'
                            f'font-size:0.8rem;font-weight:600">{escape_display_text(t)}</span>'
                            for t in _tags[:15]
                        )
                        st.markdown(f'<div style="margin-top:0.7rem">{_pills}</div>', unsafe_allow_html=True)

            with right_col:
                # Practice mode selector at top of right column
                _practice_mode = st.radio(
                    "Mode:",
                    ["Full Essay (30 min)", "Focused IRAC (15 min)", "Mini Run (7 min)"],
                    horizontal=True,
                )
                if _practice_mode.startswith("Full"):
                    _target_min = 30
                elif _practice_mode.startswith("Focused"):
                    _target_min = 15
                else:
                    _target_min = 7

                # Timer row
                _tcol1, _tcol2 = st.columns([1, 2])
                with _tcol1:
                    minutes_spent = st.number_input("Minutes spent", min_value=0, max_value=90, value=_target_min)
                with _tcol2:
                    st.caption(f"Target: {_target_min} min")

                answer = st.text_area("Your timed answer", height=320)
                self_score = st.slider("Self-score: timed IRAC", 0, 5, 0)
                missed_issues = st.text_area("Missed issues/rules/facts", height=100)
                notes = st.text_area("What to fix next time", height=100)

                if st.button("Save Timed IRAC Attempt"):
                    notes_with_hints = f"Hints used: {hints_used}/5\n\n{notes}"
                    save_attempt(
                        qd["id"],
                        "Timed IRAC",
                        answer,
                        self_score,
                        missed_issues,
                        notes_with_hints,
                        minutes_spent=minutes_spent,
                    )
                    st.success("Attempt saved.")

            # ── Below the split: call, hints, reveal ────────────────────────
            with st.expander("Call of the Question", expanded=True):
                render_call_text("Call of the Question", qd["call_of_question"])

            _new_hints = render_progressive_hints(qd)
            st.session_state[_hints_key] = _new_hints

            st.warning("Reveal only after you have attempted retrieval.")

            if st.button("Reveal Model Points"):
                with st.expander("Model Points - open after self-grading", expanded=False):
                    render_readable_text("Model Points", qd["model_points"], READING_FONT_SIZE)
                render_readable_text("Rules", qd["rules"], READING_FONT_SIZE)
                render_trigger_facts_text("Trigger Facts", qd["trigger_facts"])
                render_readable_text("Traps", qd["traps"], READING_FONT_SIZE)


elif menu == "Due Review Queue":
    st.header("Due Review Queue")

    st.warning("Review weak areas before they fade.")

    question_id = question_picker(active_default=False, due_only=True)

    if question_id:
        q = get_question_by_id(question_id)

        if q is None:
            st.error("Question not found.")
        else:
            qd = unpack_question(q)

            st.subheader(f"{qd['exam_name']} Q{qd['question_number']} - {qd['subject']}")
            st.caption(
                f"Status: {qd['july_2026_status']} | Priority: {qd['priority']} | "
                f"Last practiced: {qd['last_practiced_at']} | Due: {qd['next_review_at']}"
            )
            render_data_health_warning(qd)

            with st.expander("Call of the Question", expanded=True):
                render_call_text("Call of the Question", qd["call_of_question"])

            st.markdown("### 3-Minute Cold Recall")
            cold_recall = st.text_area(
                "Without looking: list the rule + issue triggers you missed last time.",
                height=160
            )

            st.warning("Reveal only after you have attempted retrieval.")

            if st.button("Reveal Answer Bank"):
                render_tested_issues_text("Tested Issues", qd["tested_issues"])
                render_readable_text("Rules", qd["rules"], READING_FONT_SIZE)
                render_trigger_facts_text("Trigger Facts", qd["trigger_facts"])
                render_readable_text("Traps", qd["traps"], READING_FONT_SIZE)

            score = st.slider("Review score", 0, 5, 0)
            missed = st.text_area("Still weak on:", height=100)
            notes = st.text_area("Fix note:", height=100)

            if st.button("Save Review Attempt"):
                save_attempt(
                    qd["id"],
                    "Due Review",
                    cold_recall,
                    score,
                    missed,
                    notes,
                    minutes_spent=3
                )

                st.success("Review saved. Next review date updated.")


elif menu == "Attack Outline Rules":
    st.header("Attack Outline Rules")
    st.caption("Search exact rules imported from your local Attack Outline PDF.")

    all_rules = get_outline_rules()
    outline_subjects = ["All"] + sorted({row[1] for row in all_rules if row[1]})

    if not all_rules:
        st.warning(
            "No Attack Outline rules imported yet. Put bar attack.pdf in this folder "
            "or static/bar_attack.pdf, then run: python import_attack_outline.py \"bar attack.pdf\""
        )

    col1, col2 = st.columns([2, 1])

    with col1:
        outline_query = st.text_input(
            "Search rules",
            placeholder="personal jurisdiction, hearsay, statute of frauds"
        )

    with col2:
        outline_subject = st.selectbox("Subject", outline_subjects)

    if outline_query:
        outline_results = search_outline_rules(
            outline_query,
            subject=None if outline_subject == "All" else outline_subject,
            limit=25,
        )
    else:
        outline_results = get_outline_rules(
            subject=None if outline_subject == "All" else outline_subject
        )[:25]

    st.caption(f"{len(outline_results)} result(s)")

    for rule in outline_results:
        with st.expander(f"{rule[2]} - {rule[1]} - {rule[3] or 'n/a'}", expanded=False):
            render_attack_rule_box(rule)


elif menu == "Plug & Play Templates":
    st.header("Plug & Play Templates")
    st.caption("Search essay templates for issue statements, rule phrasing, and analysis structure.")

    all_templates = get_plug_play_templates()
    plug_subjects = ["All"] + sorted({row[1] for row in all_templates if row[1]})

    if not all_templates:
        st.warning(
            "No Plug & Play templates imported yet. Run: "
            "python import_plug_play_templates.py "
            "\"LBP Plug and Play-Essay Templates to Help You Write Faster Score Higher.pdf\""
        )

    col1, col2 = st.columns([3, 1])

    with col1:
        plug_query = st.text_input(
            "Search templates",
            placeholder="personal jurisdiction, hearsay, statute of frauds"
        )

    with col2:
        plug_subject = st.selectbox("Subject", plug_subjects, key="plug_page_subject")

    if plug_query:
        plug_results = search_plug_play_templates(
            plug_query,
            subject=None if plug_subject == "All" else plug_subject,
            limit=25,
        )
    else:
        plug_results = get_plug_play_templates(
            subject=None if plug_subject == "All" else plug_subject
        )[:25]

    st.caption(f"{len(plug_results)} result(s)")

    for template in plug_results:
        with st.expander(f"{template[2]} - {template[1]} - page {template[9] or 'n/a'}", expanded=False):
            render_plug_play_template(template)


elif menu == "Review Attempts":
    st.header("Review Attempts")

    attempts = get_attempts()

    if not attempts:
        st.info("No attempts yet.")
    else:
        for row in attempts:
            (
                attempt_id,
                subject,
                exam_name,
                question_number,
                mode,
                response_text,
                score,
                missed,
                notes,
                minutes_spent,
                created
            ) = row

            with st.expander(
                f"{created} - {subject} - {exam_name} Q{question_number} - {mode} - Score: {score}/5"
            ):
                st.write(f"Minutes spent: {minutes_spent}")
                st.markdown("### Response")
                st.write(response_text)

                st.markdown("### Missed")
                st.write(missed)

                st.markdown("### Notes")
                st.write(notes)
