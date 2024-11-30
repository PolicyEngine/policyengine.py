from policyengine import Simulation


def inequality(simulation: Simulation) -> dict:
    personal_hh_equiv_income = simulation.selected.calculate(
        "equiv_household_net_income"
    )
    personal_hh_equiv_income[personal_hh_equiv_income < 0] = 0
    household_count_people = simulation.selected.calculate(
        "household_count_people"
    ).values
    personal_hh_equiv_income.weights *= household_count_people
    gini = personal_hh_equiv_income.gini()
    in_top_10_pct = personal_hh_equiv_income.decile_rank() == 10
    in_top_1_pct = personal_hh_equiv_income.percentile_rank() == 100

    personal_hh_equiv_income.weights /= household_count_people

    top_10_share = (
        personal_hh_equiv_income[in_top_10_pct].sum()
        / personal_hh_equiv_income.sum()
    )
    top_1_share = (
        personal_hh_equiv_income[in_top_1_pct].sum()
        / personal_hh_equiv_income.sum()
    )

    return {
        "gini": gini,
        "top_10_percent_share": top_10_share,
        "top_1_percent_share": top_1_share,
    }
