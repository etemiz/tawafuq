"""Build the corrected findings article, portable figures, PDF and review sheets.

Run in .venv: python tools/build_findings_article.py
Optional --refresh-historical regenerates public-domain crops from local scans.
No network or modern copyrighted page images are used by this builder.
"""

import argparse
from fractions import Fraction
import hashlib
from html import escape
from html.parser import HTMLParser
import json
import math
from pathlib import Path

import markdown
from PIL import Image, ImageDraw
import pymupdf
from weasyprint import HTML

ROOT = Path(__file__).resolve().parents[1]
ARTICLE = ROOT / "docs/articles"
STEM = "tawafuq-findings-2026-10-19"
SOURCE = ARTICLE / f"{STEM}.md"
FIGS = ARTICLE / "figs/findings-2026-10-19"
REVIEW = ROOT / "logs/findings-article-2026-10-19"
DATA = ROOT / "tools/data"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    return json.loads(path.read_text())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_component_bound(source):
    """Rebuild every headline page PMF and certify the decimal bound exactly."""
    from alignment import ScoreSpec
    from exact_column import column_distribution, markov_bound
    from real_stats import input_manifest, observed_counts
    from reference_controls import prepare

    path = DATA / "audit_exact_columns_raw_wordlike.json"
    report = read_json(path)
    directory = DATA / report["data_directory"]
    require(input_manifest(directory) == report["inputs"], "Component input hashes differ")
    require(report["reference_preprocessing"] == dict(
        raw_observed=True, size_filter=True, exclude_gold=True), "Component preprocessing differs")
    pages, details = prepare(directory, raw_observed=True, size_filter=True, exclude_gold=True)
    require(details == report["preprocessing_details"], "Component eligibility differs")
    selected = sum(len(page["reds"]) for page in pages.values())
    sites = sum(len(page["slots"]) for page in pages.values())
    require((len(pages), selected, sites) == (587, 4682, 76375), "Headline population differs")
    spec = ScoreSpec(**report["score"])
    observed = observed_counts(pages, spec)["column"]
    require(observed == report["observed"] == 3522, "Headline observed column score differs")
    require(set(report["page_distributions"]) == {str(p) for p in pages}, "Page PMF inventory differs")
    distributions = []
    mean = Fraction(0)
    for page, data in pages.items():
        counts, denominator = column_distribution(data["slots"], len(data["reds"]), spec)
        saved = report["page_distributions"][str(page)]
        require(counts == list(map(int, saved["counts"])) and denominator == int(saved["denominator"]),
                f"Exact page distribution differs: {page}")
        distributions.append((counts, denominator))
        mean += Fraction(sum(score * count for score, count in enumerate(counts)), denominator)
    bound = markov_bound(distributions, observed, 8)
    saved_bound = report["bounds"]["8"]
    require(bound == Fraction(int(saved_bound["numerator_hex"], 16),
                              int(saved_bound["denominator_hex"], 16)), "Rational bound differs")
    require(bound.numerator * 10**814 < bound.denominator, "Decimal 10^-814 certificate fails")
    require(abs(float(mean) - report["analytic_column_mean"]) < 1e-9, "Column expectation differs")
    observed_rate = 100 * observed / selected
    mean_rate = 100 * float(mean) / selected
    require(f"**{observed:,} / {selected:,}** | **{observed_rate:.2f}%**" in source,
            "Published component observation differs")
    require(f"**{float(mean):,.2f} / {selected:,}** | **{mean_rate:.2f}%**" in source,
            "Published component expectation differs")
    require("10⁻⁸¹⁴" in source and "76,375" in source, "Headline certificate/population absent")
    paths = [path, ROOT / "tools/exact_column.py", ROOT / "tools/reference_controls.py",
             ROOT / "tools/alignment.py", ROOT / "tools/real_stats.py"]
    summary = dict(pages=len(pages), selected=selected, sites=sites, observed=observed,
                   expected=float(mean), certified_decimal_power=814, exponential_base=8)
    print("Reconstructed all 587 exact page distributions and certified bound < 10^-814", flush=True)
    return {p.name: digest(p) for p in paths}, summary


