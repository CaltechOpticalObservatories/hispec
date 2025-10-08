project = "Hispec"
author = "Caltech Optical Observatories, UCLA, Keck Observatory"
release = "0.1.0"

extensions = ["myst_parser"]
html_theme = "sphinx_rtd_theme"

# allow both .rst and .md
source_suffix = {".rst": "restructuredtext", ".md": "markdown"}

templates_path = ["_templates"]
html_static_path = []

# keep Sphinx from recursing into generated dirs if they appear
exclude_patterns = ["_build", ".doctrees", "Thumbs.db", ".DS_Store"]

