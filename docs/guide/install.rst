..
    SPDX-FileCopyrightText: 2020-2024 CERN
    SPDX-FileCopyrightText: 2023-2024 GSI Helmholtzzentrum für Schwerionenforschung
    SPDX-FileNotice: All rights not expressly granted are reserved.

    SPDX-License-Identifier: GPL-3.0-or-later OR EUPL-1.2+

Installation
============

There are multiple ways to install this project. In any case, `virtual
environments`_ help to isolate your dependencies from each other.

.. _virtual environments:
    https://wikis.cern.ch/display/ACCPY/Development+advice

Install via Pip
---------------

The preferred way to install this project is via Pip from the CERN-internal
package repository. All you have to do is set up your `Acc-Py environment`_ and
invoke:

.. _Acc-Py environment:
    https://wikis.cern.ch/display/ACCPY/Getting+started+with+Acc-Py

.. code-block:: shell-session

    $ pip install cernml-coi-utils[all]

which installs the utils and all their dependencies. If you only need specific
utilities, you can specify their :ref:`respective dependencies
<setuptools:keyword/extras_require>` instead of "all". The above line is
equivalent to:

.. code-block:: shell-session

    $ pip install cernml-coi-utils[matplotlib,pjlsa,pyjapc]

Install from Source
-------------------

You can also install this project from source. This is the preferred method if
you plan to hack on it. Clone the `Git repository`_, enter its directory,  and
tell Pip to install whatever is in the current directory:

.. _Git repository: https://gitlab.cern.ch/geoff/cernml-coi-utils

.. code-block:: shell-session

    $ git clone ... # URL of your choice: HTTPS, SSH or Kerberos authentication.
    $ cd awake
    $ pip install .[all]              # Install a copy.
    $ pip install --editable .[all]   # Install a symlink.

The :option:`--editable` flag installs the package in :ref:`editable mode
<pip:editable-installs>`, a convenience feature for developers. This will *not*
copy the code into your virtual environment; instead, it creates symlinks to
the source directory. This way, any changes you make in the code will be
reflected immediately in the installation.

Install from a Wheel
--------------------

Finally, if none of the above work, you can also download a previously built
distribution of this project and install it manually. On its Gitlab_ page, you
can view all `CI/CD pipelines that belong to a tag`_. Pick the pipeline for the
version you are interested in and click the :guilabel:`Download` button on the
far right to pull down a list of artifacts. Choose the artifact labeled
:guilabel:`build_wheel`. Download the zip file offered by the server and unpack
it. Inside you find a wheel file (``*.whl``) that you can install via Pip:

.. _Gitlab: https://gitlab.cern.ch/geoff/cernml-coi-utils/
.. _CI/CD pipelines that belong to a tag:
   https://gitlab.cern.ch/geoff/cernml-coi-utils/-/pipelines?scope=tags

.. code-block:: shell-session

    $ unzip artifacts.zip
    $ pip install ./wheelhouse/cern_awake_env-VERSION-py3-none-any.whl

This method installs only this project and nothing else. It is on you to find
and install the correct dependencies.
