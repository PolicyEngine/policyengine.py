# Examples

Complete working scripts demonstrating common workflows. Each script can be run directly with `python examples/<filename>.py`.

## US budgetary impact

The canonical workflow for comparing a baseline and reform simulation, using both `economic_impact_analysis()` and `ChangeAggregate`.

```{.python include="../examples/us_budgetary_impact.py"}
```

## UK policy reform analysis

Applying parametric reforms, comparing baseline and reform with `ChangeAggregate`, analysing winners and losers by income decile, and visualising results with Plotly.

```{.python include="../examples/policy_change_uk.py"}
```

## UK income bands

Calculating net income and tax by income decile using representative microdata and `Aggregate` with quantile filters.

```{.python include="../examples/income_bands_uk.py"}
```

## US income distribution

Loading enhanced CPS microdata, running a full microsimulation, and calculating statistics within income deciles.

```{.python include="../examples/income_distribution_us.py"}
```

## UK employment income variation

Creating a custom dataset with varied employment income, running a single simulation, and visualising benefit phase-outs.

```{.python include="../examples/employment_income_variation_uk.py"}
```

## US employment income variation

Creating a custom dataset with varied employment income, running a single simulation, and visualising benefit phase-outs.

```{.python include="../examples/employment_income_variation_us.py"}
```

## Household impact

Comparing a single household's baseline vs reform with `HouseholdImpact`.

```{.python include="../examples/household_impact_example.py"}
```

## Speedtest

A simple benchmark of a full US microsimulation.

```{.python include="../examples/speedtest_us_simulation.py"}
```
