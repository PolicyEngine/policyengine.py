"""Derivations: structured + narrated explanations of one variable's value.

A ``Derivation`` is the pruned, deterministic computation tree for a single
``(simulation, variable)`` pair. The tree is the same information OpenFisca
already records when ``simulation.trace`` is on, but presented as a stable
data class (independent of OpenFisca internals) so callers can:

- print or serialize the structured tree (deterministic, free),
- pull out top-level contributions for charts or tables, and
- optionally hand the derivation to an LLM via :func:`narrate` for a plain-prose
  walkthrough (the only step that requires a network call).

This module deliberately separates the *deterministic* part of the explanation
(everything in ``Derivation``) from the *narration* (an external LLM call). A
caller can use one without the other.
"""

from .narrate import narrate, narrate_async
from .trace import (
    Derivation,
    TraceNode,
    derive,
    is_zero_value,
    top_level_contributions,
)

__all__ = [
    "Derivation",
    "TraceNode",
    "derive",
    "is_zero_value",
    "narrate",
    "narrate_async",
    "top_level_contributions",
]
