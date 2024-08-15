# Inequality Impact

## Overview

The inequality impact metrics provide insights into how a policy reform affects income distribution. These metrics are part of the `EconomicImpact` class and include measures of income inequality and concentration of income among the top earners.

## Available Metrics

1. **`inequality/gini`**: Calculates the Gini coefficient, which measures income inequality.
2. **`inequality/top_1_pct_share`**: Calculates the income share of the top 1% of earners.
3. **`inequality/top_10_pct_share`**: Calculates the income share of the top 10% of earners.

## Metric Structure

Each metric returns a dictionary with the following keys:
- **`baseline`**: The metric value before the reform.
- **`reform`**: The metric value after the reform.
- **`change`**: The absolute change in the metric value due to the reform.
- **`change_percentage`**: The percentage change in the metric value due to the reform (only for Gini coefficient and top 1% share).

All values are rounded to 2 decimal places for baseline, reform, change, and change percentage.

## Example Usage

```python
from policyengine import EconomicImpact

# Initialize the EconomicImpact class with a reform
impact = EconomicImpact(
    reform={"gov.hmrc.income_tax.rates.uk[0].rate": {"2024-01-01": 0.25}},
    country="uk"
)

# Calculate Gini coefficient impact
gini_impact = impact.calculate("inequality/gini")

# Calculate top 1% income share impact
top_1_pct_share = impact.calculate("inequality/top_1_pct_share")

# Calculate top 10% income share impact
top_10_pct_share = impact.calculate("inequality/top_10_pct_share")

# Print the results
print(f"Gini coefficient impact: {gini_impact}")
print(f"Top 1% income share impact: {top_1_pct_share}")
print(f"Top 10% income share impact: {top_10_pct_share}")
```

## Output

```
Gini coefficient impact: {'baseline': 0.43, 'reform': 0.43, 'change': -0.00, 'change_percentage': -0.39}
Top 1% income share impact: {'baseline': 0.09, 'reform': 0.09, 'change': 0.00, 'change_percentage': 1.96}
Top 10% income share impact: {'baseline': 0.31, 'reform': 0.31, 'change': 0.00, 'change_percentage': 0.64}
```

## Interpretation

In this example:

- The Gini coefficient decreases slightly from 0.43 to 0.43, indicating a small reduction in income inequality.
- The income share of the top 1% increases from 9.12% to 9.30%, reflecting a slight rise in concentration among the highest earners.
- The income share of the top 10% increases from 31.02% to 31.21%, showing a minor rise in the share of income held by the top 10% of earners.
