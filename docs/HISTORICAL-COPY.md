# A dated historical Quran: source recovery and alignment pilot

## 2026-10-19 — Columbia MS Or 422

**A concrete pre-modern-project copy is now identified and inspected.**
Columbia University Library describes **MS Or 422** as a complete Quran,
copied by **Ismāʿīl ibn Ṣāliḥ in 1193 AH / 1779**, in naskh with fifteen
long lines. The recovered colophon image visibly carries the scribe's name
and a date read as **1193**. This is more direct historical evidence than
the previously unmatched nineteenth-century shelfmark leads.

The fixed six-recto pilot also gives a useful counter-result: for the **same
33 canonical Allah-family occurrences**, the historical midpoint score is
**8/33**, compared with **27/33** in the modern print, at a tolerance of 2%
of each page's text-frame width. Measurement methods differ and historical
coordinates are coarse, so this is a descriptive development comparison.
It is **not** a new corpus-wide historical rate or origin probability.

### 1. Traceable source identity

| source | identifier / evidence |
|---|---|
| [HathiTrust item catalogue](https://catalog.hathitrust.org/Record/102811738) | Record **102811738**; shelfmark MS Or 422; date, copyist, 304 leaves, fifteen-line layout |
| [Full MARC record](https://catalog.hathitrust.org/Record/102811738.marc) | Links the digital Columbia record **14642794**, OPenn facsimile and IA item; digitization in 2020 |
| [Columbia metadata and images in OPenn](https://openn.library.upenn.edu/Data/0032/html/ms_or_422.html) | Original Columbia bibid **14258972**; metadata under CC0 and images marked public domain |
| [OPenn TEI](https://openn.library.upenn.edu/Data/0032/ms_or_422/data/ms_or_422_TEI.xml?download=1) | Explicit surface labels and image filenames; **50r = 9372_0105_web.jpg** |
| [Internet Archive item](https://archive.org/details/ldpd_14642794_000) | **ldpd_14642794_000**, ARK **ark:/13960/t44r73r5w**; public 620-image facsimile |
| [Inspected colophon image](https://archive.org/download/ldpd_14642794_000/page/n612.jpg) | Handwritten foliation **304**, scribe read as `اسمعيل بن صالح`, red numeral date read as **1193** |

These catalogue exports share Columbia's descriptive authority. Agreement
among their metadata is **not independent dating replication**. The direct
colophon reading is a single-reader inspection; no material dating,
restoration history, chain of custody or copying-exemplar relationship was
established. The Michigan 172/173 leads remain unmatched, not refuted.

The project's cited [2022 account](https://thejrns.org/index.php/thejrns/article/view/80)
places Nursi's realization of partial alignments in the **1930s**. The
catalogued 1779 copying date substantially precedes that project. This does
not date the inspected geometry to the Quran's seventh-century composition.

### 2. Selection, retrieval error and successful correction

Before any manuscript image was opened, a [local plan](../tools/data/research_historical_copy_plan_v1.json)
fixed the six rectos **50r, 100r, 150r, 200r, 250r, 300r**, plus **304r**
for the colophon. The folios are evenly spaced rather than selected for
alignments. The manuscript itself is an opportunistic source-recovery
candidate, not a random sample of all historical Qurans. This remains an
exposed-development pilot, not externally preregistered validation.

Direct OPenn shell downloads timed out. A documented transport amendment
switched to the public IA page-image route. Its first seven acquisitions
were wrong by one page: `page/n105.jpg` showed the verso following OPenn's
50r, and `page/n613.jpg` was blank. **Those files and the failed assumptions
are retained.** The index-correction record was saved before corrected
downloads; the selected folios and evaluation were unchanged.

The corrected images, at URL arguments **104, 204, 304, 404, 504, 604, 612**,
show the intended handwritten foliation numbers **50, 100, 150, 200, 250,
300, 304**. The first also matches OPenn's actual 50r by text and foliation.
No offset from a modern Quran page number was used to identify verse text.

### 3. All six pages, including low-count pages

| historical recto | canonical verse range read | verse-text rows | Allah-family names | modern pages occupied by that verse range |
|---|---|---:|---:|---|
| 50r | 4:123–128 | 15 | **8** | 97–98 |
| 100r | 9:69–72 | 15 | **6** | 197 |
| 150r | 18:35–45 | 15 | **6** | 297 |
| 200r | 29:15–23 | 15 | **10** | 397 |
| 250r | 44:41–45:2 | 13 | **2** | 497–498 |
| 300r | 94:4–96:8 | 11 | **1** | 596–597 |

Rows containing headings and unencoded head basmalas are outside the
verse-text row count. **Three printed head basmalas** are explicitly outside
the canonical verse-name inventory. Physical row numbers in the annotation
retain those intervening lines. The numerical occurrence inventory agrees
with the exact canonical name census in every read verse range: **33 names**,
including **29 standalone `الله`** and four prefixed forms. All 33 have
locations in the unchanged modern v5 ledger; none was silently substituted.

Fifteen-line copying therefore does **not** certify the same page and row
contents. Three historical verse ranges occupy two modern pages. The other
three occupy one each, but this alone does not establish identical complete
pages or line breaks. This is a same-token comparison across two layouts,
not a controlled experiment holding all page/row/glyph constraints fixed.

### 4. Score, uncertainty and the unfavorable results

The primary score flags an occurrence once if another selected family name
is on a **different row of the same page** and its whole-token center is
within **0.02 × text-frame width**. Exact standalone names are a secondary
group. The declared sensitivity uses **0.015**. Names outside the selected
33 do not supply partners in either copy. Color does not select occurrences.

Historical positions are coarse whole-token interval midpoints read from
1000px-wide ruler sheets; the historical frame is the inner text rectangle.
Modern positions are the existing detector/support-box midpoints, and frame
width is the span of **all accepted verse-word boxes** on that page. These
two measurement methods are not interchangeable certified ink boundaries.
No deskewing or new OCR was performed. Page curvature, slant, box ownership
and annotation error can affect the comparison.

| tolerance | group | historical midpoint aligned | historical coordinate-envelope lower–upper | modern same-token aligned |
|---|---|---:|---:|---:|
| **2%** | Allah family, n=33 | **8 (24.2%)** | **0–14** | **27/33 (81.8%)** |
| **2%** | standalone Allah, n=29 | **8 (27.6%)** | **0–10** | **23/29 (79.3%)** |
| 1.5% | Allah family, n=33 | **6** | **0–10** | **25/33** |
| 1.5% | standalone Allah, n=29 | **6** | **0–8** | **23/29** |

The historical envelopes assume **±5px** for each manually read center and
**±3px** for each frame edge at 1000px sheet width. A guaranteed pair must
pass for every allowed center/frame choice; a possible pair need only pass
for some choice. Endpoint bounds are conservative pairwise envelopes, not
necessarily sharp simultaneous bounds. **These allowances are not calibrated
confidence intervals.** In particular, the lower endpoint is zero: the
pilot does not certify any individual threshold match against every allowed
coordinate error. The nominal eight must not be advertised as eight
independently verified, tolerance-robust historical alignments.

Subject to those allowances, even the historical upper count is below the
modern midpoint count. But that is still conditional on the annotations,
frame conventions and modern mapping hypotheses. No p-value, significance
claim, manuscript population estimate or probability of divinity is assigned.

### 5. What this contributes to the origin question

1. **The historical track is now actionable:** an item-level dated copy,
   legible colophon, reusable public images and a complete small name ledger
   replace an unmatched shelfmark lead.
2. **Some nominal same-name alignments occur in this older copy.** That
   observation is consistent with partial pre-project alignment; it does not
   reproduce the modern print's high rate. Broad coordinate uncertainty stays
   explicit rather than being discarded to make an attractive historical claim.
3. **The same canonical names show substantially different geometry across
   these layouts.** This is evidence that presentation matters. It does not
   show which historic choices caused the modern excess, or whether copying
   traditions share geometric templates.
4. **The user's latent-design hypothesis remains open:** it posits that an
   appropriate later presentation reveals structure, not that every older
   presentation must have the same rate. A low historical pilot rate does not
   refute that proposition. Conversely, partial older alignments do not prove
   divine foresight or exclude ordinary calligraphic/textual explanations.

**The true origin of the Quran has not been identified by this experiment.**
The evidence now reaches beyond one modern print, but a causal explanation
still requires independently motivated writing rules, copying/exemplar
history, or predictions that distinguish the proposed explanations.

The finite next step is independent adjudication of these six pages' word
centers and colophon, with a shared historical/modern ink-center convention
and explicit row/line-end transcription. Only after that should a new,
genuinely held-out folio sample be frozen. The exposed versos and corrected
rectos are development evidence; do not reuse them as fresh validation.

### 6. Reproduction and checks

```bash
. .venv/bin/activate
# Scan-free arithmetic/canonical inventory replay:
python tools/historical_copy_analysis.py --verify
python -m unittest discover -s tools -p 'test_historical_copy.py' -v

# With the local acquisition cache:
python tools/historical_copy_pilot.py --verify
python tools/historical_copy_pilot.py --verify --corrected-indices
python tools/historical_copy_pilot.py --publish-manifest
python tools/historical_copy_pilot.py --review

# Public network retrieval if the cache is absent:
python tools/historical_copy_pilot.py --internet-archive
python tools/historical_copy_pilot.py --internet-archive --corrected-indices
```

For slow retrieval use `setsid`, with output under `logs/`. The direct OPenn
mode also exists, but did not succeed from this shell; failed TLS/transport
routes were not bypassed. No paid OCR/API, GPU or credentials were used.

`tools/data/research_historical_copy_{plan,retrieval_amendment,index_correction,annotations,analysis,sources}_v1.json`
retain the protocol, both retrieval failures/corrections, complete manual
inventory and source hashes/URLs. Downloaded scans, raw metadata, manifests
and ruler sheets are local in `logs/historical-copy-ms-or-422-v1/`.
The analysis refuses to overwrite its result and verifies by reconstruction.
**Five tests pass**, including exhaustive coordinate/width perturbations,
inclusive thresholds, endpoint counting, same-row/page exclusions, standalone
spellings and TEI label/path integrity. Both acquisition manifests pass byte
hash/size verification; deterministic scan-free score replay passes.

## 2026-10-19 — shared-center review and a positive historical phrase example

**The historical evidence now includes a measured three-word alignment in the
catalogued 1779 copy.** On **folio 200r, physical rows 3 and 4**, the two
occurrences of **`من دون الله` in 29:17** align word by word, including the
two ordinary words preceding Allah. The example was spotted during exposed
scan review; it is a post-hoc case, not a new randomly selected sample.

### A complete corresponding-word example

The body-center differences on 1000px-wide scan sheets are:

| corresponding word | horizontal center difference | fraction of the 623px verse-text frame |
|---|---:|---:|
| `من` | 8.5px | 1.36% |
| `دون` | 5px | 0.80% |
| `الله` | 2px | 0.32% |

Every corresponding pair passes both **2%** and **1.5%** tolerances. This
checks individual lexical centers, rather than merely the midpoint of the
phrase's combined span. Canonical IDs are **51219–51221** and **51228–51230**.
The same six tokens also align at both tolerances in the existing modern
ledger, with corresponding differences **1, 2, 4.5px**; those detector-based
phrase measurements are contextual, not a new manual phrase comparison.

Under the declared **±5px center / ±3px frame-edge** working allowances, the
historical **Allah pair is guaranteed at 2%**, while the whole three-word
match is not guaranteed. For all three pairs to be guaranteed simultaneously,
the common center allowance would need to be at most **1.92px** at 2%, or
**0.3775px** at 1.5%, retaining the frame-edge allowance. These are exact
allowance boundaries, not measured annotation precision. The nominal phrase
alignment is positive evidence; uncertainty is retained.

### Audit of every paired name under one convention

A separate plan was saved before revised annotations or revised scores. All
**33 historical and 33 matched modern names** were manually remeasured using
one operational convention: midpoint of the complete token's baseline-connected
letter bodies, including attached prefixes/elongation, excluding detached
vocalization marks. Each source was resized to 1000px width; text-frame width
was manually read as the verse-letter-body envelope in both copies. This
reduces the earlier manual-versus-detector convention mismatch. It remains a
single-reader development measurement, without deskew/perspective correction.

Two old historical annotations were over the wrong text: **18:45 on 150r**
and **44:42 on 250r**. Their old/new intervals and scan context are retained
in the new annotation file. The corrected 18:45 location adds a historical
Allah partner; the 44:42 correction has no partner on its selected folio.
The earlier frozen artifacts remain reproducible but are superseded for
current historical localization by this review.

| tolerance | group | historical lower / midpoint / upper | modern lower / midpoint / upper |
|---|---|---:|---:|
| 2% | family, n=33 | **2 / 10 / 14** | **24 / 27 / 27** |
| 2% | standalone, n=29 | **2 / 10 / 12** | **23 / 23 / 23** |
| 1.5% | family, n=33 | **0 / 8 / 13** | **22 / 26 / 27** |
| 1.5% | standalone, n=29 | **0 / 8 / 11** | **21 / 23 / 23** |

Both copies now receive the same uncalibrated coordinate allowances. Lower
and upper endpoint counts retain their conservative pairwise interpretation.
The historical primary midpoint result is therefore **10/33**, superseding
the earlier **8/33** mixed-convention development number. Fifteen physical
row-end slots per historical folio are recorded, including explicit nonverse
rows; these anchors are not complete lexical row transcriptions.

### What supports the user's investigation

This supplies a specific, inspectable instance of **multiword alignment before
the modern tawafuq project**, and a same-name pair surviving the stated
coordinate perturbations. Its words are selected by canonical identity, not
highlight color. It strengthens the historical premise of the investigation:
some word/phrase alignments already occur in a substantially earlier layout.

It does not yet establish why the alignment occurred. The repeated phrase is
near the end of two adjacent manuscript rows, and ordinary copying constraints
or shared layout traditions can contribute. Dating is still catalogue plus
single-reader colophon evidence; exemplar independence and material dating
remain unverified. Its likelihood under divine versus human explanations has
not been estimated. See the latest supporting-evidence synthesis in
[DIVINE-ORIGIN.md](DIVINE-ORIGIN.md).

### Replay and review files

```bash
. .venv/bin/activate
python tools/historical_center_review.py --verify
python tools/historical_center_review.py --phrase --verify
python -m unittest discover -s tools -p 'test_historical*.py' -v
# Optional local scan checks and review-sheet reconstruction:
python tools/historical_center_review.py --verify-scans
python tools/historical_center_review.py --sheets
python tools/historical_center_review.py --candidate-sheet
```

New artifacts: `research_historical_center_{plan,annotations,sources,review}_v1.json`
and `research_historical_phrase_{plan,review}_v1.json` in `tools/data/`.
Local raw-context rulers/strips: `logs/historical-center-review-v1/`.
**Ten focused tests pass**, both new deterministic reports replay, all **14
source image hashes** match, and the earlier historical analysis/acquisition
checks still pass. Independent adjudication remains pending; this review does
not supply a second reader or authorize a held-out extension by itself.

## 2026-10-19 — second copy: 1776 manuscript, local GPU OCR and ordinary phrases

**A second pre-project manuscript now supplies positive word and ordinary-phrase
examples.** The [OPenn catalogue for Columbia MS Or 91](https://openn.library.upenn.edu/Data/0032/html/ms_or_091.html)
describes a complete Quran, **1189 AH / 1776**, probably Iran, with **18 long
lines**, naskh script and inset color-contrast paper. Its original Columbia
bibid is **13554142**, digital bibid **13604207**, and public facsimile is
[IA ldpd_13604207_000](https://archive.org/details/ldpd_13604207_000).
This differs visibly in hand and layout from the previously studied 15-line
MS Or 422. Both catalogues call the script **naskh**; a different named script
family has not been demonstrated.

### Selection and complete name accounting

Before opening any image of MS Or 91, a local plan fixed **33r, 66r, 99r, 132r,
165r**, plus the catalogued colophon as a separate dating check. The five
rectos are evenly spaced, not chosen for their alignments. All show the
requested handwritten foliation and are retained, including the zero-alignment
name page. Partial boundary verses are handled by explicit canonical **word
ordinals**, rather than counting every name in an entire boundary verse.
On 99r the following token `والأرض` is split after its initial waw; this
non-name partial token is recorded separately from the complete-token span.

| folio | canonical complete-token span | family names | aligned at 2% | guaranteed endpoints under working allowances |
|---|---|---:|---:|---:|
| 33r | 4:123 word 2 – 4:132 end | 17 | **11** | 2 |
| 66r | 9:100 word 22 – 9:111 word 18 | 16 | **9** | 4 |
| 99r | 19:47 word 5 – 19:65 word 2 | 3 | **0** | 0 |
| 132r | 31:18 word 4 – 31:31 word 13 | 19 | **15** | 2 |
| 165r | 48:16 word 1 – 48:26 word 6 | 11 | **3** | 2 |
| **Total** | five fixed folios | **66** | **38 (57.58%)** | **10** |

All **66 names** were manually checked in the scans against the canonical
inventory; **52** are standalone Allah. Whole-token baseline-connected body
midpoints, manually read verse-text body frames and 1000px-wide sheets follow
the shared convention of the previous review. Detached marks are excluded,
attached prefixes retained. At least one partner must be on a different row
of the same physical page; no outside names supply partners.

| tolerance | group | historical lower / midpoint / upper | modern same-token ledger midpoint |
|---|---|---:|---:|
| 2% | family, n=66 | **10 / 38 / 50** | **58/66 (87.88%)** |
| 2% | standalone, n=52 | **6 / 25 / 32** | **42/52 (80.77%)** |
| 1.5% | family, n=66 | **0 / 30 / 47** | **56/66** |
| 1.5% | standalone, n=52 | **0 / 21 / 31** | **42/52** |

Historical bounds again assume uncalibrated **±5px centers / ±3px frame edges**.
They are conservative coordinate envelopes, not confidence intervals. All 66
modern tokens have locations in the unchanged ledger, but its detector centers
are contextual and are not new manual measurements. The **15/19** favorable
historical page is worth inspecting; it is not a substitute for the **38/66**
pooled result or a corpus-wide rate.

### Positive ordinary-word example and a retained nonmatch

On **99r, rows 4 and 8**, **`واذكر في الكتاب`** at the openings of **19:51**
and **19:56** aligns at all three corresponding centers. The differences are
**5px, 1.5px, 1px** across a **575px** text frame. Every word passes **1.5%**
and 2% tolerances. **Allah is not part of this measured phrase.** Its canonical
spellings in the Uthmani ledger are `واذكر فى الكتب`; historic orthography and
letter-body geometry are read from the actual scan.

The whole phrase is not guaranteed against every declared ±5px perturbation;
the `الكتاب` word pair is guaranteed at 2%. A third in-page occurrence at
**19:54** crosses rows **6/7**, and is explicitly retained as unmeasured for
the single-row three-word comparison. This is an exposed exploratory example,
not a preregistered phrase-prevalence result.

Conversely, **`ما في السماوات`** occurs four times within complete rows on
33r (4:126, twice in 4:131, and 4:132). All four were measured: **none of the
six possible corresponding-word pairs** passes the strict whole-phrase 2%
criterion. This preserves a concrete counterexample to automatic alignment
of every repeated phrase under this presentation.

### What GPU OCR contributed

Local **Surya 0.17.0** ran on a UUID-selected **RTX A6000**, using cached model
weights and inputs resized to at most 2400px height. Raw predictions, exact
input sizes, timings and model/package hashes are retained. Five text folios
and the initially mistaken colophon acquisition were processed; peak allocated
GPU memory was **2,159,608,832 bytes**. No Google/API request or charge was used.

OCR helped navigate the text, but is unsuitable as a direct name census here:
on **165r** one name-free physical row produced a repetition loop with **52
Allah-family mentions**. Raw text totals there are **61**, versus the manually
checked **11 actual page names**. OCR also misses or corrupts genuine words.
No precision/recall claim is inferred from those raw totals. Scored locations
and counts come from the scan-checked canonical manual inventory.

### Colophon acquisition correction and dating strength

The initial extrapolated IA **n402** showed the **back cover**, not the colophon.
It and its failed OCR are retained. A separately documented acquisition at
**n398** contains an actual completion statement, beginning
`وقع الفراغ من كتابة هذا القرآن المجيد`. The enlarged date passage supports
**1189 AH**, agreeing with the catalogue's 1776 attribution in a single-reader
inspection. The photographed handwritten foliation appears to be **197**,
whereas the catalogue cites **199r**: that discrepancy remains unresolved.

The catalogue additionally describes an **1895 customs stamp**; it was not
acquired or visually checked in this pilot. These catalogue mirrors are one
descriptive authority. Neither material dating nor independence of copying
exemplars has been established.

### What this adds to the supporting case

We now have substantial same-name alignment on some fixed pages and an
ordinary three-word alignment in **another manuscript predating the modern
project**, under a visibly different hand and 18-line arrangement. Together
with the 1779 copy, this makes the pre-project word/phrase premise more concrete.
The evidence is compatible with the user's proposal that presentation changes
visual prominence. It does not yet show that the older pool is as aligned as
the modern print, or that differences in handwriting alone explain the gap.

In particular, the ordinary phrase examples occur near line ends. A claim of
latent structure beyond copying/line-end constraints needs independent writing
rules or predictions across additional copies. The proposed divine reason for
later visibility remains a theological interpretation rather than a measured
historical or mathematical result.

The collection catalogue now offers further **unscored** leads: MS Or **249**
(1537), **186** (1680), **231** (1812–13), **230** (1817–18), and **200**
(1847–48). Those dates are catalogue descriptions; no images or alignments of
these candidates were inspected in this continuation.

### Reproduction and checks

```bash
. .venv/bin/activate
python tools/historical_extension.py --verify
python -m unittest discover -s tools -p 'test_historical*.py' -v
# Optional existing local acquisition/OCR checks:
python tools/historical_extension.py --verify-sources
python tools/historical_extension.py --verify-ocr
python tools/historical_extension.py --case-sheets
```

Code: `tools/historical_extension.py`, `tools/test_historical_extension.py`.
Artifacts: `research_historical_extension_{plan,sources,annotations,ocr}_v1.json`,
`research_historical_extension_colophon_{amendment,source}_v1.json`, first measured
`research_historical_extension_review_v1.json`, and current portable
**`research_historical_extension_review_v2.json`**, under `tools/data/`.

The first measured report required ignored raw OCR files for reconstruction.
A post-score portability-only revision archives that summary and enforces
identical scientific outcomes; the original report is retained. Current
`--verify` needs neither scans, GPU/model weights, local OCR cache nor network.
The optional `--verify-ocr` checks the retained raw OCR against the archive.

**15 focused historical tests pass**, including exact thresholds/envelopes,
partial boundary verses, invalid/reversed spans, repeated-phrase identities
and preservation of every first-measured scientific outcome. Portable replay,
all **nine acquisition hash/size checks**, and local OCR summary/hash replay
pass. Raw scans, review sheets and OCR remain in
`logs/historical-extension-ms-or-91-v1/`; acquisition and GPU run logs are in
`logs/historical-extension-{acquire,gpu}-v1.log`.

## 2026-10-19 — final enlarged-context correction: current second-copy results

**Use review v3 for current name rates.** The preceding section's **38/66**
pooled count and **15/19 on 132r** were first-pass ruler results and are
superseded. Before concluding the extension, every one of the 66 name intervals
was exposed on six enlarged scan-context contact sheets. Full-width row rulers
and finer enlarged details then revealed misplaced intervals over neighboring
words and incomplete prefixes. **17 intervals** were corrected explicitly;
49 were retained. Original annotations and v1/v2 results remain available.
This is a same-reader correction, not independent adjudication.

| tolerance | group | corrected historical lower / midpoint / upper | modern same-token detector midpoint |
|---|---|---:|---:|
| 2% | family, n=66 | **10 / 34 / 49** | **58/66** |
| 2% | standalone, n=52 | **8 / 26 / 33** | **42/52** |
| 1.5% | family, n=66 | **0 / 28 / 44** | **56/66** |
| 1.5% | standalone, n=52 | **0 / 22 / 32** | **42/52** |

The current primary family rate is **34/66 = 51.52%**, and standalone Allah
is **26/52 = 50%**. Corrected per-folio family midpoint counts are **11/17,
10/16, 0/3, 10/19, 3/11** for 33r through 165r. Ten family endpoints remain
guaranteed under the same uncalibrated coordinate allowances. Neither the
selection, canonical inventory, physical rows, frames, tolerance nor error
allowances was changed to obtain these corrections.

The independently measured **ordinary three-word example on 99r is unchanged**:
`واذكر في الكتاب` at 19:51/56 passes all three corresponding centers at 1.5%.
Its enlarged raw-context sheet was separately inspected. The four-occurrence
33r phrase nonmatch is also unchanged. The corrections affect the name ledger,
not the existence of this positive ordinary-phrase observation.

The supporting conclusion is therefore narrower and more accurate: **both
pre-project copies show some same-word/phrase alignment; the second fixed
sample has roughly half its selected names aligned, rather than a demonstrated
modern-like pooled rate.** The proposed style/latent-design explanation remains
an investigable interpretation, with copying/line-end constraints unresolved.

Current files and commands:

```bash
. .venv/bin/activate
python tools/historical_extension_final_review.py --verify
python -m unittest discover -s tools -p 'test_historical*.py' -v
# With local scans, rebuild enlarged evidence including corrected intervals:
python tools/historical_extension_review_sheets.py --corrected
python tools/historical_extension_review_sheets.py --rows
python tools/historical_extension_review_sheets.py --details
```

`tools/data/research_historical_extension_coordinate_review_v1.json` records
every old/new interval and the review procedure. Current results are
`tools/data/research_historical_extension_review_v3.json`.
`tools/historical_extension_final_review.py` verifies the original intervals
before applying each correction, preserves all canonical identities/rows and
recomputes scores from the corrected ledger. `historical_extension.py --verify`
still replays the **superseded v2** for provenance; it is not the current scorer.

**18 focused tests pass**, current v3 scan-free reconstruction passes, and
`git diff --check` passes. The corrected contact sheets for all altered sites
were inspected against the underlying lettering after reconstruction. Earlier
source/OCR hash checks remain applicable because no source bytes changed.
