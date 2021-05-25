"""Test the JAPC utilities."""

# pylint: disable = missing-class-docstring
# pylint: disable = missing-function-docstring
# pylint: disable = redefined-outer-name

import logging
import threading
import time
import typing as t
from unittest.mock import ANY, Mock

import pytest
from cernml.coi.unstable import cancellation

from cernml import japc_utils


def test_monitoring() -> None:
    with japc_utils.monitoring(Mock()) as handle:
        handle.startMonitoring.assert_called_once_with()
    handle.stopMonitoring.assert_called_once_with()


def test_subscriptions() -> None:
    with japc_utils.subscriptions(Mock()) as japc:
        japc.startSubscriptions.assert_called_once_with()
    japc.stopSubscriptions.assert_called_once_with()


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
    """A minimal mock of PyJapc.

    This only provides a :meth:`subscribeParam()` method that returns a
    mock handle. The values that are published by this mock handle are
    determined in the constructor.

    The argument is either a list or a mapping from strings to lists. In
    the former case, the same list (or rather, a copy) is passed to each
    subscription handle as a list of mock values. In the latter case,
    the subscription parameter's name is used as a key into the mapping
    to retrieve the list of mock values.
    """

    # pylint: disable = invalid-name
    # pylint: disable = too-few-public-methods

    TIME_STEP_SECONDS = 0.01

    def __init__(self, mock_values: t.Union[list, t.Dict[str, list]]) -> None:
        self.mock_values = mock_values

    def subscribeParam(
        self,
        name: str,
        onValueReceived: t.Callable,
        onException: t.Callable,
        **_kwargs: t.Any,
    ) -> "MockSubscriptionHandle":
        mock_values = (
            self.mock_values[name]
            if isinstance(self.mock_values, dict)
            else self.mock_values
        )
        return MockSubscriptionHandle(
            name=name,
            on_value=onValueReceived,
            on_exception=onException,
            mock_values=mock_values,
            time_step=self.TIME_STEP_SECONDS,
        )


class MockSubscriptionHandle:
    """Return value of :class:`MockJapc.subscribeParam()`.

    This is a mock of PyJapc subscription handles. It contains a list of
    arbitrary values. Whenever monitoring starts, it spins up a thread
    that publishes each item of this list in turn. Once it has iterated
    over this list, the thread ends and no further items are published.
    When monitoring is stopped and restarted, iteration starts from the
    beginning. The time between two item publications is at least
    :attr:`time_step` seconds.
    """

    def __init__(
        self,
        name: str,
        *,
        on_value: t.Callable,
        on_exception: t.Callable,
        mock_values: list,
        time_step: float,
    ) -> None:
        self.name = name
        self.on_value = on_value
        self.on_exception = on_exception
        self.mock_values = list(mock_values)
        self.time_step = time_step
        self.thread: t.Optional[threading.Thread] = None

    # pylint: disable = invalid-name

    def isMonitoring(self) -> bool:
        return bool(self.thread)

    def startMonitoring(self) -> None:
        if self.thread:
            return
        assert self.name is not None, "monitoring started before subscription"
        self.thread = threading.Thread(target=self._thread_func)
        self.thread.start()

    def stopMonitoring(self) -> None:
        if not self.thread:
            return
        thread = self.thread
        self.thread = None
        thread.join()

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
                self.on_value(self.name, value, mock_header())
                logging.info("sent %s", value)
        logging.info("terminating thread")


def extract_mock_handle(stream: japc_utils.ParamStream) -> MockSubscriptionHandle:
    # pylint: disable = protected-access
    return t.cast(MockSubscriptionHandle, stream._handle)


def test_receive_values() -> None:
    expected = [Mock(), Mock(), Mock()]
    japc = MockJapc(expected)
    stream = japc_utils.subscribe_stream(japc, "")
    with stream:
        received = [stream.pop_or_wait()[0] for _ in range(3)]
        assert stream.pop_or_wait(2 * MockJapc.TIME_STEP_SECONDS) is None
    assert received == expected


def test_block_without_values() -> None:
    japc = MockJapc([])
    stream = japc_utils.subscribe_stream(japc, "")
    with stream:
        assert stream.pop_or_wait(2 * MockJapc.TIME_STEP_SECONDS) is None


def test_raise_if_not_monitoring() -> None:
    japc = MockJapc([])
    stream = japc_utils.subscribe_stream(japc, "")
    with pytest.raises(japc_utils.StreamError):
        stream.pop_or_wait()
        assert stream.pop_or_wait(MockJapc.TIME_STEP_SECONDS) is None


