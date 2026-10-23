#!/usr/bin/env python3
"""Index completed local evidence without granting an acceptance or publishing it."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

TAG = "microcosm-uk-2024-25-national-20261023T075039Z-a133f37a"
DATA_SHA = "64f83900ca3a1242fb017585234844ce89f743d32e41cd2b6558057777f914aa"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--preparation", required=True)
    args = parser.parse_args()
    candidate = args.candidate.resolve()
    evidence = args.evidence.resolve()
    bundle_path = candidate / "src/policyengine/data/bundle/manifest.json"
    bundle = json.loads(bundle_path.read_text())
    uk = bundle["data_releases"]["uk"]
    require(uk["build_id"] == TAG, "Unexpected UK cut")
    require(
        bundle["packages"]["policyengine-uk"]["version"] == "2.147.2",
        "Unexpected model",
    )
    require(
        bundle["packages"]["policyengine-core"]["version"] == "3.33.3",
        "Unexpected core",
    )
    require(
        not uk.get("regional_source_manifest_uri"), "National-only release required"
    )
    require(
        set(uk.get("region_datasets", {})) <= {"national"},
        "Regional output routes remain",
    )
    require(
        uk["datasets"][uk["default_dataset"]]["sha256"] == DATA_SHA,
        "Unexpected national data bytes",
    )
    head = subprocess.check_output(
        ["git", "-C", str(candidate), "rev-parse", "HEAD"], text=True
    ).strip()
    subprocess.run(
        [
            "git",
            "-C",
            str(candidate),
            "merge-base",
            "--is-ancestor",
            args.preparation,
            head,
        ],
        check=True,
    )
    require(
        head != args.preparation,
        "Mechanical certification has not committed a candidate",
    )
    require(
        not subprocess.check_output(
            [
                "git",
                "-C",
                str(candidate),
                "status",
                "--porcelain",
                "--untracked-files=no",
            ],
            text=True,
        ).strip(),
        "Evidence must bind an unchanged committed candidate",
    )
    bundle_digest = digest(bundle_path)
    required = [
        "producer-gates.json",
        "replay.json",
        "budget-inputs.json",
        "reform-contract.json",
        "attribution.json",
        "old-environment.txt",
        "materialize-old.json",
        "materialize-new.json",
    ]
    for name in required:
        require((evidence / name).is_file(), f"Missing evidence: {name}")
    records = {
        name: json.loads((evidence / name).read_text())
        for name in required
        if name.endswith(".json")
    }
    for name in (
        "replay.json",
        "budget-inputs.json",
        "reform-contract.json",
        "attribution.json",
    ):
        binding = (
            records[name]["binding"] if name == "attribution.json" else records[name]
        )
        require(
            binding.get("candidate_commit") == head, f"Stale candidate binding: {name}"
        )
        require(
            binding.get("bundle_manifest_sha256") == bundle_digest,
            f"Stale bundle binding: {name}",
        )
        require(
            binding.get("bundle_uk_build_id") == TAG, f"Different cut binding: {name}"
        )
    producer = records["producer-gates.json"]
    require(
        producer.get("candidate_commit") == args.preparation,
        "Stale producer preparation binding",
    )
    require(
        producer.get("status") == "pass" and producer.get("cut_tag") == TAG,
        "Producer gates did not pass on this cut",
    )
    require(
        producer.get("dataset_sha256") == DATA_SHA,
        "Producer gates identify other data bytes",
    )
    for label in ("old", "new"):
        receipt = records[f"materialize-{label}.json"]
        require(
            receipt.get("candidate_commit") == args.preparation,
            f"Stale {label} materialization binding",
        )
        require(receipt.get("status") == "pass", f"Failed {label} materialization")
    for suffix in (
        "uc_floor.json",
        "certify.log",
        "certify.timings.jsonl",
        "pr-body.md",
    ):
        source = candidate.parent / f"{candidate.name}.{suffix}"
        require(source.is_file(), f"Missing tool artifact: {source}")
        shutil.copyfile(source, evidence / f"mechanical-{suffix}")
    timings = {}
    for line in (
        (evidence / "mechanical-certify.timings.jsonl").read_text().splitlines()
    ):
        record = json.loads(line)
        timings[record["step"]] = record
    for name in ("certify-data", "TROs", "snapshots", "strict-check", "tests"):
        require(
            timings.get(name, {}).get("returncode") == 0,
            f"No successful final mechanical stage: {name}",
        )
    uc = json.loads((evidence / "mechanical-uc_floor.json").read_text())
    require(
        uc.get("check") == "uk_uc_floor" and isinstance(uc.get("passed"), bool),
        "No measured UC-floor receipt",
    )
    require(
        uc.get("model_version") == "2.147.2" and TAG in uc.get("dataset", ""),
        "Stale UC-floor receipt",
    )
    require(
        timings.get("UC-floor", {}).get("returncode") == (0 if uc["passed"] else 1),
        "UC-floor timing disagrees with measured receipt",
    )
    replay = records["replay.json"]
    require(
        replay.get("status") == "unavailable",
        "Update the reviewed exception before changing replay status",
    )
    require(
        not records["attribution.json"].get("synthetic_fixture"),
        "Synthetic attribution is not release evidence",
    )
    gate_statuses = {
        "budget_inputs": records["budget-inputs.json"]["budget_inputs"]["result"][
            "status"
        ],
        "supported_years": records["budget-inputs.json"]["supported_years"]["result"][
            "status"
        ],
        "reform_contract": records["reform-contract.json"]["result"]["status"],
    }
    for name, status in gate_statuses.items():
        require(
            status in {"pass", "needs_review"},
            f"Gate {name} is {status}; resolve before indexing completed evidence",
        )
    # The runner appends the index step after this command exits, and tee is
    # still writing this command's own log. Index only immutable snapshots.
    outer_timings = evidence / "timings.jsonl"
    require(outer_timings.is_file(), "Missing sequential runner timings")
    shutil.copyfile(outer_timings, evidence / "timings-before-index.jsonl")
    live_files = {"evidence-index.json", "evidence-index.log", "timings.jsonl"}
    index = {
        "schema_version": 1,
        "status": "evidence collected; review required; replay unavailable",
        "preparation_commit": args.preparation,
        "candidate_commit": head,
        "bundle_manifest_sha256": bundle_digest,
        "cut_tag": uk["build_id"],
        "model": "2.147.2",
        "core": "3.33.3",
        "regional_outputs": "absent",
        "replay": replay,
        "qualification_gates": gate_statuses,
        "mechanical_stages": {
            name: timings[name]["returncode"]
            for name in (
                "certify-data",
                "TROs",
                "snapshots",
                "strict-check",
                "UC-floor",
                "tests",
            )
        },
        "excluded_live_files": sorted(live_files),
        "files": [
            {
                "path": file.name,
                "sha256": digest(file),
                "size_bytes": file.stat().st_size,
            }
            for file in sorted(evidence.iterdir())
            if file.is_file() and file.name not in live_files
        ],
        "human_actions": [
            "Review UC-floor and gate results; record any explicit fresh acceptance.",
            "Map every flagged attribution move or retain its unattributed label and limitation.",
            "Confirm old build 810315ac2, inferred from pinned producer certification path.",
            "Replay remains unavailable until the Microcosm replay fix lands.",
            "Verify/create certification issue, replace PR-body placeholder, add issue changelog.",
            "Run normal format/lint/PR checks; evidence must bind final candidate if it changes.",
            "Push only the reviewed certification branch and open a canonical draft stacked on #704.",
        ],
    }
    (evidence / "evidence-index.json").write_text(json.dumps(index, indent=2) + "\n")
    print(json.dumps({"candidate_commit": head, "status": index["status"]}))


if __name__ == "__main__":
    main()
