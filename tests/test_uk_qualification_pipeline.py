"""Orchestration of UK candidate qualification (no network).

Invariants:

- resolution keeps the certified core when the model accepts it and never
  picks a prerelease, yanked or unpublished version;
- the decision never qualifies a pair main already certifies or one main
  supersedes, and never repeats a terminal attempt;
- rewriting the certified-version test constants leaves no old value behind
  and touches only quoted literals;
- the replay request built for a candidate is valid against the scorecard's
  vendored schema and binds the candidate commit, wheels and dataset;
- promotion planning readies only the selected target and closes exactly the
  candidates it or main supersede.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import jsonschema
import pytest

from policyengine.provenance.qualification import ReplayStatus
from policyengine.provenance.qualification_ledger import write_json
from policyengine.provenance.uk_qualification import (
    accept_review,
    assemble_receipt,
    build_replay_request,
    candidate_action,
    candidate_branch,
    certified_constant_replacements,
    choose_core_version,
    core_requirement,
    latest_data_release,
    plan_promotion,
    previous_certificate,
    read_replay,
    resolve_candidate,
    rewrite_certified_constants,
)
from tests.qualification_fixtures import (
    HARNESS,
    ISSUED,
    VENDORED_SCHEMAS,
    gates,
    golden,
    graphql_base_changes_output,
    jq,
    make_pair,
    make_receipt,
    rest_pulls_output,
    sha,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
BUNDLE = json.loads(
    (REPO_ROOT / "src/policyengine/data/bundle/manifest.json").read_text()
)


def _wheel(name, version, digest):
    return {
        "packagetype": "bdist_wheel",
        "filename": f"{name.replace('-', '_')}-{version}-py3-none-any.whl",
        "url": f"https://files.pythonhosted.org/packages/{name}-{version}.whl",
        "digests": {"sha256": digest},
    }


MANIFEST = {
    "schema_version": 1,
    "data_package": {"name": "policyengine-uk-data", "version": "1.58.0"},
    "default_datasets": {"national": "enhanced_frs_2024_25"},
    "build": {"build_id": "policyengine-uk-data-1.58.0"},
    "artifacts": {
        "enhanced_frs_2024_25": {
            "kind": "microdata",
            "path": "enhanced_frs_2024_25.h5",
            "repo_id": "policyengine/policyengine-uk-data-private",
            "revision": "1.58.0",
            "sha256": "d" * 64,
            "size_bytes": 128369110,
        }
    },
}


def _resolver(**overrides):
    projects = {
        "policyengine-uk": {
            "releases": {
                "2.126.6": [_wheel("policyengine-uk", "2.126.6", "1" * 64)],
                "2.126.8": [_wheel("policyengine-uk", "2.126.8", "2" * 64)],
                "2.127.0rc1": [_wheel("policyengine-uk", "2.127.0rc1", "3" * 64)],
                "2.127.1": [
                    {**_wheel("policyengine-uk", "2.127.1", "4" * 64), "yanked": True}
                ],
            }
        },
        "policyengine-uk/2.126.8": {
            "info": {"requires_dist": ["policyengine-core>=3.32.27"]}
        },
        "policyengine-uk/2.126.6": {
            "info": {"requires_dist": ["policyengine-core>=3.34.0"]}
        },
        "policyengine-core": {
            "releases": {
                v: [_wheel("policyengine-core", v, v.replace(".", "")[0] * 64)]
                for v in ("3.33.0", "3.34.0", "3.34.1", "3.35.0rc1")
            }
        },
    }
    manifest_bytes = json.dumps(MANIFEST).encode()
    kwargs = dict(
        current_core="3.33.0",
        pypi_project=lambda path: projects[path],
        hf_revision_sha=lambda repo, rev: "f" * 40,
        hf_tags=lambda repo: ["1.57.4", "1.58.0", "v1.11.1", "version_a"],
        hf_file=lambda repo, rev, path: manifest_bytes,
    )
    kwargs.update(overrides)
    return resolve_candidate(**kwargs), manifest_bytes


def test_a_pinned_core_is_used_exactly_or_refused():
    """A requalification names its exact core: the certified one, if the
    model accepts it, must not be chosen instead."""

    resolved, _ = _resolver(model_version="2.126.8", core_version="3.34.1")
    assert resolved.pair.core.version == "3.34.1"
    assert _resolver(model_version="2.126.8")[0].pair.core.version == "3.33.0"
    with pytest.raises(ValueError, match="not on PyPI"):
        _resolver(model_version="2.126.8", core_version="9.9.9")
    with pytest.raises(ValueError, match="requires policyengine-core"):
        _resolver(model_version="2.126.6", core_version="3.33.0")


def test_resolve_refuses_a_pair_other_than_the_one_requested(
    monkeypatch, tmp_path, capsys
):
    """A requalification or recovery dispatch names one pair. If its versions
    resolve to another (a moved data tag, another core), the run fails and
    nothing else is qualified."""

    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "check_uk_candidate_pair_pin",
        Path(__file__).resolve().parents[1] / "scripts" / "check_uk_candidate.py",
    )
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    pair = make_pair(model="2.200.0")
    resolved = cli.ResolvedCandidate(
        pair,
        cli.WheelFile("m.whl", "https://example.org/m.whl", pair.model.wheel_sha256),
        cli.WheelFile("c.whl", "https://example.org/c.whl", pair.core.wheel_sha256),
        "hf://model/example@pin/manifest.json",
        ">=3.33.0",
    )
    seen = {}
    monkeypatch.setattr(
        cli,
        "resolve_candidate",
        lambda **kwargs: seen.update(kwargs) or resolved,
    )
    monkeypatch.setattr(cli, "git", lambda *args: "a" * 40)
    outputs = []
    monkeypatch.setattr(cli, "set_output", lambda **kwargs: outputs.append(kwargs))
    out = tmp_path / "candidate.json"

    def args(pair_id):
        return SimpleNamespace(
            model_version="2.200.0",
            data_version="1.58.0",
            core_version="3.34.1",
            pair_id=pair_id,
            ledger=str(tmp_path),
            force=False,
            out=str(out),
        )

    assert cli.cmd_resolve(args("0" * 64)) == 1
    assert seen["core_version"] == "3.34.1"
    assert outputs[-1]["action"] == "mismatch"
    assert not out.exists()
    assert "not the requested" in capsys.readouterr().out
    assert cli.cmd_resolve(args(pair.pair_id)) == 0
    assert json.loads(out.read_text())["pair_id"] == pair.pair_id


def test_resolution_picks_newest_stable_and_keeps_an_accepted_core():
    resolved, manifest_bytes = _resolver()
    pair = resolved.pair
    assert pair.model.version == "2.126.8"
    assert pair.model.wheel_sha256 == "2" * 64
    assert pair.core.version == "3.33.0"
    assert pair.data.release_version == "1.58.0"
    assert pair.data.release_manifest_revision == "f" * 40
    assert (
        pair.data.release_manifest_sha256 == hashlib.sha256(manifest_bytes).hexdigest()
    )
    assert resolved.manifest_uri.startswith(
        "hf://model/policyengine/policyengine-uk-data-private@"
    )


def test_resolution_moves_core_only_when_the_model_requires_it():
    resolved, _ = _resolver(model_version="2.126.6")
    assert resolved.pair.core.version == "3.34.1"


def test_core_requirement_and_choice():
    assert (
        core_requirement(["numpy>=1", "policyengine_core>=3.32.27,<4"])
        == "<4,>=3.32.27"
    )
    with pytest.raises(ValueError):
        core_requirement(["numpy"])
    with pytest.raises(ValueError):
        choose_core_version("3.33.0", ">=9", [])


def test_latest_data_release_ignores_non_version_tags():
    assert latest_data_release(["1.57.4", "1.58.0", "v1.11.1", "version_a"]) == "1.58.0"


def test_resolution_refuses_unpublished_versions():
    with pytest.raises(ValueError):
        _resolver(model_version="9.9.9")


def test_actions(tmp_path):
    current = BUNDLE["data_releases"]["uk"]
    certified = make_pair(
        model=current["model_package"]["version"],
        data=current["data_package"]["version"],
        core=BUNDLE["packages"]["policyengine-core"]["version"],
        dataset_sha=current["certified_data_artifact"]["sha256"],
    )
    assert (
        candidate_action(certified, BUNDLE, tmp_path, base_commit="a" * 40)[0]
        == "already_certified"
    )
    older = make_pair(model="2.100.0", data="1.50.0", core="3.30.0")
    assert candidate_action(older, BUNDLE, tmp_path, base_commit="a" * 40)[0] == "stale"
    newer = make_pair(model="2.200.0", data="1.58.0", core="3.33.0")
    assert (
        candidate_action(newer, BUNDLE, tmp_path, base_commit="a" * 40)[0] == "qualify"
    )
    rejected = make_receipt(pair=newer, gate_results=gates(wheel_hashes="fail"))
    write_json(
        tmp_path / "uk" / newer.pair_id / "qualification_receipt.json",
        rejected.canonical_payload(),
    )
    assert (
        candidate_action(newer, BUNDLE, tmp_path, base_commit="a" * 40)[0]
        == "duplicate"
    )
    assert (
        candidate_action(newer, BUNDLE, tmp_path, base_commit="a" * 40, force=True)[0]
        == "qualify"
    )


def test_a_promotable_pair_on_a_superseded_baseline_requalifies_once_per_commit(
    tmp_path,
):
    """Automatic promotion needs a qualification against main's current
    certificate, so a promotable pair that advances main but compared
    against an earlier one is requalified without force, once per main
    commit. Nothing else is."""

    pair = _promotable_pair_and_branch()
    current = previous_certificate(BUNDLE)
    earlier = current.model_copy(update={"bundle_version": "earlier"})
    pair_dir = tmp_path / "uk" / pair.pair_id

    def publish(receipt, certificate=earlier):
        receipt = receipt.model_copy(update={"previous_certificate": certificate})
        write_json(pair_dir / "qualification_receipt.json", receipt.canonical_payload())

    def action(base):
        return candidate_action(pair, BUNDLE, tmp_path, base_commit=base * 40)[0]

    qualified = make_receipt(pair=pair)
    publish(qualified)
    verdict, reason = candidate_action(pair, BUNDLE, tmp_path, base_commit="b" * 40)
    assert verdict == "qualify" and "superseded baseline" in reason
    (pair_dir / "attempts" / ("b" * 12)).mkdir(parents=True)
    assert action("b") == "duplicate"
    assert action("c") == "qualify"
    needs_review = make_receipt(
        pair=pair, gate_results=gates(metrics_review="needs_review")
    ).model_copy(update={"previous_certificate": earlier})
    accepted = accept_review(
        needs_review,
        reviewer="reviewer",
        accepted_receipt_sha256=needs_review.unreviewed_sha256,
        explanation="expected",
        accepted_at="2026-10-16T09:00:00Z",
    )
    assert accepted.promotable
    publish(accepted)
    assert action("c") == "qualify"
    # Against main's own certificate, on main's own commit, or not
    # promotable: nothing to do.
    write_json(
        pair_dir / "latest_attempt.json", {"attempt_key": "c" * 12, "sequence": 3}
    )
    publish(qualified, current)
    assert action("c") == "duplicate"
    for results in (gates(metrics_review="needs_review"), gates(wheel_hashes="fail")):
        publish(make_receipt(pair=pair, gate_results=results))
        assert action("c") == "duplicate"
    # A pair that does not advance main in every component is never promoted.
    sideways = make_pair(
        model="2.200.0",
        data="1.50.0",
        core=BUNDLE["packages"]["policyengine-core"]["version"],
    )
    write_json(
        tmp_path / "uk" / sideways.pair_id / "qualification_receipt.json",
        make_receipt(pair=sideways)
        .model_copy(update={"previous_certificate": earlier})
        .canonical_payload(),
    )
    assert (
        candidate_action(sideways, BUNDLE, tmp_path, base_commit="c" * 40)[0]
        == "duplicate"
    )


def test_a_target_built_on_an_earlier_main_requalifies_one_attempt_at_a_time(
    tmp_path,
):
    """Promotion fast-forwards main to the qualified commit, so a promotable
    pair built on an earlier main commit is requalified on the current one:
    once per main commit, and never while another requalification runs."""

    from policyengine.provenance.qualification_ledger import attempt_directory
    from policyengine.provenance.uk_qualification import (
        requalification_target,
        stage_attempt,
    )

    pair = _promotable_pair_and_branch()
    pair_dir = tmp_path / "uk" / pair.pair_id
    qualified = _promotion_receipt(pair=pair)
    _publish_as_attempt(tmp_path, pair, qualified, "a" * 12)
    write_json(
        pair_dir / "latest_attempt.json", {"attempt_key": "a" * 12, "sequence": 0}
    )
    now = "2026-10-16T10:00:00Z"

    def action(base):
        return candidate_action(pair, BUNDLE, tmp_path, base_commit=base * 40, now=now)

    assert action("a")[0] == "duplicate"
    verdict, reason = action("b")
    assert verdict == "qualify" and "qualified on main aaaaaaaaaaaa" in reason
    assert requalification_target([qualified], BUNDLE, tmp_path, "b" * 40) == pair
    assert requalification_target([qualified], BUNDLE, tmp_path, "a" * 40) is None
    # A requalification from b runs; c arrives meanwhile and waits for it.
    stage_attempt(
        attempt_directory(tmp_path, "uk", pair.pair_id, "b" * 12),
        {"pair": pair.canonical_payload(), "pair_id": pair.pair_id},
        HARNESS,
        owner_run_id="7",
        staged_at="2026-10-16T09:30:00Z",
    )
    assert action("b")[0] == "duplicate"
    verdict, reason = action("c")
    assert verdict == "duplicate" and "in flight" in reason
    # Once it has finished (its receipt published), c requalifies.
    requalified = qualified.model_copy(update={"completed_at": "2026-10-16T11:00:00Z"})
    _publish_as_attempt(tmp_path, pair, requalified, "b" * 12)
    write_json(
        pair_dir / "latest_attempt.json", {"attempt_key": "b" * 12, "sequence": 1}
    )
    assert action("b")[0] == "duplicate"
    assert action("c")[0] == "qualify"
    # A repeat key on the same base names the same base.
    write_json(
        pair_dir / "latest_attempt.json",
        {"attempt_key": "c" * 12 + "-2", "sequence": 2},
    )
    assert requalification_target([requalified], BUNDLE, tmp_path, "c" * 40) is None


def test_a_pair_without_an_attempt_pointer_takes_its_base_from_its_attempt(tmp_path):
    """Round 2 of #635: a pair published before latest_attempt.json existed
    must not be stranded. Its base is the attempt whose own receipt is the
    published one; with no such attempt the base is unknown and stale."""

    from policyengine.provenance.uk_qualification import (
        qualified_base,
        requalification_target,
        stale_qualification,
    )

    pair = _promotable_pair_and_branch()
    pair_dir = tmp_path / "uk" / pair.pair_id
    qualified = _promotion_receipt(pair=pair)
    write_json(pair_dir / "qualification_receipt.json", qualified.canonical_payload())
    assert qualified_base(pair_dir) is None
    assert "unrecorded" in stale_qualification(qualified, BUNDLE, pair_dir, "a" * 40)
    assert requalification_target([qualified], BUNDLE, tmp_path, "a" * 40) == pair
    _publish_as_attempt(tmp_path, pair, qualified, "a" * 12 + "-2")
    assert qualified_base(pair_dir) == "a" * 12
    assert requalification_target([qualified], BUNDLE, tmp_path, "a" * 40) is None
    assert requalification_target([qualified], BUNDLE, tmp_path, "b" * 40) == pair


def test_runs_resolved_on_different_main_commits_never_both_stage(tmp_path):
    """Round 2 of #635: one attempt per pair at a time, whatever its base."""

    from policyengine.provenance.qualification_ledger import attempt_directory
    from policyengine.provenance.uk_qualification import stage_attempt

    pair = make_pair(model="2.200.0")
    now = "2026-10-16T10:00:00Z"
    assert (
        candidate_action(pair, BUNDLE, tmp_path, base_commit="a" * 40, now=now)[0]
        == "qualify"
    )
    stage_attempt(
        attempt_directory(tmp_path, "uk", pair.pair_id, "a" * 12),
        {"pair": pair.canonical_payload(), "pair_id": pair.pair_id},
        HARNESS,
        owner_run_id="7",
        staged_at="2026-10-16T09:30:00Z",
    )
    verdict, reason = candidate_action(
        pair, BUNDLE, tmp_path, base_commit="b" * 40, now=now
    )
    assert verdict == "duplicate" and "in flight" in reason
    # Abandoned (past its expiry), it no longer holds the pair.
    later = "2026-10-16T14:00:00Z"
    assert (
        candidate_action(pair, BUNDLE, tmp_path, base_commit="b" * 40, now=later)[0]
        == "qualify"
    )


