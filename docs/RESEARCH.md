# Follow-up research

The bounded audit closed at code/data checkpoint `01cbb77`; its synthesis is
[AUDIT-CONCLUSION.md](AUDIT-CONCLUSION.md), committed with the closure notices
as **df4ea4f**. This ledger records separately scoped research after that pass.

## 2026-10-19 — one-shot rarity versus constructive component selection

### Question and protocol

Does an extremely small uniform-label probability establish that constructing
a high alignment score is computationally difficult? The
[local plan](../tools/data/research_constructive_selection_plan_v1.json)
was saved before the first construction run. It fixes the population,
objective, algorithm, tie-breaking, reported measurements and scope. This
is an exposed-data model diagnostic, not new independent validation or an
externally registered protocol.

Use the unchanged size-filtered, non-gold raw-component reference pool:
**587 eligible pages, 76,375 sites and 4,682 selected components**. Preserve
the existing number k of selected components separately on every page.
Coordinates, eligibility rules and the versioned column score remain fixed.
The constructor receives only site geometry, k and the scoring parameters;
observed red-site indices and Quranic token identities are not supplied.

### Constructive algorithm and exact optimum

For each existing column bin, let its capacity be m. If it contains sites on
at least two lines, any count j with 2 ≤ j ≤ m can achieve score j: choose
two different-line sites, then fill the other j−2 positions arbitrarily.
Every selected site then has a partner on another line in that bin.
Choosing zero or one site scores zero; any selection confined to a bin
containing only one line also scores zero.

Column contributions are additive across bins. Dynamic programming over
bins and used-site counts therefore finds an exact maximizing k-subset,
with a deterministic witness. This is polynomial-time optimization, not
repeated random attempts. Stable site-index ordering and first-maximizer
tie-breaking make the construction reproducible.

`constructive_selection.py` independently checks every witness by scalar
pair enumeration and batched occupancy scoring. Each page maximum must also
equal the largest occupied score in the previously audited integer-PMF
artifact [audit_exact_columns_raw_wordlike.json](../tools/data/audit_exact_columns_raw_wordlike.json).
That artifact is used only after selection, as an evaluation oracle. The
full CPU verifier reconstructs its distributions from the input sites.

### Results, including the unoptimized mirror score

| unchanged statistic | observed raw-site labels | constructed labels |
|---|---:|---:|
| selected components | 4,682 | 4,682 |
| column-aligned components | 3,522 (75.22%) | **4,671 (99.77%)** |
| neighbor-mirror components | 288 | **0** |
| column/mirror intersection | 220 | 0 |
| column-or-mirror union | 3,590 (76.68%) | **4,671 (99.77%)** |

All selected sites are column-aligned on **576/587 pages**, including ten
zero-count pages. Among the 577 nonempty pages, **566** have all selected
components column-aligned. Each of the remaining eleven pages has exactly
one selected component, which cannot have a same-page partner. Every page's
constructed score is the exact maximum for its fixed count and geometry.
The artifact reports every page, including these exceptions, with filtered-
reference-site indices and selected coordinates. No page or unfavorable
statistic is removed.

The optimizer considers **594,589 dynamic-programming candidate transitions**.
This counts candidate updates, not all CPU operations, human work or historical
production effort. A complete standalone verify/reconstruction run took
**1.310 seconds wall time** on this machine, including loading and hashing
inputs, construction, scalar/batched scoring and exact probability accounting.
This is a single local timing, not a portable performance guarantee; it
checks the stored PMFs rather than rebuilding their integer coefficients.

### Exact random-selection probability of the constructed maximum

Let a_p be the maximum column score on page p, and let c_p(a_p) be its exact
subset count among C(S_p,k_p) possible selections. Since every page score
is at most a_p, the total reaches sum a_p iff every page reaches its own
maximum. Under independent uniform page selections,

    P_R(total column score = sum_p a_p)
        = product_p c_p(a_p) / C(S_p, k_p).

The result is stored as an **exact rational number**, with a display
log10 probability of **−2267.513177…**, approximately **10^-2267.51**.
This is the probability of the **maximum-score event**, including all
maximizing subsets—not the probability of one prespecified coordinate list.
It is about the synthetic construction; the actual observed labels do not
attain that maximum. It is **not a new probability for the Quran**.

The deterministic constructor reaches this event directly on the supplied
geometry. Thus one-shot probability and constructive difficulty differ
dramatically even for an event defined by this project's own statistic.
The old exact uniform-null bounds remain mathematically intact; the new
result limits interpreting them as construction/search difficulty.

### What this changes—and what it does not establish

This is an explicit counterexample to the general inference
**“tiny probability under uniform random selection implies no efficient
algorithm can achieve the score.”** It also demonstrates that the basic
component statistic leaves substantial room for deliberate selection.

