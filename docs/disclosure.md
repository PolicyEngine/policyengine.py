---
title: "Disclosure control"
---

Local results from survey microdata rest on few households, and a licence
binds every published number. `policyengine.disclosure` turns per-household
results into area tables that follow the licence's rules and carry their
uncertainty. Use it for every UK result below the national level that leaves
your machine.

```python
from policyengine.outputs import compute_uk_geography_disclosure

impact = compute_uk_geography_disclosure(
    baseline_simulation=baseline,
    reform_simulation=reform,
    year=2026,
    levels=("region", "constituency"),
    reform="budget",
)
impact.findings  # what blocks publication, if anything
impact.public  # the rows that may be published, or None while blocked
```

The UK datasets derive from surveys under the UK Data Service End User
Licence. The defaults below follow its disclosure rules. You can raise them
for a study with stricter conditions; you cannot lower them.

## What a published row holds

Each row is one outcome for one area, reform and year.

| Column | Content |
|---|---|
| `level`, `area_code`, `reform`, `year`, `outcome` | The key of the row |
| `value`, `lo`, `hi` | The rounded estimate and its 90% interval |
| `direction` | `gain`, `loss`, `too_close_to_call` or `no_change` |
| `tier` | `reported`, `approximate` or `withheld` |
| `reason` | `thin_support` for an approximate row, `disclosure_control` for a withheld row |
| `support_band` | `<10`, `10–29` or `30+` survey households, never an exact count |
| `noise` | Whether the row carries keyed noise |
| `estimator` | `direct`: the estimate comes from the area's own records |

The outcomes are `average_change`, `relative_change`, `total_change`,
`share_gaining`, `share_losing` and `share_no_change`. A withheld row carries
no value, interval, direction or support band.

## The rules

**Count floor.** A number must rest on at least 10 distinct survey households
that contribute to it. For a change, a household contributes when its income
changes by more than `change_tolerance` (£1 a year, which is also the lowest
value the setting takes). Copies and clones of one survey household count
once, through the dataset's `source_household_id`. For a share, both sides
must pass: the households that gain and those that do not.

**Dominance.** While noise is off, a number is withheld in two cases:

- one survey household carries more than half of it, by size;
- the p% rule: a reader of the number, or one household that knows its own
  part, could estimate some household's part to within 10%. Every household
  is a possible target and every other household a possible reader, so the
  rule also catches a total whose other parts cancel.

These rules protect each household against any reader and against any one
other household. They do not stop two or more households that pool what they
know: a number that three households carry almost alone passes, as long as 10
contribute.

**Effective sample.** Weights that differ a lot make an estimate less precise
than its household count suggests. Where the data gives one area and one
weight per record, a low effective sample makes a row `approximate`: it keeps
its value and interval, but the interval understates the uncertainty. Where
the data is an area × household weight matrix, the household count passes by
construction, so the effective sample must also be at least 10. Weights given
as a matrix keep this rule whatever they hold: one row of a dense matrix has
one weight per record, yet every household of the nation sits in that area.

**Zero cells.** A cell with no contributing household is published as zero,
with the interval [0, 0] and the direction `no_change`. It means that no
surveyed household in the area changed, not that no household there does. Its
support band counts the households it was measured on.

**Settings.** The layer validates its settings again before it uses them, so
a copy made with `model_copy(update=...)` cannot lower a floor.

**Linked outcomes.** Average, relative and total change share a numerator, so
they are published or withheld together. Gaining, losing and no change add to
one, so the third share is published only when it is safe to derive.

## Uncertainty and rounding

Intervals come from a Poisson bootstrap over survey households with 1,000
replicates. A ratio resamples its numerator and denominator together. The
weights stay fixed, so the intervals leave out calibration uncertainty and are
too narrow, most of all where support is thin.

Values are rounded to the order of magnitude of their standard error. The
interval is rounded outward on the same base.

## The release check

Published numbers constrain each other. If a region is public and all but one
of its constituencies are public, subtraction gives the last one. The check
looks for such remainders:

- child areas against their parent area (constituencies in regions, regions in
  the nation);
- the components of a package against the package;
- when two levels that do not nest are released together, an area against
  the areas of the other level that lie wholly inside it, and against the
  areas that meet it (their sum minus the area is what they hold outside it);
- earlier publications, passed as `prior_public`.

A remainder gets the rules of a cell. Estimates added with `publish=False`
are a reference: the release does not emit their rows, but it treats the rows
that pass as public elsewhere and the withheld ones as secret, and checks
them like its own.

