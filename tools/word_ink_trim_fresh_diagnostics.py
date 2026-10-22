"""Post-comparison provenance/crops for every failure in locked fresh v6 results.

Original labels, evaluator, predictions and scores are immutable inputs. This
diagnostic cannot correct labels or turn post-exposure review into fresh data.
"""
import argparse
import json
from pathlib import Path

import ocr_corpus_map as cm
import ocr_word_boundary_map as wm
from semantic_validation import DATA, ROOT
from word_ink_trim_fresh_sample import MANUAL
from word_ink_trim_fresh_validation import OUTPUT as VALIDATION, analyze as validate
from word_union_review import digest

OUTPUT = DATA / "audit_word_ink_trim_fresh_diagnostics_v6.json"


def identity(row):
    return row["page"], row["physical_row"], row["lexical_position_rtl"]


def analyze():
    result = json.loads(VALIDATION.read_text())
    if validate(stored=result) != result:
        raise AssertionError("locked fresh ink-trim comparison differs before diagnostics")
    manual = json.loads(MANUAL.read_text())
    raw = {p["page"]: p for p in json.loads(cm.SOURCE.read_text())["pages"]}
    mapped = {p["page"]: p for p in json.loads(wm.OUTPUT.read_text())["pages"]}
    methods = {name: {identity(r): r for r in method["details"]} for name, method in result["methods"].items()}
    # Include every failure from every method, not a success-selected subset.
    selected = {identity(r) for method in result["methods"].values() for r in method["failures"]}
    cases = []
    for key in sorted(selected):
        row = methods["original_broad"][key]
        n = row["page"]
        word = next(w for w in mapped[n]["words"] if w["v_id"] == row["v_id"])
        if (word["form"], word["t"]) != (row["form"], row["t"]):
            raise AssertionError("failure provenance token differs")
        fields = ("page", "physical_row", "lexical_position_rtl", "verse", "form", "t", "v_id",
                  "core_rect", "partition", "ink_class", "mark_ownership", "x_edges", "x_edge_tolerance", "note")
        entries = {}
        for name, rows in methods.items():
            details = rows[key]
            entries[name] = {k: details.get(k) for k in ("bbox", "accepted", "center_correct", "horizontal_boundary_pass",
                                                        "signed_x_edge_errors", "all_ownership_boundary_pass", "ownership_error")}
        cases.append(dict(**{k: row[k] for k in fields}, outcomes=entries,
                          normalized_text_exact=word.get("surface_match"),
                          mandatory_regions=[dict(source_region=i, **raw[n]["regions"][i]) for i in word["mandatory_regions"]],
                          image_sha256=raw[n]["image_sha256"]))
    ambiguous = [dict(page=p["page"], **{k: w[k] for k in ("physical_row", "lexical_position_rtl", "verse", "form",
                    "partition", "note", "boundary_eligible", "ownership_evaluable", "ownership_bounds", "edge_support")})
                 for p in manual["pages"] for w in p["word_samples"]
                 if w.get("status") != "unavailable" and w["mark_ownership"] == "uncertain"]
    same = all(methods[f"{variant}_broad"][key].get("bbox") == methods[f"{variant}_conservative"][key].get("bbox")
               for variant in ("original", "trimmed") for key in methods[f"{variant}_broad"])
    return dict(version="post-comparison-fresh-ink-trim-failure-provenance-v6", cases=cases,
                ambiguous_scan_labels=ambiguous, broad_conservative_sample_boxes_identical=same,
                selection="Union of every failure in all four locked methods, deduplicated by physical slot. Original labels and scores copied unchanged.",
                inputs={p.name: digest(p) for p in (VALIDATION, MANUAL, cm.SOURCE, wm.OUTPUT, Path(__file__))},
                caveat="Post-comparison diagnostic provenance, not additional fresh annotation or independent verification of linguistic ownership. Identical broad/conservative outcomes on this sample are not independent replications. No labels, inference rules or acceptance policies changed.")


def review(directory, report):
    from PIL import Image, ImageDraw
    from image_io import open_rgb
    directory.mkdir(parents=True, exist_ok=True)
    for row in report["cases"]:
        path = ROOT / "hayrat-pics" / f'page_{row["page"]}.png'
        if digest(path) != row["image_sha256"]:
            raise AssertionError("fresh failure review image differs")
        image = open_rgb(path)
        boxes = [row["outcomes"][name]["bbox"] for name in ("original_broad", "trimmed_broad")]
        present = [box for box in boxes if box]
        left = max(0, min([row["partition"][0]]+[b[0] for b in present])-65)
        right = min(image.width, max([row["partition"][2]]+[b[2] for b in present])+65)
        top = max(0, min([row["partition"][1]]+[b[1] for b in present])-10)
        bottom = min(image.height, max([row["partition"][3]]+[b[3] for b in present])+10)
        crop = image.crop((left, top, right, bottom)).resize(((right-left)*3, (bottom-top)*3))
        sheet = Image.new("RGB", (crop.width, crop.height+65), "white")
        sheet.paste(crop, (0, 65))
        draw = ImageDraw.Draw(sheet)
        draw.text((0, 0), f'p{row["page"]} r{row["physical_row"]} k{row["lexical_position_rtl"]} {row["verse"]}; 3x', fill="black")
        draw.text((0, 17), "red original; blue trimmed; green manual horizontal edges; labels unchanged", fill="black")
        for x in range(((left+9)//10)*10, right, 10):
            draw.text(((x-left)*3, 42), str(x), fill="black")
        for box, color in zip(boxes, ("red", "blue")):
            if box:
                draw.rectangle(((box[0]-left)*3, (box[1]-top)*3+65,
                                (box[2]-left)*3-1, (box[3]-top)*3+64), outline=color, width=2)
        for edge in row["x_edges"]:
            for y in range(65, sheet.height, 12):
                draw.line(((edge-left)*3, y, (edge-left)*3, min(y+6, sheet.height)), fill="green", width=2)
        sheet.save(directory / f'p{row["page"]}_r{row["physical_row"]}_k{row["lexical_position_rtl"]}.png')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--build", action="store_true")
    modes.add_argument("--verify", action="store_true")
    modes.add_argument("--review", type=Path)
    args = parser.parse_args()
    if args.review:
        review(args.review, json.loads(OUTPUT.read_text()))
        return
    report = analyze()
    if args.verify:
        if report != json.loads(OUTPUT.read_text()):
            raise AssertionError("fresh ink-trim failure provenance differs")
        print("PASS every frozen failure, unchanged labels, raw OCR provenance and ambiguous cases")
    else:
        OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
    print("failure cases", len(report["cases"]), "same broad/conservative boxes", report["broad_conservative_sample_boxes_identical"])
    for row in report["cases"]:
        print(row["page"], row["form"], row["mandatory_regions"],
              "trim errors", row["outcomes"]["trimmed_broad"]["signed_x_edge_errors"])


if __name__ == "__main__":
    main()
