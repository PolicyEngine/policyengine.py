"""PolicyEngine boundary tests for the source-only New Zealand Axiom pilot.

The ordinary tests stub only the unpublished runtime boundary. The opt-in
integration test executes the real Axiom module; no stub validates NZ law.
"""

import json
import os
from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from policyengine.core import Simulation
from policyengine.tax_benefit_models.nz import (
    IWTC_CHANGE,
    WFF_ABATEMENT_CHANGE,
    AxiomNewZealandPilot,
    PopulaceNewZealandDataset,
)
from policyengine.tax_benefit_models.nz import datasets as nz_datasets
from policyengine.tax_benefit_models.nz import model as nz_model

REQUIRED_INPUTS = {
    "family_tax_credit_eldest_dependent_child_care_units": "decimal128(18,2)",
    "family_tax_credit_subsequent_dependent_child_care_units": "decimal128(18,2)",
    "family_tax_credit_entitlement_days": "int16",
    "wff_family_scheme_income_for_relationship_period": "decimal128(18,2)",
    "wff_family_credit_abatement_days": "int16",
    "entitled_to_in_work_tax_credit": "bool",
    "in_work_tax_credit_allowed_children_count": "int16",
    "in_work_tax_credit_weekly_periods": "int16",
    "child_tax_credit_for_entitlement_period": "decimal128(18,2)",
    "parental_tax_credit_for_entitlement_period": "decimal128(18,2)",
    "parental_tax_credit_additional_abatement": "decimal128(18,2)",
}
PADDING_INPUTS = [
    "best_start_abatement_days",
    "best_start_child_care_fraction",
    "best_start_entitlement_days",
    "best_start_family_scheme_income_for_relationship_period",
    "minimum_family_adjusted_income_tax_liability",
    "minimum_family_amount_paid",
    "minimum_family_amount_received",
    "minimum_family_full_time_earner_weeks",
    "minimum_family_scheme_income_attributable_to_full_time_weeks",
    "minimum_family_tax_credit_weekly_periods",
]
PERIOD = {"start": "2026-04-01", "end": "2027-03-31", "kind": "tax_year"}
SOURCE_METADATA = {"data_build_id": "nz-test-build", "donor_country": "US"}
TEST_PROVENANCE = {"rulespec": {"commit": "a" * 40}, "runtime": {"hash": "b" * 64}}


class FakeWeightKind:
    CALIBRATED = "calibrated"
    DESIGN = "design"


class FakeWeights:
    def __init__(self, *, values, kind):
        self.values = np.asarray(values, dtype=float)
        self.kind = kind


class FakeFrame:
    """Strictly an integration seam double, not a rules evaluator."""

    resolved_entities = []

    def __init__(self, tables, schema, weights, strata=None, *, metadata=None):
        self.tables = {name: table.copy() for name, table in tables.items()}
        self.schema = schema
        self.weights = weights
        self.metadata = metadata or {}
        self.strata = strata
        self.entities = ("person", "household", "family")
        self.weighted_entities = ("household",)

    def table(self, entity):
        return self.tables[entity]

    def n(self, entity):
        return len(self.tables[entity])

    def weights_for(self, entity):
        return self.weights[entity]

    def resolve_weights(self, entity):
        type(self).resolved_entities.append(entity)
        if entity == "household":
            return self.weights[entity]
        households = self.tables["household"]["household_id"]
        lookup = dict(zip(households, self.weights["household"].values))
        membership = (
            self.tables["person"]["person_household_id"]
            if entity == "person"
            else self.tables["family"]["family_household_id"]
        )
        return FakeWeights(
            values=membership.map(lookup), kind=FakeWeightKind.CALIBRATED
        )


@dataclass
class FakeAxiomPeriod:
    start: str
    end: str
    kind: str


