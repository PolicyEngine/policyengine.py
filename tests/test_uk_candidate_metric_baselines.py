"""Review bounds require usable baseline values for each candidate metric."""

import copy

import pytest

from policyengine.provenance.uk_candidate import compare_metric_reports, metrics_review

BOUNDS = {"default": {"relative": 0.02, "absolute": 5e8}}


#: The small-cell fields every row of the pinned tool's report carries.
PUBLISHED = {"suppressed": False, "excludes": [], "exclude_signs": {}}


def _report():
    return {
        "status": "ok",
        "metrics_version": "m1",
        "partition_version": "p1",
        "metrics": [
            {
                "metric_id": "income_tax",
                "year": 2027,
                "kind": "receipt",
                "value": 3e11,
                **PUBLISHED,
            },
            {
                "metric_id": "relative_poverty",
                "year": 2027,
                "kind": "poverty",
                "value": 0.17,
                **PUBLISHED,
            },
        ],
        "identities": [{"identity_id": "weights:household", "status": "pass"}],
    }


@pytest.mark.parametrize(
    "baseline_value", [float("nan"), float("inf"), -float("inf"), None, "invalid"]
)
def test_unusable_baseline_cannot_claim_a_large_move_is_within_bounds(baseline_value):
    candidate, previous = _report(), _report()
    candidate["metrics"][0]["value"] = 1e12
    previous["metrics"][0]["value"] = baseline_value

    status, summary, _ = compare_metric_reports(candidate, previous, BOUNDS)

    assert status == "fail"
    assert "previous" in summary and "non-finite" in summary
    gate, _ = metrics_review(
        candidate_report=candidate, previous_report=previous, bounds=BOUNDS
    )
    assert gate.status == "fail"
    assert gate.evidence_sha256


def test_a_baseline_row_without_a_value_cannot_pass():
    candidate, previous = _report(), _report()
    del previous["metrics"][0]["value"]
    assert compare_metric_reports(candidate, previous, BOUNDS)[0] == "fail"


def test_a_metric_without_a_baseline_requires_review():
    candidate, previous = _report(), _report()
    previous["metrics"] = previous["metrics"][1:]
    status, summary, evidence = compare_metric_reports(candidate, previous, BOUNDS)
    assert status == "needs_review"
    assert "no baseline" in summary and "income_tax" in summary
    assert evidence["metrics_without_baseline"] == ["income_tax 2027"]


@pytest.mark.parametrize("side", ["candidate", "previous"])
def test_a_duplicate_metric_cannot_hide_an_unusable_value(side):
    candidate, previous = _report(), _report()
    report = candidate if side == "candidate" else previous
    report["metrics"].insert(0, {**report["metrics"][0], "value": float("nan")})
    status, summary, _ = compare_metric_reports(candidate, previous, BOUNDS)
    assert status == "fail"
    assert "duplicate metrics" in summary and side in summary


def test_duplicate_finite_baselines_cannot_select_the_most_favourable_comparison():
    candidate, previous = _report(), _report()
    candidate["metrics"][0]["value"] = 1e12
    previous["metrics"].append({**previous["metrics"][0], "value": 1e12})
    status, summary, _ = compare_metric_reports(candidate, previous, BOUNDS)
    assert status == "fail"
    assert "previous report has duplicate metrics: income_tax 2027" in summary


def test_an_unusable_cross_report_cannot_pass_either_review_step():
    candidate, previous, cross = _report(), _report(), _report()
    cross["metrics"][0]["value"] = float("nan")
    gate, evidence = metrics_review(
        candidate_report=candidate,
        previous_report=previous,
        cross_report=cross,
        bounds=BOUNDS,
    )
    assert gate.status == "fail"
    assert "model_only" in evidence and "data_only" in evidence
    assert "data_only: the previous report has non-finite" in gate.summary


def test_valid_baselines_preserve_bounds_and_do_not_mutate_reports():
    candidate, previous = _report(), _report()
    original = copy.deepcopy((candidate, previous))
    assert compare_metric_reports(candidate, previous, BOUNDS)[0] == "pass"
    assert (candidate, previous) == original
    candidate["metrics"][0]["value"] = 1e12
    status, _, evidence = compare_metric_reports(candidate, previous, BOUNDS)
    assert status == "needs_review"
    assert evidence["moves_beyond_bounds"][0]["metric_id"] == "income_tax"


