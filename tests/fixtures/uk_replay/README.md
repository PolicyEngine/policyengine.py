# UK replay interface golden fixtures

Vendored unchanged from PolicyEngine/policyengine-scorecard at commit
`dc040de` (`tests/fixtures/uk_replay/`), the W6 side of the pre-promotion
replay interface. The scorecard computes digests with `rfc8785==0.1.4`;
`tests/test_canonical_json.py` checks that
`policyengine.provenance.canonical` produces the same bytes and digests.

Refresh by copying the files from a newer scorecard commit and updating the
commit above; never edit them by hand.

`receipt_6.4.1_attempt1/` holds the first real replay request and receipt, for
the pair policyengine 6.4.1, policyengine-uk 2.130.1 and uk-data 1.58.1. They
were copied unchanged from the scorecard's `replay-state` branch at commit
`4166508f` (`requests/<request_id>/`). The receipt holds aggregate fiscal
totals only. `tests/test_qualification_contracts.py` checks that the replay
policy fails it on exactly what the d1344 decision says it should.
