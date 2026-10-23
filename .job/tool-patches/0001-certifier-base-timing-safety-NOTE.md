For microcosm #1348's owner: local-only rehearsal patch; nothing pushed.

The original runner always reads and branches from origin/main, so it cannot stack on policyengine.py #704. It also relies on Hugging Face's HF_TOKEN fallback while the operational credential is HUGGING_FACE_TOKEN. This patch accepts --base-ref (default origin/main), fetches only origin/* refs, resolves one immutable commit for both the old manifest and worktree, and passes the in-memory token explicitly.

Every subprocess run through Shell now records elapsed seconds and return code (also on failures) to an adjacent .timings.jsonl file. Model-surface comparisons are guarded and timed too. Before each Shell command and each model-surface calculation, refuse load1 > 110 or free space < 55,000,000,000 bytes. The configured pytest workers must be 1..4. The dev extra currently omits pytest-xdist; install it in the isolated environment only if absent before the parallel suite.

Pytest's actual nonzero return code now fails the run even when no FAILED test lines exist (configuration/collection/xdist failures previously looked green). UC floor exceptions without a fresh measured receipt now stop the run; a measured floor violation still appears in the draft's explicit human-acceptance checklist. The patch does not grant that acceptance.

Validation: `python3 -m unittest discover -s .job/upstream/tests -v`: 10 offline mocked-command tests passed. `python3 -m py_compile .job/upstream/tools/certify_uk_cut_in_policyengine_py.py` passed. Live certification timings and downstream issues belong in the main rehearsal report.
