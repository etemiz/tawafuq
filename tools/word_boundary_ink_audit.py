"""Exposed diagnostic of in-box horizontal ink trimming, retaining all failures.

No manual partition, word identity or tolerance is used to infer a trimmed
box. Scoring uses all prior development groups, all reviewed v5 slots and
all 17 rejected unions. These cohorts overlap and must not be pooled.
"""
import argparse
import json
from pathlib import Path

from ocr_ink_trim import measure, trim, specification
from semantic_validation import DATA, ROOT, localized
from word_boundary_extent_review import OUTPUT as EXTENT
from word_boundary_ownership_policy import OUTPUT as OWNERSHIP, score_support
from word_boundary_validation import OUTPUT as DEVELOPMENT
from word_localization_validation import assess
from word_union_review import OUTPUT as UNIONS, digest
from ocr_word_boundary_map import OUTPUT as MAPPING

OUTPUT = DATA / "audit_word_boundary_ink_trim_development_v6.json"
INPUTS = (EXTENT, OWNERSHIP, DEVELOPMENT, UNIONS, MAPPING)


def cases():
    result = []
    ownership = json.loads(OWNERSHIP.read_text())
    for method, report in json.loads(EXTENT.read_text())["methods"].items():
        for row in report["details"]:
            key = f'{row["page"]}:{row["physical_row"]}:{row["lexical_position_rtl"]}'
            support = ownership["edge_support"].get(key)
            if support is None and row.get("boundary_eligible"):
                support = [[x] for x in row["x_edges"]]
            if row.get("pixels", {}).get("horizontal_partition_contact"):
                support = None
            result.append(dict(cohort="reviewed_v5", method=method, label=row,
                               support=support, bbox=row.get("bbox")))
    for method, report in json.loads(DEVELOPMENT.read_text())["results"].items():
        for group, report_group in report["groups"].items():
            for row in report_group["details"]:
                result.append(dict(cohort="development_"+group, method=method, label=row,
                                   support=None, bbox=row.get("bbox")))
    for row in json.loads(UNIONS.read_text())["details"]:
        label = dict(row, rect=row["annotation"]["core_rect"])
        result.append(dict(cohort="rejected_unions", method="counterfactual_only_still_rejected",
                           label=label, support=None, bbox=row["bbox"]))
    return result


def outcome(box, label, support):
    if label.get("status") == "unavailable":
        return dict(status="unavailable")
    if "x_edges" in label:
        result = assess(dict(bbox=box), label)
        if support is not None:
            score = score_support([box[0], box[2]], support, label["x_edge_tolerance"]) if box else None
            result["all_ownership_boundary_pass"] = bool(score and result["correct_line"]
                                                         and score["ownership_outcome"] == "all_pass")
            result["ownership_error"] = score
        return result
    correct = bool(box and label["rect"] and localized(dict(cx=(box[0]+box[2])/2, cy=(box[1]+box[3])/2), label))
    return dict(accepted=bool(box), center_correct=correct,
                status="correct_center" if correct else "wrong_center" if box else "abstained")


def summarize(rows):
    available = [r for r in rows if r["original"]["status"] != "unavailable"]
    result = dict(scheduled=len(rows), labelled=len(available), unavailable=len(rows)-len(available),
                  changed_boxes=sum(r["original_bbox"] != r["candidate_bbox"] for r in available),
                  center_regressions=sum(r["original"]["center_correct"] and not r["candidate"]["center_correct"] for r in available),
                  center_rescues=sum(not r["original"]["center_correct"] and r["candidate"]["center_correct"] for r in available))
    if any("boundary_eligible" in r for r in available):
        result["boundary_evaluable"] = sum(r.get("boundary_eligible", False) for r in available)
    if any(r["ownership_evaluable"] for r in available):
        result["all_ownership_evaluable"] = sum(r["ownership_evaluable"] for r in available)
    for variant in ("original", "candidate"):
        outcomes = [r[variant] for r in available]
        summary = dict(accepted=sum(r["accepted"] for r in outcomes),
                       correct_centers=sum(r["center_correct"] for r in outcomes),
                       wrong_accepted=sum(r["accepted"] and not r["center_correct"] for r in outcomes),
                       abstentions=sum(not r["accepted"] for r in outcomes))
        for field in ("horizontal_boundary_pass", "all_ownership_boundary_pass"):
            subset = [r for r in outcomes if field in r]
            if subset:
                summary[field] = sum(r[field] for r in subset)
        result[variant] = summary
    for field in ("horizontal_boundary_pass", "all_ownership_boundary_pass"):
        subset = [r for r in available if field in r["original"]]
        if subset:
            result[field+"_regressions"] = sum(r["original"][field] and not r["candidate"][field] for r in subset)
            result[field+"_rescues"] = sum(not r["original"][field] and r["candidate"][field] for r in subset)
    return result


