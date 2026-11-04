"""Write a byte-bound audit of regional H5 columns for an installed UK model.

Run in an environment with the exact requested policyengine-uk version and
PyTables installed. Supply the H5 files from the immutable regional manifest;
the audit verifies their hashes and downloads no microdata. The baseline is the
build model and core the regional manifest records: the audit reads their
variables in a throwaway ``uv run --with`` environment, resolved from PyPI as
of the manifest's build time, so it needs ``uv`` and PyPI. Certification reads
both models again. Columns the build model defines and the target does not
refuse; columns neither model defines are recorded as never modelled; and
target inputs the files do not store that were not build inputs are recorded
as defaulted.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
# The target model must be auditable before the current bundle certifies it.
os.environ.setdefault("POLICYENGINE_SKIP_COUNTRY_IMPORTS", "1")
sys.path.insert(0, str(REPO_ROOT / "src"))

from policyengine.provenance.regional_input_surface import (  # noqa: E402
    measure_regional_input_surface,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--regional-manifest-uri", required=True)
    parser.add_argument(
        "--artifact", required=True, action="append", metavar="NAME=PATH"
    )
    parser.add_argument("--model-version", required=True)
    parser.add_argument("--audited-by", required=True)
    parser.add_argument("--limitation", required=True, action="append")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    paths: dict[str, Path] = {}
    for entry in args.artifact:
        name, separator, path = entry.partition("=")
        if not separator or not name.strip() or not path.strip() or name in paths:
            parser.error("Each --artifact must be a unique nonblank NAME=PATH.")
        paths[name] = Path(path)
    evidence = measure_regional_input_surface(
        regional_manifest_uri=args.regional_manifest_uri,
        artifact_paths=paths,
        model_version=args.model_version,
        audited_by=args.audited_by,
        limitations=args.limitation,
        token=os.environ.get("HUGGING_FACE_TOKEN") or os.environ.get("HF_TOKEN"),
    )
    args.output.write_text(evidence.model_dump_json(indent=2) + "\n")
    print(
        f"Saved {len(evidence.artifacts)} artifact input audits to {args.output}: "
        f"policyengine-uk {evidence.model_version} against build model "
        f"{evidence.build_model_version} (core {evidence.build_core_version}); "
        f"{len(evidence.dropped_columns)} dropped, "
        f"{len(evidence.never_modelled_columns)} never-modelled, "
        f"{len(evidence.defaulted_inputs)} defaulted."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
