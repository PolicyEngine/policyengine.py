"""Regression: ``Simulation(extra_variables={...})`` must add the
named variables to ``output_dataset``.

The field lives on the base :class:`~policyengine.core.Simulation`
but the US and UK microsim ``run()`` paths historically only iterated
``self.entity_variables`` (the country model's bundled defaults),
silently dropping anything the caller added via ``extra_variables``.

The fix adds a shared :meth:`resolve_entity_variables` on
:class:`~policyengine.tax_benefit_models.common.MicrosimulationModelVersion`
that merges the two and validates unknown entity/variable names with
close-match suggestions. Both country runs now route through it.
"""

from __future__ import annotations

import pandas as pd
import pytest
from microdf import MicroDataFrame

# --- Fixtures --------------------------------------------------------


def _us_fixture_dataset(tmp_path):
    from policyengine.tax_benefit_models.us.datasets import (
        PolicyEngineUSDataset,
        USYearData,
    )

    person = MicroDataFrame(
        pd.DataFrame(
            {
                "person_id": [1, 2, 3],
                "household_id": [1, 1, 1],
                "tax_unit_id": [1, 1, 1],
                "spm_unit_id": [1, 1, 1],
                "family_id": [1, 1, 1],
                "marital_unit_id": [1, 2, 3],
                "person_weight": [1_000.0] * 3,
                "age": [35, 5, 8],
                "employment_income": [50_000, 0, 0],
            }
        ),
        weights="person_weight",
    )
    household = MicroDataFrame(
        pd.DataFrame(
            {
                "household_id": [1],
                "state_code": ["CA"],
                "household_weight": [1_000.0],
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
        id="test-extra-vars",
        name="extra_variables fixture",
        description="Small dataset for extra_variables regression tests",
        filepath=str(tmp_path / "test.h5"),
        year=2026,
        data=USYearData(
            person=person,
            tax_unit=_simple("tax_unit_id", 1, "tax_unit_weight"),
            spm_unit=_simple("spm_unit_id", 1, "spm_unit_weight"),
            family=_simple("family_id", 1, "family_weight"),
            marital_unit=_simple("marital_unit_id", 3, "marital_unit_weight"),
            household=household,
        ),
    )


# --- US: positive path -----------------------------------------------


def test__us_extra_variables_appear_on_output_dataset(tmp_path) -> None:
    """Issue #303: ``Simulation(extra_variables={"household": [...]})``
    must actually populate those columns on ``output_dataset``.
    """
    pytest.importorskip("policyengine_us")
    import policyengine as pe
    from policyengine.core import Simulation

    dataset = _us_fixture_dataset(tmp_path)
    sim = Simulation(
        dataset=dataset,
        tax_benefit_model_version=pe.us.model,
        extra_variables={
            "household": ["household_market_income"],
            "tax_unit": ["adjusted_gross_income"],
        },
    )
    sim.run()

    household_cols = sim.output_dataset.data.household.columns
    tax_unit_cols = sim.output_dataset.data.tax_unit.columns
    # ``household_market_income`` is already in defaults — confirm it
    # stays present (no duplicate-column collision) AND the new
    # ``adjusted_gross_income`` appears on ``tax_unit``.
    assert "household_market_income" in household_cols
    assert "adjusted_gross_income" in tax_unit_cols, (
        "extra_variables['tax_unit'] entry missing from output_dataset"
    )


# --- UK: resolver directly (full UK microsim fixture is heavier
#   than needed to test the shared helper) --------------------------


def test__uk_resolve_entity_variables_merges_extras() -> None:
    """``resolve_entity_variables`` on the UK model must merge extras
    into defaults the same way US does. Exercising the method directly
    is sufficient — the UK ``run()`` calls it via the exact line that
    US does, so identical behaviour there is a one-character diff.
    """
    pytest.importorskip("policyengine_uk")
    import policyengine as pe
    from policyengine.core import Simulation

    fake_sim = Simulation.model_construct(
        extra_variables={"person": ["adjusted_net_income"]}
    )
    resolved = pe.uk.model.resolve_entity_variables(fake_sim)
    assert "adjusted_net_income" in resolved["person"]
    # Non-targeted entities unchanged.
    assert resolved["benunit"] == list(pe.uk.model.entity_variables["benunit"])


def test__uk_resolve_entity_variables_raises_on_unknown_variable() -> None:
    pytest.importorskip("policyengine_uk")
    import policyengine as pe
    from policyengine.core import Simulation

    fake_sim = Simulation.model_construct(
        extra_variables={"person": ["nonexistent_variable_xyz"]}
    )
    with pytest.raises(ValueError) as exc:
        pe.uk.model.resolve_entity_variables(fake_sim)
    assert "nonexistent_variable_xyz" in str(exc.value)


# --- Negative path: validation ---------------------------------------


def test__unknown_entity_key_raises_with_suggestion(tmp_path) -> None:
    """An unknown entity key in ``extra_variables`` must raise with a
    close-match suggestion at run time (before the bare ``Microsimulation``
    call starts spending minutes of compute).
    """
    pytest.importorskip("policyengine_us")
    import policyengine as pe
    from policyengine.core import Simulation

    dataset = _us_fixture_dataset(tmp_path)
    sim = Simulation(
        dataset=dataset,
        tax_benefit_model_version=pe.us.model,
        # ``tax_units`` (plural) is a likely agent typo for ``tax_unit``.
        extra_variables={"tax_units": ["income_tax"]},
    )
    with pytest.raises(ValueError) as exc:
        sim.run()
    message = str(exc.value)
    assert "tax_units" in message
    assert "tax_unit" in message  # close-match suggestion


def test__unknown_variable_name_raises_with_suggestion(tmp_path) -> None:
    """Variable-name typos must raise with a close-match suggestion."""
    pytest.importorskip("policyengine_us")
    import policyengine as pe
    from policyengine.core import Simulation

    dataset = _us_fixture_dataset(tmp_path)
    sim = Simulation(
        dataset=dataset,
        tax_benefit_model_version=pe.us.model,
        extra_variables={"tax_unit": ["adjusted_gross_incme"]},  # typo
    )
    with pytest.raises(ValueError) as exc:
        sim.run()
    message = str(exc.value)
    assert "adjusted_gross_incme" in message
    assert "adjusted_gross_income" in message  # suggested correction


# --- Resolver behavior: deduplication --------------------------------


def test__resolve_entity_variables_dedupes_when_extra_overlaps_default(
    tmp_path,
) -> None:
    """Passing a variable that's already in the defaults must not
    produce a duplicate column or fail.
    """
    pytest.importorskip("policyengine_us")
    import policyengine as pe
    from policyengine.core import Simulation

    dataset = _us_fixture_dataset(tmp_path)
    sim = Simulation(
        dataset=dataset,
        tax_benefit_model_version=pe.us.model,
        # ``income_tax`` is already a default on ``tax_unit``.
        extra_variables={"tax_unit": ["income_tax"]},
    )
    sim.run()

    tax_unit_cols = list(sim.output_dataset.data.tax_unit.columns)
    assert tax_unit_cols.count("income_tax") == 1, (
        f"income_tax duplicated after extra_variables merge: {tax_unit_cols}"
    )
