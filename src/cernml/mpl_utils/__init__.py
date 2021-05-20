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
