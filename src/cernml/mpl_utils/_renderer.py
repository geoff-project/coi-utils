# SPDX-FileCopyrightText: 2020-2024 CERN
# SPDX-FileCopyrightText: 2023-2024 GSI Helmholtzzentrum für Schwerionenforschung
# SPDX-FileNotice: All rights not expressly granted are reserved.
#
# SPDX-License-Identifier: GPL-3.0-or-later OR EUPL-1.2+

"""Classes that make it easier to manage plotting state in COIs."""

from __future__ import annotations

import abc
import typing as t

from matplotlib import pyplot as plt
from matplotlib.figure import Figure

from ._iter import iter_matplotlib_figures

if t.TYPE_CHECKING:
    import sys

    from ._iter import MatplotlibFigures

    if sys.version_info < (3, 11):
        from typing_extensions import Self
    else:
        from typing import Self

__all__ = (
    "FigureRenderer",
    "RenderCallback",
    "RenderGenerator",
    "Renderer",
    "RendererGroup",
    "make_renderer",
    "render_generator",
)


RenderGenerator = t.Generator[None, Figure, t.NoReturn]

RenderCallback = t.Union[
    t.Callable[[Figure], None],
    t.Callable[[Figure], RenderGenerator],
]


class Renderer(metaclass=abc.ABCMeta):
    """Interface for types that facilitate Matplotlib rendering.

    This is an abstract base class. You should use a concrete
    implementation, e.g. `FigureRenderer`.
    """

    @staticmethod
    def make_figure(mode: str) -> Figure:
        """Create the correct kind of figure for the render mode.

        This creates a managed figure in the mode :rmode:`"human"` and
        an unmanaged figure in the mode :rmode:`"matplotlib_figures"`.

        Raises:
            KeyError: if *mode* is neither of the two known render
                modes.
        """
        handlers: dict[str, t.Callable[[], Figure]] = {
            "human": plt.figure,
            "matplotlib_figures": Figure,
        }
        return handlers[mode]()

    @t.overload
    def update(self, mode: t.Literal["human"]) -> None: ...

    @t.overload
    def update(self, mode: t.Literal["matplotlib_figures"]) -> MatplotlibFigures: ...

    @t.overload
    def update(self, mode: str) -> MatplotlibFigures | None: ...

    @abc.abstractmethod
    def update(self, mode: str) -> MatplotlibFigures | None:
        """Update the renderer's figures and return them.

        On the first call, this should initialize the renderer's
        figures. On all subsequent calls, it should reuse the figures
        and update their contents.

        Args:
            mode: The render mode. This must be either :rmode:`"human"`
                or :rmode:`"matplotlib_figures"`.

        Returns:
            None if the render mode is :rmode:`"human"`. Otherwise,
            a sequence of all figures managed by this renderer.
        """


