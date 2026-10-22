"""Inspect the user-supplied ODT reference and build the V3 article."""

import argparse
from fractions import Fraction
import hashlib
from html import escape
from html.parser import HTMLParser
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ARTICLE = ROOT / "docs/articles"
REFERENCE = ARTICLE / "tawafuq-art.odt"
REFERENCE_REVIEW = ROOT / "logs/article-v3-reference"
STEM = "tawafuq-v3-2026-10-19"
SOURCE = ARTICLE / f"{STEM}.md"
FIGS = ARTICLE / "figs/article-v3-2026-10-19"
REVIEW = ROOT / "logs/article-v3"
NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "draw": "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
    "xlink": "http://www.w3.org/1999/xlink",
}


def inspect_reference():
    REFERENCE_REVIEW.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(REFERENCE) as archive:
        files = archive.namelist()
        content = archive.read("content.xml")
        styles = archive.read("styles.xml")
        (REFERENCE_REVIEW / "content.xml").write_bytes(content)
        (REFERENCE_REVIEW / "styles.xml").write_bytes(styles)
        root = ET.fromstring(content)
        paragraphs = []
        for node in root.iter():
            if node.tag not in (f'{{{NS["text"]}}}p', f'{{{NS["text"]}}}h'):
                continue
            text = "".join(node.itertext())
            images = [n.get(f'{{{NS["xlink"]}}}href') for n in node.findall(".//draw:image", NS)]
            paragraphs.append(dict(kind=node.tag.split("}")[-1], text=text,
                                   attributes=node.attrib, images=images))
        pictures = []
        for filename in files:
            if filename.startswith("Pictures/") and not filename.endswith("/"):
                target = REFERENCE_REVIEW / Path(filename).name
                raw = archive.read(filename)
                target.write_bytes(raw)
                pictures.append(dict(archive_path=filename, extracted=target.name, bytes=len(raw)))
    lines = []
    for i, paragraph in enumerate(paragraphs, 1):
        style = paragraph["attributes"].get(f'{{{NS["text"]}}}style-name', "")
        lines.append(f'{i:03d} [{paragraph["kind"]}; {style}] {paragraph["text"]}')
        if paragraph["images"]:
            lines.append("    Images: " + ", ".join(paragraph["images"]))
    (REFERENCE_REVIEW / "reference.txt").write_text("\n".join(lines)+"\n")
    report = dict(reference=str(REFERENCE.relative_to(ROOT)),
                  sha256=hashlib.sha256(REFERENCE.read_bytes()).hexdigest(),
                  paragraphs=paragraphs, pictures=pictures,
                  archive_files=files)
    (REFERENCE_REVIEW / "reference.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
    print(f"Inspected {REFERENCE.relative_to(ROOT)}: {len(paragraphs)} paragraphs, {len(pictures)} pictures")
    print(f"Extracted reference: {(REFERENCE_REVIEW / 'reference.txt').relative_to(ROOT)}")


def inspect_example_pages():
    import broad_phrase_alignment as bp
    from semantic_validation import is_name
    canonical, words, _, _, _, _ = bp.load()
    report = {}
    for page in (62, 63, 82, 83):
        report[str(page)] = [dict(t=w["t"], word=w["word"], verse=canonical[w["t"]]["verse"],
                                  row=w["row"], center=w["x2"]/2, bbox=w["bbox"])
                             for w in words if w["page"] == page and is_name(canonical[w["t"]]["form"])]
    REFERENCE_REVIEW.mkdir(parents=True, exist_ok=True)
    (REFERENCE_REVIEW / "example-pages.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
    for page, rows in report.items():
        print(page, [(r["verse"], r["word"], r["center"], r["row"]) for r in rows])


def inspect_pagination():
    import pymupdf
    with pymupdf.open(ARTICLE/f"{STEM}.pdf") as document:
        for i,page in enumerate(document,1):
            lines=page.get_text().splitlines()
            print(i, " / ".join(lines[:3]), "...", " / ".join(lines[-5:-2]))


def svg_text(x, y, value, size=22, color="#204744", bold=False):
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" '
            f'font-weight="{"bold" if bold else "normal"}">{escape(str(value))}</text>')


def write_svg(name, width, height, body):
    (FIGS / name).write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}"><rect width="100%" height="100%" fill="white"/>'
        f'<g font-family="DejaVu Sans, sans-serif">{body}</g></svg>')


