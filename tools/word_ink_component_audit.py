"""Exposed scan-component separability audit of the frozen v7 contexts."""
import argparse
import json
from pathlib import Path

from ocr_ink_components import index_components, measure, verify_measurement
from ocr_ownership_evidence import ink_mask
from semantic_validation import DATA, ROOT
from word_ownership_evidence_audit import OUTPUT as SOURCE
from word_union_review import digest

OUTPUT = DATA / "audit_word_ink_components_development_v8.json"
MODES = ("crop_4", "crop_8", "page_4", "page_8")


def review(directory, report):
    """Raw scan plus component-colored panels for the retained counterexamples."""
    import hashlib
    import numpy as np
    from PIL import Image, ImageDraw
    from image_io import open_rgb
    source = json.loads(SOURCE.read_text())
    if digest(SOURCE) != report["inputs"][SOURCE.name]:
        raise AssertionError("component review source differs")
    directory.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for key, measured in report["measurements"].items():
        row = source["measurements"][key]
        page = row["page"]
        # The two unresolved failures and the three earlier clipping/center
        # counterexample pages are deliberately exposed diagnostic examples.
        if page not in (36, 66, 321, 366, 500):
            continue
        path = ROOT / "hayrat-pics" / f"page_{page}.png"
        if digest(path) != report["scan_sha256"][str(page)]:
            raise AssertionError("component review scan differs")
        image = open_rgb(path)
        box = row["original_bbox"]
        possible = ink_mask(image, box)
        full = ink_mask(image, [0, 0, image.width, image.height])
        indices = {c: index_components(full, c) for c in (4, 8)}
        replay = measure(image, box, row["pixels"]["clear_manual_reference"], indices)
        if replay != measured:
            raise AssertionError("review component replay differs")
        left, top = max(0, box[0]-25), max(0, box[1]-15)
        right, bottom = min(image.width, box[2]+25), min(image.height, box[3]+15)
        crop = image.crop((left, top, right, bottom))
        panels = []
        for mode in ("raw", "crop_8", "page_8"):
            panel = crop.copy()
            if mode != "raw":
                indexed = (index_components(possible, 8)[0] if mode == "crop_8" else
                           indices[8][0][box[1]:box[3], box[0]:box[2]])
                array = np.array(panel)
                local = array[box[1]-top:box[3]-top, box[0]-left:box[2]-left]
                for component in measured[mode]["components"]:
                    t, f = component.get("target_ink_pixels"), component.get("non_target_ink_pixels")
                    color = ((130, 0, 180) if t is None else (230, 0, 0) if t and f
                             else (0, 140, 0) if t else (225, 120, 0))
                    local[indexed == component["component_id"]] = color
                panel = Image.fromarray(array)
            panel = panel.resize((panel.width*3, panel.height*3))
            header = Image.new("RGB", (max(420, panel.width), panel.height+60), "white")
            header.paste(panel, (0, 60))
            draw = ImageDraw.Draw(header)
            draw.text((2, 2), f"p{page} {row['frame']} {mode}; evaluation colors, 3x", fill="black")
            draw.text((2, 18), "green target; orange foreign; red mixed; purple unlabelled", fill="black")
            if mode != "raw":
                s = measured[mode]["summary"]
                draw.text((2, 34), f"components {s['components']}; oracle error {s.get('oracle_minimum_pixel_errors', 'unlabelled')}", fill="black")
            draw.rectangle(((box[0]-left)*3, (box[1]-top)*3+60,
                            (box[2]-left)*3-1, (box[3]-top)*3+59), outline="blue", width=2)
            panels.append(header)
        sheet = Image.new("RGB", (sum(p.width for p in panels), panels[0].height), "white")
        offset = 0
        for panel in panels:
            sheet.paste(panel, (offset, 0))
            offset += panel.width
        name = f"p{page}_{row['frame']}_{hashlib.sha256(key.encode()).hexdigest()[:12]}.png"
        sheet.save(directory / name)
        manifest[name] = key
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
    print("component review sheets", len(manifest))