def _previous_certificate():
    return {
        "bundle_version": "6.3.0",
        "model_version": "2.125.1",
        "core_version": "3.33.0",
        "model_wheel_sha256": "1" * 64,
        "core_wheel_sha256": "2" * 64,
        "data_release_version": "1.58.0",
        "dataset_sha256": "3" * 64,
        "dataset_name": "national",
        "release_manifest_reference": {
            "repo_id": "policyengine/uk-data",
            "repo_type": "model",
            "path": "releases/1.58.0/release_manifest.json",
            "revision": "b" * 40,
        },
        "dataset_reference": {
            "repo_id": "policyengine/uk-data",
            "repo_type": "model",
            "path": "national.h5",
            "revision": "a" * 40,
            "sha256": "3" * 64,
        },
    }


def _previous_install_io(
    tmp_path, monkeypatch, *, bad_pypi=None, bad_download=None, identity_problems=None
):
    import json
    from pathlib import Path
    from types import SimpleNamespace

    import requests

    from policyengine.provenance import uk_candidate

    previous = _previous_certificate()
    commands = []

    def get(url, **kwargs):
        package, version = url.removeprefix("https://pypi.org/pypi/").split("/")[:2]
        digest = previous[
            "model_wheel_sha256"
            if package == "policyengine-uk"
            else "core_wheel_sha256"
        ]
        if package == bad_pypi:
            digest = "0" * 64
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {
                "urls": [
                    {
                        "packagetype": "bdist_wheel",
                        "filename": f"{package.replace('-', '_')}-{version}-py3-none-any.whl",
                        "url": f"https://wheels/{package}/{version}",
                        "digests": {"sha256": digest},
                    }
                ]
            },
        )

    def run(command, **kwargs):
        commands.append(command)
        if command[:2] == ["uv", "venv"]:
            python = Path(command[2]) / "bin/python"
            python.parent.mkdir(parents=True)
            python.touch()
        elif "-c" in command:
            Path(command[-1]).write_text(
                json.dumps({"problems": identity_problems or []})
            )

    monkeypatch.setattr(requests, "get", get)
    monkeypatch.setattr(uk_candidate, "_download", lambda url, path, **kwargs: path)
    monkeypatch.setattr(
        uk_candidate,
        "sha256_file",
        lambda path: (
            "0" * 64
            if (
                ("policyengine_uk" in path.name and bad_download == "policyengine-uk")
                or (
                    "policyengine_core" in path.name
                    and bad_download == "policyengine-core"
                )
            )
            else previous[
                "model_wheel_sha256"
                if "policyengine_uk" in path.name
                else "core_wheel_sha256"
            ]
        ),
    )
    return previous, commands, run


def test_previous_baseline_installs_the_certificate_pair_not_the_wrapper_extra(
    tmp_path, monkeypatch
):
    from policyengine.provenance import uk_candidate

    previous, commands, run = _previous_install_io(tmp_path, monkeypatch)
    uk_candidate.previous_pair_python(previous, tmp_path, run=run)
    install = next(
        command for command in commands if command[:3] == ["uv", "pip", "install"]
    )
    assert f"policyengine=={previous['bundle_version']}" in install
    assert not any(argument.startswith("policyengine[uk]") for argument in install)
    assert any("policyengine_uk-2.125.1" in argument for argument in install)
    assert any("policyengine_core-3.33.0" in argument for argument in install)
    assert any("-c" in command for command in commands), (
        "The installed wheels must be verified."
    )


@pytest.mark.parametrize("package", ["policyengine-uk", "policyengine-core"])
@pytest.mark.parametrize("source", ["PyPI", "download"])
def test_previous_baseline_refuses_a_different_wheel_hash(
    tmp_path, monkeypatch, package, source
):
    from policyengine.provenance import uk_candidate

    previous, _, run = _previous_install_io(
        tmp_path,
        monkeypatch,
        bad_pypi=package if source == "PyPI" else None,
        bad_download=package if source == "download" else None,
    )
    result, _ = uk_candidate.run_gate(
        "metrics_review",
        lambda: uk_candidate.previous_pair_python(previous, tmp_path, run=run),
    )
    assert result.status == "unavailable"
    assert package in result.summary and "wheel differs" in result.summary


