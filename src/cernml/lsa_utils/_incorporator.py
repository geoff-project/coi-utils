"""Provide the :class:`Incorporator` class and related items."""

from __future__ import annotations

import typing as t

import cern.accsoft.commons.value as acc_value
import cern.lsa.domain.settings as lsa_settings
import cern.lsa.domain.settings.spi as lsa_spi
import java.lang
import java.util
import numpy as np

from . import _services

DEFAULT_TRIM_DESCRIPTION = "Via COI"


class NotFound(Exception):
    """The parameter, user or context was not found in the database."""


class Incorporator:
    """Helper class to incorporation and trimming.

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
        self, parameter: str, *, context: str = None, user: str = None
    ) -> None:
        self._parameter = _services.parameter.findParameterByName(parameter)
        if not self._parameter:
            raise NotFound(parameter)
        self._cycle: lsa_settings.StandAloneContext
        # pylint: disable = no-else-raise
        if context and user:
            raise TypeError("conflicting arguments: `context` and `user`")
        elif context:
            self._cycle = _services.context.findStandAloneCycle(context)
            if not self._cycle:
                raise NotFound(context)
        elif user:
            self._cycle = _services.context.findStandAloneContextByUser(user)
            if not self._cycle:
                raise NotFound(user)
        else:
            raise TypeError("missing keyword-only argument: 'context'")

    @property
    def parameter(self) -> str:
        """The name of the current context."""
        return self._parameter.getName()

    @parameter.setter
    def parameter(self, name: str) -> None:
        self._parameter = _services.parameter.findParameterByName(name)

    @property
    def context(self) -> str:
        """The name of the current context."""
        return self._cycle.getName()

    @context.setter
    def context(self, name: str) -> None:
        self._cycle = _services.context.findStandAloneCycle(name)

    @property
    def user(self) -> t.Optional[str]:
        """The name of the current user, or None if the context is unmapped."""
        return t.cast(lsa_spi.SubContextImpl, self._cycle).getUser()

    @user.setter
    def user(self, name: str) -> None:
        self._cycle = _services.context.findStandAloneContextByUser(name)

    def get_function(self) -> t.Tuple[np.ndarray, np.ndarray]:
        """Query the function for the current context and parameter.

        This returns the function as a 2-tuple of times and values, each
        an 1D array of equal length.
        """
        request = lsa_settings.ContextSettingsRequest.byStandAloneContextAndParameters(
            self._cycle, java.util.Collections.singleton(self._parameter)
        )
        settings = _services.setting.findContextSettings(request)
        function = lsa_settings.Settings.getFunction(settings, self._parameter)
        return np.array(function.toXArray()), np.array(function.toYArray())

    def incorporate_and_trim(
        self,
        cycle_time: float,
        value: float,
        *,
        relative: bool,
        description: t.Optional[str] = None,
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
            relative: If True, *value* is added to the correction of the
                function at the given time. If False, the correction is
                set to *value*, overwriting the previous correction at
                the given time.
            description: The description to appear in LSA's trim
                history. If not passed, an implementation-defined string
                will be used.
        """
        # For the user's convenience, convert Numpy's floats into Python
        # floats, lest Java throws an exception due to ambiguous
        # overloads.
        if isinstance(value, np.floating):
            value = float(value)
        setting = self._build_incorporation_setting(cycle_time, value)
        _services.trim.incorporate(
            lsa_settings.IncorporationRequest.builder()
            .setContext(self._cycle)
            .setDescription(
                description if description is not None else DEFAULT_TRIM_DESCRIPTION
            )
            .setRelative(relative)
            .addIncorporationSetting(setting)
            .build()
        )

    def _build_incorporation_setting(
        self, cycle_time: float, value: float
    ) -> lsa_settings.IncorporationSetting:
        beam_process = self._get_beam_process_at(cycle_time)
        beam_process_time = cycle_time - beam_process.getStartTime()
        setting = lsa_spi.ScalarSetting(acc_value.Type.DOUBLE)
        setting.setBeamProcess(beam_process)
        setting.setParameter(self._parameter)
        setting.setCorrectionValue(acc_value.ValueFactory.createScalar(value))
        return lsa_settings.IncorporationSetting(setting, beam_process_time)

    def _get_beam_process_at(self, cycle_time: float) -> lsa_settings.BeamProcess:
        # If there are multiple particle transfers, find the first one
        # that returns a beam process at the given time. Since we are
        # dealing with functions, the beam processes of different
        # particle transfers cannot overlap.
        for transfer in self._parameter.getParticleTransfers():
            beam_process = lsa_settings.Contexts.getFunctionBeamProcessAt(
                self._cycle, transfer, cycle_time
            )
            if beam_process is not None:
                return beam_process
        raise NotFound(f"beam process for t_cycle={cycle_time} ms")


def get_settings_function(
    parameter: str, context: str
) -> t.Tuple[np.ndarray, np.ndarray]:
    """Query the settings function for a given parameter and context.

    This returns the function as a 2-tuple of times and values, each an
    1D array of equal length.
    """
    return Incorporator(parameter, context=context).get_function()


def get_context_by_user(user: str) -> str:
    """Look up the name of the context that belongs to the user."""
    try:
        cycle = _services.context.findStandAloneContextByUser(user)
    except java.lang.IllegalArgumentException:  # type: ignore
        raise NotFound(user) from None
    return cycle.getName()


def get_cycle_type_attributes(context: str) -> t.Dict[str, str]:
    """Look up the cycle type attributes associated with a context."""
    cycle = _services.context.findStandAloneCycle(context)
    if cycle is None:
        raise NotFound(context)
    cycle_type = _services.generation.findCycleType(cycle.getTypeName())
    if cycle_type is None:
        raise NotFound(cycle.getTypeName())
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
    Incorporator(parameter_name, context=context).incorporate_and_trim(
        cycle_time, value, relative=relative, description=description
    )
