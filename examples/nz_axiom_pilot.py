"""Run the source-only NZ entitlement pilot over a supplied Microcosm artifact.

Requires compatible Microcosm/Axiom source installs and a committed rulespec-nz
checkout. This example does not download or certify a population, convert
entitlements to Treasury fiscal costs, or publish a Scorecard result.

    POLICYENGINE_SKIP_COUNTRY_IMPORTS=1 uv run --no-sync python \
        examples/nz_axiom_pilot.py --dataset /path/to/populace_nz_2026.h5 \
        --rulespec-root /path/to/rulespec-nz --sha256 VERIFIED_ARTIFACT_SHA256

Use --weight-kind calibrated only for an artifact with calibrated weights.
"""

import argparse
import json

from policyengine.core import Simulation
from policyengine.tax_benefit_models.nz import (
    IWTC_CHANGE,
    WFF_ABATEMENT_CHANGE,
    AxiomNewZealandPilot,
    PopulaceNewZealandDataset,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--rulespec-root", required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument(
        "--weight-kind", choices=("design", "calibrated"), default="design"
    )
    args = parser.parse_args()
    dataset = PopulaceNewZealandDataset(
        name="NZ source-only transport pilot",
        description="User-supplied NZ family inputs; this adapter does not certify the population",
        filepath=args.dataset,
        source_sha256=args.sha256,
        weight_kind=args.weight_kind,
        year=2026,
    )
    simulation = Simulation(
        dataset=dataset,
        tax_benefit_model_version=AxiomNewZealandPilot(
            rulespec_root=args.rulespec_root
        ),
    )
    simulation.run()
    output = simulation.output_dataset
    # The adapter resolves effective family weights through Frame; MicroSeries
    # applies them here. Do not multiply by person/family weight columns.
    changes = {
        name: float(output.data.family[name].sum())
        for name in (WFF_ABATEMENT_CHANGE, IWTC_CHANGE)
    }
    print(
        json.dumps(
            {
                "country": "nz",
                "status": "source_only_entitlement_pilot",
                "official_budget_score_comparable": False,
                "weighted_family_entitlement_changes_nzd": changes,
                "receipt": output.metadata["policyengine_axiom_runs"][-1],
            },
            indent=2,
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
