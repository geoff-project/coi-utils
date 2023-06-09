# SPDX-FileCopyrightText: 2020-2023 CERN
# SPDX-FileCopyrightText: 2023 GSI Helmholtzzentrum für Schwerionenforschung
# SPDX-FileNotice: All rights not expressly granted are reserved.
#
# SPDX-License-Identifier: GPL-3.0-or-later OR EUPL-1.2+

"""Global variables for various LSA services."""

from __future__ import annotations

import typing as t

from cern.lsa.client import (
    ContextService,
    GenerationService,
    ParameterService,
    ServiceLocator,
    SettingService,
    TrimService,
)

if t.TYPE_CHECKING:  # pragma: no cover
    from cern.lsa.client.common import (
        CommonContextService,
        CommonGenerationService,
        CommonParameterService,
        CommonSettingService,
        CommonTrimService,
    )

context: CommonContextService = ServiceLocator.getService(ContextService)
generation: CommonGenerationService = ServiceLocator.getService(GenerationService)
parameter: CommonParameterService = ServiceLocator.getService(ParameterService)
setting: CommonSettingService = ServiceLocator.getService(SettingService)
trim: CommonTrimService = ServiceLocator.getService(TrimService)
