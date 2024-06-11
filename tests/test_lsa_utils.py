# SPDX-FileCopyrightText: 2020-2023 CERN
# SPDX-FileCopyrightText: 2023 GSI Helmholtzzentrum für Schwerionenforschung
# SPDX-FileNotice: All rights not expressly granted are reserved.
#
# SPDX-License-Identifier: GPL-3.0-or-later OR EUPL-1.2+

# pylint: disable = missing-function-docstring
# pylint: disable = missing-class-docstring
# pylint: disable = import-outside-toplevel
# pylint: disable = redefined-outer-name

"""Test the LSA utility functions."""

from __future__ import annotations

import typing as t
from functools import partial
from unittest.mock import Mock

import numpy as np
import pytest

from cernml import lsa_utils


def _is_sorted(array: np.ndarray) -> bool:
    assert np.ndim(array) == 1
    # Convert numpy.bool_ to built-in bool.
    return bool(np.all(array[:-1] < array[1:]))


# Note: @pytest.fixture def trim_service() is defined in /conftest.py.
# This is necessary to ensure it is active even in doctests.


@pytest.fixture
def incorporator() -> lsa_utils.Incorporator:
    return lsa_utils.Incorporator(
        parameter="logical.RDH.20207/K",
        user="SPS.USER.HIRADMT1",
    )


@pytest.fixture
def incorporator_group() -> lsa_utils.IncorporatorGroup:
    return lsa_utils.IncorporatorGroup(
        [
            f"logical.{i}/K"
            for i in ["MDAH.2303", "MDAH.2307", "MDAV.2301.M", "MDAV.2305.M"]
        ],
        user="SPS.USER.SFTPRO1",
    )


@pytest.fixture
def mock_hooks() -> t.Iterator[lsa_utils.Hooks]:
    hooks = Mock(spec=lsa_utils.Hooks)
    lsa_utils.Hooks.install_globally(hooks)
    try:
        yield hooks
    finally:
        lsa_utils.Hooks.uninstall_globally(hooks)


def test_get_user() -> None:
    context = lsa_utils.get_context_by_user("SPS.USER.HIRADMT1")
    assert context.startswith("HIRADMAT")


def test_get_user_doesnt_exist() -> None:
    with pytest.raises(lsa_utils.NotFound, match="bad_user"):
        _ = lsa_utils.get_context_by_user("bad_user")


def test_get_function() -> None:
    times, values = lsa_utils.get_settings_function(
        parameter="logical.RDH.20207/K",
        context="HIRADMAT_PILOT_Q20_2018_V1",
    )
    assert np.ndim(times) == np.ndim(values) == 1
    assert len(times) == len(values)
    assert _is_sorted(times)


def test_get_function_bad_name() -> None:
    with pytest.raises(lsa_utils.NotFound, match="bad_param"):
        _ = lsa_utils.get_settings_function(
            parameter="bad_param",
            context="HIRADMAT_PILOT_Q20_2018_V1",
        )


def test_get_function_bad_context() -> None:
    with pytest.raises(lsa_utils.NotFound, match="bad_context"):
        _ = lsa_utils.get_settings_function(
            parameter="logical.RDH.20207/K",
            context="bad_context",
        )


@pytest.mark.parametrize("transient", [False, True])
@pytest.mark.parametrize("relative", [False, True])
def test_incorporate(trim_service: Mock, relative: bool, transient: bool) -> None:
    # Even if we don't promise it in our type signature, we can also
    # handle NumPy floats.
    value = t.cast(float, np.float32(-0.3416))
    lsa_utils.incorporate_and_trim(
        "ETL.GSBHN10/KICK",
        "Pb54_2BP_2021_06_09_EARLY_2400ms_V1",
        120.0,
        value,
        relative=relative,
        transient=transient,
        description="cernml.lsa_utils test suite",
    )
    trim_service.incorporate.assert_called_once()
    [req], [] = trim_service.incorporate.call_args
    assert req.isRelative() == relative
    assert req.isTransient() == transient


