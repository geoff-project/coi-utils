..
    SPDX-FileCopyrightText: 2020-2024 CERN
    SPDX-FileCopyrightText: 2023-2024 GSI Helmholtzzentrum für Schwerionenforschung
    SPDX-FileNotice: All rights not expressly granted are reserved.

    SPDX-License-Identifier: GPL-3.0-or-later OR EUPL-1.2+

Normalizing Parameters
======================

.. currentmodule:: cernml.coi

The COI have inherited a rich API to specify exactly the domain on which an
optimization problem is specified and what bounds it has to respect.
Nonetheless, it is sometimes useful to restrict the domains of optimization
problems (`~SingleOptimizable.optimization_space`,
`~gymnasium.Env.observation_space` and `~gymnasium.Env.action_space`) such that
they have symmetric and normalized bounds, i.e. [−1; +1].

Consequently, such optimization problems have to perform conversions from the
*scaled* inputs of :meth:`~SingleOptimizable.compute_single_objective()` and
:func:`~gymnasium.Env.step()` in [−1; +1] to the *unscaled* inputs of the
actual machines [x₁; x₂]. In addition, :func:`~gymnasium.Env.reset()` and
:func:`~gymnasium.Env.step()` may also have to convert from *unscaled*
observations on the real machine to *scaled* observations in the range [−1;
+1].

Doing this manuallt is not only cumbersome, but also error-prone. It is easy to
forget scaling or unscaling a value; or to scale or unscale it twice; or to use
the wrong scaling factor; or to unscale a value that should have been scaled
and vice versa.

The `~cernml.gym_utils` package does not prevent any of these errors, but it
hopefully makes them less likely. At its core, it provides a
`~cernml.gym_utils.Scaler` class that wraps around an *unscaled* space with
arbitrary finite bounds. It provides methods to *scale* values from that space
into a normalized space and to *unscale* them back.

Take this toy machine as an example:

.. code-block:: python

    >>> import numpy as np
    >>> from cernml import coi, gym_utils
    >>> from gymnasium import Env
    >>> from gymnasium.spaces import Box
    >>>
    >>> class Machine:
    ...     SETTINGS_LIMITS = np.array([10.0, 10.0, 2.0, 2.0])
    ...     READINGS_SCALE = 1000.0
    ...
    ...     def recv_settings(self):
    ...         settings = np.array([3.0, 2.5, 1.0, -1.0])
    ...         print("received from machine:", settings)
    ...
    ...         return settings
    ...     def send_settings(self, settings):
    ...         print("sent to machine:", settings)
    ...
    ...     def acquire_readings(self):
    ...         readings = np.repeat(250.0, repeats=4)
    ...         print("acquired from machine:", readings)
    ...         return readings

Using scalers in a `SingleOptimizable` to communicate with it might
look like this:

.. code-block:: python

    >>> class MyOptimizable(coi.SingleOptimizable):
    ...
    ...     metadata = {
    ...         'render_modes': [],
    ...         'coi.machine': coi.Machine.NO_MACHINE,
    ...     }
    ...     # Scale settings into [−1; +1].
    ...     settings_scale = gym_utils.Scaler(
    ...         Box(-Machine.SETTINGS_LIMITS, Machine.SETTINGS_LIMITS, dtype=np.double)
    ...     )
    ...     # Scale readings into [0; 1].
    ...     readings_scale = gym_utils.Scaler(
    ...         Box(0.0, Machine.READINGS_SCALE, shape=(4,), dtype=np.double),
    ...         symmetric=False,
    ...     )
    ...
    ...     optimization_space = settings_scale.scaled_space
    ...
    ...     def __init__(self, render_mode=None):
    ...         super().__init__(render_mode)
    ...         self.machine = Machine()
    ...
    ...     def get_initial_params(self, seed=None, options=None):
    ...         super().get_initial_params(seed=seed, options=options)
    ...         if seed is not None:
    ...             next_seed = self.np_random.bit_generator.random_raw
    ...             self.settings_scale.space.seed(next_seed())
    ...             self.readings_scale.space.seed(next_seed())
    ...             self.optimization_space.seed(next_seed())
    ...         settings = self.machine.recv_settings()
    ...         return self.settings_scale.scale(settings)
    ...
    ...     def compute_single_objective(self, params):
    ...         settings = self.settings_scale.unscale(params)
    ...         self.machine.send_settings(settings)
    ...         readings = self.machine.acquire_readings()
    ...         loss = np.sum(self.readings_scale.scale(readings))
    ...         return loss

You can see that the optimizer sees scaled values, but the machine sees
unscaled ones:

.. code-block:: python

    >>> opt = MyOptimizable()
    >>> x0 = opt.get_initial_params()
    received from machine: [ 3.   2.5  1.  -1. ]
    >>> x0
    array([ 0.3 ,  0.25,  0.5 , -0.5 ])
    >>> loss = opt.compute_single_objective(x0)
    sent to machine: [ 3.   2.5  1.  -1. ]
    acquired from machine: [250. 250. 250. 250.]
    >>> loss
    1.0

And using it in an `~gymnasium.Env` might look like this:

.. code-block:: python

    >>> class MyEnv(MyOptimizable, Env):
    ...
    ...     action_space = MyOptimizable.settings_scale.scaled_space
    ...     observation_space = MyOptimizable.readings_scale.scaled_space
    ...
    ...     def __init__(self, render_mode=None):
    ...         super().__init__(render_mode)
    ...         self._actions = np.zeros(self.action_space.shape)
    ...
    ...     def reset(self, seed=None, options=None):
    ...         super().reset(seed=seed, options=options)
    ...         if seed is not None:
    ...             next_seed = self.np_random.bit_generator.random_raw
    ...             self.settings_scale.space.seed(next_seed())
    ...             self.readings_scale.space.seed(next_seed())
    ...             self.optimization_space.seed(next_seed())
    ...             self.action_space.seed(next_seed())
    ...             self.observation_space.seed(next_seed())
    ...         self.machine.send_settings(self.settings_scale.space.sample())
    ...         readings = self.machine.acquire_readings()
    ...         return self.readings_scale.scale(readings)
    ...
    ...     def step(self, action):
    ...         settings = self.settings_scale.unscale(action)
    ...         self.machine.send_settings(settings)
    ...         readings = self.machine.acquire_readings()
    ...         obs = self.readings_scale.scale(readings)
    ...         reward = -np.sum(obs)
    ...         terminated = success = reward > 0.01
    ...         truncated = False
    ...         info = {"readings": readings, "success": success}
    ...         return obs, reward, terminated, truncated, info

And again, the optimizer only sees scaled values while the machine only sees
unscaled ones:

.. code-block:: python

    >>> env = MyEnv()
    >>> obs = env.reset(seed=0)
    sent to machine: [-4.06452837  9.91057096  0.4817112   0.74395322]
    acquired from machine: [250. 250. 250. 250.]
    >>> obs
    array([0.25, 0.25, 0.25, 0.25])
    >>> action = env.action_space.sample()
    >>> obs, reward, terminated, truncated, info = env.step(action)
    sent to machine: [-5.35037513  6.47447155  1.47493981 -1.19426039]
    acquired from machine: [250. 250. 250. 250.]
    >>> obs
    array([0.25, 0.25, 0.25, 0.25])
    >>> reward
    -1.0