def check_numbers(source):
    """Bind the published principal tables to the corrected versioned reports."""
    paths = [DATA / name for name in (
        "research_same_word_alignment_v1.json", "research_same_word_exact_bounds_v1.json",
        "research_broad_phrase_alignment_v1.json", "research_phrase_structure_controls_v1.json",
        "research_historical_center_review_v1.json", "research_historical_extension_review_v3.json")]
    words, certificates, broad, structure, historical, extension = map(read_json, paths)
    view = words["views"]["conservative_v5"]
    for key, aligned, located in (("standalone_allah", 1717, 2151),
                                  ("allah_name_family", 2278, 2695),
                                  ("all_identical_words", 6580, 76511)):
        target = view["targets"][key]
        require((target["aligned"], target["located"]) == (aligned, located), key)
        require(f"{aligned:,} / {located:,}" in source, f"Article table differs: {key}")
    cert = certificates["certificates"]["page_row_width20"]["standalone_allah"]
    require(cert["conservative_decimal_power"] == 57 and cert["observed"] == 1717,
            "Conditional decimal certificate differs")
    for n, located, aligned, types, eligible in (
            (1, 73816, 4745, 580, 2680), (2, 28957, 1084, 396, 641),
            (3, 11870, 433, 171, 266), (4, 5382, 187, 75, 106),
            (5, 2625, 65, 30, 32), (6, 1296, 28, 13, 12)):
        result = broad["results"][str(n)]
        require(result["located_population"]["without_allah_forms"] == located, "Phrase population differs")
        require(result["observed"]["full_mapped"]["without_allah_forms"] == aligned, "Phrase score differs")
        counted = sum(r["without_allah_forms"] and r["aligned"]["full_mapped"] > 0
                      for r in result["per_type"])
        require(counted == types, "Aligned type count differs")
        require(f"{located:,} | **{aligned:,}** | **{types:,}**" in source,
                "Published phrase table differs")
        block = structure["models"]["repeated_phrase_blocks"]["results"][str(n)]
        require(block["observed"]["without_allah_forms"] == eligible, "Eligible population score differs")
        expected_mean = sum(structure["models"]["repeated_phrase_blocks"]["simulation"]
                            ["samples"][str(n)]["without_allah_forms"]) / 5000
        whole_mean = sum(broad["simulation"]["samples"][str(n)]["without_allah_forms"]) / 5000
        require(f"**{eligible:,}** | {whole_mean:,.2f} | {expected_mean:,.2f}" in source,
                "Published spacing comparison differs")
    first = historical["scores"]["0.02"]["allah_name_family"]["historical"]
    second = extension["scores"]["0.02"]["allah_name_family"]["historical"]
    require((first["midpoint_aligned"], first["occurrences"]) == (10, 33), "1779 score differs")
    require((second["midpoint_aligned"], second["occurrences"]) == (34, 66), "Current 1776 score differs")
    require("**10 / 33**" in source and "**34 / 66**" in source, "Historical article table differs")
    return {p.name: digest(p) for p in paths}, view, certificates


def component_graph(summary):
    rows = []
    for i, (label, count, color) in enumerate((
            ("Observed column-aligned components", summary["observed"], "#186b61"),
            ("Uniform per-page labeling: expected", summary["expected"], "#83949b"))):
        value = 100 * count / summary["selected"]
        y = 42 + i * 68
        rows.append(f'<text x="20" y="{y}" font-size="15">{escape(label)}</text>'
                    f'<rect x="20" y="{y+10}" width="590" height="19" rx="4" fill="#edf2f1"/>'
                    f'<rect x="20" y="{y+10}" width="{590*value/100:.4f}" height="19" rx="4" fill="{color}"/>'
                    f'<text x="630" y="{y+25}" font-size="20" font-weight="bold">{value:.2f}%</text>')
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="740" height="188" viewBox="0 0 740 188">'
           '<rect width="740" height="188" fill="white"/>'
           '<g font-family="DejaVu Sans, sans-serif" fill="#1b3036">' + "".join(rows)
           + '<text x="20" y="177" font-size="12" fill="#52656a">4,682 selected components; fixed bins, column-only score, specified label model.</text></g></svg>')
    (FIGS / "component-comparison.svg").write_text(svg)


