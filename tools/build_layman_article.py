"""Build the five-page, infographic-led private layman edition.

Run in .venv: python tools/build_layman_article.py
Initial generation or --refresh-scans needs hash-matched local Hayrat scans.
Subsequent builds verify and reuse the derived private-draft scan assets.
The technical article and frozen scientific inputs are never overwritten.
"""

import argparse
from html import escape
import json
import math
from pathlib import Path

import markdown
from PIL import Image, ImageDraw, ImageFont
import pymupdf
from weasyprint import HTML

from build_findings_article import (
    ARTICLE, DATA, ROOT, Resources, check_component_bound, digest, read_json, require,
)
from image_io import open_rgb

STEM = "tawafuq-layman-v2-2026-10-19"
SOURCE = ARTICLE / f"{STEM}.md"
FIGS = ARTICLE / "figs/layman-v2-2026-10-19"
REVIEW = ROOT / "logs/layman-v2-2026-10-19"
TEAL, INK, MUTED, PALE = "#17786c", "#173c3b", "#566f72", "#edf4f1"


def svg(name, width, height, body):
    result = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
              f'viewBox="0 0 {width} {height}"><rect width="100%" height="100%" fill="white"/>'
              f'<g font-family="DejaVu Sans, sans-serif" fill="{INK}">{body}</g></svg>')
    (FIGS / name).write_text(result)


def text(x, y, value, size=22, color=INK, weight="normal", anchor="start"):
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" '
            f'font-weight="{weight}" text-anchor="{anchor}">{escape(str(value))}</text>')


