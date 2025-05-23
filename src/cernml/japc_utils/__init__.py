# SPDX-FileCopyrightText: 2020-2024 CERN
# SPDX-FileCopyrightText: 2023-2024 GSI Helmholtzzentrum für Schwerionenforschung
# SPDX-FileNotice: All rights not expressly granted are reserved.
#
# SPDX-License-Identifier: GPL-3.0-or-later OR EUPL-1.2+

"""Convenience wrappers around the `~pyjapc.PyJapc` API.

Most importantly, this package provides *parameter streams*, an
abstraction on top of subscription handles. They pass an internal
callback to `~pyjapc.PyJapc` and expose methods to wait until the
next value has arrived. Parameter streams are created via
`subscribe_stream()`.
"""

from __future__ import annotations

import abc
import contextlib
import datetime
import logging
import sys
import threading
import typing as t
from collections import deque
from functools import update_wrapper

if sys.version_info < (3, 12):
    from typing_extensions import override
else:
    from typing import override

if t.TYPE_CHECKING:
    import cern.japc.core
    import pyjapc

    from cernml.coi import cancellation

__all__ = (
    "Header",
    "JavaException",
    "ParamGroupStream",
    "ParamStream",
    "StreamError",
    "monitoring",
    "subscribe_stream",
    "subscriptions",
)


LOG = logging.getLogger(__name__)


class StreamError(Exception):
    """A logical error while operating on a stream."""


class JavaException(Exception):
    """An error occurred on the Java side."""


class Header(dict):
    """Convenience wrapper around the JAPC header.

    This is a dict for all intents and purposes, but also allows
    attribute access to the most common fields.
    """

    @property
    def acquisition_stamp(self) -> datetime.datetime:
        """Accesses the header's acquisition timestamp."""
        return self["acqStamp"]

    @property
    def cycle_stamp(self) -> datetime.datetime:
        """Accesses the header's begin-of-cycle timestamp."""
        return self["cycleStamp"]

    @property
    def set_stamp(self) -> datetime.datetime:
        """Accesses the header's setting timestamp."""
        return self["setStamp"]

    @property
    def selector(self) -> str:
        """Accesses the header's timing selector."""
        return self["selector"]

    @property
    def is_first_update(self) -> bool:
        """Accesses the header's first-update flag."""
        return self["isFirstUpdate"]

    @property
    def is_immediate_update(self) -> bool:
        """Accesses the header's immediate-update flag."""
        return self["isImmediateUpdate"]


T = t.TypeVar("T")
_OneOrList = t.Union[T, list[T]]
_Item = _OneOrList[tuple[object, Header]]
_Event = t.Union[_Item, JavaException]


def _unwrap_event(event: _Event) -> _Item:
    if isinstance(event, JavaException):
        raise event
    return event


@contextlib.contextmanager
def subscriptions(japc: "pyjapc.PyJapc") -> t.Iterator["pyjapc.PyJapc"]:
    """Return a :term:`context manager` for `~pyjapc.PyJapc`.

    When entering this context, all subscriptions made through the given
    `~pyjapc.PyJapc` object are started. When exiting, they are all
    stopped. This is neither reentrant nor reusable: You should make a
    new call for each :keyword:`with` statement.

    Usage:

        >>> from pyjapc import PyJapc
        >>> def main():
        ...     japc = PyJapc()
        ...     ... # Subscribe to various parameters.
        ...     with subscriptions(japc):
        ...         ... # Subscriptions are active here.
        ...     ... # Subscriptions are stopped here.
    """
    japc.startSubscriptions()
    try:
        yield japc
    finally:
        japc.stopSubscriptions()


# Fix up return type annotation for the docs.
subscriptions.__annotations__["return"] = contextlib.AbstractContextManager[
    "pyjapc.PyJapc"
]


