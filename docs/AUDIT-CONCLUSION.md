# Audit conclusion — 2026-10-19

**Status: the bounded audit pass is closed.** The audited code/data checkpoint
is **`01cbb77`**, following the original audit baseline `bea87f3`.
The chronological evidence, repairs, retained failures and reproduction
commands remain in [AUDIT.md](AUDIT.md).

## Bottom line

**A substantial colored-component alignment excess survives the corrections
and basic reference-population controls.** Its scores and specified-model
probability bounds are reproducible. The earlier headline probabilities,
semantic generalizations and human/AI construction-impossibility conclusions
are not validated by this audit.

We can finish checking the existing claims without first solving automatic
Quran-wide word segmentation or establishing a causal explanation. Those are
follow-up research questions with their own validation requirements.

## 1. What survived, changed, or was withdrawn

Here, **withdrawn** means withdrawn as a supported conclusion of this project;
it does not assert that the opposite proposition has been proved.

| earlier claim or assumption | closing disposition | evidence |
|---|---|---|
| A large alignment excess exists in the printed colored ink. | **Survives at image-component level.** Rebuilt v3: 3,339/4,582 = 72.87% aligned, versus a 26.22% simulated mean under the stated page-slot model. | [Rebuilt extraction](AUDIT.md#rebuilt-extraction-result); [saved run](../tools/data/audit_global_v3.json). |
| Could comparing merged observations with raw fragments account for the excess? | **That mismatch alone is insufficient.** A same-unit, size-filtered, non-gold raw-site control gives 76.68% versus 27.94%; fixing line counts gives 29.08%. These controls still concern components. | [Unit-consistent controls](AUDIT.md#closer-controls-retain-the-component-position-association); [artifact](../tools/data/audit_reference_controls.json). |
| The historical global tail is about 10^-985, with combinable per-type “bits.” | **Withdrawn as validated inference.** Scoring/counting errors and unjustified flag independence invalidate that presentation. Replacement exact-rational bounds apply to precisely specified column-only component models. | [Dependence counterexample](AUDIT.md#why-individual-aligned-word-binomial-tails-are-not-justified); [exact proof](AUDIT.md#exact-per-page-distributions-much-stronger-proof-without-extrapolation). |
| The alignment rate measures an exact census of crimson divine-name words. | **Withdrawn.** Components can be letters, words, marks, fragments or merged observations; archived shape classes are not certified word identities. | [Reference-population diagnosis](AUDIT.md#the-initial-reference-population-is-not-a-neutral-word-model). |
| The Allah count is 2,696 encoded / 2,808 with opening basmalas. | **Corrected:** 2,699 encoded, or 2,811 including the 112 additional unencoded surah-head basmalas. These are corpus conventions, not detected scan counts. | [Census correction](AUDIT.md#2026-10-18--divine-name-count-corrected); [counter](../tools/divine_census.py). |
| p422 has the claimed narrow 12-of-16 Allah column, plus Hu. | **Not reproduced as stated.** The narrow 12-component column contains 11 Allah forms and Hu; the page has 16 Allah forms overall. | [Independent transcription](AUDIT.md#independent-p422-transcription-corrects-the-showcase-premise); [annotation](../tools/data/audit_manual_page422.json). |
| The showcase pages combine to an established Fisher probability of 1.65×10^-31. | **Withdrawn as validated inference.** The combination arithmetic can be reconstructed; its input events, dependence and selection correction are not established. | [Showcase inference](AUDIT.md#showcase-inference). |
| Word-identity tests are negative at every grain, demonstrating no word-specific structure. | **Withdrawn.** The old sweep had page/bin/mirror defects; corrected exploratory crimson tests show excess at several grains under a global-label model. Semantic labels, language controls and multiplicity remain unresolved. | [Recomputed identity tests](AUDIT.md#recomputed-conditional-identitymirror-tests); [grain artifact](../tools/data/audit_grain_sweep_v3.json). |
| The narrow facing-page break-band mirror test finds no excess. | **Narrow negative survives:** the corrected v3 test gives 28 hits versus a reference mean of about 31.85 on 288 spreads. This does not establish absence of other alignments. | [Recomputed mirror test](AUDIT.md#recomputed-conditional-identitymirror-tests); [artifact](../tools/data/audit_page_turn_v3.json). |
| Rosette sequence consistency establishes ground truth and 99.4% accuracy. | **Withdrawn as corpus-wide certification.** The repaired map improves the independently transcribed p567 from 12/28 to 28/28; that is a limited page check. | [Rosette validation](AUDIT.md#rosette-fixes-independently-checked-against-p567); [artifact](../tools/data/audit_rosette_labels_v3.json). |
| Count matching proves complete marking and eliminates editorial selection. | **Withdrawn.** Explicit unknowns, missing supports and wrong accepted locations remain; complete token-ID coverage is not verified geometry or marking completeness. | [Pin limitations](AUDIT.md#basmala-and-pin-defects-found-during-the-rebuild); [targeted site review](AUDIT.md#2026-10-18--targeted-omissionconflict-review-and-a-wrong-accepted-name). |
| Word geometry is mathematically unrecoverable because of kashida. | **Withdrawn.** Failures of earlier algorithms do not prove impossibility; later OCR/corpus mapping achieves useful sampled localization, with documented boundary failures. | [Earlier algorithm defects](AUDIT.md#additional-repairs-and-qualification); [frozen word validation](AUDIT.md#2026-10-19--completed-scan-first-validation-of-the-frozen-ink-trim-candidate). |
| Random page-probability products establish human/AI impossibility or divine origin. | **Withdrawn as a conclusion of these calculations.** A random-label/placement model is not a construction/search model; retained-page retries alone invalidate interpreting a one-shot product as work. | [Construction counterexample](AUDIT.md#page-probability-products-are-not-construction-work-estimates). |

## 2. What is mathematically verified—and under which model

The versioned global score flags a component once if it has either a
different-line partner in its fixed 30px column bin or a nominally reflected
neighbor-page cell partner. These bins are not sliding ±15px windows. Mirror
coordinates use the specified nominal 1024px frame; physical registration of
different scans is a separate issue. See [alignment.py](../tools/alignment.py).

For column-only scores, integer generating-function dynamic programming
counts every allowed within-page slot subset. With independent page draws,
the exponential Markov calculation gives an **exact rational upper bound**:

| fixed reference model and observed column score | verified conservative bound | proof artifact |
|---|---|---|
| Initial v3 merged observations against raw slots; 3,271 column flags | P(X ≥ 3,271) < 2×10^-726 | [audit_exact_columns.json](../tools/data/audit_exact_columns.json) |
| Same-unit size-filtered non-gold raw sites, uniformly relabelled within each page; 3,522 column flags | P(X ≥ 3,522) < 10^-814 | [audit_exact_columns_raw_wordlike.json](../tools/data/audit_exact_columns_raw_wordlike.json) |

These are **upper bounds, not exact tail probabilities**. They apply to the
listed column events and reference populations—not directly to the union
percentages, a neutral word-layout model, all exploratory choices, or a
probability of human manufacture or divine origin. Bounds from overlapping
analyses must not be multiplied into a combined claim.

The stronger geometry-conditioned controls are important to the conclusion.
On the same raw-site population with 76.68% observed union alignment, the
analytic reference mean rises to **38.82%** with coarse width/height
conditioning and **69.43%** with line, edge role and width/height conditioning.
The latter fixes **83.53% of selected labels at their original sites**.
It still has zero column/union exceedances in 5,000 simulations, but its
neighbor-mirror statistic has 718/5,000 exceedances. See the
[control definitions and full table](AUDIT.md#results-larger-reference-means-residual-column-association)
and [artifact](../tools/data/audit_geometry_controls.json).

Thus both the remaining association and the sensitivity to the model belong
in the headline. The 10^-814 bound is **not** a bound for the tighter
geometry-conditioned model. Zero simulated exceedances do not mean p=0;
the exact-rational proof is a separate analytic result, not an extrapolation
from those simulations.

## 3. Where word-level validation ended

The audit progressed beyond reviewing the old code: all 604 pages now have
a cached OCR inventory, with versioned exact-corpus anchoring and explicit
ambiguity/abstention policies. That is useful research infrastructure, not
a certified word-by-word transcription or segmentation.

The latest frozen-rule, scan-first v6 comparison accounts for all **54
scheduled positions**: 52 labelled words and two physically unavailable
slots. Its single AI reader saved the labels and evaluator lock before
opening the selected predictions. On this structured six-page sample:

- All four compared methods locate **52/52 centers** correctly.
- Horizontal ink trimming improves fixed-edge passes from **46/50 to 48/50**,
  and all-allowed-manual-ownership passes from **47/51 to 49/51**.
- There are two boundary rescues, no observed paired regressions, two retained
  failures and one boundary-unscorable word.
- Broad and conservative predictions coincide here; their identical scores
  are not independent replications. A 12px boundary pass does not establish
  complete pixel preservation.

The [locked comparison](../tools/data/audit_word_ink_trim_fresh_validation_v6.json)
remains the fresh result. Subsequent v7/v8 analyses are **exposed development**:

- [Rectangle-mask evidence](../tools/data/audit_word_ownership_evidence_development_v7.json)
  retains the p321 center regression and p500/p366 target-ink clipping harms.
  No rectangle-subtraction repair was adopted.
- [Component separability](../tools/data/audit_word_ink_components_development_v8.json)
  covers 470 context/reference measurements on 71 pages. All 50 clear v6
  in-box manual masks can be represented exactly by keeping/removing whole
  connected components, in crop/page frames and 4/8-connectivity. Correct
  component choices come from the manual reference: this is an oracle
  representability result, not automatic accuracy or outside-box recovery.

These structured, single-reader samples and overlapping development cohorts
do not supply an independently double-annotated corpus accuracy estimate.
Automatic component-to-word ownership is the next research problem, not an
unfinished arithmetic check needed to close this audit.

## 4. Completion boundary and reproducibility

This pass has an explicit disposition for the central historical numerical
and interpretive claims: retained with a defined scope, corrected, withdrawn
as supported inference, or left unestablished. Known failures and earlier
frozen reports remain available. Closure does not certify every exploratory
script, all historical-source assertions, archived article/PDF outputs, or
all 604 pages' linguistic labels.

At code/data checkpoint `01cbb77`:

- **145 tests pass; 139 Python files parse.**
- The complete quick CPU verifier passes, including independent reference
  scoring, exact-rational proof reconstruction, input hashes and derived
  outcomes for the earlier frozen reports and v7/v8 diagnostics.
- Separate scan replay reconstructs all 470 v8 component measurements;
  earlier scan validations and full simulation replays are recorded in the
  chronological audit. Quick verification checks saved simulation inference;
  it does not rerun every simulation.

Reproduce the checks with:

```bash
. .venv/bin/activate
python tools/verify_cpu.py
# With the hash-matched source scans:
python tools/word_ink_trim_fresh_validation.py --verify --scans
python tools/word_ownership_evidence_audit.py --verify --scans
python tools/word_ink_component_audit.py --verify --scans
# Optional full deterministic replay of global component-null simulations:
python tools/verify_cpu.py --full
```

Use the pinned [audit requirements](../requirements-audit.txt). Long runs
should use `setsid` and logs under `logs/`, as described in the
[reproduction guide](VERIFY.md).
Scan-free replay needs neither paid OCR access nor credentials. The scans
are not distributed in git; see [obtaining the scans](DOWNLOAD-HAYRAT.md).

## 5. Follow-up research, with separate completion gates

The following are a new phase, not conditions that keep this audit open:

1. **Word ownership and validation.** Define a versioned component-to-word
   policy with explicit ambiguous/unassigned ink, including auxiliary marks,
   adjacent words and outside-box omissions. Retain the known regression and
   clipping counterexamples. Freeze inference and evaluation before new
   untouched validation; obtain independently checked annotations and report
   errors, abstentions and coverage separately. Completion means a documented
   validation result against predeclared criteria, not an endless cycle of
   repairing only the latest exposed examples.
2. **Linguistic/layout controls.** Specify the question and comparator before
   calculating a new headline probability. Address word frequency, width,
   morphology, line/verse position, marking selection and relevant edition/
   layout differences; quantify how much freedom conditioning leaves. This
   work must establish which alternatives a test can actually distinguish.
3. **Current publication.** A corrected account of the component-level findings
   and audit corrections can be written now. New semantic, selection,
   construction or origin claims need their own evidence before inclusion.
   Archived articles are historical records,
   not the current publication source.

Reopen this audit if a concrete defect changes an audited score, bound,
provenance or validation statement. New hypotheses and algorithm improvements
receive new versioned studies. The current result is a reproducible
component-level association with explicit model dependence; its stronger
linguistic and causal interpretation remains open.

## 2026-10-19 — follow-up research pointer

After this bounded audit closed, a separate color-independent **same-word**
study found standalone Allah alignment of 1,717/2,151 mapped occurrences,
versus a width/row-conditioned mean of 795.04 and a conservative conditional
Hoeffding bound below 10^-57. See [RESEARCH.md](RESEARCH.md) for full methods,
coverage, counter-results and verification; this does not retroactively change
the original audit checkpoint. The current origin-question assessment is in
[DIVINE-ORIGIN.md](DIVINE-ORIGIN.md); further scoped work is tracked in
[RESEARCH.md](RESEARCH.md). Divine origin remains unresolved.
