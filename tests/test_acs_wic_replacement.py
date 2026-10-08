"""Keep the removal PR blocked until the actual replacement is certified."""

from policyengine.provenance.manifest import get_release_manifest


def test_certified_local_dataset_no_longer_uses_the_incomplete_wic_release():
    reference = get_release_manifest("us").datasets["populace_us_2024_acs_local"]
    # Do not skip this check or invent replacement identifiers. Microcosm #1154
    # must publish a complete dataset and its real certification must be added
    # here before the temporary ACS assumption can safely be removed.
    assert reference.revision != (
        "populace-us-2024-buildo-acs-local-767312d60-20260923T074941Z"
    ), "Blocked on Microcosm #1154: certify the replacement ACS-local release."
    assert reference.sha256 != (
        "769756c31f3ca646d12c272511744dec04c0e68870c6946dd945fbba65b6a7ec"
    ), "Blocked on Microcosm #1154: the incomplete dataset is still certified."
