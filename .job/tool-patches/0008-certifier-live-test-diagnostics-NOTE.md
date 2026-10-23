For microcosm #1348's owner: eighth local-only patch; apply after 0001–0007. No heavy execution or external action was run for this patch.

The live full-suite run printed only dots/F under -q, so failures seen at 16% and 33% could not be identified while the long remainder ran. Full-suite pytest now uses -vv and --durations=20: the streamed log identifies test nodes as they finish, and the final report names the slowest tests. Shell still streams child output into its log rather than flooding the tool console. Snapshots retain -q; worker limits, fixtures and test assertions are unchanged.

Validation: the existing 20 offline orchestration regressions passed serially in 1.204 seconds using the rehearsal Python 3.13 environment, with full results in `.job/logs/tool-diagnostics-regressions.log`. Ruff check and Ruff format --check passed. No output-flag-only test was added.

The patch applied cleanly on the already validated fresh snapshot. The complete eight-file series (nine commits) now matches the tested working tree byte-for-byte and leaves the validation worktree clean. Updated receipts: `.job/patch-series-validation.json` and `.job/logs/tool-patch-series-validation.log`. The earlier original-plus-regressions run remains 34 passed in 26.19 seconds; this diagnostic-only change was then covered by the 20-regression rerun.
