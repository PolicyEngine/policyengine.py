"""The exact candidate must respond to a positive missing purchase input."""

from __future__ import annotations

from importlib.metadata import version

import pytest

import policyengine.provenance.replay_probe as replay_probe
from policyengine.provenance.qualification import _replay_exceptions
from policyengine.provenance.receipt import content_sha256


@pytest.fixture
def registry():
    return _replay_exceptions()[0]


@pytest.fixture(scope="module")
def country():
    model = pytest.importorskip("policyengine_uk")
    if not version("policyengine-uk").startswith("2.134."):
        pytest.skip("The replay probe real-model tests require pe-uk 2.134.x.")
    return model


def run(registry):
    return replay_probe.run_replay_probes(
        attempt_id="probe-attempt",
        candidate_model_version=version("policyengine-uk"),
        exception_registry=registry,
    )


@pytest.mark.real_install
def test_sdlt_positive_input_probe_passes_on_installed_candidate(country, registry):
    result, evidence = run(registry)
    assert result.status == "pass", evidence
    assert result.evidence_sha256 == content_sha256(evidence)
    assert evidence["attempt_id"] == "probe-attempt"
    assert evidence["candidate_model_version"] == version("policyengine-uk")
    (probe,) = evidence["probes"]
    assert probe["status"] == "pass"
    assert probe["spec_sha256"] == content_sha256(
        registry.exceptions[0].probe.model_dump(mode="json")
    )
    assert probe["positive_change_gbp"] == pytest.approx(6000, abs=0.1)
    assert probe["zero_change_gbp"] == 0
    assert len(probe["rates"]) == 5
    assert all(
        rate["reform"] - rate["baseline"] == pytest.approx(0.02)
        for rate in probe["rates"]
    )


@pytest.mark.real_install
def test_probe_fails_when_installed_model_ignores_purchase_input(
    country, registry, monkeypatch
):
    import numpy as np
    from sortedcontainers import SortedDict

    original_init = country.CountryTaxBenefitSystem.__init__

    def broken_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.variables[
            "sdlt_on_residential_property_transactions"
        ].formulas = SortedDict(
            {
                "0001-01-01": lambda household, period, parameters: np.zeros(
                    household.count
                )
            }
        )

    monkeypatch.setattr(country.CountryTaxBenefitSystem, "__init__", broken_init)
    result, evidence = run(registry)
    assert result.status == "fail"
    (probe,) = evidence["probes"]
    assert probe["status"] == "fail"
    assert "error" not in probe, probe
    assert probe["positive_change_gbp"] == 0
    assert probe["zero_change_gbp"] == 0


@pytest.mark.real_install
def test_wrong_parameter_path_records_failing_probe(country, registry):
    payload = registry.canonical_payload()
    payload["exceptions"][0]["probe"]["parameter"] = "gov.hmrc.no_such_sdlt_parameter"
    registry = type(registry).model_validate(payload)
    result, evidence = run(registry)
    assert result.status == "fail"
    assert evidence["probes"][0]["status"] == "fail"
    assert "no_such_sdlt_parameter" in evidence["probes"][0]["error"]
    assert result.evidence_sha256 == content_sha256(evidence)


def test_probe_for_other_installed_version_records_failure(registry, monkeypatch):
    monkeypatch.setattr(replay_probe, "version", lambda package: "0.0.0")
    result, evidence = replay_probe.run_replay_probes(
        attempt_id="attempt",
        candidate_model_version="2.134.7",
        exception_registry=registry,
    )
    assert result.status == "fail"
    assert "does not match candidate" in evidence["probes"][0]["error"]


def test_probe_records_the_registry_digest_it_read(registry, monkeypatch):
    monkeypatch.setattr(
        replay_probe,
        "_run_probe",
        lambda spec: {
            "status": "pass",
            "positive_change_gbp": 6000,
            "zero_change_gbp": 0,
        },
    )
    result, evidence = run(registry)
    digest = content_sha256(registry.canonical_payload())
    assert evidence["exception_registry_sha256"] == digest
    assert result.details["exception_registry_sha256"] == digest
    assert result.evidence_sha256 == content_sha256(evidence)


@pytest.mark.parametrize("error", [ImportError("unavailable model"), KeyError("input")])
def test_probe_calculation_error_records_failure(registry, monkeypatch, error):
    monkeypatch.setattr(replay_probe, "version", lambda package: "2.134.7")

    def broken(spec):
        raise error

    monkeypatch.setattr(replay_probe, "_run_probe", broken)
    result, evidence = replay_probe.run_replay_probes(
        attempt_id="attempt",
        candidate_model_version="2.134.7",
        exception_registry=registry,
    )
    assert result.status == "fail"
    assert type(error).__name__ in evidence["probes"][0]["error"]
    assert result.evidence_sha256 == content_sha256(evidence)
