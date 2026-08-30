import pytest

from policyengine.scenarios import (
    CRFB_POST_OBBBA_TOB_SCENARIO_ID,
    CRFB_POST_OBBBA_TOB_TARGET_SHA256,
    CRFB_POST_OBBBA_TOB_TARGET_SOURCE,
    TRUSTEES_CORE_THRESHOLD_LAW_MODE,
    crfb_post_obbba_tob_contract,
    validate_crfb_post_obbba_tob_metadata,
)


def _valid_metadata(**overrides):
    metadata = {
        "name": CRFB_POST_OBBBA_TOB_TARGET_SOURCE,
        "scenario_id": CRFB_POST_OBBBA_TOB_SCENARIO_ID,
        "calibration_target_id": "post_obbba_calibrated_tob_75y",
        "baseline_kind": "calibration_target",
        "not_law": True,
        "law_mode": TRUSTEES_CORE_THRESHOLD_LAW_MODE,
        "sha256": CRFB_POST_OBBBA_TOB_TARGET_SHA256,
        "artifact_contract": {
            "must_consume_baseline_sha256": CRFB_POST_OBBBA_TOB_TARGET_SHA256,
            "must_expose_scenario_id": CRFB_POST_OBBBA_TOB_SCENARIO_ID,
            "reject_raw_current_law_substitution": True,
        },
    }
    metadata.update(overrides)
    return metadata


def test_crfb_post_obbba_tob_contract_names_target_and_law_mode():
    contract = crfb_post_obbba_tob_contract()

    assert contract.scenario_id == CRFB_POST_OBBBA_TOB_SCENARIO_ID
    assert contract.target_source == CRFB_POST_OBBBA_TOB_TARGET_SOURCE
    assert contract.target_sha256 == CRFB_POST_OBBBA_TOB_TARGET_SHA256
    assert contract.law_mode == TRUSTEES_CORE_THRESHOLD_LAW_MODE
    assert contract.not_law is True


def test_validate_crfb_post_obbba_tob_metadata_accepts_exact_contract():
    metadata = _valid_metadata()

    assert validate_crfb_post_obbba_tob_metadata(metadata) == metadata


def test_validate_crfb_post_obbba_tob_metadata_rejects_current_law_substitution():
    metadata = _valid_metadata(
        name="trustees_2025_current_law",
        baseline_kind="current_law_comparator",
        not_law=False,
        sha256="e059aa9fba806b260a399b8a6a18b892a6363ba12ee00fe21ab109d09dff0ec4",
    )

    with pytest.raises(ValueError, match="trustees_2025_current_law"):
        validate_crfb_post_obbba_tob_metadata(metadata)


def test_validate_crfb_post_obbba_tob_metadata_rejects_hash_mismatch():
    metadata = _valid_metadata(sha256="0" * 64)

    with pytest.raises(ValueError, match="sha256"):
        validate_crfb_post_obbba_tob_metadata(metadata)