The construction freely changes which sites are labelled. It does not
preserve Allah-name locations, actual ink-color semantics, per-line red
counts, exact width/morphology distributions or observed mirror counts.
It uses the already supplied geometry of this print. Therefore it neither
composes Quranic text nor reproduces the joint observed structure, and is
not a calibrated explanation of the actual marking/layout process. It
proves neither human authorship nor the absence of divine origin.

### Can all findings together give an origin probability?

The audited small tails concern a specific model R of component placement
or labelling. They are not P(evidence | every explanation without Allah),
and they are not P(no Allah | evidence). A naturalistic account need not
sample atoms, letters or layout sites independently and uniformly; it can
include learned language, intentional choices, revision and selection.
Which processes explain this particular text and print remains a separate
empirical question.

For illustration of the missing inference, if G and N were two exhaustive
origin hypotheses, Bayes' rule would require

    P(G | E) = P(E | G) P(G)
               / [P(E | G) P(G) + P(E | N) P(N)].

Neither origin likelihood nor the prior odds is supplied by this study.
A small upper-tail probability under R cannot substitute for them. Even
an adequately specified pair of origin models would need a defined evidence
event, dependence/selection accounting and independently justified likelihoods.
The existing tests share scans, extraction, labels and related statistics;
their probabilities cannot simply be multiplied as independent findings.

Likewise, a claim that **no human or AI could ever compose the Quran** would
need a specified composition task, admissible resources/constraints and a
valid lower-bound or impossibility argument. Neither a failed OCR method nor
a uniform-placement tail provides that argument. This study's easy component
selection is not a solution to that much larger composition task either.

There is no defined probability distribution behind “random atoms conspiring”
in the current analysis, and no quantitative irrationality or “craziness”
measure for accepting or rejecting a worldview. A numerical value would be
invented rather than measured. The defensible scientific claim remains the
observed geometric association, explicitly conditional model rejection and
the limits of those models; its religious interpretation is not settled by
these calculations.

### Reproducibility and next gate

```bash
. .venv/bin/activate
python tools/constructive_selection.py --verify
python -m unittest discover -s tools -p test_constructive_selection.py -v
python tools/verify_cpu.py
```

The [result artifact](../tools/data/research_constructive_selection_v1.json)
contains every page witness, exact maximum-event probability, plan/source
hashes and input manifests. Five new tests independently enumerate every
fixed-site subset of a 2-line/3-column frame and every k, checking all
possible selected subsets against the constructed optimum. They also cover
duplicate sites, single-line bins, changed clipping, exact joint probability,
deterministic ties and invalid inputs. The study is integrated into the CPU
verifier. No new scan annotation, OCR request or external service was used.

Logs: `logs/constructive-selection-build-v1.log`,
`logs/constructive-selection-verify-v1.log`,
`logs/constructive-selection-timed-replay-v1.log`, and
`logs/constructive-selection-cpu-v1.log`.

This study's completion gate is the verified fixed-population construction
and its probability accounting. A next study should specify semantic or
line/geometry constraints **before** measuring feasibility. Freely relabelled
components cannot answer those stronger questions; they require the separate
ownership and linguistic-control validation described in the audit conclusion.

Verification: **150 tests pass**, **141 Python files parse**, and the complete
quick CPU verifier passes, including the new construction and all earlier
frozen reports. Standalone reconstruction reproduces every witness and the
exact rational probability. The observed input geometry and earlier audit
artifacts are unchanged. Research after df4ea4f is uncommitted.

## 2026-10-19 — color-independent same-word alignment

### The object measured is the word, not its ink color

At the user's request, this study directly measures the positions of
**identical Quranic words**, including occurrences with no located partner.
It does not select colored components or use semantic ink pins. The earlier
constructive-selection experiment addresses a different component-selection
problem and neither reproduces nor explains this same-word statistic.

The [local plan](../tools/data/research_same_word_plan_v1.json) was saved
before the first same-word count and comparison runs. The source is the
unchanged exact corpus and frozen conservative v5 OCR-to-word mapping.
The analysis has a complete identity ledger for **77,404 expected verse
tokens and 14,805 unvowelled spelling types**. It locates **76,511** tokens;
**893** remain unresolved (854 without a conservative site; 39 without a
mapped token). Coverage is not a measured location-accuracy rate.

Fatiha is absent from the scanned input, so its tokens are excluded. The
112 synthetic, unencoded surah-head basmalas are excluded from this primary
**verse-token** analysis rather than mixed with canonical verse IDs. Thus
these counts are not an inventory of every printed head-basmala occurrence.

