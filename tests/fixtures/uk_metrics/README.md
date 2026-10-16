# UK metrics tool fixtures

Both files come from PolicyEngine/policyengine-uk's aggregate-impact tool
(`policyengine_uk/utils/aggregate_impact/`, policyengine-uk#2335).
`tests/test_uk_candidate_gates.py` reads them. Refresh them when a pin changes
the report; never edit them by hand.

- `budget_metrics_report.json`: a real `compute_budget_metrics` report from
  the tool's owner (workstream W3), at tool commit
  `228a05a3e925beb50da619aa01e68c266e578fc0`, on the certified pair: uk-data
  1.58.1 (`enhanced_frs_2024_25`) with policyengine-uk 2.130.1 and
  policyengine-core 3.33.0, for 2025-26 to 2031-32, with the overlap guard and
  the ten standard reforms. It holds aggregates only, under the tool's
  small-cell rule (`privacy.py`): a figure from fewer than 10 records is
  published as `value` null with `suppressed` true, and every total that
  holds one is rebuilt without it and lists it under `excludes`. It has
  1,484 metric rows (14 suppressed: Disabled Students' Allowance's total and
  caseload in each of the seven years) and 350 checks.
- `standard_reforms.yaml`: the tool's standard reform set, copied unchanged.
  Ten reforms, each with the model variable it must move, the direction and
  the least it must move it in every year. The reform responsiveness gate
  reads the same file from the vendored tool.

This report replaces a 1.58.0 report from before the tool suppressed small
cells. That report published Disabled Students' Allowance, which comes from
fewer than 10 records, unsuppressed. Never commit a report from a tool
commit that predates suppression.
