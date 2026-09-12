"""Nonpublishing candidates and the identical, fail-closed release preparation.

Candidate evidence lives in immutable Actions artifacts, never in the tree it
authenticates. The human/peer merge gate approves numerical qualification; this
helper authenticates CI source/artifact identity and checks release bytes only.
"""

from __future__ import annotations

import argparse
import base64
import csv
import datetime as dt
import hashlib
import importlib.util
import io
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import urllib.error
import urllib.request
import zipfile
from email.parser import BytesParser
from importlib import metadata
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "PolicyEngine/policyengine.py"
WORKFLOW = ".github/workflows/pr_code_changes.yaml"
COUNTRY_REPOSITORY = "PolicyEngine/policyengine-us"
COUNTRY_WORKFLOW = ".github/workflows/pr.yaml"
BUNDLE_PATH = Path("src/policyengine/data/bundle/manifest.json")
ARTIFACT_PREFIX = "wrapper-release-candidate-"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def run(root: Path, *command: str, env: dict | None = None) -> None:
    subprocess.run(command, cwd=root, env=env, check=True)


def git(root: Path, *args: str, env: dict | None = None) -> str:
    return subprocess.check_output(["git", *args], cwd=root, env=env, text=True).strip()


def load_helper(root: Path, relative: str):
    spec = importlib.util.spec_from_file_location(
        "_release_" + Path(relative).stem, root / relative
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def predicted_version(root: Path) -> str:
    helper = load_helper(root, ".github/bump_version.py")
    try:
        return helper.bump_version(
            helper.get_current_version(
                root / "pyproject.toml", root / "CHANGELOG.md", root
            ),
            helper.infer_bump(root / "changelog.d"),
        )
    except SystemExit:
        raise ValueError(
            "Release build hold: stable version prediction failed"
        ) from None


def require_unpublished(version: str) -> None:
    """Only an authoritative 404 establishes absence, including deleted files."""
    url = f"https://pypi.org/pypi/policyengine/{version}/json"
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return
        raise ValueError("Could not verify wrapper registry state") from None
    raise ValueError(f"Wrapper version {version} is already published")


def reject_untracked_build_inputs(root: Path) -> None:
    """Package/generator inputs must belong to the authenticated tracked tree."""
    paths = git(
        root,
        "ls-files",
        "--others",
        "-z",
        "--",
        "src",
        "scripts",
        ".github",
        "changelog.d",
        "pyproject.toml",
        "uv.lock",
        "Makefile",
        "CHANGELOG.md",
        "README.md",
        "MANIFEST.in",
        "setup.py",
        "setup.cfg",
        "LICENSE",
    ).split("\0")
    unexpected = [
        name
        for name in paths
        if name
        and "__pycache__" not in Path(name).parts
        and Path(name).suffix not in {".pyc", ".pyo"}
        # Generated editable/backend metadata is not a discovered package.
        and Path(name).parts[:2] != ("src", "policyengine.egg-info")
    ]
    if unexpected:
        raise ValueError("Untracked package/build inputs: " + ", ".join(unexpected))


def prepared_tree(root: Path) -> str:
    """Snapshot tracked generator outputs, preserving the checkout's index."""
    reject_untracked_build_inputs(root)
    with tempfile.TemporaryDirectory() as temporary:
        env = {**os.environ, "GIT_INDEX_FILE": str(Path(temporary) / "index")}
        git(root, "read-tree", "HEAD", env=env)
        git(root, "add", "--update", ".", env=env)
        return git(root, "write-tree", env=env)


def preparation_inputs(root: Path, head: str) -> dict:
    epoch = int(git(root, "show", "-s", "--format=%ct", head))
    return {
        "epoch": epoch,
        "release_date": dt.datetime.fromtimestamp(epoch, dt.UTC).date().isoformat(),
        "tags": git(
            root,
            "for-each-ref",
            "--sort=refname",
            "--format=%(refname) %(objectname)",
            "refs/tags",
        ).splitlines(),
    }


def controlled_environment(inputs: dict) -> dict[str, str]:
    # Prevent inherited installer indexes, user-site packages and locale/time
    # defaults from changing either side of the release comparison.
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("PIP_", "UV_")) and key != "PYTHONPATH"
    }
    env.update(
        {
            "PYTHONNOUSERSITE": "1",
            "POLICYENGINE_SKIP_COUNTRY_IMPORTS": "1",
            "SOURCE_DATE_EPOCH": str(inputs["epoch"]),
            "RELEASE_DATE": inputs["release_date"],
            "TZ": "UTC",
            "LC_ALL": "C.UTF-8",
            "UV_NO_CONFIG": "1",
            "UV_DEFAULT_INDEX": "https://pypi.org/simple",
        }
    )
    expected = (
        dt.datetime.fromtimestamp(int(env["SOURCE_DATE_EPOCH"]), dt.UTC)
        .date()
        .isoformat()
    )
    if env["RELEASE_DATE"] != expected:
        raise ValueError("Frozen release date differs from SOURCE_DATE_EPOCH")
    return env


def normalize_requirement_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def validate_tool_requirements(root: Path, config: dict) -> None:
    """The installable hash closure and its registry evidence must agree exactly."""

    expected = {}
    for name, item in config["tools"].items():
        key = normalize_requirement_name(name)
        hashes = {wheel["sha256"] for wheel in item["wheels"]}
        if (
            key in expected
            or not hashes
            or any(
                re.fullmatch(r"[0-9a-f]{64}", digest) is None
                for digest in hashes | {item["registry_json_sha256"]}
            )
        ):
            raise ValueError("Invalid or duplicate frozen tool evidence")
        expected[key] = (item["version"], hashes)
    actual = {}
    for line in (root / ".github/release-tools.txt").read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.fullmatch(
            r"([A-Za-z0-9][A-Za-z0-9._-]*)==([^\s]+)((?: --hash=sha256:[0-9a-f]{64})+)",
            line,
        )
        if match is None or normalize_requirement_name(match[1]) in actual:
            raise ValueError("Invalid or duplicate frozen tool requirement")
        actual[normalize_requirement_name(match[1])] = (
            match[2],
            set(re.findall(r"--hash=sha256:([0-9a-f]{64})", match[3])),
        )
    if actual != expected:
        raise ValueError("Frozen tool requirements differ from registry evidence")


