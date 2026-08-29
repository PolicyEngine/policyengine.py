"""Belgium pilot integration and source-stack contract tests.

The PolicyEngine seam is deterministic and runs in ordinary CI. It uses a
strict runtime double only at the unpublished Microcosm/Axiom boundary; no
test double claims to validate Belgian law. Set ``RUN_BE_AXIOM_INTEGRATION=1``
to additionally execute the real source-only stack once compatible checkouts
and the Axiom dense extension are installed.
"""

import os
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from microdf import MicroDataFrame

from policyengine.core import Simulation
from policyengine.tax_benefit_models.be import (
    EMPLOYEE_SSC,
    PIT_BEFORE_WITHHOLDING,
    REMUNERATION,
    AxiomBelgiumPilot,
    BEYearData,
    PopulaceBelgiumDataset,
)
from policyengine.tax_benefit_models.be import model as be_model_module

RULESPEC_ROOT = Path(
    os.environ.get("RULESPEC_BE_ROOT", "~/TheAxiomFoundation/rulespec-be")
).expanduser()
ORDINARY_WORKER_SSC_RATE = 0.1307  # arrete royal 28.11.1969, art. 19
INCOMES = [0.0, 20_000.0, 30_000.0, 60_000.0]
PERSON_WEIGHTS = [2.0, 2.0, 5.0, 5.0]
HOUSEHOLD_WEIGHTS = [2.0, 5.0]
SOURCE_METADATA = {
    "build_id": "microcosm-be-test-build",
    "calibration": {"weight_kind": "calibrated", "target_count": 21},
}
TEST_PROVENANCE = {
    "rulespec": {
        "repository": "TheAxiomFoundation/rulespec-be",
        "module": be_model_module.PILOT_MODULE,
        "module_sha256": "1" * 64,
        "belgium_tree_sha256": "2" * 64,
    },
    "runtime": {
        "microcosm_frame_version": "0.1.0",
        "microcosm_frame_tree_sha256": "3" * 64,
        "microcosm_axiom_adapter_sha256": "4" * 64,
        "axiom_python_version": "0.1.0",
        "axiom_python_sha256": "5" * 64,
        "axiom_dense_version": "0.1.0",
        "axiom_dense_sha256": "6" * 64,
    },
}


class FakeWeightKind:
    CALIBRATED = "calibrated"


class FakeWeights:
    def __init__(self, *, values, kind):
        self.values = np.asarray(values, dtype=float)
        self.kind = kind


class FakeFrame:
    latest = None

    def __init__(self, tables, schema, weights):
        self.tables = {name: table.copy() for name, table in tables.items()}
        self.schema = schema
        self.weights = weights
        type(self).latest = self


class FakeAxiomEngine:
    latest = None

    def __init__(self, module, *, rulespec_roots):
        self.module = Path(module)
        self.rulespec_roots = tuple(Path(root) for root in rulespec_roots)
        self.period = None
        type(self).latest = self

    def materialize(self, frame, variables, period):
        self.period = period
        assert variables == [EMPLOYEE_SSC, PIT_BEFORE_WITHHOLDING]
        gross = frame.tables["person"][REMUNERATION].to_numpy()
        return {
            EMPLOYEE_SSC: gross * 0.1,
            PIT_BEFORE_WITHHOLDING: gross * 0.2,
        }


@pytest.fixture
def stub_source_runtime(monkeypatch):
    FakeFrame.latest = None
    FakeAxiomEngine.latest = None
    monkeypatch.setattr(
        be_model_module,
        "_build_runtime_provenance",
        lambda _root: deepcopy(TEST_PROVENANCE),
    )
    monkeypatch.setattr(
        be_model_module,
        "_load_axiom_runtime",
        lambda: (
            FakeFrame,
            FakeWeightKind,
            FakeWeights,
            "current-microcosm-be-schema",
            FakeAxiomEngine,
        ),
    )


