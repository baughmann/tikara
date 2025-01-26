import os
import sys

# Add source directory to path
sys.path.insert(0, os.path.abspath("../../src"))

# Project information
project = "Tikara"
copyright = "2024, Nick Baughman"  # noqa: A001
author = "Nick Baughman"

master_doc = "index"

# -- General configuration ---------------------------------------------------
extensions = [
    # Core Sphinx extensions
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "sphinx.ext.autosectionlabel",
    # AutoAPI for automatic API documentation
    "autoapi.extension",
    # Third-party extensions
    "myst_parser",
    'sphinx.ext.doctest',
    "sphinx.ext.autodoc",
    "sphinx.ext.autodoc.typehints",
    "sphinx_design"

]

# Paths
templates_path = ["_templates"]
exclude_patterns = ["test*"]
html_static_path = ["_static"]
html_css_files = ["custom.css"]

# Create _static directory if it doesn't exist
os.makedirs("_static", exist_ok=True)

# AutoAPI configuration
autoapi_type = "python"
autoapi_dirs = ["../../src"]  # Adjust this path to your source directory
autoapi_add_toctree_entry = True  # Avoid automatic addition to the toctree
autoapi_keep_files = False  # Keeps the generated .rst files out of the docs folder
autoapi_options = [
    "members",
    "show-inheritance",
    "show-module-summary",
    "imported-members",
    "special-members",
]
autoapi_python_class_content = "both"

# Enable MyST parser and configure Markdown support
myst_enable_extensions = [
    "colon_fence",  # Enables ::: for fences
    "deflist",      # Enables definition lists
]
myst_heading_anchors = 3  # Auto-generate anchors for up to level 3 headings

# Auto-section labeling
autosectionlabel_prefix_document = True
autosectionlabel_maxdepth = None
highlight_language = 'python3'

# Suppress warnings for duplicate labels
suppress_warnings = ["autosectionlabel.*"]

html_logo ="https://raw.githubusercontent.com/baughmann/tikara/refs/heads/master/tikara_logo.svg"



# -- Options for HTML output -------------------------------------------------
html_baseurl = "https://baughmann.github.io/tikara/"
html_theme = "sphinxawesome_theme"

html_theme_options = {
    "show_breadcrumbs": True,
    "show_prev_next": True,

    "logo_light": "https://raw.githubusercontent.com/baughmann/tikara/refs/heads/master/tikara_logo.svg",
    "logo_dark": "https://raw.githubusercontent.com/baughmann/tikara/refs/heads/master/tikara_logo.svg",

    "extra_header_link_icons": {
        "github": {
            "icon": """<svg height="26px" style="margin-top:-2px;display:inline" viewBox="0 0 45 44" fill="currentColor" xmlns="http://www.w3.org/2000/svg"><path fill-rule="evenodd" clip-rule="evenodd" d="M22.477.927C10.485.927.76 10.65.76 22.647c0 9.596 6.223 17.736 14.853 20.608 1.087.2 1.483-.47 1.483-1.047 0-.516-.019-1.881-.03-3.693-6.04 1.312-7.315-2.912-7.315-2.912-.988-2.51-2.412-3.178-2.412-3.178-1.972-1.346.149-1.32.149-1.32 2.18.154 3.327 2.24 3.327 2.24 1.937 3.318 5.084 2.36 6.321 1.803.197-1.403.759-2.36 1.379-2.903-4.823-.548-9.894-2.412-9.894-10.734 0-2.37.847-4.31 2.236-5.828-.224-.55-.969-2.759.214-5.748 0 0 1.822-.584 5.972 2.226 1.732-.482 3.59-.722 5.437-.732 1.845.01 3.703.25 5.437.732 4.147-2.81 5.967-2.226 5.967-2.226 1.185 2.99.44 5.198.217 5.748 1.392 1.517 2.232 3.457 2.232 5.828 0 8.344-5.078 10.18-9.916 10.717.779.67 1.474 1.996 1.474 4.021 0 2.904-.027 5.247-.027 5.96 0 .58.392 1.256 1.493 1.044C37.981 40.375 44.2 32.24 44.2 22.647c0-11.996-9.726-21.72-21.722-21.72" fill="currentColor"></path></svg>""",
            "link": "https://github.com/baughmann/tikara"
         }
    }
}

# Permalinks
html_permalinks = True
html_permalinks_icon = "<span>#</span>"

# Copy-button configuration
todo_include_todos = False  # Disabled for now, re-enable if needed
