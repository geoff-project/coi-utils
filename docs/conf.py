# SPDX-FileCopyrightText: 2020-2024 CERN
# SPDX-FileCopyrightText: 2023-2024 GSI Helmholtzzentrum für Schwerionenforschung
# SPDX-FileNotice: All rights not expressly granted are reserved.
#
# SPDX-License-Identifier: GPL-3.0-or-later OR EUPL-1.2+

"""Configuration file for the Sphinx documentation builder.

This file only contains a selection of the most common options. For a
full list see the documentation:
https://www.sphinx-doc.org/en/master/usage/configuration.html
"""

# -- Path setup --------------------------------------------------------

from __future__ import annotations

import pathlib
import sys
import typing as t
from pathlib import Path

if sys.version_info < (3, 10):
    import importlib_metadata as importlib_metadata
else:
    import importlib.metadata as importlib_metadata

if t.TYPE_CHECKING:
    from sphinx.application import Sphinx


ROOTDIR = pathlib.Path(__file__).absolute().parent.parent


# -- Project information -----------------------------------------------

project = "cernml-coi-utils"
dist = importlib_metadata.distribution(project)

copyright = "2020–2024 CERN, 2023-2024 GSI Helmholtzzentrum für Schwerionenforschung"
author = "Nico Madysa"
release = dist.version
version = release.partition("+")[0]

for entry in dist.metadata.get_all("Project-URL", []):
    url: str
    kind, url = entry.split(", ")
    if kind == "gitlab":
        gitlab_url = url.removesuffix("/")
        license_url = f"{gitlab_url}/-/blob/master/COPYING"
        issues_url = f"{gitlab_url}/-/issues"
        break
else:
    gitlab_url = ""
    license_url = ""
    issues_url = ""

# -- General configuration ---------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
sys.path.append(str(Path("./_ext").resolve()))
extensions = [
    "fix_xrefs",
    "extra_directives",
    "mock_java_packages",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = [
    ".DS_Store",
    "Thumbs.db",
    "_build",
]

# Don't repeat the class name for methods and attributes in the page
# table of content of class API docs.
toc_object_entries_show_parents = "hide"

# A list of prefixes that are ignored for sorting the Python module
# index.
modindex_common_prefix = ["cernml."]

# Avoid role annotations as much as possible.
default_role = "py:obj"

# Use one line per argument for long signatures.
maximum_signature_line_length = 89

# -- Options for HTML output -------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation
# for a list of builtin themes.
html_theme = "python_docs_theme"
html_last_updated_fmt = "%b %d %Y"
html_theme_options = {
    "sidebarwidth": "21rem",
    "root_url": "https://acc-py.web.cern.ch/",
    "root_name": "Acc-Py Documentation server",
    "license_url": license_url,
    "issues_url": issues_url,
}
templates_path = ["./_templates/"]
html_static_path = ["./_static/"]

# -- Options for Autodoc -----------------------------------------------

autodoc_member_order = "bysource"
autodoc_typehints = "signature"
autodoc_type_aliases = {
    "MaybeTitledFigure": "~cernml.mpl_utils.MaybeTitledFigure",
    "MatplotlibFigures": "~cernml.mpl_utils.MatplotlibFigures",
    "RenderCallback": "~cernml.mpl_utils.RenderCallback",
    "RenderGenerator": "~cernml.mpl_utils.RenderGenerator",
}

napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_use_ivar = False
napoleon_attr_annotations = True

# -- options for Autosectionlabel --------------------------------------

autosectionlabel_prefix_document = True
autosectionlabel_maxdepth = 3

# -- Options for Intersphinx -------------------------------------------


def acc_py_docs_link(repo: str) -> str:
    """A URL pointing to the Acc-Py docs server."""
    return f"https://acc-py.web.cern.ch/gitlab/{repo}/docs/stable/"


def rtd_link(name: str, branch: str = "stable") -> str:
    """A URL pointing to a Read The Docs project."""
    return f"https://{name}.readthedocs.io/en/{branch}"


intersphinx_mapping = {
    "cmmnbuild": (acc_py_docs_link("scripting-tools/cmmnbuild-dep-manager"), None),
    "coi": (acc_py_docs_link("geoff/cernml-coi"), None),
    "gym": ("https://gymnasium.farama.org/", None),
    "jpype": ("https://jpype.readthedocs.io/en/latest/", None),
    "mpl": ("https://matplotlib.org/stable/", None),
    "np": ("https://numpy.org/doc/stable/", None),
    "pip": (rtd_link("pip-python3"), None),
    "pyjapc": (acc_py_docs_link("scripting-tools/pyjapc"), None),
    "python": ("https://docs.python.org/3", None),
    "setuptools": ("https://setuptools.pypa.io/en/stable/", None),
    "std": ("https://docs.python.org/3/", None),
}

# -- Options for custom extension FixXrefs -----------------------------


fix_xrefs_rules = [
    {"pattern": r"^cernml\..*\.T$", "reftarget": ("const", "typing.TypeVar")},
    {"pattern": r"^np\.", "reftarget": ("sub", "numpy."), "contnode": ("sub", "")},
    {"pattern": r"^t\.", "reftarget": ("sub", "typing."), "contnode": ("sub", "")},
    {"pattern": r"^Figure$", "reftarget": ("const", "matplotlib.figure.Figure")},
    {
        "pattern": r"^cancellation\.",
        "reftarget": ("sub", r"cernml.coi.\g<0>"),
        "contnode": ("sub", ""),
    },
    {
        "pattern": "^Value$",
        "external": {
            "uri": "https://abwww.cern.ch/ap/dist/accsoft/commons/accsoft-commons-value/PRO/build/docs/api/index.html?cern/accsoft/commons/value/Value.html",
            "package": "accsoft-commons-value",
        },
    },
    {
        "pattern": "^LSAClient$",
        "external": {
            "uri": "https://gitlab.cern.ch/scripting-tools/pjlsa#low-level-access-to-the-java-lsa-api",
            "package": "pjlsa",
        },
    },
]

# -- Custom code -------------------------------------------------------


def _fix_decorator_return_value(_app: Sphinx, obj: t.Any, _bound_method: bool) -> None:
    if callable(obj) and obj.__name__ == "render_generator":
        obj.__annotations__["return"] = "t.Callable[[str], MatplotlibFigures]"


def setup(app: Sphinx) -> None:
    """Set up hooks into Sphinx."""
    app.connect("autodoc-before-process-signature", _fix_decorator_return_value)
