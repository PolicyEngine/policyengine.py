# UK Budget reform contract reports

Real reports from the UK Budget reform contract runner (workstream W1,
`policyengine.tax_benefit_models.uk.budget_reform_contract`, PolicyEngine/policyengine.py#577),
run on 11 October 2026. The qualification gate tests in `tests/test_uk_candidate_gates.py` read them.

- `pinned_uk_2.125.1_defects.json`: every case on policyengine-uk 2.125.1, the pinned model at the time, with `max_examples=2` and no dataset. The 66 failures and 35 errors are the dated-reform defects the contract was written to catch.
- `full_allpass_uk_2.126.8.json`: the full run the gate expects. Every route and case, seed 0, `max_examples=20`, and population checks on the certified `enhanced_frs_2024_25` (SHA-256 `5ba399ea…`). The model was policyengine-uk 2.126.8 from the policyengine-uk#2305 branch with core 3.33.0, a development combination rather than a certified pair, so treat its `versions` as fixture metadata. Result: 267 pass, 6 pending decision d1344, 67 unsupported with reasons, both properties passing, 13 of 13 population checks; 20.6 minutes, peak RSS 2.7 GB.
- `full_released_uk_2.130.1.json`: the full run of contract 1.1.0 (16 October 2026), the runner at policyengine.py#574's head merged with main 8a303636, on the certified pair policyengine-uk 2.130.1 with core 3.33.0: every route and case, seed 0, `max_examples=20`, population checks on the certified `enhanced_frs_2024_25` (uk-data 1.58.1, SHA-256 `056e80fd…`). Result: 792 pass, 25 pending a methodology call (d1344 and policyengine-uk#2396), 101 unsupported with reasons, both properties passing, 19 of 19 population rows; 29.6 minutes, peak RSS 3.5 GB. Its `versions` record policyengine 6.4.0, the stale metadata of the editable install that ran it; treat them as fixture metadata. The gate tests read it through the coverage the current runner module declares, and fail rather than skip when the runner's contract version moves past it. It replaces the 1.0.0 run on policyengine-uk 2.126.12.
- `population_pass_max_examples_0.json`: population checks only, on the same dataset. It has no cases, and with `max_examples=0` its sampled properties did not run, so the gate treats it as an incomplete run.

The only edits: `dataset.path` (a local Hugging Face cache path) was replaced with a placeholder in the two files that name a dataset, and every file was re-serialized with sorted keys.
