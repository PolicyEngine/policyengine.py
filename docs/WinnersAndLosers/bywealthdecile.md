# by Wealth Decile

## Overview

The winners and losers by wealth decile metrics provide insights into how a policy reform impacts different segments of the population based on their wealth. These metrics help understand the distributional effects of policy changes across various wealth deciles.

## Available Metrics

1. `winners_and_losers/by_wealth_decile`: Calculates the proportion of people in each wealth decile who experience a gain or loss of income due to the reform, categorized into different ranges of percentage change.

## Metric Structure

The `winners_and_losers/by_wealth_decile` metric returns a dictionary with the following keys:

- `deciles`: A dictionary where each key represents a wealth decile, and the value is a list showing the proportion of people in that decile who fall into different categories based on their income change:
  - `Lose more than 5%`
  - `Lose less than 5%`
  - `No change`
  - `Gain less than 5%`
  - `Gain more than 5%`
  
- `all`: A dictionary showing the overall proportion of people across all wealth deciles who fall into each income change category.

All proportions are expressed as percentages and rounded to 1 decimal place.

## Example Usage

```python
from policyengine import EconomicImpact

# Initialize the EconomicImpact class with a reform
impact = EconomicImpact(reform={
  "gov.hmrc.income_tax.rates.uk[0].rate": {
    "2024-01-01.2100-12-31": 0.55
  }
}, country="uk")

# Calculate winners and losers by wealth decile
by_wealth_decile = impact.calculate("winners_and_losers/by_wealth_decile")

# Print the results
print(f"By wealth decile: {by_wealth_decile}")
```

## Output

```python
{
    "result": {
        "deciles": {
            "Lose more than 5%": [21.0, 31.4, 58.9, 64.5, 68.7, 79.3, 81.1, 82.6, 84.5, 86.4],
            "Lose less than 5%": [6.6, 9.9, 2.3, 1.9, 3.4, 2.0, 0.4, 2.6, 0.2, 0.6],
            "No change": [72.3, 58.6, 38.8, 33.6, 27.9, 18.7, 18.4, 14.8, 15.3, 13.0],
            "Gain less than 5%": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            "Gain more than 5%": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        },
        "all": {
            "Lose more than 5%": 65.8,
            "Lose less than 5%": 3.0,
            "No change": 31.1,
            "Gain less than 5%": 0.0,
            "Gain more than 5%": 0.0
        }
    }
}
```

## Interpretation

In this example:

- The proportion of people in the lowest wealth decile who lose more than 5% of their income is 21.0%, while those who gain more than 5% is 0.0%.
- The proportion of people in the highest wealth decile who lose more than 5% is 86.4%, with no gain more than 5%.
- Overall, 65.8% of the population experiences a loss of more than 5% in income, with no significant gains.
