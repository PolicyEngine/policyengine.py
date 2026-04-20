"""Regression: the US microsim path in ``Simulation.run``/``ensure``
must apply structural reforms (``gov.contrib.ctc.minimum_refundable``
et al.) to the Simulation it runs against.

Prior to the fix, ``_build_simulation_from_dataset`` passed the
module-level ``policyengine_us.system`` to ``instantiate_entities``
instead of the per-sim ``microsim.tax_benefit_system``. The per-sim
system has the structural reforms applied; the module one does not.
Building populations against the module system hid reform-registered
variables (``ctc_minimum_refundable_amount``) at calc time, surfacing
as ``AttributeError: 'NoneType' object has no attribute 'entity'``
inside ``for_each_variable``.

This file guards against regression at three levels of strictness:

1. **End-to-end**: a published external reform (policy 94589 on
   app.policyengine.org) exercises three
   ``gov.contrib.ctc.*.in_effect`` gates at once.
2. **Per-gate smoke test**: each individual ``gov.contrib.ctc.*``
   structural reform activates cleanly.
3. **Invariant**: the ``Microsimulation``'s ``tax_benefit_system``
   is actually being used to build populations (the fix itself).
"""

from __future__ import annotations

import pandas as pd
import pytest
from microdf import MicroDataFrame

pytest.importorskip("policyengine_us")


def _us_fixture_dataset(tmp_path, year: int = 2025):
    """Tiny in-memory dataset: two low-earning single-parent tax units.

    Exercises the minimum-refundable and per-child phase-in code paths
    that the bug used to hide.
    """
    import policyengine as pe  # noqa: F401 — triggers registry
    from policyengine.tax_benefit_models.us.datasets import (
        PolicyEngineUSDataset,
        USYearData,
    )

    person = MicroDataFrame(
        pd.DataFrame(
            {
                "person_id": [1, 2, 3, 4, 5, 6],
                "household_id": [1, 1, 1, 2, 2, 2],
                "tax_unit_id": [1, 1, 1, 2, 2, 2],
                "spm_unit_id": [1, 1, 1, 2, 2, 2],
                "family_id": [1, 1, 1, 2, 2, 2],
                "marital_unit_id": [1, 2, 3, 4, 5, 6],
                "person_weight": [1_000.0] * 6,
                "age": [32, 5, 8, 30, 3, 6],
                "employment_income": [3_000, 0, 0, 2_000, 0, 0],
            }
        ),
        weights="person_weight",
    )
    household = MicroDataFrame(
        pd.DataFrame(
            {
                "household_id": [1, 2],
                "state_code": ["CA", "TX"],
                "household_weight": [1_000.0, 1_000.0],
            }
        ),
        weights="household_weight",
    )

    def _simple(col: str, rows: int, weight: str) -> MicroDataFrame:
        return MicroDataFrame(
            pd.DataFrame({col: list(range(1, rows + 1)), weight: [1_000.0] * rows}),
            weights=weight,
        )

    return PolicyEngineUSDataset(
        id="test-contrib-ctc",
        name="Contrib CTC fixture",
        description="Tiny dataset exercising structural-reform application",
        filepath=str(tmp_path / "test.h5"),
        year=year,
        data=USYearData(
            person=person,
            tax_unit=_simple("tax_unit_id", 2, "tax_unit_weight"),
            spm_unit=_simple("spm_unit_id", 2, "spm_unit_weight"),
            family=_simple("family_id", 2, "family_weight"),
            marital_unit=_simple("marital_unit_id", 6, "marital_unit_weight"),
            household=household,
        ),
    )


# --- 1. End-to-end: published external reform runs cleanly -------------


