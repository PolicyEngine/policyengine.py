#!/usr/bin/env python3
"""Serial, isolated 2x2 attribution for the Saturday UK national recut.

Only `fixture-check`, `validate`, and --help are permitted during preparation.
`run` and its internal `cell` command load national data and belong to the
reserved heavy phase. This is private certification tooling, not public API.
"""

from __future__ import annotations

import argparse
import fnmatch
import gc
import hashlib
import importlib.metadata
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VERSIONS = {"old": "2.132.6", "new": "2.147.2"}
CUTS = {
    "old": "microcosm-uk-2024-25-national-20261019T083323Z-6cba5d71",
    "new": "microcosm-uk-2024-25-national-20261023T075039Z-a133f37a",
}
YEARS = tuple(range(2026, 2031))
CELL_IDS = tuple(
    f"{data}_data__{model}_model" for data in VERSIONS for model in VERSIONS
)
EDGES = {
    "model_on_old_data": ("old_data__old_model", "old_data__new_model"),
    "model_on_new_data": ("new_data__old_model", "new_data__new_model"),
    "data_on_old_model": ("old_data__old_model", "new_data__old_model"),
    "data_on_new_model": ("old_data__new_model", "new_data__new_model"),
    "total_change": ("old_data__old_model", "new_data__new_model"),
}
LIMITATIONS = [
    "Same producer line, Budget week only; pinned model versions at each cut's build version.",
    "Fiscal-year integer 2026 means FY2026-27; each model applies its own projection rules to fixed input bytes.",
    "A model edge includes the pinned model's required dependency environment and projection changes; it is not a formula-only experiment.",
    "The two conditional model effects and two conditional data effects can differ. The interaction is reported, not silently assigned to either cause.",
    "Missing or uncomputable cross cells do not invalidate computable edges; they prevent the affected decomposition and interaction from being identified.",
    "A missing variable is not treated as zero. Errors, missing variables and privacy suppressions have null values and no computed delta.",
    "Heads are a union across model versions and may overlap. Government balance is measured directly; summing all reported heads is invalid.",
    "Money totals are conservatively suppressed together when any nonzero head has fewer than ten positive-weight cases, preventing complementary disclosure through balance or other heads.",
    "Poverty counts and rates use person weights and HBAI groups; cells below ten positive-weight observations or ten poor/nonpoor cases are suppressed together.",
    "Source-path overlap generates review candidates, not proven causal attribution. Only reviewed mappings with an explanation count as attributed; every other flagged move is explicitly unattributed.",
    "A reviewed mapping associates a move with changes; no PR-specific counterfactual is run and no numerical share is assigned to an individual PR.",
    "Scorecard replay is unavailable until the Microcosm replay fix lands; this attribution is not a scorecard replay.",
]


def read_json(path):
    return json.loads(Path(path).read_text())


def write_json(path, value):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    )


def digest(path):
    sha = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def git(repo, *arguments, strip=True):
    # Caller can have an isolated policyengine.py GIT_DIR; never let it route
    # reads intended for these source repositories into that Git directory.
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    value = subprocess.check_output(
        ["git", "-C", str(repo), *arguments], text=True, env=env
    )
    return value.strip() if strip else value


def histories(model_repo, microcosm_repo, old_build, new_build):
    out = {}
    for name, repo, start, end in (
        ("model", model_repo, VERSIONS["old"], VERSIONS["new"]),
        ("data", microcosm_repo, old_build, new_build),
    ):
        start = git(repo, "rev-parse", f"{start}^{{commit}}")
        end = git(repo, "rev-parse", f"{end}^{{commit}}")
        # An inverted/nonancestor range would silently omit changes.
        git(repo, "merge-base", "--is-ancestor", start, end)
        lines = git(
            repo,
            "log",
            "--first-parent",
            "--reverse",
            "--format=%H%x09%s",
            f"{start}..{end}",
        )
        changes = []
        for line in lines.splitlines():
            commit, subject = line.split("\t", 1)
            prs = sorted(set(int(n) for n in re.findall(r"#(\d+)", subject)))
            paths = git(
                repo,
                "diff-tree",
                "--no-commit-id",
                "--name-only",
                "-r",
                f"{commit}^",
                commit,
            ).splitlines()
            changes.append(
                {"commit": commit, "subject": subject, "prs": prs, "paths": paths}
            )
        out[name] = {
            "from": start,
            "to": end,
            "range": f"{start}..{end}",
            "changes": changes,
        }
    return out