class FakeAxiomEngine:
    latest = None

    def __init__(self, module, *, schema, rulespec_roots):
        self.module = Path(module)
        self.schema = schema
        self.rulespec_roots = tuple(rulespec_roots)
        self.frame = None
        self.period = None
        type(self).latest = self

    def materialize(self, frame, variables, period):
        self.frame = frame
        self.period = period
        assert variables == [WFF_ABATEMENT_CHANGE, IWTC_CHANGE]
        # Deliberately non-statutory values: this tests weighted plumbing only.
        return {
            WFF_ABATEMENT_CHANGE: np.array([10.0, 20.0]),
            IWTC_CHANGE: np.array([30.0, 40.0]),
        }


class FakeEntityTableDataset:
    """Reader seam double; real-codec coverage lives in the opt-in test."""

    def __init__(self, *, file_path):
        with pd.HDFStore(file_path, mode="r") as store:
            self.tables = {entity: store[entity] for entity in nz_datasets.ENTITIES}
            self.time_period = int(store["_time_period"].iloc[0])


@pytest.fixture
def stub_runtime(monkeypatch):
    FakeFrame.resolved_entities = []
    FakeAxiomEngine.latest = None
    monkeypatch.setattr(
        nz_datasets,
        "_load_frame_runtime",
        lambda: (FakeFrame, FakeWeightKind, FakeWeights, "nz-schema"),
    )
    monkeypatch.setattr(
        nz_model,
        "_load_axiom_runtime",
        lambda: (FakeAxiomEngine, FakeAxiomPeriod),
    )
    monkeypatch.setattr(
        nz_model,
        "_build_runtime_provenance",
        lambda _root: deepcopy(TEST_PROVENANCE),
    )
    monkeypatch.setattr(
        nz_datasets, "_load_dataset_reader", lambda: FakeEntityTableDataset
    )


@pytest.fixture
def rulespec_root(tmp_path):
    root = tmp_path / "rulespec-nz"
    module = root / nz_model.PILOT_MODULE
    module.parent.mkdir(parents=True)
    module.write_text("# runtime boundary fixture; not executable RuleSpec\n")
    contract = {
        "schema": "axiom/nz-official-budget-reform-transport/1",
        "jurisdiction": "nz",
        "period": {
            "period_kind": "tax_year",
            **{k: PERIOD[k] for k in ("start", "end")},
        },
        "runtime": {"rulespec_module": nz_model.PILOT_MODULE, "root_entity": "Family"},
        "input_contract": {
            "engine_root_input_count": 21,
            "required_target_inputs": [
                {
                    "name": name,
                    "entity": "family",
                    "dtype": dtype,
                    "missing": "fail_closed",
                }
                for name, dtype in REQUIRED_INPUTS.items()
            ],
            "adapter_padding_defaults": [
                {"name": name, "value": 0} for name in PADDING_INPUTS
            ],
        },
        "output_contract": {
            "requested": [
                {"name": name, "entity": "family", "unit": "NZD"}
                for name in (WFF_ABATEMENT_CHANGE, IWTC_CHANGE)
            ],
            "formula_owned_excluded_from_dataset": [WFF_ABATEMENT_CHANGE, IWTC_CHANGE],
        },
        "official_score_bridge": {
            "model_measure": "annual family entitlement change",
            "official_measure": "forecast operating cost change",
            "like_for_like_status": "bridge_required",
        },
    }
    contract_path = root / nz_model.TRANSPORT_CONTRACT
    contract_path.parent.mkdir(parents=True)
    contract_path.write_text(json.dumps(contract))
    return root


def _tables():
    person = pd.DataFrame(
        {
            "person_id": [1, 2, 3, 4, 5],
            "person_household_id": [10, 10, 10, 20, 20],
            "person_family_id": [100, 100, 100, 200, 200],
        }
    )
    household = pd.DataFrame({"household_id": [10, 20], "household_weight": [2.0, 5.0]})
    family = pd.DataFrame(
        {
            "family_id": [100, 200],
            "family_household_id": [10, 20],
            "family_tax_credit_eldest_dependent_child_care_units": [1.0, 1.0],
            "family_tax_credit_subsequent_dependent_child_care_units": [1.0, 0.0],
            "family_tax_credit_entitlement_days": [365, 365],
            "wff_family_scheme_income_for_relationship_period": [50000.0, 100000.0],
            "wff_family_credit_abatement_days": [365, 365],
            "entitled_to_in_work_tax_credit": [False, True],
            "in_work_tax_credit_allowed_children_count": [0, 1],
            "in_work_tax_credit_weekly_periods": [0, 52],
            "child_tax_credit_for_entitlement_period": [0.0, 0.0],
            "parental_tax_credit_for_entitlement_period": [0.0, 0.0],
            "parental_tax_credit_additional_abatement": [0.0, 0.0],
        }
    )
    return {"person": person, "household": household, "family": family}


