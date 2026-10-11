# UK Budget reform contract reports

Real reports from the UK Budget reform contract runner (workstream W1,
`policyengine.tax_benefit_models.uk.budget_reform_contract`, PolicyEngine/policyengine.py#577),
run on 11 October 2026. The qualification gate tests in `tests/test_uk_candidate_gates.py` read them.

- `pinned_uk_2.125.1_defects.json`: every case on policyengine-uk 2.125.1, the pinned model at the time, with `max_examples=2` and no dataset. The 66 failures and 35 errors are the dated-reform defects the contract was written to catch.
- `full_allpass_uk_2.126.8.json`: the full run the gate expects. Every route and case, seed 0, `max_examples=20`, and population checks on the certified `enhanced_frs_2024_25` (SHA-256 `5ba399ea…`). The model was policyengine-uk 2.126.8 from the policyengine-uk#2305 branch with core 3.33.0, a development combination rather than a certified pair, so treat its `versions` as fixture metadata. Result: 267 pass, 6 pending decision d1344, 67 unsupported with reasons, both properties passing, 13 of 13 population checks; 20.6 minutes, peak RSS 2.7 GB.
- `population_pass_max_examples_0.json`: population checks only, on the same dataset. It has no cases, and with `max_examples=0` its sampled properties did not run, so the gate treats it as an incomplete run.

The only edits: `dataset.path` (a local Hugging Face cache path) was replaced with a placeholder in the two files that name a dataset, and every file was re-serialized with sorted keys.