def check_definitions(definitions, model_repo):
    for item in definitions["source_files"]:
        raw = git(model_repo, "show", f"{item['ref']}:{item['path']}", strip=False)
        if hashlib.sha256(raw.encode()).hexdigest() != item["sha256"]:
            raise ValueError(
                f"Pinned attribution definition differs: {item['ref']}:{item['path']}"
            )


def candidate_binding(candidate, expected_sha):
    candidate = candidate.expanduser().resolve()
    command = ["git", "-C", str(candidate)]
    if candidate == ROOT.parent and (ROOT / "git").is_dir():
        command = ["git", "--git-dir", str(ROOT / "git"), "--work-tree", str(candidate)]
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    commit = subprocess.check_output(
        [*command, "rev-parse", "HEAD"], text=True, env=env
    ).strip()
    path = candidate / "src/policyengine/data/bundle/manifest.json"
    manifest = read_json(path)
    release = manifest["data_releases"]["uk"]
    if manifest["packages"]["policyengine-uk"]["version"] != VERSIONS["new"]:
        raise ValueError("Candidate does not pin policyengine-uk 2.147.2")
    if manifest["packages"]["policyengine-core"]["version"] != "3.33.3":
        raise ValueError("Candidate does not pin policyengine-core 3.33.3")
    if release["build_id"] != CUTS["new"] or release["version"] != CUTS["new"]:
        raise ValueError("Candidate does not bind the Saturday national cut")
    if release["certified_data_artifact"]["sha256"] != expected_sha:
        raise ValueError("Candidate does not bind the verified new national file")
    if release.get("regional_source_manifest_uri"):
        raise ValueError("Candidate must be national-only")
    return {
        "candidate_commit": commit,
        "bundle_manifest_sha256": digest(path),
        "bundle_uk_build_id": release["build_id"],
    }


def metrics(definitions):
    result = [
        {
            "id": "gov_balance",
            "variable": "gov_balance",
            "kind": "gbp",
            "label": "Government balance",
        }
    ]
    result += [
        {
            "id": f"{h['kind']}.{h['variable']}",
            "variable": h["variable"],
            "kind": "gbp",
            "label": h["label"],
        }
        for h in definitions["heads"]
    ]
    for measure in definitions["poverty"]["measures"]:
        for group in definitions["poverty"]["groups"]:
            for kind in ("count", "rate"):
                result.append(
                    {
                        "id": f"poverty.{measure['id']}.{group['id']}.{kind}",
                        "variable": measure["variable"],
                        "group_variable": group.get("variable"),
                        "kind": kind,
                        "label": f"{measure['label']}, {group['label']}, {kind}",
                    }
                )
    return result


def safe_error(error):
    # Country errors can include values of invalid input arrays. Preserve the
    # error type and traceback location, but never publish unit-record values.
    locations = [
        f"{Path(frame.filename).name}:{frame.lineno}:{frame.name}"
        for frame in traceback.extract_tb(error.__traceback__)
    ]
    return {
        "type": type(error).__name__,
        "message": "Country API raised an error; see restricted worker stderr for the original message.",
        "locations": locations,
    }


