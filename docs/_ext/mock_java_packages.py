# SPDX-FileCopyrightText: 2020-2024 CERN
# SPDX-FileCopyrightText: 2023-2024 GSI Helmholtzzentrum für Schwerionenforschung
# SPDX-FileNotice: All rights not expressly granted are reserved.
#
# SPDX-License-Identifier: GPL-3.0-or-later OR EUPL-1.2+

"""A meta path finder for Python's import machinery that mocks Java packages."""

from __future__ import annotations

import sys
import typing as t
from importlib.abc import Loader, MetaPathFinder
from importlib.machinery import ModuleSpec
from unittest.mock import Mock

if t.TYPE_CHECKING:
    from types import ModuleType

    from sphinx.application import Sphinx


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

    def find_spec(
        self,
        fullname: str,
        path: t.Sequence[str] | None,
        target: ModuleType | None = None,
    ) -> ModuleSpec | None:
        if fullname in ("cern", "java") or fullname.startswith(("cern.", "java.")):
            return ModuleSpec(fullname, self, is_package=True)
        return None

    def create_module(self, spec: ModuleSpec) -> t.Any:
        return MockModule(name=spec.name)

    def exec_module(self, module: ModuleType) -> None:
        pass


def setup(app: Sphinx) -> None:
    """Set up hooks into Sphinx."""
    sys.meta_path.append(MockLoader())
