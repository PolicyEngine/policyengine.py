#!/usr/bin/env bash
# Fail when a tree holds agent or job notes.
#
# Usage: .github/check-agent-notes.sh [COMMIT]
#
# With no argument it lists the index, which a fresh checkout fills from the
# commit it checks out. With a commit, it lists that commit's tree through a
# temporary index, without checking it out: CI fetches a pull request's head
# as data and never runs anything from it.
#
# Subfleet build jobs keep their state in a .job/ folder at the root of
# their worktree: HANDOFF.md, PR_BODY.md, env, a git bundle and sometimes a
# whole repo.git. #704 and #699 committed .job/HANDOFF.md and .job/PR_BODY.md
# on 23 October 2026. Agents also write hand-off notes and reports at the
# root of a worktree: policyengine-uk#2376 put REPORT.md and PROGRESS.md on
# its main on 12 October 2026. Their content belongs on the pull request.
#
# The patterns are git pathspecs. "**/" matches any depth, the root
# included, and icase ignores capitalisation. The folders are rejected at any
# depth, the note names only at the root, since a note of the same name
# deeper in the tree can be real documentation.
set -euo pipefail

if [ $# -gt 0 ]; then
  scratch=$(mktemp -d)
  trap 'rm -rf "$scratch"' EXIT
  export GIT_INDEX_FILE="$scratch/index"
  git read-tree "$1^{tree}"
fi

notes=$(git -c core.quotePath=false ls-files -- \
  ':(glob,icase)**/.job' ':(glob,icase)**/.job/**' \
  ':(glob,icase)**/.job-git' ':(glob,icase)**/.job-git/**' \
  ':(glob,icase)**/.diag' ':(glob,icase)**/.diag/**' \
  ':(top,icase)HANDOFF.md' ':(top,icase)handoffs.jsonl' \
  ':(top,icase)PR_BODY.md' ':(top,icase)PR-BODY.md' \
  ':(top,icase)REPORT.md' ':(top,icase)PROGRESS.md')

if [ -n "$notes" ]; then
  # The paths come from the pull request, so the runner must not read them
  # as workflow commands: "::" at the start of a line, or the older "##["
  # anywhere in it. stop-commands with a random token turns both off until
  # the token comes back. Git quotes a name that holds a newline, so each
  # path is one line.
  token=$(od -An -N16 -tx1 /dev/urandom | tr -d ' \n')
  echo "::stop-commands::${token}"
  count=0
  while IFS= read -r path; do
    printf 'Agent or job note: %s\n' "$path"
    count=$((count + 1))
  done <<<"$notes"
  echo "::${token}::"
  # Annotation data decodes "%", so encode it.
  first=${notes%%$'\n'*}
  first=${first//%/%25}
  echo "::error::${count} agent or job note path(s) in the tree, starting with ${first} (all listed in the log) - post their content on the pull request and remove them."
  exit 1
fi
echo "No agent or job notes in the tree."