def worker(args):
    started = time.monotonic()
    output = {
        "id": args.cell_id,
        "model_version": args.expected_version,
        "data_cut": args.cut,
        "data_sha256": args.sha256,
        "status": "not_computable",
        "error": None,
        "metrics": [],
    }
    try:
        installed = importlib.metadata.version("policyengine-uk")
        if installed != args.expected_version:
            raise RuntimeError(
                f"Expected policyengine-uk {args.expected_version}, found {installed}"
            )
        if importlib.metadata.version("policyengine-core") != "3.33.3":
            raise RuntimeError(
                "The attribution requires policyengine-core 3.33.3 in both environments"
            )
        definitions = read_json(args.definitions)
        output["runtime"] = {
            "python": sys.version,
            "executable": sys.executable,
            "prefix": sys.prefix,
            "policyengine_uk": installed,
            "policyengine_core": importlib.metadata.version("policyengine-core"),
            "numpy": importlib.metadata.version("numpy"),
            "distributions": sorted(
                f"{d.metadata['Name']}=={d.version}"
                for d in importlib.metadata.distributions()
                if d.metadata["Name"]
            ),
        }
        import numpy as np
        from policyengine_uk import Microsimulation

        # Country-model API performs schema interpretation and uprating; no
        # direct policyengine-core builders or ad hoc column dropping.
        simulation = Microsimulation(dataset=str(args.data.resolve()))
        output["status"] = "computable"
        for year in YEARS:
            weights = {}
            monetary = []
            for metric in metrics(definitions):
                record = dict(
                    metric,
                    year=year,
                    fiscal_year=f"{year}-{str(year + 1)[2:]}",
                    value=None,
                    status="not_computable",
                    error=None,
                )
                try:
                    variables = simulation.tax_benefit_system.variables
                    record["required_for_diagonal"] = (
                        metric["kind"] != "gbp"
                        or metric["id"] == "gov_balance"
                        or metric["variable"] in variables
                    )
                    if metric["variable"] not in variables:
                        record["error"] = {
                            "type": "MissingVariable",
                            "message": f"{metric['variable']} is absent from policyengine-uk {installed}; it is not imputed as zero.",
                        }
                        output["metrics"].append(record)
                        continue
                    entity = variables[metric["variable"]].entity.key
                    if entity not in weights:
                        weights[entity] = np.asarray(
                            simulation.calculate(
                                f"{entity}_weight", year, unweighted=True
                            ),
                            dtype=np.float64,
                        )
                    weight = weights[entity]
                    values = np.asarray(
                        simulation.calculate(metric["variable"], year, unweighted=True),
                        dtype=np.float64,
                    )
                    if (
                        not np.all(np.isfinite(values))
                        or not np.all(np.isfinite(weight))
                        or np.any(weight < 0)
                    ):
                        raise ValueError("Nonfinite values or invalid weights")
                    if metric["kind"] == "gbp":
                        cases = int(np.count_nonzero((values != 0) & (weight > 0)))
                        record.update(
                            value=float(np.sum(values * weight, dtype=np.float64)),
                            status="ok",
                        )
                        if 0 < cases < 10:
                            record.update(value=None, status="suppressed")
                        monetary.append(record)
                    else:
                        # Poverty variables are household booleans; mapping
                        # directly to people repeats each person's status.
                        values = np.asarray(
                            simulation.calculate(
                                metric["variable"],
                                year,
                                map_to="person",
                                unweighted=True,
                            ),
                            dtype=np.float64,
                        )
                        if not np.all(np.isfinite(values)):
                            raise ValueError("Nonfinite person poverty values")
                        values = values.astype(bool)
                        if "person" not in weights:
                            weights["person"] = np.asarray(
                                simulation.calculate(
                                    "person_weight", year, unweighted=True
                                ),
                                dtype=np.float64,
                            )
                        weight = weights["person"]
                        if not np.all(np.isfinite(weight)) or np.any(weight < 0):
                            raise ValueError("Invalid person weights")
                        group = np.ones_like(values, dtype=bool)
                        if metric.get("group_variable"):
                            group = np.asarray(
                                simulation.calculate(
                                    metric["group_variable"],
                                    year,
                                    map_to="person",
                                    unweighted=True,
                                ),
                                dtype=bool,
                            )
                        observed = group & (weight > 0)
                        cases, poor_cases, nonpoor_cases = (
                            int(np.count_nonzero(mask))
                            for mask in (
                                observed,
                                observed & values,
                                observed & ~values,
                            )
                        )
                        denominator = float(np.sum(weight[group], dtype=np.float64))
                        headcount = float(
                            np.sum(weight[group & values], dtype=np.float64)
                        )
                        if cases < 10 or 0 < poor_cases < 10 or 0 < nonpoor_cases < 10:
                            record["status"] = "suppressed"
                        elif denominator == 0:
                            record["error"] = {
                                "type": "NoPopulation",
                                "message": "No positive weighted population in this group.",
                            }
                        else:
                            record.update(
                                value=headcount
                                if metric["kind"] == "count"
                                else headcount / denominator,
                                status="ok",
                            )
                except Exception as error:
                    record["error"] = safe_error(error)
                    traceback.print_exc(file=sys.stderr)
                output["metrics"].append(record)
            # A whole-year monetary envelope is deliberately conservative:
            # no residual of published heads can reveal a hidden head.
            if any(record["status"] == "suppressed" for record in monetary):
                for record in monetary:
                    if record["status"] == "ok":
                        record.update(
                            value=None,
                            status="suppressed",
                            suppression_reason="complementary protection: a monetary head has fewer than ten cases",
                        )
            reset = getattr(simulation, "_invalidate_all_caches", None)
            if reset is not None:
                # The aggregate-impact tool uses this country API hook to
                # discard calculated arrays while preserving supplied data.
                reset()
                gc.collect()
    except Exception as error:
        output["status"] = "not_computable"
        output["error"] = safe_error(error)
        traceback.print_exc(file=sys.stderr)
    output["seconds"] = round(time.monotonic() - started, 3)
    write_json(args.output, output)
    return 0


