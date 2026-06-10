from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("POLICYENGINE_SKIP_COUNTRY_IMPORTS", "1")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from policyengine.provenance.bundle_import import main

if __name__ == "__main__":
    raise SystemExit(main())
