from policyengine import Simulation
from microdf import MicroSeries
import numpy as np


def labor_supply_response(simulation: Simulation) -> dict:
    baseline = simulation.calculate("macro/baseline")
    reform = simulation.calculate("macro/reform")

    substitution_lsr = (
        reform["household"]["labor_supply"]["substitution_lsr"]
        - baseline["household"]["labor_supply"]["substitution_lsr"]
    )
    income_lsr = (
        reform["household"]["labor_supply"]["income_lsr"]
        - baseline["household"]["labor_supply"]["income_lsr"]
    )
    total_change = substitution_lsr + income_lsr
    revenue_change = (
        reform["household"]["labor_supply"]["budgetary_impact_lsr"]
        - baseline["household"]["labor_supply"]["budgetary_impact_lsr"]
    )

    substitution_lsr_hh = np.array(
        reform["household"]["labor_supply"]["substitution_lsr_hh"]
    ) - np.array(baseline["household"]["labor_supply"]["substitution_lsr_hh"])
    income_lsr_hh = np.array(
        reform["household"]["labor_supply"]["income_lsr_hh"]
    ) - np.array(baseline["household"]["labor_supply"]["income_lsr_hh"])
    decile = np.array(
        baseline["household"]["finance"]["household_income_decile"]
    )
    household_weight = baseline["household"]["demographics"][
        "household_weight"
    ]

    total_lsr_hh = substitution_lsr_hh + income_lsr_hh

    emp_income = MicroSeries(
        baseline["household"]["finance"]["employment_income_hh"],
        weights=household_weight,
    )
    self_emp_income = MicroSeries(
        baseline["household"]["finance"]["self_employment_income_hh"],
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
        baseline=baseline["household"]["labor_supply"]["weekly_hours"],
        reform=reform["household"]["labor_supply"]["weekly_hours"],
        change=reform["household"]["labor_supply"]["weekly_hours"]
        - baseline["household"]["labor_supply"]["weekly_hours"],
        income_effect=reform["household"]["labor_supply"][
            "weekly_hours_income_effect"
        ]
        - baseline["household"]["labor_supply"]["weekly_hours_income_effect"],
        substitution_effect=reform["household"]["labor_supply"][
            "weekly_hours_substitution_effect"
        ]
        - baseline["household"]["labor_supply"][
            "weekly_hours_substitution_effect"
        ],
    )

    return dict(
        substitution_lsr=substitution_lsr,
        income_lsr=income_lsr,
        relative_lsr=relative_lsr,
        total_change=total_change,
        revenue_change=revenue_change,
        decile=dict(
            average=decile_avg,
            relative=decile_rel,
        ),
        hours=hours,
    )
