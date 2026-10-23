Fixes #<certification-issue>

Certify the Saturday 24 October national Microcosm cut
`microcosm-uk-2024-25-national-20261023T075039Z-a133f37a` with
`policyengine-uk==2.147.2`, its build-time model version. The Microcosm build is
`829c1bc26`, now on main through [microcosm#1338](https://github.com/PolicyEngine/microcosm/pull/1338).
That PR reports all 19 release-cut gates passing. This cut predates the final
DfE age-keying change; that change belongs to the next main build.

This is a preparation draft: the exact-pair evidence below is pending. Replace
the issue placeholder with a verified certification issue and add its Towncrier
fragment before opening the PR. Do not treat the rehearsal's results as this
branch's certification receipts.

### Base and national-only scope

Stack on [policyengine.py#704](https://github.com/PolicyEngine/policyengine.py/pull/704),
`budget-local-data-manifest`, pinned for this preparation at
`da2ae8fb8e97145093e35366686df99c1e38449e` (or a reviewed later head). The
certification uses `--drop-regional-release` and the exact national cut tag in
its manifest URI. The certification command, receipts and resulting bundle
must agree on that tag and model pin. #699 is not the base.

This is **national-only**: constituency and local-authority outputs are absent
until Monday's 26 October cut. María Juaristi
([juaristi22](https://github.com/juaristi22)) can override that routing decision.
An override needs its own explicit routing decision and evidence; this draft
does not certify the dense cut for the newer model.

The rehearsal's metadata-only dense-schema inspection found **16 absent new
inputs and 0 newly lost build-model variables** for the older dense cut
`microcosm-uk-2024-25-dense-20261019T000432Z-ee5c2dbe`. The 83 ignored stored
columns were already unknown to the build model; the full target-input absent
count was 143. These are distinct measures. The source receipt is
`~/reviews/uk-hub/jobs/budget-certify-rehearsal/evidence/dense-schema.json`
(dense H5 SHA-256
`8e10e130d0260e0b52e2e29902f0502ebdff76a14a3e57d2c876bf4cd8db5872`);
it read no microdata values. Attach the metadata receipt with the final evidence.

### Same-line re-cut exception

**Same-line re-cut exception (coordinator, 23 Oct, under d1682 and d1344).**
The Budget coordinator's 23 October 15:10Z decision sets the evidence package
below for this Saturday cut. Its scope is a re-cut of the same producer line,
using the model pinned at that cut's build version, during Budget week. It does
not inherit #685's cross-data-line comparison exception or automatically accept
a new UC-floor gap, input gap or failed gate. Record any acceptance decision
explicitly with its owner and evidence.

### Evidence package

- [ ] Attach and verify **all release-cut gate** receipts for the exact
  `a133f37a` cut, including the producer's 19-gate report from microcosm#1338.
- [ ] Run the **UC floor** on this cut and attach its receipt. If the #685
  caseload benchmark gap persists, obtain and record fresh explicit acceptance;
  #685's acceptance is not a new-cut pass.
- [ ] Refresh and review **household snapshots** on the pinned pair.
- [ ] Run the **#574 reform contract and Budget-inputs gates** on the cut with
  the complete coverage used by policyengine.py#685; attach the receipts and
  explain every needs-review, absent or unusable input.
- [ ] Run and attach the **strict bundle check**, generated release lock and
  TRO evidence for the pinned model/data pair.
- [ ] Run the **same-line 2×2 attribution** for FY2026-27 through FY2030-31:
  `{6cba5d71 data, a133f37a data} × {pe-uk 2.132.6, pe-uk 2.147.2}`. Report
  weighted national `gov_balance`, every tax and benefit head, and poverty.
  Separate the model effect on fixed data from the data effect on a fixed
  model. Use the aggregate-impact report's `report_spec.yaml` flag thresholds;
  map each flagged move to pe-uk PRs between 2.132.6 and 2.147.2 and/or Microcosm
  changes between the two cuts' build commits. Label every unmapped move
  **unattributed**. Record a cross-model cell that cannot load as
  **not computable**, preserve its error, attribute through the computable
  cells, and list all limitations.
- [ ] Record **scorecard replay: unavailable until the Microcosm replay fix
  lands**. Attach the unavailable status now; replace it with an exact-pair
  replay receipt if the fix becomes available. Unavailable is not a pass.
- [ ] Complete and review the remaining mechanical certification checks and
  normal PR CI; attach the final commit and receipts. All evidence must identify
  the resulting candidate commit and exact model/data pair.

The previous certified pair is national cut
`microcosm-uk-2024-25-national-20261019T083323Z-6cba5d71` with pe-uk 2.132.6.
Only weighted national aggregates may be shared, with UKDS small-cell rules
applied; retain private inputs and temporary environments outside Git.

### Release and adoption timeline

1. **Friday 23 October preparation:** stage the patched microcosm#1348 tool,
   sequential guarded `run-heavy.sh`, attribution script and this decision
   record. This preparation runs no simulations, suites, snapshots, UC floor or
   national data loads, and pushes nothing.
2. **Saturday 24 October heavy phase:** start only after the other hub's
   `route-a-release-rerun-d1811-2026-10-23` reservation ends at **00:30Z** and
   `reservation.py allowed uk-hub` permits work. Every step checks load1 ≤110
   and free disk ≥55,000,000,000 bytes. Run one step at a time, review evidence
   and limitations, then push and open a same-repository draft PR. The .py
   330-minute automatic qualify job is not a pull-request trigger; the required
   evidence remains the checklist above.
3. **Review, merge and release:** finish normal PR CI and review before merge;
   main tests, Versioning and Publish then produce PyPI and the GitHub Release.
   #685 observed about **1h15 PR CI plus 3h10 merge-to-PyPI**, including roughly
   two hours of queueing. These are observations, not a release-time guarantee.
4. **Dashboard adoption:** W5 monitors PyPI and consumer dispatch (or performs
   the authorized manual fallback); the adoption workflow validates the wheel
   identity and opens a draft upgrade PR. Vahid regenerates every published
   measure and combined run on that branch; María reconciles results and
   approves exceptions. Complete review/CI, merge, explicitly deploy the
   household API, smoke-check it, and prepare the green draft revert PR. The
   rehearsal's release-path research estimates about **1h20 plus regeneration
   beyond 20m** with quiet runners, or **7h15 plus regeneration beyond 1h45**
   under the observed busy queues. The dashboard runbook's **06:00Z completion**
   includes deployment, household checks and the revert PR; its **07:00Z
   go/no-go** must reflect actual completion. A three-hour local certification
   budget alone cannot guarantee adoption by those times.
5. **Monday 26 October:** assess the next cut for constituency and
   local-authority outputs, subject to María's override and new evidence.

Timeline sources: rehearsal `evidence/timings.csv` and
`evidence/research-release.md`, the [dashboard Budget-day runbook](https://github.com/PolicyEngine/uk-autumn-budget-dashboard-2026/blob/main/docs/budget-day-runbook.md),
and the [#685 final-head PR CI run](https://github.com/PolicyEngine/policyengine.py/actions/runs/39588831360).
