#!/usr/bin/env python3
"""Build the English PDF rendition of docs/articles/tawafuq-art-v7.odt.

Extracts content directly from the ODT (paragraph styles, image frames,
tables), resolves images against docs/articles/figs/*.png by sha256 (falls
back to the embedded copies), renders HTML in the v7 article look (serif,
justified, brand-brown ruled headings, hanging bullets, callout, compact
tables, page-number footer) and writes docs/articles/tawafuq-art-v7-en.pdf
with weasyprint. English only. Validated with pymupdf (text extractable, no
replacement chars, key phrases present, 12 images drawn).
"""
import base64
import hashlib
import html
import json
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ODT = ROOT / "docs/articles/tawafuq-art-v7.odt"
FIGS = ROOT / "docs/articles/figs"
LOGS = ROOT / "logs/article-v7-pdf"
OUT_PDF = ROOT / "docs/articles/tawafuq-art-v7-en.pdf"

NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "draw": "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
    "xlink": "http://www.w3.org/1999/xlink",
    "svg": "http://www.w3.org/2000/svg",
}
W = lambda ns, a: f"{{{NS[ns]}}}{a}"

CSS = """
@page { size: A4; margin: 0.7874in;
        @bottom-center { content: counter(page); font-size: 9pt; color: #666;
                         font-family: 'DejaVu Serif', serif; } }
body { font-family: 'DejaVu Serif', 'DejaVu Sans', serif; font-size: 10.5pt;
       line-height: 1.4; color: #1b1b1b; }
h1 { font-size: 26pt; line-height: 1.2; color: #5b1f1f; text-align: center;
     margin: 0.35in 0 0.12in; }
p.lede { text-align: center; font-style: italic; color: #5b1f1f;
         font-size: 12.5pt; margin: 0 0 0.15in; }
p.lede-rule { border-bottom: 0.75pt solid #d9bcbc; padding-bottom: 0.1in; }
h2 { font-size: 15.5pt; color: #5b1f1f; border-bottom: 0.5pt solid #d9bcbc;
     padding-bottom: 0.03in; margin: 0.2in 0 0.08in; page-break-after: avoid; }
h3 { font-size: 12.5pt; color: #5b1f1f; margin: 0.16in 0 0.03in;
     page-break-after: avoid; }
p { margin: 0 0 0.0591in; text-align: justify; }
p.cap { font-size: 9pt; color: #444; font-style: italic; text-align: center;
        margin: 0.02in 0 0.1374in; page-break-before: avoid; }
p.bullet { margin: 0.0311in 0 0.0311in 0.18in; text-indent: -0.18in;
           text-align: justify; }
p.callout { text-align: center; font-style: italic; color: #5b1f1f;
            margin: 0.12in 0; }
figure { margin: 8pt 0 4pt; text-align: center; page-break-inside: avoid; }
figure img { max-width: 96%; max-height: 9.6cm; }
table { border-collapse: collapse; margin: 6pt auto 10pt; font-size: 9.5pt;
        page-break-inside: avoid; }
td, th { border: 0.6pt solid #bbb; padding: 3pt 7pt; text-align: left;
         vertical-align: top; }
th { background: #f5eeee; color: #5b1f1f; }
a { color: inherit; }
"""

H2 = {"P4", "P10", "P17", "P22", "P24"}
H3 = {"P14", "P20"}
CAP = {"P9"}


def extract(odt_path):
    with zipfile.ZipFile(odt_path) as z:
        root = ET.fromstring(z.read("content.xml"))
        embedded = {n: z.read(n) for n in z.namelist() if n.startswith("Pictures/")}
    body = root.find(f".//{W('office','text')}")
    items = []
    for el in body:
        if el.tag == W("text", "p"):
            frame = el.find("draw:frame", NS)
            if frame is not None:
                img = frame.find("draw:image", NS)
                href = img.get(W("xlink", "href"))
                items.append({"type": "image", "href": href,
                              "sha": hashlib.sha256(embedded[href]).hexdigest(),
                              "data": base64.b64encode(embedded[href]).decode()})
            else:
                text = "".join(el.itertext())
                items.append({"type": "p",
                              "style": el.get(W("text", "style-name")) or "Standard",
                              "text": text})
        elif el.tag in (W("text", "h"),):
            items.append({"type": "p",
                          "style": el.get(W("text", "style-name")) or "Standard",
                          "text": "".join(el.itertext())})
        elif el.tag == W("table", "table"):
            rows = []
            for r in el.findall("table:table-row", NS):
                cells = []
                for c in r.findall("table:table-cell", NS):
                    txt = " ".join("".join(p.itertext())
                                   for p in c.findall("text:p", NS)).strip()
                    cells.append(txt)
                rows.append(cells)
            items.append({"type": "table", "rows": rows})
    return items