def test_requalify_names_the_target_only_while_its_baseline_is_stale(
    monkeypatch, tmp_path, capsys
):
    import argparse
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "check_uk_candidate_requalify",
        Path(__file__).resolve().parents[1] / "scripts" / "check_uk_candidate.py",
    )
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    current = _promotion_receipt(pair=_promotable_pair_and_branch())
    stale = current.model_copy(
        update={
            "previous_certificate": current.previous_certificate.model_copy(
                update={"bundle_version": "earlier"}
            )
        }
    )
    monkeypatch.setattr(cli, "git", lambda *args: "a" * 40)
    write_json(
        tmp_path / "uk" / current.pair_id / "latest_attempt.json",
        {"attempt_key": "a" * 12, "sequence": 1},
    )
    for receipts, expected in (([stale], [stale.pair]), ([current], []), ([], [])):
        monkeypatch.setattr(cli, "latest_receipts", lambda root, r=receipts, **_: r)
        assert cli.cmd_requalify(argparse.Namespace(ledger=str(tmp_path))) == 0
        printed = [
            json.loads(line) for line in capsys.readouterr().out.splitlines() if line
        ]
        assert printed == [
            {"pair": pair.canonical_payload(), "pair_id": pair.pair_id}
            for pair in expected
        ]


def test_incomplete_pairs_requalify_on_a_new_base_only(tmp_path):
    pair = make_pair(model="2.200.0")
    incomplete = make_receipt(
        pair=pair, gate_results=gates(reform_contract="unavailable")
    )
    write_json(
        tmp_path / "uk" / pair.pair_id / "qualification_receipt.json",
        incomplete.canonical_payload(),
    )
    (tmp_path / "uk" / pair.pair_id / "attempts" / ("a" * 12)).mkdir(parents=True)
    assert (
        candidate_action(pair, BUNDLE, tmp_path, base_commit="a" * 40)[0] == "duplicate"
    )
    assert (
        candidate_action(pair, BUNDLE, tmp_path, base_commit="b" * 40)[0] == "qualify"
    )


def _new_record(old):
    new = json.loads(json.dumps(old))
    new["model_package"]["version"] = "2.126.8"
    new["certification"]["built_with_model_version"] = "2.126.0"
    new["certification"]["data_build_id"] = "policyengine-uk-data-1.59.0"
    new["data_package"]["version"] = "1.59.0"
    new["data_package"]["release_manifest_revision"] = "1" * 40
    return new


def test_constant_rewrite_leaves_no_old_values(tmp_path):
    for relative in (
        "tests/test_models.py",
        "tests/test_release_manifests.py",
        "tests/test_uk_regions.py",
    ):
        (tmp_path / relative).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPO_ROOT / relative, tmp_path / relative)
    old = BUNDLE["data_releases"]["uk"]
    new = _new_record(old)
    replacements = certified_constant_replacements(old, new)
    changed = rewrite_certified_constants(tmp_path, replacements)
    assert set(changed) == {
        "tests/test_models.py",
        "tests/test_release_manifests.py",
        "tests/test_uk_regions.py",
    }
    for relative in changed:
        text = (tmp_path / relative).read_text()
        for before, after in replacements:
            assert f'"{before}"' not in text and f'@{before}"' not in text
    manifests = (tmp_path / "tests/test_release_manifests.py").read_text()
    assert 'UK_MODEL_VERSION = "2.126.8"' in manifests
    assert 'UK_DATA_RELEASE_PATH = "releases/1.59.0/release_manifest.json"' in manifests
    assert 'UK_DATA_RELEASE_REVISION = "' + "1" * 40 + '"' in manifests
    assert rewrite_certified_constants(tmp_path, replacements) == []


