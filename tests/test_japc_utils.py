# SPDX-FileCopyrightText: 2020-2024 CERN
# SPDX-FileCopyrightText: 2023-2024 GSI Helmholtzzentrum für Schwerionenforschung
# SPDX-FileNotice: All rights not expressly granted are reserved.
#
# SPDX-License-Identifier: GPL-3.0-or-later OR EUPL-1.2+

"""Test the JAPC utilities."""

from __future__ import annotations

import logging
import threading
import time
import typing as t
from unittest.mock import ANY, Mock

import pytest

from cernml import japc_utils
from cernml.coi import cancellation

if t.TYPE_CHECKING:
    import pyjapc


def test_monitoring() -> None:
    with japc_utils.monitoring(Mock()) as handle:
        handle.startMonitoring.assert_called_once_with()
    handle.stopMonitoring.assert_called_once_with()


def test_subscriptions() -> None:
    with japc_utils.subscriptions(Mock()) as japc:
        t.cast(Mock, japc.startSubscriptions).assert_called_once_with()
    t.cast(Mock, japc.stopSubscriptions).assert_called_once_with()


def mock_header() -> japc_utils.Header:
    keys = [
        "acqStamp",
        "cycleStamp",
        "setStamp",
        "selector",
        "isFirstUpdate",
        "isImmediateUpdate",
    ]
    return japc_utils.Header({key: Mock() for key in keys})


class MockJapc:
    """A minimal mock of PyJapc. Instantiate via `mock_japc()`.

    This only provides a `subscribeParam()` method that returns a
    mock handle. The values that are published by this mock handle are
    determined in the constructor.

    The argument is either a list or a mapping from strings to lists. In
    the former case, the same list (or rather, a copy) is passed to each
    subscription handle as a list of mock values. In the latter case,
    the subscription parameter's name is used as a key into the mapping
    to retrieve the list of mock values.
    """

    TIME_STEP_SECONDS = 0.01

    def __init__(self, mock_values: list | dict[str, list]) -> None:
        self.mock_values = mock_values

    def subscribeParam(
        self,
        name: str | list[str],
        onValueReceived: t.Callable,
        onException: t.Callable,
        **kwargs: t.Any,
    ) -> MockSubscriptionHandle:
        if isinstance(name, str):
            mock_values = (
                self.mock_values[name]
                if isinstance(self.mock_values, dict)
                else self.mock_values
            )
        else:
            mock_values = (
                [self.mock_values[n] for n in name]
                if isinstance(self.mock_values, dict)
                else (len(name) * [self.mock_values])
            )
            mock_values = list(zip(*mock_values))
        return MockSubscriptionHandle(
            name_or_names=name,
            on_value=onValueReceived,
            on_exception=onException,
            mock_values=mock_values,
            time_step=self.TIME_STEP_SECONDS,
            **kwargs,
        )


