# By program

## Overview

The Budgetary Impact by Program metrics provide detailed insights into how a policy reform affects various government revenue and expenditure programs. These metrics are part of the `EconomicImpact` class and can be calculated for different tax and benefit programs.

## Available Metrics

1. `budgetary/by_program/income_tax`: Income Tax revenue
2. `budgetary/by_program/national_insurance`: National Insurance contributions
3. `budgetary/by_program/vat`: Value Added Tax (VAT) revenue
4. `budgetary/by_program/council_tax`: Council Tax revenue
5. `budgetary/by_program/fuel_duty`: Fuel Duty revenue
6. `budgetary/by_program/tax_credits`: Tax Credits expenditure
7. `budgetary/by_program/universal_credits`: Universal Credit expenditure
8. `budgetary/by_program/child_benefits`: Child Benefits expenditure
9. `budgetary/by_program/state_pension`: State Pension expenditure
10. `budgetary/by_program/pension_credit`: Pension Credit expenditure

## Metric Structure

Each metric returns a dictionary with the following keys:
- `baseline`: The amount before the reform (in GBP).
- `reform`: The amount after the reform (in GBP).
- `change`: The percentage change due to the reform.

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

# Calculate budgetary impact for each program
income_tax = impact.calculate("budgetary/by_program/income_tax")
national_insurance = impact.calculate("budgetary/by_program/national_insurance")
vat = impact.calculate("budgetary/by_program/vat")
council_tax = impact.calculate("budgetary/by_program/council_tax")
fuel_duty = impact.calculate("budgetary/by_program/fuel_duty")
tax_credits = impact.calculate("budgetary/by_program/tax_credits")
universal_credits = impact.calculate("budgetary/by_program/universal_credits")
child_benefits = impact.calculate("budgetary/by_program/child_benefits")
state_pension = impact.calculate("budgetary/by_program/state_pension")
pension_credit = impact.calculate("budgetary/by_program/pension_credit")

# Print the results
print(f"Income Tax: {income_tax}")
print(f"National Insurance: {national_insurance}")
print(f"VAT: {vat}")
print(f"Council Tax: {council_tax}")
print(f"Fuel Duty: {fuel_duty}")
print(f"Tax Credits: {tax_credits}")
print(f"Universal Credit: {universal_credits}")
print(f"Child Benefits: {child_benefits}")
print(f"State Pension: {state_pension}")
print(f"Pension Credit: {pension_credit}")

```

## Output 

```
Income Tax: {'baseline': 291090070166.62, 'reform': 496242053771.2, 'change': 70.5}
National Insurance: {'baseline': 50826792606.89, 'reform': 50826792606.89, 'change': 0.0}
VAT: {'baseline': 175581776889.21, 'reform': 175581776889.21, 'change': 0.0}
Council Tax: {'baseline': 47861314826.79, 'reform': 47861314826.79, 'change': 0.0}
Fuel Duty: {'baseline': 28019829809.09, 'reform': 28019829809.09, 'change': 0.0}
Tax Credits: {'baseline': -208150256.01, 'reform': -308166663.98, 'change': 48.1}
Universal Credit: {'baseline': -72209672284.1, 'reform': -73780445681.08, 'change': 2.2}
Child Benefits: {'baseline': -15975002346.41, 'reform': -15975002346.41, 'change': -0.0}
State Pension: {'baseline': -127240166697.26, 'reform': -127240166697.26, 'change': -0.0}
Pension Credit: {'baseline': -2000983943.05, 'reform': -2181135212.4, 'change': 9.0}
```

## Interpretation

In this example:

- Income Tax revenue increases significantly by 70.5%, from £291.1 billion to £496.2 billion.
- National Insurance, VAT, Council Tax, and Fuel Duty revenues remain unchanged.
- Tax Credits expenditure increases by 48.1%, from £208.2 million to £308.2 million.
- Universal Credit expenditure increases slightly by 2.2%, from £72.2 billion to £73.8 billion.
- Child Benefits and State Pension expenditures remain unchanged.
- Pension Credit expenditure increases by 9.0%, from £2.0 billion to £2.2 billion.

These metrics provide a comprehensive view of how the reform affects various government revenue streams and expenditure programs. They can help policymakers understand the fiscal implications of proposed reforms across different sectors of the budget.
Note: Negative values for benefits (e.g., Tax Credits, Universal Credit) indicate government expenditure.