def graph(view, certificates):
    target = view["targets"]["standalone_allah"]
    values = [100 * target["aligned"] / target["located"]]
    for model in ("page_row", "page_row_width20"):
        cert = certificates["certificates"][model]["standalone_allah"]
        mean = Fraction(int(cert["expectation_numerator_hex"], 16),
                        int(cert["expectation_denominator_hex"], 16))
        values.append(100 * float(mean) / target["located"])
    rows = []
    for i, (label, value) in enumerate(zip(
            ("Observed same-word alignment", "Page + row reference", "Page + row + width reference"), values)):
        y = 46 + i * 67
        color = "#186b61" if i == 0 else "#83949b"
        rows.append(f'<text x="20" y="{y}" font-size="15">{escape(label)}</text>'
                    f'<rect x="20" y="{y+10}" width="590" height="19" rx="4" fill="#edf2f1"/>'
                    f'<rect x="20" y="{y+10}" width="{590*value/100:.4f}" height="19" rx="4" fill="{color}"/>'
                    f'<text x="630" y="{y+25}" font-size="20" font-weight="bold">{value:.2f}%</text>')
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="740" height="252" viewBox="0 0 740 252">'
           '<rect width="740" height="252" fill="white"/>'
           '<g font-family="DejaVu Sans, sans-serif" fill="#1b3036">' + "".join(rows)
           + '<text x="20" y="245" font-size="12" fill="#52656a">Same 2,151 mapped standalone occurrences; reference means are model-conditional.</text></g></svg>')
    (FIGS / "same-word-comparison.svg").write_text(svg)


def historical_figures(refresh):
    manifest_path = FIGS / "sources.json"
    if not refresh and manifest_path.exists():
        manifest = read_json(manifest_path)
        for entry in manifest["figures"]:
            require(digest(FIGS / entry["output"]) == entry["output_sha256"], "Historical crop changed")
        return
    inputs = [
        dict(path=ROOT / "logs/historical-copy-ms-or-422-v1/ia-leaf-404.jpg",
             sha="15c671d08d7a10f5d61c2b8e7bde49b3d8fc8f9e0f39826082e27a6ba9efc648",
             output="historical-1779.png", url="https://archive.org/download/ldpd_14642794_000/page/n404.jpg",
             catalogue="https://openn.library.upenn.edu/Data/0032/html/ms_or_422.html"),
        dict(path=ROOT / "logs/historical-extension-ms-or-91-v1/folio-99r.jpg",
             sha="f854245849998f791e82b99c8b9387d0f3e9171b46ba83cdd26b187c6af62479",
             output="historical-1776.png", url="https://archive.org/download/ldpd_13604207_000/page/n202.jpg",
             catalogue="https://openn.library.upenn.edu/Data/0032/html/ms_or_091.html")]
    records = []
    for entry in inputs:
        require(digest(entry["path"]) == entry["sha"], "Historical source hash differs")
        with Image.open(entry["path"]) as raw:
            image = raw.convert("RGB")
            image = image.resize((1000, round(image.height * 1000 / image.width)))
        if entry["output"] == "historical-1779.png":
            sheet = Image.new("RGB", (1020, 510), "white")
            sheet.paste(image.crop((220, 330, 560, 490)).resize((1020, 480)), (0, 30))
            draw = ImageDraw.Draw(sheet)
            for x in range(225, 560, 25):
                sx = (x - 220) * 3
                draw.text((sx, 5), str(x), fill="blue")
                draw.line((sx, 30, sx, 510), fill=(100, 180, 200))
            transform = dict(resize_width=1000, crop=[220, 330, 560, 490], magnification=3,
                             overlay="25px common horizontal ruler; two adjacent physical rows")
        else:
            sheet = Image.new("RGB", (600, 460), "white")
            draw = ImageDraw.Draw(sheet)
            for i, (row, top) in enumerate(((4, 501), (8, 766))):
                sheet.paste(image.crop((315, top, 515, top+65)).resize((600, 195)), (0, i*230+35))
                draw.text((5, i*230), f"99r physical row {row}; original x coordinates", fill="black")
                for x in range(325, 515, 25):
                    sx = (x-315)*3
                    draw.text((sx, i*230+15), str(x), fill="blue")
                    draw.line((sx, i*230+35, sx, i*230+230), fill=(100, 180, 200))
            transform = dict(resize_width=1000, crops=[[315, 501, 515, 566], [315, 766, 515, 831]],
                             magnification=3, overlay="25px common horizontal ruler; omitted intervening rows labelled")
        path = FIGS / entry["output"]
        sheet.save(path)
        records.append(dict(output=path.name, output_sha256=digest(path), source_url=entry["url"],
                            source_sha256=entry["sha"], catalogue=entry["catalogue"], transform=transform))
    manifest = dict(date="2026-10-19", rights="Columbia manuscript images designated public domain by OPenn; metadata CC0. Project crops and ruler overlays reproduce common horizontal coordinates.",
                    figures=records)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")


