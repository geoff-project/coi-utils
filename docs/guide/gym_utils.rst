..
    SPDX-FileCopyrightText: 2020-2023 CERN
    SPDX-FileCopyrightText: 2023 GSI Helmholtzzentrum für Schwerionenforschung
    SPDX-FileNotice: All rights not expressly granted are reserved.

    SPDX-License-Identifier: GPL-3.0-or-later OR EUPL-1.2+

Normalizing Parameters
======================

The COI have inherited a rich API to specify exactly the domain on which an
optimization problem is specified and what bounds it has to respect.
Nonetheless, for the time being, COI restricts the domains of optimization
problems: `~cernml.coi.SingleOptimizable.optimization_space`,
`~gym.Env.observation_space` and `~gym.Env.action_space` all must have
symmetric and normalized bounds, i.e. [−1; +1].

Consequently, most optimization problems have to perform conversions from the
*scaled* inputs of
:meth:`~cernml.coi.SingleOptimizable.compute_single_objective()` and
:meth:`~gym.Env.step()` (in [−1; +1]) to the *unscaled* inputs of the actual
machines [x₁; x₂]. In addition, :meth:`~gym.Env.step()` also has to convert
from *unscaled* observations on the real machine to *scaled* observations in
the range [−1; +1].

This procedure is cumbersome and error-prone. It is easy to forget scaling or
unscaling a value; or to scale or unscale it twice; or to use the wrong scaling
factor; or to unscale a value that should have been scaled and vice versa.

The `~cernml.gym_utils` package does not prevent any of these errors, but it
hopefully makes them less likely. At its core, it provides a
`~cernml.gym_utils.Scaler` class that wraps around an *unscaled* space with
arbitrary finite bounds. It provides methods to *scale* values from that space
into a normalized space and to *unscale* them back.

Take this toy machine as an example:

.. code-block:: python

    >>> import gym
    >>> import numpy as np
    >>> from cernml import coi, gym_utils
    >>> from gym.spaces import Box
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
    ...         readings = 250.0 * np.ones(4)
    ...         print("acquired from machine:", readings)
    ...         return readings

Using scalers in a `~cernml.coi.SingleOptimizable` to communicate with it might
look like this:

.. code-block:: python

    >>> class MyOptimizable(coi.SingleOptimizable):
    ...
    ...     metadata = {
    ...         'render.modes': [],
    ...         'coi.machine': coi.Machine.NO_MACHINE,
    ...     }
    ...     # Scale settings into [−1; +1].
    ...     settings_scale = gym_utils.Scaler(
    ...         Box(
    ...             -Machine.SETTINGS_LIMITS,
    ...             Machine.SETTINGS_LIMITS,
    ...             dtype=np.double,
    ...         )
    ...     )
    ...     # Scale readings into [0; 1].
    ...     readings_scale = gym_utils.Scaler(
    ...         Box(0.0, Machine.READINGS_SCALE, shape=(4,), dtype=np.double),
    ...         symmetric=False,
    ...     )
    ...
    ...     optimization_space = settings_scale.scaled_space
    ...
    ...     def __init__(self):
    ...         self.machine = Machine()
    ...
    ...     def get_initial_params(self):
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

And using it in an `~gym.Env` might look like this:

.. code-block:: python

    >>> class MyEnv(MyOptimizable, gym.Env):
    ...
    ...     action_space = MyOptimizable.settings_scale.scaled_space
    ...     observation_space = MyOptimizable.readings_scale.scaled_space
    ...
    ...     def __init__(self):
    ...         super().__init__()
    ...         self._actions = np.zeros(self.action_space.shape)
    ...
    ...     def reset(self):
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
    ...         done = success = reward > 0.01
    ...         info = {"readings": readings, "success": success}
    ...         return obs, reward, done, info
    ...     def seed(self, seed=None):
    ...         return [
    ...             self.settings_scale.space.seed(seed),
    ...             self.readings_scale.space.seed(seed),
    ...             self.optimization_space.seed(seed),
    ...             self.action_space.seed(seed),
    ...             self.observation_space.seed(seed),
    ...         ]

And again, the optimizer only sees scaled values while the machine only sees
unscaled ones:

.. code-block:: python

    >>> env = MyEnv()
    >>> _ = env.seed(0)
    >>> obs = env.reset()
    sent to machine: [-8.91279887  9.30781874  0.53076378 -0.83993062]
    acquired from machine: [250. 250. 250. 250.]
    >>> obs
    array([0.25, 0.25, 0.25, 0.25])
    >>> obs, reward, done, info = env.step(env.action_space.sample())
    sent to machine: [-8.91279887  9.30781874  0.53076378 -0.83993062]
    acquired from machine: [250. 250. 250. 250.]
    >>> obs
    array([0.25, 0.25, 0.25, 0.25])
    >>> reward
    -1.0
