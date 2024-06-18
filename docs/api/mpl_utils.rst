..
    SPDX-FileCopyrightText: 2020-2024 CERN
    SPDX-FileCopyrightText: 2023-2024 GSI Helmholtzzentrum für Schwerionenforschung
    SPDX-FileNotice: All rights not expressly granted are reserved.

    SPDX-License-Identifier: GPL-3.0-or-later OR EUPL-1.2+

Matplotlib Utilities
====================

.. currentmodule:: cernml.mpl_utils

.. seealso::

    :doc:`/guide/iter_mpl_figures`
        User guide page on `iter_matplotlib_figures()`.
    :doc:`/guide/renderer`
        User guide page on renderers.

.. automodule:: cernml.mpl_utils

    .. autofunction:: iter_matplotlib_figures
    .. autofunction:: make_renderer
    .. autodecorator:: render_generator()

Class-based Interface
---------------------

.. autoclass:: Renderer
    :show-inheritance:
    :members:
    :exclude-members: strategy, KNOWN_STRATEGIES, update

    .. autoattribute:: strategy

    .. autoattribute:: KNOWN_STRATEGIES
        :no-value:

    .. automethod:: update

.. autoclass:: FigureRenderer
    :show-inheritance:
    :members: close, from_callback, _init_figure, _update_figure

.. autoclass:: RendererGroup
    :show-inheritance: tuple

.. autoclass:: AbstractRenderer
    :show-inheritance:

    .. automethod:: update
        :no-index:

..
    Manual annotation of the type aliases; If we used any of the auto
    directives, these would be annotated as ``py:data`` (by virtue of being
    module-scope variables, not true classes). This, in turn, confuses the
    autodoc signature handler, which expects to link to a ``py:class``.

    Manually annotating these as classes is the easiest way to circumvent
    this mess.

.. class:: cernml.mpl_utils.MatplotlibFigures

    alias of `~matplotlib.figure.Figure` |
    `~typing.Iterable`\[`~cernml.mpl_utils.MaybeTitledFigure`] |
    `~typing.Mapping`\[`str`, `~matplotlib.figure.Figure`]

.. class:: cernml.mpl_utils.MaybeTitledFigure

    alias of `~matplotlib.figure.Figure` |
    `~typing.Tuple`\[`str`, `~matplotlib.figure.Figure`]

.. class:: cernml.mpl_utils.RenderGenerator

    alias of `~typing.Generator`\[`None`,
    `~matplotlib.figure.Figure`, `~typing.NoReturn`]

.. class:: cernml.mpl_utils.RenderCallback

    alias of `~typing.Callable`\[[`~matplotlib.figure.Figure`], `None`] |
    `~typing.Callable`\[[`~matplotlib.figure.Figure`],
    `~cernml.mpl_utils.RenderGenerator`]]

Strategies
----------

.. autoclass:: FigureStrategy
.. autoclass:: HumanStrategy
.. autoclass:: MatplotlibFiguresStrategy
