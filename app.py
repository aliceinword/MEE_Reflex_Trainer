# -*- coding: utf-8 -*-

import streamlit as st

from auth import require_login
from app_shell import render_app_shell
from database import ensure_db_initialized


st.set_page_config(
    page_title="MEE Reflex Trainer",
    page_icon=":books:",
    layout="wide",
    initial_sidebar_state="expanded",
)


ensure_db_initialized()

require_login()

menu, reading_settings = render_app_shell()


if menu == "Dashboard":
    from main_pages import render_dashboard_page

    render_dashboard_page()


elif menu in {"MEE Question Bank", "Question Bank"}:
    from main_pages import render_question_bank_page

    render_question_bank_page(reading_settings["compact_mode"])


elif menu in {"MEE Advanced Tools", "Advanced Tools", "Import Questions", "Manual Entry"}:
    from content_tools import render_advanced_tools_page

    render_advanced_tools_page()
elif menu == "MEE Muscle Ladder":
    from practice_pages import render_muscle_ladder_page

    render_muscle_ladder_page(
        reading_settings["compact_mode"],
        reading_settings["reading_mode"],
    )


elif menu == "Settings":
    from main_pages import render_settings_page

    render_settings_page(
        reading_settings["reading_mode"],
        reading_settings["compact_mode"],
        reading_settings["font_size"],
        reading_settings["line_height"],
    )


elif menu == "MBE Drills":
    from mbe_pages import render_mbe_drills_page

    render_mbe_drills_page()

elif menu == "Bridge Drill":
    from mbe_pages import render_bridge_drill_page

    render_bridge_drill_page()

elif menu == "Rule Recall":
    from mbe_pages import render_rule_recall_page

    render_rule_recall_page()

elif menu == "Flashcards Drill":
    from mbe_pages import render_mbe_flashcards_drill_page

    render_mbe_flashcards_drill_page()

elif menu == "MBE Drills Question Bulk Upload":
    from mbe_pages import render_mbe_bulk_upload_page

    render_mbe_bulk_upload_page()


elif menu == "Manage Users":
    from user_pages import render_manage_users_page

    render_manage_users_page()
