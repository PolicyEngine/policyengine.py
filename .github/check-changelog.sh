#!/usr/bin/env bash
set -euo pipefail

BASE_REF="${1:-origin/main}"

towncrier check --compare-with "$BASE_REF"
