"""Named CRFB long-run TOB scenario contracts."""

from __future__ import annotations

from typing import Any, Mapping

from pydantic import BaseModel, Field

CRFB_POST_OBBBA_TOB_SCENARIO_ID = "crfb_post_obbba_tob_75y"
CRFB_POST_OBBBA_TOB_TARGET_ID = "post_obbba_calibrated_tob_75y"
CRFB_POST_OBBBA_TOB_TARGET_SOURCE = "oact_2025_08_05_provisional"
CRFB_POST_OBBBA_TOB_TARGET_SHA256 = (
    "75e9dbe6a30680670713089ceed3eb10d7ef597b88c4317d0b39571e25f381f3"
)
TRUSTEES_CORE_THRESHOLD_LAW_MODE = "trustees-2025-core-thresholds-v1"


def _expected_artifact_contract() -> dict[str, Any]:
    return {
        "must_consume_baseline_sha256": CRFB_POST_OBBBA_TOB_TARGET_SHA256,
        "must_expose_scenario_id": CRFB_POST_OBBBA_TOB_SCENARIO_ID,
        "reject_raw_current_law_substitution": True,
    }


class CRFBPostOBBBATOBContract(BaseModel):
    """Reproducibility contract for the CRFB Post-OBBBA TOB target source."""

    scenario_id: str = CRFB_POST_OBBBA_TOB_SCENARIO_ID
    calibration_target_id: str = CRFB_POST_OBBBA_TOB_TARGET_ID
    target_source: str = CRFB_POST_OBBBA_TOB_TARGET_SOURCE
    target_sha256: str = CRFB_POST_OBBBA_TOB_TARGET_SHA256
    baseline_kind: str = "calibration_target"
    not_law: bool = True
    law_mode: str = TRUSTEES_CORE_THRESHOLD_LAW_MODE
    artifact_contract: dict[str, Any] = Field(
        default_factory=_expected_artifact_contract
    )

    def validate_metadata(self, metadata: Mapping[str, Any]) -> dict[str, Any]:
        errors = []
        checks = {
            "name": self.target_source,
            "scenario_id": self.scenario_id,
            "calibration_target_id": self.calibration_target_id,
            "baseline_kind": self.baseline_kind,
            "not_law": self.not_law,
            "law_mode": self.law_mode,
            "sha256": self.target_sha256,
        }
        for key, expected in checks.items():
            actual = metadata.get(key)
            if actual != expected:
                errors.append(f"{key}={actual!r}, expected {expected!r}")

        artifact_contract = metadata.get("artifact_contract")
        if artifact_contract != self.artifact_contract:
            errors.append(
                "artifact_contract does not match the CRFB Post-OBBBA TOB contract"
            )

        if errors:
            raise ValueError(
                "Invalid CRFB Post-OBBBA TOB scenario metadata: " + "; ".join(errors)
            )
        return dict(metadata)


def crfb_post_obbba_tob_contract() -> CRFBPostOBBBATOBContract:
    return CRFBPostOBBBATOBContract()


def validate_crfb_post_obbba_tob_metadata(
    metadata: Mapping[str, Any],
) -> dict[str, Any]:
    return crfb_post_obbba_tob_contract().validate_metadata(metadata)
