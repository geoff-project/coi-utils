#!/usr/bin/env python
"""Test the LSA utility functions."""

# pylint: disable = missing-function-docstring
# pylint: disable = missing-class-docstring
# pylint: disable = import-outside-toplevel
# pylint: disable = redefined-outer-name


import numpy as np
import pytest

pjlsa = pytest.importorskip('pjlsa')
with pjlsa.LSAClient(server="next").java_api():
    from cernml import lsa_utils


def _is_sorted(array: np.ndarray) -> bool:
    assert np.ndim(array) == 1
    return np.all(array[:-1] < array[1:])


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


def test_incorporate_out_of_range() -> None:
    with pytest.raises(lsa_utils.NotFound, match="beam process for t_cycle=0.0 ms"):
        lsa_utils.incorporate_and_trim(
            "ETL.GSBHN10/KICK",
            "Pb54_2BP_2021_06_09_EARLY_2400ms_V1",
            0.0,
            0.0,
            relative=False,
        )