class MockSubscriptionHandle:
    """Return value of `MockJapc.subscribeParam()`.

    This is a mock of PyJapc subscription handles. It contains a list of
    arbitrary values. Whenever monitoring starts, it spins up a thread
    that publishes each item of this list in turn. Once it has iterated
    over this list, the thread ends and no further items are published.
    When monitoring is stopped and restarted, iteration starts from the
    beginning. The time between two item publications is at least
    `time_step` seconds.
    """

    def __init__(
        self,
        name_or_names: str | list[str],
        *,
        on_value: t.Callable,
        on_exception: t.Callable,
        mock_values: list,
        time_step: float,
        **kwargs: t.Any,
    ) -> None:
        self.thread: threading.Thread | None = None
        self.name = name_or_names
        self.on_value = on_value
        self.on_exception = on_exception
        self.mock_values = list(mock_values)
        self.time_step = time_step
        self.init_kwargs = kwargs
        if not isinstance(name_or_names, str):
            assert all(
                isinstance(iteration, Exception) or len(iteration) == len(self.name)
                for iteration in self.mock_values
            ), self.mock_values

    def isMonitoring(self) -> bool:
        return bool(self.thread)

    def startMonitoring(self) -> None:
        assert not self.thread
        self.thread = threading.Thread(target=self._thread_func)
        self.thread.start()

    def stopMonitoring(self) -> None:
        assert self.thread
        thread = self.thread
        self.thread = None
        thread.join()

    def getParameter(self) -> Mock:
        assert isinstance(self.name, str), "getParameter"
        parameter = Mock()
        parameter.getName.return_value = self.name
        return parameter

    def getParameterGroup(self) -> Mock:
        assert not isinstance(self.name, str), "getParameterGroup"
        parameter_group = Mock()
        parameter_group.getNames.return_value = list(self.name)
        return parameter_group

    def _mock_headers(self) -> japc_utils.Header | list[japc_utils.Header]:
        if isinstance(self.name, str):
            return mock_header()
        assert isinstance(self.name, list)
        return [mock_header() for _ in range(len(self.name))]

    def _thread_func(self) -> None:
        logging.info("starting thread")
        assert self.on_value is not None
        assert self.on_exception is not None
        for value in self.mock_values:
            time.sleep(self.time_step)
            if not self.isMonitoring():
                break
            if isinstance(value, Exception):
                self.on_exception(self.name, str(value), value)
            else:
                logging.info("sending %s", value)
                self.on_value(self.name, value, self._mock_headers())
                logging.info("sent %s", value)
        logging.info("terminating thread")


def mock_japc(
    mock_values: list | dict[str, list],
) -> "pyjapc.PyJapc":
    """Create a `MockJapc` that behaves like a `PyJapc`."""
    return t.cast("pyjapc.PyJapc", MockJapc(mock_values))


def extract_mock_handle(
    stream: japc_utils.ParamStream | japc_utils.ParamGroupStream,
) -> MockSubscriptionHandle:
    return t.cast(MockSubscriptionHandle, stream._handle)


def test_header() -> None:
    header = mock_header()
    assert header.acquisition_stamp is header["acqStamp"]
    assert header.cycle_stamp is header["cycleStamp"]
    assert header.set_stamp is header["setStamp"]
    assert header.selector is header["selector"]
    assert header.is_first_update is header["isFirstUpdate"]
    assert header.is_immediate_update is header["isImmediateUpdate"]


def test_str_single() -> None:
    name = "single_name"
    stream = japc_utils.subscribe_stream(mock_japc([]), name)
    assert str(stream) == f"<ParamStream({name!r})>"


def test_str_multiple() -> None:
    names = ["multiple", "names"]
    stream = japc_utils.subscribe_stream(mock_japc([]), names)
    assert str(stream) == f"<ParamGroupStream of {len(names)} parameters>"


def test_repr_single() -> None:
    name = "single_name"
    token = Mock()
    maxlen = 1357
    expected = f"<ParamStream(<PyJapc>, {name!r}, {token!r}, {maxlen!r})>"
    stream = japc_utils.subscribe_stream(
        mock_japc([]), name, token=token, maxlen=maxlen
    )
    assert repr(stream) == expected


def test_repr_multiple() -> None:
    names = ["multiple", "names"]
    token = Mock()
    maxlen = 7531
    expected = f"<ParamGroupStream(<PyJapc>, {names!r}, {token!r}, {maxlen!r})>"
    stream = japc_utils.subscribe_stream(
        mock_japc([]), names, token=token, maxlen=maxlen
    )
    assert repr(stream) == expected


def test_timing_selector_and_data_filter() -> None:
    data_filter = Mock()
    selector = Mock()
    expected = {
        "timingSelectorOverride": selector,
        "dataFilterOverride": data_filter,
        "getHeader": True,
        "noPyConversion": False,
    }
    stream = japc_utils.subscribe_stream(
        mock_japc([]), "", data_filter=data_filter, selector=selector
    )
    handle = extract_mock_handle(stream)
    assert handle.init_kwargs == expected


def test_receive_values() -> None:
    expected = [Mock(name=f"Sent #{i+1}") for i in range(3)]
    japc = mock_japc(expected)
    stream = japc_utils.subscribe_stream(japc, "")
    with stream:
        received = [stream.pop_or_wait()[0] for _ in range(3)]
        assert stream.pop_or_wait(2 * MockJapc.TIME_STEP_SECONDS) is None
    assert received == expected