def test_previous_baseline_refuses_installed_mismatches_and_rechecks_reused_environments(
    tmp_path, monkeypatch
):
    from policyengine.provenance import uk_candidate

    previous, commands, run = _previous_install_io(tmp_path, monkeypatch)
    first = uk_candidate.previous_pair_python(previous, tmp_path, run=run)
    second = uk_candidate.previous_pair_python(previous, tmp_path, run=run)
    assert first == second
    assert sum(command[:2] == ["uv", "venv"] for command in commands) == 1
    assert sum("-c" in command for command in commands) == 2
    previous, _, run = _previous_install_io(
        tmp_path,
        monkeypatch,
        identity_problems=["policyengine-core: installed bytes differ"],
    )
    result, _ = uk_candidate.run_gate(
        "metrics_review",
        lambda: uk_candidate.previous_pair_python(previous, tmp_path, run=run),
    )
    assert result.status == "unavailable"
    assert "installed bytes differ" in result.summary


def test_previous_baseline_cache_changes_when_same_wrapper_certifies_a_new_pair(
    tmp_path, monkeypatch
):
    from policyengine.provenance import uk_candidate

    previous, _, run = _previous_install_io(tmp_path, monkeypatch)
    first = uk_candidate.previous_pair_python(previous, tmp_path, run=run)
    previous["model_version"] = "2.126.12"
    second = uk_candidate.previous_pair_python(previous, tmp_path, run=run)
    assert first != second


@pytest.mark.parametrize(
    "changed_pin",
    [
        "model_version",
        "core_version",
        "data_release_version",
        "dataset_sha256",
        "model_wheel_sha256",
        "core_wheel_sha256",
    ],
)
def test_a_ledger_baseline_must_match_every_previous_certificate_pin(
    tmp_path, changed_pin
):
    from policyengine.provenance import uk_candidate
    from policyengine.provenance.qualification_ledger import write_json
    from tests.qualification_fixtures import make_pair, make_receipt

    pair = make_pair()
    previous = {
        "bundle_version": "6.3.0",
        "qualification_pair_id": pair.pair_id,
        "model_version": pair.model.version,
        "core_version": pair.core.version,
        "data_release_version": pair.data.release_version,
        "dataset_sha256": pair.data.dataset_sha256,
    }
    write_json(
        tmp_path / "uk" / pair.pair_id / "qualification_receipt.json",
        make_receipt(pair).canonical_payload(),
    )
    previous[changed_pin] = "0" * 64 if changed_pin.endswith("sha256") else "999.0.0"
    result, _ = uk_candidate.run_gate(
        "metrics_review", lambda: uk_candidate._previous_pair_pins(previous, tmp_path)
    )
    assert result.status == "unavailable"
    assert "different pairs" in result.summary


def test_a_ledger_baseline_supplies_exact_wheel_and_data_pins(tmp_path):
    from policyengine.provenance import uk_candidate
    from policyengine.provenance.qualification_ledger import write_json
    from tests.qualification_fixtures import make_pair, make_receipt

    pair = make_pair()
    previous = {
        "bundle_version": "6.3.0",
        "qualification_pair_id": pair.pair_id,
        "model_version": pair.model.version,
        "core_version": pair.core.version,
        "data_release_version": pair.data.release_version,
        "dataset_sha256": pair.data.dataset_sha256,
    }
    write_json(
        tmp_path / "uk" / pair.pair_id / "qualification_receipt.json",
        make_receipt(pair).canonical_payload(),
    )
    pins = uk_candidate._previous_pair_pins(previous, tmp_path)
    assert pins["model_wheel_sha256"] == pair.model.wheel_sha256
    assert pins["core_wheel_sha256"] == pair.core.wheel_sha256
    assert pins["dataset_reference"] == {
        "repo_id": pair.data.repo_id,
        "repo_type": pair.data.repo_type,
        "path": pair.data.dataset_path,
        "revision": pair.data.dataset_revision,
        "sha256": pair.data.dataset_sha256,
    }


