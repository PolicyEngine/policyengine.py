"""Small real-country checks for the high-level canonical SPM contract."""

import json

import pandas as pd
import pytest
from microdf import MicroDataFrame

pytest.importorskip("spm_calculator.policyengine_adapter")
pytest.importorskip("policyengine_us")

import policyengine as pe
from policyengine.core.simulation import Simulation, _cache
from policyengine.core.spm import SPMSelection
from policyengine.tax_benefit_models.us.datasets import (
    PolicyEngineUSDataset,
    USYearData,
)


@pytest.fixture
def tiny_spm_dataset(tmp_path):
    """One adult, one child, observed CA county and native group membership."""
    tables = {}
    for entity in (
        "person",
        "household",
        "spm_unit",
        "tax_unit",
        "family",
        "marital_unit",
    ):
        count = 2 if entity in {"person", "marital_unit"} else 1
        frame = pd.DataFrame(
            {f"{entity}_id": range(1, count + 1), f"{entity}_weight": [1.0] * count}
        )
        if entity == "person":
            frame["age"] = [35, 8]
            frame["employment_income"] = [35_000, 0]
            for group in ("household", "spm_unit", "tax_unit", "family"):
                frame[f"{group}_id"] = [1, 1]
            frame["marital_unit_id"] = [1, 2]
        elif entity == "household":
            frame["state_code"] = ["CA"]
            frame["county_fips"] = ["06037"]
        tables[entity] = MicroDataFrame(frame, weights=f"{entity}_weight")
    return PolicyEngineUSDataset(
        name="synthetic-spm",
        description="Uncertified two-person unit fixture",
        filepath=str(tmp_path / "input.h5"),
        year=2026,
        data=USYearData(**tables),
    )


def test_high_level_selection_is_typed_and_rejects_provider_paths():
    sim = Simulation(spm={"geography_kind": "national"})
    assert isinstance(sim.spm, SPMSelection)
    assert (
        json.loads(sim.model_dump_json(include={"spm"}))["spm"]["geography_kind"]
        == "national"
    )
    with pytest.raises(ValueError):
        Simulation(spm={"path": "/tmp/forecast.json"})


@pytest.mark.parametrize(
    "reform", [None, {"gov.irs.credits.ctc.amount.base[0].amount": 3_000}]
)
@pytest.mark.parametrize(
    "column",
    ["spm_measurement_adults", "spm_unit_spm_threshold", "spm_unit_net_income"],
)
def test_computed_dataframe_inputs_rejected_before_any_set_input(
    tiny_spm_dataset, monkeypatch, reform, column
):
    from policyengine_us.spm import SPMSimulationMixin

    tiny_spm_dataset.data.spm_unit[column] = [1]
    calls = []
    monkeypatch.setattr(
        SPMSimulationMixin, "set_input", lambda *args: calls.append(args)
    )
    sim = Simulation(
        dataset=tiny_spm_dataset, tax_benefit_model_version=pe.us.model, policy=reform
    )
    with pytest.raises(ValueError, match="computed outputs supplied as inputs"):
        sim.run()
    assert calls == []


def test_real_high_level_provenance_cache_and_disk_round_trip(
    tiny_spm_dataset, monkeypatch
):
    _cache.clear()
    county = Simulation(
        id="spm-replay", dataset=tiny_spm_dataset, tax_benefit_model_version=pe.us.model
    )
    county.ensure()
    county_receipt = county.spm_provenance()
    assert county_receipt["years"]["2026"]
    assert county_receipt["geography_kind"] == "county"
    assert county.spm_config["geography_kind"] == "county"
    assert (
        county.spm.forecast_content_sha256
        == county.spm_config["forecast_content_sha256"]
    )
    assert county.spm.scenario == "ce_trend"
    assert county.release_bundle["spm"] == county.spm_provenance()
    from policyengine import bundle

    original_bundle = bundle.get_current_bundle()
    original_bundle["measurements"]["spm"]["scenario"] = "zero_real"
    with monkeypatch.context() as context:
        context.setattr(bundle, "get_current_bundle", lambda: original_bundle)
        assert county.spm_config["scenario"] == "ce_trend"
    county_receipt["years"].clear()
    assert county.spm_provenance()["years"]
    assert json.loads(county.model_dump_json(include={"spm", "spm_receipt"}))[
        "spm_receipt"
    ]["years"]

    cached = Simulation(
        id=county.id, dataset=tiny_spm_dataset, tax_benefit_model_version=pe.us.model
    )
    cached.ensure()
    assert cached.spm_provenance() == county.spm_provenance()
    _cache.clear()
    restored = Simulation(
        id=county.id, dataset=tiny_spm_dataset, tax_benefit_model_version=pe.us.model
    )
    restored.load()
    assert restored.spm_provenance() == county.spm_provenance()

    county.spm = SPMSelection(geography_kind="national", scenario="zero_real")
    with pytest.raises(ValueError, match="SPM settings changed"):
        county.save()
    county.ensure()
    assert county.spm_provenance()["geography_kind"] == "national"
    assert county.spm_provenance()["scenario"] == "zero_real"
    assert county.output_dataset.filepath != restored.output_dataset.filepath
    assert restored.spm_provenance()["geography_kind"] == "county"