@pytest.fixture
def pilot_dataset(tmp_path):
    person = MicroDataFrame(
        pd.DataFrame(
            {
                "person_id": [1, 2, 3, 4],
                "person_household_id": [1, 1, 2, 2],
                "age": [40.0, 38.0, 30.0, 52.0],
                "is_male": [True, False, False, True],
                REMUNERATION: INCOMES,
                "person_weight": PERSON_WEIGHTS,
            }
        ),
        weights="person_weight",
    )
    household = MicroDataFrame(
        pd.DataFrame(
            {
                "household_id": [1, 2],
                "household_weight": HOUSEHOLD_WEIGHTS,
            }
        ),
        weights="household_weight",
    )
    path = tmp_path / "microcosm_be_test.h5"
    PopulaceBelgiumDataset(
        name="microcosm-be-test",
        description="four-person nonuniform-weight fixture",
        filepath=str(path),
        year=2026,
        metadata=deepcopy(SOURCE_METADATA),
        data=BEYearData(person=person, household=household),
    ).save()
    # Exercise load(), including metadata and _time_period, during the run.
    return PopulaceBelgiumDataset(
        name="microcosm-be-test",
        description="four-person nonuniform-weight fixture",
        filepath=str(path),
        year=2026,
    )


def _run(pilot_dataset, *, period=2025, communal_additional_tax_rate=0.0):
    version = AxiomBelgiumPilot(
        rulespec_root=str(RULESPEC_ROOT),
        period=period,
        communal_additional_tax_rate=communal_additional_tax_rate,
    )
    simulation = Simulation(
        dataset=pilot_dataset,
        tax_benefit_model_version=version,
    )
    simulation.run()
    return simulation


def test_run_preserves_input_periods_weights_and_metadata(
    pilot_dataset, stub_source_runtime
):
    input_path = Path(pilot_dataset.filepath)
    before = sha256(input_path.read_bytes()).hexdigest()

    simulation = _run(pilot_dataset, period=2025)
    output = simulation.output_dataset

    assert sha256(input_path.read_bytes()).hexdigest() == before
    assert output.filepath is None
    assert output.year == 2026
    assert output.policy_period == 2025
    assert FakeAxiomEngine.latest.period == 2025
    assert FakeAxiomEngine.latest.rulespec_roots == (RULESPEC_ROOT.resolve(),)
    assert pilot_dataset.metadata == SOURCE_METADATA
    assert output.metadata["build_id"] == SOURCE_METADATA["build_id"]
    assert output.metadata["calibration"] == SOURCE_METADATA["calibration"]
    run_metadata = output.metadata["policyengine_axiom_runs"][-1]
    assert run_metadata == {
        "dataset_year": 2026,
        "policy_period": 2025,
        "model_version": simulation.tax_benefit_model_version.version,
        "configuration": {
            "communal_additional_tax_rate": 0.0,
            "output_variables": [EMPLOYEE_SSC, PIT_BEFORE_WITHHOLDING],
        },
        "provenance": TEST_PROVENANCE,
    }

    frame = FakeFrame.latest
    assert frame.schema == "current-microcosm-be-schema"
    assert "person_weight" not in frame.tables["person"]
    assert "household_weight" not in frame.tables["household"]
    np.testing.assert_array_equal(
        frame.weights["household"].values,
        HOUSEHOLD_WEIGHTS,
    )
    assert frame.weights["household"].kind == FakeWeightKind.CALIBRATED

    # MicroDataFrame keeps the nonuniform calibrated person weights on every
    # output series: 0*2 + 2,000*2 + 3,000*5 + 6,000*5 = 49,000.
    assert float(output.data.person[EMPLOYEE_SSC].sum()) == 49_000.0
    np.testing.assert_array_equal(
        output.data.person["person_weight"],
        PERSON_WEIGHTS,
    )

    # Both the model's no-op persistence hook and the derived dataset's
    # missing destination leave the source bytes untouched.
    simulation.save()
    with pytest.raises(ValueError, match="without a filepath"):
        output.save()
    assert sha256(input_path.read_bytes()).hexdigest() == before


def test_default_policy_period_is_the_dataset_year(pilot_dataset, stub_source_runtime):
    simulation = _run(pilot_dataset, period=None)
    assert FakeAxiomEngine.latest.period == 2026
    assert simulation.output_dataset.policy_period == 2026


def test_run_records_result_changing_configuration(pilot_dataset, stub_source_runtime):
    simulation = _run(
        pilot_dataset,
        period=2025,
        communal_additional_tax_rate=0.075,
    )
    run_metadata = simulation.output_dataset.metadata["policyengine_axiom_runs"][-1]
    assert run_metadata["configuration"] == {
        "communal_additional_tax_rate": 0.075,
        "output_variables": [EMPLOYEE_SSC, PIT_BEFORE_WITHHOLDING],
    }
    np.testing.assert_array_equal(
        FakeFrame.latest.tables["person"]["belgium_pit_communal_additional_tax_rate"],
        [0.075] * 4,
    )


