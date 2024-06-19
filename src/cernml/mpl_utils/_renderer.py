# SPDX-FileCopyrightText: 2020-2024 CERN
# SPDX-FileCopyrightText: 2023-2024 GSI Helmholtzzentrum für Schwerionenforschung
# SPDX-FileNotice: All rights not expressly granted are reserved.
#
# SPDX-License-Identifier: GPL-3.0-or-later OR EUPL-1.2+

"""Classes that make it easier to manage plotting state in COIs."""

from __future__ import annotations

import sys
import typing as t
from abc import abstractmethod
from functools import partial

from ._iter import MatplotlibFigures, iter_matplotlib_figures
from ._strategies import FigureStrategy, HumanStrategy, MatplotlibFiguresStrategy

if t.TYPE_CHECKING:
    from matplotlib.figure import Figure

    from cernml.coi.protocols import Problem

if sys.version_info < (3, 12):
    from typing_extensions import Self, TypeAlias, override
else:
    from typing import Self, TypeAlias, override


__all__ = (
    "AbstractRenderer",
    "FigureRenderer",
    "InconsistentRenderModeError",
    "RenderCallback",
    "RenderGenerator",
    "Renderer",
    "RendererGroup",
    "make_renderer",
    "render_generator",
)


RenderGenerator: TypeAlias = t.Generator[None, "Figure", t.NoReturn]
RenderCallback: TypeAlias = t.Union[
    t.Callable[["Figure"], None],
    t.Callable[["Figure"], RenderGenerator],
]


@t.runtime_checkable
class AbstractRenderer(t.Protocol):
    """Base protocol of all renderers.

    This has been split out of `Renderer` and encapsulates the pure
    behavior of renderers, with none of the attributes. This is
    necessary for `RendererGroup`, which does not contain a `.strategy`
    of its own.
    """

    __slots__ = ()

    @abstractmethod
    def update(self) -> MatplotlibFigures | None:
        """Update the renderer's figures and return them.

        On the first call, this should initialize the renderer's
        figures. On all subsequent calls, it should reuse the figures
        and update their contents.

        Returns:
            None if the render mode is :rmode:`"human"`. Otherwise,
            a sequence of all figures managed by this renderer.
        """


class Renderer(AbstractRenderer):
    """Interface for types that facilitate Matplotlib rendering.

    This is an :term:`abstract base class`. You should use a concrete
    implementation, e.g. `FigureRenderer`.

    Args:
        render_mode: The render mode. Should be None or :rmode:`"human"`
            or :rmode:`"matplotlib_figures"`.
    """

    __slots__ = ("strategy",)

    strategy: FigureStrategy | None
    """The strategy_ to interact with the `~matplotlib.figure.Figure`
    object. Usually this is either `HumanStrategy` or
    `MatplotlibFiguresStrategy`, but users can supply their own
    implementation.

    .. _strategy: https://en.wikipedia.org/wiki/Strategy_pattern
    """

    KNOWN_STRATEGIES: t.ClassVar[dict[str, FigureStrategy]] = {
        "human": HumanStrategy(),
        "matplotlib_figures": MatplotlibFiguresStrategy(),
    }
    """Translation table from render mode to `strategy`. If you
    want to define a custom render mode, insert it into this global
    mapping."""

    def __init__(self, render_mode: str | None) -> None:
        if isinstance(render_mode, FigureStrategy) or render_mode is None:
            self.strategy = render_mode
        else:
            self.strategy = self.KNOWN_STRATEGIES[render_mode]


