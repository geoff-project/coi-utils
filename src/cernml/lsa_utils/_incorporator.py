# SPDX-FileCopyrightText: 2020-2024 CERN
# SPDX-FileCopyrightText: 2023-2024 GSI Helmholtzzentrum für Schwerionenforschung
# SPDX-FileNotice: All rights not expressly granted are reserved.
#
# SPDX-License-Identifier: GPL-3.0-or-later OR EUPL-1.2+

"""Provide `Incorporator` and `IncorporatorGroup`."""

from __future__ import annotations

import typing as t

import cern.accsoft.commons as acc
import cern.lsa.domain.settings as lsa
import java.util
import numpy as np

from . import _hooks, _services

__all__ = (
    "DEFAULT_TRIM_DESCRIPTION",
    "Incorporator",
    "IncorporatorGroup",
    "NotFound",
    "find_cycle",
    "find_parameter",
)

DEFAULT_TRIM_DESCRIPTION = "Via COI"


class NotFound(Exception):
    """The parameter, user or context was not found in the database."""


class Incorporator:
    """Class that allows changing one function-type parameter.

    This is the object-oriented alternative to the module-scope
    functions. It is slightly more reusable in that it allows caching
    the lookup of parameter and cycle.

    Args:
        parameter: The name of the parameter into which changes are to
            be incorporated.
        context: If passed, the context in which the parameter is
            modified. In cycling machines like the SPS, this is the
            cycle; in cycle-less machines like the LHC, this is the beam
            process. Must not be passed together with *user*.
        user: If passed, the user for which the parameter is modified.
            Must not be passed together with *context*.
    """

    def __init__(
        self,
        parameter: str,
        *,
        context: str | None = None,
        user: str | None = None,
    ) -> None:
        self._parameter = find_parameter(parameter)
        self._cycle = find_cycle(context=context, user=user)

    def __str__(self) -> str:
        user = self.user
        context_str = f"user={user!r}" if user else f"context={self.context!r}"
        return f"<{self.parameter} @ {context_str}>"

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.parameter!r}, context={self.context!r})"

    @property
    def parameter(self) -> str:
        """The name of the parameter."""
        return self._parameter.getName()

    @parameter.setter
    def parameter(self, name: str) -> None:
        self._parameter = find_parameter(name)

    @property
    def context(self) -> str:
        """The name of the current context."""
        return self._cycle.getName()

    @context.setter
    def context(self, name: str) -> None:
        cycle = _services.context.findStandAloneCycle(name)
        if not cycle:
            raise NotFound(name)
        self._cycle = cycle

    @property
    def user(self) -> str | None:
        """The user name, or None if the context is unmapped."""
        return self._cycle.getUser()

    @user.setter
    def user(self, name: str) -> None:
        try:
            cycle = _services.context.findStandAloneContextByUser(name)
        except java.lang.IllegalArgumentException:
            raise NotFound(name) from None
        assert isinstance(cycle, lsa.StandAloneCycle), cycle
        self._cycle = cycle

    def get_function(self) -> tuple[np.ndarray, np.ndarray]:
        """Query the function for the current context and parameter.

        This returns the function as a 2-tuple of times and values, each
        an 1D array of equal length.
        """
        request = lsa.ContextSettingsRequest.byStandAloneContextAndParameters(
            self._cycle, java.util.Collections.singleton(self._parameter)
        )
        settings = _services.setting.findContextSettings(request)
        function = lsa.Settings.getFunction(settings, self._parameter)
        return np.array(function.toXArray()), np.array(function.toYArray())

    def incorporate_and_trim(
        self,
        cycle_time: float,
        value: float,
        *,
        relative: bool,
        transient: bool | None = None,
        description: str | None = None,
    ) -> None:
        """Modify the function at a point and commit the change.

        This assumes that the parameter is a scalar function. It
        modifies the its *correction* at a given point in time and
        submits this modification to the LSA database. The *target*
        remains unmodified.

        Args:
            cycle_time: The point at which the function shall be
                modified. This is measured in milliseconds from the
                beginning of the cycle. Only those points may be chosen
                for which there is an incorporation rule in the LSA
                database.
            value: The correction value to be transmitted. How this
                value is incorporated depends on the  keyword-only
                argument *relative*.
            relative: If True, *value* is :ref:`added
                <guide/lsa_utils:relative trims>` to the correction of
                the function at the given time. If False, the correction
                is set to *value*, overwriting the previous correction
                at the given time.
            transient: If True (the default), mark this trim as
                :ref:`transient <guide/lsa_utils:transient trims>`. If
                False, this is a permanent trim.
            description: The description to appear in LSA's trim
                history. If not passed, an implementation-defined string
                will be used.
        """
        # For the user's convenience, convert Numpy's floats into Python
        # floats, lest Java throws an exception due to ambiguous
        # overloads.
        if isinstance(value, np.floating):
            value = float(value)
        setting = _build_incorporation_setting(
            parameter=self._parameter,
            context=self._cycle,
            cycle_time=cycle_time,
            value=value,
        )
        hooks = _hooks.get_current_hooks()
        request_builder = (
            lsa.IncorporationRequest.builder()
            .setContext(self._cycle)
            .setDescription(hooks.trim_description(description))
            .setRelative(relative)
            .addIncorporationSetting(setting)
        )
        # Workaround for buggy return type annotation in PJLSA 0.2.18.
        request_builder.setTransient(hooks.trim_transient(transient))
        _services.trim.incorporate(request_builder.build())

    @classmethod
    def _from_raw(
        cls, parameter: lsa.Parameter, context: lsa.StandAloneCycle
    ) -> Incorporator:
        result = super().__new__(cls)
        result._parameter = parameter
        result._cycle = context
        return result