def test_output_metadata_round_trips_only_after_a_distinct_path_is_chosen(
    tmp_path, pilot_dataset, stub_source_runtime
):
    input_path = Path(pilot_dataset.filepath)
    before = sha256(input_path.read_bytes()).hexdigest()
    output = _run(pilot_dataset, period=2025).output_dataset
    output_path = tmp_path / "belgium_output.h5"
    assert output_path != input_path

    output.filepath = str(output_path)
    output.save()
    reloaded = PopulaceBelgiumDataset(
        name=output.name,
        description=output.description,
        filepath=str(output_path),
        year=output.year,
    )
    reloaded.load()

    assert reloaded.policy_period == 2025
    assert reloaded.metadata == output.metadata
    assert sha256(input_path.read_bytes()).hexdigest() == before


def test_dataset_rejects_a_mislabeled_hdf5_period(pilot_dataset):
    mislabeled = PopulaceBelgiumDataset(
        name=pilot_dataset.name,
        description=pilot_dataset.description,
        filepath=pilot_dataset.filepath,
        year=2025,
    )
    with pytest.raises(ValueError, match="period mismatch"):
        mislabeled.load()


def test_model_version_is_derived_from_content_provenance(
    monkeypatch, stub_source_runtime
):
    first = AxiomBelgiumPilot(rulespec_root=str(RULESPEC_ROOT), period=2025)
    assert first.version.startswith("rulespec-be@222222222222+runtime@")
    assert first.version != "0.1.0-pilot"
    assert first.id == f"{be_model_module.be_model.id}@{first.version}"

    attempted_override = AxiomBelgiumPilot(
        rulespec_root=str(RULESPEC_ROOT),
        period=2025,
        id="caller-supplied-id",
    )
    assert attempted_override.id == f"{be_model_module.be_model.id}@{first.version}"

    for field in (
        "microcosm_frame_tree_sha256",
        "microcosm_axiom_adapter_sha256",
        "axiom_python_sha256",
        "axiom_dense_sha256",
    ):
        changed = deepcopy(TEST_PROVENANCE)
        changed["runtime"][field] = "a" * 64
        monkeypatch.setattr(
            be_model_module,
            "_build_runtime_provenance",
            lambda _root, value=changed: value,
        )
        changed_version = AxiomBelgiumPilot(
            rulespec_root=str(RULESPEC_ROOT),
            period=2025,
        )
        assert changed_version.version != first.version


def test_run_refuses_provenance_drift(monkeypatch, pilot_dataset, stub_source_runtime):
    version = AxiomBelgiumPilot(rulespec_root=str(RULESPEC_ROOT), period=2025)
    changed = deepcopy(TEST_PROVENANCE)
    changed["rulespec"]["module_sha256"] = "f" * 64
    monkeypatch.setattr(
        be_model_module,
        "_build_runtime_provenance",
        lambda _root: changed,
    )
    simulation = Simulation(
        dataset=pilot_dataset,
        tax_benefit_model_version=version,
    )
    with pytest.raises(RuntimeError, match="changed after"):
        simulation.run()


def test_rulespec_tree_digest_binds_paths_and_bytes(tmp_path):
    first = tmp_path / "be" / "first.yaml"
    second = tmp_path / "be" / "nested" / "second.yml"
    second.parent.mkdir(parents=True)
    first.write_text("format: rulespec/v1\nrules: []\n", encoding="utf-8")
    second.write_text("format: rulespec/v1\nrules: []\n", encoding="utf-8")
    initial = be_model_module._rulespec_tree_sha256(tmp_path)
    second.write_text("format: rulespec/v1\nrules: [changed]\n", encoding="utf-8")
    assert be_model_module._rulespec_tree_sha256(tmp_path) != initial