class FigureRenderer(Renderer, metaclass=abc.ABCMeta):
    """Renderer that manages a single figure.

    Args:
        title: If passed, a figure title that is used in the return
            value of ``renderer.update("matplotlib_figures")``. Unused
            in other render modes. In particular, this does *not* add a
            title to the figure's contents. For this, use
            :meth:`~matplotlib.figure.Figure.suptitle()` instead.

    This is another :term:`abstract base class`. There are three typical
    use cases:

    1. You pass a :term:`generator` to `from_callback()`. On the first
       `~Renderer.update()` call, the generator is called to create an
       :term:`iterator`. This iterator is polled on each
       `~Renderer.update()` call::

        >>> import numpy as np
        ...
        >>> class Problem:
        ...     metadata = {"render.modes": ["matplotlib_figures"]}
        ...
        ...     def __init__(self):
        ...         self.data = np.random.uniform(size=10)
        ...         self.renderer = FigureRenderer.from_callback(
        ...             self._iter_updates
        ...         )
        ...
        ...     def render(self, mode="human"):
        ...         if mode in self.metadata["render.modes"]:
        ...             return self.renderer.update(mode)
        ...         return super().render(mode)
        ...
        ...     def _iter_updates(self, fig):
        ...         # First iteration, initialize.
        ...         axes = fig.subplots()
        ...         [points] = axes.plot(self.data, "o")
        ...         print("initialized")
        ...         while True:
        ...             # First iteration is done, yield to the
        ...             # caller. We continue from here on the
        ...             # next `update()` call.
        ...             yield
        ...             # Update the plot, loop, and yield again.
        ...             points.set_ydata(self.data)
        ...             print("updated")
        ...
        >>> problem = Problem()
        >>> fig = problem.render("matplotlib_figures")
        initialized
        >>> fig = problem.render("matplotlib_figures")
        updated

    2. You pass a function to `from_callback()`. This returns a
       subclass that calls this function on each
       `~Renderer.update()` call.

        >>> import numpy as np
        ...
        >>> class Problem:
        ...     metadata = {"render.modes": ["matplotlib_figures"]}
        ...
        ...     def __init__(self):
        ...         self.data = np.random.uniform(size=10)
        ...         self.renderer = FigureRenderer.from_callback(
        ...             self._update_figure
        ...         )
        ...
        ...     def render(self, mode="human"):
        ...         if mode in self.metadata["render.modes"]:
        ...             return self.renderer.update(mode)
        ...         return super().render(mode)
        ...
        ...     def _update_figure(self, fig):
        ...         # Grab or create a subplot.
        ...         [axes] = fig.axes or [fig.subplots()]
        ...         # Clear and redraw from scratch on each turn.
        ...         axes.clear()
        ...         axes.plot(self.data, "o")
        ...         print("redrawn")
        ...
        >>> problem = Problem()
        >>> fig = problem.render("matplotlib_figures")
        redrawn
        >>> fig = problem.render("matplotlib_figures")
        redrawn

    3. You inherit from this class and implement `_init_figure()`
       and `_update_figure()`, which get called by
       `~Renderer.update()` at the appropriate times.

        >>> import numpy as np
        ...
        >>> class ProblemRenderer(FigureRenderer):
        ...     def __init__(self, problem):
        ...         super().__init__()
        ...         self.problem = problem
        ...
        ...     def _init_figure(self, figure):
        ...         axes = figure.subplots()
        ...         axes.plot(self.problem.data, "o")
        ...         print("initialized")
        ...
        ...     def _update_figure(self, figure):
        ...         [axes] = figure.axes
        ...         [curve] = axes.lines
        ...         data = self.problem.data
        ...         curve.set_data(np.arange(len(data)), data)
        ...         print("updated")
        ...
        >>> class Problem:
        ...     metadata = {"render.modes": ["matplotlib_figures"]}
        ...
        ...     def __init__(self):
        ...         self.data = np.random.uniform(size=10)
        ...         self.renderer = ProblemRenderer(self)
        ...
        ...     def render(self, mode="human"):
        ...         if mode in self.metadata["render.modes"]:
        ...             return self.renderer.update(mode)
        ...         return super().render(mode)
        ...
        >>> problem = Problem()
        >>> fig = problem.render("matplotlib_figures")
        initialized
        >>> fig = problem.render("matplotlib_figures")
        updated
    """

    def __init__(self, title: str | None = None) -> None:
        self.figure: Figure | None = None
        self._title = title

    def close(self) -> None:
        """Close the figure managed by this renderer.

        Unless the render mode is :rmode:`"human"` (and figures are
        managed by Matplotlib), this does nothing.
        """
        # Do not call ``pyplot.close(None)`` -- that closes the current
        # figure, as returned by ``pyplot.gcf()``, which might be
        # completely unrelated to us.
        # On the other hand, it's safe to close a figure that is not
        # managed by pyplot. This case is caught internally and nothing
        # happens.
        if self.figure is not None:
            plt.close(self.figure)

    @t.overload
    def update(self, mode: t.Literal["human"]) -> None: ...

    @t.overload
    def update(self, mode: t.Literal["matplotlib_figures"]) -> MatplotlibFigures: ...

    @t.overload
    def update(self, mode: str) -> MatplotlibFigures | None: ...

    def update(self, mode: str) -> MatplotlibFigures | None:
        try:
            figure = self.figure
        except AttributeError:
            raise TypeError("super().__init__() not called") from None
        if figure is None:
            figure = self.figure = self.make_figure(mode)
            self._init_figure(self.figure)
        else:
            self._update_figure(figure)
        if mode == "human":
            # In human mode, we must manually update our figure to
            # ensure that the results of `self._update` become visible.
            figure.show(warn=False)
            # Use draw_idle() to actually postpone drawing until the
            # next GUI pause. In `matplotlib_figures` mode, we return
            # our figure to the caller, so they are free to call draw()
            # themselves.
            figure.canvas.draw_idle()
            return None
        if mode == "matplotlib_figures":
            if self._title is None:
                return (figure,)
            return ((self._title, figure),)
        raise KeyError(mode)

    @abc.abstractmethod
    def _init_figure(self, figure: Figure) -> None:
        """Initialize the figure.

        This is called on the first call to `.update()`, directly after
        instantiating the figure. It should create and fill items of the
        plot.
        """

    @abc.abstractmethod
    def _update_figure(self, figure: Figure) -> None:
        """Update the figure, reflecting any new data.

        This is called on every subsequent `.update()` (but not on the
        first one). It should recreate or update the contents of the
        figure. Afterwards, `.update()` will automatically display the
        figure to the user.
        """

    @staticmethod
    def from_callback(func: RenderCallback, title: str | None = None) -> FigureRenderer:
        """Create a renderer via a callback function or generator.

        Args:
            func: Either a regular function or a generator. If the
                former, it is called on every `.update()`. If the
                latter, it is called once to create an :term:`iterator`.
                The iterator is polled on every `.update()`.
            title: If passed, a string to attach to the figure in the
                render mode :rmode:`"matplotlib_figures"`.

        Returns:
            An unspecified subclass of `FigureRenderer`.
        """
        return _FigureFuncRenderer(func, title)


