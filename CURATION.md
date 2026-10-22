# CURATION.md — what is in this repository and why

This is a curated open-source release of the tawafuq study, cut from the
internal working repository on 2026-10-21. Every file is placed in one of
three roles: **verification** (check the claims with no scans and no network),
**reproduction** (rebuild artifacts from the page scans you download
yourself), or **publication/provenance**. A fourth list records what was
deliberately **excluded** as internal-only or not redistributable.

Total: ~426 MB tracked (of which ~408 MB is committed verification data).

## 1. Verification (no scans, no network)

Entry point:

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-audit.txt
python tools/verify_cpu.py
```

`tools/verify_cpu.py` parses every `tools/*.py`, runs all 42 `test_*.py`
suites, then replays — from committed data only — the independent reference
scorer, input hashes, analytic expectations, stored Monte-Carlo inference,
and the exact-rational column-tail bounds (`< 2×10⁻⁷²⁶` merged-group,
`< 10⁻⁸¹⁴` size-filtered raw components). `--full` additionally regenerates
the deterministic Monte-Carlo streams.

What it consumes:

- `tools/data/audit_*.json`, `tools/data/research_*.json` (92 + 38 reports) —
  frozen audit artifacts with embedded input hashes.
- `tools/data/real_boxes/`, `tools/data/real_boxes_v3/` — extracted ink-box
  populations the statistics are computed from.
- `tools/data/ocr_*_v*/` directories — saved OCR service responses replayed
  without credentials or network.
- `tools/data/token_map*.json`, `mark_identity*.json`, rosette maps,
  `page_verse_map.json`, `quran-uthmani.json` — canonical text and pin
  ledgers.

Verification documentation: `docs/VERIFY.md` (technical guide, formerly the
root README), `docs/AUDIT.md` (full audit log and replay commands),
`docs/AUDIT-CONCLUSION.md` (claim dispositions).

## 2. Reproduction (requires the downloaded scans)

The scans are **not** included; fetch them per `docs/DOWNLOAD-HAYRAT.md`
into a local `hayrat-pics/` directory. Then the pipeline in execution order
is documented in `docs/VERIFY.md` and `tools/README.md`:

- extraction: `tools/image_io.py`, `tools/real_extract.py`,
  `tools/page_scan.py`, `tools/rosette_digits.py`, `tools/rosette_map.py`,
  `tools/build_token_map2.py`, `tools/mark_identity.py`,
  `tools/red_clusters.py`
- statistics: `tools/real_stats.py`, `tools/type_rates.py`,
  `tools/audit_stats.py`, `tools/exact_column.py`,
  `tools/geometry_controls.py`, `tools/divine_census.py`
- optional GPU OCR pilots: `tools/arabic_ocr.py`,
  `tools/arabic_ocr_easy.py` (`requirements-ocr.txt`, isolated env);
  cloud OCR: `tools/arabic_ocr_cloud.py` (your own credentials, never
  committed — `requirements-cloud-ocr.txt`)

`tools/README.md` carries the full triage, including which scripts are the
canonical pipeline and which are exploration archive kept for provenance.

## 3. Publication and provenance

- `README.md` — the article, rebuildable with
  `tools/build_readme_from_v7.py` from
  `docs/articles/tawafuq-v9-structure.json` (extracted from the v9 ODT
  `tawafuq-v9-short.odt`; both stay in git, alongside the historical v7
  structure JSON). The reworded and trimmed 19er section lives in the ODT
  itself (patched and tracked changes accepted 2026-10-22); two injected
  blocks — the about box and the numbers-provenance curation note — plus the
  builder's historical `CURATION_FIXES` record are README-side only, so the
  structure JSON stays otherwise byte-faithful to the ODT.
- `media/` — the 10 article figures, sha256-identical to
  `docs/articles/figs/`.
- `docs/articles/` — current drafts, the numbers spreadsheet and figure
  sources; `tools/build_article_*.py` rebuild the published renditions
  (historical ODT/PDF lineage stays in git history).
- `LICENSE` — MIT for the code and measurement artifacts in this repository.
  (It does not cover the Hayrat scans you download, or the third-party
  text in `docs/sources/`; only the CC BY 4.0 Hussain 2023 paper is archived —
  see `docs/sources/README.md`.)

## 4. Excluded — internal-only / not redistributable

| excluded | why |
|---|---|
| `hayrat-pics/` (604 scans) | publisher copyright; obtain via `docs/DOWNLOAD-HAYRAT.md` |
| `logs/` | may contain local credentials, paid-OCR raw caches, private review crops and build intermediates — never publish |
| `.venv/`, `__pycache__/` | local environment and build junk |
| `tools/data/red_feats.npz` (112 MB) | intermediate scan features; regenerable from the scans, not needed for verification |
| `AGENTS.md` | internal agent-operating rules for the working repo |

No credentials, keys, internal IPs or account identifiers are present in this
release; the only historical credential file lived under `logs/` and was
never tracked by git.

## Notes on scope

- The article keeps the frozen publication figures; the marked
  "Numbers provenance" note beside the headline figure points to the audited
  component-level numbers. The audit (2026-10-18/19) withdrew several earlier
  presentations — see `docs/AUDIT-CONCLUSION.md` before quoting anything.
- Byte-hash pins in the audit describe the original PNG encoding of the
  scans; freshly downloaded JPEGs are the same pages but not byte-identical
  (`docs/DOWNLOAD-HAYRAT.md`).
- Nothing here is an origin probability. `verify_cpu.py` prints the standing
  reminder: it verifies explicit statistical models, not causal claims.
- Historical commit IDs (`01cbb77`, `bea87f3`, ...) and `logs/...` paths in
  `docs/AUDIT.md` belong to the internal working repository and its gitignored
  run logs; they cannot be resolved from this curated history. The committed
  artifacts and `verify_cpu.py` are the public replay path.
