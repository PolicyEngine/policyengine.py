---
title: Weighted module (design note)
---

# Weighted module: survey weights inside policyengine.py

> **Status.** Decision, 22 September 2026. Decided here: the module
> (numpy kernels, weights as a named column, a closed accessor); the
> kernel definitions, two of which change published Gini and share
> figures; Stage 1 with the kernels under `policyengine/weighted/` and
> a parity test against `microcosm.frame.accounting`; Stage 2 as a
> major version, with the Python floor moving to 3.13 in it. Not
> decided here: Stage 3 (what the engines return). Counts come from a code census of
> policyengine.py 6.1.0, microdf 1.5.10, policyengine-core 3.32.6 and
> microcosm `fe2f92f`, each re-derived by a second reader; simulated
> figures name their setup.

## The decision

policyengine.py gets a `policyengine.weighted` module and stops
importing microdf. Three layers:

1. **Kernels.** Pure numpy functions of `(values, weights, ...)`:
   `sum`, `mean`, `count`, `n`, `effective_n`, `var`, `std`, `cov`,
   `corr`, `quantile`, `median`, `gini`, `top_share`, `bottom_share`,
   `rank`, `decile_rank`, `poverty_rate`, `poverty_gap`,
   `poverty_severity`, `groupby_sum`, `groupby_mean`. No pandas
   import. Each carries its definition in the docstring and a test
   against the reference named below.
2. **Weights as a column.** On the frames policyengine.py hands to
   users and writes to disk, the weight is an ordinary column named
   `<entity>_weight`. pandas carries it through merges, filters, sorts
   and file round trips with no code of ours. microcosm holds the same
   vector off the table as a typed `Weights(values, kind)` and
   materialises the column at every engine boundary, which is where
   policyengine.py reads it.
3. **A closed wrapper.** `df.weighted("household_weight")` binds a
   frame to its weight column and exposes only the kernels, a filter, a
   grouper, an array binder and the weight vector. Anything else raises
   `AttributeError`. `.frame` returns the plain `DataFrame`, weight
   column included.

microdf leaves policyengine.py's source in one release and leaves the
install only when policyengine-core and policyengine-uk stop returning
`MicroSeries` (Stage 3).

## Where the kernels live

Stage 1 ships the kernels in `policyengine/weighted/kernels.py`, with a
CI job on Python 3.13 asserting equality with
`microcosm.frame.accounting` on shared fixtures. They become an import
from microcosm-frame the release after it is on PyPI; if that has not
happened by 31 March 2027, the copy is the home and this paragraph is
revised.