def filter_tool_overlaps(exported: str, config: dict) -> tuple[str, list[dict]]:
    """Keep base bytes except exact frozen-tool pins, including all their hashes."""
    tools = {
        normalize_requirement_name(name): item["version"]
        for name, item in config["tools"].items()
    }
    retained, overlaps, block = [], [], ""
    for line in exported.splitlines(keepends=True):
        block += line
        if line.rstrip().endswith("\\"):
            continue
        name = re.match(r"([A-Za-z0-9][A-Za-z0-9._-]*)", block)
        key = normalize_requirement_name(name[1]) if name else None
        if key in tools:
            pin = re.match(r"[A-Za-z0-9][A-Za-z0-9._-]*==([^;\s\\]+)", block)
            if pin is None or pin[1] != tools[key]:
                raise ValueError("Exported base tool pin differs from the frozen tool")
            overlaps.append({"name": key, "version": pin[1]})
        else:
            retained.append(block)
        block = ""
    if block:
        raise ValueError("Exported base requirement has an unfinished continuation")
    return "".join(retained), sorted(overlaps, key=lambda item: item["name"])


def export_base_requirements(root: Path, output: Path, config: dict) -> dict:
    """Derive overlap evidence from the actual lock, without operator receipt input."""
    run(
        root,
        "uv",
        "export",
        "--frozen",
        "--no-dev",
        "--no-emit-project",
        "--no-header",
        "--no-annotate",
        "--quiet",
        "--format",
        "requirements-txt",
        "--output-file",
        str(output),
        env=controlled_environment({"epoch": 0, "release_date": "1970-01-01"}),
    )
    exported = output.read_text()
    filtered, overlaps = filter_tool_overlaps(exported, config)
    output.write_text(filtered)
    return {
        "exported_base_sha256": sha256(exported.encode()),
        "filtered_base_sha256": sha256(filtered.encode()),
        "removed_tool_overlaps": overlaps,
        "governing_tool_file": ".github/release-tools.txt",
        "governing_tool_file_sha256": sha256(
            (root / ".github/release-tools.txt").read_bytes()
        ),
    }


def check_toolchain(root: Path) -> dict:
    config_path = root / ".github/release-toolchain.json"
    config = json.loads(config_path.read_text())
    validate_tool_requirements(root, config)
    actions = re.findall(
        r"^\s*- uses: (\S+)",
        (root / ".github/actions/release-toolchain/action.yml").read_text(),
        flags=re.MULTILINE,
    )
    if set(actions) != {
        name + "@" + item["commit"] for name, item in config["setup_actions"].items()
    }:
        raise ValueError("Release setup actions differ from the frozen commits")
    actual = {
        "os": platform.system(),
        "arch": os.environ.get("RUNNER_ARCH"),
        "image_os": os.environ.get("ImageOS"),
        "image_version": os.environ.get("ImageVersion"),
    }
    if actual != config["runner"] or platform.python_version() != config["python"]:
        raise ValueError(
            "Release runner image or Python differs from the frozen toolchain"
        )
    uv = Path(shutil.which("uv") or "/missing-uv").resolve(strict=True)
    uv_version = subprocess.check_output([str(uv), "--version"], text=True).split()[1]
    if uv_version != config["uv"]:
        raise ValueError("Release uv differs from the frozen toolchain")
    installed = {}
    for name, item in config["tools"].items():
        installed[name] = metadata.version(name)
        if installed[name] != item["version"]:
            raise ValueError(f"Release tool {name} differs from the frozen toolchain")
    project = tomllib.loads((root / "pyproject.toml").read_text())
    if project["build-system"]["requires"] != config["build_backend_requires"]:
        raise ValueError("Build-system requirements differ from the frozen toolchain")
    with tempfile.TemporaryDirectory() as temporary:
        base_requirements = export_base_requirements(
            root, Path(temporary) / "base.txt", config
        )
    return {
        "config_sha256": sha256(config_path.read_bytes()),
        "requirements_sha256": sha256(
            (root / ".github/release-tools.txt").read_bytes()
        ),
        "runner": actual,
        "python": platform.python_version(),
        "python_binary_sha256": sha256(Path(sys.executable).resolve().read_bytes()),
        "uv": uv_version,
        "uv_binary_sha256": sha256(uv.read_bytes()),
        "tools": installed,
        "base_requirements": base_requirements,
    }


def bootstrap(root: Path, destination: Path) -> None:
    """Hash-locked build scaffold; never install model extras or mutate uv.lock."""
    destination = destination.resolve()
    config = json.loads((root / ".github/release-toolchain.json").read_text())
    validate_tool_requirements(root, config)
    if destination.exists():
        raise ValueError("Build environment destination must be new")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        requirements = Path(temporary) / "base.txt"
        env = controlled_environment({"epoch": 0, "release_date": "1970-01-01"})
        export_base_requirements(root, requirements, config)
        run(root, "uv", "venv", "--python", sys.executable, str(destination), env=env)
        python = destination / "bin/python"
        run(
            root,
            "uv",
            "pip",
            "sync",
            "--python",
            str(python),
            "--require-hashes",
            "--only-binary",
            ":all:",
            str(requirements),
            str(root / ".github/release-tools.txt"),
            env=env,
        )
        run(
            root,
            "uv",
            "pip",
            "install",
            "--python",
            str(python),
            "--no-deps",
            "--no-build-isolation",
            "--editable",
            str(root),
            env=env,
        )
        run(
            root,
            str(python),
            str(root / "scripts/release_build.py"),
            "check-toolchain",
            env=env,
        )
    with Path(os.environ["GITHUB_PATH"]).open("a") as stream:
        stream.write(str(destination / "bin") + "\n")


def prepare_prerelease_metadata(
    root: Path, version: str, country: dict | None = None
) -> None:
    if re.fullmatch(r"\d+\.\d+\.\d+rc1", version) is None:
        raise ValueError(
            "Numerical wrapper candidate must have the predicted rc1 version"
        )
    helper = load_helper(root, ".github/bump_version.py")
    helper.update_file(root / "pyproject.toml", version)
    helper.sync_bundle_versions(root / BUNDLE_PATH, version)
    bundle = json.loads((root / BUNDLE_PATH).read_text())
    us = bundle["data_releases"]["us"]
    us.pop("certification", None)
    us.pop("certified_data_artifact", None)
    if country is not None:
        descriptor = bundle["packages"]["policyengine-us"]
        descriptor["name"] = country["name"]
        descriptor["version"] = country["version"]
        descriptor.pop("sha256", None)
        descriptor.pop("wheel_url", None)
        us["model_package"] = {"name": country["name"], "version": country["version"]}
    bundle["development"] = {
        "purpose": "unpublished numerical wrapper candidate",
        "data_certification": "not_certified",
        "promotion_status": "pending",
        "data_release_metadata": "inherited reference only; no compatibility claim",
    }
    write_json(root / BUNDLE_PATH, bundle)


