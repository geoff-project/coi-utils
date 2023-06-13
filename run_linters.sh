#!/bin/bash

# SPDX-FileCopyrightText: 2020-2023 CERN
# SPDX-FileCopyrightText: 2023 GSI Helmholtzzentrum für Schwerionenforschung
# SPDX-FileNotice: All rights not expressly granted are reserved.
#
# SPDX-License-Identifier: GPL-3.0-or-later OR EUPL-1.2+

# This script runs all relevant linters with the correct arguments. If one of
# them fails, the script continues running the rest. Only at the end does the
# script determine whether it has failed over-all or not.

# Also note that we try to run the linters from fastest to slowest to get
# feedback as quickly as possible.

if [[ "$*" ]]; then
  if [[ "$*" == --print-versions ]]; then
    reuse --version
    black --version
    isort --version
    pycodestyle --version
    mypy --version
    pylint --version
  else
    echo "Usage: $0 [--print-versions]"
    exit 1
  fi
fi

exit_code=0

reuse lint || exit_code=$((exit_code | $?))

black --check . || exit_code=$((exit_code | $?))

isort --check . || exit_code=$((exit_code | $?))

flake8 src/ tests/*.py || exit_code=$((exit_code | $?))

mypy src/ tests/*.py || exit_code=$((exit_code | $?))

pylint --reports=no --score=no src/ tests/*.py || exit_code=$((exit_code | $?))

exit $exit_code
