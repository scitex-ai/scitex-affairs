"""Sphinx configuration for scitex-affairs documentation."""

import os
import sys

sys.path.insert(0, os.path.abspath("../../src"))

# -- Project information -----------------------------------------------------

project = "SciTeX Affairs"
copyright = "2026, Yusuke Watanabe"
author = "Yusuke Watanabe"

try:
    from importlib.metadata import version as _get_version

    release = _get_version("scitex-affairs")
except Exception:
    release = "0.1.0"

# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx_rtd_theme",
    "myst_parser",
    "sphinx_copybutton",
    "sphinx_autodoc_typehints",
]

autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "undoc-members": True,
    "exclude-members": "__weakref__",
}

# Heavy or optional runtime deps that the API pages do not need to import.
autodoc_mock_imports = [
    "click",
    "django",
    "figrecipe",
    "plotly",
    "scitex_app",
    "scitex_config",
    "scitex_dev",
]

autosummary_generate = True
napoleon_google_docstring = True
napoleon_numpy_docstring = True

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

# -- Options for HTML output -------------------------------------------------

html_theme = "sphinx_rtd_theme"
html_theme_options = {
    "navigation_depth": 4,
    "collapse_navigation": False,
    "sticky_navigation": True,
}
html_title = f"{project} v{release}"
html_short_title = project
html_context = {
    "display_github": True,
    "github_user": "scitex-ai",
    "github_repo": "scitex-affairs",
    "github_version": "develop",
    "conf_py_path": "/docs/sphinx/",
}

myst_enable_extensions = ["colon_fence", "deflist"]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "pandas": ("https://pandas.pydata.org/docs/", None),
}
