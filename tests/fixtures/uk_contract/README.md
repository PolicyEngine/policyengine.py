# UK Budget reform contract reports

Real reports from the UK Budget reform contract runner (workstream W1,
`policyengine.tax_benefit_models.uk.budget_reform_contract`, PolicyEngine/policyengine.py#577),
run on 11 October 2026. The qualification gate tests in `tests/test_uk_candidate_gates.py` read them.

- `pinned_uk_2.125.1_defects.json`: every case on policyengine-uk 2.125.1, the pinned model at the time, with `max_examples=2` and no dataset. The 66 failures and 35 errors are the dated-reform defects the contract was written to catch.
- `population_pass_max_examples_0.json`: population checks only, on a 1,000-household subsample of the certified `enhanced_frs_2024_25` (SHA-256 `5ba399ea…`), policyengine-uk 2.126.8. It has no cases, and with `max_examples=0` its sampled properties did not run. The tests use it as an incomplete run, and as the base of a synthetic all-pass report.

The only edit is in `population_pass_max_examples_0.json`: `dataset.path` (a local Hugging Face cache path) was replaced with a placeholder. Both files were re-serialized with sorted keys.