class FigureRenderer(Renderer):
    """Renderer that manages a single figure.

    Args:
        title: If passed, a figure title that is used in the return
            value of ``renderer.update("matplotlib_figures")``. Unused
            in other render modes. In particular, this does *not* add a
            title to the figure's contents. For this, use
            :meth:`~matplotlib.figure.Figure.suptitle()` instead.
        render_mode: The render mode. Should be None or :rmode:`"human"`
            or :rmode:`"matplotlib_figures"`. See also Strategies_.

    This is another :term:`abstract base class`. There are three typical
    use cases:

    1. You pass a :term:`generator` to `from_callback()`. On the first
       `~Renderer.update()` call, the generator is called to create an
       :term:`iterator`. This iterator is polled on each
       `~Renderer.update()` call::

        >>> import numpy as np
        >>> from cernml import coi
        ...
        >>> class Problem(coi.Problem):
        ...     metadata = {"render_modes": ["matplotlib_figures"]}
        ...
        ...     def __init__(self, render_mode=None):
        ...         super().__init__(render_mode)
        ...         self.data = np.random.uniform(size=10)
        ...         self.renderer = FigureRenderer.from_callback(
        ...             self._iter_updates, render_mode=render_mode
        ...         )
        ...
        ...     def render(self):
        ...         if self.render_mode in self.metadata["render_modes"]:
        ...             return self.renderer.update()
        ...         return super().render()
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
        >>> problem = Problem("matplotlib_figures")
        >>> fig = problem.render()
        initialized
        >>> fig = problem.render()
        updated

    2. You pass a function to `from_callback()`. This returns a
       subclass that calls this function on each
       `~Renderer.update()` call.

        >>> import numpy as np
        >>> from cernml import coi
        ...
        >>> class Problem(coi.Problem):
        ...     metadata = {"render_modes": ["matplotlib_figures"]}
        ...
        ...     def __init__(self, render_mode=None):
        ...         super().__init__(render_mode)
        ...         self.data = np.random.uniform(size=10)
        ...         self.renderer = FigureRenderer.from_callback(
        ...             self._update_figure, render_mode=render_mode
        ...         )
        ...
        ...     def render(self):
        ...         if self.render_mode in self.metadata["render_modes"]:
        ...             return self.renderer.update()
        ...         return super().render()
        ...
        ...     def _update_figure(self, fig):
        ...         # Grab or create a subplot.
        ...         [axes] = fig.axes or [fig.subplots()]
        ...         # Clear and redraw from scratch on each turn.
        ...         axes.clear()
        ...         axes.plot(self.data, "o")
        ...         print("redrawn")
        ...
        >>> problem = Problem("matplotlib_figures")
        >>> fig = problem.render()
        redrawn
        >>> fig = problem.render()
        redrawn

    3. You inherit from this class and implement `_init_figure()`
       and `_update_figure()`, which get called by
       `~Renderer.update()` at the appropriate times.

        >>> import numpy as np
        >>> from cernml import coi
        ...
        >>> class ProblemRenderer(FigureRenderer):
        ...     def __init__(self, problem, render_mode):
        ...         super().__init__(render_mode=render_mode)
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
        >>> class Problem(coi.Problem):
        ...     metadata = {"render_modes": ["matplotlib_figures"]}
        ...
        ...     def __init__(self, render_mode=None):
        ...         super().__init__(render_mode)
        ...         self.data = np.random.uniform(size=10)
        ...         self.renderer = ProblemRenderer(self, render_mode)
        ...
        ...     def render(self, mode="human"):
        ...         if self.render_mode in self.metadata["render_modes"]:
        ...             return self.renderer.update()
        ...         return super().render()
        ...
        >>> problem = Problem("matplotlib_figures")
        >>> fig = problem.render()
        initialized
        >>> fig = problem.render()
        updated
    """

    __slots__ = ("title", "figure")

    title: str | None
    """The figure title passed to `__init__ <FigureRenderer>`."""

    figure: Figure | None
    """The figure managed by this renderer. This is initialized on the
    first call to `update()`, unless the render mode is None; in that
    case, this attribute is always `None`."""

    def __init__(self, title: str | None = None, *, render_mode: str | None) -> None:
        super().__init__(render_mode)
        self.title = title
        self.figure: Figure | None = None

    def close(self) -> None:
        """Close the figure managed by this renderer.

        Unless the render mode is :rmode:`"human"` (and figures are
        managed by Matplotlib), this does nothing.
        """
        figure, self.figure = self.figure, None
        if figure is not None and self.strategy is not None:
            self.strategy.close_figure(figure)

    @override
    def update(self) -> MatplotlibFigures | None:
        try:
            figure = self.figure
        except AttributeError:
            raise TypeError("super().__init__() not called") from None
        if (strategy := self.strategy) is None:
            return None
        if figure is None:
            figure = self.figure = strategy.make_figure(self.title)
            self._init_figure(figure)
        else:
            self._update_figure(figure)
        return strategy.update_figure(figure)

    @abstractmethod
    def _init_figure(self, figure: Figure) -> None:
        """Initialize the figure.

        This is called on the first call to `.update()`, directly after
        instantiating the figure. It should create and fill items of the
        plot.
        """

    @abstractmethod
    def _update_figure(self, figure: Figure) -> None:
        """Update the figure, reflecting any new data.

        This is called on every subsequent `.update()` (but not on the
        first one). It should recreate or update the contents of the
        figure. Afterwards, `.update()` will automatically display the
        figure to the user.
        """

    @staticmethod
    def from_callback(
        func: RenderCallback, title: str | None = None, *, render_mode: str | None
    ) -> FigureRenderer:
        """Create a renderer via a callback function or generator.

        Args:
            func: Either a regular function or a generator. If the
                former, it is called on every `.update()`. If the
                latter, it is called once to create an :term:`iterator`.
                The iterator is polled on every `.update()`.
            title: If passed, a string to attach to the figure in the
                render mode :rmode:`"matplotlib_figures"`.
            render_mode: The render mode. Should be None or
                :rmode:`"human"` or :rmode:`"matplotlib_figures"`. See
                also Strategies_.

        Returns:
            An unspecified subclass of `FigureRenderer`.
        """
        return _FigureFuncRenderer(func, title, render_mode=render_mode)


