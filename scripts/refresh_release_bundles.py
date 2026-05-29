"""Refresh one or more certified policyengine.py release-bundle segments.

Examples::

    python scripts/refresh_release_bundles.py --country us
    python scripts/refresh_release_bundles.py --country uk --model-version 2.89.0
    python scripts/refresh_release_bundles.py --country all \\
        --us-model-version 1.715.2 --uk-model-version 2.89.0
"""

from __future__ import annotations

import sys

from policyengine.provenance.bundle_update import main

if __name__ == "__main__":
    sys.exit(main())
