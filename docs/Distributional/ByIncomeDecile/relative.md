# Income Decile by Relative Change

## Overview

The income decile by relative change metrics provide insights into how a policy reform affects household net income across different income deciles in relative terms. These metrics are part of the `EconomicImpact` class and measure the relative change in income due to the reform, expressed as a percentage of the baseline income.

## Available Metrics

1. `distributional/by_income/relative`: Calculates the relative change in household net income by income decile.

## Metric Structure

Each metric returns a dictionary with the following keys:
- `relative`: A dictionary where the key is the income decile, and the value is the relative change in income for that decile. The relative change is expressed as a percentage of the baseline income.

The values are rounded to several decimal places.

## Example Usage

```python
from policyengine import EconomicImpact

# Initialize the EconomicImpact class with a reform
impact = EconomicImpact(reform={
  "gov.hmrc.income_tax.rates.uk[0].rate": {
    "2024-01-01.2100-12-31": 0.55
  }}, country="uk")

# Calculate relative income change by income decile
relative_income_change = impact.calculate("distributional/by_income/relative")

# Print the result
print(f"Relative income change: {relative_income_change}")
```

## Output

```
Relative income change: {'relative': {1: -0.0704, 2: -0.0809, 3: -0.1465, 4: -0.1559, 5: -0.1784, 6: -0.1823, 7: -0.1986, 8: -0.1832, 9: -0.1960, 10: -0.1392, 11: -0.0281}}
```

## Interpretation

In this example:

- The relative income change is negative across all deciles, indicating a reduction in household net income as a percentage of the baseline.
- The highest relative decrease is observed in the 7th decile, with a reduction of approximately 19.86%.
- The smallest relative decrease is in the 11th decile, at about 2.81%.
- The relative changes vary by decile, reflecting the impact of the policy reform on different income groups.
