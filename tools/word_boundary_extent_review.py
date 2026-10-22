"""Post-exposure scan review of every originally unscorable v5 boundary.

Original scan-first labels, centers, predictions and results stay immutable.
This is a separate same-reader extent annotation, not fresh validation.
"""
import argparse
import copy
import json
from pathlib import Path

import numpy as np

from semantic_validation import DATA, ROOT
from word_boundary_fresh_sample import MANUAL as ORIGINAL, measure_ink, build as original_build
from word_union_review import digest

LABELS = DATA / "audit_word_boundary_extent_labels_v5.json"
MANUAL = DATA / "audit_manual_word_boundary_extent_v5.json"
OUTPUT = DATA / "audit_word_boundary_extent_validation_v5.json"


def identity(page, word):
    return page, word["physical_row"], word["lexical_position_rtl"]


def original():
    report = json.loads(ORIGINAL.read_text())
    if original_build(False, report) != report:
        raise AssertionError("original scan-first labels or their provenance differ")
    return report


def inventory(report):
    return [(p["page"], w) for p in report["pages"] for w in p["word_samples"]
            if w.get("status") != "unavailable" and not w["boundary_eligible"]]


def ownership_bounds(mandatory, possible, x0=0):
    """Exact edge ranges for every mask M with mandatory <= M <= possible.

    Both extremal masks are allowed, so extrema below are attainable. Equal
    endpoints prove edge invariance for every intervening ownership subset.
    """
    mandatory, possible = np.asarray(mandatory, dtype=bool), np.asarray(possible, dtype=bool)
    if mandatory.shape != possible.shape or mandatory.ndim != 2 or np.any(mandatory & ~possible):
        raise AssertionError("invalid mandatory/possible ink masks")
    _, mx = np.where(mandatory)
    _, px = np.where(possible)
    if not len(mx):
        raise AssertionError("word needs nonempty mandatory linguistic ink")
    ranges = [[x0+int(px.min()), x0+int(mx.min())], [x0+int(mx.max())+1, x0+int(px.max())+1]]
    return dict(x_edge_ranges=ranges, horizontal_invariant=all(lo == hi for lo, hi in ranges),
                mandatory_ink_pixels=int(mandatory.sum()), optional_ink_pixels=int(possible.sum()-mandatory.sum()))


def measure_extent(image, label):
    partition = label["partition"]
    ink = label["ink_class"]
    pixels = measure_ink(image, partition, ink)
    array = np.asarray(image.crop(partition), dtype=np.int16)
    r, g, b = array[..., 0], array[..., 1], array[..., 2]
    black, colored = (r < 120) & (g < 120) & (b < 120), (r > 120) & (r-g > 45)
    possible = black if ink == "black" else colored if ink == "colored" else black | colored
    mandatory = possible.copy()
    if label.get("optional_colored", False):
        if ink != "mixed":
            raise AssertionError("optional colored ink requires the mixed-ink mask")
        mandatory &= ~colored
    for x0, y0, x1, y1 in label.get("optional_rects", []):
        if not (partition[0] <= x0 < x1 <= partition[2] and partition[1] <= y0 < y1 <= partition[3]):
            raise AssertionError("optional-mark rectangle outside reviewed partition")
        mandatory[y0-partition[1]:y1-partition[1], x0-partition[0]:x1-partition[0]] = False
    bounds = ownership_bounds(mandatory, possible, partition[0])
    # Unspecified ambiguity is never resolved merely because the two masks
    # were accidentally identical: ownership alternatives must be explicit.
    bounds["alternatives_specified"] = bool(label.get("optional_colored") or label.get("optional_rects"))
    return pixels, bounds