def infographics(components, words, other_types):
    # Schematic: same 24 positions and eight labels in both panels.
    panels = (("EXAMPLE: ALIGNED LABELS", {1, 7, 13, 19, 4, 10, 16, 22}),
              ("LABELS REASSIGNED", {0, 6, 9, 14, 17, 19, 21, 23}))
    body = ""
    for p, (title, selected) in enumerate(panels):
        left = 25 + p*530
        body += text(left, 30, title, 23, weight="bold")
        for i in range(24):
            x, y = left + (i % 6)*65, 57 + (i // 6)*42
            color = "#d9477d" if i in selected else "#dce6e3"
            body += f'<rect x="{x}" y="{y}" width="46" height="16" rx="5" fill="{color}"/>'
        body += text(left, 245, "Same sites. Same number of selected labels.", 17, MUTED)
    body += text(480, 130, "→", 52, TEAL, anchor="middle")
    svg("shuffle-explained.svg", 1000, 265, body)

    body = ""
    for p, (title, count, label, color) in enumerate((
            ("OBSERVED", 75, "about 75 in 100", "#d9477d"),
            ("RANDOM-LABEL MODEL", 25, "about 25 in 100", "#66899b"))):
        left = 50 + p*515
        body += text(left, 29, title, 24, weight="bold")
        for i in range(100):
            body += (f'<circle cx="{left + (i % 10)*31 + 10}" cy="{61+(i//10)*25}" '
                     f'r="9" fill="{color if i < count else "#e5edeb"}"/>')
        body += text(left, 330, label, 27, weight="bold")
    require(round(100*components["observed"]/components["selected"]) == 75, "Observed waffle rounding differs")
    require(round(100*components["expected"]/components["selected"]) == 25, "Reference waffle rounding differs")
    svg("component-waffles.svg", 1000, 350, body)

    body = text(40, 35, "A 1, followed by these 814 zeros", 29, weight="bold")
    for i in range(814):
        body += text(42+(i % 37)*24, 77+(i//37)*16, "0", 15,
                     TEAL if (i//37) % 2 == 0 else MUTED)
    body += text(40, 450, "Digits wrapped across 22 rows of 37. This is the denominator, not 814 trials.", 17, MUTED)
    require(22*37 == 814, "Zero-grid dimensions differ")
    svg("814-zeros.svg", 1000, 470, body)

    body = ""
    for i, (title, lines) in enumerate((
            ("1  COUNT", ("Work out the allowed", "selections on each page")),
            ("2  CALCULATE", ("Use exact whole numbers", "and fractions")),
            ("3  CHECK", ("Prove the probability", "stays below the bound")))):
        left = 10 + i*340
        body += f'<rect x="{left}" y="5" width="300" height="150" rx="16" fill="{PALE}"/>'
        body += text(left+18, 43, title, 24, TEAL, "bold")
        for j, line in enumerate(lines):
            body += text(left+18, 83+j*28, line, 20)
        if i < 2:
            body += text(left+319, 91, "→", 27, TEAL, anchor="middle")
    svg("proof-in-three-steps.svg", 1000, 165, body)

    target = words["targets"]["standalone_allah"]
    actual = 100*target["aligned"]/target["located"]
    mean = words["comparisons"]["page_row_width20"]["metrics"]["standalone_allah"]["analytic_expected_aligned"]
    expected = 100*mean/target["located"]
    body = ""
    for i, (big, title, detail) in enumerate((
            (f"{actual:.2f}%", "Standalone Allah aligns", "of 2,151 mapped occurrences"),
            (f"{expected:.2f}%", "Reference model mean", "page, row and width retained"),
            (str(other_types), "Other aligned word types", "excluding Allah-name forms"))):
        left = 10+i*335
        body += f'<rect x="{left}" y="0" width="315" height="145" rx="14" fill="{PALE}"/>'
        body += text(left+18, 57, big, 43, TEAL, "bold")
        body += text(left+18, 91, title, 19, weight="bold")
        body += text(left+18, 120, detail, 16, MUTED)
    svg("word-facts.svg", 1000, 150, body)


def annotated_allah(image):
    result = image.copy()
    draw = ImageDraw.Draw(result)
    for y in range(135, 567, 14):
        draw.line((589, y, 589, min(y+7, 567)), fill=TEAL, width=2)
    for box in ((550, 146, 630, 220), (552, 476, 624, 550)):
        left, top, right, bottom = box
        draw.rounded_rectangle((left-5, top-5, right+5, bottom+5), radius=6, outline=TEAL, width=4)
    return result


def scan_assets(review, words, refresh):
    destination = FIGS / "sources.json"
    if destination.exists() and not refresh:
        manifest = read_json(destination)
        require(manifest["review_sha256"] == digest(DATA / "research_broad_phrase_review_v1.json"),
                "Scan review evidence changed")
        require(manifest["word_study_sha256"] == digest(DATA / "research_same_word_alignment_v1.json"),
                "Word-center evidence changed")
        for entry in manifest["figures"]:
            require(digest(FIGS / entry["output"]) == entry["output_sha256"], "Derived Hayrat image changed")
        return manifest

    font = ImageFont.load_default(size=25)
    word_locations = {row[0]: row for row in words["located_inventory"]}
    for token, x2, width in ((77, 1180, 80), (100, 1176, 72)):
        row = word_locations[token]
        require(row[1] == 2 and row[3:] == [x2, width], "Cover word coordinates differ")
    from same_word_alignment import canonical_inventory
    canonical, _ = canonical_inventory()
    require(canonical[77]["word"] == canonical[100]["word"] == "الله", "Cover words are not standalone Allah")
    require((canonical[77]["verse"], canonical[100]["verse"]) == ("2:7", "2:9"), "Cover verse IDs differ")
    pair_ids = {tuple(sorted(pair)) for pair in words["same_word_pair_token_ids"]}
    require((77, 100) in pair_ids, "Cover pair absent from the measured word ledger")
    page_two = next(e for e in review["lengths"]["1"]["examples"] if e["page"] == 2)
    path = ROOT / "hayrat-pics/page_2.png"
    require(digest(path) == page_two["image_sha256"], "Page 2 source hash differs")
    image = annotated_allah(open_rgb(path))
    sheet = Image.new("RGB", (1400, 1080), "white")
    draw = ImageDraw.Draw(sheet)
    draw.text((10, 7), "FULL HAYRAT PAGE 2", font=font, fill=INK)
    full = image.resize((610, round(image.height*610/image.width)))
    sheet.paste(full, (5, 55))
    draw.text((660, 7), "DETAIL: THE SAME WORD", font=font, fill=INK)
    crop = image.crop((385, 115, 845, 580))
    crop = crop.resize((700, round(crop.height*700/crop.width)))
    sheet.paste(crop, (660, 135))
    draw.text((660, 900), "2:7 / 2:9", font=font, fill=TEAL)
    draw.text((660, 944), "Original horizontal positions retained", font=font, fill=MUTED)
    target = FIGS / "hayrat-page-and-detail.png"
    sheet.save(target)
    records = [dict(output=target.name, output_sha256=digest(target), source=f"hayrat-pics/{path.name}",
                    source_sha256=digest(path), page=2, token_ids=[77, 100],
                    original_boxes=[[550, 146, 630, 220], [552, 476, 624, 550]],
                    crop=[385, 115, 845, 580], transforms="Full-page and detail resized uniformly; green guide/outlines added. No horizontal repositioning of words.")]

    for length, page, filename in (("5", 6, "hayrat-five-word-phrase.png"),
                                   ("6", 431, "hayrat-six-word-phrase.png")):
        example = next(e for e in review["lengths"][length]["examples"]
                       if e["page"] == page and e["status"] == "strict_pair")
        require(len(example["occurrences"]) == 2, "Expected a phrase pair")
        path = ROOT / f"hayrat-pics/page_{page}.png"
        require(digest(path) == example["image_sha256"], "Phrase scan hash differs")
        image = open_rgb(path)
        boxes = [b for o in example["occurrences"] for b in o["boxes"]]
        left, right = max(0, min(b[0] for b in boxes)-18), min(image.width, max(b[2] for b in boxes)+18)
        scale = 1200/(right-left)
        panels, crops = [], []
        for occurrence in example["occurrences"]:
            top = max(0, min(b[1] for b in occurrence["boxes"])-12)
            bottom = min(image.height, max(b[3] for b in occurrence["boxes"])+12)
            crop = image.crop((left, top, right, bottom))
            crop = crop.resize((1200, round(crop.height*scale)))
            panel = Image.new("RGB", (1200, crop.height+38), "white")
            panel.paste(crop, (0, 38))
            draw = ImageDraw.Draw(panel)
            draw.text((9, 4), f'Hayrat p{page} / {occurrence["verse"]}', font=font, fill=INK)
            for b in occurrence["boxes"]:
                draw.rectangle(((b[0]-left)*scale, (b[1]-top)*scale+38,
                                (b[2]-left)*scale, (b[3]-top)*scale+38), outline="#297bad", width=2)
            panels.append(panel)
            crops.append([left, top, right, bottom])
        sheet = Image.new("RGB", (1200, sum(p.height for p in panels)+16), "white")
        y = 0
        for panel in panels:
            sheet.paste(panel, (0, y))
            y += panel.height+16
        draw = ImageDraw.Draw(sheet)
        for x2 in example["occurrences"][0]["twice_centers"]:
            x = round((x2/2-left)*scale)
            for y in range(38, sheet.height, 16):
                draw.line((x, y, x, min(y+6, sheet.height)), fill="#80bad2", width=1)
        target = FIGS / filename
        sheet.save(target)
        records.append(dict(output=filename, output_sha256=digest(target), source=f"hayrat-pics/{path.name}",
                            source_sha256=digest(path), page=page, crops=crops,
                            occurrences=example["occurrences"],
                            center_differences_pixels=example["corresponding_center_differences_pixels"],
                            transforms="Both row excerpts use one horizontal crop and uniform scale. Blue support boxes and dashed first-row center guides added; intervening rows omitted."))
    manifest = dict(date="2026-10-19", use="Private working draft with Hayrat edition scan excerpts; project overlays. No transfer of rights in source scans is claimed.",
                    review_sha256=digest(DATA / "research_broad_phrase_review_v1.json"),
                    word_study_sha256=digest(DATA / "research_same_word_alignment_v1.json"), figures=records)
    destination.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n")
    return manifest


CSS = """
@page {size:A4;margin:15mm 17mm 16mm;
 @bottom-left {content:'TAWAFUQ / PRIVATE WORKING DRAFT / LAYMAN V2';font:7pt 'DejaVu Sans';color:#66817d}
 @bottom-right {content:counter(page) ' / ' counter(pages);font:8pt 'DejaVu Sans';color:#66817d}}
* {box-sizing:border-box}
body {margin:0;background:#e8f0ed;color:#213b3b;font:17px/1.5 'DejaVu Sans',sans-serif}
.page {max-width:900px;margin:24px auto;padding:45px 55px;background:white}
.eyebrow {font-size:11px;letter-spacing:1.6px;color:#17786c;margin-bottom:16px;text-transform:uppercase}
h1,h2,h3 {line-height:1.16;break-after:avoid;color:#14544b}
h1 {font-size:43px;letter-spacing:-1.4px;margin:0 0 12px}
h2 {font-size:31px;letter-spacing:-.7px;margin:0 0 16px}
h3 {font-size:20px;margin:17px 0 9px}
p {margin:12px 0;orphans:3;widows:3} strong {font-weight:700}
img {display:block;width:100%;height:auto} p:has(>img) {break-inside:avoid;margin:15px 0 8px}
img[src$="word-phrase.png"] {width:90%;margin-left:auto;margin-right:auto}
.caption {font-size:12px;line-height:1.43;color:#57716e;margin:5px 0 15px}
blockquote {background:#edf4f1;border-left:4px solid #b48842;padding:12px 17px;margin:16px 0;break-inside:avoid;font-size:18px}
blockquote p {margin:3px 0} a {color:#17786c;text-decoration:none}
.history {display:flex;align-items:flex-start;gap:18px;break-inside:avoid}
.history figure {margin:4px 0;width:48%}.history>div {width:52%}.history p {margin:0 0 11px}
.takeaway {color:#14544b;font-size:24px;line-height:1.3;margin:18px 0}
.notes {border-top:1px solid #d5e3dd;padding-top:10px;font-size:11px;line-height:1.45;color:#5f7773}
code {font-size:.86em;font-family:'DejaVu Sans Mono';overflow-wrap:anywhere}
[lang=ar] {font-family:'DejaVu Sans',sans-serif;unicode-bidi:isolate}
@media print {
 body {background:white;font-size:10.5pt;line-height:1.44}
 .page {margin:0;padding:0;max-width:none;break-after:page}.page:last-child {break-after:auto}
 .eyebrow {font-size:7.5pt;margin-bottom:12px}
 h1 {font-size:29pt} h2 {font-size:23pt;margin-bottom:14px} h3 {font-size:13pt;margin:13px 0 8px}
 p {margin:9px 0} p:has(>img) {margin:12px 0 6px}
 .caption {font-size:8pt;margin:4px 0 11px}.notes {font-size:7.5pt}
 blockquote {font-size:11.5pt;padding:9px 13px;margin:12px 0}
 .takeaway {font-size:17pt;margin:14px 0}.history {gap:14px}
}
"""


def build(refresh=False):
    FIGS.mkdir(parents=True, exist_ok=True)
    REVIEW.mkdir(parents=True, exist_ok=True)
    source = SOURCE.read_text()
    proof_inputs, components = check_component_bound((ARTICLE / "tawafuq-findings-2026-10-19.md").read_text())
    words_path = DATA / "research_same_word_alignment_v1.json"
    review_path = DATA / "research_broad_phrase_review_v1.json"
    words = read_json(words_path)["views"]["conservative_v5"]
    review = read_json(review_path)
    target = words["targets"]["standalone_allah"]
    require((target["aligned"], target["located"]) == (1717, 2151), "Word statistic differs")
    other_types = review["lengths"]["1"]["non_allah_aligned_distinct_types"]
    require(other_types == 580, "Other word-type count differs")
    for value in ("10⁻⁸¹⁴", "3,522", "4,682", "75.22%", "25.24%", "1,717", "2,151", "79.82%", "36.96%"):
        require(value in source, f"Principal claim absent from source: {value}")
    for length, page, maximum in (("5", 6, 4), ("6", 431, 4.5)):
        example = next(e for e in review["lengths"][length]["examples"] if e["page"] == page)
        require(max(example["corresponding_center_differences_pixels"]) == maximum, "Phrase caption differs")
    infographics(components, words, other_types)
    scans = scan_assets(review, words, refresh)
    history_sources = read_json(ARTICLE / "figs/findings-2026-10-19/sources.json")
    history = next(f for f in history_sources["figures"] if f["output"] == "historical-1779.png")
    require(digest(ARTICLE / "figs/findings-2026-10-19/historical-1779.png") == history["output_sha256"],
            "Historical source asset differs")
    parts = source.split("<!-- page -->")
    require(len(parts) == 5, "The layman article should have five designed pages")
    sections = []
    for i, (part, label) in enumerate(zip(parts, ("See the pattern", "Try the comparison", "Understand the number", "Look at the words", "Ask the next question")), 1):
        sections.append(f'<section class="page"><div class="eyebrow">{label} · {i:02d}</div>'
                        + markdown.markdown(part, extensions=["tables", "fenced_code"]) + '</section>')
    document = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1">'
                '<meta name="author" content="Tawafuq research project, AI-assisted">'
                '<title>A Pattern Worth Explaining — Tawafuq in Plain English</title>'
                f'<style>{CSS}</style></head><body>' + "\n".join(sections) + '</body></html>')
    resources = Resources()
    resources.feed(document)
    html_path, pdf_path = REVIEW / f"{STEM}.html", ARTICLE / f"{STEM}.pdf"
    html_path.write_text(document)
    HTML(filename=str(html_path), base_url=ARTICLE.as_uri()+"/").write_pdf(pdf_path)
    with pymupdf.open(pdf_path) as pdf:
        require(len(pdf) == 5, f"Expected 5 pages, got {len(pdf)}; inspect overflow")
        extracted = " ".join(" ".join(page.get_text() for page in pdf).split())
        for value in ("10⁻⁸¹⁴", "75.22%", "25.24%", "79.82%", "36.96%", "Quran 2:23",
                      "independently specified, text-preserving"):
            require(value in extracted, f"Principal text absent from PDF: {value}")
        require("\ufffd" not in extracted, "Replacement character in PDF")
        thumbs = []
        for i, page in enumerate(pdf, 1):
            for block in page.get_text("dict")["blocks"]:
                require(page.rect.contains(pymupdf.Rect(block["bbox"])), f"Clipped content on page {i}")
            path = REVIEW / f"page-{i:02d}.png"
            page.get_pixmap(dpi=115).save(path)
            with Image.open(path) as image:
                thumb = image.copy()
            thumb.thumbnail((380, 540))
            thumbs.append(thumb)
        contact = Image.new("RGB", (3*400, math.ceil(len(thumbs)/3)*565), "#dbe7e1")
        for i, thumb in enumerate(thumbs):
            contact.paste(thumb, (10+(i%3)*400, 10+(i//3)*565))
        contact.save(REVIEW / "contact-sheet.png")
    manifest = dict(article_sha256=digest(SOURCE), builder_sha256=digest(Path(__file__)),
                    component_certificate=components, proof_inputs=proof_inputs,
                    evidence_inputs={p.name: digest(p) for p in (words_path, review_path)},
                    assets={p.name: digest(p) for p in resources.images},
                    scan_source_manifest_sha256=digest(FIGS / "sources.json"),
                    pdf_sha256=digest(pdf_path), pages=5, infographics=5,
                    source_scan_pages=sorted({f["page"] for f in scans["figures"]}),
                    checks="Full component certificate replay; principal word/phrase claims, scan hashes/coordinates, local assets, PDF text, five-page layout and content bounds. Visual inspection separate.")
    (REVIEW / "build-manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
    print(f"Built {pdf_path.relative_to(ROOT)}: 5 pages, 5 infographics, Hayrat pages 2/6/431")
    print(f"Review: {(REVIEW / 'contact-sheet.png').relative_to(ROOT)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh-scans", action="store_true")
    build(parser.parse_args().refresh_scans)