@pytest.mark.parametrize("qualification_only", [False, True])
def test_preparation_generates_new_sidecars_and_verifies_the_exact_pair(
    tmp_path, monkeypatch, qualification_only
):
    """Run preparation, certification and real TRO generation without a network."""

    from policyengine.provenance import certification, manifest
    from policyengine.provenance.uk_qualification import prepare_candidate_commit

    monkeypatch.syspath_prepend(str(REPO_ROOT / "scripts"))
    import bundle as maintenance
    import certify_data_release as certify_script
    import generate_bundle_artifacts as artifacts
    import generate_trace_tros as tros

    release = json.loads(json.dumps(MANIFEST))
    release["build"].update(
        built_with_model_package={
            "name": "policyengine-uk",
            "version": "2.100.0" if qualification_only else "2.126.8",
        },
        built_with_core_package={
            "name": "policyengine-core",
            "version": "3.0.0" if qualification_only else "3.33.0",
        },
    )
    release_bytes = json.dumps(release).encode()
    resolved, _ = _resolver(hf_file=lambda *args: release_bytes)
    pair = resolved.pair
    bundle_dir = tmp_path / "src/policyengine/data/bundle"
    bundle_dir.mkdir(parents=True)
    source = json.loads(json.dumps(BUNDLE))
    source["data_releases"].pop("us")
    source["packages"].pop("policyengine-us")
    for packages in source["extras"].values():
        if "policyengine-us" in packages:
            packages.remove("policyengine-us")
    bundle_path = bundle_dir / "manifest.json"
    write_json(bundle_path, source)
    sidecar = bundle_dir / "uk.trace.tro.jsonld"
    old_sidecar = (
        REPO_ROOT / "src/policyengine/data/bundle/uk.trace.tro.jsonld"
    ).read_bytes()
    sidecar.write_bytes(old_sidecar)
    shutil.copy(REPO_ROOT / "pyproject.toml", tmp_path / "pyproject.toml")
    (tmp_path / "changelog.d").mkdir()
    for name in ("test_models.py", "test_release_manifests.py", "test_uk_regions.py"):
        (tmp_path / "tests").mkdir(exist_ok=True)
        shutil.copy(REPO_ROOT / "tests" / name, tmp_path / "tests" / name)

    def country_manifest(country):
        assert country == "uk"
        result = manifest.CountryReleaseManifest.model_validate(
            json.loads(bundle_path.read_text())["data_releases"][country]
        )
        result.source_sha256 = hashlib.sha256(bundle_path.read_bytes()).hexdigest()
        return result

    def data_manifest(country=None):
        result = manifest.DataReleaseManifest.model_validate_json(release_bytes)
        result.source_sha256 = hashlib.sha256(release_bytes).hexdigest()
        return result

    monkeypatch.setattr(certify_script, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(maintenance, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(artifacts, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(artifacts, "BUNDLE_MANIFEST", bundle_path)
    monkeypatch.setattr(artifacts, "PYPROJECT", tmp_path / "pyproject.toml")
    load_bundle = artifacts.load_bundle_manifest
    monkeypatch.setattr(
        artifacts, "load_bundle_manifest", lambda path=bundle_path: load_bundle(path)
    )
    monkeypatch.setattr(tros, "BUNDLE_MANIFEST", bundle_path)
    monkeypatch.setattr(tros, "BUNDLE_TRO_DIR", bundle_dir)
    monkeypatch.setattr(tros, "BUNDLE_LOCK", tmp_path / "uv.lock")
    monkeypatch.setattr(tros, "get_release_manifest", country_manifest)
    monkeypatch.setattr(tros, "get_data_release_manifest", data_manifest)
    monkeypatch.setattr(
        certification,
        "fetch_release_manifest",
        lambda uri, **kw: (
            data_manifest(),
            pair.data.release_manifest_sha256,
            certification.parse_manifest_uri(uri),
        ),
    )
    monkeypatch.setattr(
        certification,
        "fetch_pypi_wheel_metadata",
        lambda *args: {
            "sha256": pair.model.wheel_sha256,
            "url": resolved.model_wheel.url,
        },
    )
    monkeypatch.setattr(certification, "head_artifact", lambda *args, **kw: True)
    monkeypatch.setattr(
        certification, "required_supplemental_release_files", lambda *args: []
    )
    calls = []

    def run(command, *, cwd, env=None):
        calls.append(command)
        assert cwd == tmp_path
        if command[1] == "scripts/bundle.py":
            assert maintenance.main(command[2:]) == 0
        elif command[:2] == ["uv", "lock"]:
            (tmp_path / "uv.lock").write_text(
                "[[package]]\n"
                'name = "policyengine-uk"\n'
                f'version = "{pair.model.version}"\n'
                'source = { registry = "https://pypi.org/simple" }\n'
                f'wheels = [{{url = "{resolved.model_wheel.url}", hash = "sha256:{pair.model.wheel_sha256}"}}]\n'
            )
        else:
            assert command[1] == "scripts/release_lock.py"
        return subprocess.CompletedProcess(command, 0)

    prepared = prepare_candidate_commit(
        tmp_path, resolved, python=sys.executable, run=run, refresh_snapshots=False
    )
    assert sidecar.read_bytes() != old_sidecar
    assert pair.data.release_manifest_sha256.encode() in sidecar.read_bytes()
    assert prepared["compatibility_basis"] == (
        "qualified_exact_pair" if qualification_only else "built_with_model_package"
    )
    assert (tmp_path / prepared["changelog_fragment"]).is_file()
    assert maintenance.main(["check", "--include-tros", "--strict-tros"]) == 0
    assert calls[-1][2:] == ["check", "--include-tros", "--strict-tros"]
    if qualification_only:
        changed = json.loads(bundle_path.read_bytes())
        changed["packages"]["policyengine-core"]["version"] = "99.0.0"
        write_json(bundle_path, changed)
        with pytest.raises(ValueError, match="runtime core.*qualified exact pair"):
            tros.generated_tros(strict=True)


def test_replay_request_is_valid_for_the_scorecard():
    pair = make_pair()
    release_bundle = dict(
        golden("qualification_request_golden")["candidate"]["expected_release_bundle"]
    )
    request = build_replay_request(
        pair, HARNESS, release_bundle=release_bundle, issued_by=ISSUED
    )
    schema = json.loads(
        (VENDORED_SCHEMAS / "qualification_request.v1.json").read_text()
    )
    jsonschema.Draft202012Validator(schema).validate(request.document())
    candidate = request.document()["candidate"]
    assert candidate["policyengine"]["source"] == {
        "git": {
            "repository": "PolicyEngine/policyengine.py",
            "commit": HARNESS.git_commit,
        }
    }
    assert candidate["policyengine_uk"]["wheel_sha256"] == pair.model.wheel_sha256
    assert candidate["data"]["sha256"] == pair.data.dataset_sha256
    assert request.document()["requested_by"]["pair_id"] == pair.pair_id
    again = build_replay_request(
        pair, HARNESS, release_bundle=release_bundle, issued_by=ISSUED
    )
    assert again.request_id == request.request_id


def test_the_real_cli_generates_replay_requests_despite_country_import_suppression(
    tmp_path,
):
    """The real CLI can read the UK certificate despite automatic import suppression."""

    from importlib.util import find_spec

    if find_spec("policyengine_uk") is None:
        pytest.skip("Replay request generation requires the installed UK model")
    attempt = tmp_path / "attempt"
    write_json(attempt / "candidate.json", {"pair": make_pair().canonical_payload()})
    write_json(attempt / "harness.json", HARNESS.canonical_payload())
    env = dict(os.environ)
    env["POLICYENGINE_SKIP_COUNTRY_IMPORTS"] = "1"
    env.pop("GITHUB_OUTPUT", None)
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts/check_uk_candidate.py"),
            "request-replay",
            "--attempt",
            str(attempt),
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    request = json.loads((attempt / "replay/request.json").read_text())
    schema = json.loads(
        (VENDORED_SCHEMAS / "qualification_request.v1.json").read_text()
    )
    jsonschema.Draft202012Validator(schema).validate(request)
    candidate = request["candidate"]
    assert candidate["policyengine"]["source"]["git"]["commit"] == HARNESS.git_commit
    bundle = candidate["expected_release_bundle"]
    record = BUNDLE["data_releases"]["uk"]
    assert bundle["model_version"] == record["model_package"]["version"]
    assert bundle["data_version"] == record["data_package"]["version"]
    assert bundle["default_dataset"] == record["default_dataset"]


def test_reading_replay_state():
    pair = make_pair()
    request = build_replay_request(
        pair,
        HARNESS,
        release_bundle=golden("qualification_request_golden")["candidate"][
            "expected_release_bundle"
        ],
        issued_by=ISSUED,
    )
    gate, status, receipt = read_replay(
        request, fetch=lambda ref, path: None, state_ref="replay-state"
    )
    assert gate.status == "unavailable" and status is None
    running = ReplayStatus.model_validate(
        {
            "schema": "policyengine.uk-replay-status/v1",
            "request_id": request.request_id,
            "status": "running",
            "history": [
                {
                    "status": "running",
                    "at": "2026-10-15T10:00:00Z",
                    "run_url": "https://github.com/PolicyEngine/policyengine-scorecard/actions/runs/3",
                }
            ],
        }
    ).document()
    gate, status, _ = read_replay(
        request,
        fetch=lambda ref, path: (
            json.dumps(running).encode() if path.endswith("STATUS.json") else None
        ),
        state_ref="replay-state",
    )
    assert gate.status == "unavailable" and status.status == "running"
    terminal = {
        **running,
        "status": "complete",
        "receipt_sha256": "a" * 64,
        "receipt_commit": "c" * 40,
    }
    gate, _, _ = read_replay(
        request,
        fetch=lambda ref, path: (
            json.dumps(terminal).encode() if path.endswith("STATUS.json") else None
        ),
        state_ref="replay-state",
    )
    assert gate.status == "fail" and "no REPLAY_RECEIPT.json" in gate.summary


def test_assembled_receipt_without_replay_is_incomplete():
    pair = make_pair()
    local = [gate for gate in gates() if gate.gate_id != "replay"]
    receipt = assemble_receipt(
        pair,
        HARNESS,
        local,
        issued_by=ISSUED,
        completed_at="2026-10-15T10:00:00Z",
        previous=None,
        replay=None,
    )
    assert receipt.verdict == "incomplete"
    assert [gate.gate_id for gate in receipt.gates] == [gate.gate_id for gate in local]


def test_acceptance_is_bound_to_the_receipt():
    receipt = make_receipt(gate_results=gates(metrics_review="needs_review"))
    with pytest.raises(ValueError):
        accept_review(
            receipt,
            reviewer="maria",
            accepted_receipt_sha256=sha("1"),
            explanation="x",
            accepted_at="t",
        )
    reviewed = accept_review(
        receipt,
        reviewer="maria",
        accepted_receipt_sha256=receipt.unreviewed_sha256,
        explanation="Council tax move follows the 2025-26 band revaluation in uk-data.",
        accepted_at="2026-10-16T09:00:00Z",
    )
    assert reviewed.promotable
    with pytest.raises(ValueError):
        accept_review(
            make_receipt(),
            reviewer="m",
            accepted_receipt_sha256=sha("1"),
            explanation="x",
            accepted_at="t",
        )


def _promotion_receipt(**kwargs):
    return make_receipt(**kwargs).model_copy(
        update={"previous_certificate": previous_certificate(BUNDLE)}
    )


def test_promotion_plan():
    current = (
        BUNDLE["data_releases"]["uk"]["model_package"]["version"],
        BUNDLE["data_releases"]["uk"]["data_package"]["version"],
        BUNDLE["packages"]["policyengine-core"]["version"],
    )
    newest = _promotion_receipt(
        pair=make_pair(model="2.200.0", data=current[1], core=current[2])
    )
    older = _promotion_receipt(
        pair=make_pair(model="2.199.0", data=current[1], core=current[2])
    )
    rejected = _promotion_receipt(
        pair=make_pair(model="2.201.0", data=current[1], core=current[2]),
        gate_results=gates(replay="fail"),
    )
    stale = _promotion_receipt(
        pair=make_pair(model="2.0.0", data="1.0.0", core="3.0.0")
    )
    branches = {
        candidate_branch(r.pair): r.harness.git_commit
        for r in (newest, older, rejected, stale)
    }
    branches["candidate/uk/unknown"] = "0" * 40
    plan = plan_promotion([newest, older, rejected, stale], BUNDLE, branches)
    assert plan.target == newest
    assert plan.ready_branch == candidate_branch(newest.pair)
    assert plan.ready_commit == newest.harness.git_commit
    assert plan.close_branches == sorted(
        [candidate_branch(older.pair), candidate_branch(stale.pair)]
    )
    assert candidate_branch(rejected.pair) not in plan.close_branches


def _promotable_pair_and_branch(core=None):
    current = BUNDLE["data_releases"]["uk"]["data_package"]["version"]
    core = core or BUNDLE["packages"]["policyengine-core"]["version"]
    return make_pair(model="2.200.0", data=current, core=core)


def test_pairs_that_share_versions_never_share_a_branch():
    """Interrupted review of #574: a qualified pair readied the branch of an
    incomplete pair with the same model and data but another core."""

    qualified_pair = _promotable_pair_and_branch()
    other_core = _promotable_pair_and_branch(core="3.99.0")
    assert qualified_pair.pair_id != other_core.pair_id
    assert candidate_branch(qualified_pair) != candidate_branch(other_core)
    assert qualified_pair.pair_id[:12] in candidate_branch(qualified_pair)
    qualified = _promotion_receipt(pair=qualified_pair)
    incomplete = make_receipt(pair=other_core, gate_results=gates(replay="unavailable"))
    plan = plan_promotion(
        [qualified, incomplete],
        BUNDLE,
        {candidate_branch(other_core): incomplete.harness.git_commit},
    )
    assert plan.target == qualified
    assert plan.ready_branch is None
    assert "has no open pull request" in plan.reason


def test_a_branch_that_moved_off_the_qualified_commit_is_not_promoted():
    """The replayed and tested commit must be the promoted commit."""

    qualified = _promotion_receipt(pair=_promotable_pair_and_branch())
    branch = candidate_branch(qualified.pair)
    plan = plan_promotion([qualified], BUNDLE, {branch: "f" * 40})
    assert plan.target == qualified and plan.ready_branch is None
    assert "not the qualified commit" in plan.reason
    plan = plan_promotion([qualified], BUNDLE, {branch: qualified.harness.git_commit})
    assert plan.ready_branch == branch


CODE = ".github/workflows/pr_code_changes.yaml"


def _check(name, status="completed", conclusion="success", id=1):
    return {"id": id, "name": name, "status": status, "conclusion": conclusion}


def _run(event, status="completed", conclusion="success", id=1, path=CODE):
    return {
        "id": id,
        "path": path,
        "event": event,
        "status": status,
        "conclusion": conclusion,
    }


CHECKS_PASSED = [
    _check("Lint", id=1),
    _check("Test (3.13)", id=2),
    _check("Docs", conclusion="skipped", id=3),
]
RUNS_PASSED = [_run("pull_request", id=10), _run("workflow_dispatch", id=11)]


def _gh_api_output(argv, checks, runs, commit, branch):
    """What the fake `gh api` prints: the call's own jq applied by the real
    jq to an API-shaped page. Each run is the candidate's own (its commit,
    branch and this repository) unless it says otherwise, with its repository
    as the API's object; each check's suite id sits under `check_suite`, as
    in the API (rounds 5 and 6 of #635: fakes that returned every field, or
    picked fields by name, let a dropped field or a wrong source path pass).
    None for an unreadable list."""

    if "check-runs" in argv[2]:
        if checks is None:
            return None
        page = {
            "check_runs": [
                {
                    **{k: v for k, v in check.items() if k != "check_suite_id"},
                    "check_suite": {"id": check.get("check_suite_id")},
                }
                for check in checks
            ]
        }
    else:
        if runs is None:
            return None
        page = {
            "workflow_runs": [
                {
                    "head_sha": commit,
                    "head_branch": branch,
                    **run,
                    "head_repository": {
                        "full_name": run.get(
                            "head_repository", "PolicyEngine/policyengine.py"
                        )
                    },
                }
                for run in runs
            ]
        }
    return jq(argv[argv.index("--jq") + 1], page)


def _gh_pr_list_output(argv, listing):
    """What the fake `gh pr list` prints, filtering as gh does: by state
    (open unless the call says), base, head branch, a `head:` search prefix,
    then the limit (30 unless the call names one); each pull request cut to
    the `--json` fields, and the call's `--jq` applied by the real jq. A
    listing item is open and to main unless it says otherwise."""

    def option(name, default=None):
        return argv[argv.index(name) + 1] if name in argv else default

    state = option("--state", "open")
    base = option("--base")
    head = option("--head")
    search = option("--search", "")
    prefix = search.removeprefix("head:") if search.startswith("head:") else None
    fields = set(option("--json").split(","))
    matched = [
        pr
        for pr in ({"state": "OPEN", "baseRefName": "main", **pr} for pr in listing)
        if (state == "all" or pr["state"] == state.upper())
        and (base is None or pr["baseRefName"] == base)
        and (head is None or pr["headRefName"] == head)
        and (prefix is None or pr["headRefName"].startswith(prefix))
    ][: int(option("--limit", "30"))]
    printed = [{k: v for k, v in pr.items() if k in fields} for pr in matched]
    expression = option("--jq")
    return jq(expression, printed) if expression else json.dumps(printed)


# Each: checks, runs, branch at the commit, main ("parent" or "moved"), the
# push's exit code, automatic; then whether it is promoted, and the readiness
# calls made ("ready" or "undo") in order.
PROMOTION_CASES = {
    "everything passed": (
        CHECKS_PASSED,
        RUNS_PASSED,
        True,
        "parent",
        0,
        True,
        True,
        ["ready"],
    ),
    "a test still running": (
        [*CHECKS_PASSED[:1], _check("Test (3.13)", "in_progress", None, id=4)],
        RUNS_PASSED,
        True,
        "parent",
        0,
        True,
        False,
        ["undo"],
    ),
    "a test failed": (
        [*CHECKS_PASSED[:1], _check("Test (3.13)", conclusion="failure", id=4)],
        RUNS_PASSED,
        True,
        "parent",
        0,
        True,
        False,
        ["undo"],
    ),
    "an older cancelled run a newer success replaced": (
        [*CHECKS_PASSED, _check("Test (3.13)", conclusion="cancelled", id=0)],
        # The API lists newest first.
        [*RUNS_PASSED, _run("pull_request", conclusion="cancelled", id=9)],
        True,
        "parent",
        0,
        True,
        True,
        ["ready"],
    ),
    "a newer failure after an older success": (
        [*CHECKS_PASSED, _check("Test (3.13)", conclusion="failure", id=9)],
        RUNS_PASSED,
        True,
        "parent",
        0,
        True,
        False,
        ["undo"],
    ),
    "no run on the candidate's own tree": (
        CHECKS_PASSED,
        RUNS_PASSED[:1],
        True,
        "parent",
        0,
        True,
        False,
        ["undo"],
    ),
    "the own-tree run still registering its jobs": (
        CHECKS_PASSED[:1],
        [RUNS_PASSED[0], _run("workflow_dispatch", "in_progress", None, id=11)],
        True,
        "parent",
        0,
        True,
        False,
        ["undo"],
    ),
    "no checks yet": ([], RUNS_PASSED, True, "parent", 0, True, False, ["undo"]),
    # Round 3 of #635: a dispatch cancelled while queued has no jobs and so
    # no checks; the run itself must still block.
    "the own-tree run cancelled with no jobs": (
        CHECKS_PASSED,
        [RUNS_PASSED[0], _run("workflow_dispatch", conclusion="cancelled", id=11)],
        True,
        "parent",
        0,
        True,
        False,
        ["undo"],
    ),
    # Round 3 of #635: a replaced run re-run later gets newer check ids; its
    # checks must not count, whatever they conclude.
    "a replaced run's re-run checks": (
        [
            {**_check("Lint", id=1), "check_suite_id": 100},
            {**_check("Test (3.13)", id=2), "check_suite_id": 100},
            {**_check("Own tree", id=3), "check_suite_id": 110},
            {
                **_check("Test (3.13)", conclusion="failure", id=50),
                "check_suite_id": 90,
            },
        ],
        [
            {**_run("pull_request", id=10), "check_suite_id": 100},
            {**_run("workflow_dispatch", id=11), "check_suite_id": 110},
            {**_run("pull_request", conclusion="failure", id=9), "check_suite_id": 90},
        ],
        True,
        "parent",
        0,
        True,
        True,
        ["ready"],
    ),
    # An app's check outside any workflow run still counts.
    "an app's failing check": (
        [
            {**_check("Lint", id=1), "check_suite_id": 100},
            {**_check("External", conclusion="failure", id=5), "check_suite_id": 500},
        ],
        [
            {**_run("pull_request", id=10), "check_suite_id": 100},
            {**_run("workflow_dispatch", id=11), "check_suite_id": 110},
        ],
        True,
        "parent",
        0,
        True,
        False,
        ["undo"],
    ),
    # Round 5 of #635: the runs listed at a commit include any other pull
    # request's at it, a fork's included. A newer failing run of a fork, or of
    # another branch here, and its checks neither block the candidate ...
    "a fork's newer failing run at the commit": (
        [
            {**_check("Lint", id=1), "check_suite_id": 100},
            {**_check("Own tree", id=3), "check_suite_id": 110},
            {**_check("Lint", conclusion="failure", id=60), "check_suite_id": 200},
        ],
        [
            {**_run("pull_request", id=10), "check_suite_id": 100},
            {**_run("workflow_dispatch", id=11), "check_suite_id": 110},
            {
                **_run("pull_request", conclusion="failure", id=20),
                "check_suite_id": 200,
                "head_repository": "someone/policyengine.py",
            },
        ],
        True,
        "parent",
        0,
        True,
        True,
        ["ready"],
    ),
    "another branch's newer failing run at the commit": (
        [
            {**_check("Lint", id=1), "check_suite_id": 100},
            {**_check("Own tree", id=3), "check_suite_id": 110},
            {**_check("Lint", conclusion="failure", id=60), "check_suite_id": 200},
        ],
        [
            {**_run("pull_request", id=10), "check_suite_id": 100},
            {**_run("workflow_dispatch", id=11), "check_suite_id": 110},
            {
                **_run("pull_request", conclusion="failure", id=20),
                "check_suite_id": 200,
                "head_branch": "candidate/uk/other",
            },
        ],
        True,
        "parent",
        0,
        True,
        True,
        ["ready"],
    ),
    # ... nor stand in for a run of its own.
    "only a fork's run on the candidate's tree": (
        [
            {**_check("Lint", id=1), "check_suite_id": 100},
            {**_check("Own tree", id=3), "check_suite_id": 200},
        ],
        [
            {**_run("pull_request", id=10), "check_suite_id": 100},
            {
                **_run("workflow_dispatch", id=20),
                "check_suite_id": 200,
                "head_repository": "someone/policyengine.py",
            },
        ],
        True,
        "parent",
        0,
        True,
        False,
        ["undo"],
    ),
    "the checks could not be read": (
        None,
        RUNS_PASSED,
        True,
        "parent",
        0,
        True,
        False,
        ["undo"],
    ),
    "the branch moved": (
        CHECKS_PASSED,
        RUNS_PASSED,
        False,
        "parent",
        0,
        True,
        False,
        ["undo"],
    ),
    "main moved since the base": (
        CHECKS_PASSED,
        RUNS_PASSED,
        True,
        "moved",
        0,
        True,
        False,
        ["undo"],
    ),
    "main moved at the push": (
        CHECKS_PASSED,
        RUNS_PASSED,
        True,
        "parent",
        1,
        True,
        False,
        ["ready", "undo"],
    ),
    "manual promotion, on the base": (
        None,
        None,
        True,
        "parent",
        0,
        False,
        False,
        ["ready"],
    ),
    "manual promotion, main moved": (
        None,
        None,
        True,
        "moved",
        0,
        False,
        False,
        ["undo"],
    ),
}


@pytest.mark.parametrize("case", sorted(PROMOTION_CASES))
def test_promotion_makes_main_exactly_the_qualified_commit(
    monkeypatch, tmp_path, capsys, case
):
    """Round 2 of #635. A candidate is readied only while main is still the
    commit it was built on, so no merge can combine it with other code.
    Automatic promotion waits for the commit's own tree to pass its checks
    (the newest run of each workflow, the newest check of each name), then
    moves main to it with a push leased on that parent."""

    import argparse
    import importlib.util

    checks, runs, at_commit, main, push_code, automatic, promotes, readiness = (
        PROMOTION_CASES[case]
    )
    qualified = _promotion_receipt(pair=_promotable_pair_and_branch())
    branch = candidate_branch(qualified.pair)
    commit = qualified.harness.git_commit
    parent = "p" * 40
    spec = importlib.util.spec_from_file_location(
        "check_uk_candidate_for_test",
        Path(__file__).resolve().parents[1] / "scripts" / "check_uk_candidate.py",
    )
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    calls = []

    target = {
        "number": 1,
        "headRefName": branch,
        "headRefOid": commit,
        "isDraft": True,
        "isCrossRepository": False,
    }

    def run(argv, **kwargs):
        calls.append(argv)
        out = ""
        code = 0
        if argv[:3] == ["gh", "api", "graphql"]:
            out = graphql_base_changes_output(argv, set())
        elif argv[:2] == ["gh", "api"] and argv[4:5] == [f"{_REPO}/pulls"]:
            out = rest_pulls_output(argv, [target])
        elif argv[:2] == ["gh", "api"]:
            printed = _gh_api_output(argv, checks, runs, commit, branch)
            if printed is None:
                code = 1
            else:
                out = printed
        elif argv[:3] == ["git", "rev-parse", "FETCH_HEAD"]:
            out = commit if at_commit else "f" * 40
        elif argv[:3] == ["git", "rev-parse", f"{commit}^"]:
            out = parent
        elif argv[:2] == ["git", "ls-remote"]:
            out = f"{parent if main == 'parent' else 'm' * 40}\trefs/heads/main\n"
        elif argv[:2] == ["git", "push"]:
            code = push_code
        return SimpleNamespace(returncode=code, stdout=out, stderr="")

    monkeypatch.setattr(cli, "latest_receipts", lambda root, **_: [qualified])
    monkeypatch.setattr(cli, "subprocess", SimpleNamespace(run=run))
    monkeypatch.setattr(cli, "config", lambda: {"promotion": {"automatic": automatic}})
    monkeypatch.setattr(cli, "_candidate_pull_requests", lambda: [target])
    assert cli.cmd_promote(argparse.Namespace(ledger=str(tmp_path), apply=True)) == 0
    assert [
        "undo" if "--undo" in argv else "ready"
        for argv in calls
        if argv[:3] == ["gh", "pr", "ready"]
    ] == readiness
    pushes = [argv for argv in calls if argv[:2] == ["git", "push"]]
    reaches_push = "ready" in readiness and automatic
    assert pushes == (
        [
            [
                "git",
                "push",
                f"--force-with-lease=refs/heads/main:{parent}",
                "origin",
                f"{commit}:refs/heads/main",
            ]
        ]
        if reaches_push
        else []
    )
    assert not [argv for argv in calls if argv[:3] == ["gh", "pr", "merge"]]
    if not automatic:
        assert not [argv for argv in calls if argv[:2] == ["gh", "api"]]
    assert (f"promoted {branch}" in capsys.readouterr().out) is promotes


@pytest.mark.parametrize("undo_fails", [False, True])
def test_promotion_returns_every_other_ready_candidate_to_draft(
    monkeypatch, tmp_path, undo_fails
):
    """Round 3 of #635: only the plan's target may be ready, so a candidate
    left ready by a run whose undo failed, or by older code, is returned to
    draft; a failed return to draft fails the run so it is seen."""

    import argparse

    cli, calls, branch = _sweep_cli(
        monkeypatch, path="main moved", failing={"2", "1"} if undo_fails else set()
    )
    status = cli.cmd_promote(argparse.Namespace(ledger=str(tmp_path), apply=True))
    undone = [argv[3] for argv in calls if argv[:3] == ["gh", "pr", "ready"]]
    # The stale one (the draft and the fork's are left alone), then the target
    # by _promote (main moved), each by number.
    assert undone == ["2", "1"]
    assert status == (1 if undo_fails else 0)


SUPERSEDED_PAIR = make_pair(model="2.0.0", data="1.0.0", core="3.0.0")
_REPO = "repos/PolicyEngine/policyengine.py"


def _sweep_cli(
    monkeypatch,
    *,
    path,
    failing,
    checks=None,
    runs=None,
    push_code=1,
    extra=(),
    superseded=False,
    shared_fails=None,
    base_changed=(),
):
    """The promote CLI over a real `gh pr list` payload: the target (#1,
    ready), a stale same-repository candidate (#2, ready), a draft (#3), a
    fork's pull request with the stale branch's name (#4, ready), a fork's
    with the target's branch name at another commit (#5, ready) and a ready
    one whose listing lacks the fork field (#6), then ``extra`` (each may
    use "{branch}" and "{commit}" for the target's). ``superseded`` adds a
    receipt for an older pair with an open pull request (#9), which the plan
    closes. ``failing`` names the pull request numbers whose undo fails;
    ``path`` is "main moved", "lease rejected" or "main at the parent";
    ``base_changed`` names the pull requests whose base was ever changed;
    ``shared_fails`` fails the REST listing of a branch's pull requests
    ("listing") or the base-change query ("history")."""

    import importlib.util

    qualified = _promotion_receipt(pair=_promotable_pair_and_branch())
    branch = candidate_branch(qualified.pair)
    commit = qualified.harness.git_commit
    receipts = [qualified]
    if superseded:
        receipts.append(_promotion_receipt(pair=SUPERSEDED_PAIR))
    stale = "candidate/uk/stale-pair"
    spec = importlib.util.spec_from_file_location(
        "check_uk_candidate_for_test",
        Path(__file__).resolve().parents[1] / "scripts" / "check_uk_candidate.py",
    )
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    calls = []
    listing = [
        {
            "number": 1,
            "headRefName": branch,
            "headRefOid": commit,
            "isDraft": False,
            "isCrossRepository": False,
        },
        {
            "number": 2,
            "headRefName": stale,
            "headRefOid": "s" * 40,
            "isDraft": False,
            "isCrossRepository": False,
        },
        {
            "number": 3,
            "headRefName": "candidate/uk/draft",
            "headRefOid": "d" * 40,
            "isDraft": True,
            "isCrossRepository": False,
        },
        {
            "number": 4,
            "headRefName": stale,
            "headRefOid": "f" * 40,
            "isDraft": False,
            "isCrossRepository": True,
        },
        {
            "number": 5,
            "headRefName": branch,
            "headRefOid": "c" * 40,
            "isDraft": False,
            "isCrossRepository": True,
        },
        {
            "number": 6,
            "headRefName": "candidate/uk/unknown",
            "headRefOid": "u" * 40,
            "isDraft": False,
        },
        *(
            {
                key: value.format(branch=branch, commit=commit)
                if isinstance(value, str)
                else value
                for key, value in pr.items()
            }
            for pr in extra
        ),
    ]
    if superseded:
        listing.append(
            {
                "number": 9,
                "headRefName": candidate_branch(SUPERSEDED_PAIR),
                "headRefOid": "o" * 40,
                "isDraft": True,
                "isCrossRepository": False,
            }
        )

    def run(argv, **kwargs):
        calls.append(argv)
        out, code = "", 0
        if argv[:3] == ["gh", "pr", "list"]:
            out = _gh_pr_list_output(argv, listing)
        elif argv[:3] == ["gh", "api", "graphql"]:
            if shared_fails == "history":
                code = 1
            else:
                out = graphql_base_changes_output(argv, set(base_changed))
        elif argv[:2] == ["gh", "api"] and argv[4:5] == [f"{_REPO}/pulls"]:
            if shared_fails == "listing":
                code = 1
            else:
                out = rest_pulls_output(argv, listing)
        elif argv[:2] == ["gh", "api"]:
            out = _gh_api_output(
                argv, checks or CHECKS_PASSED, runs or RUNS_PASSED, commit, branch
            )
        elif argv[:3] == ["git", "rev-parse", "FETCH_HEAD"]:
            out = commit
        elif argv[:3] == ["git", "rev-parse", f"{commit}^"]:
            out = "p" * 40
        elif argv[:2] == ["git", "ls-remote"]:
            main = "m" * 40 if path == "main moved" else "p" * 40
            out = main + "\trefs/heads/main\n"
        elif argv[:2] == ["git", "push"]:
            code = push_code  # 1: the lease is rejected (main moved at the push)
        elif argv[:3] == ["gh", "pr", "ready"] and "--undo" in argv:
            code = 1 if argv[3] in failing else 0
        return SimpleNamespace(returncode=code, stdout=out, stderr="")

    monkeypatch.setattr(cli, "latest_receipts", lambda root, **_: receipts)
    monkeypatch.setattr(cli, "subprocess", SimpleNamespace(run=run))
    monkeypatch.setattr(cli, "config", lambda: {"promotion": {"automatic": True}})
    return cli, calls, branch


@pytest.mark.parametrize("path", ["main moved", "lease rejected"])
@pytest.mark.parametrize("failing", [set(), {"2"}, {"1"}])
def test_each_failed_return_to_draft_fails_the_run(
    monkeypatch, tmp_path, path, failing
):
    """Round 4 of #635: the sweep's failed undo and the target's failed undo
    (whether main moved or the lease was rejected) each fail the run alone.
    Round 5: every readiness change goes by number, on same-repository pull
    requests only; a fork's with the target's branch name neither changes the
    target's commit nor is touched, and one whose listing lacks the fork
    field counts as a fork's."""

    import argparse

    cli, calls, branch = _sweep_cli(monkeypatch, path=path, failing=failing)
    candidates = cli._candidate_pull_requests()
    assert [pr["number"] for pr in candidates] == [1, 2, 3]
    assert {pr["headRefName"]: pr["headRefOid"] for pr in candidates}[branch] != (
        "c" * 40
    )
    status = cli.cmd_promote(argparse.Namespace(ledger=str(tmp_path), apply=True))
    readiness = [
        ("undo" if "--undo" in argv else "ready", argv[3])
        for argv in calls
        if argv[:3] == ["gh", "pr", "ready"]
    ]
    target = (
        [("undo", "1")] if path == "main moved" else [("ready", "1"), ("undo", "1")]
    )
    assert readiness == [("undo", "2"), *target]
    assert status == (1 if failing else 0)
    listing = next(argv for argv in calls if argv[:3] == ["gh", "pr", "list"])
    assert listing[listing.index("--limit") + 1] == str(cli.PULL_REQUEST_LIMIT)


@pytest.mark.parametrize(("listed", "refused"), [(999, False), (1000, True)])
def test_a_candidate_listing_at_its_limit_is_refused(monkeypatch, listed, refused):
    """Round 5 of #635: gh stops a pull request search at its limit, so a
    listing that reaches it may have missed the target; promotion refuses to
    go on rather than act on part of the list."""

    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "check_uk_candidate_for_test",
        Path(__file__).resolve().parents[1] / "scripts" / "check_uk_candidate.py",
    )
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    listing = [
        {
            "number": number,
            "headRefName": f"candidate/uk/pair-{number}",
            "headRefOid": "a" * 40,
            "isDraft": True,
            "isCrossRepository": False,
        }
        for number in range(1, 1201)
    ]

    def run(argv, **kwargs):
        return SimpleNamespace(
            returncode=0, stdout=_gh_pr_list_output(argv, listing[:listed]), stderr=""
        )

    monkeypatch.setattr(cli, "subprocess", SimpleNamespace(run=run))
    assert cli.PULL_REQUEST_LIMIT == 1000
    if refused:
        with pytest.raises(SystemExit, match="::error::1000 open pull requests"):
            cli._candidate_pull_requests()
    else:
        assert len(cli._candidate_pull_requests()) == listed


OTHER_BASE = {
    "number": 7,
    "headRefName": "{branch}",
    "headRefOid": "{commit}",
    "baseRefName": "release",
    "isDraft": False,
    "isCrossRepository": False,
}


def _other(**fields):
    return {**OTHER_BASE, **fields}


FORKS = [
    _other(number=100 + n, baseRefName="main", isCrossRepository=True)
    for n in range(40)
]

# Each: other pull requests from the target's branch, the numbers whose base
# was ever changed, whether promotion refuses the target, and the pull
# request the refusal names.
SHARED_BRANCH_CASES = {
    "open, to another base": ([_other()], (), True, 7),
    "open, to another base, its head not yet updated": (
        [_other(headRefOid="a" * 40)],
        (),
        True,
        7,
    ),
    "closed at the commit, to another base": ([_other(state="CLOSED")], (), True, 7),
    "merged at the commit, to another base": ([_other(state="MERGED")], (), True, 7),
    "closed at another commit, to another base": (
        [_other(state="CLOSED", headRefOid="a" * 40)],
        (),
        False,
        None,
    ),
    "a fork's, open, to another base": (
        [_other(isCrossRepository=True)],
        (),
        False,
        None,
    ),
    "closed at the commit, to main": (
        [_other(state="CLOSED", baseRefName="main")],
        (),
        False,
        None,
    ),
    # Round 7 of #635: a base change does not change what a pull request's
    # earlier runs tested, so one now to main that ever had another base
    # counts, the candidate's own included.
    "closed at the commit, to main after a base change": (
        [_other(state="CLOSED", baseRefName="main")],
        (7,),
        True,
        7,
    ),
    "closed at another commit, to main after a base change": (
        [_other(state="CLOSED", baseRefName="main", headRefOid="a" * 40)],
        (7,),
        False,
        None,
    ),
    "the candidate's own, to main after a base change": ([], (1,), True, 1),
    # Round 7: forks' pull requests with the branch's name, however many,
    # neither crowd out nor stand in for this repository's.
    "forty forks', to main, with its branch name": (FORKS, (), False, None),
    "forty forks' and one to another base": (FORKS + [_other()], (), True, 7),
}


def _run_reads(calls):
    """The calls that read a commit's runs or checks."""

    return [
        argv
        for argv in calls
        if argv[:2] == ["gh", "api"]
        and ("actions/runs" in argv[2] or "check-runs" in argv[2])
    ]


@pytest.mark.parametrize("case", sorted(SHARED_BRANCH_CASES))
def test_a_candidate_whose_runs_may_have_tested_another_base_is_refused(
    monkeypatch, tmp_path, capsys, case
):
    """Round 6 of #635: a pull request from the candidate branch to another
    base runs the same workflows with the same commit, branch and repository,
    and GitHub's runs do not say which pull request they are for, so its
    failure could strand the candidate and its success hide the candidate's
    failure. While one is open, or after one closed at this commit, the
    candidate is kept draft and the run fails with an error naming it; the
    other pull request is never readied, undone or counted as a candidate.
    Round 7: the same holds for a pull request now to main whose base was
    ever changed, and forks' pull requests cannot crowd out the listing of
    this repository's."""

    import argparse

    extra, base_changed, refused, named = SHARED_BRANCH_CASES[case]
    cli, calls, branch = _sweep_cli(
        monkeypatch,
        path="main at the parent",
        failing=set(),
        push_code=0,
        extra=extra,
        base_changed=base_changed,
    )
    assert 7 not in [pr["number"] for pr in cli._candidate_pull_requests()]
    status = cli.cmd_promote(argparse.Namespace(ledger=str(tmp_path), apply=True))
    output = capsys.readouterr().out
    pushes = [argv for argv in calls if argv[:2] == ["git", "push"]]
    readiness = [argv[3] for argv in calls if argv[:3] == ["gh", "pr", "ready"]]
    assert "7" not in readiness
    if refused:
        assert status == 1 and not pushes
        assert f"::error::{branch} is not promoted" in output
        assert f"#{named} (" in output
        assert readiness == ["2", "1"]
        assert not _run_reads(calls)
    else:
        assert status == 0 and len(pushes) == 1
        assert f"promoted {branch}" in output


@pytest.mark.parametrize("how", ["listing", "history"])
def test_unreadable_pull_requests_from_the_candidate_branch_wait(
    monkeypatch, tmp_path, capsys, how
):
    """Round 6 of #635: when the candidate branch's pull requests (round 7:
    or a base-change history) cannot be read, the candidate waits as a draft
    without reading its runs."""

    import argparse

    cli, calls, branch = _sweep_cli(
        monkeypatch,
        path="main at the parent",
        failing=set(),
        push_code=0,
        shared_fails=how,
    )
    assert cli.cmd_promote(argparse.Namespace(ledger=str(tmp_path), apply=True)) == 0
    output = capsys.readouterr().out
    assert "could not be read" in output and "::error::" not in output
    assert not [argv for argv in calls if argv[:2] == ["git", "push"]]
    assert not _run_reads(calls)
    assert [argv[3] for argv in calls if argv[:3] == ["gh", "pr", "ready"]] == [
        "2",
        "1",
    ]


def test_only_pull_requests_to_main_are_candidates(monkeypatch):
    """Round 6 of #635: the listing asks gh for pull requests to main and
    drops any other it returns, so two pull requests from one candidate
    branch cannot collapse into one entry that sends readiness changes to
    the wrong one."""

    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "check_uk_candidate_for_test",
        Path(__file__).resolve().parents[1] / "scripts" / "check_uk_candidate.py",
    )
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    calls = []
    listing = [
        {
            "number": number,
            "baseRefName": base,
            "headRefName": "candidate/uk/2.200.0-1.58.9",
            "headRefOid": "a" * 40,
            "isDraft": False,
            "isCrossRepository": False,
        }
        for number, base in ((1, "release"), (2, "main"))
    ]

    def run(argv, **kwargs):
        calls.append(argv)
        # A gh that ignored --base: the script still keeps only main's.
        return SimpleNamespace(returncode=0, stdout=json.dumps(listing), stderr="")

    monkeypatch.setattr(cli, "subprocess", SimpleNamespace(run=run))
    assert [pr["number"] for pr in cli._candidate_pull_requests()] == [2]
    assert calls[0][calls[0].index("--base") + 1] == "main"


def test_superseded_candidates_are_closed_by_number(monkeypatch, tmp_path):
    """Round 6 of #635: closing a superseded candidate goes by its number,
    like every other write to a pull request."""

    import argparse

    cli, calls, branch = _sweep_cli(
        monkeypatch,
        path="main at the parent",
        failing=set(),
        push_code=0,
        superseded=True,
    )
    assert cli.cmd_promote(argparse.Namespace(ledger=str(tmp_path), apply=True)) == 0
    assert [argv[3] for argv in calls if argv[:3] == ["gh", "pr", "close"]] == ["9"]


NOW = "2026-10-16T12:00:00Z"
RECENT = "2026-10-16T06:00:00Z"
OLD = "2026-09-15T11:00:00Z"

# Each: the own-tree run's status, conclusion, attempt and creation time;
# whether the candidate is stranded (waits on a run refresh will not re-run).
STRANDED_CASES = {
    "failed, attempts left": ("completed", "failure", 3, RECENT, False),
    "failed at the cap": ("completed", "failure", 4, RECENT, True),
    "timed out, attempts left": ("completed", "timed_out", 1, RECENT, False),
    "cancelled, attempts left": ("completed", "cancelled", 2, RECENT, False),
    # Round 5 of #635: refresh re-runs only failed, timed-out and cancelled
    # runs, and GitHub only within 30 days, so these wait on nothing.
    "waiting on an approval": ("completed", "action_required", 1, RECENT, True),
    "skipped": ("completed", "skipped", 1, RECENT, True),
    "stale": ("completed", "stale", 1, RECENT, True),
    "failed past GitHub's re-run window": ("completed", "failure", 1, OLD, True),
    "failed just inside the window": (
        "completed",
        "failure",
        1,
        "2026-09-16T12:00:01Z",
        False,
    ),
    # Round 6: GitHub re-runs a run exactly 30 days old, and not one a
    # second older.
    "failed exactly 30 days ago": (
        "completed",
        "failure",
        1,
        "2026-09-16T12:00:00Z",
        False,
    ),
    "failed 30 days and a second ago": (
        "completed",
        "failure",
        1,
        "2026-09-16T11:59:59Z",
        True,
    ),
    # Unfinished runs and successes are not stranded at any attempt.
    "in progress at the cap": ("in_progress", None, 4, OLD, False),
    "queued past the window": ("queued", None, 1, OLD, False),
}


@pytest.mark.parametrize("case", sorted(STRANDED_CASES))
def test_a_candidate_waiting_on_runs_refresh_will_not_rerun_fails_the_run(
    monkeypatch, tmp_path, capsys, case
):
    """Round 4 of #635: refresh re-runs a run until MAX_RUN_ATTEMPTS, then
    stops; a candidate still waiting on it would otherwise wait unseen, so
    the promote run fails with an error naming it. Round 5: the same holds
    for any finished, unsuccessful run refresh will not re-run (a result it
    does not re-run, or one past GitHub's 30-day window). Otherwise it waits
    quietly, kept draft."""

    import argparse
    import datetime

    status_, conclusion, attempt, created, stranded = STRANDED_CASES[case]
    runs = [
        _run("pull_request", id=10),
        {
            **_run("workflow_dispatch", status_, conclusion, id=11),
            "run_attempt": attempt,
            "created_at": created,
        },
    ]
    cli, calls, branch = _sweep_cli(
        monkeypatch, path="main at the parent", failing=set(), runs=runs
    )
    monkeypatch.setattr(
        cli,
        "_now",
        lambda: datetime.datetime.fromisoformat(NOW.replace("Z", "+00:00")),
    )
    assert cli.MAX_RUN_ATTEMPTS == 4
    status = cli.cmd_promote(argparse.Namespace(ledger=str(tmp_path), apply=True))
    output = capsys.readouterr().out
    assert status == (1 if stranded else 0)
    assert ("::error::" in output) is stranded
    if stranded:
        assert branch in output and "will not re-run" in output
    assert [argv for argv in calls if argv[:2] == ["git", "push"]] == []
    # The target waits as a draft (round 4: one a person left ready).
    assert [argv[3] for argv in calls if argv[:3] == ["gh", "pr", "ready"]] == [
        "2",
        "1",
    ]


@pytest.mark.parametrize("other_waiting", [False, True])
def test_a_success_on_the_last_attempt_is_not_stranded(
    monkeypatch, tmp_path, capsys, other_waiting
):
    """Round 5 of #635: a run that passes on its last allowed attempt is not
    stranded, whether the candidate then promotes or still waits on another
    run."""

    import argparse

    runs = [
        _run("pull_request", "in_progress", None, id=10)
        if other_waiting
        else _run("pull_request", id=10),
        {**_run("workflow_dispatch", id=11), "run_attempt": 4, "created_at": OLD},
    ]
    cli, calls, branch = _sweep_cli(
        monkeypatch, path="main at the parent", failing=set(), runs=runs, push_code=0
    )
    assert cli.cmd_promote(argparse.Namespace(ledger=str(tmp_path), apply=True)) == 0
    output = capsys.readouterr().out
    assert "::error::" not in output
    assert (f"promoted {branch}" in output) is not other_waiting
    if other_waiting:
        assert f"automatic promotion waits for {branch}" in output


def test_a_failed_return_to_draft_while_waiting_fails_the_run(
    monkeypatch, tmp_path, capsys
):
    """Round 5 of #635: on the waiting path the target goes back to draft;
    if that fails, a ready pull request is left that a merge could combine
    with other code, so the run fails (with nothing stranded)."""

    import argparse

    runs = [
        _run("pull_request", id=10),
        _run("workflow_dispatch", "in_progress", None, id=11),
    ]
    cli, calls, branch = _sweep_cli(
        monkeypatch, path="main at the parent", failing={"1"}, runs=runs
    )
    assert cli.cmd_promote(argparse.Namespace(ledger=str(tmp_path), apply=True)) == 1
    output = capsys.readouterr().out
    assert "::error::could not return 1 to draft" in output
    assert "will not re-run" not in output
    assert [argv for argv in calls if argv[:2] == ["git", "push"]] == []


def test_automatic_promotion_is_on_with_its_basis_recorded():
    config = json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "src/policyengine/data/qualification/uk.json"
        ).read_text()
    )
    assert config["promotion"]["automatic"] is True
    assert "d1344" in config["promotion"]["decision"]


