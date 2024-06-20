..
    SPDX-FileCopyrightText: 2020-2024 CERN
    SPDX-FileCopyrightText: 2023-2024 GSI Helmholtzzentrum für Schwerionenforschung
    SPDX-FileNotice: All rights not expressly granted are reserved.

    SPDX-License-Identifier: GPL-3.0-or-later OR EUPL-1.2+

Simplified Rendering with Matplotlib
====================================

.. currentmodule:: cernml.mpl_utils

The render mode :rmode:`"matplotlib_figures"` makes it possible to create
`matplotlib` plots and have the host application embed them. Updating these
plots correctly is error-prone and the simplest solution – full clear and
redraw on each iteration – is also the slowest one.

More sophisticated solutions maintain the figure state between render updates
and only manipulate the parts of the plot that have changed. This quickly
becomes so complex that it hides the basic structure of the plot.

In addition, the render mode :rmode:`"human"` also often uses Matplotlib, but
in an interactive environment. Supporting both render modes is surprisingly
tricky; see :doc:`mpl:users/explain/figure/api_interfaces` for details.

Managing Figures with ``make_renderer()``
-----------------------------------------

With the `make_renderer()` function, you can turn methods of your class into
`Renderer`\ s: objects that take care of figure management for you. This helps
you avoid polluting your class with figures and other variables that have
nothing to do with your optimization problem.

.. code-block:: python
    :emphasize-lines: 12-14, 19

    >>> from matplotlib.figure import Figure
    >>> from cernml.mpl_utils import make_renderer
    >>> from cernml.coi import SingleOptimizable
    ...
    >>> class MyProblem(SingleOptimizable):
    ...     metadata = {
    ...         "render_modes": ["human", "matplotlib_figures"],
    ...     }
    ...
    ...     def __init__(self, render_mode=None) -> None:
    ...         super().__init__(render_mode)
    ...         self._renderer = make_renderer(
    ...             self.update_figure, render_mode=render_mode
    ...         )
    ...         ...
    ...
    ...     def render(self):
    ...         if self.render_mode in ["human", "matplotlib_figures"]:
    ...             return self._renderer.update()
    ...         return super().render()
    ...
    ...     def update_figure(self, figure: Figure) -> None:
    ...         try:
    ...             [axes] = figure.axes
    ...         except ValueError:
    ...             axes = figure.subplots(nrows=1, ncols=1)
    ...
    ...         axes.clear()
    ...         axes.plot(...)

As you can see, `make_renderer()` returns an object with a method `.update()`.
Whenever you call it, it calls back to our own method ``update_figure()`` and
passes a `.Figure` object along. The `.Figure` is being managed according to
the *render_mode* that we passed in the constructor.

Managing Multiple Renderers
---------------------------

You can also pass multiple methods to `make_renderer()`. In that case,
calling `.update()` will call back to each passed method one after the other.
You can also pass a `dict`, in which case the string keys are used as window
titles:

.. code-block:: python
    :emphasize-lines: 12-15, 20

    >>> from matplotlib.figure import Figure
    >>> from cernml.mpl_utils import make_renderer
    >>> from cernml.coi import SingleOptimizable
    ...
    >>> class MyProblem(SingleOptimizable):
    ...     metadata = {
    ...         "render_modes": ["human", "matplotlib_figures"],
    ...     }
    ...
    ...     def __init__(self, render_mode=None) -> None:
    ...         super().__init__(render_mode)
    ...         self._renderer = make_renderer({
    ...             "Loss history": self.update_history_figure,
    ...             "Beam monitor": self.update_monitor_figure,
    ...         }, render_mode=render_mode)
    ...         ...
    ...
    ...     def render(self):
    ...         if self.render_mode in ["human", "matplotlib_figures"]:
    ...             return self._renderer.update()
    ...         return super().render()
    ...
    ...     def update_history_figure(self, figure: Figure) -> None:
    ...         print("update history")
    ...
    ...     def update_monitor_figure(self, figure: Figure) -> None:
    ...         print("update monitor")
    ...
    ...     def get_initial_params(self): ...
    ...     def compute_single_objective(self, params): ...
    ...
    >>> problem = MyProblem("matplotlib_figures")
    >>> _ = problem.render()
    update history
    update monitor

