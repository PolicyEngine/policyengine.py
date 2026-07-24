# Decile impact behavior specification

Status: Approved and implemented.

## Scope

This specification covers:

- computed income groups;
- precomputed grouping variables;
- `DecileImpact` results;
- `IntraDecileImpact` results;
- the overall intra-decile result; and
- invalid, missing, zero-weight, tied, and excluded observations.

Unless configured otherwise, calculations use ten groups.

## Definitions

`income_variable`
: The income concept being measured. When no `decile_variable` is supplied, it
  is also the value used to construct groups.

`decile_variable`
: An optional precomputed grouping variable. When present, this variable
  determines group membership while `income_variable` remains the measured
  outcome.

`effective grouping weight`
: For households, `household_weight * household_count_people`. For another
  entity, that entity's survey weight.

`analysis weight`
: The weight used to calculate a reported statistic after groups have been
  constructed. `DecileImpact` uses the entity survey weight.
  `IntraDecileImpact` uses the effective grouping weight.

`excluded observation`
: An observation that does not belong to any reported group. It does not
  contribute to per-group or overall reported results.

## Group construction

Groups are always based on the baseline simulation. Reform values never cause
an observation to move between groups.

### Computed groups

When no `decile_variable` is supplied:

1. Rank observations by the baseline value of `income_variable`.
2. Use the effective grouping weight to calculate cumulative population shares.
3. Keep observations with equal ranking values in the same group.
4. Assign each observation to:

   ```text
   ceil(cumulative population share * number of groups)
   ```

5. Clamp the result to the inclusive range from 1 through the number of groups.

Each survey observation belongs to no more than one group. An observation is
never fractionally split across group boundaries.

Because observations and tied values are indivisible, reported groups are not
guaranteed to contain equal populations. Groups may be unequal or empty.

### Precomputed groups

When `decile_variable` is supplied:

- use its baseline value directly;
- include values from 1 through the configured number of groups;
- exclude missing values and values outside that range, including the
  conventional `-1` sentinel; and
- do not recalculate or rebalance the supplied groups.

This preserves country-package sentinels such as `-1` for negative income or
wealth.

## Exclusions and invalid inputs

| Case | Result |
|---|---|
| Negative computed ranking income | Include its weight when determining percentile positions, then assign group `-1` and exclude it from reported results |
| Missing or non-finite computed ranking income | Exclude it from ranking and reported results; it does not affect group boundaries |
| Zero effective grouping weight | Permit the row and clamp any computed group to at least 1. It has no influence on group construction or effective-weight results; it can still contribute to an entity-survey-weighted `DecileImpact` when its survey weight is positive |
| Negative or non-finite survey weight | Raise an error |
| All effective grouping weights are zero | Raise an error |
| Missing `household_count_people` for computed household groups | Raise an error |
| Negative or non-finite `household_count_people` | Raise an error |
| Number of groups less than one | Raise an error |
| Missing reform income for an included observation | Raise an error |
| Baseline and reform observations do not align | Raise an error |

## Worked grouping examples

### Ten equally weighted observations

```text
Income:  10 20 30 40 50 60 70 80 90 100
Weight:   1  1  1  1  1  1  1  1  1   1
Group:    1  2  3  4  5  6  7  8  9  10
```

### Tied observations

```text
Income:         10 10 20
Effective weight: 1  2  1
Group:            8  8 10
```

The observations with income 10 jointly represent 75% of the population.
Max-rank semantics therefore place both in group 8. Groups 1 through 7 and
group 9 are empty.

### One unusually large survey observation

```text
Income:          10 20
Effective weight: 15 85
Group:             2 10
```

The first observation represents 15% of the population and belongs wholly to
group 2. It is not divided between groups 1 and 2.

### Leading zero-weight observation

```text
Income:          10 20 30
Effective weight:  0  1  1
Group:              1  5 10
```

The first observation is lower-clamped to group 1 but contributes nothing to
weighted statistics.

### Negative income

```text
Income:          -10 20 30
Effective weight:  1  1  1
Ranked group:       4  7 10
Reported group:    -1  7 10
```

The negative-income observation affects the percentile positions, matching the
country-package convention, but is excluded from reported group results.

## `DecileImpact`

### Populated groups

For each populated group:

`baseline_mean`
: Survey-weighted mean baseline income.

`reform_mean`
: Survey-weighted mean reform income.

`absolute_change`
: `reform_mean - baseline_mean`.

`relative_change`
: Calculated as:

  ```text
  100 * absolute_change / baseline_mean
  ```

  If `baseline_mean` is zero, the result is null.

`count_better_off`
: Survey-weighted count of observations whose reform income is greater than
  baseline income.

`count_worse_off`
: Survey-weighted count of observations whose reform income is less than
  baseline income.

`count_no_change`
: Survey-weighted count of observations whose reform and baseline incomes are
  equal.

Household group boundaries are person-weighted, but the means and counts remain
household-survey-weighted. Person weights determine the groups; the statistics
describe households within those groups.

### Empty groups

An empty group still produces a result row:

```text
baseline_mean:   null
reform_mean:     null
absolute_change: null
relative_change: null
count_better_off: 0
count_worse_off:  0
count_no_change:  0
```

An empty group must not be represented as a populated group in which everyone
experienced no change.

## `IntraDecileImpact`

For every included household, calculate:

```text
(reform income - baseline income) / max(baseline income, 1)
```

Classify the result into exactly one category:

| Category | Definition |
|---|---|
| `lose_more_than_5pct` | Change less than or equal to -5% |
| `lose_less_than_5pct` | Change greater than -5% and less than or equal to -0.1% |
| `no_change` | Change greater than -0.1% and less than or equal to 0.1% |
| `gain_less_than_5pct` | Change greater than 0.1% and less than or equal to 5% |
| `gain_more_than_5pct` | Change greater than 5% |

Category proportions use:

```text
household_weight * household_count_people
```

For a populated group, the five category proportions must sum to 1, subject
only to floating-point tolerance.

For an empty group, all five category proportions are null.

## Overall intra-decile result

The `decile=0` result is calculated directly from all included observations:

```text
overall category proportion =
    effective weight in the category
    / total included effective weight
```

It is not the arithmetic mean of the individual group proportions.

This remains correct when:

- groups are unequal;
- groups are empty;
- tied observations skip group labels;
- one observation has an unusually large weight; or
- precomputed groups exclude observations.

If no included observation has positive effective weight, all overall
proportions are null.

## Grouping versus the measured outcome

Without `decile_variable`, `income_variable` controls both group construction
and the measured outcome.

With `decile_variable`:

- `decile_variable` controls group membership; and
- `income_variable` controls the measured outcome.

For example:

```python
income_variable = "household_net_income"
decile_variable = "household_wealth_decile"
```

This measures household-net-income changes within baseline wealth groups.

Exclusion is based on the grouping concept rather than the measured outcome. A
negative measured income remains included when its precomputed group is valid.
Therefore:

- a negative income used to construct income groups is excluded;
- negative wealth represented by wealth group `-1` is excluded; and
- negative household income inside a valid wealth group remains included.

## Approved decisions

1. Tied values remain together even when this creates unequal or empty groups.
2. Negative computed ranking income affects group boundaries but is excluded
   from reported results afterward.
3. Negative measured income inside a valid non-income group remains included.
4. Empty-group statistics are null, with winner/loser/no-change counts of zero.
5. The overall intra-decile result is calculated directly from the included
   population.
6. `relative_change` is the percentage change between the reported group means,
   rather than the mean of observation-level percentage changes.
