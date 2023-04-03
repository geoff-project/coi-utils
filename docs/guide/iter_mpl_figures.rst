Receiving Figures from ``render()``
===================================

The render mode :meth:`"matplotlib_figures" <cernml.coi.Problem.render()>` can
return a variety of types:

- a single `~mpl:matplotlib.figure.Figure`;
- a mapping from `str` to figures;
- an iterable of bare figures or `str`–figure tuples or both.

The function `~cernml.mpl_utils.iter_matplotlib_figures()` condenses all of
these options into a single iterator:

.. code-block:: python

    >>> from itertools import count
    >>> from matplotlib.figure import Figure
    >>> from cernml.mpl_utils import iter_matplotlib_figures
    >>> def render():
    ...     return [
    ...         Figure(),
    ...         Figure(),
    ...         ("Named Figure", Figure()),
    ...     ]
    >>> c = count(1)
    >>> for title, figure in iter_matplotlib_figures(render()):
    ...     # Bare figures are assigned an empty string.
    ...     if not title:
    ...         title = f"Figure {next(c)}"
    ...     print(title, "--", figure)
    Figure 1 -- Figure(640x480)
    Figure 2 -- Figure(640x480)
    Named Figure -- Figure(640x480)
