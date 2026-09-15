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
    "sphinxcontrib.mermaid",
]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

# ```mermaid fenced blocks in MyST pages are handed to sphinxcontrib-mermaid,
# and "raw" emits the mermaid.js <div> rather than shelling out to mmdc, so the
# docs build needs no node/puppeteer. Matches coo-software-architecture.
myst_fence_as_directive = ["mermaid"]
mermaid_output_format = "raw"

# Needed for the cross-page "#section" links between the architecture pages.
myst_heading_anchors = 3

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
