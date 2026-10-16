# Replay gate policy d1344-replay-regressions-v1

Decided under cos d1344 by workstream W4 on 15 October 2026, after two
independent reviews. The pull request that added this file records the
decision, the reviews and the alternatives considered.
`evaluate_replay_receipt` in `policyengine.provenance.qualification`
applies this text. Each qualification receipt records the policy id and
this file's SHA-256 in its `replay` gate details.

The replay gate fails on the regressions a scorecard replay receipt
identifies. It calls a gap known only on positive evidence from the
comparison base. It sends every other flagged move to a named reviewer.

## Fail

- A rejected request, `no_supported_years`, integrity `failed` (a crash or
  missing outputs, persistent or not), or a receipt not bound to the
  request.
- A mapping flag.
- A lost result: a coverage row with a base value and no candidate value.
- A lost response:
  - a measure-year the candidate lists as inert, unless it is a known gap;
  - a measure-year total at exactly £0 where the base's absolute value is
    at least the diff's bound, max(£1m, 1% of the base's absolute value),
    whether the base was positive or negative. A known gap never excuses
    this: a base whose record lists the measure-year as a gap cannot also
    hold a material value for it.
- An event whose supported grid is incomplete, unless every inert or
  missing and supported measure-year in it is a known gap. An incomplete
  event whose receipt does not list its missing measure-years fails, as
  does one that lists none. A receipt whose integrity is `incomplete` with
  no incomplete event also fails.
- A receipt that contradicts itself, including a complete event that lists
  an inert, or missing and supported, measure-year.

## Known gaps

A candidate measure-year that is inert, or missing and supported (in the
event's missing list and not its unsupported list), is a known gap only
when the receipt's base-side record for the same event (`diff.base_events`,
taken from the base's verified staging and run manifests) lists the same
measure and year as inert, or as missing and supported, in the base. The
gate records each known gap with the base's staging manifest SHA-256. A
legacy-layout base, or an event the base did not replay, has no record, so
none of its gaps are known.

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
  coverage row that is not a lost result;
- inertness flags on a measure-year the candidate does not list as inert;
- a receipt with no diff against a certified variant.

Unsupported years alone never fail. A move below the diff's bound raises
no flag and is not reviewed.