class IncorporatorGroup:
    """Class that allows changing several function-type parameters.

    This is the object-oriented alternative to the module-scope
    functions. It is slightly more reusable in that it allows caching
    the lookup of parameters and cycle.

    Args:
        parameters: The names of the parameters into which changes are
            to be incorporated.
        context: If passed, the context in which the parameter is
            modified. In cycling machines like the SPS, this is the
            cycle; in cycle-less machines like the LHC, this is the beam
            process. Must not be passed together with *user*.
        user: If passed, the user for which the parameter is modified.
            Must not be passed together with *context*.
    """

    def __init__(
        self,
        parameters: list[str],
        *,
        context: str | None = None,
        user: str | None = None,
    ):
        self._parameters = tuple(find_parameter(name) for name in parameters)
        self._cycle = find_cycle(context=context, user=user)

    def __str__(self) -> str:
        num = len(self._parameters)
        user = self.user
        context_str = f"user={user!r}" if user else f"context={self.context!r}"
        return f"<{num} parameter{'s'[:num!=1]} @ {context_str}>"

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}({list(self.parameters)!r}, "
            f"context={self.context!r})"
        )

    @property
    def parameters(self) -> tuple[str, ...]:
        """The names of the parameters."""
        return tuple(p.getName() for p in self._parameters)

    @property
    def context(self) -> str:
        """The name of the current context."""
        return self._cycle.getName()

    @context.setter
    def context(self, name: str) -> None:
        cycle = _services.context.findStandAloneCycle(name)
        if not cycle:
            raise NotFound(name)
        self._cycle = cycle

    @property
    def user(self) -> str | None:
        """The user name, or None if the context is unmapped."""
        return self._cycle.getUser()

    @user.setter
    def user(self, name: str) -> None:
        try:
            cycle = _services.context.findStandAloneContextByUser(name)
        except java.lang.IllegalArgumentException:
            raise NotFound(name) from None
        assert isinstance(cycle, lsa.StandAloneCycle), cycle
        self._cycle = cycle

    def incorporators(self) -> t.Iterator[Incorporator]:
        """Iterate over incorporators for each group parameter.

        Note:
            The incorporators are created dynamically and have no notion
            of equivalence. This means that ``list(self.incorporators())
            == list(self.incorporators())`` is generally False.
        """
        for parameter in self._parameters:
            # pylint: disable = protected-access
            yield Incorporator._from_raw(parameter, self._cycle)

    def get(self, parameter: str) -> Incorporator:
        """Get an incorporator for a parameter in this group.

        Raises:
            KeyError: if no parameter in the group has the given name.

        Note:
            The incorporators are created dynamically and have no notion
            of equivalence. This means that ``self.get(name) ==
            self.get(name)`` is generally False.
        """
        for param in self._parameters:
            if param.getName() == parameter:
                # pylint: disable = protected-access
                return Incorporator._from_raw(param, self._cycle)
        raise KeyError(parameter)

    def incorporate_and_trim(
        self,
        cycle_time: float,
        values: float | np.ndarray | t.Sequence[float] | t.Mapping[str, float],
        *,
        relative: bool,
        transient: bool | None = None,
        description: str | None = None,
    ) -> None:
        """Modify each function at a point and commit the change.

        This assumes that each parameter is a scalar function. It
        modifies its *correction* at a given point in time and submits
        this modification to the LSA database. The *target* remains
        unmodified.

        Args:
            cycle_time: The point at which each function shall be
                modified. This is measured in milliseconds from the
                beginning of the cycle. Only those points may be chosen
                for which there is an incorporation rule in the LSA
                database.
            values: The correction values to be transmitted. How this
                value is incorporated depends on the  keyword-only
                argument *relative*. This may be a single float (to
                incorporate the same correction to all parameters), a
                sequence of floats (one for each parameter), or a
                mapping from parameter name to float (which must mention
                each parameter once and have no superfluous items).
            relative: If True, the *values* are :ref:`added
                <guide/lsa_utils:relative trims>` to the correction of
                the function at the given time. If False, the correction
                is set to the *value*, overwriting the previous
                correction at the given time.
            transient: If True (the default), mark this trim as
                :ref:`transient <guide/lsa_utils:transient trims>`. If
                False, this is a permanent trim.
            description: The description to appear in LSA's trim
                history. If not passed, an implementation-defined string
                will be used.
        """
        values = self._canonicalize_values(values)
        hooks = _hooks.get_current_hooks()
        request_builder = (
            lsa.IncorporationRequest.builder()
            .setContext(self._cycle)
            .setDescription(hooks.trim_description(description))
            .setRelative(relative)
        )
        # Workaround for buggy return type annotation in PJLSA 0.2.18.
        request_builder.setTransient(hooks.trim_transient(transient))
        for parameter, value in zip(self._parameters, values):
            if isinstance(value, np.floating):
                value = float(value)
            setting = _build_incorporation_setting(
                parameter=parameter,
                context=self._cycle,
                cycle_time=cycle_time,
                value=value,
            )
            request_builder.addIncorporationSetting(setting)
        _services.trim.incorporate(request_builder.build())

    def _canonicalize_values(
        self,
        values: float | np.ndarray | t.Sequence[float] | t.Mapping[str, float],
    ) -> np.ndarray:
        if isinstance(values, t.Mapping):
            return _canonicalize_dict(values, self._parameters)
        return np.broadcast_to(values, (len(self._parameters),))


