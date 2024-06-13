# SPDX-FileCopyrightText: 2020-2024 CERN
# SPDX-FileCopyrightText: 2023-2024 GSI Helmholtzzentrum für Schwerionenforschung
# SPDX-FileNotice: All rights not expressly granted are reserved.
#
# SPDX-License-Identifier: GPL-3.0-or-later OR EUPL-1.2+

"""Utilities for working with the Matplotlib."""

from ._iter import MatplotlibFigures, MaybeTitledFigure, iter_matplotlib_figures
from ._renderer import (
    FigureRenderer,
    RenderCallback,
    Renderer,
    RendererGroup,
    RenderGenerator,
    make_renderer,
    render_generator,
)

__all__ = [
    "FigureRenderer",
    "MatplotlibFigures",
    "MaybeTitledFigure",
    "RenderCallback",
    "RenderGenerator",
    "Renderer",
    "RendererGroup",
    "iter_matplotlib_figures",
    "make_renderer",
    "render_generator",
]
