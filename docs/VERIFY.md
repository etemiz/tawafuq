# tawafuq — a quantitative study of Quranic word alignment

> *Curation note (2026-10-21): this file is the technical repository guide,
> formerly the root `README.md`. The root README is now the article itself.
> Scan-obtainment instructions live in `docs/DOWNLOAD-HAYRAT.md`; the file
> taxonomy is in `../CURATION.md`.*

This repository studies **tawafuq**, the claimed visual alignments in an
ayat-berkenar Quran layout, using 604 Hayrat "Qur'an in Tawafuq" page images.

**Bounded independent audit completed (2026-10-19).** Read the
**[audit conclusion](AUDIT-CONCLUSION.md)** for what survived, changed,
or was withdrawn, and the separate follow-up research scope. The earlier
“frozen” results contained scoring, counting and inference errors; the
chronological evidence and replay commands remain in
[`docs/AUDIT.md`](AUDIT.md). Historical results and articles are retained
for provenance, not as validated probability claims.

**Latest research:** actual same-word positions, selected independently of
color, show a strong alignment excess: standalone `الله` is **79.82% aligned
versus 36.96% expected** under the stated row/width-conditioned model. See
[the word-level results](RESEARCH.md#2026-10-19--color-independent-same-word-alignment)
and the **[origin-question assessment](DIVINE-ORIGIN.md)**. Divine origin
remains unresolved; the verified conditional tail bound is not an origin
probability.

## Current reproducible findings

- Rebuilt, alpha-corrected extraction: **3,339 / 4,582 = 72.87%** of eligible
  red-class image components meet the explicit column-or-neighbor-cell score,
  versus **26.22%** mean under independent per-page component-slot sampling
  (20,000 replicates). These are **mixed colored components**, not an exact
  census of crimson divine-name words. The scoring and extraction are tested
  independently on small ground truths; semantic labels remain under review.
- **Unit-matched control:** 3,590/4,682 = **76.68%** of size-filtered raw red
  components align vs **27.94%** under uniform labeling of the same non-gold
  raw-component sites. Preserving each line's count gives a 29.08% reference
  mean. These remain component statistics, with no certified word boundaries.
- The unit-matched column excess has an **exact-rational Markov upper bound
  below 10^-814 under its specified labeling model**; the initial merged-group
  baseline has a bound below 2×10^-726. Integer dynamic programming enumerates
  per-page score distributions. Both proofs can be replayed on a CPU without
  rare-event simulation.
  The earlier 10^-985 estimate used unvalidated independence assumptions.
  Human manufacture and divine origin require additional causal models.
- Corrected divine-name corpus count: **2,699 encoded occurrences**, or
  **2,811** after adding 112 unencoded surah-head basmalas. The old counter
  excluded two genuine interrogative forms and mishandled basmala accounting.
- Independent page-422 transcription finds **16 Allah forms overall**, but
  its narrow middle column contains **11 Allah forms plus Hu**. The previous
  literal “12-of-16 Allah” showcase threshold is not reproduced.
- The corrected facing-page break-band mirror test remains non-significant.
  The old “all grains negative” conclusion does **not** survive code review:
  corrected crimson identity tests show grain-dependent excess under a global
  label null. Its semantic interpretation and confounders need further work.

The historical per-type table, combined showcase p-value, unconditional
marking/anti-selection argument, and human/AI impossibility claims are not
validated. A large difference from one slot-placement model does not decide
between text, typography, editorial selection, and other causal explanations.
The initial baseline uses merged observations and raw reference fragments;
the additional controls address that mismatch. A neutral linguistic
word-placement model still needs independent validation.

## Repository layout

```
hayrat-pics/          604 page scans (NOT in git — see "Obtaining the scans")
tools/                analysis scripts (see tools/README.md for the triage)
tools/data/           historical derived artifacts + versioned audit results
tools/data/real_boxes_v3/  independently rebuilt component/slot extraction
docs/AUDIT.md         current verification report, commands and handoff
docs/AUDIT-CONCLUSION.md  closing claim dispositions and follow-up scope
docs/RESEARCH.md      post-audit research ledger
docs/DIVINE-ORIGIN.md origin-question scope assessment
docs/tawafuq-sources.md     literature survey + claim-verification log
docs/DOWNLOAD-HAYRAT.md     how to obtain the page scans (not in git)
docs/sources/         al-Afkar 2023 (CC BY 4.0) + extracted text; README lists
                      links to all other cited literature
```

## Obtaining the scans

The mushaf page images are a copyrighted print; they are **not** distributed
here. Scripts expect them at `hayrat-pics/page_<N>.png` (N = 1..604, NOT
zero-padded: `page_1.png`), file N = printed page number. Most images are
1024×1680; exceptions include page 1 (1024×1531) and page 489 (1013×1680).
The score uses a nominal 1024px reflection frame. PNGs may be transparent
and must be composited on white before measuring ink. Other scans are not
automatically interchangeable: thresholds, pixel bins and image hashes are
specific to this input. Extraction thresholds assume the two-ink print (crimson ≈ RGB 236/43/101,
magenta ≈ 209/5/125, gold rosettes).

The derived JSON artifacts in `tools/data/` are committed, so you can
re-run the statistics without the scans.

## Reproducing the main numbers

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-audit.txt

# without scans: independent reference, exact tiny cases, input hashes,
# analytic expectations and stored simulation statistics
python tools/verify_cpu.py

# regenerate the current global simulation (CPU, about 37s on audit machine)
python tools/real_stats.py 20000 --output logs/global-reproduction.json
python tools/reference_controls.py 5000 --output logs/reference-controls.json
python tools/exact_column.py --raw-wordlike --output logs/raw-component-bound.json

# with scans: regenerate extraction into a separate directory (~3 minutes)
python tools/real_extract.py 1 604 --output-directory logs/rebuilt-components
python tools/real_stats.py 20000 --data logs/rebuilt-components --output logs/rebuilt-global.json

# other audited/conditional checks
python tools/divine_census.py
python tools/type_rates.py 2000       # conditional on HISTORICAL shape labels
```

`verify_cpu.py --full` replays the stored global Monte Carlo runs and can
take several minutes. For long jobs use `setsid` and redirect output to
`logs/`. Seeds, batch sizes, raw null scores and input hashes are recorded.
No GPU, scan download, API or temporary feature file is needed for the
scan-free checks. See `docs/AUDIT.md` for the scope of each verified result.
`requirements.txt` additionally covers the older PDF/article tools.

## Key facts baked into the pipeline

- Gold rosettes carry verse numbers, but `page_verse_map.json` is an
  **inferred map**, combining self-training, DP and missing-verse heuristics.
  Its historical 99.4% CV claim is not reproduced by the committed code.
  Zero tiling violations do not certify correct verse identity.
- Repaired rosette extraction finds **6,229 markers**; a versioned inferred
  map is in `tools/data/rosette_map_v3/`. On the independently transcribed
  p567, localized assignments improve from **12/28 to 28/28**. This limited
  check does not establish corpus-wide accuracy. Rebuilt semantic pins remain
  count-matched hypotheses, with their input versions recorded explicitly.
- Fatiha is not among the 604 scans (page 1 = Basmala + 2:1-5).
- `token_map2.json` is historical exploratory output: the audit found 8,856
  reversed x-intervals and a silently unused width model. Token positions and
  boundaries need independent validation. Failures of these algorithms are
  not a proof that word geometry is mathematically impossible to recover.
- Ink thresholds: crimson = redish & B<108; magenta = redish & B≥108;
  redish = R-G>45 & R>120.

## License / attribution

- Code: MIT (see `LICENSE`).
- `tools/data/quran-uthmani.json`: Uthmani text from
  [tanzil.net](https://tanzil.net) / api.quran.com v4.
- `docs/sources/`: one CC BY 4.0 paper (Hussain 2023) and extracted text;
  all other literature is linked, not archived — see
  `docs/sources/README.md`.
- The mushaf design belongs to the Hayrat Foundation / the tawafuq
  tradition it documents; this project analyzes its printed geometry
  independently and claims no affiliation.

## 2026-10-18 — geometry-conditioned control update

On the same 4,682 size-filtered raw red components (76.68% observed alignment),
fixing counts within 20px-width/10px-height bins raises the analytic reference
rate to **38.82%**. Adding line and geometric edge role raises it to **69.43%**,
but also fixes **83.53% of red labels** at their original sites. A residual
column/union excess remains (zero exceedances in 5,000 replicates); the tight
control's neighbor-mirror score has 718/5,000 exceedances. This quantifies
model sensitivity and limited remaining randomization, not semantic or causal
validation. Full definitions, all five controls and limitations are appended
to `docs/AUDIT.md`.

```bash
python tools/geometry_controls.py 5000
python tools/geometry_controls.py --verify tools/data/audit_geometry_controls.json --full
```

## 2026-10-18 — exact-text and image validation update

A reproducibly selected six-page sample contains **38 Allah-form occurrences**:
all are visibly colored; **36/38** have another name on a different row within
15px horizontally (33/38 under the original fixed-bin score). All **40**
independently read verse endpoints match both stored maps. This is a limited
named-word check, not a whole-corpus completeness estimate.

GPU Arabic OCR was tested locally with Surya and EasyOCR. More usefully,
aligning approximate OCR lines to the **exact Quran text** assigns **37/38**
annotated names to their correct line, leaving one ambiguous. New source,
annotated data, raw OCR and replayable comparisons are documented at the end
of `docs/AUDIT.md`. The pin matcher now rejects run deficits and distinguishes
undetected runs from black ink; its v4 rebuild remains a hypothesis set.

## 2026-10-18 — fresh-page word-location and cloud OCR update

Six new independently read pages contain **22 Allah forms, all colored**.
Exact-text/Surya alignment places **22/22 on the correct text line**.
The new `tools/ocr_word_map.py` attaches exact token identities to exclusive
EasyOCR image regions: **17/22 correct localized names**, with five abstentions
and no wrong accepted name locations on this sample. Other word hypotheses
and complete boundaries still need annotation. Surya inserts five spurious
Allah forms on the sampled page with none, reinforcing the need to test
individual detections and geometry rather than average text error alone.

`tools/arabic_ocr_cloud.py` prepares Google Cloud Vision document OCR for the
same benchmark. `--plan` makes no requests; six pages estimate $0.009 at the
posted paid rate, before any free allowance. A $20 pilot budget is approved;
execution awaits credentials and **no paid calls have been made**. Full
results, commands, authentication options and the Azure comparison candidate
are at the bottom of `docs/AUDIT.md`.

### 2026-10-18 — cloud access checkpoint

The supplied service-account credential authenticates, but Google rejects
the pilot with **`BILLING_DISABLED`**. Link billing to that Google project
before retrying. No pages have been processed by Google yet. Optional
authentication dependencies are pinned in `requirements-cloud-ocr.txt`.

### 2026-10-18 — Google retry successful

Google document OCR now completed **12 pages**. Its raw word boxes locate
**60/60 annotated Allah forms**, with no extra name candidates, including
none on the zero-name control page. Combined normalized character error is
**4.49%**, lower than the tested local engines. The unchanged exact-token
mapper scores **58/60** name positions: two failures widen correct raw boxes
by including unrelated OCR fragments. These failures remain in the results.
Full word boundaries and non-name identities are still unvalidated.

Estimated OCR usage cost is **$0.018 before free allowance**, within the
approved $20 cap; actual billing was not queried. Saved raw responses and
four Google benchmark/map reports replay through `tools/verify_cpu.py`
without credentials or network. See the latest `docs/AUDIT.md` section.

## 2026-10-18 — mandatory-support mapping and broader validation

The versioned `mandatory-v2` mapper fixes the two earlier over-unions by
requiring OCR-region support that cannot disappear on an optimal edit path.
It scores **20/20 exact name locations on six fresh pages**, after being
frozen on the earlier samples. Google finds all 20 raw name sites but also
misreads a fragment of **اللهم** as an Allah candidate.

The first ordinary-word boundary labels exposed annotation errors. Separate
full-label ruler/pixel adjudication gives v2 **30/30 fixed-position non-Allah
word centers**, with **24/24** evaluable coarse horizontal boundaries and
six uncertain boundaries. These corrected-label results are post-hoc, not
a new blind accuracy estimate. The supplemental **اللهم** has a correct
center but a clipped edge, so complete word geometry remains a live issue.
Original labels and evaluations are preserved. Full methodology and the
604-page OCR-cache handoff are appended to `docs/AUDIT.md`.

### 2026-10-18 — complete 604-page OCR cache

All **604 full-page scans** are now OCRed. The compact derived artifact
`tools/data/ocr_google_corpus_v1.json` contains **87,843 raw regions**
(about 7.9 MiB), with per-page image/response hashes and engine/cost
provenance. Full raw responses stay in gitignored logs. The 2,842 raw name
candidates are OCR hypotheses, not a corrected canonical name census.

Cumulative service usage is estimated at **$0.909 before free allowance**.
All 604 raw-response conversions and the compact export verify locally;
scan-free verification is integrated in `tools/verify_cpu.py`. The next
work is exact-text/page-scope matching, boundary validation and linguistic
alignment controls, using this cache without further OCR charges.

## 2026-10-18 — independent corpus-token anchoring

The cached pages are now matched to exact Quran text **without the historical
rosette/page-verse map**. Unique text anchors retrieve a reference window;
all optimal substring alignments retain uncertainty. Unencoded head basmalas
have separate synthetic IDs. A pixel-derived gold mask prevents title text
from being treated as verse words.

The resulting wordlike-site view provides candidate locations for **76,776
unique canonical tokens**. All **111 independently annotated verse-name
locations** are correct in the checked samples; 31 were fresh for the first
anchoring model, and later fixes used exposed data. This is not a certified
whole-corpus accuracy figure. A separate fresh six-page scope test has
**5/6 exact possible envelopes**; ambiguous fringe characters remain.

The artifact explicitly retains **one cross-page token conflict** and
**11 verse-name IDs without usable support**. These cases and incomplete
boundaries need review before new word-level probability claims. Both
earlier mapping versions and their failures remain reproducible. No new
paid OCR was needed; see the latest `docs/AUDIT.md` handoff.

### 2026-10-18 — remaining name omissions reviewed

Direct scan review finds all eleven missing names in colored ink and assigns
the disputed **20:77 ولقد to p316**. It also reveals and corrects an accepted
name-location error on p542. A separate review artifact now covers all **2,697
scanned canonical verse-name IDs**, combining **2,685 automatic hypotheses
with 12 explicitly marked manual name cores**. This is complete ID coverage,
not a certification of all locations or boundaries. Replay with
`python tools/corpus_site_review.py --verify`; see `docs/AUDIT.md` for the
retained failures and next validation steps.

### 2026-10-18 — experimental OCR observation filtering

A separate v3 experiment filters small annotations and overlapping duplicate
OCR readings before text alignment. It automatically recovers six reviewed
name locations and resolves the page conflict, but still accepts two wrong
targeted name boxes. A stricter screen rejects those boxes while losing
correct detections too. All outcomes and coverage tradeoffs are replayable
with `tools/ocr_observation_validation.py --verify`; details are appended to
`docs/AUDIT.md`. This remains an exposed development experiment.

### 2026-10-19 — reading-order repair and fresh word check

Seeded text rows fix a confirmed short-annotation ordering defect on p542,
recovering both Allah identities and an ordinary word. V4 gets eight of the
twelve exposed problem-name locations correct; one wrong acceptance and
three abstentions remain. A separate frozen-rule sample on eight fresh pages
gives **20/20 correct centers** for all three compared methods. Only eight
horizontal boundaries are evaluable; all pass, while twelve remain uncertain.
See `docs/AUDIT.md` for the selection, retained failures and replay commands.

### 2026-10-19 — word-boundary-aware mapping

A separate v5 model respects canonical word boundaries while retaining
split/merged OCR ambiguity. It recovers names at **7:164** and **27:26**.
A conservative multi-region union policy rejects the remaining known wrong
name box: the twelve reviewed cases now give **10 correct, 0 wrong accepted,
and 2 abstentions**. It also rejects 709 other verse-word unions and one
basmala union, whose correctness remains under review. All earlier checked
centers are retained. These are exposed development results; details and
reproduction commands are appended to `docs/AUDIT.md`.

### 2026-10-19 — reviewing the conservative filter's losses

A frozen diagnostic scan review of 17 rejected unions finds **16 correctly
located centers**, including genuine words with nonexact OCR spelling. Two
supports omit an initial **و**, and one includes a verse marker: center
localization and complete word geometry remain distinct. The conservative
policy stays fixed. A separate **54-position, six-page** scan-first validation
plan is frozen; its annotations and fresh-v5 scores are still pending.
Details and replay commands are in `docs/AUDIT.md`.

### 2026-10-19 — fresh v5 scan-first validation completed

The frozen six-page plan now accounts for all 54 scheduled positions:
**52 labeled words and two unavailable slots**, with no replacements.
Broad v5 locates **52/52 centers**; conservative v5 locates **50/52** and
abstains on two genuine words. Neither accepts a wrong center in this sample.
Of 30 evaluable horizontal boundaries, broad v5 passes 30 and conservative
v5 passes 29, with one abstention. The other 22 boundaries remain unscorable.
This structured, single-reader sample is not a full-corpus accuracy estimate.
Original labels, frozen rules and all outcomes replay through the CPU verifier;
details are appended to `docs/AUDIT.md`.

### 2026-10-19 — separate post-exposure boundary review

Reviewing all 22 uncertain boundaries makes **21 more evaluable**, leaving
one unresolved interval. Exact ink-ownership bounds establish that three
ambiguous interior marks cannot change horizontal edges. The combined
post-exposure results are **50/51 boundary passes for broad v5** and
**48/51 for conservative v5**. Both retain a p545 word with a correct center
but a right edge 16px beyond measured ink, outside the 12px tolerance.
The original fresh-validation report is preserved; this same-reader review
is a separate result. See `docs/AUDIT.md` for the proof and retained failures.

### 2026-10-19 — boundary scoring under every allowed mark ownership

The remaining p545 extent stays uncertain, but its prediction passes the
12px tolerance for **every allowed ownership subset**. A separate policy
comparison therefore scores all 52 labelled words: **51/52 broad v5** and
**49/52 conservative v5**. Excluding or including all explicitly optional
marks gives the same totals. The +16px accepted-edge failure and two
conservative abstentions remain. These are conditional, post-exposure
results; exact mark ownership and fresh-validation claims are unchanged.

### 2026-10-19 — pixel-supported horizontal refinement experiment

The retained p545 +16px edge error comes from empty detector-box margin.
A label-free, horizontal-only in-box ink hull fixes that development case,
giving **52/52 broad** and **50/52 conservative** all-ownership boundary
passes on the reviewed words. Earlier scored outcomes have no regressions;
the partial-word, marker-contamination and wrong-location counterexamples
remain. This is an exposed experiment, not an adopted segmentation rule.
A new **54-slot scan-first validation plan** is frozen on six uninspected
pages; its annotations and fresh results are pending. See `docs/AUDIT.md`.

### 2026-10-19 — frozen ink-trim validation completed

All 54 new scan-first slots are accounted for: **52 labelled words and two
unavailable positions**. After locking labels and evaluator, both broad and
conservative methods improve from **46/50 to 48/50** fixed-edge passes, or
**47/51 to 49/51** exact all-ownership boundary passes. There are two rescues
and no regressions; all four methods retain 52/52 correct centers.
The two remaining failures include neighboring/marker ink that trimming
preserves. One boundary stays unscorable. These are dependent, single-reader,
structured-sample results, not full-corpus segmentation accuracy; the full
comparison and retained failures are appended to `docs/AUDIT.md`.

### 2026-10-19 — automatic ownership evidence exposes additional limits

A separate development audit tests neighboring-word and cached-rosette
masks across all earlier cohorts. Neighbor masking leaves the two retained
contamination failures unresolved and creates a **new p321 center error**.
A full-height rosette-column mask clears p366's edge-tolerance failure while
clipping **four legitimate target pixels**. Exact conditional edge ranges
make that ambiguity explicit; they do not certify linguistic ownership.
The locked fresh results above are preserved. No masking rule is adopted;
details and counterexamples are appended to `docs/AUDIT.md`.

### 2026-10-19 — scan components can represent the reviewed in-box masks

The next development diagnostic reconstructs connected ink components in
all 470 earlier context/reference frames on 71 pages. All **50 clear v6
in-box manual target masks** can be represented exactly by keeping/removing
whole components, for both 4- and 8-connectivity and crop/page frames.
This is an oracle representability result: the correct component choices
come from existing manual references, not an automatic ownership rule.
The p36 neighboring ink and p366 marker/stop sign occupy components separate
from their targets. Reproducible component inventories and visual reviews
are documented in `docs/AUDIT.md`.

### 2026-10-19 — follow-up: rare random selection can be easy to construct

The audit conclusion is committed as **df4ea4f**. A separate, pre-specified
fixed-geometry diagnostic constructs an exact column-maximizing selection on
the same 587-page raw-site pool, preserving each page's selected count.
It aligns **4,671/4,682 components (99.77%)**, versus 3,522 observed column
flags. The uniform-label probability of reaching this maximum is about
**10^-2267.51**, yet a deterministic algorithm constructs it directly.
It changes the selected sites freely and has zero mirror flags: this is
neither Quranic composition nor a reproduction of the joint observed pattern.
The result demonstrates why random-selection rarity alone does not measure
construction difficulty. Methods, all outcomes and causal-inference limits
are in **[the research ledger](RESEARCH.md)**.

### 2026-10-19 — actual same-word geometry, independent of color selection

The new word-level analysis identifies occurrences from the exact Quran text
and measures their mapped positions without consulting word ink color. On
different rows of the same page, with center separation at most 15px:

- Exact standalone **الله: 1,717/2,151 mapped occurrences align (79.82%)**;
  the scanned-verse inventory contains 2,152 expected occurrences.
- Preserving each word's page/row counts gives a 16.68% reference mean;
  additionally preserving coarse width-bin counts gives **36.96%**.
- Exact-rational expectation checks and an independent-page Hoeffding
  certificate give **P(T >= 1,717) < 10^-57** under the width-conditioned
  word-position model. This is a conditional upper bound, not origin odds.
- The separately defined Allah-name family gives **2,278/2,695 (84.53%)**,
  versus a width-conditioned mean of 41.72%. Prefixed forms remain distinct
  in the primary identical-spelling inventory.

All 77,404 expected verse-token identities are accounted for: 76,511 mapped,
893 unresolved. Unencoded head basmalas are outside this primary inventory.
Exact-surface filtering leaves the standalone-Allah result unchanged. Full
per-word counts, retained non-significant results, simulation replay, bounds
and location limitations are in **[the research ledger](RESEARCH.md#2026-10-19--color-independent-same-word-alignment)**.

### 2026-10-19 — origin-question status and new-session checkpoint

The current findings establish a substantial same-word geometric association
under explicit comparisons. They do not establish or disprove divine origin,
and no numerical probability of divinity has been estimated. The missing
origin-likelihood comparison is set out in [DIVINE-ORIGIN.md](DIVINE-ORIGIN.md).
The next bounded research gate preserves the actual text/order and documents
the writing model's remaining freedom; the pilot scope, inputs, checks and
commands are recorded in [RESEARCH.md](RESEARCH.md#2026-10-19--textorder-preserving-six-page-spacing-pilot).

### 2026-10-19 — text/order-preserving spacing pilot

The six-page pilot now preserves actual word order, detector widths, rows and
line extents while equalizing or permuting gaps. **58/89 rows** are feasible;
overlaps and missing/uncertain words are retained as exclusions. On eligible
rows, standalone Allah gives **7/13 aligned**, versus **5.5284** under spacing
permutations (1,643/5,000 trials reach 7). Pooled identical words retain a
residual: **28 versus 21.5968** (15/5,000 trials reach 28).

This limited interval model inherits the print's widths and line breaks and
does not render Arabic glyphs or verse markers. It is a development spacing
diagnostic, not a historical production model or divine-origin proof. The
whole-corpus same-word result above remains a separate finding. All outcomes,
coverage, exact freedom ranges and next-step decision are in
[RESEARCH.md](RESEARCH.md#2026-10-19--textorder-preserving-six-page-spacing-pilot).

```bash
python tools/text_layout_comparator.py --verify
python tools/text_layout_review.py --verify
```

### 2026-10-19 — alignment beyond Allah: words and multiword phrases

The new color-independent inventory finds **580 aligned exact word types
beyond Allah-name forms**, plus **396, 171, 75, 30 and 13 aligned repeated
phrase types** of lengths 2–6. A strict phrase match requires **every
corresponding word center within 15px**, not just the phrase midpoint.

A text/order-preserving corpus spacing diagnostic retains an excess across
all six lengths: for example, **641 two-word phrase occurrences align versus
a 335.06 spacing mean**, and **106 four-word occurrences versus 37.16**.
These refer to the eligible-row subset. Full counts, exclusions, finite-MC
uncertainty, multiplicity handling, scan examples and model/origin limitations
are in **[PHRASE-ALIGNMENT.md](PHRASE-ALIGNMENT.md)**. The broader phenomenon
is supported; divine causation remains unresolved.

```bash
python tools/broad_phrase_alignment.py --verify
python tools/broad_phrase_review.py --verify
```

### 2026-10-19 — stronger phrase-aware controls

Preserving verse-boundary gaps and the observed internal geometry of repeated
phrase blocks leaves a residual for single words and two-/three-word phrases,
but no four- to six-word excess under that stronger conditional model.
Exact certificates show that its five-/six-word scores are fixed under every
permitted gap permutation: these controls inherit the phrase geometry rather
than independently explaining its origin. Full outcomes, remaining freedom
and independently sourced nineteenth-century-copy leads are appended to
[PHRASE-ALIGNMENT.md](PHRASE-ALIGNMENT.md#2026-10-19--stronger-verse-aware-and-repeated-phrase-controls).
Divine design remains unresolved; no historical comparison copy was scored.

### 2026-10-19 — dated historical copy inspected

**[Columbia MS Or 422, catalogued 1779](HISTORICAL-COPY.md)** now provides
an inspected pre-project copy and colophon. Six folios were fixed before viewing
images. For the same **33 canonical Allah-family names**, its descriptive
midpoint score is **8/33**, versus **27/33** in the modern print at 2% of text-
frame width. Coarse historical coordinate allowances give a **0–14** envelope;
measurement methods and page/row layouts differ. All pages and acquisition
corrections are retained. This adds historical evidence and shows presentation
dependence; it does not identify the Quran's origin or provide an origin probability.

### 2026-10-19 — positive historical phrase evidence and measurement review

In the catalogued **1779** copy, both occurrences of **`من دون الله` (29:17)**
on **200r, rows 3/4**, align word by word within **1.5%** of text width. The
Allah pair also survives the declared coordinate allowances at 2%; the full
phrase does not survive every allowed perturbation. A shared manual-center
review corrects two old historical locations and gives **10/33** historical
name-family alignments versus **27/33** modern at 2%, superseding the earlier
historical **8/33** development number. See
[the review and reproducible case](HISTORICAL-COPY.md#2026-10-19--shared-center-review-and-a-positive-historical-phrase-example)
and [the supporting-evidence synthesis](DIVINE-ORIGIN.md#2026-10-19--focus-the-strongest-supporting-observations-so-far).
This adds concrete pre-project phrase evidence; divine-origin inference
still requires a comparison with independently justified writing/copying rules.

### 2026-10-19 — second historical copy and GPU OCR

Five folios fixed before inspection in **Columbia MS Or 91 (catalogued 1776,
18-line naskh)** contain **38/66** aligned Allah-family names at 2% of text
width, with **10 endpoints** surviving the stated working coordinate allowances.
The ordinary phrase **`واذكر في الكتاب`**, without Allah in the measured phrase,
also aligns word by word at 1.5% on 99r. Local GPU OCR aided reading; every
scored name was checked against the scans and canonical text. All pages and
an unsuccessful repeated-phrase case are retained. See
[the complete historical extension](HISTORICAL-COPY.md#2026-10-19--second-copy-1776-manuscript-local-gpu-ocr-and-ordinary-phrases).
This strengthens the evidence for pre-project word/phrase alignment across
different hands and layouts; its divine-origin explanation remains open.

### 2026-10-19 — corrected second-copy endpoint

An enlarged all-name review corrects 17 first-pass intervals. **Current MS Or 91
family alignment is 34/66 (51.52%), with 10 endpoints surviving the stated
coordinate allowances**, superseding the preceding 38/66. The ordinary
`واذكر في الكتاب` phrase example remains unchanged. Current replay:
`python tools/historical_extension_final_review.py --verify`.
See [the correction and complete outcomes](HISTORICAL-COPY.md#2026-10-19--final-enlarged-context-correction-current-second-copy-results).

### 2026-10-19 — superseded article drafts (retired at open-sourcing)

Three intermediate drafts — the findings article
(`tawafuq-findings-2026-10-19.{md,pdf}`), the illustrated five-page layman
companion (`tawafuq-layman-v2-2026-10-19`) and the V3 outline draft
(`tawafuq-v3-2026-10-19`) — were removed from the repository, together with
their figure sets under `docs/articles/figs/`, to avoid confusion with the
current article; drafts, figures and sources.json provenance remain in git
history. Their builders (`tools/build_findings_article.py`,
`tools/build_layman_article.py`, `tools/build_article_v3.py`) are kept for
provenance and need those retired assets (or local scans) restored first.
The article as of that date was the root `README.md`, converted from
`docs/articles/tawafuq-art-v7-structure.json`.

The findings article's central proposal stands: *Can an independently
specified, text-preserving writing process reproduce comparable alignment?*
It opens with Quran **2:23**, distinguishing the proposed alignment test
from the verse's broader challenge. The protocol is a proposal; no
submissions have been evaluated, and it does not claim that divine authorship
has been proved.

### 2026-10-22 — article v9 (short edition) rebuild

The published `README.md` is now converted from
`docs/articles/tawafuq-v9-structure.json`, extracted from the user-edited
ODT `docs/articles/tawafuq-v9-short.odt` (short edition: headline numbers
table, reproduction steps, null-model and literature sections removed;
title/byline updated). The v7 structure JSON stays in the tree for
provenance. `media/` now carries the 10 figures the v9 article references
(the unused `fig_types.png` / `fig_sensitivity.png` files were removed
from both `media/` and `docs/articles/figs/`; `tools/make_figs.py` can
regenerate them).
The 19er section was reworded and then trimmed to two results in the ODT
itself (one `P11` body paragraph split into four, verified by re-extraction:
structure items 117 → 119), and the structure JSON was regenerated from the
accepted ODT, so the ODT, the structure JSON and the README carry the same
reviewed text. The same edit pass shortened the conclusion and updated the
story's model credits. Two README-side blocks remain builder-injected — the
about box and the numbers-provenance curation note — plus the historical
`CURATION_FIXES` record (a no-op on the current structure); each is a
documented divergence, not a silent edit. Verification entry point and proof
scope are unchanged: `python tools/verify_cpu.py`.
