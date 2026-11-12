"""Generate data-only verifier vectors from the actual ordered-plan producer.

The modifiers and revision below are synthetic test fixtures. These vectors
assert canonicalization behavior, not approval or certification of a job.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("POLICYENGINE_SKIP_COUNTRY_IMPORTS", "1")
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from policyengine.provenance.ordered_scenario import (  # noqa: E402
    build_ordered_scenario,
)
from tests import ordered_receipt_modifiers as modifiers  # noqa: E402

PATH = ROOT / "src/policyengine/data/schemas/ordered_scenario_plan.v1.vectors.json"
REVISION = {"repository": "PolicyEngine/test", "git_sha": "a" * 40}


def build_vectors():
    def leaves(*functions):
        return [(function, dict(REVISION)) for function in functions]

    cases = [
        ("empty", build_ordered_scenario()),
        ("parameter_only", build_ordered_scenario({"gov.example.rate": {"2027": 0.2}})),
        (
            "parameter_infinity",
            build_ordered_scenario({"gov.example.cap": {"2027": float("inf")}}),
        ),
        (
            "two_each_phase",
            build_ordered_scenario(
                {"gov.example.rate": {"2027": 0.2}},
                before_modifiers=leaves(modifiers.add_one, modifiers.double),
                after_modifiers=leaves(modifiers.double, modifiers.add_one),
            ),
        ),
        (
            "reverse_before",
            build_ordered_scenario(
                before_modifiers=leaves(modifiers.double, modifiers.add_one)
            ),
        ),
        (
            "repeated_leaf",
            build_ordered_scenario(
                after_modifiers=leaves(modifiers.add_one, modifiers.add_one)
            ),
        ),
        (
            "typed_defaults",
            build_ordered_scenario(before_modifiers=leaves(modifiers.add_default)),
        ),
    ]
    valid = [
        {
            "id": name,
            "plan": bound.plan.model_dump(mode="json"),
            "identity": bound.identity.model_dump(mode="json"),
        }
        for name, bound in cases
    ]
    base = valid[3]["plan"]
    invalid = []
    for name in (
        "unknown_field",
        "unknown_application",
        "after_parameters",
        "unknown_leaf_field",
        "unknown_default_type",
    ):
        plan = copy.deepcopy(base)
        if name == "unknown_field":
            plan["invented"] = True
        elif name == "unknown_application":
            plan["application"] = "after_then_before"
        elif name == "after_parameters":
            plan["after"]["parameter_changes"] = {"gov.example.rate": 1}
        elif name == "unknown_leaf_field":
            plan["before"]["modifier_leaves"][0]["claimed_leaf_count"] = 1
        else:
            plan["before"]["modifier_leaves"][0]["module_defaults"] = {
                "x": {"type": "object"}
            }
        invalid.append({"id": name, "plan": plan})
    return {
        "schema_version": 1,
        "purpose": "Synthetic canonicalization vectors; no job approval or certification.",
        "valid": valid,
        "invalid": invalid,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    content = json.dumps(build_vectors(), indent=2, sort_keys=True) + "\n"
    if args.check:
        if not PATH.exists() or PATH.read_text() != content:
            raise SystemExit("Ordered Scenario vectors are stale.")
    else:
        PATH.write_text(content)


if __name__ == "__main__":
    main()