def _write_dataset(path, tables, *, year=2026):
    with pd.HDFStore(path, mode="w") as store:
        for entity, table in tables.items():
            store[entity] = table
        store.put("_time_period", pd.Series([year]), format="table")
        store.get_storer("_time_period").attrs.policyengine_metadata_json = json.dumps(
            SOURCE_METADATA
        )
    return PopulaceNewZealandDataset(
        name="nz-nonuniform-fixture",
        description="Synthetic boundary fixture, not calibrated NZ data",
        filepath=str(path),
        year=year,
    )


@pytest.fixture
def dataset(tmp_path):
    return _write_dataset(tmp_path / "nz.h5", _tables())


def _run(dataset, rulespec_root):
    model = AxiomNewZealandPilot(rulespec_root=str(rulespec_root))
    simulation = Simulation(dataset=dataset, tax_benefit_model_version=model)
    simulation.run()
    return simulation


def test_run_preserves_source_and_uses_family_weights(
    dataset, rulespec_root, stub_runtime
):
    before = sha256(Path(dataset.filepath).read_bytes()).hexdigest()
    simulation = _run(dataset, rulespec_root)
    output = simulation.output_dataset

    assert sha256(Path(dataset.filepath).read_bytes()).hexdigest() == before
    assert output.filepath is None
    assert output.is_output_dataset
    assert output.year == 2026
    assert output.policy_period == PERIOD
    assert output.metadata["data_build_id"] == SOURCE_METADATA["data_build_id"]
    assert dataset.metadata == SOURCE_METADATA
    assert "family" in FakeFrame.resolved_entities
    assert output.data.family[WFF_ABATEMENT_CHANGE].sum() == 120.0
    assert output.data.family[IWTC_CHANGE].sum() == 260.0
    np.testing.assert_array_equal(output.data.person["person_weight"], [2, 2, 2, 5, 5])
    np.testing.assert_array_equal(output.data.family["family_weight"], [2, 5])

    engine = FakeAxiomEngine.latest
    assert engine.rulespec_roots == (rulespec_root.resolve(),)
    assert engine.period == FakeAxiomPeriod(**PERIOD)
    assert engine.frame.weighted_entities == ("household",)
    assert "family_weight" not in engine.frame.table("family")
    assert "person_weight" not in engine.frame.table("person")
    assert all(name in engine.frame.table("family") for name in PADDING_INPUTS)
    assert not any(name in dataset.data.family for name in PADDING_INPUTS)
    receipt = output.metadata["policyengine_axiom_runs"][-1]
    assert receipt["provenance"] == TEST_PROVENANCE
    assert receipt["policy_period"] == PERIOD
    assert receipt["official_score_bridge"]["like_for_like_status"] == "bridge_required"
    simulation.save()
    assert sha256(Path(dataset.filepath).read_bytes()).hexdigest() == before


def test_dataset_rejects_mismatched_period(dataset, stub_runtime):
    dataset.year = 2027
    with pytest.raises(ValueError, match="period mismatch"):
        dataset.load()


@pytest.mark.parametrize("entity", ["person", "family"])
def test_source_dataset_rejects_extra_weight_vectors(tmp_path, stub_runtime, entity):
    tables = _tables()
    tables[entity][f"{entity}_weight"] = 1.0
    dataset = _write_dataset(tmp_path / "bad_weights.h5", tables)
    with pytest.raises(ValueError, match="sole stored weight"):
        dataset.load()


