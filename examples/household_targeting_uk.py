"""Example: replicate a published household targeting analysis on UK microdata.

Many published analyses define eligibility with a rule that is not a
PolicyEngine variable. This script works through one: the energy bill discount
options in the Resolution Foundation's "Billing me softly" (August 2026,
https://www.resolutionfoundation.org/publications/billing-me-softly/), which
tests the highest individual taxable income in a household against GBP 24,000,
and passports households that report a means-tested benefit.

It shows the steps such a replication needs:

1. Load the certified UK microdata with ``managed_microsimulation``.
2. Read person, benefit unit and household arrays with their weights.
3. Aggregate a person variable to the household (here, the maximum).
4. Join benefit units to households through the person-level id columns.
5. Choose between benefit receipt reported in the survey and modelled
   entitlement (``*_reported`` versus the modelled benefit variables).
6. Rank households into income deciles on the basis the publication uses.
7. Turn eligibility into counts, shares and per-household amounts.

The UK data is private. Set HUGGING_FACE_TOKEN to a token from a Hugging Face
account with access (see docs/microsim.md), so this script does not run in CI.

A full implementation of these options as a policyengine-uk reform, with the
published figures beside PolicyEngine's, is in
https://github.com/PolicyEngine/uk-energy-reforms.

Run: python examples/household_targeting_uk.py
"""

import numpy as np
import pandas as pd

import policyengine as pe

YEAR = 2024  # fiscal year 2024-25, the survey year of the publication
INDIVIDUAL_THRESHOLD = 24_000
LOWER_TIER_THRESHOLD = 18_000
HOUSEHOLD_THRESHOLD = 30_000
BUDGET = 2e9

# The Warm Home Discount passporting benefits.
PASSPORTING_BENEFITS = [
    "universal_credit",
    "pension_credit",
    "housing_benefit",
    "esa_income",
    "jsa_income",
    "income_support",
]


def values(sim, variable: str) -> np.ndarray:
    """Return a variable's values as a plain array on its own entity.

    ``sim.calculate`` returns a weighted MicroSeries. Take ``.values`` only
    when you apply the weights yourself, as this script does.
    """
    return np.asarray(sim.calculate(variable, YEAR).values)


def household_max(person_values, person_household_id, household_id):
    """Maximum of a person-level value within each household."""
    by_household = pd.Series(person_values).groupby(person_household_id).max()
    return by_household.reindex(household_id).to_numpy()


def household_any(person_values, person_household_id, household_id):
    """Whether any person in each household has a positive value."""
    by_household = pd.Series(person_values > 0).groupby(person_household_id).any()
    return by_household.reindex(household_id).to_numpy(dtype=bool)


def weighted_decile(income, weight):
    """Decile (1 to 10) of each row, with boundaries set by ``weight``."""
    order = np.argsort(income, kind="stable")
    cumulative = np.cumsum(weight[order])
    decile = np.empty(len(income))
    decile[order] = np.ceil(10 * cumulative / cumulative[-1])
    return np.clip(decile, 1, 10).astype(int)


