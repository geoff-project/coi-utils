# SPDX-FileCopyrightText: 2020-2024 CERN
# SPDX-FileCopyrightText: 2023-2024 GSI Helmholtzzentrum für Schwerionenforschung
# SPDX-FileNotice: All rights not expressly granted are reserved.
#
# SPDX-License-Identifier: GPL-3.0-or-later OR EUPL-1.2+

"""Extension that lets you handle fixes for screwed-up cross-references."""

from __future__ import annotations

import enum
import logging
import re
import typing as t

from docutils.nodes import Element, Text, TextElement, reference
from sphinx.ext import intersphinx

if t.TYPE_CHECKING:
    from sphinx.addnodes import pending_xref
    from sphinx.application import Sphinx
    from sphinx.environment import BuildEnvironment
    from sphinx.util.typing import ExtensionMetadata

LOG = logging.getLogger(__name__)

T = t.TypeVar("T", bound=t.Callable)


class nondescriptor(t.Generic[T]):
    """Function wrapper that can be used as enum value."""

    __slots__ = ("__func__", "__call__")

    def __init__(self, func: T) -> None:
        self.__call__ = self.__func__ = func


@enum.unique
class TransformKind(enum.Enum):
    """The first element of tuples for transform rules."""

    @nondescriptor
    @staticmethod
    def CONST(match: re.Match[str], arg: str) -> str:
        """Replace the entire target with *arg*."""
        return arg

    @nondescriptor
    @staticmethod
    def SUB(match: re.Match[str], arg: str) -> str:
        """Replace the matched part of the target with *arg*."""
        return match.re.sub(arg, match.string, 1)


class ExternalRef(t.TypedDict):
    """Description of an external reference."""

    package: str
    uri: str


class XrefRule(t.TypedDict, total=False):
    """Description of the dicts accepted as xref fixing rules."""

    pattern: str | t.Pattern
    reftype: str | None
    reftarget: tuple[str | TransformKind, str]
    contnode: tuple[str | TransformKind, str]
    external: ExternalRef


def retry_resolve_xref(
    app: Sphinx,
    env: BuildEnvironment,
    node: pending_xref,
    contnode: TextElement,
) -> reference | None:
    """Run the resolve procedure again.

    This should be called after `node` has been modified in some way. It
    first tries the internal resolver before resorting to Intersphinx.
    """
    domain = env.domains[node["refdomain"]]
    return domain.resolve_xref(
        env,
        node["refdoc"],
        app.builder,
        node["reftype"],
        node["reftarget"],
        node,
        contnode,
    ) or intersphinx.missing_reference(app, env, node, contnode)


def replace(match: re.Match[str], transform: tuple[str | TransformKind, str]) -> str:
    """Apply a transform rule to *target*."""
    kind, arg = transform
    if isinstance(kind, str):
        kind = TransformKind[kind.upper()]
    return kind.value(match, arg)


def make_external_ref(contnode: TextElement, uri: str, package: str) -> reference:
    """Create a new reference node that wraps *contnode*."""
    newnode = reference(
        "", "", internal=False, refuri=uri, reftitle=f"(in {package!s})"
    )
    newnode.append(contnode)
    return newnode


def fix_xrefs(
    app: Sphinx,
    env: BuildEnvironment,
    node: pending_xref,
    contnode: TextElement,
) -> Element | None:
    """Link type variables to `typing.TypeVar`."""
    target: str = node["reftarget"]
    rules: list[XrefRule] = app.config.fix_xrefs_rules
    for rule in rules:
        if match := re.search(rule["pattern"], target):
            if reftype := rule.get("reftype", "obj"):
                node["reftype"] = reftype
            if reftarget_transform := rule.get("reftarget"):
                node["reftarget"] = replace(match, reftarget_transform)
            if cont_transform := rule.get("contnode"):
                target = replace(match, cont_transform)
                contnode = t.cast(TextElement, Text(target))
            if external := rule.get("external"):
                uri = external["uri"].format(**node.attributes)
                package = external["package"].format(**node.attributes)
                LOG.info("replace xref: %s -> %s", target, uri)
                return make_external_ref(contnode, uri=uri, package=package)
            LOG.info("fix xref: %s -> %s", target, node["reftarget"])
            break
    else:
        if app.config.fix_xrefs_try_typing and hasattr(t, target):
            # Some typing members don't get their module resolved.
            node["reftarget"] = "typing." + target

    return retry_resolve_xref(app, env, node, contnode)


def setup(app: Sphinx) -> ExtensionMetadata:
    """Set up hooks into Sphinx."""
    app.setup_extension("sphinx.ext.intersphinx")
    app.add_config_value("fix_xrefs_rules", [], "env", list[XrefRule])
    app.add_config_value("fix_xrefs_try_typing", False, "env", bool)
    app.connect("missing-reference", fix_xrefs)
    return {
        "version": "1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
