# SPDX-FileCopyrightText: 2020-2024 CERN
# SPDX-FileCopyrightText: 2023-2024 GSI Helmholtzzentrum für Schwerionenforschung
# SPDX-FileNotice: All rights not expressly granted are reserved.
#
# SPDX-License-Identifier: GPL-3.0-or-later OR EUPL-1.2+

"""Figure management based on render mode."""

from __future__ import annotations

import sys
import typing as t
from abc import abstractmethod

from ._iter import MatplotlibFigures

if t.TYPE_CHECKING:
    from matplotlib.figure import Figure

if sys.version_info < (3, 12):
    from typing_extensions import override
else:
    from typing import override

__all__ = (
    "HumanStrategy",
    "MatplotlibFiguresStrategy",
    "FigureStrategy",
)


@t.runtime_checkable
class FigureStrategy(t.Protocol):
    """The base protocol for figure management.

    `Renderer` employs the strategy_ pattern. Depending on which
    `~cernml.coi.Problem.render_mode` is chosen, they are assigned
    a different strategy object. This object describes how to create,
    update and close figures.

    Users typically don't interact with this part of the package. It is
    only interesting if you want to define your own render mode.

    .. _strategy: https://en.wikipedia.org/wiki/Strategy_pattern
    """

    __slots__ = ()

    @abstractmethod
    def make_figure(self, title: str | None) -> Figure:
        """Create a figure.

        This should create the figure object. In render mode
        :rmode:`"human"`, this is a managed figure created via
        `plt.figure() <matplotlib.pyplot.figure>`. Otherwise, it's
        a regular, unmanaged figure.

        The *title* object, if passed, should be used as the label or
        window title of the figure.
        """
        raise NotImplementedError

    @abstractmethod
    def update_figure(self, figure: Figure) -> t.Any:
        """Update the figure as necessary.

        This is called by `FigureRenderer` after the user has made
        updates the artists of the figure. In render mode
        :rmode:`"human"`, this calls `Canvas.draw_idle()
        <matplotlib.backend_bases.FigureCanvasBase.draw_idle>` to bring
        the updated graphics to the user's screen.
        """
        raise NotImplementedError

    @abstractmethod
    def close_figure(self, figure: Figure) -> None:
        """Close the figure and clean it up.

        This performs any necessary cleanup when the figure is no longer
        needed. In render mode :rmode:`"human"`, this calls
        `pyplot.close() <matplotlib.pyplot.close>` to let the figure
        manager know that the figure can be recycled.
        """
        raise NotImplementedError


class HumanStrategy(FigureStrategy):
    """Strategy for render mode :rmode:`"human"`."""

    __slots__ = ()

    @override
    def make_figure(self, title: str | None) -> Figure:
        import matplotlib.pyplot as plt

        return plt.figure(title)

    @override
    def update_figure(self, figure: Figure) -> None:
        # In human mode, we must manually update our figure to
        # ensure that the results of `self._update` become visible.
        figure.show(warn=False)
        # Use draw_idle() to actually postpone drawing until the
        # next GUI pause. In `matplotlib_figures` mode, we return
        # our figure to the caller, so they are free to call draw()
        # themselves.
        figure.canvas.draw_idle()

    @override
    def close_figure(self, figure: Figure) -> None:
        import matplotlib.pyplot as plt

        # Do not call ``pyplot.close(None)`` -- that closes the current
        # figure, as returned by ``pyplot.gcf()``, which might be
        # completely unrelated to us.
        # On the other hand, it's safe to close a figure that is not
        # managed by pyplot. This case is caught internally and nothing
        # happens.
        assert figure is not None
        plt.close(figure)


class MatplotlibFiguresStrategy(FigureStrategy):
    """Strategy for render mode :rmode:`"matplotlib_figures"`."""

    __slots__ = ()

    @override
    def make_figure(self, title: str | None) -> Figure:
        from matplotlib.figure import Figure

        return Figure(label=title)

    @override
    def update_figure(self, figure: Figure) -> MatplotlibFigures:
        label = figure.get_label()
        if label is not None:
            return ((str(label), figure),)
        return (figure,)

    @override
    def close_figure(self, figure: Figure) -> None:
        pass