Word identity removes the existing diacritic/tatweel mark set and maps
alif-wasla to alif, while retaining prefixes, hamza, ta-marbuta and
alif-maqsura distinctions. For example, `الله`, `والله` and `بالله` are
different exact spellings. The explicitly separate Allah-name family uses
the existing declared name-form predicate; it is not an exact-spelling test.

No word-ink color is consulted for occurrence selection, row assignment,
center geometry or scoring. The upstream OCR was run on the original scans
and uses the existing gold-ornament exclusion; this is not a new grayscale
OCR experiment or a claim that recognition quality is independent of ink.

### Frozen statistic and comparison models

For a located occurrence i of spelling w, flag it once when there exists j
such that:

    spelling_i = spelling_j = w
    page_i = page_j
    seeded_row_i != seeded_row_j
    abs(center_x_i - center_x_j) <= 15 pixels.

Centers use the original OCR detector/support boxes, without color-based
ink trimming. Integer twice-center coordinates preserve half pixels exactly.
The output retains all matching token-ID pairs, unique aligned endpoints,
every located-but-unpaired token, and every unresolved token. Multiple
partners do not multiply an endpoint's score. This study does not count
facing/back-to-back/cross-page matches or search for a favorable tolerance.

Two conditional reference models use the **same accepted word sites**:

1. **Page + row:** uniformly exchange word identities among sites within
   each page and row. Every word's observed count on every row stays fixed.
2. **Page + row + width:** additionally restrict exchanges to
   `floor(box_width / 20)` bins, preserving each word's coarse width-bin
   counts on each row.

These are hypothetical word-position comparisons, not ink-color permutations.
They preserve the declared counts and geometry, but not canonical text order,
syntax, exact glyph morphology, or the actual writing process. Their tails
are conditional model results, not text-composition or divine-origin odds.

### Observed same-word alignment and analytic reference means

Percentages below use located occurrences of the indicated group.

| group | aligned / located | observed | page + row mean | page + row + width mean |
|---|---:|---:|---:|---:|
| exact standalone `الله` | **1,717 / 2,151** | **79.82%** | 16.68% | **36.96%** |
| all identical spellings, pooled endpoints | **6,580 / 76,511** | **8.60%** | 2.62% | **4.98%** |
| exact `الرحمن` | 16 / 43 | 37.21% | 3.79% | 18.35% |
| exact `الرحيم` | 2 / 32 | 6.25% | 0.98% | 3.13% |
| separate Allah-name family, including prefixes | **2,278 / 2,695** | **84.53%** | 20.38% | **41.72%** |

Standalone Allah is **2.16 times** the width-conditioned mean, an excess
of **42.86 percentage points**. The family rate is **2.03 times** its
width-conditioned mean. All-identical-word pooling does not imply that every
word type has an excess; the full per-spelling table is retained.

The expected canonical counts are **2,152 standalone Allah** and **2,697
Allah-family verse occurrences**. The automatic view leaves two family
locations unresolved: `والله` at **3:148** (t8595, p67 in the earlier review)
and `الله` at **10:18** (t26611, p209 in the earlier review). Existing manual
name cores are not silently substituted into this automatic study. A mapped
occurrence without a mapped partner is not proof that no true partner exists.

The family score permits different declared prefixed forms to be partners;
the exact standalone score does not. Family positions are whole-token box
centers, not separately measured subword centers of the Allah letters.

### Probability calculations: simulation and a separate mathematical bound

Each model has **5,000 replicates**, using the fixed seed and generator in
the plan. Standalone Allah, the family and pooled identical-word endpoints
have **zero exceedances** in both models. For these zero-exceedance cases,
the plus-one MC summary is **1/5,001**, and the one-sided 95% model-tail
upper confidence limit is about **0.000599**. This does not establish p=0
or estimate tails of size 10^-57 from 5,000 trials.

The secondary results are retained, including the weaker one:

- `الرحمن`: width-conditioned **5/5,000** exceedances, plus-one MC about
  **0.00120**.
- `الرحيم`: width-conditioned **2,549/5,000** exceedances, plus-one MC about
  **0.5099**. No convincing upper-tail excess in this comparison.

These are unadjusted conditional summaries of dependent metrics. The plan
declares standalone Allah and pooled identical-word endpoints as primary;
the two other spellings and broader name family are secondary. No tails
are multiplied, and comparisons do not become independent replications.

The analytic expectation is calculated independently of simulation. For a
candidate site i in stratum g with n_g sites and k_g occurrences of word w,
its inclusion probability is k_g/n_g. All eligible partners are on different
rows, hence in other independent strata. If m_h(i) sites in another stratum h
are within 15px, the exact probability of no word-w partner there is

    C(n_h - m_h(i), k_h) / C(n_h, k_h).