def candidate_us_tro(root: Path, version: str) -> dict:
    """Build a limited US TRACE using the existing graph assembly helpers."""
    sys.path[:0] = [str(root / "scripts"), str(root / "src")]
    from policyengine.provenance.trace import (
        POLICYENGINE_ORGANIZATION,
        TRACE_CONTEXT,
        _assemble_composition_and_arrangement,
        _assemble_tro_node,
    )

    manifest = root / BUNDLE_PATH
    composition, arrangement = _assemble_composition_and_arrangement(
        [
            {
                "id": "bundle_manifest",
                "hash": sha256(manifest.read_bytes()),
                "location": "data/bundle/manifest.json",
                "mime_type": "application/json",
                "name": "Unpublished candidate manifest; not reviewed for release",
            }
        ]
    )
    node = _assemble_tro_node(
        tro_name="PolicyEngine US candidate manifest (unpublished; not reviewed for release)",
        tro_description="Record of unpublished candidate bundle-manifest bytes only; not reviewed for release.",
        created_at=None,
        creator=POLICYENGINE_ORGANIZATION,
        software_version=version,
        trs_comment="Records unpublished candidate bundle-manifest bytes only; not reviewed for release.",
        composition=composition,
        arrangement=arrangement,
        performance={
            "@id": "trp/1",
            "@type": "trov:TransparentResearchPerformance",
            "trov:wasConductedBy": {"@id": "trs"},
            "trov:accessedArrangement": {"@id": "arrangement/1"},
            "pe:emittedIn": "repository-bundle",
            "rdfs:comment": "Manifest-only byte record for an unpublished candidate; not reviewed for release.",
        },
    )
    return {"@context": TRACE_CONTEXT, "@graph": [node]}


def candidate_uk_tro() -> dict:
    """Use the ordinary UK builder only; never fetch the inherited US release."""
    from policyengine.provenance.manifest import (
        DataReleaseManifestUnavailableError,
        get_data_release_manifest,
        get_release_manifest,
    )
    from policyengine.provenance.trace import build_trace_tro_from_release_bundle

    country = get_release_manifest("uk")
    try:
        data = get_data_release_manifest("uk")
    except DataReleaseManifestUnavailableError:
        raise ValueError(
            "Release build hold: UK release manifest unavailable"
        ) from None
    return build_trace_tro_from_release_bundle(
        country,
        data,
        certification=country.certification,
        model_wheel_sha256=country.model_package.sha256,
        model_wheel_url=country.model_package.wheel_url,
        emission_context={"pe:emittedIn": "repository-bundle"},
    )


def assert_source_origin(root: Path) -> dict:
    """Reject cached modules or package resources from any other checkout."""
    from importlib.resources import files

    import policyengine
    import policyengine.provenance.manifest
    import policyengine.provenance.trace

    expected = (root / "src/policyengine").resolve()
    resources = Path(str(files("policyengine"))).resolve()
    origins = {}
    for name, module in tuple(sys.modules.items()):
        if name == "policyengine" or name.startswith("policyengine."):
            filename = getattr(module, "__file__", None)
            if filename is None or not Path(filename).resolve().is_relative_to(
                expected
            ):
                raise ValueError("Prepared package import has the wrong source origin")
            origins[name] = str(Path(filename).resolve().relative_to(root.resolve()))
    if (
        resources != expected
        or Path(policyengine.__file__).resolve().parent != expected
    ):
        raise ValueError("Prepared package resources have the wrong source origin")
    return {"resources": "src/policyengine", "modules": origins}


def source_command(root: Path, *args: str, env: dict | None = None) -> dict:
    """Each source/resource verification starts in a new interpreter."""
    source_env = {
        **(os.environ if env is None else env),
        "PYTHONPATH": str(root / "src"),
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "POLICYENGINE_SKIP_COUNTRY_IMPORTS": "1",
    }
    return json.loads(
        subprocess.check_output(
            [sys.executable, str(root / "scripts/release_build.py"), *args],
            cwd=root,
            env=source_env,
            text=True,
        )
    )


def validate_tro_schema(root: Path, payload: dict, country: str) -> None:
    from jsonschema import Draft202012Validator
    from jsonschema.exceptions import ValidationError

    validator = Draft202012Validator(
        json.loads(
            (root / "src/policyengine/data/schemas/trace_tro.schema.json").read_text()
        )
    )
    try:
        validator.validate(payload)
    except ValidationError:
        raise ValueError(
            f"Release build hold: {country.upper()} TRACE fails schema validation"
        ) from None


def generate_candidate_tros(root: Path, version: str) -> None:
    """Limited US TRACE via existing assembly/schema; ordinary UK generation."""
    assert_source_origin(root)
    from policyengine.provenance.trace import serialize_trace_tro

    us, uk = candidate_us_tro(root, version), candidate_uk_tro()
    for name, payload in (
        ("us", us),
        ("uk", uk),
    ):
        validate_tro_schema(root, payload, name)
        (root / BUNDLE_PATH.parent / f"{name}.trace.tro.jsonld").write_bytes(
            serialize_trace_tro(payload)
        )


def validate_candidate_descriptors(bundle: dict) -> None:
    """Check the final generator output, not just the metadata preparation input."""
    descriptor = bundle["packages"]["policyengine-us"]
    version = descriptor["version"]
    if descriptor != {
        "name": "policyengine-us",
        "version": version,
        "country": "us",
        "import_name": "policyengine_us",
        "install_requirement": f"policyengine-us=={version}",
        "role": "country_model",
    } or bundle["data_releases"]["us"]["model_package"] != {
        "name": "policyengine-us",
        "version": version,
    }:
        raise ValueError(
            "Candidate country descriptors differ from ordinary packaged shapes"
        )


