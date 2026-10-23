#!/usr/bin/env bash
#
# Notify consumer repositories that a policyengine release is available on
# PyPI by sending a repository dispatch, which triggers their update
# workflows.
#
# Environment:
#   VERSION         Exact policyengine version that was released.
#   GH_TOKEN        PolicyEngine GitHub App token with Contents write access to
#                   the consumer repositories.
#   CONSUMER_REPOS  Space-separated repositories to notify (default:
#                   policyengine-api policyengine-sim-api).
#   PAYLOAD_FILE    Optional JSON file holding the whole dispatch body
#                   ({"event_type": ..., "client_payload": {...}}), as written
#                   by scripts/release_consumers.py. Without it, a
#                   policyengine-release event carrying only the version is sent.
set -euo pipefail

if [[ -z "${VERSION:-}" ]]; then
  echo "ERROR: VERSION must be set." >&2
  exit 1
fi

read -r -a REPOS <<< "${CONSUMER_REPOS:-policyengine-api policyengine-sim-api}"

if [[ -n "${PAYLOAD_FILE:-}" ]]; then
  payload_version=$(python - "$PAYLOAD_FILE" <<'PY'
import json
import sys

payload = json.load(open(sys.argv[1]))["client_payload"]
request = payload.get("request")
print(payload.get("version") or request["candidate"]["policyengine"]["version"])
PY
)
  if [[ "$payload_version" != "$VERSION" ]]; then
    echo "ERROR: ${PAYLOAD_FILE} is for ${payload_version}, not ${VERSION}." >&2
    exit 1
  fi
fi

for repo in "${REPOS[@]}"; do
  if [[ -n "${PAYLOAD_FILE:-}" ]]; then
    gh api "repos/PolicyEngine/${repo}/dispatches" --method POST --input "$PAYLOAD_FILE"
  else
    gh api "repos/PolicyEngine/${repo}/dispatches" \
      -f event_type=policyengine-release \
      -f "client_payload[version]=${VERSION}"
  fi
  echo "Dispatched policyengine ${VERSION} to PolicyEngine/${repo}."
done