class _FigureFuncRenderer(FigureRenderer):
    """Return type of `FigureRenderer.from_callback()`."""

    def __init__(
        self,
        func: RenderCallback,
        title: str | None = None,
    ) -> None:
        super().__init__(title)
        self._func = func
        self._generator: RenderGenerator | None = None

    def __repr__(self) -> str:
        if self._title is not None:
            return f"<{type(self).__name__}({self._func!r}, {self._title!r})>"
        return f"<{type(self).__name__}({self._func!r})>"

    def _init_figure(self, figure: Figure) -> None:
        generator = self._func(figure)
        if generator is not None:
            self._generator = generator
            next(generator)

    def _update_figure(self, figure: Figure) -> None:
        if self._generator is not None:
            self._generator.send(figure)
        else:
            self._func(figure)


class RendererGroup(Renderer, tuple[Renderer, ...]):
    """A composite renderer that dispatches to multiple children.

    This is just a tuple of renderers that implements itself the
    `Renderer` interface. Calling `~Renderer.update()`
    forwards the call to each child.

    Example::

        >>> class PrintRenderer(Renderer):
        ...     def __init__(self, index):
        ...         self.index = index
        ...     def update(self, mode):
        ...         print(f"Renderer {self.index} updated")
        >>> g = RendererGroup(PrintRenderer(i) for i in range(1, 6))
        >>> len(g)
        5
        >>> tuple(g) == g
        True
        >>> g.update()
        Renderer 1 updated
        Renderer 2 updated
        Renderer 3 updated
        Renderer 4 updated
        Renderer 5 updated
    """

    __slots__ = ()

    @t.overload
    def update(self, mode: t.Literal["human"]) -> None: ...

    @t.overload
    def update(self, mode: t.Literal["matplotlib_figures"]) -> "MatplotlibFigures": ...

    @t.overload
    def update(self, mode: str) -> "MatplotlibFigures" | None: ...

    def update(self, mode: str = "human") -> "MatplotlibFigures" | None:
        if mode == "human":
            for renderer in self:
                renderer.update("human")
            return None
        if mode == "matplotlib_figures":
            res: list[tuple[str, Figure]] = []
            for renderer in self:
                res.extend(
                    iter_matplotlib_figures(renderer.update("matplotlib_figures"))
                )
            return res
        raise KeyError(mode)


def make_renderer(
    *funcs: RenderCallback | t.Mapping[str, RenderCallback],
    squeeze: bool = True,
) -> Renderer:
    """Build a renderer from one or more callbacks.

    This is a convenience function that calls
    `FigureRenderer.from_callback()` on each passed callback. There are
    three ways to calls this function:

    1. With a single callback function or generator::

        >>> def callback(fig):
        ...     ...
        >>> make_renderer(callback)
        <_FigureFuncRenderer(<function callback at ...>)>

    2. With multiple callbacks::

        >>> g = make_renderer(callback, callback)
        >>> type(g).__name__
        'RendererGroup'
        >>> len(g)
        2

    3. With a mapping from strings to callbacks. The strings are used as
       titles in this case::

        >>> make_renderer({"Figure 1": callback})
        <_FigureFuncRenderer(<function callback at ...>, 'Figure 1')>
        >>> g = make_renderer({"foo": callback, "bar": callback})
        >>> len(g)
        2

    If the optional argument *squeeze* is passed and False, the result
    is always a `RendererGroup` – even if only one callback is
    passed::

        >>> len(make_renderer(callback, squeeze=False))
        1
        >>> len(make_renderer({"foo": callback}, squeeze=False))
        1
    """
    renderers: list[Renderer] = []
    for func_or_mapping in funcs:
        if isinstance(func_or_mapping, t.Mapping):
            renderers.extend(
                _FigureFuncRenderer(func, title)
                for title, func in func_or_mapping.items()
            )
        else:
            renderers.append(_FigureFuncRenderer(func_or_mapping))
    if squeeze and len(renderers) == 1:
        return renderers[0]
    return RendererGroup(renderers)