Multiply this avoidance probability across the other strata, subtract from
one, weight by k_g/n_g and sum over candidate sites. This computes the mean
without assuming endpoint flags are independent. Simulation means agree
with the analytic values within ordinary sampling uncertainty.

For the primary standalone statistic and secondary family statistic, a
separate exact-rational reconstruction verifies the expectations. If T_p
is the page score and k_p the fixed group count, then 0 <= T_p <= k_p and
page draws are independent. Hoeffding therefore gives

    P(sum T_p >= observed)
        <= exp[-2 (observed - E[sum T_p])^2 / sum k_p^2].

Conservative decimal certificates use **integer upper bounds on the exact
mean**, not a Gaussian tail or a floating-point extreme-tail extrapolation:

| model | statistic | observed | exact mean <= | certified conservative bound |
|---|---|---:|---:|---:|
| page + row | standalone Allah | 1,717 | 359 | **P(T >= 1,717) < 10^-124** |
| page + row + width | standalone Allah | 1,717 | 796 | **P(T >= 1,717) < 10^-57** |
| page + row | Allah-name family | 2,278 | 550 | **P(T >= 2,278) < 10^-131** |
| page + row + width | Allah-name family | 2,278 | 1,125 | **P(T >= 2,278) < 10^-58** |

The exact means and range sums are stored in
[research_same_word_exact_bounds_v1.json](../tools/data/research_same_word_exact_bounds_v1.json).
The certificate proves `ln(10) < 2303/1000` using a positive 31-term rational
exponential partial sum greater than 10, then checks the exponent inequality
with exact fractions. These are model-conditional upper bounds, not exact
tail probabilities, selection-adjusted global discovery probabilities or
probabilities of human/divine authorship.

### Missingness, method sensitivity and diagnostic review

Requiring exact normalized OCR surface agreement for **every** accepted word
keeps the standalone-Allah result **unchanged: 1,717/2,151**, with one
unresolved occurrence. It reduces the all-word inventory to 67,060 accepted
locations and the family to **2,692**, of which **2,274** align. This is a
separate coverage sensitivity, not an independent replication; only the
primary conservative view supplies the reported comparison simulations.

Existing, overlapping annotation cohorts are compared without updating
predictions or labels. In the primary view, the 111 earlier name labels give
111 located/correct centers; the 12 targeted name cases give 10 correct and
two abstentions; the latest 52-word v6 set gives 52 located/correct centers.
These exposed checks are not a new full-corpus accuracy certificate.

The stronger width model leaves **1,728/2,151 standalone-Allah occurrences
randomizable** and fixes 423 at their original sites. For the family, 2,131
are randomizable and 564 fixed. Its higher mean does not result from wholly
free movement, and the remaining association does not identify its cause.

`same_word_review.py` generates six earliest paired standalone-Allah examples
on distinct pages and six earliest unpaired examples on other pages. The 12
raw-scan sheets were inspected: the outlined target boxes contain Allah,
and the paired examples show the reported absolute centers. This is exposed
diagnostic review; an unpaired crop does not independently establish absence
of partners elsewhere on its page. Review manifests also retain all unresolved
name details and the randomization diagnostics above.

### Reproduction and interpretation

```bash
. .venv/bin/activate
python tools/same_word_alignment.py --verify
python tools/same_word_alignment.py --verify --full
python tools/same_word_exact_bounds.py --verify
python tools/same_word_review.py logs/same-word-review-v1
python -m unittest discover -s tools -p 'test_same_word*.py' -v
python tools/verify_cpu.py
```

Artifacts: the fixed plan, the complete
[occurrence/pair/comparison report](../tools/data/research_same_word_alignment_v1.json),
and the exact-rational bound certificates. Full replay reproduces **all
10,000 simulated assignments' metric scores** across the two models. Tests
use independent pair enumeration, exhaustive allowed permutations and exact
rational expectations on tiny frames. Source/input hashes bind the results
to the frozen maps, corpus, plan and prior annotation reports.

Logs: `logs/same-word-alignment-build-v1.log`,
`logs/same-word-alignment-full-replay-v1.log`,
`logs/same-word-exact-bounds-verify-v1.log`,
`logs/same-word-alignment-cpu-v1.log`; diagnostic sheets and manifests:
`logs/same-word-review-v1/`.

**This establishes a strong same-word geometric association in the mapped
verse occurrences, independent of selecting words by their color.** It is
more directly relevant to the user's claim than the earlier component-label
tests. It does not establish perfect alignment, complete word geometry,
layout invariance or a probability of divine origin. The next explanatory
comparison must preserve actual text/order and explicitly documented writing
constraints; it cannot be replaced by freely selecting other components.

