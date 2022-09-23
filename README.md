Utilities for the Common Optimization Interfaces
================================================

CERN ML is the project of bringing numerical optimization, machine learning and
reinforcement learning to the operation of the CERN accelerator complex. [The
COI][CernML-COI] are common interfaces that make it posisble to use numerical
optimization and reinforcement learning on the same optimization problems.

This package provides utility functions and classes that make it easier to work
with the COI. They encapsulate common use cases so that authors of optimization
problems don't have to start from scratch. This prevents bugs and saves time.

This repository can be found online on CERN's [Gitlab][].

[Gitlab]: https://gitlab.cern.ch/be-op-ml-optimization/cernml-coi-utils/
[CernML-COI]: https://gitlab.cern.ch/be-op-ml-optimization/cernml-coi/

Table of Contents
-----------------

[[_TOC_]]

Motivation
----------

These utilities have been extracted from the COI so that they can evolve
independently. This makes it possible to evolve them gradually as necessary
while keeping the COI themselves stable.

The utilities are separated by the third-party packages that they enhance. This
makes it possible to depend only on utilities only for the packages one is
interested in, without installing any irrelevant ones.

Utilities should be simple, self-contained, and based on actual usage. [Merge
requests][Gitlab-MRs] and [feature suggestions][Gitlab-Issues] are both
welcome!

[Gitlab-MRs]: https://gitlab.cern.ch/be-op-ml-optimization/cernml-coi-utils/-/merge_requests
[Gitlab-Issues]: https://gitlab.cern.ch/be-op-ml-optimization/cernml-coi-utils/-/issues

Installation
------------

In your project that already uses [CernML-COI][], go to `setup.cfg` or
`setup.py` and add a dependency on `cernml-coi-utils`. Add the utilities that
you're interested in as extras. Each extra is named after the third-party
package that it depends on. You may also use the extra `all` to use all
utilities.

```config
# setup.cfg
[options]
install_requires =
    cernml-coi-utils[pyjapc,matplotlib] ~= 0.2.5
```

Examples
--------

This section provides a minimal showcase. See [the documentation][acc-py-docs]
for a more thorough introduction.

[acc-py-docs]: https://acc-py.web.cern.ch/gitlab/be-op-ml-optimization/cernml-coi-utils/

A PyJapc wrapper that facilities subscription handling:

```python
from pyjapc import PyJapc
from cernml import japc_utils

japc = PyJapc("SPS.USER.ALL")
stream = japc_utils.subscribe_stream(japc, "SOME.MONITOR/Acquisition")
with stream:
    while True:
        data, header = stream.pop_or_wait()
        print(header.cycle_stamp, "--", data)
```

A PJLSA wrapper that facilitates function incorporations:

```python
from pjlsa import LSAClient

lsa = LSAClient(server="NEXT")
with lsa.java_api():
    from cernml import lsa_utils

    incorporator = lsa_utils.Incorporator("MAGNET/K", user="SPS.USER.MD1")
    incorporator.incorporate_and_trim(
        cycle_time=300.0,
        value=1e-3,
        relative=True,
        description="Automatic trim from Python",
    )
```

A Gym space wrapper to automatically normalize parameters:

```python
import numpy
from gym import spaces
from cernml import gym_utils

space = spaces.Dict({
    "positions": spaces.Box(-30.0, 30.0, shape=(2,)),
    "angles": spaces.Box(-2.0, 2.0, shape=(2,))
})
unnormalized = dict(positions=[30, 30], angles=[2, 2])

scaler = gym_utils.Scaler(spaces.flatten_space(space))
normalized = scaler.scale(spaces.flatten(space, unnormalized))
assert numpy.array_equal(normalized, [1.0, 1.0, 1.0, 1.0])

roundtrip = spaces.unflatten(space, scaler.unscale(normalized))
assert roundtrip == unnormalized
```

Simplifying rendering in a Gym environment:

```python
import time
import numpy
from cernml import mpl_utils
from matplotlib import pyplot

points = []
def iter_updates(figure):
    axes = figure.subplot(111)
    [line] = axes.plot(points)
    while True:
        yield
        indices = numpy.arange(len(points))
        line.set_data(indices, points)
        axes.update_datalim()
        axes.autoscale_view()

renderer = mpl_utils.make_renderer(iter_updates)
renderer.update("human")
for _ in range(20):
    pyplot.pause(0.5)
    points.append(numpy.random.uniform())
    renderer.update("human")
```

Stability
---------

This package uses a variant of [Semantic Versioning](https://semver.org/) that
makes additional promises during the initial development (major version 0):
whenever breaking changes to the public API are published, the first non-zero
version number will increase. This means that code that uses COI version 0.6.0
will continue to work with version 0.6.1, but may break with version 0.7.0.

The exception to this are the contents of `cernml.coi.unstable`, which may
change in any given release.

Changelog
---------

[See here](https://acc-py.web.cern.ch/gitlab/be-op-ml-optimization/cernml-coi-utils/docs/stable/changelog.html).

Documentation
-------------

Documentation is provided by the [Acc-Py documentation server][acc-py-docs],
which is only available inside the CERN network. Additionally, the API
is thoroughly documented with Python docstrings.
