"""policyengine.py adopts policyengine-uk's default capital gains response (#602).

The pinned policyengine-uk realises gains at a retention-rate elasticity of 1
when a reform sets none (policyengine-uk#2396). These tests check that:

- the pinned model's defaults are the central case;
- a CGT reform with no elasticity set equals one with an explicit
  retention-rate elasticity of 1 through all three entry points (population,
  household and managed), with relief gains at the same elasticity;
- an MTR elasticity set alone applies on its own, with a warning, and the
  record says so;
- an unreformed run is unchanged by the default;
- each entry point records the resolved assumption.

``test_uk_cgt_responses.py`` covers explicit settings, precedence, conflicts
and the record's storage; these tests hold only with the pinned default.
"""

from __future__ import annotations

import math
import warnings

import pandas as pd
import pytest

pytest.importorskip("policyengine_uk")
_capital_gains = pytest.importorskip("policyengine_uk.utils.capital_gains")
if not hasattr(_capital_gains, "capital_gains_response_assumption"):
    # Until the pin reaches the policyengine-uk release with the default
    # (policyengine-uk#2396). The commit that moves the pin removes this
    # guard, so from then on a pin without the default fails here.
    pytest.skip(
        "needs the policyengine-uk release with the default capital gains "
        "response (policyengine-uk#2396)",
        allow_module_level=True,
    )

from policyengine_uk.utils.capital_gains import (  # noqa: E402
    CapitalGainsResponseWarning,
)

import policyengine as pe  # noqa: E402
from policyengine.tax_benefit_models.uk import (  # noqa: E402
    capital_gains_responses as records,
)
from tests.test_uk_cgt_responses import (  # noqa: E402
    GAINS_VARIABLES,
    MIXED_RATIO,
    RATE_RISE,
    RATIO,
    YEAR,
    factors,
    person,
    run,
    settings,
)

CENTRAL = {"elasticity": 1.0, "mtr_elasticity": 0.0, "separate_badr_elasticity": False}


def test_the_pinned_model_defaults_to_the_central_case():
    from policyengine_uk.tax_benefit_system import processed_parameters

    responses = processed_parameters().gov.simulation.capital_gains_responses
    instant = f"{YEAR}-01-01"

    assert responses.elasticity(instant) == 1.0
    assert responses.mtr_elasticity(instant) == 0
    assert not responses.separate_badr_elasticity(instant)


def test_no_elasticity_means_the_central_response_on_the_population_route():
    default = run(policy=RATE_RISE)
    explicit = run(policy=RATE_RISE, dynamic=settings(**CENTRAL))

    for variable in GAINS_VARIABLES["person"]:
        assert person(default, variable) == person(explicit, variable), variable
    assert factors(default)[0] == pytest.approx(RATIO, abs=1e-5)
    # Relief gains take the same elasticity, against the share-weighted rate.
    relief_response = person(default, "capital_gains_badr_behavioural_response")[1]
    assert 1 + relief_response / 20_000 == pytest.approx(MIXED_RATIO, abs=1e-4)
    assert factors(default)[1] == pytest.approx(MIXED_RATIO, abs=1e-4)

    resolved = default.output_dataset.metadata[records.RECORD_KEY]["resolved"]
    assert resolved["convention"] == "retention"
    assert (resolved["elasticity"], resolved["badr_elasticity"]) == (1.0, 1.0)
    assert set(resolved["sources"].values()) == {"default"}


def test_no_elasticity_means_the_central_response_on_the_household_route():
    people = [{"age": 45, "employment_income": 80_000, "capital_gains": 50_000}]

    def gains(reform):
        result = pe.uk.calculate_household(
            people=people, year=YEAR, reform=reform, extra_variables=["capital_gains"]
        )
        return result, result.person[0]["capital_gains"]

    default, default_gains = gains(RATE_RISE)
    _, explicit_gains = gains({**RATE_RISE, **settings(**CENTRAL)})

    assert default_gains == explicit_gains
    assert default_gains == pytest.approx(50_000 * RATIO, abs=0.5)
    resolved = default["provenance"][records.RECORD_KEY]["resolved"]
    assert resolved["convention"] == "retention"


def _raw_tables() -> dict[str, pd.DataFrame]:
    ids = [1, 2]
    return {
        "person": pd.DataFrame(
            {
                "person_id": ids,
                "person_benunit_id": ids,
                "person_household_id": ids,
                "age": [45, 45],
                "employment_income": [80_000.0, 30_000.0],
                "capital_gains": [50_000.0, 0.0],
            }
        ),
        "benunit": pd.DataFrame({"benunit_id": ids}),
        "household": pd.DataFrame(
            {
                "household_id": ids,
                "household_weight": [1.0, 1.0],
                "region": ["LONDON", "LONDON"],
                "tenure_type": ["OWNED_OUTRIGHT", "OWNED_OUTRIGHT"],
                "council_tax": [0.0, 0.0],
                "rent": [0.0, 0.0],
            }
        ),
    }


def test_no_elasticity_means_the_central_response_on_the_managed_route(tmp_path):
    from policyengine_uk.data import UKSingleYearDataset

    path = tmp_path / "cgt.h5"
    UKSingleYearDataset(**_raw_tables(), fiscal_year=YEAR).save(str(path))

    def managed(reform):
        return pe.uk.managed_microsimulation(
            dataset=str(path), allow_unmanaged=True, reform=reform
        )

    default = managed(RATE_RISE)
    explicit = managed({**RATE_RISE, **settings(**CENTRAL)})

    assert list(default.calculate("capital_gains", YEAR)) == list(
        explicit.calculate("capital_gains", YEAR)
    )
    assert default.calculate("capital_gains", YEAR).values[0] == pytest.approx(
        50_000 * RATIO, abs=0.5
    )
    record = default.policyengine_bundle[records.RECORD_KEY][str(YEAR)]
    assert record["resolved"]["convention"] == "retention"
    assert record["request"] is None


def test_an_mtr_elasticity_alone_applies_with_a_warning():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        legacy = run(policy=RATE_RISE, dynamic=settings(mtr_elasticity=-0.7))

    assert [warning.category for warning in caught].count(
        CapitalGainsResponseWarning
    ) == 1
    # (45% / 24%) ** -0.7, not the retention-rate 0.55 / 0.76.
    assert factors(legacy)[0] == pytest.approx(
        math.exp(-0.7 * math.log(0.45 / 0.24)), abs=1e-5
    )
    resolved = legacy.output_dataset.metadata[records.RECORD_KEY]["resolved"]
    assert resolved["convention"] == "mtr"
    assert resolved["mtr_auto_resolved"]
    assert len(resolved["warnings"]) == 1


def test_an_unreformed_run_is_unchanged_by_the_default():
    default = run()
    static = run(
        dynamic=settings(elasticity=0, mtr_elasticity=0, separate_badr_elasticity=False)
    )

    for entity in ("person", "benunit", "household"):
        default_table = getattr(default.output_dataset.data, entity)
        static_table = getattr(static.output_dataset.data, entity)
        for column in default_table.columns:
            assert list(default_table[column]) == list(static_table[column]), (
                entity,
                column,
            )
