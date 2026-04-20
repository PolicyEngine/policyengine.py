---
title: "Visualisation"
---

PolicyEngine outputs come with `.to_plotly()` helpers for the most common chart shapes. These produce publication-ready Plotly figures with PolicyEngine's color palette — override or customize as you would any Plotly figure.

## Decile impact

```python
from policyengine.outputs import DecileImpact

impact = DecileImpact().compute(baseline, reformed)
fig = impact.to_plotly()
fig.show()
```

## Budget over reform dimension

Iterating a reform over a parameter (e.g. CTC amount from $0 to $3,000) and plotting the trajectory is two steps:

```python
amounts = [0, 1_000, 2_000, 3_000]
budgets = []
for amount in amounts:
    impact = economic_impact_analysis(
        reform={"gov.irs.credits.ctc.amount.adult_dependent": amount},
        year=2026,
    )
    budgets.append(impact.budget.total_change)

import plotly.graph_objects as go
fig = go.Figure(go.Scatter(x=amounts, y=budgets, mode="lines+markers"))
fig.update_layout(xaxis_title="CTC amount ($)", yaxis_title="Budget cost ($bn)")
```

## Household reform curve

`HouseholdImpact` traces one household across a range of employment incomes under a reform:

```python
from policyengine.outputs import HouseholdImpact

traj = HouseholdImpact(
    household_fixture={"people": [{"age": 35}], "tax_unit": {"filing_status": "SINGLE"}},
    income_range=(0, 200_000, 1_000),
).compute(baseline_reform={}, reform=REFORM)

traj.to_plotly().show()
```

Useful for showing benefit cliffs and marginal tax rates.

## Color palette

PolicyEngine's palette is available via the design system:

```python
from policyengine.plotting import PALETTE

PALETTE.BLUE_PRIMARY
PALETTE.GRAY_600
```

## Exporting

Every Plotly figure can be exported:

```python
fig.write_image("chart.png", width=1000, height=600)
fig.write_html("chart.html", include_plotlyjs="cdn")
```
