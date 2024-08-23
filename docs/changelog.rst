..
    SPDX-FileCopyrightText: 2020-2024 CERN
    SPDX-FileCopyrightText: 2023-2024 GSI Helmholtzzentrum für Schwerionenforschung
    SPDX-FileNotice: All rights not expressly granted are reserved.

    SPDX-License-Identifier: GPL-3.0-or-later OR EUPL-1.2+

:tocdepth: 3

Changelog
=========

.. currentmodule:: cernml

This package uses a variant of `Semantic Versioning <https://semver.org/>`__
that makes additional promises during the initial development (major version
0): whenever breaking changes to the public API are published, the first
non-zero version number will increase. For example, code that uses version
0.2.9 if this package will also work with version 0.2.10, but may break with
version 0.3.0.

Unreleased
----------

v0.3.0
^^^^^^

Breaking changes
~~~~~~~~~~~~~~~~
- Drop support for Python 3.7.
- Increase matplotlib requirement to 3.8.
- `.Renderer` now accepts an argument *render_mode* in the constructor. At the
  same time, the *render_mode* parameter of `.Renderer.update()` has been
  removed.
- The static method ``Renderer.make_figure()`` has been replaced with the
  attribute `.Renderer.strategy`.
- `.RendererGroup` now deduces its render mode from the element renderers. Any
  ambiguous result raises the new `.InconsistentRenderModeError` exception.
- `.iter_matplotlib_figures()` now accepts multiple arguments. It renders all
  of them immediately and in order, then returns an iterator as before. If you
  don't need iteration, consider `.concat_matplotlib_figures()`.
- The mapping test in `.iter_matplotlib_figures()` has become stricter; to be
  considered a mapping, a `.MatplotlibFigures` object must now have `items()
  <dict.items>` defined on its type, not just on itself.

Additions
~~~~~~~~~
- The decorator `.render_generator` now allows you to specify a title for the
  figure it manages.
- Add `.concat_matplotlib_figures()` to get the list of title–figure pairs
  directly.
- Add a method `~.Renderer.close()` to `.Renderer` and `.RendererGroup`. This
  allows custom renderers to have logic on closure and allows renderer groups
  to forward such calls to their elements.

Bug fixes
~~~~~~~~~
- The decorator `.render_generator` only allowed one one renderer per class. It
  now behaves as expected and gives each instance its own renderer. As
  a consequence, you can now `delete <object.__delete__>` renderers managed by
  this decorator. Doing so will effectively restart them upon the next call.

Other changes
~~~~~~~~~~~~~
- The user guide and large parts of these docs have been rewritten.
- When running unit tests for this package, LSA tests are now skipped
  automatically if no JVM is available.

v0.2
----

v0.2.12
^^^^^^^

Bug fixes
~~~~~~~~~
- Fix a bug that prevented :ref:`guide/lsa_utils:Global Trim Request Hooks`
  from properly forwarding calls to their parent hooks.

v0.2.11
^^^^^^^

Bug fixes
~~~~~~~~~
- The type hint of :meth:`~object.__enter__()` method on `lsa_utils.Hooks` now
  specifies `~typing.Self` instead of `.Hooks`. This requires a dependency on
  `typing_extensions <https://github.com/python/typing_extensions/>`_ for
  Python versions below 3.11.

v0.2.10
^^^^^^^

Additions
~~~~~~~~~
- Add support for :ref:`guide/lsa_utils:transient trims`. This increases the
  PJLSA requirement to 0.2.18.
- Add :ref:`guide/lsa_utils:Global Trim Request Hooks` that allow host
  applications like `GeOFF <https://gitlab.cern.ch/geoff/geoff-app>`_ to
  enhance trim descriptions with information that is not available inside of
  optimization problems.
- Add :class:`str() <str>` and :func:`repr` overloads for `.Incorporator` and
  `.IncorporatorGroup`.

Bug fixes
~~~~~~~~~
- Bump PyJapc dependency from 0.2.2 to 0.2.6 to gain type annotations.
- Fix type annotations for *data_filter* parameter of `.subscribe_stream()`.
- Add `~typing.Tuple`\ [`str`, …] to type annotations for *name_or_names*
  parameter of `.subscribe_stream()` for consistency with `~pyjapc.PyJapc`.
