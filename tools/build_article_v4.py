"""Build the V4 article: figures, checks, PDF, editable ODT and an ODS data workbook.

Run from the repository: . .venv/bin/activate && python tools/build_article_v4.py
Figures are written under docs/articles/figs/v4-2026-10-19 and never overwrite
assets used by earlier article versions. Headline statistics are re-derived from
the frozen evidence inputs; no earlier article's prose is reused.
"""

import argparse
from fractions import Fraction
from html import escape
from html.parser import HTMLParser
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile

import markdown
from PIL import Image, ImageDraw, ImageFont

from build_findings_article import (
    ARTICLE, DATA, ROOT, check_component_bound, digest, read_json, require,
)

STEM = "tawafuq-v4-2026-10-19"
VDIR = "v4-2026-10-19"
SOURCE = ARTICLE / f"{STEM}.md"
FIGS = ARTICLE / f"figs/{VDIR}"
REVIEW = ROOT / "logs/article-v4"
FINDINGS_FIGS = ARTICLE / "figs/findings-2026-10-19"

TEAL, GOLD, INK, MUTED, PALE, CRIMSON = "#14544b", "#b48842", "#233b3b", "#5f7773", "#edf4f1", "#c33d5f"

NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "draw": "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
    "xlink": "http://www.w3.org/1999/xlink",
}


def svg(name, width, height, body):
    (FIGS / name).write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}"><rect width="100%" height="100%" fill="white"/>'
        f'<g font-family="DejaVu Sans, sans-serif" fill="{INK}">{body}</g></svg>')


def txt(x, y, value, size=22, color=INK, weight="normal", anchor="start"):
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" '
            f'font-weight="{weight}" text-anchor="{anchor}">{escape(str(value))}</text>')


# ---------------------------------------------------------------- infographics

def fig_component_comparison(summary):
    observed = 100 * summary["observed"] / summary["selected"]
    expected = 100 * summary["expected"] / summary["selected"]
    require((round(observed, 2), round(expected, 2)) == (75.22, 25.24), "Published rates differ")
    body = txt(20, 36, "Same pages, same counts — two answers", 28, weight="bold")
    rows = (("OBSERVED HAYRAT PAGES", observed, CRIMSON), ("RANDOM-LABEL MODEL", expected, MUTED))
    for i, (label, value, color) in enumerate(rows):
        y = 76 + i * 92
        body += txt(20, y + 22, label, 19, weight="bold")
        body += f'<rect x="20" y="{y+34}" width="800" height="30" rx="8" fill="{PALE}"/>'
        body += f'<rect x="20" y="{y+34}" width="{value*8:.0f}" height="30" rx="8" fill="{color}"/>'
        body += txt(20 + value * 8 + 18, y + 56, f"{value:.2f}%", 24, color, "bold")
    body += txt(20, 272, "Component model: 3,522 of 4,682 selected components on 587 eligible pages.", 17, MUTED)
    svg("component-comparison.svg", 920, 292, body)