@pytest.mark.parametrize("transient", [False, True])
@pytest.mark.parametrize("relative", [False, True])
def test_multi_incorporate(trim_service: Mock, relative: bool, transient: bool) -> None:
    lsa_utils.incorporate_and_trim(
        [
            "logical.MDAH.2303/K",
            "logical.MDAH.2307/K",
            "logical.MDAV.2301.M/K",
            "logical.MDAV.2305.M/K",
        ],
        "SFT_PRO_MTE_L4780_2022_V1",
        4460.0,
        np.zeros(4),
        relative=relative,
        transient=transient,
        description="cernml.lsa_utils test suite",
    )
    trim_service.incorporate.assert_called_once()
    [req], [] = trim_service.incorporate.call_args
    assert req.isRelative() == relative
    assert req.isTransient() == transient


def test_incorporate_out_of_range() -> None:
    with pytest.raises(
        lsa_utils.NotFound, match="beam process for ETL.GSBHN10/KICK at 0.0 ms"
    ):
        lsa_utils.incorporate_and_trim(
            "ETL.GSBHN10/KICK",
            "Pb54_2BP_2021_06_09_EARLY_2400ms_V1",
            0.0,
            0.0,
            relative=False,
        )


@pytest.mark.parametrize("transient", [False, True])
@pytest.mark.parametrize("relative", [False, True])
def test_trim_settings(trim_service: Mock, relative: bool, transient: bool) -> None:
    lsa_utils.trim_scalar_settings(
        {
            "ER.GSECVGUN/Enable#enabled": True,
            "ER.KFH31/SettingA#batchNrA": 1,
            "ER.KFH31/SettingA#kickOnA": "ON",
            "ER.KFH31/SettingA#kickStrengthCcvA": 54.5,
        },
        user="LEI.USER.NOMINAL",
        relative=relative,
        transient=transient,
    )
    [req], [] = trim_service.trimSettings.call_args
    assert req.isRelative() == relative
    assert req.isTransient() == transient


def test_get_cycle_type_attributes() -> None:
    attributes = lsa_utils.get_cycle_type_attributes(
        "Pb54_2BP_2021_06_09_EARLY_2400ms_V1"
    )
    assert isinstance(attributes, dict)


def test_get_cycle_type_attributes_bad_name() -> None:
    with pytest.raises(lsa_utils.NotFound, match="bad_context"):
        _ = lsa_utils.get_cycle_type_attributes("bad_context")


class TestIncorporator:
    def test_str(self, incorporator: lsa_utils.Incorporator) -> None:
        assert str(incorporator) == "<logical.RDH.20207/K @ user='SPS.USER.HIRADMT1'>"

    def test_repr(self, incorporator: lsa_utils.Incorporator) -> None:
        assert (
            repr(incorporator) == "Incorporator('logical.RDH.20207/K', "
            "context='HIRADMAT_PILOT_L8400_Q20_2023_V1')"
        )

    def test_missing_argument(self) -> None:
        with pytest.raises(TypeError, match="'context' or 'user'"):
            _ = lsa_utils.Incorporator("logical.RDH.20207/K")

    def test_bad_user(self) -> None:
        with pytest.raises(lsa_utils.NotFound, match="bad_user"):
            _ = lsa_utils.Incorporator("logical.RDH.20207/K", user="bad_user")

    def test_conflicting_arguments(self) -> None:
        with pytest.raises(TypeError, match="'context' and 'user'"):
            _ = lsa_utils.Incorporator("logical.RDH.20207/K", context="bad", user="bad")

    def test_parameter(self, incorporator: lsa_utils.Incorporator) -> None:
        assert incorporator.parameter == "logical.RDH.20207/K"
        incorporator.parameter = "logical.RDH.20407/K"
        assert incorporator.parameter == "logical.RDH.20407/K"
        with pytest.raises(lsa_utils.NotFound, match="logical.RDH.20209/K"):
            incorporator.parameter = "logical.RDH.20209/K"

    def test_context(self, incorporator: lsa_utils.Incorporator) -> None:
        assert incorporator.context.startswith("HIRADMAT")
        assert incorporator.user == "SPS.USER.HIRADMT1"
        incorporator.user = "SPS.USER.SFTPRO1"
        assert incorporator.context.startswith("SFT_PRO_MTE")
        assert incorporator.user == "SPS.USER.SFTPRO1"
        incorporator.context = "AWAKE_1Inj_FB60_FT850_Q20_2018_V1"
        assert incorporator.context == "AWAKE_1Inj_FB60_FT850_Q20_2018_V1"
        assert incorporator.user is None
        with pytest.raises(lsa_utils.NotFound, match="bad_user"):
            incorporator.user = "bad_user"
        with pytest.raises(lsa_utils.NotFound, match="bad_context"):
            incorporator.context = "bad_context"


