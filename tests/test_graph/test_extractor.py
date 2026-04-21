"""Tests for the variable-graph extractor.

The extractor walks PolicyEngine-style Variable source trees and
builds a dependency graph from formula-body references. Two reference
patterns are recognized in MVP:

1. ``<entity>("<var>", <period>)`` — direct call on an entity instance
   inside a formula method. ``<entity>`` matches a known set:
   ``person``, ``tax_unit``, ``spm_unit``, ``household``, ``family``,
   ``marital_unit``, ``benunit``.
2. ``add(<entity>, <period>, ["v1", "v2"])`` — helper that sums a list
   of variable values. Each string in the list is extracted.

Tests run against a self-contained fixture tree under the test file's
own tmp directory — no dependency on an installed country model — so
behavior is deterministic and the tests pin the extraction algorithm
rather than PolicyEngine's evolving source.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from textwrap import dedent
from types import ModuleType


# ``policyengine/__init__.py`` eagerly imports the full country-model
# stack (policyengine-us, policyengine-uk), which makes a normal
# ``from policyengine.graph import ...`` fail in any environment
# where those jurisdictions aren't fully provisioned (missing release
# manifests, unresolved optional deps, etc.). The graph module is
# self-contained (stdlib + networkx only); load it via importlib
# directly so these tests remain environment-agnostic.
def _load_graph_module() -> ModuleType:
    if "policyengine.graph" in sys.modules and hasattr(
        sys.modules["policyengine.graph"], "extract_from_path"
    ):
        return sys.modules["policyengine.graph"]

    graph_dir = Path(__file__).resolve().parents[2] / "src" / "policyengine" / "graph"

    if "policyengine" not in sys.modules:
        fake_pkg = ModuleType("policyengine")
        fake_pkg.__path__ = [str(graph_dir.parent)]
        sys.modules["policyengine"] = fake_pkg
    if "policyengine.graph" not in sys.modules or not hasattr(
        sys.modules["policyengine.graph"], "__path__"
    ):
        fake_subpkg = ModuleType("policyengine.graph")
        fake_subpkg.__path__ = [str(graph_dir)]
        sys.modules["policyengine.graph"] = fake_subpkg

    for submod, filename in [
        ("policyengine.graph.graph", "graph.py"),
        ("policyengine.graph.extractor", "extractor.py"),
    ]:
        if submod in sys.modules:
            continue
        spec = importlib.util.spec_from_file_location(submod, graph_dir / filename)
        module = importlib.util.module_from_spec(spec)
        sys.modules[submod] = module
        spec.loader.exec_module(module)  # type: ignore[union-attr]

    graph_mod = sys.modules["policyengine.graph"]
    graph_mod.extract_from_path = sys.modules[
        "policyengine.graph.extractor"
    ].extract_from_path
    graph_mod.VariableGraph = sys.modules["policyengine.graph.graph"].VariableGraph
    return graph_mod


_graph = _load_graph_module()
extract_from_path = _graph.extract_from_path
VariableGraph = _graph.VariableGraph


def _write_variable(
    root: Path, var_name: str, formula_body: str, entity: str = "tax_unit"
) -> None:
    """Write a Variable subclass file mimicking policyengine-us style."""
    root.mkdir(parents=True, exist_ok=True)
    (root / f"{var_name}.py").write_text(
        dedent(f'''\
        from policyengine_us.model_api import *


        class {var_name}(Variable):
            value_type = float
            entity = TaxUnit
            label = "{var_name.replace("_", " ").title()}"
            definition_period = YEAR

            def formula({entity}, period, parameters):
                {formula_body}
        ''')
    )


class TestDirectEntityReference:
    """Pattern 1: ``entity("<var>", period)`` produces an edge."""

    def test_single_direct_reference(self, tmp_path: Path) -> None:
        root = tmp_path / "variables"
        _write_variable(
            root,
            "adjusted_gross_income",
            'return tax_unit("gross_income", period) - tax_unit("above_the_line_deductions", period)',
        )
        _write_variable(root, "gross_income", "return 0")
        _write_variable(root, "above_the_line_deductions", "return 0")

        graph = extract_from_path(root)

        assert graph.has_variable("adjusted_gross_income")
        deps = set(graph.deps("adjusted_gross_income"))
        assert deps == {"gross_income", "above_the_line_deductions"}

    def test_nonmatching_string_is_ignored(self, tmp_path: Path) -> None:
        """String literals unrelated to an entity call are ignored.

        Only a string as the first arg of a matching
        ``<entity>("<var>", period)`` call becomes an edge; string
        literals used as argument to ``print`` or bound to a local
        name are not misinterpreted as variable references.
        """
        root = tmp_path / "variables"
        root.mkdir(parents=True, exist_ok=True)
        (root / "refundable_credit.py").write_text(
            dedent("""\
            from policyengine_us.model_api import *


            class refundable_credit(Variable):
                value_type = float
                entity = TaxUnit
                label = "Refundable credit"
                definition_period = YEAR

                def formula(tax_unit, period, parameters):
                    note = "not a variable reference"
                    return tax_unit("gross_income", period)
            """)
        )
        _write_variable(root, "gross_income", "return 0")
        graph = extract_from_path(root)
        assert set(graph.deps("refundable_credit")) == {"gross_income"}


class TestAddHelperReference:
    """Pattern 2: ``add(entity, period, [...])`` emits one edge per list item."""

    def test_add_helper_list(self, tmp_path: Path) -> None:
        root = tmp_path / "variables"
        _write_variable(
            root,
            "total_income",
            'return add(tax_unit, period, ["wages", "self_employment_income", "interest"])',
        )
        _write_variable(root, "wages", "return 0")
        _write_variable(root, "self_employment_income", "return 0")
        _write_variable(root, "interest", "return 0")
        graph = extract_from_path(root)
        assert set(graph.deps("total_income")) == {
            "wages",
            "self_employment_income",
            "interest",
        }


class TestImpactAnalysis:
    """``impact(var)`` returns variables that depend on ``var`` transitively."""

    def test_transitive_upstream(self, tmp_path: Path) -> None:
        root = tmp_path / "variables"
        _write_variable(root, "wages", "return 0")
        _write_variable(
            root,
            "gross_income",
            'return add(tax_unit, period, ["wages"])',
        )
        _write_variable(
            root,
            "adjusted_gross_income",
            'return tax_unit("gross_income", period)',
        )
        _write_variable(
            root,
            "taxable_income",
            'return tax_unit("adjusted_gross_income", period)',
        )
        _write_variable(
            root,
            "federal_income_tax",
            'return tax_unit("taxable_income", period)',
        )
        graph = extract_from_path(root)

        # wages is read by gross_income → adjusted_gross_income →
        # taxable_income → federal_income_tax (depth 4).
        impact = set(graph.impact("wages"))
        assert impact == {
            "gross_income",
            "adjusted_gross_income",
            "taxable_income",
            "federal_income_tax",
        }

    def test_leaf_variable_has_empty_impact(self, tmp_path: Path) -> None:
        """A variable that nothing reads has an empty impact set."""

        root = tmp_path / "variables"
        _write_variable(
            root,
            "federal_income_tax",
            'return tax_unit("adjusted_gross_income", period)',
        )
        _write_variable(root, "adjusted_gross_income", "return 0")
        graph = extract_from_path(root)
        assert list(graph.impact("federal_income_tax")) == []


class TestMultipleFormulas:
    """Year-specific ``formula_YYYY`` methods contribute edges too."""

    def test_year_specific_formula_contributes_edges(self, tmp_path: Path) -> None:
        root = tmp_path / "variables"
        (root / "ctc.py").parent.mkdir(parents=True, exist_ok=True)
        (root / "ctc.py").write_text(
            dedent("""\
            from policyengine_us.model_api import *


            class ctc(Variable):
                value_type = float
                entity = TaxUnit
                label = "Child Tax Credit"
                definition_period = YEAR

                def formula_2020(tax_unit, period, parameters):
                    return tax_unit("ctc_base_2020", period)

                def formula_2023(tax_unit, period, parameters):
                    return tax_unit("ctc_base_2023", period)
            """)
        )
        _write_variable(root, "ctc_base_2020", "return 0")
        _write_variable(root, "ctc_base_2023", "return 0")

        graph = extract_from_path(root)
        assert set(graph.deps("ctc")) == {"ctc_base_2020", "ctc_base_2023"}


class TestPath:
    """``path(src, dst)`` returns a dependency chain if one exists."""

    def test_path_two_hops(self, tmp_path: Path) -> None:
        root = tmp_path / "variables"
        _write_variable(root, "wages", "return 0")
        _write_variable(root, "gross_income", 'return tax_unit("wages", period)')
        _write_variable(
            root,
            "adjusted_gross_income",
            'return tax_unit("gross_income", period)',
        )

        graph = extract_from_path(root)
        assert graph.path("wages", "adjusted_gross_income") == [
            "wages",
            "gross_income",
            "adjusted_gross_income",
        ]

    def test_path_returns_none_if_unreachable(self, tmp_path: Path) -> None:
        root = tmp_path / "variables"
        _write_variable(root, "island_a", "return 0")
        _write_variable(root, "island_b", "return 0")
        graph = extract_from_path(root)
        assert graph.path("island_a", "island_b") is None


class TestRequiresVariableSubclass:
    """Only classes whose base class list contains ``Variable`` are scanned.

    Helper modules (model_api, utils) should not be mistaken for
    Variable definitions even if they have method bodies that call
    entity-style functions.
    """

    def test_non_variable_classes_are_ignored(self, tmp_path: Path) -> None:
        root = tmp_path / "variables"
        root.mkdir(parents=True, exist_ok=True)
        # Looks like a variable body but the class is not a Variable.
        (root / "helper.py").write_text(
            dedent("""\
            class NotAVariable:
                def some_method(tax_unit, period, parameters):
                    return tax_unit("some_variable", period)
            """)
        )
        graph = extract_from_path(root)
        assert not graph.has_variable("NotAVariable")
        # And no edge to "some_variable" should exist from a phantom source.
        assert list(graph.impact("some_variable")) == []
