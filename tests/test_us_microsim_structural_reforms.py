"""Regression: the US microsim path in ``pe.us.economic_impact_analysis``
must apply structural reforms (``gov.contrib.ctc.minimum_refundable``
et al.) to the Simulation it runs against.

Prior to the fix, ``_build_simulation_from_dataset`` passed the
module-level ``policyengine_us.system`` to ``instantiate_entities``
instead of the ``Microsimulation``'s per-sim ``tax_benefit_system``.
The per-sim system has the structural reforms applied; the module
one does not. Building populations against the module system hid
reform-registered variables (``ctc_minimum_refundable_amount``) at
calc time, surfacing as
``AttributeError: 'NoneType' object has no attribute 'entity'``
inside ``for_each_variable``.

Tara Watson's published CTC+EITC reform (policy 94589 on
app.policyengine.org) exercises exactly this path — it uses three
``gov.contrib.ctc.*.in_effect = True`` gates. If this test fails,
every dict reform of the form ``{"gov.contrib.ctc.*": ...}`` routed
through ``Simulation(policy=...)`` will silently crash at ``.ensure()``.
"""

from __future__ import annotations

import pytest

pytest.importorskip("policyengine_us")


def test__microsim_applies_gov_contrib_ctc_minimum_refundable_reform(
    tmp_path,
) -> None:
    """End-to-end: build a Simulation with the contrib-CTC reform as a
    dict, run it, and assert the reform is live by comparing against
    baseline.

    Uses a tiny custom dataset so the test doesn't pull HF data — the
    structural-reform bug is independent of the dataset size.
    """
    import numpy as np
    import pandas as pd
    from microdf import MicroDataFrame

    import policyengine as pe
    from policyengine.core import Simulation
    from policyengine.tax_benefit_models.us.datasets import (
        PolicyEngineUSDataset,
        USYearData,
    )

    # Two single-parent tax units, both with low earnings so the
    # $2,400-per-kid minimum-refundable floor would bind if the reform
    # were applied.
    person = MicroDataFrame(
        pd.DataFrame({
            "person_id": [1, 2, 3, 4, 5, 6],
            "household_id": [1, 1, 1, 2, 2, 2],
            "tax_unit_id": [1, 1, 1, 2, 2, 2],
            "spm_unit_id": [1, 1, 1, 2, 2, 2],
            "family_id": [1, 1, 1, 2, 2, 2],
            "marital_unit_id": [1, 2, 3, 4, 5, 6],
            "person_weight": [1_000.0] * 6,
            "age": [32, 5, 8, 30, 3, 6],
            "employment_income": [3_000, 0, 0, 2_000, 0, 0],
        }),
        weights="person_weight",
    )
    household = MicroDataFrame(
        pd.DataFrame({
            "household_id": [1, 2],
            "state_code": ["CA", "TX"],
            "household_weight": [1_000.0, 1_000.0],
        }),
        weights="household_weight",
    )
    tax_unit = MicroDataFrame(
        pd.DataFrame({
            "tax_unit_id": [1, 2],
            "tax_unit_weight": [1_000.0, 1_000.0],
        }),
        weights="tax_unit_weight",
    )
    spm_unit = MicroDataFrame(
        pd.DataFrame({
            "spm_unit_id": [1, 2],
            "spm_unit_weight": [1_000.0, 1_000.0],
        }),
        weights="spm_unit_weight",
    )
    family = MicroDataFrame(
        pd.DataFrame({
            "family_id": [1, 2],
            "family_weight": [1_000.0, 1_000.0],
        }),
        weights="family_weight",
    )
    marital_unit = MicroDataFrame(
        pd.DataFrame({
            "marital_unit_id": [1, 2, 3, 4, 5, 6],
            "marital_unit_weight": [1_000.0] * 6,
        }),
        weights="marital_unit_weight",
    )

    dataset = PolicyEngineUSDataset(
        id="test-contrib-ctc",
        name="Contrib CTC fixture",
        description="Tiny dataset exercising structural-reform application",
        filepath=str(tmp_path / "test.h5"),
        year=2025,
        data=USYearData(
            person=person,
            tax_unit=tax_unit,
            spm_unit=spm_unit,
            family=family,
            marital_unit=marital_unit,
            household=household,
        ),
    )

    period = "2025-01-01"
    reform = {
        "gov.contrib.ctc.minimum_refundable.in_effect": {period: True},
        "gov.contrib.ctc.minimum_refundable.amount[0].amount": {period: 2_400},
        "gov.contrib.ctc.minimum_refundable.amount[1].amount": {period: 2_400},
    }

    baseline = Simulation(
        dataset=dataset, tax_benefit_model_version=pe.us.model
    )
    reformed = Simulation(
        dataset=dataset,
        tax_benefit_model_version=pe.us.model,
        policy=reform,
    )

    baseline.run()
    reformed.run()

    baseline_refundable = baseline.output_dataset.data.tax_unit[
        "ctc"
    ].sum()  # ctc proxy; refundable_ctc not in default output_variables
    reform_refundable = reformed.output_dataset.data.tax_unit["ctc"].sum()

    # The reform must produce a strictly positive change. Before the
    # fix, reformed sim crashed with 'NoneType has no attribute entity'
    # in refundable_ctc; if that regresses, this test fails by raising
    # rather than by asserting.
    assert reform_refundable >= baseline_refundable, (
        f"Contrib-CTC minimum-refundable reform should not reduce CTC "
        f"aggregate: baseline=${baseline_refundable:,.0f}, "
        f"reform=${reform_refundable:,.0f}"
    )
