# SPDX-FileCopyrightText: 2020-2023 CERN
# SPDX-FileCopyrightText: 2023 GSI Helmholtzzentrum für Schwerionenforschung
# SPDX-FileNotice: All rights not expressly granted are reserved.
#
# SPDX-License-Identifier: GPL-3.0-or-later OR EUPL-1.2+

# pylint: disable = missing-function-docstring
# pylint: disable = unused-argument

"""Pytest configuration file."""

from contextlib import ExitStack
from typing import Union

from pjlsa import LSAClient  # type: ignore
from pytest import ExitCode, Session

exit_stack = ExitStack()


def pytest_sessionstart(session: Session) -> None:
    lsa_client = LSAClient(server="next")
    exit_stack.enter_context(lsa_client.java_api())


def pytest_sessionfinish(session: Session, exitstatus: Union[int, ExitCode]) -> None:
    exit_stack.close()