@contextlib.contextmanager
def monitoring(handle: T) -> t.Iterator[T]:
    """Return a :term:`context manager` for JAPC subscription handles.

    When entering this context, the given subscription handle starts
    monitoring. When exiting, it stops. This is neither reentrant nor
    reusable: You should make a new call for each :keyword:`with`
    statement.

    Usage:

        >>> from pyjapc import PyJapc
        >>> def main():
        ...     japc = PyJapc()
        ...     handle = japc.subscribeParam(...)
        ...     with monitoring(handle):
        ...         ... # Subscription is active here.
        ...     ... # Subscription are stopped here.
    """
    # Avoid annotating Java types; bringing them into scope is more of a
    # headache than it gains us.
    t.cast(t.Any, handle).startMonitoring()
    try:
        yield handle
    finally:
        t.cast(t.Any, handle).stopMonitoring()


# Fix up return type annotation for the docs.
monitoring.__annotations__["return"] = contextlib.AbstractContextManager["T"]  # type: ignore[valid-type]


class _BaseStream(metaclass=abc.ABCMeta):
    """A synchronized PyJapc subscription handle.

    Do not instantiate this class yourself. Use
    `subscribe_stream()` instead.

    This class contains the common logic of `ParamStream` and
    `ParamGroupStream`. The subclasses only contain thin wrapper
    methods that perform some type casting. The whole reason for this
    setup is to communicate via types whether a stream may return an
    object or a list of objects.
    """

    Self = t.TypeVar("Self", bound="_BaseStream")

    def __init__(
        self,
        japc: "pyjapc.PyJapc",
        name: str | list[str] | tuple[str, ...],
        *,
        token: cancellation.Token | None,
        maxlen: int | None,
        **kwargs: t.Any,
    ) -> None:
        self._handle = japc.subscribeParam(
            name,
            onValueReceived=self._on_value,
            onException=self._on_exception,
            getHeader=True,
            **kwargs,
        )
        self._queue: deque[_Event] = deque(maxlen=maxlen)
        # If we get a token, we reuse its condition variable. This is
        # the only reasonable way to wait for _either_ a cancellation
        # _or_ a new JAPC event.
        self._token = token
        self._condition = token.wait_handle if token else threading.Condition()

    def __enter__(self: Self) -> Self:
        self.start_monitoring()
        return self

    def __exit__(self, *args: object) -> None:
        self.stop_monitoring()

    @property
    def token(self) -> cancellation.Token | None:
        """The stream's cancellation token, if any.

        While the stream is inactive (``self.monitoring is False``), the
        token may be replaced with another
        `~cernml.coi.cancellation.Token`. This may be useful to
        restart the stream after a cancellation.

        Raises:
            StreamError: If attempting to set the token while the stream
                is monitoring its parameter. This is to prevent
                hard-to-track-down deadlocks in which the stream waits
                on a stale token.
        """
        return self._token

    @token.setter
    def token(self, token: cancellation.Token | None) -> None:
        if self.monitoring:
            raise StreamError("cannot change cancellation token while monitoring")
        # See comment in __init__(). We need to keep token and condition
        # variable in sync to not miss any events.
        self._token = token
        self._condition = token.wait_handle if token else threading.Condition()

    @property
    def monitoring(self) -> bool:
        """True if this stream is receiving values, False otherwise."""
        return self._handle.isMonitoring()

    def start_monitoring(self) -> None:
        """Start receiving values on this stream."""
        self._handle.startMonitoring()

    def stop_monitoring(self) -> None:
        """Stop receiving values on this stream."""
        self._handle.stopMonitoring()

    def clear(self) -> None:
        """Empty the queue."""
        with self._condition:
            self._queue.clear()

    @contextlib.contextmanager
    def locked(self) -> t.Iterator[None]:
        """Return a :term:`context manager` that locks this stream.

        Locking the stream may prevent `TOC/TOU
        <https://en.wikipedia.org/wiki/Time-of-check_to_time-of-use>`_
        errors. While the stream is locked, no new items can be enqueued
        by the subscription handler. You should lock the stream only for
        short periods of time; blocking the subscription handler for too
        long risks that data gets lost.

        However, you *may* call `pop_or_wait()` while the stream
        is locked. It automatically releases the lock while waiting.

        The returned context manager is neither reentrant nor reusable
        nor meaningful. Call this method again to get new or nested
        locks.

        Example:

            >>> def take_newest(
            ...     stream: ParamStream
            ... ) -> t.Tuple[object, Header]:
            ...     '''Return the latest value, discard all others.'''
            ...     with stream.locked():
            ...         if stream.ready:
            ...             value = stream.newest
            ...             # Without the lock, the subscription handler
            ...             # might enqueue an item here, which would be
            ...             # lost forever.
            ...             stream.clear()
            ...             return value
            ...         # `ParamStream` uses a reentrant lock, so
            ...         # nothing bad happens if you call
            ...         # `pop_or_wait()` while it is locked.
            ...         return stream.pop_or_wait()
        """
        with self._condition:
            yield

    @property
    def ready(self) -> bool:
        """True if there is an event in the queue."""
        with self._condition:
            return bool(self._queue)

    @property
    @abc.abstractmethod
    def oldest(self) -> _Item:
        """The oldest item in the queue.

        Raises:
            IndexError: if the queue is empty.
            JavaException: if an exception occurred on the Java side
                while receiving this value.
        """
        with self._condition:
            event = self._queue[0]
        return _unwrap_event(event)

    @property
    @abc.abstractmethod
    def newest(self) -> _Item:
        """The most recent item in the queue.

        Raises:
            IndexError: if the queue is empty.
            JavaException: if an exception occurred on the Java side
                while receiving this value.
        """
        with self._condition:
            event = self._queue[-1]
        return _unwrap_event(event)

    # Tricky: We write the docstring on this internal method and
    # dynamically copy it onto the public method in the subclasses.
    def _pop_or_wait(self, timeout: float | None) -> _Item | None:
        """Return the next item from the queue or wait for one.

        If there already is an item in the queue, it is removed and this
        function returns it immediately. If there is none, this function
        blocks and waits for a new value to arrive.

        Args:
            timeout: If passed and not None, the amount of time (in
                seconds) for which to wait if there is no value in the
                queue.

        Returns:
            The oldest value in the queue or, if there is none, the next
            value received. None if the specified timeout elapses before
            a new value has arrived.

        Raises:
            ~cernml.coi.cancellation.CancelledError: if a
                `~cernml.coi.cancellation.Token` has been passed
                to `subscribe_stream()` and the token has been
                cancelled.
            JavaException: if an exception occurred on the Java side
                while receiving this value.
            StreamError: if the queue is empty, the subscription is not
                active and no timeout has been specified; this serves to
                prevent a deadlock in the application.
        """
        # Prevent deadlock.
        if not self.monitoring and timeout is None and not self._queue:
            raise StreamError("would deadlock")
        with self._condition:
            if self._token:
                self._token.raise_if_cancellation_requested()
            while not self._queue:
                # Threading: This wait may return for three reasons: 1.
                # a new item has arrived, 2. our cancellation token has
                # been cancelled, 3. the timeout has expired. We must
                # check all three.
                success = self._condition.wait(timeout)
                if self._token:
                    self._token.raise_if_cancellation_requested()
                if not success:
                    return None
            event = self._queue.popleft()
        return _unwrap_event(event)

    # Tricky: We write the docstring on this internal method and
    # dynamically copy it onto the public method in the subclasses.
    def _pop_if_ready(self) -> _Item | None:
        """Return the next value or None if the queue is empty.

        This is similar to ``pop_or_wait(timeout=0.0)``, but never
        checks the token for a cancellation request.

        Raises:
            JavaException: if an exception occurred on the Java side
                while receiving this value.
        """
        with self._condition:
            if self._queue:
                event = self._queue.popleft()
                return _unwrap_event(event)
        return None

    # Tricky: We write the docstring on this internal method and
    # dynamically copy it onto the public method in the subclasses.
    def _wait_for_next(self, timeout: float | None = None) -> _Item | None:
        """Clear the queue and wait for a new item to arrive.

        This is like calling `clear()` followed by
        `pop_or_wait()`, but does not release the lock in-between.
        In any case, the queue is empty after this call.

        Args:
            timeout: If passed and not None, the amount of time (in
                seconds) for which to wait.

        Returns:
            The next value to arrive. None if the specified timeout
            elapses before a new value has arrived.

        Raises:
            ~cernml.coi.cancellation.CancelledError: if a
                `~cernml.coi.cancellation.Token` has been passed
                to `subscribe_stream()` and the token has been
                cancelled.
            JavaException: if an exception occurred on the Java side
                while receiving this value.
            StreamError: if the subscription is not active and no
                timeout has been specified; this serves to prevent a
                deadlock in the application.
        """
        with self.locked():
            self.clear()
            return self._pop_or_wait(timeout)

    def _on_value(
        self,
        names: _OneOrList[str],
        values: t.Any,
        headers: _OneOrList[dict] | None,
    ) -> None:
        assert headers is not None, "we always pass getHeader=True"
        with self._condition:
            event: _Event
            if isinstance(names, str):
                event = (t.cast(object, values), Header(t.cast(dict, headers)))
            else:
                event = [
                    (value, Header(header))
                    for value, header in zip(
                        t.cast(list[object], values), t.cast(list[dict], headers)
                    )
                ]
            self._queue.append(event)
            # Threading: Notify all will wake up all threads waiting for
            # new data. They will race for `self._condition` and only
            # one will acquire it and successfully pop off the queue.
            # The others will find each find an empty queue (after
            # acquiring the lock in turn) and go back to sleep.
            # Threading: We cannot use `notify()` because we share our
            # condition variable with `self._token`. A thread that waits
            # only on the token might be woken up and none of the
            # threads waiting on the queue would be the wiser.
            self._condition.notify_all()

    def _on_exception(
        self, _names: _OneOrList[str], _desc: str, exc: Exception
    ) -> None:
        with self._condition:
            self._queue.append(JavaException(exc))
            # Threading: See comment in `_on_value()`.
            self._condition.notify_all()


