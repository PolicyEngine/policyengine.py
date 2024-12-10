# Calculate

The `Simulation.calculate` function is the most important function in the `Simulation` class. Think of initialising the `Simulation` class as setting up the world model (with assumptions and data specified), and `calculate` as asking it a question (we refer to this as an `endpoint`).

Generally, you call `calculate('folder/structure/question')`, with the questions being organised in a folder structure that makes sense. For example, we might call `Simulation.calculate('macro/comparison/budget/general/tax_revenue_impact')` to ask the model to calculate the impact of a tax revenue change on the budget.

The set of possible questions depends on the parameters of the `Simulation` you've defined. For example, if you set up a simulation with household data describing a person who earns £30,000 a year, you can't ask it for the budgetary impact of a reform, but you can ask it for the change to that person's net income. If you set up a simulation from PolicyEngine's survey data, you can ask it for the impact of a policy on the distribution of income, but you can't ask "how does this reform affect this person's net income?".

This page contains a list of all the questions you can ask the model, organised by folder structure. Under each one, we add the description, output type, and conditions under which you can ask that question.

To reduce duplication, we've organised them into four categories, by the type of simulation you're running:

* Single macro: simulations of a single policy on a large survey dataset. e.g. "What is the poverty rate?"
* Comparison macro: simulations of two policies (and the effect of comparing them) on a large survey dataset. e.g. "How much revenue would this policy raise?"
* Single household: simulations of a single policy on a single household. e.g. "What is my net income?"
* Comparison household: simulations of two policies (and the effect of comparing them) on a single household. e.g. "How much better off would I be under this policy?"


## Single macro



### `macro/gov/balance/total_spending`

The total spending of the government.

*Output type*: `float`

*Conditions*: None




### `macro/gov/balance/total_state_tax`

The total tax revenue collected at the state level.

*Output type*: `float`

*Conditions*: None




### `macro/gov/balance/total_tax`

The total tax revenue collected across all levels of government.

*Output type*: `float`

*Conditions*: None




### `macro/gov/budget_window/total_budget`

The total government budget over the specified budget window.

*Output type*: `float`

*Conditions*: None




### `macro/gov/budget_window/total_federal_budget`

The total federal government budget over the specified budget window.

*Output type*: `float`

*Conditions*: None




### `macro/gov/budget_window/total_spending`

The total government spending over the specified budget window.

*Output type*: `float`

*Conditions*: None




### `macro/gov/budget_window/total_state_tax`

The total state tax revenue over the specified budget window.

*Output type*: `float`

*Conditions*: None




### `macro/gov/budget_window/total_tax`

The total tax revenue over the specified budget window.

*Output type*: `float`

*Conditions*: None




### `macro/gov/programs/{program}`

Total expenditure or revenue from a given program. Available programs in the UK are: child_benefit, council_tax, fuel_duty, income_tax, national_insurance, ni_employer, pension_credit, state_pension, tax_credits, universal_credit, vat.

*Output type*: `float`

*Conditions*: `country='uk'`




### `macro/household/demographics/total_households`

Total number of households in the simulation.

*Output type*: `float`

*Conditions*: None




### `macro/household/finance/deep_poverty_gap`

The aggregate gap between household incomes and the deep poverty line.

*Output type*: `float`

*Conditions*: None




### `macro/household/finance/deep_poverty_rate`

The proportion of households in deep poverty.

*Output type*: `float`

*Conditions*: None




### `macro/household/finance/poverty_gap`

The aggregate gap between household incomes and the poverty line.

*Output type*: `float`

*Conditions*: None




### `macro/household/finance/poverty_rate`

The proportion of households in poverty.

*Output type*: `float`

*Conditions*: None




### `macro/household/finance/total_benefits`

Total benefits received by all households.

*Output type*: `float`

*Conditions*: None




### `macro/household/finance/total_market_income`

Total market income (before taxes and transfers) for all households.

*Output type*: `float`

*Conditions*: None




### `macro/household/finance/total_net_income`

Total net income (after taxes and transfers) for all households.

*Output type*: `float`

*Conditions*: None




### `macro/household/finance/total_tax`

Total tax paid by all households.

*Output type*: `float`

*Conditions*: None



### `macro/household/income_distribution/{lower_bound}`

Total households with income above the lower bound. Request `household/income_distribution` for the full dictionary (this will be more helpful).

*Output type*: `float`

*Conditions*: None




### `macro/household/inequality/gini`

Gini coefficient measuring income inequality (0 = perfect equality, 1 = perfect inequality).

*Output type*: `float`

*Conditions*: None




### `macro/household/inequality/top_10_percent_share`

Share of total income held by the top 10% of households.

*Output type*: `float`

*Conditions*: None




### `macro/household/inequality/top_1_percent_share`

Share of total income held by the top 1% of households.

*Output type*: `float`

*Conditions*: None

## Comparison macro



### `macro/comparison/budget/general/baseline_net_income`

Total household net income under the baseline policy.

*Output type*: `float`

*Conditions*: None




### `macro/comparison/budget/general/benefit_spending_impact`

Change in total government benefit spending between reform and baseline.

*Output type*: `float`

*Conditions*: None




### `macro/comparison/budget/general/budgetary_impact`

