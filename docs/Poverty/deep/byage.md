# By age

## Overview

The deep poverty by age group metrics provide insights into how a policy reform affects deep poverty rates for different age categories. These metrics are part of the `EconomicImpact` class and can be calculated for children, adults, seniors, and the overall population.

## Available Metrics

1. `poverty/deep/child`: Calculates the deep poverty rate for children.
2. `poverty/deep/adult`: Calculates the deep poverty rate for adults.
3. `poverty/deep/senior`: Calculates the deep poverty rate for seniors.
4. `poverty/deep/age/all`: Calculates the overall deep poverty rate.

## Metric Structure

Each metric returns a dictionary with the following keys:
- `baseline`: The deep poverty rate before the reform.
- `reform`: The deep poverty rate after the reform.
- `change`: The percentage change in the deep poverty rate due to the reform.

All values are rounded to 1 decimal place for the baseline, reform, and change.

## Example Usage

```python
from policyengine import EconomicImpact

# Initialize the EconomicImpact class with a reform
impact = EconomicImpact(reform={
  "gov.hmrc.income_tax.rates.uk[0].rate": {
    "2024-01-01.2100-12-31": 0.55
  }
}, country="uk")

# Calculate deep poverty rates by age group
child_deep_poverty = impact.calculate("poverty/deep/child")
adult_deep_poverty = impact.calculate("poverty/deep/adult")
senior_deep_poverty = impact.calculate("poverty/deep/senior")
overall_deep_poverty = impact.calculate("poverty/deep/age/all")

# Print the results
print(f"Child deep poverty: {child_deep_poverty}")
print(f"Adult deep poverty: {adult_deep_poverty}")
print(f"Senior deep poverty: {senior_deep_poverty}")
print(f"Overall deep poverty: {overall_deep_poverty}")

```

## output

```
Child deep poverty: {'baseline': 2.4, 'reform': 2.5, 'change': 0.7}
Adult deep poverty: {'baseline': 2.6, 'reform': 2.7, 'change': 3.9}
Senior deep poverty: {'baseline': 1.8, 'reform': 1.8, 'change': 0.5}
Overall deep poverty: {'baseline': 2.4, 'reform': 2.5, 'change': 2.7}

```

## Interpretation

In this example:

- The child deep poverty rate increases slightly from 2.4% to 2.5%, a 0.7% increase.
- The adult deep poverty rate increases from 2.6% to 2.7%, a 3.9% increase.
- The senior deep poverty rate remains stable at 1.8%, with a minimal 0.5% increase.
- The overall deep poverty rate increases from 2.4% to 2.5%, a 2.7% increase.