class ParamStream(_BaseStream):
    """A synchronized handle to a one-parameter PyJapc subscription.

    Typically you use `subscribe_stream()` to instantiate this
    class.
    """

    # Ignore missing docstring: we copy a few from non-public methods on
    # _BaseStream onto public methods of this class.
    # pylint: disable = missing-function-docstring

    def __init__(
        self,
        japc: "pyjapc.PyJapc",
        name: str,
        *,
        token: cancellation.Token | None,
        maxlen: int | None,
        **kwargs: t.Any,
    ) -> None:
        super().__init__(japc, name, token=token, maxlen=maxlen, **kwargs)

    def __str__(self) -> str:
        return f"<{type(self).__name__}({self.parameter_name!r})>"

    def __repr__(self) -> str:
        return (
            f"<{type(self).__name__}(<PyJapc>, "
            f"{self.parameter_name!r}, {self.token!r}, "
            f"{self._queue.maxlen!r})>"
        )

    @property
    def parameter_name(self) -> str:
        """The name of the stream's underlying parameter."""
        handle = t.cast("cern.japc.core.SubscriptionHandle", self._handle)
        return handle.getParameter().getName()

    @property
    @override
    def oldest(self) -> tuple[object, Header]:
        return t.cast(tuple[object, Header], super().oldest)

    @property
    @override
    def newest(self) -> tuple[object, Header]:
        return t.cast(tuple[object, Header], super().newest)

    @t.overload
    def pop_or_wait(self) -> tuple[object, Header]: ...

    @t.overload
    def pop_or_wait(self, timeout: float) -> tuple[object, Header] | None: ...

    def pop_or_wait(  # noqa: D102
        self, timeout: float | None = None
    ) -> tuple[object, Header] | None:
        return t.cast(tuple[object, Header], super()._pop_or_wait(timeout))

    # Workaround for <https://github.com/python/mypy/issues/17166>.
    update_wrapper(pop_or_wait, _BaseStream._pop_or_wait, assigned=["__doc__"])

    def pop_if_ready(self) -> tuple[object, Header] | None:  # noqa: D102
        return t.cast(tuple[object, Header], super()._pop_if_ready())

    # Workaround for <https://github.com/python/mypy/issues/17166>.
    update_wrapper(pop_if_ready, _BaseStream._pop_if_ready, assigned=["__doc__"])

    @t.overload
    def wait_for_next(self) -> tuple[object, Header]: ...

    @t.overload
    def wait_for_next(self, timeout: float) -> tuple[object, Header] | None: ...

    def wait_for_next(  # noqa: D102
        self, timeout: float | None = None
    ) -> tuple[object, Header] | None:
        return t.cast(tuple[object, Header], super()._wait_for_next(timeout))

    # Workaround for <https://github.com/python/mypy/issues/17166>.
    update_wrapper(wait_for_next, _BaseStream._wait_for_next, assigned=["__doc__"])


