# SPDX-FileCopyrightText: 2020-2023 CERN
# SPDX-FileCopyrightText: 2023 GSI Helmholtzzentrum für Schwerionenforschung
# SPDX-FileNotice: All rights not expressly granted are reserved.
#
# SPDX-License-Identifier: GPL-3.0-or-later OR EUPL-1.2+

# pylint: disable = import-outside-toplevel
# pylint: disable = invalid-name
# pylint: disable = redefined-builtin
# pylint: disable = too-many-arguments
# pylint: disable = unused-argument

"""Configuration file for the Sphinx documentation builder.

This file only contains a selection of the most common options. For a
full list see the documentation:
https://www.sphinx-doc.org/en/master/usage/configuration.html
"""

# -- Path setup --------------------------------------------------------

from __future__ import annotations

import inspect
import pathlib
import sys
import typing as t
from importlib import import_module
from importlib.abc import Loader, MetaPathFinder
from importlib.machinery import ModuleSpec
from types import ModuleType
from unittest.mock import Mock

from docutils import nodes
from sphinx.ext import intersphinx

if sys.version_info < (3, 10):
    import importlib_metadata as metadata
else:
    # Starting with Python 3.10 (see pyproject.toml).
    # pylint: disable = ungrouped-imports
    from importlib import metadata

if t.TYPE_CHECKING:
    # pylint: disable = unused-import
    from sphinx import addnodes
    from sphinx.application import Sphinx
    from sphinx.environment import BuildEnvironment


class MockModule(Mock):
    """Mock that reproduces only its name under `repr()` and `str()`.

    This class overrides the `__repr__()` method of
    `~unittest.mock.Mock` to only show the mock name. We do this because
    Sphinx Autodoc internally uses `repr()` to print types. Without this
    override, any Java types produced by the `MockLoader` below would
    appear as ``<Mock name='...', id='...'>`` in the docs.
    """

    def __str__(self) -> str:
        return self._extract_mock_name()

    def __repr__(self) -> str:
        return self._extract_mock_name()


class MockLoader(Loader, MetaPathFinder):
    """An additional module loader to avoid Java-related errors.

    We don't want to require a full Java Virtual Machine just to build
    the docs, but without it, ``import cern, vaja`` deep in the LSA
    utilities would fail.

    To avoid this, we override the import mechanism and every time
    someone tries to import one of these packages, we return a mock
    object that will just return more mocks for every attribute.
    """

    # pylint: disable = unused-argument, missing-function-docstring

    def find_spec(
        self,
        fullname: str,
        path: t.Optional[t.Sequence[str]],
        target: t.Optional[ModuleType] = None,
    ) -> t.Optional[ModuleSpec]:
        if (
            fullname in ["cern", "java"]
            or fullname.startswith("cern.")
            or fullname.startswith("java.")
        ):
            return ModuleSpec(fullname, self, is_package=True)
        return None

    def create_module(self, spec: ModuleSpec) -> t.Any:
        return MockModule(name=spec.name)

    def exec_module(self, module: ModuleType) -> None:
        pass


sys.meta_path.append(MockLoader())

ROOTDIR = pathlib.Path(__file__).absolute().parent.parent


# -- Project information -----------------------------------------------

project = "cernml-coi-utils"
copyright = "2020–2023 CERN, 2023 GSI Helmholtzzentrum für Schwerionenforschung"
author = "Nico Madysa"
release = metadata.version(project)

# -- General configuration ---------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosectionlabel",
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

# Don't repeat the class name for methods and attributes in the page
# table of content of class API docs.
toc_object_entries_show_parents = "hide"

# Avoid role annotations as much as possible.
default_role = "py:obj"

# -- Options for Autodoc -----------------------------------------------

autodoc_member_order = "bysource"
autodoc_type_aliases = {
    "MaybeTitledFigure": "~cernml.mpl_utils.MaybeTitledFigure",
    "MatplotlibFigures": "~cernml.mpl_utils.MatplotlibFigures",
    "RenderCallback": "~cernml.mpl_utils.RenderCallback",
    "RenderGenerator": "~cernml.mpl_utils.RenderGenerator",
}

napoleon_google_docstring = True
napoleon_numpy_docstring = False

# -- options for Autosectionlabel --------------------------------------

autosectionlabel_prefix_document = True

# -- Options for Intersphinx -------------------------------------------


def acc_py_docs_link(repo: str) -> str:
    """A URL pointing to the Acc-Py docs server."""
    return f"https://acc-py.web.cern.ch/gitlab/{repo}/docs/stable/"


