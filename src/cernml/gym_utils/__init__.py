"""Utilities for working with OpenAI Gym."""

import numpy as np
from gym.spaces import Box


class Scaler:
    """Helper class for scaling and unscaling arrays.

    Args:
        space: The box to use as a base space. This must be *bounded*,
            i.e. all elements of *space.low* and *space.high* must be
            finite.
        symmetric: If passed and False, scale values into the normalized
            box [0; 1]. By default, the normalized box is [−1; +1].

    Raises:
        TypeError: if the given space cannot be used for scaling.

    In this context, *scaling* uses linear interpolation to bring an
    array from some finite box *B* into a normalized box *B'*. This is
    [−1, +1] by default::

        >>> scaler = Scaler(Box(5, 10, shape=(3,)))
        >>> scaler.scale([5, 7.5, 10])
        array([-1.,  0.,  1.], dtype=float32)

    "Unscaling" does the reverse. It brings a normalized point back into
    the box *B*::

        >>> scaler.unscale([-1, 0, 1])
        array([ 5. ,  7.5, 10. ], dtype=float32)

    Both operations are *monotonic*: A value that is greater than
    another does not become smaller after scaling or unscaling. This may
    seem obvious, but it isn't true for all interpolation formulas::

        >>> def lerp(box, t):
        ...     '''Precise, but non-monotonic interpolation.'''
        ...     return box.high * t + box.low * (np.ones_like(t) - t)
        >>> box = Box(1.0, 3.0, shape=())
        >>> # Operate close to the low end, this makes addition inexact.
        >>> t1 = np.float32(2.9802322e-8)
        >>> t2 = np.float32(3.352763e-8)
        >>> # One is obviously smaller than the other.
        >>> t1 < t2
        True
        >>> # But after rescaling, the other became smaller!
        >>> lerp(box, t1) > lerp(box, t2)
        True
        >>> lerp(box, t1), lerp(box, t2)
        (1.0000001, 1.0)

    In addition, scaling is *precise*: When given either edge of the box
    *B*, the result is exactly −1 and +1 respectively::

        >>> scaler = Scaler(Box(0, 2, ()))
        >>> # Scale two values at once.
        >>> scaler.scale([0, 2])
        array([-1.,  1.], dtype=float32)

    By contrast, unscaling is *imprecise*: The inputs −1 and +1 are not
    guaranteed to reproduce the edges of the box *B* exactly::

        >>> scaler = Scaler(Box(-9.8, 9.0, ()))
        >>> # Unscale two values at once.
        >>> scaler.unscale([-1, 1])
        array([-9.8     ,  8.999999], dtype=float32)

    Both methods pass through the array subclass of the argument, but
    coerce the dtype to whatever the given space uses::

        >>> scaler = Scaler(Box(0, 1, (2,), dtype=np.float32))
        >>> x = np.zeros((2,), dtype=np.float64).view(np.recarray)
        >>> isinstance(scaler.unscale(x), np.recarray)
        True
        >>> isinstance(scaler.scale(x), np.recarray)
        True
        >>> scaler.scale(x).dtype == np.float32
        True
        >>> scaler.unscale(x).dtype == np.float32
        True

    An asymmetric normalized space can be generated as well::

        >>> scaler = Scaler(Box(-10, 10, (2,)), symmetric=False)
        >>> scaler.scale([-10, 10])
        array([0., 1.], dtype=float32)
        >>> scaler.unscale([0, 1])
        array([-10.,  10.], dtype=float32)
    """

    def __init__(self, space: Box, symmetric: bool = True) -> None:
        if not space.is_bounded():
            raise TypeError(f"space is not bounded: {space}")
        self._space = space
        self._symmetric = symmetric

    def scale(self, unnormalized: np.ndarray) -> np.ndarray:
        """Rescale an array from [*low*, *high*] to [−1, +1]."""
        unnormalized = np.asanyarray(unnormalized, dtype=self._space.dtype)
        low, high = self._space.low, self._space.high
        intermediary = (unnormalized - low) / (high - low)
        return (2.0 * intermediary - 1.0) if self._symmetric else intermediary

    def unscale(self, normalized: np.ndarray) -> np.ndarray:
        """Rescale an array from [−1, +1] to [*low*, *high*]."""
        normalized = np.asanyarray(normalized, dtype=self._space.dtype)
        low, high = self._space.low, self._space.high
        intermediary = 0.5 * (normalized + 1.0) if self._symmetric else normalized
        return intermediary * (high - low) + low

    @property
    def symmetric(self) -> bool:
        """True if the scaled space is symmetric, False otherwise."""
        return self._symmetric

    @property
    def space(self) -> Box:
        """The box originally passed to this scaler.

        Example:

            >>> box = Box(-3, 3, (3,))
            >>> scaler = Scaler(box)
            >>> scaler.space == box
            True
            >>> scaler.space.dtype == box.dtype
            True
        """
        return self._space

    @property
    def scaled_space(self) -> Box:
        """A normalized space with the same shape as :attr:`space`.

        Example:

            >>> box = Box(5, 8, shape=(3,))
            >>> Scaler(box).scaled_space
            Box([-1. -1. -1.], [1. 1. 1.], (3,), float32)
            >>> Scaler(box, symmetric=False).scaled_space
            Box([0. 0. 0.], [1. 1. 1.], (3,), float32)
        """
        return Box(
            -1 if self._symmetric else 0,
            1,
            shape=self.space.shape,
            dtype=self.space.dtype,
        )


def scale_from_box(
    space: Box, unnormalized: np.ndarray, *, symmetric: bool = True
) -> np.ndarray:
    """Normalize an array into [−1; +1] or [0; 1].

    This is a convenience wrapper around :meth:`Scaler.scale()`.
    """
    return Scaler(space, symmetric=symmetric).scale(unnormalized)


def unscale_into_box(
    space: Box, normalized: np.ndarray, *, symmetric: bool = True
) -> np.ndarray:
    """Denormalize an array from [−1; +1] or [0; 1].

    This is a convenience wrapper around :meth:`Scaler.unscale()`.
    """
    return Scaler(space, symmetric=symmetric).unscale(normalized)
