Communicating with the LSA Database
===================================

In the general case, full interaction with the LSA database is already
supported through the `Pjlsa`_ package. However, this package exposes the full
Java API. This gives the user full flexibility, but also makes it difficult to
solve certain common problems without writing many lines of code.

.. _pjlsa: https://gitlab.cern.ch/scripting-tools/pjlsa/

This package wraps Pjlsa and provides a simple, Pythonic wrapper that solves
80% of all use cases. It makes no claim to being complete and contributions are
welcome.

Importing an LSA-Dependent Package
----------------------------------

The `~cernml.lsa_utils` package directly imports Java packages via the JPype
import system. It does not set up the JVM for you, so you have to start the JVM
before importing the package. (In this regard, `~cernml.lsa_utils` itself
behaves as if it were a Java package.)

The cleanest way to import `~cernml.lsa_utils` is to use PJLSA's context
manager for enabling Java imports:

.. code-block:: python

    import pjlsa

    lsa_client = pjlsa.LSAClient()
    with lsa_client.java_api():
        from cernml import lsa_utils
    context = lsa_utils.get_context_by_user("SPS.USER.ALL")

Note that the context manager only manages a change in the Python *import*
system. Once a Java package has been imported, it remains available and
functional, even outside of the context. (As long as functions or methods
inside the package don't make additional imports, of course.)

If you need Java imports enabled for a longer time, there are two options:

1. You can call a ``main()`` function inside the :keyword:`with` block.
2. You can import another module of your own inside the :keyword:`with` block
   and write your program logic in this inner module.

If none of these solutions work for you, you may also use the
`jpype:jpype.imports` module, which permanently modifies the import system:

.. code-block:: python

    import pjlsa

    lsa_client = pjlsa.LSAClient()

    import jpype.imports
    # From here on, Java imports are okay.

    import java.lang
    import cern.lsa.client
    import cernml.lsa_utils

Trimming One or Several Scalar Settings
---------------------------------------

The function `~cernml.lsa_utils.trim_scalar_settings()` provides a convenient
way to trim scalar settings in the LSA database. In the simplest case, you
simply pass a mapping of parameter name to new value and the context to be
modified:

.. code-block:: python

    lsa_utils.trim_scalar_settings(
        {"ER.KFH31/SettingA#kickStrengthCcvA": 54.5},
        context="Pb54_2BP_2021_06_09_EARLY_2400ms_V1",
    )

If the context is mapped to a user, you can also specify the **user** instead
of the context:

.. code-block:: python
    :emphasize-lines: 3

    lsa_utils.trim_scalar_settings(
        {"ER.KFH31/SettingA#kickStrengthCcvA": 54.5},
        user="LEI.USER.NOMINAL",
    )

If the mapping contains **multiple parameters**, they are changed
*transactionally*: the trim only succeeds if all settings can be applied. If
any one of them fails, the trim is rolled back and changes are applied at all.
Furthermore, the entire trim occupies only one entry in the trim history.

You can pass an additional *description* parameter to document your trim in the
trim history:

.. code-block:: python
    :emphasize-lines: 4

    lsa_utils.trim_scalar_settings(
        {"ER.KFH31/SettingA#kickStrengthCcvA": 54.5},
        user="LEI.USER.NOMINAL",
        description="Reset kick strength to known good value",
    )

If you pass a true value for the *relative* flag, all changes are applied on
top of the current settings:

.. code-block:: python
    :emphasize-lines: 4

    lsa_utils.trim_scalar_settings(
        {"ER.KFH31/SettingA#kickStrengthCcvA": 0.1},
        user="LEI.USER.NOMINAL",
        relative=True,
        description="Increase KFH31 kick strength slightly",
    )

All types of scalar settings are supported: integers, booleans and
floating-point values – both the built-in Python types and NumPy variants – are
automatically converted to Java objects. If you want to trim an enum setting,
you can pass either an integer (which denotes the enum's ordinal number), or a
string (which denotes its name):

.. code-block:: python

    # Instead of "ON" and "OFF", you could also pass 1 and 0 resp.
    # for this particular enum.
    lsa_utils.trim_scalar_settings(
        {"ER.KFH31/SettingA#kickOnA": "ON"},
        user="LEI.USER.NOMINAL",
    )

Trimming a Single Function
--------------------------

Unless you want to pass an entire function object every time, trimming a
function is slightly more complicated than trimming scalar settings. There are
two ways to solve this task using `~cernml.lsa_utils`.

The simple one is by using the free function
`~cernml.lsa_utils.incorporate_and_trim()`. There are several other functions
to make using it easier:

.. code-block:: python

    import numpy as np

    context = lsa_utils.get_context_by_user("SPS.USER.HIRADMT1")
    assert context == "HIRADMAT_PILOT_Q20_2018_V1"

    xs, ys = lsa_utils.get_settings_function("logical.RDH.20207/J", context)
    assert isinstance(xs, np.ndarray)
    assert isinstance(ys, np.ndarray)
    assert xs.shape == ys.shape

    attrs = lsa_utils.get_cycle_type_attributes(context)["VE:Start flat top"]
    assert attrs["VE:Start flat top"] == "6200"

    lsa_utils.incorporate_and_trim(
        "logical.RDH.20208/J", context, cycle_time=1440.0, value=0.0,
        relative=False,
        description="Usage example of cernml.lsa_utils",
    )

The slightly more complex one is to create an `~cernml.lsa_utils.Incorporator`
and call the respective methods on it. This class avoids conversion from Python
strings to LSA objects on every function call. Thus, if you are going to make
multiple calls using the same parameter and context, this is going to be
slightly more efficient.

.. code-block:: python

    inc = lsa_utils.Incorporator(
        "logical.RDH.20207/J",
        user="SPS.USER.HIRADMT1",
    )
    assert inc.context == "HIRADMAT_PILOT_Q20_2018_V1"

    xs, ys = inc.get_function()
    assert isinstance(xs, np.ndarray) and isinstance(ys, np.ndarray)
    assert xs.shape == ys.shape

    inc.incorporate_and_trim(
        1440.0, 0.0, relative=False, description="Usage example"
    )

Trimming Multiple Functions
---------------------------

The `~cernml.lsa_utils` package also allows trimming several functions with a
single trim, as long as they're modified in the same location. (This
requirement may be relaxed in the future, if necessary.) Again, there are two
ways to achieve this. The simple one is by using the same function
`~cernml.lsa_utils.incorporate_and_trim()` as for one parameter:

.. code-block:: python

    lsa_utils.incorporate_and_trim(
        [
            "logical.MDAH.2303/K",
            "logical.MDAH.2307/K",
            "logical.MDAV.2301.M/K",
            "logical.MDAV.2305.M/K",
        ],
        context="SFT_PRO_MTE_L4780_2022_V1",
        cycle_time=4460.0,
        value=[0.1, -0.1, 0.0, 0.05],
        relative=False,
        description="Usage example of cernml.lsa_utils",
    )

The first parameter is a list of all functions that should be changed
simultaneously, the second is the context to use. Then come the point to modify
(measured in milliseconds since the start of cycle) and the value to
incorporate. This may be anything that converts to a NumPy array of the correct
size (including a single float). The remaining parameters are the same as
before.

For a more object-oriented interface, you can use
`~cernml.lsa_utils.IncorporatorGroup`:

.. code-block:: python

    group = lsa_utils.IncorporatorGroup(
        [
            "logical.MDAH.2303/K",
            "logical.MDAH.2307/K",
            "logical.MDAV.2301.M/K",
            "logical.MDAV.2305.M/K",
        ],
        user="SPS.USER.HIRADMT1",
    )
    assert group.context == "HIRADMAT_PILOT_Q20_2018_V1"

    # Increase all parameters by 0.1:
    group.incorporate_and_trim(
        4460.0, 0.1, relative=True, description="Usage example"
    )

The group also allows creating one `~cernml.lsa_utils.Incorporator` for each
parameter individually:

.. code-block:: python

    inc = group.get("logical.MDAH.2303/K")
    assert isinstance(inc, lsa_utils.Incorporator)

    parameters = tuple(
        incorporator.parameters for incorporator in group.incorporators()
    )
    assert parameters == group.parameters == (
        "logical.MDAH.2303/K",
        "logical.MDAH.2307/K",
        "logical.MDAV.2301.M/K",
        "logical.MDAV.2305.M/K",
    )

Incorporation Ranges
--------------------

In order to modify a function via Python, at least one *incorporation range*
must be defined for it. Incorporation ranges define how a modification of the
function is incorporated into its overall shape and serve to preserve certain
properties of continuity, flatness, etc.

Incorporation ranges are defined for each beam process, parameter and
(optionally) parameter group. One simple way to figure out the beam processes
for a given context by hand, you can open the LSA App Suite, start settings
management, select the desired context and enable "Show Sub Contexts".

.. image:: incorporation-settings.png
    :alt: Screenshot of the LSA App Suite settings management.

To create an incorporation range, you stay within the LSA App Suite and start
the Incorporation Ranges app under the category "Contexts". There, you can pick
the beam process, parameter and parameter group. If a rule should apply to
multiple similar parameters, you can set the parameter group to "all".

.. image:: incorporation-rules.png
    :alt: Screenshot of the LSA App Suite incorporation ranges manager.

Each incorporation range has a *start* and *end* as well as a *forward rule*
and a *backward rule*. The *start* and *end* determine the time interval within
the beam process for which the range is valid. They're measured in milliseconds
from the start of the beam process. By clicking the drop-down button, you can
also enter special constants that refer to the start and end of the entire beam
process.

It is not possible to define incorporation ranges that span multiple beam
processes. It is also not *advisable* to modify a function close to the start
or the end of the beam process. Generally, the incorporation rules will only be
applied up to the beam process edge linear interpolation will occur up to the
closest point in the next beam process, wherever that point may be.

The forward and backward rules define how a modification at a single point is
propagated into the range. Most rules take an additional time parameter.
Generally, they define how smoothly a change is incorporated. As for *start*
and *end*, the parameter may be set to certain constants such as "start of beam
process" or "start of incorporation range".

The most important rules are given below. In the app, you can also click the
question mark icon to get more help on how they work.

``CONSTANTIR``
    All points in the current beam process are set to the same value. This
    ignores the rule parameter as well as the length of the incorporation range
    (except to check whether the rule may be applied at all).

``DELTAIR``
    The selected point is set to the desired value. In addition, an interval
    whose length is given by the rule parameter is raised or lowered by the
    same amount. The shape of the function within this interval is preserved.
    Note that this interval is unrelated to the incorporation range. Outside of
    this interval, no further continuity constraints are applied  – the
    function is simply linearly interpolated to the next point, wherever that
    may be.

``CONSTANT_DECAY_IR``
    The selected point is set to the desired value. In the interval whose
    length is given by the rule parameter, the delta that was necessary to
    achieve this change is linearly decreased to zero. The shape of the
    function within this interval is honored.

``TRIANGLEIR``
    The selected point is set to the desired value. The function is linearly
    interpolated over an interval whose length is given by the rule parameter.
    The function is flattened over the given interval. This is the main
    difference between this rule and ``CONSTANT_DECAY_IR``.

Note that the incorporation range has no effect on how these rules behave; it
only determines the time interval for which they are valid. For example, you
can declare an incorporation range from 400 to 700 ms where both rules are
``CONSTANT_DECAY_IR`` with a parameter of 40 ms. In this case:

1. Incorporating a change at 400 ms will modify the function in the interval
   from 360 to 440 ms by linearly decreasing the delta to zero.
2. Incorporating a change at 600 ms will modify the interval from 560 to 640
   ms. This does not overlap with the previous change, but uses the same rule
   and leads to the same triangular shape.
3. Incorporating a change at 650 ms will overlap with cause an overlap with the
   previous interval. This will honor the previously falling slop, but add its
   own changes on top.
4. An attempt to incorporate a change at 710 ms will fail, as it is outside of
   the incorporation range.

.. image:: incorporation-result.png
   :alt: Result of the above incorporations into a constant function.
