# SPDX-FileCopyrightText: 2020-2024 CERN
# SPDX-FileCopyrightText: 2023-2024 GSI Helmholtzzentrum für Schwerionenforschung
# SPDX-FileNotice: All rights not expressly granted are reserved.
#
# SPDX-License-Identifier: GPL-3.0-or-later OR EUPL-1.2+

"""Pytest configuration file."""

import warnings
from collections.abc import Iterator
from contextlib import ExitStack
from typing import Union
from unittest.mock import Mock

import jpype  # type: ignore[import-untyped]
import pytest
from pjlsa import LSAClient  # type: ignore[import-untyped]

exit_stack = ExitStack()

collect_ignore: list[str] = []


def pytest_sessionstart(session: pytest.Session) -> None:
    try:
        lsa_client = LSAClient(server="next")
    except jpype.JVMNotFoundException:
        warnings.warn("JVM not found, skipping LSA tests", stacklevel=1)
        collect_ignore.extend(
            (
                "src/cernml/lsa_utils/__init__.py",
                "src/cernml/lsa_utils/_hooks.py",
                "src/cernml/lsa_utils/_incorporator.py",
                "src/cernml/lsa_utils/_services.py",
                "src/cernml/lsa_utils/_utils.py",
            )
        )
    else:
        exit_stack.enter_context(lsa_client.java_api())


def pytest_sessionfinish(
    session: pytest.Session, exitstatus: Union[int, pytest.ExitCode]
) -> None:
    exit_stack.close()


@pytest.fixture(autouse=True)
def trim_service(monkeypatch: pytest.MonkeyPatch) -> Iterator[Mock]:
    if jpype.isJVMStarted():
        from cernml.lsa_utils import _services

        service = Mock(spec=_services.TrimService)
        monkeypatch.setattr(_services, "trim", service)
    else:
        service = Mock(spec=object())
    return service
