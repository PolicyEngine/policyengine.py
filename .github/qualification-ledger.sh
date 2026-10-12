#!/usr/bin/env bash
#
# Check out, or publish to, the qualification ledger branch.
#
#   .github/qualification-ledger.sh checkout <dir>
#   .github/qualification-ledger.sh publish <dir> "<commit message>"
#
# The ledger is an orphan branch that only grows: each candidate pair writes
# its own directory, so concurrent publishes never touch the same file and a
# rejected push is retried by replaying the single new commit on the latest
# tip. The new commit may be the branch's first (two runs can both find no
# ledger yet), so it is replayed with cherry-pick, which needs no parent.
set -euo pipefail

BRANCH="${LEDGER_BRANCH:-uk-qualification-ledger}"
command="${1:?usage: qualification-ledger.sh checkout|publish <dir> [message]}"
dir="${2:?ledger directory required}"

case "$command" in
  checkout)
    if git ls-remote --exit-code --heads origin "$BRANCH" >/dev/null 2>&1; then
      git fetch --quiet origin "$BRANCH"
      git worktree add --quiet --force -B "$BRANCH" "$dir" FETCH_HEAD
    else
      git worktree add --quiet --detach "$dir"
      (
        cd "$dir"
        git switch --quiet --orphan "$BRANCH"
        cat > README.md <<'README'
# UK candidate qualification ledger

Written by `.github/workflows/certify-uk-release.yaml` in PolicyEngine/policyengine.py.
Each `uk/<pair_id>/` directory holds a candidate pair, every qualification
attempt's gate evidence, the replay request and receipt, and the latest
qualification receipt. Nothing is deleted.
README
      )
    fi
    ;;
  publish)
    message="${3:?commit message required}"
    cd "$dir"
    git add -A
    if git diff --cached --quiet; then
      echo "Ledger unchanged."
      exit 0
    fi
    identity=(-c user.name="policyengine-qualification[bot]"
              -c user.email="qualification@policyengine.org")
    git "${identity[@]}" commit --quiet -m "$message"
    new_commit="$(git rev-parse HEAD)"
    delay="${LEDGER_RETRY_DELAY:-5}"
    for attempt in 1 2 3 4 5 6; do
      if git push --quiet origin "HEAD:refs/heads/$BRANCH"; then
        echo "Published ledger: $message"
        exit 0
      fi
      # Someone else published first: replay this one commit on their tip.
      if ! git fetch --quiet origin "$BRANCH"; then
        sleep $((attempt * delay))
        continue
      fi
      git reset --quiet --hard FETCH_HEAD
      if ! git "${identity[@]}" cherry-pick --allow-empty "$new_commit" >/dev/null; then
        git cherry-pick --abort || true
        echo "::error::The ledger commit conflicts with a concurrent publish."
        exit 1
      fi
      sleep $((attempt * delay))
    done
    echo "::error::Could not publish the qualification ledger after 6 attempts."
    exit 1
    ;;
  *)
    echo "Unknown command: $command" >&2
    exit 2
    ;;
esac
