# Replay gate policy d1344-replay-regressions-v2

Decided under cos d1344 by workstream W4 on 15 October 2026, after two
independent reviews. The pull request that added this file records the
decision, the reviews and the alternatives considered. Revised on 16
October 2026, before first use, after the third to fifth reviews of
policyengine.py#637: scorecard's own record of a mixed known gap no longer
blocks, flag counters must equal the flags the rows carry, and any
candidate value other than £0 at a known gap is a contradiction.
The data-limited exception amendment below implements the Budget
coordinator's proposal of 17 October 2026 under cos d1344. The registry
records its decision and review status; the proposal requires independent
review agreement before adoption.
`evaluate_replay_receipt` in `policyengine.provenance.qualification`
applies this text. Each qualification receipt records the policy id and
this file's SHA-256 in its `replay` gate details.

The replay gate fails on the regressions a scorecard replay receipt
identifies. It calls a gap known only on positive evidence from the
comparison base, and passes the rows that record a known gap. It sends
every other flagged move to a named reviewer.

## Fail

- A rejected request, `no_supported_years`, integrity `failed` (a crash or
  missing outputs, persistent or not), or a receipt not bound to the
  request. Only the narrow data-limited exceptions below can make a failed
  integrity reviewable.
- A mapping flag.
- A lost result: a coverage row with a base value and no candidate value,
  unless it is the record of a known gap (below).
- A lost response:
  - a measure-year the candidate lists as inert, unless it is a known gap
    or a data-limited exception applies;
  - a measure-year total at exactly £0 where the base's absolute value is
    at least the diff's bound, max(£1m, 1% of the base's absolute value),
    whether the base was positive or negative, unless a data-limited
    exception applies. A known gap never excuses this: a base whose record
    lists the measure-year as a gap cannot also hold a material value for
    it, and a data-limited exception never excuses that contradiction.
- An event whose supported grid is incomplete, unless every inert or
  missing and supported measure-year in it is a known gap or is accounted
  for by a data-limited exception. An incomplete event whose receipt does
  not list its missing measure-years fails, and so does one with no inert
  and no missing and supported measure-year at all. A receipt whose
  integrity is `incomplete` with no incomplete event also fails.
- A receipt that contradicts itself, including a complete event that lists
  an inert, or missing and supported, measure-year; flag counters that
  differ, either way, from the flags its rows carry; and a candidate value
  other than £0 for a measure-year that is a known gap.

## Known gaps

A candidate measure-year that is inert, or missing and supported (in the
event's missing list and not its unsupported list), is a known gap only
when the receipt's base-side record for the same event (`diff.base_events`,
taken from the base's verified staging and run manifests) lists the same
measure and year as inert, or as missing and supported, in the base. The
gate records each known gap with the base's staging manifest SHA-256. A
legacy-layout base, or an event the base did not replay, has no record, so
none of its gaps are known.

A known gap does not block. Where one side is inert and the other missing,
scorecard records the gap as a coverage row with exactly £0 on the inert
side and no value on the other, and an inertness flag on the inert side
only, on a row with no values. Those flags are the gap itself and neither
fail nor send the row to review. (Where the candidate is the inert side, its
inert list already decides that flag.) The gate records every row a known
gap accounts for, in whole or in part, beside the known gaps; the rest of a
partly excused row's flags are judged as usual. Any other row at a known gap
is judged as usual: a coverage row with a base value and no candidate value,
even £0, is still a lost result, and any candidate value other than £0 at a
known gap contradicts the candidate's own record, which lists the
measure-year as inert (exactly £0) or missing (no value).

## Data-limited exceptions

`uk_replay_exceptions.json` lists narrowly scoped exceptions for regressions
caused by inputs absent from the candidate's data. Missingness alone does
not establish cause. The registry is reviewed like code. Each entry records
an id, failure codes, event, measure key, years, required missing inputs,
cause, tracking issue, approved lineage, positive-input probe specification,
publication designation, governing decision and review status.

An exception applies only when its code, event, measure key and year all
match, and the same qualification attempt's `budget_inputs` gate result
and its evidence report every required input as missing from the
candidate's data. A degenerate but present input cannot satisfy that
condition. The same evidence must show that the previous certified pair
never supplied the input usably: its model did not define the input, or
its data lacked the input column. A previous pair with both the variable
and column present requires a fresh reviewed registry decision and fails,
including when the previous column was degenerate. The approved
SDLT lineage is that no certified uk-data release through 1.58.2 supplied
the input. When the data gains an input, or the measure-year falls outside
the entry's years, the exception stops applying automatically.

Every excepted measure-year must have a candidate effect of exactly £0
at the measure-total level and on every source row. Any nonzero candidate
effect is a contradiction and fails, independently of any base known gap.

The gates job also runs the registry's positive-input probe directly on the
exact installed candidate model, using one synthetic household and no
survey data. For the SDLT exception, an England household buys an additional
residential property for £300,000 in 2026. The reform adds 0.02 to every
band of `gov.hmrc.stamp_duty.residential.purchase.additional.rate`. Its
`sdlt_on_residential_property_transactions` output must increase by £6,000
within £0.10, and must be exactly unchanged when the purchase input is £0.
An import error, missing variable or parameter, or any other inability to
run the probe records failure. An exception requires a passing probe from
the same attempt (identified by both pair id and attempt key), bound to the
candidate model version and probe specification by digests. Finalization
re-reads the evidence and verifies its digest, as it does for `budget_inputs`.

Matching `construction_inert` integrity failures and `lost_response`
regressions (candidate inertness or a measure-year total of £0 against a
material base value) become review items. Each names the exception, cause
and required missing inputs. A failed receipt proceeds to the ordinary
corpus and diff checks only if every integrity failure matches an
exception. Every unmatched failure, mapping flag, lost result and
contradiction retains its ordinary treatment. An exception accounts only
for its matched inert measure-years when checking grid completeness; it
does not excuse a missing result.

An applied exception always requires review and can never qualify a
candidate automatically. Promotion requires a named reviewer to accept
the exact qualification receipt. Applied-exception review items carry the
registry's publication designation, and the named reviewer's acceptance
explanation must restate it. For SDLT the designation is: not computable,
in PolicyEngine/uk-autumn-budget-dashboard-2026 (data-limited handling,
PR #51; Budget-day runbook, PR #14).

The gate records every applied exception's id, event, measure key, year
and matched codes, the registry's SHA-256, and the digests of the same
attempt's `budget_inputs` and probe results it relied on. Every result
that reads the registry records its digest.

## Review

A needs-review verdict blocks automatic promotion. It stays blocked until a
named reviewer accepts that exact qualification receipt. These go to
review:

- numerical flags;
- structural flags other than a lost response, including sign reversals
  and moves from zero to non-zero;
- construction flags;
- support flags (the separate `supported_years` gate fails a candidate that
  loses a year the previous certificate supported);
- coverage gains, coverage rows with no value on either side, and any other
  coverage row that is not a lost result or the record of a known gap;
- inertness flags on a measure-year the candidate does not list as inert,
  other than the record of a known gap;
- a receipt with no diff against a certified variant.

Unsupported years alone never fail. A move below the diff's bound raises
no numerical flag; it is reviewed only if another flag, such as a structural
one, fires on it.
