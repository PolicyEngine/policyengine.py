#!/usr/bin/env bash
#
# Capture the installed policyengine version as a GitHub Actions step output.
#
# Environment:
#   GITHUB_OUTPUT  Step output file provided by GitHub Actions.
set -euo pipefail

VERSION=$(python .github/fetch_version.py)
if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Unexpected version output: ${VERSION}" >&2
  exit 1
fi
echo "version=${VERSION}" >> "$GITHUB_OUTPUT"
echo "Captured version ${VERSION}"