@pytest.mark.parametrize("package", ["policyengine-uk", "policyengine-core"])
@pytest.mark.parametrize(
    "mismatch", ["version", "wheel", "installed bytes", "missing package"]
)
def test_baseline_identity_verification_detects_installed_mismatches(
    tmp_path, monkeypatch, package, mismatch
):
    import json
    import sys

    from policyengine.provenance import uk_candidate, wheels

    settings = {
        "source": str(
            __import__("pathlib").Path(uk_candidate.__file__).resolve().parents[1]
        ),
        "wheels": [
            {
                "name": name,
                "version": "1.0.0",
                "sha256": "1" * 64,
                "path": str(tmp_path / f"{name}.whl"),
            }
            for name in ("policyengine-uk", "policyengine-core")
        ],
    }

    def installed_version(name):
        from importlib.metadata import PackageNotFoundError

        if name == package and mismatch == "missing package":
            raise PackageNotFoundError(name)
        return "2.0.0" if name == package and mismatch == "version" else "1.0.0"

    monkeypatch.setattr("importlib.metadata.version", installed_version)
    monkeypatch.setattr(
        wheels,
        "verify_installed_against_wheel",
        lambda name, path: {
            "wheel_sha256": "2" * 64
            if name == package and mismatch == "wheel"
            else "1" * 64,
            "problems": [f"{name}: mutated installed bytes"]
            if name == package and mismatch == "installed bytes"
            else [],
        },
    )
    output = tmp_path / "identity.json"
    monkeypatch.setattr(sys, "argv", ["runner", json.dumps(settings), str(output)])
    # Restore the package namespace the isolated verifier creates when the test ends.
    monkeypatch.setitem(sys.modules, "policyengine", sys.modules["policyengine"])
    exec(
        compile(uk_candidate.PREVIOUS_IDENTITY_RUNNER, "previous-identity", "exec"), {}
    )
    report = json.loads(output.read_text())
    assert report["problems"] and package in report["problems"][0]


def test_previous_data_is_downloaded_from_its_pin_and_verified(tmp_path, monkeypatch):
    import hashlib
    import json
    from types import SimpleNamespace

    import requests

    from policyengine.provenance import uk_candidate

    data = b"exact previous data"
    digest = hashlib.sha256(data).hexdigest()
    previous = _previous_certificate()
    previous["dataset_sha256"] = previous["dataset_reference"]["sha256"] = digest
    urls = []

    def download(url, path, **kwargs):
        urls.append(url)
        path.parent.mkdir(parents=True)
        path.write_bytes(data)
        return path

    monkeypatch.setattr(uk_candidate, "_download", download)
    monkeypatch.setattr(
        requests,
        "get",
        lambda *args, **kwargs: SimpleNamespace(
            raise_for_status=lambda: None,
            content=json.dumps(_previous_release_manifest(previous)).encode(),
        ),
    )
    path = uk_candidate.previous_pair_dataset(previous, tmp_path)
    assert urls == [
        "https://huggingface.co/policyengine/uk-data/resolve/"
        + "a" * 40
        + "/national.h5"
    ]
    assert path.read_bytes() == data
    path.write_bytes(b"wrong published wrapper data")
    result, _ = uk_candidate.run_gate(
        "metrics_review", lambda: uk_candidate.previous_pair_dataset(previous, tmp_path)
    )
    assert result.status == "unavailable"
    assert "dataset bytes differ" in result.summary


def _previous_release_manifest(previous):
    return {
        "schema_version": 1,
        "country_id": "uk",
        "data_package": {
            "name": "uk-data",
            "version": previous["data_release_version"],
        },
        "default_datasets": {"national": previous["dataset_name"]},
        "artifacts": {
            previous["dataset_name"]: {
                "kind": "microdata",
                **previous["dataset_reference"],
            }
        },
    }


