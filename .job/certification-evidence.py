#!/usr/bin/env python3
"""Guarded, exact-cut evidence steps for the separate heavy-phase job.

Argument parsing and --help use only the standard library. Private artifacts
stay in an outside-Git Hugging Face cache; producer receipts contain only gate
identities, statuses and hashes. This script does not grant release acceptance.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPO = "policyengine/populace-uk-private"
LINE = "microcosm-uk-2024-25-national"
MODELS = {"old": "2.132.6", "new": "2.147.2"}
CUTS = {
    "old": f"{LINE}-20261019T083323Z-6cba5d71",
    "new": f"{LINE}-20261023T075039Z-a133f37a",
}
DATA_SHA = {
    "old": "810ba980005a8b907cb51464279fa5e0125464b7af9a4871b7f6744c30951ece",
    "new": "64f83900ca3a1242fb017585234844ce89f743d32e41cd2b6558057777f914aa",
}
CORE = "3.33.3"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path.name}")
    return value


def outside_git(path: Path) -> Path:
    path = path.expanduser().resolve()
    if path == ROOT or ROOT in path.parents:
        raise ValueError("Storage, caches and evidence outputs must be outside Git")
    if any((parent / ".git").exists() for parent in (path, *path.parents)):
        raise ValueError(
            "Storage, caches and evidence outputs must be outside every Git checkout"
        )
    return path


def write_json(path: Path, value: dict[str, Any]) -> None:
    path = outside_git(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False) as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
        temporary = Path(stream.name)
    temporary.replace(path)


def guard(storage: Path) -> None:
    """Refuse each expensive action unless both reservation and resources allow it."""
    storage = outside_git(storage)
    storage.mkdir(parents=True, exist_ok=True)
    script = Path(
        os.environ.get(
            "PE_CERTIFY_RESERVATION_SCRIPT",
            "~/reviews/fleet-ops/tools/reservation.py",
        )
    ).expanduser()
    subprocess.run([sys.executable, str(script), "allowed", "uk-hub"], check=True)
    load1 = os.getloadavg()[0]
    free = shutil.disk_usage(storage).free
    if load1 > 110 or free < 55_000_000_000:
        raise RuntimeError(
            f"Resource guard refused: load1={load1:.2f}; free_bytes={free} "
            "(requires load1 <=110 and free_bytes >=55000000000)"
        )


def clean_git_environment() -> dict[str, str]:
    return {
        key: value
        for key, value in os.environ.items()
        if key not in {"GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"}
    }


def candidate_binding(candidate: Path, *, certified: bool) -> dict[str, Any]:
    candidate = candidate.resolve()
    command = ["git", "-C", str(candidate)]
    if candidate == ROOT and (ROOT / ".job/git").is_dir():
        command = [
            "git",
            "--git-dir",
            str(ROOT / ".job/git"),
            "--work-tree",
            str(ROOT),
        ]
    head = subprocess.check_output(
        [*command, "rev-parse", "HEAD"], text=True, env=clean_git_environment()
    ).strip()
    manifest_path = candidate / "src/policyengine/data/bundle/manifest.json"
    manifest = read_json(manifest_path)
    release = manifest["data_releases"]["uk"]
    if certified:
        if manifest["packages"]["policyengine-uk"]["version"] != MODELS["new"]:
            raise ValueError("Candidate bundle does not pin policyengine-uk 2.147.2")
        if manifest["packages"]["policyengine-core"]["version"] != CORE:
            raise ValueError("Candidate bundle does not pin policyengine-core 3.33.3")
        if release["build_id"] != CUTS["new"]:
            raise ValueError("Candidate bundle identifies a different UK data cut")
        if release["certified_data_artifact"]["sha256"] != DATA_SHA["new"]:
            raise ValueError(
                "Candidate bundle identifies different national data bytes"
            )
        if release.get("regional_source_manifest_uri"):
            raise ValueError("Candidate still routes a regional release")
    return {
        "candidate_commit": head,
        "bundle_manifest_sha256": sha256(manifest_path),
        "bundle_uk_build_id": release["build_id"],
        "evaluated_before_certification": not certified,
    }


def manifest(metadata: Path, label: str) -> tuple[dict[str, Any], str]:
    path = metadata / f"{label}-release_manifest.json"
    value = read_json(path)
    build = value["build"]
    if build["cut_tag"] != CUTS[label]:
        raise ValueError(f"Unexpected {label} release cut")
    if build["build_id"] != LINE:
        raise ValueError("The producer line changed")
    if build["built_with_model_package"]["version"] != MODELS[label]:
        raise ValueError(f"Unexpected build-time model for {label} cut")
    if build["built_with_core_package"]["version"] != CORE:
        raise ValueError(f"Unexpected build-time core for {label} cut")
    for artifact in value["artifacts"].values():
        if artifact.get("repo_id") != REPO or artifact.get("revision") != CUTS[label]:
            raise ValueError("Artifact is not pinned to the intended repository/cut")
        expected = artifact.get("sha256", "")
        if len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
            raise ValueError("Every artifact must have a SHA-256")
    name = value["default_datasets"]["national"]
    if value["artifacts"][name]["sha256"] != DATA_SHA[label]:
        raise ValueError(f"Unexpected {label} national data SHA-256")
    return value, sha256(path)


def cache_directory(fallback: Path) -> Path:
    setting = os.environ.get("HF_HUB_CACHE")
    if setting:
        return outside_git(Path(setting))
    home = os.environ.get("HF_HOME")
    return outside_git(Path(home) / "hub" if home else fallback / "hf-cache")


def fetch(artifact: dict[str, Any], cache: Path) -> Path:
    """Download/hash bytes without loading H5 or echoing private producer detail."""
    guard(cache)
    from huggingface_hub import hf_hub_download

    filename = artifact["path"]
    if artifact.get("kind") == "diagnostics" and not filename.startswith("releases/"):
        filename = f"releases/{LINE}/{filename}"
    downloaded = Path(
        hf_hub_download(
            repo_id=artifact["repo_id"],
            repo_type="dataset",
            revision=artifact["revision"],
            filename=filename,
            token=os.environ.get("HUGGING_FACE_TOKEN") or os.environ.get("HF_TOKEN"),
            cache_dir=str(cache),
        )
    )
    if sha256(downloaded) != artifact["sha256"]:
        raise ValueError(f"Downloaded artifact SHA-256 mismatch: {filename}")
    return downloaded


def producer_gates(args: argparse.Namespace) -> int:
    value, release_digest = manifest(args.metadata, "new")
    cache = cache_directory(args.output.parent)
    paths = {
        name: fetch(artifact, cache) for name, artifact in value["artifacts"].items()
    }
    certification = read_json(paths["release_certification"])
    if certification.get("shippable") is not True:
        raise ValueError("Producer certification is not shippable")
    if certification["candidate"]["sha256"] != DATA_SHA["new"]:
        raise ValueError("Producer certification identifies other candidate bytes")
    part_artifacts = {
        "calibration_seam": "terminal_gates",
        "release_cut": "release_cut_gates",
        "spine": "spine_gates",
    }
    for part_name, artifact_name in part_artifacts.items():
        part = certification["parts"][part_name]
        artifact = value["artifacts"][artifact_name]
        if part["sha256"] != artifact["sha256"]:
            raise ValueError(f"Producer certification part SHA mismatch: {part_name}")
        report = read_json(paths[artifact_name])
        for key in ("gates_manifest_sha256", "policy_sha256"):
            if part.get(key) != report.get(key) or not part.get(key):
                raise ValueError(
                    f"Producer certification part {key} mismatch: {part_name}"
                )
    gates_report = read_json(paths["release_cut_gates"])
    raw_gates = gates_report.get("gates")
    if not isinstance(raw_gates, dict):
        raise ValueError("Expected release-cut gates keyed by gate ID")
    ids = certification["parts"]["release_cut"]["entry_ids"]
    if len(ids) != 19 or len(set(ids)) != 19 or set(raw_gates) != set(ids):
        raise ValueError(
            "Producer certification and report must identify the same 19 gates"
        )
    gates = [
        {"gate_id": name, "status": raw_gates[name].get("status")}
        for name in sorted(ids)
    ]
    if any(gate["status"] != "passed" for gate in gates):
        raise ValueError("At least one release-cut gate did not pass")
    if certification["parts"]["release_cut"].get("statuses") != {"passed": 19}:
        raise ValueError(
            "Producer certification does not attest 19 passed release-cut gates"
        )
    if (
        gates_report.get("shippable") is not True
        or gates_report.get("blocked_at_phase") is not None
    ):
        raise ValueError("Release-cut gate report is blocked or not shippable")
    receipt = {
        "schema_version": 1,
        "step": "producer-gates",
        "status": "pass",
        **candidate_binding(args.candidate, certified=False),
        "release_manifest_sha256": release_digest,
        "cut_tag": CUTS["new"],
        "dataset_sha256": DATA_SHA["new"],
        "gates": gates,
        "artifact_sha256": {
            name: item["sha256"] for name, item in value["artifacts"].items()
        },
        "limitations": [
            "Producer evidence only; wrapper/model/data gates are separate.",
            "Raw producer detail remains private in the outside-Git cache.",
        ],
    }
    write_json(args.output, receipt)
    return 0


def materialize(args: argparse.Namespace) -> int:
    storage = outside_git(args.storage)
    value, release_digest = manifest(args.metadata, args.label)
    name = value["default_datasets"]["national"]
    source = fetch(value["artifacts"][name], cache_directory(storage))
    target = storage / "data" / f"{args.label}.h5"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        if sha256(target) != DATA_SHA[args.label]:
            raise ValueError(f"Existing {args.label} data file has different bytes")
    else:
        target.symlink_to(source.resolve())
    receipt = {
        "schema_version": 1,
        "step": "materialize",
        "status": "pass",
        **candidate_binding(args.candidate, certified=False),
        "label": args.label,
        "cut_tag": CUTS[args.label],
        "dataset_sha256": DATA_SHA[args.label],
        "release_manifest_sha256": release_digest,
        "data_path": str(target),
        "data_loaded": False,
    }
    write_json(
        args.output or storage / "evidence" / f"materialize-{args.label}.json", receipt
    )
    return 0


def wrapper(candidate: Path) -> Any:
    source = candidate.resolve() / "src"
    sys.path.insert(0, str(source))
    os.environ["POLICYENGINE_SKIP_COUNTRY_IMPORTS"] = "1"
    gate_module = importlib.import_module("policyengine.provenance.uk_candidate")
    if source not in Path(gate_module.__file__).resolve().parents:
        raise ValueError(
            "Imported qualification gates do not belong to the candidate source"
        )
    for package, expected in (
        ("policyengine-uk", MODELS["new"]),
        ("policyengine-core", CORE),
    ):
        if importlib.metadata.version(package) != expected:
            raise ValueError(
                f"The evidence environment must install {package}=={expected}"
            )
    return gate_module


def checked_data(path: Path, label: str) -> Path:
    path = outside_git(path)
    if sha256(path) != DATA_SHA[label]:
        raise ValueError(f"{label} data file SHA-256 does not match the pinned cut")
    return path


def qualified_metadata(args: argparse.Namespace) -> dict[str, Any]:
    _, digest = manifest(args.metadata, "new")
    return {
        **candidate_binding(args.candidate, certified=True),
        "release_manifest_sha256": digest,
        "dataset_sha256": DATA_SHA["new"],
        "model_version": MODELS["new"],
        "core_version": CORE,
    }


def gate_record(outcome: Any) -> dict[str, Any]:
    result, evidence = outcome
    return {"result": result.model_dump(mode="json"), "evidence": evidence}


def budget_inputs(args: argparse.Namespace) -> int:
    binding = qualified_metadata(args)
    module = wrapper(args.candidate)
    old_data, new_data = (
        checked_data(args.old_data, "old"),
        checked_data(args.new_data, "new"),
    )
    qualification = args.candidate / "src/policyengine/data/qualification"
    config = read_json(qualification / "uk.json")
    critical_path = qualification / config["budget_inputs"]["critical"]
    critical = read_json(critical_path)
    storage = outside_git(args.output.parent)
    storage.mkdir(parents=True, exist_ok=True)
    # Resolving a venv's python symlink would select the base interpreter and
    # silently lose the old model environment.
    old_python = str(args.old_python.expanduser().absolute())
    versions_code = (
        "import importlib.metadata as m,json;print(json.dumps({n:m.version(n) "
        "for n in ('policyengine-uk','policyengine-core')}))"
    )
    old_versions = json.loads(
        subprocess.check_output([old_python, "-c", versions_code], text=True)
    )
    if old_versions != {"policyengine-uk": MODELS["old"], "policyengine-core": CORE}:
        raise ValueError(
            "Old input snapshot environment has different model/core versions"
        )
    with tempfile.TemporaryDirectory(prefix="inputs-", dir=storage) as directory:
        work = Path(directory)
        guard(storage)
        previous = module.run_inputs_snapshot(
            old_python,
            critical=critical["critical"],
            out=work / "previous.json",
            dataset_path=old_data,
        )
        guard(storage)
        current = module.run_inputs_snapshot(
            sys.executable,
            critical=critical["critical"],
            out=work / "candidate.json",
            dataset_path=new_data,
        )
    from policyengine_uk.system import system

    previous_status = dict(previous["input_status"])
    for name in system.variables:
        previous_status.setdefault(
            name,
            {"in_model": False, "is_input": False, "in_data": False, "usable": False},
        )
    pair = SimpleNamespace(pair_id=binding["bundle_manifest_sha256"])
    guard(storage)
    inputs = module.budget_inputs(
        pair,
        new_data,
        model_input_variables=[
            name
            for name, variable in system.variables.items()
            if variable.is_input_variable()
        ],
        model_variables=system.variables,
        critical_inputs=critical["critical"],
        accepted_gaps=critical.get("accepted_gaps", {}),
        previous_missing_inputs=previous["missing_inputs"],
        previous_unusable_critical=[
            item[0] for item in previous.get("unusable_critical", [])
        ],
        previous_input_status=previous_status,
        previous_ever_usable_inputs=previous.get("ever_usable_inputs"),
    )
    guard(storage)
    years = module.supported_years(
        pair,
        new_data,
        required_years=config["required_years"],
        budget_horizon_years=config["budget_horizon_years"],
        previous_supported_years=previous["supported_years"],
        projected_years=lambda _: current["supported_years"],
    )
    _, old_manifest_digest = manifest(args.metadata, "old")
    receipt = {
        "schema_version": 1,
        "step": "budget-inputs",
        **binding,
        "previous_release_manifest_sha256": old_manifest_digest,
        "previous_dataset_sha256": DATA_SHA["old"],
        "previous_model_version": MODELS["old"],
        "qualification_config_sha256": sha256(qualification / "uk.json"),
        "critical_inputs_spec_sha256": sha256(critical_path),
        "budget_inputs": gate_record(inputs),
        "supported_years": gate_record(years),
        "limitations": [
            "Previous input coverage is recomputed on the direct previously certified pair.",
            "Earlier ever-usable input lineage beyond that predecessor is not reconstructed.",
        ],
    }
    write_json(args.output, receipt)
    return (
        2
        if any(
            outcome[0].status in {"fail", "error", "unavailable"}
            for outcome in (inputs, years)
        )
        else 0
    )


def reform_contract(args: argparse.Namespace) -> int:
    binding = qualified_metadata(args)
    module = wrapper(args.candidate)
    data = checked_data(args.new_data, "new")
    config_path = args.candidate / "src/policyengine/data/qualification/uk.json"
    settings = read_json(config_path)["reform_contract"]
    if (
        int(settings.get("seed", -1)) != 0
        or int(settings.get("max_examples", -1)) != 20
    ):
        raise ValueError(
            "Contract configuration must retain seed=0 and max_examples=20"
        )
    guard(args.output.parent)
    outcome = module.reform_contract(
        entrypoint=settings["entrypoint"],
        dataset_path=data,
        seed=0,
        max_examples=20,
        expected_versions={"policyengine-uk": MODELS["new"], "policyengine-core": CORE},
        expected_dataset_sha256=DATA_SHA["new"],
        pending_decisions=settings.get("pending_decisions", ()),
    )
    write_json(
        args.output,
        {
            "schema_version": 1,
            "step": "reform-contract",
            **binding,
            "qualification_config_sha256": sha256(config_path),
            **gate_record(outcome),
            "disclosure": "Uses the qualification gate's publishable_contract_report sanitization.",
        },
    )
    return 2 if outcome[0].status in {"fail", "error", "unavailable"} else 0


def replay_unavailable(args: argparse.Namespace) -> int:
    write_json(
        args.output,
        {
            "schema_version": 1,
            "step": "scorecard-replay",
            "status": "unavailable",
            **qualified_metadata(args),
            "reason": "Microcosm scorecard replay fix has not landed; exact-pair replay is unavailable.",
            "acceptance_basis": "Coordinator 23 October decision under d1682 and d1344; Budget-week same-line re-cut exception.",
            "limitations": [
                "Unavailable is not a replay pass; replace this receipt after the replay fix lands."
            ],
        },
    )
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name, function in (
        ("producer-gates", producer_gates),
        ("materialize", materialize),
        ("budget-inputs", budget_inputs),
        ("reform-contract", reform_contract),
        ("replay-unavailable", replay_unavailable),
    ):
        command = commands.add_parser(name, help=function.__doc__)
        command.add_argument("--candidate", "--wrapper", type=Path, default=ROOT)
        command.add_argument("--metadata", type=Path, default=ROOT / ".job/metadata")
        command.add_argument("--output", type=Path, required=name != "materialize")
        command.set_defaults(function=function)
        if name == "materialize":
            command.add_argument("--label", choices=("old", "new"), required=True)
            command.add_argument("--storage", type=Path, required=True)
        if name == "budget-inputs":
            command.add_argument("--old-python", type=Path, required=True)
            command.add_argument("--old-data", type=Path, required=True)
        if name in {"budget-inputs", "reform-contract"}:
            command.add_argument("--new-data", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        return args.function(args)
    except Exception as error:
        # Never dump raw private producer documents or survey arrays.
        print(
            f"{args.command} failed ({type(error).__name__}): {error}", file=sys.stderr
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
