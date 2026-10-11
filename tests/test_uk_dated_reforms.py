"""UK household reform dates share the wrapper policy's effective-date reading."""

import pytest

import policyengine as pe
import policyengine.tax_benefit_models.uk.household as uk_household

INCOME_TAX_RATE = "gov.hmrc.income_tax.rates.uk[0].rate"


@pytest.mark.parametrize(
    ("schedule", "expected"),
    [
        (0.21, {"2027-01-01.2100-12-31": 0.21}),
        ({"2027-04-06": 0.21}, {"2027-04-06.2100-12-31": 0.21}),
        (
            {"2027-04-06.2028-04-05": 0.21},
            {"2027-04-06.2028-04-05": 0.21},
        ),
        (
            {"2028-04-06": 0.22, "2027-04-06": 0.21},
            {
                "2028-04-06.2100-12-31": 0.22,
                "2027-04-06.2028-04-05": 0.21,
            },
        ),
    ],
    ids=["scalar", "effective-date", "interval", "reverse-date-schedule"],
)
def test_household_constructor_receives_inclusive_ranges(
    monkeypatch, schedule, expected
):
    captured = {}

    class CapturingSimulation:
        def __init__(self, *, situation, reform):
            captured["reform"] = reform

        def calculate(self, variable, period, map_to):
            return [0.0]

    monkeypatch.setattr("policyengine_uk.Simulation", CapturingSimulation)
    monkeypatch.setattr(
        uk_household,
        "_default_output_columns",
        lambda extra: {"person": ["income_tax"]},
    )

    pe.uk.calculate_household(
        people=[{"age": 40, "employment_income": 30_000}],
        year=2027,
        reform={INCOME_TAX_RATE: schedule},
    )

    assert captured["reform"] == {INCOME_TAX_RATE: expected}
    assert all("." in key for key in captured["reform"][INCOME_TAX_RATE])


def test_household_reform_keeps_unknown_path_validation(monkeypatch):
    def unexpected_simulation(**kwargs):
        pytest.fail("An invalid reform should fail before simulation construction")

    monkeypatch.setattr("policyengine_uk.Simulation", unexpected_simulation)

    with pytest.raises(ValueError, match="did you mean"):
        pe.uk.calculate_household(
            people=[{"age": 40}],
            year=2027,
            reform={"gov.hmrc.income_tax.rates.uk[0].rat": 0.21},
        )


def test_household_april_effective_date_changes_fiscal_year_income_tax():
    pytest.importorskip("policyengine_uk.utils.dated_reforms")

    inputs = {"people": [{"age": 40, "employment_income": 30_000}], "year": 2027}
    baseline = pe.uk.calculate_household(**inputs)
    reformed = pe.uk.calculate_household(
        **inputs,
        reform={INCOME_TAX_RATE: {"2027-04-06": 0.21}},
    )

    assert reformed.person[0].income_tax - baseline.person[0].income_tax == pytest.approx(
        174.30, abs=0.01
    )


@pytest.mark.parametrize(("year", "expected_change"), [(2027, 174.30), (2028, 0.0)])
def test_household_interval_reform_expires_after_fiscal_year(year, expected_change):
    pytest.importorskip("policyengine_uk.utils.dated_reforms")

    inputs = {"people": [{"age": 40, "employment_income": 30_000}], "year": year}
    baseline = pe.uk.calculate_household(**inputs)
    reformed = pe.uk.calculate_household(
        **inputs,
        reform={INCOME_TAX_RATE: {"2027-04-06.2028-04-05": 0.21}},
    )

    assert reformed.person[0].income_tax - baseline.person[0].income_tax == pytest.approx(
        expected_change, abs=0.01
    )