T = t.TypeVar("T")


class _RenderDescriptor(t.Generic[T]):
    def __init__(
        self,
        func: t.Callable[[T, Figure], None] | t.Callable[[T, Figure], RenderGenerator],
    ) -> None:
        self.func = func
        self.__doc__ = func.__doc__
        self.attrname: str | None = None
        self.renderer: _FigureFuncRenderer | None = None

    def _make_renderer(self, instance: T) -> _FigureFuncRenderer:
        def iter_func_call(fig: Figure) -> RenderGenerator | None:
            return self.func(instance, fig)

        return _FigureFuncRenderer(t.cast(RenderCallback, iter_func_call))

    def __set_name__(self, owner: type[T], name: str) -> None:
        if self.attrname is None:
            self.attrname = name
        elif name != self.attrname:
            raise TypeError(
                f"cannot assign the samer renderer to two different "
                f"names ({self.attrname!r} and {name!r})"
            )

    @t.overload
    def __get__(self, instance: None, owner: type[T]) -> Self: ...

    @t.overload
    def __get__(
        self, instance: T, owner: type[T]
    ) -> t.Callable[[str], MatplotlibFigures | None]: ...

    def __get__(
        self, instance: T | None, owner: type[T]
    ) -> Self | t.Callable[[str], MatplotlibFigures | None]:
        if instance is None:
            return self
        if self.attrname is None:
            raise TypeError(
                "cannot use renderer instance without calling __set_name__ on it"
            )
        if self.renderer is None:
            self.renderer = self._make_renderer(instance)
        return self.renderer.update


def render_generator(
    func: t.Callable[[T, Figure], None] | t.Callable[[T, Figure], RenderGenerator],
) -> _RenderDescriptor[T]:
    """Decorator wrapper for `FigureRenderer`.

    This is a wrapper around `FigureRenderer.from_callback()`. It
    automatically manages a `FigureRenderer` for you. Calling the
    decorated method will call `.update()` on that renderer instead.
    This keeps your :samp:`render()` implementation short and avoids
    duplicate code in your plotting logic.

    For a less magical interface, see the `FigureRenderer` class
    itself.

    Example::

        >>> import numpy as np
        >>> class Problem:
        ...     metadata = {
        ...         "render.modes": ["human", "matplotlib_figures"],
        ...     }
        ...
        ...     def __init__(self):
        ...         self.data = np.random.uniform(size=10)
        ...
        ...     def render(self, mode="human"):
        ...         if mode in self.metadata["render.modes"]:
        ...             # Manages a `FigureRenderer` in the background
        ...             # and actually calls `renderer.update(mode)`
        ...             # on it.
        ...             return self.update_figure(mode)
        ...         return super().render(mode)
        ...
        ...     @render_generator
        ...     def update_figure(self, fig):
        ...         # First iteration, initialize.
        ...         axes = fig.subplots()
        ...         [points] = axes.plot(self.data, "o")
        ...         print("initialized")
        ...         while True:
        ...             # First iteration is done, yield to the
        ...             # caller. We continue from here on the
        ...             # next `update()` call.
        ...             yield
        ...             # Update the plot, loop, and yield again.
        ...             points.set_ydata(self.data)
        ...             print("updated")
        >>> problem = Problem()
        >>> fig = problem.render("matplotlib_figures")
        initialized
        >>> fig = problem.render("matplotlib_figures")
        updated
        >>> # This is not <bound method Problem.update_figure>!
        >>> problem.update_figure
        <bound method FigureRenderer.update of <...>>
        >>> Problem.update_figure
        <..._RenderDescriptor object at ...>
    """
    return _RenderDescriptor(func)
