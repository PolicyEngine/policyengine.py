macro_single = Simulation(
    country="uk",
    type="forecast/macro",
    data="enhanced_frs_2022_23",
    year=2025,
    reform={
        "reform": {
            "gov.hmrc.income_tax.allowances.personal_allowance.amount": 0,
        },
    }
)

macro_single.calculate("budget/revenue") # -> £700 billion

macro = Simulation(
    country="uk",
    type="macro",
    data="enhanced_frs_2022_23",
    year=2025,
    reform={
        "reform": {
            "gov.hmrc.income_tax.allowances.personal_allowance.amount": 0,
        },
    }
)

macro.calculate("budget/revenue_impact") # -> +£100 billion

micro = Simulation(
    country="uk",
    type="household",
    data={
        "employment_income": {
            2025: 30_000,
        }
    },
    year=2025,
    reform={
        "reform": {
            "gov.hmrc.income_tax.allowances.personal_allowance.amount": 0,
        },
    },
)

micro.calculate("budget/income_impact") # -> -£5,000
micro.calculate("budget/net_income_change/chart") # plotly.graph_objects.Figure

