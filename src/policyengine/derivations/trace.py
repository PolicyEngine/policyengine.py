"""Deterministic computation-trace extraction.

Turns the live OpenFisca tracer output for a single variable into a stable
:class:`Derivation` data class. Everything here is pure and side-effect-free
once the tracer has captured the calculation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable


@dataclass(frozen=True)
class TraceNode:
    """One node in the pruned computation tree.

    Mirrors OpenFisca's per-variable trace entry: the variable name, the
    scalar value it took for the requested household, and its immediate
    dependencies (each themselves a :class:`TraceNode`). Booleans surface as
    Python ``bool``; numeric values surface as ``float``.
    """

    name: str
    value: Any
    children: tuple[TraceNode, ...] = field(default_factory=tuple)

    def to_text(self, *, max_depth: int = 8, prune_zero: bool = True) -> str:
        """Render the tree as an indented text block.

        Parameters
        ----------
        max_depth:
            Stop descending below this depth (root has depth 0).
        prune_zero:
            When True (the default), zero-valued subtrees below depth 1 are
            omitted from the rendering. This is the format we feed to LLMs:
            keep the top-level zero categories so the model knows they were
            considered, but drop the cascading zero leaves under them.
        """

        lines: list[str] = []
        _render(self, depth=0, lines=lines, max_depth=max_depth, prune_zero=prune_zero)
        return "\n".join(lines)


@dataclass(frozen=True)
class Derivation:
    """A single variable's computation, captured as a structured tree.

    ``Derivation`` is the deterministic core of an explanation. It can be
    rendered as text, walked programmatically for charts, or passed to
    :func:`policyengine.derivations.narrate` for a prose summary.
    """

    variable: str
    value: Any
    trace: TraceNode
    period: Any

    def trace_text(self, *, max_depth: int = 8, prune_zero: bool = True) -> str:
        """Convenience wrapper around :meth:`TraceNode.to_text`."""
        return self.trace.to_text(max_depth=max_depth, prune_zero=prune_zero)

    def top_level_contributions(self) -> list[tuple[str, Any]]:
        """``[(child_variable_name, value), ...]`` for the root's children.

        Useful when you want a deterministic structured breakdown next to the
        prose narrative — e.g. "the answer is the sum of these named pieces".
        """
        return top_level_contributions(self)


def _scalar(value: Any) -> Any:
    """Reduce a vectorized OpenFisca result to a single Python scalar."""
    if hasattr(value, "__len__") and len(value):
        item = value[0]
    else:
        item = value
    if hasattr(item, "item"):
        item = item.item()
    return item


def is_zero_value(value: Any) -> bool:
    """True if ``value`` is the zero of its type (False, 0, 0.0).

    Exported because callers sometimes want to filter their own copies of the
    tree without redefining what "zero" means.
    """
    item = _scalar(value)
    if isinstance(item, bool):
        return item is False
    if isinstance(item, (int, float)):
        return item == 0
    return False


def _convert(node: Any) -> TraceNode:
    """Convert an OpenFisca tracer node into our stable ``TraceNode`` shape."""
    return TraceNode(
        name=node.name,
        value=_scalar(node.value),
        children=tuple(_convert(child) for child in node.children),
    )


def _render(
    node: TraceNode,
    *,
    depth: int,
    lines: list[str],
    max_depth: int,
    prune_zero: bool,
) -> None:
    if depth > max_depth:
        return
    if prune_zero and depth > 1 and is_zero_value(node.value):
        return
    lines.append("  " * depth + node.name + " = " + _format_value(node.value))
    for child in node.children:
        _render(
            child,
            depth=depth + 1,
            lines=lines,
            max_depth=max_depth,
            prune_zero=prune_zero,
        )


def _format_value(value: Any) -> str:
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, float):
        return f"{value:.2f}".rstrip("0").rstrip(".") or "0"
    return str(value)


def _find_root(roots: Iterable[Any], target: str) -> Any | None:
    """Depth-first search the tracer roots for a node named ``target``."""
    for root in roots:
        if root.name == target:
            return root
        match = _find_root(root.children, target)
        if match is not None:
            return match
    return None


def derive(simulation: Any, variable: str, period: Any) -> Derivation:
    """Compute ``variable`` on ``simulation`` and return a structured derivation.

    The caller is responsible for owning the ``Simulation`` and any reform on
    it. ``derive`` turns the tracer on (if not already on), clears any prior
    trees so the captured tree is exactly the one we asked for, runs the
    calculation, and converts the resulting tree to a stable ``TraceNode``.
    """

    simulation.trace = True
    if hasattr(simulation, "tracer") and hasattr(simulation.tracer, "trees"):
        simulation.tracer.trees.clear()
    simulation.calculate(variable, period)

    if not hasattr(simulation, "tracer") or not simulation.tracer.trees:
        raise RuntimeError(
            f"No trace recorded after calculating {variable!r}. "
            "Ensure the simulation backend supports tracing."
        )
    root = _find_root(simulation.tracer.trees, variable)
    if root is None:
        raise RuntimeError(
            f"Tracer did not produce a root for {variable!r}. "
            "This usually means the variable was already cached."
        )
    return Derivation(
        variable=variable,
        value=_scalar(root.value),
        trace=_convert(root),
        period=period,
    )


def top_level_contributions(derivation: Derivation) -> list[tuple[str, Any]]:
    """Return ``[(name, value), ...]`` for the immediate dependencies of the root.

    Children appear in the order OpenFisca recorded them. Use this when you
    want a deterministic structured breakdown alongside the prose narrative.
    """
    return [(child.name, child.value) for child in derivation.trace.children]
