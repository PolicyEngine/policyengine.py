"""Regression: ``PolicyEngineUKLatest`` / ``PolicyEngineUSLatest`` must not
raise on manifest-vs-installed version drift.

Previously both models raised ``ValueError`` on any version mismatch
between the bundled manifest and the installed country model. That
made every country-model bump — routine weekly work — require a
coordinated pypkg manifest update, and when downstream core tightened
parameter validation, every post-merge pypkg publish failed at import
time because the stale pins in the pypkg extras couldn't install
cleanly.

The check is now a ``UserWarning`` so calculations run against
whatever country-model version is installed.
"""

from __future__ import annotations

import warnings
from unittest.mock import patch

from policyengine.core.release_manifest import get_release_manifest
from policyengine.tax_benefit_models.uk.model import PolicyEngineUKLatest
from policyengine.tax_benefit_models.us.model import PolicyEngineUSLatest


def _pick_mismatched_version(manifest_version: str) -> str:
    # Pick a plausibly-parseable version that differs from the manifest.
    # We use .0 / .1 variants so the value is always distinct from the
    # bundled manifest's version string.
    return manifest_version + ".drift"


def test__given_uk_version_drift__then_warns_instead_of_raising():
    manifest_version = get_release_manifest("uk").model_package.version
    mismatched_version = _pick_mismatched_version(manifest_version)

    with patch(
        "policyengine.tax_benefit_models.uk.model.metadata.version",
        return_value=mismatched_version,
    ):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            PolicyEngineUKLatest()

    messages = [str(w.message) for w in caught if issubclass(w.category, UserWarning)]
    assert any("policyengine-uk" in m and mismatched_version in m for m in messages), (
        f"Expected UserWarning naming policyengine-uk + drift version; got: {messages}"
    )


def test__given_us_version_drift__then_warns_instead_of_raising():
    manifest_version = get_release_manifest("us").model_package.version
    mismatched_version = _pick_mismatched_version(manifest_version)

    with patch(
        "policyengine.tax_benefit_models.us.model.metadata.version",
        return_value=mismatched_version,
    ):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            PolicyEngineUSLatest()

    messages = [str(w.message) for w in caught if issubclass(w.category, UserWarning)]
    assert any("policyengine-us" in m and mismatched_version in m for m in messages), (
        f"Expected UserWarning naming policyengine-us + drift version; got: {messages}"
    )