class _FigureFuncRenderer(FigureRenderer):
    """Return type of `FigureRenderer.from_callback()`."""

    __slots__ = ("func", "_generator")

    func: RenderCallback
    """The callback passed to the constructor."""

    def __init__(
        self, func: RenderCallback, title: str | None = None, *, render_mode: str | None
    ) -> None:
        super().__init__(title, render_mode=render_mode)
        self.func = func
        self._generator: RenderGenerator | None = None

    def __repr__(self) -> str:
        if self.title is not None:
            return f"<{type(self).__name__}({self.func!r}, {self.title!r})>"
        return f"<{type(self).__name__}({self.func!r})>"

    @override
    def _init_figure(self, figure: Figure) -> None:
        generator = self.func(figure)
        if generator is not None:
            self._generator = generator
            next(generator)

    @override
    def _update_figure(self, figure: Figure) -> None:
        if self._generator is not None:
            self._generator.send(figure)
        else:
            self.func(figure)


class RendererGroup(AbstractRenderer, tuple[AbstractRenderer, ...]):
    """A composite renderer that dispatches to multiple elements.

    This is just a tuple of renderers that implements itself the
    `AbstractRenderer` interface. Calling `.update()` forwards the call
    to each element renderer.

    Example::

        >>> class PrintRenderer(Renderer):
        ...     def __init__(self, index):
        ...         self.index = index
        ...     def update(self):
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

    Note:
        Because a renderer group does not manage or know the render
        mode, it has to guess it based on the return type of the element
        renderers. It assumes :rmode:`"human"` if they return `None` and
        :rmode:`"matplotlib_figures"` otherwise.

        An empty group always assumed :rmode:`"matplotlib_figures"` and
        returns an empty list, which is the safer option.
    """

    __slots__ = ()

    def update(self) -> MatplotlibFigures | None:
        """Update all element renderers.

        Returns:
            None if all element renderers return None. A list of figures
            and title–figure tuples if all element renderers return
            figures. An empty group always returns an empty list.

        Raises:
            InconsistentRenderModeError: If some but not all element
                renderers return None. This indicates that the renderers
                have conflicting render modes.
        """
        all_figures: list[tuple[str, Figure]] = []
        any_none = False
        for renderer in self:
            figures = renderer.update()
            if figures is None:
                if all_figures:
                    raise InconsistentRenderModeError(all_figures)
                any_none = True
            elif any_none:
                raise InconsistentRenderModeError(figures)
            else:
                all_figures.extend(iter_matplotlib_figures(figures))
        if any_none:
            return None
        return all_figures


class InconsistentRenderModeError(RuntimeError):
    """A `RendererGroup` contains renderers with conflicting render modes."""

    def __init__(self, figures: MatplotlibFigures, *args: object) -> None:
        msg = (
            f"renderers with conflicting render mode; "
            f"received None and also {figures!r}"
        )
        super().__init__(msg, *args)


def make_renderer(
    *funcs: RenderCallback | t.Mapping[str, RenderCallback],
    squeeze: bool = True,
    render_mode: str | None,
) -> AbstractRenderer:
    """Build a renderer from one or more callbacks.

    This is a convenience function that calls
    `FigureRenderer.from_callback()` on each passed callback. There are
    three ways to calls this function:

    1. With a single callback function or generator::

        >>> def callback(fig): ...
        ...
        >>> make_renderer(callback, render_mode=None)
        <_FigureFuncRenderer(<function callback at ...>)>

    2. With multiple callbacks::

        >>> g = make_renderer(callback, callback, render_mode=None)
        >>> type(g).__name__
        'RendererGroup'
        >>> isinstance(g, tuple)
        True
        >>> len(g)
        2

    3. With a mapping from strings to callbacks. The strings are used as
       titles in this case::

        >>> make_renderer({"Figure 1": callback}, render_mode=None)
        <_FigureFuncRenderer(<function callback at ...>, 'Figure 1')>
        >>> g = make_renderer(
        ...     {"foo": callback, "bar": callback},
        ...     render_mode=None,
        ... )
        >>> len(g)
        2

    If the optional argument *squeeze* is passed and False, the result
    is always a `RendererGroup` – even if only one callback is
    passed::

        >>> len(make_renderer(callback, squeeze=False, render_mode=None))
        1
        >>> len(make_renderer(
        ...     {"foo": callback}, squeeze=False, render_mode=None
        ... ))
        1
    """
    renderers: list[Renderer] = []
    for func_or_mapping in funcs:
        if isinstance(func_or_mapping, t.Mapping):
            renderers.extend(
                _FigureFuncRenderer(func, title, render_mode=render_mode)
                for title, func in func_or_mapping.items()
            )
        else:
            renderers.append(
                _FigureFuncRenderer(func_or_mapping, render_mode=render_mode)
            )
    if squeeze and len(renderers) == 1:
        return renderers[0]
    return RendererGroup(renderers)