def test_promotion_requires_the_current_supported_years_baseline(monkeypatch):
    """C passed against A, but loses the year B added before C finished."""

    from policyengine.provenance.certification import (
        BASIS_QUALIFIED_PAIR,
        build_bundle_data_release_payload,
        build_country_manifest_payload,
    )
    from policyengine.provenance.manifest import (
        CountryReleaseManifest,
        DataReleaseManifest,
    )
    from policyengine.provenance.uk_candidate import supported_years

    core = BUNDLE["packages"]["policyengine-core"]["version"]
    pair_b = make_pair(model="2.131.0", data="1.58.2", core=core)
    pair_c = make_pair(model="2.132.0", data="1.58.3", core=core)
    years_a = list(range(2025, 2032))
    years_b = list(range(2025, 2033))
    monkeypatch.setattr(
        "policyengine.provenance.uk_candidate.data_year", lambda _: 2024
    )

    def gate(pair, years, previous_years):
        return supported_years(
            pair,
            Path("projected.h5"),
            required_years=years_a[:-1],
            budget_horizon_years=years_a[1:],
            previous_supported_years=previous_years,
            projected_years=lambda _: years,
        )[0]

    gate_b = gate(pair_b, years_b, years_a)
    gate_c = gate(pair_c, years_a, years_a)
    assert gate_b.status == gate_c.status == "pass"
    assert gate(pair_c, years_a, years_b).status == "fail"
    receipt_b = _promotion_receipt(
        pair=pair_b,
        gate_results=[gate_b if g.gate_id == "supported_years" else g for g in gates()],
    )
    receipt_c = _promotion_receipt(
        pair=pair_c,
        gate_results=[gate_c if g.gate_id == "supported_years" else g for g in gates()],
    )
    assert receipt_b.promotable and receipt_c.promotable

    release = json.loads(json.dumps(MANIFEST))
    release["data_package"]["version"] = pair_b.data.release_version
    release["build"]["build_id"] = pair_b.data.build_id
    release["artifacts"][pair_b.data.dataset]["revision"] = pair_b.data.dataset_revision
    manifest = DataReleaseManifest.model_validate(release)
    uri_parts = {
        "repo_id": pair_b.data.repo_id,
        "repo_type": pair_b.data.repo_type,
        "path": pair_b.data.release_manifest_path,
        "revision": pair_b.data.release_manifest_revision,
    }
    country = build_country_manifest_payload(
        country="uk",
        manifest=manifest,
        uri_parts=uri_parts,
        policyengine_version=BUNDLE["policyengine_version"],
        model_package=pair_b.model.name,
        model_version=pair_b.model.version,
        model_wheel={"sha256": pair_b.model.wheel_sha256},
        compatibility_basis=BASIS_QUALIFIED_PAIR,
        core_version=core,
        qualified_pair_id=pair_b.pair_id,
    )
    record_b = build_bundle_data_release_payload(
        country_payload=country,
        data_producer="populace",
        manifest_uri=f"hf://model/{pair_b.data.repo_id}@{pair_b.data.release_manifest_revision}/{pair_b.data.release_manifest_path}",
        uri_parts=uri_parts,
    )
    CountryReleaseManifest.model_validate(record_b)
    current_b = json.loads(json.dumps(BUNDLE))
    current_b["data_releases"]["uk"] = record_b
    branches = {candidate_branch(pair_c): receipt_c.harness.git_commit}

    assert plan_promotion([receipt_b, receipt_c], BUNDLE, branches).ready_branch
    plan = plan_promotion([receipt_b, receipt_c], current_b, branches)
    assert plan.target == receipt_c
    assert plan.ready_branch is None and plan.ready_commit is None
    assert "requalif" in plan.reason and plan.requalify == receipt_c.pair


