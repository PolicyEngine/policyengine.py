#!/usr/bin/env bash
# Heavy phase only. Preparation must never invoke this script without --help.
set -euo pipefail
set +x

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BRANCH=certify-uk-a133f37a-national
BASE_704=da2ae8fb8e97145093e35366686df99c1e38449e
TAG=microcosm-uk-2024-25-national-20261023T075039Z-a133f37a
STEPS='prepare-tool producer-gates materialize-old materialize-new old-environment prepare-repository certify replay-status budget-inputs reform-contract attribution evidence-index'
START=prepare-tool
RESUME=0
while (($#)); do
    case "$1" in
        --help|-h)
            cat <<'EOF'
Usage: ./run-heavy.sh [--from STEP] [--resume-certification]

Heavy phase only, after 2026-10-24 00:30Z and reservation clearance.
Runs sequentially; each step checks reservation.py allowed uk-hub,
load1 <=110 and free disk >=55,000,000,000 bytes. Stops on any failure.
No push or PR is performed. Supply HF_TOKEN/HUGGING_FACE_TOKEN or agent-secret.

PE_CERTIFY_STORAGE: private scratch outside Git (default /private/tmp/uk-a133f37a-national-UID).
PE_CERTIFY_MODEL_REPO: read-only policyengine-uk repository with both model tags.
PE_CERTIFY_RESERVATION_SCRIPT: fleet reservation.py (default ~/reviews/fleet-ops/tools/reservation.py).
Steps: prepare-tool producer-gates materialize-old materialize-new old-environment
       prepare-repository certify replay-status budget-inputs reform-contract attribution evidence-index
--from reuses earlier artifacts in the same storage/workspace; it never marks them passing.
--resume-certification is only for an interrupted, uncommitted tool worktree.
EOF
            exit 0 ;;
        --from) [[ $# -ge 2 ]] || { echo '--from requires STEP' >&2; exit 64; }; START=$2; shift 2 ;;
        --resume-certification) RESUME=1; shift ;;
        *) echo "Unknown argument: $1" >&2; exit 64 ;;
    esac
done
case " $STEPS " in *" $START "*) ;; *) echo "Unknown step: $START" >&2; exit 64 ;; esac

