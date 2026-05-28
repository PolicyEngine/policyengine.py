from types import SimpleNamespace

import pandas as pd
import pytest
from microdf import MicroDataFrame

import policyengine.outputs as outputs
from policyengine.core import Simulation
from policyengine.outputs import (
    CliffImpact,
    CliffImpactInSimulation,
    calculate_cliff_impact,
    configure_cliff_impact_variables,
)


class _FakeModelVersion:
    model = SimpleNamespace(id="fake-model")
    version = "test"
    variables_by_name = {
        "cliff_gap": object(),
        "is_on_cliff": object(),
        "is_adult": object(),
    }

    def get_variable(self, variable_name: str):
        if variable_name not in self.variables_by_name:
            raise ValueError(variable_name)
        return SimpleNamespace(entity="person")


def _simulation(
    simulation_id: str,
    data: dict[str, list[float]],
    *,
    extra_variables: dict[str, list[str]] | None = None,
) -> Simulation:
    person = MicroDataFrame(
        pd.DataFrame(
            {
                "person_id": list(range(1, len(data["person_weight"]) + 1)),
                **data,
            }
        ),
        weights="person_weight",
    )
    return Simulation.model_construct(
        id=simulation_id,
        extra_variables=extra_variables or {},
        tax_benefit_model_version=_FakeModelVersion(),
        output_dataset=SimpleNamespace(data=SimpleNamespace(person=person)),
    )


def test_cliff_impact_models_serialize_to_legacy_shape():
    result = CliffImpact(
        baseline=CliffImpactInSimulation(cliff_gap=1.0, cliff_share=0.25),
        reform=CliffImpactInSimulation(cliff_gap=2.0, cliff_share=0.5),
    )

    assert result.model_dump(mode="json") == {
        "baseline": {"cliff_gap": 1.0, "cliff_share": 0.25},
        "reform": {"cliff_gap": 2.0, "cliff_share": 0.5},
    }


def test_cliff_impact_symbols_are_publicly_exported():
    assert outputs.CliffImpact is CliffImpact
    assert outputs.CliffImpactInSimulation is CliffImpactInSimulation
    assert outputs.calculate_cliff_impact is calculate_cliff_impact
    assert outputs.configure_cliff_impact_variables is configure_cliff_impact_variables


def test_configure_cliff_impact_variables_preserves_existing_extras():
    baseline = _simulation(
        "baseline",
        {
            "person_weight": [1.0],
            "cliff_gap": [0.0],
            "is_on_cliff": [0.0],
            "is_adult": [1.0],
        },
        extra_variables={"person": ["existing_person_variable"]},
    )
    reform = _simulation(
        "reform",
        {
            "person_weight": [1.0],
            "cliff_gap": [0.0],
            "is_on_cliff": [0.0],
            "is_adult": [1.0],
        },
        extra_variables={"person": ["cliff_gap"]},
    )

    configure_cliff_impact_variables(baseline, reform)
    configure_cliff_impact_variables(baseline, reform)

    assert baseline.extra_variables["person"] == [
        "existing_person_variable",
        "cliff_gap",
        "is_on_cliff",
        "is_adult",
    ]
    assert reform.extra_variables["person"] == [
        "cliff_gap",
        "is_on_cliff",
        "is_adult",
    ]


def test_calculate_cliff_impact_matches_legacy_shape():
    baseline = _simulation(
        "baseline",
        {
            "person_weight": [1.0, 2.0],
            "cliff_gap": [10.0, 20.0],
            "is_on_cliff": [1.0, 0.0],
            "is_adult": [1.0, 1.0],
        },
    )
    reform = _simulation(
        "reform",
        {
            "person_weight": [1.0, 2.0],
            "cliff_gap": [2.0, 3.0],
            "is_on_cliff": [0.0, 1.0],
            "is_adult": [1.0, 1.0],
        },
    )

    result = calculate_cliff_impact(baseline, reform)

    assert result.baseline.cliff_gap == 50.0
    assert result.baseline.cliff_share == pytest.approx(1 / 3)
    assert result.reform.cliff_gap == 8.0
    assert result.reform.cliff_share == pytest.approx(2 / 3)


def test_calculate_cliff_impact_requires_materialized_columns():
    baseline = _simulation(
        "baseline",
        {
            "person_weight": [1.0],
            "cliff_gap": [10.0],
            "is_adult": [1.0],
        },
    )
    reform = _simulation(
        "reform",
        {
            "person_weight": [1.0],
            "cliff_gap": [10.0],
            "is_on_cliff": [1.0],
            "is_adult": [1.0],
        },
    )

    with pytest.raises(ValueError, match="is_on_cliff"):
        calculate_cliff_impact(baseline, reform)
