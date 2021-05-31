"""Configuration file for the Sphinx documentation builder.

This file only contains a selection of the most common options. For a
full list see the documentation:
https://www.sphinx-doc.org/en/master/usage/configuration.html
"""

# pylint: disable = import-outside-toplevel
# pylint: disable = invalid-name
# pylint: disable = redefined-builtin

# -- Path setup --------------------------------------------------------

import datetime
import pathlib
import sys
from importlib.machinery import ModuleSpec
from unittest.mock import Mock

import importlib_metadata


class MockLoader:
    def find_spec(self, fullname, path, target):
        if (
            fullname in ["cern", "java"]
            or fullname.startswith("cern.")
            or fullname.startswith("java.")
        ):
            return ModuleSpec(fullname, self, is_package=True)
        return None

    def create_module(self, spec):
        return Mock()

    def exec_module(self, module):
        pass


sys.meta_path.append(MockLoader())

ROOTDIR = pathlib.Path(__file__).absolute().parent.parent


# -- Project information -----------------------------------------------

project = "cernml-coi-utils"
copyright = "2020–2021, BE-OP-SPS, CERN"
author = "Nico Madysa"

release = importlib_metadata.version(project)


# -- General configuration ---------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.graphviz",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
]

# Add any paths that contain templates here, relative to this directory.
# templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = [
    ".DS_Store",
    "Thumbs.db",
    "_build",
]

# -- Options for Autodoc -----------------------------------------------

autodoc_member_order = "bysource"
autodoc_type_aliases = {}

napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_type_aliases = {
    "Problem": "cernml.coi._problem.Problem",
}

# -- Options for Graphviz ----------------------------------------------

graphviz_output_format = "svg"

# -- Options for Intersphinx -------------------------------------------

ACC_PY_DOCS_ROOT = "https://acc-py.web.cern.ch/gitlab/"

intersphinx_mapping = {
    "coi": (ACC_PY_DOCS_ROOT + "be-op-ml-optimization/cernml-coi/docs/stable/", None),
    "pyjapc": (ACC_PY_DOCS_ROOT + "scripting-tools/pyjapc/docs/stable/", None),
    "jpype": ("https://jpype.readthedocs.io/en/latest/", None),
    "mpl": ("https://matplotlib.org/stable/", None),
    "python": ("https://docs.python.org/3", None),
}

# -- Options for Myst-Parser -------------------------------------------

myst_enable_extensions = ["deflist"]
myst_heading_anchors = 3

# -- Options for HTML output -------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation
# for a list of builtin themes.
html_theme = "sphinxdoc"

# Add any paths that contain custom static files (such as style sheets)
# here, relative to this directory. They are copied after the builtin
# static files, so a file named "default.css" will overwrite the builtin
# "default.css". html_static_path = ["_static"]
