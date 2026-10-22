# Independent mathematical and code audit

## 2026-10-18 — baseline and working contract

Status: **BOUNDED AUDIT PASS CLOSED (2026-10-19)**. Read the
[closing synthesis](AUDIT-CONCLUSION.md); this file is the chronological ledger.
Historical numbers in older articles are not validated by their
previous “frozen” label. Findings here distinguish implementation correctness,
descriptive observations, and inference conditional on a specified null.

Baseline revision: `bea87f365eb4550f262175a3d04651eb5c411333`.
Pre-existing work: modifications to `requirements.txt` and untracked
`tools/build_article_v4.py` (plus internal working notes since retired at
open-sourcing). Preserve these.
Work is CPU-only; no external systems or network services are required.

### Confirmed baseline defects

1. `real_stats.py` scores 3,564 / 4,623 = 77.09%, not the documented
   3,357 / 4,621 = 72.65%. A 20-replicate diagnostic run had null mean 27.03%;
   this is a reproduction diagnostic, not an audited inference.
2. Column and mirror counts are added: a four-word fixture scores eight.
3. Iterating the previous usable page permits nonadjacent pages to match.
4. Current column bins are compared with previous reflected-distance bins.
5. `type_rates.py` uses integer bitwise AND on occupancy counts; 1 versus 2
   incorrectly gives no match. It only flags the later member of a pair.
6. Observed type flags are pooled, null flags are type-specific; null overlap
   handling differs. Feature-to-box ranks can misassociate missing crops.
7. Type classification depends on ephemeral `/tmp/opencode/ink_B3.npy` and
   locally available, untracked `red_feats.npz`.
8. A Monte Carlo z-score is not a justified extreme-tail probability.
   Zero exceedances is not p=0. Independence of word-type evidence is unproved.
9. 3,269 bits means decimal exponent 984.067, not 3,269.
10. README's `python tools/real_extract.py` lacks its two required arguments.

### Work queue

- Define explicit scoring, independent reference, and meaningful regression tests.
- Correct global implementation; save reproducible null samples, input hashes,
  parameters, runtime and finite-simulation uncertainty.
- Correct type scoring using committed labels with exact source-box identity;
  separately assess reliability and regeneration of those labels.
- Reconstruct showcase formulas and correction assumptions.
- Audit negative identity/mirror tests, upstream extraction, normalization,
  and dependency/reproduction commands. Negative findings need auditing too.
- Reconcile publication summaries and provide a one-command CPU verifier.

### Interpretation rules

- A sampled slot is an image component, not necessarily a linguistic word.
- Observed/null scoring must be the same function on the same eligible pool.
- A placement null is conditional on geometry and counts; it is not a model
  of human manufacture, nor a probability of divine origin.
- “Not significant” does not prove absence, especially for incomplete pins.
- Source-selected showcase pages require selection-aware inference; arbitrary
  multipliers and independence assumptions must not be called established.
- Update this ledger with dated evidence and commands after each stage.

## 2026-10-18 — global scorer, first moments, and type comparisons

Implemented `alignment.py` with an independent scalar pair-enumeration
reference and a batched NumPy occupancy scorer. `test_alignment.py` checks
all subset pairs on a four-slot/two-page population, random batches,
overlap, missing pages, even occupancies, both endpoints, pairing rules,
bin boundaries, and exact analytic means by complete enumeration.

Score `component-union-v1`: same 30px column bin with at least two distinct
line indices, OR same reflected 32px cell and line across numerically
adjacent eligible pages. Odd x / even (1024-x); each endpoint flagged once.
Facing = even/odd pairs; leaf = odd/even pairs; both reported separately.
These are bins, NOT ±15px tolerance windows. Local line IDs are not exact
cross-page pixel heights. Scoring keeps the legacy bin choices for a clear
comparison; future physical-coordinate metrics must have new versions.

The 584 eligible pages have 4,623 components. Twenty pages are excluded;
nine valid pages with zero colored components are now retained. Observed:
column 3,328, mirror 285, intersection 219, union **3,394 (73.4155%)**.
The initial 20,000-replicate run gave mean union 26.2197%, SD 0.8101
percentage points, zero exceedances (about 59 seconds on this machine).
Re-running after adding analytic output records the current final artifact.

`slot_expectation.py` derives the exact model first moment: conditional on
a selected slot, no other-line column partner has probability
C(S-1-m,k-1)/C(S-1,k-1); avoidance in each eligible neighboring page has
probability C(S_q-m_q,k_q)/C(S_q,k_q). Page draws are independent, so these
avoidance probabilities multiply. Summing k/S times per-slot alignment
probabilities gives E[column] = **1,089.554679**, independently of Monte Carlo.

For the column-only statistic X=sum X_p, 0<=X_p<=k_p and independent page
draws imply Hoeffding's inequality:
P(X>=3328) <= exp[-2(3328-E[X])² / sum(k_p²)], sum(k_p²)=46,811.
This gives **log10 upper bound -92.973540** under the slot null. It is a
rigorous, loose MODEL-CONDITIONAL bound, not the historical p~10^-985,
not selection-adjusted, and not a human-construction probability.

Sensitivity runs (5,000 reps each): facing union 72.9613% vs 24.9058%;
leaf union 72.4854% vs 24.8909%. Shifting the column origin by 15px gives
73.5021% column-only vs 23.4967%; the excess is not just one bin phase.

### Per-type correction

`type_rates.py` now reads committed `red_types.npz`, validates exact
(page, source-box-index, x, line) identities, and labels two additional
current components `unclassified`. All 4,621 old assignments still match
their source-box coordinates. No temporary files or feature archive needed
for this conditional calculation. This does NOT validate semantic accuracy.

Like-for-like within-type results (2,000 reps):

| archived shape label | n | observed | slot mean |
|---|---:|---:|---:|
| allah | 2,158 | 79.10% | 17.17% |
| allah_pref | 111 | 12.61% | 1.49% |
| rabbi | 1,095 | 44.66% | 8.98% |
| huwa | 34 | 5.88% | 0.78% |
| partner_word | 707 | 63.93% | 26.35% |

Hu has 256/2,000 exceedances in this same-type question, rather than a
validated z=31 claim. Pooled scoring asks a different question: members
align with ANY colored component. It gives e.g. allah 87.21% vs 23.84%
and huwa 58.82% vs 26.23% (5,000 reps). The old table mixed these two
questions. Labels are shared and tails must not be multiplied.

Commands/artifacts:

```bash
python -m unittest discover -s tools -p test_alignment.py -v
python tools/real_stats.py 20000 --output tools/data/audit_global.json
python tools/real_stats.py 5000 --pairing facing --output tools/data/audit_global_facing.json
python tools/real_stats.py 5000 --pairing leaf --output tools/data/audit_global_leaf.json
python tools/real_stats.py 5000 --pairing none --column-origin 41 --output tools/data/audit_global_shifted_columns.json
python tools/type_rates.py 2000 --output tools/data/audit_types_same.json
python tools/type_rates.py 5000 --scope pooled --output tools/data/audit_types_pooled.json
```

Activate `.venv` first. Artifacts include raw null scores, SHA-256 input
hashes, seeds, batch sizes and finite-simulation intervals. Batch size is
part of the RNG configuration. A zero-exceedance run yields a binomial
upper confidence bound, never p=0 or an inferred Gaussian tail.

## 2026-10-18 — divine-name count corrected

`divine_census.py` wrongly treated ءالله at **10:59 and 27:59** as false
friends; reading the verses establishes that these are interrogative divine
names. It also removed 1:1, then added only 112 basmalas (one missing).
Corrected explicit conventions:

- 2,698 excluding encoded opening basmala 1:1;
- **2,699 in encoded corpus** (including 1:1);
- **2,811 with all 113 surah-head basmalas** (2,699 + 112 unencoded heads).

The embedded basmala at 27:30 is retained in each count. Calling 2,696 vs
2,808 vs 2,806 just “normalizer conventions” concealed actual mistakes.
The literature's 2,806 count is not verified by this counter. Invocation
`python tools/divine_census.py` now reproduces the corrected artifact and
does not regress the Fatiha correction. Ink pins come from semantic mode;
their count is conditional on pin correctness, not a certified lower bound.

## 2026-10-18 — upstream and negative-test audit (continuing)

### Confirmed upstream defects and fixes

- `page_scan.components` failed to resolve union-find roots and omitted the
  final label; component medians also included other regions inside a box.
  Replaced with SciPy CPU four-connected labeling and per-component pixels.
  Tiny image ground truths cover isolated final labels, merged branches,
  overlapping boxes and border behavior. Disk dilation no longer wraps
  opposite image edges via `np.roll`.
- PNG transparency was ignored by `.convert("RGB")`. Page 7 has transparent
  BLACK background and therefore failed the old black-text detector. New
  `image_io.py` renders transparency onto white paper. With this fix page 7
  yields a valid 15-line grid, 215 slots, two red-class components. Main
  extraction, pin, rosette and census pixel readers now use this helper.
- `map_tokens.est_width` looked for `tools/data/data/letter_model.json`,
  silently using fallback widths. The actual model also has flat width
  coefficients, not `width['letters']`. Both bugs fixed and schema-tested.
  Historical token maps/width-walk censuses must NOT be represented as
  regenerating unchanged after these fixes.
- `real_extract.py` now has documented default bounds, explicit output
  directory and overwrite flags, versioned artifacts, an extraction report,
  and nonzero exit status on page errors. An isolated full rebuild is running
  into `tools/data/real_boxes_v3/`; historical `real_boxes/` is preserved.
- Local scans are not uniformly 1024x1680: e.g. page 1 is 1024x1531.

### Identity and page-turn results

The historical 30px/112px identity calculation does reproduce approximately
on semantic pins: mag 63 pairs vs label-null 57.2, z~0.7; cri 5,250 vs
5,069.2, z~1.5 (2,000 reps). Slot sampling now fails on missing/insufficient
slots instead of dropping observations, and groups pins once per page.

The historical grain sweep was NOT a valid “all grains negative” test:

1. It discarded page IDs and counted same-page pairs as cross-page pairs.
2. Fine 15px columns were clipped into 32 bins (half the page collapsed);
   56px rows were clipped into 15 bins (bottom half collapsed).
3. Its mirror variant reversed ALL column labels: an invertible relabeling
   leaves every same-cell pair unchanged and does not test mirrored pairs.

`grain_sweep.py` now keeps pages, uses full physical partitions, and tests
actual opposite-cell pairs with cross-page subtraction. Pair formulas are
checked against explicit pair enumeration. **The replacement is NOT uniformly
negative:** several crimson identity statistics exceed the global label-null,
including 5,064 vs 4,591 mean at the ~30px physical grid (0/2,000 exceedances).
Magenta ~30px is 58 vs 53.9, not significant. The new suite has 26 dependent,
exploratory tests. Do not turn this into either “no word structure” or
“semantic miracle”: the null does not preserve page/surah word frequencies,
word widths or morphology; the incomplete pins were selected by matching.

The page-turn test also used max COLORED band as page bottom and called all
adjacent pairs facing spreads. It now uses true first/last reconstructed
bands (including empty ones), deduplicates carried runs by their OWN page,
and separates physical pair conventions. On **285 facing pairs**, observed
mirror hits = **31 vs 35.01** under x-permutation, upper-tail MC~0.777
(2,000 reps). Same-x hits 39 vs 34.21, MC~0.233. This narrow mirror test
remains negative; it does not establish absence of every form of tawafuq.

### Showcase inference

`showcase_audit.py` reconstructs Fisher arithmetic and exact fixed-page
occupancy tails using integer generating-function DP (tested by all-subset
enumeration). The old 1.65e-31 Fisher arithmetic is reproducible, but its
inference is unvalidated: approximate constituent probabilities, source
selection, independence, and the x1,320 correction family are not established.
A source predating our scans does NOT justify multiplying its dependent
subevents. Random-slot probabilities do not price a skilled scribe's work.

Fixed-page component occupancy outputs are explicitly separate from semantic
12-of-16 claims and sliding-window tolerances. Shape labels themselves need
validation: the historical p422 Hu box is labeled `rabbi`. An initial audit
note repeated an old mislocation of Muhammad at x~960 on line 5; direct
visual reading later corrected that note (see the latest section below).

### Rosette map: ground-truth label requires revision

Source review of `rosette_map.py` shows self-training/sequence harvesting,
DP assignment, inferred missing “ghost” verses, and page-boundary heuristics.
Its p604 training anchor assumes consecutive verse numbers from 1, although
the page contains surahs 112/113/114 and numbers restart twice. The DP selects
its cheapest terminal verse index rather than requiring the full expected
sequence. The “99.4% cross-validation” is not implemented in the committed
script; an independent held-out label set has not yet been located.
Zero tiling violations are a structural consistency check, not a measurement
of verse assignment accuracy. Treat these maps as inferred until independently
validated; do not rebuild or relabel pins silently.

## 2026-10-18 — rebuilt data, exact-rational bound, and checkpoint

### Rebuilt extraction result

The isolated v3 rebuild finished: **604 pages written, zero page errors**,
about 193 seconds on this CPU. Artifact report:
`tools/data/real_boxes_v3/_extraction_report.json` (source hashes included).
There are 4,932 red-class components before analysis eligibility filtering;
587 eligible pages contribute **4,582** components. Fifty-eight pages have
different red-component counts from the historical extraction. The repaired
connected components reduce raw slot fragmentation substantially.

Current v3 score: column **3,271**, nominal-reflected neighbor **277**,
intersection **209**, union **3,339 / 4,582 = 72.8721%**. Twenty thousand
page-slot replicates give mean union **1,201.24265** (~26.2166%), SD 37.1107
(~0.81 percentage points), zero exceedances. Analytic union expectation is
1,201.882038; the simulation difference is within ordinary MC uncertainty.
The independent analytic column mean is **1,080.763019**. Hoeffding log10
upper bound is **-90.632557** for the column-only statistic.

The scan inventory (`audit_integrity.json`, optional scan hashes included)
also found 16 images at 1024x1679, p333 at 1024x1692, and **p489 at 1013x1680**,
in addition to p1's different height. The versioned alignment statistic uses
nominal 1024px reflection, not independently registered physical sheet edges.
This does not affect the column-only probability proof; exact physical mirror
claims need image registration and per-page dimensions.

### Exact per-page distributions: much stronger proof without extrapolation

`exact_column.py` computes each page's column-score distribution exactly.
For one x-bin, m slots occupy lines with counts m_l. For j>0 selections:

- A_j = sum_l C(m_l,j) selections occupy only one line (column score 0);
- C(m,j)-A_j selections occupy multiple lines (all j components align).

The bin polynomial is therefore

    1 + sum_{j>=1} z^j [ A_j + (C(m,j)-A_j) y^j ].

Multiplying over bins and extracting coefficient z^k y^a gives the integer
number of k-slot subsets with column score a. Divide by C(S,k) for the exact
page PMF. This handles dependencies among bins; it does NOT approximate their
occupancies as independent. Exhaustive tiny-subset tests check the entire PMF.
Every actual page's PMF mean also agrees with the independent hypergeometric
first-moment formula.

Under the independent-page slot null, for any integer b>1, Markov gives

    P(sum X_p >= 3271) <= b^(-3271) product_p E[b^(X_p)].

All coefficients, MGFs and the final bound are exact integers/Fractions.
The four bases 2,3,4,8 give log10 upper bounds -514.162, -672.914,
**-725.857534**, -688.475. Base 4 gives an exact rational bound approximately
**1.39 x 10^-726**, conservatively **below 2 x 10^-726**. The historical
session log describes individual-word binomial tails without justified
independence; the new number is an independently checkable mathematical
upper bound under an explicit model. Choosing the smallest valid bound on
the SAME event does not require a multiple-test correction; interpreting a
data-selected alignment statistic as a global discovery still does.

`tools/data/audit_exact_columns.json` stores all page subset-count arrays,
exact bound numerators/denominators in hexadecimal, parameters and hashes.
Hex avoids Python's decimal-digit string limit on these large integers.
`verify_cpu.py` reconstructs the proof, checks exact integer coefficients
and rational bounds, and cross-checks each mean independently.

**Limits:** raw component slots are not linguistic word slots. The null does
not preserve word width, morphology, text order or calligrapher decisions.
An extremely small bound under this model does not eliminate other natural
models or prove supernatural causation. This scientific limitation remains
even when the probability calculation is mathematically rigorous.

### Additional repairs and qualification

- The original token map has **8,856 reversed x intervals**. Writers now
  use min/max bounds, not reversed RTL endpoint ordering. Letter fitting now
  filters empty normalized tokens to match token-map indices. Historical
  width training and token maps have NOT been silently regenerated.
- Rosette alignment now consumes the full expected sequence and charges
  missing suffix verses; its banded DP cost is checked against independent
  exhaustive path search. The invalid consecutive-number p604 training
  anchor was removed. These repairs do not validate the old inferred map.
- The source's fixed y>=110 rosette extraction window excluded first-line
  rosettes; the subsequent versioned rebuild is recorded below.
- `mark_identity.py` now defaults to semantic hypotheses, supports an explicit
  output path, resets carry state across omitted pages, and does not assign
  a whole cross-block family from its first block. Old tint exploration is
  explicit. A count match remains an identity hypothesis, not ground truth.
- The phrase census formerly selected the longest colored run anywhere in
  several bands, even outside its own predicted phrase window. It now clips
  to that window and marks output exploratory; cross-page phrases are not
  silently sampled on just one page. It cannot prove unconditional marking.
- The old 19er script still mixed raw/normalized token indices despite the
  historical handoff saying this was fixed. It is replaced by a purely
  descriptive semantic-pin inspection with explicit token IDs and unknowns.
- Run-pair census now uses carried runs' actual pages and checks slot capacity.
  Mag: 67,335 vs mean ~54,735; cri: 24,111 vs ~14,543 (2,000 reps). These are
  component-layout tests, not word-pair proof.
- Shape k-means avoids an N x K x feature tensor (~1.6GB), uses squared-norm
  matrix distances, retains only one page image at a time and compresses new
  feature archives. Direct-distance fixtures verify the numerical assignments.
- Archived semantic shape accuracy remains unverified. The historical c3
  distance cutoff of 55 was ineffective for nonnegative sum-one features
  (Euclidean distance <=sqrt(2)); manual cluster names cannot certify words.
- The older `pair_census.py`/Farrin result depends on an untracked feature
  archive, stale surah anchors and incorrectly subset-indexed shape labels.
  Its positive/negative structure verdicts are not certified by this audit.
- Failed OCR/width algorithms, particularly with these bugs, do not prove a
  mathematical impossibility of recovering word geometry. Older “kashida
  impossibility proven three ways” wording is unsupported.

### Reproduction and verification at this checkpoint

CPU-only minimal environment: Python 3.12.3, NumPy 2.5.4, SciPy 1.18.1,
Pillow 13.0.0, pinned in `requirements-audit.txt`. No GPU/API is involved.

```bash
. .venv/bin/activate
python tools/verify_cpu.py
python tools/exact_column.py
python tools/real_stats.py 20000 --output logs/global-reproduction.json
# independent scan rebuild, about three minutes on the audit machine
setsid .venv/bin/python tools/real_extract.py 1 604 --output-directory logs/rebuilt-components > logs/rebuild.log 2>&1 < /dev/null &
# after extraction completes:
python tools/real_stats.py 20000 --data logs/rebuilt-components --output logs/rebuilt-global.json
# optional full deterministic replay of all saved global nulls:
setsid .venv/bin/python tools/verify_cpu.py --full > logs/verification-full.log 2>&1 < /dev/null &
```

CLI `real_stats.py` now defaults to **v3**. To reproduce historical-data audit
artifacts (`audit_global.json`, facing/leaf/shifted/line-null), explicitly add
`--data tools/data/real_boxes` to the earlier commands. The within-line
historical null preserves counts on each observed line: exact E[column]
1,126.351745, E[union] 1,250.640878 (~27.05%), Hoeffding log10 bound -89.941942.

Verified so far: **28 independent tests pass**; six stored global simulations
fully replayed byte-for-byte in their score arrays; independent scalar flags,
input hashes and stored inference reproduce; exact-rational proof replay and
all per-page mean cross-checks pass. Logs: `logs/audit-verify-quick.log`,
`logs/audit-verify-full.log`. `git diff --check` passed. No commits made.

### Coverage and next-session handoff

**Verified narrow computational core:** alignment reference/batching, page
and line sampling, finite-MC summaries, exact first moments, exact column PMFs,
rational bounds, corpus form counting, component-labeling primitives and CPU
proof/replay interface. Full dataset extraction completed independently.

**Reviewed/repaired but NOT scientifically certified:** archived type labels,
semantic pins, word/phrase/run pair tests, rosette classifier/map, token-map
writers, width training/censuses, literature-matching heuristics. Several of
these have sensible conditional outputs but need independent annotation and
rebuilds before semantic/publication conclusions.

**Not comprehensively reviewed:** remaining exploration/crop/sign tools,
all article/PDF generation paths and detailed historical-source assertions.
All Python sources parse, but that is not a correctness certificate. Older
HTML/PDF exports remain historical and may contain superseded claims.

Next work, in priority order:

1. Build a held-out, independently read verse/word annotation set with source
   coordinates and ambiguity labels. Validate rosettes and semantic pins,
   including false-positive matches, not just matching counts.
2. Correct first-line rosette coverage and reading order within lines; rebuild
   maps into versioned destinations. Quantify assignment uncertainty rather
   than declaring sequence consistency “ground truth.”
3. Construct comparable word-/width-/line-/morphology-conditioned controls;
   distinguish annotation selection and typography from lexical alignment.
4. Audit/rebuild remaining literature and phrase completeness claims. Address
   the corrected positive crimson identity results without cherry-picking.
