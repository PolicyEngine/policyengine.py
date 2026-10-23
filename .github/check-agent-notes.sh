#!/usr/bin/env bash
# Fail when the checked-out tree holds agent or job notes.
#
# Subfleet build jobs keep their state in a .job/ folder at the root of
# their worktree: HANDOFF.md, PR_BODY.md, env, a git bundle and sometimes a
# whole repo.git. #704 and #699 committed .job/HANDOFF.md and .job/PR_BODY.md
# on 23 October 2026. Agents also write hand-off notes and reports at the
# root of a worktree: policyengine-uk#2376 put REPORT.md and PROGRESS.md on
# its main on 12 October 2026. Their content belongs on the pull request.
#
# It reads the index, which a fresh checkout fills from the commit it checks
# out: on a pull request, the merge of its head into its base. Main has none
# of these paths, so a pull request to main fails exactly when it adds one.
# The patterns are git pathspecs. "**/" matches any depth, the root
# included, and icase ignores capitalisation. The folders are rejected at any
# depth, the note names only at the root, since a note of the same name
# deeper in the tree can be real documentation.
set -euo pipefail

notes=$(git -c core.quotePath=false ls-files -- \
  ':(glob,icase)**/.job' ':(glob,icase)**/.job/**' \
  ':(glob,icase)**/.job-git' ':(glob,icase)**/.job-git/**' \
  ':(glob,icase)**/.diag' ':(glob,icase)**/.diag/**' \
  ':(top,icase)HANDOFF.md' ':(top,icase)handoffs.jsonl' \
  ':(top,icase)PR_BODY.md' ':(top,icase)PR-BODY.md' \
  ':(top,icase)REPORT.md' ':(top,icase)PROGRESS.md')

if [ -n "$notes" ]; then
  # One path per line: git quotes a name that holds a newline. The prefix
  # keeps a path that starts with "::" from being read as a workflow command.
  count=0
  while IFS= read -r path; do
    printf 'Agent or job note: %s\n' "$path"
    count=$((count + 1))
  done <<<"$notes"
  first=${notes%%$'\n'*}
  echo "::error::${count} agent or job note path(s) in the tree, starting with ${first} (all listed in the log) - post their content on the pull request and remove them."
  exit 1
fi
echo "No agent or job notes in the tree."