class TestIncorporatorGroup:
    def test_str(self, incorporator_group: lsa_utils.IncorporatorGroup) -> None:
        assert str(incorporator_group) == "<4 parameters @ user='SPS.USER.SFTPRO1'>"

    def test_repr(self, incorporator_group: lsa_utils.IncorporatorGroup) -> None:
        assert (
            repr(incorporator_group) == "IncorporatorGroup(['logical.MDAH.2303/K', "
            "'logical.MDAH.2307/K', 'logical.MDAV.2301.M/K', "
            "'logical.MDAV.2305.M/K'], context='SFT_PRO_MTE_L4780_2024_V1')"
        )

    def test_bad_names(self) -> None:
        with pytest.raises(lsa_utils.NotFound, match="bad_name"):
            _ = lsa_utils.IncorporatorGroup(["bad_name"], user="SPS.USER.SFTPRO1")

    def test_parameters(self, incorporator_group: lsa_utils.IncorporatorGroup) -> None:
        assert incorporator_group.parameters == (
            "logical.MDAH.2303/K",
            "logical.MDAH.2307/K",
            "logical.MDAV.2301.M/K",
            "logical.MDAV.2305.M/K",
        )

    def test_iterator(self, incorporator_group: lsa_utils.IncorporatorGroup) -> None:
        incorporators = list(incorporator_group.incorporators())
        assert all(i.context == incorporator_group.context for i in incorporators)
        assert [i.parameter for i in incorporators] == [
            "logical.MDAH.2303/K",
            "logical.MDAH.2307/K",
            "logical.MDAV.2301.M/K",
            "logical.MDAV.2305.M/K",
        ]

    def test_get(self, incorporator_group: lsa_utils.IncorporatorGroup) -> None:
        incorporators = list(incorporator_group.incorporators())
        for i in incorporators:
            assert incorporator_group.get(i.parameter).parameter == i.parameter
        with pytest.raises(KeyError, match="bad_name"):
            incorporator_group.get("bad_name")

    def test_context(self, incorporator_group: lsa_utils.IncorporatorGroup) -> None:
        assert incorporator_group.context.startswith("SFT_PRO_MTE")
        assert incorporator_group.user == "SPS.USER.SFTPRO1"
        incorporator_group.user = "SPS.USER.HIRADMT1"
        assert incorporator_group.context.startswith("HIRADMAT")
        assert incorporator_group.user == "SPS.USER.HIRADMT1"
        incorporator_group.context = "AWAKE_1Inj_FB60_FT850_Q20_2018_V1"
        assert incorporator_group.context == "AWAKE_1Inj_FB60_FT850_Q20_2018_V1"
        assert incorporator_group.user is None
        with pytest.raises(lsa_utils.NotFound, match="bad_user"):
            incorporator_group.user = "bad_user"
        with pytest.raises(lsa_utils.NotFound, match="bad_context"):
            incorporator_group.context = "bad_context"

    def test_incorporate(
        self,
        trim_service: Mock,
        incorporator_group: lsa_utils.IncorporatorGroup,
    ) -> None:
        incorporator_group.incorporate_and_trim(4460.0, 0.0, relative=False)
        trim_service.incorporate.assert_called_once()

    def test_incorporate_dict(
        self,
        trim_service: Mock,
        incorporator_group: lsa_utils.IncorporatorGroup,
    ) -> None:
        values = {
            "logical.MDAH.2303/K": 1.0,
            "logical.MDAH.2307/K": 2.0,
            "logical.MDAV.2301.M/K": 3.0,
            "logical.MDAV.2305.M/K": 4.0,
        }
        incorporator_group.incorporate_and_trim(4460.0, values, relative=False)
        trim_service.incorporate.assert_called_once()

    def test_incorporate_bad_type(
        self,
        trim_service: Mock,
        incorporator_group: lsa_utils.IncorporatorGroup,
    ) -> None:
        with pytest.raises(Exception, match="value of type STRING"):
            incorporator_group.incorporate_and_trim(
                4460.0, t.cast(float, "0.0"), relative=False
            )
        trim_service.incorporate.assert_not_called()

    def test_incorporate_dict_too_big(
        self,
        trim_service: Mock,
        incorporator_group: lsa_utils.IncorporatorGroup,
    ) -> None:
        values = {
            "logical.MDAH.2201/K": 0.0,
            "logical.MDAH.2303/K": 1.0,
            "logical.MDAH.2307/K": 2.0,
            "logical.MDAV.2301.M/K": 3.0,
            "logical.MDAV.2305.M/K": 4.0,
        }
        with pytest.raises(KeyError, match="logical.MDAH.2201/K"):
            incorporator_group.incorporate_and_trim(4460.0, values, relative=False)
        trim_service.incorporate.assert_not_called()


