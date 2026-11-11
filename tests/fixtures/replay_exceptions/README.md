# UK replay data-limited exception fixtures

The four `*2.134.7*.json` files are byte-for-byte copies of the Budget
coordinator's 17 October 2026 decision fixtures. They contain national
aggregates and provenance only, with no survey-level records. The archived
qualification receipt retains its original v1 policy and digest; it is
historical evidence, not a payload produced by the new gate.

The original replay request was not supplied. Tests preserve the archived
receipt and construct a request from its execution identity, then rebind and
reseal a copy. All integrity failures, corpus records and diff rows remain
unchanged. This tests the real regression evidence without claiming an
unavailable original request binding.

`main_replay_policy.py.txt` freezes the evaluator and its gap helper from
commit `3a278490102f`; `main_policy_metadata.json` records that commit's
policy id and text digest. Differential tests compare the complete gate
result against that oracle, removing only the new exception provenance
fields and the deliberately changed policy id/digest. A subprocess also
checks every replay evaluation in the existing contract suite, including
Hypothesis-generated receipts.