T = t.TypeVar("T", bound="Problem")


class _RenderDescriptor(t.Generic[T]):
    """The return type of `render_generator`."""

    def __init__(
        self,
        func: t.Callable[[T, Figure], None] | t.Callable[[T, Figure], RenderGenerator],
        title: str | None = None,
    ) -> None:
        self.func = func
        self.title = title
        self.__doc__ = func.__doc__
        self.attrname: str | None = None
        self.renderer: _FigureFuncRenderer | None = None

    def _make_renderer(self, instance: T, owner: type[T]) -> _FigureFuncRenderer:
        @t.overload
        def partial_(
            f: t.Callable[[T, Figure], None],
        ) -> t.Callable[[Figure], None]: ...
        @t.overload
        def partial_(
            f: t.Callable[[T, Figure], RenderGenerator],
        ) -> t.Callable[[Figure], RenderGenerator]: ...
        def partial_(
            f: t.Callable[[T, Figure], RenderGenerator | None],
        ) -> t.Callable[[Figure], RenderGenerator | None]:
            return f.__get__(instance, owner)

        try:
            render_mode = instance.render_mode
        except AttributeError as exc:
            raise AttributeError(
                f"missing attribute `render_mode` in `Problem` instance: {instance!r}"
            ) from exc
        return _FigureFuncRenderer(
            partial_(self.func), title=self.title, render_mode=render_mode
        )

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
    ) -> t.Callable[[], MatplotlibFigures | None]: ...

    def __get__(
        self, instance: T | None, owner: type[T]
    ) -> Self | t.Callable[[], MatplotlibFigures | None]:
        if instance is None:
            return self
        if self.attrname is None:
            raise TypeError(
                "cannot use renderer instance without calling __set_name__ on it"
            )
        if self.renderer is None:
            self.renderer = self._make_renderer(instance, owner)
        return self.renderer.update


UnboundRenderCallback: TypeAlias = t.Union[
    t.Callable[[T, "Figure"], None], t.Callable[[T, "Figure"], RenderGenerator]
]


@t.overload
def render_generator(func: UnboundRenderCallback[T], /) -> _RenderDescriptor[T]: ...


@t.overload
def render_generator(
    title: str | None = None, /
) -> t.Callable[[UnboundRenderCallback[T]], _RenderDescriptor[T]]: ...


def render_generator(
    title: UnboundRenderCallback[T] | str | None = None, /
) -> (
    _RenderDescriptor[T] | t.Callable[[UnboundRenderCallback[T]], _RenderDescriptor[T]]
):
    """Decorator wrapper for `FigureRenderer.from_callback()`.

    This decorator automatically manages a `FigureRenderer` for you.
    Calling the decorated method will instead call `.update()` on that
    renderer. This keeps your :samp:`render()` implementation short and
    avoids duplicate code in your plotting logic.

    Example use::

        >>> from cernml import coi
        ...
        >>> class Problem(coi.Problem):
        ...     ...
        ...
        ...     @render_generator
        ...     def update_fig1(self, fig: Figure) -> None:
        ...         ...
        ...
        ...     @render_generator("Title of Figure 2")
        ...     def update_fig2(self, fig: Figure) -> RenderGenerator:
        ...         ...
        ...
    """
    # Note: This documentation is shorter than usual. Because this
    # function uses typing.overload, we cannot customize its signature
    # for the API docs. Thus we avoid `autodectorator` and document it
    # manually. See <https://github.com/sphinx-doc/sphinx/issues/10351>
    if callable(title):
        return _RenderDescriptor(func=title, title=None)
    return partial(_RenderDescriptor, title=title)