def test_package_tree_digest_binds_execution_modules(monkeypatch, tmp_path):
    package_root = tmp_path / "microcosm" / "frame"
    package_root.mkdir(parents=True)
    (package_root / "__init__.py").write_text("from .bundle import Frame\n")
    bundle = package_root / "bundle.py"
    bundle.write_text("class Frame: pass\n")
    monkeypatch.setattr(
        be_model_module,
        "find_spec",
        lambda _name: SimpleNamespace(
            submodule_search_locations=[str(package_root)],
        ),
    )

    initial = be_model_module._package_tree_sha256("microcosm.frame")
    bundle.write_text("class Frame: changed = True\n")
    assert be_model_module._package_tree_sha256("microcosm.frame") != initial


def test_current_microcosm_frame_accepts_the_pilot_weight_contract():
    microcosm_frame = pytest.importorskip(
        "microcosm.frame",
        reason="microcosm-frame is an unpublished source dependency",
    )
    from microcosm.frame.adapters.axiom import BE_SCHEMA

    person = pd.DataFrame({"person_id": [1, 2], "person_household_id": [1, 2]})
    household = pd.DataFrame({"household_id": [1, 2]})
    weights = {
        "household": microcosm_frame.Weights(
            values=np.asarray(HOUSEHOLD_WEIGHTS),
            kind=microcosm_frame.WeightKind.CALIBRATED,
        )
    }
    frame = microcosm_frame.Frame(
        {"person": person, "household": household},
        BE_SCHEMA,
        weights,
    )
    np.testing.assert_array_equal(
        frame.weights_for("household").values,
        HOUSEHOLD_WEIGHTS,
    )
    assert frame.weights_for("household").kind is microcosm_frame.WeightKind.CALIBRATED


def test_saved_dataset_matches_the_current_axiom_hdf5_layout(pilot_dataset):
    pytest.importorskip(
        "microcosm.frame",
        reason="microcosm-frame is an unpublished source dependency",
    )
    from microcosm.frame.adapters.axiom import AxiomEntityTableDataset

    current = AxiomEntityTableDataset(file_path=pilot_dataset.filepath)
    assert current.time_period == 2026
    assert set(current.tables) == {"person", "household"}
    assert "person_weight" not in current.person
    assert current.household["household_weight"].tolist() == HOUSEHOLD_WEIGHTS

    pilot_dataset.load()
    np.testing.assert_array_equal(
        pilot_dataset.data.person["person_weight"],
        PERSON_WEIGHTS,
    )


def test_dataset_rejects_a_mismatched_legacy_person_weight(tmp_path):
    pytest.importorskip(
        "microcosm.frame",
        reason="microcosm-frame is an unpublished source dependency",
    )
    from microcosm.frame.adapters.axiom import AxiomEntityTableDataset

    path = tmp_path / "legacy_mismatch.h5"
    AxiomEntityTableDataset(
        tables={
            "person": pd.DataFrame(
                {
                    "person_id": [1, 2],
                    "person_household_id": [1, 2],
                    "person_weight": [2.0, 999.0],
                }
            ),
            "household": pd.DataFrame(
                {
                    "household_id": [1, 2],
                    "household_weight": [2.0, 5.0],
                }
            ),
        },
        time_period=2026,
    ).save(path)

    dataset = PopulaceBelgiumDataset(
        name="legacy-mismatch",
        description="invalid redundant person weights",
        filepath=str(path),
        year=2026,
    )
    with pytest.raises(ValueError, match="person_weight values do not exactly match"):
        dataset.load()


@pytest.mark.skipif(
    os.environ.get("RUN_BE_AXIOM_INTEGRATION") != "1",
    reason=(
        "set RUN_BE_AXIOM_INTEGRATION=1 with compatible microcosm-frame, "
        "axiom-rules-engine, dense extension, and rulespec-be source checkouts"
    ),
)
def test_real_source_stack_computes_the_worker_slice(pilot_dataset):
    simulation = _run(pilot_dataset, period=2025)
    person = pd.DataFrame(simulation.output_dataset.data.person)
    gross = person[REMUNERATION].to_numpy()
    ssc = person[EMPLOYEE_SSC].to_numpy()
    pit = person[PIT_BEFORE_WITHHOLDING].to_numpy()

    statutory = gross * ORDINARY_WORKER_SSC_RATE
    assert ssc[0] == 0.0
    assert ssc[1] == 0.0
    assert 0.0 < ssc[2] < statutory[2]
    np.testing.assert_allclose(ssc[3], statutory[3], rtol=1e-9)
    assert pit[0] == 0.0
    assert 0.0 <= pit[1] <= pit[2] < pit[3]
