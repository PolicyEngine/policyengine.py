"""``Simulation(policy={...})`` and ``Simulation(dynamic={...})``.

These tests pin the v4 contract: the same flat reform dict shape that
``pe.{uk,us}.calculate_household(reform=...)`` accepts is also accepted
by ``Simulation(policy=...)`` / ``Simulation(dynamic=...)``, and is
compiled into the full ``Policy`` / ``Dynamic`` object on construction.
We exercise only the coercion path — no country microsim is run — so
the tests are fast and don't need HF credentials.
"""

from __future__ import annotations

import pytest

pytest.importorskip("policyengine_us")

import policyengine as pe
from policyengine.core import Dynamic, Policy, Simulation
from tests.fixtures.filtering_fixtures import us_test_dataset  # noqa: F401


@pytest.fixture
def tiny_dataset(us_test_dataset):
    """In-memory US dataset pinned to 2026. Simulation is never .run() in these tests."""
    us_test_dataset.year = 2026
    return us_test_dataset


class TestDictPolicyCoercion:
    def test__dict_policy__then_compiled_to_policy_with_parameter_values(self, tiny_dataset):
        sim = Simulation(
            dataset=tiny_dataset,
            tax_benefit_model_version=pe.us.model,
            policy={"gov.irs.credits.ctc.amount.base[0].amount": 3_000},
        )
        assert isinstance(sim.policy, Policy)
        assert len(sim.policy.parameter_values) == 1

        pv = sim.policy.parameter_values[0]
        assert pv.parameter.name == "gov.irs.credits.ctc.amount.base[0].amount"
        assert pv.value == 3_000
        # Scalar reforms default the effective date to {year}-01-01.
        assert pv.start_date.year == 2026
        assert pv.start_date.month == 1

    def test__dict_policy_with_effective_date__then_start_date_matches(self, tiny_dataset):
        sim = Simulation(
            dataset=tiny_dataset,
            tax_benefit_model_version=pe.us.model,
            policy={
                "gov.irs.credits.ctc.amount.base[0].amount": {
                    "2026-07-01": 2_500,
                    "2027-01-01": 3_000,
                },
            },
        )
        assert isinstance(sim.policy, Policy)
        assert len(sim.policy.parameter_values) == 2
        starts = sorted(pv.start_date for pv in sim.policy.parameter_values)
        assert [d.strftime("%Y-%m-%d") for d in starts] == [
            "2026-07-01",
            "2027-01-01",
        ]

    def test__unknown_parameter_path__raises_with_suggestion(self, tiny_dataset):
        with pytest.raises(ValueError) as exc:
            Simulation(
                dataset=tiny_dataset,
                tax_benefit_model_version=pe.us.model,
                policy={
                    # plausible typo of the real path
                    "gov.irs.credits.ctc.amount.base[0].amont": 3_000,
                },
            )
        assert "not defined" in str(exc.value)
        assert "did you mean" in str(exc.value)

    def test__existing_policy_object_passes_through_unchanged(self, tiny_dataset):
        import datetime

        from policyengine.core import Parameter, ParameterValue

        existing = Policy(
            name="Existing",
            parameter_values=[
                ParameterValue(
                    parameter=Parameter(
                        name="gov.irs.credits.ctc.amount.base[0].amount",
                        tax_benefit_model_version=pe.us.model,
                        data_type=float,
                    ),
                    start_date=datetime.datetime(2026, 1, 1),
                    end_date=None,
                    value=2_750,
                )
            ],
        )
        sim = Simulation(
            dataset=tiny_dataset,
            tax_benefit_model_version=pe.us.model,
            policy=existing,
        )
        assert sim.policy is existing

    def test__dict_without_model_version__raises(self, tiny_dataset):
        with pytest.raises(ValueError) as exc:
            Simulation(
                dataset=tiny_dataset,
                policy={"gov.irs.credits.ctc.amount.base[0].amount": 3_000},
            )
        assert "tax_benefit_model_version" in str(exc.value)


class TestDictDynamicCoercion:
    def test__dict_dynamic__then_compiled_to_dynamic(self, tiny_dataset):
        sim = Simulation(
            dataset=tiny_dataset,
            tax_benefit_model_version=pe.us.model,
            dynamic={"gov.irs.credits.ctc.amount.base[0].amount": 2_800},
        )
        assert isinstance(sim.dynamic, Dynamic)
        assert len(sim.dynamic.parameter_values) == 1
        assert sim.dynamic.parameter_values[0].value == 2_800
