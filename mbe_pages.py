# -*- coding: utf-8 -*-
"""MBE page renderer for the separate multiple-choice trainer."""

import os

from ui_components import FULL_PAGE_EMBED_HEIGHT, render_html_file_embed


def render_mbe_drills_page():
    mbe_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mbe_trap_trainer.html")
    render_html_file_embed(
        mbe_path,
        height=FULL_PAGE_EMBED_HEIGHT,
        missing_message=(
            "mbe_trap_trainer.html was not found next to app.py. "
            "Make sure the file is in the project folder."
        ),
    )
