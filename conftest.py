# SPDX-FileCopyrightText: 2020-2024 CERN
# SPDX-FileCopyrightText: 2023-2024 GSI Helmholtzzentrum für Schwerionenforschung
# SPDX-FileNotice: All rights not expressly granted are reserved.
#
# SPDX-License-Identifier: GPL-3.0-or-later OR EUPL-1.2+

"""Pytest configuration file."""

from collections.abc import Iterator
from contextlib import ExitStack
from typing import Union
from unittest.mock import Mock

import pytest
from pjlsa import LSAClient  # type: ignore[import-untyped]

exit_stack = ExitStack()


def pytest_sessionstart(session: pytest.Session) -> None:
    lsa_client = LSAClient(server="next")
    exit_stack.enter_context(lsa_client.java_api())


def pytest_sessionfinish(
    session: pytest.Session, exitstatus: Union[int, pytest.ExitCode]
) -> None:
    exit_stack.close()


@pytest.fixture(autouse=True)
def trim_service(monkeypatch: pytest.MonkeyPatch) -> Iterator[Mock]:
    from cernml.lsa_utils import _services

    service = Mock(spec=_services.TrimService)
    monkeypatch.setattr(_services, "trim", service)
    return service
