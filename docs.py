"""
Documentation generation and serving utilities for the application.
"""

import os


def get_docs_path():
    """Returns the path to the documentation directory."""
    return os.path.abspath(os.path.dirname(__file__))
