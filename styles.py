# -*- coding: utf-8 -*-
"""Global Streamlit styling for the MEE trainer."""

import streamlit as st


def render_global_styles():
    st.markdown("""
    <style>
    /* Main app background */
    .stApp {
        background: linear-gradient(135deg, #F7FBFF 0%, #EEF6FF 48%, #ECFEFF 100%);
        color: #102033;
    }
    
    /* Main content container */
    .block-container {
        max-width: none !important;
        width: 100% !important;
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
        max-width: none;
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
        max-width: none;
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
        max-width: none;
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
        padding: 1.05rem 1.25rem;
        margin: 0.75rem 0 1rem 0;
        box-shadow: 0 4px 14px rgba(29, 78, 137, 0.07);
        width: 100%;
        max-width: none;
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
        max-width: none;
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
        max-width: none;
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
        max-width: none;
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

    .trigger-map-shell {
        margin-top: 0.75rem;
    }

    .trigger-map-box {
        border-color: #FDBA74;
        box-shadow: 0 6px 18px rgba(251, 146, 60, 0.11);
    }

    .trigger-call-text {
        color: #1E293B;
        background: #FFF7ED;
        border: 1px solid #FED7AA;
        border-radius: 12px;
        padding: 0.65rem 0.75rem;
        margin-bottom: 0.7rem;
        font-size: 0.95rem;
        line-height: 1.45;
        font-weight: 700;
    }

    .trigger-map-card {
        background: #FFFBEB;
    }

    .trigger-rule-link {
        color: #78350F;
        font-size: 0.92rem;
        line-height: 1.42;
        margin-top: 0.35rem;
    }

    .trigger-rule-bank {
        background: #FFFFFF;
        border: 1px solid #FED7AA;
        border-radius: 12px;
        padding: 0.65rem 0.8rem;
        margin-top: 0.65rem;
    }

    .trigger-rule-bank-title {
        color: #9A3412;
        font-size: 0.86rem;
        font-weight: 850;
        margin-bottom: 0.35rem;
        text-transform: uppercase;
        letter-spacing: 0.02em;
    }

    .trigger-rule-bank ul {
        margin: 0;
        padding-left: 1.15rem;
    }

    .trigger-rule-bank li {
        color: #1E293B;
        font-size: 0.92rem;
        line-height: 1.42;
        margin-bottom: 0.35rem;
    }
    
    .issues-box {
        background: rgba(255, 255, 255, 0.97);
        border: 1.5px solid #BFDBFE;
        border-radius: 18px;
        padding: 1rem 1.2rem;
        margin: 0.85rem 0 1.1rem 0;
        box-shadow: 0 6px 18px rgba(59, 130, 246, 0.08);
        max-width: none;
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
        max-width: none;
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
        max-width: none;
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
    
    /* Practice page - thin metadata strip metric labels */
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
    
    /* Inactive nav button (secondary) - flat, light */
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
        max-width: none;
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
        max-width: none;
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
        max-width: none;
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


def render_reading_styles(font_size, line_height, max_width, box_padding):
    st.markdown(f"""
    <style>
    .readable-box,
    .sample-answer-box,
    .structured-answer-box,
    .rule-break-card,
    .question-box,
    .triggers-box,
    .call-box,
    .hint-box,
    .trap-box,
    .trap-warning-box {{
        background: rgba(255, 255, 255, 0.96) !important;
        border: 1.5px solid #CDEBFF !important;
        border-radius: 14px !important;
        padding: {box_padding} !important;
        margin: 0.55rem 0 0.8rem 0 !important;
        box-shadow: 0 4px 14px rgba(29, 78, 137, 0.07) !important;
        max-width: min({max_width}px, 100%) !important;
        width: 100% !important;
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
        font-size: {font_size}px !important;
        line-height: {line_height} !important;
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
        font-size: {font_size}px !important;
        line-height: {line_height} !important;
    }}

    [data-testid="stTextArea"] textarea {{
        min-height: 120px;
    }}

    .stMarkdown {{
        line-height: {line_height};
    }}

    .fact-text, .fact-text p,
    .question-text,
    .trigger-facts-text,
    .call-card-text, .call-subpart,
    .outline-rule-text,
    .plug-text,
    .hint-text {{
        font-size: {font_size}px !important;
        line-height: {line_height} !important;
    }}
    </style>
    """, unsafe_allow_html=True)


def render_control_text_styles():
    st.markdown(
        """
    <style>
    .page-title-text { font-size: 1.8rem !important; }
    .page-subtitle { font-size: 0.98rem !important; }
    h1, [data-testid="stHeading"] h1 { font-size: 2.15rem !important; }
    h2, [data-testid="stHeading"] h2 { font-size: 1.7rem !important; }
    h3, [data-testid="stHeading"] h3 { font-size: 1.42rem !important; }
    h4, [data-testid="stHeading"] h4 { font-size: 1.2rem !important; }
    .fact-title, .question-title, .call-title, .readable-title,
    .outline-rule-title, .plug-title, .hint-title, .structured-section-title {
        font-size: 1.18rem !important;
    }

    [data-testid="stExpander"] summary p,
    [data-testid="stExpander"] summary span,
    [data-testid="stExpander"] summary div[data-testid="stMarkdownContainer"] p,
    .streamlit-expanderHeader, .streamlit-expanderHeader p {
        font-size: 1.18rem !important;
        font-weight: 700 !important;
    }

    [data-testid="stTabs"] button[data-baseweb="tab"] p,
    [data-testid="stTabs"] [data-baseweb="tab"] p,
    [data-testid="stTabs"] button[data-baseweb="tab"] {
        font-size: 1.12rem !important;
        font-weight: 700 !important;
    }

    [data-testid="stRadio"] [data-testid="stWidgetLabel"] p,
    [data-testid="stRadio"] [role="radiogroup"] label p,
    [data-testid="stRadio"] [role="radiogroup"] label div {
        font-size: 1.08rem !important;
    }
    [data-testid="stRadio"] [data-testid="stWidgetLabel"] p {
        font-weight: 700 !important;
    }

    [data-testid="stCaptionContainer"] p {
        font-size: 0.95rem !important;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

