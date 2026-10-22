# Beyond Allah: exact word and phrase alignment

## 2026-10-19 — color-independent corpus study

**The measured alignment extends well beyond Allah-name forms.** This study
finds aligned occurrences of **580 other exact word types**, and hundreds of
distinct repeated phrases. It selects identities from Quranic text, without
consulting ink color. Its strongest phrase rule requires **every corresponding
word** to align, not just the middle of a colored region.

The results establish broader geometric structure and an excess under an
explicit text/order-preserving spacing comparison. **They do not yet identify
its divine or non-divine cause.** The earlier six-page Allah-only comparison
does not summarize this larger word/phrase evidence.

## What was frozen before scoring

The [local plan](../tools/data/research_broad_phrase_plan_v1.json) was saved
before the new phrase counts and spacing scores. It binds candidate/evaluator
source, tests, input hashes, normalization, window lengths, exclusions, metrics,
simulation and review selection. It is not external preregistration.

- **Input:** the unchanged 604-page Hayrat scans' conservative v5 word map and
  canonical Quran text. The existing inventory has 77,404 expected verse tokens,
  76,511 mapped and 893 unresolved. Fatiha and synthetic unencoded head
  basmalas remain outside the primary inventory.
- **Words:** the complete exact-spelling inventory, preserving prefixes and
  hamza distinctions under the earlier declared normalization.
- **Phrases:** contiguous **2–6-word windows within one verse**, with at least
  two canonical occurrences anywhere. Longer passages, verse-crossing windows,
  related roots and semantic synonyms are outside this rule.
- **Locations:** every constituent must have a mapped center on the same page
  and seeded row, in canonical RTL order. Missing constituents, page/row splits
  and reversed centers remain in an occurrence ledger.
- **Strict partner:** an identical word sequence on another row of the same
  page, with **every corresponding center separated by at most 15px**. Each
  occurrence is counted once regardless of partner count.
- **Primary groups:** six lengths, each excluding identities containing any
  Allah-name form under the canonical name predicate. This does not exclude
  other divine words, such as `ربكما` or `الرحيم`. Inclusive results are also
  retained. Excluding Allah forms demonstrates that the evidence is broader
  than those forms; it is not a claim about only ordinary secular words.

The algorithm reads the existing detector/support boxes, not word-ink labels.
The upstream OCR saw the original scans and uses the existing gold-title
exclusion; this is not a new grayscale recognition experiment.

## Full mapped results beyond Allah-name forms

| unit | located occurrences | strictly aligned occurrences | distinct aligned types | pages with alignment |
|---|---:|---:|---:|---:|
| one word | 73,816 | **4,745** | **580** | **561** |
| two-word phrase | 28,957 | **1,084** | **396** | **223** |
| three-word phrase | 11,870 | **433** | **171** | **89** |
| four-word phrase | 5,382 | **187** | **75** | **44** |
| five-word phrase | 2,625 | **65** | **30** | **16** |
| six-word phrase | 1,296 | **28** | **13** | **7** |

Phrase denominators concern canonically repeated windows whose complete
geometry is mapped on one row, not every possible passage in the Quran.
Most located occurrences in these broad inventories have no mapped strict
partner; all of them remain in the denominator and unpaired ledger. Missing
partners can hide actual alignments, and mapping errors can introduce false
ones. These figures are not a claim that every word aligns.

Windows overlap: one six-word alignment can contribute several shorter
alignments. Word types, phrase lengths and pages with related passages are
not independent replications. **Do not add the rows into an independent
evidence count or multiply their probabilities.**

Inclusive aligned totals, retaining Allah-containing identities, are **6,580,
1,348, 565, 245, 95 and 40** for lengths 1 through 6. The single-word pair
ledger exactly reproduces the earlier frozen corpus study.

## Concrete scan-checked examples

These examples follow the predeclared earliest-pair, distinct-identity/page
selection within each length. The spellings below retain the study's normalized
Quranic forms; they are not new linguistic annotations.