def edge_value(cells, cell_id, metric, year):
    cell = cells[cell_id]
    if cell["status"] != "computable":
        return None, f"{cell_id}: not computable"
    for record in cell["metrics"]:
        if record["id"] == metric["id"] and record["year"] == year:
            if record["status"] == "ok":
                return record["value"], None
            return None, f"{cell_id}: {record['status']}"
    return None, f"{cell_id}: metric not available"


def attribution(move, history, mappings):
    component = (
        "model"
        if move["effect"].startswith("model_")
        else "data"
        if move["effect"].startswith("data_")
        else None
    )
    allowed = [component] if component else ["model", "data"]
    reviewed = []
    candidates = []
    for kind in allowed:
        changes = history[kind]["changes"]
        for change in changes:
            variable = move["variable"].lower()
            matching_paths = [
                path
                for path in change["paths"]
                if Path(path).stem.lower() == variable
                or f"/{variable}/" in path.lower()
            ]
            if matching_paths:
                candidates.append(
                    {
                        "component": kind,
                        "commit": change["commit"],
                        "prs": change["prs"],
                        "paths": matching_paths,
                        "basis": "source-path overlap; requires human causal review",
                    }
                )
        for mapping in mappings:
            if mapping["component"] != kind or not fnmatch.fnmatchcase(
                move["metric_id"], mapping["metric"]
            ):
                continue
            if not fnmatch.fnmatchcase(move["effect"], mapping.get("effect", "*")):
                continue
            if mapping.get("years") and move["year"] not in mapping["years"]:
                continue
            selected = [
                c
                for c in changes
                if any(c["commit"].startswith(s) for s in mapping.get("commits", []))
                or set(c["prs"]) & set(mapping.get("prs", []))
            ]
            if not selected:
                raise ValueError(
                    f"Reviewed mapping references no change in the pinned {kind} range: {mapping}"
                )
            if (
                not mapping.get("reason", "").strip()
                or not mapping.get("reviewer", "").strip()
            ):
                raise ValueError("A reviewed mapping needs reason and reviewer")
            reviewed.append(
                {
                    "component": kind,
                    "reason": mapping["reason"],
                    "reviewer": mapping["reviewer"],
                    "changes": selected,
                }
            )
    uncovered = sorted(set(allowed) - {item["component"] for item in reviewed})
    return {
        "status": "unattributed" if uncovered else "attributed",
        "unmapped_components": uncovered,
        "reviewed_mappings": reviewed,
        "candidate_causes": candidates,
    }


