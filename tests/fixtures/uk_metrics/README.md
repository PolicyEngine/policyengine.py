# UK metrics tool fixtures

Both files come from PolicyEngine/policyengine-uk's aggregate-impact tool
(`policyengine_uk/utils/aggregate_impact/`, policyengine-uk#2335), which the
qualification config pins at commit
`9b33fe19f80676fc5b81d2d80b36072e1c2fc1df`. They were produced at its parent,
`bd8bff74c0baea19c09eedf9ce1391d598d2ffaf`; the pinned commit changes only
when the tool digest is taken (at module load rather than at the end of a
run), so `standard_reforms.yaml` is byte-identical there and the report format
is unchanged. A report from the pinned commit differs only in
`metrics_version`, which the gate compares between the two pairs' reports,
never against this file. `tests/test_uk_candidate_gates.py` reads them.
Refresh them when a pin changes the report; never edit them by hand.

- `standard_reforms.yaml`: the tool's standard reform set, copied unchanged.
  Ten reforms, each with the model variable it must move, the direction and
  the least it must move it in every year. The reform responsiveness gate
  reads the same file from the vendored tool.
- `budget_metrics_report.json`: a real `compute_budget_metrics` report from
  the tool's owner (workstream W3), run on 11 October 2026 at the pinned tool
  commit on uk-data 1.58.0 (`enhanced_frs_2024_25`) with policyengine-uk main,
  for 2025-26 to 2031-32, with the overlap guard and the ten standard reforms.
  It holds aggregates only: 1,470 metric rows and 346 checks (327 pass,
  15 warn, 4 fail), each check with its `failing_scopes`.