CSS = """
@page { size:A4; margin:16mm 17mm 16mm;
 @bottom-left { content:'TAWAFUQ / FINDINGS & OPEN CHALLENGE'; font:7pt 'DejaVu Sans'; color:#61777a; }
 @bottom-right { content:counter(page) ' / ' counter(pages); font:8pt 'DejaVu Sans'; color:#61777a; }}
* {box-sizing:border-box}
body {margin:0;background:#e9eeec;color:#203238;font:15px/1.53 'DejaVu Sans',sans-serif}
.sheet {max-width:880px;margin:24px auto;background:white;padding:45px 58px}
.eyebrow {font-size:10px;letter-spacing:1.5px;text-transform:uppercase;color:#186b61;margin-bottom:15px}
h1,h2,h3 {line-height:1.18;color:#143f3b;break-after:avoid}
h1 {font-size:45px;letter-spacing:-1.7px;margin:0 0 17px}
h2 {font-size:28px;letter-spacing:-.65px;margin:0 0 20px}
h3 {font-size:17px;margin:18px 0 9px}
p {margin:10px 0;orphans:3;widows:3}
a {color:#186b61;text-decoration:none} strong {font-weight:700}
blockquote {margin:17px 0;padding:11px 17px;border-left:4px solid #b08337;background:#f4f6f2;color:#143f3b;font-size:18px;break-inside:avoid}
blockquote p {margin:0}
table {border-collapse:collapse;width:100%;margin:17px 0;font-size:12px;break-inside:avoid}
th {text-align:left;background:#e8f0ed;color:#143f3b}
td,th {padding:8px 7px;border-bottom:1px solid #dce5e1;vertical-align:top}
tbody tr:nth-child(even) {background:#f7f9f8}
img {max-width:100%;height:auto} p:has(>img) {margin:17px 0;break-inside:avoid}
ul,ol {padding-left:22px} li {margin:7px 0}
code {font-family:'DejaVu Sans Mono',monospace;font-size:.86em;overflow-wrap:anywhere}
pre {white-space:pre-wrap;background:#f0f4f2;padding:12px;font-size:11px;line-height:1.55;break-inside:avoid}
.historical-pair {display:flex;align-items:flex-start;gap:16px;break-inside:avoid;margin:15px 0}
.historical-pair figure {width:50%;margin:0}
.historical-pair img {display:block;width:100%}
figcaption,small {font-size:10px;line-height:1.45;color:#53686b}
figcaption {margin-top:7px}
[lang=ar] {font-family:'DejaVu Sans',sans-serif;font-size:1.14em;unicode-bidi:isolate}
@media print {
 body {background:white;font-size:9.5pt;line-height:1.46}
 .sheet {margin:0;padding:0;max-width:none;break-after:page}
 .sheet:last-child {break-after:auto}
 .eyebrow {font-size:7.5pt;margin-bottom:12px}
 h1 {font-size:32pt} h2 {font-size:21pt;margin-bottom:16px} h3 {font-size:11.5pt;margin:15px 0 7px}
 p {margin:9px 0} blockquote {font-size:12pt;margin:13px 0;padding:10px 13px}
 table {font-size:8.5pt;margin:12px 0} td,th {padding:7px 6px}
 li {margin:5px 0} pre {font-size:8pt;line-height:1.42;padding:9px}
 small,figcaption {font-size:7pt} .historical-pair {margin:12px 0;gap:12px}
 .references {font-size:8.3pt;line-height:1.4}
 .references p {margin:8px 0}
}
"""