If, for some reason, you cannot pass multiple render functions to
`make_renderer()`, you can also update each renderer individually and combine
their results in your :meth:`~cernml.coi.Problem.render()` method with
`iter_matplotlib_figures()`:

.. code-block:: python
    :emphasize-lines: 8-10, 18-20, 37-40

    >>> from matplotlib.figure import Figure
    >>> from cernml.mpl_utils import make_renderer, iter_matplotlib_figures
    >>> from cernml.coi import SingleOptimizable
    ...
    >>> class LossHistory:
    ...     def __init__(self, render_mode=None):
    ...         self.history = []
    ...         self.renderer = make_renderer(
    ...             self.update_figure, render_mode=render_mode
    ...         )
    ...
    ...     def update_figure(self, figure):
    ...         print("update history")
    ...
    >>> class BeamMonitor:
    ...     def __init__(self, render_mode=None):
    ...         self.latest_reading = None
    ...         self.renderer = make_renderer(
    ...             self.update_figure, render_mode=render_mode
    ...         )
    ...
    ...     def update_figure(self, figure):
    ...         print("update monitor")
    ...
    >>> class MyProblem(SingleOptimizable):
    ...     metadata = {
    ...         "render_modes": ["human", "matplotlib_figures"],
    ...     }
    ...
    ...     def __init__(self, render_mode=None) -> None:
    ...         super().__init__(render_mode)
    ...         self.history = LossHistory(render_mode)
    ...         self.monitor = BeamMonitor(render_mode)
    ...
    ...     def render(self):
    ...         if self.render_mode in ["human", "matplotlib_figures"]:
    ...             return iter_matplotlib_figures(
    ...                 self.history.renderer.update(),
    ...                 self.monitor.renderer.update(),
    ...             )
    ...         return super().render()
    ...
    ...     def get_initial_params(self): ...
    ...     def compute_single_objective(self, params): ...
    ...
    >>> problem = MyProblem("matplotlib_figures")
    >>> _ = problem.render()
    update history
    update monitor

Using Generators to Split Initialization and Updates
----------------------------------------------------

It is often the case that you'll want to create your plot once and then
continuously update it with new data. For this purpose, the callback function
you pass to `make_renderer()` may also be a :term:`generator` function.

Generator functions are function that contain :ref:`std:yieldexpr`. Whenever
they reach a :ref:`yield statement <std:yield>`, they suspend their execution.
Later, the calling code resume the generator and it will continue from the
yield statement as if nothing had happend.

This allows us to write code like this:

.. code-block:: python
    :emphasize-lines: 24, 32

    >>> import numpy as np
    >>> from matplotlib.figure import Figure
    >>> from cernml.mpl_utils import RenderGenerator, make_renderer
    >>> from cernml.coi import SingleOptimizable
    ...
    >>> class MyProblem(SingleOptimizable):
    ...     metadata = {
    ...         "render_modes": ["human", "matplotlib_figures"],
    ...     }
    ...
    ...     def __init__(self, render_mode=None) -> None:
    ...         super().__init__(render_mode)
    ...         self._history = []
    ...         self._renderer = make_renderer(
    ...             self.update_figure, render_mode=render_mode
    ...         )
    ...         ...
    ...
    ...     def render(self):
    ...         if self.render_mode in ["human", "matplotlib_figures"]:
    ...             return self._renderer.update()
    ...         return super().render()
    ...
    ...     def update_figure(self, figure: Figure) -> RenderGenerator:
    ...         print("initialization")
    ...         axes = figure.subplots(nrows=1, ncols=1)
    ...         [line2d] = axes.plot([], [], "o-")
    ...         while True:
    ...             num = len(self._history)
    ...             print(f"update data ({num} points)")
    ...             line2d.set_data(np.arange(num), np.array(self._history))
    ...             yield
    ...             print("resuming generator")
    ...
    ...     def get_initial_params(self):
    ...         self._history = []
    ...         return 0.0
    ...
    ...     def compute_single_objective(self, params):
    ...         loss = np.linalg.norm(params)
    ...         self._history.append(loss)
    ...         return loss
    ...
    >>> problem = MyProblem("matplotlib_figures")
    >>> x0 = problem.get_initial_params()
    >>> _ = problem.render()
    initialization
    update data (0 points)
    >>> for _ in range(10):
    ...     _ = problem.compute_single_objective(x0)
    >>> _ = problem.render()
    resuming generator
    update data (10 points)