def reject_local_file_uri(payload: dict) -> None:
    if "file:" in canonical(payload).lower():
        raise ValueError("Candidate manifest or TRO contains a local file URI")


def verify_identity(root: Path, version: str, flavor: str) -> dict:
    assert_source_origin(root)
    bundle = json.loads((root / BUNDLE_PATH).read_text())
    if flavor == "rc1":
        validate_candidate_descriptors(bundle)
        reject_local_file_uri(bundle)
    manifest_hash = sha256((root / BUNDLE_PATH).read_bytes())
    tro_hashes = {}
    values = [
        tomllib.loads((root / "pyproject.toml").read_text())["project"]["version"],
        bundle["bundle_version"],
        bundle["policyengine_version"],
        bundle["packages"]["policyengine"]["version"],
        bundle["citation"]["version"],
    ]
    for country, item in bundle["data_releases"].items():
        values.append(item["policyengine_version"])
        if item["bundle_id"] != f"{country}-{version}":
            raise ValueError("Candidate bundle_id differs from its actual version")
        payload = json.loads(
            (root / BUNDLE_PATH.parent / f"{country}.trace.tro.jsonld").read_text()
        )
        if flavor == "rc1":
            reject_local_file_uri(payload)
        tro = payload["@graph"][0]
        values.append(tro["trov:createdWith"]["schema:softwareVersion"])
        manifest_pins = [
            artifact.get("trov:sha256")
            for artifact in tro["trov:hasComposition"]["trov:hasArtifact"]
            if artifact.get("@id") == "composition/1/artifact/bundle_manifest"
        ]
        if manifest_pins != [manifest_hash]:
            raise ValueError(f"Packaged {country.upper()} TRO manifest hash differs")
        tro_hashes[country] = sha256(
            (root / BUNDLE_PATH.parent / f"{country}.trace.tro.jsonld").read_bytes()
        )
    if any(value != version for value in values):
        raise ValueError("Package, manifest, citation or TRO version differs")
    if flavor == "rc1":
        from policyengine.provenance.trace import serialize_trace_tro

        us = bundle["data_releases"]["us"]
        tro = json.loads(
            (root / BUNDLE_PATH.parent / "us.trace.tro.jsonld").read_text()
        )["@graph"][0]
        artifacts = tro["trov:hasComposition"]["trov:hasArtifact"]
        if (
            "certification" in us
            or "certified_data_artifact" in us
            or bundle.get("development", {}).get("data_certification")
            != "not_certified"
            or len(artifacts) != 1
            or artifacts[0]["@id"] != "composition/1/artifact/bundle_manifest"
            or artifacts[0]["trov:sha256"] != sha256((root / BUNDLE_PATH).read_bytes())
            or any(
                key.startswith("pe:") and key != "pe:emittedIn"
                for key in tro["trov:hasPerformance"]
            )
            or tro["trov:hasPerformance"].get("pe:emittedIn") != "repository-bundle"
        ):
            raise ValueError("Candidate contains an inherited or false certification")
        if (
            root / BUNDLE_PATH.parent / "us.trace.tro.jsonld"
        ).read_bytes() != serialize_trace_tro(candidate_us_tro(root, version)):
            raise ValueError(
                "Packaged US candidate TRO differs from the exact limited record"
            )
        uk = candidate_uk_tro()
        validate_tro_schema(root, uk, "uk")
        if (
            root / BUNDLE_PATH.parent / "uk.trace.tro.jsonld"
        ).read_bytes() != serialize_trace_tro(uk):
            raise ValueError("Packaged UK TRO differs from ordinary UK reconstruction")
    elif "development" in bundle:
        raise ValueError("Stable release cannot contain development metadata")
    return {
        "bundle_manifest_sha256": manifest_hash,
        "tro_sha256": tro_hashes,
        "source_origin": assert_source_origin(root),
    }


def verify_identity_fresh(root: Path, version: str, flavor: str, env: dict) -> dict:
    return source_command(
        root, "verify-identity", "--version", version, "--flavor", flavor, env=env
    )


def prepare(root: Path, flavor: str, source: dict, country: dict | None = None) -> dict:
    inputs = preparation_inputs(root, source["head"])
    env = controlled_environment(inputs)
    toolchain = check_toolchain(root)
    version = predicted_version(root) + ("rc1" if flavor == "rc1" else "")
    require_unpublished(version)
    python = sys.executable
    if flavor == "release":
        run(root, python, "scripts/check_release_credentials.py", env=env)
        run(
            root,
            python,
            "scripts/bundle.py",
            "check",
            "--published-spm",
            "--include-tros",
            "--strict-tros",
            env=env,
        )
        run(root, python, "scripts/release_lock.py", env=env)
        run(
            root, "make", "changelog", f"RELEASE_DATE={inputs['release_date']}", env=env
        )
        run(root, python, "scripts/bundle.py", "generate", env=env)
        run(root, python, "scripts/release_lock.py", "--refresh", env=env)
        run(
            root,
            python,
            "scripts/bundle.py",
            "generate",
            "--include-tros",
            "--strict-tros",
            env=env,
        )
        run(
            root,
            python,
            "scripts/bundle.py",
            "check",
            "--published-spm",
            "--include-tros",
            "--strict-tros",
            env=env,
        )
    else:
        if country is None:
            raise ValueError("Unpublished final-country candidate artifact is required")
        prepare_prerelease_metadata(root, version, country)
        run(root, python, "scripts/bundle.py", "generate", env=env)
        run(
            root,
            python,
            "scripts/release_build.py",
            "candidate-tros",
            "--version",
            version,
            env=env,
        )
    identity = verify_identity_fresh(root, version, flavor, env)
    tree = prepared_tree(root)
    commit_env = {
        **env,
        "GIT_AUTHOR_NAME": "PolicyEngine release preparation",
        "GIT_AUTHOR_EMAIL": "hello@policyengine.org",
        "GIT_COMMITTER_NAME": "PolicyEngine release preparation",
        "GIT_COMMITTER_EMAIL": "hello@policyengine.org",
        "GIT_AUTHOR_DATE": f"@{inputs['epoch']} +0000",
        "GIT_COMMITTER_DATE": f"@{inputs['epoch']} +0000",
    }
    prepared_commit = git(
        root,
        "commit-tree",
        tree,
        "-p",
        git(root, "rev-parse", "HEAD"),
        "-m",
        "Nonpublishing release preparation",
        env=commit_env,
    )
    receipt = {
        "schema_version": 1,
        "flavor": flavor,
        "version": version,
        "source": source,
        "preparation_inputs": inputs,
        "toolchain": toolchain,
        "prepared_tree": tree,
        "prepared_local_commit": prepared_commit,
    }
    receipt["package_identity"] = identity
    return receipt