class ParamGroupStream(_BaseStream):
    """A synchronized handle to a multi-parameter PyJapc subscription.

    Typically you use `subscribe_stream()` to instantiate this
    class.
    """

    # Ignore missing docstring: we copy a few from non-public methods on
    # _BaseStream onto public methods of this class.
    # pylint: disable = missing-function-docstring

    def __init__(
        self,
        japc: "pyjapc.PyJapc",
        name: list[str] | tuple[str, ...],
        *,
        token: cancellation.Token | None,
        maxlen: int | None,
        **kwargs: t.Any,
    ) -> None:
        super().__init__(japc, name, token=token, maxlen=maxlen, **kwargs)

    def __str__(self) -> str:
        return f"<{type(self).__name__} of {len(self.parameter_names)} parameters>"

    def __repr__(self) -> str:
        return (
            f"<{type(self).__name__}(<PyJapc>, "
            f"{list(self.parameter_names)!r}, {self.token!r}, "
            f"{self._queue.maxlen!r})>"
        )

    @property
    def parameter_names(self) -> tuple[str, ...]:
        """A list with the names of all underlying parameters."""
        handle = t.cast(
            "cern.japc.core.group.GroupSubscriptionHandle",
            self._handle,
        )
        return tuple(handle.getParameterGroup().getNames())

    @property
    @override
    def oldest(self) -> list[tuple[object, Header]]:
        return t.cast(list[tuple[object, Header]], super().oldest)

    @property
    @override
    def newest(self) -> list[tuple[object, Header]]:
        return t.cast(list[tuple[object, Header]], super().newest)

    @t.overload
    def pop_or_wait(self) -> list[tuple[object, Header]]: ...

    @t.overload
    def pop_or_wait(self, timeout: float) -> list[tuple[object, Header]] | None: ...

    def pop_or_wait(  # noqa: D102
        self, timeout: float | None = None
    ) -> list[tuple[object, Header]] | None:
        return t.cast(list[tuple[object, Header]], super()._pop_or_wait(timeout))

    # Workaround for <https://github.com/python/mypy/issues/17166>.
    update_wrapper(pop_or_wait, _BaseStream._pop_or_wait, assigned=["__doc__"])

    def pop_if_ready(self) -> list[tuple[object, Header]] | None:  # noqa: D102
        return t.cast(list[tuple[object, Header]], super()._pop_if_ready())

    # Workaround for <https://github.com/python/mypy/issues/17166>.
    update_wrapper(pop_if_ready, _BaseStream._pop_if_ready, assigned=["__doc__"])

    @t.overload
    def wait_for_next(self) -> list[tuple[object, Header]]: ...

    @t.overload
    def wait_for_next(self, timeout: float) -> list[tuple[object, Header]] | None: ...

    def wait_for_next(  # noqa: D102
        self, timeout: float | None = None
    ) -> list[tuple[object, Header]] | None:
        return t.cast(list[tuple[object, Header]], super()._wait_for_next(timeout))

    # Workaround for <https://github.com/python/mypy/issues/17166>.
    update_wrapper(wait_for_next, _BaseStream._wait_for_next, assigned=["__doc__"])


