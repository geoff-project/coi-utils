# SPDX-FileCopyrightText: 2020-2023 CERN
# SPDX-FileCopyrightText: 2023 GSI Helmholtzzentrum für Schwerionenforschung
# SPDX-FileNotice: All rights not expressly granted are reserved.
#
# SPDX-License-Identifier: GPL-3.0-or-later OR EUPL-1.2+

# pylint: disable = import-outside-toplevel
# pylint: disable = missing-function-docstring
# pylint: disable = unused-argument

"""Pytest configuration file."""

from contextlib import ExitStack
from typing import Iterator, Union
from unittest.mock import Mock

from pjlsa import LSAClient  # type: ignore
from pytest import ExitCode, MonkeyPatch, Session, fixture

exit_stack = ExitStack()


def pytest_sessionstart(session: Session) -> None:
    lsa_client = LSAClient(server="next")
    exit_stack.enter_context(lsa_client.java_api())


def pytest_sessionfinish(session: Session, exitstatus: Union[int, ExitCode]) -> None:
    exit_stack.close()


@fixture(autouse=True)
def trim_service(monkeypatch: MonkeyPatch) -> Iterator[Mock]:
    from cernml.lsa_utils import _services

    service = Mock(spec=_services.TrimService)
    monkeypatch.setattr(_services, "trim", service)
    yield service