The check matches areas by their codes, and it raises on a code that matches
nothing rather than leave areas unchecked. Each value of `parent_of` must be
an area code of the parent level's estimates.

`compute_uk_geography_disclosure` always checks constituencies and local
authorities against their region, and regions against the nation, also when
you publish one level only. A level given as a weight matrix needs
`parent_of=` with the region of each area; without it the function raises,
because a check against the nation alone nearly always passes.

The check reports; it does not withhold cells by itself. A blocking finding
names the group and suggests a cell. Withhold it, then check again. When a
finding suggests no cell, withhold the parent (`finding.group` at
`finding.group_level`) instead:

```python
for finding in impact.findings:
    print(finding.code, finding.group, finding.suggested)

impact.release.withhold(
    level="constituency",
    area_code="E14001234",
    reform="budget",
    year=2026,
    outcome="average_change",
)
impact.refresh()  # checks again and fills impact.public once nothing blocks
```

Two findings can be accepted after review, with `acknowledge=[...]`:

- `unchecked_overlap`: levels that overlap without nesting, such as
  constituencies and local authorities, are released together. The release
  checks each area against the areas wholly inside it and against the areas
  that meet it. It does not check other differences between overlapping
  areas, and on weight-matrix data it checks none.
- `noise_reference_public`: an earlier table shows the same cells under
  another noise setting.

## Noise

Noise is off by default. With `DisclosureSettings(noise=True)`, each survey
household's change is scaled by a fixed factor between 8% and 12% away from 1,
derived from its id and a secret key. The same household has the same factor
in every table and every rebuild. Noise replaces the dominance rule; the count
floor still applies. The range cannot start closer to 1 than 8%.

A number that one household dominates, published with noise, gives that
household's part to within 8 to 12%. The p% rule treats 10% as the line, so
noise puts such a number right at that line, not safely past it. Whether the
UK Data Service accepts noise in place of the dominance rule is a licence
question, which is why noise stays off by default.

- **Size.** The noise in a total is about a tenth of that total's sampling
  error.
- **Key.** Pass `noise_key=` or set `POLICYENGINE_DISCLOSURE_NOISE_KEY`. There
  is no default key. Keep the key out of repositories and CI logs, and do not
  change it between releases of one dataset: two noised versions of a number
  average towards the truth.
- **Limits.** Denominators carry no noise. The factor cancels in a ratio of
  two numbers that the same household dominates. A remainder that subtraction
  recovers is the noised sum of the withheld cells, so it has the protection
  of a noised cell and no more: the count floor applies to it, and noise
  stands in for the dominance rule as it does for a cell. An un-noised copy
  of the same cell gives the factor away.

## Validating published files

`validate_public` checks the format of a table, a CSV file or a directory. It
needs no key and no microdata, so it can run on every pull request:

```bash
python -m policyengine.disclosure validate public/data --reviewed notes.csv
```

It rejects private audit columns, unknown tiers, a value in a withheld row,
unrounded values, a direction that does not match its interval, and files it
does not recognise. It cannot tell whether a number rested on enough
households; only the release that made the file can.

## Private objects

`audit_dir=` writes the exact values, household counts and shares behind every
row. The directory must be outside any git repository.

`AreaEstimates`, the object that `estimate_change` returns, holds the same
exact values. With noise on it also holds the noise factor of every household
that gains or loses, and within one dataset those factors do the same job as
the key. Keep it in memory and treat it as you treat the key. It cannot be
pickled or copied.

## What a reader can still derive

`average_change` and `relative_change` together give the area's total
baseline income to within a few per cent (household count × average ÷
relative). That total is a denominator: it carries no noise and is not
checked for dominance.

## Arrays without a simulation

The package works on arrays and imports nothing from the rest of the library:

```python
from policyengine.disclosure import AreaWeights, Release, estimate_change

seats = estimate_change(
    level="constituency",
    reform="budget",
    year=2026,
    areas=AreaWeights.from_labels(seat_codes, household_weights),
    source_ids=source_household_ids,
    baseline=baseline_net_income,
    reformed=reformed_net_income,
)
release = Release()
release.add(seats)
release.check()
public = release.to_public()
```

`AreaWeights.from_matrix(matrix, area_codes)` takes an area × household weight
matrix instead. A dataset without `source_household_id` needs `source_ids=`
from the caller; the layer does not guess which records share a survey
household.