POLICY_94589_REFORM = {
    # ARPA-style CTC
    "gov.irs.credits.ctc.amount.arpa[0].amount": 4_800,
    "gov.irs.credits.ctc.amount.arpa[1].amount": 4_800,
    "gov.irs.credits.ctc.phase_out.arpa.in_effect": True,
    "gov.irs.credits.ctc.phase_out.arpa.amount": 25,
    "gov.irs.credits.ctc.phase_out.arpa.threshold.JOINT": 35_000,
    "gov.irs.credits.ctc.phase_out.arpa.threshold.SINGLE": 25_000,
    "gov.irs.credits.ctc.phase_out.arpa.threshold.SEPARATE": 25_000,
    "gov.irs.credits.ctc.phase_out.arpa.threshold.HEAD_OF_HOUSEHOLD": 25_000,
    "gov.irs.credits.ctc.phase_out.arpa.threshold.SURVIVING_SPOUSE": 25_000,
    "gov.irs.credits.ctc.phase_out.amount": 25,
    "gov.irs.credits.ctc.phase_out.threshold.JOINT": 200_000,
    "gov.irs.credits.ctc.phase_out.threshold.SINGLE": 100_000,
    "gov.irs.credits.ctc.phase_out.threshold.SEPARATE": 100_000,
    "gov.irs.credits.ctc.phase_out.threshold.HEAD_OF_HOUSEHOLD": 100_000,
    "gov.irs.credits.ctc.phase_out.threshold.SURVIVING_SPOUSE": 100_000,
    "gov.irs.credits.ctc.refundable.phase_in.rate": 0.2,
    "gov.irs.credits.ctc.refundable.phase_in.threshold": 0,
    "gov.irs.credits.ctc.refundable.individual_max": 4_800,
    # All three structural-reform in_effect gates — THE ONES THAT HIT THE BUG
    "gov.contrib.ctc.minimum_refundable.in_effect": True,
    "gov.contrib.ctc.minimum_refundable.amount[0].amount": 2_400,
    "gov.contrib.ctc.minimum_refundable.amount[1].amount": 2_400,
    "gov.contrib.ctc.per_child_phase_in.in_effect": True,
    "gov.contrib.ctc.per_child_phase_out.in_effect": True,
    "gov.contrib.ctc.per_child_phase_out.avoid_overlap": True,
    # Flattened EITC
    "gov.irs.credits.eitc.max[0].amount": 2_000,
    "gov.irs.credits.eitc.max[1].amount": 2_000,
    "gov.irs.credits.eitc.max[2].amount": 2_000,
    "gov.irs.credits.eitc.max[3].amount": 2_000,
    "gov.irs.credits.eitc.phase_in_rate[0].amount": 0.2,
    "gov.irs.credits.eitc.phase_in_rate[1].amount": 0.2,
    "gov.irs.credits.eitc.phase_in_rate[2].amount": 0.2,
    "gov.irs.credits.eitc.phase_in_rate[3].amount": 0.2,
    "gov.irs.credits.eitc.phase_out.rate[0].amount": 0.1,
    "gov.irs.credits.eitc.phase_out.rate[1].amount": 0.1,
    "gov.irs.credits.eitc.phase_out.rate[2].amount": 0.1,
    "gov.irs.credits.eitc.phase_out.rate[3].amount": 0.1,
    "gov.irs.credits.eitc.phase_out.start[0].amount": 20_000,
    "gov.irs.credits.eitc.phase_out.start[1].amount": 20_000,
    "gov.irs.credits.eitc.phase_out.start[2].amount": 20_000,
    "gov.irs.credits.eitc.phase_out.start[3].amount": 20_000,
    "gov.irs.credits.eitc.phase_out.joint_bonus[0].amount": 7_000,
    "gov.irs.credits.eitc.phase_out.joint_bonus[1].amount": 7_000,
}


def test__policy_94589_reform_runs_end_to_end(tmp_path) -> None:
    """Canary: the exact reform from app.policyengine.org policy 94589
    (a 42-parameter CTC+EITC expansion that activates three
    ``gov.contrib.ctc.*.in_effect`` gates simultaneously) must run
    through ``Simulation.ensure()`` without raising.
    """
    import policyengine as pe
    from policyengine.core import Simulation

    dataset = _us_fixture_dataset(tmp_path)
    sim = Simulation(
        dataset=dataset,
        tax_benefit_model_version=pe.us.model,
        policy=POLICY_94589_REFORM,
    )
    sim.run()
    # Reform can't silently zero everything.
    reform_ctc = sim.output_dataset.data.tax_unit["ctc"].sum()
    assert reform_ctc > 0, (
        f"Reformed CTC aggregate should be positive, got {reform_ctc}"
    )


# --- 2. Per-gate smoke tests ------------------------------------------


CONTRIB_GATES = [
    # Each tuple: (params_to_enable, human description).
    # CTC gates — the original bug's exact shape.
    (
        {
            "gov.contrib.ctc.minimum_refundable.in_effect": True,
            "gov.contrib.ctc.minimum_refundable.amount[0].amount": 2_400,
            "gov.contrib.ctc.minimum_refundable.amount[1].amount": 2_400,
        },
        "ctc_minimum_refundable",
    ),
    (
        {"gov.contrib.ctc.per_child_phase_in.in_effect": True},
        "ctc_per_child_phase_in",
    ),
    (
        {"gov.contrib.ctc.per_child_phase_out.in_effect": True},
        "ctc_per_child_phase_out",
    ),
    # Non-CTC gate — proves the fix generalises beyond the single
    # family of structural reforms that triggered the original bug.
    (
        {"gov.contrib.streamlined_eitc.in_effect": True},
        "streamlined_eitc",
    ),
]


