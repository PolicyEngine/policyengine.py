# UK metrics tool fixtures

`standard_reforms.yaml` is copied unchanged from PolicyEngine/policyengine-uk at
commit `c7a6c963991b4873a51042bda640f28eb914e34e`
(`policyengine_uk/utils/aggregate_impact/standard_reforms.yaml`), the commit the
qualification config pins the metrics tool to. It is the tool's standard reform
set: ten reforms, each with the model variable it must move, the direction and
the least it must move it in every year. The reform responsiveness gate reads
the same file from the vendored tool, and `tests/test_uk_candidate_gates.py`
reads this copy. Refresh it by copying from the newly pinned commit; never
edit it by hand.
