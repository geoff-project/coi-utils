Matplotlib Utilities
====================

.. automodule:: cernml.mpl_utils

    .. autofunction:: iter_matplotlib_figures
    .. autofunction:: make_renderer
    .. autoclass:: Renderer
        :show-inheritance:
        :members:
    .. autoclass:: FigureRenderer
        :show-inheritance:
        :members: close, from_callback, _init_figure, _update_figure
    .. autoclass:: RendererGroup
        :show-inheritance: tuple
    .. autodecorator:: render_generator

    ..
        Manual annotation of the type aliases; If we used any of the auto
        directives, these would be annotated as `:py:data:` (by virtue of being
        module-scope variables, not true classes). This, in turn, confuses the
        autodoc signature handler, which expects to link to a `:py:class:`.

        Manually annotating these as classes is the easiest way to circumvent
        this mess.

    .. class:: cernml.mpl_utils.MatplotlibFigures

        alias of :class:`~matplotlib.figure.Figure` |
        :class:`~typing.Iterable`\[:class:`~cernml.mpl_utils.MaybeTitledFigure`] |
        :class:`~typing.Mapping`\[:class:`str`, :class:`~matplotlib.figure.Figure`]

    .. class:: cernml.mpl_utils.MaybeTitledFigure

        alias of :class:`~matplotlib.figure.Figure` |
        :data:`~typing.Tuple`\[:class:`str`, :class:`~matplotlib.figure.Figure`]

    .. class:: cernml.mpl_utils.RenderGenerator

        alias of :class:`~typing.Generator`\[:data:`None`,
        :class:`~matplotlib.figure.Figure`, :data:`~typing.NoReturn`]

    .. class:: cernml.mpl_utils.RenderCallback

        alias of :data:`~typing.Callable`\[[:class:`~matplotlib.figure.Figure`],
        :data:`None`] |
        :data:`~typing.Callable`\[[:class:`~matplotlib.figure.Figure`],
        :class:`~cernml.mpl_utils.RenderGenerator`]]
