# UK replay interface golden fixtures

Vendored unchanged from PolicyEngine/policyengine-scorecard at commit
`dc040de` (`tests/fixtures/uk_replay/`), the W6 side of the pre-promotion
replay interface. The scorecard computes digests with `rfc8785==0.1.4`;
`tests/test_canonical_json.py` checks that
`policyengine.provenance.canonical` produces the same bytes and digests.

Refresh by copying the files from a newer scorecard commit and updating the
commit above; never edit them by hand.