def test_receive_group() -> None:
    sent_values = {
        "param_a": [Mock(name="value for param_a")],
        "param_b": [Mock(name="value for param_b")],
    }
    expected = tuple(v[0] for v in sent_values.values())
    japc = mock_japc(sent_values)
    stream = japc_utils.subscribe_stream(japc, ["param_a", "param_b"])
    with stream:
        data = stream.pop_or_wait()
        values, headers = zip(*data)
    assert values == expected
    assert all(isinstance(h, japc_utils.Header) for h in headers), headers


def test_block_without_values() -> None:
    japc = mock_japc([])
    stream = japc_utils.subscribe_stream(japc, "")
    with stream:
        assert stream.pop_or_wait(2 * MockJapc.TIME_STEP_SECONDS) is None


def test_raise_if_not_monitoring() -> None:
    japc = mock_japc([])
    stream = japc_utils.subscribe_stream(japc, "")
    with pytest.raises(japc_utils.StreamError):
        stream.pop_or_wait()
    assert stream.pop_or_wait(MockJapc.TIME_STEP_SECONDS) is None


def test_queue_maxlen_is_one() -> None:
    sent_values = [Mock(name=f"Sent value #{i+1}") for i in range(3)]
    japc = mock_japc(sent_values)
    stream = japc_utils.subscribe_stream(japc, "")
    with stream:
        handle = extract_mock_handle(stream)
        assert handle.thread is not None
        handle.thread.join()
        all_available = [value for value, _header in iter(stream.pop_if_ready, None)]
    assert all_available == sent_values[-1:]


def test_queue_without_maxlen() -> None:
    sent_values = [Mock(name=f"Sent value #{i+1}") for i in range(5)]
    japc = mock_japc(sent_values)
    stream = japc_utils.subscribe_stream(japc, "", maxlen=None)
    with stream:
        handle = extract_mock_handle(stream)
        assert handle.thread is not None
        handle.thread.join()
        all_available = [value for value, _header in iter(stream.pop_if_ready, None)]
    assert all_available == sent_values


def test_pop_if_ready_doesnt_block() -> None:
    sent_values = [Mock() for _ in range(2)]
    japc = mock_japc(sent_values)
    stream = japc_utils.subscribe_stream(japc, "", maxlen=None)
    with stream:
        first, _ = stream.pop_or_wait()
        assert stream.pop_if_ready() is None
        second, _ = stream.pop_or_wait()
    assert [first, second] == sent_values


def test_locked_prevents_updates() -> None:
    sent_values = [Mock(name="Sent value")]
    japc = mock_japc(sent_values)
    stream = japc_utils.subscribe_stream(japc, "")
    with stream:
        assert not stream.ready
        with stream.locked():
            # Wait long enough that the thread calls the subscription
            # handler. This blocks because we're holding the lock.
            time.sleep(2 * MockJapc.TIME_STEP_SECONDS)
            assert not stream.ready
        # Threading: Ensure that the thread has time to acquire the lock
        # and send its data.
        time.sleep(MockJapc.TIME_STEP_SECONDS)
    assert stream.ready


def test_clear() -> None:
    sent_values = [Mock(name="Sent value")]
    japc = mock_japc(sent_values)
    stream = japc_utils.subscribe_stream(japc, "")
    with stream:
        assert not stream.ready
        # Wait until the thread has sent its data.
        handle = extract_mock_handle(stream)
        assert handle.thread is not None
        handle.thread.join()
    assert stream.ready
    assert [stream.oldest[0]] == [stream.newest[0]] == sent_values
    stream.clear()
    assert not stream.ready


def test_stream_token() -> None:
    japc = mock_japc([])
    token = cancellation.Token()
    stream = japc_utils.subscribe_stream(japc, "", token=token)
    assert token is stream.token
    new_token = cancellation.Token()
    stream.token = new_token
    assert token is not stream.token
    assert new_token is stream.token
    with stream:
        assert stream.monitoring
        with pytest.raises(japc_utils.StreamError, match="while monitoring"):
            stream.token = token
        assert stream.token is new_token
    stream.token = None
    assert new_token is not stream.token
    assert stream.token is None


