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

We don't fully instantiate the classes here — their ``__init__`` goes
on to fetch the data-release manifest from Hugging Face (needs network
+ credentials), run dataset certification, and call the expensive
``TaxBenefitModelVersion.__init__`` that loads every parameter. We
just want to verify the version-mismatch branch switched from ``raise``
to ``warn``. We do that by calling the relevant ``__init__`` with the
downstream work mocked out.
"""

from __future__ import annotations

import warnings
from unittest.mock import patch

from policyengine.provenance.manifest import get_release_manifest


def _pick_mismatched_version(manifest_version: str) -> str:
    # Pick a value that's distinct from any real bundled manifest version.
    return manifest_version + ".drift"


def _run_init_version_check_branch(
    module_path: str,
    class_name: str,
    installed_version: str,
) -> list[warnings.WarningMessage]:
    """Exercise only the manifest-vs-installed version check in ``__init__``.

    Patches ``metadata.version`` to return ``installed_version``, and
    stubs everything the ``__init__`` calls after the version check so
    we don't hit the network or do heavy work. Returns the list of
    warnings emitted during the check.
    """
    with patch(f"{module_path}.metadata.version", return_value=installed_version):
        with patch(
            f"{module_path}.certify_data_release_compatibility",
            return_value=None,
        ):
            with patch(
                f"{module_path}._get_runtime_data_build_metadata",
                return_value={},
            ):
                # Prevent super().__init__ from actually running the
                # parameter-loading pipeline — we only care that the
                # version branch in our override emits a warning, not
                # an exception.
                with patch(
                    f"{module_path}.TaxBenefitModelVersion.__init__",
                    return_value=None,
                ):
                    # Import late so the patches above apply to the
                    # module-level names used by __init__.
                    import importlib

                    module = importlib.import_module(module_path)
                    cls = getattr(module, class_name)
                    with warnings.catch_warnings(record=True) as caught:
                        warnings.simplefilter("always")
                        # The class is a TaxBenefitModelVersion subclass
                        # that normally takes kwargs for the parameter
                        # tree. We're not exercising the parameter tree.
                        try:
                            cls()
                        except Exception:
                            # Any downstream exception (e.g. attribute
                            # access on the stubbed super) is irrelevant
                            # — the warning was already emitted before
                            # that point.
                            pass
                    return list(caught)


def test__given_uk_version_drift__then_warns_instead_of_raising():
    manifest_version = get_release_manifest("uk").model_package.version
    mismatched_version = _pick_mismatched_version(manifest_version)

    caught = _run_init_version_check_branch(
        module_path="policyengine.tax_benefit_models.uk.model",
        class_name="PolicyEngineUKLatest",
        installed_version=mismatched_version,
    )

    messages = [str(w.message) for w in caught if issubclass(w.category, UserWarning)]
    assert any("policyengine-uk" in m and mismatched_version in m for m in messages), (
        f"Expected UserWarning naming policyengine-uk + drift version; got: {messages}"
    )


def test__given_us_version_drift__then_warns_instead_of_raising():
    manifest_version = get_release_manifest("us").model_package.version
    mismatched_version = _pick_mismatched_version(manifest_version)

    caught = _run_init_version_check_branch(
        module_path="policyengine.tax_benefit_models.us.model",
        class_name="PolicyEngineUSLatest",
        installed_version=mismatched_version,
    )

    messages = [str(w.message) for w in caught if issubclass(w.category, UserWarning)]
    assert any("policyengine-us" in m and mismatched_version in m for m in messages), (
        f"Expected UserWarning naming policyengine-us + drift version; got: {messages}"
    )
