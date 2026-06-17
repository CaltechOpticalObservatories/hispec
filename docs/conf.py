"""Sphinx configuration for the HISPEC documentation."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

project = "HISPEC"
author = "Caltech Optical Observatories, UCLA, Keck Observatory"
release = "0.1.0"

extensions = [
    "myst_parser",
]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

master_doc = "index"
templates_path = ["_templates"]
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
]

html_theme = "shibuya"
html_title = "HISPEC Documentation"
html_static_path = []
html_theme_options = {
    "accent_color": "blue",
    "github_url": "https://github.com/CaltechOpticalObservatories/hispec",
}