@pytest.mark.parametrize(
    "reform,label",
    CONTRIB_GATES,
    ids=[label for _, label in CONTRIB_GATES],
)
def test__gov_contrib_gate_runs_cleanly(tmp_path, reform, label) -> None:
    """Each ``gov.contrib.*`` structural-reform gate activated via a
    parameter dict must apply cleanly through ``Simulation.run()``.
    Before the fix, CTC-family gates crashed with
    ``AttributeError: 'NoneType' object has no attribute 'entity'``.
    """
    import policyengine as pe
    from policyengine.core import Simulation

    dataset = _us_fixture_dataset(tmp_path)
    sim = Simulation(
        dataset=dataset,
        tax_benefit_model_version=pe.us.model,
        policy=reform,
    )
    sim.run()  # no exception = fix still holds


# --- 3. Invariant: population built from microsim's own system --------


def test__population_built_against_reform_applied_system(tmp_path, monkeypatch) -> None:
    """The fix's actual contract: ``_build_simulation_from_dataset``
    must pass the ``TaxBenefitSystem`` that has the structural reform
    applied — i.e. ``microsim.tax_benefit_system``, not some other copy.

    We intercept the helper, capture the ``system`` it received, and
    assert identity against ``microsim.tax_benefit_system``. That's a
    stricter invariant than any behavioral assertion — a silently-
    diverged copy would still fail the ``is`` check.

    Also verify that a structural-reform-only variable is registered
    on that captured system. Survives future ``policyengine_us``
    releases that might ship the variable unconditionally: the
    identity assertion is the load-bearing one.
    """
    import policyengine as pe
    from policyengine.core import Simulation
    from policyengine.tax_benefit_models.us.model import PolicyEngineUSLatest

    captured: dict = {}
    original = PolicyEngineUSLatest._build_simulation_from_dataset

    def _capturing(self_, microsim, dataset_arg, system):
        captured["system"] = system
        captured["microsim_system"] = microsim.tax_benefit_system
        return original(self_, microsim, dataset_arg, system)

    monkeypatch.setattr(
        PolicyEngineUSLatest,
        "_build_simulation_from_dataset",
        _capturing,
    )

    dataset = _us_fixture_dataset(tmp_path)
    sim = Simulation(
        dataset=dataset,
        tax_benefit_model_version=pe.us.model,
        policy={
            "gov.contrib.ctc.minimum_refundable.in_effect": True,
            "gov.contrib.ctc.minimum_refundable.amount[0].amount": 2_400,
            "gov.contrib.ctc.minimum_refundable.amount[1].amount": 2_400,
        },
    )
    sim.run()

    assert "system" in captured, (
        "_build_simulation_from_dataset was never called — test setup is broken"
    )
    # The load-bearing contract: the helper got the per-sim system.
    assert captured["system"] is captured["microsim_system"], (
        "_build_simulation_from_dataset was passed a TaxBenefitSystem "
        "that is not microsim.tax_benefit_system. Reform-registered "
        "variables will be invisible at calc time."
    )
    # And that system has the structural reform variable registered.
    assert (
        captured["system"].get_variable("ctc_minimum_refundable_amount") is not None
    ), (
        "Structural reform variable missing from the captured system — "
        "reform was not applied before population build"
    )


# --- 4. Parameter-change-shows-up-in-output invariant ----------------


def test__reform_parameter_change_is_reflected_in_output(tmp_path) -> None:
    """A reform that changes non-structural parameter values must
    produce different output from baseline across *every* affected
    variable. Guards against (a) the reform silently becoming a no-op
    and (b) partial application where one variable sees the change
    but another does not.

    Uses two non-structural overrides (CTC base and EITC max) so the
    test flags partial-application regressions, not just "no reform
    applied at all".
    """
    import policyengine as pe
    from policyengine.core import Simulation

    dataset = _us_fixture_dataset(tmp_path)
    baseline = Simulation(dataset=dataset, tax_benefit_model_version=pe.us.model)
    # Raise base CTC amount AND change EITC phase-in rate — different
    # program families, both at low incomes where the fixture's 2-kid
    # tax units are squarely in the phase-in region.
    reformed = Simulation(
        dataset=dataset,
        tax_benefit_model_version=pe.us.model,
        policy={
            "gov.irs.credits.ctc.amount.base[0].amount": 10_000,
            "gov.irs.credits.eitc.phase_in_rate[2].amount": 0.9,
        },
    )
    baseline.run()
    reformed.run()

    baseline_ctc = baseline.output_dataset.data.tax_unit["ctc"].sum()
    reform_ctc = reformed.output_dataset.data.tax_unit["ctc"].sum()
    baseline_eitc = baseline.output_dataset.data.tax_unit["eitc"].sum()
    reform_eitc = reformed.output_dataset.data.tax_unit["eitc"].sum()
    assert reform_ctc > baseline_ctc, (
        "CTC reform didn't reach the calculation: "
        f"baseline CTC {baseline_ctc} vs reformed CTC {reform_ctc}"
    )
    assert reform_eitc != baseline_eitc, (
        "EITC reform didn't reach the calculation (partial application "
        f"regression): baseline EITC {baseline_eitc} vs reformed EITC "
        f"{reform_eitc}"
    )
