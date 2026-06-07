# -*- coding: utf-8 -*-
"""MBE page renderer for the separate multiple-choice trainer."""

import os

from ui_components import render_html_file_embed, render_page_title


def render_mbe_drills_page():
    render_page_title(
        "MBE Drills - Trap Trainer",
        (
            "Multiple-choice trap drilling. Drill or lecture mode, import your "
            "AdaptiBar misses, and add your own cards."
        ),
    )

    mbe_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mbe_trap_trainer.html")
    render_html_file_embed(
        mbe_path,
        missing_message=(
            "mbe_trap_trainer.html was not found next to app.py. "
            "Make sure the file is in the project folder."
        ),
    )
