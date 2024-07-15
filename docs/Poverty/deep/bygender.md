# By gender

## Overview

The deep poverty by gender metrics provide insights into how a policy reform affects deep poverty rates for different genders. These metrics are part of the `EconomicImpact` class and can be calculated for males, females, and the overall population.

## Available Metrics

1. `poverty/deep/male`: Calculates the deep poverty rate for males.
2. `poverty/deep/female`: Calculates the deep poverty rate for females.
3. `poverty/deep/gender/all`: Calculates the overall deep poverty rate.

## Metric Structure

Each metric returns a dictionary with the following keys:
- `baseline`: The deep poverty rate before the reform.
- `reform`: The deep poverty rate after the reform.
- `change`: The percentage change in the deep poverty rate due to the reform.

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

# Calculate deep poverty rates by gender
male_deep_poverty = impact.calculate("poverty/deep/male")
female_deep_poverty = impact.calculate("poverty/deep/female")
overall_deep_poverty = impact.calculate("poverty/deep/gender/all")

# Print the results
print(f"Male deep poverty: {male_deep_poverty}")
print(f"Female deep poverty: {female_deep_poverty}")
print(f"Overall deep poverty: {overall_deep_poverty}")

```

## output 

```
Male deep poverty: {'baseline': 2.66, 'reform': 2.73, 'change': 2.5}
Female deep poverty: {'baseline': 2.16, 'reform': 2.23, 'change': 2.9}
Overall deep poverty: {'baseline': 2.41, 'reform': 2.47, 'change': 2.7}

```

## Interpretation

In this example:

- The baseline male deep poverty rate is 2.66%, which increases to 2.73% after the reform, representing a 2.5% increase.
- The baseline female deep poverty rate is 2.16%, which increases to 2.23% after the reform, representing a 2.9% increase.
- The overall deep poverty rate increases from 2.41% to 2.47%, a change of 2.7%.