def main():
    # The certified default dataset, pinned by the policyengine.py release.
    sim = pe.uk.managed_microsimulation()

    # Households. The publication covers Great Britain.
    household_id = values(sim, "household_id")
    household_weight = values(sim, "household_weight")
    in_gb = values(sim, "country").astype(str) != "NORTHERN_IRELAND"
    weight = household_weight * in_gb

    # Persons. person_household_id links each person to a household.
    person_household_id = values(sim, "person_household_id")
    person_benunit_id = values(sim, "person_benunit_id")
    taxable_income = values(sim, "total_income")

    # 3. Highest individual income in the household.
    highest_income = household_max(taxable_income, person_household_id, household_id)
    individual_test = highest_income < INDIVIDUAL_THRESHOLD

    # The household option: total taxable income, equivalised. policyengine-uk's
    # household_equivalisation_bhc is the modified OECD scale rescaled so that a
    # couple is 1.0, as in HBAI. Check which form a publication uses: on the
    # unrescaled form (single adult 1.0) the same threshold passes far more
    # households.
    household_income = (
        pd.Series(taxable_income)
        .groupby(person_household_id)
        .sum()
        .reindex(household_id)
        .to_numpy()
    )
    equivalised = household_income / values(sim, "household_equivalisation_bhc")
    household_test = equivalised < HOUSEHOLD_THRESHOLD

    # 5. Passporting. The *_reported variables hold receipt reported in the
    # survey; the modelled variables hold entitlement after take-up. Published
    # analyses of survey data usually mean reported receipt.
    reported = np.zeros(len(person_household_id))
    for benefit in PASSPORTING_BENEFITS:
        reported += values(sim, f"{benefit}_reported")
    passported_reported = household_any(reported, person_household_id, household_id)

    modelled = sum(
        np.asarray(sim.calculate(benefit, YEAR, map_to="household").values)
        for benefit in PASSPORTING_BENEFITS
    )
    passported_modelled = modelled > 0

    # 6. Deciles. household_income_decile ranks people by equivalised income
    # before housing costs. HBAI headline distributions, and many publications,
    # use income after housing costs, so build that ranking explicitly and say
    # whether households or people set the boundaries.
    income_ahc = values(sim, "equiv_hbai_household_net_income_ahc")
    people = values(sim, "household_count_people")
    decile_ahc = weighted_decile(income_ahc, weight * people)
    lowest_four = decile_ahc <= 4

    def share(mask, among=None):
        among = np.ones(len(mask), dtype=bool) if among is None else among
        return (weight * mask * among).sum() / (weight * among).sum()

    print(f"GB households: {weight.sum() / 1e6:.1f}m")
    print(f"Highest individual income below £24,000: {share(individual_test):.0%}")
    print(
        "  share of the four lowest AHC deciles: "
        f"{share(individual_test, lowest_four):.0%}"
    )
    print(f"Equivalised household income below £30,000: {share(household_test):.0%}")
    print(f"Passported, reported receipt: {share(passported_reported):.0%}")
    print(f"Passported, modelled entitlement: {share(passported_modelled):.0%}")

    # 7. A fixed budget shared among eligible households.
    eligible = individual_test | passported_reported
    recipients = (weight * eligible).sum()
    print(
        f"£{BUDGET / 1e9:.0f}bn among {recipients / 1e6:.1f}m eligible households: "
        f"£{BUDGET / recipients:.0f} each"
    )
    upper = (highest_income < LOWER_TIER_THRESHOLD) | passported_reported
    lower = individual_test & ~upper
    cost = (weight * (220 * upper + 85 * lower)).sum()
    print(f"Two tiers of £220 and £85 cost £{cost / 1e9:.2f}bn")

    # 4. Benefit units to households. Join through the person-level ids.
    # Do not use sim.calculate("household_id", map_to="benunit"): mapping from a
    # larger entity to a smaller one shares the value among the smaller units,
    # which is right for amounts and wrong for ids and flags.
    benunit_id = values(sim, "benunit_id")
    benunit_household = (
        pd.Series(person_household_id)
        .groupby(person_benunit_id)
        .first()
        .reindex(benunit_id)
        .to_numpy()
    )

    def by_benunit(household_values):
        return (
            pd.Series(household_values, index=household_id)
            .reindex(benunit_household)
            .to_numpy()
        )

    benunit_weight = values(sim, "benunit_weight") * by_benunit(in_gb)
    couple_with_children = values(sim, "is_couple").astype(bool) & (
        values(sim, "benunit_count_children") > 0
    )
    loses = (
        couple_with_children
        & by_benunit(household_test).astype(bool)
        & ~by_benunit(individual_test).astype(bool)
    )
    print(
        "Couples with children passing the household test but not the "
        f"individual one: {(benunit_weight * loses).sum() / 1e3:,.0f}k"
    )


if __name__ == "__main__":
    main()
