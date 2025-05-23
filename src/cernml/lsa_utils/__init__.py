# SPDX-FileCopyrightText: 2020-2024 CERN
# SPDX-FileCopyrightText: 2023-2024 GSI Helmholtzzentrum für Schwerionenforschung
# SPDX-FileNotice: All rights not expressly granted are reserved.
#
# SPDX-License-Identifier: GPL-3.0-or-later OR EUPL-1.2+

"""Utilities for communication with the LSA database.

This package makes use of `Pjlsa`_. Pjlsa uses the `CommonBuild
Dependency Manager`_ and transitively `JPype`_ to modify the Python
import machinery in order to provide Java packages as regular imports.
Consequently, some care must be taken when importing this package, or
any package that depends on it.

.. _Pjlsa: https://gitlab.cern.ch/scripting-tools/pjlsa
.. _`CommonBuild Dependency Manager`:
    https://gitlab.cern.ch/scripting-tools/cmmnbuild-dep-manager
.. _JPype: https://github.com/jpype-project/jpype

Pjlsa provides a class `LSAClient`, which allows hooking into the
Python import machinery. It is considered best practice to instantiate
this class once and only once at the outermost scope of execution. This
means that any package that is meant to be imported by other Python code
**must not, under any circumstances,** instantiate `LSAClient`.

Similarly, such packages must not make use of the following objects
(which all are just different ways to invoke the same import hook):

- the method
  :meth:`Manager.imports()<cmmnbuild_dep_manager.Manager.imports()>` of
  the :doc:`CommonBuild Dependency Manager <cmmnbuild:index>`;
- the module `jpype.imports` of :doc:`JPype <jpype:index>`, which
  executes code upon import.

Instead, such packages should simply import any Java packages they use,
**assuming that they are already available**. It is then the task of the
top-most Python script to import these packages with JPype properly set
up.
"""

try:
    from ._hooks import (
        AbstractHooks,
        DefaultHooks,
        Hooks,
        InconsistentHookInstalls,
        get_current_hooks,
    )
    from ._incorporator import Incorporator, IncorporatorGroup, NotFound
    from ._utils import (
        get_context_by_user,
        get_cycle_type_attributes,
        get_settings_function,
        incorporate_and_trim,
        trim_scalar_settings,
    )
except ImportError as exc:
    raise ImportError("import this package in `with LSAClient().java_api()`") from exc

__all__ = (
    "AbstractHooks",
    "DefaultHooks",
    "Hooks",
    "InconsistentHookInstalls",
    "Incorporator",
    "IncorporatorGroup",
    "NotFound",
    "get_context_by_user",
    "get_current_hooks",
    "get_cycle_type_attributes",
    "get_settings_function",
    "incorporate_and_trim",
    "trim_scalar_settings",
)
