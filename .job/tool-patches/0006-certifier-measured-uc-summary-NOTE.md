For microcosm #1348's owner: sixth local-only rehearsal patch; apply after 0001–0005. No heavy execution or external action was run for this patch.

The live cut passed the UC floor, but the original generated handoff always requested acceptance of the previous cut's gap. This patch carries the full measured receipt in context, reports a concise passed/FAILED result with both measure-to-benchmark ratios, and adds the explicit UC acceptance checkbox only for an actual measured failure. It does not truncate JSON into a potentially incomplete receipt summary.

Fresh receipts remain mandatory. Missing/incomplete/contradictory receipts and disagreement between process exit status and measured result fail operationally; an actual measured failure still requires explicit human acceptance. Wrapper qualification remains separately pending.

Validation: 20 lightweight offline stdlib unittest regressions passed. New coverage checks passing and failing handoff text, exact rounded ratios, and rejection of incomplete or contradictory successful receipts. Ruff check and Ruff format checks passed. Live passing receipt remains .job/certification.uc_floor.json; this source-only patch does not rerun the national simulation.