def fig_lookup(items):
    by_hash = {hashlib.sha256(p.read_bytes()).hexdigest(): p
               for p in FIGS.rglob("*.png")}
    lut, dumped = {}, 0
    for it in items:
        if it["type"] != "image":
            continue
        p = by_hash.get(it["sha"])
        if p is None:
            p = LOGS / "pics" / Path(it["href"]).name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(base64.b64decode(it["data"]))
            dumped += 1
        lut[it["href"]] = p
    return lut, dumped


def render(items, lut):
    out = ["<html><head><meta charset='utf-8'><style>" + CSS + "</style></head><body>"]
    i = 0
    while i < len(items):
        it = items[i]
        if it["type"] == "p":
            style, text = it["style"], it["text"]
            if not text.strip():
                i += 1
                continue
            esc = html.escape(text)
            if style == "P1":
                out.append(f"<h1>{esc}</h1>")
            elif style == "P2":
                out.append(f'<p class="lede">{esc}</p>')
            elif style == "P3":
                out.append(f'<p class="lede lede-rule">{esc}</p>')
            elif style in H2:
                out.append(f"<h2>{esc}</h2>")
            elif style in H3:
                out.append(f"<h3>{esc}</h3>")
            elif style in CAP:
                out.append(f'<p class="cap">{esc}</p>')
            elif style == "P15":
                out.append(f'<p class="bullet">{esc}</p>')
            elif style == "P16":
                out.append(f'<p class="callout">{esc}</p>')
            else:
                out.append(f"<p>{esc}</p>")
        elif it["type"] == "image":
            cap = ""
            if (i + 1 < len(items) and items[i + 1].get("type") == "p"
                    and items[i + 1]["style"] in CAP):
                cap = items[i + 1]["text"]
                i += 1
            src = lut[it["href"]].as_uri()
            out.append('<figure><img src="%s">%s</figure>' % (
                src, f'<figcaption class="cap">{html.escape(cap)}</figcaption>' if cap else ""))
        elif it["type"] == "table":
            rows = [r for r in it["rows"] if any(c.strip() for c in r)]
            parts = ["<table>"]
            for r, row in enumerate(rows):
                tag = "th" if r == 0 else "td"
                parts.append("<tr>" + "".join(f"<{tag}>{html.escape(c)}</{tag}>"
                                              for c in row) + "</tr>")
            out.append("".join(parts) + "</table>")
        i += 1
    out.append("</body></html>")
    return "\n".join(out)


def main():
    LOGS.mkdir(parents=True, exist_ok=True)
    items = extract(ODT)
    (LOGS / "v7_content.json").write_text(
        json.dumps([{k: v for k, v in it.items() if k != "data"} for it in items],
                   ensure_ascii=False, indent=1), encoding="utf-8")
    lut, dumped = fig_lookup(items)
    html_src = render(items, lut)
    (LOGS / "tawafuq-art-v7-en.html").write_text(html_src, encoding="utf-8")
    from weasyprint import HTML
    HTML(string=html_src, base_url=str(ROOT / "docs/articles") + "/").write_pdf(str(OUT_PDF))
    print(f"images: {sum(1 for it in items if it['type']=='image')} "
          f"(hash-matched to figs/: {sum(1 for it in items if it['type']=='image') - dumped}, "
          f"embedded fallback: {dumped})")

    import pymupdf
    with pymupdf.open(OUT_PDF) as pdf:
        pages = len(pdf)
        text = " ".join(" ".join(p.get_text() for p in pdf).split())
        n_img = sum(len(p.get_images()) for p in pdf)
    assert "\ufffd" not in text, "replacement char in PDF text"
    phrases = ["72.65%", "P(X ≥ 3,522", "z = 62", "10^-814",
               "https://github.com/etemiz", "What this means for a Muslim",
               "For the first time, the visual claim",
               "Faithful polymaths for jumping to domains beyond faith",
               "For the first time, the visual claim behind that assertion",
               "Show another book that was written centuries ago",
               "Criticism and open questions", "verify_cpu.py"]
    missing = [p for p in phrases if p not in text]
    assert not missing, f"missing phrases: {missing}"
    assert "INSERT LINK HERE" not in text
    print(f"PDF OK: {pages} pages, {n_img} images drawn, no replacement chars, "
          f"{len(phrases)}/{len(phrases)} key phrases present")


if __name__ == "__main__":
    main()
