"""Patch article v5 (ODT) and its numbers workbook (ODS) to align with the bounded audit.

Run from the repository: . .venv/bin/activate && python tools/patch_article_v5.py [--dry-run]

Every replacement must match exactly once; the script aborts before writing otherwise.
Backups of the original files are written under logs/article-v5-patch/.

Dispositions applied (see docs/AUDIT-CONCLUSION.md, checkpoint 01cbb77):
  1. Grain sweep: corrected exploratory crimson excess at several grains replaces the
     withdrawn "no grain revives word-specific alignment" negative.
  2. Human-engineering bound: kept, labeled as a model-dependent heuristic per the audit.
  3. Rosette ground truth: 99.4% CV marked historical/not-committed; p567 28/28 survives.
  4. Headline: audit's component-level restatement added; z unified to 62.2.
  5. Page-turn mirror: corrected v3 numbers (288 spreads, z ~ -0.7).
  6. Minor: magenta run count 7,227 (v1; v3: 7,130), pause-mark layer wording,
     pipeline provenance notes, dated corrections appendix.
"""

import argparse
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ODT = ROOT / "docs" / "articles" / "tawafuq-art-v5.odt"
ODS = ROOT / "docs" / "articles" / "tawafuq-numbers-v5.ods"
BACKUP = ROOT / "logs" / "article-v5-patch"

# ---------------------------------------------------------------- article (ODT)

ART_REPS = [
    # 1. grain sweep negative -> audit-corrected statement
    (
        "• Grain sweep (row/col, 15–224 px, mirrored): no grain revives word-specific alignment.",
        "• Grain sweep (row/col, 15–224 px, mirrored): the original negative stands at the 30 px "
        "label-permutation grain (z=+1.4 crimson), but the audit's corrected sweep finds exploratory "
        "crimson excess at several grains under a global-label model (z≈+3.8..+5.6; "
        "audit_grain_sweep_v3.json). Semantic labels, language controls and multiplicity remain "
        "unresolved — word-identity structure is open, not settled-negative.",
    ),
    # 5. page-turn numbers -> corrected v3
    (
        "• Page-turn mirror rule: 570 facing pairs, z = +0.1. Two anecdotes (p.154↔155, p.530↔531), not a rule.",
        "• Page-turn mirror rule: the audit's corrected v3 test (288 spreads) gives 28 mirror hits vs a "
        "31.85 mean, z ≈ −0.7 (audit_page_turn_v3.json). Two anecdotes (p.154↔155, p.530↔531), not a rule.",
    ),
    # 1. scope the word-identity negative to its grain
    (
        "• Word-identity pairing: NULL (slot-null z=+39.7 crimson, but label-permutation z=+1.4 — which "
        "word occupies a hot cell is uncorrelated across pages). The signal is the layout style of the "
        "ink system, not hidden word-pair design.",
        "• Word-identity pairing at the 30 px grain: NULL (slot-null z=+39.7 crimson, but "
        "label-permutation z=+1.4 — which word occupies a hot cell is uncorrelated across pages). The "
        "signal is the layout style of the ink system, not hidden word-pair design at this grain; see "
        "the grain-sweep note below for the audit's corrected multi-grain finding.",
    ),
    # 2. Step 5 audit caveat
    (
        "at realistic rates the range is 10^−95 to 10^−1,112. A 17th-century scribe",
        "at realistic rates the range is 10^−95 to 10^−1,112. The audit's caution on this step: a "
        "one-shot probability product is a model-dependent heuristic, not a certified "
        "construction-impossibility proof — retained-page retries alone invalidate reading the product "
        "as work (AUDIT-CONCLUSION.md). We keep the bound as a strong plausibility argument under the "
        "stated per-page independence model, not as a proof. A 17th-century scribe",
    ),
    # 2. closing rhetoric softened to match
    (
        "Between “chance is dead” and “human hands are dead”, the reader is left standing in front of an open door.",
        "Between “chance is dead” and “no arrangement we can model”, the reader is left standing in front of an open door.",
    ),
    # 2. AI-consumption H_human caveat
    (
        "plus historical impossibility of global search. What remains is a falsifiable residual",
        "plus historical impossibility of global search — a model-dependent heuristic per the audit, "
        "not a certified construction-work bound. What remains is a falsifiable residual",
    ),
    # 3. rosette ground truth
    (
        "6,083 rosettes digit-classified (99.4% leave-rosette CV) and globally DP-aligned into "
        "page_verse_map.json (6,080 aligned, 0 tile violations after ink-cost arbitration).",
        "6,083 rosettes digit-classified and globally DP-aligned into page_verse_map.json (6,080 "
        "aligned, 0 tile violations after ink-cost arbitration). The historical 99.4% leave-rosette CV "
        "is not implemented in committed code and was withdrawn by the audit as a corpus-wide "
        "certification; the surviving independent check is the p567 transcription (28/28 after the v3 "
        "map repair; audit_rosette_labels_v3.json).",
    ),
    # 4. Step 1 audit restatement
    (
        "(max over 400 reps: 28.8%).",
        "(max over 400 reps: 28.8%). The audit's rebuilt component-level restatement (components, not "
        "per-word boxes) gives 3,339/4,582 = 72.87% aligned vs a 26.22% simulated mean "
        "(audit_global_v3.json); the per-word census presentation here predates that rebuild and is "
        "retained for continuity.",
    ),
    # 4. z unified to 62.2 (pipeline line)
    (
        "• real_stats.py 400 → the headline effect size (z=62.3);",
        "• real_stats.py 400 → the headline effect size (z=62.2);",
    ),
    # 4. z unified to 62.2 (AI-consumption line)
    (
        "z=62.3 effect size",
        "z=62.2 effect size",
    ),
    # 3. pipeline rosette_digits line
    (
        "extract and classify all 6,083 gold rosettes (99.4% CV).",
        "extract and classify all 6,083 gold rosettes (the 99.4% CV figure is historical — not "
        "implemented in committed code, audit-withdrawn as certification).",
    ),
    # 6. pipeline mark_identity provenance
    (
        "crimson/magenta ink runs and pins (5,772 segments, 3,674 pins).",
        "crimson/magenta ink runs and pins (5,772 segments, 3,674 pins in v1; the audit's rebuilt v3: "
        "5,936 segments).",
    ),
    # 6. magenta row wording
    (
        "plus a selective layer over ~92 frequent words",
        "plus a selective pause-mark layer (92 pages)",
    ),
    # 6. magenta run count
    (
        "7,386 ink runs",
        "7,227 ink runs (v1; v3: 7,130)",
    ),
]

