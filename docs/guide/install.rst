..
    SPDX-FileCopyrightText: 2020-2024 CERN
    SPDX-FileCopyrightText: 2023-2024 GSI Helmholtzzentrum für Schwerionenforschung
    SPDX-FileNotice: All rights not expressly granted are reserved.

    SPDX-License-Identifier: GPL-3.0-or-later OR EUPL-1.2+

Installation
============

There are multiple ways to install this project. In any case, `virtual
environments`_ help to isolate your dependencies from each other.

.. _`virtual environments`: https://wikis.cern.ch/display/ACCPY/Development+advice

Install via Pip
---------------

The preferred way to install this project is via Pip from the CERN-internal
package repository. All you have to do is set up your `Acc-Py environment`_ and
invoke:

.. _`Acc-Py environment`: https://wikis.cern.ch/display/ACCPY/Getting+started+with+Acc-Py

.. code-block:: shell-session

    $ pip install cernml-coi-utils[all]

which installs the utils and all their dependencies. If you only need specific
utilities, you can specify their respective dependencies instead of "all". The
above line is equivalent to:

.. code-block:: shell-session

    $ pip install cernml-coi-utils[matplotlib,pjlsa,pyjapc]

Install from Source
-------------------

You can also install this project from source. This is the preferred method if
you plan to hack on it. Clone the Git repository, enter its directory,  and
tell Pip to install whatever is in the current directory:

.. code-block:: shell-session

    $ git clone ... # URl of your choice: HTTPS, SSH or Kerberos authentication.
    $ cd awake
    $ pip install .[all]              # Install a copy.
    $ pip install --editable .[all]   # Install a symlink.

The ``--editable`` flag is a convenience feature for developers. This will skip
copying the code into your environment and instead create symlinks to the
source directory. This way, any changes you make in the code will be reflected
immediately in the installation.

Install from a Wheel
--------------------

Finally, if none of the above work, you can also download a previously built
distribution of this project and install it manually. On its `Gitlab`_ page,
navigate through `Repository`_ to the `Tags`_ page. On the latest tag, click
the *Download* button (next to the green checkmark) and choose the
*built_wheel* artifacts. Download the zip file offered by the server and unpack
it. Inside you find a wheel file (``*.whl``) that you can install via Pip:

.. _Gitlab: https://gitlab.cern.ch/geoff/cernml-coi-utils/
.. _Repository: https://gitlab.cern.ch/geoff/cernml-coi-utils/-/tree/master
.. _Tags: https://gitlab.cern.ch/geoff/cernml-coi-utils/-/tags

.. code-block:: shell-session

    $ unzip artifacts.zip
    $ pip install ./wheelhouse/cern_awake_env-VERSION-py3-none-any.whl

This method installs only this project and nothing else. It is on you to find
and install the correct dependencies.
