#!/usr/bin/env bash
#
# Notify consumer repositories that a policyengine release is available on
# PyPI by sending a policyengine-release repository dispatch, which triggers
# their update workflows to open single-version bump PRs.
#
# Environment:
#   VERSION   Exact policyengine version that was released.
#   GH_TOKEN  PolicyEngine GitHub App token with Contents write access to the
#             consumer repositories.
set -euo pipefail

if [[ -z "${VERSION:-}" ]]; then
  echo "ERROR: VERSION must be set." >&2
  exit 1
fi

CONSUMER_REPOS=(
  policyengine-api
  policyengine-api-v2
)

for repo in "${CONSUMER_REPOS[@]}"; do
  gh api "repos/PolicyEngine/${repo}/dispatches" \
    -f event_type=policyengine-release \
    -f "client_payload[version]=${VERSION}"
  echo "Dispatched policyengine-release ${VERSION} to PolicyEngine/${repo}."
done
