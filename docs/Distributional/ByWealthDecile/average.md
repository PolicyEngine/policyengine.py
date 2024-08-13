# Average

## Overview

The wealth distribution by average metrics provide insights into how a policy reform affects the average wealth across different wealth deciles. These metrics are part of the `EconomicImpact` class and measure the average change in household net wealth due to the reform.

## Available Metrics

1. `distributional/by_wealth/average`: Calculates the average change in household net wealth by wealth decile.

## Metric Structure

Each metric returns a dictionary with the following keys:
- `average`: A dictionary where the key is the wealth decile, and the value is the average change in wealth for that decile.

The values represent the change in wealth due to the policy reform, rounded to several decimal places.

## Example Usage

```python
from policyengine import EconomicImpact

# Initialize the EconomicImpact class with a reform
impact = EconomicImpact(reform={
  "gov.hmrc.income_tax.rates.uk[0].rate": {
    "2024-01-01.2100-12-31": 0.55
  }}, country="uk")

# Calculate average wealth change by wealth decile
average_wealth_change = impact.calculate("distributional/by_wealth/average")

# Print the result
print(f"Average wealth change: {average_wealth_change}")
```

## Output

```
Average wealth change: {'average': {1: -1542.53, 2: -1982.53, 3: -4556.84, 4: -5370.20, 5: -7216.05, 6: -7591.30, 7: -9211.03, 8: -9648.62, 9: -11506.89, 10: -14378.30, 11: -13195.00}}
```

## Interpretation

In this example:

- The average wealth change is negative across all deciles, indicating a reduction in household net wealth due to the policy reform.
- The impact is most severe in the highest deciles, with the highest decrease observed in the top decile (11), at -13,195.00.
- The decrease in wealth is progressively less severe in lower deciles, with the smallest decrease observed in the lowest decile (1), at -1,542.53.