def wheel_identity(raw: bytes, version: str, package: str = "policyengine") -> dict:
    """Check an immutable byte snapshot, including its complete mechanical RECORD."""
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or any(
            name.startswith("/")
            or ".." in PurePosixPath(name).parts
            or "\\" in name
            or (item.external_attr >> 16) & 0o170000 == 0o120000
            for name, item in zip(names, archive.infolist())
        ):
            raise ValueError("Unsafe or duplicate wheel member")
        members = {name: archive.read(name) for name in names if not name.endswith("/")}
    metadata_names = [name for name in members if name.endswith(".dist-info/METADATA")]
    if len(metadata_names) != 1:
        raise ValueError("Wheel must have exactly one METADATA")
    prefix = metadata_names[0].removesuffix("METADATA")
    info = BytesParser().parsebytes(members[metadata_names[0]])
    if info["Name"].lower().replace("_", "-") != package or info["Version"] != version:
        raise ValueError("Wheel package or version differs from the selected candidate")
    if prefix + "WHEEL" not in members or prefix + "RECORD" not in members:
        raise ValueError("Wheel lacks WHEEL or RECORD")
    record = list(csv.reader(io.StringIO(members[prefix + "RECORD"].decode())))
    if (
        any(len(row) != 3 for row in record)
        or len(record) != len(members)
        or {row[0] for row in record} != set(members)
    ):
        raise ValueError("Wheel RECORD membership differs")
    for name, digest, size in record:
        if name == prefix + "RECORD":
            if digest or size:
                raise ValueError("Wheel RECORD self entry must be empty")
        elif digest != "sha256=" + base64.urlsafe_b64encode(
            hashlib.sha256(members[name]).digest()
        ).rstrip(b"=").decode() or size != str(len(members[name])):
            raise ValueError(f"Wheel RECORD differs for {name}")
    return {
        "sha256": sha256(raw),
        "size_bytes": len(raw),
        "name": package,
        "version": version,
        "members": {
            name: {"sha256": sha256(data), "size": len(data)}
            for name, data in sorted(members.items())
        },
    }


def build(root: Path, receipt: dict, output: Path) -> dict:
    reject_untracked_build_inputs(root)
    output.mkdir(parents=True, exist_ok=False)
    env = controlled_environment(receipt["preparation_inputs"])
    run(
        root,
        "uv",
        "pip",
        "install",
        "--python",
        sys.executable,
        "--no-deps",
        "--no-build-isolation",
        "--editable",
        str(root),
        env=env,
    )
    actual_version = subprocess.check_output(
        [sys.executable, ".github/fetch_version.py"], cwd=root, env=env, text=True
    ).strip()
    if actual_version != receipt["version"]:
        raise ValueError("Installed prepared wrapper version differs")
    identity = verify_identity_fresh(root, receipt["version"], receipt["flavor"], env)
    if identity != receipt["package_identity"]:
        raise ValueError("Prebuild package identity differs from prepared evidence")
    if receipt["flavor"] == "release":
        install_model_metadata(root, env)
        run(root, "bash", ".github/capture-version.sh", env=env)
    # No isolated resolver: the frontend/backend closure was hash-installed.
    run(
        root,
        sys.executable,
        "-m",
        "build",
        "--wheel",
        "--no-isolation",
        "--outdir",
        str(output),
        env=env,
    )
    wheels = list(output.glob("*.whl"))
    if len(wheels) != 1:
        raise ValueError("Build must produce exactly one candidate wheel")
    receipt["wheel"] = {
        "filename": wheels[0].name,
        **wheel_identity(wheels[0].read_bytes(), receipt["version"]),
    }
    verify_wheel_package_identity(receipt)
    if prepared_tree(root) != receipt["prepared_tree"]:
        raise ValueError("Package build mutated tracked prepared inputs")
    return receipt


def verify_wheel_package_identity(receipt: dict) -> None:
    expected = {
        "policyengine/data/bundle/manifest.json": receipt["package_identity"][
            "bundle_manifest_sha256"
        ],
        **{
            f"policyengine/data/bundle/{country}.trace.tro.jsonld": digest
            for country, digest in receipt["package_identity"]["tro_sha256"].items()
        },
    }
    for name, digest in expected.items():
        if receipt["wheel"]["members"].get(name, {}).get("sha256") != digest:
            raise ValueError(
                f"Built wheel {name} differs from prepared package identity"
            )


def install_model_metadata(root: Path, env: dict) -> None:
    """Install exact model wheels for the existing packages-only release check.

    This is a build scaffold, not a microsimulation runtime. The complete model
    dependency graph remains authenticated by release_lock and is exercised in
    the separate numerical qualification environment.
    """
    bundle = json.loads((root / BUNDLE_PATH).read_text())
    lock = tomllib.loads((root / "uv.lock").read_text())
    guard = load_helper(root, "scripts/release_lock.py")
    guard.validate_registry_lock(
        tomllib.loads((root / "pyproject.toml").read_text()), lock
    )
    lines = []
    for name in bundle["extras"]["models"]:
        component = bundle["packages"][name]
        matches = [
            item
            for item in lock["package"]
            if item["name"] == component["name"]
            and item["version"] == component["version"]
        ]
        if len(matches) != 1 or not matches[0].get("wheels"):
            raise ValueError(
                "Model metadata must use the exact reviewed registry wheel"
            )
        hashes = sorted({wheel["hash"] for wheel in matches[0]["wheels"]})
        lines.append(
            f"{component['name']}=={component['version']} "
            + " ".join("--hash=" + digest for digest in hashes)
        )
    with tempfile.TemporaryDirectory() as temporary:
        requirements = Path(temporary) / "models.txt"
        requirements.write_text("\n".join(lines) + "\n")
        run(
            root,
            "uv",
            "pip",
            "install",
            "--python",
            sys.executable,
            "--no-deps",
            "--require-hashes",
            "--only-binary",
            ":all:",
            "-r",
            str(requirements),
            env=env,
        )


