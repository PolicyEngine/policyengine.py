"""Factories for execution-contract tests."""

from datetime import datetime, timezone

from policyengine.execution import (
    ArtifactIdentity,
    ExecutionReceipt,
    PackageResolution,
    PackageVersion,
    RequestedExecutionAliases,
    ResolvedExecutionBundle,
    RuntimeIdentity,
)
from policyengine.provenance.manifest import get_release_manifest

REQUEST_SHA256 = "1" * 64
RESULT_SHA256 = "2" * 64
POPULATION_SHA256 = "3" * 64


def make_execution_receipt(*, run_id: str = "run-1") -> ExecutionReceipt:
    release = get_release_manifest("us")
    return ExecutionReceipt(
        requested=RequestedExecutionAliases(
            engine="default",
            bundle="latest",
            model="latest",
            data="certified",
            population="national",
            numeric_mode="default",
        ),
        resolved=ResolvedExecutionBundle(
            runtime=RuntimeIdentity(
                name="policyengine-core",
                version="3.30.0",
            ),
            numeric_mode="numpy-native",
            model=PackageResolution(
                actual=PackageVersion(
                    name="policyengine-us",
                    version="1.765.0",
                ),
                certified=PackageVersion.model_validate(
                    release.model_package.model_dump(mode="json")
                ),
            ),
            data=PackageResolution(
                actual=PackageVersion(name="populace-data", version="0.1.1"),
                certified=PackageVersion(
                    name=release.data_package.name,
                    version=release.data_package.version,
                    sha256=release.data_package.sha256,
                    wheel_url=release.data_package.wheel_url,
                ),
            ),
            population_artifact=ArtifactIdentity(
                name=release.default_dataset,
                uri=release.default_dataset_uri,
                revision=release.data_package.release_manifest_revision,
                sha256=POPULATION_SHA256,
                build_id=(
                    release.certification.data_build_id
                    if release.certification is not None
                    else None
                ),
            ),
            certified_release=release,
        ),
        run_id=run_id,
        created_at=datetime(2026, 7, 9, 12, 0, tzinfo=timezone.utc),
        request_sha256=REQUEST_SHA256,
        result_sha256=RESULT_SHA256,
    )