The renderer produced by `make_renderer()` detects that the callback is
a generator and polls it up to the first :keyword:`yield` statement. This
initializes our plot with some empty data. We then fill the history array with
a few calls to
:meth:`~cernml.coi.SingleOptimizable.compute_single_objective()`. Finally, we
call :meth:`~cernml.coi.Problem.render()` again. This does not restart the
generator function, but instead resumes from :keyword:`yield`: the generator
stays in the :keyword:`while` loop and only updates the data, without
reinitializing the entire figure.

Removing Renderers with ``@render_generator``
---------------------------------------------

For even more concise code, `render_generator()` lets you remove
renderers entirely from your optimization problem. It acts as a decorator and
lets you transform a callback method as if you had passed it to
`make_renderer()`. Calling that method will then instead call `.update()` on
that renderer.

For example:

.. code-block:: python
    :emphasize-lines: 20-23, 26, 33

    >>> from matplotlib.figure import Figure
    >>> from cernml.mpl_utils import (
    ...     RenderGenerator,
    ...     iter_matplotlib_figures,
    ...     render_generator,
    ... )
    >>> from cernml.coi import SingleOptimizable
    ...
    >>> class MyProblem(SingleOptimizable):
    ...     metadata = {
    ...         "render_modes": ["human", "matplotlib_figures"],
    ...     }
    ...
    ...     def __init__(self, render_mode=None) -> None:
    ...         super().__init__(render_mode)
    ...         ...
    ...
    ...     def render(self):
    ...         if self.render_mode in ["human", "matplotlib_figures"]:
    ...             return iter_matplotlib_figures(
    ...                 self.update_history_figure(),
    ...                 self.update_monitor_figure(),
    ...             )
    ...         return super().render()
    ...
    ...     @render_generator
    ...     def update_history_figure(self, figure: Figure) -> RenderGenerator:
    ...         print("initialize history")
    ...         while True:
    ...             print("update history")
    ...             yield
    ...
    ...     @render_generator("Beam monitor")
    ...     def update_monitor_figure(self, figure: Figure) -> None:
    ...         print("update monitor")
    ...
    ...     def get_initial_params(self): ...
    ...     def compute_single_objective(self, params): ...
    ...
    >>> problem = MyProblem("matplotlib_figures")
    >>> _ = problem.render()
    initialize history
    update history
    update monitor
    >>> _ = problem.render()
    update history
    update monitor

As you can see, `render_generator` works with both regular callback methods and
with generators. You can also pass a title to it, with the same effect as if
you had passed a `dict` to `make_renderer()`.

A Full Example
--------------

