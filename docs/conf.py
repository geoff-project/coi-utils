"""Configuration file for the Sphinx documentation builder.

This file only contains a selection of the most common options. For a
full list see the documentation:
https://www.sphinx-doc.org/en/master/usage/configuration.html
"""

# pylint: disable = import-outside-toplevel
# pylint: disable = invalid-name
# pylint: disable = redefined-builtin

# -- Path setup --------------------------------------------------------

import pathlib
import re
import sys
import typing as t
from importlib.abc import Loader, MetaPathFinder
from importlib.machinery import ModuleSpec
from types import FunctionType, ModuleType
from unittest.mock import Mock

import importlib_metadata


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
copyright = "2020–2021, BE-OP-SPS, CERN"
author = "Nico Madysa"
release = importlib_metadata.version(project)
default_role = "py:obj"

# -- General configuration ---------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
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


def _deduce_public_module_name(name: str) -> str:
    """Return *name* with all private module names removed."""
    if name.startswith("cernml.coi._"):
        return "cernml.coi"
    if name.startswith("cernml.mpl_utils._"):
        return "cernml.mpl_utils"
    if name == "gym.core":
        return "gym"
    if name.startswith("gym.spaces."):
        return "gym.spaces"
    return name


def _hide_class_module(class_):  # type: ignore
    """Hide private module names.

    This compares each class's module of origin against a filter list in
    :func:`_deduce_public_module_name()` and removes any modules that we
    deem "private", nudging people towards using the public re-exports
    instead.
    """
    old_name = getattr(class_, "__module__", "")
    if not old_name:
        return
    new_name = _deduce_public_module_name(old_name)
    if new_name != old_name:
        class_.__module__ = new_name


def _expand_typing_abbreviation(class_):  # type: ignore
    """Fix broken expansion of generic decorator constructor arguments.

    The :class:`@cern.mpl_utils.render_generator()` is a generic method
    decorator that is actually a class, not a function itself. The
    constructor contains a type variable *T*, non-class types
    :data:`~typing.Callable` and a (fake-class) type alias
    :class:`~cernml.mpl_utils.RenderGenerator`. Obviously, this throws
    Autodoc for a loop.

    If we didn't do anything, it would leave everything unexpanded. This
    would correctly show "RenderGenerator" and link to its definition.
    However, it would also leave "t.Callable" unexpanded and unable to
    link to its definition.

    We *could* just run the annotations through
    :func:`~typing.get_type_hints()`. This would expand everything,
    including RenderGenerator, making the type as an abbreviation
    useless.

    Instead, we manually expand the parts we want to expand (the typing
    module and concrete class :class:`~matplotlib.figure.Figure`) and
    leave the rest untouched.
    """
    # Don't use typing.get_type_hints, it expands *everything*.
    annotations = getattr(class_.__init__, "__annotations__", None)
    if not annotations:
        return
    # Expand `Figure` and `t` without expanding `RenderGenerator`.
    expanded = {
        name: re.sub(r"\bt\b", "typing", type_).replace(
            "Figure", "~matplotlib.figure.Figure"
        )
        for name, type_ in annotations.items()
    }
    class_.__init__.__annotations__ = expanded


def _hide_private_modules(_app, obj, _bound_method):  # type: ignore
    if isinstance(obj, type):
        for base in obj.__mro__:
            _hide_class_module(base)
        if issubclass(obj, t.Generic):
            _expand_typing_abbreviation(obj)
    if isinstance(obj, FunctionType):
        if "gym_utils" in obj.__module__ or obj.__name__ == "make_renderer":
            for annotated_type in t.get_type_hints(obj).values():
                _hide_class_module(annotated_type)


def setup(app):  # type: ignore
    """Sphinx setup hook."""
    app.connect("autodoc-before-process-signature", _hide_private_modules)


# -- Options for Intersphinx -------------------------------------------

ACC_PY_DOCS_ROOT = "https://acc-py.web.cern.ch/gitlab/"

intersphinx_mapping = {
    "coi": (ACC_PY_DOCS_ROOT + "geoff/cernml-coi/docs/stable/", None),
    "jpype": ("https://jpype.readthedocs.io/en/latest/", None),
    "mpl": ("https://matplotlib.org/stable/", None),
    "np": ("https://numpy.org/doc/stable/", None),
    "pyjapc": (ACC_PY_DOCS_ROOT + "scripting-tools/pyjapc/docs/stable/", None),
    "python": ("https://docs.python.org/3", None),
}

# -- Options for HTML output -------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation
# for a list of builtin themes.
html_theme = "sphinxdoc"

# Add any paths that contain custom static files (such as style sheets)
# here, relative to this directory. They are copied after the builtin
# static files, so a file named "default.css" will overwrite the builtin
# "default.css". html_static_path = ["_static"]
