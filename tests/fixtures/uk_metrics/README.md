# UK metrics tool fixtures

`reforms_config.yaml` is copied unchanged from PolicyEngine/policyengine-uk at
commit `073e80809141852eda42127b9e692b17e81343eb`
(`policyengine_uk/tests/microsimulation/reforms_config.yaml`), the commit the
qualification config pins the metrics tool to. It is the standard reform set
for the reform responsiveness gate: eight reforms, each with the change in
weighted government balance in 2029-30 (`expected_impact`, in GBP bn) recorded
from real runs on the certified pair. `tests/test_uk_candidate_gates.py` reads
it. Refresh it by copying from the newly pinned commit; never edit it by hand.
