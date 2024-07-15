# By age

## Overview

The regular poverty by age group metrics provide insights into how a policy reform affects poverty rates for different age categories. These metrics are part of the `EconomicImpact` class and can be calculated for children, adults, seniors, and the overall population.

## Available Metrics

1. `poverty/regular/child`: Calculates the poverty rate for children.
2. `poverty/regular/adult`: Calculates the poverty rate for adults.
3. `poverty/regular/senior`: Calculates the poverty rate for seniors.
4. `poverty/regular/all`: Calculates the overall poverty rate.

## Metric Structure

Each metric returns a dictionary with the following keys:
- `baseline`: The poverty rate before the reform.
- `reform`: The poverty rate after the reform.
- `change`: The percentage change in the poverty rate due to the reform.

All values are rounded to 2 decimal places for the baseline and reform, and to 1 decimal place for the change.

## Example Usage

```python
from policyengine import EconomicImpact

# Initialize the EconomicImpact class with a reform
impact = EconomicImpact(reform={
  "gov.hmrc.income_tax.rates.uk[0].rate": {
    "2024-01-01.2100-12-31": 0.55
  }
}, country="uk")

# Calculate poverty rates by age group
child_poverty = impact.calculate("poverty/regular/child")
adult_poverty = impact.calculate("poverty/regular/adult")
senior_poverty = impact.calculate("poverty/regular/senior")
overall_poverty = impact.calculate("poverty/regular/all")

# Print the results
print(f"Child poverty: {child_poverty}")
print(f"Adult poverty: {adult_poverty}")
print(f"Senior poverty: {senior_poverty}")
print(f"Overall poverty: {overall_poverty}")

```
## Example Output

```
Child poverty: {'baseline': 0.32, 'reform': 0.36, 'change': 10.1}
Adult poverty: {'baseline': 0.17, 'reform': 0.19, 'change': 8.4}
Senior poverty: {'baseline': 0.13, 'reform': 0.17, 'change': 30.5}
Overall poverty: {'baseline': 0.20, 'reform': 0.22, 'change': 11.7}
```
## Interpretation

In this example:

- The child poverty rate increases from 32% to 36%, a 10.1% increase.
- The adult poverty rate increases from 17% to 19%, an 8.4% increase.
- The senior poverty rate increases from 13% to 17%, a significant 30.5% increase.
- The overall poverty rate increases from 20% to 22%, an 11.7% increase.