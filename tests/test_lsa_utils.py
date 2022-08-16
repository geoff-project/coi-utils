#!/usr/bin/env python
"""Test the LSA utility functions."""

# pylint: disable = missing-function-docstring
# pylint: disable = missing-class-docstring
# pylint: disable = import-outside-toplevel
# pylint: disable = redefined-outer-name

from __future__ import annotations

import typing as t
from unittest.mock import Mock

import numpy as np
import pytest

pjlsa = pytest.importorskip("pjlsa")
with pjlsa.LSAClient(server="next").java_api():
    from cernml import lsa_utils


def _is_sorted(array: np.ndarray) -> bool:
    assert np.ndim(array) == 1
    # Convert numpy._bool to built-in bool.
    return bool(np.all(array[:-1] < array[1:]))


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


def test_incorporate(monkeypatch: pytest.MonkeyPatch) -> None:
    # pylint: disable=protected-access
    trim = Mock()
    monkeypatch.setattr(lsa_utils._services, "trim", trim)
    # Even if we don't promise it in our type signature, we can also
    # handle NumPy floats.
    value = t.cast(float, np.float32(-0.3416))
    lsa_utils.incorporate_and_trim(
        "ETL.GSBHN10/KICK",
        "Pb54_2BP_2021_06_09_EARLY_2400ms_V1",
        120.0,
        value,
        relative=False,
        description="cernml.lsa_utils test suite",
    )
    trim.incorporate.assert_called_once()


def test_multi_incorporate(monkeypatch: pytest.MonkeyPatch) -> None:
    # pylint: disable=protected-access
    trim = Mock()
    monkeypatch.setattr(lsa_utils._services, "trim", trim)
    lsa_utils.incorporate_and_trim(
        (
            "logical.MDAH.2303/K",
            "logical.MDAH.2307/K",
            "logical.MDAV.2301.M/K",
            "logical.MDAV.2305.M/K",
        ),
        "SFT_PRO_MTE_L4780_2022_V1",
        4460.0,
        0.0,
        relative=False,
        description="cernml.lsa_utils test suite",
    )
    trim.incorporate.assert_called_once()


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


def test_get_cycle_type_attributes() -> None:
    attributes = lsa_utils.get_cycle_type_attributes(
        "Pb54_2BP_2021_06_09_EARLY_2400ms_V1"
    )
    assert isinstance(attributes, dict)


def test_get_cycle_type_attributes_bad_name() -> None:
    with pytest.raises(lsa_utils.NotFound, match="bad_context"):
        _ = lsa_utils.get_cycle_type_attributes("bad_context")


@pytest.fixture
def incorporator() -> lsa_utils.Incorporator:
    return lsa_utils.Incorporator(
        parameter="logical.RDH.20207/K",
        user="SPS.USER.HIRADMT1",
    )


class TestIncorporator:
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


@pytest.fixture
def incorporator_group() -> lsa_utils.IncorporatorGroup:
    return lsa_utils.IncorporatorGroup(
        [
            f"logical.{i}/K"
            for i in ["MDAH.2303", "MDAH.2307", "MDAV.2301.M", "MDAV.2305.M"]
        ],
        user="SPS.USER.SFTPRO1",
    )


class TestIncorporatorGroup:
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
        incorporator_group: lsa_utils.IncorporatorGroup,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # pylint: disable=protected-access
        trim = Mock()
        monkeypatch.setattr(lsa_utils._services, "trim", trim)
        incorporator_group.incorporate_and_trim(4460.0, 0.0, relative=False)
        trim.incorporate.assert_called_once()

    def test_incorporate_dict(
        self,
        incorporator_group: lsa_utils.IncorporatorGroup,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # pylint: disable=protected-access
        trim = Mock()
        monkeypatch.setattr(lsa_utils._services, "trim", trim)
        values = {
            "logical.MDAH.2303/K": 1.0,
            "logical.MDAH.2307/K": 2.0,
            "logical.MDAV.2301.M/K": 3.0,
            "logical.MDAV.2305.M/K": 4.0,
        }
        incorporator_group.incorporate_and_trim(4460.0, values, relative=False)
        trim.incorporate.assert_called_once()

    def test_incorporate_bad_type(
        self,
        incorporator_group: lsa_utils.IncorporatorGroup,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # pylint: disable=protected-access
        monkeypatch.setattr(lsa_utils._services, "trim", Mock())
        with pytest.raises(Exception, match="value of type STRING"):
            incorporator_group.incorporate_and_trim(
                4460.0, t.cast(float, "0.0"), relative=False
            )

    def test_incorporate_dict_too_big(
        self,
        incorporator_group: lsa_utils.IncorporatorGroup,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # pylint: disable=protected-access
        monkeypatch.setattr(lsa_utils._services, "trim", Mock())
        values = {
            "logical.MDAH.2201/K": 0.0,
            "logical.MDAH.2303/K": 1.0,
            "logical.MDAH.2307/K": 2.0,
            "logical.MDAV.2301.M/K": 3.0,
            "logical.MDAV.2305.M/K": 4.0,
        }
        with pytest.raises(KeyError, match="logical.MDAH.2201/K"):
            incorporator_group.incorporate_and_trim(4460.0, values, relative=False)
