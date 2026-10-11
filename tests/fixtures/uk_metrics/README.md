# UK metrics tool fixtures

`standard_reforms.yaml` is copied unchanged from PolicyEngine/policyengine-uk at
commit `fd944159ee27bd1a0f6a664bf537cb98d4b976ae`
(`policyengine_uk/utils/aggregate_impact/standard_reforms.yaml`), the commit the
qualification config pins the metrics tool to. It is the tool's standard reform
set: ten reforms, each with the model variable it must move, the direction and
the least it must move it in every year. The reform responsiveness gate reads
the same file from the vendored tool, and `tests/test_uk_candidate_gates.py`
reads this copy. Refresh it by copying from the newly pinned commit; never
edit it by hand.