def fig_page_coverage(excluded):
    require(len(excluded) == 17, "Coverage exclusions differ")
    body = txt(20, 33, "604 input pages; 587 enter this component test", 29, weight="bold")
    for page in range(1, 605):
        x, y = 20 + ((page - 1) % 40) * 17, 58 + ((page - 1) // 40) * 20
        fill = "#bd5b55" if page in excluded else "#298c7c"
        body += f'<rect x="{x}" y="{y}" width="13" height="13" rx="2" fill="{fill}"/>'
    body += (txt(740, 130, "587", 55, TEAL, "bold") + txt(740, 167, "eligible pages", 23)
             + txt(740, 242, "17", 55, "#bd5b55", "bold") + txt(740, 279, "no usable line grid", 21))
    svg("page-coverage.svg", 1100, 392, body)


def fig_phrase_breadth(review):
    values = [(n, review["lengths"][str(n)]["non_allah_aligned_distinct_types"]) for n in range(1, 7)]
    require([v for _, v in values] == [580, 396, 171, 75, 30, 13], "Phrase breadth differs")
    body = txt(20, 32, "Distinct aligned word / phrase types", 28, weight="bold")
    for i, (length, count) in enumerate(values):
        y = 60 + i * 45
        label = "One word" if length == 1 else f"{length}-word phrases"
        body += txt(20, y + 19, label, 20)
        body += f'<rect x="235" y="{y}" width="{count / 600 * 650:.0f}" height="24" rx="4" fill="#298c7c"/>'
        body += txt(245 + count / 600 * 650, y + 20, count, 20, weight="bold")
    body += txt(20, 358, "Excludes Allah-name-containing identities. Overlapping windows are not independent evidence.", 17, MUTED)
    svg("phrase-breadth.svg", 1100, 382, body)


def fig_word_facts(words):
    target = words["targets"]["standalone_allah"]
    require((target["aligned"], target["located"]) == (1717, 2151), "Standalone Allah statistic differs")
    mean = words["comparisons"]["page_row_width20"]["metrics"]["standalone_allah"]["analytic_expected_aligned"]
    actual = 100 * target["aligned"] / target["located"]
    expected = 100 * mean / target["located"]
    cards = ((f"{actual:.2f}%", "Standalone Allah aligns", "of 2,151 mapped occurrences"),
             (f"{expected:.2f}%", "Reference model mean", "page, row and rough width retained"),
             ("580", "Other aligned word types", "excluding Allah-name forms"))
    body = ""
    for i, (big, title, detail) in enumerate(cards):
        left = 10 + i * 335
        body += f'<rect x="{left}" y="0" width="315" height="145" rx="14" fill="{PALE}"/>'
        body += txt(left + 18, 57, big, 43, TEAL, "bold")
        body += txt(left + 18, 91, title, 19, weight="bold")
        body += txt(left + 18, 120, detail, 16, MUTED)
    body += txt(10, 175, "A same-word pair counts when another row of the same page lies within 15 pixels.", 17, MUTED)
    svg("word-facts.svg", 1000, 192, body)


def fig_waffles(summary):
    observed = round(100 * summary["observed"] / summary["selected"])
    expected = round(100 * summary["expected"] / summary["selected"])
    require((observed, expected) == (75, 25), "Waffle rounding differs")
    body = ""
    for p, (title, count, label, color) in enumerate((
            ("OBSERVED", observed, "about 75 in 100", CRIMSON),
            ("RANDOM-LABEL MODEL", expected, "about 25 in 100", MUTED))):
        left = 50 + p * 515
        body += txt(left, 29, title, 24, weight="bold")
        for i in range(100):
            fill = color if i < count else "#e5edeb"
            body += f'<circle cx="{left + (i % 10) * 31 + 10}" cy="{61 + (i // 10) * 25}" r="9" fill="{fill}"/>'
        body += txt(left, 330, label, 27, weight="bold")
    svg("component-waffles.svg", 1000, 352, body)


def fig_shuffle():
    panels = (("AN EXAMPLE PAGE WITH COLUMNS", {1, 7, 13, 19, 4, 10, 16, 22}),
              ("THE SAME PAGE, LABELS REASSIGNED", {0, 6, 9, 14, 17, 19, 21, 23}))
    body = ""
    for p, (title, selected) in enumerate(panels):
        left = 25 + p * 540
        body += txt(left, 30, title, 21, weight="bold")
        for i in range(24):
            x, y = left + (i % 6) * 65, 57 + (i // 6) * 42
            color = CRIMSON if i in selected else "#dce6e3"
            body += f'<rect x="{x}" y="{y}" width="46" height="16" rx="5" fill="{color}"/>'
        body += txt(left, 245, "Same sites. Same number of selected labels.", 17, MUTED)
    body += txt(495, 140, "→", 52, GOLD, "bold", anchor="middle")
    svg("shuffle-explained.svg", 1050, 268, body)


def fig_zeros():
    body = txt(40, 35, "A 1, followed by these 814 zeros", 29, weight="bold")
    for i in range(814):
        body += txt(42 + (i % 37) * 24, 77 + (i // 37) * 16, "0", 15,
                    TEAL if (i // 37) % 2 == 0 else MUTED)
    body += txt(40, 452, "Digits wrapped across 22 rows of 37. This is the denominator of the bound — not 814 trials.", 17, MUTED)
    require(22 * 37 == 814, "Zero-grid dimensions differ")
    svg("814-zeros.svg", 1000, 470, body)


def fig_proof():
    body = ""
    for i, (title, lines) in enumerate((
            ("1  COUNT", ("Work out the allowed", "selections on each page")),
            ("2  CALCULATE", ("Use exact whole numbers", "and fractions")),
            ("3  CHECK", ("Prove the probability", "stays below the bound")))):
        left = 10 + i * 340
        body += f'<rect x="{left}" y="5" width="300" height="150" rx="16" fill="{PALE}"/>'
        body += txt(left + 18, 43, title, 24, GOLD, "bold")
        for j, line in enumerate(lines):
            body += txt(left + 18, 83 + j * 28, line, 20)
        if i < 2:
            body += txt(left + 319, 91, "→", 27, GOLD, "bold", anchor="middle")
    svg("proof-in-three-steps.svg", 1030, 168, body)


def fig_log_scale():
    events = [("Five-card royal flush", math.log10(649740)),
              ("6/49 lottery: one ticket", math.log10(math.comb(49, 6))),
              ("100 fair coins: all heads", 100 * math.log10(2)),
              ("52 cards: one specified order", math.lgamma(53) / math.log(10)),
              ("1,000 fair coins: all heads", 1000 * math.log10(2)),
              ("Component model: certified bound", 814)]
    body = txt(20, 35, "A ruler of probability exponents", 30, weight="bold")
    for i, (label, value) in enumerate(events):
        y = 72 + i * 61
        body += txt(20, y + 21, label, 21)
        body += f'<rect x="450" y="{y}" width="{max(1, value / 850 * 550):.0f}" height="27" fill="{"#c33d5f" if i == 5 else "#91a5a7"}"/>'
        body += txt(458 + value / 850 * 550, y + 22, ">814" if i == 5 else f"{value:.2f}", 20)
    body += '<line x1="450" y1="451" x2="1000" y2="451" stroke="#576c70"/>'
    for tick in (0, 100, 200, 400, 600, 800):
        x = 450 + tick / 850 * 550
        body += f'<line x1="{x:.0f}" y1="451" x2="{x:.0f}" y2="459" stroke="#576c70"/>'
        body += txt(x - 7, 484, tick, 17)
    body += txt(450, 517, "−log10(probability): each +1 means ten times less likely", 18)
    body += txt(20, 557, "The last bar is a conditional bound, not an authorship probability or a combined test.", 18, MUTED)
    svg("log-probability-scale.svg", 1100, 578, body)


# --------------------------------------------------------------- scan excerpts

def scan_page_detail(words):
    """Hayrat page 2 with the two standalone Allah occurrences outlined."""
    from image_io import open_rgb
    from same_word_alignment import canonical_inventory
    canonical, _ = canonical_inventory()
    located = {row[0]: row for row in words["located_inventory"]}
    for token, x2, width in ((77, 1180, 80), (100, 1176, 72)):
        row = located[token]
        require(row[1] == 2 and row[3:] == [x2, width], "Cover word coordinates differ")
        require(canonical[token]["word"] == "الله", "Cover words are not standalone Allah")
    require((canonical[77]["verse"], canonical[100]["verse"]) == ("2:7", "2:9"), "Cover verses differ")
    pairs = {tuple(sorted(p)) for p in words["same_word_pair_token_ids"]}
    require((77, 100) in pairs, "Cover pair absent from the measured ledger")
    path = ROOT / "hayrat-pics/page_2.png"
    image = open_rgb(path).copy()
    draw = ImageDraw.Draw(image)
    for y in range(135, 567, 14):
        draw.line((589, y, 589, min(y + 7, 567)), fill=TEAL, width=2)
    for box in ((550, 146, 630, 220), (552, 476, 624, 550)):
        left, top, right, bottom = box
        draw.rounded_rectangle((left - 5, top - 5, right + 5, bottom + 5), radius=6, outline=TEAL, width=4)
    font = ImageFont.load_default(size=25)
    sheet = Image.new("RGB", (1400, 1080), "white")
    draw = ImageDraw.Draw(sheet)
    draw.text((10, 7), "FULL HAYRAT PAGE 2", font=font, fill=INK)
    full = image.resize((610, round(image.height * 610 / image.width)))
    sheet.paste(full, (5, 55))
    draw.text((660, 7), "DETAIL: THE SAME NAME", font=font, fill=INK)
    crop = image.crop((385, 115, 845, 580))
    crop = crop.resize((700, round(crop.height * 700 / crop.width)))
    sheet.paste(crop, (660, 135))
    draw.text((660, 900), "Allah at 2:7 / 2:9", font=font, fill=TEAL)
    draw.text((660, 944), "Original horizontal positions retained", font=font, fill=MUTED)
    sheet.save(FIGS / "hayrat-page-and-detail.png")
    return dict(source=f"hayrat-pics/{path.name}", source_sha256=digest(path),
                token_ids=[77, 100], boxes=[[550, 146, 630, 220], [552, 476, 624, 550]],
                center_difference_pixels=abs(1180 - 1176) / 2,
                transforms="Full page and detail resized uniformly; green guide and outlines added; no word moved.")


def scan_spread():
    """Hayrat pages 62 and 63 with every mapped Allah-family occurrence outlined."""
    from image_io import open_rgb
    from semantic_validation import is_name
    import broad_phrase_alignment as bp
    canonical, words_all, mapping, views, _, _ = bp.load()
    measured = views["views"]["conservative_v5"]
    hashes = {p["page"]: p["image_sha256"] for p in mapping["pages"]}
    saved_ends = {t for pair in measured["family_pair_token_ids"] for t in pair}
    font = ImageFont.load_default(size=33)
    provenance, source_rows, page_counts = [], {}, {}
    for page in (62, 63):
        rows = [dict(w, verse=canonical[w["t"]]["verse"]) for w in words_all
                if w["page"] == page and is_name(canonical[w["t"]]["form"])]
        ends = {r["t"] for r in rows for s in rows
                if r["row"] != s["row"] and abs(r["x2"] - s["x2"]) <= 30}
        require(ends == {r["t"] for r in rows if r["t"] in saved_ends}, "Illustration flags differ from ledger")
        source_rows[page] = rows
        page_counts[str(page)] = dict(mapped_family=len(rows), aligned_family=len(ends))
        path = ROOT / f"hayrat-pics/page_{page}.png"
        require(digest(path) == hashes[page], "Spread image hash differs")
        image = open_rgb(path)
        draw = ImageDraw.Draw(image)
        remaining = {r["t"] for r in rows if r["t"] in ends}
        by_id = {r["t"]: r for r in rows}
        while remaining:
            group = {min(remaining)}
            while True:
                more = {t for t in remaining if any(by_id[t]["row"] != by_id[s]["row"]
                        and abs(by_id[t]["x2"] - by_id[s]["x2"]) <= 30 for s in group)}
                if more <= group:
                    break
                group |= more
            remaining -= group
            cx = round(sum(by_id[t]["x2"] / 2 for t in group) / len(group))
            y0 = max(0, min(by_id[t]["bbox"][1] for t in group) - 6)
            y1 = min(image.height, max(by_id[t]["bbox"][3] for t in group) + 6)
            for y in range(y0, y1, 18):
                draw.line((cx, y, cx, min(y + 8, y1)), fill="#7faed0", width=2)
        for row in rows:
            x0, y0, x1, y1 = row["bbox"]
            outline = "#246eb1" if row["t"] in ends else "#8b9599"
            draw.rectangle((max(0, x0 - 4), max(0, y0 - 4),
                            min(image.width - 1, x1 + 4), min(image.height - 1, y1 + 4)),
                           outline=outline, width=3)
        annotated = REVIEW / f"page-{page}-annotated.png"
        image.save(annotated)
        provenance.append(dict(page=page, source=f"hayrat-pics/{path.name}", source_sha256=digest(path),
                               occurrences=[dict(verse=r["verse"], word=r["word"], bbox=r["bbox"],
                                                 row=r["row"], aligned=r["t"] in ends) for r in rows]))
    right = source_rows[63]
    lower = next(r for r in right if r["verse"] == "3:114" and r["word"] == "بالله")
    partner = next(r for r in right if r["verse"] == "3:110" and r["word"] == "بالله")
    bottom = next(r for r in right if r["verse"] == "3:115" and r["word"] == "والله")
    require(abs(lower["x2"] - partner["x2"]) / 2 == 10.5 and lower["t"] in saved_ends, "Lower reference word differs")
    require(bottom["t"] not in saved_ends, "Bottom nonmatch status differs")
    images = [Image.open(REVIEW / f"page-{p}-annotated.png") for p in (62, 63)]
    out = Image.new("RGB", (images[0].width + images[1].width + 34,
                            max(i.height for i in images) + 58), "white")
    draw = ImageDraw.Draw(out)
    for i, (label, image) in enumerate((("Hayrat page 62", images[0]), ("Hayrat page 63", images[1]))):
        draw.text((10 + i * (images[0].width + 34), 6), label, fill=INK, font=font)
        out.paste(image, (i * (images[0].width + 34), 58))
    out.save(FIGS / "hayrat-spread-62-63.png")
    return dict(sources=provenance, page_counts=page_counts,
                lower_billah=dict(verses=["3:110", "3:114"], distance_pixels=10.5))


def scan_ordinary_pairs(review):
    """Two everyday corresponding-word examples from the checked inventory."""
    from image_io import open_rgb
    font = ImageFont.load_default(size=33)
    panels, provenance = [], []
    for page, label in ((1, "GUIDANCE"), (2, "THEIR HEARTS")):
        example = next(e for e in review["lengths"]["1"]["examples"] if e["page"] == page)
        require(example["status"] == "strict_pair", f"Page {page} example is not a strict pair")
        path = ROOT / f"hayrat-pics/page_{page}.png"
        require(digest(path) == example["image_sha256"], "Ordinary word source differs")
        image = open_rgb(path)
        boxes = [b for o in example["occurrences"] for b in o["boxes"]]
        left = max(0, min(b[0] for b in boxes) - 85)
        right = min(image.width, max(b[2] for b in boxes) + 85)
        scale = 900 / (right - left)
        parts = []
        for o in example["occurrences"]:
            top = max(0, min(b[1] for b in o["boxes"]) - 12)
            bottom = min(image.height, max(b[3] for b in o["boxes"]) + 12)
            crop = image.crop((left, top, right, bottom)).resize((900, round((bottom - top) * scale)))
            panel = Image.new("RGB", (900, crop.height + 50), "white")
            panel.paste(crop, (0, 50))
            draw = ImageDraw.Draw(panel)
            words_text = " ".join(example["words"])
            draw.text((8, 5), f"{label} / {words_text} / {o['verse']}", font=font, fill=INK)
            for box in o["boxes"]:
                draw.rectangle(((box[0] - left) * scale, (box[1] - top) * scale + 50,
                                (box[2] - left) * scale, (box[3] - top) * scale + 50),
                               outline="#246eb1", width=3)
            parts.append(panel)
        joined = Image.new("RGB", (900, sum(p.height for p in parts) + 20), "white")
        y = 0
        for panel in parts:
            joined.paste(panel, (0, y))
            y += panel.height + 20
        panels.append(joined)
        provenance.append(dict(page=page, source=f"hayrat-pics/{path.name}", source_sha256=digest(path),
                               words=example["words"], verses=[o["verse"] for o in example["occurrences"]],
                               center_differences_pixels=example["corresponding_center_differences_pixels"]))
    require(provenance[0]["center_differences_pixels"] == [3.5], "Guidance caption differs")
    require(provenance[1]["center_differences_pixels"] == [2.5], "Hearts caption differs")
    sheet = Image.new("RGB", (1840, max(p.height for p in panels)), "white")
    for i, panel in enumerate(panels):
        sheet.paste(panel, (i * 940, 0))
    sheet.save(FIGS / "ordinary-word-pairs.png")
    return provenance


def scan_phrase_example(review, length, page, filename, max_diff):
    example = next(e for e in review["lengths"][length]["examples"]
                   if e["page"] == page and e["status"] == "strict_pair")
    require(len(example["occurrences"]) == 2, "Expected a phrase pair")
    diffs = example["corresponding_center_differences_pixels"]
    require(max(diffs) == max_diff, f"Phrase caption differs on page {page}")
    from image_io import open_rgb
    font = ImageFont.load_default(size=25)
    path = ROOT / f"hayrat-pics/page_{page}.png"
    require(digest(path) == example["image_sha256"], "Phrase scan hash differs")
    image = open_rgb(path)
    boxes = [b for o in example["occurrences"] for b in o["boxes"]]
    left = max(0, min(b[0] for b in boxes) - 18)
    right = min(image.width, max(b[2] for b in boxes) + 18)
    scale = 1200 / (right - left)
    panels, crops = [], []
    for occurrence in example["occurrences"]:
        top = max(0, min(b[1] for b in occurrence["boxes"]) - 12)
        bottom = min(image.height, max(b[3] for b in occurrence["boxes"]) + 12)
        crop = image.crop((left, top, right, bottom))
        crop = crop.resize((1200, round(crop.height * scale)))
        panel = Image.new("RGB", (1200, crop.height + 38), "white")
        panel.paste(crop, (0, 38))
        draw = ImageDraw.Draw(panel)
        draw.text((9, 4), f"Hayrat p{page} / {occurrence['verse']}", font=font, fill=INK)
        for b in occurrence["boxes"]:
            draw.rectangle(((b[0] - left) * scale, (b[1] - top) * scale + 38,
                            (b[2] - left) * scale, (b[3] - top) * scale + 38), outline="#297bad", width=2)
        panels.append(panel)
        crops.append([left, top, right, bottom])
    sheet = Image.new("RGB", (1200, sum(p.height for p in panels) + 16), "white")
    draw = ImageDraw.Draw(sheet)
    y = 0
    for panel in panels:
        sheet.paste(panel, (0, y))
        y += panel.height + 16
    for x2 in example["occurrences"][0]["twice_centers"]:
        x = round((x2 / 2 - left) * scale)
        for y in range(38, sheet.height, 16):
            draw.line((x, y, x, min(y + 6, sheet.height)), fill="#80bad2", width=1)
    sheet.save(FIGS / filename)
    return dict(page=page, source=f"hayrat-pics/{path.name}", source_sha256=digest(path),
                words=example["words"], verses=[o["verse"] for o in example["occurrences"]],
                center_differences_pixels=diffs, crops=crops)


def check_historical_figure():
    manifest = read_json(FINDINGS_FIGS / "sources.json")
    entry = next(f for f in manifest["figures"] if f["output"] == "historical-1779.png")
    require(digest(FINDINGS_FIGS / "historical-1779.png") == entry["output_sha256"], "Historical asset differs")
    return entry


# ---------------------------------------------------------------------- export

CSS = """
@page {size:A4;margin:15mm 17mm 16mm;
 @bottom-left {content:'TAWAFUQ / V4 / PRIVATE WORKING DRAFT';font:7pt 'DejaVu Sans';color:#66817d}
 @bottom-right {content:counter(page) ' / ' counter(pages);font:8pt 'DejaVu Sans';color:#66817d}}
* {box-sizing:border-box}
body {margin:0;background:#f2efe9;color:#233b3b;font:16px/1.5 'DejaVu Sans',sans-serif}
.sheet {max-width:900px;margin:24px auto;padding:42px 56px;background:white}
.eyebrow {color:#14544b;text-transform:uppercase;letter-spacing:1.6px;font-size:10px;margin-bottom:14px}
h1,h2,h3 {line-height:1.16;break-after:avoid;color:#14544b}
h1 {font-size:40px;letter-spacing:-1.2px;margin:0 0 15px}
h2 {font-size:28px;letter-spacing:-.7px;margin:0 0 16px}
h3 {font-size:19px;margin:17px 0 9px}
p {margin:10px 0;orphans:3;widows:3} strong {font-weight:700}
img {display:block;width:100%;height:auto} p:has(>img) {break-inside:avoid;margin:14px 0}
img[src$="hayrat-page-and-detail.png"] {width:88%;margin:auto}
img[src$="word-phrase.png"] {width:82%;margin:auto}
img[src$="component-comparison.svg"] {width:72%;margin:auto}
img[src$="814-zeros.svg"] {width:54%;margin:auto}
img[src$="log-probability-scale.svg"] {width:62%;margin:auto}
img[src$="proof-in-three-steps.svg"] {width:70%;margin:auto}
img[src$="page-coverage.svg"] {width:92%;margin:auto}
blockquote {background:#edf4f1;border-left:4px solid #b48842;padding:12px 17px;margin:16px 0;break-inside:avoid;font-size:18px}
blockquote p {margin:3px 0} a {color:#14544b;text-decoration:none}
[lang=ar] {font-family:'DejaVu Sans',sans-serif;unicode-bidi:isolate}
code {font-size:.86em;font-family:'DejaVu Sans Mono';overflow-wrap:anywhere}
pre {white-space:pre-wrap;padding:10px;background:#edf4f1;font-size:11px;line-height:1.4;break-inside:avoid}
table {width:100%;border-collapse:collapse;margin:13px 0;font-size:12px;break-inside:avoid}
td,th {padding:7px 6px;border-bottom:1px solid #d7e4dd;text-align:left;vertical-align:top}
th {background:#e9f1ec}
ul,ol {padding-left:22px} li {margin:5px 0}
@media print {
 body {background:white;font-size:9.8pt;line-height:1.43}
 .sheet {margin:0;padding:0;max-width:none;break-after:page}.sheet:last-child {break-after:auto}
 .eyebrow {font-size:7.2pt;margin-bottom:11px}
 h1 {font-size:27pt} h2 {font-size:19pt;margin-bottom:14px} h3 {font-size:11.7pt;margin:12px 0 7px}
 p {margin:8px 0} blockquote {font-size:11pt;padding:9px 13px;margin:11px 0}
 pre {font-size:7.6pt;line-height:1.35} table {font-size:8pt} td,th {padding:6px 5px}
}
"""


class Fragment(HTMLParser):
    """Minimal HTML tree for exporting one Markdown page to editable ODT."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = dict(tag="root", attrs={}, children=[])
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = dict(tag=tag, attrs=dict(attrs), children=[])
        self.stack[-1]["children"].append(node)
        if tag not in ("img", "br", "hr", "meta", "link", "input"):
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if self.stack[-1]["tag"] == tag:
            self.stack.pop()

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i]["tag"] == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        self.stack[-1]["children"].append(data)


def node_text(node):
    return node if isinstance(node, str) else "".join(node_text(c) for c in node["children"])


def export_odt(parts, destination):
    from odf.opendocument import OpenDocumentText, load
    from odf import dc, draw, style, table, teletype
    from odf import text as otext
    import pymupdf
    document = OpenDocumentText()
    document.meta.addElement(dc.Title(text="The Words That Line Up — Tawafuq V4"))
    document.meta.addElement(dc.Creator(text="Emin Temiz; AI-assisted draft"))
    layout = style.PageLayout(name="A4Layout")
    layout.addElement(style.PageLayoutProperties(
        pagewidth="21cm", pageheight="29.7cm", margintop="1.6cm", marginbottom="1.6cm",
        marginleft="1.7cm", marginright="1.7cm"))
    document.automaticstyles.addElement(layout)
    document.masterstyles.addElement(style.MasterPage(name="Standard", pagelayoutname=layout))
    specifications = {"Body": ("10pt", False, None), "Title": ("27pt", True, None),
                      "Heading": ("19pt", True, None), "NewPage": ("19pt", True, "page"),
                      "Subhead": ("12pt", True, None), "Quote": ("10pt", False, None),
                      "Code": ("8pt", False, None), "Bullet": ("10pt", False, None),
                      "Image": ("9pt", False, None)}
    for name, (size, bold, break_before) in specifications.items():
        s = style.Style(name=name, family="paragraph")
        props = dict(marginbottom="0.18cm", lineheight="135%")
        if name in ("Title", "Heading", "NewPage", "Subhead"):
            props["keepwithnext"] = "always"
        if break_before:
            props["breakbefore"] = break_before
        if name == "Image":
            props["textalign"] = "center"
        if name == "Bullet":
            props["marginleft"] = "0.35cm"
        s.addElement(style.ParagraphProperties(**props))
        s.addElement(style.TextProperties(
            fontsize=size, fontweight="bold" if bold else "normal",
            fontfamily="DejaVu Sans Mono" if name == "Code" else "DejaVu Sans"))
        document.styles.addElement(s)
    for name, properties in (("Bold", dict(fontweight="bold")),
                             ("Italic", dict(fontstyle="italic")),
                             ("InlineCode", dict(fontfamily="DejaVu Sans Mono", fontsize="8.5pt"))):
        s = style.Style(name=name, family="text")
        s.addElement(style.TextProperties(**properties))
        document.styles.addElement(s)
    image_count = 0

    def add_image(parent, node):
        nonlocal image_count
        path = (ARTICLE / node["attrs"]["src"]).resolve()
        require(path.is_relative_to(ARTICLE) and path.is_file(), "Invalid ODT image")
        if path.suffix == ".svg":
            png = REVIEW / (path.stem + "-odt.png")
            with pymupdf.open(path) as svg_document:
                svg_document[0].get_pixmap(matrix=pymupdf.Matrix(1.6, 1.6), alpha=False).save(png)
            path = png
        with Image.open(path) as im:
            width, height = im.size
        physical = 15.6 if "word-phrase" in path.name else 17.3
        frame = draw.Frame(name=f"Figure{image_count}", anchortype="as-char",
                           width=f"{physical}cm", height=f"{physical * height / width:.4f}cm")
        frame.addElement(draw.Image(href=document.addPicture(str(path)), type="simple",
                                    show="embed", actuate="onLoad"))
        parent.addElement(frame)
        image_count += 1

    def inline(parent, node):
        if isinstance(node, str):
            teletype.addTextToElement(parent, node)
            return
        tag = node["tag"]
        if tag == "img":
            add_image(parent, node)
            return
        if tag == "br":
            parent.addElement(otext.LineBreak())
            return
        if tag == "a":
            child = otext.A(href=node["attrs"].get("href", ""))
        elif tag in ("strong", "b", "em", "i", "code"):
            child = otext.Span(
                stylename="Bold" if tag in ("strong", "b") else "Italic" if tag in ("em", "i") else "InlineCode")
        else:
            child = otext.Span()
        for item in node["children"]:
            inline(child, item)
        parent.addElement(child)

    table_count = 0

    def blocks(parent, node, first=False):
        nonlocal table_count
        if isinstance(node, str):
            if node.strip():
                parent.addElement(otext.P(stylename="Body", text=node))
            return
        tag = node["tag"]
        if tag in ("h1", "h2", "h3", "h4"):
            name = "Title" if tag == "h1" else "NewPage" if first else "Heading" if tag == "h2" else "Subhead"
            p = otext.H(outlinelevel=int(tag[1]), stylename=name)
            for item in node["children"]:
                inline(p, item)
            parent.addElement(p)
        elif tag in ("p", "li"):
            is_image = any(isinstance(c, dict) and c["tag"] == "img" for c in node["children"])
            p = otext.P(stylename="Image" if is_image else "Bullet" if tag == "li" else "Body")
            if tag == "li":
                teletype.addTextToElement(p, "• ")
            for item in node["children"]:
                inline(p, item)
            parent.addElement(p)
        elif tag == "pre":
            for line in node_text(node).splitlines():
                p = otext.P(stylename="Code")
                teletype.addTextToElement(p, line)
                parent.addElement(p)
        elif tag == "table":
            out = table.Table(name=f"Table{table_count}")
            table_count += 1

            def rows(n):
                return [n] if isinstance(n, dict) and n["tag"] == "tr" else [
                    r for c in n.get("children", []) if isinstance(c, dict) for r in rows(c)]
            for row in rows(node):
                r = table.TableRow()
                for cell in row["children"]:
                    if not isinstance(cell, dict) or cell["tag"] not in ("td", "th"):
                        continue
                    c = table.TableCell(valuetype="string")
                    p = otext.P(stylename="Body")
                    for item in cell["children"]:
                        inline(p, item)
                    c.addElement(p)
                    r.addElement(c)
                out.addElement(r)
            parent.addElement(out)
        elif tag == "blockquote":
            for c in node["children"]:
                if isinstance(c, dict) and c["tag"] == "p":
                    p = otext.P(stylename="Quote")
                    for item in c["children"]:
                        inline(p, item)
                    parent.addElement(p)
        else:
            for child in node["children"]:
                blocks(parent, child)
    for part in parts:
        fragment = Fragment()
        fragment.feed(part)
        first = True
        for node in fragment.root["children"]:
            if isinstance(node, str) and not node.strip():
                continue
            blocks(document.text, node, first=first)
            first = False
    document.save(str(destination), addsuffix=False)
    load(str(destination))
    with zipfile.ZipFile(destination) as archive:
        require(archive.read("mimetype") == b"application/vnd.oasis.opendocument.text", "Invalid ODT mimetype")
        root = ET.fromstring(archive.read("content.xml"))
        recovered = " ".join(" ".join(root.itertext()).split())
        for phrase in ("10⁻⁸¹⁴", "10⁻⁵⁷", "Emin Temiz", "Türkçe özet", "3,522", "36.96%", "بِسْمِ اللَّهِ"):
            require(phrase in recovered, f"Missing ODT content: {phrase}")
        for image in root.findall(".//draw:image", NS):
            require(image.get(f'{{{NS["xlink"]}}}href') in archive.namelist(), "ODT image not embedded")
        expected = []
        for part in parts:
            fragment = Fragment()
            fragment.feed(part)
            expected.append(node_text(fragment.root))
        canonical = lambda value: re.sub(r"\s+", "", value).replace("•", "")
        require(canonical("".join(expected)) == canonical(recovered), "ODT export lost or altered article text")
        page_headings = [h for h in root.findall(".//text:h", NS)
                         if h.get(f'{{{NS["text"]}}}style-name') == "NewPage"]
        require(len(page_headings) == len(parts) - 1, "ODT page-break structure differs")
    return dict(embedded_images=image_count, structure_checked=True,
                full_text_roundtrip_checked=True, visual_office_render_checked=False)


def export_ods(summary, words, review, structure, historical, extension, examples, destination):
    """Emit the V4 data workbook and verify it by reloading and spot-checking cells."""
    from odf.opendocument import OpenDocumentSpreadsheet, load
    from odf.table import Table, TableColumn, TableRow, TableCell
    from odf.text import P as TextP
    from odf.style import Style, TableCellProperties, TextProperties

    document = OpenDocumentSpreadsheet()
    for name, size, bold, back in (("Header", "10pt", True, "#e9f1ec"), ("Cell", "10pt", False, None)):
        s = Style(name=name, family="table-cell")
        props = {}
        if back:
            props["backgroundcolor"] = back
        if props:
            s.addElement(TableCellProperties(**props))
        s.addElement(TextProperties(fontsize=size, fontweight="bold" if bold else "normal",
                                     fontfamily="DejaVu Sans"))
        document.styles.addElement(s)

    sheets = {}

    def sheet(name, header, rows):
        table = Table(name=name)
        table.addElement(TableColumn(numbercolumnsrepeated=str(len(header))))
        header_row = TableRow()
        for value in header:
            cell = TableCell(valuetype="string")
            cell.addElement(TextP(stylename="Header", text=str(value)))
            header_row.addElement(cell)
        table.addElement(header_row)
        for row in rows:
            r = TableRow()
            for value in row:
                if isinstance(value, bool):
                    cell = TableCell(valuetype="boolean", value="true" if value else "false")
                    cell.addElement(TextP(stylename="Cell", text=str(value)))
                elif isinstance(value, (int, float)) and not isinstance(value, bool):
                    cell = TableCell(valuetype="float", value=f"{value}")
                    cell.addElement(TextP(stylename="Cell", text=str(value)))
                else:
                    cell = TableCell(valuetype="string")
                    cell.addElement(TextP(stylename="Cell", text=str(value)))
                r.addElement(cell)
            table.addElement(r)
        document.spreadsheet.addElement(table)
        sheets[name] = dict(header=header, rows=rows)

    target = words["targets"]
    sa = target["standalone_allah"]
    metrics = words["comparisons"]["page_row_width20"]["metrics"]["standalone_allah"]
    hoeffding = -metrics["column_hoeffding_log10_upper_bound"]
    require(hoeffding > 57, "Word bound differs")

    sheet("Component certificate", ["quantity", "value"],
          [["input pages", 604], ["eligible pages", summary["pages"]],
           ["excluded pages (no usable line grid)", 604 - summary["pages"]],
           ["eligible component sites", summary["sites"]],
           ["selected red-class components", summary["selected"]],
           ["observed aligned components (T)", summary["observed"]],
           ["observed rate (%)", round(100 * summary["observed"] / summary["selected"], 2)],
           ["expected mean aligned", round(summary["expected"], 6)],
           ["expected rate (%)", round(100 * summary["expected"] / summary["selected"], 2)],
           ["model", "uniform per-page component labeling"],
           ["certified bound", "P(T >= 3522) < 10^-814"],
           ["proof arithmetic", "integer/rational; replayed by builder"]])

    word_rows = [["target", "word", "expected tokens", "located", "aligned", "aligned % of located"]]
    for key, word in (("standalone_allah", sa["word"]), ("alrahman", target["alrahman"]["word"]),
                      ("alrahim", target["alrahim"]["word"]),
                      ("allah_name_family", target["allah_name_family"].get("word", "(name family)")),
                      ("all_identical_words", "(every identical word)")):
        t = target[key]
        word_rows.append([key, word, t["canonical_expected"], t["located"], t["aligned"],
                          round(100 * t["aligned"] / t["located"], 2)])
    word_rows += [["model", "page/row/20px-width identity exchange", "", "", "", ""],
                  ["model mean aligned (standalone Allah)", "", "", "", round(metrics["analytic_expected_aligned"], 4), ""],
                  ["model mean rate (%)", "", "", "", "", round(100 * metrics["analytic_expected_aligned"] / sa["located"], 2)],
                  ["conditional bound", "P(T >= 1717) < 10^-57", "", "", "", ""]]
    sheet("Word study", ["quantity"] + ["word", "expected", "located", "aligned", "aligned %"], word_rows[1:])

    breadth_rows = [[n, review["lengths"][str(n)]["non_allah_aligned_distinct_types"],
                     "distinct aligned types excluding Allah-name identities"] for n in range(1, 7)]
    sheet("Phrase breadth", ["phrase length (words)", "distinct aligned types", "scope"], breadth_rows)

    blocks = structure["models"]["repeated_phrase_blocks"]
    structure_rows = []
    for n in range(1, 7):
        entry = blocks["lengths"][str(n)]
        inference = entry["inference"]
        structure_rows.append([n, entry["observed"]["without_allah_forms"],
                               round(inference["null_mean"], 4), inference["exceedances"],
                               inference["reps"], bool(entry["exact_score_invariance_certified"]["without_allah_forms"])])
    sheet("Structure controls", ["length", "observed (without Allah forms)", "phrase-block null mean",
                                 "trials reaching observed", "trials", "exact score invariance"], structure_rows)

    example_rows = [["Allah at 2:7 / 2:9 (Hayrat p2)", 2.0],
                    ["Guidance at 2:2 / 2:5 (Hayrat p1)", examples["guidance"]],
                    ["Their hearts at 2:7 / 2:10 (Hayrat p2)", examples["hearts"]],
                    ["Bills at 3:110 / 3:114 (Hayrat p63)", 10.5],
                    ["Five-word phrase 2:40 / 2:47 (Hayrat p6), max", examples["five"]],
                    ["Six-word phrase 34:36 / 34:39 (Hayrat p431), max", examples["six"]]]
    sheet("Measured examples", ["example", "corresponding center difference (pixels)"], example_rows)

    first = historical["scores"]["0.02"]["allah_name_family"]["historical"]
    second = extension["scores"]["0.02"]["allah_name_family"]["historical"]
    require((first["midpoint_aligned"], first["occurrences"]) == (10, 33), "1779 score differs")
    require((second["midpoint_aligned"], second["occurrences"]) == (34, 66), "1776 score differs")
    sheet("Historical copies", ["manuscript", "catalogued", "tolerance", "family midpoint aligned", "family occurrences"],
          [["Columbia MS Or 422", 1779, "2% of text-frame width", 10, 33],
           ["Columbia MS Or 91", 1776, "2% of text-frame width", 34, 66],
           ["caveat", "", "assumed coordinate allowances; single-reader inspection; unverified provenance", "", ""]])

    document.save(str(destination), addsuffix=False)
    loaded = load(str(destination))
    TABLE_NS = "urn:oasis:names:tc:opendocument:xmlns:table:1.0"
    with zipfile.ZipFile(destination) as archive:
        require(archive.read("mimetype") == b"application/vnd.oasis.opendocument.spreadsheet",
                "Invalid ODS mimetype")
        root = ET.fromstring(archive.read("content.xml"))
        names = [t.get(f"{{{TABLE_NS}}}name")
                 for t in root.findall(f".//{{{TABLE_NS}}}table")]
        require(len(names) == len(sheets), "ODS sheet count differs")
        texts = " ".join(" ".join(root.itertext()).split())
        for phrase in ("3522", "10^-814", "1717", "36.96", "580"):
            require(phrase in texts, f"Missing ODS content: {phrase}")
    return dict(sheets=len(sheets), sheet_names=list(sheets), tables_reloaded=len(loaded.spreadsheet.childNodes))


# ----------------------------------------------------------------------- build

class ArticleLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images, self.links = [], []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "img":
            self.images.append(values["src"])
        if tag == "a":
            self.links.append(values.get("href", ""))


def build():
    import pymupdf
    from weasyprint import HTML
    FIGS.mkdir(parents=True, exist_ok=True)
    REVIEW.mkdir(parents=True, exist_ok=True)
    source = SOURCE.read_text()
    parts = source.split("<!-- page -->")
    require(len(parts) == 21, f"V4 should contain 21 designed pages, found {len(parts)}")
    component_inputs, summary = check_component_bound(source)
    words = read_json(DATA / "research_same_word_alignment_v1.json")["views"]["conservative_v5"]
    review = read_json(DATA / "research_broad_phrase_review_v1.json")
    structure = read_json(DATA / "research_phrase_structure_review_v1.json")
    historical = read_json(DATA / "research_historical_center_review_v1.json")
    extension = read_json(DATA / "research_historical_extension_review_v3.json")
    exp_lower = sum((Fraction(2303, 1000) ** j / Fraction(math.factorial(j))) for j in range(31))
    require(exp_lower > 10, "Rational ln(10) certificate fails")
    require(Fraction(2 * 921 ** 2, 12895) > 57 * Fraction(2303, 1000), "Word-bound decimal exponent check fails")

    fig_component_comparison(summary)
    exact = read_json(DATA / "audit_exact_columns_raw_wordlike.json")
    fig_page_coverage(set(map(int, exact["preprocessing_details"]["excluded_pages"])))
    fig_phrase_breadth(review)
    fig_word_facts(words)
    fig_waffles(summary)
    fig_shuffle(); fig_zeros(); fig_proof(); fig_log_scale()
    infographics = sorted(p.name for p in FIGS.glob("*.svg"))

    ordinary = scan_ordinary_pairs(review)
    examples = dict(two=scan_page_detail(words)["center_difference_pixels"],
                    guidance=ordinary[0]["center_differences_pixels"][0],
                    hearts=ordinary[1]["center_differences_pixels"][0],
                    five=max(scan_phrase_example(review, "5", 6, "hayrat-five-word-phrase.png", 4)
                             ["center_differences_pixels"]),
                    six=max(scan_phrase_example(review, "6", 431, "hayrat-six-word-phrase.png", 4.5)
                            ["center_differences_pixels"]))
    spread = scan_spread()
    historical_entry = check_historical_figure()

    for phrase in ("10⁻⁸¹⁴", "10⁻⁵⁷", "75.22%", "25.24%", "79.82%", "36.96%", "3,522", "4,682",
                   "76,375", "1,717", "2,151", "580", "10.5 pixels", "Türkçe özet", "34 of 66"):
        require(phrase in source, f"Principal claim absent from V4: {phrase}")
    rendered = [markdown.markdown(part, extensions=["tables", "fenced_code"]) for part in parts]
    sections = []
    for i, content in enumerate(rendered, 1):
        sections.append(f'<section class="sheet"><div class="eyebrow">V4 · 19 October 2026 · {i:02d}</div>{content}</section>')
    document = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1">'
                '<meta name="author" content="Emin Temiz; AI-assisted draft">'
                '<title>The Words That Line Up — Tawafuq V4</title>'
                f'<style>{CSS}</style></head><body>' + "\n".join(sections) + '</body></html>')
    links = ArticleLinks()
    links.feed(document)
    for src in links.images:
        require((ARTICLE / src).is_file(), f"Broken illustration link: {src}")
    html_path = REVIEW / f"{STEM}.html"
    pdf_path = ARTICLE / f"{STEM}.pdf"
    odt_path = ARTICLE / f"{STEM}.odt"
    ods_path = ARTICLE / f"{STEM}.ods"
    html_path.write_text(document)
    HTML(filename=str(html_path), base_url=ARTICLE.as_uri() + "/").write_pdf(pdf_path)
    with pymupdf.open(pdf_path) as pdf:
        require(len(pdf) == 21, f"Expected 21 PDF pages, got {len(pdf)}; inspect overflow")
        extracted = " ".join(" ".join(page.get_text() for page in pdf).split())
        for phrase in ("10⁻⁸¹⁴", "10⁻⁵⁷", "75.22%", "79.82%", "36.96%", "Türkçe özet", "Conclusion for AI consumption"):
            require(phrase in extracted, f"Missing PDF content: {phrase}")
        require("\ufffd" not in extracted, "Replacement character in PDF")
        thumbs = []
        for i, page in enumerate(pdf, 1):
            for block in page.get_text("dict")["blocks"]:
                require(page.rect.contains(pymupdf.Rect(block["bbox"])), f"Clipped PDF content on page {i}")
            path = REVIEW / f"page-{i:02d}.png"
            page.get_pixmap(dpi=110).save(path)
            with Image.open(path) as raw:
                thumb = raw.copy()
            thumb.thumbnail((330, 470))
            thumbs.append(thumb)
        sheet = Image.new("RGB", (4 * 350, math.ceil(len(thumbs) / 4) * 495), "#e3e9e2")
        for i, thumb in enumerate(thumbs):
            sheet.paste(thumb, (10 + (i % 4) * 350, 10 + (i // 4) * 495))
        sheet.save(REVIEW / "contact-sheet.png")
    odt_report = export_odt(rendered, odt_path)
    ods_report = export_ods(summary, words, review, structure, historical, extension, examples, ods_path)
    manifest = dict(source_sha256=digest(SOURCE), builder_sha256=digest(Path(__file__)),
                     evidence_inputs={**component_inputs},
                     component_certificate=summary,
                     figure_sources=dict(spread=spread, examples=examples, historical=historical_entry),
                     assets={src: digest(ARTICLE / src) for src in links.images},
                     pdf_sha256=digest(pdf_path), odt_sha256=digest(odt_path), ods_sha256=digest(ods_path),
                     pdf_pages=21, infographics=infographics, odt=odt_report, ods=ods_report,
                     word_decimal_arithmetic_checks=True,
                     rights="Private working draft with Hayrat scan excerpts and project overlays; source-image rights are separate.")
    (REVIEW / "build-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(f"Built {pdf_path.relative_to(ROOT)}: 21 pages, {len(infographics)} infographics")
    print(f"Built {odt_path.relative_to(ROOT)}: {odt_report['embedded_images']} embedded figures")
    print(f"Built {ods_path.relative_to(ROOT)}: {ods_report['sheets']} data sheets")
    print(f"Review: {(REVIEW / 'contact-sheet.png').relative_to(ROOT)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    build()