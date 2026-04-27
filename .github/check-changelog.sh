#!/usr/bin/env bash
set -euo pipefail

if [ "${GITHUB_EVENT_NAME:-}" = "pull_request" ] && [ -n "${GITHUB_BASE_REF:-}" ]; then
  git fetch --no-tags --depth=1 origin "$GITHUB_BASE_REF:refs/remotes/origin/$GITHUB_BASE_REF"
  FRAGMENTS=$(git diff --name-only --diff-filter=ACMRT "origin/$GITHUB_BASE_REF" HEAD -- changelog.d/ | grep -v '^changelog.d/.gitkeep$' || true)
else
  FRAGMENTS=$(find changelog.d -type f ! -name '.gitkeep' -print)
fi

if [ -z "$FRAGMENTS" ]; then
  echo "::error::No changelog fragment found in this pull request."
  echo "Add one with: echo 'Description.' > changelog.d/\$(git branch --show-current).<type>.md"
  echo "Types: added, changed, fixed, removed, breaking"
  exit 1
fi