@pytest.mark.parametrize(
    "field",
    [None, *type(previous_certificate(BUNDLE)).model_fields],
)
def test_promotion_binds_every_previous_certificate_field(field):
    qualified = _promotion_receipt(pair=_promotable_pair_and_branch())
    previous = qualified.previous_certificate
    if field is None:
        previous = None
    else:
        value = getattr(previous, field)
        if field in {"dataset_reference", "release_manifest_reference"}:
            value = value.model_copy(update={"revision": "0" * 40})
        elif field.endswith("sha256") or field == "qualification_pair_id":
            value = "0" * 64
        else:
            value = "different"
        previous = previous.model_copy(update={field: value})
    stale = qualified.model_copy(update={"previous_certificate": previous})
    plan = plan_promotion(
        [stale], BUNDLE, {candidate_branch(stale.pair): stale.harness.git_commit}
    )
    assert plan.target == stale
    assert plan.ready_branch is None and plan.ready_commit is None
    assert "requalif" in plan.reason


@pytest.mark.parametrize("missing", [False, True])
def test_stale_baseline_does_not_close_or_fall_back_to_other_candidates(missing):
    previous = previous_certificate(BUNDLE)
    newest = _promotion_receipt(pair=_promotable_pair_and_branch()).model_copy(
        update={
            "previous_certificate": None
            if missing
            else previous.model_copy(update={"bundle_version": "different"})
        }
    )
    older = _promotion_receipt(
        pair=make_pair(
            model="2.199.0",
            data=newest.pair.data.release_version,
            core=newest.pair.core.version,
        )
    )
    superseded_by_main = _promotion_receipt(
        pair=make_pair(model="2.0.0", data="1.0.0", core="3.0.0")
    )
    receipts = [newest, older, superseded_by_main]
    branches = {candidate_branch(r.pair): r.harness.git_commit for r in receipts}
    plan = plan_promotion(receipts, BUNDLE, branches)
    assert plan.target == newest
    assert plan.ready_branch is None and plan.ready_commit is None
    assert plan.close_branches == [candidate_branch(superseded_by_main.pair)]
    assert plan.requalify == newest.pair