.. code-block:: python
    :emphasize-lines: 17-20, 35, 89

    >>> import numpy as np
    >>> from cernml import coi
    >>> from cernml.mpl_utils import make_renderer
    >>> from gymnasium.spaces import Box
    ...
    >>> class MyProblem(coi.SingleOptimizable):
    ...     metadata = {
    ...         "render_modes": ["human", "matplotlib_figures"],
    ...         "cern.machine": coi.Machine.NO_MACHINE,
    ...     }
    ...     optimization_space = Box(-1.0, 1.0, shape=(4,))
    ...
    ...     def __init__(self, render_mode=None):
    ...         super().__init__(render_mode)
    ...         self._last_readings = None
    ...         # Create the renderer.
    ...         self._renderer = make_renderer(
    ...             self._iter_updates,
    ...             render_mode=render_mode,
    ...         )
    ...         self.response = np.random.uniform(size=(10, 4))
    ...
    ...     def get_initial_params(self, seed=None, options=None):
    ...         print("get_initial_params()")
    ...         super().get_initial_params(seed=seed, options=options)
    ...         if seed is not None:
    ...             seed = self.np_random.bit_generator.random_raw()
    ...             self.optimization_space.seed(seed)
    ...         self._last_readings = None
    ...         return self.optimization_space.sample()
    ...
    ...     def compute_single_objective(self, params):
    ...         print("compute_single_objective()")
    ...         # The `@` operator performs matrix multiplication in Python.
    ...         self._last_readings = self.response @ params
    ...         loss = np.sqrt(np.mean(np.square(self._last_readings)))
    ...         return loss
    ...
    ...     def render(self):
    ...         # As before.
    ...         if self.render_mode in self.metadata["render_modes"]:
    ...             return self._renderer.update()
    ...         return super().render()
    ...
    ...     # This is a generator. It contains `yield` instead of `return`.
    ...     def _iter_updates(self, figure):
    ...         print("initializing the figure")
    ...         # This part is executed on the very first call to `render()`.
    ...         # This might happen before or after `compute_single_objective()`,
    ...         # so `self._last_readings` might still be None.
    ...         axes = figure.subplots()
    ...         axes.set_xlabel("Monitor")
    ...         axes.set_ylabel("Reading (a.u.)")
    ...         axes.grid()
    ...         # Both graphs start out empty. We fill them later.
    ...         # Remember that `plot()` returns a list of lines; we
    ...         # unpack it directly to get the lines themselves.
    ...         [initial] = axes.plot([], "o", alpha=0.3, label="Initial")
    ...         [current] = axes.plot([], "o", color="tab:blue", label="Current")
    ...         axes.legend(loc="best")
    ...         # This is our update loop.
    ...         while True:
    ...             if self._last_readings is None:
    ...                 # First call after `get_initial_params()`.
    ...                 # We don't have any data yet.
    ...                 print("render(no data)")
    ...                 initial.set_data([], [])
    ...                 current.set_data([], [])
    ...             elif len(initial.get_ydata()) == 0:
    ...                 # First call with data. We need to update
    ...                 # both graphs and adjust axes limits.
    ...                 print("render(reset initial)")
    ...                 ydata = self._last_readings
    ...                 xdata = np.arange(1, 1 + len(ydata))
    ...                 initial.set_data(xdata, ydata)
    ...                 current.set_data(xdata, ydata)
    ...                 axes.relim()           # Recalculate data bounding box.
    ...                 axes.autoscale_view()  # Adjust axes limits.
    ...                 figure.tight_layout()  # Adjust margins around axes.
    ...             else:
    ...                 # Any future call. Only update `current`.
    ...                 # Don't adjust axes limits; otherwise the plot would
    ...                 # "jump" around a lot.
    ...                 print("render(update current)")
    ...                 current.set_ydata(self._last_readings)
    ...             # Yield statement. This is where we return `render()`.
    ...             # Next time `render()` calls us, we will continue here
    ...             # and loop around to `while True`.
    ...             yield


The following program shows the order in which these functions call each other:

.. code-block:: python

    >>> problem = MyProblem("matplotlib_figures")
    >>> x0 = problem.get_initial_params()
    get_initial_params()
    >>> fig = problem.render()
    initializing the figure
    render(no data)
    >>> for i in range(1, 4):
    ...     print(f"iteration #{i}")
    ...     x = problem.optimization_space.sample()
    ...     loss = problem.compute_single_objective(x)
    ...     fig = problem.render()
    iteration #1
    compute_single_objective()
    render(reset initial)
    iteration #2
    compute_single_objective()
    render(update current)
    iteration #3
    compute_single_objective()
    render(update current)
    >>> # Start from scratch, to show that it works.
    >>> x0 = problem.get_initial_params()
    get_initial_params()
    >>> fig = problem.render()
    render(no data)
    >>> loss = problem.compute_single_objective(x0)
    compute_single_objective()
    >>> fig = problem.render()
    render(reset initial)


And this is what the plot could look like after a few iterations:

.. image:: renderer.png
    :alt: Example plot after a two iterations
