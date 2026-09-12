"""Real country calculations keep independent native entity orders aligned."""

import hashlib
import importlib

import numpy as np
import pandas as pd
import pytest

# The canonical calculator API is not published yet. Skip rather than weaken
# these cases: they must run against the real module, never a substitute.
pytest.importorskip("spm_calculator.release")
pytest.importorskip("spm_calculator.rolling_forecast")
pytest.importorskip("spm_calculator.policyengine_adapter")

from spm_calculator.release import SPMUnit  # noqa: E402
from spm_calculator.rolling_forecast import load_forecast  # noqa: E402

import policyengine as pe
from policyengine.tax_benefit_models.us.datasets import PolicyEngineUSDataset
from policyengine.tax_benefit_models.us.model import PolicyEngineUSLatest
from policyengine.tax_benefit_models.us.spm import resolve_spm_selection


@pytest.fixture
def independent_entity_frames():
    # Person order, group IDs, table orders, and indexes differ independently.
    # The California unit also has a child, so aggregate outputs exercise real
    # membership joins instead of only one-to-one relabeling.
    person = pd.DataFrame(
        {
            "person_id": [300, 101, 200, 100],
            "person_household_id": [30, 10, 20, 10],
            "person_tax_unit_id": [3, 1, 2, 1],
            "person_spm_unit_id": [330, 110, 220, 110],
            "person_family_id": [3000, 1000, 2000, 1000],
            "person_marital_unit_id": [33, 44, 22, 11],
            "age": [50, 8, 40, 30],
            "employment_income": [31_000.0, 1_000.0, 23_000.0, 13_000.0],
        },
        index=[91, -4, 300, 17],
    )
    return {
        "person": person,
        "household": pd.DataFrame(
            {
                "household_id": [20, 10, 30],
                "household_weight": [2.5, 7.0, 4.0],
                "county_fips": ["36061", "06037", "48201"],
                "state_fips": [36, 6, 48],
            },
            index=[77, 42, -9],
        ),
        "tax_unit": pd.DataFrame({"tax_unit_id": [3, 2, 1]}, index=[8, 12, -7]),
        "spm_unit": pd.DataFrame(
            {
                "spm_unit_id": [220, 330, 110],
                "spm_unit_tenure_type": [
                    "OWNER_WITHOUT_MORTGAGE",
                    "OWNER_WITH_MORTGAGE",
                    "RENTER",
                ],
            },
            index=[13, -8, 50],
        ),
        "family": pd.DataFrame({"family_id": [1000, 3000, 2000]}, index=[9, -2, 17]),
        "marital_unit": pd.DataFrame(
            {"marital_unit_id": [22, 11, 44, 33]}, index=[87, -1, 11, 44]
        ),
    }