Verification: **159 tests pass**, **146 Python sources parse**, and the
complete quick CPU verifier passes with the word ledger, both analytic models,
all earlier frozen reports and the exact-rational bound certificates. Full
same-word simulation replay reproduces all saved scores. The final unit-suite
rerun also passes after strengthening the within-stratum permutation test.
`git diff --check` passes. Research after df4ea4f remains uncommitted.

## 2026-10-19 — origin-question assessment and session transfer

The user requested a committed handoff and further resolution of the divine-
origin question. [DIVINE-ORIGIN.md](DIVINE-ORIGIN.md) records the current
scientific answer: a strong same-word association is established under the
declared comparisons; the origin question is **not resolved** by those
results. It gives the posterior-odds calculation and explains why no unique
probability of divinity follows from a benchmark-model tail bound. No
fabricated prior, origin likelihood or worldview-irrationality score is used.

The retired session handoff note (kept in git history) was the next-session
entry point. It preserved the
word-specific focus and defined one finite text/order-preserving layout
pilot on six already exposed pages, beginning with rendering feasibility
and explicit uncertainty. It does not treat a synthetic component selection
as an explanation of the actual word positions. Historical manuscript and
independent transcription comparisons remain separate evidence tracks.

The implementation and statistical reports are unchanged by these closing
documentation updates. All pending constructive-selection and same-word
research, reports and handoff documents are included in the research commit
prepared at session end; identify its final hash from git history. Earlier
dated statements about uncommitted work are historical checkpoints.

## 2026-10-19 — text/order-preserving six-page spacing pilot

### Question, freeze and feasibility

Continuing checkpoint **e16e19d**, the user requested further investigation
of divine design. This study completes the finite pilot specified by the
session handoff: can an explicitly constrained interval layout retain
same-word alignment while preserving the actual text and its order?

Development pages are exactly **36, 124, 298, 366, 500, 508**. They were
previously exposed in v6; they are not a fresh sample. The
[feasibility ledger](../tools/data/research_text_layout_feasibility_v1.json)
was constructed without calculating target alignment scores. It records
canonical IDs, seeded rows, widths, actual RTL gaps, missing internal tokens,
uncertain row/page boundaries, split supports and multiowner candidate regions.
No overlapping interval is clipped or silently converted to whitespace.

Of **89 rows containing mapped verse words, 58 qualify**, covering **534 of
822 located words**. Exclusion reasons overlap: 23 rows have overlapping
detector intervals, four have missing internal tokens, four touch uncertain
inter-row token boundaries, and one has an uncertain page-envelope boundary.
The 31 excluded rows and all their mapped words remain in the ledger.

The [separate plan](../tools/data/research_text_layout_plan_v1.json), candidate
source, evaluator, tests and input hashes were frozen before the first target
score. The plan is local, not an external preregistration. Its freeze command
refuses to overwrite an existing plan or result.

### What is fixed and what moves

Both comparators keep each eligible row's **canonical token identity/order,
page/row membership, original detector/support-box widths and outermost
word-box edges**. Only the n−1 nonnegative gaps change:

1. **Equal gaps:** replace them with their exact rational average.
2. **Empirical-gap permutations:** independently, uniformly permute the
   observed gap multiset within each row. The multiset and total spacing stay
   unchanged. There are **5,000 six-page trials**, PCG64 seed **20261020**.

Neither rule consults the alignment score. Original gap lists reconstruct
the original twice-center coordinates exactly. Equal spacing uses fractions;
random layouts retain exact half-pixel centers. The frozen score remains
same-page, different-row center separation **<=15px**, with each endpoint
counted once. Partners must also belong to the eligible-row population.
Standalone Allah and pooled identical spellings are primary; the declared
Allah-name family is secondary.

This is an **interval renderer, not rendered Arabic calligraphy**. The observed
gap multiset supplies an empirical spacing scale, but exchangeability of gaps
is a toy assumption. Gaps can contain verse markers, stop signs or diacritics;
the generator does not model their ink ownership, glyph joins or kashida.
Original widths and line breaks can already contain alignment-directed choices.
Holding them fixed does not independently explain how they arose.

### All outcomes on the eligible population

| group | population | observed aligned | equal-gap aligned | permutation mean | trials >= observed |
|---|---:|---:|---:|---:|---:|
| exact standalone `الله` | 13 | **7** | 5 | **5.5284** | **1,643/5,000** |
| all identical spellings | 534 | **28** | 22 | **21.5968** | **15/5,000** |
| separate Allah-name family | 18 | **14** | 11 | **11.9020** | **1,031/5,000** |

Plus-one Monte Carlo summaries are respectively **0.3287, 0.003199 and
0.2064**. For the pooled identical-word metric, the simulated tail fraction
is 0.0030, with a two-sided 95% binomial interval about **[0.00168, 0.00494]**.
These are unadjusted, dependent, exposed-development comparisons under the
stated spacing rule. They are not a global discovery probability or origin
likelihood. The standalone-Allah comparison is not significant here; the
pooled identical-word residual must also be retained.