def test_queue_maxlen_is_one() -> None:
    sent_values = [Mock() for _ in range(3)]
    japc = MockJapc(sent_values)
    stream = japc_utils.subscribe_stream(japc, "")
    with stream:
        handle = extract_mock_handle(stream)
        assert handle.thread is not None
        handle.thread.join()
        all_available = [value for value, _header in iter(stream.pop_if_ready, None)]
    assert all_available == sent_values[-1:]


def test_queue_without_maxlen() -> None:
    sent_values = [Mock() for _ in range(5)]
    japc = MockJapc(sent_values)
    stream = japc_utils.subscribe_stream(japc, "", maxlen=None)
    with stream:
        handle = extract_mock_handle(stream)
        assert handle.thread is not None
        handle.thread.join()
        all_available = [value for value, _header in iter(stream.pop_if_ready, None)]
    assert all_available == sent_values


def test_pop_if_ready_doesnt_block() -> None:
    sent_values = [Mock() for _ in range(2)]
    japc = MockJapc(sent_values)
    stream = japc_utils.subscribe_stream(japc, "", maxlen=None)
    with stream:
        first, _ = stream.pop_or_wait()
        assert stream.pop_if_ready() is None
        second, _ = stream.pop_or_wait()
    assert [first, second] == sent_values


def test_locked_prevents_updates() -> None:
    sent_values = [Mock()]
    japc = MockJapc(sent_values)
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
    sent_values = [Mock()]
    japc = MockJapc(sent_values)
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


def test_wait_for_next_clears_queue() -> None:
    sent_values = [Mock() for _ in range(5)]
    japc = MockJapc(sent_values)
    token = cancellation.Token()
    stream = japc_utils.subscribe_stream(japc, "", maxlen=3, token=token)
    with stream:
        cond = token.wait_handle
        with cond:
            # Wait until the queue is full.
            cond.wait_for(lambda: stream.ready)
            cond.wait_for(lambda: stream.oldest != (sent_values[0], ANY))
            # Fetch the next value. The queue holds three items, one has
            # been pushed out, so the next one must be the fifth.
            assert stream.wait_for_next() == (sent_values[4], ANY)
            # The queue must be empty.
            with pytest.raises(IndexError):
                _ = stream.oldest


def test_oldest_newest() -> None:
    sent_values = [Mock(), Mock()]
    japc = MockJapc(sent_values)
    stream = japc_utils.subscribe_stream(japc, "", maxlen=2)
    with stream:
        # Wait until the thread has sent its data.
        handle = extract_mock_handle(stream)
        assert handle.thread is not None
        handle.thread.join()
    first = stream.oldest
    second = stream.newest
    assert [first[0], second[0]] == sent_values
    assert stream.ready
    assert stream.pop_if_ready() == first
    assert stream.pop_if_ready() == second
    assert stream.pop_if_ready() is None
    assert not stream.ready


def test_exception() -> None:
    sent_values = [Mock(), Mock(), ValueError()]
    japc = MockJapc(sent_values)
    stream = japc_utils.subscribe_stream(japc, "")
    with stream:
        received = []
        with pytest.raises(japc_utils.JavaException):
            while True:
                value, _ = stream.pop_or_wait()
                received.append(value)
    assert received == sent_values[:-1]


def test_cancel() -> None:
    token = cancellation.Token(cancelled=True)
    japc = MockJapc([Mock()])
    stream = japc_utils.subscribe_stream(japc, "", token=token)
    with pytest.raises(cancellation.CancelledError):
        with stream:
            stream.pop_or_wait()
    assert not stream.ready


def test_cancel_preempts_ready() -> None:
    token = cancellation.Token(cancelled=True)
    japc = MockJapc([Mock()])
    stream = japc_utils.subscribe_stream(japc, "", token=token)
    with pytest.raises(cancellation.CancelledError):
        with stream:
            handle = extract_mock_handle(stream)
            assert handle.thread is not None
            handle.thread.join()
            stream.pop_or_wait()
    assert stream.ready


def test_cancel_breaks_deadlock() -> None:
    sent_values = [Mock() for _ in range(3)]
    japc = MockJapc(sent_values)
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
    with pytest.raises(cancellation.CancelledError):
        received_values = []
        with stream:
            canceller.start()
            # Would eventually deadlock if not cancelled.
            for value, _ in iter(stream.pop_or_wait, None):
                received_values.append(value)
    canceller.join()
    assert not stream.ready
    assert received_values == sent_values