def github(path: str, *, binary: bool = False):
    """gh authenticates GitHub API/redirects; never accept an operator download URL."""
    result = subprocess.run(
        ["gh", "api", "--method", "GET", path],
        capture_output=True,
    )
    if result.returncode:
        # Classify known diagnostics without forwarding raw stderr, credentials,
        # response bodies or operator query strings into public Actions logs.
        diagnostic = result.stderr.decode(errors="replace").lower()
        status = re.search(r"http (\d{3})", diagnostic)
        category = "request failed"
        if "rate limit" in diagnostic or (status and status[1] == "429"):
            category = "rate limit; retry after the GitHub limit resets"
        elif status and status[1] in {"401", "403"}:
            category = (
                "access denied; check the App installation and Actions read permission"
            )
        elif status and status[1] == "404":
            category = (
                "not found or inaccessible; check artifact ID and repository access"
            )
        elif "gh auth login" in diagnostic:
            category = "authentication unavailable"
        request_path = path.split("?", 1)[0]
        if (
            re.fullmatch(
                r"repos/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+", request_path
            )
            is None
        ):
            request_path = "GitHub API request"
        code = "HTTP " + status[1] if status else f"exit {result.returncode}"
        raise ValueError(
            f"Authenticated GitHub artifact lookup failed ({code}; {category}): {request_path}"
        )
    return result.stdout if binary else json.loads(result.stdout)


def pages(path: str, key: str) -> list:
    rows = []
    for page in range(1, 101):
        data = github(
            path + ("&" if "?" in path else "?") + f"per_page=100&page={page}"
        )
        batch = data[key] if key else data
        rows.extend(batch)
        if len(batch) < 100:
            return rows
    raise ValueError("GitHub pagination exceeded the bounded release lookup")


def authenticated_artifact(
    repository: str, artifact_id: int, workflow: str
) -> tuple[dict, dict, dict[str, bytes]]:
    artifact = github(f"repos/{repository}/actions/artifacts/{artifact_id}")
    run_info = github(
        f"repos/{repository}/actions/runs/{artifact['workflow_run']['id']}"
    )
    if (
        artifact.get("expired")
        or artifact.get("id") != artifact_id
        or run_info.get("status") != "completed"
        or run_info.get("conclusion") != "success"
        or run_info.get("event") != "pull_request"
        or run_info.get("path", "").split("@")[0] != workflow
        or run_info.get("repository", {}).get("full_name") != repository
        or run_info.get("head_repository", {}).get("full_name") != repository
        or artifact["workflow_run"].get("head_sha") != run_info.get("head_sha")
    ):
        raise ValueError(
            "Artifact is not from the required successful repository PR workflow"
        )
    # Conservatively require the artifact to belong to the current successful
    # attempt. The artifact creation interval below is the actual discriminator;
    # the attempt endpoint describes the same current attempt as run_info, not
    # an independent producing-attempt attestation. A later rerun never makes an
    # earlier failed attempt acceptable.
    attempt_number = run_info.get("run_attempt")
    if type(attempt_number) is not int or attempt_number < 1:
        raise ValueError("Artifact run has no authenticated current attempt")
    attempt = github(
        f"repos/{repository}/actions/runs/{run_info['id']}/attempts/{attempt_number}"
    )
    for key in (
        "id",
        "run_attempt",
        "status",
        "conclusion",
        "event",
        "path",
        "head_sha",
    ):
        if attempt.get(key) != run_info.get(key):
            raise ValueError("Artifact producing attempt differs from successful run")
    if any(
        attempt.get(key, {}).get("full_name") != repository
        for key in ("repository", "head_repository")
    ):
        raise ValueError("Artifact producing attempt has a different repository")
    try:
        started = dt.datetime.fromisoformat(attempt["run_started_at"])
        created = dt.datetime.fromisoformat(artifact["created_at"])
        ended = dt.datetime.fromisoformat(attempt["updated_at"])
        if not started <= created <= ended:
            raise ValueError(
                "Artifact was not produced in the current successful attempt"
            )
    except (KeyError, TypeError) as exc:
        raise ValueError("Artifact attempt timestamps are unavailable") from exc
    raw = github(f"repos/{repository}/actions/artifacts/{artifact_id}/zip", binary=True)
    if artifact.get("digest") != "sha256:" + sha256(raw):
        raise ValueError("Artifact bytes differ from the authenticated GitHub digest")
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or any(
            name.startswith("/") or ".." in PurePosixPath(name).parts or "\\" in name
            for name in names
        ):
            raise ValueError("Unsafe or duplicate artifact member")
        members = {name: archive.read(name) for name in names if not name.endswith("/")}
    return artifact, run_info, members


def country_component(
    root: Path, artifact_id: str, destination: Path
) -> tuple[dict, dict]:
    if not artifact_id or not artifact_id.isdecimal():
        raise ValueError(
            "Release build hold: final country candidate artifact ID is required"
        )
    artifact, run_info, members = authenticated_artifact(
        COUNTRY_REPOSITORY, int(artifact_id), COUNTRY_WORKFLOW
    )
    receipt = json.loads(members["release-build/receipt.json"])
    selected = json.loads((root / BUNDLE_PATH).read_text())["packages"][
        "policyengine-us"
    ]["version"]
    if (
        re.fullmatch(r"\d+\.\d+\.\d+", selected) is None
        or receipt.get("prepared_version") != selected
    ):
        raise ValueError(
            "Country artifact must be the selected final version, never rc1"
        )
    if (
        receipt.get("source_head") != run_info["head_sha"]
        or receipt.get("policy_source_matches_head") is not True
    ):
        raise ValueError("Country CI receipt/source identity differs")
    filename = receipt["wheel"]["filename"]
    if Path(filename).name != filename:
        raise ValueError("Invalid country wheel filename")
    raw = members["dist/" + filename]
    identity = wheel_identity(raw, selected, "policyengine-us")
    if (
        identity["sha256"] != receipt["wheel"]["sha256"]
        or identity["size_bytes"] != receipt["wheel"]["size_bytes"]
    ):
        raise ValueError("Country wheel differs from its authenticated CI receipt")
    destination.mkdir(parents=True, exist_ok=False)
    path = destination / filename
    path.write_bytes(raw)
    component = source_command(root, "country-wheel-component", "--wheel", str(path))
    return component, {
        "repository": COUNTRY_REPOSITORY,
        "artifact_id": artifact["id"],
        "artifact_digest": artifact["digest"],
        "run_id": run_info["id"],
        "run_attempt": run_info["run_attempt"],
        "attempt_control": "artifact_creation_within_current_successful_attempt_interval",
        "source_head": receipt["source_head"],
        "receipt_sha256": sha256(members["release-build/receipt.json"]),
        "component": component,
        "wheel": identity,
    }