def test_promotion_on_an_unrelated_main_commit_keeps_the_same_baseline():
    qualified = _promotion_receipt(pair=_promotable_pair_and_branch())
    unrelated_main = json.loads(json.dumps(BUNDLE))
    unrelated_main["data_releases"]["us"]["data_package"]["version"] = "99.0.0"
    assert previous_certificate(unrelated_main) == qualified.previous_certificate
    branch = candidate_branch(qualified.pair)
    plan = plan_promotion(
        [qualified], unrelated_main, {branch: qualified.harness.git_commit}
    )
    assert plan.ready_branch == branch
    assert plan.ready_commit == qualified.harness.git_commit
    assert plan.requalify is None


def test_a_forced_rerun_stages_a_new_attempt(tmp_path):
    """Interrupted review of #574: a forced run reused the existing attempt key,
    so the workflow's duplicate guard stopped it."""

    from policyengine.provenance.qualification_ledger import attempt_directory
    from policyengine.provenance.uk_qualification import attempt_key

    pair = _promotable_pair_and_branch()
    base = "a" * 40
    assert attempt_key(pair, tmp_path, base_commit=base, force=True) == base[:12]
    attempt_directory(tmp_path, "uk", pair.pair_id, base[:12]).mkdir(parents=True)
    assert attempt_key(pair, tmp_path, base_commit=base) == base[:12]
    assert attempt_key(pair, tmp_path, base_commit=base, force=True) == f"{base[:12]}-2"
    attempt_directory(tmp_path, "uk", pair.pair_id, f"{base[:12]}-2").mkdir(
        parents=True
    )
    assert attempt_key(pair, tmp_path, base_commit=base, force=True) == f"{base[:12]}-3"


#: Source for the fake gh's REST pull request listing, embedded in the
#: workflow shell tests (they run gh in another process): `pulls(args,
#: listing)` answers `gh api -X GET repos/<repo>/pulls -f head=<owner>:<branch>
#: -f base=... -f state=...` as GitHub does, keeping only pull requests from
#: that owner's branch (a fork's has another owner; an item's branch is the
#: BRANCH environment variable's unless it names another), and applies the
#: call's --jq to REST-shaped objects with the real jq.
FAKE_GH_PULLS = """
import shutil
import subprocess


def pulls(args, listing):
    fields = dict(
        value.split("=", 1) for flag, value in zip(args, args[1:]) if flag == "-f"
    )
    owner, _, branch = fields["head"].partition(":")
    page = []
    for pr in listing:
        pr = {
            "headRefName": os.environ["BRANCH"],
            "state": "OPEN",
            "isDraft": True,
            **pr,
        }
        pr_owner = "someone" if pr.get("isCrossRepository") else "PolicyEngine"
        state = "open" if pr["state"] == "OPEN" else "closed"
        if (
            pr_owner == owner
            and pr["headRefName"] == branch
            and pr["baseRefName"] == fields.get("base", pr["baseRefName"])
            and fields.get("state", "open") in ("all", state)
        ):
            page.append(
                {
                    "number": pr["number"],
                    "state": state,
                    "draft": pr["isDraft"],
                    "base": {"ref": pr["baseRefName"]},
                    "head": {"ref": pr["headRefName"]},
                }
            )
    sys.stdout.write(
        subprocess.run(
            [shutil.which("jq"), "-r", args[args.index("--jq") + 1]],
            input=json.dumps(page),
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    )
"""

#: Forks' pull requests with the candidate branch's name, newer than its own:
#: gh pr list's default listing of 30 would hold only these (round 7 of #635).
FORK_PULLS = [
    {
        "number": 600 + n,
        "baseRefName": "main",
        "isCrossRepository": True,
        "isDraft": False,
    }
    for n in range(40)
]


@pytest.mark.parametrize("step_name", ["open", "verdict"])
@pytest.mark.parametrize("exists", [True, False])
def test_the_workflow_writes_to_the_candidates_own_pull_request_by_number(
    tmp_path, step_name, exists
):
    """Round 6 of #635: the steps that open or update the candidate's pull
    request find it among this repository's pull requests to main and write
    by number; a fork's pull request with the branch's name, or this
    repository's from the branch to another base, is never edited. With no
    candidate pull request, the prepare step opens one to main and the
    verdict step fails."""

    import yaml

    assert shutil.which("jq"), "jq is required to run the workflow's jq"
    workflow = yaml.safe_load(
        (REPO_ROOT / ".github/workflows/certify-uk-release.yaml").read_text()
    )
    job, name = {
        "open": ("prepare", "Open or update the draft candidate PR"),
        "verdict": ("replay", "Update the candidate PR with the verdict"),
    }[step_name]
    step = next(s for s in workflow["jobs"][job]["steps"] if s.get("name") == name)
    log_path = tmp_path / "commands.jsonl"
    listing = [
        *FORK_PULLS,
        {"number": 576, "baseRefName": "release", "isCrossRepository": False},
        {
            "number": 577,
            "baseRefName": "main",
            "isCrossRepository": False,
            "state": "CLOSED",
        },
    ]
    if exists:
        listing.append(
            {"number": 574, "baseRefName": "main", "isCrossRepository": False}
        )
    fake = f"""#!{sys.executable}
import json
import os
import sys
from pathlib import Path

{FAKE_GH_PULLS}
args = sys.argv[1:]
with Path(os.environ["COMMAND_LOG"]).open("a") as log:
    log.write(json.dumps(["gh", *args]) + "\\n")
if args[:1] == ["api"] and "repos/PolicyEngine/policyengine.py/pulls" in args:
    pulls(args, {listing!r})
"""
    binary_dir = tmp_path / "bin"
    binary_dir.mkdir()
    (binary_dir / "gh").write_text(fake)
    (binary_dir / "gh").chmod(0o755)
    branch = "candidate/uk/2.126.8-1.58.0"
    result = subprocess.run(
        ["bash", "-e", "-o", "pipefail", "-c", step["run"]],
        cwd=tmp_path,
        env={
            **os.environ,
            "PATH": f"{binary_dir}{os.pathsep}{os.environ['PATH']}",
            "BRANCH": branch,
            "PAIR_ID": "a" * 64,
            "GITHUB_REPOSITORY": "PolicyEngine/policyengine.py",
            "GITHUB_RUN_ID": "1",
            "LEDGER_BRANCH": "uk-qualification-ledger",
            "RUNNER_TEMP": str(tmp_path),
            "COMMAND_LOG": str(log_path),
        },
        capture_output=True,
        text=True,
        timeout=30,
    )
    commands = [json.loads(line) for line in log_path.read_text().splitlines()]
    writes = [c for c in commands if c[1:3] in (["pr", "edit"], ["pr", "create"])]
    if exists:
        assert result.returncode == 0, result.stdout + result.stderr
        assert [c[:4] for c in writes] == [["gh", "pr", "edit", "574"]]
    elif step_name == "open":
        assert result.returncode == 0, result.stdout + result.stderr
        assert len(writes) == 1 and writes[0][1:3] == ["pr", "create"]
        create = writes[0]
        assert create[create.index("--base") + 1] == "main"
        assert create[create.index("--head") + 1] == branch
    else:
        assert result.returncode == 1
        assert f"no open pull request from {branch} to main" in result.stdout
        assert writes == []


@pytest.mark.parametrize(
    ("pr_state", "reset_fails"),
    [("ready", False), ("draft", False), ("absent", False), ("ready", True)],
)
def test_the_workflow_drafts_existing_prs_before_replacing_their_head(
    tmp_path, pr_state, reset_fails
):
    """Execute the workflow shell with local gh/git stand-ins and no remote writes."""

    import yaml

    workflow = yaml.safe_load(
        (REPO_ROOT / ".github/workflows/certify-uk-release.yaml").read_text()
    )
    step = next(
        step
        for step in workflow["jobs"]["prepare"]["steps"]
        if step.get("name") == "Commit and push the candidate commit"
    )
    state_path = tmp_path / "pr-state.json"
    state_path.write_text(json.dumps({"status": pr_state}))
    log_path = tmp_path / "commands.jsonl"
    fake = f"""#!{sys.executable}
import json
import os
import sys
from pathlib import Path

{FAKE_GH_PULLS}
command = Path(sys.argv[0]).name
args = sys.argv[1:]
state_path = Path(os.environ["PR_STATE"])
state = json.loads(state_path.read_text())
with Path(os.environ["COMMAND_LOG"]).open("a") as log:
    log.write(json.dumps([command, *args]) + "\\n")
if command == "gh" and args[:1] == ["api"]:
    # Forty newer ready forks' pull requests with the branch's name, and one
    # of this repository's from the branch to another base, are never undone
    # and never hide the candidate's own (round 7 of #635).
    listing = [
        *{FORK_PULLS!r},
        {{
            "number": 576,
            "baseRefName": "release",
            "isCrossRepository": False,
            "isDraft": False,
        }},
    ]
    if state["status"] != "absent":
        listing.append(
            {{
                "number": 574,
                "baseRefName": "main",
                "isCrossRepository": False,
                "isDraft": state["status"] != "ready",
            }}
        )
    pulls(args, listing)
elif command == "gh" and args[:2] == ["pr", "ready"]:
    assert args[2:] == ["574", "--undo"]
    if os.environ["RESET_FAILS"] == "1":
        sys.exit(42)
    state["status"] = "draft"
    state_path.write_text(json.dumps(state))
elif command == "git" and args[0] == "push":
    if state["status"] == "ready":
        sys.exit(91)
"""
    binary_dir = tmp_path / "bin"
    binary_dir.mkdir()
    for command in ("gh", "git"):
        executable = binary_dir / command
        executable.write_text(fake)
        executable.chmod(0o755)
    result = subprocess.run(
        ["bash", "-e", "-o", "pipefail", "-c", step["run"]],
        cwd=tmp_path,
        env={
            **os.environ,
            "PATH": f"{binary_dir}{os.pathsep}{os.environ['PATH']}",
            "BRANCH": "candidate/uk/2.126.8-1.58.0",
            "PAIR_ID": "a" * 64,
            "GITHUB_REPOSITORY": "PolicyEngine/policyengine.py",
            "GH_TOKEN": "local-workflow-test",
            "PR_STATE": str(state_path),
            "COMMAND_LOG": str(log_path),
            "RESET_FAILS": "1" if reset_fails else "0",
        },
        capture_output=True,
        text=True,
        timeout=30,
    )
    commands = [json.loads(line) for line in log_path.read_text().splitlines()]
    pushes = [i for i, command in enumerate(commands) if command[:2] == ["git", "push"]]
    resets = [
        i for i, command in enumerate(commands) if command[:3] == ["gh", "pr", "ready"]
    ]
    if reset_fails:
        assert result.returncode == 42, result.stdout + result.stderr
        assert not pushes
    else:
        assert result.returncode == 0, result.stdout + result.stderr
        assert len(pushes) == 1
        if pr_state == "ready":
            assert len(resets) == 1 and resets[0] < pushes[0]
            assert json.loads(state_path.read_text())["status"] == "draft"
        else:
            assert not resets
    assert step["env"]["GH_TOKEN"] == "${{ steps.app-token.outputs.token }}"


# --- Attempt lifecycle -----------------------------------------------------------------


@pytest.mark.parametrize("abandonment", ["expired", "failed_owner"])
def test_abandoned_stage_recovers_without_reusing_evidence(tmp_path, abandonment):
    from policyengine.provenance.qualification_ledger import (
        attempt_directory,
        read_json,
    )
    from policyengine.provenance.uk_qualification import (
        attempt_is_recoverable,
        attempt_key,
        stage_attempt,
    )

    pair = make_pair(model="2.200.0")
    base = "a" * 40
    attempt = attempt_directory(tmp_path, "uk", pair.pair_id, base[:12])
    payload = {"pair": pair.canonical_payload(), "base_commit": base}
    stage_attempt(attempt, payload, HARNESS)
    # The owner fails before request-replay, leaving durable but unfinished work.
    write_json(
        attempt / "staging.json",
        {
            "sequence": 1,
            "owner_run_id": "42",
            "staged_at": "2026-10-14T10:00:00Z",
            "expires_at": "2026-10-14T14:00:00Z",
        },
    )
    original = read_json(attempt / "candidate.json")
    now = "2026-10-14T15:00:00Z" if abandonment == "expired" else "2026-10-14T11:00:00Z"

    def failed(run_id):
        return abandonment == "failed_owner" and run_id == "42"

    assert attempt_is_recoverable(attempt, now=now, owner_is_failed=failed)
    assert (
        candidate_action(
            pair, BUNDLE, tmp_path, base_commit=base, now=now, owner_is_failed=failed
        )[0]
        == "qualify"
    )
    new_key = attempt_key(
        pair, tmp_path, base_commit=base, now=now, owner_is_failed=failed
    )
    assert new_key == base[:12] + "-2"
    new_attempt = attempt_directory(tmp_path, "uk", pair.pair_id, new_key)
    stage_attempt(new_attempt, payload, HARNESS, owner_run_id="43", staged_at=now)
    assert read_json(attempt / "candidate.json") == original
    assert (
        candidate_action(
            pair, BUNDLE, tmp_path, base_commit=base, now=now, owner_is_failed=failed
        )[0]
        == "duplicate"
    )


@pytest.mark.parametrize("protected", ["live", "request", "terminal", "missing_stage"])
def test_recovery_preserves_live_sent_and_terminal_attempts(tmp_path, protected):
    from policyengine.provenance.uk_qualification import (
        attempt_is_recoverable,
        stage_attempt,
    )

    pair = make_pair()
    attempt = tmp_path / "attempt"
    stage_attempt(attempt, {"pair": pair.canonical_payload()}, HARNESS)
    write_json(
        attempt / "staging.json",
        {
            "sequence": 1,
            "owner_run_id": "42",
            "expires_at": "2026-10-14T14:00:00Z",
        },
    )
    now = "2026-10-14T15:00:00Z"
    if protected == "live":
        now = "2026-10-14T11:00:00Z"
    elif protected == "request":
        write_json(attempt / "replay" / "request.json", {"sent": True})
    elif protected == "terminal":
        write_json(
            attempt / "qualification_receipt.json", make_receipt().canonical_payload()
        )
    else:
        (attempt / "staging.json").unlink()
    assert not attempt_is_recoverable(attempt, now=now, owner_is_failed=lambda _: False)


def test_stage_records_owner_and_expiry_immutably(tmp_path):
    from policyengine.provenance.qualification_ledger import read_json
    from policyengine.provenance.uk_qualification import stage_attempt

    payload = {"pair": make_pair().canonical_payload()}
    stage_attempt(
        tmp_path, payload, HARNESS, owner_run_id="42", staged_at="2026-10-14T10:00:00Z"
    )
    stage = read_json(tmp_path / "staging.json")
    assert stage["owner_run_id"] == "42"
    assert stage["expires_at"] == "2026-10-14T14:00:00Z"
    stage_attempt(tmp_path, payload, HARNESS, owner_run_id="43")
    assert read_json(tmp_path / "staging.json") == stage


def test_unowned_legacy_stage_is_recoverable_on_the_same_base(tmp_path):
    from policyengine.provenance.qualification_ledger import attempt_directory
    from policyengine.provenance.uk_qualification import stage_attempt

    pair = make_pair(model="2.200.0")
    base = "a" * 40
    attempt = attempt_directory(tmp_path, "uk", pair.pair_id, base[:12])
    stage_attempt(attempt, {"pair": pair.canonical_payload()}, HARNESS)
    write_json(attempt / "staging.json", {"sequence": 1})
    assert candidate_action(pair, BUNDLE, tmp_path, base_commit=base)[0] == "qualify"