def build_report(cells, definitions, history, mappings, fixture=False):
    moves, missing = [], []
    for metric in metrics(definitions):
        for year in YEARS:
            for effect, (start, end) in EDGES.items():
                before, error_before = edge_value(cells, start, metric, year)
                after, error_after = edge_value(cells, end, metric, year)
                move = {
                    "metric_id": metric["id"],
                    "variable": metric["variable"],
                    "kind": metric["kind"],
                    "year": year,
                    "effect": effect,
                    "base_cell": start,
                    "head_cell": end,
                    "base": before,
                    "head": after,
                    "delta": None,
                    "threshold": None,
                    "flagged": False,
                    "status": "not_computable",
                    "reasons": [e for e in (error_before, error_after) if e],
                }
                if not move["reasons"]:
                    threshold = definitions["flags"][metric["kind"]]
                    bound = max(
                        threshold["absolute"],
                        threshold.get("relative", 0) * abs(before),
                    )
                    move.update(
                        delta=after - before,
                        threshold=bound,
                        flagged=abs(after - before) > bound,
                        status="computable",
                    )
                    if move["flagged"]:
                        move["attribution"] = attribution(move, history, mappings)
                else:
                    missing.append(
                        {
                            "metric_id": metric["id"],
                            "year": year,
                            "effect": effect,
                            "reasons": move["reasons"],
                        }
                    )
                moves.append(move)
    interactions = []
    for metric in metrics(definitions):
        for year in YEARS:
            relevant = {
                m["effect"]: m
                for m in moves
                if m["metric_id"] == metric["id"] and m["year"] == year
            }
            before, after = (
                relevant["model_on_old_data"]["delta"],
                relevant["model_on_new_data"]["delta"],
            )
            interactions.append(
                {
                    "metric_id": metric["id"],
                    "year": year,
                    "value": after - before
                    if before is not None and after is not None
                    else None,
                    "definition": "model_on_new_data - model_on_old_data = data_on_new_model - data_on_old_model",
                }
            )
    flags = [move for move in moves if move["flagged"]]
    return {
        "schema_version": 1,
        "purpose": "same-line UK national 2x2 attribution",
        "synthetic_fixture": fixture,
        "years": list(YEARS),
        "models": VERSIONS,
        "cuts": CUTS,
        "definitions": definitions,
        "history": history,
        "cells": cells,
        "effects": moves,
        "interactions": interactions,
        "unavailable_effects": missing,
        "unattributed": [
            m for m in flags if m["attribution"]["status"] == "unattributed"
        ],
        "limitations": LIMITATIONS,
        "scorecard_replay": {
            "status": "unavailable",
            "reason": "Awaiting Microcosm replay fix; rerun separately when it lands.",
        },
        "summary": {
            "cells_computable": sum(
                c["status"] == "computable" for c in cells.values()
            ),
            "flagged_moves": len(flags),
            "unattributed_moves": sum(
                m["attribution"]["status"] == "unattributed" for m in flags
            ),
        },
    }