@t.overload
def subscribe_stream(
    japc: "pyjapc.PyJapc",
    name_or_names: str,
    *,
    token: cancellation.Token | None = ...,
    maxlen: int | None = ...,
    convert_to_python: bool = ...,
    selector: str | None = ...,
    data_filter: dict[str, t.Any] | None = ...,
) -> ParamStream: ...


# Note: `name_or_names` is annotated as a list on purpose. The reason is
# that Python's strings themselves are collections of strings:
# `list("foo") == ["f", "o", "o"]`. Hence, `t.Collection[str]` and
# `t.Iterable[str]` will conflict with plain `str`. This likely will
# never be fixable.
@t.overload
def subscribe_stream(
    japc: "pyjapc.PyJapc",
    name_or_names: list[str] | tuple[str, ...],
    *,
    token: cancellation.Token | None = ...,
    maxlen: int | None = ...,
    convert_to_python: bool = ...,
    selector: str | None = ...,
    data_filter: dict[str, t.Any] | None = ...,
) -> ParamGroupStream: ...


def subscribe_stream(
    japc: "pyjapc.PyJapc",
    name_or_names: str | list[str] | tuple[str, ...],
    *,
    token: cancellation.Token | None = None,
    maxlen: int | None = 1,
    convert_to_python: bool = True,
    selector: str | None = None,
    data_filter: dict[str, t.Any] | None = None,
) -> ParamStream | ParamGroupStream:
    """Subscribe to a parameter and create a stream of its values.

    The returned stream synchronizes with the subscription handler to
    ensure that no race conditions occur. It provides methods that allow
    the caller to fetch the latest value or to wait for the next one to
    arrive. By default, the stream also maintains a queue to reduce the
    risk of losing values.

    Args:
        japc: The `~pyjapc.PyJapc` object on which to subscribe.
        name_or_names: The parameter(s) to which to subscribe. Pass a
            single string to subscribe to a parameter, a list of strings
            to subscribe to a parameter group.
        token: If passed, the stream will hold onto this
            `~cernml.coi.cancellation.Token` and watch it. In
            this case, `~ParamStream.pop_or_wait()` can get
            cancelled through the token.
        maxlen: The maximum length of the stream's internal queue. The
            default is 1, i.e. only the most recent value is retained.
            If None, there is no limit and the queue might grow beyond
            all bounds if not emptied regularly.
        convert_to_python: If passed and False, return raw Java objects.
            By default, JAPC attempts to convert Java objects to Python
            objects.
        selector: If passed, use this instead of the default timing
            selector of *japc*.
        data_filter: If passed, use this instead of the default data
            filter of *japc*.

    Returns:
        A `ParamStream` for a single parameter and a
        `ParamGroupStream` for a parameter group.

    Note:
        The synchronization happens purely on a threading level. No
        timestamps are inspected or acted upon. If you need to ensure
        certain timing behavior, you must inspect the `Header`
        returned by the stream.

    The returned parameter streams are :term:`context managers <context
    manager>`. Entering their context starts monitoring their handle,
    exiting stops it. They are reusable, but not re-entrant. This means
    the *same* stream may be used in subsequent :keyword:`with` blocks,
    but not in nested ones.

        >>> def run_analysis(japc: "PyJapc") -> None:
        ...     stream = subscribe_stream(japc, "device/property#field")
        ...     with stream:
        ...         values_and_headers = [
        ...             stream.pop_or_wait() for _ in range(10)
        ...         ]
        ...     values, headers = zip(*values_and_headers)
        ...     ...
    """
    subscribe_kwargs: dict[str, t.Any] = {"noPyConversion": not convert_to_python}
    if selector is not None:
        subscribe_kwargs["timingSelectorOverride"] = selector
    if data_filter is not None:
        subscribe_kwargs["dataFilterOverride"] = data_filter
    if isinstance(name_or_names, str):
        return ParamStream(
            japc, name_or_names, token=token, maxlen=maxlen, **subscribe_kwargs
        )
    return ParamGroupStream(
        japc, name_or_names, token=token, maxlen=maxlen, **subscribe_kwargs
    )
