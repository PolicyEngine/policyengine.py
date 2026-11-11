"""Synthetic, survey-free evidence for data-limited replay exceptions.

The country model is intentionally used directly: this probe establishes that
the exact installed candidate responds to a positive input, independently of
the survey data whose absence is under review.
"""

from __future__ import annotations

import math
from importlib.metadata import version
from typing import Any

from policyengine.provenance.qualification import (
    GateResult,
    ReplayExceptionProbe,
    ReplayExceptionRegistry,
    _replay_exceptions,
)
from policyengine.provenance.receipt import content_sha256


def _run_probe(spec: ReplayExceptionProbe) -> dict[str, Any]:
    from policyengine_uk import Simulation
    from policyengine_uk.model_api import Reform

    period = str(spec.year)
    reform_rates: list[dict[str, float]] = []

    def modify_parameters(parameters):
        scale = parameters
        for name in spec.parameter.split("."):
            scale = getattr(scale, name)
        # SDLT uses a marginal rate scale; update every bracket, including
        # those above the synthetic purchase price, against its actual value.
        if not scale.brackets:
            raise ValueError("Probe parameter has no rate brackets.")
        rates = []
        for bracket in scale.brackets:
            baseline = float(bracket.rate(period))
            changed = baseline + spec.rate_increment
            bracket.rate.update(period=period, value=changed)
            rates.append({"baseline": baseline, "reform": changed})
        if reform_rates and reform_rates != rates:
            raise ValueError("Positive and zero probes used different reform rates.")
        reform_rates[:] = rates
        return parameters

    class ProbeReform(Reform):
        def apply(self):
            self.modify_parameters(modifier_function=modify_parameters)

    def output(price: float, reform=None) -> float:
        situation = {
            "people": {"person": {"age": {period: 40}}},
            "benunits": {"benunit": {"members": ["person"]}},
            "households": {
                "household": {
                    "members": ["person"],
                    "region": {period: spec.region},
                    spec.input_variable: {period: price},
                }
            },
        }
        simulation = Simulation(situation=situation, reform=reform)
        values = simulation.calculate(spec.output_variable, period)
        if len(values) != 1:
            raise ValueError("Probe must produce exactly one household output.")
        result = float(values[0])
        if not math.isfinite(result):
            raise ValueError("Probe produced a non-finite output.")
        return result

    positive_baseline = output(spec.positive_input_gbp)
    positive_reform = output(spec.positive_input_gbp, ProbeReform)
    zero_baseline = output(0)
    zero_reform = output(0, ProbeReform)
    positive_change = positive_reform - positive_baseline
    zero_change = zero_reform - zero_baseline
    passed = (
        positive_change > 0
        and abs(positive_change - spec.expected_change_gbp)
        <= spec.absolute_tolerance_gbp
        and zero_change == 0
    )
    return {
        "status": "pass" if passed else "fail",
        "positive_baseline_gbp": positive_baseline,
        "positive_reform_gbp": positive_reform,
        "positive_change_gbp": positive_change,
        "zero_baseline_gbp": zero_baseline,
        "zero_reform_gbp": zero_reform,
        "zero_change_gbp": zero_change,
        "rates": reform_rates,
    }


def run_replay_probes(
    *,
    attempt_id: str,
    candidate_model_version: str,
    exception_registry: ReplayExceptionRegistry | None = None,
) -> tuple[GateResult, dict[str, Any]]:
    """Run registry probes and seal their attempt-specific JSON evidence.

    Any import, version, variable, parameter or calculation failure becomes
    failing evidence. The replay evaluator decides whether an exception needs
    this evidence; this result is not an additional unconditional release gate.
    """

    if exception_registry is None:
        registry, registry_sha256 = _replay_exceptions()
    else:
        registry = exception_registry
        registry_sha256 = content_sha256(registry.canonical_payload())
    evidence: dict[str, Any] = {
        "attempt_id": attempt_id,
        "candidate_model_version": candidate_model_version,
        "exception_registry_sha256": registry_sha256,
        "probes": [],
    }
    for entry in registry.exceptions:
        probe: dict[str, Any] = {
            "exception_id": entry.id,
            "spec_sha256": content_sha256(entry.probe.model_dump(mode="json")),
        }
        try:
            installed_version = version("policyengine-uk")
            probe["installed_model_version"] = installed_version
            if installed_version != candidate_model_version:
                raise ValueError(
                    f"Installed policyengine-uk {installed_version} does not match "
                    f"candidate {candidate_model_version}."
                )
            probe.update(_run_probe(entry.probe))
        except Exception as error:
            probe.update(status="fail", error=f"{type(error).__name__}: {error}")
        evidence["probes"].append(probe)
    failed = sum(probe["status"] != "pass" for probe in evidence["probes"])
    result = GateResult(
        gate_id="replay_probe",
        status="fail" if failed else "pass",
        summary=(
            f"{failed} of {len(evidence['probes'])} replay exception probes failed."
            if failed
            else f"All {len(evidence['probes'])} replay exception probes passed."
        ),
        evidence_sha256=content_sha256(evidence),
        details={
            "attempt_id": attempt_id,
            "candidate_model_version": candidate_model_version,
            "exception_registry_sha256": registry_sha256,
            "probe_count": len(evidence["probes"]),
            "failed_probes": failed,
        },
    )
    return result, evidence