Overall budgetary impact of the reform (positive means the reform raises revenue).

*Output type*: `float`

*Conditions*: None




### `macro/comparison/budget/general/households`

Number of households affected by the reform.

*Output type*: `float`

*Conditions*: None




### `macro/comparison/budget/general/state_tax_revenue_impact`

Change in state tax revenue between reform and baseline.

*Output type*: `float`

*Conditions*: None




### `macro/comparison/budget/general/tax_revenue_impact`

Change in total tax revenue between reform and baseline.

*Output type*: `float`

*Conditions*: None




### `macro/comparison/budget/programs/{program}/baseline`

Program spending/revenue under baseline policy, where program is one of: child_benefit, council_tax, fuel_duty, income_tax, national_insurance, ni_employer, pension_credit, state_pension, tax_credits, universal_credit, vat.

*Output type*: `float`

*Conditions*: None




### `macro/comparison/budget/programs/{program}/reform`

Program spending/revenue under reform policy. See baseline endpoint for available programs.

*Output type*: `float`

*Conditions*: None




### `macro/comparison/budget/programs/{program}/difference`

Change in program spending/revenue (reform - baseline). See baseline endpoint for available programs.

*Output type*: `float`

*Conditions*: None




### `macro/comparison/budget/window/federal_budget`

Impact on federal budget over the budget window.

*Output type*: `float`

*Conditions*: None




### `macro/comparison/budget/window/total_budget`

Impact on total budget over the budget window.

*Output type*: `float`

*Conditions*: None




### `macro/comparison/decile/income/average/{n}`

Average change in household net income for income decile n (1-10).

*Output type*: `float`

*Conditions*: None




### `macro/comparison/decile/income/relative/{n}`

Percentage change in household net income for income decile n (1-10).

*Output type*: `float`

*Conditions*: None




### `macro/comparison/decile/wealth/average/{n}`

Average change in household net income for wealth decile n (1-10).

*Output type*: `float`

*Conditions*: None




### `macro/comparison/decile/wealth/relative/{n}`

Percentage change in household net income for wealth decile n (1-10).

*Output type*: `float`

*Conditions*: None




### `macro/comparison/inequality/gini/baseline`

See baseline endpoint for `household/inequality/gini`.

*Output type*: `float`

*Conditions*: None




### `macro/comparison/inequality/gini/reform`

Gini coefficient under reform policy.

*Output type*: `float`

*Conditions*: None




### `macro/comparison/inequality/top_10_pct_share/baseline`

See baseline endpoint for `household/inequality/top_10_percent_share`.

*Output type*: `float`

*Conditions*: None




### `macro/comparison/inequality/top_10_pct_share/reform`

Share of income held by top 10% under reform policy.

*Output type*: `float`

*Conditions*: None




### `macro/comparison/inequality/top_1_pct_share/baseline`

See baseline endpoint for `household/inequality/top_1_percent_share`.

*Output type*: `float`

*Conditions*: None




### `macro/comparison/inequality/top_1_pct_share/reform`

Share of income held by top 1% under reform policy.

*Output type*: `float`

*Conditions*: None




### `macro/comparison/poverty/age/{poverty_type}/{group}/{metric}`

Poverty metrics by age group, where:
- poverty_type is 'poverty' or 'deep_poverty'
- group is 'all', 'child', 'adult', or 'senior'
- metric is 'baseline', 'reform', or 'change_count' (only available for poverty)

*Output type*: `float`

*Conditions*: None




### `macro/comparison/poverty/gender/{poverty_type}/{gender}/{metric}`

Poverty metrics by gender, where:
- poverty_type is 'poverty' or 'deep_poverty'
- gender is 'male' or 'female'
- metric is 'baseline' or 'reform'

*Output type*: `float`

*Conditions*: None




### `macro/comparison/winners/income_decile/all/{outcome}`

Count of households experiencing each outcome across all income deciles, where outcome is:
'Gain more than 5%', 'Gain less than 5%', 'No change', 'Lose less than 5%', 'Lose more than 5%'

*Output type*: `float`

*Conditions*: None




### `macro/comparison/winners/income_decile/deciles/{outcome}`

Count of households experiencing each outcome by income decile. See all endpoint for outcome options.

*Output type*: `float`

*Conditions*: None




### `macro/comparison/winners/wealth_decile/all/{outcome}`

Count of households experiencing each outcome across all wealth deciles. See income_decile/all endpoint for outcome options.

*Output type*: `float`

*Conditions*: None




### `macro/comparison/winners/wealth_decile/deciles/{outcome}`

Count of households experiencing each outcome by wealth decile. See income_decile/all endpoint for outcome options.

*Output type*: `float`

*Conditions*: None

## Single household



### `household/net_income`

Net income of the household after taxes and benefits.

*Output type*: `float`

*Conditions*: None

## Comparison household



### `household/baseline/net_income`

Net income of the household under the baseline policy.

*Output type*: `float`

*Conditions*: None



### `household/comparison/net_income_change`

Change in net income of the household between reform and baseline.

*Output type*: `float`

*Conditions*: None



### `household/reform/net_income`

Net income of the household under the reform policy.

*Output type*: `float`

*Conditions*: None
