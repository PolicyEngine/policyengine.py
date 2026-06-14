"""Citable simulation run records.

A run record is a self-contained directory — ``reform.json``,
``input.json``, ``results.json``, ``bundle.trace.tro.jsonld``, and a
``run.trace.tro.jsonld`` binding them all — whose TRO composition
fingerprint is the citable identifier for a hosted simulation run.
These tests pin the failure mode that motivated the feature: a web-app
result that vanished before publication and could not be re-derived.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest
from pydantic import BaseModel, ConfigDict

from policyengine.core.dataset import Dataset
from policyengine.core.parameter import Parameter
from policyengine.core.parameter_value import ParameterValue
from policyengine.core.policy import Policy
from policyengine.core.run_record import (
    UncertifiableSimulationError,
    build_simulation_run_record_payloads,
    reform_specification,
    write_simulation_run_record,
)
from policyengine.core.simulation import Simulation
from policyengine.provenance.manifest import (
    get_data_release_manifest,
    get_release_manifest,
)
from policyengine.provenance.trace import (
    build_trace_tro_from_release_bundle,
    canonical_json_bytes,
)
from policyengine.provenance.verify import verify_trace_tro_path

from .test_trace_tro import _fake_fetch_pypi, _us_data_release_manifest

FIXED_CREATED_AT = "2026-06-12T00:00:00Z"


class _StubYearData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    person: pd.DataFrame

    @property
    def entity_data(self) -> dict[str, pd.DataFrame]:
        return {"person": self.person}


def _parameter_value(name: str, value, start: str) -> ParameterValue:
    return ParameterValue.model_construct(
        parameter=Parameter.model_construct(name=name),
        value=value,
        start_date=datetime.fromisoformat(start),
        end_date=None,
    )


def _policy(*, modifier=None) -> Policy:
    return Policy.model_construct(
        name="ctc-base-3000",
        parameter_values=[
            _parameter_value(
                "gov.irs.credits.ctc.amount.base[0].amount", 3_000, "2026-01-01"
            ),
            _parameter_value("gov.abolitions.snap", True, "2026-01-01"),
        ],
        simulation_modifier=modifier,
    )


def _dataset(tmp_path: Path, filename: str, payload: bytes, **overrides) -> Dataset:
    filepath = tmp_path / filename
    filepath.write_bytes(payload)
    fields = {
        "name": filename.removesuffix(".h5"),
        "description": "test dataset",
        "filepath": str(filepath),
        "year": 2026,
        "data": None,
    }
    fields.update(overrides)
    return Dataset.model_construct(**fields)


@pytest.fixture
def bundle_tro(monkeypatch):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    tro = build_trace_tro_from_release_bundle(
        get_release_manifest("us"),
        _us_data_release_manifest(),
        fetch_pypi=_fake_fetch_pypi,
    )
    yield tro
    get_release_manifest.cache_clear()
    get_data_release_manifest.cache_clear()


@pytest.fixture
def simulation(tmp_path) -> Simulation:
    output_data = _StubYearData(
        person=pd.DataFrame({"age": [30, 40], "income_tax": [1_000.0, 2_000.0]})
    )
    return Simulation.model_construct(
        id="run-1",
        created_at=datetime(2026, 6, 12),
        policy=_policy(),
        dynamic=None,
        dataset=_dataset(tmp_path, "input_dataset.h5", b"input bytes"),
        scoping_strategy=None,
        extra_variables={},
        tax_benefit_model_version=None,
        output_dataset=_dataset(
            tmp_path, "output_dataset.h5", b"output bytes", data=output_data
        ),
    )


class TestReformSpecification:
    def test__given_none__then_returns_none(self):
        assert reform_specification(None) is None

    def test__given_parameter_values__then_payload_is_content_only(self):
        spec = reform_specification(_policy())
        assert spec["parameter_values"] == [
            {
                "parameter": "gov.abolitions.snap",
                "value": True,
                "start_date": "2026-01-01T00:00:00",
                "end_date": None,
            },
            {
                "parameter": "gov.irs.credits.ctc.amount.base[0].amount",
                "value": 3_000,
                "start_date": "2026-01-01T00:00:00",
                "end_date": None,
            },
        ]
        # Nondeterministic identity fields must not leak into the payload:
        # the same reform must hash identically across constructions.
        assert "id" not in spec
        assert "created_at" not in spec
        for entry in spec["parameter_values"]:
            assert set(entry) == {"parameter", "value", "start_date", "end_date"}

    def test__given_two_constructions__then_payload_bytes_match(self):
        first = canonical_json_bytes(reform_specification(_policy()))
        second = canonical_json_bytes(reform_specification(_policy()))
        assert first == second

    def test__given_simulation_modifier__then_raises_uncertifiable(self):
        with pytest.raises(UncertifiableSimulationError) as exc:
            reform_specification(_policy(modifier=lambda sim: sim))
        assert "simulation_modifier" in str(exc.value)


class TestRunRecordPayloads:
    def test__given_run_simulation__then_results_bind_output_file_hash(
        self, simulation
    ):
        payloads = build_simulation_run_record_payloads(simulation)
        output = payloads["results"]["output_dataset"]
        expected = hashlib.sha256(b"output bytes").hexdigest()
        assert output["sha256"] == expected
        assert output["file"] == "output_dataset.h5"
        assert output["tables"] == {
            "person": {"rows": 2, "columns": ["age", "income_tax"]}
        }

    def test__given_input_dataset__then_input_binds_file_hash_not_path(
        self, simulation
    ):
        payloads = build_simulation_run_record_payloads(simulation)
        dataset = payloads["input"]["dataset"]
        assert dataset["sha256"] == hashlib.sha256(b"input bytes").hexdigest()
        assert dataset["file"] == "input_dataset.h5"
        # Local absolute paths must not leak into a publishable record.
        assert "/" not in dataset["file"]
        assert json.dumps(payloads["input"]).find("tmp") == -1 or not str(
            simulation.dataset.filepath
        ).startswith("/tmp")

    def test__given_unrun_simulation__then_raises_with_guidance(self, simulation):
        simulation.output_dataset = None
        with pytest.raises(ValueError) as exc:
            build_simulation_run_record_payloads(simulation)
        assert "ensure()" in str(exc.value)

    def test__given_missing_output_file__then_raises(self, simulation):
        Path(simulation.output_dataset.filepath).unlink()
        with pytest.raises(FileNotFoundError):
            build_simulation_run_record_payloads(simulation)


class TestWriteRunRecord:
    def test__given_simulation__then_record_directory_is_self_contained(
        self, simulation, bundle_tro, tmp_path
    ):
        record = write_simulation_run_record(
            simulation,
            tmp_path / "record",
            bundle_tro=bundle_tro,
            created_at=FIXED_CREATED_AT,
        )
        names = {path.name for path in record.paths.values()}
        assert names == {
            "run.trace.tro.jsonld",
            "bundle.trace.tro.jsonld",
            "results.json",
            "input.json",
            "reform.json",
        }
        for path in record.paths.values():
            assert path.exists()

    def test__given_record__then_fingerprint_is_citable_and_deterministic(
        self, simulation, bundle_tro, tmp_path
    ):
        first = write_simulation_run_record(
            simulation,
            tmp_path / "first",
            bundle_tro=bundle_tro,
            created_at=FIXED_CREATED_AT,
        )
        second = write_simulation_run_record(
            simulation,
            tmp_path / "second",
            bundle_tro=bundle_tro,
            created_at=FIXED_CREATED_AT,
        )
        assert first.composition_fingerprint == second.composition_fingerprint
        assert len(first.composition_fingerprint) == 64
        tro_bytes = first.paths["tro"].read_bytes()
        assert tro_bytes == second.paths["tro"].read_bytes()

    def test__given_record__then_verifier_passes_offline(
        self, simulation, bundle_tro, tmp_path
    ):
        record = write_simulation_run_record(
            simulation,
            tmp_path / "record",
            bundle_tro=bundle_tro,
            created_at=FIXED_CREATED_AT,
        )
        report = verify_trace_tro_path(record.paths["tro"])
        assert report.fingerprint_status == "ok"
        assert report.ok

    def test__given_tampered_results__then_verifier_reports_mismatch(
        self, simulation, bundle_tro, tmp_path
    ):
        record = write_simulation_run_record(
            simulation,
            tmp_path / "record",
            bundle_tro=bundle_tro,
            created_at=FIXED_CREATED_AT,
        )
        results_path = record.paths["results"]
        tampered = json.loads(results_path.read_text())
        tampered["output_dataset"]["tables"]["person"]["rows"] = 99
        results_path.write_text(json.dumps(tampered, indent=2, sort_keys=True) + "\n")
        report = verify_trace_tro_path(record.paths["tro"])
        assert not report.ok
        statuses = {check.artifact_id: check.status for check in report.artifacts}
        assert statuses["results"] == "mismatch"

    def test__given_bundle_tro_url__then_recorded_on_performance(
        self, simulation, bundle_tro, tmp_path
    ):
        record = write_simulation_run_record(
            simulation,
            tmp_path / "record",
            bundle_tro=bundle_tro,
            bundle_tro_url="https://example.org/bundle.trace.tro.jsonld",
            created_at=FIXED_CREATED_AT,
        )
        graph = record.tro["@graph"][0]
        performance = graph["trov:hasPerformance"]
        assert (
            performance["pe:bundleTroUrl"]
            == "https://example.org/bundle.trace.tro.jsonld"
        )

    def test__given_record_tro__then_validates_against_schema(
        self, simulation, bundle_tro, tmp_path, request
    ):
        jsonschema = pytest.importorskip("jsonschema")
        from importlib.resources import files

        schema = json.loads(
            Path(
                str(
                    files("policyengine").joinpath(
                        "data", "schemas", "trace_tro.schema.json"
                    )
                )
            ).read_text()
        )
        record = write_simulation_run_record(
            simulation,
            tmp_path / "record",
            bundle_tro=bundle_tro,
            created_at=FIXED_CREATED_AT,
        )
        payload = json.loads(record.paths["tro"].read_text())
        jsonschema.Draft202012Validator(schema).validate(payload)

    def test__given_modifier_policy__then_write_refuses(
        self, simulation, bundle_tro, tmp_path
    ):
        simulation.policy = _policy(modifier=lambda sim: sim)
        with pytest.raises(UncertifiableSimulationError):
            write_simulation_run_record(
                simulation, tmp_path / "record", bundle_tro=bundle_tro
            )
        assert not (tmp_path / "record" / "run.trace.tro.jsonld").exists()

    def test__given_simulation_method__then_delegates(
        self, simulation, bundle_tro, tmp_path
    ):
        record = simulation.write_run_record(
            tmp_path / "record",
            bundle_tro=bundle_tro,
            created_at=FIXED_CREATED_AT,
        )
        assert record.paths["tro"].exists()


class TestCompiledReformIntegration:
    """The dict-reform compile path feeds reform_specification."""

    def test__given_dict_policy__then_specification_lists_parameter_path(self):
        pytest.importorskip("policyengine_us")
        import policyengine as pe

        if pe.us is None:
            pytest.skip("country imports are disabled in this environment")
        from policyengine.tax_benefit_models.common.reform import (
            compile_reform_to_policy,
        )

        compiled = compile_reform_to_policy(
            {"gov.irs.credits.ctc.amount.base[0].amount": 3_000},
            year=2026,
            model_version=pe.us.model,
        )
        spec = reform_specification(compiled)
        assert spec["parameter_values"][0]["parameter"] == (
            "gov.irs.credits.ctc.amount.base[0].amount"
        )
        assert spec["parameter_values"][0]["value"] == 3_000
