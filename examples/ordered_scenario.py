"""Demonstrate ordered phases with synthetic state and no household data.

Run from a checkout containing these example functions. Supply that actual
checkout's repository and full commit SHA; the API records the caller's claim.
"""

import argparse
from types import SimpleNamespace

from ordered_scenario_modifiers import add_one, double

from policyengine.provenance import build_ordered_scenario


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--git-sha", required=True)
    args = parser.parse_args()
    revision = {"repository": args.repository, "git_sha": args.git_sha}
    bound = build_ordered_scenario(
        before_modifiers=[(add_one, revision), (double, revision)],
        after_modifiers=[(double, revision), (add_one, revision)],
    )
    before, after = bound.scenario.parts_by_data_load()
    state = SimpleNamespace(value=1)
    before.simulation_modifier(state)
    assert state.value == 4
    # A native simulation constructs its data between these two calls.
    after.simulation_modifier(state)
    assert state.value == 9
    print(bound.identity.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
