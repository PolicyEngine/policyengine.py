"""``verify_trace_tro`` — fetch-and-rehash verification of a TRO.

``trace-tro-validate`` checks structure against the JSON Schema; this
layer checks the substance: every artifact in the composition is
fetched from its arrangement location, rehashed, and compared against
the ``trov:sha256`` the TRO claims, and the composition fingerprint is
recomputed from the artifact hashes. This is the replication command a
third party runs instead of trusting us.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from policyengine.cli import main
from policyengine.provenance.trace import (
    canonical_json_bytes,
    compute_trace_composition_fingerprint,
)
from policyengine.provenance.verify import (
    verify_trace_tro,
    verify_trace_tro_path,
)


def _tro_for(
    artifacts: dict[str, tuple[str, str]],
    *,
    fingerprint: str | None = None,
) -> dict:
    """Build a minimal TRO graph: ``{artifact_id: (sha256, location)}``."""
    artifact_nodes = []
    location_nodes = []
    for artifact_id, (sha, location) in artifacts.items():
        full_id = f"composition/1/artifact/{artifact_id}"
        artifact_nodes.append(
            {
                "@id": full_id,
                "@type": "trov:ResearchArtifact",
                "trov:sha256": sha,
            }
        )
        location_nodes.append(
            {
                "@id": f"arrangement/1/location/{artifact_id}",
                "@type": "trov:ArtifactLocation",
                "trov:hasArtifact": {"@id": full_id},
                "trov:hasLocation": location,
            }
        )
    hashes = [sha for sha, _ in artifacts.values()]
    return {
        "@context": [{"trov": "https://w3id.org/trace/trov/0.1#"}],
        "@graph": [
            {
                "@id": "tro",
                "@type": "trov:TransparentResearchObject",
                "trov:hasComposition": {
                    "@id": "composition/1",
                    "@type": "trov:ArtifactComposition",
                    "trov:hasFingerprint": {
                        "@id": "composition/1/fingerprint",
                        "@type": "trov:CompositionFingerprint",
                        "trov:sha256": fingerprint
                        or compute_trace_composition_fingerprint(hashes),
                    },
                    "trov:hasArtifact": artifact_nodes,
                },
                "trov:hasArrangement": [
                    {
                        "@id": "arrangement/1",
                        "@type": "trov:ArtifactArrangement",
                        "trov:hasArtifactLocation": location_nodes,
                    }
                ],
            }
        ],
    }


def _file_artifact(tmp_path: Path, name: str, payload: bytes) -> tuple[str, str]:
    (tmp_path / name).write_bytes(payload)
    return hashlib.sha256(payload).hexdigest(), name


class TestVerifyTraceTRO:
    def test__given_matching_local_files__then_all_ok(self, tmp_path):
        tro = _tro_for(
            {
                "results": _file_artifact(tmp_path, "results.json", b"results"),
                "reform": _file_artifact(tmp_path, "reform.json", b"reform"),
            }
        )
        report = verify_trace_tro(tro, base_dir=tmp_path)
        assert report.fingerprint_status == "ok"
        assert {check.status for check in report.artifacts} == {"ok"}
        assert report.ok

    def test__given_corrupted_file__then_mismatch_and_not_ok(self, tmp_path):
        tro = _tro_for(
            {"results": _file_artifact(tmp_path, "results.json", b"results")}
        )
        (tmp_path / "results.json").write_bytes(b"tampered")
        report = verify_trace_tro(tro, base_dir=tmp_path)
        assert not report.ok
        assert report.artifacts[0].status == "mismatch"

    def test__given_https_location__then_fetcher_is_used(self, tmp_path):
        payload = b"remote bytes"
        sha = hashlib.sha256(payload).hexdigest()
        tro = _tro_for({"dataset": (sha, "https://example.org/dataset.h5")})
        fetched: list[str] = []

        def fetch(url: str) -> bytes:
            fetched.append(url)
            return payload

        report = verify_trace_tro(tro, base_dir=tmp_path, fetch=fetch)
        assert fetched == ["https://example.org/dataset.h5"]
        assert report.ok

    def test__given_unreachable_location__then_unfetchable_and_not_ok(self, tmp_path):
        tro = _tro_for({"dataset": ("a" * 64, "https://example.org/gone.h5")})

        def fetch(url: str) -> bytes:
            raise OSError("connection refused")

        report = verify_trace_tro(tro, base_dir=tmp_path, fetch=fetch)
        assert not report.ok
        check = report.artifacts[0]
        assert check.status == "unfetchable"
        assert "connection refused" in (check.detail or "")

    def test__given_skip__then_artifact_skipped_and_ok(self, tmp_path):
        tro = _tro_for(
            {
                "results": _file_artifact(tmp_path, "results.json", b"results"),
                "dataset": ("b" * 64, "https://example.org/restricted.h5"),
            }
        )

        def fetch(url: str) -> bytes:
            raise AssertionError("skipped artifacts must not be fetched")

        report = verify_trace_tro(tro, base_dir=tmp_path, fetch=fetch, skip={"dataset"})
        statuses = {check.artifact_id: check.status for check in report.artifacts}
        assert statuses == {"results": "ok", "dataset": "skipped"}
        assert report.ok

    def test__given_forged_fingerprint__then_fingerprint_mismatch(self, tmp_path):
        tro = _tro_for(
            {"results": _file_artifact(tmp_path, "results.json", b"results")},
            fingerprint="f" * 64,
        )
        report = verify_trace_tro(tro, base_dir=tmp_path)
        assert report.fingerprint_status == "mismatch"
        assert not report.ok

    def test__given_path_helper__then_base_dir_defaults_to_parent(self, tmp_path):
        tro = _tro_for(
            {"results": _file_artifact(tmp_path, "results.json", b"results")}
        )
        tro_path = tmp_path / "run.trace.tro.jsonld"
        tro_path.write_bytes(canonical_json_bytes(tro))
        report = verify_trace_tro_path(tro_path)
        assert report.ok

    def test__given_absolute_or_traversal_location__then_unfetchable(self, tmp_path):
        outside = tmp_path / "outside.json"
        outside.write_bytes(b"outside")
        sha = hashlib.sha256(b"outside").hexdigest()
        record_dir = tmp_path / "record"
        record_dir.mkdir()
        for location in (str(outside), "../outside.json"):
            tro = _tro_for({"results": (sha, location)})
            report = verify_trace_tro(tro, base_dir=record_dir)
            assert report.artifacts[0].status == "unfetchable", location
            assert not report.ok


class TestVerifyCLI:
    def test__given_valid_record__then_exit_zero_and_reports_ok(self, tmp_path, capsys):
        tro = _tro_for(
            {"results": _file_artifact(tmp_path, "results.json", b"results")}
        )
        tro_path = tmp_path / "run.trace.tro.jsonld"
        tro_path.write_bytes(canonical_json_bytes(tro))
        exit_code = main(["trace-tro-verify", str(tro_path)])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "ok: results" in captured.out
        assert "fingerprint: ok" in captured.out

    def test__given_tampered_record__then_exit_nonzero(self, tmp_path, capsys):
        tro = _tro_for(
            {"results": _file_artifact(tmp_path, "results.json", b"results")}
        )
        (tmp_path / "results.json").write_bytes(b"tampered")
        tro_path = tmp_path / "run.trace.tro.jsonld"
        tro_path.write_bytes(canonical_json_bytes(tro))
        exit_code = main(["trace-tro-verify", str(tro_path)])
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "mismatch" in captured.out.lower()

    def test__given_skip_flag__then_skipped_artifact_does_not_fail(
        self, tmp_path, capsys
    ):
        tro = _tro_for(
            {
                "results": _file_artifact(tmp_path, "results.json", b"results"),
                "dataset": ("c" * 64, "https://example.invalid/nope.h5"),
            }
        )
        tro_path = tmp_path / "run.trace.tro.jsonld"
        tro_path.write_bytes(canonical_json_bytes(tro))
        exit_code = main(["trace-tro-verify", str(tro_path), "--skip", "dataset"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "skipped: dataset" in captured.out


@pytest.fixture(autouse=True)
def _no_ci_env(monkeypatch):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
