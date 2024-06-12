# SPDX-FileCopyrightText: 2020-2023 CERN
# SPDX-FileCopyrightText: 2023 GSI Helmholtzzentrum für Schwerionenforschung
# SPDX-FileNotice: All rights not expressly granted are reserved.
#
# SPDX-License-Identifier: GPL-3.0-or-later OR EUPL-1.2+

"""Submodule for global hooks into the LSA utilities."""

from __future__ import annotations

import sys
import warnings
from abc import ABCMeta, abstractmethod
from types import TracebackType

if sys.version_info < (3, 11):
    from typing_extensions import Self
else:
    from typing import Self


class InconsistentHookInstalls(Warning):
    """Hooks have been installed in another order than they've been installed."""


global_hooks: Hooks


class AbstractHooks(metaclass=ABCMeta):
    """The bare interface trim request hooks.

    These are the abstract methods that you can override to implement
    :ref:`guide/lsa_utils:Global Trim Request Hooks`. You should
    subclass `Hooks` instead of this class, since that also provides
    logic to install and uninstall your hooks.
    """

    @abstractmethod
    def trim_description(self, desc: str | None) -> str:
        """Hook to override the trim description.

        The argument is the description as passed by the user, or `None`
        if none was passed. The return value should be the description
        to actually use. Unlike the argument, this *must* be a string.

        Call :samp:`super().trim_description({desc})` to pass the
        decision on to the previously installed hook.
        """
        raise NotImplementedError

    @abstractmethod
    def trim_transient(self, transient: bool | None) -> bool:
        """Hook to override the transient-trim flag.

        The argument is the flag as passed by the user, or `None` if
        none was passed. The return value should be the transient-trim
        flag to actually use. Unlike the argument, this *must* be a
        bool, never `None`.

        Call :samp:`super().trim_transient({transient})` to pass the
        decision on to the previously installed hook.
        """
        raise NotImplementedError


class Hooks(AbstractHooks):
    """The base class for all trim request hooks.

    This is the class that you should subclass to implement your own
    :ref:`guide/lsa_utils:Global Trim Request Hooks`.

    This class implements the installation/uninstallation logic for
    hooks:

        >>> hooks = Hooks()
        >>> hooks.install_globally()
        >>> get_current_hooks() is hooks
        True
        >>> hooks.uninstall_globally()
        >>> get_current_hooks() is hooks
        False

    Instead of calling `~Hooks.install_globally()` and
    `~Hooks.uninstall_globally()` manually, it is usually easier to use
    the hooks as a :term:`context manager` in a :keyword:`with`
    statement:

        >>> with hooks:
        ...     assert get_current_hooks() is hooks

    This class also provides base implementations for the abstract
    methods defined by `AbstractHooks`; these simply forward the method
    call to whatever hook was installed before this one.

    Calling the hook methods while the hook is not installed raises a
    `RuntimeError`:

        >>> hooks.trim_description(None)
        Traceback (most recent call last):
        ...
        RuntimeError: called trim_description() on an uninstalled hook
    """

    def __init__(self) -> None:
        self.__parent: Hooks | None = None

    # pylint: disable = global-statement

    def install_globally(self) -> None:
        """Install this object as the new global trim request hook.

        .. note:: Consider using this object as a :term:`context
            manager` instead.

        This also links the previous hook to this one so that the hook
        methods' base implementations can find it.

        Raises:
            RuntimeError: if this object already is the current hook.
        """
        global global_hooks
        # Prevent self.__parent is self loop, since it would make
        # uninstallation impossible.
        if global_hooks is self:
            raise RuntimeError("hook is already installed")
        self.__parent, global_hooks = global_hooks, self

    def uninstall_globally(self) -> None:
        """Uninstall these hooks and install the previous ones.

        Every call to this method must be matched to a call to
        `install_globally()`.

        Warning:
            If this is not the currently installed hooks object, an
            `InconsistentHookInstalls` warning is issued. In this case,
            all hooks installed after this one are also uninstalled. If
            this hook was never installed, all custom hooks are
            uninstalled and the defaults are reinstated.
        """
        global global_hooks
        if global_hooks is not self:
            warnings.warn(
                f"current hook is {global_hooks!r}, but expected "
                f"{self!r}, child of {self.__parent!r}",
                InconsistentHookInstalls,
                stacklevel=2,
            )
        if self.__parent is None:
            raise RuntimeError("cannot uninstall root hooks")
        global_hooks, self.__parent = self.__parent, None

    # pylint: enable = global-statement

    def __enter__(self) -> Self:
        self.install_globally()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.uninstall_globally()

    def trim_description(self, desc: str | None) -> str:
        if not self.__parent:
            raise RuntimeError("called trim_description() on an uninstalled hook")
        return self.__parent.trim_description(desc)

    def trim_transient(self, transient: bool | None) -> bool:
        if not self.__parent:
            raise RuntimeError("called trim_transient() on an uninstalled hook")
        return self.__parent.trim_transient(transient)


class DefaultHooks(Hooks):
    """Default implementation for the `Hooks`.

    This implementation is used whenever no other hooks are installed.
    It is stateless and all instances are equal to each other:

        >>> DefaultHooks() == DefaultHooks()
        True
    """

    def __eq__(self, other: object) -> bool:
        # pylint: disable = unidiomatic-typecheck
        if type(self) is type(other):
            return True
        return NotImplemented

    def __ne__(self, other: object) -> bool:
        return not self == other

    def trim_description(self, desc: str | None) -> str:
        """Default trim description.

        The default description is ``"via cernml-coi-utils"`` (the name
        of this distribution package). If the user passes a description,
        it is used instead.
        """
        return desc if desc is not None else "via cernml-coi-utils"

    def trim_transient(self, transient: bool | None) -> bool:
        """Default transient-trim flag.

        The default flag is `True`, unless the user explicitly passed
        `False`.
        """
        return transient if transient is not None else True


global_hooks = DefaultHooks()


def get_current_hooks() -> AbstractHooks:
    """Return the currently installed `Hooks`.

    If no hooks are currently installed, `DefaultHooks()` are returned
    instead.
    """
    return global_hooks