def test_dataset_rejects_family_crossing_households(tmp_path, stub_runtime):
    tables = _tables()
    tables["person"].loc[4, "person_family_id"] = 100
    dataset = _write_dataset(tmp_path / "cross_household.h5", tables)
    with pytest.raises(ValueError, match="exactly one household"):
        dataset.load()


@pytest.mark.parametrize("problem", ["missing", "null", "wrong_dtype"])
def test_substantive_family_inputs_never_default(
    dataset, rulespec_root, stub_runtime, problem
):
    dataset.load()
    name = "entitled_to_in_work_tax_credit"
    if problem == "missing":
        dataset.data.family = dataset.data.family.drop(columns=[name])
    elif problem == "null":
        dataset.data.family[name] = dataset.data.family[name].astype("boolean")
        dataset.data.family.loc[0, name] = None
    else:
        dataset.data.family[name] = [0, 1]
    with pytest.raises(ValueError, match=name):
        _run(dataset, rulespec_root)


def test_formula_owned_inputs_are_rejected(dataset, rulespec_root, stub_runtime):
    dataset.load()
    dataset.data.family[WFF_ABATEMENT_CHANGE] = 999.0
    with pytest.raises(ValueError, match="formula-owned"):
        _run(dataset, rulespec_root)


def test_changed_runtime_requires_new_model(
    dataset, rulespec_root, stub_runtime, monkeypatch
):
    model = AxiomNewZealandPilot(rulespec_root=str(rulespec_root))
    monkeypatch.setattr(
        nz_model, "_build_runtime_provenance", lambda _root: {"changed": True}
    )
    simulation = Simulation(dataset=dataset, tax_benefit_model_version=model)
    with pytest.raises(RuntimeError, match="changed"):
        simulation.run()


def test_extra_simulation_controls_fail_closed(dataset, rulespec_root, stub_runtime):
    model = AxiomNewZealandPilot(rulespec_root=str(rulespec_root))
    simulation = Simulation(
        dataset=dataset,
        tax_benefit_model_version=model,
        extra_variables={"family": ["unknown"]},
    )
    with pytest.raises(ValueError, match="extra_variables"):
        simulation.run()


def test_model_configuration_json_roundtrip(rulespec_root, stub_runtime):
    model = AxiomNewZealandPilot(rulespec_root=str(rulespec_root))
    restored = AxiomNewZealandPilot.model_validate_json(model.model_dump_json())
    assert restored.id == model.id
    assert restored.runtime_provenance == model.runtime_provenance
    assert restored.transport_contract == model.transport_contract


def test_tampered_effective_weights_fail(dataset, rulespec_root, stub_runtime):
    dataset.load()
    dataset.data.family["family_weight"] = [1.0, 1.0]
    with pytest.raises(ValueError, match="Frame-resolved"):
        _run(dataset, rulespec_root)


def test_output_datasets_cannot_be_reused(dataset, rulespec_root, stub_runtime):
    output = _run(dataset, rulespec_root).output_dataset
    with pytest.raises(ValueError, match="reused"):
        _run(output, rulespec_root)


@pytest.mark.parametrize("values", [[1.0], [float("nan"), 2.0]])
def test_invalid_engine_outputs_fail(
    dataset, rulespec_root, stub_runtime, monkeypatch, values
):
    monkeypatch.setattr(
        FakeAxiomEngine,
        "materialize",
        lambda *_: {
            WFF_ABATEMENT_CHANGE: np.array(values),
            IWTC_CHANGE: np.array([0.0, 0.0]),
        },
    )
    with pytest.raises(ValueError, match="invalid NZ output"):
        _run(dataset, rulespec_root)


def test_wrong_policy_build_year_fails_closed(tmp_path, rulespec_root, stub_runtime):
    dataset = _write_dataset(tmp_path / "wrong_year.h5", _tables(), year=2025)
    with pytest.raises(ValueError, match="2026"):
        _run(dataset, rulespec_root)


def test_expected_source_hash_is_verified(dataset, stub_runtime):
    dataset.source_sha256 = "0" * 64
    with pytest.raises(ValueError, match="SHA-256"):
        dataset.load()


