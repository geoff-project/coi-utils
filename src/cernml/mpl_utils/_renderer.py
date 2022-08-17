"""Classes that make it easier to manage plotting state in COIs."""

from __future__ import annotations

import abc
import typing as t

from matplotlib import pyplot
from matplotlib.figure import Figure

from ._iter import iter_matplotlib_figures

if t.TYPE_CHECKING:  # pragma: no cover
    # pylint: disable = unused-import
    from ._iter import MatplotlibFigures

RenderGenerator = t.Generator[None, Figure, t.NoReturn]

RenderCallback = t.Union[
    t.Callable[[Figure], None],
    t.Callable[[Figure], "RenderGenerator"],
]


class Renderer(metaclass=abc.ABCMeta):
    """Interface for types that facilitate Matplotlib rendering.

    This is an abstract base class. You should use a concrete
    implementation, e.g. :class:`FigureRenderer`.
    """

    @staticmethod
    def make_figure(mode: str) -> Figure:
        """Create the correct kind of figure for the render mode.

        This creates a managed figure in the mode ``"human"`` and an
        unmanaged figure in the mode ``"matplotlib_figures"``.

        Raises:
            KeyError: if *mode* is neither of the two known render
                modes.
        """
        func = {"human": pyplot.figure, "matplotlib_figures": Figure}[mode]
        return func()

    @abc.abstractmethod
    def update(self, mode: str) -> t.Optional["MatplotlibFigures"]:
        """Update the renderer's figures and return them.

        On the first call, this should initialize the renderer's
        figures. On all subsequent calls, it should reuse the figures
        and update their contents.

        Args:
            mode: The render mode. This must be either ``"human"`` or
                ``"matplotlib_figures"``.

        Returns:
            None if the render mode is ``"human"``. Otherwise, a
            sequence of all figures managed by this renderer.
        """


class FigureRenderer(Renderer, metaclass=abc.ABCMeta):
    """Renderer that manages a single figure.

    Args:
        title: If passed, a figure title that is used in the return
            value of ``renderer.update("matplotlib_figures")``. Unused
            in other render modes. In particular, this does *not* add a
            title to the figure's contents. For this, consider using
            :meth:`~matplotlib.figure.Figure.suptitle()` instead.

    This is another abstract base class. There are three typical use
    cases:

    1. You pass a generator to :meth:`from_callback()`. On the first
       :meth:`update()` call, the generator is called to create an
       iterator. This iterator is polled on each
       :meth:`~Renderer.update()` call::

        >>> import numpy as np
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
        >>> problem = Problem()
        >>> fig = problem.render("matplotlib_figures")
        initialized
        >>> fig = problem.render("matplotlib_figures")
        updated

    2. You pass a function to :meth:`from_callback()`. This returns a
       subclass that calls this function on each
       :meth:`~Renderer.update()` call.

        >>> import numpy as np
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
        >>> problem = Problem()
        >>> fig = problem.render("matplotlib_figures")
        redrawn
        >>> fig = problem.render("matplotlib_figures")
        redrawn

    3. You inherit from this class and implement :meth:`_init_figure()`
       and :meth:`_update_figure()`, which get called by
       :meth:`~Renderer.update()` at the appropriate times.

        >>> import numpy as np
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
        >>> problem = Problem()
        >>> fig = problem.render("matplotlib_figures")
        initialized
        >>> fig = problem.render("matplotlib_figures")
        updated
    """

    def __init__(self, title: t.Optional[str] = None) -> None:
        self.figure: t.Optional[Figure] = None
        self._title = title

    def close(self) -> None:
        """Close the figure managed by this renderer.

        This only does anything if the figure has been created with
        render mode ``"human"``.
        """
        # Do not call ``pyplot.close(None)`` -- that closes the current
        # figure, as returned by ``pyplot.gcf()``, which might be
        # completely unrelated to us.
        # On the other hand, it's safe to close a figure that is not
        # managed by pyplot. This case is caught internally and nothing
        # happens.
        if self.figure is not None:
            pyplot.close(self.figure)

    def update(self, mode: str) -> t.Optional["MatplotlibFigures"]:
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

        This is called on the first call to :meth:`~Renderer.update()`,
        directly after instantiating the figure. It should create and
        fill items of the plot.
        """

    @abc.abstractmethod
    def _update_figure(self, figure: Figure) -> None:
        """Update the figure, reflecting any new data.

        This is called on every subsequent :meth:`~Renderer.update()`
        (but not on the first one). It should recreate or update the
        contents of the figure. Afterwards, :meth:`~Renderer.update()`
        will automatically display the figure to the user.
        """

    @staticmethod
    def from_callback(
        func: "RenderCallback", title: t.Optional[str] = None
    ) -> "FigureRenderer":
        """Create a renderer via a callback function or generator.

        Args:
            func: Either a regular function or a generator. If the
                former, it is called on every
                :meth:`~Renderer.update()`. If the latter, it is called
                once to create an iterator. The iterator is polled on
                every :meth:`~Renderer.update()`.
            title: If passed, a string to attach to the figure in the
                render mode ``"matplotlib_figures"``.

        Returns:
            An unspecified subclass of :class:`FigureRenderer`.
        """
        return _FigureFuncRenderer(func, title)


class _FigureFuncRenderer(FigureRenderer):
    """Return type of :meth:`FigureRenderer.from_callback()`."""

    def __init__(
        self,
        func: RenderCallback,
        title: t.Optional[str] = None,
    ) -> None:
        super().__init__(title)
        self._func = func
        self._generator: t.Optional[RenderGenerator] = None

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


class RendererGroup(Renderer, t.Tuple[Renderer, ...]):
    """A composite renderer that dispatches to multiple children.

    This is just a tuple of renderers that implements itself the
    :class:`Renderer` interface. Calling :meth:`~Renderer.update()`
    forwards the call to each child.

    Example::

        >>> class PrintRenderer(Renderer):
        ...     def __init__(self, index):
        ...         self.index = index
        ...     def update(self, mode):
        ...         print("Renderer", self.index, "updated")
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

    def update(self, mode: str = "human") -> t.Optional["MatplotlibFigures"]:
        if mode == "human":
            for renderer in self:
                renderer.update(mode)
            return None
        if mode == "matplotlib_figures":
            res: t.List[t.Tuple[str, Figure]] = []
            for renderer in self:
                res.extend(iter_matplotlib_figures(renderer.update(mode)))
            return res
        raise KeyError(mode)