def review(directory):
    from PIL import Image, ImageDraw
    from image_io import open_rgb
    directory.mkdir(parents=True, exist_ok=True)
    report = original()
    pages = {p["page"]: p for p in report["pages"]}
    for n, word in inventory(report):
        path = ROOT / "hayrat-pics" / f"page_{n}.png"
        if digest(path) != pages[n]["image_sha256"]:
            raise AssertionError("extent review scan hash differs")
        image = open_rgb(path)
        box = word["partition"]
        left, top = max(0, box[0]-100), max(0, box[1]-15)
        right, bottom = min(image.width, box[2]+100), min(image.height, box[3]+15)
        crop = image.crop((left, top, right, bottom)).resize(((right-left)*3, (bottom-top)*3))
        sheet = Image.new("RGB", (crop.width, crop.height+45), "white")
        sheet.paste(crop, (0, 45))
        draw = ImageDraw.Draw(sheet)
        row, k = word["physical_row"], word["lexical_position_rtl"]
        draw.text((0, 0), f"p{n} row {row} word {k}; original crop x={left}..{right}, y={top}..{bottom}; 3x", fill="black")
        for x in range(((left+9)//10)*10, right, 10):
            px = (x-left)*3
            draw.line((px, 34, px, 44), fill="gray")
            if x % 20 == 0:
                draw.text((px, 20), str(x), fill="black")
        sheet.save(directory / f"p{n}_r{row}_k{k}.png")


def components(selected):
    """Scan-only connected ink boxes to inspect manual partition contacts."""
    from scipy.ndimage import label as label_components, find_objects
    from image_io import open_rgb
    wanted = {tuple(map(int, key.split(":"))) for key in selected.split(",")}
    pages = {p["page"]: p for p in original()["pages"]}
    labels = json.loads(LABELS.read_text())["labels"]
    for row in labels:
        key = identity(row["page"], row)
        if key not in wanted:
            continue
        path = ROOT / "hayrat-pics" / f'page_{row["page"]}.png'
        if digest(path) != pages[row["page"]]["image_sha256"]:
            raise AssertionError("component diagnostic scan hash differs")
        # Include a 20px horizontal margin so clipped components are visible.
        x0, y0, x1, y1 = row["partition"]
        x0, x1 = max(0, x0-20), min(1024, x1+20)
        array = np.asarray(open_rgb(path).crop((x0, y0, x1, y1)), dtype=np.int16)
        r, g, b = array[..., 0], array[..., 1], array[..., 2]
        for name, mask in (("black", (r < 120) & (g < 120) & (b < 120)),
                           ("colored", (r > 120) & (r-g > 45))):
            indexed, _ = label_components(mask, np.ones((3, 3)))
            boxes = []
            for index, slices in enumerate(find_objects(indexed), 1):
                if slices is not None:
                    ys, xs = slices
                    boxes.append(dict(bbox=[x0+xs.start, y0+ys.start, x0+xs.stop, y0+ys.stop],
                                      pixels=int(np.sum(indexed[slices] == index))))
            print(key, name, sorted(boxes, key=lambda r: r["bbox"]))


def build(scans=True, stored=None):
    from image_io import open_rgb
    source = original()
    labels = json.loads(LABELS.read_text())
    if labels["original_sha256"] != digest(ORIGINAL):
        raise AssertionError("extent review refers to another original sample")
    entries = {identity(r["page"], r): r for r in labels["labels"]}
    expected = {identity(n, w) for n, w in inventory(source)}
    if len(entries) != len(labels["labels"]) or set(entries) != expected:
        raise AssertionError("extent review must cover exactly every originally unscorable boundary")
    result = copy.deepcopy(source)
    for page in result["pages"]:
        n = page["page"]
        image = None
        if scans:
            path = ROOT / "hayrat-pics" / f"page_{n}.png"
            if digest(path) != page["image_sha256"]:
                raise AssertionError("extent review image hash differs")
            image = open_rgb(path)
        saved = next(p for p in stored["pages"] if p["page"] == n) if stored else None
        for i, word in enumerate(page["word_samples"]):
            key = identity(n, word)
            if key not in entries:
                continue
            label = entries[key]
            partition = label["partition"]
            core = word["core_rect"]
            cx, cy = (core[0]+core[2])/2, (core[1]+core[3])/2
            if not (0 <= partition[0] < partition[2] <= 1024 and 0 <= partition[1] < partition[3] <= 1680
                    and partition[0] <= cx <= partition[2] and partition[1] <= cy <= partition[3]):
                raise AssertionError("review partition excludes the original core center or scan bounds")
            if label["mark_ownership"] not in {"clear", "uncertain"} or not label.get("note"):
                raise AssertionError("extent review needs an explicit ownership decision and note")
            if scans:
                pixels, bounds = measure_extent(image, label)
            else:
                pixels, bounds = saved["word_samples"][i]["pixels"], saved["word_samples"][i]["ownership_bounds"]
            fields = ("partition", "pixels", "ink_class", "mark_ownership", "x_edges", "boundary_eligible", "boundary_exclusion_reasons")
            word["original_boundary"] = {k: copy.deepcopy(word[k]) for k in fields}
            resolved = label["mark_ownership"] == "clear" or (bounds["alternatives_specified"] and bounds["horizontal_invariant"])
            reasons = [] if resolved else ["uncertain_horizontal_mark_ownership"]
            reasons += ["horizontal_partition_contact"] if pixels["horizontal_partition_contact"] else []
            word.update(partition=partition, pixels=pixels, ink_class=label["ink_class"],
                        mark_ownership=label["mark_ownership"], x_edges=[pixels["ink_bbox"][0], pixels["ink_bbox"][2]],
                        boundary_eligible=not reasons, boundary_exclusion_reasons=reasons, extent_review=label,
                        ownership_bounds=bounds)
    words = [w for p in result["pages"] for w in p["word_samples"] if w.get("status") != "unavailable"]
    result.update(version="post-exposure-boundary-extent-annotations-v5",
                  summary=dict(scheduled=sum(len(p["word_samples"]) for p in result["pages"]), labelled=len(words),
                               unavailable=source["summary"]["unavailable"], reviewed=len(entries),
                               newly_evaluable=sum(w["boundary_eligible"] for w in words if "extent_review" in w),
                               invariant_optional_mark_cases=sum(w["mark_ownership"] == "uncertain" and w["boundary_eligible"]
                                                                 for w in words if "extent_review" in w),
                               still_unscorable=sum(not w["boundary_eligible"] for w in words),
                               boundary_evaluable=sum(w["boundary_eligible"] for w in words)),
                  original_summary=source["summary"],
                  annotation_source_sha256=digest(Path(__file__)),
                  inputs={p.name: digest(p) for p in (ORIGINAL, LABELS)},
                  protocol="Post-exposure review by the same AI reader of every originally unscorable boundary. "
                  "Enlarged scan context without OCR-box overlays; original core rectangles, identities, "
                  "tolerance, predictions and available/unavailable slots unchanged. Revised whitespace "
                  "partitions and explicit unresolved ownership; contact still excludes scoring. "
                  "Ambiguous interior marks can supply invariant horizontal edges only when every subset "
                  "between explicit mandatory/possible pixel masks has the same left/right extremes. "
                  "Original boundary records retained for every reviewed label. Not fresh or independent double annotation.")
    return result


def analyze():
    from word_boundary_fresh_validation import OUTPUT as INITIAL, analyze as initial_analyze, summarize
    from word_localization_validation import assess
    initial = json.loads(INITIAL.read_text())
    if initial_analyze() != initial:
        raise AssertionError("original frozen prediction comparison differs")
    manual = json.loads(MANUAL.read_text())
    if build(False, manual) != manual:
        raise AssertionError("post-exposure boundary annotations differ")
    methods = {}
    for method, previous in initial["methods"].items():
        rows = {identity(r["page"], r): r for r in previous["details"]}
        details = []
        for page in manual["pages"]:
            for label in page["word_samples"]:
                old = rows[identity(page["page"], label)]
                if label.get("status") == "unavailable":
                    details.append(copy.deepcopy(old))
                    continue
                outcome = assess(old, label)
                if (outcome["accepted"], outcome["center_correct"]) != (old["accepted"], old["center_correct"]):
                    raise AssertionError("boundary review changed a frozen center outcome")
                details.append(dict(page=page["page"], **label, **outcome,
                                    original_boundary_eligible=old["boundary_eligible"],
                                    original_horizontal_boundary_pass=old["horizontal_boundary_pass"]))
        reviewed = [r for r in details if "extent_review" in r]
        methods[method] = dict(original_summary=previous["summary"], summary=summarize(details),
                               reviewed_summary=summarize(reviewed), details=details,
                               boundary_failures=[r for r in details if r.get("boundary_eligible")
                                                  and not r["horizontal_boundary_pass"]])
    return dict(version="post-exposure-boundary-extent-comparison-v5", methods=methods,
                inputs={p.name: digest(p) for p in (ORIGINAL, LABELS, MANUAL, INITIAL)},
                caveat="Same-reader post-exposure boundary review. Original fresh-v5 report remains immutable. "
                "Newly evaluable boundaries are development/adjudication only, not fresh accuracy. "
                "No model/acceptance changes; uncertainty and abstentions remain explicit.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--inventory", action="store_true")
    modes.add_argument("--review", type=Path)
    modes.add_argument("--components", help="comma-separated page:row:position scan-only ink diagnostics")
    modes.add_argument("--build", action="store_true")
    modes.add_argument("--compare", action="store_true")
    modes.add_argument("--verify", action="store_true")
    parser.add_argument("--scans", action="store_true")
    args = parser.parse_args()
    if args.inventory:
        for n, w in inventory(original()):
            print(n, w["physical_row"], w["lexical_position_rtl"], w["verse"], w["form"],
                  w["partition"], w["boundary_exclusion_reasons"])
    elif args.review:
        review(args.review)
    elif args.components:
        components(args.components)
    elif args.build:
        report = build()
        MANUAL.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
        print(report["summary"])
        for p in report["pages"]:
            for w in p["word_samples"]:
                if "extent_review" in w:
                    print(p["page"], w["physical_row"], w["lexical_position_rtl"], w["form"],
                          w["x_edges"], w["boundary_eligible"], w["boundary_exclusion_reasons"])
    else:
        if args.verify:
            manual = json.loads(MANUAL.read_text())
            if build(args.scans, manual) != manual:
                raise AssertionError("extent-review annotations/pixels differ")
        report = analyze()
        if args.verify:
            if report != json.loads(OUTPUT.read_text()):
                raise AssertionError("extent-review comparison differs")
            print("PASS all 22 reviewed boundaries, preserved originals, pixel/core provenance and comparisons")
        else:
            OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
        for method, result in report["methods"].items():
            print(method, result["summary"], "reviewed", result["reviewed_summary"])
            for w in result["boundary_failures"]:
                print("boundary failure", w["page"], w["physical_row"], w["lexical_position_rtl"], w["form"],
                      w["status"], w.get("signed_x_edge_errors"))


if __name__ == "__main__":
    main()