def test_decimal_inputs_are_preserved(dataset, rulespec_root, stub_runtime):
    dataset.load()
    name = "wff_family_scheme_income_for_relationship_period"
    dataset.data.family[name] = [Decimal("50000.00"), Decimal("100000.00")]
    simulation = _run(dataset, rulespec_root)
    assert list(FakeAxiomEngine.latest.frame.table("family")[name]) == [
        Decimal("50000.00"),
        Decimal("100000.00"),
    ]
    assert simulation.output_dataset.data.family[WFF_ABATEMENT_CHANGE].sum() == 120.0


@pytest.mark.parametrize(
    "value", [Decimal("1.001"), Decimal("10000000000000000"), "50000.00"]
)
def test_out_of_contract_decimal_inputs_fail(
    dataset, rulespec_root, stub_runtime, value
):
    dataset.load()
    name = "wff_family_scheme_income_for_relationship_period"
    dataset.data.family[name] = [value, value]
    with pytest.raises(ValueError, match=name):
        _run(dataset, rulespec_root)


def test_nonzero_adapter_padding_fails(dataset, rulespec_root, stub_runtime):
    dataset.load()
    dataset.data.family[PADDING_INPUTS[0]] = 1
    with pytest.raises(ValueError, match="padding"):
        _run(dataset, rulespec_root)


def test_mutated_input_has_distinct_execution_fingerprint(
    dataset, rulespec_root, stub_runtime
):
    first = _run(dataset, rulespec_root).output_dataset.metadata[
        "policyengine_axiom_runs"
    ][-1]
    dataset.data.family["wff_family_scheme_income_for_relationship_period"] = [
        50001.0,
        100000.0,
    ]
    second = _run(dataset, rulespec_root).output_dataset.metadata[
        "policyengine_axiom_runs"
    ][-1]
    assert first["input_artifact_sha256"] == second["input_artifact_sha256"]
    assert first["input_frame_sha256"] != second["input_frame_sha256"]
    json.dumps(second, allow_nan=False)


@pytest.mark.skipif(
    os.environ.get("RUN_NZ_AXIOM_INTEGRATION") != "1",
    reason="requires compatible source-only Microcosm/Axiom runtime",
)
def test_real_axiom_source_stack_executes_both_reforms(tmp_path):
    from microcosm.frame.adapters.axiom import AxiomEntityTableDataset

    root = Path(os.environ["RULESPEC_NZ_ROOT"]).resolve()
    tables = _tables()
    family_inputs = tables["family"]
    for name, dtype in REQUIRED_INPUTS.items():
        if dtype == "decimal128(18,2)":
            family_inputs = family_inputs.assign(
                **{name: family_inputs[name].map(lambda value: Decimal(str(value)))}
            )
    family_inputs = family_inputs.assign(
        entitled_to_in_work_tax_credit=family_inputs[
            "entitled_to_in_work_tax_credit"
        ].astype("boolean")
    )
    tables["family"] = family_inputs
    path = tmp_path / "real_nz_fixture.h5"
    # Use the producer's actual codec, including exact Decimal persistence
    # and nullable booleans, rather than a parallel PolicyEngine writer.
    AxiomEntityTableDataset(tables=tables, time_period=2026).save(path)
    dataset = PopulaceNewZealandDataset(
        name="nz-real-runtime-fixture",
        description="Synthetic integration fixture, not calibrated NZ data",
        filepath=str(path),
        year=2026,
    )
    simulation = _run(dataset, root)
    family = simulation.output_dataset.data.family
    # These are the two upstream RuleSpec companion cases, with nonuniform
    # household weights 2 and 5. No official population score is asserted.
    np.testing.assert_allclose(np.asarray(family[WFF_ABATEMENT_CHANGE]), [568.5, 0.0])
    np.testing.assert_allclose(np.asarray(family[IWTC_CHANGE]), [0.0, 438.5])
    assert family[WFF_ABATEMENT_CHANGE].sum() == 1137.0
    assert family[IWTC_CHANGE].sum() == 2192.5