def make_renderer(
    *funcs: t.Union[t.Mapping[str, "RenderCallback"], "RenderCallback"],
    squeeze: bool = True,
) -> Renderer:
    """Build a renderer from one or more callbacks.

    This is a convenience function that calls
    :meth:`FigureRenderer.from_callback` on each passed callback. There
    are three ways to calls this function:

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
    is always a :class:`RendererGroup` – even if only one callback is
    passed::

        >>> len(make_renderer(callback, squeeze=False))
        1
        >>> len(make_renderer({"foo": callback}, squeeze=False))
        1
    """
    renderers: t.List[Renderer] = []
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


T = t.TypeVar("T")  # pylint: disable=invalid-name


class render_generator(t.Generic[T]):
    """Decorator wrapper for :class:`FigureRenderer`.

    This is a wrapper around :meth:`FigureRenderer.from_callback()`. It
    automatically manages a :class:`FigureRenderer` for you. Calling the
    decorated method will call ``renderer.update()`` instead. This keeps
    your ``render()`` implementation short and avoids duplicate code in
    your plotting logic.

    For a less magical interface, see the :class:`FigureRenderer` class
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
        <mpl_utils...render_generator object at ...>
    """

    # pylint: disable = too-few-public-methods
    # pylint: disable = invalid-name

    def __init__(
        self,
        func: t.Union[
            t.Callable[[T, Figure], None],
            t.Callable[[T, Figure], RenderGenerator],
        ],
    ) -> None:
        self.func = func
        self.__doc__ = func.__doc__
        self.attrname: t.Optional[str] = None
        self.renderer: t.Optional[_FigureFuncRenderer] = None

    def _make_renderer(self, instance: T) -> _FigureFuncRenderer:
        def iter_func_call(fig: Figure) -> t.Optional[RenderGenerator]:
            return self.func(instance, fig)

        return _FigureFuncRenderer(t.cast(RenderCallback, iter_func_call))

    def __set_name__(self, owner: t.Type[T], name: str) -> None:
        if self.attrname is None:
            self.attrname = name
        elif name != self.attrname:
            raise TypeError(
                f"cannot assign the samer renderer to two different "
                f"names ({self.attrname!r} and {name!r})"
            )

    @t.overload
    def __get__(self, instance: None, owner: t.Type[T]) -> render_generator[T]:
        ...  # pragma: no cover

    @t.overload
    def __get__(
        self, instance: T, owner: t.Type[T]
    ) -> t.Callable[[str], t.Optional["MatplotlibFigures"]]:
        ...  # pragma: no cover

    def __get__(
        self, instance: t.Optional[T], owner: t.Type[T]
    ) -> t.Union[
        render_generator[T], t.Callable[[str], t.Optional["MatplotlibFigures"]]
    ]:
        if instance is None:
            return self
        if self.attrname is None:
            raise TypeError(
                "cannot use renderer instance without calling __set_name__ on it"
            )
        if self.renderer is None:
            self.renderer = self._make_renderer(instance)
        return self.renderer.update