def test_generic_composition_inputs_remain_allowed(tiny_spm_dataset):
    tiny_spm_dataset.data.person["is_adult"] = [True, False]
    tiny_spm_dataset.data.spm_unit["spm_unit_count_adults"] = [1]
    tiny_spm_dataset.data.spm_unit["spm_unit_count_children"] = [1]
    sim = Simulation(dataset=tiny_spm_dataset, tax_benefit_model_version=pe.us.model)
    sim.run()
    assert sim.output_dataset.data.person["is_adult"].tolist() == [True, False]
    assert sim.spm_provenance()["years"]["2026"]


def test_state_only_high_level_default_requires_geography(tiny_spm_dataset):
    from spm_calculator.errors import SPMInputError

    tiny_spm_dataset.data.household.drop(columns=["county_fips"], inplace=True)
    sim = Simulation(dataset=tiny_spm_dataset, tax_benefit_model_version=pe.us.model)
    with pytest.raises(SPMInputError) as error:
        sim.run()
    assert error.value.code == "SPM_GEOGRAPHY_REQUIRED"
    sim.spm = SPMSelection(geography_kind="national")
    sim.run()
    assert sim.spm_provenance()["geography_kind"] == "national"


def test_run_record_binds_spm_settings_and_receipt(tiny_spm_dataset):
    from policyengine.core.run_record import build_simulation_run_record_payloads

    tiny_spm_dataset.save()
    sim = Simulation(
        dataset=tiny_spm_dataset,
        tax_benefit_model_version=pe.us.model,
        spm={"geography_kind": "national"},
    )
    sim.run()
    sim.save()
    payloads = build_simulation_run_record_payloads(sim)
    assert payloads["input"]["spm"] == sim.spm_config
    assert payloads["results"]["spm"] == sim.spm_provenance()
    sim.spm = SPMSelection(geography_kind="national", scenario="zero_real")
    with pytest.raises(ValueError, match="SPM settings changed"):
        build_simulation_run_record_payloads(sim)


def test_real_high_level_reform_and_baseline_share_selection(
    tiny_spm_dataset, monkeypatch
):
    from policyengine.tax_benefit_models.us.model import PolicyEngineUSLatest

    tiny_spm_dataset.data.household.drop(columns=["county_fips"], inplace=True)
    configurations = []
    original = PolicyEngineUSLatest._build_simulation_from_dataset

    def capture(self, country_simulation, dataset, system):
        configurations.append(country_simulation.spm_config)
        return original(self, country_simulation, dataset, system)

    monkeypatch.setattr(PolicyEngineUSLatest, "_build_simulation_from_dataset", capture)
    sim = Simulation(
        dataset=tiny_spm_dataset,
        tax_benefit_model_version=pe.us.model,
        spm={"geography_kind": "national", "scenario": "zero_real"},
        policy={"gov.irs.credits.ctc.amount.base[0].amount": 3_000},
    )
    sim.run()
    assert len(configurations) == 2
    assert configurations == [sim.spm_config, sim.spm_config]
    assert sim.spm_provenance()["scenario"] == "zero_real"


def test_managed_native_h5_selection_and_clone_provenance(tiny_spm_dataset, tmp_path):
    """The actual managed loader can consume a tiny native H5 in development."""
    import h5py
    import numpy as np

    path = tmp_path / "synthetic-native.h5"
    with h5py.File(path, "w") as stream:
        for entity, frame in tiny_spm_dataset.data.entity_data.items():
            for name in frame.columns:
                output_name = name
                if entity == "person" and name.endswith("_id") and name != "person_id":
                    output_name = f"person_{name}"
                values = frame[name].to_numpy()
                if values.dtype.kind in {"O", "U"}:
                    values = np.asarray(values, dtype="S")
                stream.create_dataset(f"{output_name}/2026", data=values)
    managed = pe.us.managed_microsimulation(
        dataset=str(path),
        allow_unmanaged=True,
        spm={"geography_kind": "national", "scenario": "zero_real"},
    )
    assert managed.policyengine_bundle["spm"] == managed.spm_config
    managed.calculate("spm_unit_spm_threshold", 2026)
    clone = managed.clone()
    assert clone.spm_config == managed.spm_config
    assert clone.spm_provenance() == managed.spm_provenance()
    clone.calculate("spm_unit_spm_threshold", 2025)
    assert "2025" in clone.spm_provenance()["years"]
    assert "2025" not in managed.spm_provenance()["years"]
    returned = managed.spm_provenance()
    returned["years"].clear()
    assert managed.spm_provenance()["years"]
    json.dumps(managed.spm_provenance())
