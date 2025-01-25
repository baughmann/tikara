import os
import sys

sys.path.insert(0, os.path.abspath("../../src"))

project = "tikara"
copyright = "2024, Nick Baughman"  # noqa: A001
author = "Nick Baughman"

# -- General configuration ---------------------------------------------------
extensions = [
    # Core Sphinx extensions
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "sphinx.ext.doctest",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.todo",
    "sphinx.ext.duration",
    "sphinx.ext.intersphinx",
    "sphinx.ext.coverage",
    "sphinx.ext.graphviz",
    "sphinx.ext.autosummary",
    # Third-party extensions
    "myst_parser",
    "sphinx_autodoc_typehints",
    "sphinx_copybutton",
    "sphinx_git",
    "sphinxemoji.sphinxemoji",
    "sphinx_sitemap",
]

# Create _static directory if it doesn't exist
os.makedirs("docs/source/_static", exist_ok=True)

templates_path = ["_templates"]
exclude_patterns = ["test*"]
sphinxemoji_style = "twemoji"

# Intersphinx configuration
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "requests": ("https://requests.readthedocs.io/en/latest/", None),
}

# AutoDoc configuration
autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "special-members": "__init__",
    "undoc-members": True,
    "exclude-members": "__weakref__",
}

# Primary domain
primary_domain = "py"

# -- Options for HTML output -------------------------------------------------
html_baseurl = "https://baughmann.github.io/tikara/"
html_theme = "sphinxawesome_theme"
html_permalinks_icon = "<span>#</span>"
html_static_path = ["_static"]
sitemap_url_scheme = "{link}"


# Theme options
html_theme_options = {
    "show_breadcrumbs": True,
    "show_prev_next": True,
    "show_toc_level": 3,
}

# Enable todos
todo_include_todos = True
todo_emit_warnings = True

# Better section anchors
html_permalinks = True
# Disable warning about duplicate labels
suppress_warnings = ["autosectionlabel.*"]

autosectionlabel_prefix_document = True
autosectionlabel_maxdepth = None

# Configure myst parser to avoid duplicate labels
myst_heading_anchors = 3


# Configure MyST for README parsing
myst_enable_extensions = [
    "colon_fence",
    "deflist",
]

# Handle escaping in test module names
python_use_unqualified_type_names = True