class TestHooks:
    def test_default_hooks_are_default(self) -> None:
        assert isinstance(lsa_utils.get_current_hooks(), lsa_utils.DefaultHooks)

    def test_default_hooks_are_identical(self) -> None:
        # Check changes in get_current_hooks() implementation.
        assert lsa_utils.get_current_hooks() is lsa_utils.get_current_hooks()

    def test_cannot_uninstall_default_hooks(self) -> None:
        hooks = lsa_utils.get_current_hooks()
        assert isinstance(hooks, lsa_utils.DefaultHooks)
        with pytest.raises(RuntimeError):
            hooks.uninstall_globally()

    def test_install_replaces_hooks(self) -> None:
        default = lsa_utils.get_current_hooks()
        new_hooks = lsa_utils.Hooks()
        new_hooks.install_globally()
        try:
            assert lsa_utils.get_current_hooks() is new_hooks
        finally:
            new_hooks.uninstall_globally()
        assert lsa_utils.get_current_hooks() == default

    def test_context_replaces_hooks(self) -> None:
        default = lsa_utils.get_current_hooks()
        new_hooks = lsa_utils.Hooks()
        with new_hooks:
            assert lsa_utils.get_current_hooks() is new_hooks
        assert lsa_utils.get_current_hooks() == default

    def test_double_install_raises_runtime_error(self) -> None:
        hooks = lsa_utils.Hooks()
        with hooks:
            with pytest.raises(RuntimeError):
                hooks.install_globally()

    def test_bare_uninstall_raises_runtime_error(self) -> None:
        hooks = lsa_utils.Hooks()
        with pytest.warns(lsa_utils.InconsistentHookInstalls):
            with pytest.raises(RuntimeError):
                hooks.uninstall_globally()

    def test_double_uninstall_raises_runtime_error(self) -> None:
        hooks = lsa_utils.Hooks()
        with pytest.warns(lsa_utils.InconsistentHookInstalls):
            with pytest.raises(RuntimeError):
                with hooks:
                    hooks.uninstall_globally()

    def test_call_non_installed_hooks_raises_runtime_error(self) -> None:
        hooks = lsa_utils.Hooks()
        with pytest.raises(RuntimeError):
            hooks.trim_description(Mock())
        with pytest.raises(RuntimeError):
            hooks.trim_transient(Mock())

    def test_inconsistent_uninstall_warns(self) -> None:
        outer_hooks = lsa_utils.Hooks()
        inner_hooks = lsa_utils.Hooks()
        with pytest.warns(lsa_utils.InconsistentHookInstalls):
            with outer_hooks:
                inner_hooks.install_globally()
        # Both are uninstalled now.
        for hooks in outer_hooks, inner_hooks:
            with pytest.raises(RuntimeError):
                hooks.trim_transient(Mock())

    def test_hooks_call_parent(self, mock_hooks: Mock) -> None:
        hooks = lsa_utils.Hooks()
        desc = Mock()
        transient = Mock()
        with hooks:
            hooks.trim_description(desc)
            hooks.trim_transient(transient)
        mock_hooks.trim_description.assert_called_once_with(desc)
        mock_hooks.trim_transient.assert_called_once_with(transient)

    def test_hooks_equality(self) -> None:
        subclass = type("Subclass", (lsa_utils.DefaultHooks,), {})
        assert lsa_utils.DefaultHooks() == lsa_utils.DefaultHooks()
        assert lsa_utils.DefaultHooks() != subclass()
        assert subclass() != lsa_utils.DefaultHooks()
        assert subclass() == subclass()
        assert lsa_utils.DefaultHooks() != lsa_utils.Hooks()
        assert lsa_utils.Hooks() != lsa_utils.DefaultHooks()
        assert lsa_utils.Hooks() != lsa_utils.Hooks()

    def test_default_hooks_values(self) -> None:
        hooks = lsa_utils.get_current_hooks()
        desc = Mock()
        transient = Mock()
        assert hooks.trim_description(None) == "via cernml-coi-utils"
        assert hooks.trim_description(desc) == desc
        assert hooks.trim_transient(None) is True
        assert hooks.trim_transient(transient) == transient

    @pytest.mark.parametrize("transient_return", [False, True])
    @pytest.mark.parametrize(
        "curried_call",
        [
            partial(
                lsa_utils.trim_scalar_settings,
                {"ER.GSECVGUN/Enable#enabled": True},
                user="LEI.USER.NOMINAL",
            ),
            partial(
                lsa_utils.incorporate_and_trim,
                "ETL.GSBHN10/KICK",
                "Pb54_2BP_2021_06_09_EARLY_2400ms_V1",
                120.0,
                -0.3416,
                relative=False,
            ),
            partial(
                lsa_utils.incorporate_and_trim,
                [
                    "logical.MDAH.2303/K",
                    "logical.MDAH.2307/K",
                    "logical.MDAV.2301.M/K",
                    "logical.MDAV.2305.M/K",
                ],
                "SFT_PRO_MTE_L4780_2022_V1",
                4460.0,
                np.zeros(4),
                relative=False,
            ),
        ],
    )
    def test_hooks_are_called(
        self,
        trim_service: Mock,
        mock_hooks: Mock,
        curried_call: t.Callable,
        transient_return: bool,
    ) -> None:
        mock_hooks.trim_description.return_value = str(Mock())
        mock_hooks.trim_transient.return_value = transient_return
        desc = Mock()
        transient_arg = Mock()
        curried_call(description=desc, transient=transient_arg)
        mock_hooks.trim_description.assert_called_once_with(desc)
        mock_hooks.trim_transient.assert_called_once_with(transient_arg)
        [req], [] = getattr(
            trim_service,
            (
                "trimSettings"
                if "trim_scalar_settings" in repr(curried_call)
                else "incorporate"
            ),
        ).call_args
        assert req.getDescription() == mock_hooks.trim_description.return_value
        assert req.isTransient() == mock_hooks.trim_transient.return_value
