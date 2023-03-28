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