def analyze(scans=False, stored=None):
    from image_io import open_rgb
    from ocr_corpus_map import SOURCE
    raw = {p["page"]: p for p in json.loads(SOURCE.read_text())["pages"]}
    grouped, measurements, images, scan_hashes, focus = {}, {}, {}, {}, []
    for case in cases():
        label, box = case["label"], case["bbox"]
        n = label["page"]
        if box is None:
            proposed, measurement_key = None, None
        else:
            measurement_key = f'{n}:'+":".join(map(str, box))
            if measurement_key not in measurements:
                if scans:
                    if n not in images:
                        path = ROOT / "hayrat-pics" / f"page_{n}.png"
                        if digest(path) != raw[n]["image_sha256"]:
                            raise AssertionError("ink diagnostic image hash differs")
                        images[n] = open_rgb(path)
                    pixels = measure(images[n], box)
                else:
                    pixels = stored["measurements"][measurement_key]["pixels"]
                measurements[measurement_key] = dict(page=n, original_bbox=box, pixels=pixels, **trim(box, pixels))
            proposed = measurements[measurement_key]["bbox"]
            scan_hashes[str(n)] = raw[n]["image_sha256"]
        original = outcome(box, label, case["support"])
        candidate = outcome(proposed, label, case["support"])
        if original.get("accepted") != candidate.get("accepted"):
            raise AssertionError("ink trimming changed acceptance")
        for field in ("center_correct", "horizontal_boundary_pass"):
            if field in label and original.get(field) != label[field]:
                raise AssertionError("original diagnostic outcome differs from source report")
        if case["cohort"] == "rejected_unions" and original["center_correct"] != label["center_correct"]:
            raise AssertionError("original rejected-union core result differs")
        identity = {k: label[k] for k in ("page", "verse", "form", "t", "v_id", "physical_row", "lexical_position_rtl", "sample_id") if k in label}
        row = dict(**identity, measurement_key=measurement_key, original_bbox=box, candidate_bbox=proposed,
                   original=original, candidate=candidate, ownership_evaluable=case["support"] is not None)
        if "annotation" in label:
            row["original_extent_annotation"] = label["annotation"]
        if "x_edges" in label:
            row.update(boundary_eligible=label["boundary_eligible"], x_edges=label["x_edges"],
                       x_edge_tolerance=label["x_edge_tolerance"])
        grouped.setdefault(case["cohort"], {}).setdefault(case["method"], []).append(row)
        if (case["cohort"], case["method"]) == ("reviewed_v5", "broad_v5") and original.get("accepted") and not original.get("all_ownership_boundary_pass"):
            mapping_page = next(p for p in json.loads(MAPPING.read_text())["pages"] if p["page"] == n)
            word = next(w for w in mapping_page["words"] if w["v_id"] == label["v_id"])
            focus.append(dict(**identity, original_bbox=box, candidate_bbox=proposed,
                              reviewed_possible_ink_bbox=label["pixels"]["ink_bbox"],
                              original_outcome=original, candidate_outcome=candidate,
                              measurement_key=measurement_key, surface_match=word.get("surface_match"),
                              mandatory_regions=[dict(source_region=i, **raw[n]["regions"][i]) for i in word["mandatory_regions"]]))
    groups = {cohort: {method: dict(summary=summarize(rows), details=rows,
                                  regressions=[r for r in rows if r["original"].get("center_correct")
                                               and not r["candidate"].get("center_correct")
                                               or r["original"].get("horizontal_boundary_pass")
                                               and not r["candidate"].get("horizontal_boundary_pass")
                                               or r["original"].get("all_ownership_boundary_pass")
                                               and not r["candidate"].get("all_ownership_boundary_pass")])
                       for method, rows in methods.items()} for cohort, methods in grouped.items()}
    return dict(version="exposed-in-box-horizontal-ink-diagnostic-v6", specification=specification(),
                measurements=measurements, scan_sha256=scan_hashes, groups=groups, accepted_edge_failure_diagnostics=focus,
                inputs={p.name: digest(p) for p in (*INPUTS, SOURCE, Path(__file__), Path(__file__).with_name("ocr_ink_trim.py"))},
                caveat="Every cohort is exposed development; overlapping cohorts/methods must not be pooled. The candidate uses only a predicted box and scan pixels, never target identity, manual partitions, cores or tolerance. It retains all thresholded in-box ink, possibly from neighbors/markers, cannot recover missing ink outside the original box, and can move a center. All rejected unions remain rejected by the conservative policy. Existing mapper outputs and original scores are unchanged. No fresh accuracy or automatic policy adoption is claimed.")


