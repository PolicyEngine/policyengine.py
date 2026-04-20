---
title: "Examples"
---

Complete runnable scripts in `examples/` — each demonstrates one workflow end-to-end. Run with `python examples/<file>.py`.

## US

### Budget impact of a reform

```{.python include="../examples/us_budgetary_impact.py"}
```

### Income distribution over microdata

```{.python include="../examples/income_distribution_us.py"}
```

### Household impact curve

```{.python include="../examples/household_impact_example.py"}
```

### Employment-income variation

```{.python include="../examples/employment_income_variation_us.py"}
```

### Full microsimulation speedtest

```{.python include="../examples/speedtest_us_simulation.py"}
```

## UK

### Reform with decile impact

```{.python include="../examples/policy_change_uk.py"}
```

### Income bands analysis

```{.python include="../examples/income_bands_uk.py"}
```

### Employment-income variation

```{.python include="../examples/employment_income_variation_uk.py"}
```

### Paper reproduction

```{.python include="../examples/paper_repro_uk.py"}
```

## Writing your own

Patterns worth following:

- Always pass `year` explicitly — don't rely on defaults
- Construct the baseline `Simulation` once; build reforms on top rather than recomputing
- Save the `.manifest.json` alongside your results for reproducibility
- Use typed outputs (`Aggregate`, `Poverty`, etc.) rather than ad-hoc `.calculate` calls — the outputs handle edge cases like missing weights

More patterns in [Outputs](outputs.md) and [Impact analysis](impact-analysis.md).