@pytest.mark.parametrize("name", ["", [""]])
def test_wait_for_next_clears_queue(name: str | list[str]) -> None:
    sent_values = [Mock(name=f"Sent value #{i+1}") for i in range(5)]
    expected_return_values = [
        (v, ANY) if isinstance(name, str) else [(v, ANY)] for v in sent_values
    ]
    japc = mock_japc(sent_values)
    token = cancellation.Token()
    stream = japc_utils.subscribe_stream(japc, name, maxlen=3, token=token)
    with stream:
        cond = token.wait_handle
        with cond:
            # Wait until the queue is full.
            cond.wait_for(lambda: stream.ready)
            cond.wait_for(lambda: stream.oldest != expected_return_values[0])
            # Fetch the next value. The queue holds three items, one has
            # been pushed out, so the next one must be the fifth.
            assert stream.wait_for_next() == expected_return_values[4]
            # The queue must be empty.
            with pytest.raises(IndexError):
                _ = stream.oldest


@pytest.mark.parametrize("name", ["", [""]])
def test_oldest_newest(name: str | list[str]) -> None:
    sent_values = [Mock(name=f"Sent value #{i+1}") for i in range(2)]
    expected_return_values = [
        (v, ANY) if isinstance(name, str) else [(v, ANY)] for v in sent_values
    ]
    japc = mock_japc(sent_values)
    stream = japc_utils.subscribe_stream(japc, name, maxlen=2)
    with stream:
        # Wait until the thread has sent its data.
        handle = extract_mock_handle(stream)
        assert handle.thread is not None
        handle.thread.join()
    first = stream.oldest
    second = stream.newest
    assert [first, second] == expected_return_values
    assert stream.ready
    assert stream.pop_if_ready() == first
    assert stream.pop_if_ready() == second
    assert stream.pop_if_ready() is None
    assert not stream.ready


def test_exception() -> None:
    sent_values = [Mock(), Mock(), ValueError()]
    japc = mock_japc(sent_values)
    stream = japc_utils.subscribe_stream(japc, "")
    with stream:
        received = []
        with pytest.raises(japc_utils.JavaException):  # noqa: PT012
            while True:
                value, _ = stream.pop_or_wait()
                received.append(value)
    assert received == sent_values[:-1]


def test_cancel() -> None:
    token = cancellation.Token(cancelled=True)
    japc = mock_japc([Mock()])
    stream = japc_utils.subscribe_stream(japc, "", token=token)
    with pytest.raises(cancellation.CancelledError), stream:
        stream.pop_or_wait()
    assert not stream.ready


def test_cancel_preempts_ready() -> None:
    token = cancellation.Token(cancelled=True)
    japc = mock_japc([Mock()])
    stream = japc_utils.subscribe_stream(japc, "", token=token)
    with stream:
        handle = extract_mock_handle(stream)
        assert handle.thread is not None
        handle.thread.join()
        with pytest.raises(cancellation.CancelledError):
            stream.pop_or_wait()
    assert stream.ready


def test_cancel_breaks_deadlock() -> None:
    sent_values = [Mock() for _ in range(3)]
    japc = mock_japc(sent_values)
    source = cancellation.TokenSource()
    stream = japc_utils.subscribe_stream(japc, "", token=source.token)

    def cancel_delayed() -> None:
        handle = extract_mock_handle(stream)
        assert handle.thread is not None
        handle.thread.join()
        # Add some time to handle the last sent value.
        time.sleep(MockJapc.TIME_STEP_SECONDS)
        source.cancel()

    canceller = threading.Thread(target=cancel_delayed)
    received_values = []
    with stream:
        canceller.start()
        with pytest.raises(cancellation.CancelledError):  # noqa: PT012
            # Would eventually deadlock if not cancelled.
            for value, _ in iter(stream.pop_or_wait, None):
                received_values.append(value)
    canceller.join()
    assert not stream.ready
    assert received_values == sent_values
