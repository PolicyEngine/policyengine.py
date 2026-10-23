For microcosm #1348's owner: follow-up local-only rehearsal patch; apply after 0001.

The first live run silently waited during uninstrumented preflight before reaching Shell. This patch records writer-check, national/regional manifest downloads, git fetch/base resolution/worktree creation, the old-bundle read and the direct regional-constant rewrite in the same JSONL timings. Each preflight/model-surface step prints start and completion messages. Shell child output now streams immediately into the .certify.log file, so operators can tail package installs, TRO generation and pytest while they run.

Git fetch has a 300-second subprocess timeout and the two writer-check network calls each have a 120-second timeout. Hugging Face metadata has a 60-second per-request timeout; downloads use a default 120-second per-request timeout, preserving an operator's existing HF_HUB_DOWNLOAD_TIMEOUT. Hub retries can extend total wall time; these values bound individual HTTP operations, not the whole manifest step.

Validation: 11 offline stdlib unittest regressions passed in 0.118 seconds; Ruff check and Ruff format --check passed for the runner and its test file. Formatting only also cleans the initial patch's tests.
