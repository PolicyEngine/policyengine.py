"""Write the published JSON Schemas for policyengine.py receipt contracts.

The Pydantic models in ``policyengine.provenance.receipt`` are the source;
the schema files under ``src/policyengine/data/schemas/`` are what other
languages consume. ``tests/test_execution_receipt.py`` checks that the two
accept and reject the same receipts.

Usage::

    python scripts/generate_receipt_schemas.py          # write
    python scripts/generate_receipt_schemas.py --check  # fail if stale
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = REPO_ROOT / "src" / "policyengine" / "data" / "schemas"
os.environ.setdefault("POLICYENGINE_SKIP_COUNTRY_IMPORTS", "1")
sys.path.insert(0, str(REPO_ROOT / "src"))

from policyengine.provenance.receipt import ExecutionReceipt  # noqa: E402

SCHEMAS = {
    "execution_receipt.v1.schema.json": ExecutionReceipt.json_schema,
}


def render(builder) -> str:
    return json.dumps(builder(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    stale = []
    for filename, builder in SCHEMAS.items():
        path = SCHEMA_DIR / filename
        content = render(builder)
        if path.exists() and path.read_text() == content:
            continue
        if args.check:
            stale.append(path)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        print(f"wrote {path.relative_to(REPO_ROOT)}")
    for path in stale:
        print(f"{path.relative_to(REPO_ROOT)} is not up to date.", file=sys.stderr)
    return 1 if stale else 0


if __name__ == "__main__":
    raise SystemExit(main())