| page | eligible / located rows | eligible words | Allah aligned / eligible | equal-gap Allah | permutation Allah mean |
|---|---:|---:|---:|---:|---:|
| 36 | 10/15 | 98 | 2/4 | 2 | 1.8008 |
| 124 | 9/15 | 83 | 0/3 | 0 | 0.0000 |
| 298 | 9/15 | 75 | 0/0 | 0 | 0.0000 |
| 366 | 9/14 | 83 | 0/0 | 0 | 0.0000 |
| 500 | 8/15 | 86 | 2/2 | 0 | 0.7276 |
| 508 | 13/15 | 109 | 3/4 | 3 | 3.0000 |

Every page, excluded row, deterministic endpoint/pair, first random layout
selected by trial index, and all per-page/pooled simulation scores are saved
in [the comparison artifact](../tools/data/research_text_layout_comparison_v1.json).
A SHA-256 digest also binds every generated random center coordinate in
page/trial/token order. Nothing was optimized to maximize alignment.

### Independent cross-check and remaining freedom

[The post-score review](../tools/data/research_text_layout_review_v1.json)
uses a separate scalar all-pairs reference, checks the original population
against the frozen full-corpus occurrence/pair ledger, and verifies the equal
and first-random layouts' ordering and non-overlap. Family membership is checked
against canonical normalized forms on this population.

All six pages together have **19 mapped standalone-Allah occurrences**, of
which **14 align** when all mapped rows are allowed. Restricting to feasible
rows removes six occurrences and some partners, giving the primary **7/13**.
There is no full-page generated comparator for the excluded words. These
denominators must not be interchanged with the 2,151-occurrence corpus study.

For a word at zero-based row position r, its coordinate depends on the sum
of the first r gaps. The r smallest/largest gaps give exact attainable center
extrema under permutations. The number of distinct gap arrangements is
(n−1)! divided by the product of factorials of gap multiplicities. These
formulae quantify the model's freedom without relying on sampled movement:

- **418/534** eligible word centers can move.
- **8/13** eligible standalone-Allah centers can move; five are fixed.
- On p508, **three Allah endpoints have a guaranteed partner under every
  permitted gap permutation**. The certificate compares the worst-case
  separation of exact attainable center extrema on different rows. It is
  sufficient for persistence, not a complete characterization of all endpoint
  events.

Six scan-backed original/equal/first-random sheets were generated and inspected
at `logs/text-layout-pilot-v1/page_<N>.png`. The latter two panels are labelled
interval schematics; they must not be presented as alternative Quran scripts
or independent word-boundary annotations.

### Origin implication and completion decision

**This pilot does not establish divine design.** It demonstrates limited
text/order-preserving interval feasibility and shows that some alignment
persists under substantial spacing rearrangement. Standalone Allah is not
unusual under this pilot's spacing rule; pooled identical spellings retain a
conditional residual. Neither result explains the inherited word widths,
line/page assignments or historical production process.

The earlier whole-corpus association and its row/width-permutation bounds
remain intact. They concern different populations and models; this pilot
does not refute them, provide a full-corpus non-divine explanation, or convert
them into an origin probability. A successful interval comparator and an
unsuccessful one alike fall short of the missing origin-likelihood comparison.

**Gate decision:** finish v1 as a development spacing-sensitivity diagnostic;
do not promote it directly to a held-out historical/origin test. Its next
useful successor needs widths/justification constraints motivated independently
of this finished tawafuq print, explicit marker/glyph handling, and validation
of complete row text and geometry before evaluation on held-out pages.
Independently dated pre-discovery copies and alignment-blind transcriptions
remain distinct, potentially more discriminating evidence for latent design.

### Reproduction

```bash
. .venv/bin/activate
python tools/text_layout_pilot.py --feasibility --verify
python tools/text_layout_comparator.py --verify
python tools/text_layout_review.py --verify
python tools/text_layout_review.py --verify --review logs/text-layout-pilot-v1
python -m unittest discover -s tools -p 'test_text_layout.py' -v
python tools/verify_cpu.py
```

The four new tests use exhaustive distinct gap permutations, an independent
left-to-right packing reconstruction, exact attainable-extrema comparisons,
scalar endpoint enumeration, rational equal spacing and tolerance boundaries.
The CPU verifier integrates complete deterministic replay of the pilot and
its independent review. No paid OCR, network connection or GPU is required.

Verification completed: **163 tests pass**, **150 Python files parse**, and
the complete quick CPU verifier passes, including all earlier frozen reports
and full deterministic replay of the new spacing trials. Standalone pilot
replay and feasibility verification also pass. Log:
`logs/text-layout-pilot-cpu-v1.log`. All six review sheets were inspected;
`git diff --check` passes. This continuation after e16e19d is uncommitted.