5. Finish archive/tool review and regenerate a current publication only after
   those semantics and causal limitations are incorporated.

Start a new session by reading this final section, README, and git status.
Preserve the baseline user work listed above. The internal agent
configuration file (not published) was not edited.

## 2026-10-18 — latest checkpoint: independent images and rebuilt semantics

This section supersedes earlier work-queue entries about first-line rosettes,
reading order, and the old semantic input set. The primary component proof
is unchanged; upstream semantic work has advanced substantially.

### Independent p422 transcription corrects the showcase premise

I read the full displayed p422 image independently of the previous notes.
`audit_manual_page422.json` records all 18 red-class components, their words,
verse references, source-box IDs, coordinates and image hash. It gives:

- **16 Allah forms overall:** 15 standalone الله and one بالله;
- the narrow middle bin contains **11 Allah forms plus هو**, total 12;
- Muhammad is on printed line 12, not printed line 5;
- the archived shape label calls the Hu component `rabbi`.

An initial audit note repeated the old mistaken Muhammad location at x~960
on line 5. That was corrected after direct image reading: that component
really is Allah. The actual shape-label counterexample is Hu/Rabbi. These
corrections are recorded explicitly rather than treating older visual notes
as ground truth.

Consequently the literal **“12-of-16 Allah column plus Hu”** premise is not
reproduced in this scan under the stated component/center-bin measurement.
The actual 12-component column includes Hu. Exact occupancy arithmetic on
12 selected components does not validate that semantic 12-of-16 claim.
`showcase_audit.py` now includes this independent census and uses the same
32-bin clipping convention for 30px fixed-page calculations.

### Rosette fixes independently checked against p567

`audit_manual_rosettes.json` records a full visual transcription of p567:
**69:35–69:52, then 70:1–70:10**, 28 localized rosettes. The old inferred
map incorrectly extended the page through 70:11. On these 28 locations,
only **12 historical assignments match**, including two missing first-row
markers. This is a concrete counterexample to the old ground-truth label,
not a population accuracy estimate.

Repairs and versioned rebuilds:

1. Render PNG alpha on white and include the full image height. The full-height
   v2 detector finds **6,229 rosettes**, exactly the encoded corpus excluding
   Fatiha's seven verses. Equal totals alone do not prove correct detection.
2. Keep small zero dots: independent p567 inspection found zero components
   of 8–9 pixels in printed 40, 50 and 10, rejected by the old 10px cutoff.
   The v3 threshold is 5px; it retains 12,301 digit crops vs v2's 12,270.
3. Group slight y-jitter within rows and read right-to-left. Raw `(cy,-cx)`
   sorting wrongly ordered multiple rosettes on the same printed line.
4. Remove invalid consecutive-number training anchors at p567 and p604,
   where verse numbering restarts mid-page. Require global alignment to
   consume both full sequences, including charged missing suffixes.
5. Page spans use canonical verse order; missing-verse `cy=-1` sentinels
   cannot become first verses merely because of a geometric sort.

The rebuilt map assigns all **6,229** detected rosettes without ghost verses;
**6,101 decoded numbers agree** with sequence assignments. That agreement
is not held-out classifier accuracy. On the independent p567 transcription,
the repaired map matches **28/28 locations and labels**, and digit counts
match **28/28** (v2: 25/28). This remains a limited, deliberately inspected
page, not a random validation sample or a 99.4% CV claim.

Commands (CPU, isolated outputs):

```bash
python tools/rosette_digits.py --output-directory tools/data/rosettes_v3
OPENBLAS_NUM_THREADS=1 python tools/rosette_map.py --digits tools/data/rosettes_v3/rosette_digits.npz --boxes tools/data/real_boxes_v3 --output-directory tools/data/rosette_map_v3
python tools/verify_rosette_labels.py --sequence tools/data/rosette_map_v3/rosette_seq.npz --detections tools/data/rosettes_v3/rosette_digits.json --output tools/data/audit_rosette_labels_v3.json
```

Use `setsid` and logs for long runs. `--min-digit-pixels 10` reproduces the
v2 extraction threshold. These sources and glyph artifacts require no GPU.

### Basmala and pin defects found during the rebuild

The committed old basmala detector found **zero** bands on these scans; its
B<100 rule and 15-consecutive-dense-row requirement did not match the magenta
basmala strokes. It also did not reproduce the schema of its cached 111-band
artifact. A repaired detector finds **112 geometric candidates in 112 inferred
surah-head intervals**, using long colored horizontal strokes. These are
candidates, not independently transcribed basmala labels.

`mark_identity.py` constructed a basmala exclusion set but **never applied
it**. That is now applied to the per-band run cloud. Another RTL bug merged
right/left run pieces into reversed inner bounds instead of their union.
There are **78 reversed intervals in old semantic pins** (167 in broad mode),
and **zero** in the repaired semantic set. A small independent geometry test
checks the corrected merge. Pin extraction now accepts explicit map, rosette,
box and basmala versions, and reports their hashes. Analysis loaders follow
that component-version metadata instead of silently reverting to old bands.

The repaired pipeline produces **3,807 unique token pin hypotheses** in 5,936
segments: mag 1,480, cri 2,327. Corrected coordinates and maps do not make
count matching a proof of word identity. For example the la-ilaha family
table has 18 marked hypotheses, 10 unknown, one no-run/unmarked hypothesis,
one cross-block case; it does not reproduce a verified 30/30 complete marking
census. These outcomes cannot settle selection circularity without pixels/
independent word labels.

```bash
python tools/find_basmala.py --output tools/data/basmala_bands_v3.json
python tools/mark_identity.py --verse-map tools/data/rosette_map_v3/page_verse_map.json --rosettes tools/data/rosette_map_v3/rosette_seq.npz --boxes tools/data/real_boxes_v3 --basmala tools/data/basmala_bands_v3.json --output tools/data/mark_identity_semantic_v3.json
```

### Recomputed conditional identity/mirror tests

All following runs use repaired v3 pin/run input metadata and 2,000
replicates. New artifacts carry source-pin, corpus and component-file hashes.

- Legacy 30px/112px cell definition: mag 75 same-word pairs vs label-null
  mean ~59.9 (MC upper-tail ~0.0405); cri 5,375 vs ~5,136.6 (~0.0225).
  These are exploratory unadjusted model tails, not semantic certainty.
- Physical-partition ~30px grain: cri **5,211 vs 4,677.89**, 0/2,000
  exceedances; mag 73 vs 56.584, MC ~0.0265. Several other crimson grains
  also exceed the global-label null. The old universal-negative verdict is
  untenable. The suite contains 26 dependent explorations; language, widths,
  page/surah frequencies and selected-label uncertainty remain confounders.
- Facing break bands: **288** eligible spreads, nominal-mirror hits **28
  vs 31.8515±5.518**; same-x hits **33 vs 30.9035±5.605**. No mirror excess.
- Janna/Nar: zero pair hits on 8/7 selected pins (very low power). Allah/Rab
  slot excess remains but disappears/reverses under pair-label permutation.
  The refrain test has **zero B-side pins** and is **untestable**, not evidence
  of absence.
- Run positions: mag 67,342 vs 54,527.5±338.8; cri 23,355 vs
  14,000.3±148.7. Layout excess is not a word-specific causal result.

`phrase_mirror_test.py` now uses exact linear-time counter formulas rather
than within-cell quadratic pair loops; page counts are grouped once rather
than rescanned for every replicate. Independent brute pair enumeration
checks duplicates, spread parity and self-mirrored center cells.

```bash
python tools/word_pair_census.py 2000 mark_identity_semantic_v3.json
python tools/grain_sweep.py 2000 --src mark_identity_semantic_v3.json --output tools/data/audit_grain_sweep_v3.json
python tools/phrase_mirror_test.py 2000 --src mark_identity_semantic_v3.json --output tools/data/audit_phrase_mirror_v3.json
python tools/page_turn_mirror.py 2000 --src mark_identity_semantic_v3.json --output tools/data/audit_page_turn_v3.json
python tools/run_pair_census.py 2000 --src mark_identity_semantic_v3.json --output tools/data/audit_run_pairs_v3.json
```

### Why individual aligned-word binomial tails are not justified

Take three slots: (line 0,x100), (line 1,x100), (line 0,x300). Choose two
uniformly. The aligned-word score is 2 for the first two slots together,
and 0 for either other subset. Thus P(X=0)=2/3, P(X=2)=1/3, P(X=1)=0.
Independent Bernoulli flags with the same mean would give Binomial(2,1/3),
including P(X=1)=4/9 and P(X=2)=1/9. Alignment flags share their partners
and are dependent. Mean agreement does not validate a binomial tail.

The exact page-PMF proof above handles this dependence; adding historical
per-type binomial “bits” does not. The original S4 log explicitly called its
tail binomial; an earlier audit description calling it Gaussian was imprecise
and is corrected here. Similarly the napkin expression, written
unambiguously as `(1/8.5)**(3.4*604)`, has log10 value **-1908.654706**.
That real-number arithmetic is correct, but its event/count assumptions and
human-construction interpretation are uncalibrated. Chained exponent notation
in older summaries was ambiguous.

### Page-probability products are not construction work estimates

For independent local page attempts with success probabilities p_i, the
probability that ONE blind attempt succeeds on every page is product p_i.
If successful pages can be retained while failed pages are retried, the
expected number of page attempts is instead sum_i 1/p_i (geometric waiting
times). For example p_i=0.1 on 604 independent pages gives first-try all-page
probability 10^-604 and expected local-retry work **6,040 page attempts**.

Those illustrative probabilities are not estimates for this mushaf. They
show why multiplying random page-failure probabilities does not establish
human/AI construction impossibility. Actual construction difficulty requires
a justified constraint/search model and measured or constructive evidence.

The historical surrogate calibration also needs repair before reuse:
`pack()` charges 10+GAP per token, while its CHAR_W budget subtracts 10 per
VERSE and GAP per CHARACTER. The consistent aggregate budget would charge
(10+GAP)*number_of_tokens before allocating character widths. Whole-verse
packing then adds page slack, so matching a page total alone does not validate
surrogate word positions. These archive results are not the current proof.

### Additional robustness and current verification status

The rebuilt v3 **within-line** null preserves each observed line's count:
10,000 replicates still have zero exceedances, mean union ~26.9018%; exact
E[column]=1,109.339561, E[union]=1,232.620644. Its column Hoeffding log10
bound is **-88.282976**. Thus the component excess is not explained just by
different per-line red-component counts, although language/width controls
are still absent.

Final checkpoint checks:

- **36 independent tests pass**; all 70 Python files parse.
- **Seven** global MC datasets fully replayed (prior six in
  `logs/audit-verify-full.log`; new v3 line-null in
  `logs/audit-verify-v3-line-full.log`).
- Exact integer distributions/rational bounds reconstruct, and all page
  means agree with the separate hypergeometric formulas.
- The CPU verifier also checks new semantic-result input hashes, observed
  word/grain/phrase counts, stored MC arithmetic and the 28 annotated rosettes.
- Latest scan-free verifier benchmark: **40.85s, 149,628 KiB max RSS** on
  this machine (~146 MiB); no GPU, scans, network or temporary feature cache.
- `git diff --check` passes. No commits or remote operations performed.

Exact rational proof values are compared as integers; approximate display
logarithms tolerate platform libm rounding. `.gitattributes` fixes LF line
endings for hashed text artifacts across checkout platforms. Degenerate
reference distributions now report undefined z as null; missing-side phrase
tests carry an explicit untestable status rather than a zero-effect verdict.

### Updated handoff and remaining scope

The global component calculation now has an explicit, independently tested
mathematical foundation, including the exact-rational bound. It does not
validate historical semantic labels or human/divine-causation claims.

Next session should:

1. Expand independent, representative word/verse annotation beyond the two
   deliberately inspected pages. Assess both missed and falsely assigned pins.
2. Validate phrase-family marking completeness against pixels; do not infer
   completeness or selection independence from count matching or broad bands.
3. Build word-/width-/morphology-/page-frequency-conditioned controls and
   registered physical-layout comparisons. Investigate the corrected crimson
   identity excess rather than presuming a universal null or a miracle.
4. Finish comprehensive review of remaining exploration/source/article code.
   Reconcile older generated HTML/PDFs and figures before a new publication.

Start with this section and current git status. The script index formerly
kept in `map.md` now lives in `tools/README.md` (`map.md` was retired at
open-sourcing). `requirements-audit.txt` is the minimal CPU environment. The
original user modifications to article work are preserved.

## 2026-10-18 — unit-consistent controls and final handoff for this pass

### The initial reference population is not a neutral word model

The new integrity diagnostic quantifies the preprocessing distinction:

- 4,582 observed merged red groups vs **123,218 raw reference components**;
- 4,038 observed boxes are exact raw boxes, 4,137 centers/lines occur in the
  raw pool, and 4,392 column/line cells occur there;
- the raw pool includes **4,796 gold-class components**;
- observed width quantiles (10/50/90%) are 46/68/100px, reference 9/50/116px.

The exact mathematical bound for that reference model remains correct. But
calling it a calibrated neutral WORD-placement probability would be unjustified:
the observations are merged, references include fragments/rosettes, and glyph
shape/width/language roles have not been modeled. This limitation is now stated
in the README, not hidden behind the tiny number.

### Closer controls retain the component-position association

`reference_controls.py` applies the same size filter to observations and
references where indicated: width **30–300px**, height **20–120px**. Removing
gold uses the same reference rule. In raw-observation controls, the observed
red components are a literal subset of exactly the reference sites: the
uniform-label null is a well-defined conditional component permutation.
These size-filtered sites still are not certified linguistic words.

All controls have 587 eligible pages and 5,000 replicates:

| comparison | observed n | observed union | reference union mean | raw-site subset? |
|---|---:|---:|---:|---|
| merged, common size filter, no gold | 4,115 | 76.4520% | 24.2110% | no |
| raw red vs all raw sites | 6,758 | 74.1048% | 38.4046% | yes |
| raw red, common size filter, no gold | 4,682 | **76.6766%** | **27.9436%** | yes |
| same raw size-filtered pool, per-line counts fixed | 4,682 | **76.6766%** | **29.0805%** | yes |

Thus the initial merging/fragment mismatch alone does not explain the
association. The controls change the populations, so these rates must not be
substituted for an Allah-word census or treated as independent replications.
They are exploratory model comparisons on the same printed artifact.

### Stronger exact proof on an actual reference subset

For the size-filtered non-gold raw-site control, **3,522 column-aligned
components** are observed; the exact uniform-label expectation is
**1,181.551667**. The same integer page-PMF method gives

    P(sum X_p >= 3522) <= 8^(-3522) product_p E[8^(X_p)].

The best of the four fixed bases 2/3/4/8 has log10 upper bound
**-814.074673**, conservatively **below 10^-814**. This is an exact-rational
upper bound under that conditional component-labeling model. It applies to
the **column-only statistic**, not directly to the 76.68% column-or-mirror
union. The independent per-line control also has a Hoeffding column bound
with log10 upper bound **-92.409662**.

Artifacts:

- `audit_reference_controls.json` — all four populations, observed and raw
  null scores, input hashes, analytic means and bounded-score inference;
- `audit_exact_columns_raw_wordlike.json` — complete integer distributions,
  exact rational bounds and the explicit reference preprocessing;
- the initial `audit_exact_columns.json` remains a separate baseline proof.

```bash
python tools/reference_controls.py 5000
python tools/exact_column.py --raw-wordlike
python tools/verify_cpu.py
```

The verifier reconstructs both rational proofs, checks their stated
conservative decimal bounds by exact integer comparison, independently scores
every control, and recomputes analytic expectations and saved MC inference.
All four control simulations were fully replayed in
`logs/audit-verify-controls-full.log`; combined with the previous seven,
**11 global component-null datasets** have been fully replayed. No extremely
rare tail is estimated from 5,000 simulations: the tiny bound is analytic.

### What this establishes and what remains

**Established computationally:** the explicit component statistics, their
conditional model distributions/bounds, and a strong color-position association
that survives these basic unit and line-count controls. Current checks:
**36 independent tests**, **71 syntax-parsed Python files**, two exact-rational
proof reconstructions, and 11 full global-null replays. Latest expanded
scan-free verifier measurement: **50.84s, 149,648 KiB max RSS** (~146 MiB)
on this CPU. Earlier 40.85s timing excluded the added controls.

**Still open:** fine width/height distributions, word identity and morphology,
verse-/line-edge roles, selection rules, image registration and independent
semantic annotation. A uniform component-color-label model is not a neutral
linguistic layout model or a model of a skilled calligrapher. Small conditional
model tails quantify neither human manufacture nor divine origin. Bounds for
different controls must not be multiplied into a combined miracle probability.

Next-session order:

1. Representative independent word/verse labels and false-pin audits, extending
   the deliberately inspected p422/p567 examples.
2. Width-/height-/edge-role-/language-conditioned controls; distinguish fixed
   vocabulary geometry, editorial marking and layout choices from word-specific
   alignment. Preserve the unit-consistency checks introduced here.
3. Independently verify phrase marking completeness and source interpretations.
4. Finish exploration/archive review, including surrogate calibration and
   legacy Farrin/shape indexing, then reconcile generated article/PDF outputs.

This is a completed substantial computational audit pass, not a certificate
for every exploratory script or semantic/historical claim. Start a new session
here, then read README/map and git status. All code/data changes remain local;
no commits, pushes or publication actions were requested or performed.

## 2026-10-18 — t2 working copy and audit snapshot (gpt-6.1-sol)

At the user's request, repository history through `bea87f3` and the complete
uncommitted project snapshot were copied from `~/v/tawafuq` into `~/v/t2`.
The original repository was read only. The existing t2 `AGENTS.md` was
preserved byte-for-byte and is excluded from the imported-work commit.
Local scans were copied for future independent reading and remain git-ignored.
The Python environment was recreated locally with the pinned audit dependencies.

Verification in t2: `python tools/verify_cpu.py` passed all 36 independent
tests, both exact-rational proof reconstructions, saved-data/hash checks and
the annotated rosette check. Log: `logs/import-verification.log`.
`git diff --check -- . ':!AGENTS.md'` passed. A checksum-based dry-run copy
confirmed project files match the source before this dated handoff addition.

Continuation: add fixed width/height-stratified raw-site label controls,
including per-line and geometric line-edge conditioning. These address the
next computational item in the prior handoff. Independent representative
word/verse annotation remains the highest-priority semantic validation task.

## 2026-10-18 — geometry-conditioned raw-site controls (gpt-6.1-sol)

Work continues in t2. Imported audit/article work was committed locally as
`8c86a87`, with the requested `(gpt-6.1-sol)` note. The local instruction file
still differs from the inherited repository version; it has not been edited.

### Model and independent arithmetic

`geometry_controls.py` uses the same size-filtered, non-gold raw-component
population as the unit-consistent control: **76,375 reference sites, 4,682
red-class observations, 587 pages**. The observed sites are an actual subset
of these sites; no word identity or merged-observation substitution is used.
All five controls score the same 3,590-component union (76.6766%), with
3,522 column flags, 288 neighbor-mirror flags and 220 overlapping flags.

Each page is partitioned into disjoint strata. We retain the observed number
of red labels per stratum, then choose that many distinct sites uniformly.
Different strata/pages are independent. Width and height use inclusive box
dimensions and fixed zero-anchored 20px/10px bins; the fine control uses
10px/5px bins. Line conditioning adds the reconstructed line ID. Edge role
is a two-bit left/right mask: a box is within 60px of the corresponding
extreme of that line's size-filtered non-gold raw sites. These extremes are
geometric component boundaries, **not certified word/verse boundaries**.

For a specified selected site in stratum g, condition its stratum from
(S_g,k_g) to (S_g-1,k_g-1). For each stratum h with m_h potential other-line
column partners, the probability of avoiding them is
`C(S'_h-m_h,k'_h)/C(S'_h,k'_h)`. Multiply these avoidance probabilities over
independent strata. Mirror-partner avoidance is an analogous product on
eligible adjacent pages. Column and neighbor avoidance involve different
pages, so they factor conditional on that site's inclusion. Weight each site
by k_g/S_g and sum to obtain column, mirror, intersection and union means.
This computes model first moments without assuming aligned flags independent.

Independent small-case checks enumerate all allowed stratum subsets and
score them by scalar pair enumeration. They cover duplicates, empty/full
strata, missing pages and all spread conventions. Other checks reduce the
formula to the prior page/line hypergeometric means, check sampler subset
frequencies and fixed counts, and cover fully deterministic conditioning.

### Results: larger reference means, residual column association

All five cases use 5,000 replicates, seed 3, batch size 128. The reference
rates below are **analytic means**; simulated means agree within Monte Carlo
uncertainty. The observed union rate is 76.6766% throughout.

| fixed counts within each page | analytic reference union | selected labels fixed at their sites | selected labels free to move |
|---|---:|---:|---:|
| width 20px × height 10px | 38.8234% | 321 (6.86%) | 4,361 |
| line + width/height | 64.2278% | 3,340 (71.34%) | 1,342 |
| edge role + width/height | 48.5633% | 1,215 (25.95%) | 3,467 |
| line + edge role + width/height | **69.4348%** | **3,911 (83.53%)** | **771** |
| fine width 10px × height 5px | 51.7137% | 1,447 (30.91%) | 3,235 |

Thus the 27.94% uniform-label reference is sensitive to conditioning on
component geometry. Tighter conditioning also retains many original labels:
the line+edge+size case has just **737 mixed strata, 1,630 mixed reference
sites**, and 771 randomizable red labels. This is a real restriction of the
conditional model, not five independent replications or proof that size/line
alone causally explains the difference.

