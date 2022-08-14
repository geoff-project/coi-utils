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

if t.TYPE_CHECKING:
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