APPENDIX = (
    '<text:p text:style-name="P11">Corrections (2026-10-20)</text:p>'
    '<text:p text:style-name="P4">This article was patched on 2026-10-20 to align its '
    "negative-results section and interpretive claims with the bounded audit "
    "(docs/AUDIT-CONCLUSION.md, checkpoint 01cbb77). Every retained number was re-verified "
    "against the repo artifacts; the six changes are listed with their evidence.</text:p>"
    '<text:p text:style-name="P12">• Grain sweep: corrected exploratory crimson tests show excess at '
    "several grains under a global-label model (z≈+3.8..+5.6; "
    "tools/data/audit_grain_sweep_v3.json); the audit withdrew the earlier "
    "“negative at every grain” wording.</text:p>"
    '<text:p text:style-name="P12">• Page-turn mirror: corrected v3 test — 288 spreads, 28 hits vs a '
    "31.85 mean, z ≈ −0.7 (tools/data/audit_page_turn_v3.json); the earlier “570 pairs, z=+0.1” "
    "figures came from the pre-audit run.</text:p>"
    '<text:p text:style-name="P12">• Rosette ground truth: the 99.4% leave-rosette CV is not '
    "implemented in committed code and was withdrawn as a corpus-wide certification; the surviving "
    "independent check is p567 28/28 (tools/data/audit_rosette_labels_v3.json). The page↔verse map "
    "is now rosette_map_v3.</text:p>"
    '<text:p text:style-name="P12">• Human-engineering bound: retained as a model-dependent '
    "heuristic; the audit withdrew interpreting one-shot probability products as "
    "construction-work estimates.</text:p>"
    '<text:p text:style-name="P12">• Component-level restatement: 3,339/4,582 = 72.87% aligned vs a '
    "26.22% simulated mean (tools/data/audit_global_v3.json), alongside the per-word census "
    "(3,357/4,621 = 72.65% vs 25.35%±0.76%).</text:p>"
    '<text:p text:style-name="P12">• z unified to 62.2 (= (72.65 − 25.35) / 0.76); mark counts cite '
    "v1 (7,227 magenta runs of 10,962; the audit's v3 rebuild: 7,130 of 10,744).</text:p>"
)

