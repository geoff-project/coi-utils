..
    SPDX-FileCopyrightText: 2020-2023 CERN
    SPDX-FileCopyrightText: 2023 GSI Helmholtzzentrum für Schwerionenforschung
    SPDX-FileNotice: All rights not expressly granted are reserved.

    SPDX-License-Identifier: GPL-3.0-or-later OR EUPL-1.2+

Changelog
=========

This package uses a variant of `Semantic Versioning <https://semver.org/>`__
that makes additional promises during the initial development (major version
0): whenever breaking changes to the public API are published, the first
non-zero version number will increase. For example, code that uses version
0.2.9 if this package will also work with version 0.2.10, but may break with
version 0.3.0.

Unreleased
----------

- FIX: Bump PyJapc dependency from 0.2.2 to 0.2.6 to gain type annotations.
- FIX: Type annotations for *data_filter* parameter of
  `~cernml.japc_utils.subscribe_stream()`.

v0.2.9
------

- FIX: Bad CI configuration that prevented the package from being released.

v0.2.8
------

- FIX: Bad CI config that prevented the docs from being built.

v0.2.7
------

- ADD: Support for Python 3.9 has been added.
- FIX: Various dead links in the documentation. One minor consequence is that
  `cernml.mpl_utils.render_generator` now is a function and no longer a type.
  This should not have any impact on user code.
- OTHER: Open-source this package by adding the appropriate license notices.

v0.2.6
------

- ADD: `~cernml.lsa_utils.trim_scalar_settings()`.
- FIX: Several broken links in the documentation.
- OTHER: Switched project manifest from ``setup.cfg`` to ``pyproject.toml``.

v0.2.5
------

- ADD: Install extra ``doc_only`` to build docs in a non-CERN environment. (This skips the PyJapc and PJLSA dependencies.)
- ADD: `cernml.mpl_utils.FigureRenderer.close()`.
- ADD: `cernml.lsa_utils.IncorporatorGroup`.
- ADD: Ability to trim multiple functions with one call to `~cernml.lsa_utils.incorporate_and_trim()`.
- FIX: Type annotation of `cernml.lsa_utils.Incorporator.user`.
- FIX: Type annotation of `cernml.mpl_utils.render_generator`.

v0.2.4
------

- Add `~cernml.mpl_utils.FigureRenderer.close()` to `~cernml.mpl_utils.FigureRenderer`.

v0.2.3
------

- Add optional parameter *description* to `~cernml.lsa_utils.incorporate_and_trim()`.
- Add a section on incorporation ranges to the `user guide <guide/lsa_utils.md#incorporation-ranges>`__.

v0.2.2
------

- FIX: Properly handle multiple particle transfers in `cernml.lsa_utils.incorporate_and_trim()`.

v0.2.1
------

- ADD: :doc:`Installation guide <guide/install>`.
- FIX: Mark `~cernml.lsa_utils` as type-annotated.
- FIX: Include ``pjlsa`` dependency in extra ``all``.
- FIX: Overly loose dependency on :doc:`cernml-coi <coi:index>`.

v0.2.0
------

- BREAKING: rename `~cernml.japc_utils.ParamStream` and `~cernml.japc_utils.ParamGroupStream` methods: ``wait_next()`` becomes `~cernml.japc_utils.ParamStream.pop_or_wait()`, ``next_if_ready()`` becomes `~cernml.japc_utils.ParamStream.pop_if_ready()`.
- BREAKING: Refactor the renderer API: ``SimpleRenderer`` is replaced by `~cernml.mpl_utils.FigureRenderer`, which is an :term:`ABC <abstract base class>`. Replace ``from_generator()`` with `~cernml.mpl_utils.FigureRenderer.from_callback()`.
- ADD: Method `~cernml.japc_utils.ParamStream.wait_for_next()` to `~cernml.japc_utils.ParamStream` and `~cernml.japc_utils.ParamGroupStream`.
- ADD: `~cernml.mpl_utils.make_renderer()` and `~cernml.mpl_utils.RendererGroup`.
- ADD: `~cernml.lsa_utils.get_cycle_type_attributes()` from cernml-coi-funcs 0.2.2.
- ADD: `Scaler.scaled_space <cernml.gym_utils.Scaler.scaled_space>`.
- ADD: The *symmetric* parameter to `~cernml.gym_utils.Scaler`, `~cernml.gym_utils.scale_from_box()` and `~cernml.gym_utils.unscale_into_box()`.
- OTHER: Extend and reorganize the documentation.

v0.1.0
------

Initial version. Code has been extracted from cernml-coi_ and
cernml-coi-funcs_. Documentation has been adjusted.

.. _cernml-coi: https://gitlab.cern.ch/geoff/cernml-coi/
.. _cernml-coi-funcs: https://gitlab.cern.ch/geoff/cernml-coi-funcs/
