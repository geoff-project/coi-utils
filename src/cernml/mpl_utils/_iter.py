# SPDX-FileCopyrightText: 2020-2023 CERN
# SPDX-FileCopyrightText: 2023 GSI Helmholtzzentrum für Schwerionenforschung
# SPDX-FileNotice: All rights not expressly granted are reserved.
#
# SPDX-License-Identifier: GPL-3.0-or-later OR EUPL-1.2+

"""Utilities for working with the Matplotlib."""

from __future__ import annotations

import typing as t

from matplotlib.figure import Figure

MaybeTitledFigure = t.Union[Figure, t.Tuple[str, Figure]]
"""Helper annotation for `MatplotlibFigures`."""

MatplotlibFigures = t.Union[
    Figure,
    t.Iterable[MaybeTitledFigure],
    t.Mapping[str, Figure],
]
"""Type of the return value of render mode ``"matplotlib_figures"``."""


def iter_matplotlib_figures(
    figures: "MatplotlibFigures",
) -> t.Iterator[t.Tuple[str, Figure]]:
    """Handle result of render mode ``"matplotlib_figures"``.

    Problem authors are given a lot of freedom in what they return from
    :meth:`~cernml.coi.Problem.render()`. This method unifies all
    possible return types and produces one consistent iterator.

    Args:
        figures: The :class:`return value <MatplotlibFigures>` of
            :meth:`render("matplotlib_figures")
            <cernml.coi.Problem.render()>`.

    Yields:
        A 2-tuple of a title and a figure for every item in *figures*.
        If a figure doesn't have a title, the empty string is used.

    Examples:

        >>> class Figure:
        ...     def __repr__(self) -> str:
        ...         return "Figure()"
        ...
        >>> def print_matplotlib_figures(figures):
        ...     for t, f in iter_matplotlib_figures(figures):
        ...         print(f"{t!r}: {f!r}")
        ...
        >>> # A single figure:
        >>> print_matplotlib_figures(Figure())
        '': Figure()
        >>> # Lists of figures:
        >>> print_matplotlib_figures([Figure(), Figure()])
        '': Figure()
        '': Figure()
        >>> # Arbitrary iterables of figures:
        >>> print_matplotlib_figures(Figure() for _ in range(3))
        '': Figure()
        '': Figure()
        '': Figure()
        >>> # Lists of title-figure tuples OR figures:
        >>> print_matplotlib_figures([
        ...     ["Foo", Figure()],
        ...     ("Bar", Figure()),
        ...     Figure(),
        ... ])
        'Foo': Figure()
        'Bar': Figure()
        '': Figure()
        >>> # Mappings from titles to figures:
        >>> print_matplotlib_figures({"Foo": Figure(), "Bar": Figure()})
        'Foo': Figure()
        'Bar': Figure()
        >>> # We get a clear error message if a string is passed.
        >>> print_matplotlib_figures(("not_a_title", Figure()))
        Traceback (most recent call last):
        ...
        TypeError: not a figure: 'not_a_title'
    """
    if hasattr(figures, "items"):
        yield from iter(t.cast(t.Mapping[str, Figure], figures).items())
        return
    try:
        iterator = iter(figures)
    except TypeError:
        # Not iterable, assume a single figure.
        yield "", t.cast(Figure, figures)
        return
    for item in iterator:
        # Unpack `item` if it is iterable. We avoid catching `TypeError`
        # because we are inside a loop and it would be eight times
        # slower. Make a special exception for strings (which are
        # iterable), since they would produce a confusing error message.
        if isinstance(item, str):
            raise TypeError(f"not a figure: {item!r}")
        if hasattr(item, "__iter__") or hasattr(item, "__getitem__"):
            title, figure = t.cast(t.Tuple[str, Figure], item)
        else:
            title, figure = "", item
        yield title, figure