Every case has zero column and union exceedances. For each such statistic,
the plus-one Monte Carlo summary is 1/5,001 (~0.000200), with a one-sided
95% binomial upper limit ~0.000599 on the model-tail probability. These are
finite-simulation summaries, **not p=0 or extreme-tail estimates**. Analytic
column Hoeffding log10 upper bounds are -58.5526, -6.4773, -32.0224, -2.1339
and -25.3916 in table order; these use conservative [0,k_page] ranges and
are not the old exact-PMF bounds for a different null.

The tight line+edge+size model has E[column]=3,174.4583, E[union]=3,250.9375.
The union residual is **339.0625 components / 7.2418 percentage points**.
Its **neighbor-mirror** score is 288 vs exact mean 279.8333 (simulated
279.681±7.197); 718/5,000 exceedances, plus-one upper-tail ~0.14377.
The residual column/union association therefore must not be described as a
significant mirror-specific discovery under this control. The statistics
and controls share data; their tails must not be multiplied.

### Reproduction, interpretation and handoff

```bash
. .venv/bin/activate
python tools/geometry_controls.py 5000
python tools/geometry_controls.py --verify tools/data/audit_geometry_controls.json --full
python tools/verify_cpu.py
```

The versioned artifact `tools/data/audit_geometry_controls.json` records all
raw null scores, hashes, fixed geometry parameters, analytic means, finite-MC
summaries and degeneracy diagnostics. Full replay of these five simulations
is also available through `verify_cpu.py --full`; the quick verifier checks
their scalar observed scores, strata, means and stored inference.

These are still image-component controls. Coarse size matching is not fixed
morphology, and box dimensions themselves can depend on ink extraction and
lexical identity. Conditioning on line/edge/size can retain part of the
layout being studied. Neither the residual nor the reduced gap identifies
editorial selection, typography, textual causes or divine/human manufacture.

Next work remains: independent representative word/verse and false-pin
annotation; phrase-family completeness against pixels; finer linguistic
controls and registered physical layouts. The new model comparisons give a
more informative baseline without replacing those semantic validation tasks.

Verification at this checkpoint: **41 tests pass**, all **73 Python sources
parse**, both prior exact-rational proofs reconstruct, and the expanded
scan-free verifier completes successfully. All five new 5,000-replicate
simulations were replayed exactly. Logs: `logs/geometry-controls.log`,
`logs/geometry-verification-full.log`, `logs/geometry-verification-cpu.log`.
The staged work passes `git diff --cached --check`.

## 2026-10-18 — representative semantic reading and GPU OCR (gpt-6.1-sol)

The user requested further verification and suggested GPU Arabic OCR. Work
below replaces the vague need for future annotation with a concrete initial
validation set and a functioning exact-corpus/OCR alignment experiment.

### Independently selected pages, exact text, and actual ink

Before inspecting predictions, `semantic_validation.py` selected one page
from each fixed range 1–100, 101–200, 201–300, 301–400, 401–500, 501–604.
Selection minimizes SHA256(`seed:page`) using the saved seed. Six existing
rosette-training anchor pages and previously annotated p567 were excluded.
The resulting pages are **15, 148, 276, 365, 412, 513**. This is a stratified
sample of the remaining pages, not a selection of the most aligned examples.

I read all six unlabelled scans before opening their predicted semantic
pins/maps, then checked their complete verse texts against the Quran corpus.
`audit_manual_semantic_sample.json` records image hashes, all Allah-form
locations, verse references, within-verse occurrence numbers, and localized
verse-end labels. Review rectangles surround divine-name ink cores; they are
approximate localization windows, not independently traced word boundaries.
This is one AI reader. Another reader could strengthen it, but the work is
not blocked on recruiting one.

| sampled page | independently read complete verses | Allah forms |
|---|---|---:|
| 15 | 2:102–105 | 4 |
| 148 | 6:152–157 | 2 |
| 276 | 16:88–93 | 7 |
| 365 | 25:68–77 | 5 |
| 412 | 31:20–28 | 13 |
| 513 | 48:24–28 | 7 |

**All 38 corpus occurrences are visibly colored**, independently confirmed
by colored pixels within their localized review windows. Both historical
and repaired rosette maps agree with **40/40** independently read endpoints.
These six pages support genuine lexical marking and alignment, rather than
only an anonymous-component effect. They do not establish whole-corpus
marking completeness or the accuracy of every pin/word family.

Using pixel-refined centers within the manual windows and distinct text rows:

- the existing fixed-origin 30px bin score flags **33/38** names (86.84%);
- shifting the bin origin by 15px flags **35/38** (92.11%);
- a direct center-distance rule, partner on another row within **15px**,
  flags **36/38** (94.74%); a 30px distance threshold gives the same count.

These are descriptive results on this sample, not p-values. All definitions
are reported: p365 has centers close to a fixed-bin boundary, illustrating
why visible closeness and sharing an arbitrary bin are different questions.
Manual localization uncertainty also matters near bin edges.

### Pin validation reveals errors hidden by count matching

The v3 file correctly locates **28/38** names, with **28/28** correct
name-labelled predictions on these pages. That precision statement is
restricted to predictions labelled as Allah forms, not all semantic pins.
Two other labels are demonstrably wrong at known name sites:

- p412, 31:25: the pin labelled **الحمد** sits on the visible **لله**;
- p513, 48:24: a pin labelled **ايديهم** spans the colored multiword phrase
  containing **الله**, not that token's actual location on the previous row.

Three visibly colored Allah forms also occur in the old `black` lists:
31:23, 31:25 (لله), and 48:24. Missing detected runs had been interpreted too
strongly. The exact text is not in doubt; the text-to-ink association was.

Two concrete implementation defects were repaired:

1. The semantic candidate set omitted genuine prefixed forms such as
   والله and بالله. It now shares the census's explicit genuine-form set,
   retaining false-friend exclusions.
2. A run deficit could silently pass: `merge_split_runs()` returned a short
   list unchanged, and `zip()` discarded unmatched candidate tokens while
   `match_class()` reported `full`. Deficits now return `amb`, never full.

Further, new extraction calls classify zero detected runs as
`no_detected_run`, export `unlocated` token lists, and leave marking
completeness unknown. They no longer manufacture black/unmarked verdicts
from a detector failure. The legacy `black` field remains empty in the v4
rebuild for schema compatibility; historical files are preserved.

The versioned full rebuild is `mark_identity_semantic_v4.json`. On the same
development sample it correctly locates **29/38** names with **29/29** correct
name-labelled predictions, and eliminates the false ايديهم assignment.
The الحمد/lله misassignment remains, exposing a faulty assumed family-color
rule. Nine names still lack correct pins. This is a diagnostic post-repair
comparison, **not a new held-out accuracy estimate**: the sample helped find
these defects. New evaluation pages are needed before generalizing a repaired
automatic semantic pipeline. Earlier v3 conditional statistics are not
silently recomputed on the changed pin population.

### Two local GPU Arabic OCR engines, measured on the same sample

Installed into isolated `.venv/ocr` so pinned CPU audit dependencies are
unchanged. The supplied A6000 GPU was selected by UUID; the pilot coexisted
with training. No training process was stopped. Model caches and run logs
are under `logs/`; scans were processed locally. Weights are not in git.
Raw derived OCR outputs, engine versions and model-file hashes are retained
in `ocr_sample_v1/` (Surya) and `ocr_easy_sample_v1/` (EasyOCR).

| engine | normalized character errors | normalized word errors | independently localized name cores |
|---|---:|---:|---:|
| Surya 0.17.0, boxed OCR | 250/3,189 = **7.84%** | 320/758 = 42.22% | **2/38** |
| EasyOCR 1.7.2, Arabic+English | 354/3,189 = **11.10%** | 443/758 = 58.44% | **27/38** |

Normalization removes diacritics, tatweel, digits and punctuation and applies
the audited Arabic normalization. CER ignores whitespace. WER preserves
token boundaries: OCR often separates attached prefixes, increasing WER.
Neither metric is an estimate of errors in the underlying Quran text.
All 27 EasyOCR single-name candidates localize to known names in this sample;
the remaining 11 names are missed by that strict recognition/localization
criterion. Surya reads approximate line text better but its word boxes are
not reliable enough here. These are tested configurations, not a ranking of
every OCR model or proof that Arabic word geometry is unrecoverable.

Surya took ~101 seconds for the six-page warm-cache boxed run, peak allocated
GPU memory ~2.16 GB; EasyOCR ~17.3 seconds including model startup/download,
peak allocated ~1.66 GB. GPU sharing affects timings. The first Surya call
did not request word records; that diagnostic run is retained only in logs.
The scored version explicitly sets `return_words=True`. The CPU benchmark
rejects absent word records instead of reporting a misleading zero accuracy.

### Exact Quran + approximate OCR: a useful next-stage result

The user's exact-text point can be exploited without trusting OCR spelling.
`ocr_line_map.py` aligns normalized exact corpus characters to Surya's
approximate line readings. It retains **all minimum edit-cost paths** using
forward/backward dynamic programming. A word receives a stable text-line
assignment only if all possible nondeleted character assignments use that
one line and no optimal path can delete the entire word.

Results: **753/758** corpus words get stable line hypotheses. For the
independently localized names, **37/38 are assigned to the correct line**,
one remains ambiguous, and **none receives a wrong stable line**. Only name
lines were independently checked; the other word-line hypotheses are not
automatically certified. The original word x-coordinates are **not** inferred
or interpolated from character counts. Algorithmic optimal-path stability is
not a calibrated posterior probability.

This is a practical route forward: exact corpus identities, OCR-assisted line
boundaries, and independently validated image geometry. It addresses a real
upstream bottleneck instead of treating low-coverage pin output as absent ink.

### Reproduction and next steps

```bash
. .venv/bin/activate
python tools/semantic_validation.py --review logs/semantic-review
python tools/semantic_validation.py --analyze
python tools/semantic_validation.py --verify tools/data/audit_semantic_validation.json --scans
python tools/ocr_benchmark.py --verify
python tools/ocr_benchmark.py --source tools/data/ocr_easy_sample_v1 --output tools/data/audit_easyocr_arabic.json --verify
python tools/ocr_line_map.py --verify
python tools/verify_cpu.py
```

GPU regeneration uses `requirements-ocr.txt`, `.venv/ocr`, and
`CUDA_VISIBLE_DEVICES=<GPU UUID>` with `tools/arabic_ocr.py` or
`tools/arabic_ocr_easy.py`. Run long jobs with `setsid`; use an isolated
output destination and benchmark it before replacing a stored result.
Raw OCR source/weights/versions and exact corpus/annotation hashes travel
with the artifacts. CPU benchmark/proof checks need no OCR packages or GPU.

Next: use the exact-text line map and color-separated geometry to recover
word x-locations; validate on newly selected pages untouched by development.
Remove unvalidated family-color assumptions and audit phrase completeness.
Then construct word-/language-/layout-conditioned comparisons using the
validated identities. The present positive sample supports real named-word
alignment. It does not turn a random-slot probability into a probability of
human authorship, nor supply a calibrated probability for divine origin.

Checkpoint verification: **54 tests pass**, all **81 Python files parse**,
both prior exact-rational component proofs reconstruct, and the full quick
CPU verifier completes, including the saved semantic comparison, both OCR
benchmarks and exact-corpus line-map replay. The separate `--scans` check
also reproduces sample image hashes and localized ink measurements.
Logs: `logs/semantic-ocr-verification-cpu.log`,
`logs/semantic-verification-scans.log`, `logs/semantic-v4-rebuild.log`,
`logs/arabic-ocr-words.log`, `logs/easyocr-arabic.log`,
`logs/ocr-line-map.log`. `git diff --check` passes. No commit was made during
this continuation; the last existing commit remains `3a353f7`.

## 2026-10-18 — fresh-page OCR, actual word-region mapping and paid-service handoff

The user requested continued OCR work, permitted stopping slow training if
needed, and subsequently approved **up to $20 for paid OCR**. Both new local
jobs completed while sharing A6000 GPUs selected by UUID. Training did not
need to be stopped. Paid-service credentials were not exposed in this
session, so **no paid requests were sent and spending is $0**.

### New sample, read before OCR predictions

`ocr_heldout_sample.py` fixes seed
`t2-heldout-ocr-localization-v1-2026-10-18`, minimizes SHA256(seed:page) in
the same six page strata, and excludes the previous training anchors and
development sample. The resulting pages are **74, 128, 201, 342, 447, 529**.
I read the unlabelled full scans before generating their OCR predictions,
recording exact verse ranges and every Allah-form ink-core window. Exact
corpus comparison corrected the transcription of p74's prefixed **ولله**;
its rectangle intentionally surrounds the colored name core. All name
identities/counts agree with the corpus. This is one AI reader, with
approximate localization windows rather than traced word boundaries.

| page | independently read complete verses | Allah forms |
|---|---|---:|
| 74 | 3:187–194 | 4 |
| 128 | 6:9–18 | 3 |
| 201 | 9:94–99 | 11 |
| 342 | 23:18–27 | 2 |
| 447 | 37:52–76 | 2 |
| 529 | 54:28–49 | 0 |

`audit_manual_ocr_heldout.json` stores annotations and scan hashes. Unlike
the first sample, this sample does **not** independently localize every
verse endpoint. Full-page OCR needs no endpoint-based crop on these pages.
`heldout_semantics.py` independently measures pixels inside the manual
windows: **22/22 names are colored**, **16/22** share the original 30px
column bin with another name on a different row, and **19/22** have another
name on a different row within 15px horizontally. These are descriptive
sample measurements, not a chance-model test. Combined with the first
sample, 60/60 annotated corpus occurrences are colored; no whole-corpus
completeness claim follows.

The unchanged v4 semantic-pin rules locate **17/22 names correctly**, with
**17/17** accepted name-labelled predictions correct on this fresh sample.
This is a genuine out-of-development check for v4, not a new repair using
these pages. Five names still have no correct v4 pins. Other word families
remain unvalidated.

### OCR comparison and an important negative control

Both existing runners now accept `--manual`, as do the CPU benchmark and
line mapper; default first-sample replay is preserved. Raw results and
weight/version metadata are retained separately in `ocr_heldout_surya_v1/`
and `ocr_heldout_easy_v1/`.

| method, fresh sample | normalized character errors | names with correct word-region centers |
|---|---:|---:|
| Surya 0.17.0 raw | 226/3,320 = **6.81%** | **3/22** |
| EasyOCR 1.7.2 raw single-name regions | 374/3,320 = **11.27%** | **14/22** |
| exact corpus + exclusive EasyOCR region mapping | same raw OCR input | **17/22**, 17 accepted, 5 abstentions |

Surya raw WER is 253/781 = 32.39%; EasyOCR is 422/781 = 54.03%, under the
same normalization/token-boundary policy as the first benchmark. The raw
EasyOCR benchmark has **14 name candidates, all correctly localized**.
The word mapper evaluates **exact token identity plus position**, a
stronger criterion than matching a raw name region to any annotated name.

**p529 is a useful negative control:** its exact text and independent image
reading contain no Allah forms. EasyOCR emits no single-name candidates
there, but Surya inserts **five** Allah-form word records into three line
readings. Across the fresh sample Surya emits 32 single-name candidates;
29 have centers outside every annotated name core. Some are extra or
duplicated readings and many carry repeated broad, implausible boxes.
Surya's lower average CER therefore does not make its word coordinates or
individual name readings trustworthy. The inserted p529 forms are visible
in the raw line text, not only an artifact of the scoring code.

The exact-corpus/Surya line mapper gives **776/781 stable word-line
hypotheses**, and **22/22 annotated names on the correct line**, with no
unstable or wrong stable name line. Only the names' lines were independently
checked; the remaining stable assignments are hypotheses.

### Exact text now gets real x-location hypotheses

`ocr_word_map.py` attaches exact corpus words to actual EasyOCR regions,
using the existing all-minimum-edit-path calculation. For each word it
collects every candidate region on every optimal path. Acceptance requires:

1. no optimal path can delete the entire word;
2. none of its candidate regions can belong to another corpus word on any
   optimal path;
3. detector boxes are valid and the candidate boxes have overlapping
   vertical intervals.

Single regions retain their detected boxes. Exclusive split-prefix regions
on the same row use the union of their detected boxes. Multiword regions
are never apportioned by character count, and color-family rules are not
used. This is **conditional edit-model exclusivity**, not calibrated
confidence or independent certification of complete word boundaries.

On the development sample this locates **520/758** word hypotheses and
**22/38** correct named-token positions, with 22 accepted name predictions.
The rule was developed there before new-page OCR predictions. On the fresh
sample it locates **525/781** word hypotheses and **17/22** correct named-token
positions, with 17 accepted and no wrong accepted name position. Most
non-name identities and all full word boundaries remain unchecked.

The v4 and OCR methods cover different omissions: 13 correct names overlap,
and their **retrospective union covers 21/22**. This is a diagnostic union,
not a tested automatic fusion policy. An agreement/abstention/fallback rule
needs to be specified and evaluated separately before a fused accuracy
claim. These pages are now exposed for future development; further tuning
requires another untouched evaluation sample.

### Paid OCR: recommendation, cost and remaining access

Recommended first trial: **Google Cloud Vision `DOCUMENT_TEXT_DETECTION`**.
It supports Arabic and supplies structured word/symbol geometry. Alternative:
**Azure Document Intelligence `prebuilt-read`**, which also supplies word
polygons. These are candidates for this Quran layout, not established
Quran-specific winners. The decisive benchmark is correct token geometry
and false detections, alongside normalized CER; exact Quran spelling is
already available. Provider Arabic support does not establish accuracy on
fully vocalized Ottoman-style Quran text.

Official references checked in this session:

- https://cloud.google.com/vision/docs/ocr
- https://cloud.google.com/vision/docs/languages
- https://cloud.google.com/vision/pricing
- https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/prebuilt/read?view=doc-intel-4.0.0

Google's posted document-text price is **$1.50/1,000 images** after the first
1,000 free monthly units, with prorated usage. Ignoring any free allowance,
six requests estimate **$0.009**, and one request for each of 604 pages
estimates **$0.906**, excluding other features/services/taxes. These are
planning estimates, not charges incurred. The $20 allowance is ample for
a small comparison.

`arabic_ocr_cloud.py` is prepared for Google Vision: PNGs composited on
white, raw JSON retained, real word boxes converted into the existing
benchmark schema, one request per uncached page, no automatic retries,
page/planning-budget checks and cache reuse. No reference Quran text is
sent in the request. Unit tests cover omitted zero-valued coordinates,
line breaks and retaining separate word geometry. Live authentication and
service quality are **not tested** until credentials are supplied.

Access options: `GOOGLE_CLOUD_VISION_API_KEY` in the runner's environment,
or a service-account file via `--credentials`. Keep a local credential file
under gitignored `logs/`; do not commit it or paste its contents into chat.
The account must have billing/API access. Service-account authentication
additionally needs `google-auth` and `requests` in the environment used to
run the cloud client. No new cloud packages are needed for `--plan` or CPU
verification. Nothing outside the project was searched for credentials.

### Reproduction and next handoff

```bash
. .venv/bin/activate
python tools/ocr_heldout_sample.py --verify
python tools/heldout_semantics.py --verify --scans
python tools/ocr_word_map.py --verify
python tools/ocr_benchmark.py --source tools/data/ocr_heldout_easy_v1 --manual tools/data/audit_manual_ocr_heldout.json --output tools/data/audit_ocr_heldout_easy.json --verify
python tools/ocr_benchmark.py --source tools/data/ocr_heldout_surya_v1 --manual tools/data/audit_manual_ocr_heldout.json --output tools/data/audit_ocr_heldout_surya.json --verify
python tools/ocr_line_map.py --source tools/data/ocr_heldout_surya_v1 --manual tools/data/audit_manual_ocr_heldout.json --output tools/data/audit_ocr_heldout_line_map.json --verify
python tools/ocr_word_map.py --source tools/data/ocr_heldout_easy_v1 --manual tools/data/audit_manual_ocr_heldout.json --output tools/data/audit_ocr_heldout_word_map.json --verify
python tools/arabic_ocr_cloud.py --plan
python tools/verify_cpu.py
```

Cloud execution once access is configured (use `.venv/ocr` if installing
optional authentication dependencies):

```bash
python tools/arabic_ocr_cloud.py --credentials logs/google-vision-credentials.json
python tools/ocr_benchmark.py --source tools/data/ocr_heldout_google_v1 --manual tools/data/audit_manual_ocr_heldout.json --output tools/data/audit_ocr_heldout_google.json
python tools/ocr_word_map.py --source tools/data/ocr_heldout_google_v1 --manual tools/data/audit_manual_ocr_heldout.json --output tools/data/audit_ocr_heldout_google_word_map.json
```

Next: obtain service access and compare Google on these fixed pages; expand
boundary/non-name annotation; specify a fusion policy, then evaluate it on
another untouched sample. After geometry is validated, resume the linguistic
and layout-conditioned null work. Local run logs:
`logs/ocr-heldout-surya.log`, `logs/ocr-heldout-easy.log`,
`logs/ocr-heldout-verification-cpu.log`.

Checkpoint verification: **62 tests pass**, all **87 Python files parse**,
the complete quick CPU verifier replays both OCR samples and all prior
component/exact-rational checks, and the separate held-out `--scans` replay
reproduces image hashes and pixel measurements. `git diff --check` passes.
No commit was requested or made; existing work remains in the working tree.

## 2026-10-18 — Google credential supplied; live pilot blocked by billing

The user supplied a service-account credential file inside gitignored
`logs/`. Its contents were not printed or copied into source/artifacts.
Installed optional `google-auth==2.62.0` and `requests==2.34.2` into
`.venv/ocr`, using `uv pip install --python .venv/ocr/bin/python` because
these virtual environments do not contain pip. Versions are recorded in
`requirements-cloud-ocr.txt`.

