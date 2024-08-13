# Relative 

## Overview

The wealth distribution by relative change metrics provide insights into how a policy reform affects the relative change in household net income across different wealth deciles. These metrics are part of the `EconomicImpact` class and measure the proportional change in income due to the reform.

## Available Metrics

1. `distributional/by_wealth/relative`: Calculates the relative change in household net income by wealth decile.

## Metric Structure

Each metric returns a dictionary with the following keys:
- `relative`: A dictionary where the key is the wealth decile, and the value is the relative change in income for that decile.

The relative change is calculated as the ratio of the change in income to the baseline income, providing a measure of how income changes proportionally within each decile.

## Example Usage

```python
from policyengine import EconomicImpact

# Initialize the EconomicImpact class with a reform
impact = EconomicImpact(reform={
  "gov.hmrc.income_tax.rates.uk[0].rate": {
    "2024-01-01.2100-12-31": 0.55
  }}, country="uk")

# Calculate relative income change by wealth decile
relative_income_change = impact.calculate("distributional/by_wealth/relative")

# Print the result
print(f"Relative income change: {relative_income_change}")
```

## Output

```
Relative income change: {'relative': {1: -0.0704, 2: -0.0809, 3: -0.1465, 4: -0.1559, 5: -0.1784, 6: -0.1823, 7: -0.1986, 8: -0.1832, 9: -0.1960, 10: -0.1392, 11: -0.0281}}
```

## Interpretation

In this example:

- The relative income change is negative across all wealth deciles, indicating a proportional decrease in household net income due to the policy reform.
- The relative change is highest in the higher deciles, with the most significant decrease observed in the top decile (11), at -0.0281 (2.81% decrease).
- The impact is also noticeable in the lower deciles, with the smallest relative decrease observed in the lowest decile (1), at -0.0704 (7.04% decrease).
