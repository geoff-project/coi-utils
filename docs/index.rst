..
    SPDX-FileCopyrightText: 2020-2023 CERN
    SPDX-FileCopyrightText: 2023 GSI Helmholtzzentrum für Schwerionenforschung
    SPDX-FileNotice: All rights not expressly granted are reserved.

    SPDX-License-Identifier: GPL-3.0-or-later OR EUPL-1.2+

Utilities for the Common Optimization Interfaces
================================================

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

This repository can be found online on CERN's `Gitlab`_.

.. _Gitlab: https://gitlab.cern.ch/geoff/cernml-coi-utils/

.. toctree::
    :maxdepth: 2

    guide/index
    api/index
    changelog
