#!/usr/bin/env python3
"""Fetch a fixed, unscored historical manuscript pilot from public OPenn data.

The source/folio plan must exist before this script is run. No modern-page
number offsets or guessed image sequence numbers are used. Cached bytes are
retained and hashed; --verify is offline and checks every downloaded file.
"""

import argparse
import hashlib
import json
from pathlib import Path
import urllib.request
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "tools/data/research_historical_copy_plan_v1.json"
OUT = ROOT / "logs/historical-copy-ms-or-422-v1"
NS = {"t": "http://www.tei-c.org/ns/1.0"}
BASE = "https://openn.library.upenn.edu/Data/0032/ms_or_422/"
AMENDMENT = ROOT / "tools/data/research_historical_copy_retrieval_amendment_v1.json"
CORRECTION = ROOT / "tools/data/research_historical_copy_index_correction_v1.json"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fetch(url, path):
    if path.exists():
        return path.read_bytes()
    request = urllib.request.Request(url, headers={"User-Agent": "tawafuq-historical-research/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read()
    path.write_bytes(data)
    return data


def surfaces(data):
    """Return actual TEI labels and web-image URLs; reject duplicate labels."""
    result = {}
    tree = ET.fromstring(data)
    for surface in tree.findall(".//t:surface", NS):
        label = surface.get("n", "")
        graphics = [g for g in surface.findall("t:graphic", NS)
                    if g.get("url", "").endswith("_web.jpg")]
        if not graphics:
            continue
        if len(graphics) != 1 or label in result:
            raise ValueError(f"Ambiguous surface: {label}")
        result[label] = {"url": BASE + "data/" + graphics[0].get("url"),
                         "width": graphics[0].get("width"),
                         "height": graphics[0].get("height")}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--internet-archive", action="store_true",
                        help="Amended retrieval route; folio labels provisional")
    parser.add_argument("--corrected-indices", action="store_true",
                        help="Retain corrected page/n candidates, with original attempts preserved")
    parser.add_argument("--review", action="store_true", help="Render cached corrected candidates at 1000px width")
    parser.add_argument("--publish-manifest", action="store_true",
                        help="Save hashes/URLs of cached acquisitions for scan-free provenance")
    args = parser.parse_args()
    plan_bytes = PLAN.read_bytes()
    plan = json.loads(plan_bytes)
    manifest_path = OUT / ("manifest-corrected.json" if args.corrected_indices else "manifest.json")
    if args.publish_manifest:
        target = ROOT / "tools/data/research_historical_copy_sources_v1.json"
        manifests = [json.loads((OUT / name).read_text())
                     for name in ("manifest.json", "manifest-corrected.json")]
        report = dict(study=plan["study"], plan_sha256=sha(plan_bytes),
                      amendment_sha256=sha(AMENDMENT.read_bytes()),
                      correction_sha256=sha(CORRECTION.read_bytes()),
                      acquisition_attempts=manifests,
                      source_authority="Columbia's descriptive catalogue, mirrored in OPenn, HathiTrust and Internet Archive; not independent dating authorities.",
                      source_ids=dict(shelfmark="MS Or 422", clio_original="14258972",
                                      clio_digital="14642794", hathitrust_record="102811738",
                                      internet_archive="ldpd_14642794_000", ark="ark:/13960/t44r73r5w"),
                      folio_match="Corrected candidates show 50,100,150,200,250,300,304 in upper-left foliation; first recto also matches exposed OPenn 9372_0105_web.jpg by text and foliation.",
                      material_dating_or_acquisition_chain_verified=False)
        for manifest in manifests:
            for item in manifest["files"]:
                data = (OUT / item["file"]).read_bytes()
                assert sha(data) == item["sha256"] and len(data) == item["bytes"]
        if target.exists():
            assert json.loads(target.read_text()) == report
            print("Published source manifest replay passed")
        else:
            target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
            print("Saved", target.relative_to(ROOT))
        return
    if args.review:
        from PIL import Image, ImageDraw
        manifest = json.loads((OUT / "manifest-corrected.json").read_text())
        for item in manifest["files"]:
            if not item["file"].endswith(".jpg"):
                continue
            image = Image.open(OUT / item["file"])
            image = image.resize((1000, round(image.height * 1000 / image.width)))
            image.save(OUT / ("review-" + item["file"]))
            ruler = image.copy()
            draw = ImageDraw.Draw(ruler)
            for x in range(0, 1000, 50):
                draw.line((x, 0, x, image.height), fill=(80, 170, 200), width=1)
                draw.text((x+2, 100), str(x), fill=(0, 0, 180))
            for y in range(0, image.height, 100):
                draw.text((5, y), str(y), fill=(0, 0, 180))
            ruler.save(OUT / ("ruler-" + item["file"]))
        return
    if args.verify:
        manifest = json.loads(manifest_path.read_text())
        assert manifest["plan_sha256"] == sha(plan_bytes)
        if "amendment_sha256" in manifest:
            assert manifest["amendment_sha256"] == sha(AMENDMENT.read_bytes())
        if "correction_sha256" in manifest:
            assert manifest["correction_sha256"] == sha(CORRECTION.read_bytes())
        for item in manifest["files"]:
            data = (OUT / item["file"]).read_bytes()
            assert sha(data) == item["sha256"], item["file"]
            assert len(data) == item["bytes"], item["file"]
        print(f"Offline verification passed: {len(manifest['files'])} files")
        return
    if args.corrected_indices and not args.internet_archive:
        parser.error("--corrected-indices requires --internet-archive for retrieval")
    if manifest_path.exists():
        raise FileExistsError("Acquisition manifest exists; use --verify instead of overwriting")
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {"study": plan["study"], "plan_sha256": sha(plan_bytes), "files": []}

    def retain(url, filename, **extra):
        data = fetch(url, OUT / filename)
        manifest["files"].append({"file": filename, "url": url,
                                  "sha256": sha(data), "bytes": len(data), **extra})
        return data

    if args.internet_archive:
        manifest["amendment_sha256"] = sha(AMENDMENT.read_bytes())
        if args.corrected_indices:
            manifest["correction_sha256"] = sha(CORRECTION.read_bytes())
        retain(plan["sources"]["internet_archive"], "internet-archive-metadata.json")
        retain("https://archive.org/download/ldpd_14642794_000/"
               "ldpd_14642794_000_scandata.xml", "internet-archive-scandata.xml")
        indices = ([104, 204, 304, 404, 504, 604, 612] if args.corrected_indices
                   else [105, 205, 305, 405, 505, 605, 613])
        for folio, leaf in zip(plan["selection"]["folios"] + ["304r"], indices):
            url = f"https://archive.org/download/ldpd_14642794_000/page/n{leaf}.jpg"
            data = retain(url, f"ia-leaf-{leaf}.jpg", target_folio=folio,
                          page_n_argument=leaf, folio_correspondence="provisional")
            print(f"IA leaf {leaf}, provisional {folio}: {len(data)} bytes", flush=True)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        print("Saved", manifest_path.relative_to(ROOT))
        return
    data = retain(plan["sources"]["openn_tei"], "ms_or_422_TEI.xml")
    inventory = surfaces(data)
    print("TEI web-image surfaces:", len(inventory))
    print("First labels:", list(inventory)[:12])
    for folio in plan["selection"]["folios"] + ["304r"]:
        matches = [(label, info) for label, info in inventory.items()
                   if label.removeprefix("fol. ").strip() == folio]
        if len(matches) != 1:
            raise ValueError(f"Need exactly one TEI surface for {folio}: {matches}")
        label, info = matches[0]
        image = retain(info["url"], f"folio-{folio}.jpg", folio=folio,
                       tei_label=label, tei_width=info["width"], tei_height=info["height"])
        print(f"{folio}: {len(image)} bytes {sha(image)}")
    retain(plan["sources"]["internet_archive"], "internet-archive-metadata.json")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print("Saved", manifest_path.relative_to(ROOT))


if __name__ == "__main__":
    main()
