"""Acquire and OCR the fixed second historical copy; scan-free review replay.

Raw source metadata, images and GPU OCR stay in logs. Derived manifests and
manual measurements live in tools/data. Run GPU mode in .venv/ocr.
"""

import argparse
from collections import defaultdict
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
from itertools import combinations
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "tools/data"
PLAN = DATA / "research_historical_extension_plan_v1.json"
SOURCES = DATA / "research_historical_extension_sources_v1.json"
LABELS = DATA / "research_historical_extension_annotations_v1.json"
FIRST_REVIEW = DATA / "research_historical_extension_review_v1.json"
OUTPUT = DATA / "research_historical_extension_review_v2.json"
OCR_ARCHIVE = DATA / "research_historical_extension_ocr_v1.json"
OUT = ROOT / "logs/historical-extension-ms-or-91-v1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_new(path, report):
    if path.exists():
        if json.loads(path.read_text()) != report:
            raise ValueError(f"Frozen artifact differs: {path.name}")
    else:
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")


def acquire():
    from PIL import Image, ImageDraw
    plan = json.loads(PLAN.read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    item = plan["source"]["internet_archive"]
    files = []

    def fetch(url, name, **details):
        path = OUT / name
        if not path.exists():
            request = urllib.request.Request(url, headers={"User-Agent":"tawafuq-historical-research/1.0"})
            with urllib.request.urlopen(request, timeout=60) as response:
                data = response.read()
            path.write_bytes(data)
        files.append(dict(file=name, url=url, sha256=sha(path), bytes=path.stat().st_size, **details))
        print("Cached", name, path.stat().st_size, flush=True)
        return path

    metadata = fetch(f"https://archive.org/metadata/{item}/metadata", "metadata.json")
    fetch(f"https://archive.org/download/{item}/{item}_scandata.xml", "scandata.xml")
    for folio, n in zip(plan["selection"]["folios"]+[plan["selection"]["colophon"]],
                        plan["selection"]["ia_page_n_candidates"]):
        path = fetch(f"https://archive.org/download/{item}/page/n{n}.jpg", f"folio-{folio}.jpg",
                     target_folio=folio, ia_page_n=n, correspondence="provisional pending visual reading")
        with Image.open(path) as raw:
            image = raw.convert("RGB")
            image = image.resize((1000, round(image.height*1000/image.width)))
        image.save(OUT / f"review-{folio}.jpg")
        ruler = image.copy()
        draw = ImageDraw.Draw(ruler)
        for x in range(0,1000,25):
            draw.line((x,0,x,ruler.height), fill=(100,180,210))
            if x%50 == 0:
                for y in range(0,ruler.height,400):
                    draw.text((x+1,y+3),str(x), fill="blue")
        for y in range(0,ruler.height,100):
            draw.text((1,y),str(y), fill="blue")
        ruler.save(OUT / f"ruler-{folio}.png")
    meta = json.loads(metadata.read_text())["result"]
    report = dict(study=plan["study"], plan_sha256=sha(PLAN), files=files,
                  catalogue=dict(title=meta["title"], date=meta["date"],
                                 description=meta["description"], imagecount=meta["imagecount"]),
                  authority="Columbia catalogue metadata mirrored by IA/OPenn, not independent dating replication")
    save_new(SOURCES, report)


def ocr():
    if not os.environ.get("CUDA_VISIBLE_DEVICES", "").startswith("GPU-"):
        raise ValueError("Select CUDA_VISIBLE_DEVICES using a GPU UUID")
    sources=json.loads(SOURCES.read_text())
    image_sources=[s for s in sources["files"] if "target_folio" in s]
    if (OUT/"ocr-metadata.json").exists() and all((OUT/f'ocr-{s["target_folio"]}.json').exists() for s in image_sources):
        for source in image_sources:
            cached=json.loads((OUT/f'ocr-{source["target_folio"]}.json').read_text())
            if cached["image_sha256"]!=source["sha256"] or sha(OUT/source["file"])!=source["sha256"]:
                raise ValueError("Cached OCR image hash differs")
        print("All OCR pages cached; preserving original raw results and metadata")
        return
    os.environ.setdefault("MODEL_CACHE_DIR", str(ROOT / "logs/ocr-models"))
    os.environ.setdefault("HF_HOME", str(ROOT / "logs/huggingface"))
    os.environ.setdefault("TORCH_DEVICE", "cuda")
    os.environ.setdefault("RECOGNITION_BATCH_SIZE", "4")
    os.environ.setdefault("DETECTOR_BATCH_SIZE", "1")
    os.environ.setdefault("FOUNDATION_MAX_TOKENS", "768")
    import torch
    from PIL import Image
    from surya.foundation import FoundationPredictor
    from surya.recognition import RecognitionPredictor
    from surya.detection import DetectionPredictor
    torch.set_num_threads(4)
    torch.cuda.set_per_process_memory_fraction(.18)
    sources = json.loads(SOURCES.read_text())
    recognizer = RecognitionPredictor(FoundationPredictor())
    detector = DetectionPredictor()
    reports = []
    for source in sources["files"]:
        if "target_folio" not in source:
            continue
        folio = source["target_folio"]
        destination = OUT / f"ocr-{folio}.json"
        path = OUT/source["file"]
        if sha(path) != source["sha256"]:
            raise ValueError("Image changed")
        if destination.exists():
            cached = json.loads(destination.read_text())
            if cached["image_sha256"] != source["sha256"]:
                raise ValueError("OCR cache source mismatch")
            reports.append(dict(folio=folio, cached=True))
            continue
        with Image.open(path) as raw:
            image = raw.convert("RGB")
            original_size = list(image.size)
            scale = min(1,2400/image.height)
            image = image.resize((round(image.width*scale),round(image.height*scale)))
        start = time.perf_counter()
        result = recognizer([image], det_predictor=detector, math_mode=False, return_words=True)[0]
        report = dict(folio=folio, image_sha256=source["sha256"], original_size=original_size,
                      ocr_size=list(image.size), elapsed_seconds=time.perf_counter()-start,
                      result=result.model_dump(), source_sha256=sha(Path(__file__)),
                      status="Unvalidated OCR hypotheses, not independent transcription")
        destination.write_text(json.dumps(report,ensure_ascii=False,indent=1)+"\n")
        reports.append(dict(folio=folio, lines=len(result.text_lines), seconds=report["elapsed_seconds"]))
        for line in report["result"]["text_lines"]:
            print(folio, line["text"], flush=True)
        print("Completed", folio, reports[-1], flush=True)
    metadata = dict(engine="surya-ocr", packages={p:importlib.metadata.version(p) for p in
                    ("surya-ocr","torch","transformers","pillow")}, gpu=torch.cuda.get_device_name(),
                    source_sha256=sha(Path(__file__)), sources_sha256=sha(SOURCES), pages=reports,
                    peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                    model_files={str(p.relative_to(ROOT/"logs/ocr-models")):sha(p)
                                 for p in sorted((ROOT/"logs/ocr-models").rglob("*")) if p.is_file()})
    save_new(OUT/"ocr-metadata.json",metadata)


def page_inventory(canonical, page):
    first = [r for r in canonical.values() if r["verse"] == page["first_verse"]]
    last = [r for r in canonical.values() if r["verse"] == page["last_verse"]]
    first_word = page["first_word"]
    last_word = len(last) if page["last_word"] is None else page["last_word"]
    if not 1 <= first_word <= len(first) or not 1 <= last_word <= len(last):
        raise ValueError("Invalid canonical word boundary")
    start = first[first_word-1]["t"]
    stop = last[last_word-1]["t"]
    if start > stop:
        raise ValueError("Reversed canonical page boundaries")
    return {t:r for t,r in canonical.items() if start <= t <= stop}


def inventory():
    import same_word_alignment as sw
    from semantic_validation import is_name
    canonical,_ = sw.canonical_inventory()
    for page in json.loads(LABELS.read_text())["pages"]:
        print("FOLIO",page["folio"])
        for verse in (page["first_verse"],page["last_verse"]):
            words = [r["word"] for r in canonical.values() if r["verse"] == verse]
            print(verse, " ".join(f"{i+1}:{w}" for i,w in enumerate(words)))
        names = defaultdict(list)
        for r in canonical.values():
            if is_name(r["form"]):
                names[r["verse"]].append(r)
        for row in page_inventory(canonical,page).values():
            if is_name(row["form"]):
                print(row["t"],row["verse"],names[row["verse"]].index(row)+1,row["word"])


def phrase_windows(canonical, verse, words):
    rows = [r for r in canonical.values() if r["verse"] == verse]
    return [rows[i:i+len(words)] for i in range(len(rows)-len(words)+1)
            if [r["word"] for r in rows[i:i+len(words)]] == words]


def ocr_summary():
    from semantic_validation import is_name
    import same_word_alignment as sw
    plan = json.loads(PLAN.read_text())
    reports = []
    for folio in plan["selection"]["folios"]+[plan["selection"]["colophon"]]:
        path = OUT/f"ocr-{folio}.json"
        raw = json.loads(path.read_text())
        counts = [sum(is_name(sw.mt.norm(w)) for w in line["text"].split())
                  for line in raw["result"]["text_lines"]]
        reports.append(dict(folio=folio, raw_sha256=sha(path), lines=len(counts),
                            raw_text_name_family_mentions=sum(counts),
                            high_repetition_line_flags=[dict(line_index=i,bbox=raw["result"]["text_lines"][i]["bbox"],
                                                             raw_name_mentions=n)
                                                        for i,n in enumerate(counts) if n>=10],
                            image_sha256=raw["image_sha256"],original_size=raw["original_size"],
                            ocr_size=raw["ocr_size"],elapsed_seconds=raw["elapsed_seconds"]))
    metadata = json.loads((OUT/"ocr-metadata.json").read_text())
    return dict(engine=metadata["engine"],packages=metadata["packages"],gpu=metadata["gpu"],
                peak_allocated_bytes=metadata["peak_allocated_bytes"],
                model_files=metadata["model_files"],pages=reports,
                caveat="Text-mention counts are raw OCR outputs, NOT a name census, precision or recall. A repetition loop on 165r fabricates many Allah mentions in a name-free line. All scoring uses scan-checked canonical manual names instead.")


def analyze():
    import historical_copy_analysis as old
    import historical_center_review as shared
    import same_word_alignment as sw
    from semantic_validation import is_name
    labels = json.loads(LABELS.read_text())
    plan = json.loads(PLAN.read_text())
    sources = json.loads(SOURCES.read_text())
    canonical,_ = sw.canonical_inventory()
    if [p["folio"] for p in labels["pages"]] != plan["selection"]["folios"]:
        raise ValueError("Frozen folio selection changed")
    by_verse = defaultdict(list)
    for row in canonical.values():
        if is_name(row["form"]):
            by_verse[row["verse"]].append(row)
    historical, pages, seen = [], [], set()
    for page in labels["pages"]:
        corpus = page_inventory(canonical,page)
        expected = {t for t,r in corpus.items() if is_name(r["form"])}
        found = set()
        frame_left,frame_right = page["frame"]
        if not 0 <= frame_left < frame_right <= 1000 or frame_right-frame_left <= 6:
            raise ValueError("Invalid verse-text frame")
        for verse,ordinal,word,physical_row,left,right in page["names"]:
            if not 1 <= ordinal <= len(by_verse[verse]):
                raise ValueError("Invalid canonical name ordinal")
            truth=by_verse[verse][ordinal-1]
            t=truth["t"]
            if t not in expected or t in found or t in seen or truth["word"]!=word:
                raise ValueError(f'Canonical name mismatch or duplicate: {page["folio"]} {verse} {ordinal} {word} vs {truth}; in span={t in expected}')
            if not isinstance(physical_row,int) or not 1 <= physical_row <= 18:
                raise ValueError("Invalid physical row")
            if not frame_left <= left < right <= frame_right:
                raise ValueError("Body interval outside manual frame")
            found.add(t)
            seen.add(t)
            historical.append(dict(t=t,word=word,verse=verse,page=page["folio"],row=physical_row,
                                   center=(left+right)/2,frame_width=frame_right-frame_left))
        if found != expected:
            raise ValueError(f'Incomplete name inventory on {page["folio"]}: {sorted(expected-found)}')
        pages.append(dict(folio=page["folio"],canonical_token_span=[min(corpus),max(corpus)],
                          first_token=corpus[min(corpus)],last_token=corpus[max(corpus)],
                          canonical_name_count=len(expected),inventory_complete=True,
                          boundary_note=page.get("boundary_note")))
    modern_raw=json.loads(old.MODERN.read_text())["views"]["conservative_v5"]["located_inventory"]
    lookup={r[0]:r for r in modern_raw}
    extents=defaultdict(list)
    for _,pg,_,x2,width in modern_raw:
        extents[pg].extend(((x2-width)/2,(x2+width)/2))
    modern=[]
    for row in historical:
        if row["t"] in lookup:
            _,pg,physical_row,x2,_=lookup[row["t"]]
            modern.append(dict(t=row["t"],word=row["word"],page=pg,row=physical_row,
                               center=x2/2,frame_width=max(extents[pg])-min(extents[pg])))
    scores={}
    for tolerance in (0.02,0.015):
        scores[str(tolerance)]={}
        for group,standalone in (("allah_name_family",False),("standalone_allah",True)):
            scores[str(tolerance)][group]=dict(historical=old.bounds(historical,tolerance,5,3,standalone),
                                                modern_ledger_context_only=old.bounds(modern,tolerance,standalone=standalone))
    phrase_reports=[]
    for candidate in labels["phrase_candidates"]:
        page=next(p for p in labels["pages"] if p["folio"]==candidate["folio"])
        corpus=page_inventory(canonical,page)
        words=candidate["canonical_words"]
        expected=[]
        for verse in dict.fromkeys(r["verse"] for r in corpus.values()):
            for window in phrase_windows(canonical,verse,words):
                if all(r["t"] in corpus for r in window):
                    expected.append(window[0]["t"])
        occurrences=[]
        for occurrence in candidate["occurrences"]:
            windows=phrase_windows(canonical,occurrence["verse"],words)
            ordinal=occurrence["phrase_ordinal_in_verse"]
            if not 1 <= ordinal <= len(windows) or len(occurrence["bodies"])!=len(words):
                raise ValueError("Phrase identity or measurement length differs")
            window=windows[ordinal-1]
            rows=[]
            for truth,(left,right) in zip(window,occurrence["bodies"]):
                if truth["t"] not in corpus or not page["frame"][0]<=left<right<=page["frame"][1]:
                    raise ValueError("Phrase body/identity outside page")
                rows.append(dict(t=truth["t"],word=truth["word"],page=page["folio"],row=occurrence["row"],
                                 center=(left+right)/2,frame_width=page["frame"][1]-page["frame"][0]))
            occurrences.append(rows)
        accounted=[rows[0]["t"] for rows in occurrences]
        other=candidate.get("other_in_page_occurrence")
        if other:
            unmeasured=phrase_windows(canonical,other["verse"],words)
            if len(unmeasured)!=1:
                raise ValueError("Ambiguous unmeasured phrase instance")
            accounted.append(unmeasured[0][0]["t"])
        if sorted(accounted)!=sorted(expected):
            raise ValueError(f'Incomplete repeated phrase accounting: {candidate["id"]}; expected {expected}, annotated {accounted}')
        pairs=[]
        for i,j in combinations(range(len(occurrences)),2):
            pairs.append(dict(occurrences=[i,j],scores={str(tau):shared.phrase_bounds(occurrences[i],occurrences[j],tau)
                                                      for tau in (0.02,0.015)}))
        phrase_reports.append(dict(id=candidate["id"],display=candidate["display"],folio=candidate["folio"],
                                   all_in_page_canonical_occurrence_starts=sorted(expected),
                                   measured_occurrences=occurrences,unmeasured=other,pairs=pairs,
                                   status="Post-hoc case search on the fixed pages, not a prevalence/significance estimate"))
    page_scores={p["folio"]:old.bounds([r for r in historical if r["page"]==p["folio"]],.02,5,3) for p in labels["pages"]}
    archived_ocr=json.loads(OCR_ARCHIVE.read_text())
    if archived_ocr["first_review_sha256"] != sha(FIRST_REVIEW):
        raise ValueError("First measured review changed")
    paths=[PLAN,SOURCES,LABELS,old.MODERN,sw.mt.TOKENS_F,Path(__file__),Path(old.__file__),Path(shared.__file__),Path(sw.__file__),OCR_ARCHIVE,FIRST_REVIEW,
           DATA/"research_historical_extension_colophon_amendment_v1.json",DATA/"research_historical_extension_colophon_source_v1.json"]
    report=dict(study=plan["study"],inputs={p.name:sha(p) for p in paths},pages=pages,
                scores=scores,page_scores=page_scores,historical_occurrences=historical,
                modern_ledger_context_only=modern,modern_unresolved=sorted(seen-set(r["t"] for r in modern)),
                phrases=phrase_reports,ocr=archived_ocr["summary"],colophon=labels["colophon"],
                source_authority=sources["authority"],inference=plan["inference"],
                compatibility="Different hand, 18-line rather than prior 15-line manuscript. Both catalogues label the script naskh. No quantitative claim of a modern-like historical rate or hidden style-normalized miracle follows automatically.")
    first=json.loads(FIRST_REVIEW.read_text())
    if {k:v for k,v in report.items() if k!="inputs"} != {k:v for k,v in first.items() if k!="inputs"}:
        raise ValueError("Portability-only revision changed a scientific outcome")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--acquire", action="store_true")
    parser.add_argument("--ocr", action="store_true")
    parser.add_argument("--verify-sources", action="store_true")
    parser.add_argument("--inventory", action="store_true")
    parser.add_argument("--colophon-candidate", action="store_true")
    parser.add_argument("--case-sheets", action="store_true")
    parser.add_argument("--analyze", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--archive-ocr", action="store_true")
    parser.add_argument("--verify-ocr", action="store_true")
    args = parser.parse_args()
    if args.acquire:
        acquire()
    elif args.archive_ocr:
        summary=ocr_summary()
        if summary!=json.loads(FIRST_REVIEW.read_text())["ocr"]:
            raise ValueError("OCR summary differs from first measured review")
        save_new(OCR_ARCHIVE,dict(first_review_sha256=sha(FIRST_REVIEW),summary=summary,
                 amendment="Post-score portability repair only. First v1 analysis read raw OCR from ignored logs; v2 reconstructs every scientific outcome unchanged from this archived summary, requiring no scans, model weights or local OCR cache. Original v1 retained."))
        print("Archived OCR summary for portable replay")
    elif args.verify_ocr:
        if ocr_summary()!=json.loads(OCR_ARCHIVE.read_text())["summary"]:
            raise ValueError("Raw local OCR cache differs from archive")
        print("Local OCR hashes and summary match archive")
    elif args.case_sheets:
        from PIL import Image, ImageDraw
        with Image.open(OUT/"folio-99r.jpg") as raw:
            image = raw.convert("RGB")
            image = image.resize((1000,round(image.height*1000/image.width)))
        sheet = Image.new("RGB",(600,460),"white")
        draw = ImageDraw.Draw(sheet)
        for i, (row, top) in enumerate(((4,501),(8,766))):
            crop = image.crop((315,top,515,top+65)).resize((600,195))
            sheet.paste(crop,(0,i*230+35))
            draw.text((5,i*230),f"99r physical row {row}; original x coordinates",fill="black")
            for x in range(325,515,25):
                sx=(x-315)*3
                draw.text((sx,i*230+15),str(x),fill="blue")
                draw.line((sx,i*230+35,sx,i*230+230),fill=(100,180,210))
        sheet.save(OUT/"case-99r-rows-4-8.png")
        with Image.open(OUT/"colophon-candidate-n398.jpg") as raw:
            image=raw.convert("RGB")
            image=image.resize((1000,round(image.height*1000/image.width)))
            image.crop((300,330,870,730)).resize((1140,800)).save(OUT/"colophon-date-detail.jpg")
        print("Saved raw-context phrase and colophon details")
    elif args.colophon_candidate:
        from PIL import Image
        amendment = DATA/"research_historical_extension_colophon_amendment_v1.json"
        plan = json.loads(PLAN.read_text())
        n = json.loads(amendment.read_text())["candidate_n"]
        url = f'https://archive.org/download/{plan["source"]["internet_archive"]}/page/n{n}.jpg'
        path = OUT/f"colophon-candidate-n{n}.jpg"
        if not path.exists():
            with urllib.request.urlopen(url,timeout=60) as response:
                path.write_bytes(response.read())
        with Image.open(path) as raw:
            image = raw.convert("RGB")
            image.resize((1000,round(image.height*1000/image.width))).save(OUT/f"review-colophon-n{n}.jpg")
        save_new(DATA/"research_historical_extension_colophon_source_v1.json",
                 dict(amendment_sha256=sha(amendment),url=url,file=path.name,
                      sha256=sha(path),bytes=path.stat().st_size))
        print("Saved provisional colophon candidate",n)
    elif args.analyze or args.verify:
        report=analyze()
        if args.verify:
            if json.loads(OUTPUT.read_text())!=report:
                raise ValueError("Historical extension deterministic replay differs")
            print("Historical extension scan-free replay passed")
        else:
            save_new(OUTPUT,report)
        for tau,groups in report["scores"].items():
            print(tau,{g:{c:[s["guaranteed_aligned"],s["midpoint_aligned"],s["possibly_aligned"],s["occurrences"]]
                          for c,s in copies.items()} for g,copies in groups.items()})
        for page in report["pages"]:
            s=report["page_scores"][page["folio"]]
            print(page["folio"],page["canonical_name_count"],s["midpoint_aligned"],s["guaranteed_aligned"])
        for candidate in report["phrases"]:
            print(candidate["id"],[(p["occurrences"],p["scores"]["0.02"]["midpoint_phrase_match"]) for p in candidate["pairs"]])
    elif args.ocr:
        ocr()
    elif args.inventory:
        inventory()
    elif args.verify_sources:
        manifest = json.loads(SOURCES.read_text())
        if manifest["plan_sha256"] != sha(PLAN):
            raise ValueError("Plan hash changed")
        for item in manifest["files"]:
            path = OUT/item["file"]
            if sha(path) != item["sha256"] or path.stat().st_size != item["bytes"]:
                raise ValueError(f'Acquisition changed: {item["file"]}')
        correction=json.loads((DATA/"research_historical_extension_colophon_source_v1.json").read_text())
        amendment=DATA/"research_historical_extension_colophon_amendment_v1.json"
        if correction["amendment_sha256"]!=sha(amendment):
            raise ValueError("Colophon amendment changed")
        path=OUT/correction["file"]
        if sha(path)!=correction["sha256"] or path.stat().st_size!=correction["bytes"]:
            raise ValueError("Colophon candidate changed")
        print("Source hash/size verification passed",len(manifest["files"])+1,"files")
    else:
        parser.error("Choose --acquire, --ocr or --verify-sources")


if __name__ == "__main__":
    main()