Service-account authentication **succeeded**. The first six-page-pilot
request was rejected with HTTP 403 before any OCR result was returned. A
separate empty-image-list diagnostic established the precise provider
reason: **`BILLING_DISABLED`**. The provider says billing must be enabled
on the credential's project; recent enablement can take a few minutes to
propagate. No successful page requests or paid OCR artifacts exist from
this attempt. Expected completed-page OCR usage is zero; no billing receipt
was queried. The approved cap remains $20 and the six-page planning estimate
remains $0.009 before free allowance.

The cloud client now reports allowlisted provider reason codes rather than
only an opaque HTTP status. Account-specific error messages/metadata and
credentials are excluded from its error summary. A focused test checks this
alongside the existing raw-coordinate conversion tests.

**Action needed:** link a billing account to the credential's project in
the Google Cloud console, then retry the existing client with that same
local credential path. No change to the annotation sample or benchmark is
needed. API access/permissions beyond the billing check and actual Quran
OCR quality remain untested until a page succeeds. Logs:
`logs/cloud-ocr-auth-install.log`, `logs/ocr-heldout-google.log`.

## 2026-10-18 — Google OCR succeeds: 12-page comparison and mapper failure

After the user requested another attempt, Google accepted all six fixed
held-out pages. The original six-page development sample was then processed
with the same default document-OCR configuration. **12 successful page
requests**, no automatic retries, two isolated raw-response directories:
`ocr_heldout_google_v1/` and `ocr_sample_google_v1/`. The former billing
blocker is resolved. No local training was interrupted.

### Raw Google word locations outperform the tested local configurations

The existing unmodified benchmark compares OCR against exact Quran text
and manually recorded name-core windows. Only normalization removes
diacritics/punctuation; recognized spelling is not repaired before raw OCR
scoring. Google received page images, not expected Quran text. No language
hint or provider-specific accuracy tuning was used.

| sample / method | normalized character errors | raw single-name locations |
|---|---:|---:|
| development / Google | 140/3,189 = **4.39%** | **38/38**, 38 candidates |
| development / Surya | 250/3,189 = 7.84% | 2/38 |
| development / EasyOCR | 354/3,189 = 11.10% | 27/38 |
| fresh six pages / Google | 152/3,320 = **4.58%** | **22/22**, 22 candidates |
| fresh six pages / Surya | 226/3,320 = 6.81% | 3/22 |
| fresh six pages / EasyOCR | 374/3,320 = 11.27% | 14/22 |

Google's **60 single-name candidates all localize to the 60 annotated
names**, with no extra or duplicate name candidates in these samples and
none on the zero-name p529 control. This establishes excellent sampled
name-core localization for this configuration; it does not certify the
entire corpus, all words or full word boundaries. Raw-name scoring matches
to any name at a site; it does not itself assign within-verse token IDs.

Combined normalized CER is **292/6,509 = 4.49%**; normalized WER is
**311/1,539 = 20.21%**. Splitting prefixes, pause marks and verse-number
decorations contribute errors under the existing normalization. Google's
converted output has more than 15 region-lines on some pages, so these
provider paragraph/break groups should not be treated as certified physical
text rows. Word boxes remain the useful geometry source.

### The downstream exact-token mapper is not perfect

The unchanged `exclusive-all-optimal-ocr-region-v1` mapper accepts
**1,516/1,539** corpus word-location hypotheses (747/758 development,
769/781 fresh). For annotated names it accepts all 60, but only
**58/60** centers are correct: **37/38 development**, **21/22 fresh**.
Non-name word identities and boundaries are not independently scored.

Both failures are **mapper over-unions**, despite correct raw Google
Allah boxes:

- p365, 25:68, second Allah occurrence (`t=47022`): mapped box
  `[20,133,994,224]` spans nearly a full text row.
- p201, 9:99, fourth Allah occurrence (`t=25664`): mapped box
  `[91,1573,447,1662]` combines the correct raw name box
  `[362,1583,447,1662]` with a separate tiny OCR reading **مه** at
  `[91,1573,114,1595]`.

The issue is concrete: a word's candidate set is the **union over all
optimal paths**. An optional, partly inserted OCR fragment can have no
other possible corpus-word owner and still enter that union. A common
vertical overlap does not establish a contiguous word. Thus edit-path
exclusivity is weaker than a correct boundary/location guarantee. These
outcomes are retained; no rules were tuned to make the fresh-page score
perfect. A stricter mandatory-support/contiguity rule or a validated
raw-name fallback is a next development task requiring new evaluation
pages. Do not describe the 1,516 hypotheses as certified words or the
mapper as 100% accurate.

### Costs, preservation and replay

The two run metadata records each estimate $0.009 at the posted paid
rate: **$0.018 total for the 12 successful requests**, before monthly free
allowance/taxes. Actual billing was not queried; this is an estimate, not
a receipt. It is well within the approved $20 pilot cap. Aggregate API
response time across the 12 successful page calls was approximately
**6.72 seconds**, excluding authentication, image preparation, saving and
benchmarking. Model revision is not pinned by this managed API.

Raw provider JSON, converted word boxes, source/annotation hashes and
timings are saved; no credentials or image payloads are in these artifacts.
The credential stays under gitignored `logs/`. Four benchmark/map reports:

- `audit_ocr_google.json`, `audit_ocr_google_word_map.json`;
- `audit_ocr_heldout_google.json`, `audit_ocr_heldout_google_word_map.json`.

`verify_cpu.py` now replays conversion from each raw response and both
samples' benchmark/map results, including the two mapper failures. It
needs no service credentials, authentication packages, network or GPU.

```bash
. .venv/bin/activate
python tools/ocr_benchmark.py --source tools/data/ocr_heldout_google_v1 --manual tools/data/audit_manual_ocr_heldout.json --output tools/data/audit_ocr_heldout_google.json --verify
python tools/ocr_word_map.py --source tools/data/ocr_heldout_google_v1 --manual tools/data/audit_manual_ocr_heldout.json --output tools/data/audit_ocr_heldout_google_word_map.json --verify
python tools/ocr_benchmark.py --source tools/data/ocr_sample_google_v1 --output tools/data/audit_ocr_google.json --verify
python tools/ocr_word_map.py --source tools/data/ocr_sample_google_v1 --output tools/data/audit_ocr_google_word_map.json --verify
python tools/verify_cpu.py
```

Google is now the **best tested service/configuration here** for the measured
name geometry and normalized text error, rather than merely the recommended
first candidate. Azure has not been tested. Next: retain Google's raw
geometry, repair ambiguity/contiguity handling with a versioned mapper,
annotate non-name words and true boundaries, and evaluate on another
untouched sample before expanding accuracy claims or recomputing semantic
alignment statistics. Logs: `logs/ocr-heldout-google.log`,
`logs/ocr-sample-google.log`, `logs/google-ocr-verification-cpu.log`.

Checkpoint: **63 tests pass**, all **87 Python files parse**, complete quick
CPU verification succeeds including the four Google reports and raw-response
conversions, and `git diff --check` passes. The credential is confirmed
gitignored. No commit was requested or made.

## 2026-10-18 — mandatory-support mapper, fresh word validation and full OCR cache

The user authorized further OCR and continuation. No additional access is
needed: the configured Google service account works, and the approved $20
cap is ample. Work now addresses semantic/localization correctness rather
than treating raw OCR spelling or edit-path stability as ground truth.

### V2 repairs the logical cause of the two earlier over-unions

`ocr_word_map.py --method mandatory-v2` preserves the original `exclusive-v1`
default and its saved reports. It adds a **bidirectional all-optimal-path**
rule. Reverse the same unit-cost character alignment, treating OCR regions
as reference words and canonical Quran words as destination regions. An
OCR region is mandatory support for token i only if:

- no optimal path can wholly insert that region in the forward direction;
- all possible nondeleted associations of that region belong to token i.

Optional OCR fragments are excluded, even if token i is their only possible
owner when they happen to align. Accepted split-region unions must share
a vertical interval and cannot span the center of another nonempty detected
word. No character-length interpolation, color-family assumption or Quran
name-specific fallback is used. A mandatory region can still contain only
part of a printed word: the output explicitly says **support, not certified
complete boundary**. Algorithmic stability remains conditional on the edit
cost/order model, not a calibrated probability.

An independent exhaustive-path test enumerates tiny strings and both grouped
and character-split word/region partitions, checking mandatory ownership
against every optimal edit path. Other cases cover optional inserted
fragments, repeated alternatives, real split prefixes, intervening words and
multiword regions.

Both old name failures are repaired on exposed development data: v2 scores
**38/38** and **22/22** correct name locations, with **744/758** and
**770/781** generic word-support hypotheses. This is development performance,
not a fresh held-out estimate. The earlier v1 **58/60** result stays intact.

### Another six pages: frozen rule, pre-OCR reading, broader word labels

`word_validation_sample.py` uses seed
`t2-mandatory-word-boundary-v2-2026-10-18`, the same six fixed strata and
19 exclusions (training anchors and both exposed six-page samples). It
selects **26, 130, 286, 393, 462, 588**. The v2 function's source hash is
recorded in the sample and verified. The rule was frozen before these OCR
predictions and was not changed after evaluating them.

I read the unlabelled scans, recorded every scoped Allah-form occurrence,
and selected the second and fifth lexical words on physical Quran rows
3, 8 and 13, ignoring rosettes. These fixed positions sample both line
interiors and varied ink classes. One supplemental **اللهم** checks an
explicitly excluded operational census form; it is reported separately,
not described as an unrelated or non-divine word.

| page | evaluated complete-verse block | Allah forms | sampled word labels |
|---|---|---:|---:|
| 26 | 2:177–181 | 2 | 6 |
| 130 | 6:28–35 | 4 | 6 |
| 286 | 17:50–58 | 0 | 6 |
| 393 | 28:71–77 | 9 | 6 |
| 462 | 39:41–47 | 5 | 7, including supplemental اللهم |
| 588 | 83:27–36, upper block only | 0 | 2 |

p588 contains a surah ornament, an unencoded basmala and another surah below
the evaluated block. The pre-OCR scope crops it at y=670, before the ornament,
so no basmala Allah is mislabeled as a false positive. Missing sampled rows
8/13 in that scope are omitted. Full-page p588 is separately included in
the corpus cache; these are different image scopes, not interchangeable
requests.

`audit_manual_word_validation_v2.json` records original labels, scope,
image hashes and rule hash. The 33 sampled labels comprise 30 fixed-position
non-Allah tokens, two overlapping Allah labels and one supplemental اللهم.
This is one AI reader, not human double annotation or a random sample of
all individual corpus words.

Google raw OCR on this scoped sample: **103/3,066 = 3.36% CER**,
**120/718 = 16.71% WER**. All **20/20** annotated Allah-form sites have
correct raw-name boxes, but there are **21 raw name candidates**: the extra
is an Allah-labelled reading at **اللهم**, 39:46. Neither zero-name scoped
page produces a name candidate. Thus across all three samples raw Google
has **80 correctly localized target names among 81 raw name candidates**;
the earlier 60/60 no-extra result does not generalize to zero extras here.
This operational-census distinction is important, not merely a cosmetic
OCR spelling difference.

Both mapper versions get **20/20 exact name identities/locations** on the
new sample. V2 supplies **712/718** generic word-support hypotheses, v1
711/718. With the older development samples, v2 has **80/80** annotated
exact-name positions correct; only the latest 20 were untouched by v2
development.

### Annotation audit: original windows are preserved, not silently repaired

The initial pre-OCR ordinary-word labels were too coarse to be true ink-edge
ground truth. On those labels v2 scored **32/33 sampled centers** and
**14/33** nominal +/-12px horizontal-edge checks (non-Allah: 30/31 centers,
12/31 nominal edge checks). The sole center miss was my coordinate error:
17:57 word 15 **عذاب** had a window on neighboring **إن**, not the target
word. Other windows had generous or shifted margins inconsistent with a
12px edge test. These initial outcomes remain in
`audit_word_localization_v2.json`; they are not valid evidence that most
Google boundaries are wrong.

I then reread **every** sampled word using unlabelled row crops with
coordinate rulers (`--review logs/word-v2-review`), not just failed labels.
`adjudicate_word_sample.py` records manual whitespace partitions and measures
black/colored pixel extents inside them, independently of OCR geometry.
It saves a separate adjudicated annotation file and evaluation report, with
the original rectangles and source hash retained. This is post-OCR
adjudication by the same reader, **not a new blind accuracy estimate**.

Pixel contact at a horizontal partition edge makes the boundary uncertain:
overhanging diacritics/neighboring ink can prevent simple rectangular
ownership. Six sampled words are therefore **unscorable for boundaries**,
not counted as certified passes. For the adjudicated labels:

| method | all 33 sampled centers | fixed-position non-Allah centers | coarse horizontal edges |
|---|---:|---:|---|
| v1 | 32/33; one abstention | 29/30 | 26/27 evaluable; 6 uncertain |
| v2 | **33/33** | **30/30** | **26/27 evaluable; 6 uncertain** |

For non-Allah labels including the vocative: v2 **31/31 centers**, **24/25**
evaluable horizontal boundaries, six uncertain. The 30 fixed-position
non-Allah words alone have **24/24** evaluable boundaries and six uncertain.
The genuine remaining edge failure is **اللهم**: the OCR/support box is
`[778,1134,863,1211]`, while independently measured colored ink has horizontal
extent **[753,858]**. Its left edge misses about 25px even though the center
and exact token identity are correct. This directly demonstrates why
successful named-word centers do not certify complete word geometry.
V1 abstains on p393 **فيما**; v2 recovers its mandatory support. All outcomes,
including the uncertainty and vocative failure, are retained.

Artifacts: `ocr_word_validation_google_v2/`,
`audit_ocr_word_validation_google_v2.json`,
`audit_manual_word_validation_v2_adjudicated.json`,
`audit_word_localization_v2_adjudicated.json`, and the two older
`audit_ocr_*google_word_map_v2.json` development reports.

### Full-page OCR acquisition and budget

Raw OCR is reusable independently of subsequent mapper repairs. A full
604-scan cache was started, with full-image hashes/dimensions in
`google_corpus_manifest_v1.json`. Sixteen prior responses have exactly
matching full-page scopes and are reused through local relative symlinks;
the two cropped pages (p365 and p588) require new full-page calls. This
leaves **588 new requests**, estimated **$0.882** before free allowance.
The 18 scoped pilot calls estimate $0.027, so a completed full cache brings
the cumulative estimate to **$0.909**, within the approved $20 cap. Actual
billing is not queried.

`google_corpus_cache.py` prepares scopes/cache reuse and exports compact
derived word regions after completion. Large raw responses stay under
gitignored `logs/ocr-google-corpus-v1/`; the compact export is intended for
replayable downstream research. Full-page OCR includes ornament text and
unencoded basmalas and is **not** a full semantic annotation or certified
Quran token map. Final completion/inventory numbers follow below.

### Reproduction and remaining scientific work

```bash
. .venv/bin/activate
python tools/word_validation_sample.py --verify --scans
python tools/adjudicate_word_sample.py --verify --scans
python tools/word_localization_validation.py --verify
python tools/word_localization_validation.py --manual tools/data/audit_manual_word_validation_v2_adjudicated.json --output tools/data/audit_word_localization_v2_adjudicated.json --verify
python tools/google_corpus_cache.py --summarize
python tools/google_corpus_cache.py --verify --raw
python tools/verify_cpu.py
```

Next: exploit the cached corpus with exact verse text while explicitly
handling ornaments, unencoded basmalas, overlapping diacritics and split/
merged readings. Maintain localization-versus-boundary uncertainty; use
new ruled pre-OCR boundary annotations for another truly held-out check.
Then construct linguistic/width/line/layout-conditioned comparisons from
validated word geometry. No new miracle probability or authorship inference
is justified by this OCR improvement alone. No additional credentials or
hardware are currently required.

### Full-cache completion checkpoint

**604/604 full-page responses are now available**, with no missing pages:
**588 new requests + 16 reused matching responses**. Export
`tools/data/ocr_google_corpus_v1.json` contains **87,843 uncorrected service
regions** and **2,842 operational raw Allah-form candidates**. These are
OCR candidates including basmalas/ornaments and recognition errors, **not
a corrected corpus name census or 87,843 certified linguistic words**.
The fresh اللهم error already demonstrates why raw candidate totals cannot
be equated with canonical counts.

The compact export is about **7.9 MiB**; roughly **302 MiB** of full provider
responses remain in gitignored `logs/ocr-google-corpus-v1/`. The export
records every response hash, image hash, acquisition-metadata hash,
engine/options, request reuse and planning-cost arithmetic. A full local
`--verify --raw` replay passed: all 604 raw conversions and compact regions
agree, all region boxes fit their input image frames, and candidate counts
and image inventory reproduce. The compact artifact also verifies without
the raw cache, credentials, network or scans through `verify_cpu.py`.

Estimated cumulative OCR usage is **606 successful requests × $0.0015 =
$0.909**, before any free allowance/taxes. This comprises the 18 scoped
pilot calls plus 588 new full-page calls; the extra two scoped calls are
the cropped p365/p588 variants. This is not an invoice. No training
process was stopped and no additional GPU inference was needed.

Full acquisition log: `logs/ocr-google-corpus-v1.log`. Fresh mapper checks:
`logs/word-localization-validation-v2.log`,
`logs/word-localization-v2-adjudicated.log`. Verification:
`logs/word-v2-verification-cpu.log`,
`logs/word-v2-corpus-verification-cpu.log`. No extra paid OCR is needed to
replay or improve mapping on these cached scans.

Final verification at this checkpoint: **77 tests pass**, all **93 Python
files parse**, and the complete quick CPU verifier passes, including v1/v2
development comparisons, both original/adjudicated fresh evaluations and
the compact 604-page inventory. The separate `--scans` annotation checks
and full `--raw` 604-response replay also pass. `git diff --check` passes.
No commit was requested or made.

## 2026-10-18 — full OCR-to-corpus anchoring, independent scopes and remaining conflicts

This continuation uses the cached OCR only. **No additional paid requests,
downloads or GPU jobs** were needed; the cumulative service estimate remains
$0.909 before allowance/taxes. The new inference route does not read any
historical page-verse map, rosette assignment, semantic pin file or letter-width
model. Those old artifacts are not silently replaced.

### Matching exact text without assuming page identities

`ocr_corpus_map.py` builds a virtual reference of **77,881 tokens / 327,514
normalized characters**: the original 77,433 canonical token IDs are preserved,
and **448 synthetic tokens** represent the 112 unencoded surah-head basmalas.
Surah 1's encoded basmala is not added again; surah 9 has no added basmala.
Synthetic head tokens have `t=null`, `kind=surah_head_basmala` and a `surah:0`
reference. Embedded verse basmalas retain their normal canonical IDs.

There are **301,979 globally unique 20-character anchor strings** in that
reference. Each page's approximate OCR characters retrieve a bounded reference
window by unique-anchor coverage; no page number supplies a Quran location.
The working retrieval model requires 40 covered characters and a 20-character
advantage over disjoint alternatives, uses a span bound `2*OCR_length+128`,
64-character padding, and a maximum conditional edit rate of 0.30. These are
explicit heuristic settings, not calibrated probabilities.

Within the retrieved window, substring edit alignment allows a **free reference
prefix/suffix**, but every observed insertion still costs one. Forward and
backward dynamic programming retain all minimum-cost substring alignments.
A region supplies mandatory token support only if it cannot be wholly inserted
on an optimal path and all its possible reference owners are the same token.
Unique anchors must themselves be compatible with an optimal alignment.
Complete token spelling, physical boundaries and globally exhaustive retrieval
are not guaranteed by this conditional support rule.

The new vectorized edit-table recurrence is exact. For one row, if `u[j]`
omits the same-row insertion edge, then
`D[j] = j + min(D[0], min_{1<=k<=j}(u[k]-k))`. A cumulative minimum evaluates
the full left-neighbor closure without a Python character-pair loop. Tests
compare every cell with an independent scalar recurrence and enumerate all
reference substrings and all optimal edit paths on tiny examples, including
grouped words/regions, repeated text, noise and head-basmala token IDs. No new
numerical dependency or GPU is required.

### First independent six-page scope/name check

`corpus_map_validation.py` fixed a hash-selected sample, read before the new
corpus-map predictions: **11, 199, 239, 304, 402, 570**. It records complete
verse ranges and every scoped Allah-form name core, plus the separate Maryam
basmala name. Exact corpus comparison confirms **31 verse-name occurrences**.

| page | independently read verse range | verse names |
|---|---|---:|
| 11 | 2:77–83 | 6 |
| 199 | 9:80–86 | 9 |
| 239 | 12:38–43 | 5 |
| 304 | 19:1–11 | 0, plus one head-basmala name |
| 402 | 29:53–63 | 6 |
| 570 | 71:11–28 | 5 |

Unmasked v1 gets **31/31 fresh verse-name identities/centers correct**, and
**80/80** previously exposed development names. The Maryam basmala is assigned
to synthetic **19:0**, not a nearby verse name. However, v1's possible scope
envelope is exact on only **5/6 pages**: title text in p304's gold ornament
was wrongly attached to the preceding verse's **بعباده / ربه**, with boxes in
the title. Its ambiguous suffix also extends to 19:12. This is a real failure,
retained in `audit_ocr_corpus_map_v1.json` and its validation report.

Across all 604 pages, v1 yields a conditional window match on every page,
**76,273 verse-word support occurrences** and **47 canonical token IDs with
cross-page duplicate supports**. These are hypotheses, not 604 certified
page scopes or word boundaries. A successful retrieval status does not erase
the independently found title/edge failures.

### Image-derived gold masks: v2, then a genuinely fresh scope check