@pytest.mark.parametrize("format", ["fixed", "table"])
@pytest.mark.parametrize("link_style", ["native", "plain"])
def test_native_inputs_and_calculated_outputs_align_by_id(
    tmp_path, independent_entity_frames, format, link_style, monkeypatch
):
    frames = independent_entity_frames
    if link_style == "plain":
        frames["person"] = frames["person"].rename(
            columns={
                f"person_{entity}_id": f"{entity}_id"
                for entity in frames
                if entity != "person"
            }
        )
    else:
        # Conflicting plain aliases must not override native memberships at
        # either input construction or output assembly.
        for entity, frame in frames.items():
            if entity != "person":
                frames["person"][f"{entity}_id"] = frame[f"{entity}_id"].iloc[0]
    path = tmp_path / f"shuffled-{format}.h5"
    with pd.HDFStore(path, mode="w") as store:
        for entity, frame in frames.items():
            store.put(entity, frame, format=format)
    source_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    dataset = PolicyEngineUSDataset(
        name="independently shuffled native tables",
        description="Uncertified four-person numeric alignment fixture",
        filepath=str(path),
        year=2026,
    )
    inputs = {
        entity: pd.DataFrame(frame).copy(deep=True)
        for entity, frame in dataset.data.entity_data.items()
    }

    # Keep the real high-level input builder, country calculations, result
    # assembly and SPM receipt. Limit requested variables to this regression.
    outputs = {entity: ["employment_income"] for entity in frames}
    outputs["person"] += ["county_fips", "state_fips"]
    outputs["household"] += ["county_fips", "state_fips"]
    outputs["spm_unit"] += ["spm_unit_spm_threshold"]
    monkeypatch.setattr(
        PolicyEngineUSLatest, "resolve_entity_variables", lambda self, sim: outputs
    )
    country_simulations = []
    build = PolicyEngineUSLatest._build_simulation_from_dataset

    def capture(self, country_simulation, dataset, system):
        build(self, country_simulation, dataset, system)
        country_simulations.append(country_simulation)

    monkeypatch.setattr(PolicyEngineUSLatest, "_build_simulation_from_dataset", capture)
    simulation = pe.Simulation(dataset=dataset, tax_benefit_model_version=pe.us.model)
    simulation.run()
    output = simulation.output_dataset.data.entity_data
    country = country_simulations[0]

    # Assert numeric geography at both boundaries, including the two CA people.
    assert output["person"]["county_fips"].tolist() == [
        "48201",
        "06037",
        "36061",
        "06037",
    ]
    assert output["person"]["state_fips"].tolist() == [48, 6, 36, 6]
    assert output["household"]["county_fips"].tolist() == ["36061", "06037", "48201"]
    assert output["household"]["state_fips"].tolist() == [36, 6, 48]
    np.testing.assert_array_equal(
        country.calculate("state_fips", 2026, map_to="person").values,
        [48, 6, 36, 6],
    )

    incomes = frames["person"]
    for entity, frame in inputs.items():
        entity_id = f"{entity}_id"
        assert output[entity][entity_id].tolist() == frame[entity_id].tolist()
        assert output[entity].weights.tolist() == frame[f"{entity}_weight"].tolist()
        if entity == "person":
            expected = incomes.set_index("person_id")["employment_income"]
        else:
            link = f"person_{entity_id}" if link_style == "native" else entity_id
            expected = incomes.groupby(link)["employment_income"].sum()
            assert output["person"][entity_id].tolist() == incomes[link].tolist()
        np.testing.assert_array_equal(
            output[entity]["employment_income"].to_numpy(),
            expected.loc[frame[entity_id]].to_numpy(),
        )
        # Each entity receives its native weight in the country's own ID order.
        expected_weights = frame.set_index(entity_id)[f"{entity}_weight"]
        np.testing.assert_array_equal(
            country.calculate(f"{entity}_weight", 2026).values,
            expected_weights.loc[country.populations[entity].ids].to_numpy(),
        )
        pd.testing.assert_frame_equal(
            pd.DataFrame(dataset.data.entity_data[entity]), frame
        )
    assert output["spm_unit"]["employment_income"].sum() == 279_500.0

    # Thresholds are compared with the real standalone calculator for each
    # county/composition/tenure; merely retaining the IDs cannot pass this test.
    forecast = load_forecast()
    scenario = resolve_spm_selection()["scenario"]
    expected_thresholds = []
    for spm_id, county, children, tenure in (
        (220, "36061", 0, "owner_without_mortgage"),
        (330, "48201", 0, "owner_with_mortgage"),
        (110, "06037", 1, "renter"),
    ):
        assignment = forecast.resolve_county(
            2026, county, county_vintage="2020", scenario=scenario
        )
        result = forecast.calculate_unit(
            SPMUnit(
                unit_id=str(spm_id),
                year=2026,
                num_adults=1,
                num_children=children,
                tenure=tenure,
                geography_kind="metro",
                geography_id=assignment["area_id"],
            ),
            scenario=scenario,
        )
        expected_thresholds.append(np.float32(result["threshold"]))
    np.testing.assert_array_equal(
        output["spm_unit"]["spm_unit_spm_threshold"].to_numpy(), expected_thresholds
    )
    assert simulation.spm_provenance()["geography_kind"] == "county"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == source_sha256


@pytest.mark.parametrize(
    "selection",
    [
        {"path": "/tmp/invalid.json"},
        {"geography_kind": "unsupported"},
        {"forecast_content_sha256": "0" * 64},
    ],
)
def test_invalid_managed_spm_rejected_before_dataset_materialization(
    monkeypatch, selection
):
    module = importlib.import_module("policyengine.tax_benefit_models.us.model")
    calls = []

    def sentinel(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("Invalid SPM must not materialize data")

    monkeypatch.setattr(module, "materialize_dataset", sentinel)
    with pytest.raises(ValueError):
        pe.us.managed_microsimulation(spm=selection)
    assert calls == []
