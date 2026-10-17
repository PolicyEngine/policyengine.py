# UK Budget reform contract reports

Real reports from the UK Budget reform contract runner (workstream W1,
`policyengine.tax_benefit_models.uk.budget_reform_contract`, PolicyEngine/policyengine.py#577),
run on 11 October 2026. The qualification gate tests in `tests/test_uk_candidate_gates.py` read them.

- `pinned_uk_2.125.1_defects.json`: every case on policyengine-uk 2.125.1, the pinned model at the time, with `max_examples=2` and no dataset. The 66 failures and 35 errors are the dated-reform defects the contract was written to catch.
- `full_released_uk_2.135.0.json`: the full run of contract 2.0.0 (17 October 2026), the runner at policyengine.py#627's head f1f2431d9 (main merged in, #643 included), on policyengine-uk 2.135.0, which holds the d1344 statutory resumption (policyengine-uk#2423), with core 3.33.0. It covers every route and case, seed 0 and `max_examples=20`, with population checks on the certified `enhanced_frs_2024_25` (SHA-256 `056e80fd…`, the dataset of the certified pair). Result: 881 pass, 19 pending a methodology call (policyengine-uk#2396, the default capital gains response), 119 unsupported with reasons, both properties passing, 19 of 19 population rows. #651 changed only how the household route imports the UK model; its review found the output unchanged row for row. Its `versions` record policyengine 6.4.3, the stale metadata of the editable install that ran it; treat them as fixture metadata. The gate tests read it through the coverage the current runner module declares, and fail rather than skip when the runner's contract version moves past it. It replaces the 1.1.0 run on policyengine-uk 2.130.1, whose freeze checks contract 2.0.0 replaced.
- `population_pass_max_examples_0.json`: population checks only, on the earlier certified `enhanced_frs_2024_25` (uk-data 1.58.0, SHA-256 `5ba399ea…`). It has no cases, and with `max_examples=0` its sampled properties did not run, so the gate treats it as an incomplete run.

The edits:
- `dataset.path` (a local Hugging Face cache path) was replaced with a placeholder in the two files that name a dataset, and every file was re-serialized with sorted keys.
- Population rows are computed on the survey dataset, so a count from 1 to 9 in their `detail` is a small cell, which the metrics tool's `privacy.py` rule never publishes. Since policyengine.py#643 the runner suppresses them at source, so `full_released_uk_2.135.0.json` reads `"fewer than 10"` where they occur, and its population details agree across routes. No gate rule reads `detail`, and the qualification ledger (`publishable_contract_report`) publishes none of a population detail's values beyond its top-level true/false findings, since rows of one check on different routes share a subsample and their differences would give a handful's figures back. Check any new fixture for such counts before committing it.

The run of contract 1.0.0 on policyengine-uk 2.126.8 (`full_allpass_uk_2.126.8.json`) was removed once no test read it.