- Change the type of `.ParamGroupStream.parameter_names` from
  `~typing.List`\ [`str`] to `~typing.Tuple`\ [`str`, …] to prevent users from
  subtly broken code like :samp:`stream.parameter_names.append({name})`. This
  is technically a breaking change, but the impact is assumed to be negligible.

v0.2.9
^^^^^^

Bug fixes
~~~~~~~~~
- Fix bad CI configuration that prevented the package from being released.

v0.2.8
^^^^^^

Bug fixes
~~~~~~~~~
- Fix bad CI config that prevented the docs from being built.

v0.2.7
^^^^^^

Additions
~~~~~~~~~
- Add support for Python 3.9.

Bug fixes
~~~~~~~~~
- Fix various dead links in the documentation. One minor consequence is that
  `.render_generator` now is a function and no longer a type. This should not
  have any impact on user code.

Other changes
~~~~~~~~~~~~~
- Open-source this package by adding the appropriate license notices.

v0.2.6
^^^^^^

Additions
~~~~~~~~~
- Add `lsa_utils.trim_scalar_settings()`.

Bug fixes
~~~~~~~~~
- Fix several broken links in the documentation.

Other changes
~~~~~~~~~~~~~
- Switch project manifest from :file:`setup.cfg` to :file:`pyproject.toml`.

v0.2.5
^^^^^^

Additions
~~~~~~~~~
- Add install extra ``doc_only`` to build docs in a non-CERN environment. (This skips the PyJapc and PJLSA dependencies.)
- Add `mpl_utils.FigureRenderer.close()`.
- Add `lsa_utils.IncorporatorGroup`.
- Add ability to trim multiple functions with one call to `~lsa_utils.incorporate_and_trim()`.

Bug fixes
~~~~~~~~~
- Fix type annotation of `.Incorporator.user`.
- Fix type annotation of `.render_generator`.

v0.2.4
^^^^^^

- Add `~.FigureRenderer.close()` to `.FigureRenderer`.

v0.2.3
^^^^^^

Additions
~~~~~~~~~
- Add optional parameter *description* to `~lsa_utils.incorporate_and_trim()`.
- Add a section on :ref:`guide/lsa_utils:incorporation ranges` to the user guide.

v0.2.2
^^^^^^

Bug fixes
~~~~~~~~~
- Properly handle multiple particle transfers in `~lsa_utils.incorporate_and_trim()`.

v0.2.1
^^^^^^

Additions
~~~~~~~~~
- Add :doc:`guide/install` guide.

Bug fixes
~~~~~~~~~
- Mark `.lsa_utils` as type-annotated.
- Include ``pjlsa`` dependency in extra ``all``.
- Restrict overly loose dependency on :doc:`cernml-coi <coi:index>`.

v0.2.0
^^^^^^

Breaking changes
~~~~~~~~~~~~~~~~
- Rename `.ParamStream` and `.ParamGroupStream` methods: ``wait_next()`` becomes `~.ParamStream.pop_or_wait()`, ``next_if_ready()`` becomes `~.ParamStream.pop_if_ready()`.
- Refactor the renderer API: ``SimpleRenderer`` is replaced by `.FigureRenderer`, which is an :term:`abstract base class`. Replace ``from_generator()`` with `.from_callback()`.

Additions
~~~~~~~~~
- Add method `~.ParamStream.wait_for_next()` to `.ParamStream` and `.ParamGroupStream`.
- Add `.make_renderer()` and `.RendererGroup`.
- Add `.get_cycle_type_attributes()` from cernml-coi-funcs 0.2.2.
- Add `.Scaler.scaled_space`.
- Add The *symmetric* parameter to `.Scaler`, `.scale_from_box()` and `.unscale_into_box()`.

Other changes
~~~~~~~~~~~~~
- Extend and reorganize the documentation.

v0.1
----

v0.1.0
^^^^^^

Initial version. Code has been extracted from cernml-coi_ and
cernml-coi-funcs_. Documentation has been adjusted.

.. _cernml-coi: https://gitlab.cern.ch/geoff/cernml-coi/
.. _cernml-coi-funcs: https://gitlab.cern.ch/geoff/cernml-coi-funcs/
