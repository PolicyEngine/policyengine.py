from policyengine import Simulation
from microdf import MicroSeries
import numpy as np


def labor_supply(simulation: Simulation) -> dict:
    baseline_labor_supply = simulation.calculate(
        "macro/baseline/household/labor_supply", include_arrays=True
    )
    reform_labor_supply = simulation.calculate(
        "macro/reform/household/labor_supply", include_arrays=True
    )
    baseline_finance = simulation.calculate(
        "macro/baseline/household/finance", include_arrays=True
    )
    baseline_demographics = simulation.calculate(
        "macro/baseline/household/demographics", include_arrays=True
    )

    substitution_lsr = (
        reform_labor_supply["substitution_lsr"]
        - baseline_labor_supply["substitution_lsr"]
    )
    income_lsr = (
        reform_labor_supply["income_lsr"] - baseline_labor_supply["income_lsr"]
    )
    total_change = substitution_lsr + income_lsr

    substitution_lsr_hh = np.array(
        reform_labor_supply["substitution_lsr_hh"]
    ) - np.array(baseline_labor_supply["substitution_lsr_hh"])
    income_lsr_hh = np.array(reform_labor_supply["income_lsr_hh"]) - np.array(
        baseline_labor_supply["income_lsr_hh"]
    )
    decile = np.array(baseline_finance["household_income_decile"])
    household_weight = baseline_demographics["household_weight"]

    total_lsr_hh = substitution_lsr_hh + income_lsr_hh

    emp_income = MicroSeries(
        baseline_finance["employment_income_hh"],
        weights=household_weight,
    )
    self_emp_income = MicroSeries(
        baseline_finance["self_employment_income_hh"],
        weights=household_weight,
    )
    earnings = emp_income + self_emp_income
    original_earnings = earnings - total_lsr_hh
    substitution_lsr_hh = MicroSeries(
        substitution_lsr_hh, weights=household_weight
    )
    income_lsr_hh = MicroSeries(income_lsr_hh, weights=household_weight)

    decile_avg = dict(
        income=income_lsr_hh.groupby(decile).mean().to_dict(),
        substitution=substitution_lsr_hh.groupby(decile).mean().to_dict(),
    )
    decile_rel = dict(
        income=(
            income_lsr_hh.groupby(decile).sum()
            / original_earnings.groupby(decile).sum()
        ).to_dict(),
        substitution=(
            substitution_lsr_hh.groupby(decile).sum()
            / original_earnings.groupby(decile).sum()
        ).to_dict(),
    )

    relative_lsr = dict(
        income=(income_lsr_hh.sum() / original_earnings.sum()),
        substitution=(substitution_lsr_hh.sum() / original_earnings.sum()),
    )

    decile_rel["income"] = {
        int(k): v for k, v in decile_rel["income"].items() if k > 0
    }
    decile_rel["substitution"] = {
        int(k): v for k, v in decile_rel["substitution"].items() if k > 0
    }

    hours = dict(
        baseline=baseline_labor_supply["weekly_hours"],
        reform=reform_labor_supply["weekly_hours"],
        change=reform_labor_supply["weekly_hours"]
        - baseline_labor_supply["weekly_hours"],
        income_effect=reform_labor_supply["weekly_hours_income_effect"]
        - baseline_labor_supply["weekly_hours_income_effect"],
        substitution_effect=reform_labor_supply[
            "weekly_hours_substitution_effect"
        ]
        - baseline_labor_supply["weekly_hours_substitution_effect"],
    )

    rel_labor_supply_change = (
        total_change / baseline_labor_supply["total_earnings"]
    )
    ftes_baseline = baseline_labor_supply["total_workers"]
    ftes_reform = baseline_labor_supply["total_workers"] * (
        1 + rel_labor_supply_change
    )
    earnings_change = (
        reform_labor_supply["total_earnings"]
        - baseline_labor_supply["total_earnings"]
    )

    return dict(
        earnings=dict(
            baseline=baseline_labor_supply["total_earnings"],
            reform=reform_labor_supply["total_earnings"],
            change=earnings_change,
            rel_change=earnings_change
            / baseline_labor_supply["total_earnings"],
        ),
        fte=dict(
            baseline=ftes_baseline,
            reform=ftes_reform,
            change=ftes_reform - ftes_baseline,
            rel_change=ftes_reform / ftes_baseline - 1,
        ),
        substitution_lsr=substitution_lsr,
        income_lsr=income_lsr,
        relative_lsr=relative_lsr,
        decile=dict(
            average=decile_avg,
            relative=decile_rel,
        ),
        hours=hours,
    )
