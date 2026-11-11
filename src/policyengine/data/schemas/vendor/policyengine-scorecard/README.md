# Vendored policyengine-scorecard schemas

Copied unchanged from PolicyEngine/policyengine-scorecard, `main` at commit
`71cad306f37f7f9bfb4b58497ff9ddd78b396e00` (the merge of scorecard#183, which
added `diff.base_events` and the corpus grid lists;
`docs/uk_replay/schemas/`): the v1
pre-promotion replay interface between policyengine.py qualification (W4)
and the replay corpus (W6). `policyengine.provenance.qualification` mirrors
them, and `tests/test_qualification_contracts.py` checks the mirrors and the
schemas accept and reject the same documents. Refresh by copying from a newer
scorecard commit and updating the commit above; never edit them by hand.