`ocr_ornament_bands.py` detects wide, vertically extended gold bands from
white-composited pixels, without textual/verse labels. At least 25% row-width
gold coverage, gaps <=16 rows and band height >=60px distinguish headers from
small verse rosettes. Color thresholds and image hashes are recorded.
It finds **114 band candidates on 99 pages**. These are extraction hypotheses,
not an independently certified census of surah ornaments. Synthetic tests
check headers, multiple small rosettes, row gaps and retaining red basmalas.

The v2 wrapper excludes **806 OCR regions** centered in those bands, preserving
original source-region IDs. This repairs the preceding-verse title assignments
on p304 and changes p604's false 111:5 prefix to the correct **112:1**. All
**111 checked verse-name centers** remain correct, but the first six pages
are exposed development for v2 after their title failure was inspected.

Another six unlabelled scans were read before masked-v2 predictions:
**160, 188, 272, 391, 427, 517**. Their fixed hash strata cover 101–579,
excluding earlier samples and the v1 scope-log ranges already displayed
(1–100 and 580–604). Two independently selected pages have gold headers.

| page | independently read full scope | v2 possible envelope |
|---|---|---|
| 160 | 7:82–87 | correct |
| 188 | 9:14–20 | correct |
| 272 | 16:55–64 | correct |
| 391 | 28:51–59 | correct |
| 427 | 34:1–7 | extends ambiguously to 34:8 |
| 517 | 50:1–15 | correct |

Thus **5/6 exact envelopes, 11/12 endpoints**, not perfect scope accuracy.
The extra 34:8 token **افتري** has possible support but **no accepted box**;
the analogous 19:12 **ييحيي** fringe also has no box. Possible ambiguity and
accepted word localization are different outputs and both are retained.

The two new basmala names are recognized with the correct synthetic owner,
but v2 abstains on their geometry: its intervening-region check also applied
to a **single** detector box. Overlapping Google boxes for a broken **بسم**
fragment put that fragment's center inside the Allah box. An individual box
cannot be a multi-region union, so this exposes a geometry-policy defect,
not loss of basmala identity or removal by the gold mask.

Masked v2 on all pages: **76,224 verse-word supports**, **76,217 unique
canonical tokens**, **302 head-basmala supports**, **2,679 verse-name supports**,
and **7 duplicate canonical IDs**. A full 604-page DP replay and a separate
full 604-scan gold-mask replay both reproduce these artifacts.

### Explicit post-hoc site policy, with a conflict and missing names retained

`ocr_corpus_sites.py` is a separate view, not an overwrite of v1/v2. It fixes
the single-box policy: one mandatory valid detector region can supply its
own box, even if a neighboring OCR box overlaps. Actual multi-region unions
keep the conservative v2 contiguity check. It also excludes support boxes
under **35px tall**, after seven duplicate examples exposed tiny verse-marker/
annotation readings as false word-site candidates. This threshold is a
post-hoc wordlike-site criterion, not a validated universal word-size rule;
small legitimate material can be excluded too.

The view retains **76,777 verse-word site hypotheses**, representing **76,776
unique canonical tokens**, plus **372 head-basmala supports**. It rescues 638
single-region supports and excludes 16 tiny boxes. There are **2,686 canonical
verse-name support hypotheses**; **111/111 exposed annotated names** remain
correct. The three annotated head-basmala name centers are now also located.
These post-hoc results are not additional held-out accuracy estimates or
proof of complete word boundaries. Exact OCR surface agreement is recorded
separately from inferred identity.

**One cross-page conflict remains:** token `t=40736`, **20:77 ولقد**, has
candidate boxes on both p315 and p316. Neither is silently selected or
merged. **Eleven expected scanned verse-name IDs lack usable support**:
3:148 والله; 4:37 الله; 7:164 الله; 9:116 الله; 10:18 الله; 11:92 الله;
27:26 الله; 39:3 لله; 48:9 بالله; 58:8 الله; 73:20 والله.
Candidate pages and full token IDs are stored in the site report. Missing
support does not mean absent text, black ink or unmarked words. Fatiha's
unscanned tokens are explicitly excluded from this missing-name list.

This is a practical, independently anchored corpus-word hypothesis set. It
still needs conflict/omission review and stronger word-boundary ground truth
before being treated as a certified linguistic reference population or used
for new causal/probability claims.

### Artifacts, replay and next work

- `audit_ocr_corpus_map_v1.json` — retained unmasked conditional map (~35 MiB).
- `audit_ocr_ornament_bands_v1.json` — image-derived band candidates.
- `audit_ocr_corpus_map_masked_v2.json` — retained masked map (~35 MiB).
- `audit_ocr_corpus_sites_v1.json` — post-hoc wordlike sites, one conflict,
  eleven missing-name hypotheses and exposed validation (~23 MiB).
- `audit_manual_corpus_map_sample_v1.json`, `audit_corpus_map_validation_v1.json`,
  `audit_corpus_map_masked_development_v2.json` — first fresh labels/checks.
- `audit_manual_ornament_scope_v2.json`, `audit_ornament_scope_validation_v2.json`
  — second fresh scope/basmala check, including failures/abstentions.

```bash
. .venv/bin/activate
python tools/ocr_corpus_map.py --verify
python tools/ocr_corpus_map.py --verify --full --ornaments tools/data/audit_ocr_ornament_bands_v1.json --output tools/data/audit_ocr_corpus_map_masked_v2.json
python tools/ocr_ornament_bands.py --verify
python tools/corpus_map_validation.py --verify-manual --scans
python tools/corpus_map_validation.py --verify
python tools/ornament_scope_validation.py --verify --scans
python tools/ocr_corpus_sites.py --verify
python tools/verify_cpu.py
```

The quick CPU verifier checks every stored token identity/support box and
summary, replays a fixed 12-page DP set per map, and reproduces all annotation
comparisons and the site view. `--full` also replays all pages; scan replay
of the gold bands is separate. Inference logs are `logs/ocr-corpus-map-v1.log`
and `logs/ocr-corpus-map-masked-v2.log`; full replay logs are
`logs/ocr-corpus-map-masked-v2-verification.log` and
`logs/ocr-ornament-bands-verification.log`.

Next: inspect the single duplicate and eleven missing names in the scans;
separate explicit page envelopes from ambiguous fringe characters; audit
ordinary-word and basmala overlaps on new ruled annotations; then build
language-/width-/line-conditioned comparisons from the validated sites.
No further OCR service access is currently required.

Checkpoint verification: **90 tests pass**, all **101 Python files parse**,
and the complete quick CPU verifier passes. Separate verification replays
all **604 masked-page DPs** and all **604 scan-derived ornament detections**.
Both independent annotation sets' scan hashes replay; the three separately
annotated basmala centers also pass a direct post-hoc site check
(`logs/corpus-basmala-site-check.log`). `git diff --check` passes.
Full quick-verification log: `logs/corpus-map-verification-cpu.log`.
No commit was requested or made.

## 2026-10-18 — targeted omission/conflict review and a wrong accepted name

Inspected the full scans for the eleven missing-name IDs and the p315/p316
duplicate. This is an **exposed, failure-selected review by one AI reader**,
not another held-out accuracy sample. `tools/corpus_site_review.py` records
the read name-core windows, exact token IDs, scan hashes, neighboring text,
raw overlapping OCR regions and their all-optimal alignment owners. The
versioned result is `tools/data/audit_corpus_site_review_v1.json`.

### Eleven missing names are present and colored

| exact verse/form | scan | observed mapping problem |
|---|---:|---|
| 3:148 والله | 67 | tiny mandatory fragment; main name has no full OCR box |
| 4:37 الله | 83 | exact detection has multiple possible token owners |
| 7:164 الله | 171 | exact detection has multiple possible token owners |
| 9:116 الله | 204 | real detection assigned to an earlier ordinary token |
| 10:18 الله | 209 | no OCR region at the name; tiny annotation assigned elsewhere |
| 11:92 الله | 231 | real detection has support for other tokens, not this one |
| 27:26 الله | 378 | exact detection has multiple possible token owners |
| 39:3 لله | 457 | overlapping separate/combined detections are individually optional |
| 48:9 بالله | 510 | real detection has support for other tokens, not this one |
| 58:8 الله, later occurrence | 542 | real detection assigned to the earlier name |
| 73:20 والله | 574 | overlapping split/combined detections are individually optional |

All eleven are visibly colored. In particular, a region's absence from
mandatory support often reflects **identity alignment**, not failure to
detect the word. Three exact detections have ambiguous owners; four more
real detections are assigned elsewhere or lack support for the intended
token. The two overlap cases expose redundant OCR regions as competing
readings of the same ink. The model currently concatenates those readings
as though they were successive observations.

### Accepted support can still have the wrong identity

The p542 detection at `[219,698,286,776]` is the **later** name after
`يعذبنا`, token **70044**, but was accepted for the **earlier** name,
token **70038**, in `بما لم يحيك به الله`. The earlier name is visibly at
x~800–875 on the same row. The review replaces that one automatic name
location with a separately marked core window and preserves the superseded
box. This is a genuine accepted-location error, despite exact OCR surface
agreement and mandatory ownership under the conditional edit model.

Ordinary sites also fail here: p204's **9:116 والارض**, token **25998**,
was placed on the later Allah word; p542's **58:8 يحيك**, token **70036**,
has a small support box above the earlier name area instead of its actual
word at the right of the row. These original sites are retained as evidence
in the review. They must not be treated as independently validated ordinary
word geometry in a reference population.

### Cross-page conflict resolved by reading the scans

**20:77 ولقد**, token **40736**, begins at the top right of **p316**.
P315 ends with **20:76 من تزكى**. Its additional OCR `مال` box at
`[94,1602,162,1651]` lies inside `تزكى`, and the substring model wrongly
extends that page into the next verse. The explicit review decision accepts
p316 and rejects p315 for this token; earlier maps/site output are preserved.

### Reconciled name-ID inventory and its limits

The report includes one location record for every **2,697 scanned canonical
verse-name IDs**: **2,685 automatic hypotheses + 12 reviewed name cores**.
The twelve comprise the eleven omissions plus the wrongly placed earlier
p542 name. Inventory is checked directly against the exact corpus, excluding
unscanned surah 1; **2,699 − 2 = 2,697**. Unencoded head basmalas are separate.

This establishes **token-ID coverage of a mixed hypothesis/review view**, not
2,697 visually verified locations, complete word boundaries or a corpus-wide
color census. Automatic support boxes and manual name cores are explicitly
distinguished. The reviewed cores are approximate localization windows and
must not be used as equivalent width measurements. No new probability claim
is computed from this view.

```bash
. .venv/bin/activate
python tools/corpus_site_review.py --verify
python tools/corpus_site_review.py --verify --scans
python tools/verify_cpu.py
```

Verification: targeted diagnostics and scan hashes replay; the complete quick
CPU verifier passes, including **90 tests** and syntax checks on **102 Python
files**. Log: `logs/corpus-site-review-verification-cpu.log`. The new review
is included in the scan-free verifier. No additional OCR requests were made.

Next: improve the observation model for overlapping OCR alternatives and
small annotation fragments, and evaluate that rule on new pre-prediction
ordinary-word/basmala boundary labels. Keep possible page fringes distinct
from accepted sites. The known wrong ordinary sites and accepted-name error
make corpus-wide word-geometry validation necessary before linguistic null
comparisons. Cached OCR is sufficient for this work.

## 2026-10-18 — observation-filtered v3 experiment: recoveries and precision losses

The preceding audit/OCR checkpoint was committed as **72acecc**. This
continuation uses the existing cache and adds no service requests.

### Change the observations before alignment

`ocr_observation_map.py` produces a separate experimental v3 map. It removes
invalid boxes, gold-header observations, boxes below 35px high, and text
that normalizes to no Arabic letters **before** reading-order grouping and
character alignment. The earlier site-height filter acted only after
alignment, so small annotations could still corrupt the reading sequence.

Two retained detector regions conflict when their intersection covers at
least **3/5 of the smaller box's area**. Each connected conflict component
is resolved by an exact maximum-weight independent-set calculation, with
weight `box_area × round(1,000,000 × clipped_service_confidence)`. This can
select one combined region or multiple nonconflicting fragments. It uses
geometry/confidence, not canonical spelling, expected names or annotations.
Ties use deterministic source-index order. Components over 22 regions
would abstain entirely; none did in this run. This is a **heuristic choice
of OCR observations**, not a probability model over alternative readings.
All retained/rejected source-region IDs, weights and reasons are recorded.

Across the 604 pages, preprocessing excludes **806 ornament regions, 4,288
small observations, 1,507 nonlexical observations and 418 overlapping
alternatives**. All pages still obtain conditional reference-window matches.
The raw v3 mapper gives **77,040 verse-word support hypotheses** and no
cross-page duplicate canonical IDs. Applying the same single-box site policy
as the previous view gives **77,048 unique verse-token hypotheses**, **360
synthetic head-basmala supports** and **2,693 verse-name hypotheses**.

### Exposed development comparison, including regressions

Every annotation here was already exposed. No fresh accuracy estimate is
claimed. The algorithm receives no manually supplied page scopes or boxes.

| check | preserved sites v1 | filtered-observation v3 sites | v3 with stricter screen |
|---|---:|---:|---:|
| earlier 111 name centers correct / accepted | 111 / 111 | 111 / 111 | 93 / 93 |
| 12 targeted name centers correct / accepted | 0 / 1 | **6 / 8** | **6 / 6** |
| 33 adjudicated word centers correct / accepted | 33 / 33 | 33 / 33 | 22 / 22 |
| coarse boundaries passing / 27 evaluable | 26 / 27 | 26 / 27 | 18 / 27 |
| accepted envelope exact on 12 scoped pages | 12 / 12 | 12 / 12 | 12 / 12 |
| three annotated basmala names located | 3 / 3 | 3 / 3 | 2 / 3 |

The six automatically recovered target locations are **4:37, 9:116, 11:92,
39:3, 48:9 and 73:20**. The **20:77 ولقد** duplicate disappears automatically:
only p316 retains the token. The ordinary **9:116 والارض** location becomes
the correct `[705,1143,851,1221]` rather than the later Allah box.

However, v3 introduces an accepted **wrong** support for **3:148 والله**:
`[17,1574,239,1649]`, on the left-end neighboring text instead of the real
name at x~320–397. The earlier **58:8 الله** remains wrongly placed on the
later name. Its nearby **يحيك** support also remains wrong. Four scanned
name IDs still lack usable sites: **7:164, 10:18, 27:26, later 58:8**.
Therefore **2,693 supported name IDs is not 2,693 correct locations**.

The optional stricter screen requires exact normalized OCR surface agreement
and reference-token overlap with an optimal globally unique text anchor.
It rejects both known wrong accepted name boxes, while retaining the six
recoveries, but also drops **18/111 earlier correct names**, **11/33 sampled
word centers**, and one of the three annotated basmala names. Across all
pages it leaves **57,791 verse-token hypotheses / 2,399 verse-name supports**.
Even this screen is not certification: anchor overlap need not cover every
character of the word, and the observations themselves are heuristic.

The 12/12 scope result refers to the **first/last accepted-site verse**,
not the possible-character envelope. The earlier 5/6 possible-envelope
findings concerned ambiguous fringe text and are a different quantity.
Six sampled word boundaries remain unscorable in every view; a withheld
box does not count as a boundary pass.

### Verification and next work

Artifacts are `audit_ocr_observation_map_v3.json` and
`audit_ocr_observation_validation_v3.json`. The latter records all individual
outcomes, rejected correct locations, known wrong supports, omission IDs,
scope checks and input hashes. Earlier maps and the mixed manual-review
inventory remain separate inputs, not overwritten predictions.

Four new tests compare overlap selection with **all possible subsets** on
small random graphs, check split/combined detector alternatives, preserve
tall prefixes while excluding small marks, and exercise the exact overlap
threshold and large-component abstention. “Tests passed” counts automated
implementation checks, **not pages read or empirical truth established**.
Saved-data replay and scan-based semantic evaluation are separate checks.

```bash
. .venv/bin/activate
python -m unittest discover -s tools -p test_ocr_observation_map.py -v
python tools/ocr_observation_map.py --verify --full
python tools/ocr_observation_validation.py --verify
python tools/verify_cpu.py
```

The full 604-page v3 DP/filtering replay and development-report replay pass.
Logs: `logs/ocr-observation-map-v3.log`,
`logs/ocr-observation-validation-v3.log`,
`logs/ocr-observation-validation-v3-replay.log` and
`logs/ocr-observation-verification-cpu.log`.

Next: keep v3 experimental; obtain fresh, frozen-rule ordinary-word/basmala
location and boundary annotations before inspecting corresponding predictions.
The p542 failure requires stronger local reading-order/context treatment;
global exact token IDs and confidence-weighted overlap suppression do not
solve it. A lattice that retains competing spatial readings would address
uncertainty more directly than selecting one reading and screening outputs.

Checkpoint verification: **94 automated tests pass**, **105 Python files
parse**, and the complete quick CPU verifier reaches successful completion,
including v3's filtering decisions, fixed review-page DPs and all comparison
outcomes. The separate **full 604-page v3 replay** also passes.
`git diff --check` passes.

## 2026-10-19 — seeded reading rows, p542 repaired, and fresh frozen-rule check

The observation-filtered v3 checkpoint was committed as **cae0427**. This
continuation uses the same cached OCR and scan images.

### Confirmed cause of the p542 identity error

The old reading-order function anchors a row at its **first, topmost box
center**, then starts another row when a later center is 40px away. On
p542 an annotation recognized as `ولا`, source region 77, has box
`[774,679,817,720]`, center y=699.5. The left-side real words in the next
text line have centers around 735–738, so they join its group. The right-side
words center around 741–746 and start a second group. Consequently the
left half (`يعذبنا الله بما نقول`) is read **before** the right half
(`يحيك به الله ويقولون في انفسهم لولا`). This explains both the name-ID
swap and why a small annotation had supplied the accepted `يحيك` box.

`ocr_reading_order.py` supplies a separate geometry-only heuristic:

- Seed rows using boxes at least **0.75 × page median retained box height**.
- Group those seeds with a **40px median-center gap** rule.
- Assign shorter observations as satellites to the nearest seed row whose
  median vertical box interval overlaps them. Satellites do not move centers.
- Keep unmatched satellites as separate rows, and read each row right-to-left.

`ocr_row_map.py` applies that order to v3's unchanged observation selection,
then reuses the exact anchor retrieval and all-optimal substring mathematics.
It records row seeds/satellites and original source-region IDs. Its ordered
mapping wrapper is separate because earlier manual provenance hashes the
historical mapper's source. A synthetic test verifies identical reports when
old and new orders agree; the shared edit/path routines retain their existing
exhaustive reference tests.

### Development outcomes and remaining errors

V4 correctly assigns the **earlier and later 58:8 Allah names on p542** and
places **58:8 يحيك** at its actual `[909,707,997,785]` word box. On the twelve
previously reviewed name locations:

| method | correct | wrong accepted | abstained |
|---|---:|---:|---:|
| preserved site view | 0 | 1 | 11 |
| v3 observation-filtered sites | 6 | 2 | 4 |
| v4 seeded-row sites | **8** | **1** | **3** |
| v4 exact-surface/anchor screen | 8 | 0 | 4 |

These twelve labels are exposed development. The **p67 3:148 والله wrong
accepted union remains**. **7:164, 10:18 and 27:26** still lack accepted
sites. The stronger screen drops the p67 error but again loses 18 of the
earlier 111 correctly localized names. V4 preserves the earlier **111/111**
name-center checks, **33/33** adjudicated word centers, **26/27** evaluable
coarse boundaries, **12/12** accepted verse envelopes and **3/3** earlier
basmala centers. The p315 duplicate remains resolved in favor of p316.

On all 604 pages, raw v4 has **77,047 canonical verse-word support
hypotheses**. Applying the established single-box site policy gives
**77,055 unique canonical token hypotheses**, **360 synthetic head-basmala
supports** and **2,694 verse-name hypotheses**, with no duplicate canonical
IDs across pages. The known p67 error remains among those hypotheses;
support totals are not correct-location totals.

### Fresh annotations under frozen inference-source hashes

Before reading any selected pages' predicted word coordinates, froze four
inference-file hashes and the selection protocol in
`audit_row_sample_plan_v4.json`. Full predictions already existed on disk;
the reader did not use them to supply annotation truth. Six hash-stratified
**non-ornament** pages were selected, excluding prior samples/targeted reviews:
**163, 252, 317, 355, 448, 543**. On each, independently read the second
canonical lexical word of physical text rows **3, 8 and 13**. Two separately
hash-selected top-header pages, **311 and 321**, supply their surah-head
basmala names (20:0 and 21:0). This deliberately structured small sample is
not a uniform random sample of corpus words.

One AI reader inspected the full unlabelled scans and coordinate-ruler row
crops before the prediction comparison. Exact corpus text confirms token
identities. Manual whitespace partitions and image pixels define approximate
horizontal ink extents; no OCR coordinates define those partitions. Ink
contacting a horizontal partition edge makes the boundary **unscorable**.
The annotations and partitions were retained before inspecting predictions.

All three methods—preserved sites, v3 and v4—get **20/20 correct centers**:
**18/18 fixed-position words and 2/2 basmala names**. All **8/8 evaluable**
horizontal boundaries meet the pre-existing +/-12px tolerance. **12/20
boundaries are unscorable**, including both basmalas, because of partition
contacts. This check finds no center regression; it does **not** show v4
outperforming the older methods on fresh data or certify complete word edges.

Manual files: `audit_row_sample_plan_v4.json`,
`audit_manual_row_sample_v4.json`. Prediction/evaluation files:
`audit_ocr_row_map_v4.json`, `audit_ocr_row_development_v4.json`,
`audit_row_fresh_validation_v4.json`. Unlabelled ruled crops are in
`logs/row-v4-fresh-review/`.

