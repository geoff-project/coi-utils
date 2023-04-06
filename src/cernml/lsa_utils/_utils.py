"""Functional interface for `Incorporator`."""

from __future__ import annotations

import typing as t
from numbers import Real

import java.lang
import numpy as np
from cern.accsoft.commons.value import ValueFactory
from cern.lsa.domain.settings import TrimRequest

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


@t.overload
def incorporate_and_trim(
    parameter_name: str,
    context: str,
    cycle_time: float,
    value: float,
    *,
    relative: bool,
    description: t.Optional[str] = None,
) -> None:
    ...  # pragma: no cover


@t.overload
def incorporate_and_trim(
    parameter_name: t.List[str],
    context: str,
    cycle_time: float,
    value: t.Union[np.ndarray, t.Sequence[float]],
    *,
    relative: bool,
    description: t.Optional[str] = None,
) -> None:
    ...  # pragma: no cover


def incorporate_and_trim(
    parameter_name: t.Union[str, t.List[str]],
    context: str,
    cycle_time: float,
    value: t.Union[float, np.ndarray, t.Sequence[float]],
    *,
    relative: bool,
    description: t.Optional[str] = None,
) -> None:
    """Modify a function or functions at a point and commit the change.

    This assumes that each parameter is a scalar function. It modifies
    the functions' *correction* at a given point in time and submits
    this modification to the LSA database. The *target* remains
    unmodified.

    Args:
        parameter_name: The name of the parameter whose function is to
            be modified. This may be a list of names to trim several
            functions at once.
        context: The context in which the parameter is modified. In
            cycling machines like the SPS, this is the cycle; in
            cycle-less machines like the LHC, this is the beam process.
        cycle_time: The point at which the function shall be modified.
            This is measured in milliseconds from the beginning of the
            cycle. Only those points may be chosen for which there is an
            incorporation rule in the LSA database.
        value: The correction value to be transmitted. How this value is
            incorporated depends on the  keyword-only argument
            *relative*. If *parameter_name* is a string, this is a
            single float. If *parameter_name* is a list of strings, this
            should be an array or list of the same length.
        relative: If True, *value* is added to the correction of the
            function at the given time. If False, the correction is set
            to *value*, overwriting the previous correction at the given
            time.
        description: The description to appear in LSA's trim history. If
            not passed, an implementation-defined string will be used.
    """
    if isinstance(parameter_name, str):
        _incorporator.Incorporator(
            parameter_name, context=context
        ).incorporate_and_trim(
            cycle_time, t.cast(float, value), relative=relative, description=description
        )
    else:
        _incorporator.IncorporatorGroup(
            parameter_name, context=context
        ).incorporate_and_trim(
            cycle_time, value, relative=relative, description=description
        )


def trim_scalar_settings(
    settings: t.Dict[str, t.Union[Real, str]],
    *,
    user: t.Optional[str] = None,
    context: t.Optional[str] = None,
    relative: bool = False,
    description: t.Optional[str] = None,
) -> None:
    """Trim multiple scalar settings at once.

    This modifies multiple database settings in a single transaction. If
    any of them fails, none are applied at all. The settings must be
    *scalars*, i.e. either numbers or enums or strings.

    Args:
        settings: The settings to send to the database. This is a
            mapping from parameter names to the new values. Python
            integers are automatically converted to `~jpype.JLong`,
            floats to `~jpype.JDouble`, strings to `~jpype.JString`.
            NumPy single-precision floats `numpy.float32` are converted
            to `~jpype.JFloat`.
        context: If passed, the context in which the parameters are
            modified. In cycling machines like the SPS, this is the
            cycle; in cycle-less machines like the LHC, this is the beam
            process. Must not be passed together with *user*.
        user: If passed, the user for which the parameters are modified.
            Must not be passed together with *context*.
        relative: If True, each passed value is added to the value in
            the database. The default is to overwrite the database value
            with the new one.
        description: The description to appear in LSA's trim history. If
            not passed, an implementation-defined string will be used.
    """
    cycle = _incorporator.find_cycle(context=context, user=user)
    trim = TrimRequest.builder()
    trim.setContext(cycle)
    for parameter_name, value in settings.items():
        scalar = java.lang.Object @ value  # type: ignore[operator]
        trim.addScalar(
            _services.parameter.findParameterByName(parameter_name),
            ValueFactory.createScalar(scalar),
        )
    trim.setRelative(relative)
    trim.setDescription(description or _incorporator.DEFAULT_TRIM_DESCRIPTION)
    _services.trim.trimSettings(trim.build())