def analyze(scans=False, stored=None):
    source = json.loads(SOURCE.read_text())
    measurements = {}
    by_page = {}
    for key, row in source["measurements"].items():
        by_page.setdefault(row["page"], []).append((key, row))
    for page, rows in sorted(by_page.items()):
        if scans:
            from image_io import open_rgb
            path = ROOT / "hayrat-pics" / f"page_{page}.png"
            if digest(path) != source["scan_sha256"][str(page)]:
                raise AssertionError("component scan hash differs")
            image = open_rgb(path)
            full = ink_mask(image, [0, 0, image.width, image.height])
            indices = {c: index_components(full, c) for c in (4, 8)}
        for key, row in rows:
            box, pixels = row["original_bbox"], row["pixels"]
            measured = (measure(image, box, pixels["clear_manual_reference"], indices) if scans
                        else stored["measurements"][key])
            verify_measurement(box, pixels, measured)
            measurements[key] = measured
    groups = {}
    # Keep the source's overlapping cohorts and methods separate. A source
    # policy is only used to recover context links, never to mask components.
    for cohort, methods in source["groups"].items():
        groups[cohort] = {}
        for method, policies in methods.items():
            rows = policies["other_words"]["details"]
            details = []
            for row in rows:
                detail = {k: row[k] for k in ("page", "verse", "form", "measurement_key") if k in row}
                key = row["measurement_key"]
                detail["summaries"] = {mode: measurements[key][mode]["summary"] for mode in MODES} if key else None
                details.append(detail)
            summaries = {}
            for mode in MODES:
                available = [r["summaries"][mode] for r in details if r["summaries"] is not None]
                refs = [r for r in available if "oracle_minimum_pixel_errors" in r]
                summaries[mode] = dict(scheduled=len(rows), available=len(available), clear_reference_cases=len(refs),
                    cases_with_mixed_components=sum(r["mixed_components"] > 0 for r in refs),
                    exact_in_box_partition_representable=sum(r["exact_in_box_partition_representable"] for r in refs),
                    oracle_minimum_pixel_errors=sum(r["oracle_minimum_pixel_errors"] for r in refs))
            groups[cohort][method] = dict(summary=summaries, details=details)
    helpers = ("ocr_ink_components.py", "ocr_ownership_evidence.py", "ocr_ink_trim.py", "image_io.py")
    return dict(version="exposed-scan-component-separability-v8", measurements=measurements, groups=groups,
        scan_sha256=source["scan_sha256"],
        inputs={p.name: digest(p) for p in (SOURCE, Path(__file__), *(ROOT / "tools" / name for name in helpers))},
        protocol="Use the unchanged black-or-colored threshold union. Index 4- and 8-connected components in the original OCR crop and full page. Store every touching component's full bounding box, full pixel count and in-box pixel count. Existing clear manual partitions supply only in-box evaluation counts. Mixed components contain both manual target and non-target ink. Sum min(target, non-target) is the exact best in-box pixel error over all whole-component keep/remove choices. Full-page ink outside B is unlabelled, not assumed foreign. No target proposal or acceptance change is constructed.",
        caveat="Exposed development data, conditional on existing single-reader partitions and thresholds. Pure components do not establish automatic linguistic ownership; connected components need not be letters or auxiliary marks. Zero oracle error is representability, not achieved prediction or full-word coverage. Overlapping cohorts/methods are not pooled. Scan-free replay checks accounting and derived outcomes; scan replay additionally reconstructs topology and pixels.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--build", action="store_true")
    modes.add_argument("--verify", action="store_true")
    modes.add_argument("--review", type=Path)
    parser.add_argument("--scans", action="store_true")
    args = parser.parse_args()
    saved = json.loads(OUTPUT.read_text()) if args.verify or args.review else None
    if args.review:
        review(args.review, saved)
        return
    report = analyze(scans=args.build or args.scans, stored=saved)
    if args.verify:
        if report != saved:
            raise AssertionError("component separability audit differs")
        print("PASS component accounting, exact oracle errors and frozen context links")
    else:
        OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
    print("measurements", len(report["measurements"]), "pages", len(report["scan_sha256"]))
    for cohort, methods in report["groups"].items():
        for method, row in methods.items():
            print(cohort, method, "page_8", row["summary"]["page_8"])


if __name__ == "__main__":
    main()
