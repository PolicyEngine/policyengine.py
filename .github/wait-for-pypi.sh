#!/usr/bin/env bash
#
# Wait until the given policyengine release is visible on PyPI, so consumers
# notified afterwards can resolve the exact version.
#
# Environment:
#   VERSION  Exact policyengine version to wait for.
set -euo pipefail

if [[ -z "${VERSION:-}" ]]; then
  echo "ERROR: VERSION must be set." >&2
  exit 1
fi

ATTEMPTS=30
DELAY=20
for attempt in $(seq 1 "$ATTEMPTS"); do
  if curl -fsSL -o /dev/null "https://pypi.org/pypi/policyengine/${VERSION}/json"; then
    echo "policyengine ${VERSION} is visible on PyPI."
    exit 0
  fi
  echo "Attempt ${attempt}/${ATTEMPTS}: policyengine ${VERSION} not visible on PyPI yet; retrying in ${DELAY}s."
  sleep "$DELAY"
done

echo "ERROR: Timed out waiting for policyengine ${VERSION} on PyPI." >&2
exit 1
