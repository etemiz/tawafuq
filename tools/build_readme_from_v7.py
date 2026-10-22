#!/usr/bin/env python3
"""Convert the frozen article structure into the repository README.md.

Input: docs/articles/tawafuq-v9-structure.json (paragraphs, images with
sha256, tables extracted from docs/articles/tawafuq-v9-short.odt; the v7
extraction and builder history stay in git).
Images are matched against docs/articles/figs/** by sha256, copied into
media/ under their original basenames, and embedded with the caption as
alt text. Two curation blocks are inserted: an about-this-repository note
after the lede, and a numbers-provenance note after the headline figure.
Run from the repository root: python tools/build_readme_from_v7.py
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STRUCTURE = ROOT / "docs/articles/tawafuq-v9-structure.json"
FIGS = ROOT / "docs/articles/figs"
MEDIA = ROOT / "media"
OUT = ROOT / "README.md"

# v9 paragraph roles (from the ODT automatic styles: 16pt bold brown = H2,
# 12.5pt bold brown = H3, 9pt gray centered = caption, 13pt brown centered
# = subtitle, 10pt centered = byline).
H2 = {"P13", "P20", "P27", "P29"}
H3 = {"P23"}
BULLET = "P24"
CALLOUT = "P19"
CAPTION = "P15"
TITLE = "P1"
LEDE = "P2"
BYLINE = "P3"

ABOUT = """\
> **About this repository.** This is the open release of the tawafuq study:
> the article below, the measurement code, and every audit artifact needed to
> check the numbers without trusting the authors.
>
> - **Verify (no scans, no network):** `python tools/verify_cpu.py`
>   — replays hashes, independent scorers, analytic means and exact-rational
>   probability bounds from committed data.
> - **Reproduce from scans:** download the 604 Hayrat page images yourself
>   (they are not redistributed here) following `docs/DOWNLOAD-HAYRAT.md`,
>   then run the extraction pipeline in `tools/`.
> - **What each file is for:** see `CURATION.md`. Verification entry points
>   and proof scope: `docs/AUDIT.md`, `docs/VERIFY.md`.
"""

PROVENANCE = """\
> **Numbers provenance (curation note, 2026-10-21).** The headline figures
> above (72.65% vs 25.35% ± 0.76%, z = 62.2; certified bound < 10⁻⁸¹⁴) are
> the article's frozen publication numbers. The open-source audit certifies
> the current component-level numbers, all replayable with
> `python tools/verify_cpu.py`: crimson components aligned
> **3,339 / 4,582 = 72.87%** against a **26.2%** analytic null
> (`tools/data/audit_global_v3.json`); exact-rational column-tail bounds
> **< 2 × 10⁻⁷²⁶** for merged groups (3,271 flags) and
> **< 10⁻⁸¹⁴** for size-filtered raw components (3,522 flags)
> (`tools/data/audit_exact_columns*.json`). The older word-level
> "3,357 of 4,621" census is a historical Phase-A figure; the audit notes
> that the current `real_stats.py` denominator differs
> (`docs/AUDIT.md`). Both bounds are model-conditional, not origin proofs.
"""

# Curation-layer substitutions applied after conversion, so the structure
# JSON stays byte-faithful to the ODT while the README points at published
# files (RESULTS.md was retired at open sourcing) and carries the verified,
# Readability-rewritten 19er section: reworded on 2026-10-22 and patched
# into tawafuq-v9-short.odt itself (so the ODT and README now carry the
# same reviewed text); the entry is kept as a no-op guard and as the
# record of the old wording it superseded.
CURATION_FIXES = {
    "(RESULTS.md; red_types.npz)": "(AUDIT.md; red_types.npz)",
    "We tested the “19er” premise — Rashad Khalifa’s Code 19, which removes "
    "verses 9:128-129 and builds count claims on the shortened text — against "
    "the mushaf itself instead of against arithmetic. Three results. First, "
    "the removed words are live design, not passengers: the hasbiya-Allah of "
    "9:129 sits in p.206’s own 3-word left-edge column and has four "
    "same-cell, same-shape Allah partners elsewhere in the book (pp. 83, 112, "
    "115, 205), so the excision deletes working alignment; the two huwa words "
    "of 9:129 are not positionally aligned but carry the mushaf’s "
    "partner-sign marking (a semantic sign layer). Second, the removal "
    "desynchronizes the printed artifact: the gold rosette chain pins the "
    "verse count page by page — our page↔verse map reproduces it with zero "
    "violations across all 604 pages, and pages end at verse ends on every "
    "checkable page (581 strict + 3 hanging of 584) — so a text two verses "
    "short falls out of register with the printed structure for every page "
    "after 9:127. That is what “removing the two verses hurts the alignment” "
    "means concretely: it hurts the following pages’ verse-end alignment, "
    "not just one page. Third, we reject the 19-numerology frame itself: it "
    "is the same convention-fragile counting we decline to use as evidence "
    "(the halving series, 6,666), and the one computational paper built on "
    "it (IJASAT 2019) carries internally inconsistent verse arithmetic (its "
    "Δ4 against an actual Δ9, a Table 1 verse count that contradicts its own "
    "assumptions, a Table 4 row contradicting its body text). Honest caveat: "
    "our word-level test of the insertion claim is small (n=3, statistically "
    "inconclusive) — but it found no insertion-break signature, and what "
    "signal there is leans against the removal.": (
        "We tested the “19er” premise — Rashad Khalifa’s Code 19, which "
        "removes verses 9:128–129 and then builds its counts on the "
        "shortened text — against the mushaf itself instead of against "
        "arithmetic. Three results.\n"
        "\n"
        "First, the removed words are live design, not passengers. On page "
        "206, the hasbiya-Allah of 9:129 (“Allah is sufficient for me”) "
        "sits at the end of line 11, inside that page’s own three-word "
        "left-edge column of crimson words — and the same end-of-line slot "
        "on line 11 holds a same-shape crimson Allah word on four other "
        "pages of the book: 83, 112, 115 and 205. So the supposedly “added” "
        "verse does exactly what the rest of the book’s divine names do; "
        "cut it out, and working alignment goes with it. The verse’s two "
        "huwa words (“He”) line up with nothing by position. The first one, "
        "however, sits right beside the phrase لَا إِلَٰهَ إِلَّا هُوَ "
        "(“no god but He”), which the printer inked in magenta — and the "
        "identical phrase in 27:26 carries the identical magenta mark: a "
        "second, meaning-based marking system layered on top of the "
        "positional one. The second huwa is printed plain black.\n"
        "\n"
        "Second, removing the two verses would throw the printed book out "
        "of step with itself. This mushaf is an ayet-berkenar book: every "
        "page ends at a verse boundary (581 strict + 3 hanging of 584 "
        "checkable pages), and the gold rosette medallions pin the verse "
        "count page by page (our page↔verse map reproduces 6,080 of 6,083 "
        "rosettes with zero tile violations). A text two verses short stops "
        "matching those printed markers from page 206 onward — on every "
        "page after 9:127. That is what “removing the two verses hurts the "
        "alignment” means in practice: not one page, but the verse-end "
        "alignment of everything that follows.\n"
        "\n"
        "Third, we reject the 19-numerology frame itself. It is the same "
        "convention-fragile counting we decline to use as evidence (the "
        "halving series, 6,666), and the one computational paper built on "
        "it — IJASAT 2019 — cannot keep its own verse arithmetic straight: "
        "it announces “the difference is only four” where the actual "
        "difference is nine; its Table 1 says the Quran has 6,236 verses "
        "while its own calculations divide 6,666 by two; and its Table 4 "
        "prints 464 verses for Nisa–Anam while its body text says four "
        "hundred and sixty-one.\n"
        "\n"
        "Honest caveat: our word-level test of the insertion claim is small "
        "(three marked words) and statistically inconclusive. It found no "
        "insertion-break signature, and the little signal there is leans "
        "against the removal."),
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fig_lookup():
    table = {}
    for path in FIGS.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".svg"}:
            table[sha256(path)] = path
    return table


def clean(text):
    return " ".join((text or "").split())


def esc_cell(text):
    return clean(text).replace("|", "\\|")


def table_md(rows, out):
    rows = [r for r in rows]
    while rows and not any(clean(c) for c in rows[0]):
        rows.pop(0)
    if not rows:
        return
    width = max(len(r) for r in rows)
    rows = [list(r) + [""] * (width - len(r)) for r in rows]
    out.append("| " + " | ".join(esc_cell(c) for c in rows[0]) + " |")
    out.append("|" + "|".join([" --- "] * width) + "|")
    for row in rows[1:]:
        out.append("| " + " | ".join(esc_cell(c) for c in row) + " |")
    out.append("")


def main():
    items = json.loads(STRUCTURE.read_text())
    lookup = fig_lookup()
    MEDIA.mkdir(exist_ok=True)
    out = []
    pending_caption = None
    last_was_image = False
    injected_about = False

    def flush_caption():
        nonlocal pending_caption
        if pending_caption and last_was_image:
            out.append(f"*{pending_caption}*")
            out.append("")
        pending_caption = None

    for item in items:
        if item["type"] == "image":
            sha = item["sha"]
            source = lookup.get(sha)
            if source is None:
                raise SystemExit(f"no figure match for {item['href']} sha={sha}")
            target = MEDIA / source.name
            if not target.exists() or sha256(target) != sha:
                shutil.copy2(source, target)
            out.append(f"![{source.stem}](media/{source.name})")
            out.append("")
            last_was_image = True
            continue
        if item["type"] == "table":
            flush_caption()
            table_md(item["rows"], out)
            last_was_image = False
            continue

        style = item.get("style", "")
        text = clean(item.get("text", ""))
        if style == TITLE:
            out.append(f"# {text}")
            out.append("")
            continue
        if style == LEDE:
            out.append(f"**{text}**")
            out.append("")
            continue
        if not text:
            continue
        if style == BYLINE:
            out.append(f"**{text}**")
            out.append("")
            out.append(ABOUT)
            injected_about = True
            continue
        if style == CAPTION:
            pending_caption = text
            if last_was_image:
                flush_caption()
            else:
                # caption after a table or loose caption: render italic line
                out.append(f"*{text}*")
                out.append("")
                pending_caption = None
            continue
        flush_caption()
        if style in H2:
            if out and out[-1] != "":
                out.append("")
            out.append(f"## {text}")
            out.append("")
        elif style in H3:
            if out and out[-1] != "":
                out.append("")
            out.append(f"### {text}")
            out.append("")
        elif style == BULLET:
            body = text[1:].strip() if text.startswith("•") else text
            out.append(f"- {body}")
        elif style == CALLOUT:
            if out and out[-1] != "":
                out.append("")
            out.append(f"> {text}")
            out.append("")
        else:
            if not injected_about:
                # structure without a byline: still inject the about block
                out.append(ABOUT)
                injected_about = True
            out.append(text)
            out.append("")
        last_was_image = False
    flush_caption()

    # Provenance note goes directly after the headline-figure caption block.
    final = []
    inserted = False
    i = 0
    while i < len(out):
        line = out[i]
        final.append(line)
        if not inserted and line.startswith(
                "*Real book vs 400 shuffled copies."):
            final.append("")
            final.append(PROVENANCE.rstrip("\n"))
            inserted = True
        i += 1
    if not inserted:
        raise SystemExit("headline figure caption not found; "
                         "provenance note not inserted")

    final.append("---")
    final.append("")
    final.append(
        "Converted from the v9 article structure "
        "(`docs/articles/tawafuq-v9-structure.json`, extracted from "
        "`tawafuq-v9-short.odt`, which stays in git; builder: "
        "`tools/build_readme_from_v7.py`). Figures in `media/` are "
        "sha256-identical to `docs/articles/figs/`."
    )
    text = "\n".join(final).rstrip() + "\n"
    for old, new in CURATION_FIXES.items():
        text = text.replace(old, new)
    OUT.write_text(text)
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes), images in {MEDIA}")


if __name__ == "__main__":
    sys.exit(main())
