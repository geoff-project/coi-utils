..
    SPDX-FileCopyrightText: 2020-2024 CERN
    SPDX-FileCopyrightText: 2023-2024 GSI Helmholtzzentrum für Schwerionenforschung
    SPDX-FileNotice: All rights not expressly granted are reserved.

    SPDX-License-Identifier: GPL-3.0-or-later OR EUPL-1.2+

Managing PyJapc Subscriptions
=============================

.. currentmodule:: cernml.japc_utils

.. note::
    Skip to :ref:`guide/japc_utils:Introducing Parameter Streams` to see usage
    examples.

Motivation
----------

Imagine the following, trivial optimization problem. It talks to two imaginary
devices via `~pyjapc.PyJapc`. We're deliberately ignoring all sorts of
complicating factors, like normalization, configuration or other
transformations:

.. code-block:: python

    from cernml import coi
    from gymnasium.spaces import Box
    from pyjapc import PyJapc

    class ExampleEnv(coi.SingleOptimizable):
        metadata = {
            'cern.machine': coi.Machine.SPS,
            'cern.japc': True,
        }

        optimization_space = Box(-1.0, 1.0, shape=())

        def __init__(self, japc=None):
            if japc is None:
                japc = PyJapc('SPS.USER.ALL')
            self.japc = japc

        def get_initial_params(self, *, seed=None, options=None):
            super().get_initial_params(seed=seed, options=options)
            return self.japc.getParam("SOME.DIPOLE/Settings")

        def compute_single_objective(self, params):
            self.japc.setParam("SOME.DIPOLE/Settings", params)
            return self.japc.getParam("SOME.MONITOR/Acquisition")

This code is (hopefully!) simple enough to understand. However, GET requests
via JAPC are often considered expensive. In most cases, you actually want to
use a SUBSCRIBE request instead. This would look somewhat like this:


.. code-block:: python
    :emphasize-lines: 17-22,24-25,28,36-39

    from cernml import coi
    from gymnasium.spaces import Box
    from pyjapc import PyJapc

    class ExampleEnv(coi.SingleOptimizable):
        metadata = {
            'cern.machine': coi.Machine.SPS,
            'cern.japc': True,
        }

        optimization_space = Box(-1.0, 1.0, shape=())

        def __init__(self, japc=None):
            if japc is None:
                japc = PyJapc('SPS.USER.ALL')
            self.japc = japc
            self.handle = japc.subscribeParam(
                "SOME.MONITOR/Acquisition",
                self._handle_value,
            )
            self.handle.startMonitoring()
            self.latest_value = None  # See 1.

        def _handle_value(self, name, value):  # See 2.
            self.last_value = value

        def close(self):
            self.handle.stopMonitoring()  # See 3.

        def get_initial_params(self, *, seed=None, options=None):
            super().get_initial_params(seed=seed, options=options)
            return self.japc.getParam("SOME.DIPOLE/Settings")

        def compute_single_objective(self, params):
            self.japc.setParam("SOME.DIPOLE/Settings", params)
            self.latest_value = None # See 4.
            while self.latest_value is None:
                time.sleep(1)  # See 5.
            return self.latest_value.copy()

This code already is somewhat more complicated than before. It also has a
number of problems:

1. **We have to define a variable that holds the latest acquired value.**
   This is in addition to the subscription handle. If we have to monitor more
   than one value, this quickly fills our class with lots of variables that are
   difficult to keep track of.

2. **We have to supply our own subscription handler.**
   This code is usually the same and tedius to write. If we want to handle
   errors, we have to supply an additional error handler. This error handler
   cannot throw exceptions (since it is invoked on another thread), so we must
   find another way to propagate the error.

3. **We have to start and stop monitoring the subscription manually.**
   If we forget to start the stream, our environment will simply *deadlock*,
   waiting for an event that will never arrive.

4. **We have to do manually synchronize with the subscription handler.**
   This is very tricky and easy to get wrong. We first invalidate the holding
   variable we defined in #1. Then we spin in a loop until the subscription
   handler sets it to a new value. Much like #2, this is repetitive and hides
   the actual logic of our problem.

5. **The waiting time of one second is completely arbitrary.**
   It may be far too short (if we wait for an SPS supercycle to pass) or far
   too long (if we subscribe to a parameter on a non-multiplexed device).

Synchronization
---------------

For now, let us only focus on the last problem: Figuring out how long exactly
to wait. Luckily, the Python standard library module `threading` provides
multiple primitives for cross-thread synchronization. In our case, we want to
wait on thread A for a condition to become true, and signal such from thread B.
For this, we can use a `~threading.Condition` variable:

.. code-block:: python
    :emphasize-lines: 1,24,28-30,41-44

    from threading import Condition

    from cernml import coi
    from gymnasium.spaces import Box
    from pyjapc import PyJapc

    class ExampleEnv(coi.SingleOptimizable):
        metadata = {
            'cern.machine': coi.Machine.SPS,
            'cern.japc': True,
        }

        optimization_space = Box(-1.0, 1.0, shape=())

        def __init__(self, japc=None):
            if japc is None:
                japc = PyJapc('SPS.USER.ALL')
            self.japc = japc
            self.handle = japc.subscribeParam(
                "SOME.MONITOR/Acquisition",
                self._handle_value,
            )
            self.handle.startMonitoring()
            self.condition = Condition()
            self.latest_value = None

        def _handle_value(self, name, value):
            with self.condition:  # See 1.
                self.last_value = value
                self.condition.notify()

        def close(self):
            self.handle.stopMonitoring()

        def get_initial_params(self, *, seed=None, options=None):
            super().get_initial_params(seed=seed, options=options)
            return self.japc.getParam("SOME.DIPOLE/Settings")

        def compute_single_objective(self, params):
            self.japc.setParam("SOME.DIPOLE/Settings", params)
            with self.condition:  # See 2.
                self.latest_value = None
                self.condition.wait_for(lambda: self.latest_value is not None)
                return self.latest_value.copy()

Once again, the code has become more complicated with logic that only hides the
problem we want to express.

1. Whenever we receive a new value, we lock the condition variable. This
   ensures that our write to ``last_value`` doesn't interleave with the read
   inside :meth:`~cernml.coi.SingleOptimizable.compute_single_objective()` in
   any strange way.
2. To receive a new value, we invalidate the old one (as before), and then
   *wait* until a new value is there. In contrast to :func:`time.sleep()`, this
   uses operating system functionality to wait exactly until the
   :meth:`~threading.Condition.notify()` call has passed.

Introducing Parameter Streams
-----------------------------

The module `cernml.japc_utils` provides *parameter streams*: Objects that wrap
around all the code we had to write manually:

- They wrap around a **subscription handle** and expose methods to start and
  stop monitoring it.
- They contain a **queue of received values** so that you never miss any. By
  default, the queue has a maximum length of one. This is identical to our
  holder variable ``latest_value``.
- They manage a **condition variable** in order to synchronize with the
  subscription handler.
- *In addition*, they install an **error handler**: Any JAPC error is caught
  and raises a Python exception when you attempt to read the next value.

Here is how much they simplify your code:

.. code-block:: python
    :emphasize-lines: 1,17-20,24,32-33

    from cernml import coi, japc_utils
    from gymnasium.spaces import Box
    from pyjapc import PyJapc

    class ExampleEnv(coi.SingleOptimizable):
        metadata = {
            'cern.machine': coi.Machine.SPS,
            'cern.japc': True,
        }

        optimization_space = Box(-1.0, 1.0, shape=())

        def __init__(self, japc=None):
            if japc is None:
                japc = PyJapc('SPS.USER.ALL')
            self.japc = japc
            self.stream = japc_utils.subscribe_stream(  # See 1.
                japc,
                "SOME.MONITOR/Acquisition",
            )
            self.stream.start_monitoring()  # See 2.

        def close(self):
            self.handle.stop_monitoring()  # See 2.

        def get_initial_params(self, *, seed=None, options=None):
            super().get_initial_params(seed=seed, options=options)
            return self.japc.getParam("SOME.DIPOLE/Settings")

        def compute_single_objective(self, params):
            self.japc.setParam("SOME.DIPOLE/Settings", params)
            value, header = self.stream.wait_for_next()  # See 3. and 4.
            return value

1. The `~subscribe_stream()` function call closely mirrors
   :meth:`~pyjapc.PyJapc.subscribeParam()`, but does not require callback
   functions.
2. We still need to start and stop monitoring. In constrast to to PyJapc,
   parameter streams use ``snake_case``-style method names.
3. A single call to `~ParamStream.wait_for_next()` invalidates the queue,
   synchronizes with the subscription handler and waits for the next
   acquisition to arrive. Note that parameter streams always return the JAPC
   header.
4. The *header* variable is an object of type `~cernml.japc_utils.Header`. It
   is mostly a regular dictionary (which you would get from raw subscriptions
   with ``getHeader=True``), but also exposes its most common keys as
   attributes; e.g. :samp:`{header}.acquisition_stamp` is the same as
   :samp:`{header}["acquisition_stamp"]` but is more accessible to IDE
   auto-completion.

There are also methods to support other workflows, such as
`~ParamStream.pop_or_wait()`, `~ParamStream.pop_if_ready()` and
`~ParamStream.clear()`:

.. code-block:: python

    from matplotlib.figure
    from cernml.japc_utils import subscribe_stream

    def process_data(japc):
        stream = subscribe_stream(
            japc,
            "SOME.DEVICE/Property#field",
            maxlen=None,  # Use an unbounded queue.
        )
        while True:
            value, header = stream.pop_or_wait()
            update_plots(value, header.cycle_stamp)

Cancellation Integration
------------------------

Let's extend our previous optimization problem a little. Assume that the device
may have intermittent failures. Maybe it works most of the time, but
occasionally returns data that is all-zeros. Or maybe it monitors an
accelerator that may unexpectedly lose its beam for several cycles. Parameter
streams make this case easy to handle:

.. code-block:: python

    from logging import getLogger

    LOG = getLogger(__name__)

    class ExampleEnv(coi.SingleOptimizable):

        # Rest is the same as before ...

        def compute_single_objective(self, params):
            self.japc.setParam("SOME.DIPOLE/Settings", params)
            while True:
                value, header = self.stream.wait_for_next()
                if value == 0.0:
                    LOG.warning("bad value from SOME.MONITOR")
                    continue
                return value

However, one problem remains: This implementation of
:meth:`~cernml.coi.SingleOptimizable.compute_single_objective()` will not
return for as long as the device failure persists. If this is a long time, the
host application never regains control and its user has no possibility to
interrupt and cancel the operation.

This is the problem that :ref:`cooperative cancellation
<guide/cancellation:cancellation>` aims to solve. We can request a cancellation
`~cernml.coi.cancellation.Token` from the host application and use it to check
whether the user has cancelled our optimization. Parameter streams have full
support for cancellation tokens:

.. code-block:: python
    :emphasize-lines: 5,10,14,18,31-35

    class ExampleEnv(coi.SingleOptimizable):
        metadata = {
            'cern.machine': coi.Machine.SPS,
            'cern.japc': True,
            'cern.cancellable': True,  # See 1.
        }

        optimization_space = Box(-1.0, 1.0, shape=())

        def __init__(self, japc=None, cancellation_token=None):
            if japc is None:
                japc = PyJapc('SPS.USER.ALL')
            self.japc = japc
            self.token = cancellation_token or coi.cancellation.Token()
            self.stream = japc_utils.subscribe_stream(
                japc,
                "SOME.MONITOR/Acquisition",
                token=cancellation_token,  # See 2.
            )
            self.stream.start_monitoring()

        def close(self):
            self.handle.stop_monitoring()

        def get_initial_params(self, *, seed=None, options=None):
            super().get_initial_params(seed=seed, options=options)
            return self.japc.getParam("SOME.DIPOLE/Settings")

        def compute_single_objective(self, params):
            self.japc.setParam("SOME.DIPOLE/Settings", params)
            try:
                value, header = self.stream.wait_for_next()  # See 3.
            except coi.cancellation.CancelledError:
                self.token.complete_cancellation()  # See 4.
                raise
            return value

Some notes as usual:

1. By adding :mdkey:`"cern.cancellable"` to our metadata, we signal to the host
   application that we would like to receive a cancellation token.
2. The only thing that is *strictly* necessary is that you pass the
   cancellation token to `subscribe_stream()`. Everything else is handled for
   us from here.
3. If (and only if) you have given a token to the stream, it will wait on
   *both* a new acquisition *and* a cancellation. If the former happens, we
   receive the new value and return. If the latter happens, the usual
   `~cernml.coi.cancellation.CancelledError` is raised.
4. Since cancellation is *cooperative*, we should cooperate with our host. By
   calling :meth:`~cernml.coi.cancellation.Token.complete_cancellation()`, we
   let it know that we understood the request and brought ourselves into a
   clean state. This way, the host can reuse our object – for example to reset
   ``SOME.DIPOLE`` back to its original state.

Context Managers
----------------

You can monitor parameter streams not only manually (as usual), but you can
also use them in :keyword:`with` statements:

.. code-block:: python

    with japc_utils.subscribe_stream(japc, "SOME.MONITOR/Acquisition") as stream:
        value, header = stream.pop_or_wait()

    # or equivalently:
    stream = japc_utils.subscribe_stream(japc, "SOME.MONITOR/Acquisition")
    with stream:
        value, header = stream.pop_or_wait()

Here, `~ParamStream.start_monitoring()` is called upon entry into the block and
`~ParamStream.stop_monitoring()` is called upon exit. The advantage of
:keyword:`with` statements is that the exit handler is called even if the block
is exited through an exception.

The package provides two additional :term:`context managers <context manager>`:
`~subscriptions()` and `~monitoring()`. They handle raw `~pyjapc.PyJapc`
objects and subscription handles respectively in an analogous manner:

.. code-block:: python

    with japc_utils.subscriptions(japc):
        # japc.startSubscriptions() is called here.
        ...
    # japc.stopSubscriptions() is called here.

    handle = japc.subscribeParam("SOME.MONITOR/Acquisition", print)
    with japc_utils.monitoring(handle):
        # handle.startMonitoring() is called here.
        ...
    # handle.stopMonitoring() is called here.

Parameter Group Streams
-----------------------

Much like `~pyjapc.PyJapc` itself, parameter streams support subscriptions to
multiple parameters at once. If you pass a list of strings to
`subscribe_stream()`, it returns a `ParamGroupStream`:

.. code-block:: python
    :emphasize-lines: 6

    stream = japc_utils.subscribe_stream(japc, ["PARAM1", "PARAM2"])
    with stream:
        data_header_pairs = stream.pop_or_wait()
        for data, header in data_header_pairs:
            ...
        all_data, headers = zip(*data_header_pairs)
        for data in all_data:
            ...

Note that the stream returns a list of value–header tuples. The line
highlighted in the above snippet uses :func:`zip()` to transpose it into
a tuple of one value list and one header list.