| page | repeated text | verse occurrences | corresponding center differences |
|---|---|---|---|
| 1 | `هدى` — guidance | 2:2, 2:5 | **3.5px** |
| 2 | `قلوبهم` — their hearts | 2:7, 2:10 | **2.5px** |
| 6 | `اذكروا نعمتى التى أنعمت عليكم` | 2:40, 2:47 | **0.5, 1.5, 1.5, 2.0, 4.0px** |
| 431 | `قل إن ربى يبسط الرزق لمن` | 34:36, 34:39 | **1.0, 0.5, 3.5, 4.5, 0.0, 4.0px** |
| 528 | `ولقد يسرنا القرءان للذكر فهل من` | 54:17, 54:22 | **1.0, 3.0, 3.0, 0.5, 1.0, 0.5px** |

The familiar four-word refrain **`فبأى ءالاء ربكما تكذبان`** has **31/31
mapped occurrences** aligned under the strict same-page rule. This is one
phrase type among 75 aligned four-word types, not all the phrase evidence.
Identical recurrent phrasing and its typographic treatment remain relevant
to interpreting that example.

Six paired and two unpaired examples per length produce **48 scan sheets**.
All were inspected through six contact sheets, with original coordinate
frames shared by paired crops. The identities and corresponding placements
are visibly supported in this diagnostic selection; some detector edges do
not enclose all ink. This is exposed, single-reader inspection, not independent
corpus accuracy certification. Unpaired crops do not certify absence of all
partners elsewhere on the page. Local sheets and manifest:
`logs/broad-phrase-review-v1/`.

## A text/order-preserving spacing comparison

To avoid substituting other words into the observed sites, the new comparison
keeps **actual text and canonical order, page/row membership, detector widths
and outer row edges**. It independently permutes each eligible row's observed
nonnegative gap multiset. All lengths are scored on the same generated page
layouts, preserving dependencies among their scores.

The whole-corpus feasibility extension reuses the earlier six-page criteria
exactly and checks agreement on those six pages. It was undertaken at the
user's request to broaden the investigation, not as an automatic extension
of the closed pilot. Of **8,717 rows containing mapped verse words**, **6,335
qualify**, containing **54,845 words**. Exclusion counts overlap: 1,520 rows
have overlapping detector intervals, 530 have missing internal tokens, 460
touch uncertain adjacent-row token boundaries, and 84 have uncertain page
envelopes. All 2,382 excluded rows remain recorded, without clipping or repair.

Only partners within the eligible population enter this comparison. Thus the
following observations and denominators differ from the full mapped table:

| unit, excluding Allah-name forms | eligible occurrences | actual aligned | spacing mean | ratio to mean | trials >= actual |
|---|---:|---:|---:|---:|---:|
| one word | 52,980 | **2,680** | **1,955.4524** | **1.37x** | **0/5,000** |
| two-word phrase | 20,839 | **641** | **335.0562** | **1.91x** | **0/5,000** |
| three-word phrase | 8,562 | **266** | **118.1984** | **2.25x** | **0/5,000** |
| four-word phrase | 3,897 | **106** | **37.1562** | **2.85x** | **0/5,000** |
| five-word phrase | 1,892 | **32** | **7.3884** | **4.33x** | **0/5,000** |
| six-word phrase | 916 | **12** | **2.2012** | **5.45x** | **2/5,000** |

There are 5,000 coherent corpus layouts, **PCG64 seed 20261021**, with no
alignment-directed optimization or parameter search. Original gaps reproduce
every original eligible center exactly. Generated centers remain exact
half-pixel coordinates, and a digest binds their full trial sequence.

For lengths 1–5, the plus-one Monte Carlo summary is **1/5,001 ≈ 0.000200**;
zero exceedances do not mean p=0. The individual one-sided 95% model-tail
upper confidence limit is about **0.000599**. For length 6, the plus-one
summary is **3/5,001 ≈ 0.000600**, and its two-sided 95% interval for the
tail is about **[0.0000484, 0.001444]**. The plan applies a **six-test
Bonferroni adjustment** to the primary plus-one summaries: approximately
**0.00120** for lengths 1–5, **0.00360** for length 6. These are conditional,
exposed-development comparisons, not origin probabilities or probabilities
that all these historical observations arose by chance in any possible way.