def source_from_event(root: Path) -> dict:
    if os.environ.get("GITHUB_EVENT_NAME") != "pull_request":
        raise ValueError("Candidate builds require the actual pull_request event")
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    pr = event["pull_request"]
    if (
        pr["head"]["repo"]["full_name"] != REPOSITORY
        or pr["base"]["repo"]["full_name"] != REPOSITORY
    ):
        raise ValueError("Candidate source must be a same-repository PR")
    head, base = pr["head"]["sha"], pr["base"]["sha"]
    parents = git(root, "show", "-s", "--format=%P", "HEAD").split()
    if (
        parents != [base, head]
        or git(root, "rev-parse", "HEAD") != os.environ["GITHUB_SHA"]
    ):
        raise ValueError("Candidate checkout is not the exact prospective PR merge")
    return {
        "pr": event["number"],
        "head": head,
        "base": base,
        "merged_tree": git(root, "rev-parse", "HEAD^{tree}"),
    }


def source_from_merge(root: Path, merge_commit: str) -> dict:
    """Accept merge/squash results qualified against their exact first-parent base.

    Rebase merging is unsupported. A changed main base requires a new candidate
    and root/peer agreement before merge, never stale-base artifact reuse.
    """
    prs = pages(f"repos/{REPOSITORY}/commits/{merge_commit}/pulls", "")
    eligible = [
        pr
        for pr in prs
        if pr.get("merged_at")
        and pr.get("merge_commit_sha") == merge_commit
        and pr["base"]["ref"] == "main"
    ]
    if len(eligible) != 1:
        raise ValueError("Release build hold: no unique merged PR for this source")
    pr = eligible[0]
    return {
        "pr": pr["number"],
        "head": pr["head"]["sha"],
        "base": git(root, "rev-parse", merge_commit + "^1"),
        "merged_tree": git(root, "rev-parse", merge_commit + "^{tree}"),
    }


def select_candidate(candidates: list[dict]) -> dict:
    if not candidates:
        raise ValueError(
            "Release build hold: no authenticated qualifying candidate artifact"
        )
    fingerprints = {
        canonical(
            {
                key: item["receipt"][key]
                for key in (
                    "source",
                    "version",
                    "flavor",
                    "prepared_tree",
                    "preparation_inputs",
                    "toolchain",
                    "package_identity",
                    "wheel",
                )
            }
        )
        for item in candidates
    }
    if len(fingerprints) != 1:
        raise ValueError(
            "Multiple divergent eligible candidate artifacts; re-review required"
        )
    # Repeated identical preparations have one deterministic selected identity.
    return min(candidates, key=lambda item: item["artifact_id"])


def discover_candidate(source: dict) -> dict:
    expected_name = f"{ARTIFACT_PREFIX}{source['head']}-{source['base']}-release"
    artifacts = pages(
        f"repos/{REPOSITORY}/actions/artifacts?name={expected_name}", "artifacts"
    )
    candidates = []
    for item in artifacts:
        if item.get("expired"):
            continue
        artifact, run_info, members = authenticated_artifact(
            REPOSITORY, item["id"], WORKFLOW
        )
        receipt = json.loads(members["receipt.json"])
        prs = run_info.get("pull_requests", [])
        # GitHub's PR-reference head/base SHA fields change when the PR moves.
        # run.head_sha is immutable. The reviewed job independently records
        # its event's base and actual merge-parent/tree checks in the artifact.
        if run_info.get("head_sha") != source["head"] or not any(
            pr.get("number") == source["pr"] for pr in prs
        ):
            raise ValueError(
                "Candidate run does not bind the exact reviewed PR head/base"
            )
        if (
            artifact["name"] != expected_name
            or receipt.get("source") != source
            or receipt.get("flavor") != "release"
        ):
            raise ValueError(
                "Candidate receipt/source differs from authenticated workflow identity"
            )
        ci = receipt.get("ci", {})
        if (
            ci.get("run_id") != run_info["id"]
            or ci.get("run_attempt") != run_info["run_attempt"]
            or ci.get("repository") != REPOSITORY
            or ci.get("workflow") != WORKFLOW
        ):
            raise ValueError("Candidate CI receipt run identity differs")
        filename = receipt["wheel"]["filename"]
        raw = members["dist/" + filename]
        if {"filename": filename, **wheel_identity(raw, receipt["version"])} != receipt[
            "wheel"
        ]:
            raise ValueError(
                "Candidate wheel/RECORD differs from authenticated receipt"
            )
        candidates.append(
            {
                "artifact_id": artifact["id"],
                "artifact_digest": artifact["digest"],
                "run_id": run_info["id"],
                "attempt_control": "artifact_creation_within_current_successful_attempt_interval",
                "receipt": receipt,
                "receipt_sha256": sha256(members["receipt.json"]),
            }
        )
    if not candidates:
        raise ValueError(
            "Release publication hold: no authenticated stable candidate for exact "
            f"PR {source['pr']} head {source['head']} and base {source['base']}. "
            "Finish Wf qualification, rerun against the current base, and obtain "
            "root/peer agreement before a merge or squash merge; rebase merges "
            "are unsupported."
        )
    return select_candidate(candidates)


def verify_prepared_receipt(actual: dict, expected: dict) -> None:
    for key in (
        "source",
        "flavor",
        "version",
        "preparation_inputs",
        "toolchain",
        "prepared_tree",
        "package_identity",
    ):
        if actual.get(key) != expected.get(key):
            raise ValueError(f"Release {key} differs from the authenticated candidate")


