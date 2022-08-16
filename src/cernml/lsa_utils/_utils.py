"""Functional interface for :class:`Incorporator` plus some other small functions."""

from __future__ import annotations

import typing as t

import java.lang
import numpy as np

from . import _incorporator, _services


def get_settings_function(
    parameter: str, context: str
) -> t.Tuple[np.ndarray, np.ndarray]:
    """Query the settings function for a given parameter and context.

    This returns the function as a 2-tuple of times and values, each an
    1D array of equal length.
    """
    return _incorporator.Incorporator(parameter, context=context).get_function()


def get_context_by_user(user: str) -> str:
    """Look up the name of the context that belongs to the user."""
    try:
        cycle = _services.context.findStandAloneContextByUser(user)
    except java.lang.IllegalArgumentException:  # type: ignore
        raise _incorporator.NotFound(user) from None
    return cycle.getName()


def get_cycle_type_attributes(context: str) -> t.Dict[str, str]:
    """Look up the cycle type attributes associated with a context."""
    cycle = _services.context.findStandAloneCycle(context)
    if cycle is None:
        raise _incorporator.NotFound(context)
    cycle_type = _services.generation.findCycleType(cycle.getTypeName())
    # The cycle type must exist because we got the name from a cycle.
    assert cycle_type is not None
    return {attr.getName(): attr.getValue() for attr in cycle_type.getAttributes()}


def incorporate_and_trim(
    parameter_name: str,
    context: str,
    cycle_time: float,
    value: float,
    *,
    relative: bool,
    description: t.Optional[str] = None,
) -> None:
    """Modify the function at a point and commit the change.

    This assumes that the parameter is a scalar function. It modifies
    the its *correction* at a given point in time and submits this
    modification to the LSA database. The *target* remains unmodified.

    Args:
        parameter_name: The name of the parameter whose function is to
            be modified.
        context: The context in which the parameter is modified. In
            cycling machines like the SPS, this is the cycle; in
            cycle-less machines like the LHC, this is the beam process.
        cycle_time: The point at which the function shall be modified.
            This is measured in milliseconds from the beginning of the
            cycle. Only those points may be chosen for which there is an
            incorporation rule in the LSA database.
        value: The correction value to be transmitted. How this value is
            incorporated depends on the  keyword-only argument
            *relative*.
        relative: If True, *value* is added to the correction of the
            function at the given time. If False, the correction is set
            to *value*, overwriting the previous correction at the given
            time.
        description: The description to appear in LSA's trim history. If
            not passed, an implementation-defined string will be used.
    """
    _incorporator.Incorporator(parameter_name, context=context).incorporate_and_trim(
        cycle_time, value, relative=relative, description=description
    )