The stronger long-phrase ratios are descriptive; nested windows and repeated
passages share evidence. The limited number of long phrases and the two
six-word exceedances remain part of the report.

## Sensitivity, counter-results and limits

Requiring exact normalized OCR surface agreement for **every constituent**
retains the following full-mapped, non-Allah-form aligned counts/populations:
**4,310/64,368; 778/22,977; 245/8,184; 78/3,233; 28/1,432; 12/646** for
lengths 1–6. These are descriptive location-coverage sensitivities, not a
new simulation or an independent replication. Longer windows lose more
coverage because every constituent must pass. The original outcomes remain
the primary ones; none of the losses is silently repaired.

Individual types need not have an excess. For example, exact `ما` has
**40** eligible aligned endpoints versus a spacing mean of **43.8294**.
The full per-type table preserves these counter-results, not only the most
visually striking phrases. Rankings by observed aligned endpoint count are
descriptive; no individual-type significance claim was made.

This is still an **interval-spacing model**, not realistic alternative
calligraphy. Original widths and line breaks may contain deliberate layout
choices. Gaps may contain verse/stop signs and diacritics; their ownership,
glyph joins, repeated-phrase templates, context-dependent spacing and kashida
are not reconstructed. Exchangeability of gaps is not independently established
as a historical writing rule. The data remain one print, with imperfect OCR
geometry and exposed development choices. Facing-page/back-to-back geometry,
same-root words, related meanings and phrases spanning rows are not measured
by this particular study.

## What follows for divine design

The user's broader premise is now supported directly: **many actual words
and multiword phrases align; the result is not confined to Allah-name forms
or to a statistic of colored components.** A coherent text/order-preserving
spacing comparison also leaves a substantial excess across all six declared
lengths. This is stronger and more relevant evidence for the phenomenon than
the earlier component-selection experiments or the small pilot alone.

**A divine-design proof has not been obtained.** The study rejects a defined
spacing model; it has not established that every credible writing/typographic
process would fail, or that divine foresight uniquely predicts the observed
configuration. Repeated text, common phrase spacing, margin constraints and
calligraphic choices are parts of the remaining explanatory comparison, not
mechanisms whose sufficiency has already been demonstrated.

The next discriminating gate should address **phrase-sensitive writing
constraints or independent copies**, rather than merely generating more tiny
tails from increasingly broad inventories. In particular, independently
justified phrase/glyph widths and justification rules, alignment-blind
transcriptions, or independently dated pre-discovery manuscripts can test
whether the geometry emerges without alignment-directed decisions. Any such
study needs fixed predictions and evaluation before opening its target scores.
The current study is complete as a bounded broader measurement and spacing
comparison; its evidence and failures remain available for that next gate.

## Reproduction and artifacts

```bash
. .venv/bin/activate
python tools/broad_phrase_alignment.py --verify
python tools/broad_phrase_alignment.py --verify --full
python tools/broad_phrase_review.py --verify
python tools/broad_phrase_review.py --verify --review logs/broad-phrase-review-v1
python -m unittest discover -s tools -p 'test_broad_phrase_alignment.py' -v
python tools/verify_cpu.py
```

Long jobs should use `setsid`, with logs under `logs/`. Scan-free verification
needs no API, paid OCR, network or GPU. Recreating scan sheets requires the
hash-matched local scans. The existing scans and raw OCR cache were reused.

- `tools/data/research_broad_phrase_plan_v1.json`: frozen scope/evaluation and
  candidate/input hashes.
- `research_broad_phrase_feasibility_v1.json`: all rows, token IDs, gaps and
  exclusions under those criteria.
- `research_broad_phrase_alignment_v1.json`: complete occurrence ledgers,
  all strict pairs and unpaired starts, all per-type outcomes, sensitivities,
  stored simulation scores/type/page sums and generated-center digest.
