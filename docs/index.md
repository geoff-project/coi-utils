# Utilities for the Common Optimization Interfaces

CERN ML is the project of bringing numerical optimization, machine learning and
reinforcement learning to the operation of the CERN accelerator complex. The
COI are common interfaces that make it posisble to use numerical optimization
and reinforcement learning on the same optimization problems.

This package provides utility functions and classes that make it easier to work
with the COI. They encapsulate common use cases so that authors of optimization
problems don't have to start from scratch. This prevents bugs and saves time.

These utilities have been extracted from the COI so that they can evolve
independently. This makes it possible to evolve them gradually as necessary
while keeping the COI themselves stable.

This repository can be found online on CERN's [Gitlab][].

[Gitlab]: https://gitlab.cern.ch/be-op-ml-optimization/cernml-coi/

```{toctree}
---
maxdepth: 2
---

guide
api
changelog
```
