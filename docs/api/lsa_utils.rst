..
    SPDX-FileCopyrightText: 2020-2024 CERN
    SPDX-FileCopyrightText: 2023-2024 GSI Helmholtzzentrum für Schwerionenforschung
    SPDX-FileNotice: All rights not expressly granted are reserved.

    SPDX-License-Identifier: GPL-3.0-or-later OR EUPL-1.2+

PJLSA Utilities
===============

.. seealso::

    :doc:`/guide/lsa_utils`
        User guide page on this module.

.. automodule:: cernml.lsa_utils

Free-Function API
-----------------

.. autofunction:: get_context_by_user
.. autofunction:: get_cycle_type_attributes
.. autofunction:: get_settings_function
.. autofunction:: trim_scalar_settings
.. autofunction:: incorporate_and_trim
.. autoexception:: NotFound
    :show-inheritance:

Object-Oriented API
-------------------

.. autoclass:: Incorporator
    :show-inheritance:
    :members:
.. autoclass:: IncorporatorGroup
    :show-inheritance:
    :members:

Global Trim Request Hooks
-------------------------

See also :ref:`guide/lsa_utils:Global Trim Request Hooks` in the
:doc:`/guide/index`.

.. autoclass:: AbstractHooks
    :show-inheritance:
    :members:
.. autoclass:: Hooks
    :show-inheritance:
    :members: install_globally, uninstall_globally
.. autoclass:: DefaultHooks
    :show-inheritance:
    :members:
.. autofunction:: get_current_hooks
.. autoexception:: InconsistentHookInstalls
    :show-inheritance:
