# tools/ — script triage

Audit status (2026-10-18): the historical pipeline below does NOT reproduce
validated “frozen” results. Current commands and proof scope are listed in
the dated audit section at the end and `docs/AUDIT.md`.

Two historical tiers: the **pipeline** and the **exploration archive** (kept for provenance;
results superseded, dead ends, or crop-labeling helpers). Within the
retired science log (now `docs/AUDIT.md` and `docs/RESEARCH.md`), sessions
map to scripts.

## Canonical pipeline (in use order)

| script | produces | used by |
|---|---|---|
| `pdf_extract.py` | text from source PDFs | docs/sources/*.txt |
| `page_scan.py` (+ `annotate.py`) | per-page colored-word scan, `--pair A B` facing/back-to-back checks | first-pass verification |
| `real_extract.py` | ink boxes + slot clouds + line grids | `tools/data/real_boxes/` |
| `real_stats.py <reps>` | global alignment rate vs real-geometry null | headline numbers |
| `rosette_digits.py` | 6,083 rosettes + digit crops | rosette_seq |
| `rosette_map.py` | digit classification + global DP → page→verse GROUND TRUTH | `page_verse_map.json`, `rosette_seq.npz` |
| `build_token_map2.py` | token records on rosette spans | `token_map2.json` |
| `map_tokens.py` | token-map library (load_tokens/load_page; keep_strips mode) | imported by census scripts |
| `mark_identity.py` | rosette-segment pins: default / `--semantic` (honest) / `--quran` | `mark_identity*.json` |
| `phrase_census.py` | echo-family census (rosette-anchored width-walk + pixel runs) | `phrase_census.json` |
| `mine_surplus.py` | shape clustering of mag runs (`--all` = full pool) | `mag_runs.json`, `tint_dictionary.json`, atlases |
| `pair_census.py` | type-level cross-page pair census | z=33 result |
| `run_pair_census.py <reps>` | ink-run pair census | z=+33/+60 result |
| `word_pair_census.py <reps> [src]` | same-(word,cell) pairs vs slot + label-permutation nulls | the z≈1 negative |
| `type_rates.py` | per-type alignment rates | Allah 86.5% table |
| `divine_census.py` | robust corpus word counts + pin coverage | `divine_census.json` |
| `lit_verdict.py` | literature claim verdicts | `lit_verdict.json` |
| `phrase_mirror_test.py <reps>` | A2a phrase-mirror pair test | negative |
| `page_turn_mirror.py <reps> <tol>` | A2b page-turn mirror test | negative |
| `grain_sweep.py <src>` | A2c grain sensitivity sweep | negative |
| `test_19er.py` | 9:128-129 participation test | n=3 verdict |
| `audit_crimson.py` | token_map2 position audit | the 48% finding |

Supporting (canonical, called by the above or needed to rebuild artifacts):
`fit_letters.py` (EM letter-width model → `letter_model.json`),
`find_basmala.py` (surah-opener bands → `basmala_bands.json`),
`red_clusters.py` (red-box features → `red_feats.npz`, input to type_rates).

## Exploration archive (provenance; not part of the pipeline)

- `prob_model.py`, `prob_cond.py`, `prob_other.py` — surrogate-layout
  nulls (sessions 1-3; superseded for the headline by real_stats, still
  the source of the analytic/surrogate tables).
- `rosette_scan.py` — superseded by `rosette_digits.py`.
- `sign_scan.py`, `sign_atlas.py`, `sign_clusters.py`, `sign_taxonomy2.py`
  — sign-layer investigation; resolved as waqf pause marks (S12).
- `mark_hosts.py`, `family_census2.py` — walk-drift-limited exploratory
  censuses (inconclusive by design; superseded by mark_identity).
- `label_crops.py`, `label_sheet.py`, `context_crops.py`, `probe_crops.py`,
  `cluster_read.py`, `mine_identity.py`, `run_crops.py` — crop-sheet
  generation/labeling helpers for the visual reads.
- `patch_strip_map.py`, `rebuild_runs.py`, `rebuild_rosette.py`,
  `span_test.py` — the token_map3 rebuild experiments; kept because they
  PROVE the kashida limit (three independent failures, S11).
- `extract_words.py` — early extraction prototype.

## 2026-10-18 — independently audited CPU route

| script | verified role |
|---|---|
| `verify_cpu.py [--full]` | scan-free independent flags, exact small cases, hashes, analytic means, stored inference; full deterministic MC replay optional |
| `alignment.py` | scalar reference and memory-bounded batched Boolean-union scorer |
| `slot_expectation.py` | hypergeometric first moments; Hoeffding column bound |
| `exact_column.py` | exact subset-count page distributions and exact-rational exponential Markov bounds |
| `reference_controls.py <reps>` | common size/gold filters and literal raw-component subset/permutation controls, including per-line counts |
| `real_stats.py <reps>` | current global component model; defaults to `real_boxes_v3`, not the historical pool |
| `real_extract.py 1 604 --output-directory <dir>` | repaired CPU image extraction, white-alpha rendering, source/version report |
| `image_io.py` | alpha-aware white-paper image rendering |
| `type_rates.py <reps> [--scope pooled]` | like-for-like statistics conditional on archived HISTORICAL shape labels; semantic correctness not certified |
| `divine_census.py` | explicit 2,699 encoded / 2,811 all-head-basmala count |
| `showcase_audit.py` | exact fixed-page occupancy arithmetic; separates arithmetic from unsupported Fisher inference |
| `audit_integrity.py [--scans]` | token/rosette/pin structural inventory and optional input image hashes |
| `word_pair_census.py`, `grain_sweep.py`, `phrase_mirror_test.py`, `page_turn_mirror.py`, `run_pair_census.py` | corrected conditional tests on archived semantic pins/runs, with explicitly limited inference |

`real_boxes/`, `red_types.npz`, token maps, rosettes and pins remain historical
inputs. New component extraction is separate in `real_boxes_v3/`. Do not
transfer old box indices or shape labels onto the rebuilt pool. Downstream
pin/map regeneration is not certified. `mark_identity.py` now defaults to
semantic candidates; broad tint hypotheses require `--tint-exploration`.

Mathematical tests: `python -m unittest discover -s tools -p 'test_*.py'`.
These test meaningful independent cases; syntax checks do not certify the
remaining exploration/archive scripts.

The initial merged-group bound is <2e-726 under its raw-slot reference;
the unit-consistent size-filtered raw-component bound is <1e-814. Both are
model-conditional. Neither supplies a validated neutral linguistic word null.

## 2026-10-18 — geometry-conditioned controls

- `geometry_controls.py <reps>` — fixed width/height-bin color-label counts
  within page, optionally line and geometric edge role; five comparisons on
  the same raw-site population. Saves `data/audit_geometry_controls.json`.
  Includes analytic hypergeometric means and fixed-label/mixed-stratum counts.
- `geometry_controls.py --verify <report.json> [--full]` — scalar observed
  scoring, population/strata checks, analytic means, saved MC inference and
  optional deterministic replay. Integrated into `verify_cpu.py [--full]`.
- `test_geometry_controls.py` — exact tiny-subset enumeration, reduction to
  prior page/line models, sampler checks and deterministic-limit ground truth.

These are component-geometry models. Strong conditioning leaves many labels
fixed and does not supply independently verified word/verse boundaries.

## 2026-10-18 — semantic validation and optional GPU OCR

- `semantic_validation.py --review logs/semantic-review` selects the six
  independently inspected pages and makes unlabelled review crops.
  `--analyze` compares exact corpus names, manual locations, pins and rosettes;
  `--verify tools/data/audit_semantic_validation.json [--scans]` replays it.
- `arabic_ocr.py` and `arabic_ocr_easy.py` run local GPU pilots with Surya
  and EasyOCR. Create an isolated environment at `.venv/ocr`, install
  `requirements-ocr.txt`, activate it, and select a GPU UUID with
  `CUDA_VISIBLE_DEVICES`. Model caches/output defaults are under `logs/`.
  Optional OCR packages and weights retain their upstream licenses.
- `ocr_benchmark.py [--verify]` checks normalized text errors and annotated
  name locations; `--source`/`--output` select the EasyOCR artifacts.
- `ocr_line_map.py [--verify]` aligns exact Quran words to approximate OCR
  lines, retaining all-optimal-path ambiguity. It does not invent word x-boxes.
- `mark_identity_semantic_v4.json` records the prefix/deficit/no-black-inference
  repairs. It is distinct from the v3 hypotheses used by earlier statistics.

CPU verification replays these saved-data checks without importing OCR/GPU
libraries. New tests compare edit arithmetic and ambiguity with exhaustive
small independent ground truths, plus corpus/pixel/location checks.

## 2026-10-18 — fresh sample, word regions and optional paid OCR

- `ocr_heldout_sample.py [--verify]` rebuilds/checks the second pre-OCR
  six-page annotation set and image hashes (requires scans).
- `heldout_semantics.py [--verify] [--scans]` checks exact name counts,
  localized ink/alignment and unchanged v4 pins. Default replay uses saved
  pixels; `--scans` rereads images.
- `ocr_word_map.py [--verify]` maps exact corpus identities to exclusive
  detected word/region boxes over all optimal edit paths; split-prefix
  boxes can be united, multiword boxes are never interpolated. Defaults
  to the first EasyOCR sample; use `--manual`, `--source`, `--output` for
  the held-out sample or cloud results.
- Local OCR runners, `ocr_benchmark.py` and `ocr_line_map.py` now accept
  `--manual` while preserving their original defaults.
- `arabic_ocr_cloud.py --plan` estimates Google document OCR usage without
  requests. For execution use `GOOGLE_CLOUD_VISION_API_KEY` or
  `--credentials logs/google-vision-credentials.json`; the latter requires
  optional `google-auth`/`requests`. Credentials belong in gitignored logs
  or the environment, not artifacts. Service-account live access is pending.
  The approved pilot budget is $20; no paid calls have yet been made.
- `test_ocr_word_map.py`, `test_arabic_ocr_cloud.py` cover exclusivity,
  deletions/repeated words, split/cross-row regions and cloud coordinate
  conversion. `verify_cpu.py` replays both samples and new artifacts.

Fresh results: 22/22 name lines correct; exact-token EasyOCR region locations
17/22 correct, five abstentions, no wrong accepted name locations. Raw Surya
hallucinates five Allah forms on the zero-name control page. See AUDIT.md
for denominators, method limitations and paid-service handoff.

### 2026-10-18 — cloud authentication checkpoint

`requirements-cloud-ocr.txt` pins optional service-account dependencies.
Authentication with the supplied gitignored credential succeeds; live OCR
is blocked by Google's **`BILLING_DISABLED`** response. The user needs to
enable billing on the credential's project before the pilot can continue.
The client now prints provider reason codes without account-specific error
metadata. Three focused cloud-client tests pass; `git diff --check` passes.

### 2026-10-18 — successful Google pilot artifacts

Billing retry succeeded: `data/ocr_heldout_google_v1/` and
`data/ocr_sample_google_v1/` retain raw Google responses and real word boxes.
`data/audit_ocr_heldout_google*.json` and `data/audit_ocr_google*.json`
record text/location benchmarks and exact-token region maps. Raw name boxes
score 60/60; the unchanged region mapper scores 58/60, with two over-union
failures preserved. Estimated 12-page OCR cost: $0.018 before free allowance.
The CPU verifier reconstructs conversions and replays all four reports
without service access. No need to rerun paid OCR for saved-data checks.

## 2026-10-18 — mandatory-support v2 and full-corpus acquisition

- `ocr_word_map.py --method mandatory-v2` adds bidirectional optimal-path
  ownership and intervening-word checks. Historical v1 remains the default.
  Use a distinct output path; both versions replay through the CPU verifier.
- `word_validation_sample.py` fixes the third six-page sample, frozen-rule
  hash, name labels and fixed row/word-position labels; `--verify --scans`
  checks provenance, `--review logs/word-v2-review` makes unlabelled ruled crops.
- `adjudicate_word_sample.py [--verify] [--scans]` retains a separate post-OCR
  full-label ruler/pixel adjudication, preserving original labels. Partition
  contacts remain unscorable boundaries rather than certified passes.
- `word_localization_validation.py [--verify]` compares both mapper versions
  and separates centers, coarse boundaries and abstentions. Supply the
  adjudicated `--manual` and `--output` to replay that separate report.
- `google_corpus_cache.py` prepares a 604-page full-scan manifest and reuses
  matching prior full-page responses in `logs/ocr-google-corpus-v1/`.
  `--summarize` exports compact raw regions after completion;
  `--verify [--raw]` checks compact inventory/arithmetic and optionally
  replays every local raw response. Acquisition uses `arabic_ocr_cloud.py`
  with the corpus manifest, cache output and an explicit page/budget limit.

Fresh v2 name locations score 20/20. Post-hoc corrected ordinary-word centers
score 30/30; six boundaries remain uncertain and supplemental اللهم has a
real clipped edge. See AUDIT.md before interpreting these as accuracy claims.

Full-cache status: **604/604 complete**, 588 new calls plus 16 reused responses.
Compact `data/ocr_google_corpus_v1.json` stores 87,843 raw regions; full JSON
responses remain in `logs/ocr-google-corpus-v1/`. `google_corpus_cache.py
--verify --raw` replays every response; `verify_cpu.py` checks the compact
artifact without that cache. Estimated cumulative OCR usage is $0.909 before
free allowance. Raw name-candidate count (2,842) is not a certified census.

## 2026-10-18 — corpus anchoring and wordlike sites

- `ocr_corpus_map.py` matches cached OCR to exact Quran text via unique
  character anchors and all-optimal substring alignment, without old verse/
  rosette maps. Synthetic head basmalas preserve original canonical IDs.
  Default output is retained unmasked v1; `--ornaments` plus a separate
  `--output` produces masked v2. `--verify [--full]` checks every stored
  identity/box and replays 12 fixed pages (all pages with `--full`).
- `ocr_ornament_bands.py [--verify]` derives wide tall gold bands directly
  from all 604 scans; no verse labels. V2 excludes OCR centers in those bands.
- `corpus_map_validation.py` records/checks the six fresh v1 page/name
  annotations; `--verify-manual --scans` rereads hashes. `--verify` reproduces
  the v1 comparison. Masked-v2 comparison is explicitly development/exposed.
- `ornament_scope_validation.py [--verify] [--scans]` checks another six fresh
  masked-v2 page scopes and two basmalas, retaining endpoint/geometry failures.
- `ocr_corpus_sites.py [--verify]` is an explicitly post-hoc site view:
  single mandatory detector boxes do not require union-contiguity checks;
  multi-region unions keep the conservative rule; boxes <35px tall are
  excluded. One duplicate canonical token and 11 missing-name hypotheses
  remain in its output, rather than being silently assigned or called black.

Outputs are `data/audit_ocr_corpus_map_v1.json`,
`data/audit_ocr_corpus_map_masked_v2.json`,
`data/audit_ocr_corpus_sites_v1.json` and the corresponding annotation/
validation JSONs. All are hypotheses with recorded inputs and policy limits;
111 checked name centers do not certify all word identities/boundaries.
`verify_cpu.py [--full]` integrates saved-data checks without scans or network;
full scan replay of gold segmentation is a separate command.

## 2026-10-18 — targeted corpus-site review

`corpus_site_review.py [--verify] [--scans]` replays the failure-selected
review of eleven missing names, one additional wrong accepted name location,
and the p315/p316 duplicate. Output: `data/audit_corpus_site_review_v1.json`.
All eleven omitted names are visibly colored; 20:77 ولقد belongs to p316.
The reconciled name-ID view contains 2,685 automatic hypotheses and 12
explicitly marked approximate manual cores, covering 2,697 scanned canonical
verse-name IDs. Coverage does not validate every automatic location or full
word boundaries. Wrong ordinary-word supports are retained as review evidence.
The scan-free verifier includes this replay; `--scans` also checks source
image hashes. Full findings and next work are at the bottom of AUDIT.md.

## 2026-10-18 — experimental observation filtering

- `ocr_observation_map.py [--verify] [--full]` builds/replays a separate v3
  map from cached OCR. Small/nonlexical/header regions are removed before
  text alignment; strong overlaps use an exact confidence-area-weighted
  independent-set choice. Source-region decisions remain auditable.
- `ocr_observation_validation.py [--verify]` compares previous sites, v3
  sites and a stricter exact-surface/anchor screen on exposed labels.
  V3 recovers six targeted names, fixes the duplicate and an ordinary-word
  mislocation, but accepts two wrong targeted name boxes. The stricter
  screen rejects those errors with substantial coverage loss.
- `test_ocr_observation_map.py` checks the combinatorial selection against
  independent exhaustive subsets and geometric/annotation edge cases.

Outputs: `data/audit_ocr_observation_map_v3.json` and
`data/audit_ocr_observation_validation_v3.json`; both replay in the CPU
verifier. These are experimental development results, not fresh semantic
accuracy estimates or a certified word-level reference population.

## 2026-10-19 — seeded rows and fresh frozen-rule word checks

- `ocr_reading_order.py --pages 542` exposes the old short-box row split and
  a tall-seed/median-center ordering. Short satellites cannot move row centers.
- `ocr_row_map.py [--verify] [--full]` builds/replays separate v4 hypotheses;
  `--pages` permits a development subset. Full-map output is
  `data/audit_ocr_row_map_v4.json`. Both p542 names and its `يحيك` are repaired;
  p67's accepted error and three name omissions remain.
- `ocr_observation_validation.py --mapping data/audit_ocr_row_map_v4.json
  --output data/audit_ocr_row_development_v4.json [--verify]` replays exposed
  development checks; its original v3 default report still reproduces.
- `row_validation_sample.py --verify [--scans]` checks frozen inference-source
  hashes and fresh annotation/pixel provenance. `--review` emits unlabelled
  ruler crops. The stored plan selects six non-header pages and two basmalas.
- `row_map_validation.py [--verify]` compares old/v3/v4 on that fresh sample:
  all get 20/20 centers and 8/8 evaluable horizontal boundaries; twelve edges
  remain unscorable. Output: `data/audit_row_fresh_validation_v4.json`.
- `test_ocr_reading_order.py` tests short-box row splitting, complete region
  inventory, translation invariance and legacy-equivalent ordered mapping.

All checks are integrated with the CPU verifier. The fresh sample is small,
structured and single-reader; it does not certify corpus-wide word geometry.

## 2026-10-19 — boundary-aware word/region lattice

- `ocr_word_boundary_map.py [--verify] [--full]` adds v5 whole-word endpoint
  alignment with bounded split/merge groups. Character edits cost 4, extra
  boundaries cost 1; all optimal paths retain region-owner ambiguity.
  RapidFuzz CPU acceleration is pinned in `requirements-audit.txt`.
- `word_boundary_sites.py [--verify]` supplies a conservative automatic view:
  actual multi-region unions must reproduce exact normalized token text.
  Single regions retain the previous site policy. Rejected unions are saved.
- `word_boundary_validation.py [--verify]` compares v4, broad v5 and the
  conservative view on exposed annotations. V5 recovers names at 7:164 and
  27:26; the conservative view abstains on the wrong p67 union. The targeted
  result is 10 correct / 0 wrong / 2 abstained, with other checked locations
  retained. This is development, including the formerly fresh v4 sample.
- `test_ocr_word_boundary_map.py` independently enumerates tiny whole-word
  substrings and split/merge paths; tests backward costs, exact boundaries,
  repeated-word ambiguity and multiword-region abstention.

Outputs: `data/audit_ocr_word_boundary_map_v5.json`,
`data/audit_word_boundary_sites_v5.json`,
`data/audit_word_boundary_development_v5.json`. All replay in the CPU verifier.
The conservative view excludes 711 nonexact unions and retains 2,695 scanned
name-ID hypotheses. It is not certified full-corpus semantics or boundaries.

## 2026-10-19 — frozen exclusion review and next validation sample

- `word_union_review.py --verify [--scans]` replays a 17-case hash-stratified
  review of the 711 rejected unions. `--review logs/word-union-review-v5`
  regenerates full-width scan context crops without predicted-box overlays.
  Sixteen rejected centers are correct; extent review retains two incomplete
  words, one included verse marker and the known wrong p67 location. This is
  a target-aware diagnostic review, not an accepted-site accuracy estimate.
- `word_boundary_fresh_plan.py --verify` checks a separate frozen scan-first
  plan: 54 physical word positions on pages 66/157/229/376/445/545. No fresh
  annotations or scores exist yet. Its protocol keeps unavailable positions
  and uncertain diacritic ownership explicit.
- `test_word_union_review.py` checks deterministic selection, stratum censuses
  and invalid-frame rejection. Both saved review and fresh plan replay in
  `verify_cpu.py`; use `--scans` on the review for original-image hashes.

Artifacts: `audit_word_union_review_plan_v5.json`,
`audit_manual_word_union_review_v5.json`, `audit_word_union_review_v5.json`,
and `audit_word_boundary_fresh_plan_v5.json` in `tools/data/`.

## 2026-10-19 — completed fresh physical-position validation

- `word_boundary_fresh_sample.py --verify [--scans]` replays the scan-first
  annotations for all 54 frozen slots. There are 52 labeled words and two
  unavailable seventh-word positions (p66 row 12, p445 row 2). Independent
  core rectangles score centers; separate partitions and explicit mark
  uncertainty leave 30 horizontal boundaries evaluable. `--review
  logs/word-boundary-fresh-v5` regenerates unlabelled full-width ruler sheets.
- `word_boundary_fresh_validation.py --verify` checks the saved annotation/
  evaluation lock and frozen broad/conservative comparison: **52 versus 50
  correct centers**, no wrong accepted centers; conservative v5 abstains on
  two genuine p445 words. Horizontal passes are **30/30 versus 29/30**, with
  the latter deficit an abstention. Unavailable positions and uncertain
  boundaries are retained explicitly. Both checks run in `verify_cpu.py`.
- `test_word_boundary_fresh_validation.py` guards denominators and mixed-ink
  measurement. The structured six-page sample is single-reader, not uniform
  corpus accuracy or independent double annotation. Labels are now exposed
  for any later model development; original inference rules are unchanged.

Artifacts in `tools/data/`: `audit_word_boundary_fresh_labels_v5.json`,
`audit_manual_word_boundary_fresh_v5.json`,
`audit_word_boundary_fresh_evaluation_lock_v5.json`, and
`audit_word_boundary_fresh_validation_v5.json`.

## 2026-10-19 — post-exposure review of all uncertain extents

- `word_boundary_extent_review.py --verify [--scans]` replays all 22 originally
  unscorable boundaries in a separate same-reader, post-exposure annotation.
  `--review logs/word-boundary-extent-v5` regenerates enlarged scan/ruler
  contexts; `--components page:row:position` prints scan-only ink components.
  Original fresh labels and results are immutable.
- Revised whitespace cuts and exact mandatory/possible-pixel edge bounds
  make 21 more boundaries evaluable; three retain uncertain interior marks
  whose inclusion cannot change either horizontal edge. p545 `اولئك` retains
  right-edge uncertainty 597..607 and stays unscorable.
- Combined post-exposure boundary passes: **50/51 broad, 48/51 conservative**.
  Both methods retain the accepted p545 `السبيل` right-edge failure (+16px,
  tolerance 12px); conservative v5 also retains its two p445 abstentions.
  Center outcomes remain unchanged. This is not a new fresh accuracy score.
- `test_word_boundary_extent_review.py` exhaustively checks every optional-
  pixel subset of tiny ternary frames against the exact edge-range proof.
  The stored review/comparison is integrated into `verify_cpu.py`.

Artifacts: `audit_word_boundary_extent_labels_v5.json`,
`audit_manual_word_boundary_extent_v5.json`, and
`audit_word_boundary_extent_validation_v5.json` in `tools/data/`.

## 2026-10-19 — explicit auxiliary policies and all-ownership scoring

- `word_boundary_ownership_policy.py --build` reconstructs attainable edge
  columns from the unchanged reviewed masks and hashed scans. It compares
  mandatory-only, include-all-optional, and every-allowed-subset scoring.
  Optional pixels come only from the previous explicit annotations; colored
  lexical letters/vowels are retained unless explicitly marked optional.
- `--verify [--scans]` replays
  `audit_word_boundary_ownership_policy_v5.json`; scan-free replay is also
  integrated into `verify_cpu.py`. This does not edit the prior labels or
  resolve the remaining mark-ownership uncertainty.
- Both endpoint conventions and all-subset scoring give **51/52 broad**,
  **49/52 conservative**, including the p545 accepted-edge failure and both
  conservative abstentions. The remaining interval passes under every
  ownership choice; it has uncertain exact geometry but a stable verdict.
- `test_word_boundary_ownership_policy.py` independently enumerates all
  subsets of tiny ternary masks to verify joint edge support and exact
  best/worst errors. Separate cases test holes in attainable columns,
  disagreement between endpoint-only and all-subset reasoning, colored
  lexical ink, the tolerance boundary, abstentions and unavailable slots.

## 2026-10-19 — in-box horizontal ink-hull experiment and fresh plan

- `ocr_ink_trim.py` implements a label-free candidate using only a scan and
  existing OCR box. Trim empty horizontal margins around all black/colored
  thresholded in-box ink; preserve vertical bounds and empty boxes. It
  cannot recover outside ink or remove thresholded neighboring marks.
- `word_boundary_ink_audit.py --build` measures **244 distinct boxes on 65
  exposed pages** and scores all earlier v4/broad-v5/conservative-v5 groups,
  all reviewed v5 slots and all 17 rejected unions. `--verify [--scans]`
  replays projections and outcomes; `--review logs/word-boundary-ink-trim-v6`
  generates the p545 and retained-counterexample overlays.
- Artifact `audit_word_boundary_ink_trim_development_v6.json` retains both
  original and candidate geometry/scores, all regressions, original extent
  annotations and the p545 raw OCR-region provenance. Reviewed all-ownership
  passes become 52/52 broad, 50/52 conservative, with no scored regressions
  across the exposed cohorts. Earlier mapper outputs are unchanged; rejected
  unions are counterfactual diagnostics and stay rejected automatically.
- `word_ink_trim_fresh_plan.py [--verify]` freezes the candidate, source/input
  hashes and **54 scan-first positions on p36/124/298/366/500/508**. All
  earlier exposed/measured pages and ornamented pages are excluded. This is
  a plan only; selected scans, labels and fresh scores are still pending.
  Artifact: `audit_word_ink_trim_fresh_plan_v6.json`.
- `test_ocr_ink_trim.py` exhaustively checks small binary images for minimal
  hull, containment and ink preservation; also tests color thresholds,
  center drift and retained limits. `test_word_ink_trim_fresh_plan.py` checks
  eligibility, frame-order invariance and the complete slot schedule.
- Both new reports are integrated into `verify_cpu.py`. The `v6` suffix
  identifies this refinement experiment, not a replacement corpus mapper.

## 2026-10-19 — completed locked fresh ink-trim comparison

- `word_ink_trim_fresh_sample.py --verify [--scans]` reproduces scan-first
  transcriptions, independent letter cores, full-ink partitions and explicit
  ownership uncertainty for all 54 frozen positions. `--review DIRECTORY`
  regenerates scan-only ruled rows; `--word-crops DIRECTORY` shows manual-cut
  context, and `--components page:row:position` prints scan-only components.
  Canonical text can be queried with `--corpus-verses` without OCR geometry.
- `word_ink_trim_fresh_validation.py --verify [--scans]` checks the saved
  annotation/evaluator lock before opening selected predictions, reproduces
  all four original/trimmed broad/conservative outcomes and records every
  paired transition, failure and regression. Labels/evaluator were locked
  before the first comparison; no later label or rule changes are included.
- Of 54 slots, 52 are labelled and two p508 seventh-word positions are
  unavailable. Fixed-edge passes improve **46/50 → 48/50**; exact
  all-ownership passes improve **47/51 → 49/51**. Centers stay **52/52** for
  every method. The broad/conservative boxes coincide on this sample, so
  these are paired dependent results, not independent replications.
- `word_ink_trim_fresh_diagnostics.py --verify` replays raw OCR provenance for
  the union of all failures in all four methods; `--review DIRECTORY`
  regenerates overlays. The two residual failures, p36 `لتعتدوا` and p366
  `طسم`, retain neighboring/marker ink. This is post-comparison diagnosis,
  with the original scan labels and scores preserved.
- `test_word_ink_trim_fresh_validation.py` checks complete slot accounting,
  abstention denominators, unavailable slots, uncertain ownership, recomputed
  center regressions and invalid pairing. CPU replay includes the new
  comparison and failure provenance.

New `tools/data/` artifacts: `audit_word_ink_trim_fresh_labels_v6.json`,
`audit_manual_word_ink_trim_fresh_v6.json`,
`audit_word_ink_trim_fresh_evaluation_lock_v6.json`,
`audit_word_ink_trim_fresh_validation_v6.json`, and
`audit_word_ink_trim_fresh_diagnostics_v6.json`. The original frozen plan's
historical planned-only stage marker is preserved unchanged.

## 2026-10-19 — automatic ownership-evidence development audit

- `ocr_ownership_evidence.py` constructs optional-ink masks from overlapping
  other mandatory-word rectangles and cached rosette rectangles. It compares
  those separately and jointly, plus an aggressive full-height rosette-column
  stress test. Exact conditional supports use M ⊆ S ⊆ P; automatic M is a
  hypothesis, not a certified target-ink subset. Empty M retains the box and
  supplies no edge certificate.
- `word_ownership_evidence_audit.py --verify [--scans]` reproduces **470
  context/reference-specific measurements on 71 exposed pages**, every earlier
  cohort and the formerly fresh v6 sample. Baseline is the unmasked in-box
  ink hull, with raw geometry and scores also retained. No cohorts are pooled.
- Clear manual partitions are used only to check proposals: count mandatory
  foreign ink, missing outside target ink and newly clipped target pixels.
  The audit retains a p321 center regression, p500's 28 clipped target pixels,
  and p366's favorable tolerance verdict despite four clipped target pixels.
- `--review logs/word-ownership-evidence-v7` regenerates all scored-regression,
  reference-confirmed extra-clipping and residual-failure overlays. Red pixels
  show clipped manual target ink; automatic claims, cores and both boxes are
  drawn separately.
- `test_ocr_ownership_evidence.py` independently enumerates every ownership
  subset of tiny ternary frames, checking exact joint supports. Tests also
  cover half-open masks, empty M, unclaimed foreign ink, outside missing ink,
  marker-shadow clipping and criterion-specific regression accounting.
- Artifact: `audit_word_ownership_evidence_development_v7.json`. Integrated
  into `verify_cpu.py`. This is a post-exposure diagnostic; the v6 labels,
  evaluator, original/trimmed results and conservative exclusions are intact.

## 2026-10-19 — scan-component separability diagnostic

- `ocr_ink_components.py` indexes the unchanged black-or-colored ink union
  with 4- and 8-connectivity, in the original OCR crop and full page. Every
  touching component retains its bounding box and inside/outside pixel counts.
- Existing clear manual references are evaluation only. For each component,
  target/non-target counts give the exact minimum in-box error over all
  whole-component assignments: `sum(min(target, non_target))`. A zero minimum
  means representability, not automatic ownership or full-word recovery.
- `word_ink_component_audit.py --verify [--scans]` replays the 470 frozen v7
  context/reference measurements on 71 pages, with the earlier overlapping
  cohorts kept separate. Scan-free mode checks accounting and derived results;
  scan mode additionally reconstructs every component and reference count.
- `--review logs/word-ink-components-v8` produces 37 raw/crop/page comparison
  sheets on the five retained counterexample pages, plus a context-key manifest.
  Evaluation colors: green target-only, orange foreign-only, red mixed, purple
  unlabelled. Outside-box ink remains unclassified.
- `test_ocr_ink_components.py` checks the exact oracle by exhaustive independent
  enumeration of every tiny ternary mask and every component assignment. It
  also covers diagonal contacts, outside-crop bridges, touching ink colors and
  empty/unlabelled frames.
- Artifact: `audit_word_ink_components_development_v8.json`. CPU-integrated.
  All 50 clear v6 in-box masks are exactly representable under all four modes;
  component selection is still unresolved. Full details and next step are in
  `docs/AUDIT.md`.

## 2026-10-19 — constructive fixed-geometry selection research

- `constructive_selection.py --verify` reconstructs an exact column-maximizing
  k-subset on every eligible page of the existing raw size-filtered, non-gold
  population. Input to the constructor is geometry and k, not observed red-site
  indices or word identities. Dynamic programming produces deterministic
  witnesses, checked by independent scoring and the audited exact-PMF support.
- Plan: `research_constructive_selection_plan_v1.json`, saved before the first
  run. Result: `research_constructive_selection_v1.json`, containing all 587
  page witnesses, source/input hashes and the exact uniform-null probability
  of the global maximum event. Both artifacts are under `tools/data/`.
- `test_constructive_selection.py` checks optimality against exhaustive subset
  enumeration, exact probability, duplicate sites, clipping and invalid inputs.
  Integrated into `verify_cpu.py`.
- Constructed column/union score: 4,671/4,682; mirror score: zero. This is a
  fixed-site label-selection diagnostic, not composition, semantic marking or
  a historical production model. Interpretation and the next research gate:
  `docs/RESEARCH.md`.

## 2026-10-19 — color-independent same-word alignment

- `same_word_alignment.py --verify [--full]` — full canonical verse-token
  ledger, strict unvowelled spelling identities, original OCR/support-box
  centers, and same-page different-row partners within 15px. No word-color
  selection. Reports every word type, missing tokens and matching pairs;
  standalone Allah and the broader declared name family stay separate.
- Two 5,000-replicate word-position comparisons preserve all per-word page/row
  counts, with an additional 20px width-bin condition in the second model.
  Analytic hypergeometric avoidance means accompany finite-MC uncertainty.
  Quick replay checks saved scores; `--full` regenerates all 10,000 trials.
- `same_word_exact_bounds.py --verify` — exact-rational expectations and
  integer-certified decimal Hoeffding upper bounds for standalone Allah and
  the separate family, under both models. Width-conditioned bounds: <10^-57
  and <10^-58 respectively. These are not exact tails or origin probabilities.
- `same_word_review.py logs/same-word-review-v1` — reproducible post-count raw
  crops for six paired and six unpaired standalone-Allah locations; manifests
  also expose the two unresolved names and target-randomization constraints.
- Tests: `test_same_word_alignment.py`, `test_same_word_exact_bounds.py`.
  Exhaustive independent small-frame pair/permutation/expectation checks.
- Data: `research_same_word_plan_v1.json`, `research_same_word_alignment_v1.json`,
  `research_same_word_exact_bounds_v1.json`. CPU-integrated. Methods and all
  five predeclared metrics, including the non-significant Rahim result, are
  appended to `docs/RESEARCH.md`.

## 2026-10-19 — text/order-preserving spacing pilot

- `text_layout_pilot.py --feasibility --verify`: six-page canonical-order,
  seeded-row and original interval feasibility; 58/89 rows qualify. Missing,
  overlapping and ambiguous rows remain excluded explicitly.
- `text_layout_comparator.py --verify`: frozen plan/candidate/input checks,
  exact original/equal-gap packing and full replay of 5,000 empirical-gap
  permutations, with actual word order, widths and row extents preserved.
  First build required `--freeze` before `--build`; existing v1 plans/results
  are not overwritten. Artifacts: `research_text_layout_*_v1.json`.
- `text_layout_review.py --verify [--review logs/text-layout-pilot-v1]`:
  independent all-pairs/packing checks, frozen-ledger agreement, exact center
  freedom, coverage and optional scan-backed schematic sheets.
- `test_text_layout.py`: four exhaustive independent permutation/packing,
  endpoint-scoring and rational-tolerance tests. Full pilot and review replay
  are integrated into `verify_cpu.py`.

This is a completed exposed-development interval/spacing diagnostic, not a
glyph renderer or historical/origin test. Full methods and mixed outcomes,
including continuation status, are in `docs/RESEARCH.md`.

## 2026-10-19 — broader color-independent word/phrase study

- `broad_phrase_alignment.py --verify [--full]`: all exact words and repeated
  within-verse 2–6-word windows; strict corresponding-word and descriptive
  hull-center scores, complete occurrence/type/pair accounting, exact-surface
  sensitivity, and a coherent actual-text/order spacing comparison. Reuses
  the six-page interval criteria on all pages; excludes no rows silently.
  `--full` regenerates all 5,000 corpus layouts and coordinate digest.
- `broad_phrase_review.py --verify [--review logs/broad-phrase-review-v1]`:
  independent scalar checks of every strict pair and all per-type endpoint
  totals; 48 predetermined paired/unpaired scan sheets and six contact sheets.
- `test_broad_phrase_alignment.py`: five independent exhaustive/reference
  word-window, missingness, strict-phrase and vectorized-packing checks.
- Artifacts: `data/research_broad_phrase_{plan,feasibility,alignment,review}_v1.json`.
  Both report checks are integrated into `verify_cpu.py`; candidate/evaluation
  hashes were frozen before scoring. New methods and outcomes:
  `docs/PHRASE-ALIGNMENT.md`.

Six lengths' primary comparisons exclude identities containing Allah-name
forms and use declared six-test Bonferroni adjustment. Phrase windows overlap;
the comparisons are not independent origin evidence. Gap exchangeability and
fixed inherited widths are a development model, not validated calligraphy.

## 2026-10-19 — verse/phrase-aware controls and exact invariance

- `phrase_structure_controls.py --verify [--full]`: frozen verse-internal
  and repeated-phrase-block gap controls, preserving canonical text/order,
  widths and anchors; 5,000 trials per model. Complete type/page accounting,
  deterministic verse-internal equalization and exact word-center extrema.
- `phrase_structure_review.py --verify`: independent canonical grouping and
  measured-center prefix ranges, guaranteed/outer-envelope pairs, exact
  score-invariance certificates and descriptive residual-type diagnostics.
- `test_phrase_structure_controls.py`, `test_phrase_structure_review.py`:
  six primary-model and two post-score envelope tests with exhaustive small
  layouts/coordinates and a correlated-position counterexample.
- Data: `data/research_phrase_structure_{plan,controls,review}_v1.json`.
  Both report checks are integrated in `verify_cpu.py`; `--full` replays all
  10,000 new layouts as well as earlier full checks.

Methods, all surviving/disappearing residuals and historical-copy leads are
in the latest section of `docs/PHRASE-ALIGNMENT.md`. Conditional invariance
inherits existing phrase shapes and is not an origin proof.

## 2026-10-19 — dated historical-copy pilot

- `historical_copy_pilot.py --internet-archive [--corrected-indices]`: cached
  public manuscript acquisition for the fixed six rectos and colophon of
  Columbia MS Or 422 (catalogued 1779). Keeps the original off-by-one attempts.
  `--verify [--corrected-indices]` checks cached hashes/sizes; `--review`
  renders 1000px sheets/rulers; `--publish-manifest` exports/replays source
  URLs and hashes without copying raw metadata into source code.
- `historical_copy_analysis.py --verify`: scan-free deterministic canonical
  name-inventory check and descriptive same-token historical/modern scores.
  Includes assumed historical-coordinate envelope bounds and both tolerances;
  refuses to overwrite the frozen result. No statistical origin inference.
- `test_historical_copy.py`: five exhaustive/reference coordinate-envelope,
  threshold, partner-population and TEI label/path checks.
- Data: `data/research_historical_copy_{plan,retrieval_amendment,index_correction,annotations,analysis,sources}_v1.json`.
  Local scans/raw metadata and ruler sheets: `logs/historical-copy-ms-or-422-v1/`.
  Methods, all six pages, colophon/provenance qualifications and limits:
   `docs/HISTORICAL-COPY.md`. These checks run separately from `verify_cpu.py`.

## 2026-10-19 — shared-center review and historical phrase case

- `historical_center_review.py --verify`: replays all 33 historical/modern
  paired names under a shared manual letter-body-center convention, including
  symmetric working coordinate allowances and explicit old/new center changes.
  The annotation records correct two old historical wrong locations and retain
  all 90 physical row-end slots, with headings/basmalas explicit.
- `historical_center_review.py --phrase --verify`: checks canonical identity
  and all three corresponding centers for the two **من دون الله** instances
  in 29:17 on historical 200r rows 3/4. Both pass the nominal 1.5% threshold;
  the Allah pair alone is guaranteed under the declared allowances at 2%.
  Includes modern-ledger context and exact whole-phrase error boundaries.
- `--verify-scans` checks all 14 source image hashes. `--sheets` rebuilds full
  pages and full-width modern target strips without old x overlays;
  `--candidate-sheet` enlarges the historical phrase context. Outputs are local
  under `logs/historical-center-review-v1/`.
- Data: `data/research_historical_center_{plan,annotations,sources,review}_v1.json`
  and `data/research_historical_phrase_{plan,review}_v1.json`.
- `test_historical_center_review.py`: five meaningful checks for complete paired
  coverage, physical-page/nonverse exclusions, exact thresholds, strict lexical
  correspondence versus phrase-hull matching, and exhaustive error corners.
  All ten `test_historical*.py` tests pass. Replay commands remain separate
  from `verify_cpu.py`. Earlier frozen studies are not overwritten.

The historical case supports pre-project word/phrase alignment; it is exposed,
single-reader development evidence, not independent adjudication or an origin
likelihood. Full methods and new scores are appended to `docs/HISTORICAL-COPY.md`.

## 2026-10-19 — second historical copy with local GPU OCR

- `historical_extension.py --acquire`: acquires five preselected rectos and
  initial colophon candidate of MS Or 91 (catalogued 1776), retaining original
  source hashes/metadata. `--colophon-candidate` retains the documented separate
  correction. `--verify-sources` checks all nine cached acquisitions.
- `--ocr`: optional Surya 0.17 GPU run in `.venv/ocr`, requiring a GPU UUID.
  Raw predictions/model hashes remain local; complete cache is reused. The
  actual run included a severe repetition hallucination, so raw mention counts
  must not replace canonical scan-checked names. Google was not used.
- `--verify`: portable, scan-free reconstruction of all 66 manual names, partial
  boundary-word inventory, both tolerance/identity groups, coordinate envelopes,
  modern same-token ledger context, and positive/unsuccessful ordinary phrases.
  Reads current `research_historical_extension_review_v2.json`; the first v1
  report is retained, and unchanged scientific outcomes are enforced.
- `--archive-ocr` records the portable OCR summary; `--verify-ocr` checks the
  local raw predictions against that archive. `--inventory` prints canonical
  boundary tokens/names. `--case-sheets` rebuilds enlarged phrase/date context.
- `test_historical_extension.py`: five boundary, phrase-identity and first-result
  preservation checks. All **15** `test_historical*.py` tests pass.
- Artifacts: `data/research_historical_extension_{plan,sources,annotations,ocr}_v1.json`,
  `data/research_historical_extension_colophon_{amendment,source}_v1.json`,
  `data/research_historical_extension_review_v{1,2}.json`.
  Local scans/metadata/OCR: `logs/historical-extension-ms-or-91-v1/`.

All five folios and both successful/unsuccessful phrase cases are retained.
Methods, colophon foliation discrepancy, supporting observations and scope are
in the newest `docs/HISTORICAL-COPY.md` section. These checks remain separate
from the whole CPU verifier.

## 2026-10-19 — current historical extension scorer (v3)

- `historical_extension_final_review.py --verify`: applies 17 explicit
  post-score enlarged-context coordinate corrections, verifies canonical
  identity/row preservation, and replays **review_v3**, the current name result.
  Family primary count **34/66** supersedes the first-pass **38/66**.
- `historical_extension_review_sheets.py --corrected`: enlarged scan contexts
  for all 66 corrected/retained names; `--rows` and `--details` expose full-row
  and finer original-coordinate rulers. Original context sheets remain local.
- `test_historical_extension_final_review.py`: non-destructive patching and
  rejection of wrong-original, duplicate/unknown and impossible edge updates.
  All **18** historical tests and v3 reconstruction pass.
- Data: `data/research_historical_extension_coordinate_review_v1.json`,
  `data/research_historical_extension_review_v3.json`.

The original script's `--verify` continues to reconstruct **superseded v2**
for provenance. Use the final-review script for current name counts. Ordinary
phrase observations are unchanged; these are still same-reader development
measurements, not independent adjudication or origin likelihoods.

## 2026-10-19 — corrected findings publication

- `build_findings_article.py`: builds the article's HTML, ten-page
  PDF, data-derived comparison chart and review images from
  an input draft that is not included in this release (superseded by the v9
  ODT).
- Version 2, **The 10⁻⁸¹⁴ Result**, reconstructs all 587 headline component
  page distributions from hash-matched inputs, checks the observed column
  score, rebuilds the base-8 rational Markov bound and verifies the decimal
  certificate by integer comparison. Component and word-level charts stay
  separate. The HTML intermediate is written in the local review directory.
- Principal numerical tables are checked against the frozen same-word,
  broad-phrase, phrase-control and corrected historical reports before export.
  PDF checks include page count, principal text, linked images/alt text and
  content bounds. Review images and build hashes go under
  `logs/findings-article-2026-10-19/`.
- Two included historical crops use public-domain-designated Columbia scans.
  Their URLs, source/output hashes and coordinate transformations are in
  a provenance file that is not included in this release. No modern
  copyrighted scan is embedded.
- Run `. .venv/bin/activate` then `python tools/build_findings_article.py`.
  Publication dependencies are already listed in `requirements.txt`.

The article's proposed challenge uses Quran 2:23 as its epigraph. It separates
measurement correction, optimized feasibility and alignment-blind prediction;
there is no administered competition or evaluated submission yet.

## 2026-10-19 — infographic-led layman private draft

- `build_layman_article.py`: builds the separate five-page
  layman companion (outputs not included in this release) with larger
  type, five SVG infographics, and Hayrat scan examples from pages 2, 6 and
  431. The 100-dot pictures use explicitly rounded 75/25 counts; the zero
  grid contains exactly 814 zeros, arranged in 22 rows of 37.
- The builder reuses the technical publication's complete component-bound
  replay and checks the word statistics, selected phrase distances and source
  image hashes. Both paired excerpts retain a shared horizontal coordinate
  frame; support boxes/guides are overlays, not repositioned word images.
- Private-draft figures and their provenance are not included in this
  release. Initial generation or
  `--refresh-scans` requires hash-matched local scans; ordinary later builds
  verify and reuse the derived assets. Hayrat material is attributed as
  source scan excerpts; the source-image rights are not transferred.
- HTML intermediates, page/contact-sheet reviews and the build manifest are
  local under `logs/layman-v2-2026-10-19/`. The builder checks five-page layout,
  principal PDF text, image descriptions and content bounds.

## 2026-10-19 — V3 article from the user-supplied ODT outline

- `build_article_v3.py` builds
  `docs/articles/tawafuq-v3-2026-10-19.{md,pdf,odt}` content into a 17-page PDF
  and editable, self-contained ODT. The original `tawafuq-art.odt` is read-only
  input, with its hash recorded. `--inspect-reference` extracts the outline
  and its four embedded pictures under `logs/article-v3-reference/`.
- `--inspect-example-pages` prints the frozen Allah-family geometry for
  Hayrat pages 62/63 and 82/83. Generated spread outlines mark every mapped
  name; blue means a different-row partner within 15px and gray a nonmatch.
  The lower 3:114 `بالله` is included, while 3:115 `والله` remains a nonmatch.
- New ordinary-word pairs, coverage/breadth graphics and a corrected
  logarithmic probability chart are generated from checked inputs. V3 has
  14 embedded figures, including eight infographics; provenance is in
  a figures directory that is not included in this release.
- The builder replays the exact 587-page component certificate, checks current
  principal tables, identities, coordinates and source hashes, validates PDF
  text/bounds and checks a complete ODT text round-trip and embedded images.
  SVGs are rasterized for reliable ODT embedding. `odfpy` is listed in
  `requirements.txt`; no office-suite executable is needed to build.
- PDF page images, contact sheet, HTML and build hashes stay in
  `logs/article-v3/`. `--inspect-pagination` diagnoses overflow. PDF layout is
  visually reviewed; ODT office-suite rendering is not separately certified.
