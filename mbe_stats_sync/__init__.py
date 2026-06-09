# -*- coding: utf-8 -*-
"""Hidden Streamlit bridge that receives MBE practice stats from the trainer iframe."""

import os

import streamlit.components.v1 as components

_component_path = os.path.join(os.path.dirname(__file__))
_mbe_stats_sync = components.declare_component("mbe_stats_sync", path=_component_path)


def render_mbe_stats_sync(*, key="mbe_stats_sync"):
    """Render a zero-height listener iframe and return the latest stats payload."""
    return _mbe_stats_sync(key=key)
