# SPDX-FileCopyrightText: 2020-2024 CERN
# SPDX-FileCopyrightText: 2023-2024 GSI Helmholtzzentrum für Schwerionenforschung
# SPDX-FileNotice: All rights not expressly granted are reserved.
#
# SPDX-License-Identifier: GPL-3.0-or-later OR EUPL-1.2+

# pylint: disable = missing-function-docstring
# pylint: disable = missing-class-docstring
# pylint: disable = import-outside-toplevel
# pylint: disable = redefined-outer-name

"""Tests for `cernml.gym_utils`."""

import typing as t

import numpy as np
import pytest
from gymnasium.spaces import Box

from cernml.gym_utils import Scaler, scale_from_box, unscale_into_box


class VerboseBox(Box):
    """A box that more clearly communicates its bounds.

    By default, Gym boxes repr themselves with bounds ``(low.min(),
    high.max())``. For reproducibility, we're interested in the exact
    bounds. Furthermore, because we include the full bounds, we do not
    need the shape attribute.
    """

    def __repr__(self) -> str:  # pragma: no cover
        return f"Box({self.low}, {self.high}, {self.dtype})"


@pytest.fixture(
    scope="module", params=np.random.default_rng().uniform(-10, 10, size=(50, 2, 3))
)
def space(request: t.Any) -> Box:
    edges = np.asarray(request.param, dtype=np.float32)
    edges.sort(axis=0)
    low, high = edges
    return VerboseBox(low, high)


def test_scale_is_precise(space: Box) -> None:
    scaler = Scaler(space)
    dtype = t.cast(np.dtype[np.floating], space.dtype)
    normalized = Box(-1, 1, shape=space.shape, dtype=dtype.type)
    assert np.array_equal(scaler.scale(space.low), normalized.low)
    assert np.array_equal(scaler.scale(space.high), normalized.high)


def test_unscale_edges(space: Box) -> None:
    scaler = Scaler(space)
    ones = np.ones(space.shape, dtype=space.dtype)
    unscaled_low = scaler.unscale(-ones)
    unscaled_high = scaler.unscale(ones)
    assert np.allclose(unscaled_low, space.low, atol=1e-6)
    assert np.allclose(unscaled_high, space.high, atol=1e-6)
    assert np.all(unscaled_low >= space.low), space


def test_unscale_is_imprecise() -> None:
    space = Box(-9.861845970153809, 9.348796844482422, (3,))
    scaler = Scaler(space)
    bad_value = scaler.unscale(np.ones(space.shape))
    assert bad_value not in space


def test_reject_inf() -> None:
    low = np.array([-1, -1, -1])
    high = np.array([1, np.inf, 1])
    with pytest.raises(TypeError, match="space is not bounded"):
        _ = Scaler(Box(low, high, dtype=np.float64))


def test_broadcast() -> None:
    space = Box(-2, 2, shape=(3, 3), dtype=np.float64)
    neg_ones, ones = scale_from_box(space, np.array([space.low, space.high]))
    assert np.allclose(neg_ones, -1, atol=1e-6)
    assert np.allclose(ones, 1, atol=1e-6)


def test_scale_is_monotonic(space: Box) -> None:
    points = np.array([space.sample() for _ in range(10)])
    points.sort(axis=0)
    scaled = scale_from_box(space, points)
    assert np.array_equal(scaled, np.sort(scaled, axis=0))


def test_unscale_is_monotonic(space: Box) -> None:
    points = np.random.default_rng().uniform(-1, 1, size=(10, *space.shape))
    points.sort(axis=0)
    unscaled = unscale_into_box(space, points)
    assert np.array_equal(unscaled, np.sort(unscaled, axis=0))