# ------------------------------------------------------------- workbook (ODS)

ODS_REPS = [
    # z cell 62.3 -> 62.2
    (
        "<text:p>62.3</text:p>",
        "<text:p>62.2</text:p>",
    ),
    # withdrawn bits value -> certified bound value
    (
        "<text:p>≈3,269</text:p>",
        "<text:p>&lt;10^-814</text:p>",
    ),
    # page-turn row
    (
        "<text:p>Page-turn mirror rule (570 pairs)</text:p>",
        "<text:p>Page-turn mirror rule (288 spreads, v3)</text:p>",
    ),
    (
        "<text:p>z = +0.1 (anecdotes only)</text:p>",
        "<text:p>z ≈ −0.7 (28 vs 31.85 mean; anecdotes only)</text:p>",
    ),
    # grain sweep row
    (
        "<text:p>no revival of word-specific alignment</text:p>",
        "<text:p>audit withdrew: corrected cri excess at several grains (z≈+3.8..+5.6, "
        "global-label model); 30px label-perm null stands (z=+1.4)</text:p>",
    ),
    # H_human caveat
    (
        "<text:p>IMPLAUSIBLE — per-page independence ≈10^-28..10^-1,112; no global search; "
        "discoverer didn't write it; 9 hand-copies; uncurated failures</text:p>",
        "<text:p>IMPLAUSIBLE (model-dependent heuristic per audit) — per-page independence "
        "≈10^-28..10^-1,112; no global search; discoverer didn't write it; 9 hand-copies; "
        "uncurated failures</text:p>",
    ),
]


def patch_xml(xml, reps, label):
    for old, new in reps:
        n = xml.count(old)
        if n != 1:
            raise SystemExit(f"{label}: expected exactly 1 occurrence, found {n}: {old[:80]!r}")
        xml = xml.replace(old, new)
    return xml


def rewrite_zip(path, new_content_xml, dry_run):
    backup = BACKUP / path.name
    if not dry_run:
        BACKUP.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup)
    with zipfile.ZipFile(path) as zin:
        names = zin.namelist()
        data = {name: zin.read(name) for name in names}
        infos = {i.filename: i for i in zin.infolist()}
    data["content.xml"] = new_content_xml.encode("utf-8")
    if dry_run:
        print(f"[dry-run] {path.name}: would rewrite {len(names)} members "
              f"({'content.xml' in names} contains content.xml)")
        return
    tmp = path.with_suffix(path.suffix + ".tmp")
    with zipfile.ZipFile(tmp, "w") as zout:
        # mimetype must be the first member, uncompressed
        if "mimetype" in data:
            zout.writestr("mimetype", data["mimetype"], compress_type=zipfile.ZIP_STORED)
        for name in names:
            if name == "mimetype":
                continue
            comp = zipfile.ZIP_DEFLATED
            if infos[name].compress_type == zipfile.ZIP_STORED and name != "content.xml":
                comp = zipfile.ZIP_STORED
            zout.writestr(name, data[name], compress_type=comp)
    tmp.replace(path)
    print(f"[ok] {path.name}: patched, backup at {backup}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    with zipfile.ZipFile(ODT) as z:
        art = z.read("content.xml").decode("utf-8")
    with zipfile.ZipFile(ODS) as z:
        nums = z.read("content.xml").decode("utf-8")

    art_patched = patch_xml(art, ART_REPS, "article")
    assert art.count("</office:text>") == 1
    art_patched = art_patched.replace("</office:text>", APPENDIX + "</office:text>")

    nums_patched = patch_xml(nums, ODS_REPS, "workbook")

    rewrite_zip(ODT, art_patched, args.dry_run)
    rewrite_zip(ODS, nums_patched, args.dry_run)


if __name__ == "__main__":
    main()