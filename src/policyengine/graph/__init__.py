"""Variable dependency graph for PolicyEngine source trees.

Parses ``Variable`` subclasses in a PolicyEngine jurisdiction (e.g.
``policyengine-us``, ``policyengine-uk``) and extracts the variable-
to-variable dataflow graph from formula-method bodies.

The extractor is static: it walks the Python AST and never imports
user code, so it works on any PolicyEngine source tree without
requiring the jurisdiction to be installed or the country model to
resolve. That makes it usable for refactor-impact analysis, CI
pre-merge checks, docs generation, and code-introspection queries
from a Claude Code plugin.

Recognized reference patterns in v1:

- ``<entity>("<var>", <period>)`` — direct call on an entity instance
  (``person``, ``tax_unit``, ``spm_unit``, ``household``, ``family``,
  ``marital_unit``, ``benunit``).
- ``add(<entity>, <period>, ["v1", "v2", ...])`` — sum helper; each
  string in the list becomes an edge.

Typical usage:

.. code-block:: python

    from policyengine.graph import extract_from_path

    graph = extract_from_path("/path/to/policyengine-us/policyengine_us/variables")
    # Variables that transitively depend on AGI:
    for downstream in graph.impact("adjusted_gross_income"):
        print(downstream)
    # Direct dependencies of a variable:
    print(graph.deps("earned_income_tax_credit"))
    # Dependency chain from one variable to another:
    print(graph.path("wages", "federal_income_tax"))
"""

from policyengine.graph.extractor import extract_from_path
from policyengine.graph.graph import VariableGraph

__all__ = ["VariableGraph", "extract_from_path"]