@pytest.mark.parametrize(
    "mismatch",
    [
        "release",
        "default dataset",
        "dataset sha",
        "dataset revision",
        "dataset path",
        "dataset repo",
        "dataset repo type",
        "dataset absent",
        "manifest sha",
    ],
)
def test_previous_baseline_refuses_a_mismatched_release_manifest(
    tmp_path, monkeypatch, mismatch
):
    import hashlib
    import json
    from types import SimpleNamespace

    import requests

    from policyengine.provenance import uk_candidate

    previous = _previous_certificate()
    data = b"certified previous data"
    digest = hashlib.sha256(data).hexdigest()
    previous["dataset_sha256"] = previous["dataset_reference"]["sha256"] = digest
    path = tmp_path / "previous-data" / digest / "national.h5"
    path.parent.mkdir(parents=True)
    path.write_bytes(data)
    manifest = _previous_release_manifest(previous)
    if mismatch == "release":
        manifest["data_package"]["version"] = "999.0.0"
    elif mismatch == "default dataset":
        manifest["default_datasets"]["national"] = "wrong"
    elif mismatch == "dataset sha":
        manifest["artifacts"]["national"]["sha256"] = "0" * 64
    elif mismatch == "dataset revision":
        manifest["artifacts"]["national"]["revision"] = "c" * 40
    elif mismatch == "dataset path":
        manifest["artifacts"]["national"]["path"] = "other.h5"
    elif mismatch == "dataset repo":
        manifest["artifacts"]["national"]["repo_id"] = "policyengine/other-data"
    elif mismatch == "dataset repo type":
        manifest["artifacts"]["national"]["repo_type"] = "dataset"
    elif mismatch == "dataset absent":
        manifest["artifacts"] = {}
    else:
        previous["release_manifest_reference"]["sha256"] = "0" * 64
    monkeypatch.setattr(
        requests,
        "get",
        lambda *a, **k: SimpleNamespace(
            raise_for_status=lambda: None, content=json.dumps(manifest).encode()
        ),
    )
    result, _ = uk_candidate.run_gate(
        "metrics_review", lambda: uk_candidate.previous_pair_dataset(previous, tmp_path)
    )
    assert result.status == "unavailable"
    assert "manifest" in result.summary


@pytest.mark.parametrize(
    "missing",
    ["dataset_reference", "dataset_sha256", "core_version", "data_release_version"],
)
def test_unpinned_previous_baselines_are_incomplete(tmp_path, missing):
    from policyengine.provenance import uk_candidate

    previous = _previous_certificate()
    del previous[missing]
    result, _ = uk_candidate.run_gate(
        "metrics_review", lambda: uk_candidate.previous_pair_dataset(previous, tmp_path)
    )
    assert result.status == "unavailable"


def _orchestrate_metrics(tmp_path, monkeypatch, metrics, identity_mismatch=False):
    """Run ``run_candidate_gates`` with only the metrics gate and ``metrics``
    standing in for ``run_metrics_report``; ``(results, evidence)``."""

    import json
    from pathlib import Path
    from types import SimpleNamespace

    from policyengine.provenance import dataset_materialization, uk_candidate
    from tests.qualification_fixtures import HARNESS, make_pair

    previous = _previous_certificate()
    previous_path = tmp_path / "certified-previous.h5"
    candidate_path = tmp_path / "candidate.h5"
    config = json.loads(
        (
            Path(__file__).parents[1] / "src/policyengine/data/qualification/uk.json"
        ).read_text()
    )
    monkeypatch.setattr(uk_candidate, "_previous_pair_pins", lambda *args: previous)
    monkeypatch.setattr(
        uk_candidate, "previous_pair_python", lambda *args: "certified-previous-python"
    )

    def previous_dataset(*args):
        if identity_mismatch:
            raise uk_candidate.PreviousPairUnavailable(
                "Previous dataset identity mismatch"
            )
        return previous_path

    monkeypatch.setattr(uk_candidate, "previous_pair_dataset", previous_dataset)
    monkeypatch.setattr(
        dataset_materialization,
        "materialize_dataset",
        lambda *a, **k: SimpleNamespace(path=candidate_path),
    )
    monkeypatch.setattr(uk_candidate, "vendor_metrics_tool", lambda *a, **k: tmp_path)

    def only_metrics(gates):
        gate = next(function for name, function in gates if name == "metrics_review")
        result, evidence = uk_candidate.run_gate("metrics_review", gate)
        return [result], {"metrics_review": evidence}

    monkeypatch.setattr(uk_candidate, "run_gates", only_metrics)
    monkeypatch.setattr(uk_candidate, "run_metrics_report", metrics)
    return uk_candidate.run_candidate_gates(
        SimpleNamespace(pair=make_pair()),
        HARNESS,
        config=config,
        work_dir=tmp_path,
        previous_certificate=previous,
        ledger_root=None,
    )


