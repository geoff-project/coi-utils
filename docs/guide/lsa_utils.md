# Communicating with the LSA Database

In the general case, full interaction with the LSA database is already
supported through the [Pjlsa](https://gitlab.cern.ch/scripting-tools/pjlsa/)
package. However, this package exposes the full Java API. This gives the user
full flexibility, but also makes it difficult to solve certain common problems
without writing many lines of code.

This package wraps Pjlsa and provides a simple, Pythonic wrapper that solves
80% of all use cases. It makes no claim to being complete and contributions are
welcome.

## Importing an LSA-Dependent Package

The {mod}`~cernml.lsa_utils` package directly imports Java packages via the
JPype import system. It does not set up the JVM for you, so you have to start
the JVM before importing the package. (In this regard, {mod}`~cernml.lsa_utils`
itself behaves as if it were a Java package.)

The cleanest way to import {mod}`~cernml.lsa_utils` is to use PJLSA's context
manager for enabling Java imports:

```{code-block} python
import pjlsa

lsa_client = pjlsa.LSAClient()
with lsa_client.java_api():
    from cernml import lsa_utils
context = lsa_utils.get_context_by_user("SPS.USER.ALL")
```

Note that the context manager only manages a change in the Python *import*
system. Once a Java package has been imported, it remains available and
functional, even outside of the context. (As long as functions or methods
inside the package don't make additional imports, of course.)

If you need Java imports enabled for a longer time, there are two options:
1. You can call a `main()` function inside the {keyword}`with` block.
2. You can import another module of your own inside the {keyword}`with` block
   and write your program logic in this inner module.

If none of these solutions work for you, you may also use the
{mod}`jpype:jpype.imports` module, which permanently modifies the import
system:

```{code-block} python
import pjlsa

lsa_client = pjlsa.LSAClient()

import jpype.imports
# From here on, Java imports are okay.

import java.lang
import cern.lsa.client
import cernml.lsa_utils
```

## Usage Examples

There are two ways to use {mod}`~cernml.lsa_utils`. The simple one is by using
the free functions that it provides:

```{code-block} python
import numpy as np

context = lsa_utils.get_context_by_user("SPS.USER.HIRADMT1")
assert context == "HIRADMAT_PILOT_Q20_2018_V1"

xs, ys = lsa_utils.get_settings_function("logical.RDH.20207/J", context)
assert isinstance(xs, np.ndarray) and isinstance(ys, np.ndarray)
assert xs.shape == ys.shape

attrs = lsa_utils.get_cycle_type_attributes(context)["VE:Start flat top"]
assert attrs["VE:Start flat top"] == "6200"

lsa_utils.incorporate_and_trim(
    "logical.RDH.20208/J", context, cycle_time=1440.0, value=0.0,
    relative=False,
    description="Usage example of cernml.lsa_utls",
)
```

The slightly more complex one is to create an
{class}`~cernml.lsa_utils.Incorporator` and call the respective methods on it.
This class avoids conversion from Python strings to LSA objects on every
function call. Thus, if you are going to make multiple calls using the same
parameter and context, this is going to be slightly more efficient.

```{code-block} python
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
```
