#!/usr/bin/env bash
#
# Check out, or publish to, the qualification ledger branch.
#
#   .github/qualification-ledger.sh checkout <dir>
#   .github/qualification-ledger.sh publish <dir> "<commit message>"
#
# The ledger is an orphan branch that only grows. Each attempt writes its own
# directory (uk/<pair_id>/attempts/<key>/), which concurrent publishes never
# share. A rejected push is retried by replaying the single new commit on the
# latest tip; the new commit may be the branch's first (two runs can both find
# no ledger yet), so it is replayed with cherry-pick, which needs no parent.
#
# Two attempts of one pair do share that pair's published files
# (qualification_receipt.json, latest_attempt.json and pair.json). Git must
# never merge those line by line: a textual merge of two receipts can produce
# a valid-looking receipt that is neither (one attempt's harness with another's
# replay). They are replayed as binary, so a concurrent change to them
# conflicts. When those are the only conflicts and LEDGER_REDERIVE is set, the
# tip's copies are kept and "$LEDGER_REDERIVE <dir>" recomputes every pair's
# published files from its immutable attempts; otherwise the publish fails.
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
    attributes="$(mktemp)"
    trap 'rm -f "$attributes"' EXIT
    printf '%s\n' \
      'qualification_receipt.json merge=binary' \
      'latest_attempt.json merge=binary' \
      'pair.json merge=binary' > "$attributes"
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
      if ! git "${identity[@]}" -c core.attributesFile="$attributes" \
          cherry-pick --allow-empty "$new_commit" >/dev/null 2>&1; then
        conflicted="$(git diff --name-only --diff-filter=U)"
        shared_only=true
        while IFS= read -r path; do
          [ -z "$path" ] && continue
          case "$path" in
            uk/*/qualification_receipt.json|uk/*/latest_attempt.json|uk/*/pair.json)
              # Only a pair's published files, never an attempt's own.
              case "$path" in uk/*/*/*) shared_only=false ;; esac ;;
            *) shared_only=false ;;
          esac
        done <<< "$conflicted"
        if [ -z "$conflicted" ] || [ "$shared_only" != true ] \
            || [ -z "${LEDGER_REDERIVE:-}" ]; then
          git cherry-pick --abort || true
          echo "::error::The ledger commit conflicts with a concurrent publish."
          exit 1
        fi
        while IFS= read -r path; do
          git checkout --ours -- "$path"
        done <<< "$conflicted"
        # Recompute published files from the attempts, the tip's and this one's.
        $LEDGER_REDERIVE "$PWD"
        git add -A
        # Completes the cherry-pick, keeping its message, even if empty.
        git "${identity[@]}" commit --quiet --allow-empty --no-edit
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
