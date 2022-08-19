"""Provide :class:`Incorporator` and :class:`IncorporatorGroup` and related items."""

from __future__ import annotations

import typing as t

import cern.accsoft.commons.value as acc_value
import cern.lsa.domain.settings as lsa_settings
import cern.lsa.domain.settings.spi as lsa_spi
import java.util
import numpy as np

from . import _services

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
        context: t.Optional[str] = None,
        user: t.Optional[str] = None,
    ) -> None:
        self._parameter = _services.parameter.findParameterByName(parameter)
        if not self._parameter:
            raise NotFound(parameter)
        self._cycle = _find_cycle(context=context, user=user)

    @property
    def parameter(self) -> str:
        """The name of the parameter."""
        return self._parameter.getName()

    @parameter.setter
    def parameter(self, name: str) -> None:
        parameter = _services.parameter.findParameterByName(name)
        if not parameter:
            raise NotFound(name)
        self._parameter = parameter

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
    def user(self) -> t.Optional[str]:
        """The name of the current user, or None if the context is unmapped."""
        return self._cycle.getUser()

    @user.setter
    def user(self, name: str) -> None:
        try:
            cycle = _services.context.findStandAloneContextByUser(name)
        except java.lang.IllegalArgumentException:  # type: ignore
            raise NotFound(name) from None
        assert isinstance(cycle, lsa_settings.StandAloneCycle), cycle
        self._cycle = cycle

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
        setting = _build_incorporation_setting(
            parameter=self._parameter,
            context=self._cycle,
            cycle_time=cycle_time,
            value=value,
        )
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

    @classmethod
    def _from_raw(
        cls, parameter: lsa_settings.Parameter, context: lsa_settings.StandAloneCycle
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
        parameters: t.List[str],
        *,
        context: t.Optional[str] = None,
        user: t.Optional[str] = None,
    ):
        found_parameters = []
        for name in parameters:
            parameter = _services.parameter.findParameterByName(name)
            if not parameter:
                raise NotFound(name)
            found_parameters.append(parameter)
        self._parameters = tuple(found_parameters)
        self._cycle = _find_cycle(context=context, user=user)

    @property
    def parameters(self) -> t.Tuple[str, ...]:
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
    def user(self) -> t.Optional[str]:
        """The name of the current user, or None if the context is unmapped."""
        return self._cycle.getUser()

    @user.setter
    def user(self, name: str) -> None:
        try:
            cycle = _services.context.findStandAloneContextByUser(name)
        except java.lang.IllegalArgumentException:  # type: ignore
            raise NotFound(name) from None
        assert isinstance(cycle, lsa_settings.StandAloneCycle), cycle
        self._cycle = cycle

    def incorporators(self) -> t.Iterator[Incorporator]:
        """Iterate over incorporators for each of the group's parameters.

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
        values: t.Union[float, np.ndarray, t.Sequence[float], t.Mapping[str, float]],
        *,
        relative: bool,
        description: t.Optional[str] = None,
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
            relative: If True, the *values* are added to the correction
                of the respective functions at the given time. If False,
                the corrections are set to th *values*, overwriting the
                previous correction at the given time.
            description: The description to appear in LSA's trim
                history. If not passed, an implementation-defined string
                will be used.
        """
        values = self._canonicalize_values(values)
        request_builder = (
            lsa_settings.IncorporationRequest.builder()
            .setContext(self._cycle)
            .setDescription(
                description if description is not None else DEFAULT_TRIM_DESCRIPTION
            )
            .setRelative(relative)
        )
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
        values: t.Union[float, np.ndarray, t.Sequence[float], t.Mapping[str, float]],
    ) -> np.ndarray:
        if isinstance(values, t.Mapping):
            return _canonicalize_dict(values, self._parameters)
        return np.broadcast_to(values, (len(self._parameters),))


def _canonicalize_dict(
    values: t.Mapping[str, float], parameters: t.Iterable[lsa_settings.Parameter]
) -> np.ndarray:
    # Shallow-copy the dict, remove items from it. If anything is left,
    # the user specified parameters that we don't know.
    values = dict(values)
    result = np.array([values.pop(p.getName()) for p in parameters])
    if values:
        raise KeyError(f"superfluous key: {values.popitem()[0]}")
    return result


def _find_cycle(
    *, context: t.Optional[str], user: t.Optional[str]
) -> lsa_settings.StandAloneCycle:
    if context and user:
        raise TypeError("conflicting arguments: 'context' and 'user'")
    if user:
        try:
            cycle = _services.context.findStandAloneContextByUser(user)
        except java.lang.IllegalArgumentException:  # type: ignore
            raise NotFound(user) from None
        assert isinstance(cycle, lsa_settings.StandAloneCycle), cycle
        return cycle
    if context:
        cycle = _services.context.findStandAloneCycle(context)
        if not cycle:
            raise NotFound(context)
        return cycle
    raise TypeError("missing keyword-only argument: 'context' or 'user'")


def _build_incorporation_setting(
    parameter: lsa_settings.Parameter,
    context: lsa_settings.StandAloneContext,
    cycle_time: float,
    value: float,
) -> lsa_settings.IncorporationSetting:
    beam_process = _get_beam_process_at(parameter, context, cycle_time)
    beam_process_time = cycle_time - beam_process.getStartTime()
    setting = lsa_spi.ScalarSetting(acc_value.Type.DOUBLE)
    setting.setBeamProcess(beam_process)
    setting.setParameter(parameter)
    setting.setCorrectionValue(acc_value.ValueFactory.createScalar(value))
    return lsa_settings.IncorporationSetting(setting, beam_process_time)


def _get_beam_process_at(
    parameter: lsa_settings.Parameter,
    context: lsa_settings.StandAloneContext,
    cycle_time: float,
) -> lsa_settings.BeamProcess:
    # If there are multiple particle transfers, find the first one
    # that returns a beam process at the given time. Since we are
    # dealing with functions, the beam processes of different
    # particle transfers cannot overlap.
    for transfer in parameter.getParticleTransfers():
        beam_process = lsa_settings.Contexts.getFunctionBeamProcessAt(
            context, transfer, cycle_time
        )
        if beam_process is not None:
            return beam_process
    raise NotFound(f"beam process for {parameter.getName()} at {cycle_time} ms")