def validate(report):
    schema = read_json(ROOT / "attribution.schema.json")
    validate_schema(report, schema, schema)
    if report["schema_version"] != 1 or report["years"] != list(YEARS):
        raise ValueError("Unexpected report schema or fiscal-year horizon")
    if set(report["cells"]) != set(CELL_IDS):
        raise ValueError("Report must retain all four cells, including errors")
    for cell_id, cell in report["cells"].items():
        if cell["id"] != cell_id or cell["status"] not in (
            "computable",
            "not_computable",
        ):
            raise ValueError(f"Malformed cell: {cell_id}")
        if cell["status"] == "not_computable" and not cell.get("error"):
            raise ValueError(f"Uncomputable cell must preserve its error: {cell_id}")
        expected_metrics = {
            (metric["id"], year)
            for metric in metrics(report["definitions"])
            for year in YEARS
        }
        actual_metrics = [(item["id"], item["year"]) for item in cell["metrics"]]
        if cell["status"] == "computable" and (
            len(actual_metrics) != len(set(actual_metrics))
            or set(actual_metrics) != expected_metrics
        ):
            raise ValueError(
                f"Computable cell must retain every metric/year exactly once: {cell_id}"
            )
        for item in cell["metrics"]:
            if item["status"] == "ok" and (
                not isinstance(item["value"], (int, float))
                or not math.isfinite(item["value"])
            ):
                raise ValueError("OK metric must have a finite value")
            if item["status"] != "ok" and item["value"] is not None:
                raise ValueError("Unavailable metric must have a null value")
    for move in report["effects"]:
        if move["effect"] not in EDGES or move["year"] not in YEARS:
            raise ValueError("Unknown effect or fiscal year")
        if move["status"] == "computable" and not math.isfinite(move["delta"]):
            raise ValueError("Computable edge must have a finite delta")
        if move["status"] != "computable" and move["delta"] is not None:
            raise ValueError("Unavailable edge must have a null delta")
        if move["flagged"] and move.get("attribution", {}).get("status") not in (
            "attributed",
            "unattributed",
        ):
            raise ValueError("Every flagged edge needs an attribution verdict")
    expected = [
        m
        for m in report["effects"]
        if m["flagged"] and m["attribution"]["status"] == "unattributed"
    ]
    if report["unattributed"] != expected:
        raise ValueError("Unattributed index does not cover every unmapped flag")
    if report["scorecard_replay"]["status"] != "unavailable":
        raise ValueError("Replay remains unavailable under this exception")
    # JSON serialization rejects NaN/Infinity anywhere, including raw cells.
    json.dumps(report, allow_nan=False)


def validate_schema(value, schema, root, path="$"):
    """Validate the schema features used by this receipt without dependencies.

    The accompanying schema is also consumable by a full Draft 2020-12
    validator. This intentionally small validator is for this fixed schema.
    """
    if "$ref" in schema:
        target = root
        for part in schema["$ref"].removeprefix("#/").split("/"):
            target = target[part]
        return validate_schema(value, target, root, path)
    if "const" in schema and value != schema["const"]:
        raise ValueError(f"{path}: value differs from schema constant")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError(f"{path}: value outside schema enumeration")
    kinds = schema.get("type", [])
    kinds = [kinds] if isinstance(kinds, str) else kinds
    matches = {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "boolean": isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "null": value is None,
    }
    if kinds and not any(matches[kind] for kind in kinds):
        raise ValueError(f"{path}: incorrect schema type")
    if isinstance(value, dict):
        if any(key not in value for key in schema.get("required", [])):
            raise ValueError(f"{path}: missing required schema property")
        if len(value) < schema.get("minProperties", 0) or len(value) > schema.get(
            "maxProperties", math.inf
        ):
            raise ValueError(f"{path}: wrong number of schema properties")
        properties = schema.get("properties", {})
        for key, child in value.items():
            selected = properties.get(key, schema.get("additionalProperties", True))
            if selected is False:
                raise ValueError(f"{path}.{key}: unexpected property")
            if isinstance(selected, dict):
                validate_schema(child, selected, root, f"{path}.{key}")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            raise ValueError(f"{path}: too few schema items")
        for index, child in enumerate(value):
            validate_schema(child, schema.get("items", {}), root, f"{path}[{index}]")


