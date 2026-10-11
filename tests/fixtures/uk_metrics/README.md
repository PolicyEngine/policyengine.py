# UK metrics tool fixtures

Both files come from PolicyEngine/policyengine-uk's aggregate-impact tool
(`policyengine_uk/utils/aggregate_impact/`, policyengine-uk#2335), which the
qualification config pins at commit
`bd8bff74c0baea19c09eedf9ce1391d598d2ffaf`.
`tests/test_uk_candidate_gates.py` reads them. Refresh them from the newly
pinned commit; never edit them by hand.

- `standard_reforms.yaml`: the tool's standard reform set, copied unchanged.
  Ten reforms, each with the model variable it must move, the direction and
  the least it must move it in every year. The reform responsiveness gate
  reads the same file from the vendored tool.
- `budget_metrics_report.json`: a real `compute_budget_metrics` report from
  the tool's owner (workstream W3), run on 11 October 2026 on uk-data 1.58.0
  (`enhanced_frs_2024_25`) with policyengine-uk main, for 2025-26 to 2031-32,
  with the overlap guard and the ten standard reforms. It holds aggregates
  only: 1,470 metric rows and 346 checks (327 pass, 15 warn, 4 fail). It was
  produced at tool commit `c7a6c963991b4873a51042bda640f28eb914e34e`, one
  commit before the pin; the only change since adds `failing_scopes` to each
  check row, so this report has no `failing_scopes`.