```bash
. .venv/bin/activate
python tools/ocr_reading_order.py --pages 542
python -m unittest discover -s tools -p test_ocr_reading_order.py -v
python tools/ocr_row_map.py --verify --full
python tools/ocr_observation_validation.py --verify --mapping tools/data/audit_ocr_row_map_v4.json --output tools/data/audit_ocr_row_development_v4.json
python tools/row_validation_sample.py --verify --scans
python tools/row_map_validation.py --verify
python tools/verify_cpu.py
```

Next: investigate p67's missing real name box and misleading left-edge
reading; retain abstention for the three unresolved names. Broaden ordinary
word-boundary ground truth with partitions that explicitly separate diacritic
ownership, and sample wider x/row positions before using these sites as a
linguistic/width-conditioned reference population. The fresh twenty-center
check is useful but does not validate the full 77,055-site inventory.

Checkpoint verification: **98 automated tests pass**, **110 Python files
parse**, and the complete quick CPU verifier passes with both old v3 and
new v4 reports. Separate **full 604-page v4 DP/filtering/row replay** passes;
the fresh labels' source hashes and scan-derived pixels also replay. Logs:
`logs/ocr-row-full-replay-v4.log`, `logs/ocr-row-verification-cpu-v4.log`,
`logs/ocr-row-v3-compatibility.log`, `logs/ocr-row-development-v4-replay.log`,
`logs/row-fresh-scan-replay-v4.log`, `logs/row-fresh-validation-v4.log`.
`git diff --check` passes. Continuation changes after cae0427 are uncommitted.

## 2026-10-19 — boundary-aware v5, two names recovered and conservative unions

The seeded-row/fresh-validation checkpoint was committed as **d178552**.
This continuation reuses cached OCR and the same scans. CPU word-distance
acceleration is pinned as **rapidfuzz==3.14.3** in `requirements-audit.txt`.

### Respect word boundaries while retaining all optimal paths

The character-only alignment can assign part of an exact recognized `الله`
region to neighboring canonical words at no boundary cost. In the remaining
**7:164** and **27:26** cases, this prevents mandatory whole-word ownership
even though the detected name is correctly spelled and positioned.

`ocr_word_boundary_map.py` builds an explicit word/region lattice. The
geometry-filtered observations and seeded reading order are those of v4;
unique text anchors retrieve the reference window. The new lattice allows
**1:1, 1:2, 1:3, 2:1 and 3:1** canonical-word/detector-region transitions.
For a transition consuming p words and q regions, its integer cost is

    4 × Levenshtein(concatenated canonical words, concatenated OCR regions)
      + (p + q − 2).

Whole-word deletions and whole-region insertions cost four times their
normalized character length. Reference prefixes/suffixes are free only at
canonical word boundaries. The character/boundary weights **4 and 1** and
maximum group size **3** are model choices, not estimated OCR probabilities.
Many:many boundary-shift groups are not allowed.

Forward and backward tables retain **all** minimum-cost paths. An edge is
optimal exactly when forward(start) + edge_cost + backward(end) equals the
global optimum. Every observation inherits all canonical owners of all
optimal consuming edges. A one-region/multiple-word edge remains ambiguous
and cannot supply independently partitioned word boxes. A region is mandatory
only if it has one possible owner and cannot be inserted on any optimum.
This preserves uncertainty for repeated text and genuinely merged detections.

The vectorized insertion closure uses cumulative observed-character costs,
generalizing the earlier unit-cost closure. Backward computation reverses
the **edge-cost matrices**, not concatenated word strings: reversing word
order without reversing characters would incorrectly change split/merge
distances. Independent exhaustive tiny path/subsequence-end enumeration
tests costs, all owners and insertion possibilities, including this case.

V5's start/end indices are **virtual token boundaries**, not character
indices. V1's optimal-character-anchor flags do not apply to the new lattice;
compatibility flags are explicitly false and the artifact records that
anchors are used for retrieval only. A successful v5 status means conditional
word-window alignment, not a calibrated confidence or certified page scope.

### Recoveries, retained error and conservative site policy

V5 correctly locates the previously unresolved **7:164 الله on p171** and
**27:26 الله on p378**, while retaining the earlier p542 and other recoveries.
Its broad site view still assigns the p67 `والله` token to an incorrect
multi-region union at `[17,1574,239,1649]`. P209's **10:18 الله** remains
without support; the cache contains no detector region at its real name core.

`word_boundary_sites.py` therefore records a separate, explicitly post-hoc
policy: a union of **more than one mandatory region must exactly reproduce
the canonical normalized token**. Single-region support keeps the existing
geometry/35px-height policy. This uses no manual locations. It rejects the
p67 union whose recognized text is neighboring material rather than `والله`.
It also rejects **709 other verse-word unions and one head-basmala union**,
for **711 exclusions including p67**; legitimate words with OCR spelling errors may
be excluded too. The broad model and every rejected union remain available.

| exposed check | v4 sites | broad v5 sites | v5 exact multi-region unions |
|---|---:|---:|---:|
| 12 reviewed names: correct / wrong / abstained | 8 / 1 / 3 | 10 / 1 / 1 | **10 / 0 / 2** |
| earlier 111 name centers correct | 111 | 111 | 111 |
| 33 adjudicated word centers correct | 33 | 33 | 33 |
| earlier coarse boundaries passing / 27 evaluable | 26 / 27 | 26 / 27 | 26 / 27 |
| former fresh-v4 centers correct / 20 | 20 / 20 | 20 / 20 | 20 / 20 |
| former fresh-v4 boundaries passing / 8 evaluable | 8 / 8 | 8 / 8 | 8 / 8 |
| earlier three head-basmala centers correct | 3 | 3 | 3 |

All these labels are **exposed development for v5**, including the sample
that was fresh under frozen v4 rules. No fresh v5 accuracy estimate is
claimed. Zero known wrong acceptances in the targeted subset does not certify
the rest of the corpus. The 12 earlier accepted verse envelopes and the
p315/p316 duplicate resolution also remain correct under these checks.

### Corpus outputs and replay

All **604 pages** produce conditional word-window matches. The raw mapper
has **77,214 canonical verse-word support hypotheses**. The broad single-box
site view gives **77,221 unique canonical token hypotheses / 2,696 verse-name
supports**. The conservative view retains **76,511 unique verse-token
hypotheses**, **359 synthetic head-basmala supports**, and **2,695 canonical
verse-name hypotheses**, with no duplicate canonical IDs across pages.
Its two missing scanned name IDs are explicitly **3:148 والله** and
**10:18 الله**. Their real colored name cores are already retained in the
separate manual review; they are not inserted into automatic predictions.

Artifacts:

- `audit_ocr_word_boundary_map_v5.json` — full model, region ambiguity,
  word-boundary costs/settings and input hashes.
- `audit_word_boundary_sites_v5.json` — conservative site hypotheses,
  all excluded unions, missing-name IDs and policy outcomes.
- `audit_word_boundary_development_v5.json` — v4/broad-v5/conservative-v5
  comparisons on all earlier labels and retained failures.

```bash
. .venv/bin/activate
python -m unittest discover -s tools -p test_ocr_word_boundary_map.py -v
python tools/ocr_word_boundary_map.py --verify --full
python tools/word_boundary_sites.py --verify
python tools/word_boundary_validation.py --verify
python tools/verify_cpu.py
```

Next: validate v5 on new, frozen-rule annotations with broader physical row/x
coverage and independently resolved diacritic ownership. Review a reproducible
sample of the 711 rejected unions rather than assuming all were false words.
The two missing names require new image-derived evidence or deliberate
abstention; the automatic output must not imply they are absent or black.

Checkpoint verification: **103 automated tests pass**, **114 Python files
parse**, and the complete quick CPU verifier passes, including all earlier
reports, the new lattice, conservative sites and exposed comparisons. A
separate **full 604-page v5 DP/geometry replay** also passes. Logs:
`logs/word-boundary-full-replay-v5.log`,
`logs/word-boundary-verification-cpu-v5.log`,
`logs/word-boundary-sites-v5-replay.log`,
`logs/word-boundary-development-v5-replay.log`.
`git diff --check` passes. Continuation after d178552 is uncommitted.

## 2026-10-19 — rejected-union scan review and frozen broader v5 plan

The boundary-aware v5 checkpoint was committed as **e9db0c8**. Its precommit
replay completed successfully in `logs/word-boundary-precommit-cpu-v5.log`:
103 tests, all earlier reports and all v5 quick checks passed.

### What the exact-text exclusion costs

`word_union_review.py` freezes a diagnostic sample before the current scan
review. It stratifies all **711 exclusions** by two versus three-or-more
mandatory regions and one versus two-or-more normalized character edits.
Each ordinary stratum contributes its first four `SHA256(seed:page:v_id)`
ranks, or its entire population if smaller. The one rejected verse-name and
one rejected head-basmala union are both included as separate censuses.
The known p67 name remains exposed development, not a new discovery.

| exclusion stratum | population | reviewed |
|---|---:|---:|
| ordinary, 2 regions, 1 edit | 628 | 4 |
| ordinary, 2 regions, at least 2 edits | 72 | 4 |
| ordinary, at least 3 regions, 1 edit | 6 | 4 |
| ordinary, at least 3 regions, at least 2 edits | 3 | 3 |
| head basmala | 1 | 1 |
| verse name | 1 | 1 |
| **total** | **711** | **17** |

One AI reader inspected full-width context crops, with target identities but
without predicted-box overlays, and marked independent target-letter cores
in original scan coordinates. Comparison with the rejected centers gives
**16 correct centers and one wrong center**. The wrong one is the retained
p67 `والله` error. Coarse extent review gives **13 plausible word boxes,
two partial words, one box including a neighboring verse marker, and one
wrong location**. In particular:

- p105's rejected synthetic `5:0` **بسم** follows the long connecting stroke
  of the printed basmala; the union is plausibly one genuine word.
- Several rejected vocatives (`يايها`, `يبني`, `ويقوم`, `يهمن`) are correctly
  located even though OCR supplies long alifs absent from normalized canonical
  spelling. The sample also contains ordinary OCR character substitutions.
- p227 **11:58 ونجينهم** and p193 **9:47 ولاوضعوا** have correctly centered
  supports but omit their initial printed **و** from the union.
- p603 **110:2 افواجا** is correctly centered, but its union also includes the
  adjacent verse-2 rosette.

Thus rejecting a nonexact union does **not** establish that it is a false
word location. Conversely, a correct center does **not** establish complete
word geometry. The small, unequal-stratum, hash-ranked diagnostic sample
supplies neither accepted-site accuracy nor a design-based corpus estimate.
No inference or acceptance rule was changed using this review. Diacritic
ownership remains unadjudicated; the 13 plausible extents are not certified
full boundaries or independent double annotations.

Artifacts: `audit_word_union_review_plan_v5.json` records the selection,
population counts, predictions and frozen source/input hashes;
`audit_manual_word_union_review_v5.json` retains all 17 core/extent labels
and notes; `audit_word_union_review_v5.json` stores the replayed comparisons.
Scan-derived review crops are reproducible local outputs under
`logs/word-union-review-v5/`.

### Broader scan-first validation is frozen, not yet annotated

`word_boundary_fresh_plan.py` separately freezes new non-ornament pages
**66, 157, 229, 376, 445 and 545**, one hash-ranked page in each of six page
strata. It excludes prior annotated pages, known failure/replay pages and
all pages from this rejected-union review. Without reading the selected
predictions or scans, it schedules **54 positions**: lexical words 1/4/7
from the right on physical Quran rows 2/7/12 of every selected page.

The plan requires scan-first identity/core labels and separate full-ink
partitions, explicit uncertainty for overhanging diacritics, and accounting
for every scheduled slot. Missing positions get a recorded reason, with no
replacement. Only after labels are saved may frozen broad/conservative v5
predictions be compared. `audit_word_boundary_fresh_plan_v5.json` is a plan
only: **no fresh-v5 annotations or validation score are claimed**.

```bash
. .venv/bin/activate
python tools/word_union_review.py --verify --scans
python tools/word_union_review.py --review logs/word-union-review-v5
python tools/word_boundary_fresh_plan.py --verify
python -m unittest discover -s tools -p test_word_union_review.py -v
python tools/verify_cpu.py
```

The CPU verifier replays the frozen exclusion sample, independent-core
comparisons and fresh-plan hashes. Sampling tests verify frame-order
invariance, special-category/small-stratum censuses and rejection of corrupt
or duplicate entries. Next: annotate the frozen 54 slots before inspecting
their predictions; retain the two incomplete-word examples and marker union
when considering any future orthography-tolerant policy.

Continuation verification: **106 tests pass**, **117 Python files parse**, and
the complete quick CPU verifier passes with both new artifact checks. The
separate `word_union_review.py --verify --scans` also passes all reviewed
original-image hashes. Log: `logs/word-union-review-cpu-v5.log`.
`git diff --check` passes. This continuation after e9db0c8 is uncommitted.

## 2026-10-19 — completed frozen 54-position scan-first v5 comparison

The exclusion-review and broader-plan checkpoint was committed as
**31cdaf1**. The previously frozen plan is retained byte-for-byte, including
its historical `planned_only` stage marker. The following new artifacts
record completion; the plan itself is not retroactively rewritten.

### Scan-first annotations and complete slot accounting

One AI reader inspected the full scans and unlabelled, full-width ruler
crops on pages **66, 157, 229, 376, 445 and 545**, before opening selected v5
predictions. Rows are the fixed printed 110px slots: on p376 and p445 the
top basmala occupies slot 1, so the first ordinary text row is slot 2.
Each row's lexical sequence was read from the scan, then checked against
canonical text independently of OCR. Initial conjunctions and visually
separated vocatives remain parts of their canonical lexical tokens;
rosettes are never counted as words.

All **54 scheduled positions** are retained. Two seventh words are
unavailable: **p66 row 12** and **p445 row 2** each contain only six lexical
words. These slots carry explicit reasons and receive no replacements.
There are therefore **52 word labels**, not 54 successes or 54 OCR attempts.
This sample contains ordinary words and opening letters; none of the selected
52 tokens is an Allah-form name, so it adds no fresh name-census score.

The reader marked separate letter-core rectangles and whitespace-delimited
ink partitions from the scans. Core rectangles score centers without using
OCR boxes. Horizontal ink edges use the earlier black/colored thresholds,
with an explicit union mask for mixed ink. Five labels have uncertain
linguistic-mark versus recitation-sign ownership; nineteen ink masks reach
a horizontal partition edge. Two labels have both issues, so **22 boundaries are
unscorable** and **30 remain evaluable**. No label was revised after viewing
predictions. These are one-reader coarse partitions, not independent double
annotation or certified ownership of every overhanging diacritic.

Before the first comparison, `audit_word_boundary_fresh_evaluation_lock_v5.json`
recorded the saved-label, plan, annotation and evaluator hashes. Core
inclusion scores centers; horizontal boundary tolerance remains the earlier
**12px** convention. A mapper abstention stays in the denominator of any
otherwise boundary-evaluable label. Unavailable physical slots do not enter
the word denominator at all.

### Frozen broad versus conservative results

| method | correct centers / 52 | wrong accepted | abstentions | horizontal passes / 30 evaluable |
|---|---:|---:|---:|---:|
| broad v5 sites | **52** | **0** | **0** | **30** |
| conservative exact multi-region unions | **50** | **0** | **2** | **29** |

Both conservative abstentions are on **p445**:

- **37:1 والصفت**, physical row 2 / word 1. Broad support is
  `[818,147,987,216]`; measured horizontal ink edges are `[819,999]`.
  Its center is correct and edge errors `[-1,-12]` meet the existing coarse
  tolerance. The conservative view excludes this nonexact union.
- **37:20 يويلنا**, physical row 12 / word 7. Broad support is
  `[283,1253,392,1317]`, correctly centered on the visually separated
  vocative. Full horizontal geometry is unscorable because ink contacts
  both sides of the manual partition. Conservative v5 excludes this
  nonexact union too; the correct center does not certify its full extent.

The boundary shortfall of conservative v5 is **one abstention**, not a wrong
boundary among its accepted evaluable boxes. The other abstention is already
boundary-unscorable. Every outcome, including unavailable and unscorable
slots, is retained along with page/physical-row/lexical-position breakdowns.

This fresh sample confirms a coverage loss from exact-text screening while
retaining the earlier known reason for screening: the p67 wrong union.
It does not justify declaring all 711 exclusions wrong or all broad unions
correct. The six-page structured sample is not uniform over corpus words;
the methods share scans/OCR/labels, and no independent full-corpus accuracy
or causal inference follows. All these labels are now exposed for any future
policy development. The inference and acceptance rules remain frozen.

### Artifacts and replay

- `word_boundary_fresh_sample.py` — unlabelled ruler crops, scan-first
  transcription/core/partition replay, mixed-ink measurement and full slot
  inventory. `audit_word_boundary_fresh_labels_v5.json` is the handwritten
  scan-derived input; `audit_manual_word_boundary_fresh_v5.json` stores
  corpus identities, pixels and explicit boundary exclusions.
- `word_boundary_fresh_validation.py` — saved evaluation lock and comparison
  in `audit_word_boundary_fresh_validation_v5.json`. The lock guards both
  evaluator source and annotation hashes.
- `test_word_boundary_fresh_validation.py` — checks unavailable versus
  abstained denominators, retention of eligible abstentions in boundary
  denominators, and mixed black/colored masks with gold/background excluded.

```bash
. .venv/bin/activate
python tools/word_boundary_fresh_sample.py --verify --scans
python tools/word_boundary_fresh_validation.py --verify
python -m unittest discover -s tools -p test_word_boundary_fresh_validation.py -v
python tools/verify_cpu.py
```

Next: resolve the 22 uncertain/contacting boundaries in a separately versioned,
explicitly post-exposure review, preserving these original labels and results.
Any orthography-tolerant union policy must retain the partial-word and
rosette-contamination examples and receive a new untouched validation sample.

Continuation verification: **109 tests pass**, **120 Python files parse**, and
the complete quick CPU verifier passes, including all prior reports, the
new scan-first labels, evaluation lock and full slot accounting. A separate
`word_boundary_fresh_sample.py --verify --scans` reproduces original-image
hashes and all stored pixel measurements. Logs:
`logs/word-boundary-fresh-cpu-v5.log` and
`logs/word-boundary-fresh-scan-replay-v5.log`.
`git diff --check` passes. Continuation after 31cdaf1 is uncommitted.

## 2026-10-19 — post-exposure extent review, ownership bounds and a retained failure

The completed fresh-v5 checkpoint was committed as **52f46a0**. Its original
54-slot plan, handwritten labels, measured annotations, evaluation lock and
fresh comparison remain unchanged. This continuation is a **separate
post-exposure review by the same reader**, not a larger fresh accuracy test.

### Review every originally unscorable boundary

`word_boundary_extent_review.py` selects exactly the **22 originally
unscorable word boundaries**, with no success/failure-based subsampling.
All were reread on 3x enlarged scan crops with neighboring words and
original-coordinate rulers, without OCR-box overlays. Scan-only connected
ink components helped identify which marks crossed an old partition.

Several original rectangles were too wide and included neighboring ink;
others clipped a target's own letter or vowel. Examples include:

- p229 **11:77 رسلنا**: the old rectangle included part of neighboring
  `لوطا`; a narrower whitespace cut leaves target ink at x907..994.
- p157 **7:65 قال**: the old left cut clipped its lam, while the right side
  admitted a separate magenta **ط** stop sign above preceding `هودا`.
  Enlarged reading and connected components isolate its own magenta letters
  and vowels at x339..388. The original uncertainty and note are retained
  in the prior artifact; this is the explicit post-exposure correction.
- p445 **37:20 يويلنا**: the old partition clipped the visually separated
  vocative on the right and entered following `هذا` on the left. Both parts
  of the canonical token are now included, with ink edges x285..395.
- p545 **59:7 واليتمي**: the old right cut clipped the initial **و**;
  the reviewed partition includes it, giving edges x460..602.

No original token identity, coarse center-core rectangle, prediction,
acceptance rule, 12px tolerance or unavailable slot was changed. Revised
partitions need not contain every pixel of an old coarse core rectangle;
they retain its center and use the scan to isolate full target ink. The
original 30 evaluable labels are copied unchanged. Every reviewed word
stores its original boundary record alongside the new partition and note.

### Exact horizontal uncertainty bounds without claiming full mark ownership

Some ambiguous marks are wholly inside the word's horizontal footprint.
Instead of asserting ownership of these marks, the review records explicit
**mandatory** and **possible** thresholded ink masks, M and P. Conditional
on those manual ownership assumptions, every allowed target mask S obeys

    M ⊆ S ⊆ P, with M nonempty.

For leftmost ink column L and exclusive right boundary R,

    L(P) ≤ L(S) ≤ L(M),
    R(M) ≤ R(S) ≤ R(P).

These extrema are attainable at the two endpoint masks. Thus horizontal
edges are invariant for **every** ownership subset exactly when both
endpoint pairs coincide. This is an exact finite-set statement, not an
estimated probability, automatic linguistic assignment or proof that the
manual mandatory/possible masks are correct.

Three cases have invariant horizontal edges despite unresolved full mark
ownership: p66 **3:136 جزاؤهم**, p376 **27:1 طس**, and p545 **59:7 السبيل**.
For the first two, colored auxiliary marks are optional; for the last, the
isolated superscript **لا** is optional within an explicit rectangle.
Their left/right extrema are unchanged under every included/excluded subset.
The separate magenta **ط** above p157 `نكدا` is identifiable stop notation
and is excluded from that word's black linguistic-ink mask.