## 2026-10-19 — beyond Allah: exact words and multiword phrases

At the user's explicit request, the next study broadens the object of interest
to actual repeated words and phrases, independent of ink color. Complete
methods, all outcomes, examples and origin implications are in
[PHRASE-ALIGNMENT.md](PHRASE-ALIGNMENT.md). The preceding six-page result is
not a summary of this larger phenomenon.

The locally frozen study analyzes all single words and canonically repeated
within-verse windows of lengths 2–6. An occurrence must be mapped on one row;
a strict partner on another row of the same page must align **every
corresponding word center within 15px**. Missing/cross-row windows and all
unpaired occurrences are retained. No word-ink color selects the inventory.

Excluding all Allah-name-containing identities, full mapped aligned counts
are **4,745 single-word occurrences (580 types)**; **1,084 two-word phrase
occurrences (396 types)**; **433 three-word (171 types)**; **187 four-word
(75 types)**; **65 five-word (30 types)**; **28 six-word (13 types)**. These
overlap and must not be added as independent evidence. Full populations and
all per-type outcomes, including negative residuals, are in the report.

The text/order-preserving empirical-gap model reuses the pilot's feasibility
rules corpus-wide: **6,335/8,717 rows**, **54,845/76,511 mapped words** qualify.
All excluded rows remain explicit. On the eligible subset, non-Allah-form
observed aligned counts versus simulated means are **2,680 vs 1,955.45**
(one word), **641 vs 335.06** (two), **266 vs 118.20** (three), **106 vs 37.16**
(four), **32 vs 7.39** (five), **12 vs 2.20** (six). In 5,000 coherent full-corpus
layouts, lengths 1–5 have zero exceedances and length 6 has two. Six-test
Bonferroni-adjusted plus-one summaries are approximately **0.00120** and
**0.00360**, respectively. No extreme-tail extrapolation or origin probability
is claimed. The subset comparison is not a tail for the full mapped counts.

Forty-eight predeclared scan-backed diagnostic sheets were inspected via six
contact sheets. Examples include `هدى` at 2:2/2:5; the five-word phrase
`اذكروا نعمتى التى أنعمت عليكم` at 2:40/2:47; and six-word phrases at
34:36/34:39 and 54:17/54:22, with every corresponding center within 4.5px
in those examples. Both paired and unpaired diagnostics remain in the manifest.

The implementation is `tools/broad_phrase_alignment.py`, with independent
scalar review in `tools/broad_phrase_review.py` and five exhaustive/reference
tests in `tools/test_broad_phrase_alignment.py`. Four versioned
`tools/data/research_broad_phrase_*_v1.json` artifacts retain the frozen plan,
full row feasibility, all outcomes and review. Complete deterministic replay
reproduces every trial's scores and coordinate digest; the independent scalar
review checks every strict pair and all per-type endpoint counts.

**Interpretation:** broader word/phrase alignment and a model-conditional
spacing excess are established. Divine design remains unresolved. The model
inherits the print's widths and line breaks and does not reconstruct phrase-
sensitive calligraphy/marker ownership. A next causal gate needs independently
justified writing constraints or independent copies, not more inventory tails
treated as origin probabilities. This study completes the requested broader
measurement; it does not reopen the historical audit.

Verification: **168 tests pass**, **153 Python files parse**, complete quick
CPU verification passes, and separate full replay reproduces all 5,000 broad
spacing layouts' metric/type/page accounting and coordinate digest. All 48
predeclared diagnostic sheets were inspected through six contact sheets.
`git diff --check` passes. No new OCR, network service or GPU was used;
research after e16e19d remains uncommitted.

## 2026-10-19 — verse/phrase-aware controls and historical-copy leads

