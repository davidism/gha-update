import importlib.metadata

# Project --------------------------------------------------------------

project = "gha-update"
version = release = importlib.metadata.version(project).partition(".dev")[0]

# General --------------------------------------------------------------

default_role = "code"
extensions = [
    "sphinx.ext.extlinks",
    "myst_parser",
]
autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_preserve_defaults = True
extlinks = {
    "issue": ("https://github.com/davidism/gha-update/issues/%s", "#%s"),
    "pr": ("https://github.com/davidism/gha-update/pull/%s", "#%s"),
}
myst_enable_extensions = [
    "fieldlist",
]
myst_heading_anchors = 2

# HTML -----------------------------------------------------------------

html_theme = "furo"
html_static_path = ["_static"]
html_css_files = ["theme.css"]
html_copy_source = False
html_theme_options = {
    "source_repository": "https://github.com/davidism/gha-update/",
    "source_branch": "main",
    "source_directory": "docs/",
    "light_css_variables": {
        "font-stack": "'Atkinson Hyperlegible', sans-serif",
        "font-stack--monospace": "'Source Code Pro', monospace",
    },
}
pygments_style = "default"
pygments_style_dark = "github-dark"
html_show_copyright = False
html_use_index = False
html_domain_indices = False
