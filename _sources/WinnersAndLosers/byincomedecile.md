# by Income Decile

## Overview

The winners and losers by income decile metrics provide insights into how a policy reform affects income changes across different income deciles. These metrics help to understand the distribution of income gains and losses among various income groups. The analysis is categorized based on the percentage change in income and provides a breakdown for each decile.

## Available Metrics

1. `winners_and_losers/by_income_decile`: Evaluates the income changes across income deciles and categorizes the population based on the magnitude of income gain or loss.

## Metric Structure

Each metric returns a dictionary with the following keys:
- `result`: Contains two sub-dictionaries:
  - `deciles`: Breakdown of the population within each decile into categories based on income change.
  - `all`: Summary statistics showing the average percentage of the population in each category across all deciles.

### Income Change Categories

The categories used for income change are:
- **Lose more than 5%**: Percentage of the population experiencing an income loss greater than 5%.
- **Lose less than 5%**: Percentage of the population experiencing an income loss less than 5%.
- **No change**: Percentage of the population experiencing no change in income.
- **Gain less than 5%**: Percentage of the population experiencing an income gain less than 5%.
- **Gain more than 5%**: Percentage of the population experiencing an income gain greater than 5%.

## Example Usage

```python
from policyengine import EconomicImpact

# Initialize the EconomicImpact class with a reform
impact = EconomicImpact(reform={
  "gov.hmrc.income_tax.rates.uk[0].rate": {
    "2024-01-01.2100-12-31": 0.55
  }}, country="uk")

# Calculate income change metrics by income decile
by_income = impact.calculate("winners_and_losers/by_income_decile")
by_wealth = impact.calculate("winners_and_losers/by_wealth_decile")

# Print the results
print(f"By Income Decile: {by_income}")
print(f"By Wealth Decile: {by_wealth}")
```

## Output

### By Income Decile

```python
{
    'result': {
        'deciles': {
            'Lose more than 5%': [16.8, 21.8, 28.9, 52.2, 72.4, 85.4, 91.9, 93.0, 98.0, 95.4],
            'Lose less than 5%': [2.7, 4.8, 5.8, 9.0, 5.2, 0.3, 0.6, 0.1, 0.0, 1.4],
            'No change': [80.5, 73.4, 65.3, 38.8, 22.4, 14.3, 7.5, 6.9, 1.9, 3.1],
            'Gain less than 5%': [0.0, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            'Gain more than 5%': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        },
        'all': {
            'Lose more than 5%': 65.6,
            'Lose less than 5%': 3.0,
            'No change': 31.4,
            'Gain less than 5%': 0.0,
            'Gain more than 5%': 0.0
        }
    }
}
```

## Interpretation

In this example:

- For income deciles, the percentage of people losing more than 5% increases from the lower deciles to the higher deciles, with a substantial concentration of losses in the top deciles. The majority of the population experiences no change in income, with very few gaining or losing within small ranges.
- For wealth deciles, a similar pattern is observed, with a significant proportion of the population in higher deciles experiencing losses greater than 5%, while most people in lower deciles experience no change.

