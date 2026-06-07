# -*- coding: utf-8 -*-

import streamlit as st

from auth import require_login
from app_shell import render_app_shell
from content_tools import render_advanced_tools_page
from database import init_db
from main_pages import render_dashboard_page, render_question_bank_page, render_settings_page
from mbe_pages import render_mbe_drills_page
from practice_pages import render_muscle_ladder_page
from user_pages import render_manage_users_page




st.set_page_config(
    page_title="MEE Reflex Trainer",
    page_icon=":books:",
    layout="wide",
    initial_sidebar_state="expanded",
)


init_db()



require_login()

menu, reading_settings = render_app_shell()


if menu == "Dashboard":
    render_dashboard_page()


elif menu == "Question Bank":
    render_question_bank_page(reading_settings["compact_mode"])


elif menu in {"Advanced Tools", "Import Questions", "Manual Entry"}:
    render_advanced_tools_page()

elif menu == "MEE Muscle Ladder":
    render_muscle_ladder_page(
        reading_settings["compact_mode"],
        reading_settings["reading_mode"],
    )


elif menu == "Settings":
    render_settings_page(
        reading_settings["reading_mode"],
        reading_settings["compact_mode"],
        reading_settings["font_size"],
        reading_settings["line_height"],
    )


elif menu == "MBE Drills":
    render_mbe_drills_page()


elif menu == "Manage Users":
    render_manage_users_page()