- `research_broad_phrase_review_v1.json`: independent scalar checks and the
  predetermined diagnostic examples; a descriptive top-type table per length.

Five new tests use exhaustive tiny coordinates, independent scalar phrase
matching and every distinct tiny gap arrangement, including missing/row-split
windows, exact spelling, verse boundaries and the case where phrase centers
agree but constituent words fail. Full replay reproduces all 5,000 layouts'
metric scores, per-type/page sums and generated-center digest. Every reported
strict pair and all four views' per-type endpoint totals also pass the
independent scalar review. Logs: `logs/broad-phrase-build-v1.log`,
`logs/broad-phrase-full-replay-v1.log`, `logs/broad-phrase-cpu-v1.log`.

Verification completed: **168 tests pass**, **153 Python files parse**, full
quick CPU verification passes, and the separate full spacing replay reproduces
all stored scores, sums and generated-center digest. All 48 scan diagnostics
were inspected through six contact sheets; `git diff --check` passes. Research
after e16e19d, including this study and the preceding pilot, remains uncommitted.

## 2026-10-19 — stronger verse-aware and repeated-phrase controls

The next user request was to investigate divine design further. Rather than
only expanding the inventory or shrinking another tail, this study tests
whether the earlier comparison disturbed relevant writing structure. Its
[separate plan](../tools/data/research_phrase_structure_plan_v1.json), candidate,
tests and evaluation were frozen before the new model scores.

### Two explicitly stronger comparisons

The population and original observations are **exactly the earlier eligible
rows**, with unchanged canonical text/order, page/row assignments, detector
widths, outer edges and strict <=15px corresponding-word score. Word color
still does not select the inventory. The models have 5,000 trials each,
PCG64 seeds **20261022** and **20261023**:

1. **Verse-internal gaps.** Fix gaps between different canonical verses.
   Shuffle only the internal gaps of each verse fragment on a row, preserving
   that fragment's total internal spacing. This keeps the measured intervals
   at verse boundaries rather than moving them elsewhere in the line.
2. **Repeated-phrase blocks.** On each row/verse fragment, scan the canonical
   sequence from its first RTL word, taking the longest repeated 2–6-word
   phrase available, or a singleton otherwise. Repetition means at least two
   canonical occurrences anywhere, without consulting alignment geometry.
   These nonoverlapping blocks retain their original internal gaps. Fix
   verse-boundary gaps too; shuffle only gaps **between** blocks within the
   same row/verse fragment.

The second model **inherits the actual shapes of repeated phrases**. It tests
their remaining placement freedom; it does not independently create or
explain their original geometry. The segmentation is a fixed diagnostic
rule, not a claim that a historical scribe used this greedy algorithm.

### Results, including the disappearing long-phrase residual

All counts below exclude identities containing Allah-name forms, with the
same populations as the earlier eligible-row table:

| length | actual aligned | earlier whole-row gap mean | verse-internal mean; exceedances | phrase-block mean; exceedances |
|---|---:|---:|---:|---:|
| 1 word | **2,680** | 1,955.45 | **2,214.74; 0/5,000** | **2,489.22; 0/5,000** |
| 2 words | **641** | 335.06 | **445.00; 0/5,000** | **592.35; 0/5,000** |
| 3 words | **266** | 118.20 | **172.71; 0/5,000** | **255.88; 3/5,000** |
| 4 words | **106** | 37.16 | **61.89; 0/5,000** | **105.34; 3,343/5,000** |
| 5 words | **32** | 7.39 | **13.39; 0/5,000** | **32.00; 5,000/5,000** |
| 6 words | **12** | 2.20 | **3.76; 19/5,000** | **12.00; 5,000/5,000** |

The **single-word and two-/three-word residuals survive the phrase-block
control**. Four- to six-word residuals do not. These outcomes refine the
interpretation of the earlier excess; they neither change its observations
nor invalidate arithmetic under its different model.