One case remains horizontally unresolved: p545 **59:8 اولئك**. Its left edge
is fixed at **506**, but the right edge ranges from **597 to 607** depending
on inclusion of the small magenta auxiliary guide. The neighboring word's
separate stop sign is excluded from the reviewed partition. This label
stays unscorable; an interval is retained instead of choosing a favorable
single edge.

### Post-exposure results and newly exposed accepted-boundary failure

The review makes **21 additional boundaries evaluable**, leaving **one**
unresolved and **51 evaluable in total**. All 52 center labels and both
unavailable physical slots retain their original outcomes.

| stage | broad v5 horizontal passes | conservative v5 horizontal passes |
|---|---:|---:|
| original fresh labels, unchanged | 30 / 30 | 29 / 30 |
| newly evaluable post-exposure labels only | 20 / 21 | 19 / 21 |
| combined post-exposure boundary view | **50 / 51** | **48 / 51** |

Both methods fail the newly evaluable **p545, 59:7 السبيل**, physical row 7 /
word 7. Its measured horizontal edges are **[23,144]**; predicted edges are
**[20,160]**, with errors **[-3,+16]**. The center remains correct, but the
right edge exceeds the unchanged 12px tolerance. The optional recitation
sign cannot fix this discrepancy because the word's horizontal extrema
are invariant whether that sign is included or not.

Conservative v5 additionally abstains on the same two p445 words as before:
`والصفت` and `يويلنا`. The latter now has evaluable horizontal extent and
passes in broad v5, while its conservative abstention stays in the boundary
denominator. Thus the combined conservative shortfall comprises **one
accepted boundary failure and two abstentions**, not three wrong accepted
boxes. Center totals remain **52/52 broad** and **50/52 conservative**, with
no wrong accepted centers in this set. These are dependent, same-reader
post-exposure boundary results; the original fresh report is not replaced.

### Artifacts, mathematical tests and replay

- `audit_word_boundary_extent_labels_v5.json` — all 22 reviewed partitions,
  ownership assumptions and explanatory notes.
- `audit_manual_word_boundary_extent_v5.json` — new pixels and exact edge
  ranges, original boundary records and complete 54-slot inventory.
- `audit_word_boundary_extent_validation_v5.json` — original versus reviewed
  outcomes and all boundary failures for both unchanged policies.
- `test_word_boundary_extent_review.py` independently enumerates every
  ownership subset for every nonempty-mandatory 2×3 ternary pixel frame,
  checking attainable edge ranges and the invariance equivalence. It also
  checks interior versus edge-changing optional color, invalid masks and
  omission of unavailable slots from the review inventory.

```bash
. .venv/bin/activate
python tools/word_boundary_extent_review.py --verify --scans
python tools/word_boundary_extent_review.py --review logs/word-boundary-extent-v5
python -m unittest discover -s tools -p test_word_boundary_extent_review.py -v
python tools/verify_cpu.py
```

Next: make the treatment of auxiliary recitation guides explicit before
resolving the remaining interval. Any geometry or union-policy change must
retain the p545 accepted-edge failure and the earlier incomplete-word,
marker-contamination and p67 wrong-location examples, then receive new
untouched validation rather than treating these reviewed labels as fresh.

Continuation verification: **113 tests pass**, **122 Python files parse**, and
the complete quick CPU verifier passes, including all earlier artifacts and
the new extent/ownership comparisons. Separate
`word_boundary_extent_review.py --verify --scans` reproduces all reviewed
scan hashes, pixels and ownership bounds. Logs:
`logs/word-boundary-extent-cpu-v5.log` and
`logs/word-boundary-extent-scan-replay-v5.log`.
`git diff --check` passes. Continuation after 52f46a0 is uncommitted.

## 2026-10-19 — explicit auxiliary-mark policies and ownership-robust verdicts

The extent-review checkpoint was committed as **e40a54e**. Its 22 reviewed
partitions, original boundary records, ownership bounds and reported 50/51
and 48/51 results are preserved. This continuation asks a different question:
can a prediction's tolerance verdict be established even when the precise
edge and full auxiliary-mark ownership are unresolved?

### Explicit scope of the policies

`word_boundary_ownership_policy.py` compares three conventions over the
**same previously designated optional pixels**, without reassigning marks
after looking at which choice improves a prediction:

1. **Mandatory only:** keep M; exclude only the explicit optional pixels.
2. **Include optional:** keep P, including all those optional pixels.
3. **All ownership:** require the prediction to pass for every S with
   M ⊆ S ⊆ P, including both endpoint conventions and every partial subset.

These are conditional mask conventions, not a claim that every optional
mark has now been linguistically classified. Neighboring words/signs already
outside the reviewed partition remain outside. Mandatory letters and vowels
of either color are retained; there is no global rule to discard magenta
ink. Fully colored lexical words such as p157 `قال` keep their lexical ink.
Previously evaluable words without ownership alternatives have singleton
edge support. Partition-contact exclusions, line requirements, abstentions,
the 12px tolerance and the two unavailable physical slots remain explicit.

### Exact attainable edges, including holes

For nonempty M, let mL be its leftmost occupied column and mR its rightmost
occupied column (inclusive). Let C(P) be the finite set of occupied columns
of P. The attainable left and exclusive right edges are exactly

    A = {x ∈ C(P) : x ≤ mL},
    B = {x+1 : x ∈ C(P), x ≥ mR}.

Coordinates include the partition's x offset. Every pair in **A × B** is
attainable: retain M and add a possible pixel at each desired extreme. Both
extreme choices lie outside or on M's extrema, so neither changes the other
edge. Conversely, every allowed mask must contain M, giving these same
restrictions. Thus the joint edge set is exactly that Cartesian product.

For predicted edges (pL,pR), the exact best and worst max-absolute errors are

    best  = max(min[a∈A] |pL-a|, min[b∈B] |pR-b|),
    worst = max(max[a∈A] |pL-a|, max[b∈B] |pR-b|).

Every ownership passes iff worst ≤ 12; every ownership fails iff best > 12;
otherwise the verdict is ownership-sensitive. These statements concern the
horizontal tolerance test; the prediction must also be accepted and on the
correct physical line.

Using actual attainable columns matters. If M has a pixel at x2 and P adds
only x0, the left edge can be 0 or 2, never 1. Interpolating the interval
would falsely permit a zero-error left edge at 1. Likewise, two failing
endpoint masks alone do not prove that every interior subset fails. The
tests independently enumerate all optional-pixel subsets of every
nonempty-mandatory 2×3 ternary frame, checking the entire joint support,
best/worst errors and all three possible verdicts against this formula.

### Remaining interval: uncertain edge, stable verdict

For p545 **59:8 اولئك**, the prior edge envelope remains
**L=506, R∈[597,607]**. Both methods retain predicted edges **[497,600]**.
The left error is always −9px, and every attainable right error lies within
−7..+3px. Thus the **worst max-absolute error is 9px**: every allowed
ownership subset passes the unchanged 12px tolerance. The exact right edge
and full ownership remain unresolved; no single favorable edge is selected.

All four previously uncertain-ownership words are checked, along with all
other scheduled slots. Their conditional verdicts are stable under every
ownership subset:

| convention | broad v5 passes / labelled | conservative v5 passes / labelled |
|---|---:|---:|
| mandatory only | 51 / 52 | 49 / 52 |
| include all explicit optional ink | 51 / 52 | 49 / 52 |
| every allowed ownership subset | **51 / 52** | **49 / 52** |

The broad shortfall remains the accepted p545 **59:7 السبيل** right-edge
error **+16px**. Conservative additionally retains its p445 `والصفت` and
`يويلنا` abstentions. Neither endpoint policy nor any intermediate subset
can erase the accepted failure. The prior 51-evaluable boundary outcomes
are asserted unchanged; the only added verdict is the formerly unresolved
word's ownership-robust pass. Center outcomes remain 52/52 and 50/52.

### Replay and interpretation

New artifact: `tools/data/audit_word_boundary_ownership_policy_v5.json`.
It includes all 54 scheduled positions, attainable edge supports for all 22
reviewed words, explicit policies, best/worst errors, original summaries and
all retained failures. Input/source hashes and full scan replay bind these
supports to the earlier masks. Scan-free replay uses the stored supports;
`--scans` independently reconstructs them from the images and cross-checks
the prior pixel counts and edge bounds.

```bash
. .venv/bin/activate
python tools/word_boundary_ownership_policy.py --build
python tools/word_boundary_ownership_policy.py --verify --scans
python -m unittest discover -s tools -p test_word_boundary_ownership_policy.py -v
python tools/verify_cpu.py
```

This remains **same-reader, post-exposure development analysis**, conditional
on the manual masks. It establishes tolerance-verdict invariance, not exact
segmentation, independent linguistic ownership or a new fresh accuracy
estimate. The OCR geometry and union/acceptance policies are unchanged.
Next: investigate the retained p545 accepted-edge failure as development
data; any repair must retain earlier incomplete-word, marker-contamination
and p67 wrong-location counterexamples and receive new untouched validation.

Continuation verification: **119 tests pass**, **124 Python files parse**,
and the complete quick CPU verifier passes, including the new integrated
ownership-policy check and all earlier reports. Separate scan replay
reconstructs every reviewed support, reproducing the prior ink counts and
ownership bounds. Logs: `logs/word-boundary-ownership-cpu-v5.log`,
`logs/word-boundary-ownership-scans-v5.log`,
`logs/word-boundary-ownership-replay-v5.log`, and
`logs/word-boundary-ownership-tests-v5.log`.
`git diff --check` passes. Continuation after e40a54e is uncommitted.

## 2026-10-19 — p545 detector-margin diagnosis and an in-box ink-hull candidate

The ownership-policy checkpoint was committed as **65e78eb**. Original v5
predictions, 50/51 and 48/51 reviewed fixed-boundary scores, and 51/52 and
49/52 all-ownership scores remain the historical inputs. This continuation
investigates the retained accepted-edge failure as **exposed development**.

### Exact text can still have unsupported detector margins

The p545 **59:7 السبيل** hypothesis has one mandatory OCR region, **68**,
whose raw text is `السَّبِيلِ` and normalizes exactly to the canonical token.
Its detector box is **[20,705,160,772]**. Using the already established black
and colored thresholds, its in-box ink has bounding box
**[26,705,144,772]**, with **1,257 thresholded pixels**. Thus the original
box's rightmost **16 columns are empty** under these thresholds; exact
normalized text did not ensure a tight geometric extent.

The reviewed full-word horizontal edges remain **[23,144]**. A horizontal
in-box hull gives edges **[26,144]**, changing edge errors from **[-3,+16]**
to **[+3,0]**. Both centers are inside the original independent letter core.
The original tolerance failure is retained beside the candidate's pass.

This does not repair complete word segmentation. The original vertical
extent remains **705..772**, while the reviewed possible full-ink extent is
**699..784**. The lower kasra is visibly outside the detector box; top ink
also includes the optional superscript stop sign. A correct horizontal
tolerance verdict must not be described as complete diacritic coverage.

### Label-free rule and exact geometric limits

`ocr_ink_trim.py` uses only an image, the existing integer half-open OCR box
and the earlier fixed thresholds:

    black: R<120 and G<120 and B<120
    colored: R>120 and R-G>45
    ink: black OR colored

For nonempty in-box thresholded ink K in B=[x0,x1)×[y0,y1), set

    B' = [min_x(K), max_x(K)+1) × [y0,y1).

This is the unique narrowest horizontal interval, at the unchanged vertical
bounds, containing **all** of K. Therefore K ⊆ B' ⊆ B. No connected-component
selection, identity, OCR text, manual core, partition, auxiliary ownership
decision or tolerance is used to infer B'. Empty-ink boxes are preserved,
with an explicit status rather than an inference that a word is absent.
Acceptance, identity, text support and conservative union exclusions stay
unchanged. Centers are recomputed, since shrinking can move them.

Two limitations follow directly. Ink missing outside B cannot be recovered
by any B' ⊆ B. Conversely, thresholded neighboring/marker ink already in B
is retained by this hull. The method tightens detector margins; it does not
assign pixels to linguistic words. The independent tests enumerate every
2×3 binary image, verifying containment, minimality and ink preservation,
and include an explicit case where trimming loses a previously correct
center. Other tests cover exact RGB inequalities, signed channel arithmetic,
colored lexical letters, outside ink, empty boxes, invalid measurements,
uncertain edges, abstentions and unavailable positions.

### All prior cohorts and all retained counterexamples

`word_boundary_ink_audit.py` measures **244 distinct boxes on 65 exposed
pages**. It evaluates every earlier development group for seeded v4, broad
v5 and conservative v5, all 54 reviewed-v5 physical slots for each policy,
and all 17 rejected unions as explicitly **counterfactual** geometry checks.
Shared words, pages and methods are dependent; no pooled accuracy is formed.

There are **no center regressions, no center rescues, and no scored
horizontal-boundary regressions** in any of these cohorts. The only new
boundary pass is the p545 failure above:

| reviewed v5 measure | original | horizontal-hull candidate |
|---|---:|---:|
| broad centers | 52 / 52 | 52 / 52 |
| conservative centers | 50 / 52 | 50 / 52 |
| broad fixed/invariant boundaries | 50 / 51 | 51 / 51 |
| conservative fixed/invariant boundaries | 48 / 51 | 49 / 51 |
| broad all-ownership boundary verdicts | 51 / 52 | **52 / 52** |
| conservative all-ownership boundary verdicts | 49 / 52 | **50 / 52** |

The two conservative p445 abstentions remain. Among earlier v5 development
words, the adjudicated sample stays at **26/26 evaluable boundary passes**,
and the former fresh-v4 sample stays at **8/8**. All earlier name outcomes
remain unchanged, including the wrong accepted p67 broad hypothesis.

The rejected-union review retains all four known extent counterexamples:

- **p227, u06, 11:58 ونجينهم:** `[759,799,935,876]` becomes
  `[768,799,935,876]`. The initial waw at approximately x960..995 remains
  outside. A correct center is still a partial-word box.
- **p193, u15, 9:47 ولاوضعوا:** `[608,1469,773,1537]` becomes
  `[613,1469,773,1537]`. The initial waw around x800..820 is still missing.
- **p603, u07, 110:2 افواجا:** `[849,1029,1002,1103]` becomes
  `[851,1029,1002,1103]`. The overlay still includes the adjacent verse-2
  numeral/rosette; black marker ink is retained along with word ink.
- **p67, u17, 3:148 والله:** `[17,1574,239,1649]` becomes
  `[35,1574,239,1649]`. Both boxes are horizontally disjoint from the
  independent target core x326..393. The wrong location remains wrong.

All 17 unions remain excluded by the conservative automatic policy; their
counterfactual center tally stays **16 correct, one wrong**. Their original
coarse extent labels and notes are preserved, not silently reclassified.

### Freeze new untouched validation before treating the candidate as progress

`word_ink_trim_fresh_plan.py` freezes the candidate's exact rule/source hashes,
original broad/conservative prediction artifacts, raw OCR/corpus inputs and
selection. It selects **p36, p124, p298, p366, p500 and p508**, one minimum
`SHA256(seed:page)` rank per original page stratum, excluding all previous
scan-first pages, prior exclusions, all 65 measured pages and ornament bands.

The plan schedules **54 positions**: lexical words 1/4/7 from the right on
physical Quran text rows 2/7/12. Selected scans and page-specific predictions
have not been inspected for this plan. There are **no annotations or fresh
scores yet**. Every slot must be retained; unavailable/uncertain positions
receive explicit reasons without replacement. Independent identity, letter
cores, full-ink partitions and optional-mark assumptions must be saved before
prediction comparison. Then lock the labels and evaluator and compare four
paired methods: original/trimmed broad and original/trimmed conservative.
Recompute centers and preserve all regressions and denominators. No retuning
on that sample or independent-double-annotation claim is permitted.

Artifacts:

- `audit_word_boundary_ink_trim_development_v6.json` — all measured scan
  projections, source hashes, original/candidate scores, regression lists,
  retained extent labels and raw p545 region provenance.
- `audit_word_ink_trim_fresh_plan_v6.json` — candidate rules and the complete
  untouched 54-slot plan, explicitly marked planned-only.

```bash
. .venv/bin/activate
python tools/word_boundary_ink_audit.py --verify --scans
python tools/word_boundary_ink_audit.py --review logs/word-boundary-ink-trim-v6
python tools/word_ink_trim_fresh_plan.py --verify
python -m unittest discover -s tools -p 'test_*ink_trim*.py' -v
python tools/verify_cpu.py
```

The `v6` suffix names an **experimental refinement diagnostic**, not an
adopted replacement mapper or a new accuracy estimate. Next: annotate the
frozen six-page plan scan-first, then evaluate the frozen candidate without
changing its rule in response to those results.

Continuation verification: **127 tests pass**, **129 Python files parse**,
and the complete quick CPU verifier passes with both new integrated checks
and all previous reports. Separate scan replay reproduces every projection
and outcome; fresh-plan replay reproduces source hashes and the full slot
inventory. Logs: `logs/word-boundary-ink-trim-cpu-final-v6.log` and
`logs/word-boundary-ink-trim-scans-v6.log`. The first concurrent CPU attempt
had cached the plan implementation before its final input-hash additions;
the complete final run above starts from the frozen files and passes.
`git diff --check` passes. Continuation after 65e78eb is uncommitted.

## 2026-10-19 — completed scan-first validation of the frozen ink-trim candidate

The diagnostic and untouched-plan checkpoint was committed as **f032a12**.
This continuation completes its six-page, 54-slot plan without changing the
candidate, its thresholds, acceptance policies, selected pages or tolerance.
The plan artifact and its historical planned-only stage marker are preserved;
separate annotation, lock and result artifacts record the completed stages.

### Scan annotation before prediction comparison

One AI reader inspected p36/124/298/366/500/508 as enlarged scan-only row
crops with original-coordinate rulers, without OCR boxes or selected
predictions. First-seven canonical lexical sequences on physical rows
2/7/12 were transcribed from scans, then confirmed against corpus text.
Verse rosettes are ignored in lexical counting, and attached initial waw
stays with its canonical token even when visually separated.

The reader marked independent letter-core rectangles and separate full-ink
partitions for words 1/4/7. Before locking, scan-only enlarged word context
and connected ink components corrected draft whitespace cuts that clipped
vowels or admitted adjacent marks. These are all **pre-comparison** drafts;
the final handwritten labels and measured annotations were saved before any
selected prediction comparison. No post-comparison revisions are folded in.

All **54 physical slots** are retained, with **52 labelled words and two
unavailable positions**, both on p508:

- Row 7 has six canonical tokens through **47:24 القرءان**; the separated
  waw and `اعمى` form one canonical `واعمي`, not two word positions.
- Row 12 has six tokens of **47:27** through `وجوههم`; `وادبرهم` begins on
  the next physical row. There is no seventh word on this row.

Neither unavailable slot is replaced or counted as a mapper abstention.

### Two kinds of uncertainty, with different scoring eligibility

**50 words** have fixed or invariant horizontal edges. One additional word,
p508 **47:20 القتال**, has an explicit optional auxiliary-mark mask:

- The isolated black superscript **لا** is a scan component at
  **[563,134,576,158]**, containing **138 thresholded pixels**. Its enclosing
  rectangle is optional; the neighboring lexical lam's damma at
  **[579,145,588,160]** remains mandatory.
- The exact attainable left edges range **563..571**, while the exclusive
  right edge is fixed at **667**. Thus exact horizontal geometry is not
  unique, but every allowed ownership subset can be tested without choosing
  a favorable single edge.

The original prediction has worst max-absolute edge error **11px** and the
trimmed prediction **5px** under those frozen masks, so both pass every
ownership subset at the unchanged 12px tolerance. This supplies the **51st
ownership-evaluable boundary**, not a newly resolved exact edge.

One word remains boundary-unscorable: p298 **18:49 الا**. Its high extension
and lower kasra overlap horizontally with `احصيها`'s fatha/initial alif on
the left and `كبيرة`'s tanwin on the right. The letter core is clear, but
the broad rectangle contains neighboring ink and touches its horizontal
cuts. No exact optional ownership mask was asserted. Coincident extrema
of that raw crop do **not** establish target-edge invariance; its boundary
is excluded from both denominators, while its center remains scored.

### Lock before opening selected predictions

`word_ink_trim_fresh_sample.py` builds the complete annotation inventory,
scan hashes, thresholded pixels, exact edge supports and explicit exclusions
without reading selected OCR text or boxes. The evaluation source then
writes `audit_word_ink_trim_fresh_evaluation_lock_v6.json`, binding:

- the original frozen plan;
- the handwritten and measured annotation artifacts;
- the sample builder, evaluator and every reused pixel/ownership/center
  scoring source.

The lock stage is `all_scan_labels_saved_before_selected_predictions_read`.
Only after it was saved did the first selected-prediction comparison run.
Every later replay checks the lock before opening prediction JSON. No frozen
inference, annotation or evaluation source changed after comparison.

### Four paired methods: two rescues, no regressions, two retained failures

| method | accepted / labelled | correct centers | fixed-edge passes | all-ownership passes |
|---|---:|---:|---:|---:|
| original broad | 52 / 52 | 52 / 52 | 46 / 50 | 47 / 51 |
| trimmed broad | 52 / 52 | 52 / 52 | **48 / 50** | **49 / 51** |
| original conservative | 52 / 52 | 52 / 52 | 46 / 50 | 47 / 51 |
| trimmed conservative | 52 / 52 | 52 / 52 | **48 / 50** | **49 / 51** |

There are no abstentions or wrong accepted centers in this sample. Each
paired comparison has **two rescued boundaries, zero boundary regressions,
zero center changes, and two boundaries failing both variants**. All 52
available original boxes are shared by broad and conservative policies here,
as are their trimmed boxes. These are identical paired outcomes on this
sample, **not two independent replications** of a benefit.

All four original accepted-boundary failures are retained:

| page / token | measured edges | original edges / signed errors | trimmed edges / signed errors | result |
|---|---|---|---|---|
| p36, 2:231 لتعتدوا | [235,330] | [201,328] / [-34,-2] | [207,328] / [-28,-2] | remains failing |
| p124, 5:104 قالوا | [931,997] | [916,995] / [-15,-2] | [931,995] / [0,-2] | rescued |
| p366, 26:1 طسم | [896,989] | [857,989] / [-39,0] | [867,989] / [-29,0] | remains failing |
| p508, 47:27 فكيف | [802,935] | [787,928] / [-15,-7] | [802,928] / [0,-7] | rescued |

The two rescues remove unsupported left margins. Their right edges still
omit 2px and 7px of the measured full-ink extent; passing the 12px convention
does not certify complete segmentation. The candidate never expands a box.

### Residual failures demonstrate the ink-preservation limitation

The separate post-comparison diagnostic selects the **union of every failure
in all four methods**, deduplicated by physical slot. It copies labels and
scores unchanged and records raw mandatory-region provenance and overlays:

- **p36:** one region, **14**, reads exactly `لِتَعْتَدُوا`. Its detector
  box nevertheless reaches into the following `ومن` and the separate magenta
  **ج** stop sign. Horizontal trimming retains that in-box neighboring/guide
  ink, leaving a **−28px** left-edge error. Exact normalized OCR text did
  not imply isolated word geometry.
- **p366:** one region, **4**, reads `لسمل`, supported by the boundary-aware
  text lattice as canonical `طسم`. Its box includes the adjacent verse-1
  numeral/rosette and magenta **ط** stop sign. The conservative policy only
  adds an exact-text requirement for multi-region unions, so this single
  region stays accepted. Trimming retains contaminating ink and leaves a
  **−29px** left-edge error.

These are real retained failures of the frozen candidate on new labels.
Earlier partial-word, rosette-contamination, p67 wrong-location and p545
vertical-clipping examples also remain in their original development
reports. None is removed or fixed by favorable relabelling.

### Artifacts, replay and limits of interpretation

- `audit_word_ink_trim_fresh_labels_v6.json` — handwritten scan transcriptions,
  letter cores, partitions, two unavailable slots and ownership assumptions.
- `audit_manual_word_ink_trim_fresh_v6.json` — all scan hashes, thresholded
  measurements, exact attainable supports and eligibility decisions.
- `audit_word_ink_trim_fresh_evaluation_lock_v6.json` — pre-comparison label
  and scoring-source hashes.
- `audit_word_ink_trim_fresh_validation_v6.json` — four complete outcomes,
  52 distinct predicted-box pixel projections, all paired transitions,
  regressions and failures, plus page/row/position breakdowns.
- `audit_word_ink_trim_fresh_diagnostics_v6.json` — separate post-comparison
  provenance for every failure and the two uncertain scan labels.

```bash
. .venv/bin/activate
python tools/word_ink_trim_fresh_sample.py --verify --scans
python tools/word_ink_trim_fresh_validation.py --verify --scans
python tools/word_ink_trim_fresh_diagnostics.py --verify
python tools/word_ink_trim_fresh_diagnostics.py --review logs/word-ink-trim-fresh-v6/failures
python -m unittest discover -s tools -p test_word_ink_trim_fresh_validation.py -v
python tools/verify_cpu.py
```

Tests check complete slot accounting, unchanged boundary denominators under
abstention, omission of unavailable slots, unspecified versus explicit
ownership, recomputed-center regressions and invalid pairings. CPU replay
includes the frozen comparison and all failure provenance.

This is a **fresh, frozen-rule, single-reader structured sample**. It is not
independent double annotation, a uniform-word corpus accuracy estimate or
proof of complete word segmentation. The four methods share the same scans,
OCR and labels. Two rescues without observed regressions are a finite-sample
result, not a calibrated guarantee for other words. Next: treat the two new
contamination failures as development cases for any image-based ownership
repair; preserve this locked report and use new untouched validation for
changed inference. Do not tune the frozen candidate on these outcomes.

Continuation verification: **132 tests pass**, **133 Python files parse**,
and the complete quick CPU verifier passes, including all earlier reports,
the new annotation/evaluator lock, four methods, paired transitions and
failure provenance. Separate annotation and comparison scan replays reproduce
all image hashes, ownership masks/supports and 52 predicted-box projections.
Logs: `logs/word-ink-trim-fresh-cpu-v6.log`,
`logs/word-ink-trim-fresh-annotation-scan-replay-v6.log`,
`logs/word-ink-trim-fresh-comparison-scan-replay-v6.log`, and
`logs/word-ink-trim-fresh-diagnostics-v6.log`. The first-comparison log is
`logs/word-ink-trim-fresh-first-comparison-v6.log`.
`git diff --check` passes. Continuation after f032a12 is uncommitted.

## 2026-10-19 — automatic ownership evidence, unclaimed ink and harmful subtraction

The completed fresh-v6 checkpoint and existing superseded-article removals
were committed as **8d5b7f2**. Its frozen scan annotations, evaluator and
four-method report are unchanged. All v6 results are **exposed development
data for this continuation**; no result below is added to the fresh score.

### Test the available evidence before inventing a repair

The two residual failures suggested two automatic evidence sources:

1. Other usable mandatory-word hypotheses from the existing v4/v5 mapper.
   Their rectangles can overlap a target box and claim some of its ink.
   The target word and any hypothesis sharing its mandatory region IDs are
   excluded from this competing set.
2. Cached `rosettes_v3/rosette_digits.json` centers and widths/heights, turned
   into half-open rectangles. Those geometries can originate in gold-ring
   or pale-disk extraction; they are evidence, not certified full marker
   masks. No recognition label or enlarged padding is inferred from them.

All v5 views use the same broad usable-word claim context. The conservative
policy determines the evaluated target inventory, not a separate filtered
set of competitors; seeded-v4 targets use the v4 claim context.

`ocr_ownership_evidence.py` compares **four explicit policies**, without
choosing whichever gives the best score: other-word rectangles, rosette
rectangles, their union, and a deliberately aggressive **column-shadow
stress test**. The latter projects each overlapping rosette's x interval
through the original OCR box's full vertical extent.

For all policies, P is the union of black/colored thresholded ink inside
the original OCR box B, using the unchanged thresholds. If A is the policy's
automatic rectangle mask, define the heuristic mandatory mask

    M = P \ A.

The displayed proposal is the horizontal hull H(M), with original vertical
bounds and acceptance preserved. The reference baseline is **unmasked H(P)**,
not the wider raw detector rectangle. Thus a mask cannot take credit for
the earlier empty-margin trimming rescues. Raw boxes and outcomes remain
available beside both. An empty M preserves the original box with an
explicit no-certificate fallback; it never establishes word absence.

### Exact conditional bounds do not certify the automatic ownership premise

For nonempty M, the previous finite-set theorem gives the **exact joint
horizontal support** for every S with M ⊆ S ⊆ P. Actual occupied columns
are retained, including holes, rather than filling an interval. The two
edge supports form a Cartesian product because optional extreme pixels
can be chosen independently around nonempty mandatory ink. Independent
tests enumerate every ownership subset of every nonempty-mandatory 2×3
ternary frame and compare the full joint support.

This is conditional mathematics. To interpret that family as the true
target's in-box ownership, one additionally needs

    M ⊆ T_in_box ⊆ P.

Automatic rectangles do not establish the first inclusion. Unclaimed
foreign ink stays in M, even if both endpoints are invariant. Moreover,
full target ink outside B is absent from P and cannot be recovered by
shrinking. An exact calculation over a wrongly specified ownership family
does not repair the premise.

For existing **clear, boundary-eligible manual partitions only**, the audit
therefore separately measures, relative to those single-reader labels:

- pixels in M that are not in the manual target;
- target pixels moved into the optional set;
- full target pixels missing outside the original box;
- extra target pixels omitted by the proposed geometry.

The manual partition and ink class are evaluation inputs only, never used
to construct an automatic proposal. For a fixed manual edge label, a second
exact calculation scores **every inferred ownership hull**, not just H(M).
It records best/worst error and whether the family all passes, all fails,
or contains both outcomes. These are finite geometric statements, not
calibrated ownership probabilities or independent linguistic annotation.

### Both residual failures contain ink that competing boxes fail to claim

**p36, 2:231 لتعتدوا:** no other usable mandatory-word rectangle overlaps
its box, and no rosette rectangle overlaps it. The following `ومن` detector
ends at **x191**, while its printed initial waw occupies approximately
**x213..230**, already inside the target's detector box. Thus a neighboring
word's incomplete box cannot tell this subtraction rule where its own
missing letter is.

All four policies retain edges **[207,328]**, with left error **−28px**.
Relative to the frozen clear manual partition, M contains **357 non-target
pixels**, and the original crop also omits **6 target pixels**. The computed
in-box edges are invariant, but the mandatory-ownership premise is false.
This is a concrete counterexample to treating unclaimed ink as target ink.

**p366, 26:1 طسم:** the cached rosette rectangle is
**[857,168,897,209]**. It covers the verse numeral, while the magenta **ط**
stop sign lies above it. Rectangle subtraction removes **30 thresholded
pixels**, but **134 non-target pixels** remain mandatory. Edges stay
**[867,989]**, with the same **−29px** left error. Other-word and combined
rectangle policies likewise leave the failure unresolved.

### A favorable boundary verdict can hide deletion of real target ink

The p366 column-shadow stress test removes the marker and stop sign's
columns, giving **[897,989]** against manual edges **[896,989]**. This passes
the 12px convention, but clips **four legitimate black pixels** from the
target's upper elongation mark at x896. The actual target is completely
inside the original box in this case, so the four missing pixels are newly
introduced by the proposal.

Its conditional family has attainable left edges including the stop sign
and the target extremum; the exact comparison against the fixed manual
edges has **best error 0px, worst error 29px**. Thus the family is
**ownership-sensitive**, even though the chosen mandatory-only endpoint
passes. The tolerance success is neither full pixel preservation nor an
all-ownership guarantee.

On the now-exposed 52-word v6 sample, broad and conservative views coincide:

| diagnostic policy | fixed-edge passes | all-manual-ownership passes | newly clipped target pixels in clear references |
|---|---:|---:|---:|
| unmasked ink-hull baseline | 48 / 50 | 49 / 51 | 0 by definition |
| other-word rectangles | 48 / 50 | 49 / 51 | 28 on p500 `الي` |
| rosette rectangles | 48 / 50 | 49 / 51 | 0 |
| union of both rectangle sets | 48 / 50 | 49 / 51 | 28 on p500 `الي` |
| rosette-column stress test | 49 / 50 | 50 / 51 | 4 on p366 `طسم` |

The p500 competitor is `يوم`, with box **[892,693,962,769]**. Its overlap
with `الي` changes that target's hull from **[959,693,1003,769]** to
**[962,693,1003,769]**, clipping **28 manually assigned target pixels**.
Both tolerance and center checks still pass. Its original box already
omitted 3 target pixels; the candidate omits 31. In the earlier p66 reviewed
sample, the column-shadow stress test additionally clips one target pixel
from `الذين` while leaving its tolerance verdict unchanged.

Among the 50 clear fixed-edge v6 labels, **44** have some full target ink
outside their original detector box. This is a conditional pixel-coverage
count on these manual partitions, **not a corpus segmentation-error rate**.
It makes the already documented distinction between center, horizontal
tolerance and complete diacritic coverage concrete.

### The earlier cohorts expose a real new center regression

The full audit also retains every previous name/word group for seeded v4,
broad v5 and conservative v5, the original reviewed-v5 slots, and all
17 rejected unions as counterfactual geometry checks. The cohorts overlap;
their counts are not pooled. It measures **470 frame/reference-specific
contexts on 71 exposed pages**.

Other-word subtraction, alone or in the rectangle union, changes the
**p321 synthetic 21:0 basmala Allah** support from
**[228,260,369,338]** to **[275,260,369,338]**. The competing `الرحمن`
rectangle is **[129,256,275,335]**. The target's original independent core
is **[223,252,317,335]**:

- original/unmasked center x = **298.5**, inside the core;
- candidate center x = **322**, outside the core's right edge **317**.

This is **one physical center regression**, repeated in the seeded-v4,
broad-v5 and conservative-v5 views of the prior 20-word sample, whose center
total drops **20/20 → 19/20** under these masks. The word's earlier boundary
was already unscorable; the regression is still recorded individually,
rather than hidden by its pre-existing boundary uncertainty. No center
rescues or other scored regressions occur in these cohorts.

The two missing-initial-waw examples remain outside-box omissions, the p67
wrong location remains wrong, and all 17 rejected unions remain rejected
by the conservative automatic policy. Their original extent annotations
are retained rather than reclassified from these coarse geometry tests.

### Reproducibility and next step

New artifact: `audit_word_ownership_evidence_development_v7.json`. It stores
every policy/cohort outcome, criterion-specific regressions, raw automatic
claims, possible/mandatory column projections and mask hashes, exact
conditional supports, manual-reference contradictions and input/source
hashes. Scan replay reconstructs the full pixel masks and reference checks;
scan-free replay checks the stored projections and all derived outcomes.
The CPU verifier includes this diagnostic and all earlier frozen reports.

```bash
. .venv/bin/activate
python tools/word_ownership_evidence_audit.py --verify --scans
python tools/word_ownership_evidence_audit.py --review logs/word-ownership-evidence-v7
python -m unittest discover -s tools -p test_ocr_ownership_evidence.py -v
python tools/verify_cpu.py
```

**No rectangle-subtraction rule is adopted or presented as a new fresh
accuracy result.** The useful result is identifying the missing ownership
evidence and retaining concrete harms, even where the coarse boundary score
improves. Next: investigate scan-derived letter/auxiliary-mark components
and explicit ambiguous ownership rather than assuming detector rectangles
partition words. Any changed inference must retain these counterexamples,
the locked v6 report, and receive new untouched validation.

Continuation verification: **140 tests pass**, **136 Python files parse**,
and the complete quick CPU verifier passes with the new ownership-evidence
check and every earlier frozen report. Separate scan replay reconstructs all
470 contexts, possible/mandatory masks, manual intersections, conditional
supports and derived scores. Logs: `logs/word-ownership-evidence-cpu-v7.log`
and `logs/word-ownership-evidence-scan-replay-v7.log`. Overlays are reproducible
under `logs/word-ownership-evidence-v7/`.
`git diff --check` passes. Continuation after 8d5b7f2 is uncommitted.

## 2026-10-19 — scan-component granularity and oracle representability

The automatic-rectangle evidence audit was committed as **87f0289**.
Its complete CPU verifier and independent scan replay both pass. This
continuation follows its documented next step: examine actual connected ink
instead of assuming detector rectangles partition words.

### Four explicit component partitions

`ocr_ink_components.py` uses the **unchanged threshold union** of black and
colored ink. It labels components under both 4-connectivity (edge neighbors)
and 8-connectivity (edge or corner neighbors), independently in:

1. the original OCR crop;
2. the full page, retaining every component that intersects that crop.

The second frame matters because a connection outside a crop can merge two
apparently disconnected in-box fragments. Pixel inventory entries retain
component IDs, full-frame bounding boxes, in-box counts and outside-box
counts. Full-page pixels outside the original box are **unlabelled here**;
they are not presumed foreign or added to a proposed word.

Every v7 context/reference key is preserved: **470 measurements on 71
exposed pages**, including all earlier cohorts, the rejected unions and the
formerly fresh v6 sample. Cohort and method totals remain separate. Clear,
boundary-eligible manual partitions alone supply target/non-target counts;
other contexts receive component inventories but no semantic oracle score.
In particular, p321's basmala center-regression case stays unlabelled for
pixel ownership rather than gaining a new inferred manual partition.

### Exact best possible error for whole-component assignments

For a component C intersecting B, let t(C) be the number of manually assigned
target pixels inside B and f(C) the other thresholded in-box pixels. If C
must be kept or removed whole, the two possible in-box errors are f(C) and
t(C). Components partition the possible ink, so their decisions are
independent for this additive loss. Hence the exact minimum is

    E_oracle = sum_C min(t(C), f(C)).

An exact in-box partition is representable iff no component contains both
classes. This is a reference-informed oracle: it assumes knowledge of the
target/non-target counts to choose components. It is **not an automatic
classifier, an accuracy score, a boundary score or a proof that a component
is a letter**. It places no word-count or nonempty-output constraint on the
component assignments.

Coarsening components cannot improve this minimum: it restricts the allowed
keep/remove assignments. The verifier checks both crop-to-page and
4-to-8-connectivity inequalities. Independent tests exhaust every 2×3
ternary frame (background/target/foreign), enumerate every component
assignment, and compare the resulting minimum with the formula. Synthetic
outside-crop bridges show that zero crop-local error can coexist with a
positive page-component minimum; touching black/colored ink can also create
a mixed component.

### Observed result: component selection, rather than granularity, is open

| exposed cohort / method | clear in-box references | exactly representable | oracle pixel errors |
|---|---:|---:|---:|
| reviewed-v5 broad | 48 | 48 | 0 |
| reviewed-v5 conservative | 46 | 46 | 0 |
| v6 now-development broad | 50 | 50 | 0 |
| v6 now-development conservative | 50 | 50 | 0 |

These results hold separately under **all four** frame/connectivity modes.
The cohorts/methods overlap and must not be pooled. Eligibility already
selects clear manual partitions; this is not evidence that arbitrary Quran
words, ambiguous marks or full-page segmentations have no touching ink.

The two retained contamination failures now have concrete component
inventories under full-page 8-connectivity:

- **p36, 2:231 لتعتدوا:** eight target-only components contain **1,139
  in-box pixels**, while four foreign-only components contain **357**.
  The neighboring initial waw is its own **173px** component at
  **[213,183,230,207]**. The target's bottom mark belongs to a component
  **[306,209,330,217]**, with 80 pixels inside B and **6 outside**. This
  exposes the original crop truncation without automatically expanding it.
- **p366, 26:1 طسم:** four target-only components contain **909 pixels**;
  two foreign-only components contain **164**. The stop sign contributes
  **134** in-box pixels and the verse numeral **30**. The target elongation
  at **[896,158,931,172]** is a separate **150px target-only component**.
  Thus the four target pixels clipped by v7's column-shadow stress test
  need not be deleted to represent the manual mask at component granularity.

These are representability observations, not a rule for recognizing the
four target components or excluding the two foreign ones. For p500 `الي`,
the component-colored review likewise retains the target ink that the
neighbor rectangle had clipped. The old masking regression and failures
remain recorded in v7, and no candidate geometry is produced here.

### Reproducibility and next step

New artifact: `audit_word_ink_components_development_v8.json`. Source and
helper hashes bind it to the v7 evidence and unchanged thresholds. Scan-free
replay verifies component accounting, reference totals, exact oracle errors,
coarsening inequalities and all source context links. It does not certify
pixel connectivity by itself. Scan replay reconstructs every component and
manual intersection directly from the source images.

```bash
. .venv/bin/activate
python tools/word_ink_component_audit.py --verify --scans
python tools/word_ink_component_audit.py --review logs/word-ink-components-v8
python -m unittest discover -s tools -p test_ocr_ink_components.py -v
python tools/verify_cpu.py
```

The review command creates **37** raw/crop-8/page-8 comparison sheets on
p36, p66, p321, p366 and p500, with a filename-to-context manifest. Target-only
components are green, foreign-only orange, mixed red and unlabelled purple.
The raw panel and ink outside B remain visible. The p36, p366, p500 and p321
counterexample sheets were visually checked against these interpretations.

Next: investigate automatic component-to-word evidence while explicitly
retaining unassigned/ambiguous components, whole-component versus
within-component ownership distinctions, and outside-box ink. Freeze any
actual changed inference before new untouched validation. The current
representability result supplies no automatic component selection and no
new fresh accuracy result.

Verification logs: `logs/word-ink-components-scans-v8.log`,
`logs/word-ink-components-review-v8.log`, and
`logs/word-ink-components-cpu-v8.log`. The suite passes **145 tests** and
**139 Python files parse**. The complete quick CPU verifier passes, including
all earlier frozen reports and the new component accounting check; separate
scan replay reconstructs all 470 measurements. `git diff --check` passes.
Continuation after 87f0289 is uncommitted.

## 2026-10-19 — bounded audit closure and separate research phase

The component-separability checkpoint was committed as **01cbb77**. At the
user's direction, the current audit pass is now **closed with an explicit
scope**, rather than extended until automatic word segmentation and causal
interpretation are solved. [AUDIT-CONCLUSION.md](AUDIT-CONCLUSION.md) is the
closing synthesis: central historical claims are retained with conditions,
corrected, withdrawn as supported inference, or identified as unestablished.
It supersedes the open-ended continuation queues above as the current
handoff; those dated entries remain part of the evidence history.

The surviving finding is a reproducible colored-component alignment excess
under specified models, including exact-rational column-only bounds. The
conclusion also reports geometry-conditioning sensitivity, the corrected
census/showcase/identity findings, frozen v6 validation and v7/v8 limitations.
It does not certify a Quran-wide word census, complete ink ownership, every
exploratory tool, or the historical semantic and construction/origin claims.

Separate next-phase gates cover automatic word ownership with untouched,
independently checked validation; linguistically and geometrically justified
comparators; and a corrected publication using only supported claims. New
algorithm research no longer keeps this pass open. A concrete defect affecting
an audited result, provenance or validation statement would reopen that item.

This closure changes documentation only. The verified code/data endpoint is
01cbb77: **145 tests**, **139 parsed Python files**, complete quick CPU replay
and separate v8 scan reconstruction pass as recorded above. The conclusion
was checked against the dated ledger and linked artifacts; no new statistical
result, test run or scan annotation is claimed by the closure itself.
