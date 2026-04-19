"""AST-based extractor for PolicyEngine Variable subclasses.

Walks a directory of ``.py`` files, identifies ``Variable`` subclasses
by looking for ``class Foo(Variable):`` in the AST, and extracts
variable references from each class's ``formula*`` methods.

The extractor never imports user code, so it works on any PolicyEngine
source tree regardless of whether the jurisdiction is installed.
This keeps refactor-impact analysis and CI pre-merge checks fast and
dependency-free.

Two reference patterns are recognized:

1. ``<entity>("<var>", <period>)`` where ``<entity>`` is a bare ``Name``
   matching one of:
   ``person``, ``tax_unit``, ``spm_unit``, ``household``, ``family``,
   ``marital_unit``, ``benunit``, ``tax_unit``.
2. ``add(<entity>, <period>, [<list of string literals>])`` — the
   ``add`` helper that sums a list of variable names on an entity.

Limitations of the v1 extractor (tracked for v2):

- Parameter references (``parameters(period).gov.xxx.yyy``) are not
  yet captured; only variable-to-variable edges.
- Dynamic variable names built via string concatenation or format
  strings are skipped (low-prevalence in practice).
- ``entity.sum("var")`` or ``entity.mean("var")`` method calls are
  not yet recognized; only the direct-call form. (Low-prevalence
  in ``policyengine-us``; common enough to add as a small follow-up.)
"""

from __future__ import annotations

import ast
import os
from pathlib import Path
from typing import Iterable, Iterator, Sequence, Union

from policyengine.graph.graph import VariableGraph


# Names of entity instances as they appear as method parameters in
# Variable formulas. Any ``Call`` whose ``func`` is a bare ``Name``
# matching one of these AND whose first arg is a string literal is
# treated as a variable reference. Bare names (not attribute access)
# ensures we don't accidentally match something like
# ``reform.person("x", period)``.
_ENTITY_CALL_NAMES: frozenset[str] = frozenset(
    {
        "person",
        "tax_unit",
        "spm_unit",
        "household",
        "family",
        "marital_unit",
        "benunit",
    }
)


PathLike = Union[str, "os.PathLike[str]"]


def extract_from_path(path: PathLike) -> VariableGraph:
    """Build a ``VariableGraph`` from all ``.py`` files under ``path``.

    Directories are walked recursively. Files that fail to parse as
    Python (syntax errors) are silently skipped — the extractor is a
    best-effort tool over real source trees, not a compiler.
    """
    root = Path(path)
    graph = VariableGraph()

    files: Iterable[Path]
    if root.is_file():
        files = [root]
    else:
        files = root.rglob("*.py")

    for file_path in files:
        try:
            source = file_path.read_text()
        except (OSError, UnicodeDecodeError):
            continue
        try:
            tree = ast.parse(source, filename=str(file_path))
        except SyntaxError:
            continue
        _visit_module(tree, file_path=str(file_path), graph=graph)

    return graph


# -------------------------------------------------------------------
# AST traversal
# -------------------------------------------------------------------


def _visit_module(tree: ast.Module, *, file_path: str, graph: VariableGraph) -> None:
    """Register each Variable subclass and walk its formula methods."""
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        if not _class_inherits_variable(node):
            continue
        var_name = node.name
        graph.add_variable(var_name, file_path=file_path)
        for child in node.body:
            if isinstance(child, ast.FunctionDef) and _is_formula_method(child):
                for dependency in _extract_references(child):
                    graph.add_edge(dependency=dependency, dependent=var_name)


def _class_inherits_variable(cls: ast.ClassDef) -> bool:
    """True iff the class's base list contains a ``Variable`` name.

    Matches ``class X(Variable):``. Does not resolve aliased imports
    — PolicyEngine's ``from policyengine_us.model_api import *``
    convention keeps the base name literally ``Variable``, which is
    what real jurisdictions use and what this check matches.
    """
    for base in cls.bases:
        if isinstance(base, ast.Name) and base.id == "Variable":
            return True
    return False


def _is_formula_method(func: ast.FunctionDef) -> bool:
    """Return True for ``formula`` and ``formula_YYYY`` methods."""
    return func.name == "formula" or func.name.startswith("formula_")


# -------------------------------------------------------------------
# Reference extraction from a formula body
# -------------------------------------------------------------------


def _extract_references(func: ast.FunctionDef) -> Iterator[str]:
    """Yield every variable name referenced in the function body."""
    for node in ast.walk(func):
        if not isinstance(node, ast.Call):
            continue
        # Pattern 1: <entity>("<var>", <period>)
        entity_ref = _entity_call_to_variable(node)
        if entity_ref is not None:
            yield entity_ref
            continue
        # Pattern 2: add(<entity>, <period>, ["v1", "v2", ...])
        yield from _add_call_to_variables(node)


def _entity_call_to_variable(call: ast.Call) -> str | None:
    """Return the variable name if ``call`` is an entity-call pattern.

    The entity has to be a bare Name (not an attribute access), so
    calls like ``some.object.person("x", period)`` are deliberately
    not matched. First positional arg must be a string literal.
    """
    if not isinstance(call.func, ast.Name):
        return None
    if call.func.id not in _ENTITY_CALL_NAMES:
        return None
    if not call.args:
        return None
    first = call.args[0]
    if isinstance(first, ast.Constant) and isinstance(first.value, str):
        return first.value
    return None


def _add_call_to_variables(call: ast.Call) -> Iterator[str]:
    """Yield variable names from an ``add(entity, period, [list])`` call.

    Matches the common helper. The third positional arg must be a
    ``list`` literal of string literals. Anything dynamically built
    is skipped.
    """
    if not isinstance(call.func, ast.Name):
        return
    if call.func.id not in {"add", "aggr"}:
        return
    if len(call.args) < 3:
        return
    names_arg = call.args[2]
    if not isinstance(names_arg, (ast.List, ast.Tuple)):
        return
    for elt in names_arg.elts:
        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
            yield elt.value