def _canonicalize_dict(
    values: t.Mapping[str, float], parameters: t.Iterable[lsa.Parameter]
) -> np.ndarray:
    # Shallow-copy the dict, remove items from it. If anything is left,
    # the user specified parameters that we don't know.
    values = dict(values)
    result = np.array([values.pop(p.getName()) for p in parameters])
    if values:
        raise KeyError(f"superfluous key: {values.popitem()[0]}")
    return result


def find_parameter(name: str) -> lsa.Parameter:
    """Look up a parameter by its name.

    Raises `NotFound` if the parameter does not exist in the database.
    """
    parameter = _services.parameter.findParameterByName(name)
    if not parameter:
        raise NotFound(name)
    return parameter


def find_cycle(
    *, context: str | None = None, user: str | None = None
) -> lsa.StandAloneCycle:
    """Resolve context/user strings to a LSA domain cycle.

    You should pass either *context* or *user*. Passing both or neither
    raises a `TypeError`. If the given user or context does not exist,
    `NotFound` is raised.
    """
    if context and user:
        raise TypeError("conflicting arguments: 'context' and 'user'")
    if user:
        try:
            cycle = _services.context.findStandAloneContextByUser(user)
        except java.lang.IllegalArgumentException:
            raise NotFound(user) from None
        assert isinstance(cycle, lsa.StandAloneCycle), cycle
        return cycle
    if context:
        cycle = _services.context.findStandAloneCycle(context)
        if not cycle:
            raise NotFound(context)
        return cycle
    raise TypeError("missing keyword-only argument: 'context' or 'user'")


def _build_incorporation_setting(
    parameter: lsa.Parameter,
    context: lsa.StandAloneContext,
    cycle_time: float,
    value: float,
) -> lsa.IncorporationSetting:
    beam_process = _get_beam_process_at(parameter, context, cycle_time)
    beam_process_time = cycle_time - beam_process.getStartTime()
    setting = lsa.spi.ScalarSetting(acc.value.Type.DOUBLE)
    setting.setBeamProcess(beam_process)
    setting.setParameter(parameter)
    setting.setCorrectionValue(acc.value.ValueFactory.createScalar(value))
    return lsa.IncorporationSetting(setting, beam_process_time)


def _get_beam_process_at(
    parameter: lsa.Parameter,
    context: lsa.StandAloneContext,
    cycle_time: float,
) -> lsa.BeamProcess:
    # If there are multiple particle transfers, find the first one
    # that returns a beam process at the given time. Since we are
    # dealing with functions, the beam processes of different
    # particle transfers cannot overlap.
    for transfer in parameter.getParticleTransfers():
        beam_process = lsa.Contexts.getFunctionBeamProcessAt(
            context, transfer, cycle_time
        )
        if beam_process is not None:
            return beam_process
    raise NotFound(f"beam process for {parameter.getName()} at {cycle_time} ms")