def candidate_build(root: Path, flavor: str, output: Path) -> None:
    source = source_from_event(root)
    if git(root, "status", "--porcelain", "--untracked-files=no"):
        raise ValueError("Candidate checkout must be clean")
    reject_untracked_build_inputs(root)
    if output.exists():
        raise ValueError("Candidate output must be new")
    output.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix="wrapper-preparation-") as temporary:
        prepared = Path(temporary) / "source"
        run(root, "git", "clone", "--quiet", "--no-hardlinks", str(root), str(prepared))
        git(prepared, "checkout", "--detach", git(root, "rev-parse", "HEAD"))
        # Switch editable metadata/import resolution to this isolated source.
        env = controlled_environment(preparation_inputs(prepared, source["head"]))
        run(
            prepared,
            "uv",
            "pip",
            "install",
            "--python",
            sys.executable,
            "--no-deps",
            "--no-build-isolation",
            "--editable",
            str(prepared),
            env=env,
        )
        country, evidence = None, None
        if flavor == "rc1":
            country, evidence = country_component(
                prepared,
                os.environ.get("RELEASE_COUNTRY_CANDIDATE_ARTIFACT_ID", ""),
                output / "country",
            )
        receipt = prepare(prepared, flavor, source, country)
        receipt["ci"] = {
            "repository": REPOSITORY,
            "workflow": WORKFLOW,
            "run_id": int(os.environ["GITHUB_RUN_ID"]),
            "run_attempt": int(os.environ["GITHUB_RUN_ATTEMPT"]),
        }
        if evidence is not None:
            receipt["country_candidate"] = evidence
        build(prepared, receipt, output / "dist")
        write_json(output / "receipt.json", receipt)
        # A portable exact tracked-source snapshot is review evidence, never
        # loaded as instructions or substituted for a trusted source checkout.
        with (output / "prepared-source.tar").open("wb") as stream:
            subprocess.run(
                ["git", "archive", receipt["prepared_tree"]],
                cwd=prepared,
                stdout=stream,
                check=True,
            )


def versioning(root: Path, output: Path) -> None:
    if git(root, "status", "--porcelain", "--untracked-files=no"):
        raise ValueError("Versioning checkout must be clean")
    source = source_from_merge(root, git(root, "rev-parse", "HEAD"))
    candidate = discover_candidate(source)
    receipt = prepare(root, "release", source)
    verify_prepared_receipt(receipt, candidate["receipt"])
    write_json(output, {"candidate": candidate, "actual_preparation": receipt})


def publish_check(root: Path, output: Path) -> None:
    sentinel = git(root, "rev-parse", "HEAD")
    if git(root, "show", "-s", "--format=%s", sentinel) != "Update package version":
        raise ValueError("Publication requires the ordinary Versioning sentinel")
    if len(git(root, "show", "-s", "--format=%P", sentinel).split()) != 1:
        raise ValueError("Versioning sentinel must have exactly one parent")
    source = source_from_merge(root, git(root, "rev-parse", "HEAD^1"))
    candidate = discover_candidate(source)
    expected = candidate["receipt"]
    actual = {
        "schema_version": 1,
        "flavor": "release",
        "source": source,
        "version": tomllib.loads((root / "pyproject.toml").read_text())["project"][
            "version"
        ],
        "preparation_inputs": preparation_inputs(root, source["head"]),
        "toolchain": check_toolchain(root),
        "prepared_tree": prepared_tree(root),
    }
    env = controlled_environment(actual["preparation_inputs"])
    actual["package_identity"] = verify_identity_fresh(
        root, actual["version"], "release", env
    )
    verify_prepared_receipt(actual, expected)
    run(root, sys.executable, "scripts/check_release_credentials.py", env=env)
    run(
        root,
        sys.executable,
        "scripts/bundle.py",
        "check",
        "--published-spm",
        "--include-tros",
        "--strict-tros",
        env=env,
    )
    run(root, sys.executable, "scripts/release_lock.py", env=env)
    build(root, actual, root / "dist")
    if actual["wheel"]["members"] != expected["wheel"]["members"]:
        raise ValueError("Rebuilt release wheel members differ from qualified Wf")
    require_unpublished(actual["version"])
    write_json(
        output,
        {
            "candidate": candidate,
            "actual_release": actual,
            "actual_sentinel_commit": sentinel,
            "member_equality": True,
            "container_equal": actual["wheel"]["sha256"] == expected["wheel"]["sha256"],
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=[
            "bootstrap",
            "check-toolchain",
            "candidate",
            "candidate-tros",
            "verify-identity",
            "country-wheel-component",
            "require-unpublished",
            "versioning",
            "publish-check",
        ],
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--flavor", choices=["rc1", "release"])
    parser.add_argument("--version")
    parser.add_argument("--wheel", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "check-toolchain":
            print(json.dumps(check_toolchain(ROOT), sort_keys=True))
        elif args.command == "candidate-tros":
            if not args.version:
                raise ValueError("Candidate TRO version is required")
            generate_candidate_tros(ROOT, args.version)
        elif args.command == "verify-identity":
            if not args.version or not args.flavor:
                raise ValueError("Identity verification requires version and flavor")
            print(json.dumps(verify_identity(ROOT, args.version, args.flavor)))
        elif args.command == "country-wheel-component":
            if args.wheel is None:
                raise ValueError("Country component requires an actual wheel")
            assert_source_origin(ROOT)
            sys.path.insert(0, str(ROOT / "scripts"))
            component = load_helper(
                ROOT, "scripts/spm_bundle.py"
            ).local_wheel_component(args.wheel, "policyengine-us")
            assert_source_origin(ROOT)
            print(json.dumps(component))
        elif args.command == "require-unpublished":
            require_unpublished(
                tomllib.loads((ROOT / "pyproject.toml").read_text())["project"][
                    "version"
                ]
            )
        else:
            if args.output is None:
                raise ValueError("An explicit external output path is required")
            output = args.output.resolve()
            if output.is_relative_to(ROOT) and args.command != "publish-check":
                raise ValueError(
                    "Evidence/build environment must stay outside tracked source"
                )
            if args.command == "bootstrap":
                bootstrap(ROOT, output)
            elif args.command == "candidate":
                if args.flavor is None:
                    raise ValueError("Candidate flavor is required")
                candidate_build(ROOT, args.flavor, output)
            elif args.command == "versioning":
                versioning(ROOT, output)
            else:
                publish_check(ROOT, output)
    except (
        ValueError,
        KeyError,
        OSError,
        subprocess.CalledProcessError,
        zipfile.BadZipFile,
    ) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