The next bounded investigation preserves verse-boundary gaps and, in a
stronger control, the observed internal geometry of greedy canonical repeated
2–6-word blocks. Both candidates/evaluation were separately frozen before
scoring. Full methods, both outcomes, exact proofs and sources are appended to
[PHRASE-ALIGNMENT.md](PHRASE-ALIGNMENT.md#2026-10-19--stronger-verse-aware-and-repeated-phrase-controls).

On the unchanged eligible population excluding Allah-name forms, observed
counts for lengths 1–6 remain **2,680, 641, 266, 106, 32, 12**. Verse-internal
gap permutation means are **2,214.74, 445.00, 172.71, 61.89, 13.39, 3.76**;
the corresponding exceedance counts are **0, 0, 0, 0, 0, 19 / 5,000**.
Preserving repeated-phrase blocks raises the means to **2,489.22, 592.35,
255.88, 105.34, 32, 12**, with exceedances **0, 0, 3, 3,343, 5,000, 5,000**.
The plan adjusts twelve primary comparisons. Single-word and short-phrase
residuals survive; the long-phrase residuals do not under that stronger control.

The phrase-block model leaves **23,542/48,510 gaps permutable** and
**24,224/54,845 word centers movable**. Exact attained center extrema and
independently checked pair-envelope certificates prove that the non-Allah-form
five- and six-word scores are **identically 32 and 12 under every allowed
layout**. The model inherits their phrase geometry/anchors, so the theorem is
neither an independent construction of those shapes nor an origin proof.
The post-score envelope refinement is retained separately from primary tests.

Online source work independently distinguishes Kayışzâde Hâfız Osman Nûri
(d. 1894) from Hâfız Osman (d. 1698). TDV lists candidate Michigan Arabic
manuscripts 172/173 as nineteenth-century Qurans; Michigan documents its
1924 Abdul Hamid collection acquisition and public HathiTrust digitization.
Matching item-level records, colophons, compatible layouts and target scans
were not recovered in this pass. These are candidate leads, not pre-discovery
alignment measurements; all URLs and retrieval limits are in the full report.

The next discriminating gate is recovery/compatibility checking of independently
dated copies or independently justified writing/phrase shapes. Current findings
establish geometry and conditional residuals; divine design remains unresolved.
Code: `phrase_structure_controls.py`, independent `phrase_structure_review.py`,
and two test modules. Data: `research_phrase_structure_{plan,controls,review}_v1.json`.

Verification completed: **176 tests**, **157 parsed Python files**, complete
quick CPU verification and separate full replay of both new 5,000-trial runs
pass. Independent canonical-group, attained-extrema and pair-envelope checks
pass, including the exact score-invariance certificates. `git diff --check`
passes. Network use was limited to public historical/source research; no new
OCR service or GPU was used. Continuations after e16e19d remain uncommitted.

## 2026-10-19 — recovered 1779 manuscript and fixed historical pilot

The historical track now has an actual item-level copy: **Columbia MS Or 422**,
catalogued **1193 AH / 1779**, copied by Ismāʿīl ibn Ṣāliḥ with fifteen-line
naskh pages. The recovered **304r colophon** visibly supports the catalogue's
name/year in a single-reader check. The [full historical report](HISTORICAL-COPY.md)
links Columbia/OPenn metadata, HathiTrust record **102811738** and IA item
**ldpd_14642794_000**, including public-domain scans and retained source hashes.
These mirrored catalogue descriptions are not independent dating authorities.

A separate local plan selected rectos **50,100,150,200,250,300 before images
were opened**. All six were inspected, as was the colophon. Failed transport
routes and an off-by-one IA page-index assumption are retained with explicit
amendment/correction records. Corrected images visibly show the intended folios.
No sampled page was replaced for its alignment outcome.

All **33 canonical Allah-family occurrences** in the six read verse ranges
are annotated; **29** are exact standalone Allah. All 33 have unchanged modern
ledger positions. Three unencoded head basmalas are explicitly excluded. The
older copy's page/line contents are not identical to the modern layout: three
historical verse ranges span two modern pages. Both comparison populations
contain only the same selected canonical names, without outside partners.

At **2% of text-frame width**, historical midpoint counts are **8/33 family**
and **8/29 standalone**; modern counts are **27/33** and **23/29**. At **1.5%**,
they are **6/33,6/29** versus **25/33,23/29**. Historical ±5px center/±3px frame-
edge allowances give conservative count envelopes **0–14,0–10** at 2%, and
**0–10,0–8** at 1.5%. These assumed coordinate allowances are not calibrated
confidence intervals; the nominal historical matches are not guaranteed at
every allowed coordinate choice. Manual ink and modern detector-box center
conventions differ. No significance or population/origin probability is claimed.

This adds directly inspected pre-project geometry and a same-token comparison
showing substantial presentation dependence. It does not reproduce the modern
rate historically, refute latent design through a chosen later layout, or
establish a sufficient non-divine production process. **Origin remains unresolved.**
The next finite gate is independent adjudication of these exposed pages and
colophon under a shared measurement convention before fresh-page validation.

Code: `historical_copy_pilot.py`, `historical_copy_analysis.py`; data:
`research_historical_copy_{plan,retrieval_amendment,index_correction,annotations,analysis,sources}_v1.json`.
Five finite ground-truth tests pass; deterministic canonical/score replay and
both nine-entry acquisition-manifest byte checks pass. Ruler sheets/raw inputs
are local under `logs/historical-copy-ms-or-422-v1/`. No paid OCR/API, credentials
or GPU were used. Historical studies and earlier uncommitted work are preserved.
