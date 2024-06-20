# SPDX-FileCopyrightText: 2020-2024 CERN
# SPDX-FileCopyrightText: 2023-2024 GSI Helmholtzzentrum für Schwerionenforschung
# SPDX-FileNotice: All rights not expressly granted are reserved.
#
# SPDX-License-Identifier: GPL-3.0-or-later OR EUPL-1.2+

"""Utilities for working with the Matplotlib."""

from __future__ import annotations

import sys
import typing as t

if t.TYPE_CHECKING:
    from matplotlib.figure import Figure

if sys.version_info < (3, 12):
    from typing_extensions import TypeAlias
else:
    from typing import TypeAlias


__all__ = (
    "MatplotlibFigures",
    "MaybeTitledFigure",
    "iter_matplotlib_figures",
)

MaybeTitledFigure: TypeAlias = t.Union["Figure", tuple[str, "Figure"]]
"""Helper annotation for `MatplotlibFigures`."""

MatplotlibFigures = t.Union[
    "Figure",
    t.Iterable[MaybeTitledFigure],
    t.Mapping[str, "Figure"],
]
"""Type of the return value of render mode :rmode:`"matplotlib_figures"`."""


def iter_matplotlib_figures(
    *figures: MatplotlibFigures,
) -> t.Iterator[tuple[str, Figure]]:
    """Handle result of render mode :rmode:`"matplotlib_figures"`.

    Problem authors are given a lot of freedom in what they return from
    :meth:`~cernml.coi.Problem.render()`. This method unifies all
    possible return types and produces one consistent iterator.

    Args:
        *figures: Each argument is the return value of
            a call to :meth:`~cernml.coi.Problem.render()` in render
            mode :rmode:`"matplotlib_figures"`.

    Yields:
        2-tuples :samp:`({title}, {figure})` for every item in
        *figures*. For any item without a *title*, the empty string is
        used.

    Note:
        Even though this function returns an iterator, it is *eager*:
        all arguments are evaluated immediately when this function is
        called. This ensures that rendering happens in a predictable,
        consistent manner.

    Examples:

        >>> class Figure:
        ...     def __repr__(self) -> str:
        ...         return "Figure()"
        ...
        >>> def print_matplotlib_figures(*figures):
        ...     for t, f in iter_matplotlib_figures(*figures):
        ...         print(f"{t!r}: {f!r}")
        ...
        >>> print_matplotlib_figures(Figure())
        '': Figure()
        >>> print_matplotlib_figures([
        ...     ["Foo", Figure()],
        ...     ("Bar", Figure()),
        ...     Figure(),
        ... ])
        'Foo': Figure()
        'Bar': Figure()
        '': Figure()
        >>> print_matplotlib_figures(Figure(), {"Foo": Figure()})
        '': Figure()
        'Foo': Figure()
    """
    # Run through all sub-iterators first, _then_ return the resulting
    # iterator. Otherwise, we might end up not updating all renderers
    # just because our caller didn't exhaust `results`.
    results: list[tuple[str, Figure]] = []
    for part in figures:
        results.extend(_iter(part))
    return iter(results)


def _iter(figures: MatplotlibFigures) -> t.Iterator[tuple[str, Figure]]:
    if hasattr(figures, "items"):
        yield from iter(t.cast(t.Mapping[str, "Figure"], figures).items())
        return
    try:
        iterator = iter(t.cast(t.Iterable, figures))
    except TypeError:
        # Not iterable, assume a single figure.
        yield "", t.cast("Figure", figures)
        return
    for item in iterator:
        # Unpack `item` if it is iterable. We avoid catching `TypeError`
        # because we are inside a loop and it would be eight times
        # slower. Make a special exception for strings (which are
        # iterable), since they would produce a confusing error message.
        if isinstance(item, str):
            raise TypeError(f"not a figure: {item!r}")
        if hasattr(item, "__iter__") or hasattr(item, "__getitem__"):
            title, figure = t.cast(tuple[str, "Figure"], item)
        else:
            title, figure = "", item
        yield title, figure