def run(args):
    definitions = read_json(args.definitions)
    check_definitions(definitions, args.model_repo)
    history = histories(
        args.model_repo, args.microcosm_repo, args.old_build, args.new_build
    )
    mappings = read_json(args.mapping)["mappings"] if args.mapping else []
    binding = (
        candidate_binding(args.candidate, args.new_sha256) if args.candidate else None
    )
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if any(
        (parent / ".git").exists() for parent in (output.parent, *output.parent.parents)
    ):
        raise ValueError("Attribution evidence and restricted logs must be outside Git")
    cells = {}
    for data in VERSIONS:
        data_path = getattr(args, f"{data}_data").resolve()
        expected = getattr(args, f"{data}_sha256")
        if digest(data_path) != expected:
            raise ValueError(
                f"{data} national file SHA-256 differs from the pinned manifest"
            )
        for model in VERSIONS:
            subprocess.run(
                [
                    sys.executable,
                    str(args.reservation_script.resolve()),
                    "allowed",
                    "uk-hub",
                ],
                check=True,
            )
            load = os.getloadavg()[0]
            free = shutil.disk_usage(output.parent).free
            if load > 110 or free < 55_000_000_000:
                raise RuntimeError(
                    f"Cell resource guard refused: load1={load:.2f}, free_bytes={free}"
                )
            cell_id = f"{data}_data__{model}_model"
            cell_output = output.parent / f"attribution-{cell_id}.json"
            log_path = output.parent / f"attribution-{cell_id}.stderr.log"
            # Preserve the virtualenv interpreter symlink: resolving it to
            # the base Python would discard that environment's model pin.
            interpreter = getattr(args, f"{model}_python").expanduser().absolute()
            command = [
                str(interpreter),
                str(Path(__file__).resolve()),
                "cell",
                "--cell-id",
                cell_id,
                "--data",
                str(data_path),
                "--sha256",
                expected,
                "--cut",
                CUTS[data],
                "--expected-version",
                VERSIONS[model],
                "--definitions",
                str(args.definitions.resolve()),
                "--output",
                str(cell_output),
            ]
            env = os.environ.copy()
            env.pop("PYTHONPATH", None)
            env["PYTHONNOUSERSITE"] = "1"
            # These logs can contain model error input values: evidence stays
            # outside Git, mode 0600, and only redacted errors enter report.
            fd = os.open(log_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w") as log:
                process = subprocess.run(
                    command, stdout=log, stderr=log, env=env, cwd=output.parent
                )
            if process.returncode or not cell_output.exists():
                cells[cell_id] = {
                    "id": cell_id,
                    "status": "not_computable",
                    "model_version": VERSIONS[model],
                    "data_cut": CUTS[data],
                    "data_sha256": expected,
                    "metrics": [],
                    "error": {
                        "type": "WorkerExit",
                        "message": f"Worker exited {process.returncode}; restricted log: {log_path.name}",
                    },
                }
            else:
                cells[cell_id] = read_json(cell_output)
            cells[cell_id]["restricted_error_log"] = log_path.name
            print(f"{cell_id}: {cells[cell_id]['status']}", flush=True)
    report = build_report(cells, definitions, history, mappings)
    if args.candidate:
        if candidate_binding(args.candidate, args.new_sha256) != binding:
            raise ValueError(
                "Candidate commit or bundled manifest changed during attribution"
            )
        report["binding"] = binding
    validate(report)
    write_json(output, report)
    print(json.dumps(report["summary"], sort_keys=True))
    # Missing cross cells and unattributed moves are expected review states,
    # not invented passes. Failed diagonal cells block the evidence package.
    diagonals = [cells[c] for c in ("old_data__old_model", "new_data__new_model")]
    return (
        0
        if all(
            cell["status"] == "computable"
            and not any(
                item["status"] == "not_computable"
                and item.get("required_for_diagonal", True)
                for item in cell["metrics"]
            )
            for cell in diagonals
        )
        else 1
    )


def fixture_check(args):
    fixture = read_json(ROOT / "attribution-fixture.json")
    definitions = fixture["definitions"]
    cells = {}
    for cell_id, item in fixture["cells"].items():
        records = []
        for year in YEARS:
            for metric in metrics(definitions):
                amount = sum(
                    v * w
                    for v, w in zip(
                        item["values"][metric["variable"]],
                        fixture["weights"],
                        strict=True,
                    )
                )
                if metric["kind"] == "rate":
                    amount /= sum(fixture["weights"])
                records.append(
                    dict(metric, year=year, value=amount, status="ok", error=None)
                )
        cells[cell_id] = {
            "id": cell_id,
            "status": "computable",
            "model_version": VERSIONS[cell_id.split("__")[1].split("_")[0]],
            "metrics": records,
            "error": None,
        }
    history = {"model": {"changes": []}, "data": {"changes": []}}
    report = build_report(cells, definitions, history, [], fixture=True)
    validate(report)

    def find(effect):
        return next(
            m
            for m in report["effects"]
            if m["metric_id"] == "gov_balance"
            and m["year"] == 2026
            and m["effect"] == effect
        )

    for effect, expected in fixture["expected_gov_balance_deltas"].items():
        if find(effect)["delta"] != expected:
            raise ValueError(f"Synthetic {effect} has wrong weighted delta")
    if not report["unattributed"]:
        raise ValueError("Synthetic flags must remain visibly unattributed")
    if (
        next(
            i["value"]
            for i in report["interactions"]
            if i["metric_id"] == "gov_balance"
        )
        != fixture["expected_interaction"]
    ):
        raise ValueError("Synthetic 2x2 interaction is wrong")
    write_json(args.output, report)
    cells["new_data__old_model"] = {
        "id": "new_data__old_model",
        "status": "not_computable",
        "metrics": [],
        "error": {
            "type": "SyntheticSchemaError",
            "message": "Synthetic incompatible cut/model cell",
        },
    }
    partial = build_report(cells, definitions, history, [], fixture=True)
    validate(partial)
    if (
        next(
            m
            for m in partial["effects"]
            if m["metric_id"] == "gov_balance"
            and m["year"] == 2026
            and m["effect"] == "model_on_old_data"
        )["delta"]
        != fixture["expected_gov_balance_deltas"]["model_on_old_data"]
    ):
        raise ValueError("Failed cross cell must preserve independent edges")
    if any(i["value"] is not None for i in partial["interactions"]):
        raise ValueError("Missing cross cell must leave interaction unidentified")
    write_json(args.output.with_name(args.output.stem + "-missing-cell.json"), partial)
    print(
        "Synthetic weighted aggregates, 2x2 edges/interaction, flags, error-cell retention and output schema: passed; no model import or data load."
    )
    return 0


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    sub = result.add_subparsers(dest="command", required=True)
    heavy = sub.add_parser("run", help="HEAVY: serial four-cell national attribution")
    for side in VERSIONS:
        heavy.add_argument(f"--{side}-python", type=Path, required=True)
        heavy.add_argument(f"--{side}-data", type=Path, required=True)
        heavy.add_argument(f"--{side}-sha256", required=True, type=sha256_argument)
    heavy.add_argument("--model-repo", type=Path, required=True)
    heavy.add_argument("--microcosm-repo", type=Path, required=True)
    heavy.add_argument("--reservation-script", type=Path, required=True)
    heavy.add_argument(
        "--candidate",
        type=Path,
        help="Bind evidence to this final certified candidate commit and bundle manifest",
    )
    heavy.add_argument("--old-build", required=True)
    heavy.add_argument("--new-build", default="829c1bc26")
    heavy.add_argument(
        "--definitions", type=Path, default=ROOT / "attribution-definitions.json"
    )
    heavy.add_argument(
        "--mapping", type=Path, default=ROOT / "attribution-mapping.json"
    )
    heavy.add_argument("--output", type=Path, required=True)
    heavy.set_defaults(action=run)
    cell = sub.add_parser("cell", help=argparse.SUPPRESS)
    cell.add_argument("--cell-id", choices=CELL_IDS, required=True)
    cell.add_argument("--data", type=Path, required=True)
    cell.add_argument("--sha256", type=sha256_argument, required=True)
    cell.add_argument("--cut", choices=list(CUTS.values()), required=True)
    cell.add_argument(
        "--expected-version", choices=list(VERSIONS.values()), required=True
    )
    cell.add_argument("--definitions", type=Path, required=True)
    cell.add_argument("--output", type=Path, required=True)
    cell.set_defaults(action=worker)
    check = sub.add_parser(
        "fixture-check", help="LIGHT: validate tiny synthetic fixture only"
    )
    check.add_argument("--output", type=Path, required=True)
    check.set_defaults(action=fixture_check)
    verify = sub.add_parser("validate", help="LIGHT: validate an existing JSON report")
    verify.add_argument("report", type=Path)
    verify.set_defaults(action=lambda args: validate(read_json(args.report)) or 0)
    return result


def sha256_argument(text):
    if not re.fullmatch(r"[0-9a-f]{64}", text):
        raise argparse.ArgumentTypeError("Expected lowercase 64-character SHA-256")
    return text


if __name__ == "__main__":
    arguments = parser().parse_args()
    sys.exit(arguments.action(arguments))