def test_newer_abandoned_stage_recovers_despite_an_older_replay_request(tmp_path):
    from policyengine.provenance.qualification_ledger import attempt_directory
    from policyengine.provenance.uk_qualification import attempt_key, stage_attempt

    pair = make_pair(model="2.200.0")
    base = "a" * 40
    payload = {"pair": pair.canonical_payload()}
    earlier = attempt_directory(tmp_path, "uk", pair.pair_id, base[:12])
    stage_attempt(
        earlier, payload, HARNESS, owner_run_id="41", staged_at="2026-10-14T09:00:00Z"
    )
    write_json(earlier / "replay" / "request.json", {"sent": True})
    newer = attempt_directory(tmp_path, "uk", pair.pair_id, base[:12] + "-2")
    stage_attempt(
        newer, payload, HARNESS, owner_run_id="42", staged_at="2026-10-14T10:00:00Z"
    )
    now = "2026-10-14T15:00:00Z"
    assert (
        candidate_action(pair, BUNDLE, tmp_path, base_commit=base, now=now)[0]
        == "qualify"
    )
    assert attempt_key(pair, tmp_path, base_commit=base, now=now) == base[:12] + "-3"
    assert (earlier / "replay" / "request.json").exists()


def _publish_as_attempt(ledger, pair, receipt, key):
    """Publish ``receipt`` as an earlier, unstaged attempt's own receipt.

    A published receipt counts only as its latest attempt's receipt
    (``published_receipt``), so the fixture records the attempt it came from.
    """

    pair_dir = ledger / "uk" / pair.pair_id
    write_json(
        pair_dir / "attempts" / key / "qualification_receipt.json",
        receipt.canonical_payload(),
    )
    write_json(pair_dir / "qualification_receipt.json", receipt.canonical_payload())


@pytest.mark.parametrize("verdict", ["qualified", "rejected"])
@pytest.mark.parametrize("main_advanced", [False, True])
@pytest.mark.parametrize("staged_base", ["a" * 40, "f" * 40])
def test_forced_stage_recovery_binds_the_terminal_receipt_it_supersedes(
    tmp_path, verdict, main_advanced, staged_base, monkeypatch, capsys
):
    import importlib.util

    from policyengine.provenance.qualification_ledger import attempt_directory
    from policyengine.provenance.uk_qualification import stage_attempt

    pair = make_pair(model="2.200.0")
    results = gates(wheel_hashes="fail") if verdict == "rejected" else gates()
    terminal = make_receipt(pair=pair, gate_results=results)
    base = staged_base
    _publish_as_attempt(tmp_path, pair, terminal, "terminal")
    attempt = attempt_directory(tmp_path, "uk", pair.pair_id, base[:12] + "-2")
    payload = {
        "pair": pair.canonical_payload(),
        "supersedes_receipt_sha256": terminal.unreviewed_sha256,
    }
    stage_attempt(
        attempt, payload, HARNESS, owner_run_id="42", staged_at="2026-10-14T10:00:00Z"
    )
    if main_advanced:
        base = "b" * 40
    now = "2026-10-14T15:00:00Z"
    assert (
        candidate_action(pair, BUNDLE, tmp_path, base_commit=base, now=now)[0]
        == "qualify"
    )
    spec = importlib.util.spec_from_file_location(
        "check_uk_bound_recovery_for_test", REPO_ROOT / "scripts/check_uk_candidate.py"
    )
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    monkeypatch.setattr(cli, "utc_now", lambda: now)
    assert cli.main(["recoverable", "--ledger", str(tmp_path)]) == 0
    assert json.loads(capsys.readouterr().out) == payload
    changed = make_receipt(pair=pair, gate_results=gates(replay="fail"))
    _publish_as_attempt(tmp_path, pair, changed, "terminal-later")
    assert (
        candidate_action(pair, BUNDLE, tmp_path, base_commit=base, now=now)[0]
        == "duplicate"
    )
    with pytest.raises(ValueError, match="exact receipt"):
        stage_attempt(attempt.parent / (base[:12] + "-3"), payload, HARNESS)
    assert cli.main(["recoverable", "--ledger", str(tmp_path)]) == 0
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("protected", ["live", "request", "terminal", "unbound"])
def test_forced_recovery_preserves_newer_work_on_another_base(tmp_path, protected):
    from policyengine.provenance.qualification_ledger import attempt_directory
    from policyengine.provenance.uk_qualification import stage_attempt

    pair = make_pair(model="2.200.0")
    terminal = make_receipt(pair=pair)
    write_json(
        tmp_path / "uk" / pair.pair_id / "qualification_receipt.json",
        terminal.canonical_payload(),
    )
    original_base, replacement_base = "f" * 40, "b" * 40
    payload = {
        "pair": pair.canonical_payload(),
        "supersedes_receipt_sha256": terminal.unreviewed_sha256,
    }
    original = attempt_directory(tmp_path, "uk", pair.pair_id, original_base[:12])
    stage_attempt(
        original, payload, HARNESS, owner_run_id="42", staged_at="2026-10-14T10:00:00Z"
    )
    replacement = attempt_directory(tmp_path, "uk", pair.pair_id, replacement_base[:12])
    replacement_payload = (
        {"pair": pair.canonical_payload()} if protected == "unbound" else payload
    )
    stage_attempt(
        replacement,
        replacement_payload,
        HARNESS,
        owner_run_id="43",
        staged_at=(
            "2026-10-14T14:00:00Z" if protected == "live" else "2026-10-14T10:00:00Z"
        ),
    )
    if protected == "request":
        write_json(replacement / "replay" / "request.json", {"sent": True})
    elif protected == "terminal":
        write_json(
            replacement / "qualification_receipt.json", terminal.canonical_payload()
        )
    for base in (original_base, replacement_base, "c" * 40):
        assert (
            candidate_action(
                pair, BUNDLE, tmp_path, base_commit=base, now="2026-10-14T15:00:00Z"
            )[0]
            == "duplicate"
        )


@pytest.mark.parametrize("verdict", ["qualified", "rejected"])
@pytest.mark.parametrize("main_advanced", [False, True])
@pytest.mark.parametrize("abandonment", ["expired", "failed_owner"])
def test_resolution_preserves_authorization_to_recover_forced_work(
    tmp_path, monkeypatch, verdict, main_advanced, abandonment
):
    import importlib.util

    from policyengine.provenance.qualification_ledger import attempt_directory
    from policyengine.provenance.uk_qualification import stage_attempt

    spec = importlib.util.spec_from_file_location(
        "check_uk_resolve_recovery_for_test",
        REPO_ROOT / "scripts/check_uk_candidate.py",
    )
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    pair = make_pair(model="2.200.0")
    terminal = make_receipt(
        pair=pair,
        gate_results=gates(replay="fail") if verdict == "rejected" else gates(),
    )
    _publish_as_attempt(tmp_path, pair, terminal, "terminal")
    base = "a" * 40
    resolved = cli.ResolvedCandidate(
        pair,
        cli.WheelFile(
            "model.whl", "https://example.org/model.whl", pair.model.wheel_sha256
        ),
        cli.WheelFile(
            "core.whl", "https://example.org/core.whl", pair.core.wheel_sha256
        ),
        "hf://model/example@pin/manifest.json",
        ">=3.33.0",
    )
    monkeypatch.setattr(cli, "resolve_candidate", lambda **kwargs: resolved)
    monkeypatch.setattr(cli, "git", lambda *args: base)
    monkeypatch.setattr(
        cli,
        "owner_run_failed",
        lambda run_id: abandonment == "failed_owner" and run_id == "42",
    )
    now = "2026-10-14T15:00:00Z" if abandonment == "expired" else "2026-10-14T11:00:00Z"
    monkeypatch.setattr(cli, "utc_now", lambda: now)
    monkeypatch.setattr(cli, "set_output", lambda **kwargs: None)
    out = tmp_path / "candidate.json"
    args = SimpleNamespace(
        model_version=None,
        data_version=None,
        core_version=None,
        pair_id=None,
        ledger=str(tmp_path),
        force=True,
        out=str(out),
    )
    assert cli.cmd_resolve(args) == 0
    payload = json.loads(out.read_text())
    # The recheck under the preparation lock reads it (round 3 of #635).
    assert payload["force"] is True
    assert payload["supersedes_receipt_sha256"] == terminal.unreviewed_sha256
    attempt = attempt_directory(tmp_path, "uk", pair.pair_id, payload["attempt_key"])
    stage_attempt(
        attempt, payload, HARNESS, owner_run_id="42", staged_at="2026-10-14T10:00:00Z"
    )
    original_candidate = (attempt / "candidate.json").read_bytes()
    if main_advanced:
        base = "b" * 40
    args.force = False
    assert cli.cmd_resolve(args) == 0
    recovery = json.loads(out.read_text())
    assert recovery["action"] == "qualify" and recovery["force"] is False
    assert recovery["base_commit"] == base
    assert recovery["attempt_key"] == (base[:12] if main_advanced else base[:12] + "-2")
    assert recovery["supersedes_receipt_sha256"] == terminal.unreviewed_sha256
    replacement = attempt_directory(
        tmp_path, "uk", pair.pair_id, recovery["attempt_key"]
    )
    stage_attempt(replacement, recovery, HARNESS, owner_run_id="43", staged_at=now)
    assert (attempt / "candidate.json").read_bytes() == original_candidate
    assert cli.cmd_resolve(args) == 0
    assert json.loads(out.read_text())["action"] == "duplicate"


def test_cross_base_recovery_allocates_new_keys_without_overwriting_evidence(tmp_path):
    from policyengine.provenance.qualification_ledger import attempt_directory
    from policyengine.provenance.uk_qualification import attempt_key, stage_attempt

    pair = make_pair(model="2.200.0")
    old_base, current_base = "a" * 40, "b" * 40
    existing = attempt_directory(tmp_path, "uk", pair.pair_id, current_base[:12])
    sent_payload = {"pair": pair.canonical_payload(), "base_commit": current_base}
    stage_attempt(
        existing,
        sent_payload,
        HARNESS,
        owner_run_id="41",
        staged_at="2026-10-14T09:00:00Z",
    )
    write_json(existing / "replay" / "request.json", {"sent": True})
    abandoned = attempt_directory(tmp_path, "uk", pair.pair_id, old_base[:12])
    stage_attempt(
        abandoned,
        {"pair": pair.canonical_payload(), "base_commit": old_base},
        HARNESS,
        owner_run_id="42",
        staged_at="2026-10-14T10:00:00Z",
    )
    now = "2026-10-14T15:00:00Z"
    assert (
        candidate_action(pair, BUNDLE, tmp_path, base_commit=current_base, now=now)[0]
        == "qualify"
    )
    assert attempt_key(pair, tmp_path, base_commit=current_base, now=now) == (
        current_base[:12] + "-2"
    )
    assert json.loads((existing / "candidate.json").read_text()) == sent_payload
    assert json.loads((existing / "replay" / "request.json").read_text()) == {
        "sent": True
    }


@pytest.mark.parametrize(
    ("status", "conclusion", "expected"),
    [
        ("completed", "failure", True),
        ("completed", "cancelled", True),
        ("completed", "timed_out", True),
        ("in_progress", "failure", False),
        ("completed", "success", False),
        ("queued", None, False),
    ],
)
def test_recovery_requires_a_confirmed_failed_owner(
    monkeypatch, status, conclusion, expected
):
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "check_uk_owner_for_test", REPO_ROOT / "scripts/check_uk_candidate.py"
    )
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    calls = []

    def run(argv, **kwargs):
        calls.append(argv)
        return subprocess.CompletedProcess(
            argv, 0, json.dumps({"status": status, "conclusion": conclusion})
        )

    monkeypatch.setattr(cli, "subprocess", SimpleNamespace(run=run))
    assert cli.owner_run_failed("42") is expected
    assert "42" in calls[0] and cli.LEDGER_REPOSITORY in calls[0]
    cli.owner_run_failed.cache_clear()
    monkeypatch.setattr(
        cli,
        "subprocess",
        SimpleNamespace(run=lambda *a, **k: subprocess.CompletedProcess(a, 1, "")),
    )
    assert not cli.owner_run_failed("42")


def test_catchup_finds_abandoned_stages_without_replay_requests(
    tmp_path, monkeypatch, capsys
):
    import importlib.util

    from policyengine.provenance.qualification_ledger import attempt_directory
    from policyengine.provenance.uk_qualification import stage_attempt

    spec = importlib.util.spec_from_file_location(
        "check_uk_recovery_for_test", REPO_ROOT / "scripts/check_uk_candidate.py"
    )
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    pair = make_pair()
    attempt = attempt_directory(tmp_path, "uk", pair.pair_id, "a" * 12)
    payload = {"pair": pair.canonical_payload()}
    stage_attempt(attempt, payload, HARNESS)
    write_json(
        attempt / "staging.json",
        {
            "sequence": 1,
            "owner_run_id": "42",
            "expires_at": "2026-10-14T14:00:00Z",
        },
    )
    monkeypatch.setattr(cli, "utc_now", lambda: "2026-10-14T11:00:00Z")
    monkeypatch.setattr(cli, "owner_run_failed", lambda run_id: run_id == "42")
    assert cli.main(["recoverable", "--ledger", str(tmp_path)]) == 0
    assert json.loads(capsys.readouterr().out) == payload
    replacement = attempt_directory(tmp_path, "uk", pair.pair_id, "a" * 12 + "-2")
    stage_attempt(
        replacement,
        payload,
        HARNESS,
        owner_run_id="43",
        staged_at="2026-10-14T11:00:00Z",
    )
    assert cli.main(["recoverable", "--ledger", str(tmp_path)]) == 0
    assert capsys.readouterr().out == ""
    write_json(
        attempt / "staging.json",
        {
            "sequence": 3,
            "owner_run_id": "42",
            "expires_at": "2026-10-14T14:00:00Z",
        },
    )
    write_json(
        tmp_path / "uk" / pair.pair_id / "qualification_receipt.json",
        make_receipt(pair=pair).canonical_payload(),
    )
    assert cli.main(["recoverable", "--ledger", str(tmp_path)]) == 0
    assert capsys.readouterr().out == ""


