# By gender

## Overview
The regular poverty by gender metrics provide insights into how a policy reform affects poverty rates for different genders. These metrics are part of the EconomicImpact class and can be calculated for males, females, and the overall population.

## Available Metrics
- `poverty/regular/male`: Calculates the poverty rate for males.
- `poverty/regular/female`: Calculates the poverty rate for females.
- `poverty/regular/gender/all`: Calculates the overall poverty rate.

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

# Calculate poverty rates by gender
male_poverty = impact.calculate("poverty/regular/male")
female_poverty = impact.calculate("poverty/regular/female")
overall_poverty = impact.calculate("poverty/regular/gender/all")

# Print the results
print(f"Male poverty: {male_poverty}")
print(f"Female poverty: {female_poverty}")
print(f"Overall poverty: {overall_poverty}")
```

## Example output 

```
Male poverty: {'baseline': 0.18, 'reform': 0.21, 'change': 12.9}
Female poverty: {'baseline': 0.21, 'reform': 0.23, 'change': 10.7}
Overall poverty: {'baseline': 0.20, 'reform': 0.22, 'change': 11.7}

```

## Interpretation

In this example:

- The baseline male poverty rate is 18%, which increases to 21% after the reform, representing a 12.9% increase.
- The baseline female poverty rate is 21%, which increases to 23% after the reform, representing a 10.7% increase.
- The overall poverty rate increases from 20% to 22%, a change of 11.7%.

These metrics can help policymakers understand the differential impact of a reform on poverty rates across genders.