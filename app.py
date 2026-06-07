# -*- coding: utf-8 -*-

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os
import random
import re
import time
from html import escape
from io import StringIO

from database import (
    init_db,
    add_question,
    get_questions,
    get_question_by_id,
    save_attempt,
    get_attempts,
    save_rule_attempt,
    get_rule_attempts,
    get_rule_flashcards,
    search_rule_flashcards,
    get_subjects,
    get_statuses,
    get_dashboard_stats,
    get_outline_rules,
    add_outline_rule,
    search_outline_rules,
    find_best_outline_rules_for_question,
    get_plug_play_templates,
    search_plug_play_templates,
    find_best_plug_play_for_call,
    upsert_admin,
    get_app_user,
    list_app_users,
    add_app_user,
    delete_app_user,
    set_user_password,
)
from text_cleanup import normalize_extracted_text


def _hash_password(plain):
    import bcrypt
    return bcrypt.hashpw(str(plain).encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _check_password(plain, hashed):
    try:
        import bcrypt
        return bcrypt.checkpw(str(plain).encode("utf-8"), str(hashed).encode("utf-8"))
    except Exception:
        return False


st.set_page_config(
    page_title="MEE Reflex Trainer",
    page_icon=":books:",
    layout="wide",
    initial_sidebar_state="expanded",
)


init_db()


def _seed_admin_from_secrets():
    """Ensure the admin account from st.secrets exists (survives DB resets).

    Add this to your secrets to enable the login + admin:
        [auth.admin]
        username = "olesialek"
        email = "olesialek@gmail.com"
        name = "Olesia"
        password = "<bcrypt hash from make_user.py>"
    """
    try:
        adm = st.secrets["auth"]["admin"]
    except Exception:
        return
    try:
        upsert_admin(
            str(adm["username"]).strip().lower(),
            str(adm.get("email", "")).strip().lower(),
            adm.get("name", "Admin"),
            str(adm["password"]),
        )
    except Exception:
        pass


def require_login():
    _seed_admin_from_secrets()

    # If no accounts exist at all (e.g. local use with no admin configured),
    # run open so the app still works without a login.
    if not list_app_users():
        return

    if st.session_state.get("_authed_user"):
        return

    st.markdown(
        "<div style='max-width:400px;margin:8vh auto 0'>"
        "<h2 style='text-align:center;color:#1D4E89'>MEE Reflex Trainer</h2>"
        "<p style='text-align:center;color:#5A7A9A;font-size:0.9rem'>Please sign in to continue.</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        with st.form("login_form"):
            login_id = st.text_input("Email or username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", use_container_width=True)

        if submitted:
            record = get_app_user(login_id)
            if record and _check_password(password, record["password_hash"]):
                st.session_state["_authed_user"] = record["username"]
                st.session_state["_authed_name"] = record.get("name") or record["username"]
                st.session_state["_is_admin"] = record["is_admin"]
                st.rerun()
            else:
                st.error("Incorrect email/username or password.")

    st.stop()


require_login()


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


def render_app_header():
    st.markdown(
        """
        <div class="app-top-header">
            <div>
                <div class="app-title">MEE Reflex Trainer</div>
                <div class="app-subtitle">Focused MEE training: issue spotting -> rule flash -> IRAC under pressure.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_page_title(title, subtitle=None):
    subtitle_html = f'<div class="page-subtitle">{escape(str(subtitle))}</div>' if subtitle else ""
    st.markdown(
        f"""
        <div class="page-title-block">
            <div class="page-title-text">{escape(str(title))}</div>
            {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_reading_mode_notice():
    st.markdown(
        """
        <div class="reading-mode-notice">
            Reading mode is on: larger text, wider spacing, narrower reading boxes.
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("""
<style>
/* Main app background */
.stApp {
    background: linear-gradient(135deg, #F7FBFF 0%, #EEF6FF 48%, #ECFEFF 100%);
    color: #102033;
}

/* Main content container */
.block-container {
    max-width: 1500px !important;
    padding-top: 1.15rem !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    padding-bottom: 2.5rem !important;
    overflow: visible !important;
}

.main .block-container > div:first-child {
    padding-top: 0;
    overflow: visible !important;
}

header[data-testid="stHeader"] {
    height: 2.65rem !important;
    min-height: 2.65rem !important;
    background: transparent !important;
    pointer-events: none;
}

div[data-testid="stToolbar"] {
    right: 0.8rem;
    pointer-events: auto;
}

.app-top-header {
    width: 100%;
    max-width: 1500px;
    margin: 0.15rem auto 0.55rem auto;
    padding: 0.55rem 0.9rem;
    background: rgba(255, 255, 255, 0.88);
    border: 1px solid #D6E4FF;
    border-radius: 14px;
    box-shadow: 0 5px 16px rgba(37, 99, 235, 0.05);
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.75rem;
    min-height: 3.15rem;
    overflow: visible;
}

.app-title {
    color: #2F5597;
    font-size: 1.35rem;
    font-weight: 900;
    letter-spacing: 0;
    line-height: 1.18;
    padding: 0;
    overflow: visible;
}

.app-subtitle {
    color: #64748B;
    font-size: 0.82rem;
    margin-top: 0.15rem;
}

.app-pill {
    background: #E0F2FE;
    color: #075985;
    border: 1px solid #BAE6FD;
    border-radius: 999px;
    padding: 0.35rem 0.7rem;
    font-size: 0.82rem;
    font-weight: 800;
    white-space: nowrap;
}

.page-title-block {
    margin: 0.45rem 0 0.55rem 0;
    padding: 0.1rem 0 0.15rem 0;
    overflow: visible;
}

.page-title-text {
    color: #2F5597 !important;
    font-size: 1.55rem !important;
    line-height: 1.28 !important;
    min-height: 1.9rem;
    display: block;
    overflow: visible;
    margin: 0 !important;
    padding: 0 !important;
    font-weight: 900;
}

.page-subtitle {
    color: #64748B;
    font-size: 0.86rem;
    margin-top: 0.2rem;
}

.reading-mode-notice {
    background: #DBEAFE;
    border: 1px solid #BFDBFE;
    color: #1E3A8A;
    border-radius: 10px;
    padding: 0.35rem 0.65rem;
    margin: 0.25rem 0 0.45rem 0;
    font-size: 0.82rem;
    font-weight: 650;
}

.main-workspace {
    max-width: 1480px;
    margin: 0 auto;
}

.element-container {
    margin-bottom: 0.35rem;
}

.study-card {
    background: rgba(255, 255, 255, 0.94);
    border: 1px solid #D6E4FF;
    border-radius: 18px;
    padding: 1rem 1.15rem;
    box-shadow: 0 8px 22px rgba(37, 99, 235, 0.06);
    margin-bottom: 0.9rem;
}

.sticky-panel {
    position: sticky;
    top: 1rem;
    background: rgba(255, 255, 255, 0.96);
    border: 1px solid #D8B4FE;
    border-radius: 18px;
    padding: 1rem;
    box-shadow: 0 8px 24px rgba(90, 24, 154, 0.08);
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #EAF4FF 0%, #E8FFF9 100%);
    border-right: 2px solid #CDEBFF;
    min-width: 245px !important;
    max-width: 285px !important;
    width: 270px !important;
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
    min-width: 245px !important;
    max-width: 285px !important;
}

/* Headers */
h1, h2, h3 {
    color: #1D4E89 !important;
    font-weight: 800 !important;
    line-height: 1.35 !important;
    padding: 0.12rem 0 !important;
    margin-top: 0.35rem !important;
    overflow: visible !important;
}

h1 {
    background: none !important;
    color: #2563EB !important;
    -webkit-text-fill-color: #2563EB !important;
    line-height: 1.22 !important;
    padding-top: 0.35rem !important;
    margin-bottom: 0.35rem !important;
}

[data-testid="stHeading"]:has(h1),
[data-testid="stHeading"] h1 {
    width: 100% !important;
    overflow: visible !important;
}

[data-testid="stHeading"]:has(h1),
[data-testid="stHeadingWithActionElements"]:has(h1),
[data-testid="stHeading"] [data-testid="stMarkdownContainer"]:has(h1) {
    min-height: 4.8rem !important;
    overflow: visible !important;
}

h2, h3 {
    line-height: 1.35 !important;
    padding: 0.1rem 0 !important;
    margin-top: 0.75rem !important;
    margin-bottom: 0.45rem !important;
    overflow: visible !important;
}

[data-testid="stHeading"],
[data-testid="stHeadingWithActionElements"],
[data-testid="stMarkdownContainer"],
.stMarkdown {
    overflow: visible !important;
}

[data-testid="stHeading"] h1,
[data-testid="stHeading"] h2,
[data-testid="stHeading"] h3,
[data-testid="stHeadingWithActionElements"] h1,
[data-testid="stHeadingWithActionElements"] h2,
[data-testid="stHeadingWithActionElements"] h3 {
    min-height: 1.8em !important;
    overflow: visible !important;
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

[data-testid="stCheckbox"] label {
    min-height: 42px !important;
    align-items: center !important;
}

[data-testid="stCheckbox"] label p,
[data-testid="stCheckbox"] label span {
    font-size: 16px !important;
    line-height: 1.35 !important;
    font-weight: 650 !important;
}

[data-testid="stCheckbox"] input,
[data-testid="stCheckbox"] [role="checkbox"] {
    transform: scale(1.15);
}

.review-controls-title {
    color: #1D4E89;
    font-weight: 850;
    font-size: 1.02rem;
    margin-bottom: 0.25rem;
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
    padding: 0.65rem 0.9rem;
}

div[data-baseweb="select"] {
    width: 100%;
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
    font-size: 16px !important;
    line-height: 1.32 !important;
}

[data-testid="stSidebar"] [role="radiogroup"] label {
    min-height: 42px !important;
    padding: 8px 11px !important;
}

[data-testid="stSidebar"] .stRadio > div {
    gap: 0.25rem;
}

[role="radio"][aria-checked="true"],
[role="radio"][aria-checked="true"] + div,
[role="radiogroup"] label:has([aria-checked="true"]) {
    background-color: #DDF4FF !important;
    color: #102033 !important;
}

header,
[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
[data-testid="stMainMenu"],
[data-baseweb="menu"],
[role="listbox"] {
    background-color: transparent !important;
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
    max-width: 1000px;
}

.readable-box.compact {
    padding: 0.85rem 1rem;
    margin: 0.55rem 0 0.8rem 0;
}

.readable-title {
    color: #1D4E89;
    font-weight: 700;
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

.sample-answer-box {
    background: rgba(255, 255, 255, 0.97);
    border: 1.5px solid #CDEBFF;
    border-radius: 14px;
    padding: 0.95rem 1.05rem;
    margin: 0.55rem 0 0.8rem 0;
    box-shadow: 0 4px 14px rgba(29, 78, 137, 0.07);
    width: 100%;
}

.sample-answer-title {
    color: #1D4E89;
    font-weight: 800;
    font-size: 1.02rem;
    margin-bottom: 0.55rem;
    padding-bottom: 0.3rem;
    border-bottom: 2px solid #DBEAFE;
}

.sample-answer-text {
    color: #102033;
    font-size: 16.5px;
    line-height: 1.58;
}

.sample-answer-text p {
    margin: 0.35rem 0 0.8rem 0;
}

.structured-answer-box {
    background: #FFFFFF;
    border: 1.5px solid #CDEBFF;
    border-radius: 14px;
    padding: 0.95rem 1.05rem;
    margin: 0.55rem 0 0.8rem 0;
    box-shadow: 0 4px 14px rgba(29, 78, 137, 0.07);
    width: 100%;
}

.structured-answer-title {
    color: #1D4E89;
    font-weight: 850;
    font-size: 1.05rem;
    margin-bottom: 0.35rem;
}

.structured-answer-note {
    color: #52657A;
    font-size: 0.92rem;
    line-height: 1.35;
    margin-bottom: 0.8rem;
}

.structured-section {
    border-top: 1px solid #DBEAFE;
    padding-top: 0.65rem;
    margin-top: 0.65rem;
}

.structured-section-title {
    color: #234A7C;
    font-weight: 800;
    font-size: 0.95rem;
    margin-bottom: 0.35rem;
}

.structured-section-body {
    color: #102033;
    font-size: 16px;
    line-height: 1.48;
}

.structured-list {
    margin: 0.15rem 0 0 1.15rem;
    padding: 0;
}

.structured-list li {
    margin: 0.25rem 0;
    padding-left: 0.1rem;
}

.sample-point {
    background: #EFF6FF;
    border-left: 4px solid #2563EB;
    border-radius: 0 10px 10px 0;
    color: #1E3A8A;
    font-weight: 850;
    padding: 0.45rem 0.7rem;
    margin: 0.85rem 0 0.55rem 0;
}

.sample-label-main,
.sample-label {
    color: #0F766E;
    font-weight: 850;
    margin: 0.75rem 0 0.25rem 0;
}

.sample-label-main {
    color: #1D4E89;
}

.trap-box {
    background: rgba(255, 251, 235, 0.98);
    border: 1.5px solid #FDBA74;
    border-radius: 14px;
    padding: 0.9rem 1rem;
    margin: 0.55rem 0 0.8rem 0;
    box-shadow: 0 5px 16px rgba(234, 88, 12, 0.08);
    width: 100%;
}

.trap-title {
    color: #9A3412;
    font-weight: 850;
    font-size: 1.02rem;
    margin-bottom: 0.55rem;
    padding-bottom: 0.3rem;
    border-bottom: 2px solid #FED7AA;
}

.trap-card {
    background: #FFF7ED;
    border-left: 4px solid #EA580C;
    border-radius: 0 12px 12px 0;
    color: #431407;
    padding: 0.65rem 0.8rem;
    margin: 0.45rem 0;
    line-height: 1.48;
    font-size: 16px;
}

.trap-number {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.45rem;
    height: 1.45rem;
    border-radius: 999px;
    background: #FFEDD5;
    color: #9A3412;
    border: 1px solid #FDBA74;
    font-weight: 850;
    margin-right: 0.45rem;
    font-size: 0.82rem;
}

.rule-break-card {
    background: rgba(255, 255, 255, 0.98);
    border: 1.5px solid #A7F3D0;
    border-radius: 18px;
    padding: 1rem 1.15rem;
    margin: 0.8rem 0 1rem 0;
    box-shadow: 0 8px 22px rgba(16, 185, 129, 0.08);
    max-width: 1000px;
    width: 100%;
}

.rule-break-title {
    color: #047857;
    font-weight: 900;
    font-size: 1.08rem;
    margin-bottom: 0.75rem;
    padding-bottom: 0.45rem;
    border-bottom: 2px solid #D1FAE5;
}

.rule-break-section {
    margin-bottom: 0.75rem;
}

.rule-break-label {
    color: #065F46;
    font-weight: 850;
    font-size: 0.82rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin-bottom: 0.25rem;
}

.rule-break-text {
    color: #1E293B;
    font-size: 16px;
    line-height: 1.55;
}

.rule-break-list {
    margin: 0.25rem 0 0 1.2rem;
    color: #1E293B;
    font-size: 16px;
    line-height: 1.55;
}

.rule-break-list li {
    margin-bottom: 0.25rem;
}

.rule-break-trap {
    background: #FFF7ED;
    border-left: 4px solid #F97316;
    border-radius: 10px;
    padding: 0.65rem 0.8rem;
    color: #7C2D12;
    font-size: 15px;
    line-height: 1.45;
    margin-top: 0.6rem;
}

.rule-break-note {
    background: #EFF6FF;
    border-left: 4px solid #3B82F6;
    border-radius: 10px;
    padding: 0.55rem 0.75rem;
    color: #1E3A8A;
    font-size: 14px;
    line-height: 1.45;
    margin-top: 0.6rem;
}

/* Compact question/fact pattern boxes */
.question-box {
    background: rgba(255, 255, 255, 0.96);
    border: 1.5px solid #CDEBFF;
    border-radius: 14px;
    padding: 0.9rem 1rem;
    margin: 0.55rem 0 0.8rem 0;
    box-shadow: 0 4px 14px rgba(29, 78, 137, 0.07);
    max-width: 1000px;
}

.question-title {
    color: #1D4E89;
    font-weight: 700;
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

.triggers-box {
    background: rgba(255, 255, 255, 0.97);
    border: 1.5px solid #FDE68A;
    border-radius: 18px;
    padding: 1rem 1.2rem;
    margin: 0.85rem 0 1.1rem 0;
    box-shadow: 0 6px 18px rgba(250, 204, 21, 0.10);
    max-width: 1000px;
}

.triggers-title {
    color: #92400E;
    font-weight: 850;
    font-size: 1.05rem;
    margin-bottom: 0.75rem;
    padding-bottom: 0.4rem;
    border-bottom: 2px solid #FEF3C7;
}

.trigger-card {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    background: #FFFBEB;
    border: 1px solid #FDE68A;
    border-radius: 14px;
    padding: 0.75rem 0.85rem;
    margin-bottom: 0.55rem;
}

.trigger-number {
    min-width: 1.7rem;
    height: 1.7rem;
    border-radius: 999px;
    background: #FACC15;
    color: #713F12;
    font-weight: 850;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.9rem;
}

.trigger-content {
    flex: 1;
}

.trigger-fact-text {
    color: #1E293B;
    font-size: 16.5px;
    line-height: 1.5;
    font-weight: 650;
}

.trigger-why {
    color: #78350F;
    font-size: 0.92rem;
    line-height: 1.4;
    margin-top: 0.35rem;
}

.issues-box {
    background: rgba(255, 255, 255, 0.97);
    border: 1.5px solid #BFDBFE;
    border-radius: 18px;
    padding: 1rem 1.2rem;
    margin: 0.85rem 0 1.1rem 0;
    box-shadow: 0 6px 18px rgba(59, 130, 246, 0.08);
    max-width: 1000px;
}

.issues-title {
    color: #1D4ED8;
    font-weight: 850;
    font-size: 1.05rem;
    margin-bottom: 0.75rem;
    padding-bottom: 0.4rem;
    border-bottom: 2px solid #DBEAFE;
}

.issue-card {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    background: #F8FBFF;
    border: 1px solid #DBEAFE;
    border-radius: 14px;
    padding: 0.75rem 0.85rem;
    margin-bottom: 0.55rem;
}

.issue-number {
    min-width: 1.7rem;
    height: 1.7rem;
    border-radius: 999px;
    background: #DBEAFE;
    color: #1D4ED8;
    font-weight: 850;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.9rem;
}

.issue-text {
    color: #1E293B;
    font-size: 16.5px;
    line-height: 1.5;
}

.flash-page-wrap {
    background: #f5f4f0;
    padding: 1rem;
    border-radius: 18px;
}

.flash-header {
    margin-bottom: 1rem;
    border-bottom: 2px solid #1a1a1a;
    padding-bottom: 0.75rem;
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    gap: 1rem;
}

.flash-header h2 {
    font-size: 13px;
    font-weight: 800;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #1a1a1a !important;
    margin: 0;
}

.flash-header .flash-meta {
    font-size: 11px;
    color: #666;
    font-family: monospace;
}

.flash-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(320px, 1fr));
    gap: 16px;
}

.flash-card {
    background: #fff;
    border: 1px solid #d0cfc9;
    border-radius: 6px;
    overflow: hidden;
    break-inside: avoid;
    page-break-inside: avoid;
}

.flash-front {
    background: #1a1a1a;
    color: #f5f4f0;
    padding: 14px 16px;
    border-bottom: 3px solid #e85d26;
}

.flash-card-num {
    font-family: monospace;
    font-size: 10px;
    color: #e85d26;
    letter-spacing: 0.1em;
    margin-bottom: 6px;
}

.flash-front h3 {
    font-size: 14px;
    font-weight: 700;
    line-height: 1.35;
    margin: 0 0 8px 0;
    color: #f5f4f0 !important;
}

.flash-question {
    font-size: 12px;
    color: #b8b5ae;
    line-height: 1.5;
    font-style: italic;
}

.flash-back {
    padding: 14px 16px;
    background: #fff;
}

.flash-rule-line {
    display: flex;
    gap: 8px;
    align-items: flex-start;
    margin-bottom: 6px;
    font-size: 12px;
    line-height: 1.5;
}

.flash-rule-key {
    font-family: monospace;
    font-size: 11px;
    font-weight: 700;
    color: #e85d26;
    min-width: 120px;
    flex-shrink: 0;
    padding-top: 1px;
}

.flash-rule-val {
    color: #1a1a1a;
}

.flash-trap-box {
    background: #fff8f5;
    border-left: 3px solid #e85d26;
    padding: 7px 10px;
    margin-top: 10px;
    font-size: 11px;
    color: #663300;
    line-height: 1.5;
}

.flash-key-rule {
    background: #f0f9f0;
    border-left: 3px solid #2a7a2a;
    padding: 7px 10px;
    margin-top: 10px;
    font-size: 11px;
    color: #1a3d1a;
    line-height: 1.5;
}

.flash-mini-title {
    display: block;
    font-size: 10px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 3px;
    font-weight: 800;
}

.flash-tags {
    margin-top: 10px;
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
}

.flash-tag {
    font-family: monospace;
    font-size: 10px;
    background: #f0efe9;
    color: #666;
    padding: 2px 7px;
    border-radius: 3px;
}

@media print {
    [data-testid="stSidebar"], header, footer {
        display: none !important;
    }
    .block-container {
        max-width: none !important;
        padding: 10px !important;
    }
    .flash-page-wrap {
        background: #fff;
    }
    .flash-grid {
        gap: 12px;
    }
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
    font-weight: 700;
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
    max-width: 1000px;
}

.call-title {
    color: #2563EB;
    font-weight: 700;
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
    font-weight: 700;
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
    max-width: 1000px;
}

.outline-rule-title {
    color: #1D4E89;
    font-weight: 700;
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

.meta-strip {
    display: flex;
    flex-wrap: wrap;
    gap: 0.55rem;
    align-items: center;
    background: rgba(255, 255, 255, 0.72);
    border: 1px solid #D6E4FF;
    border-radius: 14px;
    padding: 0.65rem 0.8rem;
    margin: 0.65rem 0 0.9rem 0;
    color: #1E293B;
}

.meta-strip span {
    background: #F8FBFF;
    border: 1px solid #E0E7FF;
    border-radius: 999px;
    padding: 0.25rem 0.6rem;
    font-size: 0.9rem;
}

.meta-strip .badge-active {
    background: #DCFCE7 !important;
    border-color: #BBF7D0 !important;
    color: #166534 !important;
    font-weight: 800;
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
    font-weight: 700;
    font-size: 1.02rem;
    margin-bottom: 0.35rem;
    padding-bottom: 0.3rem;
    border-bottom: 2px solid #DBEAFE;
}

.plug-section-title {
    color: #0F766E;
    font-weight: 700;
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

/* Practice page â€” thin metadata strip metric labels */
[data-testid="stMetricLabel"] p,
[data-testid="stMetricLabel"] {
    font-size: 0.72rem !important;
    line-height: 1.2 !important;
}

/* Question context strip */
.question-strip {
    background: #EAF4FF;
    border-radius: 10px;
    padding: 0.5rem 1rem;
    margin: 0.5rem 0 1rem;
    display: flex;
    gap: 1rem;
    align-items: center;
    flex-wrap: wrap;
    font-size: 0.93rem;
}

/* Step label block */
.step-block {
    background: #EFF6FF;
    border-left: 3px solid #3B82F6;
    border-radius: 0 8px 8px 0;
    padding: 0.65rem 1rem;
    margin-bottom: 0.65rem;
}

.step-label {
    font-size: 0.82rem;
    font-weight: 700;
    color: #1E40AF;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    margin-bottom: 0.2rem;
}

.step-title {
    font-size: 0.97rem;
    font-weight: 600;
    color: #1D3557;
}

/* Status badges */
.badge {
    display: inline-block;
    border-radius: 999px;
    padding: 2px 10px;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.03em;
}

.badge-active  { background: #D1FAE5; color: #065F46; }
.badge-due     { background: #FEF3C7; color: #92400E; }
.badge-retired { background: #FCE7F3; color: #9D174D; }
.badge-mpt     { background: #EDE9FE; color: #5B21B6; }
.badge-low     { background: #F1F5F9; color: #475569; }

/* Study tip (blue) */
.study-tip {
    background: #EFF6FF;
    border-left: 4px solid #3B82F6;
    padding: 0.6rem 1rem;
    border-radius: 0 8px 8px 0;
    font-size: 0.95rem;
    color: #1E3A5F;
    margin: 0.4rem 0 0.7rem;
}

/* Reveal gate (amber) */
.reveal-gate {
    background: #FFFBEB;
    border-left: 4px solid #F59E0B;
    padding: 0.6rem 1rem;
    border-radius: 0 8px 8px 0;
    font-size: 0.95rem;
    color: #78350F;
    margin: 0.4rem 0 0.7rem;
}

/* Muted caption text */
.muted { color: #4A6585; font-size: 0.85rem; }

/* Sidebar nav buttons */
[data-testid="stSidebar"] .stButton > button {
    text-align: left !important;
    justify-content: flex-start !important;
    padding: 0.5rem 0.75rem !important;
    margin-bottom: 2px !important;
    font-weight: 600 !important;
    font-size: 16px !important;
    line-height: 1.35 !important;
    min-height: 40px !important;
}

[data-testid="stSidebar"] .stButton > button *,
[data-testid="stSidebar"] .stButton > button p,
[data-testid="stSidebar"] .stButton > button span {
    font-size: 16px !important;
    line-height: 1.35 !important;
}

/* Inactive nav button (secondary) â€” flat, light */
[data-testid="stSidebar"] .stButton > button[kind="secondary"] {
    background: rgba(255, 255, 255, 0.70) !important;
    color: #102033 !important;
    -webkit-text-fill-color: #102033 !important;
    box-shadow: none !important;
    border: 1px solid #D1E3F8 !important;
}

[data-testid="stSidebar"] .stButton > button[kind="secondary"] * {
    color: #102033 !important;
    -webkit-text-fill-color: #102033 !important;
}

[data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover {
    background: #DDF4FF !important;
    transform: none !important;
    box-shadow: none !important;
}

/* Active nav button (primary) keeps the gradient highlight */
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.25) !important;
}

/* Sidebar group label */
.nav-group-label {
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    color: #4A6585;
    margin: 0.8rem 0 0.3rem;
    text-transform: uppercase;
}

/* Fact pattern boxes (readable narrative paragraphs) */
.fact-box {
    background: rgba(255, 255, 255, 0.97);
    border: 1.5px solid #C7D2FE;
    border-radius: 18px;
    padding: 1.05rem 1.25rem;
    margin: 0.85rem 0 1.1rem 0;
    box-shadow: 0 6px 18px rgba(99, 102, 241, 0.08);
    max-width: 1000px;
}

.fact-title {
    color: #4338CA;
    font-weight: 700;
    font-size: 1.05rem;
    margin-bottom: 0.65rem;
    padding-bottom: 0.35rem;
    border-bottom: 2px solid #E0E7FF;
}

.fact-text {
    color: #1E293B;
    font-size: 17px;
    line-height: 1.65;
    letter-spacing: 0.05px;
}

.fact-text p {
    margin: 0 0 0.85rem 0;
}

.fact-text p:last-child {
    margin-bottom: 0;
}

.trigger-highlight {
    background: linear-gradient(180deg, rgba(255, 245, 157, 0.15) 0%, rgba(255, 235, 59, 0.72) 100%);
    border-bottom: 2px solid #FACC15;
    padding: 0.05rem 0.18rem;
    border-radius: 5px;
    font-weight: 700;
    color: #1E293B;
}

.highlighted-fact-box {
    border-color: #FACC15 !important;
    box-shadow: 0 8px 22px rgba(250, 204, 21, 0.16) !important;
}

.q-highlight-1 {
    background: linear-gradient(180deg, rgba(191, 219, 254, 0.25), rgba(96, 165, 250, 0.55));
    border-bottom: 2px solid #3B82F6;
    padding: 0.05rem 0.18rem;
    border-radius: 5px;
    font-weight: 750;
}

.q-highlight-2 {
    background: linear-gradient(180deg, rgba(233, 213, 255, 0.25), rgba(168, 85, 247, 0.50));
    border-bottom: 2px solid #9333EA;
    padding: 0.05rem 0.18rem;
    border-radius: 5px;
    font-weight: 750;
}

.q-highlight-3 {
    background: linear-gradient(180deg, rgba(187, 247, 208, 0.25), rgba(34, 197, 94, 0.45));
    border-bottom: 2px solid #16A34A;
    padding: 0.05rem 0.18rem;
    border-radius: 5px;
    font-weight: 750;
}

.q-highlight-4 {
    background: linear-gradient(180deg, rgba(254, 215, 170, 0.25), rgba(251, 146, 60, 0.55));
    border-bottom: 2px solid #EA580C;
    padding: 0.05rem 0.18rem;
    border-radius: 5px;
    font-weight: 750;
}

.q-highlight-5 {
    background: linear-gradient(180deg, rgba(251, 207, 232, 0.25), rgba(236, 72, 153, 0.42));
    border-bottom: 2px solid #DB2777;
    padding: 0.05rem 0.18rem;
    border-radius: 5px;
    font-weight: 750;
}

.q-highlight-6 {
    background: linear-gradient(180deg, rgba(153, 246, 228, 0.25), rgba(20, 184, 166, 0.45));
    border-bottom: 2px solid #0D9488;
    padding: 0.05rem 0.18rem;
    border-radius: 5px;
    font-weight: 750;
}

.question-highlight-legend {
    background: #FFFFFF;
    border: 1px solid #D6E4FF;
    border-radius: 14px;
    padding: 0.8rem 1rem;
    margin: 0.75rem 0;
    box-shadow: 0 6px 18px rgba(37, 99, 235, 0.06);
}

.legend-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.55rem;
    align-items: center;
}

.legend-chip {
    border-radius: 999px;
    padding: 0.25rem 0.6rem;
    font-size: 0.85rem;
    font-weight: 800;
    color: #1E293B;
    border: 1px solid rgba(0,0,0,0.08);
}

.tooltip-highlight {
    position: relative;
    cursor: help;
    padding: 0.05rem 0.18rem;
    border-radius: 5px;
    font-weight: 750;
    outline: none;
}

.tooltip-highlight .tooltip-bubble {
    visibility: hidden;
    opacity: 0;
    position: absolute;
    z-index: 9999;
    left: 0;
    bottom: 135%;
    width: min(360px, 80vw);
    background: #FFFFFF;
    color: #102033;
    text-align: left;
    border-radius: 12px;
    padding: 0.75rem 0.85rem;
    font-size: 13px;
    line-height: 1.45;
    font-weight: 500;
    border: 1.5px solid #93C5FD;
    box-shadow: 0 12px 28px rgba(37, 99, 235, 0.18);
    pointer-events: none;
}

.tooltip-highlight .tooltip-bubble::after {
    content: "";
    position: absolute;
    top: 100%;
    left: 18px;
    border-width: 7px;
    border-style: solid;
    border-color: #FFFFFF transparent transparent transparent;
}

.tooltip-highlight:hover .tooltip-bubble,
.tooltip-highlight:focus .tooltip-bubble,
.tooltip-highlight:focus-within .tooltip-bubble {
    visibility: visible;
    opacity: 1;
}

.tooltip-title {
    display: block;
    color: #1D4E89;
    font-weight: 850;
    font-size: 12px;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    margin-bottom: 0.25rem;
}

.tooltip-reason {
    display: block;
    color: #102033;
}

.tooltip-hint {
    display: block;
    margin-top: 0.4rem;
    color: #4A6585;
    font-size: 12px;
}

.fact-highlight-legend {
    background: #FFFBEB;
    border: 1px solid #FDE68A;
    border-radius: 14px;
    padding: 0.75rem 1rem;
    margin: 0.75rem 0;
    color: #78350F;
    font-size: 0.95rem;
}

/* Layout stabilization pass */
*, *::before, *::after {
    box-sizing: border-box;
}

.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stVerticalBlock"],
[data-testid="stHorizontalBlock"],
[data-testid="column"],
.element-container {
    min-width: 0 !important;
}

[data-testid="stVerticalBlock"],
[data-testid="stHorizontalBlock"] {
    gap: 0.75rem !important;
}

[data-testid="column"] {
    min-width: 0 !important;
    overflow: visible !important;
}

[data-testid="stVerticalBlock"] > [style*="flex-direction: column"] {
    min-width: 0 !important;
}

.app-top-header {
    flex-wrap: wrap;
    align-items: flex-start;
}

.app-top-header > div:first-child {
    min-width: min(100%, 420px);
}

.app-pill {
    margin-top: 0.15rem;
}

.page-title-block,
.page-title-text,
[data-testid="stHeading"],
[data-testid="stHeadingWithActionElements"] {
    contain: none !important;
    overflow: visible !important;
}

.readable-box,
.question-box,
.fact-box,
.triggers-box,
.issues-box,
.call-box,
.hint-box,
.outline-rule-box,
.plug-box {
    width: 100% !important;
    max-width: 100% !important;
    overflow: visible !important;
}

.readable-text,
.question-text,
.fact-text,
.trigger-fact-text,
.trigger-why,
.issue-text,
.call-card-text,
.call-subpart,
.hint-text,
.outline-rule-text,
.plug-text {
    max-width: 100%;
    overflow-wrap: anywhere;
    word-break: normal;
}

div[data-testid="stExpander"] {
    overflow: visible !important;
}

div[data-testid="stExpander"] details {
    overflow: visible !important;
}

div[data-testid="stExpander"] summary {
    min-height: 46px !important;
    padding-top: 0.55rem !important;
    padding-bottom: 0.55rem !important;
    overflow: visible !important;
}

div[data-testid="stExpander"] summary p,
div[data-testid="stExpander"] summary span {
    line-height: 1.35 !important;
}

[data-testid="stTextArea"] textarea {
    width: 100% !important;
    min-height: 120px !important;
    resize: vertical;
}

[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
div[data-baseweb="select"] {
    min-height: 42px !important;
}

.stButton > button,
.stDownloadButton > button,
.stFormSubmitButton > button {
    min-height: 42px !important;
    white-space: normal !important;
}

.meta-strip,
.question-strip {
    width: 100%;
    align-items: flex-start;
}

.flash-grid,
.plug-grid {
    grid-template-columns: repeat(auto-fit, minmax(min(320px, 100%), 1fr)) !important;
}

.trap-warning-box {
    background: rgba(255, 255, 255, 0.98);
    border: 1.5px solid #FDBA74;
    border-radius: 18px;
    padding: 1rem 1.2rem;
    margin: 0.85rem 0 1.1rem 0;
    box-shadow: 0 6px 18px rgba(249, 115, 22, 0.10);
    max-width: 1000px;
    overflow: visible !important;
}

.trap-warning-title {
    color: #C2410C;
    font-weight: 900;
    font-size: 1.05rem;
    margin-bottom: 0.75rem;
    padding-bottom: 0.4rem;
    border-bottom: 2px solid #FED7AA;
}

.trap-card {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    background: #FFF7ED;
    border: 1px solid #FED7AA;
    border-left: 5px solid #F97316;
    border-radius: 14px;
    padding: 0.75rem 0.85rem;
    margin-bottom: 0.6rem;
    overflow: visible !important;
    white-space: normal !important;
}

.trap-number {
    min-width: 1.7rem;
    width: 1.7rem;
    height: 1.7rem;
    border-radius: 999px;
    background: #F97316;
    color: white;
    font-weight: 900;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.9rem;
    flex-shrink: 0;
    margin-right: 0 !important;
}

.trap-text {
    color: #7C2D12;
    font-size: 16px;
    line-height: 1.5;
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: unset !important;
    overflow-wrap: anywhere;
    flex: 1;
}

.mini-progress-box {
    background: rgba(255,255,255,0.96);
    border: 1px solid #D6E4FF;
    border-radius: 16px;
    padding: 0.85rem 1rem;
    margin: 0.75rem 0 1rem 0;
    box-shadow: 0 6px 18px rgba(37, 99, 235, 0.06);
}

.mini-progress-title {
    color: #2F5597;
    font-weight: 900;
    font-size: 0.95rem;
    margin-bottom: 0.55rem;
}

.mini-progress-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
}

.mini-step-chip {
    border-radius: 999px;
    padding: 0.35rem 0.65rem;
    display: flex;
    gap: 0.45rem;
    align-items: center;
    font-size: 0.85rem;
    border: 1px solid #E2E8F0;
}

.mini-step-chip span {
    font-size: 0.75rem;
    font-weight: 800;
    text-transform: uppercase;
}

.mini-step-active {
    background: #DBEAFE;
    color: #1E3A8A;
    border-color: #93C5FD;
}

.mini-step-done {
    background: #DCFCE7;
    color: #166534;
    border-color: #86EFAC;
}

.mini-step-locked {
    background: #F8FAFC;
    color: #64748B;
    border-color: #E2E8F0;
}

.mini-question-panel {
    background: rgba(255,255,255,0.98);
    border: 1.5px solid #D6E4FF;
    border-radius: 18px;
    padding: 1rem 1.15rem;
    margin: 0.8rem 0 1rem 0;
    box-shadow: 0 8px 22px rgba(37, 99, 235, 0.06);
}

.compact-picker {
    background: rgba(255,255,255,0.72);
    border: 1px solid #D6E4FF;
    border-radius: 14px;
    padding: 0.55rem 0.7rem 0.65rem;
    margin: 0.35rem 0 0.7rem 0;
}

.compact-picker .picker-count {
    color: #64748B;
    font-size: 0.82rem;
    font-weight: 700;
    margin-top: 1.85rem;
}

.compact-picker [data-testid="stVerticalBlock"] {
    gap: 0.35rem !important;
}

.compact-picker [data-testid="stSelectbox"],
.compact-picker [data-testid="stTextInput"],
.compact-picker [data-testid="stCheckbox"] {
    margin-bottom: 0 !important;
}

.compact-picker .stButton > button {
    min-height: 38px !important;
    padding: 0.45rem 0.85rem !important;
}

.mini-drill-note {
    background: #DBEAFE;
    border: 1px solid #BFDBFE;
    color: #1E3A8A;
    border-radius: 10px;
    padding: 0.45rem 0.7rem;
    margin: 0.3rem 0 0.55rem;
    font-size: 0.88rem;
    line-height: 1.35;
}

.trigger-mini-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(min(280px, 100%), 1fr));
    gap: 0.45rem;
    margin: 0.4rem 0 0.25rem;
}

.trigger-mini-chip {
    background: #F8FBFF;
    border: 1px solid #DBEAFE;
    border-left: 4px solid #60A5FA;
    border-radius: 10px;
    color: #1E293B;
    font-size: 0.84rem;
    line-height: 1.32;
    padding: 0.45rem 0.55rem;
}

.dashboard-wrap {
    max-width: 1450px;
    margin: 0 auto;
}

.compact-card {
    background: rgba(255,255,255,0.96);
    border: 1px solid #D6E4FF;
    border-radius: 16px;
    padding: 0.8rem 0.95rem;
    box-shadow: 0 6px 18px rgba(37, 99, 235, 0.06);
    min-height: 100%;
}

.compact-card h3 {
    color: #2F5597 !important;
    font-size: 1rem !important;
    margin: 0 0 0.45rem 0 !important;
    line-height: 1.2 !important;
}

.compact-card p,
.compact-card li {
    font-size: 0.92rem;
    line-height: 1.35;
    margin-bottom: 0.25rem;
}

.compact-metric {
    background: #F8FBFF;
    border: 1px solid #DBEAFE;
    border-radius: 14px;
    padding: 0.65rem 0.75rem;
    text-align: center;
}

.compact-metric .metric-label {
    color: #64748B;
    font-size: 0.75rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}

.compact-metric .metric-value {
    color: #1E3A8A;
    font-size: 1.25rem;
    font-weight: 900;
    margin-top: 0.15rem;
}

.workout-step {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.6rem;
    background: #F8FBFF;
    border: 1px solid #E0E7FF;
    border-radius: 12px;
    padding: 0.45rem 0.6rem;
    margin-bottom: 0.4rem;
}

.workout-step strong {
    color: #1E3A8A;
    font-size: 0.9rem;
}

.workout-step span {
    color: #64748B;
    font-size: 0.82rem;
}

.tiny-win {
    background: #ECFDF5;
    border: 1px solid #BBF7D0;
    color: #166534;
    border-radius: 14px;
    padding: 0.7rem 0.85rem;
    font-weight: 750;
    font-size: 0.92rem;
}

.warning-mini {
    background: #FFF7ED;
    border-left: 4px solid #F97316;
    border-radius: 12px;
    padding: 0.65rem 0.8rem;
    color: #7C2D12;
    font-size: 0.88rem;
    line-height: 1.35;
    margin-bottom: 0.45rem;
}

.dashboard-button-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem;
    margin-top: 0.45rem;
}

@media (max-width: 900px) {
    .block-container {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }

    .app-top-header {
        padding: 0.8rem;
        gap: 0.55rem;
    }

    .app-title {
        font-size: 1.35rem;
    }

    .app-pill {
        white-space: normal;
    }

    .page-title-text {
        font-size: 1.45rem !important;
        min-height: auto;
    }
}
</style>
""", unsafe_allow_html=True)

if st.session_state.get("current_page", "Daily Workout") != "MBE Drills":
    render_app_header()


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
    text = re.sub(r'\.["â€](?=[A-Z])', '.\n\n"', text)

    # through"written -> through "written
    text = re.sub(r'([a-zA-Z])["â€]([a-zA-Z])', r'\1 "\2', text)

    # Fix section-symbol spacing.
    text = re.sub(r"Â§\s+(\d+)\.\s+(\d+)", r"Â§ \1.\2", text)
    text = re.sub(r"Ã‚Â§\s+(\d+)\.\s+(\d+)", r"Â§ \1.\2", text)
    text = re.sub(r"\bId\.\s+Â§\s+(\d+)\.\s+(\d+)", r"Id. Â§ \1.\2", text)
    text = re.sub(r"\bId\.\s+Ã‚Â§\s+(\d+)\.\s+(\d+)", r"Id. Â§ \1.\2", text)

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


def clean_sample_answer_text(text):
    if not text:
        return ""

    text = normalize_extracted_text(str(text))
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ").replace("Ãƒâ€šÃ‚Â ", " ")
    text = re.sub(r"[ \t]+", " ", text)

    # The imported condensed-answer summaries are often synthetic and can read
    # awkwardly. Keep the actual answer analysis as the comparison material.
    text = re.sub(
        r"(?is)^Question summary:\s*.*?(?=Condensed sample-answer path:|Point\s+(?:One|Two|Three|Four|Five|Six)|\d+\.\s+Point|\Z)",
        "",
        text,
    )
    text = re.sub(r"(?i)Condensed sample-answer path:\s*", "Sample Answer:\n", text)

    # Repair common PDF/import label damage.
    text = re.sub(r"(?i)\bFact-based\s*\n*\s*analysis\s*\n*\s*:", "Fact-based analysis:", text)
    text = re.sub(r"(?i)\bRule\s*\(\s*s\s*\)\s*:", "Rule(s):", text)
    text = re.sub(r"(?i)\bShort\s+answer\s*:", "Short answer:", text)
    text = re.sub(r"(?i)\bConclusion\s*:", "Conclusion:", text)
    text = re.sub(r"\b([a-z])\s+Short answer:", "Short answer:", text)
    text = re.sub(r"\b([a-z])\s+Rule\(s\):", "Rule(s):", text)

    # Turn point headers and labels into predictable paragraph breaks.
    text = re.sub(
        r"(?i)(?:^|\s)(\d+\.\s*)?(Point\s+(?:One|Two|Three|Four|Five|Six)(?:\s*\([^)]*\))?)\s+",
        r"\n\n\2\n",
        text,
    )
    text = re.sub(
        r"(?i)\s+(Short answer:|Rule\(s\):|Fact-based analysis:|Conclusion:)",
        r"\n\n\1",
        text,
    )

    lines = []
    for raw_line in text.splitlines():
        line = re.sub(r"[ \t]+", " ", raw_line).strip()
        if not line:
            lines.append("")
            continue

        if line in {"-", "â€¢"}:
            continue

        line = re.sub(r"^[-â€¢]\s*", "", line).strip()
        line = re.sub(r"\s+([,.;:!?])", r"\1", line)
        line = re.sub(r"([.!?])([A-Z])", r"\1 \2", line)
        line = re.sub(r"\s+", " ", line)

        if line:
            lines.append(line)

    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def render_sample_answer_text(title, text):
    formatted = clean_sample_answer_text(text)
    if not formatted:
        st.info("No sample answer/model analysis available for this question yet.")
        return

    safe_title = escape_display_text(title)
    blocks = []
    label_classes = {
        "Sample Answer:": "sample-label-main",
        "Short answer:": "sample-label",
        "Rule(s):": "sample-label",
        "Fact-based analysis:": "sample-label",
        "Conclusion:": "sample-label",
    }

    for paragraph in [p.strip() for p in formatted.split("\n\n") if p.strip()]:
        if re.fullmatch(r"Point\s+(One|Two|Three|Four|Five|Six)(\s*\([^)]*\))?", paragraph, flags=re.IGNORECASE):
            blocks.append(f'<div class="sample-point">{escape_display_text(paragraph)}</div>')
            continue

        label_match = re.match(r"^(Sample Answer:|Short answer:|Rule\(s\):|Fact-based analysis:|Conclusion:)\s*(.*)$", paragraph, flags=re.IGNORECASE | re.DOTALL)
        if label_match:
            label = label_match.group(1)
            body = label_match.group(2).strip()
            canonical_label = next((known for known in label_classes if known.lower() == label.lower()), label)
            blocks.append(f'<div class="{label_classes.get(canonical_label, "sample-label")}">{escape_display_text(canonical_label)}</div>')
            if body:
                body_html = "<br>".join(escape_display_text(line) for line in body.splitlines() if line.strip())
                blocks.append(f"<p>{body_html}</p>")
        else:
            paragraph_html = "<br>".join(escape_display_text(line) for line in paragraph.splitlines() if line.strip())
            blocks.append(f"<p>{paragraph_html}</p>")

    st.markdown(
        (
            '<div class="sample-answer-box">'
            f'<div class="sample-answer-title">{safe_title}</div>'
            f'<div class="sample-answer-text">{"".join(blocks)}</div>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


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
        r"\bAssuming\s+t\s+Short answer:",
        r"\bs\s+Short answer:",
        r"\bking\s+to\s+recover\b",
        r"\b03\.\s+There\b",
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
        line = re.sub(r"^[-•]\s*", "", line).strip()
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
        st.info("No structured answer material is available for this question yet.")
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

    st.markdown(
        (
            '<div class="structured-answer-box">'
            f'<div class="structured-answer-title">{escape_display_text(title)}</div>'
            '<div class="structured-answer-note">'
            'The imported model answer for this question is incomplete or not cleanly split, '
            'so this view uses the clean answer-bank fields.'
            '</div>'
            f'{"".join(section_html)}'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


def render_sample_answer_section(qd, expanded=False):
    model_points = (qd.get("model_points", "") or "").strip() if isinstance(qd, dict) else ""
    rules = (qd.get("rules", "") or "").strip() if isinstance(qd, dict) else ""
    quality = model_answer_quality(qd) if isinstance(qd, dict) else "missing"

    if not model_points and not rules and not (
        qd.get("tested_issues") or qd.get("trigger_facts")
    ):
        st.info("No sample answer/model analysis available for this question yet.")
        return

    with st.expander("Compare With Sample Answer - open after self-grading", expanded=expanded):
        st.warning("Open this only after you attempted the issue/rule. No passive reading.")
        # Priority: show the structured model_points whenever it is present and not
        # detectably corrupt. Only fall back to the rules-based structured view when
        # model_points is empty/None or known-damaged.
        if model_points and quality != "damaged":
            render_sample_answer_text("Sample Answer / Model Analysis", model_points)
        else:
            render_structured_model_analysis(qd, title="Structured Model Analysis")


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


def clean_trap_items(traps_text):
    return extract_trap_items(traps_text)


def render_trap_warnings(title, traps_text):
    traps = extract_trap_items(traps_text)

    if not traps:
        st.info("No trap warnings available yet.")
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


def render_rule_breakdown_card(
    title,
    rule_text="",
    elements=None,
    trigger_facts=None,
    application_hint="",
    trap="",
    source="",
):
    elements = elements or []
    trigger_facts = trigger_facts or []
    rule_text = re.sub(r"\s+", " ", str(rule_text or "")).strip()

    if len(rule_text) > 900:
        rule_text = rule_text[:900].rsplit(" ", 1)[0] + "..."

    elements_html = "".join(f"<li>{escape_display_text(el)}</li>" for el in elements)
    facts_html = "".join(f"<li>{escape_display_text(fact)}</li>" for fact in trigger_facts)
    safe_title = escape_display_text(title)
    safe_rule = escape_display_text(rule_text) if rule_text else "Rule support not found yet."
    safe_application = (
        escape_display_text(application_hint)
        if application_hint
        else "Connect each fact to a rule element."
    )
    safe_trap = (
        escape_display_text(trap)
        if trap
        else "Do not jump to conclusion before applying each element."
    )
    note_html = ""

    if source == "Model-derived fallback":
        note_html = (
            '<div class="rule-break-note">'
            'Note: This rule was pulled from model analysis. Prefer importing flashcards or Attack Outline rules for cleaner rules.'
            '</div>'
        )

    st.markdown(
        (
            '<div class="rule-break-card">'
            f'<div class="rule-break-title">{safe_title}</div>'
            '<div class="rule-break-section">'
            '<div class="rule-break-label">Rule</div>'
            f'<div class="rule-break-text">{safe_rule}</div>'
            '</div>'
            '<div class="rule-break-section">'
            '<div class="rule-break-label">Elements / Test</div>'
            f'<ul class="rule-break-list">{elements_html if elements_html else "<li>Identify the elements from the rule.</li>"}</ul>'
            '</div>'
            '<div class="rule-break-section">'
            '<div class="rule-break-label">Trigger Facts</div>'
            f'<ul class="rule-break-list">{facts_html if facts_html else "<li>No trigger facts matched yet.</li>"}</ul>'
            '</div>'
            '<div class="rule-break-section">'
            '<div class="rule-break-label">How facts apply</div>'
            f'<div class="rule-break-text">{safe_application}</div>'
            '</div>'
            '<div class="rule-break-trap">'
            f'<strong>Trap:</strong> {safe_trap}'
            '</div>'
            f'{note_html}'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


def split_rule_into_elements(rule_text):
    if not rule_text:
        return []

    text = str(rule_text).replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\s+", " ", text).strip()
    elements = []

    numbered = re.findall(r"(?:\(\d+\)|\d+\.)\s*([^;.\n]+(?:;|\.|$))", text)
    for item in numbered:
        item = item.strip(" ;.")
        if 5 <= len(item) <= 220:
            elements.append(item)

    if not elements:
        semi_parts = re.split(r";|\bAND\b|\bOR\b", text)
        for part in semi_parts:
            part = part.strip(" .;:")
            if 8 <= len(part) <= 220:
                elements.append(part)

    return elements[:6]


def infer_rule_title_from_call(call_text, subject):
    text = (call_text or "").lower()
    subject_l = (subject or "").lower()

    if "summary judgment" in text:
        return "Summary Judgment"
    if "proximate cause" in text or "causation" in text:
        return "Proximate Cause"
    if "negligence" in text and "statute" in text:
        return "Negligence Per Se"
    if "false imprisonment" in text or "detain" in text:
        return "False Imprisonment"
    if "forum" in text and ("first amendment" in subject_l or "constitutional" in subject_l):
        return "First Amendment Forum"
    if "content-based" in text or "content neutral" in text or "content-neutral" in text:
        return "Content-Based vs Content-Neutral Speech Regulation"
    if "actual authority" in text:
        return "Actual Authority"
    if "apparent authority" in text:
        return "Apparent Authority"
    if "agency" in text or "agent" in text:
        return "Creation of Agency"
    if "partnership" in text:
        return "Partnership Formation"
    if "diversity" in text:
        return "Diversity Jurisdiction"
    if "personal jurisdiction" in text:
        return "Personal Jurisdiction"
    if "hearsay" in text:
        return "Hearsay"
    if "statute of frauds" in text:
        return "Statute of Frauds"
    if "parol evidence" in text:
        return "Parol Evidence"
    if "adverse possession" in text:
        return "Adverse Possession"

    return "Rule Tested"


def find_rule_support_for_call(qd, call_text):
    subject = qd.get("subject", "")
    query = f"{call_text} {qd.get('tested_issues', '')}"

    try:
        flash_results = search_rule_flashcards(query, subject=subject, limit=3)
        if flash_results:
            card = flash_results[0]
            return {
                "title": card[2],
                "rule_text": card[3],
                "source": "Flashcards",
            }
    except Exception:
        pass

    try:
        outline_results = search_outline_rules(query, subject=subject, limit=3)
        if outline_results:
            rule = outline_results[0]
            return {
                "title": rule[2],
                "rule_text": rule[4],
                "source": "Attack Outline",
            }
    except Exception:
        pass

    try:
        plug_results = search_plug_play_templates(query, subject=subject, limit=3)
        if plug_results:
            tpl = plug_results[0]
            return {
                "title": tpl[2],
                "rule_text": tpl[5],
                "source": "Plug & Play",
            }
    except Exception:
        pass

    return {
        "title": infer_rule_title_from_call(call_text, subject),
        "rule_text": qd.get("rules", ""),
        "source": "Model-derived fallback",
    }


def build_rule_search_query(qd, call_text=""):
    parts = [
        call_text or "",
        qd.get("tested_issues", "") or "",
        qd.get("call_of_question", "") or "",
        qd.get("subject", "") or "",
    ]

    text = " ".join(parts)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:800]


def get_rule_skeleton_support(qd, call_text=""):
    query = build_rule_search_query(qd, call_text)
    subject = qd.get("subject", "")

    try:
        results = search_rule_flashcards(query, subject=subject, limit=5)
        if results:
            r = results[0]
            return {
                "source": "Flashcards2025",
                "title": r[2],
                "rule_text": r[3],
                "tags": r[5] if len(r) > 5 else "",
            }
    except Exception:
        pass

    try:
        results = search_outline_rules(query, subject=subject, limit=5)
        if results:
            r = results[0]
            return {
                "source": "Attack Outline",
                "title": r[2],
                "rule_text": r[4],
                "tags": "",
            }
    except Exception:
        pass

    try:
        results = search_plug_play_templates(query, subject=subject, limit=5)
        if results:
            r = results[0]
            return {
                "source": "Plug & Play",
                "title": r[2],
                "rule_text": r[5],
                "tags": "",
            }
    except Exception:
        pass

    raw_rules = qd.get("rules", "") or ""
    if len(raw_rules.strip()) > 20:
        return {
            "source": "Model-derived fallback",
            "title": "Model Rule / Analysis",
            "rule_text": raw_rules,
            "tags": "",
        }

    return {
        "source": "None",
        "title": "No rule skeleton found",
        "rule_text": "",
        "tags": "",
    }


def render_rule_skeleton(title, rule_support):
    source = rule_support.get("source", "Unknown")
    rule_title = rule_support.get("title", title)
    rule_text = rule_support.get("rule_text", "")

    if not rule_text:
        st.info("No rule skeleton found yet. Import Flashcards2025 or search the Rule Flashcards page.")
        try:
            if not get_rule_flashcards():
                st.warning("Rule Flashcards are not imported yet. Run: python import_flashcards2025.py Flashcards2025.rtf")
        except Exception:
            pass
        st.code("python import_flashcards2025.py Flashcards2025.rtf")
        return

    if source == "Model-derived fallback":
        st.warning(
            "This rule skeleton is from model analysis. It may include application. "
            "Prefer Flashcards2025 / Attack Outline rules for clean rule statements."
        )

    st.markdown(f"### {escape_display_text(rule_title)}")
    st.caption(f"Source: {source}")

    if "render_outline_rule_text" in globals():
        render_outline_rule_text("Rule Skeleton", rule_text)
    elif "render_readable_text" in globals():
        render_readable_text("Rule Skeleton", rule_text)
    else:
        st.write(rule_text)


def render_rule_skeletons_for_calls(qd):
    st.markdown("### Rule Skeleton")
    subquestions = extract_subquestions(qd.get("call_of_question", ""))

    if not subquestions:
        rule_support = get_rule_skeleton_support(qd)
        render_rule_skeleton("Rule Skeleton", rule_support)
        return

    for subq in subquestions:
        call_text = subq.get("text", "")
        if subq.get("subparts"):
            call_text += " " + " ".join([sp.get("text", "") for sp in subq["subparts"]])

        rule_support = get_rule_skeleton_support(qd, call_text)
        with st.expander(f"{subq.get('label', 'Question')} Rule Skeleton", expanded=True):
            render_rule_skeleton(f"{subq.get('label', 'Question')} Rule Skeleton", rule_support)


def get_trigger_facts_for_call(qd, call_text, max_facts=5):
    call_l = (call_text or "").lower()

    try:
        mapping = get_fact_sentences_for_subquestions(qd, max_per_question=max_facts)
        for item in mapping:
            item_text = item.get("call", {}).get("text", "")
            item_l = item_text.lower()
            if item_l and (item_l in call_l or call_l in item_l):
                return item.get("facts", [])[:max_facts]
    except Exception:
        pass

    try:
        facts = get_clean_trigger_facts(qd, max_items=max_facts)
        return facts[:max_facts]
    except Exception:
        pass

    return []


def infer_application_hint(rule_title, call_text, facts, qd):
    title = (rule_title or "").lower()
    call_l = (call_text or "").lower()

    if "summary judgment" in title or "summary judgment" in call_l:
        return "Ask whether the admitted facts leave any genuine dispute of material fact. Draw reasonable inferences against the moving party."
    if "proximate" in title or "causation" in title:
        return "Connect the defendant's conduct to the harm. Ask whether the harm was a reasonably foreseeable consequence."
    if "negligence per se" in title or ("negligence" in call_l and "statute" in call_l):
        return "Do not stop at statutory violation. Ask whether the plaintiff is in the protected class and whether the harm is the type the statute was designed to prevent."
    if "false imprisonment" in title or "detain" in call_l:
        return "Apply intent, confinement, lack of consent, and awareness or harm to the facts."
    if "actual authority" in title:
        return "Look for principal-to-agent manifestations and whether the agent reasonably believed they were authorized."
    if "apparent authority" in title:
        return "Look for principal-to-third-party manifestations and the third party's reasonable belief."
    if "agency" in title:
        return "Apply consent plus control. Do not assume agency merely because someone helped or acted voluntarily."
    if "forum" in title:
        return "Classify the location first. The forum determines the First Amendment test."
    if "content" in title:
        return "Ask whether the law targets speech because of message/topic or regulates conduct, time, place, or manner."

    return "Apply each rule element to the specific trigger facts. Do not write a rule dump."


def infer_rule_trap(rule_title, call_text, qd):
    title = (rule_title or "").lower()

    if "summary judgment" in title:
        return "Do not weigh evidence or draw inferences for the moving party."
    if "proximate" in title:
        return "Foreseeability can be a jury question; do not treat every causation issue as resolved as a matter of law."
    if "negligence per se" in title:
        return "Statutory violation is not enough unless protected class and protected harm are satisfied."
    if "false imprisonment" in title:
        return "Physical force is not required, but there must be confinement or restraint."
    if "actual authority" in title:
        return "Actual authority is based on principal-to-agent manifestations, not what the third party believed."
    if "apparent authority" in title:
        return "Apparent authority is based on principal-to-third-party manifestations, not secret instructions to the agent."
    if "forum" in title:
        return "Do not pick strict scrutiny or intermediate scrutiny before classifying the forum."
    if "content" in title:
        return "A safety purpose in the preamble does not automatically make a speech law content-neutral."

    traps = clean_trap_items(qd.get("traps", ""))
    return traps[0] if traps else "Do not jump to conclusion before applying every element."


def render_rules_tested_by_call(qd):
    st.markdown("### Rules Tested and Fact Application")

    subquestions = extract_subquestions(qd.get("call_of_question", "")) if "extract_subquestions" in globals() else []

    if not subquestions:
        subquestions = [{"label": "Question", "text": qd.get("call_of_question", ""), "subparts": []}]

    for subq in subquestions:
        call_text = subq.get("text", "")

        if subq.get("subparts"):
            subpart_text = " ".join([f"{sp.get('label', '')} {sp.get('text', '')}" for sp in subq["subparts"]])
            full_call = f"{call_text} {subpart_text}".strip()
        else:
            full_call = call_text

        rule_support = find_rule_support_for_call(qd, full_call)
        rule_title = rule_support.get("title", infer_rule_title_from_call(full_call, qd.get("subject", "")))
        rule_text = rule_support.get("rule_text", "")
        source = rule_support.get("source", "")
        elements = split_rule_into_elements(rule_text)
        facts = get_trigger_facts_for_call(qd, full_call)
        application_hint = infer_application_hint(rule_title, full_call, facts, qd)
        trap = infer_rule_trap(rule_title, full_call, qd)

        render_rule_breakdown_card(
            f"{subq.get('label', 'Question')} - {rule_title}",
            rule_text=rule_text,
            elements=elements,
            trigger_facts=facts,
            application_hint=application_hint,
            trap=trap,
            source=source,
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


def infer_fact_relevance(fact, qd):
    fact_l = fact.lower()
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


def render_trigger_facts_text(title, text):
    qd = text if isinstance(text, dict) else {"trigger_facts": text, "subject": "", "tested_issues": "", "rules": ""}
    render_trigger_facts(title, qd)


def render_raw_trigger_facts_expander(qd):
    original_text = qd.get("trigger_facts", "") or ""
    if not original_text:
        return

    with st.expander("Original trigger facts text", expanded=False):
        render_readable_text("Original Trigger Facts", clean_trigger_facts_text(original_text), READING_FONT_SIZE)


def render_trigger_facts(title, qd):
    facts = get_clean_trigger_facts(qd)

    if not facts:
        st.info("No trigger facts available yet.")
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


def render_tested_issues(title, tested_issues_text):
    issues = extract_issue_bullets(tested_issues_text)

    if not issues:
        cleaned = clean_tested_issues_text(tested_issues_text)
        render_readable_text(title, cleaned, READING_FONT_SIZE)
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


def render_raw_tested_issues_expander(qd):
    original_text = qd.get("tested_issues", "") or ""
    if not original_text:
        return

    with st.expander("Original tested issues text", expanded=False):
        render_tested_issues("Original Tested Issues", original_text)


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

    st.info("Colors show which facts likely support each call of the question.")
    if show_explanations:
        st.info("Hover over or click a highlighted fact to see why it matters.")
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

    with st.expander("Detected facts by question", expanded=False):
        for item in mapping:
            st.markdown(f"**{item['label']}**")
            if item["facts"]:
                for fact in item["facts"]:
                    st.write("- " + fact)
            else:
                st.info("No specific facts detected for this call.")


def render_question_highlights_with_fallback(title, qd, text=None, show_explanations=True):
    try:
        render_question_specific_highlighted_facts(title, qd, show_explanations=show_explanations)
    except Exception:
        st.warning("Question-specific highlighting failed; showing universal highlights instead.")
        render_universal_highlighted_fact_pattern(title, qd, text=text)


def render_trigger_candidate_diagnostics(qd):
    with st.expander("Detected trigger facts for highlighting", expanded=False):
        candidates = get_universal_trigger_candidates(qd)
        if candidates:
            st.caption(f"{len(candidates)} candidate trigger facts detected. Showing the shortest useful preview.")

            preview_items = candidates[:6]
            preview_html = ""
            for candidate in preview_items:
                short = re.sub(r"\s+", " ", str(candidate)).strip()
                if len(short) > 150:
                    short = short[:150].rsplit(" ", 1)[0] + "..."
                preview_html += f'<div class="trigger-mini-chip">{escape_display_text(short)}</div>'

            st.markdown(f'<div class="trigger-mini-grid">{preview_html}</div>', unsafe_allow_html=True)

            if len(candidates) > len(preview_items):
                st.caption(f"{len(candidates) - len(preview_items)} more hidden to keep the page compact.")

            with st.expander("Show full detected trigger list", expanded=False):
                for candidate in candidates:
                    st.write("- " + candidate)
        else:
            st.info("No trigger facts detected yet.")


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
        r"Ã‚Â©\s*\d{4}.*",
        r"Â©\s*\d{4}.*",
        r"National Conference of Bar Examiners.*",
        r".*Question Bank.*",
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
    text = text.replace("ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â§", "Â§").replace("Ãƒâ€šÃ‚Â§", "Â§").replace("Ã‚Â§", "Â§")
    text = text.replace("ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â©", "Â©").replace("Ãƒâ€šÃ‚Â©", "Â©").replace("Ã‚Â©", "Â©")

    junk_patterns = [
        r"Ãƒâ€šÃ‚Â©\s*\d{4}\s+LegacySource.*",
        r"Ã‚Â©\s*\d{4}\s+LegacySource.*",
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
    text = re.sub(r"Â§\s+(\d+)\.\s+(\d+)", r"Â§ \1.\2", text)
    text = re.sub(r"(?<=[a-z0-9])\.(?=[A-Z])", ". ", text)
    text = re.sub(r"Ãƒâ€šÃ‚Â§\s+(\d+)\.\s+(\d+)", r"Ã‚Â§ \1.\2", text)
    text = re.sub(r"Ã‚Â§\s+(\d+)\.\s+(\d+)", r"Ã‚Â§ \1.\2", text)

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

    caption_parts = []
    if subject:
        caption_parts.append(f"Subject: {subject}")
    if appearance_rate:
        caption_parts.append(f"Appearance Rate: {appearance_rate}")
    if pdf_page:
        caption_parts.append(f"PDF Page: {pdf_page}")

    if caption_parts:
        st.caption(" | ".join(caption_parts))

    render_outline_rule_text(rule_title or "Attack Outline Rule", rule_text)

    if pdf_page:
        link = outline_pdf_link(pdf_page)
        if link:
            st.markdown(
                f'<a href="{link}" target="_blank">Open Outline Page</a>',
                unsafe_allow_html=True,
            )


FLASHCARD_EXPORT_CSS = """
body { background:#f5f4f0; font-family: Arial, sans-serif; margin: 20px; color:#1a1a1a; }
.flash-page-wrap { background:#f5f4f0; padding:1rem; border-radius:18px; }
.flash-header { margin-bottom:1rem; border-bottom:2px solid #1a1a1a; padding-bottom:.75rem; display:flex; justify-content:space-between; align-items:flex-end; gap:1rem; }
.flash-header h2 { font-size:13px; font-weight:800; letter-spacing:.12em; text-transform:uppercase; color:#1a1a1a; margin:0; }
.flash-header .flash-meta { font-size:11px; color:#666; font-family:monospace; }
.flash-grid { display:grid; grid-template-columns:repeat(2, minmax(320px, 1fr)); gap:16px; }
.flash-card { background:#fff; border:1px solid #d0cfc9; border-radius:6px; overflow:hidden; break-inside:avoid; page-break-inside:avoid; }
.flash-front { background:#1a1a1a; color:#f5f4f0; padding:14px 16px; border-bottom:3px solid #e85d26; }
.flash-card-num { font-family:monospace; font-size:10px; color:#e85d26; letter-spacing:.1em; margin-bottom:6px; }
.flash-front h3 { font-size:14px; font-weight:700; line-height:1.35; margin:0 0 8px 0; color:#f5f4f0; }
.flash-question { font-size:12px; color:#b8b5ae; line-height:1.5; font-style:italic; }
.flash-back { padding:14px 16px; background:#fff; }
.flash-rule-line { display:flex; gap:8px; align-items:flex-start; margin-bottom:6px; font-size:12px; line-height:1.5; }
.flash-rule-key { font-family:monospace; font-size:11px; font-weight:700; color:#e85d26; min-width:120px; flex-shrink:0; padding-top:1px; }
.flash-rule-val { color:#1a1a1a; }
.flash-trap-box { background:#fff8f5; border-left:3px solid #e85d26; padding:7px 10px; margin-top:10px; font-size:11px; color:#663300; line-height:1.5; }
.flash-key-rule { background:#f0f9f0; border-left:3px solid #2a7a2a; padding:7px 10px; margin-top:10px; font-size:11px; color:#1a3d1a; line-height:1.5; }
.flash-mini-title { display:block; font-size:10px; letter-spacing:.08em; text-transform:uppercase; margin-bottom:3px; font-weight:800; }
.flash-tags { margin-top:10px; display:flex; flex-wrap:wrap; gap:4px; }
.flash-tag { font-family:monospace; font-size:10px; background:#f0efe9; color:#666; padding:2px 7px; border-radius:3px; }
@media print { body { margin: 10px; background:#fff; } .flash-page-wrap { background:#fff; } .flash-grid { gap:12px; } }
"""


def short_text(text, max_chars=420):
    if not text:
        return ""

    text = re.sub(r"\s+", " ", str(text)).strip()

    if len(text) <= max_chars:
        return text

    return text[:max_chars].rsplit(" ", 1)[0] + "..."


def _flash_tags(subject, title, source):
    words = re.findall(r"[A-Za-z][A-Za-z0-9&-]{2,}", f"{subject or ''} {title or ''}")
    tags = [subject, source]

    for word in words[:5]:
        if word.lower() not in {str(t).lower() for t in tags if t}:
            tags.append(word)

    return [str(tag) for tag in tags if tag][:7]


def make_rule_card_from_outline(rule, index):
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

    return {
        "num": index,
        "category": subject or "Rule",
        "title": rule_title or "Untitled Rule",
        "question": f"What is the rule for {rule_title or 'this doctrine'}?",
        "rule_lines": [
            ("Source", "Attack Outline"),
            ("Appearance", appearance_rate or "Not specified"),
            ("Rule", short_text(rule_text, 520)),
        ],
        "key_rule": short_text(rule_text, 360),
        "trap": "Recite elements first; then apply facts. Do not jump to conclusion.",
        "tags": _flash_tags(subject, rule_title, "Attack Outline"),
    }


def make_rule_card_from_template(template, index):
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

    return {
        "num": index,
        "category": subject or "Template",
        "title": module_title or "Untitled Template",
        "question": issue_statement or f"What is the framework for {module_title or 'this issue'}?",
        "rule_lines": [
            ("Source", "Plug & Play"),
            ("Trigger", short_text(scenario_trigger, 220)),
            ("Rule", short_text(rule_text, 520)),
        ],
        "key_rule": short_text(rule_text, 360),
        "trap": short_text(testing_notes, 320) or "Use the template; do not write a rule dump.",
        "tags": _flash_tags(subject, module_title, "Plug & Play"),
    }


def make_rule_card_from_flashcard(card, index):
    card_id, subject, rule_title, rule_text, source_file, tags = card

    tag_list = [tag for tag in str(tags or "").split() if tag]
    if not tag_list:
        tag_list = _flash_tags(subject, rule_title, "Flashcards")

    return {
        "num": index,
        "category": subject or "Rule",
        "title": rule_title or "Untitled Rule",
        "question": f"What is the rule for {rule_title or 'this doctrine'}?",
        "rule_lines": [
            ("Source", "Flashcards" if (source_file or "").lower() == "flashcards2025.rtf" else (source_file or "Flashcards")),
            ("Subject", subject or "Unknown"),
            ("Rule", short_text(rule_text, 620)),
        ],
        "key_rule": short_text(rule_text, 420),
        "trap": "Recite elements first, then apply facts.",
        "tags": tag_list[:7],
    }


def render_rule_flashcard_box(card):
    card_id, subject, rule_title, rule_text, source_file, tags = card
    card_dict = make_rule_card_from_flashcard(card, 1)
    card_dict["rule_lines"] = [
        ("Subject", subject or "Unknown"),
        ("Source", "Flashcards" if (source_file or "").lower() == "flashcards2025.rtf" else (source_file or "Flashcards")),
        ("Rule", short_text(rule_text, 1200)),
    ]
    st.markdown(flashcard_html(card_dict), unsafe_allow_html=True)


def find_relevant_rule_flashcards(query, subject=None, limit=3):
    if "search_rule_flashcards" not in globals():
        return []

    results = search_rule_flashcards(query, subject=subject, limit=limit)

    if not results and subject and subject != "All":
        results = search_rule_flashcards(query, subject=None, limit=limit)

    return results[:limit]


def flashcard_html(card):
    rule_lines_html = ""

    for key, value in card.get("rule_lines", []):
        if not value:
            continue
        rule_lines_html += (
            '<div class="flash-rule-line">'
            f'<div class="flash-rule-key">{escape_display_text(key)}</div>'
            f'<div class="flash-rule-val">{escape_display_text(value)}</div>'
            '</div>'
        )

    tags_html = "".join(
        f'<span class="flash-tag">{escape_display_text(tag)}</span>'
        for tag in card.get("tags", [])
        if tag
    )

    return f"""
    <div class="flash-card">
      <div class="flash-front">
        <div class="flash-card-num">CARD {int(card.get("num", 0)):02d} Â· {escape_display_text(card.get("category", ""))}</div>
        <h3>{escape_display_text(card.get("title", ""))}</h3>
        <div class="flash-question">{escape_display_text(card.get("question", ""))}</div>
      </div>
      <div class="flash-back">
        {rule_lines_html}
        <div class="flash-key-rule"><span class="flash-mini-title">Key Rule</span>{escape_display_text(card.get("key_rule", ""))}</div>
        <div class="flash-trap-box"><span class="flash-mini-title">Trap</span>{escape_display_text(card.get("trap", ""))}</div>
        <div class="flash-tags">{tags_html}</div>
      </div>
    </div>
    """


def render_flashcard(card):
    st.markdown(flashcard_html(card), unsafe_allow_html=True)


def flashcard_grid_html(cards):
    cards_html = "".join(flashcard_html(card) for card in cards)
    return f"""
    <div class="flash-page-wrap">
      <div class="flash-header">
        <h2>MEE Rule Flashcards</h2>
        <div class="flash-meta">{len(cards)} cards Â· print-ready</div>
      </div>
      <div class="flash-grid">{cards_html}</div>
    </div>
    """


def render_flashcard_grid(cards):
    st.markdown(flashcard_grid_html(cards), unsafe_allow_html=True)


def build_flashcards_html_document(cards):
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>MEE Rule Flashcards</title>
  <style>{FLASHCARD_EXPORT_CSS}</style>
</head>
<body>
{flashcard_grid_html(cards)}
</body>
</html>
"""


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
    trigger_items = get_clean_trigger_facts(qd, max_items=5)

    if trigger_items:
        return "\n".join(trigger_items[:5])

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
    rule_hint = ""

    try:
        support = get_rule_skeleton_support(qd)
        if support.get("rule_text"):
            rule_hint = (
                f"{support.get('title', 'Rule Skeleton')}\n"
                f"Source: {support.get('source', 'Unknown')}\n\n"
                f"{first_nonempty_lines(support.get('rule_text', ''), 4)}"
            )
    except Exception:
        rule_hint = ""

    if not rule_hint:
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
            elif hint_title.startswith("Hint 5"):
                render_trap_warnings("Trap Warning", hint_text)
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

    fact_text = (
        extract_fact_pattern_only(question_text)
        if "extract_fact_pattern_only" in globals()
        else question_text
    )
    cleaned = clean_fact_pattern_text(fact_text)

    if len(cleaned) <= max_chars:
        return cleaned

    return cleaned[:max_chars].rsplit(" ", 1)[0] + "... [mini packet ends - open full question if needed]"


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


def get_rule_flash_prompts(qd):
    prompts = []

    if "extract_subquestions" in globals():
        subquestions = extract_subquestions(qd.get("call_of_question", ""))

        for subq in subquestions:
            text = subq.get("text", "")
            if text:
                prompts.append(text)

            for subpart in subq.get("subparts", []):
                if subpart.get("text"):
                    prompts.append(subpart["text"])

    if "extract_issue_bullets" in globals():
        for issue in extract_issue_bullets(qd.get("tested_issues", "")):
            prompts.append(issue)

    if not prompts:
        prompts.append(qd.get("call_of_question", "Write the rule tested by this question."))

    clean = []
    seen = set()

    for prompt in prompts:
        prompt = re.sub(r"\s+", " ", str(prompt)).strip()

        if len(prompt) < 8:
            continue

        key = prompt.lower()
        if key not in seen:
            seen.add(key)
            clean.append(prompt)

    return clean[:8]


def mini_drill_state_key(qd, suffix):
    return f"mini_drill_{qd['id']}_{suffix}"


def init_mini_drill_state(qd, total_questions):
    active_key = mini_drill_state_key(qd, "active_index")
    done_key = mini_drill_state_key(qd, "done_questions")

    if active_key not in st.session_state:
        st.session_state[active_key] = 0

    if done_key not in st.session_state:
        st.session_state[done_key] = set()
    elif not isinstance(st.session_state[done_key], set):
        st.session_state[done_key] = set(st.session_state[done_key] or [])

    if total_questions <= 0:
        st.session_state[active_key] = 0
    elif st.session_state[active_key] >= total_questions:
        st.session_state[active_key] = max(0, total_questions - 1)


def render_mini_drill_progress(qd, subquestions):
    active_key = mini_drill_state_key(qd, "active_index")
    done_key = mini_drill_state_key(qd, "done_questions")

    active_idx = st.session_state.get(active_key, 0)
    done = st.session_state.get(done_key, set())

    chips = []
    for i, subq in enumerate(subquestions):
        label = escape_display_text(subq.get("label", f"Question {i + 1}"))
        if i in done:
            status_class = "mini-step-done"
            status_text = "Done"
        elif i == active_idx:
            status_class = "mini-step-active"
            status_text = "Active"
        else:
            status_class = "mini-step-locked"
            status_text = "Next"

        chips.append(
            f'<div class="mini-step-chip {status_class}"><strong>{label}</strong><span>{status_text}</span></div>'
        )

    st.markdown(
        (
            '<div class="mini-progress-box">'
            '<div class="mini-progress-title">Mini Drill Progress</div>'
            f'<div class="mini-progress-row">{"".join(chips)}</div>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


def reset_mini_drill_progress(qd):
    prefixes = (
        f"mini_drill_{qd['id']}_",
        f"mini_answer_piece_{qd['id']}_",
        f"mini_score_piece_{qd['id']}_",
        f"mini_missed_piece_{qd['id']}_",
        f"mini_fix_piece_{qd['id']}_",
        f"mini_reveal_{qd['id']}_",
    )

    for key in list(st.session_state.keys()):
        if any(str(key).startswith(prefix) for prefix in prefixes):
            del st.session_state[key]


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


def get_model_section_for_subquestion(qd, subq_index, subpart=None):
    # Priority: split from model_points. Rules is only used as the structured
    # fallback below (when model_points has no usable per-call breakdown).
    model_text = qd.get("model_points", "") or ""
    points = split_model_answer_points(model_text)
    wanted_subpart = (subpart or None)
    quality = model_answer_quality(qd)

    for p in points:
        if quality in ("usable", "partial") and p["num"] == subq_index and (p.get("subpart") or None) == wanted_subpart:
            return p["heading"], p["text"]

    if quality in ("usable", "partial") and wanted_subpart is None:
        matching = [p for p in points if p["num"] == subq_index]
        if matching:
            combined = "\n\n".join([p["text"] for p in matching])
            heading = f"Point {subq_index} - Combined"
            return heading, combined

    if qd.get("tested_issues") or qd.get("rules") or qd.get("trigger_facts"):
        subquestions = flatten_subquestions_for_answer_mapping(qd)
        call_text = ""
        for subq in subquestions:
            if subq.get("num") == subq_index and (subq.get("subpart") or None) == wanted_subpart:
                call_text = subq.get("text", "")
                break

        return (
            f"Structured Model Analysis - Question {subq_index}",
            call_text,
        )

    return None, ""


def render_sample_answer_for_subquestion(qd, subq_index, label, subpart=None):
    title = label or f"Question {subq_index}"

    try:
        section_heading, model_text = get_model_section_for_subquestion(qd, subq_index, subpart)
    except Exception:
        section_heading, model_text = "", ""

    if not model_text:
        st.info(f"No sample answer/model analysis is available for {title} yet.")
        return

    with st.expander(f"Compare With Sample Answer - {title}", expanded=False):
        st.warning("Open only after you attempted this call.")
        if str(section_heading or "").startswith("Structured Model Analysis"):
            render_structured_model_analysis(
                qd,
                call_text=model_text,
                title=section_heading or f"Sample Answer - {title}",
            )
        else:
            render_sample_answer_text(section_heading or f"Sample Answer - {title}", model_text)


def render_single_mini_question_workflow(qd, subq, display_index, hints_used=0):
    label = subq.get("label", f"Question {display_index}")
    answer_num = subq.get("num", display_index)
    answer_subpart = subq.get("subpart")
    answer_piece = render_subquestion_card(qd, subq, display_index, hints_used)

    st.markdown("### Step 2: Check this question")
    reveal_key = f"mini_reveal_{qd['id']}_{display_index}"

    if st.button(f"Reveal / Check {label}", key=f"{reveal_key}_button"):
        st.session_state[f"{reveal_key}_shown"] = True

    if st.session_state.get(f"{reveal_key}_shown", False):
        call_text = subq.get("text", "").strip()
        if subq.get("subparts"):
            subpart_text = "\n".join(
                [f"{part.get('label', '')} {part.get('text', '')}".strip() for part in subq["subparts"]]
            )
            full_call = f"{call_text}\n{subpart_text}".strip()
        else:
            full_call = call_text or "No call text available."

        try:
            rule_support = find_rule_support_for_call(qd, full_call)
            rule_title = rule_support.get("title", "Rule Tested")
            rule_text = rule_support.get("rule_text", "")
            source = rule_support.get("source", "")
            elements = split_rule_into_elements(rule_text) if "split_rule_into_elements" in globals() else []
            facts = get_trigger_facts_for_call(qd, full_call) if "get_trigger_facts_for_call" in globals() else []
            application_hint = (
                infer_application_hint(rule_title, full_call, facts, qd)
                if "infer_application_hint" in globals()
                else ""
            )
            trap = infer_rule_trap(rule_title, full_call, qd) if "infer_rule_trap" in globals() else ""

            render_rule_breakdown_card(
                rule_title,
                rule_text=rule_text,
                elements=elements,
                trigger_facts=facts,
                application_hint=application_hint,
                trap=trap,
                source=source,
            )
        except Exception:
            st.warning("Rule breakdown unavailable for this call.")

        render_sample_answer_for_subquestion(qd, answer_num, label, subpart=answer_subpart)

        st.markdown("### Step 3: Score this question")

        col1, col2, col3 = st.columns(3)
        with col1:
            issue_score = st.slider(
                f"{label} issue score",
                0,
                5,
                0,
                key=f"mini_issue_score_{qd['id']}_{display_index}",
            )
        with col2:
            rule_score = st.slider(
                f"{label} rule score",
                0,
                5,
                0,
                key=f"mini_rule_score_{qd['id']}_{display_index}",
            )
        with col3:
            fact_score = st.slider(
                f"{label} fact score",
                0,
                5,
                0,
                key=f"mini_fact_score_{qd['id']}_{display_index}",
            )

        avg_score = round((issue_score + rule_score + fact_score) / 3)

        missed = st.text_area(
            f"{label} - What did you miss?",
            placeholder="Example: I missed the exception or the key trigger fact.",
            height=80,
            key=f"mini_missed_{qd['id']}_{display_index}",
        )

        fix_note = st.text_area(
            f"{label} - Fix note",
            placeholder="One sentence for future you.",
            height=80,
            key=f"mini_fix_{qd['id']}_{display_index}",
        )

        st.metric(f"{label} score", f"{avg_score}/5")

        done_key = mini_drill_state_key(qd, "done_questions")
        active_key = mini_drill_state_key(qd, "active_index")

        if st.button(f"Mark {label} Done", key=f"mini_done_{qd['id']}_{display_index}"):
            if done_key not in st.session_state or not isinstance(st.session_state[done_key], set):
                st.session_state[done_key] = set(st.session_state.get(done_key, []))

            st.session_state[done_key].add(display_index - 1)
            st.session_state[f"mini_answer_piece_{qd['id']}_{display_index}"] = answer_piece
            st.session_state[f"mini_score_piece_{qd['id']}_{display_index}"] = avg_score
            st.session_state[f"mini_missed_piece_{qd['id']}_{display_index}"] = missed
            st.session_state[f"mini_fix_piece_{qd['id']}_{display_index}"] = fix_note

            total = len(flatten_subquestions_for_answer_mapping(qd))
            if display_index < total:
                st.session_state[active_key] = display_index
            else:
                st.session_state[active_key] = display_index - 1

            st.success(f"{label} marked done.")
            st.rerun()

    return answer_piece


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
            flashcard_matches = find_relevant_rule_flashcards(
                f"{full_call}\n{qd.get('tested_issues', '')}",
                subject=qd.get("subject", ""),
                limit=3,
            )

            if flashcard_matches:
                st.markdown("##### Flashcard Rules")
                for card in flashcard_matches:
                    render_rule_flashcard_box(card)

            if outline_matches:
                st.markdown("##### Attack Outline Rules")
                for rule in outline_matches:
                    render_attack_rule_box(rule)
            elif not flashcard_matches:
                st.info("No exact outline rule found for this call yet.")

    issue_sentence = ""
    rule_sentence = ""
    application = ""
    counterargument = ""
    conclusion = ""

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


_BADGE_MAP = {
    "Active standalone MEE":                ("ACTIVE",       "badge-active"),
    "Retired standalone - background only": ("RETIRED",      "badge-retired"),
    "MPT background only":                  ("MPT BG",       "badge-mpt"),
    "Historical / low priority":            ("LOW PRIORITY", "badge-low"),
}


def render_question_strip(qd):
    status = qd.get("july_2026_status", "") or ""
    badge_label, badge_class = _BADGE_MAP.get(status, ("UNKNOWN", "badge-low"))
    priority = qd.get("priority") or "-"
    st.markdown(
        f'<div class="question-strip">'
        f'<strong>{escape_display_text(qd["exam_name"])} Q{escape_display_text(str(qd["question_number"]))}</strong>'
        f'<span class="muted">{escape_display_text(qd["subject"])}</span>'
        f'<span class="badge {badge_class}">{badge_label}</span>'
        f'<span class="muted">Priority {escape_display_text(str(priority))}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    render_data_health_warning(qd)


def render_meta_strip(qd):
    status = qd.get("july_2026_status", "") or "-"
    st.markdown(
        f"""
        <div class="meta-strip">
          <span><b>{escape_display_text(qd['exam_name'])} Q{escape_display_text(str(qd['question_number']))}</b></span>
          <span>{escape_display_text(qd['subject'])}</span>
          <span class="badge-active">{escape_display_text(status)}</span>
          <span>Priority {escape_display_text(str(qd.get('priority') or '-'))}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_data_health_warning(qd)


def section_card(title=None, body=None):
    if title:
        st.markdown(f"### {title}")
    if body:
        st.markdown(body)


def render_step_block(step_n, total, label, description=""):
    st.markdown(
        f'<div class="step-block">'
        f'<div class="step-label">Step {step_n} of {total}</div>'
        f'<div class="step-title">{escape_display_text(label)}</div>'
        + (f'<div class="muted" style="margin-top:0.2rem">{escape_display_text(description)}</div>' if description else "")
        + "</div>",
        unsafe_allow_html=True,
    )
    st.progress((step_n - 1) / max(total - 1, 1))


def study_tip(text):
    st.markdown(
        f'<div class="study-tip">{escape_display_text(text)}</div>',
        unsafe_allow_html=True,
    )


def reveal_gate_box(text):
    st.markdown(
        f'<div class="reveal-gate">{escape_display_text(text)}</div>',
        unsafe_allow_html=True,
    )


def render_stopwatch(key):
    """Live ticking stopwatch with Start/Pause/Reset. Returns elapsed seconds."""
    run_key = f"sw_running_{key}"
    start_key = f"sw_start_{key}"
    accum_key = f"sw_accum_{key}"

    st.session_state.setdefault(run_key, False)
    st.session_state.setdefault(start_key, 0.0)
    st.session_state.setdefault(accum_key, 0.0)

    running = st.session_state[run_key]
    elapsed = st.session_state[accum_key]
    if running:
        elapsed += time.time() - st.session_state[start_key]

    disp_col, start_col, reset_col = st.columns([3, 1, 1])

    with disp_col:
        running_js = "true" if running else "false"
        base_seconds = float(st.session_state[accum_key])
        started_ms = int(st.session_state[start_key] * 1000)
        accent = "#0D9488" if running else "#4A6585"
        components.html(
            f"""
            <div style="font-family:'Segoe UI',system-ui,sans-serif;
                        background:#FFFFFF;border:1.5px solid #D1E3F8;
                        border-left:4px solid {accent};border-radius:10px;
                        padding:0.55rem 1rem;display:flex;align-items:center;gap:0.7rem">
              <span style="font-size:0.72rem;font-weight:700;letter-spacing:0.06em;
                           text-transform:uppercase;color:#4A6585">Stopwatch</span>
              <span id="sw_display" style="font-size:1.7rem;font-weight:700;
                           font-variant-numeric:tabular-nums;color:#1D3557;
                           letter-spacing:0.02em">00:00</span>
            </div>
            <script>
              var running = {running_js};
              var base = {base_seconds};
              var startedMs = {started_ms};
              function fmt(total) {{
                if (total < 0) total = 0;
                var h = Math.floor(total / 3600);
                var m = Math.floor((total % 3600) / 60);
                var s = Math.floor(total % 60);
                var mm = String(m).padStart(2, '0');
                var ss = String(s).padStart(2, '0');
                return h > 0 ? (h + ':' + mm + ':' + ss) : (mm + ':' + ss);
              }}
              function tick() {{
                var total = base;
                if (running) {{ total += (Date.now() - startedMs) / 1000; }}
                var el = document.getElementById('sw_display');
                if (el) {{ el.textContent = fmt(total); }}
              }}
              tick();
              if (running) {{ setInterval(tick, 250); }}
            </script>
            """,
            height=64,
        )

    with start_col:
        if st.button("Pause" if running else "Start", key=f"sw_toggle_{key}", use_container_width=True):
            if running:
                st.session_state[accum_key] += time.time() - st.session_state[start_key]
                st.session_state[run_key] = False
            else:
                st.session_state[start_key] = time.time()
                st.session_state[run_key] = True
            st.rerun()

    with reset_col:
        if st.button("Reset", key=f"sw_reset_{key}", use_container_width=True):
            st.session_state[run_key] = False
            st.session_state[start_key] = 0.0
            st.session_state[accum_key] = 0.0
            st.rerun()

    return elapsed


def stopwatch_minutes(key):
    """Elapsed whole minutes for the given stopwatch, for prefilling minutes_spent."""
    accum = st.session_state.get(f"sw_accum_{key}", 0.0)
    if st.session_state.get(f"sw_running_{key}", False):
        accum += time.time() - st.session_state.get(f"sw_start_{key}", time.time())
    return int(round(accum / 60))


def question_picker(active_default=True, due_only=False, compact=False):
    subjects = ["All"] + get_subjects()
    statuses = ["All"] + get_statuses()

    if compact:
        st.markdown('<div class="compact-picker">', unsafe_allow_html=True)
        col1, col2, col3, col4 = st.columns([1, 1, 0.85, 1.15], gap="small")
    else:
        col1, col2, col3 = st.columns(3)

    with col1:
        subject_filter = st.selectbox("Subject filter", subjects, key=f"subject_filter_{compact}_{due_only}")

    with col2:
        status_filter = st.selectbox("July 2026 status", statuses, key=f"status_filter_{compact}_{due_only}")

    with col3:
        active_only = st.checkbox("Active July 2026 only", value=active_default, key=f"active_only_{compact}_{due_only}")

    if compact:
        with col4:
            search = st.text_input(
                "Search",
                placeholder="hearsay, PMSI, jurisdiction",
                key=f"question_search_{compact}_{due_only}",
            )
    else:
        search = st.text_input(
            "Search issues / rules / traps",
            placeholder="e.g., hearsay, PMSI, personal jurisdiction",
            key=f"question_search_{compact}_{due_only}",
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
        if compact:
            st.markdown("</div>", unsafe_allow_html=True)
        return None

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

    if compact:
        pick_col, select_col, count_col = st.columns([0.75, 3.2, 0.8], gap="small")
    else:
        st.caption(f"{len(questions)} matching questions")
        surprise_col, count_col = st.columns([1, 3])

        with surprise_col:
            if st.button("Pick for me", key=f"{picker_key}_surprise"):
                selected_index = random.randrange(len(questions))
                st.session_state[picker_key] = selected_index
                st.session_state[select_key] = labels[selected_index]

        with count_col:
            st.write("Use the picker when you know what you want; use random when starting is the hard part.")

    if compact:
        with pick_col:
            if st.button("Pick for me", key=f"{picker_key}_surprise", use_container_width=True):
                selected_index = random.randrange(len(questions))
                st.session_state[picker_key] = selected_index
                st.session_state[select_key] = labels[selected_index]
        with select_col:
            selected_label = st.selectbox("Pick a question", labels, key=select_key)
        with count_col:
            st.markdown(f'<div class="picker-count">{len(questions)} matches</div>', unsafe_allow_html=True)
    else:
        selected_label = st.selectbox("Pick a question", labels, key=select_key)

    selected_index = labels.index(selected_label)
    st.session_state[picker_key] = selected_index

    if compact:
        st.markdown("</div>", unsafe_allow_html=True)

    return questions[selected_index][0]


NAV_GROUPS = [
    ("MEE - TRAIN",   ["Dashboard", "Mini Essay Drill", "Muscle Ladder", "Timed IRAC Drill"]),
    ("MEE - DRILLS",  ["Issue Spotting Drill", "Rule Flashcards", "Due Review Queue"]),
    ("MEE - LIBRARY", ["Attack Outline Rules", "Plug & Play Templates", "Review Attempts"]),
    ("MEE - MANAGE",  ["Question Bank"]),
    ("MBE",           ["MBE Drills"]),
]

if st.session_state.get("_is_admin"):
    NAV_GROUPS = NAV_GROUPS + [("ADMIN", ["Manage Users"])]

_menu_aliases = {
    "Daily Workout": "Dashboard",
    "Muscle Ladder": "MEE Muscle Ladder",
    "Question Bank": "Bulk Import MEE Bank",
}

if "current_page" not in st.session_state:
    st.session_state["current_page"] = "Dashboard"

for _group_name, _pages in NAV_GROUPS:
    st.sidebar.markdown(f'<div class="nav-group-label">{_group_name}</div>', unsafe_allow_html=True)
    for _page in _pages:
        _is_active = st.session_state["current_page"] == _page
        if st.sidebar.button(
            _page,
            key=f"nav_btn_{_page}",
            use_container_width=True,
            type="primary" if _is_active else "secondary",
        ):
            st.session_state["current_page"] = _page
            st.rerun()

menu = _menu_aliases.get(st.session_state["current_page"], st.session_state["current_page"])

if st.session_state.get("_authed_user"):
    st.sidebar.markdown(
        f"<div style='font-size:0.8rem;color:#4A6585;margin-top:0.6rem'>Signed in as "
        f"<b>{escape(str(st.session_state.get('_authed_name', st.session_state['_authed_user'])))}</b></div>",
        unsafe_allow_html=True,
    )
    if st.sidebar.button("Sign out", key="logout_btn", use_container_width=True):
        st.session_state.pop("_authed_user", None)
        st.session_state.pop("_authed_name", None)
        st.rerun()

st.sidebar.markdown("### Reading Comfort")
if "adhd_mode" not in st.session_state:
    st.session_state["adhd_mode"] = False
ADHD_READING_MODE = st.sidebar.checkbox(
    "Reading mode (larger text)",
    value=st.session_state["adhd_mode"],
    key="adhd_checkbox",
)
st.session_state["adhd_mode"] = ADHD_READING_MODE

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
    font-weight: 700 !important;
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
</style>
""", unsafe_allow_html=True)

if ADHD_READING_MODE:
    render_reading_mode_notice()


if menu == "Dashboard":
    stats = get_dashboard_stats()
    render_page_title("Daily Workout", "One tiny useful rep. No overwhelm.")

    st.markdown('<div class="dashboard-wrap">', unsafe_allow_html=True)

    def compact_metric(label, value):
        st.markdown(
            (
                '<div class="compact-metric">'
                f'<div class="metric-label">{escape(str(label))}</div>'
                f'<div class="metric-value">{escape(str(value))}</div>'
                '</div>'
            ),
            unsafe_allow_html=True,
        )

    metric_cols = st.columns(5)
    metric_values = [
        ("Questions", stats["total_questions"]),
        ("Active", stats["active_questions"]),
        ("Attempts", stats["total_attempts"]),
        ("Avg Score", stats["avg_score"]),
        ("Due Reviews", stats["due_reviews"]),
    ]
    for metric_col, (label, value) in zip(metric_cols, metric_values):
        with metric_col:
            compact_metric(label, value)

    rule_bank_cards = get_rule_flashcards() if "get_rule_flashcards" in globals() else []
    rule_bank_subjects = sorted({row[1] for row in rule_bank_cards if len(row) > 1 and row[1]})

    left_col, mid_col, right_col = st.columns([1.15, 1.15, 1], gap="medium")

    with left_col:
        st.markdown(
            """
            <div class="compact-card">
                <h3>Today's Workout</h3>
                <div class="workout-step"><strong>Mini Essay Drill</strong><span>8 min</span></div>
                <div class="workout-step"><strong>Rule Learning</strong><span>5 min</span></div>
                <div class="workout-step"><strong>Due Review</strong><span>5 min</span></div>
                <div class="workout-step"><strong>Stop or continue</strong><span>your choice</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        btn1, btn2, btn3 = st.columns(3)
        with btn1:
            if st.button("Start Mini Essay", use_container_width=True):
                st.session_state["current_page"] = "Mini Essay Drill"
                st.rerun()
        with btn2:
            if st.button("Start Rule Learning", use_container_width=True):
                st.session_state["current_page"] = "Rule Flashcards"
                st.rerun()
        with btn3:
            if st.button("Due Review Queue", use_container_width=True):
                st.session_state["current_page"] = "Due Review Queue"
                st.rerun()

    with mid_col:
        st.markdown(
            """
            <div class="compact-card">
                <h3>Tiny Win</h3>
                <div class="tiny-win">Do one Level 1 or Mini Essay question. Save it. That counts.</div>
                <p><strong>Minimum Session:</strong></p>
                <ul>
                    <li>8 min Mini Essay</li>
                    <li>2 min compare</li>
                    <li>1 fix note</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right_col:
        st.markdown(
            """
            <div class="compact-card">
                <h3>ADHD Guardrails</h3>
                <div class="warning-mini">No passive reading before retrieval.</div>
                <div class="warning-mini">Do not perfect the app before studying.</div>
                <div class="warning-mini">Stop after one rep if energy is low.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if not rule_bank_cards:
        st.warning("Import the flashcards file by running:")
        st.code("python import_flashcards2025.py Flashcards2025.rtf")

    bottom_left, bottom_right = st.columns([1.5, 1], gap="medium")

    with bottom_left:
        st.markdown('<div class="compact-card"><h3>Weakest Subjects</h3>', unsafe_allow_html=True)
        if stats["subject_stats"]:
            subject_df = pd.DataFrame(
                stats["subject_stats"],
                columns=["Subject", "Average Score", "Attempts"]
            ).head(5)
            st.dataframe(subject_df, use_container_width=True, hide_index=True, height=205)
        else:
            st.info("No attempts yet. Complete one short practice attempt to activate this view.")
        st.markdown("</div>", unsafe_allow_html=True)

    with bottom_right:
        due_reviews = stats["due_reviews"]
        next_action = (
            f"You have {due_reviews} due reviews. Do one before new work."
            if due_reviews > 0
            else "No reviews due. Do one Mini Essay Drill."
        )
        st.markdown(
            (
                '<div class="compact-card">'
                '<h3>Next Action</h3>'
                f'<p>{escape(next_action)}</p>'
                f'<p><strong>Today:</strong> {escape(str(stats["today_attempts"]))} attempts, '
                f'{escape(str(stats["today_minutes"]))} min</p>'
                f'<p><strong>Rule bank:</strong> {len(rule_bank_cards)} cards, '
                f'{len(rule_bank_subjects)} subjects</p>'
                f'<p><strong>Unpracticed:</strong> {escape(str(stats["unpracticed_questions"]))}</p>'
                '</div>'
            ),
            unsafe_allow_html=True,
        )

    with st.expander("Smart Practice Queue", expanded=False):
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

            st.dataframe(queue_df.head(10), use_container_width=True, hide_index=True, height=260)
        else:
            st.info("No active questions found yet. Import or add a few questions to build the queue.")

    with st.expander("Full 35-minute session plan", expanded=False):
        st.markdown("""
        1. **5 min** - Issue spotting
        2. **7 min** - Rule flash
        3. **15 min** - IRAC paragraph
        4. **5 min** - Self-grade
        5. **3 min** - Make one weak-rule note

        **Rule:** attempt retrieval before reviewing the answer.

        Where is the sample answer? Open any drill, attempt first, then click
        **Compare With Sample Answer**.
        """)

    with st.expander("Due and Untouched by Subject", expanded=False):
        if stats["due_by_subject"]:
            due_df = pd.DataFrame(stats["due_by_subject"], columns=["Subject", "Due"])
            st.dataframe(due_df.head(10), use_container_width=True, hide_index=True, height=260)
        elif stats["untouched_by_subject"]:
            untouched_df = pd.DataFrame(
                stats["untouched_by_subject"],
                columns=["Subject", "Untouched Active"]
            )
            st.dataframe(untouched_df.head(10), use_container_width=True, hide_index=True, height=260)
        else:
            st.success("No due reviews and no untouched active questions.")

    st.markdown('</div>', unsafe_allow_html=True)


elif menu == "Bulk Import MEE Bank":
    render_page_title(
        "Bulk Import MEE Bank",
        "Import or review MEE question-bank material.",
    )

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
    st.caption("Tip: Press Enter twice between paragraphs for clean spacing when displayed.")

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
    render_page_title(
        "Add MEE Question",
        "Manually add one question with its call, rule bank, and answer notes.",
    )

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
        st.caption("Tip: Press Enter twice between paragraphs for clean spacing when displayed.")
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
    render_page_title(
        "MEE Muscle Ladder",
        "Train gradually: issue -> rule -> trigger facts -> IRAC -> full essay.",
    )

    st.info(
        "Use this page only for the ladder progression. For hints, attack-outline rules, "
        "templates, and deeper review tools, use the dedicated tabs."
    )

    question_id = question_picker(active_default=True, compact=True)

    if question_id:
        q = get_question_by_id(question_id)

        if q is None:
            st.error("Question not found.")
        else:
            qd = unpack_question(q)

            st.caption(
                f"{qd['exam_name']} Q{qd['question_number']} | {qd['subject']} | "
                f"Priority {qd['priority'] or '-'}"
            )

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
                goal_text = "Spot issues and write rules from memory."
            elif level.startswith("Level 2"):
                target_minutes = 10
                goal_text = "Connect each issue/rule to trigger facts."
            elif level.startswith("Level 3"):
                target_minutes = 15
                goal_text = "Write one strong IRAC paragraph."
            elif level.startswith("Level 4"):
                target_minutes = 20
                goal_text = "Outline the entire essay."
            else:
                target_minutes = 30
                goal_text = "Full timed MEE simulation."

            st.markdown(
                f'<div class="mini-drill-note">{target_minutes}-minute target: {goal_text}</div>',
                unsafe_allow_html=True,
            )

            prompt_col, work_col = st.columns([1, 1.15], gap="large")

            with prompt_col:
                with st.expander("Call of the Question", expanded=True):
                    render_call_text("Call of the Question", qd["call_of_question"])

                with st.expander("Fact Pattern", expanded=True):
                    fact_only = (
                        extract_fact_pattern_only(qd["question_text"], qd["call_of_question"])
                        if "extract_fact_pattern_only" in globals()
                        else qd["question_text"]
                    )
                    render_fact_pattern_text("Fact Pattern", fact_only)

            with work_col:
                st.markdown(f"### {level.split(' - ')[0]} Work")

                if level.startswith("Level 1"):
                    user_issues = st.text_area(
                        "Step A - What issues do you see?",
                        placeholder="List each legal issue raised by this call.",
                        height=120
                    )
                    user_rules = st.text_area(
                        "Step B - Write the rules from memory",
                        placeholder="Write the governing test, elements, or standard.",
                        height=140
                    )
                    user_facts = st.text_area(
                        "Optional - Which facts triggered those issues?",
                        placeholder="Quote or summarize the facts that connect to each rule element.",
                        height=90
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
                    combined_answer = st.text_area(
                        "For each issue, write: Issue -> Rule -> Trigger Facts",
                        placeholder=(
                            "Issue 1: ___\nRule: ___\nTrigger facts: ___\n\n"
                            "Issue 2: ___\nRule: ___\nTrigger facts: ___"
                        ),
                        height=280
                    )

                elif level.startswith("Level 3"):
                    combined_answer = st.text_area(
                        "Write ONE strong IRAC paragraph",
                        placeholder=(
                            "Issue: Whether ___\nRule: Under ___\nApplication: Here, ___ because ___\n"
                            "Counterargument: However, ___\nConclusion: Therefore, ___"
                        ),
                        height=280
                    )

                elif level.startswith("Level 4"):
                    combined_answer = st.text_area(
                        "Outline the full essay. Short bullets only.",
                        placeholder=(
                            "Call 1:\n- Issue:\n- Rule:\n- Facts:\n- Conclusion:\n\n"
                            "Call 2:\n- Issue:\n- Rule:\n- Facts:\n- Conclusion:"
                        ),
                        height=300
                    )

                else:
                    combined_answer = st.text_area("Write the full timed essay", height=360)

            st.divider()

            score_col, check_col = st.columns([1, 1], gap="large")

            with score_col:
                st.markdown("### Score and Save")
                issue_score = st.slider("Issue score", 0, 5, 0)
                rule_score = st.slider("Rule score", 0, 5, 0)
                fact_score = st.slider("Fact connection score", 0, 5, 0)

                average_score = round((issue_score + rule_score + fact_score) / 3)
                st.metric("Training score", f"{average_score}/5")

                missed = st.text_area(
                    "What did you miss?",
                    placeholder="Missed issue, element, or trigger fact.",
                    height=90
                )

                notes = st.text_area(
                    "Fix note for future you",
                    placeholder="One useful instruction for next time.",
                    height=90
                )

                if st.button("Save Muscle Ladder Attempt", use_container_width=True):
                    save_attempt(
                        qd["id"],
                        level,
                        combined_answer,
                        average_score,
                        missed,
                        notes,
                        minutes_spent=target_minutes
                    )

                    st.success("Saved. This question is now scheduled for review based on your score.")

            with check_col:
                st.markdown("### Quick Answer Check")
                reveal_gate_box("Reveal only after writing your answer.")

                if st.button("Reveal Compact Answer Check", use_container_width=True):
                    st.session_state[f"ladder_reveal_{qd['id']}"] = True

                if st.session_state.get(f"ladder_reveal_{qd['id']}", False):
                    render_tested_issues_text("Tested Issues", qd["tested_issues"])
                    render_readable_text("Rules", qd["rules"], READING_FONT_SIZE)
                    render_trigger_facts("Trigger Facts", qd)
                    render_trap_warnings("Trap Warnings", qd["traps"])
                    render_sample_answer_section(qd, expanded=False)


elif menu == "Mini Essay Drill":
    render_page_title(
        "Mini Essay Drill",
        "Previous exam question -> issue -> rule -> trigger facts. No full essay.",
    )
    st.markdown(
        '<div class="mini-drill-note">8-minute drill: recognition, rule recall, fact connection.</div>',
        unsafe_allow_html=True,
    )

    question_id = question_picker(active_default=True, compact=True)

    if question_id:
        q = get_question_by_id(question_id)

        if q is None:
            st.error("Question not found.")
        else:
            qd = unpack_question(q)
            subquestions = flatten_subquestions_for_answer_mapping(qd)
            reveal_key = f"mini_reveal_{qd['id']}"

            render_meta_strip(qd)

            main_col, side_col = st.columns([2.25, 1], gap="large")

            with side_col:
                st.markdown("### Study Tools")
                render_stopwatch(f"mini_{qd['id']}")

                with st.container(border=True):
                    st.markdown("#### Question Snapshot")
                    st.write(f"Subject: {qd['subject']}")
                    st.write(f"Status: {qd['july_2026_status'] or '-'}")
                    st.write(f"Priority: {qd['priority'] or '-'}")
                    st.write(f"Source: {qd['source'] or '-'}")

                try:
                    hints_used = render_progressive_hints(qd)
                except NameError:
                    hints_used = 0

                render_trigger_candidate_diagnostics(qd)

                with st.expander("Exact Attack Outline Rule", expanded=False):
                    outline_matches = find_best_outline_rules_for_question(
                        qd.get("subject", ""),
                        qd.get("tested_issues", ""),
                        qd.get("rules", ""),
                        qd.get("traps", ""),
                        limit=3,
                    )

                    if outline_matches:
                        for rule in outline_matches:
                            render_attack_rule_box(rule)
                    else:
                        st.info("No exact outline rule found yet.")

                    search_term = st.text_input(
                        "Search Attack Outline rules",
                        placeholder="personal jurisdiction, hearsay, statute of frauds",
                        key=f"mini_outline_search_{qd['id']}",
                    )

                    if search_term:
                        results = search_outline_rules(search_term, subject=qd["subject"], limit=5)

                        if results:
                            for rule in results:
                                render_attack_rule_box(rule)
                        else:
                            st.info("No Attack Outline rules matched that search.")

                with st.expander("Plug & Play Template", expanded=False):
                    plug_matches = find_best_plug_play_for_call(
                        qd.get("subject", ""),
                        qd.get("call_of_question", ""),
                        qd.get("question_text", ""),
                        qd.get("tested_issues", ""),
                        limit=3,
                    )

                    if plug_matches:
                        for template in plug_matches:
                            render_plug_play_template(template)
                    else:
                        st.info("No Plug & Play template matched yet.")

                reveal_gate_box("Reveal only after writing your answer.")

                if st.button("Reveal Issues + Rules"):
                    st.session_state[reveal_key] = True

                if st.session_state.get(reveal_key, False):
                    render_tested_issues_text("Tested Issues", qd["tested_issues"])
                    render_raw_tested_issues_expander(qd)
                    render_readable_text("Rules", qd["rules"], READING_FONT_SIZE)
                    render_trigger_facts("Trigger Facts", qd)
                    render_raw_trigger_facts_expander(qd)
                    render_trap_warnings("Trap Warnings", qd["traps"])
                    with st.expander("Raw trap text", expanded=False):
                        st.text(qd.get("traps", "") or "")
                    model_points = (qd.get("model_points", "") or "").strip()
                    if model_points and model_answer_quality(qd) != "damaged":
                        with st.expander("Full Model Answer / Analysis", expanded=False):
                            render_sample_answer_text("Full Model Answer / Analysis", model_points)
                    elif qd.get("rules") or qd.get("tested_issues") or qd.get("trigger_facts"):
                        with st.expander("Full Model Answer / Analysis", expanded=False):
                            render_structured_model_analysis(qd, title="Structured Model Analysis")
                    else:
                        st.info("No full model answer/model analysis available for this question yet.")

            with main_col:
                with st.expander("1. Call of the Question - read this first", expanded=True):
                    render_call_text("Call of the Question", qd["call_of_question"])

                st.markdown("### Mini Fact Packet")
                render_fact_pattern_text("Mini Fact Packet", make_mini_fact_packet(qd["question_text"]), max_chars=None)

                if st.session_state.get(reveal_key, False):
                    render_universal_highlighted_fact_pattern(
                        "Mini Fact Packet with Trigger Facts Highlighted",
                        qd,
                        text=make_mini_fact_packet(qd["question_text"]),
                    )

                with st.expander("Open full fact pattern if needed", expanded=False):
                    fact_only = (
                        extract_fact_pattern_only(qd["question_text"], qd["call_of_question"])
                        if "extract_fact_pattern_only" in globals()
                        else qd["question_text"]
                    )
                    render_fact_pattern_text("Full Fact Pattern", fact_only)

                st.markdown("### Breakout Calls")
                st.caption("Answer the active call, reveal/check it, score it, mark it done, then move on.")

                if not subquestions:
                    subquestions = [
                        {
                            "label": "Question 1",
                            "text": qd.get("call_of_question", ""),
                            "subparts": [],
                        }
                    ]

                init_mini_drill_state(qd, len(subquestions))
                render_mini_drill_progress(qd, subquestions)

                reset_col, spacer_col = st.columns([1, 3])
                with reset_col:
                    if st.button("Reset Mini Drill Progress for This Question", use_container_width=True):
                        reset_mini_drill_progress(qd)
                        st.rerun()

                active_key = mini_drill_state_key(qd, "active_index")
                done_key = mini_drill_state_key(qd, "done_questions")
                active_idx = st.session_state[active_key]
                done_questions = st.session_state[done_key]

                for idx, subq in enumerate(subquestions):
                    label = subq.get("label", f"Question {idx + 1}")
                    is_active = idx == active_idx
                    is_done = idx in done_questions
                    status = "DONE" if is_done else "ACTIVE" if is_active else "NEXT"

                    with st.expander(f"{label} - {status}", expanded=is_active):
                        if not is_active and not is_done:
                            st.info("Complete the earlier question first, then come back here.")
                            continue

                        render_single_mini_question_workflow(qd, subq, idx + 1, hints_used)

                done_questions = st.session_state.get(done_key, set())

                if len(done_questions) == len(subquestions):
                    st.divider()
                    st.success("All subquestions completed. Ready to save the full Mini Essay attempt.")

                    all_answers = []
                    all_scores = []
                    all_missed = []
                    all_notes = []

                    for i, subq in enumerate(subquestions, start=1):
                        all_answers.append(st.session_state.get(f"mini_answer_piece_{qd['id']}_{i}", ""))
                        all_scores.append(st.session_state.get(f"mini_score_piece_{qd['id']}_{i}", 0))
                        all_missed.append(st.session_state.get(f"mini_missed_piece_{qd['id']}_{i}", ""))
                        all_notes.append(st.session_state.get(f"mini_fix_piece_{qd['id']}_{i}", ""))

                    final_score = round(sum(all_scores) / len(all_scores)) if all_scores else 0
                    combined_answer = "\n\n====================\n\n".join([a for a in all_answers if a])
                    combined_missed = "\n".join([m for m in all_missed if m])
                    combined_notes = "\n".join([n for n in all_notes if n])
                    notes_with_hints = f"Hints used: {hints_used}/5\n\n{combined_notes}"

                    st.metric("Final Mini Drill Score", f"{final_score}/5")

                    if st.button("Save Full Mini Essay Attempt"):
                        save_attempt(
                            qd["id"],
                            "Mini Essay Drill - Stepwise",
                            combined_answer,
                            final_score,
                            combined_missed,
                            notes_with_hints,
                            minutes_spent=8 * len(subquestions),
                        )

                        st.success("Full Mini Essay attempt saved.")

                st.info(
                    "Mini Essay Rule: if you can spot the issue and write the rule from memory, "
                    "the full essay becomes much easier."
                )


elif menu == "Issue Spotting Drill":
    render_page_title(
        "Issue Spotting Drill",
        "Spot tested issues first, then compare against the answer bank.",
    )

    question_id = question_picker()

    if question_id:
        q = get_question_by_id(question_id)

        if q is None:
            st.error("Question not found.")
        else:
            qd = unpack_question(q)

            render_meta_strip(qd)

            study_tip("Timer target: 5 minutes. Read the call first, then identify the legal triggers.")

            issue_main_col, issue_side_col = st.columns([2.1, 1], gap="large")

            with issue_side_col:
                st.markdown("### Study Tools")
                render_stopwatch(f"issue_{qd['id']}")

                with st.container(border=True):
                    st.markdown('<div class="review-controls-title">Review Controls</div>', unsafe_allow_html=True)
                    show_highlights_early = st.checkbox(
                        "Review mode: show trigger fact highlights immediately",
                        value=False,
                    )
                    show_explanations = st.checkbox(
                        "Show explanation bubbles on highlighted facts",
                        value=True,
                    )

                render_trigger_candidate_diagnostics(qd)

                hints_used = render_progressive_hints(qd)

                reveal_gate_box("Reveal only after writing your answer.")

                if st.button("Reveal Tested Issues"):
                    render_tested_issues_text("Tested Issues", qd["tested_issues"])
                    render_raw_tested_issues_expander(qd)
                    render_trigger_facts("Trigger Facts", qd)
                    render_raw_trigger_facts_expander(qd)
                    render_trap_warnings("Trap Warnings", qd["traps"])
                    with st.expander("Raw trap text", expanded=False):
                        st.text(qd.get("traps", "") or "")
                    render_question_highlights_with_fallback(
                        "Fact Pattern with Trigger Facts Highlighted by Question",
                        qd,
                        show_explanations=show_explanations,
                    )
                    render_trigger_candidate_diagnostics(qd)
                    flashcard_matches = find_relevant_rule_flashcards(
                        qd.get("tested_issues", ""),
                        subject=qd.get("subject", ""),
                        limit=3,
                    )
                    if flashcard_matches:
                        st.markdown("### Relevant Flashcard Rules")
                        for card in flashcard_matches:
                            render_rule_flashcard_box(card)
                    else:
                        st.info("No relevant flashcard rules matched this issue yet.")
                    render_sample_answer_section(qd, expanded=False)

            with issue_main_col:
                with st.expander("Call of the Question", expanded=True):
                    render_call_text("Call of the Question", qd["call_of_question"])

                with st.expander("Fact Pattern", expanded=True):
                    fact_only = (
                        extract_fact_pattern_only(qd["question_text"], qd["call_of_question"])
                        if "extract_fact_pattern_only" in globals()
                        else qd["question_text"]
                    )
                    if show_highlights_early:
                        render_question_highlights_with_fallback(
                            "Fact Pattern with Trigger Facts Highlighted by Question",
                            qd,
                            text=fact_only,
                            show_explanations=show_explanations,
                        )
                    else:
                        render_fact_pattern_text("Fact Pattern", fact_only)

                user_issues = st.text_area(
                    "Your issue list",
                    placeholder="List each issue in short phrases.",
                    height=180
                )

            confidence = st.slider("Confidence", 1, 5, 3)

            col1, col2 = st.columns(2)

            with col1:
                self_score = st.slider("Self-score: issue spotting", 0, 5, 0)

            with col2:
                _sw_min = min(60, max(0, stopwatch_minutes(f"issue_{qd['id']}")))
                minutes_spent = st.number_input("Minutes spent", min_value=0, max_value=60, value=_sw_min or 5)

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


elif menu == "Rule Flashcards":
    render_page_title(
        "Rule Flashcards",
        "Printable rule cards for active recall. Inspired by your MBE miss-card format.",
    )

    imported_flashcards_all = get_rule_flashcards() if "get_rule_flashcards" in globals() else []
    outline_rules_all = get_outline_rules() if "get_outline_rules" in globals() else []
    templates_all = get_plug_play_templates() if "get_plug_play_templates" in globals() else []

    subjects = sorted({
        str(row[1]).strip()
        for row in imported_flashcards_all
        if len(row) > 1 and str(row[1]).strip()
    } | {
        str(row[1]).strip()
        for row in outline_rules_all
        if len(row) > 1 and str(row[1]).strip()
    } | {
        str(row[1]).strip()
        for row in templates_all
        if len(row) > 1 and str(row[1]).strip()
    })

    if not subjects:
        st.warning("No flashcards found. Import flashcards, Attack Outline rules, or Plug & Play templates first.")
        st.code("python import_flashcards2025.py Flashcards2025.rtf")
        st.code('python import_attack_outline.py "bar attack.pdf"')
        st.code('python import_plug_play_templates.py "LBP Plug and Play-Essay Templates to Help You Write Faster Score Higher.pdf"')
        st.stop()

    controls_col1, controls_col2, controls_col3 = st.columns([1.2, 1.1, 1], gap="large")

    with controls_col1:
        selected_subject = st.selectbox("Subject filter", ["All"] + subjects, key="flashcards_subject")

    with controls_col2:
        source_filter = st.radio(
            "Source",
            ["Flashcards", "Attack Outline", "Plug & Play", "All"],
            horizontal=True,
            key="flashcards_source",
        )

    with controls_col3:
        card_count = st.slider("Number of cards", 4, 40, 12, key="flashcards_count")

    search_term = st.text_input(
        "Search rule topic",
        placeholder="battery, personal jurisdiction, hearsay, agency, statute of frauds",
        key="flashcards_search",
    )

    if st.button("Print this page"):
        st.info("Use your browser print shortcut: Ctrl+P / Cmd+P. Print CSS is enabled.")

    imported_results = []
    outline_results = []
    template_results = []
    subject_arg = None if selected_subject == "All" else selected_subject

    if source_filter in ["Flashcards", "All"]:
        if search_term:
            imported_results = search_rule_flashcards(search_term, subject=subject_arg, limit=card_count)
        else:
            imported_results = get_rule_flashcards(subject=subject_arg)[:card_count]

    if source_filter in ["Attack Outline", "All"]:
        if search_term:
            outline_results = search_outline_rules(search_term, subject=subject_arg, limit=card_count)
        else:
            outline_results = get_outline_rules(subject=subject_arg)[:card_count]

    if source_filter in ["Plug & Play", "All"]:
        if search_term:
            template_results = search_plug_play_templates(search_term, subject=subject_arg, limit=card_count)
        else:
            template_results = get_plug_play_templates(subject=subject_arg)[:card_count]

    cards = []
    card_index = 1

    for card in imported_results:
        cards.append(make_rule_card_from_flashcard(card, card_index))
        card_index += 1

    for rule in outline_results:
        cards.append(make_rule_card_from_outline(rule, card_index))
        card_index += 1

    for template in template_results:
        cards.append(make_rule_card_from_template(template, card_index))
        card_index += 1

    cards = cards[:card_count]

    if not cards:
        st.warning("No flashcards found. Import flashcards, Attack Outline rules, or Plug & Play templates first, or broaden your search.")
    else:
        export_html = build_flashcards_html_document(cards)

        if st.button("Export Flashcards HTML"):
            st.session_state["show_flashcards_download"] = True

        if st.session_state.get("show_flashcards_download", False):
            st.download_button(
                "Download Flashcards HTML",
                data=export_html,
                file_name="mee_rule_flashcards.html",
                mime="text/html",
            )

        render_flashcard_grid(cards)


elif menu in ["Rule Learning Portal", "Rule Flash Drill", "Rule Retrieval Drill"]:
    render_page_title(
        "Rule Learning Portal",
        "Learn black-letter rules by subject. No MEE question required.",
    )
    st.info(
        "Use this when the rule itself is fuzzy. Pick a subject and rule, write it from memory, "
        "reveal the exact rule, then rewrite your clean version."
    )

    imported_flashcards = get_rule_flashcards() if "get_rule_flashcards" in globals() else []
    outline_rules = get_outline_rules() if "get_outline_rules" in globals() else []
    plug_templates = get_plug_play_templates() if "get_plug_play_templates" in globals() else []

    subjects = sorted({
        str(row[1]).strip()
        for row in imported_flashcards
        if len(row) > 1 and str(row[1]).strip()
    } | {
        str(row[1]).strip()
        for row in outline_rules
        if len(row) > 1 and str(row[1]).strip()
    } | {
        str(row[1]).strip()
        for row in plug_templates
        if len(row) > 1 and str(row[1]).strip()
    })

    if not subjects:
        st.warning("No rules imported yet. Import flashcards, Attack Outline rules, or Plug & Play templates first.")
        st.code("python import_flashcards2025.py Flashcards2025.rtf")
        st.code('python import_attack_outline.py "bar attack.pdf"')
        st.code('python import_plug_play_templates.py "LBP Plug and Play-Essay Templates to Help You Write Faster Score Higher.pdf"')
        st.stop()

    top_col1, top_col2 = st.columns([1, 1], gap="large")

    with top_col1:
        selected_subject = st.selectbox("Choose subject", subjects)

    with top_col2:
        source_choice = st.radio(
            "Rule source",
            ["Flashcards", "Attack Outline Rules", "Plug & Play Templates", "All"],
            horizontal=True,
        )

    search_term = st.text_input(
        "Search rule topic",
        placeholder="battery, personal jurisdiction, hearsay, actual authority, statute of frauds",
    )

    if search_term:
        subject_flashcards = (
            search_rule_flashcards(search_term, subject=selected_subject, limit=50)
            if source_choice in ["Flashcards", "All"]
            else []
        )
        subject_outline_rules = (
            search_outline_rules(search_term, subject=selected_subject, limit=50)
            if source_choice in ["Attack Outline Rules", "All"]
            else []
        )
        subject_templates = (
            search_plug_play_templates(search_term, subject=selected_subject, limit=50)
            if source_choice in ["Plug & Play Templates", "All"]
            else []
        )
    else:
        subject_flashcards = (
            get_rule_flashcards(subject=selected_subject)[:50]
            if source_choice in ["Flashcards", "All"]
            else []
        )
        subject_outline_rules = (
            get_outline_rules(subject=selected_subject)[:50]
            if source_choice in ["Attack Outline Rules", "All"]
            else []
        )
        subject_templates = (
            get_plug_play_templates(subject=selected_subject)[:50]
            if source_choice in ["Plug & Play Templates", "All"]
            else []
        )

    rule_options = []

    for row in subject_flashcards:
        card_id, subject, rule_title, rule_text, source_file, tags = row
        label = f"{rule_title} - Flashcards"
        rule_options.append((label, "Flashcards", row))

    for row in subject_outline_rules:
        rule_id, subject, rule_title, appearance_rate, rule_text, pdf_page, printed_page, source_file = row
        appearance = appearance_rate or "Rule"
        label = f"{rule_title} - {appearance} - Attack Outline"
        rule_options.append((label, "Attack Outline", row))

    for row in subject_templates:
        template_id, subject, module_title, scenario_trigger, issue_statement, rule_text, analysis_template, conclusion_template, testing_notes, pdf_page, source_file = row
        label = f"{module_title} - Plug & Play"
        rule_options.append((label, "Plug & Play", row))

    if not rule_options:
        st.info("No matching rules found for this subject/search. Try a broader search term.")
        st.stop()

    labels = [item[0] for item in rule_options]
    selected_rule_label = st.selectbox("Choose rule/topic to drill", labels)
    selected_index = labels.index(selected_rule_label)
    selected_label, selected_source_type, selected_item = rule_options[selected_index]

    if selected_source_type == "Flashcards":
        selected_rule_title = selected_item[2]
        prompt = f"What is the rule for {selected_rule_title}?"
    elif selected_source_type == "Attack Outline":
        selected_rule_title = selected_item[2]
        prompt = f"What is the rule for: {selected_rule_title}?"
    else:
        selected_rule_title = selected_item[2]
        prompt = f"What is the rule and issue framework for: {selected_rule_title}?"

    prompt_slug = re.sub(r"[^A-Za-z0-9]+", "_", selected_rule_label[:80]).strip("_")
    reveal_key = f"rule_learning_reveal_{prompt_slug}"

    main_col, side_col = st.columns([2.1, 1], gap="large")

    with main_col:
        st.markdown("### Rule Prompt")
        st.info(prompt)

        memory_rule = st.text_area(
            "Write the rule from memory",
            placeholder="State the legal test, required elements, standard, and any major exception.",
            height=180,
            key=f"rule_learning_memory_{prompt_slug}",
        )
        st.caption("Do this closed-book first. The goal is active recall, not recognition.")

        confidence = st.slider(
            "Confidence before reveal",
            1,
            5,
            3,
            key=f"rule_learning_confidence_{prompt_slug}",
        )

        if st.button("Reveal Exact Rule", key=f"rule_learning_reveal_btn_{prompt_slug}"):
            st.session_state[reveal_key] = True

        if st.session_state.get(reveal_key, False):
            st.markdown("### Exact Rule")

            if selected_source_type == "Flashcards":
                render_rule_flashcard_box(selected_item)
                related_rules = search_outline_rules(selected_rule_title, subject=selected_subject, limit=2)
                related_templates = search_plug_play_templates(selected_rule_title, subject=selected_subject, limit=2)
                if source_choice == "All" and (related_rules or related_templates):
                    with st.expander("Related Rule Support", expanded=False):
                        for rule in related_rules:
                            render_attack_rule_box(rule)
                        for template in related_templates:
                            render_plug_play_template(template)
            elif selected_source_type == "Attack Outline":
                render_attack_rule_box(selected_item)
                related_templates = search_plug_play_templates(selected_rule_title, subject=selected_subject, limit=2)
                if source_choice == "All" and related_templates:
                    with st.expander("Related Plug & Play Templates", expanded=False):
                        for template in related_templates:
                            render_plug_play_template(template)
            else:
                render_plug_play_template(selected_item)
                related_rules = search_outline_rules(selected_rule_title, subject=selected_subject, limit=3)
                if source_choice == "All" and related_rules:
                    with st.expander("Related Attack Outline Rules", expanded=False):
                        for rule in related_rules:
                            render_attack_rule_box(rule)

            with st.expander("Rule comparison checklist", expanded=True):
                st.markdown("""
                Check your answer:
                - Did I name the correct doctrine?
                - Did I include all elements?
                - Did I include the correct standard?
                - Did I include exceptions or defenses?
                - Could I write this in 20 seconds on the MEE?
                """)

            final_rule = st.text_area(
                "Rewrite the clean final rule in your own words",
                placeholder="This is the version future-you should memorize. Keep it short, accurate, and exam-ready.",
                height=160,
                key=f"rule_learning_final_{prompt_slug}",
            )

            score_col1, score_col2, score_col3 = st.columns(3)

            with score_col1:
                element_score = st.slider("Element accuracy", 0, 5, 0, key=f"rule_learning_element_{prompt_slug}")

            with score_col2:
                completeness_score = st.slider("Completeness", 0, 5, 0, key=f"rule_learning_complete_{prompt_slug}")

            with score_col3:
                fluency_score = st.slider("Speed / fluency", 0, 5, 0, key=f"rule_learning_fluency_{prompt_slug}")

            average_score = round((element_score + completeness_score + fluency_score) / 3)
            st.metric("Rule score", f"{average_score}/5")

            missed_elements = st.text_area(
                "What did you miss?",
                placeholder="Example: I forgot that offensive contact counts for battery even without physical injury.",
                height=100,
                key=f"rule_learning_missed_{prompt_slug}",
            )

            mnemonic = st.text_area(
                "Memory note / mnemonic",
                placeholder="Example: Battery = intent + harmful/offensive contact.",
                height=100,
                key=f"rule_learning_notes_{prompt_slug}",
            )

            if st.button("Save Rule Attempt", key=f"rule_learning_save_{prompt_slug}"):
                save_rule_attempt(
                    subject=selected_subject,
                    rule_title=selected_rule_title,
                    source_type=selected_source_type,
                    prompt=prompt,
                    memory_rule=memory_rule,
                    final_rule=final_rule,
                    score=average_score,
                    missed_elements=missed_elements,
                    notes=f"Confidence before reveal: {confidence}/5\n\n{mnemonic}",
                )

                st.success("Rule attempt saved. Weak rules become review material.")

    with side_col:
        with st.expander("Browse rules in this subject", expanded=False):
            browser_rows = []
            for row in get_rule_flashcards(subject=selected_subject)[:50]:
                browser_rows.append({
                    "rule title": row[2],
                    "appearance": "",
                    "source": "Flashcards" if (row[4] or "").lower() == "flashcards2025.rtf" else (row[4] or "Flashcards"),
                })
            for row in get_outline_rules(subject=selected_subject)[:50]:
                browser_rows.append({
                    "rule title": row[2],
                    "appearance": row[3] or "",
                    "source": "Attack Outline",
                })
            for row in get_plug_play_templates(subject=selected_subject)[:50]:
                browser_rows.append({
                    "rule title": row[2],
                    "appearance": "",
                    "source": "Plug & Play",
                })

            if browser_rows:
                st.dataframe(pd.DataFrame(browser_rows), use_container_width=True, hide_index=True)
            else:
                st.info("No rules found for this subject.")

        with st.expander("Review recent rule attempts", expanded=False):
            recent_attempts = get_rule_attempts(limit=20) if "get_rule_attempts" in globals() else []

            if not recent_attempts:
                st.info("No rule attempts saved yet.")
            else:
                for attempt in recent_attempts:
                    (
                        attempt_id,
                        subject,
                        rule_title,
                        source_type,
                        attempt_prompt,
                        attempt_memory_rule,
                        attempt_final_rule,
                        score,
                        missed_elements,
                        notes,
                        created_at,
                    ) = attempt

                    st.markdown(f"**{created_at} - {subject} - {rule_title} - {score}/5**")
                    st.caption(source_type)
                    st.markdown("**Prompt**")
                    st.write(attempt_prompt)
                    st.markdown("**Missed elements**")
                    st.write(missed_elements or "No missed elements saved.")
                    st.markdown("**Final clean rule**")
                    st.write(attempt_final_rule or "No final rule saved.")
                    st.divider()


elif menu == "Timed IRAC Drill":
    render_page_title(
        "Timed IRAC Drill",
        "Write under time, then compare rule accuracy and fact use.",
    )

    question_id = question_picker()

    if question_id:
        q = get_question_by_id(question_id)

        if q is None:
            st.error("Question not found.")
        else:
            qd = unpack_question(q)

            render_data_health_warning(qd)

            # Persist hints_used across renders via session state
            _hints_key = f"timed_irac_hints_{question_id}"
            hints_used = st.session_state.get(_hints_key, 0)

            # â”€â”€ Two-column split layout â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            left_col, right_col = st.columns([1, 1])

            with left_col:
                st.markdown(
                    '<p style="font-size:0.88rem;font-weight:700;color:#4A6585;margin-bottom:0.35rem">Question Prompt</p>',
                    unsafe_allow_html=True,
                )

                _prompt_text = extract_fact_pattern_only(qd["question_text"], qd["call_of_question"])

                if _prompt_text:
                    _paras = split_fact_pattern_paragraphs(_prompt_text)
                    _inner = "".join(
                        f'<p style="margin-bottom:1.2em">{escape_display_text(p)}</p>'
                        for p in _paras
                    )
                else:
                    _inner = '<p style="color:#58708A;font-style:italic">No prompt stored â€” retrieve from your materials.</p>'

                st.markdown(
                    f'<div style="height:520px;overflow-y:auto;background:#f8f9fa;padding:1rem;'
                    f'border-left:4px solid #c9a84c;line-height:1.6;font-size:1rem;border-radius:4px">'
                    f'{_inner}</div>',
                    unsafe_allow_html=True,
                )

                # Issue tags as colored pills
                _issues_raw = qd.get("tested_issues", "") or ""
                if _issues_raw:
                    _tags = extract_issue_bullets(_issues_raw)
                    if not _tags:
                        _tags = [t.strip() for t in re.split(r"[;\n]", clean_tested_issues_text(_issues_raw)) if t.strip()]
                    if _tags:
                        _pills = "".join(
                            f'<span style="display:inline-block;background:#dbeafe;color:#1e40af;'
                            f'border-radius:999px;padding:3px 10px;margin:2px 3px 2px 0;'
                            f'font-size:0.8rem;font-weight:600">{escape_display_text(t)}</span>'
                            for t in _tags[:15]
                        )
                        st.markdown(f'<div style="margin-top:0.7rem">{_pills}</div>', unsafe_allow_html=True)

            with right_col:
                # Live stopwatch
                render_stopwatch(f"irac_{qd['id']}")

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
                    _sw_min = min(90, max(0, stopwatch_minutes(f"irac_{qd['id']}")))
                    minutes_spent = st.number_input(
                        "Minutes spent", min_value=0, max_value=90, value=_sw_min or _target_min
                    )
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

            # â”€â”€ Below the split: call, hints, reveal â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            with st.expander("Call of the Question", expanded=True):
                render_call_text("Call of the Question", qd["call_of_question"])

            _new_hints = render_progressive_hints(qd)
            st.session_state[_hints_key] = _new_hints

            reveal_gate_box("Reveal only after writing your answer.")

            if st.button("Reveal Model Points"):
                render_tested_issues_text("Tested Issues", qd["tested_issues"])
                render_raw_tested_issues_expander(qd)
                render_readable_text("Rules", qd["rules"], READING_FONT_SIZE)
                render_trigger_facts("Trigger Facts", qd)
                render_raw_trigger_facts_expander(qd)
                render_trap_warnings("Trap Warnings", qd["traps"])
                with st.expander("Raw trap text", expanded=False):
                    st.text(qd.get("traps", "") or "")
                render_sample_answer_section(qd, expanded=False)
                with st.expander("Fact Pattern with Trigger Facts Highlighted", expanded=False):
                    render_universal_highlighted_fact_pattern("Fact Pattern with Trigger Facts Highlighted", qd)
                render_trigger_candidate_diagnostics(qd)


elif menu == "Due Review Queue":
    render_page_title(
        "Due Review Queue",
        "Practice questions scheduled for spaced review.",
    )

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
                render_raw_tested_issues_expander(qd)
                render_readable_text("Rules", qd["rules"], READING_FONT_SIZE)
                render_trigger_facts("Trigger Facts", qd)
                render_raw_trigger_facts_expander(qd)
                render_trap_warnings("Trap Warnings", qd["traps"])
                with st.expander("Raw trap text", expanded=False):
                    st.text(qd.get("traps", "") or "")
                render_sample_answer_section(qd, expanded=False)

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
    render_page_title(
        "Attack Outline Rules",
        "Search your rule outline, and add your own rules any time.",
    )

    all_rules = get_outline_rules()
    existing_subjects = sorted({row[1] for row in all_rules if row[1]})
    outline_subjects = ["All"] + existing_subjects

    if not all_rules:
        st.info(
            "No rules yet. Use \"Add your own rules\" below to type or paste rules from "
            "your own outline. You can also bulk-import from a CSV."
        )

    with st.expander("Add your own rules", expanded=not all_rules):
        add_tab, bulk_tab = st.tabs(["Add one rule", "Bulk add (CSV)"])

        with add_tab:
            with st.form("add_outline_rule_form", clear_on_submit=True):
                rc1, rc2 = st.columns([2, 1])
                with rc1:
                    new_subject = st.text_input(
                        "Subject",
                        placeholder="e.g., Evidence, Contracts, Civil Procedure",
                    )
                with rc2:
                    new_appearance = st.text_input(
                        "Appearance rate (optional)",
                        placeholder="e.g., High",
                    )

                if existing_subjects:
                    st.caption("Existing subjects: " + ", ".join(existing_subjects))

                new_title = st.text_input(
                    "Rule title",
                    placeholder="e.g., Hearsay - definition and exceptions",
                )
                new_rule_text = st.text_area(
                    "Rule text",
                    placeholder="Write or paste the rule statement, elements, and any exceptions.",
                    height=180,
                )
                new_source = st.text_input("Source label", value="My outline")

                submitted_rule = st.form_submit_button("Save rule")

                if submitted_rule:
                    if not new_subject.strip() or not new_title.strip() or not new_rule_text.strip():
                        st.error("Subject, rule title, and rule text are all required.")
                    else:
                        created = add_outline_rule(
                            new_subject.strip(),
                            new_title.strip(),
                            new_appearance.strip(),
                            new_rule_text.strip(),
                            None,
                            "",
                            new_source.strip() or "My outline",
                        )
                        if created:
                            st.success("Rule added.")
                            st.rerun()
                        else:
                            st.warning("A matching rule already exists (same subject, title, and source).")

        with bulk_tab:
            st.caption(
                "Upload a CSV with columns: subject, rule_title, rule_text "
                "(optional: appearance_rate, source)."
            )

            rule_template = pd.DataFrame([
                {
                    "subject": "Evidence",
                    "rule_title": "Hearsay - definition",
                    "rule_text": "Hearsay is an out-of-court statement offered to prove the truth of the matter asserted...",
                    "appearance_rate": "High",
                    "source": "My outline",
                }
            ])
            rule_buffer = StringIO()
            rule_template.to_csv(rule_buffer, index=False)
            st.download_button(
                "Download CSV template",
                data=rule_buffer.getvalue(),
                file_name="outline_rules_template.csv",
                mime="text/csv",
            )

            rules_csv = st.file_uploader("Upload rules CSV", type=["csv"], key="rules_csv")

            if rules_csv is not None:
                rules_df = pd.read_csv(rules_csv).fillna("")
                required = ["subject", "rule_title", "rule_text"]
                missing = [c for c in required if c not in rules_df.columns]

                if missing:
                    st.error(f"Missing required columns: {missing}")
                else:
                    st.dataframe(rules_df.head(20), use_container_width=True)

                    if st.button("Import rules from CSV"):
                        added = 0
                        skipped = 0
                        for _, row in rules_df.iterrows():
                            subject_value = str(row.get("subject", "")).strip()
                            title_value = str(row.get("rule_title", "")).strip()
                            text_value = str(row.get("rule_text", "")).strip()

                            if not subject_value or not title_value or not text_value:
                                skipped += 1
                                continue

                            created = add_outline_rule(
                                subject_value,
                                title_value,
                                str(row.get("appearance_rate", "")).strip(),
                                text_value,
                                None,
                                "",
                                str(row.get("source", "")).strip() or "My outline (CSV)",
                            )
                            if created:
                                added += 1
                            else:
                                skipped += 1

                        st.success(f"Imported {added} rule(s). Skipped {skipped} (duplicate or incomplete).")
                        st.rerun()

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
        _label = f"{rule[2]} - {rule[1]}"
        if rule[3]:
            _label += f" - {rule[3]}"
        with st.expander(_label, expanded=False):
            render_attack_rule_box(rule)


elif menu == "Plug & Play Templates":
    render_page_title(
        "Plug & Play Templates",
        "Search essay templates for issue statements, rule phrasing, and analysis structure.",
    )

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
        with st.expander(f"{template[2]} - {template[1]}", expanded=False):
            render_plug_play_template(template)


elif menu == "Review Attempts":
    render_page_title(
        "Review Attempts",
        "Review saved answers, missed issues, notes, and sample-answer comparisons.",
    )

    attempts = get_attempts()

    if not attempts:
        st.info("No attempts yet.")
    else:
        for row in attempts:
            (
                attempt_id,
                question_id,
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
                if response_text:
                    st.text_area(
                        "Student response",
                        value=response_text,
                        height=220,
                        key=f"attempt_response_{attempt_id}",
                        disabled=True,
                    )
                else:
                    st.info("No student response saved for this attempt.")

                st.markdown("### Missed")
                st.write(missed or "No missed issues saved.")

                st.markdown("### Notes")
                st.write(notes or "No notes saved.")

                q = get_question_by_id(question_id)
                if q is not None:
                    qd = unpack_question(q)
                    render_sample_answer_section(qd, expanded=False)
                else:
                    st.info("Original question not found for this attempt.")


elif menu == "MBE Drills":
    render_page_title(
        "MBE Drills - Trap Trainer",
        (
            "Multiple-choice trap drilling. Drill or lecture mode, import your "
            "AdaptiBar misses, and add your own cards."
        ),
    )

    _mbe_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mbe_trap_trainer.html")
    try:
        with open(_mbe_path, "r", encoding="utf-8") as _f:
            _mbe_html = _f.read()
        components.html(_mbe_html, height=2000, scrolling=True)
    except FileNotFoundError:
        st.error(
            "mbe_trap_trainer.html was not found next to app.py. "
            "Make sure the file is in the project folder."
        )


elif menu == "Manage Users":
    if not st.session_state.get("_is_admin"):
        st.error("Admins only.")
    else:
        render_page_title("Manage Users", "Create or remove people who can sign in.")

        st.markdown("#### Add a user")
        with st.form("add_user_form", clear_on_submit=True):
            ac1, ac2 = st.columns(2)
            with ac1:
                nu_username = st.text_input("Username", placeholder="e.g. alice")
                nu_email = st.text_input("Email", placeholder="alice@example.com")
            with ac2:
                nu_name = st.text_input("Display name", placeholder="Alice Smith")
                nu_password = st.text_input("Temporary password", type="password")
            nu_is_admin = st.checkbox("Make this user an admin", value=False)
            add_submitted = st.form_submit_button("Add user")

            if add_submitted:
                if not nu_username.strip() or not nu_password:
                    st.error("Username and password are required.")
                else:
                    ok, msg = add_app_user(
                        nu_username, nu_email, nu_name.strip() or nu_username,
                        _hash_password(nu_password), is_admin=nu_is_admin,
                    )
                    if ok:
                        st.success(msg + " Share the username/email + this password with them.")
                    else:
                        st.error(msg)

        st.divider()
        st.markdown("#### Existing users")
        _users = list_app_users()
        if not _users:
            st.info("No users yet.")
        for _u in _users:
            u_username, u_email, u_name, u_is_admin, u_created = _u
            uc1, uc2, uc3 = st.columns([3, 2, 1])
            with uc1:
                badge = " (admin)" if u_is_admin else ""
                st.markdown(f"**{escape(u_username)}**{badge}  \n{escape(u_email or '')}")
            with uc2:
                st.caption(f"{escape(u_name or '')}\nadded {escape(str(u_created or ''))[:10]}")
            with uc3:
                _is_self = u_username == st.session_state.get("_authed_user")
                if u_is_admin or _is_self:
                    st.caption("—")
                elif st.button("Remove", key=f"del_user_{u_username}"):
                    delete_app_user(u_username)
                    st.rerun()

        st.divider()
        st.markdown("#### Change my password")
        with st.form("change_pw_form", clear_on_submit=True):
            new_pw = st.text_input("New password", type="password")
            new_pw2 = st.text_input("Confirm new password", type="password")
            pw_submitted = st.form_submit_button("Update my password")
            if pw_submitted:
                if not new_pw or new_pw != new_pw2:
                    st.error("Passwords are empty or do not match.")
                else:
                    set_user_password(st.session_state["_authed_user"], _hash_password(new_pw))
                    st.success("Password updated. Use it next time you sign in.")