class Resources(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "img":
            require(bool(attrs.get("alt")), "Missing image description")
            path = (ARTICLE / attrs["src"]).resolve()
            require(path.is_relative_to(ARTICLE) and path.is_file(), "Invalid article asset")
            self.images.append(path)


def build(refresh=False):
    FIGS.mkdir(parents=True, exist_ok=True)
    REVIEW.mkdir(parents=True, exist_ok=True)
    source = SOURCE.read_text()
    component_inputs, component_summary = check_component_bound(source)
    inputs, view, certs = check_numbers(source)
    inputs.update(component_inputs)
    component_graph(component_summary)
    graph(view, certs)
    historical_figures(refresh)
    parts = source.split("<!-- page -->")
    sections = []
    for index, part in enumerate(parts, 1):
        content = markdown.markdown(part, extensions=["tables", "fenced_code"])
        classes = "sheet references" if index == len(parts) else "sheet"
        sections.append(f'<section class="{classes}"><div class="eyebrow">'
                        f'Research report · 19 October 2026 · {index:02d}</div>{content}</section>')
    document = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1">'
                '<meta name="author" content="Tawafuq research project, AI-assisted">'
                '<meta name="description" content="The certified 10^-814 component-label bound, separate word-level evidence, and a proposed reproduction challenge.">'
                '<title>The 10⁻⁸¹⁴ Result — Tawafuq and an Open Challenge</title>'
                f'<style>{CSS}</style></head><body>' + "\n".join(sections) + '</body></html>')
    resources = Resources()
    resources.feed(document)
    html_path, pdf_path = REVIEW / f"{STEM}.html", ARTICLE / f"{STEM}.pdf"
    html_path.write_text(document)
    HTML(filename=str(html_path), base_url=ARTICLE.as_uri() + "/").write_pdf(pdf_path)
    with pymupdf.open(pdf_path) as pdf:
        require(len(pdf) == len(parts), f"Expected {len(parts)} pages, got {len(pdf)}; inspect overflow")
        text = "\n".join(page.get_text() for page in pdf)
        require("\ufffd" not in text, "Replacement characters in PDF")
        for value in ("10⁻⁸¹⁴", "75.22%", "25.24%", "3,522 / 4,682", "1,181.55 / 4,682",
                      "79.82%", "36.96%", "1,717 / 2,151", "34 / 66", "10 / 33"):
            require(value in text, f"Missing principal claim in PDF: {value}")
        require("independently specified, text-preserving" in " ".join(text.split()), "Challenge missing from PDF")
        thumbs = []
        for i, page in enumerate(pdf, 1):
            for block in page.get_text("dict")["blocks"]:
                require(page.rect.contains(pymupdf.Rect(block["bbox"])), f"Clipped content on page {i}")
            path = REVIEW / f"page-{i:02d}.png"
            page.get_pixmap(dpi=110).save(path)
            with Image.open(path) as raw:
                thumbnail = raw.copy()
                thumbnail.thumbnail((350, 500))
                thumbs.append(thumbnail)
        sheet = Image.new("RGB", (4*370, math.ceil(len(thumbs)/4)*530), "#dae3df")
        for i, thumbnail in enumerate(thumbs):
            sheet.paste(thumbnail, (10+(i%4)*370, 10+(i//4)*530))
        sheet.save(REVIEW / "contact-sheet.png")
        page_count = len(pdf)
    manifest = dict(article_sha256=digest(SOURCE), builder_sha256=digest(Path(__file__)),
                    evidence_inputs=inputs, component_certificate=component_summary,
                    assets={p.name: digest(p) for p in resources.images},
                    html_sha256=digest(html_path), pdf_sha256=digest(pdf_path), pages=page_count,
                    checks="All 587 headline page PMFs rebuilt from hash-matched component inputs; exact base-8 rational bound reconstructed and numerator*10**814 < denominator certified. Principal tables matched to corrected reports; local images/alt text, page count, text presence and PDF bounds checked. Visual inspection is separate.")
    (REVIEW / "build-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Built {pdf_path.relative_to(ROOT)}: {page_count} pages")
    print(f"Review: {(REVIEW / 'contact-sheet.png').relative_to(ROOT)}")
    print("Principal numeric tables, resources, extracted text and PDF bounds checked")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh-historical", action="store_true")
    build(parser.parse_args().refresh_historical)