STORAGE="${PE_CERTIFY_STORAGE:-/private/tmp/uk-a133f37a-national-$UID}"
[[ "$STORAGE" == /* ]] || { echo 'PE_CERTIFY_STORAGE must be an absolute path' >&2; exit 64; }
export PE_CERTIFY_RESERVATION_SCRIPT="${PE_CERTIFY_RESERVATION_SCRIPT:-$HOME/reviews/fleet-ops/tools/reservation.py}"
export PE_CERTIFY_STORAGE="$STORAGE"
MODEL_REPO="${PE_CERTIFY_MODEL_REPO:-$HOME/PolicyEngine/policyengine-uk}"
HEAVY_REPO="$ROOT/.job/heavy-repo"
CANDIDATE="$ROOT/.job/certification"
EVIDENCE="$STORAGE/evidence"
METADATA="$ROOT/.job/metadata"
OLD_PYTHON="$STORAGE/venv-old/bin/python"
NEW_PYTHON="$CANDIDATE/.venv/bin/python"
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4 NUMEXPR_NUM_THREADS=4
export PYTHONUNBUFFERED=1
unset POLICYENGINE_UK_DATA_MANIFEST_FILE POLICYENGINE_US_DATA_MANIFEST_FILE
unset VIRTUAL_ENV GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE

source_git() {
    if [[ -d "$ROOT/.job/git" ]]; then
        git --git-dir="$ROOT/.job/git" --work-tree="$ROOT" "$@"
    else
        git -C "$ROOT" "$@"
    fi
}
guard() {
    python3 "$PE_CERTIFY_RESERVATION_SCRIPT" allowed uk-hub || return $?
    python3 - "$ROOT" "$STORAGE" <<'PY'
import datetime, os, pathlib, shutil, sys
assert datetime.datetime.now(datetime.timezone.utc) >= datetime.datetime(2026, 10, 24, 0, 30, tzinfo=datetime.timezone.utc), 'Heavy phase may not start before 2026-10-24 00:30Z'
load = os.getloadavg()[0]
for name in sys.argv[1:]:
    path = pathlib.Path(name).resolve()
    while not path.exists():
        path = path.parent
    free = shutil.disk_usage(path).free
    if load > 110 or free < 55_000_000_000:
        raise SystemExit(f'HOLD: load1={load:.2f}, free={free} bytes at {path}')
print(f'Guard passed: load1={load:.2f}; disk >=55 decimal GB')
PY
}

# This guard precedes scratch directories, environment installation and downloads.
guard
mkdir -p "$STORAGE"
chmod 700 "$STORAGE"
STORAGE="$(cd -- "$STORAGE" && pwd -P)"
export PE_CERTIFY_STORAGE="$STORAGE"
python3 - "$STORAGE" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
if any((p / '.git').exists() for p in (path, *path.parents)):
    raise SystemExit('PE_CERTIFY_STORAGE must be outside every Git repository')
PY
mkdir -p "$EVIDENCE" "$STORAGE/tmp" "$STORAGE/cache"
export TMPDIR="$STORAGE/tmp" UV_CACHE_DIR="$STORAGE/cache/uv"
export UV_PYTHON_INSTALL_DIR="$STORAGE/cache/python" HF_HOME="$STORAGE/cache/hf"
export XDG_CACHE_HOME="$STORAGE/cache/xdg" MPLCONFIGDIR="$STORAGE/cache/matplotlib"
export NUMBA_CACHE_DIR="$STORAGE/cache/numba"
if [[ -z "${HUGGING_FACE_TOKEN:-${HF_TOKEN:-}}" ]]; then
    IFS= read -r HUGGING_FACE_TOKEN < <(agent-secret get HUGGING_FACE_TOKEN maxghenis)
fi
export HUGGING_FACE_TOKEN="${HUGGING_FACE_TOKEN:-${HF_TOKEN:-}}"
[[ -n "$HUGGING_FACE_TOKEN" ]] || { echo 'No Hugging Face token available' >&2; exit 1; }
export HF_TOKEN="$HUGGING_FACE_TOKEN"
source_git merge-base --is-ancestor "$BASE_704" HEAD
[[ "$(source_git branch --show-current)" == "$BRANCH" ]] || { echo "Expected preparation branch $BRANCH" >&2; exit 1; }
[[ -z "$(source_git status --porcelain --untracked-files=no)" ]] || { echo 'Commit tracked preparation changes before running' >&2; exit 1; }
PREP_SHA="$(source_git rev-parse HEAD)"

REACHED=0
step() {
    local name=$1
    shift
    if [[ "$name" == "$START" ]]; then REACHED=1; fi
    if [[ "$REACHED" == 0 ]]; then return; fi
    guard
    printf '\nStarting %s\n' "$name"
    local started=$SECONDS
    local rc=0
    # Wait for tee so logs are complete before another step indexes them.
    # pipefail also propagates a log write failure.
    "$@" 2>&1 | tee "$EVIDENCE/$name.log" || rc=$?
    python3 - "$EVIDENCE/timings.jsonl" "$name" "$((SECONDS-started))" "$rc" <<'PY'
import datetime, json, sys
with open(sys.argv[1], 'a') as stream:
    stream.write(json.dumps({'step': sys.argv[2], 'elapsed_seconds': int(sys.argv[3]), 'returncode': int(sys.argv[4]), 'finished_at': datetime.datetime.now(datetime.timezone.utc).isoformat()})+'\n')
PY
    [[ "$rc" == 0 ]] || { echo "Stopped at $name (exit $rc); retain receipts and use --from after resolving it" >&2; exit "$rc"; }
}
prepare_repository() {
    [[ ! -e "$CANDIDATE" || "$RESUME" == 1 ]] || { echo 'Candidate exists; see handoff resume guidance' >&2; return 1; }
    if [[ ! -d "$HEAVY_REPO/.git" ]]; then
        local source
        if [[ -d "$ROOT/.job/git" ]]; then source="$ROOT/.job/git"; else source="$(source_git rev-parse --absolute-git-dir)"; fi
        git clone --quiet --no-hardlinks --single-branch --branch "$BRANCH" "$source" "$HEAVY_REPO" || return $?
        git -C "$HEAVY_REPO" branch -m preparation-source || return $?
        git -C "$HEAVY_REPO" remote set-url origin https://github.com/PolicyEngine/policyengine.py.git || return $?
        # A literal file symlink is not matched by the repository's data/ pattern.
        printf '/data\n/.venv/\n' >> "$HEAVY_REPO/.git/info/exclude" || return $?
    fi
    git -C "$HEAVY_REPO" cat-file -e "$PREP_SHA^{commit}" || return $?
    [[ "$(git -C "$HEAVY_REPO" rev-parse preparation-source)" == "$PREP_SHA" ]] || {
        echo 'Scratch repository belongs to another preparation commit; choose a fresh workspace' >&2; return 1;
    }
}
old_environment() {
    [[ -x "$OLD_PYTHON" ]] || uv venv --python 3.13 "$STORAGE/venv-old" || return $?
    guard || return $?
    uv pip install --python "$OLD_PYTHON" 'policyengine-uk==2.132.6' 'policyengine-core==3.33.3' tables || return $?
    uv pip freeze --python "$OLD_PYTHON" > "$EVIDENCE/old-environment.txt"
}
certify() {
    local resume_args=()
    [[ "$RESUME" == 0 ]] || resume_args+=(--resume-worktree)
    export PE_CERTIFY_TOOL_SOURCE_COMMIT
    PE_CERTIFY_TOOL_SOURCE_COMMIT="$(git -C "$ROOT/.job/microcosm" rev-parse HEAD)" || return $?
    # The tool runs snapshots, strict check, UC floor and the four-worker full
    # suite sequentially. Its patched internal guard also checks reservations.
    uv run --no-project --python 3.13 --with huggingface_hub \
        python "$ROOT/.job/certify_uk_cut_in_policyengine_py.py" \
        --pepy-repo "$HEAVY_REPO" --base-ref "$PREP_SHA" \
        --branch "$BRANCH" --worktree "$CANDIDATE" \
        --national-tag "$TAG" --drop-regional-release \
        --model-version 2.147.2 --core-version 3.33.3 \
        --test-workers 4 --pr-base budget-local-data-manifest "${resume_args[@]}"
}
evidence_index() {
    python3 "$ROOT/.job/index-evidence.py" --candidate "$CANDIDATE" \
        --evidence "$EVIDENCE" --preparation "$PREP_SHA"
}

step prepare-tool python3 "$ROOT/.job/prepare-tool.py"
step producer-gates uv run --no-project --python 3.13 --with huggingface_hub \
    python "$ROOT/.job/certification-evidence.py" producer-gates \
    --metadata "$METADATA" --output "$EVIDENCE/producer-gates.json"
for label in old new; do
    step "materialize-$label" uv run --no-project --python 3.13 --with huggingface_hub \
        python "$ROOT/.job/certification-evidence.py" materialize \
        --label "$label" --metadata "$METADATA" --storage "$STORAGE"
done
step old-environment old_environment
step prepare-repository prepare_repository
step certify certify
step replay-status "$NEW_PYTHON" "$ROOT/.job/certification-evidence.py" replay-unavailable \
    --candidate "$CANDIDATE" --output "$EVIDENCE/replay.json"
step budget-inputs "$NEW_PYTHON" "$ROOT/.job/certification-evidence.py" budget-inputs \
    --candidate "$CANDIDATE" --old-python "$OLD_PYTHON" \
    --old-data "$STORAGE/data/old.h5" --new-data "$STORAGE/data/new.h5" \
    --output "$EVIDENCE/budget-inputs.json"
step reform-contract "$NEW_PYTHON" "$ROOT/.job/certification-evidence.py" reform-contract \
    --candidate "$CANDIDATE" --new-data "$STORAGE/data/new.h5" \
    --output "$EVIDENCE/reform-contract.json"
step attribution python3 "$ROOT/.job/run-attribution.py" run \
    --candidate "$CANDIDATE" \
    --old-python "$OLD_PYTHON" --new-python "$NEW_PYTHON" \
    --old-data "$STORAGE/data/old.h5" --new-data "$STORAGE/data/new.h5" \
    --old-sha256 810ba980005a8b907cb51464279fa5e0125464b7af9a4871b7f6744c30951ece \
    --new-sha256 64f83900ca3a1242fb017585234844ce89f743d32e41cd2b6558057777f914aa \
    --model-repo "$MODEL_REPO" --microcosm-repo "$ROOT/.job/microcosm" \
    --old-build 810315ac2 --new-build 829c1bc26 \
    --reservation-script "$PE_CERTIFY_RESERVATION_SCRIPT" \
    --mapping "$ROOT/.job/attribution-mapping.json" --output "$EVIDENCE/attribution.json"
step evidence-index evidence_index
printf '\nEvidence retained in %s; human review is required before push/PR.\n' "$EVIDENCE"