def figures(words, mapping, original, phrase_review):
    """Render from the frozen ledgers, preserving each scan's horizontal frame."""
    from PIL import Image, ImageDraw, ImageFont
    from build_findings_article import digest, require, read_json, DATA
    from image_io import open_rgb
    from semantic_validation import is_name
    import same_word_alignment as sw

    canonical, _ = sw.canonical_inventory()
    page_hashes = {p["page"]: p["image_sha256"] for p in mapping["pages"]}
    measured = original["views"]["conservative_v5"]
    saved_ends = {t for pair in measured["family_pair_token_ids"] for t in pair}
    font = ImageFont.load_default(size=33)
    provenance = []
    page_counts = {}
    source_rows = {}
    for page in (62, 63, 82, 83):
        rows = [dict(w, verse=canonical[w["t"]]["verse"]) for w in words
                if w["page"] == page and is_name(canonical[w["t"]]["form"])]
        ends = {r["t"] for r in rows for s in rows
                if r["row"] != s["row"] and abs(r["x2"]-s["x2"]) <= 30}
        require(ends == {r["t"] for r in rows if r["t"] in saved_ends}, "Illustration flags differ from ledger")
        source_rows[page] = rows
        page_counts[str(page)] = dict(mapped_family=len(rows), aligned_family=len(ends))
        path = ROOT / f"hayrat-pics/page_{page}.png"
        require(digest(path) == page_hashes[page], "Spread image hash differs")
        image = open_rgb(path)
        draw = ImageDraw.Draw(image)
        # Connected partner groups are illustration guides, not an all-pairs claim.
        remaining = {r["t"] for r in rows if r["t"] in ends}
        by_id = {r["t"]: r for r in rows}
        while remaining:
            group = {min(remaining)}
            while True:
                more = {t for t in remaining if any(by_id[t]["row"] != by_id[s]["row"]
                        and abs(by_id[t]["x2"]-by_id[s]["x2"]) <= 30 for s in group)}
                if more <= group:
                    break
                group |= more
            remaining -= group
            cx = round(sum(by_id[t]["x2"]/2 for t in group)/len(group))
            y0 = max(0, min(by_id[t]["bbox"][1] for t in group)-6)
            y1 = min(image.height, max(by_id[t]["bbox"][3] for t in group)+6)
            for y in range(y0, y1, 18):
                draw.line((cx, y, cx, min(y+8, y1)), fill="#7faed0", width=2)
        for row in rows:
            x0, y0, x1, y1 = row["bbox"]
            draw.rectangle((max(0,x0-4), max(0,y0-4), min(image.width-1,x1+4), min(image.height-1,y1+4)),
                           outline="#246eb1" if row["t"] in ends else "#8b9599", width=3)
        target = REVIEW / f"page-{page}-annotated.png"
        image.save(target)
        provenance.append(dict(page=page, source=f"hayrat-pics/{path.name}", source_sha256=digest(path),
                               occurrences=[dict(t=r["t"], verse=r["verse"], word=r["word"], bbox=r["bbox"],
                                                 row=r["row"], center=r["x2"]/2, aligned=r["t"] in ends) for r in rows]))
    right = source_rows[63]
    a = next(r for r in right if r["verse"] == "3:114" and r["word"] == "بالله")
    b = next(r for r in right if r["verse"] == "3:110" and r["word"] == "بالله")
    bottom = next(r for r in right if r["verse"] == "3:115" and r["word"] == "والله")
    require(abs(a["x2"]-b["x2"])/2 == 10.5 and a["t"] in saved_ends, "Lower reference word not accounted for")
    require(bottom["t"] not in saved_ends, "Bottom nonmatch status differs")
    for first, second in ((62,63), (82,83)):
        with Image.open(REVIEW / f"page-{first}-annotated.png") as a_image, Image.open(REVIEW / f"page-{second}-annotated.png") as b_image:
            out = Image.new("RGB", (a_image.width+b_image.width+34, max(a_image.height,b_image.height)+58), "white")
            out.paste(a_image, (0,58))
            out.paste(b_image, (a_image.width+34,58))
            draw = ImageDraw.Draw(out)
            draw.text((10,6), f"Hayrat page {first}", fill="#204744", font=font)
            draw.text((a_image.width+44,6), f"Hayrat page {second}", fill="#204744", font=font)
            out.save(FIGS / f"hayrat-spread-{first}-{second}.png")

    ordinary_panels = []
    for page, label in ((1,"GUIDANCE"), (2,"THEIR HEARTS")):
        example = next(e for e in phrase_review["lengths"]["1"]["examples"] if e["page"] == page)
        path = ROOT / f"hayrat-pics/page_{page}.png"
        require(digest(path) == example["image_sha256"], "Ordinary word source differs")
        image = open_rgb(path)
        boxes = [b for o in example["occurrences"] for b in o["boxes"]]
        left, right = max(0,min(b[0] for b in boxes)-85), min(image.width,max(b[2] for b in boxes)+85)
        scale = 900/(right-left)
        panels = []
        for o in example["occurrences"]:
            top, bottom_y = max(0,min(b[1] for b in o["boxes"])-12), min(image.height,max(b[3] for b in o["boxes"])+12)
            crop = image.crop((left,top,right,bottom_y)).resize((900,round((bottom_y-top)*scale)))
            panel = Image.new("RGB", (900,crop.height+50), "white")
            panel.paste(crop,(0,50))
            draw = ImageDraw.Draw(panel)
            draw.text((8,5), f"{label} / {o['verse']}", font=font, fill="#204744")
            for box in o["boxes"]:
                draw.rectangle(((box[0]-left)*scale,(box[1]-top)*scale+50,(box[2]-left)*scale,(box[3]-top)*scale+50),
                               outline="#246eb1",width=3)
            panels.append(panel)
        joined = Image.new("RGB", (900,sum(p.height for p in panels)+20), "white")
        y = 0
        for panel in panels:
            joined.paste(panel,(0,y)); y += panel.height+20
        ordinary_panels.append(joined)
        provenance.append(dict(page=page, source_sha256=digest(path), kind="ordinary_word_pair", example=example))
    ordinary = Image.new("RGB", (1840,max(p.height for p in ordinary_panels)), "white")
    for i,panel in enumerate(ordinary_panels):
        ordinary.paste(panel,(i*940,0))
    ordinary.save(FIGS / "ordinary-word-pairs.png")

    exact = read_json(DATA / "audit_exact_columns_raw_wordlike.json")
    excluded = set(map(int,exact["preprocessing_details"]["excluded_pages"]))
    require(len(excluded) == 17, "Coverage grid exclusions differ")
    body = svg_text(20,33,"604 input pages; 587 enter this component test",29,bold=True)
    for page in range(1,605):
        x,y = 20+((page-1)%40)*17, 58+((page-1)//40)*20
        body += f'<rect x="{x}" y="{y}" width="13" height="13" rx="2" fill="{"#d66b65" if page in excluded else "#298c7c"}"/>'
    body += svg_text(745,133,"587",55,"#17786c",True)+svg_text(745,170,"eligible pages",23)
    body += svg_text(745,245,"17",55,"#bd5b55",True)+svg_text(745,282,"no usable line grid",21)
    write_svg("page-coverage.svg",1100,390,body)

    values = [(n,phrase_review["lengths"][str(n)]["non_allah_aligned_distinct_types"]) for n in range(1,7)]
    require([v for _,v in values] == [580,396,171,75,30,13], "Phrase breadth differs")
    body = svg_text(20,30,"Distinct aligned word / phrase types",28,bold=True)
    for i,(length,count) in enumerate(values):
        y=58+i*45
        body += svg_text(20,y+19,"One word" if length==1 else f"{length}-word phrases",20)
        body += f'<rect x="235" y="{y}" width="{count/600*650}" height="24" rx="4" fill="#298c7c"/>'
        body += svg_text(245+count/600*650,y+20,count,20,bold=True)
    body += svg_text(20,358,"Excludes Allah-name-containing identities. Overlapping windows are not independent evidence.",17,"#5d7572")
    write_svg("phrase-breadth.svg",1100,380,body)

    events = [("Five-card royal flush",math.log10(649740)),
              ("6/49 lottery: one ticket",math.log10(math.comb(49,6))),
              ("100 fair coins: all heads",100*math.log10(2)),
              ("52 cards: one specified order",math.lgamma(53)/math.log(10)),
              ("1,000 fair coins: all heads",1000*math.log10(2)),
              ("Component model: certified bound",814)]
    body=svg_text(20,35,"A ruler of probability exponents",30,bold=True)
    for i,(label,value) in enumerate(events):
        y=72+i*61
        body += svg_text(20,y+21,label,21)
        body += f'<rect x="445" y="{y}" width="{max(1,value/850*550)}" height="27" fill="{"#cf3673" if i==5 else "#91a5a7"}"/>'
        body += svg_text(453+value/850*550,y+22,">814" if i==5 else f"{value:.2f}",20)
    body += '<line x1="445" y1="449" x2="995" y2="449" stroke="#576c70"/>'
    for tick in (0,100,200,400,600,800):
        x=445+tick/850*550
        body += f'<line x1="{x}" y1="449" x2="{x}" y2="457" stroke="#576c70"/>'
        body += svg_text(x-7,482,tick,17)
    body += svg_text(445,515,"−log10(probability): each +1 means 10 times less likely",18)
    body += svg_text(20,555,"The last bar is a conditional bound, not an authorship probability or a combined test.",18,"#5d7572")
    write_svg("log-probability-scale.svg",1100,575,body)
    report=dict(reference_sha256=digest(REFERENCE), sources=provenance, page_counts=page_counts,
                lower_billah_pair=dict(tokens=[a["t"],b["t"]],distance_pixels=10.5),
                bottom_wallah_nonmatch=bottom["t"], probability_scale=events,
                rights="Private working draft with Hayrat scan excerpts and project overlays; source-image rights are separate.")
    (FIGS / "sources.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    return report


class Fragment(HTMLParser):
    """Small HTML tree for exporting the same Markdown content to editable ODT."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = dict(tag="root",attrs={},children=[])
        self.stack = [self.root]

    def handle_starttag(self,tag,attrs):
        node=dict(tag=tag,attrs=dict(attrs),children=[])
        self.stack[-1]["children"].append(node)
        if tag not in ("img","br","hr","meta","link","input"):
            self.stack.append(node)

    def handle_startendtag(self,tag,attrs):
        self.handle_starttag(tag,attrs)
        if self.stack[-1]["tag"]==tag:
            self.stack.pop()

    def handle_endtag(self,tag):
        for i in range(len(self.stack)-1,0,-1):
            if self.stack[i]["tag"]==tag:
                del self.stack[i:]
                break

    def handle_data(self,data):
        self.stack[-1]["children"].append(data)


def node_text(node):
    return node if isinstance(node,str) else "".join(node_text(c) for c in node["children"])


def export_odt(parts,destination):
    from odf.opendocument import OpenDocumentText, load
    from odf import text, style, draw, table, dc, teletype
    from PIL import Image
    import pymupdf
    from build_findings_article import require
    document=OpenDocumentText()
    document.meta.addElement(dc.Title(text="How Unusual Are the Quran's Visual Alignments? — V3"))
    document.meta.addElement(dc.Creator(text="Emin Temiz; AI-assisted draft"))
    layout=style.PageLayout(name="A4Layout")
    layout.addElement(style.PageLayoutProperties(pagewidth="21cm",pageheight="29.7cm",margintop="1.6cm",marginbottom="1.6cm",marginleft="1.7cm",marginright="1.7cm"))
    document.automaticstyles.addElement(layout)
    master=style.MasterPage(name="Standard",pagelayoutname=layout)
    document.masterstyles.addElement(master)
    specifications={
        "Body":("10pt",False,None),"Title":("27pt",True,None),
        "Heading":("19pt",True,None),"NewPage":("19pt",True,"page"),
        "Subhead":("12pt",True,None),"Quote":("10pt",False,None),
        "Code":("8pt",False,None),"Bullet":("10pt",False,None),"Image":("9pt",False,None)}
    for name,(size,bold,break_before) in specifications.items():
        s=style.Style(name=name,family="paragraph")
        props=dict(marginbottom="0.18cm",lineheight="135%")
        if name in ("Title","Heading","NewPage","Subhead"):
            props["keepwithnext"]="always"
        if break_before:
            props["breakbefore"]=break_before
        if name=="Image":
            props["textalign"]="center"
        if name=="Bullet":
            props["marginleft"]="0.35cm"
        s.addElement(style.ParagraphProperties(**props))
        s.addElement(style.TextProperties(fontsize=size,fontfamily="DejaVu Sans Mono" if name=="Code" else "DejaVu Sans",fontweight="bold" if bold else "normal"))
        document.styles.addElement(s)
    for name,properties in (("Bold",dict(fontweight="bold")),("Italic",dict(fontstyle="italic")),("InlineCode",dict(fontfamily="DejaVu Sans Mono",fontsize="8.5pt"))):
        s=style.Style(name=name,family="text"); s.addElement(style.TextProperties(**properties)); document.styles.addElement(s)
    image_count=0

    def add_image(parent,node):
        nonlocal image_count
        path=(ARTICLE/node["attrs"]["src"]).resolve()
        require(path.is_relative_to(ARTICLE) and path.is_file(),"Invalid ODT image")
        if path.suffix==".svg":
            png=REVIEW/(path.stem+"-odt.png")
            with pymupdf.open(path) as svg_document:
                svg_document[0].get_pixmap(matrix=pymupdf.Matrix(1.6,1.6),alpha=False).save(png)
            path=png
        with Image.open(path) as im:
            width,height=im.size
        physical_width=17.3
        if "word-phrase" in path.name:
            physical_width=15.6
        frame=draw.Frame(name=f"Figure{image_count}",anchortype="as-char",width=f"{physical_width}cm",height=f"{physical_width*height/width:.4f}cm")
        href=document.addPicture(str(path))
        frame.addElement(draw.Image(href=href,type="simple",show="embed",actuate="onLoad"))
        parent.addElement(frame); image_count+=1

    def inline(parent,node):
        if isinstance(node,str):
            teletype.addTextToElement(parent,node)
            return
        tag=node["tag"]
        if tag=="img":
            add_image(parent,node); return
        if tag=="br":
            parent.addElement(text.LineBreak()); return
        if tag=="a":
            child=text.A(href=node["attrs"].get("href",""))
        elif tag in ("strong","b","em","i","code"):
            child=text.Span(stylename="Bold" if tag in ("strong","b") else "Italic" if tag in ("em","i") else "InlineCode")
        else:
            child=text.Span()
        for item in node["children"]:
            inline(child,item)
        parent.addElement(child)

    table_count=0
    def blocks(parent,node,first=False):
        nonlocal table_count
        if isinstance(node,str):
            if node.strip():
                parent.addElement(text.P(stylename="Body",text=node))
            return
        tag=node["tag"]
        if tag in ("h1","h2","h3","h4"):
            name="Title" if tag=="h1" else "NewPage" if first else "Heading" if tag=="h2" else "Subhead"
            p=text.H(outlinelevel=int(tag[1]),stylename=name)
            for item in node["children"]: inline(p,item)
            parent.addElement(p)
        elif tag in ("p","li"):
            is_image=any(isinstance(c,dict) and c["tag"]=="img" for c in node["children"])
            p=text.P(stylename="Image" if is_image else "Bullet" if tag=="li" else "Body")
            if tag=="li": teletype.addTextToElement(p,"• ")
            for item in node["children"]: inline(p,item)
            parent.addElement(p)
        elif tag=="pre":
            for line in node_text(node).splitlines():
                p=text.P(stylename="Code"); teletype.addTextToElement(p,line); parent.addElement(p)
        elif tag=="table":
            out=table.Table(name=f"Table{table_count}"); table_count+=1
            def rows(n):
                return [n] if isinstance(n,dict) and n["tag"]=="tr" else [r for c in n.get("children",[]) if isinstance(c,dict) for r in rows(c)]
            for row in rows(node):
                r=table.TableRow()
                for cell in row["children"]:
                    if not isinstance(cell,dict) or cell["tag"] not in ("td","th"): continue
                    c=table.TableCell(valuetype="string"); p=text.P(stylename="Body")
                    for item in cell["children"]: inline(p,item)
                    c.addElement(p); r.addElement(c)
                out.addElement(r)
            parent.addElement(out)
        elif tag=="blockquote":
            for c in node["children"]:
                if isinstance(c,dict) and c["tag"]=="p":
                    p=text.P(stylename="Quote")
                    for item in c["children"]: inline(p,item)
                    parent.addElement(p)
        else:
            for child in node["children"]: blocks(parent,child)
    for part in parts:
        fragment=Fragment(); fragment.feed(part)
        first=True
        for node in fragment.root["children"]:
            if isinstance(node,str) and not node.strip(): continue
            blocks(document.text,node,first=first); first=False
    document.save(str(destination),addsuffix=False)
    load(str(destination))
    with zipfile.ZipFile(destination) as archive:
        require(archive.read("mimetype")==b"application/vnd.oasis.opendocument.text","Invalid ODT mimetype")
        root=ET.fromstring(archive.read("content.xml"))
        recovered=" ".join(" ".join(root.itertext()).split())
        for phrase in ("10⁻⁸¹⁴","10⁻⁵⁷","Emin Temiz","Türkçe özet","3,522","36.96%"):
            require(phrase in recovered,f"Missing ODT content: {phrase}")
        for image in root.findall(".//draw:image",NS):
            require(image.get(f'{{{NS["xlink"]}}}href') in archive.namelist(),"ODT image not embedded")
        expected=[]
        for part in parts:
            fragment=Fragment(); fragment.feed(part); expected.append(node_text(fragment.root))
        canonical=lambda value: re.sub(r"\s+","",value).replace("•","")
        require(canonical("".join(expected))==canonical(recovered),"ODT export lost or altered article text")
        page_headings=[h for h in root.findall(".//text:h",NS)
                       if h.get(f'{{{NS["text"]}}}style-name')=="NewPage"]
        require(len(page_headings)==len(parts)-1,"ODT section/page-break structure differs")
    return dict(embedded_images=image_count,structure_checked=True,full_text_roundtrip_checked=True,
                visual_office_render_checked=False)


CSS="""
@page {size:A4;margin:15mm 17mm 16mm;
 @bottom-left {content:'TAWAFUQ / V3 / PRIVATE WORKING DRAFT';font:7pt 'DejaVu Sans';color:#63807b}
 @bottom-right {content:counter(page) ' / ' counter(pages);font:8pt 'DejaVu Sans';color:#63807b}}
body {margin:0;background:#e7efeb;color:#233b3b;font:16px/1.48 'DejaVu Sans',sans-serif}
.sheet {max-width:900px;margin:24px auto;padding:42px 56px;background:white}
.eyebrow {color:#17786c;text-transform:uppercase;letter-spacing:1.4px;font-size:10px;margin-bottom:14px}
h1,h2,h3 {color:#14544b;line-height:1.17;break-after:avoid}
h1 {font-size:40px;letter-spacing:-1.2px;margin:0 0 15px}h2 {font-size:29px;margin:0 0 16px}h3 {font-size:18px;margin:15px 0 8px}
p {margin:10px 0;orphans:3;widows:3}a {color:#17786c;text-decoration:none}
img {display:block;width:100%;height:auto}p:has(>img) {break-inside:avoid;margin:14px 0}
img[src$="word-phrase.png"] {width:88%;margin:auto}
img[src$="page-coverage.svg"] {width:92%;margin:auto}
blockquote {margin:15px 0;padding:11px 15px;background:#edf4f1;border-left:4px solid #b48842;break-inside:avoid}
blockquote p {margin:3px 0}code {font-family:'DejaVu Sans Mono';font-size:.86em;overflow-wrap:anywhere}
pre {white-space:pre-wrap;padding:10px;background:#edf4f1;font-size:11px;line-height:1.4;break-inside:avoid}
table {width:100%;border-collapse:collapse;margin:13px 0;font-size:12px;break-inside:avoid}
td,th {padding:7px 6px;border-bottom:1px solid #d7e4dd;text-align:left;vertical-align:top}th {background:#e9f1ec}
ul,ol {padding-left:22px}li {margin:5px 0}
@media print {body {background:white;font-size:9.8pt;line-height:1.43}
 .sheet {margin:0;padding:0;max-width:none;break-after:page}.sheet:last-child {break-after:auto}
 .eyebrow {font-size:7.2pt;margin-bottom:11px}h1 {font-size:28pt}h2 {font-size:20pt}h3 {font-size:11.7pt}
 p {margin:8px 0}pre {font-size:7.6pt;line-height:1.35}table {font-size:8pt}td,th {padding:6px 5px}
 .math {font-size:9.2pt;line-height:1.38}.math pre {font-size:7.5pt}.sources {font-size:8.5pt;line-height:1.4}}
"""


def build():
    import markdown
    import pymupdf
    from PIL import Image
    from weasyprint import HTML
    import broad_phrase_alignment as bp
    from build_findings_article import DATA, Resources, check_component_bound, check_numbers, digest, read_json, require
    from build_layman_article import infographics
    FIGS.mkdir(parents=True,exist_ok=True); REVIEW.mkdir(parents=True,exist_ok=True)
    if not (REFERENCE_REVIEW/"reference.json").exists(): inspect_reference()
    reference=read_json(REFERENCE_REVIEW/"reference.json")
    require(reference["sha256"]==digest(REFERENCE),"The reference ODT changed; inspect it again")
    source=SOURCE.read_text()
    component_inputs,component_summary=check_component_bound((ARTICLE/"tawafuq-findings-2026-10-19.md").read_text())
    table_inputs,_,_=check_numbers((ARTICLE/"tawafuq-findings-2026-10-19.md").read_text())
    exp_lower=sum((Fraction(2303,1000)**j/Fraction(math.factorial(j))) for j in range(31))
    require(exp_lower>10,"Rational ln(10) certificate fails")
    require(Fraction(2*921**2,12895)>57*Fraction(2303,1000),"Word-bound decimal exponent check fails")
    canonical,words,mapping,original,_,_=bp.load()
    phrase_review=read_json(DATA/"research_broad_phrase_review_v1.json")
    # Reuse the data-derived, private-draft infographic family consistently.
    infographics(component_summary,original["views"]["conservative_v5"],580)
    figure_report=figures(words,mapping,original,phrase_review)
    for phrase in ("10⁻⁸¹⁴","10⁻⁵⁷","3,522","4,682","76,375","75.22%","25.24%","1,717/2,151","36.96%","Türkçe özet"):
        require(phrase in source,f"Principal claim absent from V3: {phrase}")
    parts=source.split("<!-- page -->")
    require(len(parts)==17,"V3 should contain 17 designed pages")
    rendered=[markdown.markdown(part,extensions=["tables","fenced_code"]) for part in parts]
    sections=[]
    for i,content in enumerate(rendered,1):
        classes="sheet math" if i in (8,9) else "sheet sources" if i==17 else "sheet"
        sections.append(f'<section class="{classes}"><div class="eyebrow">V3 · 19 October 2026 · {i:02d}</div>{content}</section>')
    document=('<!doctype html><html lang="en"><head><meta charset="utf-8">'
              '<meta name="author" content="Emin Temiz; AI-assisted draft">'
              '<title>How Unusual Are the Quran’s Visual Alignments? — V3</title>'
              f'<style>{CSS}</style></head><body>'+"\n".join(sections)+'</body></html>')
    resources=Resources(); resources.feed(document)
    html=REVIEW/f"{STEM}.html"; pdf_path=ARTICLE/f"{STEM}.pdf"; odt_path=ARTICLE/f"{STEM}.odt"
    html.write_text(document)
    HTML(filename=str(html),base_url=ARTICLE.as_uri()+"/").write_pdf(pdf_path)
    with pymupdf.open(pdf_path) as pdf:
        require(len(pdf)==17,f"Expected 17 PDF pages, got {len(pdf)}; inspect overflow")
        extracted=" ".join(" ".join(p.get_text() for p in pdf).split())
        for phrase in ("10⁻⁸¹⁴","10⁻⁵⁷","3,522","75.22%","36.96%","Türkçe özet","Conclusion for AI consumption"):
            require(phrase in extracted,f"Missing PDF content: {phrase}")
        require("\ufffd" not in extracted,"Replacement character in PDF")
        thumbs=[]
        for i,page in enumerate(pdf,1):
            for block in page.get_text("dict")["blocks"]:
                require(page.rect.contains(pymupdf.Rect(block["bbox"])),f"Clipped PDF content on page {i}")
            path=REVIEW/f"page-{i:02d}.png"; page.get_pixmap(dpi=110).save(path)
            with Image.open(path) as raw: thumb=raw.copy()
            thumb.thumbnail((330,470)); thumbs.append(thumb)
        sheet=Image.new("RGB",(4*350,math.ceil(len(thumbs)/4)*495),"#dce7e1")
        for i,thumb in enumerate(thumbs): sheet.paste(thumb,(10+(i%4)*350,10+(i//4)*495))
        sheet.save(REVIEW/"contact-sheet.png")
    odt_report=export_odt(rendered,odt_path)
    require(digest(REFERENCE)==reference["sha256"],"Reference ODT was modified")
    inputs=dict(component_inputs,**table_inputs)
    manifest=dict(source_sha256=digest(SOURCE),builder_sha256=digest(Path(__file__)),reference_sha256=digest(REFERENCE),
                  evidence_inputs=inputs,component_certificate=component_summary,
                  figure_sources_sha256=digest(FIGS/"sources.json"),page_counts=figure_report["page_counts"],
                  assets={p.name:digest(p) for p in resources.images},pdf_sha256=digest(pdf_path),
                  odt_sha256=digest(odt_path),odt=odt_report,pdf_pages=17,
                  infographic_count=sum(p.suffix==".svg" for p in resources.images),
                  word_decimal_arithmetic_checks=True)
    (REVIEW/"build-manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print(f"Built {pdf_path.relative_to(ROOT)}: 17 pages")
    print(f"Built {odt_path.relative_to(ROOT)}: {odt_report['embedded_images']} embedded figures")
    print(f"Review: {(REVIEW/'contact-sheet.png').relative_to(ROOT)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inspect-reference", action="store_true")
    parser.add_argument("--inspect-example-pages", action="store_true")
    parser.add_argument("--inspect-pagination", action="store_true")
    args = parser.parse_args()
    if args.inspect_reference:
        inspect_reference()
    elif args.inspect_example_pages:
        inspect_example_pages()
    elif args.inspect_pagination:
        inspect_pagination()
    else:
        build()