microcosm's README names `microcosm-frame` as the package that succeeds
microdf, and its `DESIGN.md` allows "a thin pandas-compat veneer" for
migration; `policyengine.weighted` is that veneer. `accounting.py` has
six functions, and its quantile and Gini formulas are the ones pinned
below; the other thirteen kernels exist in neither package today.
microcosm-frame is unpublished (the `microcosm` name on PyPI is someone
else's) and requires Python 3.13. policyengine.py's floor moves from
3.11 to 3.13 with Stage 2's major version: CI already tests 3.11 to
3.14, sim-api's runtime images are `python:3.13`, axiom-oracles
requires 3.13, and the country packages, which allow 3.11, are
unaffected. policyengine.py already imports `microcosm.frame` for the Belgium
pilot (`be/model.py:217`) as an undeclared source checkout.

## What policyengine.py does today

- All 39 `MicroDataFrame` constructions in `src/` bind by column name,
  and 40 `pd.DataFrame(mdf)` unwraps take the wrapper off again;
  `core/dataset.py:144` unwraps "to avoid weighted operations during
  mapping". The wrapper goes on at dataset boundaries and comes off for
  the work.
- `src/` calls eight of microdf's 57 documented members, all on
  `MicroSeries`: `sum`, `count`, `mean`, `quantile`, `rank(pct=True)`,
  `groupby(labels).sum/mean`, `values`, `to_numpy`. No `MicroDataFrame`
  member is called in `src/`, `tests/` or `examples/`.
- `inequality.py:20-56` computes its own Gini with the record's weight
  share where the trapezoid needs its income share, so it agrees with
  microdf only under equal weights: for incomes 10,000, 30,000 and
  120,000 with weights 800, 1,200 and 50 it gives 0.2916 against
  0.2829. Its shares (`:184-219`) assign the record straddling the
  cutoff wholly to the top, an upward bias in the top-1% share of 4.7%
  at 1,000 records and 0.09% at 100,000 on simulated lognormal incomes
  with uniform random weights. The organisation has six independent
  weighted-Gini implementations.
- `pyproject.toml` pins `microdf_python>=1.3.0,<1.4`; the lock resolves
  1.3.0, two minor versions behind. Under 1.3.0 `notna()` returns a
  plain `Series`, and the weighted answer in `change_aggregate.py`
  survives because `__getitem__` re-attaches weights at the final
  mask. On a four-row fixture the same filtered aggregate is 190
  weighted and 6 unweighted, and nothing asserts which one ships.

## The wrapper

```python
w = df.weighted("household_weight")

w.mean("income")
w.quantile("income", 0.5)
w.gini("income")
w.top_share("income", 0.10)
w.poverty_rate("income", "threshold")
w.count()  # sum of weights
w.weights  # read-only copy of the weight column

w.where(df.income > 20_000)  # a Series mask must share the frame's index
w.by("region").mean("income")  # Series indexed by the sorted keys
w.with_values("change", reform_income - baseline_income)
w.frame  # the plain DataFrame, unchanged
```

Rules the wrapper enforces:

- The surface is the list above, with no `__getattr__` passthrough:
  `w.agg`, `w.apply`, `w.value_counts` and every other pandas method
  raise. This closes the failure the September 2026 review of microdf
  (PolicyEngine/microdf#333) found: `groupby("g").agg({"x": "mean"})`
  returns the unweighted mean while `.x.mean()` returns the weighted
  one, with no warning, on a green 852-test suite. srvyr's
  `summarise(mean(x))` returns an unweighted mean; this wrapper has no
  such path.
- Masks are positional for arrays. A pandas `Series` mask must have an
  index equal to the frame's, and a missing value in a mask raises,
  because pandas aligns boolean keys by label and a reindexed mask
  applied positionally is wrong with no error.
- Values bound with `with_values` are summed under this frame's
  weights, so reform-minus-baseline binds to the baseline frame by
  convention. `change_aggregate.py:140` gets there by accident today:
  `MicroSeries` arithmetic adopts the left operand's weights with no
  check, so the result carries reform weights whenever a scoping
  strategy has replaced them.
- The weight column cannot be aggregated through the wrapper.
  `MicroDataFrame` weights its own weight column, so
  `mdf["household_weight"].sum()` is a sum of squares: 202 for weights
  10, 10, 1, 1.
- Weights are copied and validated on binding with microcosm-frame's
  invariant: finite, non-negative, not all zero. Zero weights are
  allowed (the Enhanced CPS is 84% zero-weight rows). A missing weight
  column raises; policyengine-core's `get_weights` returns `None` when
  it cannot match the weight period and `MicroSeries` then uses unit
  weights silently.
- `.frame` is a plain property with no warning. The warning belongs on
  operations that drop weights silently, of which the wrapper has none.

The shape follows xarray's `obj.weighted(w)`: an accessor returning a
`__slots__` object with a fixed method list. The accessor and the
bound wrapper are two objects, because pandas 2 caches the accessor on
the frame. The manners follow srvyr's `tbl_svy`: filter and group
freely, refuse joins and reordering inside the wrapper, block writes to
the weight variable, make the exit explicit.

## Definitions the kernels pin

Every kernel raises on a weight that is NaN, infinite or negative.
Zero-weight rows are kept by `sum`, `mean` and `count` and skipped by
`quantile` and `rank`. A NaN value propagates: an aggregate over data
containing NaN is NaN, never a silently partial number, and the caller
drops rows with `where`. Sorting is stable (`mergesort`). The last
column says where a definition changes a number PolicyEngine publishes
today.

| Kernel | Definition | Reference | Changes published numbers |
|---|---|---|---|
| `quantile` | Inverse CDF: smallest value whose cumulative weight share reaches `q`. | `np.quantile(method="inverted_cdf", weights=)`; `microcosm.frame.accounting.wquantile`; R `survey::svyquantile` default rule, survey ≥ 4.4-1 | No |
| `sum`, `mean`, `count`, `n`, `effective_n` | `Σwx`, `Σwx/Σw`, `Σw`, the row count, Kish `(Σw)²/Σw²`. | `np.average` | No |
| `var`, `std`, `cov`, `corr` | `Σw(x−μ)²/Σw`, `ddof=0`: the population variance. `survey::svyvar`'s `n/(n−1)` correction is below 1e-4 at these sample sizes, and a `Σw`-based correction depends on the weight scale. | `np.cov(aweights=, ddof=0)` | Not published today |
| `gini` | Lorenz-curve trapezoid over weighted cumulative population and income. Negative values are used as given, as `inequality.py` does today; `negatives="zero"` is available. | `microcosm.frame.accounting.gini`; microdf; `laeken::gini` | **Yes**: differs from `inequality.py:20` by about 1e-3 at 50 records, 3e-5 at 1,000, below 1e-6 at 20,000 |
| `top_share`, `bottom_share` | Record straddling the cutoff split proportionally; constant incomes give exactly `p`. | microdf `_weighted_top_share` | **Yes**: `inequality.py:199` uses a hard cutoff |
| `rank`, `decile_rank` | Max-rank ties on cumulative weight; decile = `ceil(10·rank_pct)` clipped to 1–10. This is the ECDF convention: a record at a decile cutpoint goes to the upper decile, so `quantile(k/10)` boundaries do not reproduce `decile_rank` groups. A ranking weight may differ from the summing weight. | microdf `rank`; `decile_grouping.py` tests | No |
| `poverty_rate`, `poverty_gap`, `poverty_severity` | `P_α = Σ_i w_i·1[y_i < z_i]·((z_i − y_i)/z_i)^α / Σ_i w_i` for α = 0, 1, 2: denominator over all rows, strict `<`, per-row threshold, `z_i ≤ 0` raises. The currency total `Σw(z−y)⁺` is `poverty_gap_total`. | Foster, Greer and Thorbecke 1984 | Not published today; microdf's `poverty_gap` is the currency total |
| `groupby_*` | `np.add.at` over group codes for sum, mean and count; other kernels per group. | `microcosm.frame.accounting.groupby_wsum` | No |

Weights are survey sampling weights: non-integer, calibrated floats
that sum to a population. Every shipped PolicyEngine population file
inspected stores one such column, `household_weight`, on the household
table; the other entity weights are derived from it at load.

## Migration

**Stage 1: the module.** Land `policyengine/weighted/` with the
kernels, the accessor and the tests, then move `outputs/inequality.py`
(issue #527), `outputs/decile_grouping.py` and
`outputs/labor_supply_response.py` onto it. Gini and share outputs move
by the tie rule; the changelog says so, and the diff on the US and UK
baselines, including small filtered cells, is signed off before
release.

**Stage 2: the datasets.** `MicroDataFrame` is a declared type on the
public data model: eleven pydantic fields on `USYearData`,
`UKYearData` and `BEYearData` plus 18 `dict[str, MicroDataFrame]`
signatures, 105 references in 12 source files, and 25 test files
holding 254 test functions. It is a major version, in two releases:

1. Entity frames become a thin `DataFrame` subclass whose `sum`,
   `mean`, `count` and `quantile` raise `TypeError("use .weighted(...)")`.
   policyengine-sim-api's `_sum_output_variable` calls
   `data[variable].sum()` on these frames and gets a weighted number
   today; without this release it would get an unweighted one with no
   error. The companion sim-api change moves its two fast paths and
   its no-weight-column fallback onto the accessor.
2. Frames become plain `DataFrame`; a validator on `YearData` coerces
   any `MicroDataFrame` passed in; every test fixture is converted so
   the suite runs the path production runs; the 39 constructions
   become the accessor at the point of use; `pyproject.toml` drops
   `microdf_python`.

Each release ships after sim-api has bumped to the previous one and
diffed its inequality outputs on the US and UK baselines. sim-api pins
`policyengine==5.2.0` today; axiom-oracles pins `policyengine[us]==5.0.0`
and reaches this on a deliberate bump.

**Stage 3: the engines.** policyengine-core returns a `MicroSeries`
from its three `calculate` methods; policyengine-uk's own
`Microsimulation.calculate` does the same and its `model_api.py`
re-exports `MicroSeries` into the namespace of 844 files;
policyengine-api's `compare.py` holds 36 microdf references in one
file. What follows a `calculate` call across the organisation's
checkouts is pandas-shaped: subscripts, `.values`, `.sum`, arithmetic
and comparisons in the hundreds each, `.gini` in about a dozen files.
Changing the return type is a deprecation cycle of its own. Until then
microdf stays installed transitively and maintained:
PolicyEngine/microdf#333 is the floor, and the roadmap item to widen
pandas-method coverage is withdrawn there.

## Not settled here

- **Variance of published estimates.** Replicate-weight standard
  errors need replicate weights, which PolicyEngine's calibrated files
  do not carry. The uncertainty story belongs with microcosm's
  calibration.

## Flip conditions

- Reopen the wrapper's surface if, after Stage 2, more than three
  sites in `outputs/` reach for `.frame` to do arithmetic the wrapper
  could own.
- The kernel copy becomes an import, or permanent, on the triggers in
  "Where the kernels live".
- Revisit the design if pandas ships native observation weights (its
  "weighted mean" issue has been open since 2015) or the data layer
  moves off pandas. In the second case the kernels carry over
  unchanged and only the accessor is rewritten, which is why the
  kernels take arrays.
