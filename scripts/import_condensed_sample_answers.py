# -*- coding: utf-8 -*-

"""Compatibility wrapper for the cleaned condensed-answer importer.

The old importer updated several question fields and preserved noisy PDF text in
model_points. Keep this filename working, but route it through the safer importer
that updates only questions.model_points.
"""

import _bootstrap  # noqa: F401

from import_condensed_answers import main


if __name__ == "__main__":
    main()
