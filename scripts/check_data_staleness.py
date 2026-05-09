"""Flag when the bundled country release manifest falls behind upstream.

Each bundled country release manifest pins the country-model version the
certified microdata was built with. If that pin drifts behind the currently
installed country-model version, downstream calculations may diverge from what
the data was calibrated against. This script surfaces that drift so a CI job
or a human can decide whether to kick off a data rebuild.

Outputs a single-line verdict per country, plus a summary. Exits non-zero when
any country is stale so CI can gate on it.

No network access: reads both sides locally via ``importlib.metadata`` and the
packaged release manifest loader.
"""

from __future__ import annotations

import sys
from importlib import metadata
from importlib.util import find_spec

from policyengine.provenance.manifest import (
    CountryReleaseManifest,
    get_release_manifest,
)

COUNTRIES = ("us", "uk")


def load_release_manifest(country: str) -> CountryReleaseManifest:
    return get_release_manifest(country)


def check_country(country: str) -> tuple[str, bool]:
    """Return ``(one-line-verdict, is_stale)``."""
    manifest = load_release_manifest(country)

    pkg = manifest.model_package.name
    pinned = manifest.model_package.version

    if find_spec(pkg.replace("-", "_")) is None:
        return (
            f"{country}: {pkg} not installed; skipping staleness check",
            False,
        )

    try:
        installed = metadata.version(pkg)
    except metadata.PackageNotFoundError:
        return (
            f"{country}: {pkg} importable but package metadata not found; "
            "skipping staleness check",
            False,
        )

    if installed == pinned:
        return (
            f"{country}: ok ({pkg} {installed} matches bundle pin)",
            False,
        )
    return (
        f"{country}: STALE ({pkg} installed={installed}, "
        f"bundle pin={pinned}; consider a release-bundle refresh)",
        True,
    )


def main() -> int:
    verdicts = []
    any_stale = False
    for country in COUNTRIES:
        verdict, stale = check_country(country)
        verdicts.append(verdict)
        any_stale = any_stale or stale
    print("\n".join(verdicts))
    return 1 if any_stale else 0


if __name__ == "__main__":
    sys.exit(main())
