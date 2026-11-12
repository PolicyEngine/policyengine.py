"""Entity-table population runs retain native dataset-mode behavior."""

import numpy as np
import pandas as pd
import pytest
from microdf import MicroDataFrame

pytest.importorskip("policyengine_us")
pytest.importorskip("spm_calculator.policyengine_adapter")

import policyengine as pe
from policyengine.core.simulation import Simulation
from policyengine.tax_benefit_models.us.datasets import (
    PolicyEngineUSDataset,
    USYearData,
)
from policyengine.tax_benefit_models.us.model import PolicyEngineUSLatest


@pytest.fixture
def population_tables():
    """Two CA households with unequal native weights and observed counties."""
    tables = {}
    for entity in (
        "person",
        "household",
        "tax_unit",
        "spm_unit",
        "family",
        "marital_unit",
    ):
        frame = pd.DataFrame({f"{entity}_id": [1, 2], f"{entity}_weight": [2.0, 3.0]})
        if entity == "person":
            for group in (
                "household",
                "tax_unit",
                "spm_unit",
                "family",
                "marital_unit",
            ):
                frame[f"{group}_id"] = [1, 2]
            frame["age"] = [35, 45]
            frame["medicaid_enrolled"] = [True, True]
            frame["medicaid_slcsp_cost_index"] = [100.0, 200.0]
        elif entity == "household":
            frame["state_code"] = ["CA", "CA"]
            frame["county_fips"] = ["06037", "06037"]
            frame["county"] = ["ALAMEDA_COUNTY_CA", "ALAMEDA_COUNTY_CA"]
        tables[entity] = MicroDataFrame(frame, weights=f"{entity}_weight")
    return PolicyEngineUSDataset(
        name="synthetic-population-context",
        description="Uncertified two-household population-context fixture",
        year=2026,
        data=USYearData(**tables),
    )


@pytest.mark.parametrize(
    "reform", [None, {"gov.irs.credits.ctc.amount.base[0].amount": 3_000}]
)
def test_population_context_precedes_inputs_in_both_arms(
    population_tables, monkeypatch, reform
):
    from policyengine_us.spm import SPMSimulationMixin

    building = set()
    countries = []
    writes = []
    build = PolicyEngineUSLatest._build_simulation_from_dataset
    set_input = SPMSimulationMixin.set_input

    def capture_build(self, country, dataset, system):
        building.add(id(country))
        try:
            return build(self, country, dataset, system)
        finally:
            building.remove(id(country))
            countries.append(country)

    def capture_input(self, *args, **kwargs):
        if id(self) in building:
            assert self.is_over_dataset, "Population mode must precede the first input"
            writes.append(id(self))
        return set_input(self, *args, **kwargs)

    monkeypatch.setattr(
        PolicyEngineUSLatest, "_build_simulation_from_dataset", capture_build
    )
    monkeypatch.setattr(SPMSimulationMixin, "set_input", capture_input)
    monkeypatch.setattr(
        PolicyEngineUSLatest,
        "resolve_entity_variables",
        lambda self, sim: {"person": ["medicaid_slcsp_state_denominator"]},
    )
    simulation = Simulation(
        dataset=population_tables, tax_benefit_model_version=pe.us.model, policy=reform
    )
    simulation.run()
    assert len(countries) == (2 if reform else 1)
    assert set(writes) == {id(country) for country in countries}

    # The actual population formula uses the native weighted enrollee sum,
    # rather than the calibrated single-household denominator.
    np.testing.assert_array_equal(
        simulation.output_dataset.data.person["medicaid_slcsp_state_denominator"],
        [800.0, 800.0],
    )
    for country in countries:
        assert country.is_over_dataset
        assert country.dataset is None
        assert not country.check_macro_cache("employment_income", "2026")
        np.testing.assert_array_equal(
            country.calculate("medicaid_slcsp_state_denominator", 2026).values,
            [800.0, 800.0],
        )
        # Dataset counties carry forward from stored periods instead of
        # being recomputed from the deliberately different FIPS input.
        assert country.calculate("county", 2027).tolist() == [
            "ALAMEDA_COUNTY_CA",
            "ALAMEDA_COUNTY_CA",
        ]
        # The real SPM mixin must protect its formulas in both arms.
        with pytest.raises(ValueError, match="formula-owned SPM output"):
            country.set_input("spm_unit_spm_threshold", 2026, [1.0, 1.0])