The plan treats the six lengths under two models as **twelve primary
comparisons**, applying factor-12 Bonferroni adjustment to plus-one Monte
Carlo summaries. For the phrase-block model, adjusted summaries are about
**0.00240, 0.00240, 0.00960, 1, 1, 1** for lengths 1–6. The verse-internal
six-word result has adjusted summary **0.04799**, but its unadjusted 95%
tail interval is about **[0.002289, 0.005928]**: Monte Carlo uncertainty is
material near that threshold. It should not be portrayed as a sharply
resolved significance boundary. Zero exceedances elsewhere still do not
mean zero probability or justify extreme-tail extrapolation.

### Quantifying what the controls fix

There are **48,510 eligible gap sites** and **54,845 eligible word centers**.

| property | verse-internal control | phrase-block control |
|---|---:|---:|
| groups with more than one distinct gap value | 7,660 | 5,869 |
| permutable gap sites | 44,595 | 23,542 |
| gap sites fixed in value | 3,915 | 24,968 |
| word centers able to move | 36,935 | 24,224 |

Fixing many centers/phrase shapes can force existing alignments. An exact
prefix-sum calculation gives each word's attainable center minimum and
maximum: in every gap stratum, take the required number of smallest or
largest values preceding that word. The complete stratum sums remain fixed.
These are **exact attainable extrema**, not simulated estimates or claims
that all intermediate positions are attainable.

An independent post-score review also constructs lower/upper certificates
for each strict alignment score. Using twice-centers and intervals [l,u]:

- A corresponding-word pair is guaranteed within tolerance if
  `max(abs(l_a-u_b), abs(u_a-l_b)) <= 30`.
- It is impossible within tolerance if
  `max(0, l_a-u_b, l_b-u_a) > 30`.
- A phrase pair is guaranteed only if every corresponding word is guaranteed;
  it is ruled out if any corresponding word is impossible. All not-ruled-out
  pairs provide an **outer bound**, not exact joint feasibility: word positions
  can be correlated.

Guaranteed-pair endpoints give a rigorous lower score; not-ruled-out-pair
endpoints give a rigorous upper score. Equal bounds certify exact invariance
under **every** allowed gap permutation, without relying on rare-event Monte
Carlo or independence of endpoint flags.

| length | observed | phrase-block guaranteed lower score | envelope upper score |
|---|---:|---:|---:|
| 1 | 2,680 | 2,027 | 2,876 |
| 2 | 641 | 533 | 653 |
| 3 | 266 | 241 | 266 |
| 4 | 106 | 104 | 106 |
| 5 | **32** | **32** | **32** |
| 6 | **12** | **12** | **12** |

Thus the five- and six-word scores are **mathematically fixed under the
phrase-block model**, not merely unchanged in 5,000 lucky trials. This is
a conditional geometry theorem. Its premises preserve observed phrase
shapes/anchors, so it cannot serve as a proof that those shapes arose without
design, or as a proof of divine design. The upper-envelope refinement was
added as a separate exposed diagnostic after the primary scores.

A deterministic comparator equalizes verse-internal gaps to integer
floor/ceiling of their mean, assigning the remainder to earliest RTL gaps,
while retaining verse-boundary gaps. It gives **2,317, 531, 224, 90, 26 and
10** non-Allah-form aligned endpoints for lengths 1–6, versus actual
**2,680, 641, 266, 106, 32 and 12**. No score was optimized. This is another
fixed-width interval layout, not reconstructed Arabic calligraphy or a
historical-production explanation.

### Separately sourced historical-copy leads

Online research on **2026-10-19** located these independently maintained
sources for a future pre-discovery comparison:

1. **Muhittin Serin, TDV İslâm Ansiklopedisi,
   [Kayışzâde Hâfız Osman Nûri](https://islamansiklopedisi.org.tr/kayiszade-hafiz-osman-nuri).**
   It distinguishes the nineteenth-century calligrapher (d. 1894) from the
   earlier Hâfız Osman (d. 1698). It lists Michigan Arabic manuscripts **172
   and 173**, describing copies completed in **1305/1888** and **1301/1884**
   respectively. These are **source-reported candidate identifications**;
   this study did not independently read their colophons or match their
   item-level catalogue records. Attribution to this scribe alone does not
   establish the 15-line/604-page layout: the same entry describes other
   manuscripts with eleven or thirteen lines.
2. **University of Michigan Library,
   [Islamic Manuscripts Collection: About](https://guides.lib.umich.edu/islamicmss/about).**
   The library records purchase of the so-called Abdul Hamid collection from
   Maurice Nahman in **1924**, and includes Kayışzâde among its represented
   calligraphers. The library also notes that the supposed earlier ownership
   by Sultan Abdülhamid II is not established. The collection's acquisition
   date is not yet an item-level provenance verification for the two cited
   Qurans.
3. **University of Michigan Library,
   [Digitized manuscripts](https://guides.lib.umich.edu/islamicmss/digitized).**
   It documents public viewing and full downloads through HathiTrust for
   most of the collection, and a page-image API route. The item-level
   Michigan search required JavaScript; the attempted shelfmark/name
   catalogue queries did not identify the matching Quran records. No target
   scan from these two copies was acquired or scored. Retrieval failure
   does not establish that they are undigitized or lack alignment.

These are actionable leads, **not new measurements of nineteenth-century
alignment**. A future study must first match item-level identifiers, verify
dates/provenance and page/line compatibility, then freeze a cross-copy score
and target selection before examining target geometry. Original colophons,
dated acquisition records and adequate images would improve the evidence
over repeating a modern discovery narrative.

The cited supportive [2022 JRNS account](https://thejrns.org/index.php/thejrns/article/view/80)
(printed pp. 17–20) describes partial earlier alignment, commissioned copies,
selection of Husrev's script and nine handwritten versions. It also quotes
unchanged page/line counts with organization of the writing. This is relevant
historical testimony, not a measurement that horizontal spacing was uniquely
fixed or that all copies were produced independently of alignment goals.

### Conclusion and next gate

**There remains a real model-conditional residual beyond Allah-name forms,
particularly in single words and short phrases, after retaining more of the
writing structure.** Long-phrase one-shot rarity is substantially sensitive
to whether the comparator preserves the phrase geometry already present in
the print. Those two findings must be reported together.

No divine-design proof or sufficient non-divine historical explanation has
been obtained. This continuation completes two stronger spacing diagnostics,
exact persistence/invariance certificates, and a bounded historical-source
search. The next useful gate is item-level recovery/compatibility checking of
independent dated copies or a writing model whose glyph/phrase shapes are
justified independently of this completed print. More overlapping conditional
tails alone do not close the origin-likelihood gap.

Reproduce with:

```bash
. .venv/bin/activate
python tools/phrase_structure_controls.py --verify
python tools/phrase_structure_controls.py --verify --full
python tools/phrase_structure_review.py --verify
python -m unittest discover -s tools -p 'test_phrase_structure*.py' -v
python tools/verify_cpu.py
```

Artifacts: `tools/data/research_phrase_structure_{plan,controls,review}_v1.json`.
The independent review reconstructs canonical block choice, checks both
directions of the group/context correspondence, reconstructs every attainable
center envelope relative to measured centers, and checks all candidate-pair
certificates. Six new primary-model tests and two post-score envelope tests
use exhaustive tiny permutations/coordinates, including correlated word
positions where envelope overlap does not imply joint feasibility.
Full replay reproduces both 5,000-trial runs, type/page sums and center digests.
Logs: `logs/phrase-structure-build-v1.log`,
`logs/phrase-structure-full-replay-v1.log`, `logs/phrase-structure-cpu-v1.log`.

Verification completed: **176 tests pass**, **157 Python files parse**, the
complete quick CPU verifier passes, and separate full replay reproduces both
5,000-trial runs, all type/page sums and generated-center digests. The
independent range/group/pair-envelope audit passes, including exact five-/six-
word score invariance under the block model. `git diff --check` passes.
Earlier frozen studies are preserved; this continuation remains uncommitted.
