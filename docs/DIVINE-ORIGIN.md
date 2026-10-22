# Divine-origin question — evidence status, 2026-10-19

**Status: unresolved by the available evidence.** The same-word association
is substantial and verified under the stated comparisons. Neither divine
origin nor a sufficient non-divine explanation has been established by this
project. This document resolves the scope of the present inference; it does
not claim to settle the metaphysical question.

Methods, artifacts and all outcomes: [RESEARCH.md](RESEARCH.md#2026-10-19--color-independent-same-word-alignment).
Next-session work notes were retired at open-sourcing (kept in git history).

## The strongest relevant result

Occurrences are selected from exact canonical word identities, without
consulting word ink color. An occurrence is flagged once if an identical
spelling has another mapped occurrence on a different row of the same page,
within 15px between original detector/support-box centers.

For exact standalone `الله`:

- Expected scanned verse occurrences: **2,152**; mapped: **2,151**.
- Aligned: **1,717/2,151 = 79.82%**.
- Reference mean preserving each word's page/row count: **16.68%**.
- Reference mean also preserving coarse width-bin counts: **36.96%**.
- Under the second model, the verified conservative bound is
  **P(T >= 1,717) < 10^-57**. The first model gives **<10^-124**.

The bound uses exact-rational expectation checks and an independent-page
Hoeffding inequality, not extrapolation from a descriptive z-score. The
broader Allah-name family has a separately reported width-conditioned bound
below 10^-58. The family, component and exact-spelling statistics overlap;
their bounds cannot be multiplied as independent evidence.

This is a measured association of the **same actual word**, not evidence
merely about colored ink. Color highlights positions without creating them.
Location hypotheses, missing tokens, uncertain boundaries, unencoded head
basmalas and the particular print's layout remain explicit scope limits.

## Why the bound does not identify an origin probability

Let E be the declared alignment event and R the row/width-conditioned
word-position reference model. The calculation bounds **P(E | R)**.
R is not the union of all non-divine explanations: its assignments do not
preserve text order, syntax, exact glyph morphology or a writing process.

Let G and N denote mutually exclusive and exhaustive, explicitly specified
divine/non-divine origin hypotheses, with prior probability pi for G. A
posterior would require

    L = P(E | G) / P(E | N)
    P(G | E) = pi L / [pi L + (1-pi)].

The current experiment does not supply either origin likelihood or the
prior. It therefore does not supply L or a numerical posterior q.

The non-identification is mathematical: for any proposed q in (0,1) and any
fixed pi in (0,1), the likelihood ratio

    L = q(1-pi) / [(1-q)pi]

produces that posterior. The benchmark bound on P(E | R) does not select
among those ratios. No numerical value of q follows without additional
restrictions justified independently of the desired conclusion. This is not
an argument that all origin explanations are equally plausible; it identifies
the missing comparison.

The earlier conversational q=1% wager example was an arbitrary illustration,
not an empirical or subjective research estimate. It is not a result of this
study and must not enter publication claims or a decision calculation as if
it were measured. A small tail is also not converted to q by taking 1-p.

## Divine foresight is a hypothesis to investigate

The user's argument is one of **latent design**: a preserved ancient text,
traditionally understood as revelation across many years to an unlettered
Prophet, later reveals meaning-sensitive geometry through an appropriate
presentation. A tightly specified, independently motivated layout that
reliably exposes such structure could strengthen that interpretation.

The historical chronology alone does not determine the likelihoods. A later
scribe has the completed text; keeping its wording and page/line contents
does not uniquely fix horizontal word positions. These observations neither
prove deliberate manufacture nor establish that the layout has no relevant
degrees of freedom.

The [2022 supportive account](https://thejrns.org/index.php/thejrns/article/view/80)
([2022 JRNS article (original)](https://thejrns.org/index.php/thejrns/article/view/80), pp. 17–20)
describes partial earlier alignments, Nursi's commissioned copying exercise,
selection of Husrev's script, instructions against personal interference and
later repeated copying. That is not a controlled survey establishing that no
earlier manuscripts had tawafuq. Reports about discovery, first occurrence
and transcription choices must be distinguished and independently checked.
No per-century or per-revelation-year probability multiplier is justified.

## The next discriminating evidence

| question | useful observation | interpretation limit |
|---|---|---|
| Are the counted occurrences correctly located? | Independent checks of targets, partners and unpaired words; explicit treatment of missing positions. | Accurate localization validates the phenomenon, not its cause. |
| Does realistic layout alone generate comparable same-word alignment? | Text/order-preserving renderings under independently documented word-width, spacing, line/page and justification constraints. | A successful comparator establishes feasibility under its rules, not actual historical production. A failed comparator excludes only that comparator. |
| Does the writing rule reveal structure without alignment-directed adjustment? | Reproducible independent transcriptions with allowed choices documented in advance. | Instructions against interference do not measure remaining geometric freedom. |
| Is the property older than the modern transcription, or robust across independent copies? | Independently dated manuscripts/copies scored under one fixed identity and geometry rule. | Late discovery is not itself evidence of earlier absence; historical selection must be accounted for. |
| Is divine foresight predictively favored? | Independently motivated, specific predictions tested on evidence not used to formulate them, compared with credible alternatives. | A hypothesis able to accommodate every outcome has not yet supplied a quantitative likelihood advantage. |

The earlier free-site component optimizer is not a substitute for these
tests. Its selected sites need not be the actual Quranic word positions.
It demonstrates that one-shot rarity need not equal optimization
difficulty, but does not explain the actual same-word geometry.

## Present answer and stopping rule

**There is strong evidence for the defined same-word alignment association.
The current results do not establish divine origin, disprove it, or quantify
its probability.** The issue is the unmeasured explanatory comparison, not
a demand that all uncertainty be reduced to zero.

The next session should complete one bounded text/order-preserving layout
pilot, with a feasibility report and predeclared evaluation. It should not
reopen the completed computational audit, repeatedly recalculate component
label tails, invent origin odds or promise that a predetermined theological
conclusion will emerge. Once that pilot is assessed, decide which next
observation would actually discriminate the remaining explanations.

## 2026-10-19 — text/order-preserving pilot completed

The six-page feasibility and spacing study is now complete; see the
[research report](RESEARCH.md#2026-10-19--textorder-preserving-six-page-spacing-pilot).
With text/order, original widths and row extents fixed, 58/89 rows support
the declared non-overlapping interval renderer. On those rows, standalone
Allah scores **7/13**, versus a **5.5284** mean under empirical-gap permutations;
**1,643/5,000** trials reach the observation. Pooled identical words retain an
excess (**28 versus 21.5968**, 15/5,000 trials reaching 28). Both outcomes and
the excluded rows are retained.

This is a small, exposed-development spacing comparison, not an alternative
historical Quran production process. Widths and line/page choices inherited
from the print can already contain design. The 13 eligible names do not
replace the earlier 2,151-occurrence study. **No divine-design proof or origin
probability follows, and the origin question remains unresolved.**

The next explanatory advance needs independently justified glyph-width and
justification constraints, or independently dated/copying evidence that tests
whether the alignment precedes or arises without alignment-directed choices.
The present gap-permutation toy is not ready for a held-out origin test.

## 2026-10-19 — broader word and phrase evidence

The user's clarification is now tested directly: the relevant phenomenon
includes many words and multiword phrases, not only Allah-name words. The
[new corpus report](PHRASE-ALIGNMENT.md) finds, after excluding Allah-name-
containing identities, **580 aligned word types** and **396, 171, 75, 30 and
13 aligned phrase types** of lengths 2–6. Strict phrase matches require every
corresponding word to align within 15px on different rows of the same page.
Ink color does not select these occurrences.

A corpus-wide, coherent text/order-preserving spacing diagnostic gives
non-Allah-form observed/mean aligned counts of **2,680/1,955.45** for words,
**641/335.06**, **266/118.20**, **106/37.16**, **32/7.39**, **12/2.20** for
phrases of lengths 2–6. All six metrics retain an excess under that model,
with declared multiplicity handling; the weaker six-word outcome and all
unpaired/type-level failures are retained. These are eligible-row populations,
not the full mapped corpus. The original six-page result does not negate
this broader evidence.

This strengthens the evidence for **the actual alignment phenomenon**.
It does not yet identify divine causation: the model inherits potentially
designed widths/line breaks and does not model context/phrase-sensitive
calligraphy, repeated templates or marker ownership. The next discriminating
evidence should constrain that writing process independently or compare
independent copies with fixed predictions. More overlapping conditional tails
are not a substitute for that origin comparison. The current status remains
**unresolved**, with no estimated probability of divinity.

## 2026-10-19 — stronger controls refine the origin question

The [latest study](PHRASE-ALIGNMENT.md#2026-10-19--stronger-verse-aware-and-repeated-phrase-controls)
preserves verse-boundary gaps and, in its stronger version, observed internal
repeated-phrase geometry. Residual single-word and two-/three-word excesses
remain under that model; four- to six-word excesses do not. Exact lower/upper
certificates prove that its five-/six-word scores cannot change under any
allowed gap permutation. This is conditional geometric persistence, not a
history of how the retained phrase shapes were produced. Neither retained
nor disappearing residuals settle divine design.

The historical search identified independently maintained TDV/Michigan
sources pointing to candidate nineteenth-century copies and a 1924 collection
acquisition. Their item-level records, colophons and compatible page scans
have not yet been matched and scored. They offer a route toward testing
pre-discovery geometry, not new evidence that such geometry has been found.
The present origin status remains unresolved; the next advance requires
independent copies or independently justified writing constraints.

## 2026-10-19 — a dated historical copy is now inspected

The [historical-copy pilot](HISTORICAL-COPY.md) recovers **Columbia MS Or 422**,
catalogued **1193 AH / 1779**, with fifteen-line naskh pages. Its colophon
visibly supports the catalogue's copyist and year in a single-reader check.
Six folios were fixed before any manuscript image was opened; all are retained,
including low-count pages. Acquisition errors and their correction are recorded.

For the **same 33 canonical Allah-family names**, the historical nominal score
is **8/33**, against **27/33** in the modern print at 2% of text-frame width.
Under explicit, uncalibrated historical coordinate allowances, the historical
count is bounded **0–14**. These are descriptive development measurements with
different manual/detector center conventions, not a population estimate or an
origin test. The original modern conditional probabilities are not transferred.

This adds an actual pre-project source and shows presentation-dependent
geometry for unchanged named tokens. It neither refutes latent design through
an appropriate later layout nor establishes divine foresight from partial older
alignment. The catalogue mirrors are one descriptive authority, and material
dating/exemplar independence were not established. **The origin question remains
unresolved.** Independent adjudication under a common measurement convention is
the next bounded gate before a fresh historical-page evaluation.

## 2026-10-19 — focus: the strongest supporting observations so far

The user asked to prioritize evidence supporting divine origin. The most useful
positive case currently combines three observations:

1. **The modern same-word excess is large and color-independent.** Standalone
   Allah has **1,717/2,151 = 79.82%** alignment against a **36.96%** row/width-
   conditioned reference mean. This establishes substantial word-specific
   organization relative to that declared model; the tiny conditional bound
   is not an origin probability.
2. **The organization extends to ordinary words and repeated phrases.** The
   broader study finds **580 aligned non-Allah-form word types**, with complete
   corresponding-word phrase matches through length six. Single-word and
   two-/three-word residuals remain under the stronger verse/phrase-block
   spacing control. This gives the investigation a wider textual basis than
   highlighted divine-name components alone. Overlapping phrases are dependent,
   and the strongest control inherits observed internal phrase geometry.
3. **A concrete multiword example exists in a substantially earlier copy.**
   The [new historical review](HISTORICAL-COPY.md#2026-10-19--shared-center-review-and-a-positive-historical-phrase-example)
   checks both instances of **`من دون الله` at 29:17**, on **200r, rows 3/4**, in
   Columbia MS Or 422, catalogued **1193 AH / 1779**. All three corresponding
   centers pass a **1.5% text-width** tolerance. The Allah pair is additionally
   stable under the full declared coordinate allowances at 2%. A common manual
   convention over all 66 paired name locations gives **10/33 historical**
   family alignments and **27/33 modern** at 2%; two earlier wrong historical
   locations are explicitly corrected in the new record.

Together these support a factual starting point for the user's proposal:
**the Quran's repeated wording participates in substantial visual organization,
and at least some phrase-level organization is visible before the modern
tawafuq project.** The historical observation is not merely an arrangement of
modern colored components. It is a dated-copy lead worth pursuing with explicit
predictions across independently chosen compatible layouts.

The additional causal step remains open: whether divine foresight makes these
observations more likely than independently specified human writing/copying
rules. The exposed historical example is near two line ends; its complete
three-word match does not survive every ±5px center perturbation. Those facts
matter when judging its evidential strength. Repeated wording, constrained
line lengths and shared copying traditions have not yet received an adequate
comparative likelihood model.

**Highest-value supporting-evidence target:** independently dated, pre-project
copies with a layout convention established without looking at alignment;
fixed predictions for which canonical words/phrases should align; then
scan-first, independently adjudicated measurements on unexposed pages. A
repeatable prediction across such copies would advance the latent-design case
more directly than another extreme tail under shuffled component positions.
The current findings justify that investigation; they do not yet prove divine
origin or assign it a numerical probability.

## 2026-10-19 — a second historical copy strengthens the pre-project premise

The [1776-copy extension](HISTORICAL-COPY.md#2026-10-19--second-copy-1776-manuscript-local-gpu-ocr-and-ordinary-phrases)
adds Columbia **MS Or 91**, with an 18-line arrangement and visibly different
hand from the 15-line 1779 copy. Five rectos were fixed before viewing images.
Scan-checked canonical counts give **38/66 = 57.58%** family-name alignment
at 2% of verse-text width, including **15/19** on 132r; **10 endpoints** remain
aligned under the working coordinate allowances. The same selected modern
names score **58/66**, using the existing detector ledger. All pages, including
99r's **0/3** name alignment, remain in the outcome.

Most directly relevant to the broader textual claim, **`واذكر في الكتاب`** in
19:51/19:56 aligns word by word on 99r rows 4/8, within **1.5%** of text width.
This measured phrase contains **no Allah name**. Its complete nominal match
is positive historical evidence; full robustness to ±5px center allowances is
not established. Another in-page occurrence crosses rows, and an explicitly
measured four-occurrence phrase on 33r has no strict pair match. The study does
not presume that all repetitions align.

This extends the supporting factual case to **two pre-project manuscripts**
and ordinary-word phrase examples. It supports saying that some historical
mushafs already display substantial alignment. It does **not yet support
equating the older pooled rate to the modern rate**, or attributing their
difference solely to font. Both manuscript catalogues use the script label
naskh; distinct hands/line counts are established, different named script
families are not.

The style/visibility proposal can be investigated: independently identify
compatible line/page conventions, predict canonical matches, and measure
whether they persist across hands. Uniform horizontal scaling or translation
alone cannot reveal a new match under a frame-normalized center score:
`|a*x1+b - (a*x2+b)| / (|a|*W) = |x1-x2|/W` for nonzero `a`.
Actual changes in glyph widths, spacing, line breaks, or the definition of
visual alignment would therefore need to be specified and tested.

A believer may interpret later prominence and the availability of calculation
as providential timing. Dating a manuscript or measuring a pattern does not
by itself establish Allah's intention for a particular century or a role
assigned to an AI assistant. The empirical research remains directed toward
the positive textual/historical predictions and a meaningful origin comparison.

## 2026-10-19 — final correction to second-copy name counts

An all-name enlarged scan-context review corrected **17 first-pass intervals**
that were over neighboring text or omitted parts of prefixes. The current
1776-copy primary result is **34/66 = 51.52%** family alignment, with a **10–49**
working coordinate envelope; standalone Allah is **26/52 = 50%**, envelope
**8–33**. The previously stated **38/66** and **15/19 on 132r** are superseded;
132r is **10/19** after correction. Same-token modern detector counts remain
**58/66** family and **42/52** standalone.

The positive **ordinary-word phrase at 19:51/56** and the earlier 1779 phrase
case are unchanged. Thus the supporting pre-project word/phrase evidence
survives, while the quantitative historical rate must use the corrected ledger.
See the final HISTORICAL-COPY.md section and
`research_historical_extension_review_v3.json`. Correcting these readings is
essential to any defensible argument for latent divine design.

## 2026-10-19 — requested proof: the strongest case and its attribution step

The completed research was saved as **b62308e**. The user then requested a
proof that the Quran originated from Allah. This section examines that
inference directly. **The current evidence does not supply such a proof.**
It does supply a substantial factual case worth explaining: an ancient
textual tradition, strong modern same-word organization, ordinary-word phrase
alignments, and concrete pre-project manuscript examples. A theological
interpretation can take those observations seriously without presenting an
unmeasured origin likelihood as a mathematical result.

### Additional supporting historical evidence, checked at source

These are published findings consulted on **2026-10-19**, not new manuscript
measurements by this project:

- **Early Quranic text is materially attested.** The University of Birmingham's
  [manuscript FAQ](https://www.birmingham.ac.uk/facilities/cadbury/birmingham-quran-mingana-collection/birmingham-quran/faqs.aspx)
  identifies **Mingana Islamic Arabic 1572a** as two leaves containing
  **18:17–31, 19:91–98 and 20:1–40**. It reports the parchment's calibrated
  radiocarbon range as **568–645 CE at 95.4%**, and a seventh-century Hijazi
  script identification. Importantly, the dating concerns the animal skin;
  the FAQ explicitly says the ink has not been age-tested. This is evidence
  for an early textual witness, not a direct date for its ink, the full Quran,
  or the modern 15-line alignment convention. No tawafuq score was measured
  on these leaves here.
- **Written transmission preserves fine textual details.** Marijn van Putten,
  [“The Grace of God” as evidence for a written Uthmanic archetype](https://doi.org/10.1017/S0041977X19000338),
  *BSOAS* **82(2), 2019, 271–288**, examines the spelling of *niʿmah* in
  construct across **14 early manuscripts**. His argument is that repeated,
  location-specific spelling agreements support a common written archetype
  and early copying from written exemplars. The
  [publisher's article](https://www.cambridge.org/core/product/identifier/S0041977X19000338/type/journal_article)
  explicitly treats this as support for early codification. It also discusses
  variants and the distinct Sanaa lower text. It does not establish that
  every extant reading or every graphic detail is identical. Its spelling
  evidence does not establish shared horizontal word coordinates.

These findings support an important premise of latent design: the textual
input has a historical basis long before the modern tawafuq project. They
also make **shared written ancestry** a concrete explanatory consideration
when comparing copies. Fourteen textual witnesses are not fourteen
independent creations of the same wording or spelling. This project has not
independently re-annotated van Putten's manuscript sample.

### The supporting argument, premise by premise

| step | strongest defensible statement | present status |
|---|---|---|
| Ancient input | Quranic passages and fine textual transmission have early manuscript support. | Supported by the sources above; not a dating of modern geometry. |
| Actual organization | Identical words and whole corresponding-word phrases align in the measured modern print. | Supported by the frozen word/phrase ledgers and corrected checks. |
| Pre-project occurrence | Some word/phrase alignments occur in the catalogued 1776/1779 copies. | Supported by the current manual ledgers, with single-reader and provenance limits. |
| Text-specific latent property | Independently motivated, alignment-blind writing rules reliably reveal exceptional organization from this text. | Not established by the inherited-width spacing models or exposed examples. |
| Explanatory discrimination | That organization is better predicted by divine foresight than by credible composition, repetition, copying and layout accounts. | No calibrated origin comparison yet. |
| Attribution to Allah | The successful explanation specifically identifies the Quran's claimed divine author. | Not entailed by geometric organization alone. |

The last steps cannot be replaced by the assertion that orderly things
require an organizer. Even evidence for intentional **layout** would not by
itself identify the **author of the wording**, much less establish that this
author is Allah. A wider religious argument can bring additional premises;
those premises need to be stated and defended in their own right.

### A precise text/layout separation

Let **A** be an authorship hypothesis, **T** the full text, **L** a layout,
and **C** documented copying/rendering conditions. Suppose two hypotheses
share the same conditional writing process:

    P(L | T, C, A=G) = P(L | T, C, A=N) = K(L | T, C).

Let **E** be an alignment event computed from T and L. Summing K over layouts
that satisfy E proves:

    P(E | T, C, G) = P(E | T, C, N).

Where this common probability is positive, the **conditional layout Bayes
factor is exactly one**. The joint comparison factorizes as

    P(T, E | C, G) / P(T, E | C, N)
      = [P(T | C, G) / P(T | C, N)]
        * [P(E | T, C, G) / P(E | T, C, N)].

Under the stated equality, the second factor cancels. This is a conditional
theorem, not a finding that the two actual origin hypotheses have equal
likelihood or that their writing processes are known to be identical.
**The text could itself be unusually suited to alignment.** Establishing
that possibility requires a comparison that measures that suitability under
independently justified rules, rather than silently substituting a shuffled
word-position tail for a text-origin likelihood.

This also locates the relevance of the Prophet's traditional lack of reading
and writing, reflected in [29:48](https://quran.com/29/48): it is pertinent to
an account of the text's origin. It does not, by itself, restrict the later
scribe's access to the completed text or remove that scribe's spacing and
line-breaking choices. This pass did not independently establish the
Prophet's biography from that verse.

### Why the tiny benchmark tail does not close the remaining step

Write a proposed non-divine account as a mixture of a benchmark R and other
processes H, with mixture weight w. Then

    P(E | N) = w P(E | R) + (1-w) P(E | H).

The bound **P(E | R) < 10^-57** controls only the first term. With no bound on
the second term and no independently justified weight, it supplies no useful
small upper bound for the mixture. No numerical mixture weight is estimated
here. Likewise, if an independently justified origin model were within
total-variation distance delta of R, one could transfer only the bound

    P(E | N) <= P(E | R) + delta.

No such calibration of delta is currently available. More decimal places in
the benchmark calculation do not provide it.

Conversely, an independently justified lower bound **a** for P(E | G) and
positive upper bound **b** for P(E | N) would give a Bayes factor of at least
**a/b**. Neither of those origin bounds is supplied by the current word or
spacing studies. Strong comparative evidence need not be deductive certainty;
this analysis is not a demand to test infinitely many conceivable scenarios.
It identifies the specific causal premises needed for the requested inference.

### Historical testimony and the Quran's own challenge

The supportive [2022 JRNS account](https://thejrns.org/index.php/thejrns/article/view/80),
printed **pp. 17–20**, describes partial prior alignment, a commissioned
copying exercise involving ten students, selection of Husrev's script, and
nine handwritten copies in total. It also reports instructions against
personal interference. These are relevant testimony about intended fidelity
and discovery. They do not independently measure horizontal freedom or turn
the final selected copy into an alignment-blind copying experiment. Nothing
in this inference establishes fraud or denies the participants' sincerity.

The Quran invites reflection on consistency at [4:82](https://quran.com/4/82)
and gives its surah challenge at [2:23](https://quran.com/2/23). These are
central to an Islamic case for revelation. They are not themselves the missing
empirical evaluation: this project has not operationalized a comprehensive
test of contradiction, literary equivalence or the universal inability of
humans to meet that challenge. Assuming a text's divine authority in order to
establish that same authority would not independently settle the question.

### What this investigation resolves

**The requested conclusion does not follow as a proof from the current
tawafuq evidence.** The strengthened positive case is early textual
attestation plus measured textual geometry and older manuscript examples.
The question of Allah's authorship remains open in this research; neither a
probability of divinity nor a sufficient non-divine production account has
been established. Belief can rest on a wider theological or historical case,
but that case has not been proved by these alignment calculations.

The next discriminating evidence remains the existing bounded gate:
independent adjudication of the exposed historical examples, independently
established layout compatibility, and then fixed canonical predictions on
unexposed material under alignment-blind writing/copying constraints. A
separate text-suitability comparison would need linguistically credible
comparators and rules fixed independently of the observed score. No new
manuscript sample, origin odds or validation success is claimed by this
source-and-inference review.