intersphinx_mapping = {
    "cmmnbuild": (acc_py_docs_link("scripting-tools/cmmnbuild-dep-manager"), None),
    "coi": (acc_py_docs_link("geoff/cernml-coi"), None),
    "gym": ("https://gymnasium.farama.org/", None),
    "jpype": ("https://jpype.readthedocs.io/en/latest/", None),
    "mpl": ("https://matplotlib.org/stable/", None),
    "np": ("https://numpy.org/doc/stable/", None),
    "pyjapc": (acc_py_docs_link("scripting-tools/pyjapc"), None),
    "python": ("https://docs.python.org/3", None),
    "std": ("https://docs.python.org/3/", None),
}

# -- Options for HTML output -------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation
# for a list of builtin themes.
html_theme = "sphinxdoc"

# Add any paths that contain custom static files (such as style sheets)
# here, relative to this directory. They are copied after the builtin
# static files, so a file named "default.css" will overwrite the builtin
# "default.css". html_static_path = ["_static"]


# -- Custom code -------------------------------------------------------


def replace_modname(modname: str) -> None:
    """Change the module that a list of objects publicly belongs to.

    This package follows the pattern to have private modules called
    :samp:`_{name}` that expose a number of classes and functions that
    are meant for public use. The parent package then exposes these like
    this::

        from ._name import Thing

    However, these objects then still expose the private module via
    their ``__module__`` attribute::

        assert Thing.__module__ == 'parent._name'

    This function iterates through all exported members of the package
    or module *modname* (as determined by either ``__all__`` or
    `vars()`) and fixes each one's module of origin up to be the
    *modname*. It does so recursively for all public attributes (i.e.
    those whose name does not have a leading underscore).
    """
    todo: t.List[t.Any] = [import_module(modname)]
    while todo:
        parent = todo.pop()
        for pubname in pubnames(parent):
            obj = inspect.getattr_static(parent, pubname)
            private_modname = getattr(obj, "__module__", "")
            if private_modname and _is_true_prefix(modname, private_modname):
                obj.__module__ = modname
                todo.append(obj)


def pubnames(obj: t.Any) -> t.Iterator[str]:
    """Return an iterator over the public names in an object."""
    return iter(
        t.cast(t.List[str], getattr(obj, "__all__", None))
        or (
            name
            for name, _ in inspect.getmembers_static(obj)
            if not name.startswith("_")
        )
    )


def _is_true_prefix(prefix: str, full: str) -> bool:
    return full.startswith(prefix) and full != prefix


# Do submodules first so that `coi.check()` is correctly assigned.
replace_modname("cernml.gym_utils")
replace_modname("cernml.japc_utils")
replace_modname("cernml.lsa_utils")
replace_modname("cernml.mpl_utils")


def make_external_ref(
    contnode: nodes.TextElement, uri: str, package: str
) -> nodes.reference:
    """Create a new reference node that wraps *contnode*."""
    newnode = nodes.reference(
        "", "", internal=False, refuri=uri, reftitle=f"(in {package!s})"
    )
    newnode.append(contnode)
    return newnode


def _fix_crossrefs(
    app: Sphinx,
    env: BuildEnvironment,
    node: addnodes.pending_xref,
    contnode: nodes.TextElement,
) -> t.Optional[nodes.Element]:
    # Autodoc doesn't handle typing.TypeVar correctly.
    if node["reftarget"].rpartition(".")[-1] == "T":
        node["reftarget"] = "std:typing.TypeVar"
        return intersphinx.missing_reference(app, env, node, contnode)
    # Intersphinx cannot read the :canonical: attribute on the ..class
    # directive for Box.
    if node["reftarget"] == "gymnasium.spaces.box.Box":
        node["reftarget"] = "gymnasium.spaces.Box"
        return intersphinx.missing_reference(app, env, node, contnode)
    # Cross-link Java documentation.
    if node["reftarget"] == "cern.accsoft.commons.value.Value":
        return make_external_ref(
            contnode,
            uri="https://abwww.cern.ch/ap/dist/accsoft/commons/accsoft-commons-value/"
            "PRO/build/docs/api/index.html?cern/accsoft/commons/value/Value.html",
            package="accsoft-commons-value",
        )
    # No documentation exists for PJLsa, pick a related section of the
    # README file.
    if node["reftarget"] == "LSAClient":
        return make_external_ref(
            contnode,
            uri="https://gitlab.cern.ch/scripting-tools/pjlsa#"
            "low-level-access-to-the-java-lsa-api",
            package="pjlsa",
        )
    return None


def _fix_decorator_return_value(_app: Sphinx, obj: t.Any, _bound_method: bool) -> None:
    if callable(obj) and obj.__name__ == "render_generator":
        obj.__annotations__["return"] = "t.Callable[[str], MatplotlibFigures]"


def setup(app: Sphinx) -> None:
    """Set up hooks into Sphinx."""
    app.connect("missing-reference", _fix_crossrefs)
    app.connect("autodoc-before-process-signature", _fix_decorator_return_value)
