# Overall

## Overview

The Budgetary Impact Overall metrics provide a high-level summary of how a policy reform affects government finances. These metrics are part of the `EconomicImpact` class and offer insights into the overall budgetary impact, changes in benefit spending, and changes in tax revenue.

## Available Metrics

1. `budgetary/overall/budgetary_impact`: Overall budgetary impact of the reform
2. `budgetary/overall/benefit_spending_impact`: Impact on total benefit spending
3. `budgetary/overall/tax_revenue_impact`: Impact on total tax revenue

## Metric Structure

Each metric returns a dictionary with specific keys:

### Budgetary Impact
- `budgetary_impact`: The overall budgetary impact (in GBP)

### Benefit Spending Impact
- `baseline_total_benefits`: Total benefits before the reform (in GBP)
- `reformed total benefits`: Total benefits after the reform (in GBP)
- `benefit_spending_impact`: The difference in benefit spending (in GBP)

### Tax Revenue Impact
- `baseline total tax`: Total tax revenue before the reform (in GBP)
- `reformed total tax`: Total tax revenue after the reform (in GBP)
- `tax_revenue_impact`: The difference in tax revenue (in GBP)

## Example Usage

```python
from policyengine import EconomicImpact

# Initialize the EconomicImpact class with a reform
impact = EconomicImpact(reform={
  "gov.hmrc.income_tax.rates.uk[0].rate": {
    "2024-01-01.2100-12-31": 0.55
  }
}, country="uk")

# Calculate overall budgetary impacts
budgetary_impact = impact.calculate("budgetary/overall/budgetary_impact")
benefit_spending_impact = impact.calculate("budgetary/overall/benefit_spending_impact")
tax_revenue_impact = impact.calculate("budgetary/overall/tax_revenue_impact")

# Print the results
print(f"Budgetary Impact: {budgetary_impact}")
print(f"Benefit Spending Impact: {benefit_spending_impact}")
print(f"Tax Revenue Impact: {tax_revenue_impact}")

```

## output

```
Budgetary Impact: {'budgetary_impact': 203274712297.14}
Benefit Spending Impact: {'baseline_total_benefits': 247160184562.67, 'reformed total benefits': 249032006583.15, 'benefit spending impact': 1871822020.49}
Tax Revenue Impact: {'baseline total tax': 447861864968.89, 'reformed total tax': 653008399286.52, 'tax revenue impact': 205146534317.63}
```

## Interpretation

In this example:

1. Overall Budgetary Impact:

- The reform results in a positive budgetary impact of approximately £203.27 billion. This represents the net fiscal effect of the reform, combining changes in both tax revenue and benefit spending.


2. Benefit Spending Impact:

- Baseline total benefits: £247.16 billion
- Reformed total benefits: £249.03 billion
- The reform increases benefit spending by £1.87 billion


3. Tax Revenue Impact:

- Baseline total tax: £447.86 billion
- Reformed total tax: £653.01 billion
- The reform increases tax revenue by £205.15 billion



The reform significantly increases tax revenue (by £205.15 billion) while slightly increasing benefit spending (by £1.87 billion). The net effect is a substantial positive budgetary impact of £203.27 billion.
These metrics provide a comprehensive overview of the fiscal implications of the proposed reform. They can help policymakers understand the overall financial impact on government finances, including changes in both revenue and expenditure.
Note: All monetary values are in GBP (British Pounds).