def test_a_malformed_metrics_report_is_not_written_to_the_ledger(tmp_path, monkeypatch):
    """The attempt's evidence goes to a public ledger branch: a report that
    breaks the small-cell format is kept only as its digest and problems."""

    import json

    marker = 987654321.5  # synthetic

    def metrics(python, vendor, **settings):
        report = _report()
        report["dataset_path"] = str(settings["dataset_path"])
        if settings["label"] == "candidate":
            report["metrics"][0].update(value=marker, suppressed=True)
        return report

    results, evidence = _orchestrate_metrics(tmp_path, monkeypatch, metrics)
    assert results[0].status == "fail"
    assert set(evidence["metrics_report_candidate"]) == {
        "withheld",
        "report_sha256",
        "problems",
    }
    assert str(marker) not in json.dumps(evidence["metrics_report_candidate"])
    assert evidence["metrics_report_previous"]["metrics"] == _report()["metrics"]


@pytest.mark.parametrize("identity_mismatch", [False, True])
def test_metric_orchestration_uses_the_verified_previous_dataset_before_computing(
    tmp_path, monkeypatch, identity_mismatch
):
    calls = []

    def metrics(python, vendor, **settings):
        calls.append((python, settings))
        report = _report()
        report["dataset_path"] = str(settings["dataset_path"])
        if settings["label"] != "previous":
            report["metrics"][0]["value"] = 1e12
        return report

    results, _ = _orchestrate_metrics(tmp_path, monkeypatch, metrics, identity_mismatch)
    previous_path = tmp_path / "certified-previous.h5"
    if identity_mismatch:
        assert results[0].status == "unavailable"
        assert calls == [], (
            "Unverified baselines must be refused before computing metrics."
        )
    else:
        assert results[0].status == "needs_review"
        previous_call = next(call for call in calls if call[1]["label"] == "previous")
        assert previous_call[0] == "certified-previous-python"
        assert previous_call[1]["dataset_path"] == previous_path
        assert "data_dir" not in previous_call[1]


@pytest.mark.parametrize(
    "failure", ["install", "verifier", "missing report", "bad json", "bad schema"]
)
def test_baseline_installation_or_verification_failure_is_incomplete(
    tmp_path, monkeypatch, failure
):
    import subprocess
    from pathlib import Path

    from policyengine.provenance import uk_candidate

    previous, _, fake_run = _previous_install_io(tmp_path, monkeypatch)

    def run(command, **kwargs):
        if (failure == "install" and command[:3] == ["uv", "pip", "install"]) or (
            failure == "verifier" and "-c" in command
        ):
            raise subprocess.CalledProcessError(1, command)
        fake_run(command, **kwargs)
        if "-c" in command:
            output = Path(command[-1])
            if failure == "missing report":
                output.unlink()
            elif failure == "bad json":
                output.write_text("invalid json")
            elif failure == "bad schema":
                output.write_text("[]")

    result, _ = uk_candidate.run_gate(
        "metrics_review",
        lambda: uk_candidate.previous_pair_python(previous, tmp_path, run=run),
    )
    assert result.status == "unavailable"


@pytest.mark.parametrize(
    "mismatch", ["receipt pair", "receipt verdict", "dataset reference"]
)
def test_previous_pair_cannot_borrow_another_ledgers_identity(tmp_path, mismatch):
    from policyengine.provenance import uk_candidate
    from policyengine.provenance.qualification_ledger import write_json
    from tests.qualification_fixtures import gates, make_pair, make_receipt

    pair = make_pair()
    previous = {
        "bundle_version": "6.3.0",
        "qualification_pair_id": pair.pair_id,
        "model_version": pair.model.version,
        "core_version": pair.core.version,
        "data_release_version": pair.data.release_version,
        "dataset_sha256": pair.data.dataset_sha256,
    }
    receipt = make_receipt(pair)
    if mismatch == "receipt pair":
        receipt = make_receipt(make_pair(core="3.32.0"))
        previous["core_version"] = (
            "3.32.0"  # Other pins match; the receipt's pair id must still match.
        )
    elif mismatch == "receipt verdict":
        receipt = make_receipt(pair, gate_results=gates("fail"))
    else:
        previous["dataset_reference"] = {"path": "other.h5"}
    write_json(
        tmp_path / "uk" / pair.pair_id / "qualification_receipt.json",
        receipt.canonical_payload(),
    )
    result, _ = uk_candidate.run_gate(
        "metrics_review", lambda: uk_candidate._previous_pair_pins(previous, tmp_path)
    )
    assert result.status == "unavailable"