def test_attempt_lifecycle(tmp_path):
    from policyengine.provenance.qualification import GateResult
    from policyengine.provenance.qualification_ledger import (
        attempt_directory,
        read_json,
    )
    from policyengine.provenance.uk_qualification import (
        attempt_is_waiting_for_replay,
        finalize_attempt,
        stage_attempt,
        write_gate_results,
    )

    pair = make_pair()
    attempt = attempt_directory(tmp_path, "uk", pair.pair_id, "abcdef123456")
    stage_attempt(
        attempt,
        {
            "pair": pair.canonical_payload(),
            "pair_id": pair.pair_id,
            "previous_certificate": None,
        },
        HARNESS,
    )
    local = [gate for gate in gates() if gate.gate_id != "replay"]
    write_gate_results(attempt, local, {gate.gate_id: {"ok": True} for gate in local})
    assert not attempt_is_waiting_for_replay(attempt)
    receipt = finalize_attempt(
        attempt, tmp_path, issued_by=ISSUED, completed_at="2026-10-15T10:00:00Z"
    )
    assert receipt.verdict == "incomplete"  # the replay never ran
    assert (
        read_json(tmp_path / "uk" / pair.pair_id / "qualification_receipt.json")[
            "verdict"
        ]
        == "incomplete"
    )

    request = build_replay_request(
        pair,
        HARNESS,
        release_bundle=golden("qualification_request_golden")["candidate"][
            "expected_release_bundle"
        ],
        issued_by=ISSUED,
    )
    write_json(attempt / "replay" / "request.json", request.document())
    assert attempt_is_waiting_for_replay(attempt)
    write_json(
        attempt / "replay" / "replay.result.json",
        GateResult(gate_id="replay", status="pass", summary="ok").canonical_payload(),
    )
    assert not attempt_is_waiting_for_replay(attempt)
    final = finalize_attempt(
        attempt, tmp_path, issued_by=ISSUED, completed_at="2026-10-15T11:00:00Z"
    )
    assert final.verdict == "qualified"
    assert final.replay.request_id == request.request_id
    assert (attempt / "receipts" / f"{receipt.receipt_sha256}.json").is_file()
    assert (attempt / "receipts" / f"{final.receipt_sha256}.json").is_file()
    assert (
        read_json(attempt / "receipts" / f"{receipt.receipt_sha256}.json")
        == receipt.canonical_payload()
    )


def test_older_attempt_finalization_preserves_latest_staged_attempt(tmp_path):
    from policyengine.provenance.qualification_ledger import (
        attempt_directory,
        read_json,
    )
    from policyengine.provenance.uk_qualification import (
        finalize_attempt,
        stage_attempt,
        write_gate_results,
    )

    pair = make_pair()
    # The staging order deliberately differs from directory/commit order.
    older = attempt_directory(tmp_path, "uk", pair.pair_id, "ffffffffffff")
    newer = attempt_directory(tmp_path, "uk", pair.pair_id, "aaaaaaaaaaaa")
    payload = {"pair": pair.canonical_payload(), "previous_certificate": None}
    stage_attempt(older, payload, HARNESS)
    newer_harness = HARNESS.model_copy(update={"git_commit": "a" * 40})
    stage_attempt(newer, payload, newer_harness)
    for attempt in (older, newer):
        write_gate_results(attempt, gates(), {})
    newest = finalize_attempt(
        newer, tmp_path, issued_by=ISSUED, completed_at="2026-10-15T10:00:00Z"
    )
    old = finalize_attempt(
        older, tmp_path, issued_by=ISSUED, completed_at="2026-10-15T11:00:00Z"
    )
    latest = read_json(tmp_path / "uk" / pair.pair_id / "qualification_receipt.json")
    assert latest == newest.canonical_payload()
    assert read_json(older / "qualification_receipt.json") == old.canonical_payload()
    assert read_json(newer / "qualification_receipt.json") == newest.canonical_payload()


def test_terminal_attempt_receipt_is_immutable_and_finalization_is_idempotent(tmp_path):
    from policyengine.provenance.qualification_ledger import attempt_directory
    from policyengine.provenance.uk_qualification import (
        finalize_attempt,
        stage_attempt,
        write_gate_results,
    )

    pair = make_pair()
    attempt = attempt_directory(tmp_path, "uk", pair.pair_id, "abcdef123456")
    stage_attempt(attempt, {"pair": pair.canonical_payload()}, HARNESS)
    write_gate_results(attempt, gates(), {})
    original = finalize_attempt(
        attempt, tmp_path, issued_by=ISSUED, completed_at="2026-10-15T10:00:00Z"
    )
    original_bytes = (attempt / "qualification_receipt.json").read_bytes()
    write_gate_results(attempt, gates(replay="fail"), {})
    repeated = finalize_attempt(
        attempt, tmp_path, issued_by=ISSUED, completed_at="2026-10-15T11:00:00Z"
    )
    assert repeated == original
    assert (attempt / "qualification_receipt.json").read_bytes() == original_bytes


def test_new_staged_attempt_advances_a_legacy_latest_receipt(tmp_path):
    from policyengine.provenance.qualification_ledger import (
        attempt_directory,
        read_json,
    )
    from policyengine.provenance.uk_qualification import (
        finalize_attempt,
        stage_attempt,
        write_gate_results,
    )

    legacy = make_receipt()
    latest_path = tmp_path / "uk" / legacy.pair_id / "qualification_receipt.json"
    write_json(latest_path, legacy.canonical_payload())
    attempt = attempt_directory(tmp_path, "uk", legacy.pair_id, "new-attempt")
    stage_attempt(attempt, {"pair": legacy.pair.canonical_payload()}, HARNESS)
    write_gate_results(attempt, gates(), {})
    current = finalize_attempt(
        attempt, tmp_path, issued_by=ISSUED, completed_at="2026-10-15T11:00:00Z"
    )
    assert read_json(latest_path) == current.canonical_payload()


@pytest.mark.parametrize(
    "interrupted", ["missing", "older", "missing-pointer", "missing-receipt"]
)
def test_terminal_finalization_repairs_interrupted_latest_publication(
    tmp_path, interrupted
):
    from policyengine.provenance.qualification_ledger import (
        attempt_directory,
        read_json,
    )
    from policyengine.provenance.uk_qualification import (
        finalize_attempt,
        stage_attempt,
        write_gate_results,
    )

    pair = make_pair()
    payload = {"pair": pair.canonical_payload()}
    older = attempt_directory(tmp_path, "uk", pair.pair_id, "older")
    stage_attempt(older, payload, HARNESS)
    write_gate_results(older, gates(), {})
    old_receipt = finalize_attempt(
        older, tmp_path, issued_by=ISSUED, completed_at="2026-10-15T09:00:00Z"
    )
    current = attempt_directory(tmp_path, "uk", pair.pair_id, "newer")
    stage_attempt(current, payload, HARNESS.model_copy(update={"git_commit": "a" * 40}))
    write_gate_results(current, gates(), {})
    receipt = finalize_attempt(
        current, tmp_path, issued_by=ISSUED, completed_at="2026-10-15T10:00:00Z"
    )
    original_bytes = (current / "qualification_receipt.json").read_bytes()
    pair_dir = tmp_path / "uk" / pair.pair_id
    latest = pair_dir / "qualification_receipt.json"
    pointer = pair_dir / "latest_attempt.json"
    if interrupted == "older":
        write_json(latest, old_receipt.canonical_payload())
        write_json(pointer, {"attempt_key": "older", "sequence": 1})
    else:
        if interrupted != "missing-pointer":
            latest.unlink()
        if interrupted != "missing-receipt":
            pointer.unlink()
    repeated = finalize_attempt(
        current, tmp_path, issued_by=ISSUED, completed_at="2026-10-15T11:00:00Z"
    )
    assert repeated == receipt
    assert (current / "qualification_receipt.json").read_bytes() == original_bytes
    assert read_json(latest) == receipt.canonical_payload()
    assert read_json(pointer) == {"attempt_key": "newer", "sequence": 2}
    finalize_attempt(
        older, tmp_path, issued_by=ISSUED, completed_at="2026-10-15T12:00:00Z"
    )
    assert read_json(latest) == receipt.canonical_payload()


def test_stale_latest_pointer_cannot_replace_a_newer_incomplete_receipt(tmp_path):
    from policyengine.provenance.qualification_ledger import (
        attempt_directory,
        read_json,
    )
    from policyengine.provenance.uk_qualification import (
        finalize_attempt,
        stage_attempt,
        write_gate_results,
    )

    pair = make_pair()
    payload = {"pair": pair.canonical_payload()}
    older = attempt_directory(tmp_path, "uk", pair.pair_id, "older")
    stage_attempt(older, payload, HARNESS)
    write_gate_results(older, gates(), {})
    finalize_attempt(
        older, tmp_path, issued_by=ISSUED, completed_at="2026-10-15T09:00:00Z"
    )
    newer = attempt_directory(tmp_path, "uk", pair.pair_id, "newer")
    stage_attempt(newer, payload, HARNESS.model_copy(update={"git_commit": "a" * 40}))
    write_gate_results(newer, gates(replay="unavailable"), {})
    current = finalize_attempt(
        newer, tmp_path, issued_by=ISSUED, completed_at="2026-10-15T10:00:00Z"
    )
    pair_dir = tmp_path / "uk" / pair.pair_id
    write_json(
        pair_dir / "latest_attempt.json", {"attempt_key": "older", "sequence": 1}
    )
    finalize_attempt(
        older, tmp_path, issued_by=ISSUED, completed_at="2026-10-15T11:00:00Z"
    )
    assert (
        read_json(pair_dir / "qualification_receipt.json")
        == current.canonical_payload()
    )
    assert read_json(pair_dir / "latest_attempt.json") == {
        "attempt_key": "newer",
        "sequence": 2,
    }


# --- Release dispatch ----------------------------------------------------------------


def test_release_payload_keeps_version_first_and_carries_identity():
    from policyengine.provenance.receipt import certificate_sha256
    from policyengine.provenance.uk_qualification import release_dispatch_payload

    version = BUNDLE["policyengine_version"]
    payload = release_dispatch_payload(BUNDLE, version=version)
    assert payload["event_type"] == "policyengine-release"
    body = payload["client_payload"]
    assert list(body)[0] == "version" and body["version"] == version
    uk = body["bundle"]["uk"]
    record = BUNDLE["data_releases"]["uk"]
    assert uk["model_version"] == record["model_package"]["version"]
    assert uk["dataset_sha256"] == record["certified_data_artifact"]["sha256"]
    assert uk["certificate_sha256"] == certificate_sha256(record)
    assert body["qualification"] is None  # the committed pair was not auto-qualified
    assert len(body) <= 10  # repository_dispatch limit on top-level keys
    with pytest.raises(ValueError):
        release_dispatch_payload(BUNDLE, version="0.0.0")


def test_release_payload_names_the_qualification_receipt():
    from policyengine.provenance.uk_qualification import release_dispatch_payload

    bundle = json.loads(json.dumps(BUNDLE))
    receipt = make_receipt()
    bundle["data_releases"]["uk"]["certification"].update(
        compatibility_basis="qualified_exact_pair",
        qualification_pair_id=receipt.pair_id,
    )
    payload = release_dispatch_payload(
        bundle,
        version=bundle["policyengine_version"],
        fetch_receipt=lambda country, pair_id: receipt,
    )
    assert payload["client_payload"]["qualification"] == {
        "uk": {
            "pair_id": receipt.pair_id,
            "verdict": "qualified",
            "promotable": True,
            "receipt_sha256": receipt.receipt_sha256,
        }
    }


def test_released_bundle_request_is_valid_for_the_scorecard():
    from policyengine.provenance.uk_qualification import released_bundle_request

    record = BUNDLE["data_releases"]["uk"]
    dataset = record["default_dataset"]
    manifest = {
        "schema_version": 1,
        "data_package": {
            "name": "policyengine-uk-data",
            "version": record["data_package"]["version"],
        },
        "default_datasets": {"national": dataset},
        "artifacts": {
            dataset: {
                "kind": "microdata",
                "path": record["datasets"][dataset]["path"],
                "repo_id": record["datasets"][dataset]["repo_id"],
                "revision": record["datasets"][dataset]["revision"],
                "sha256": record["datasets"][dataset]["sha256"],
                "size_bytes": 128369110,
            }
        },
    }
    core = BUNDLE["packages"]["policyengine-core"]["version"]
    request = released_bundle_request(
        BUNDLE,
        version=BUNDLE["policyengine_version"],
        wheel_sha256=sha("7"),
        packaged_manifest_sha256=sha("8"),
        release_bundle=golden("qualification_request_golden")["candidate"][
            "expected_release_bundle"
        ],
        hf_file=lambda repo, rev, path: json.dumps(manifest).encode(),
        pypi_project=lambda name: {
            "releases": {core: [_wheel("policyengine-core", core, sha("6"))]}
        },
        requested_by={
            "repository": "PolicyEngine/policyengine.py",
            "workflow_run_id": 5,
            "commit": "e" * 40,
        },
    )
    schema = json.loads(
        (VENDORED_SCHEMAS / "qualification_request.v1.json").read_text()
    )
    jsonschema.Draft202012Validator(schema).validate(request.document())
    assert request.kind == "released_bundle"
    assert request.document()["candidate"]["policyengine"]["source"] == {
        "pypi": {"wheel_sha256": sha("7")}
    }


def test_expected_release_bundle_uses_the_scorecard_certification_environment(
    monkeypatch, tmp_path
):
    """W6 interface point 4: no tokens, no proxy exceptions, no network."""

    from policyengine.provenance import uk_qualification

    environ = {
        "PATH": "/usr/bin",
        "HF_TOKEN": "t",
        "HUGGING_FACE_TOKEN": "t",
        "HUGGINGFACE_HUB_TOKEN": "t",
        "NO_PROXY": "huggingface.co",
        "no_proxy": "huggingface.co",
        "HTTPS_PROXY": "http://corporate:3128",
        "POLICYENGINE_SKIP_COUNTRY_IMPORTS": "1",
    }
    env = uk_qualification.certification_environment(environ)
    assert env["PATH"] == "/usr/bin"
    for name in ("HF_TOKEN", "HUGGING_FACE_TOKEN", "HUGGINGFACE_HUB_TOKEN"):
        assert name not in env
    assert "NO_PROXY" not in env and "no_proxy" not in env
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
        assert env[name] == env[name.lower()] == "http://127.0.0.1:9"
    assert env["HF_HUB_OFFLINE"] == "1"

    seen = {}

    def run(args, *, cwd, env, check, capture_output, text):
        seen["env"] = env
        return type("Done", (), {"stdout": '{"policyengine_version": "6.2.6"}\n'})()

    monkeypatch.setattr(uk_qualification.subprocess, "run", run)
    monkeypatch.setattr(uk_qualification.os, "environ", environ)
    assert uk_qualification.expected_release_bundle("python", cwd=tmp_path) == {
        "policyengine_version": "6.2.6"
    }
    assert seen["env"] == env


def test_the_certification_environment_falls_back_to_the_packaged_certificate():
    """Executed: with the proxies, the manifest request fails and the bundled
    certification is used (the mechanism W6's recipe relies on)."""

    import os
    import subprocess
    import sys

    from policyengine.provenance import uk_qualification

    script = (
        "import json\n"
        "from policyengine.provenance import manifest\n"
        "try:\n"
        "    manifest.get_data_release_manifest('uk')\n"
        "    print('reached')\n"
        "except manifest.DataReleaseManifestUnavailableError:\n"
        "    print('unavailable')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        env=uk_qualification.certification_environment(os.environ),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.stdout.strip().splitlines()[-1] == "unavailable", result.stderr