def review(directory, report):
    from PIL import Image, ImageDraw
    from image_io import open_rgb
    directory.mkdir(parents=True, exist_ok=True)
    selected = [r for r in report["groups"]["reviewed_v5"]["broad_v5"]["details"]
                if (r["page"], r.get("physical_row"), r.get("lexical_position_rtl")) == (545, 7, 7)]
    selected += [r for r in report["groups"]["rejected_unions"]["counterfactual_only_still_rejected"]["details"]
                 if r["original_extent_annotation"]["extent"] != "plausible_word"]
    for row in selected:
        image = open_rgb(ROOT / "hayrat-pics" / f'page_{row["page"]}.png')
        if digest(ROOT / "hayrat-pics" / f'page_{row["page"]}.png') != report["scan_sha256"][str(row["page"])]:
            raise AssertionError("diagnostic review scan hash differs")
        box = row["original_bbox"]
        left, top = max(0, box[0]-100), max(0, box[1]-35)
        right, bottom = min(image.width, box[2]+100), min(image.height, box[3]+35)
        crop = image.crop((left, top, right, bottom)).resize(((right-left)*3, (bottom-top)*3))
        sheet = Image.new("RGB", (crop.width, crop.height+45), "white")
        sheet.paste(crop, (0, 45))
        draw = ImageDraw.Draw(sheet)
        draw.text((0, 0), f'p{row["page"]} {row["verse"]}; red original, blue in-box horizontal hull; 3x', fill="black")
        for target, color in ((box, "red"), (row["candidate_bbox"], "blue")):
            draw.rectangle(((target[0]-left)*3, (target[1]-top)*3+45,
                            (target[2]-left)*3-1, (target[3]-top)*3+44), outline=color, width=2)
        for x in range(((left+19)//20)*20, right, 20):
            draw.text(((x-left)*3, 23), str(x), fill="black")
        sheet.save(directory / f'p{row["page"]}_{row.get("sample_id", "edge")}.png')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--build", action="store_true")
    modes.add_argument("--verify", action="store_true")
    modes.add_argument("--review", type=Path)
    parser.add_argument("--scans", action="store_true")
    args = parser.parse_args()
    saved = json.loads(OUTPUT.read_text()) if not args.build else None
    if args.review:
        review(args.review, saved)
        return
    report = analyze(scans=args.build or args.scans, stored=saved)
    if args.verify:
        if report != saved:
            raise AssertionError("in-box horizontal ink diagnostic differs")
        print("PASS all exposed ink-trim cohorts, raw projections, original outcomes and counterexamples")
    else:
        OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
    for cohort, methods in report["groups"].items():
        for method, result in methods.items():
            print(cohort, method, result["summary"])


if __name__ == "__main__":
    main()
