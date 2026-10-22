"""Exposed ownership-evidence diagnostic across every earlier evaluation cohort.

Compare rectangle masks against the unmasked in-box hull. Conditional edge
ranges and manual-reference contradictions accompany every proposed change.
This creates neither new fresh results nor a replacement automatic mapper.
"""
import argparse
import hashlib
import json
from pathlib import Path

import ocr_corpus_map as cm
import ocr_corpus_sites as cs
import ocr_row_map as rm
import ocr_word_boundary_map as wm
from ocr_ownership_evidence import POLICIES, overlaps, rosette_box, measure, proposal, reference_checks
from semantic_validation import DATA, ROOT
from word_boundary_ink_audit import INPUTS as EARLIER_INPUTS, cases as earlier_cases, outcome
from word_ink_trim_fresh_validation import OUTPUT as FRESH
from word_boundary_ownership_policy import score_support
from word_union_review import digest

OUTPUT = DATA / "audit_word_ownership_evidence_development_v7.json"
ROSETTES = DATA / "rosettes_v3" / "rosette_digits.json"


def cases():
    result = earlier_cases()
    for name, report in json.loads(FRESH.read_text())["methods"].items():
        if not name.startswith("original_"):
            continue
        for row in report["details"]:
            result.append(dict(cohort="fresh_v6_now_development", method=name, label=row,
                               support=row.get("edge_support"), bbox=row.get("bbox")))
    return result


def same_token(word, label):
    if word["kind"] != label.get("kind", "verse"):
        return False
    return (word["t"] == label["t"] if word["kind"] == "verse" else
            (word["verse"], word["word_in_verse"]) == (label["verse"], label["word_in_verse"]))


def word_claims(page, raw):
    rows = []
    if page["status"] in {"conditional_window_match", "conditional_word_window_match"}:
        for word in page["words"]:
            row, _ = cs.site(word, raw["regions"])
            if row is not None:
                rows.append(row)
    return rows


def summarize(rows):
    available = [r for r in rows if r["baseline"]["status"] != "unavailable"]
    result = dict(scheduled=len(rows), labelled=len(available), unavailable=len(rows)-len(available),
                  changed_boxes=sum(r["baseline_bbox"] != r["candidate_bbox"] for r in available),
                  masked_ink_cases=sum(r.get("optional_ink_pixels", 0) > 0 for r in available),
                  empty_mandatory_fallbacks=sum(r.get("proposal_status") == "empty_mandatory_fallback" for r in available))
    for name in ("baseline", "candidate"):
        result[name] = dict(accepted=sum(r[name]["accepted"] for r in available),
                            correct_centers=sum(r[name]["center_correct"] for r in available),
                            wrong_accepted=sum(r[name]["accepted"] and not r[name]["center_correct"] for r in available),
                            abstentions=sum(not r[name]["accepted"] for r in available))
    for name, field, eligible in (("center", "center_correct", lambda r: True),
                                   ("fixed_boundary", "horizontal_boundary_pass", lambda r: r.get("boundary_eligible", False)),
                                   ("all_ownership_boundary", "all_ownership_boundary_pass", lambda r: r["ownership_evaluable"])):
        subset = [r for r in available if eligible(r)]
        if subset:
            result[name+"_evaluable"] = len(subset)
            for variant in ("baseline", "candidate"):
                result[variant][name+"_pass"] = sum(r[variant][field] is True for r in subset)
            result[name+"_rescues"] = sum(not r["baseline"][field] and r["candidate"][field] for r in subset)
            result[name+"_regressions"] = sum(r["baseline"][field] and not r["candidate"][field] for r in subset)
    references = [r["manual_reference_checks"] for r in available if r.get("manual_reference_checks") is not None]
    result["clear_manual_reference_cases"] = len(references)
    result["mandatory_non_target_cases"] = sum(r["mandatory_non_target_pixels"] > 0 for r in references)
    result["extra_target_clipping_cases"] = sum(r["extra_target_pixels_clipped"] > 0 for r in references)
    result["extra_target_pixels_clipped"] = sum(r["extra_target_pixels_clipped"] for r in references)
    result["original_box_missing_target_cases"] = sum(r["target_pixels_outside_original_box"] > 0 for r in references)
    return result


def is_failure(row, variant):
    score = row[variant]
    return (score["status"] != "unavailable" and (not score["center_correct"]
            or row.get("boundary_eligible", False) and not score["horizontal_boundary_pass"]
            or row["ownership_evaluable"] and not score.get("all_ownership_boundary_pass")))


def regressions(row):
    if row["baseline"]["status"] == "unavailable":
        return []
    checks = [("center", "center_correct", True),
              ("fixed_boundary", "horizontal_boundary_pass", row.get("boundary_eligible", False)),
              ("all_ownership_boundary", "all_ownership_boundary_pass", row["ownership_evaluable"])]
    return [name for name, field, eligible in checks if eligible and row["baseline"][field] and not row["candidate"][field]]


def analyze(scans=False, stored=None):
    from image_io import open_rgb
    raw = {p["page"]: p for p in json.loads(cm.SOURCE.read_text())["pages"]}
    mapped = {"v4": {p["page"]: p for p in json.loads(rm.OUTPUT.read_text())["pages"]},
              "v5": {p["page"]: p for p in json.loads(wm.OUTPUT.read_text())["pages"]}}
    rosettes = json.loads(ROSETTES.read_text())
    measurements, images, claims, grouped, scan_hashes = {}, {}, {}, {}, {}
    for case in cases():
        label, box = case["label"], case["bbox"]
        n = label["page"]
        frame = "v4" if case["method"] == "seeded_rows_v4" else "v5"
        record_key = None
        measured = None
        baseline_box = box
        if box is not None:
            if (frame, n) not in claims:
                claims[frame, n] = word_claims(mapped[frame][n], raw[n])
            matches = [w for w in claims[frame, n] if same_token(w, label)]
            if len(matches) != 1 or matches[0]["bbox"] != box:
                raise AssertionError("ownership case does not reproduce frozen target support")
            word = matches[0]
            record_key = f'{frame}:{n}:{word["v_id"]}:'+":".join(map(str, box))
            # Different labels of the same box may offer different manual
            # references. Keep each source annotation distinct in the cache.
            reference = label if (label.get("mark_ownership") == "clear" and label.get("boundary_eligible")
                                  and "partition" in label and "ink_class" in label) else None
            reference_key = json.dumps({k: reference[k] for k in ("partition", "ink_class")} if reference else None, sort_keys=True)
            record_key += ":"+hashlib.sha256(reference_key.encode()).hexdigest()
            if record_key not in measurements:
                target_regions = set(word["mandatory_regions"])
                others = [w for w in claims[frame, n] if w["v_id"] != word["v_id"]
                          and not target_regions.intersection(w["mandatory_regions"]) and overlaps(box, w["bbox"])]
                markers = [dict(index=i, bbox=rosette_box(r), **r) for i, r in enumerate(rosettes.get(str(n), []))
                           if overlaps(box, rosette_box(r))]
                if scans:
                    if n not in images:
                        path = ROOT / "hayrat-pics" / f"page_{n}.png"
                        if digest(path) != raw[n]["image_sha256"]:
                            raise AssertionError("ownership evidence scan hash differs")
                        images[n] = open_rgb(path)
                    measured = measure(images[n], box, [w["bbox"] for w in others], [r["bbox"] for r in markers], reference)
                else:
                    measured = stored["measurements"][record_key]["pixels"]
                measurements[record_key] = dict(page=n, frame=frame, v_id=word["v_id"], original_bbox=box,
                    target_regions=word["mandatory_regions"],
                    other_word_claims=[{k: w[k] for k in ("v_id", "t", "verse", "word_in_verse", "kind", "form", "bbox", "mandatory_regions")} for w in others],
                    rosette_claims=markers, pixels=measured)
            measured = measurements[record_key]["pixels"]
            baseline_box = proposal(box, measured["possible"], measured["possible"])["bbox"]
            scan_hashes[str(n)] = raw[n]["image_sha256"]
        raw_outcome = outcome(box, label, case["support"])
        baseline = outcome(baseline_box, label, case["support"])
        for field in ("center_correct", "horizontal_boundary_pass"):
            if field in label and raw_outcome.get(field) != label[field]:
                raise AssertionError("source annotation outcome differs")
        for policy in POLICIES:
            proposed = proposal(box, measured["possible"], measured["policies"][policy]) if measured else None
            candidate_box = proposed["bbox"] if proposed else None
            candidate = outcome(candidate_box, label, case["support"])
            if raw_outcome.get("accepted") != candidate.get("accepted"):
                raise AssertionError("ownership diagnostic changed original acceptance")
            row = {k: label[k] for k in ("page", "physical_row", "lexical_position_rtl", "verse", "form", "t", "v_id", "sample_id") if k in label}
            row.update(raw_ocr_bbox=box, baseline_bbox=baseline_box, candidate_bbox=candidate_box,
                       raw_outcome=raw_outcome, baseline=baseline, candidate=candidate, measurement_key=record_key,
                       letter_core=label.get("rect", label.get("core_rect")),
                       ownership_evaluable=case["support"] is not None,
                       manual_reference_checks=reference_checks(box, candidate_box, measured["possible"], measured["policies"][policy], measured["clear_manual_reference"]) if measured else None)
            if proposed:
                row.update(proposal_status=proposed["status"], optional_ink_pixels=proposed["optional_ink_pixels"],
                           conditional_edge_support=proposed["conditional_edge_support"],
                           conditional_horizontal_invariant=proposed["horizontal_invariant"])
            if "boundary_eligible" in label:
                row["boundary_eligible"] = label["boundary_eligible"]
            if (proposed and proposed["conditional_edge_support"] is not None and label.get("boundary_eligible")):
                family = score_support(label["x_edges"], proposed["conditional_edge_support"], label["x_edge_tolerance"])
                family["correct_line"] = candidate["correct_line"]
                row["conditional_family_vs_fixed_label"] = family
            if "annotation" in label:
                row["original_extent_annotation"] = label["annotation"]
            row["regressions"] = regressions(row)
            grouped.setdefault(case["cohort"], {}).setdefault(case["method"], {}).setdefault(policy, []).append(row)
    groups = {cohort: {method: {policy: dict(summary=summarize(rows), details=rows,
                    retained_failures=[r for r in rows if is_failure(r, "baseline") or is_failure(r, "candidate")],
                    regressions=[r for r in rows if r["regressions"]])
                    for policy, rows in policies.items()} for method, policies in methods.items()}
              for cohort, methods in grouped.items()}
    helpers = ["ocr_ownership_evidence.py", "ocr_ink_trim.py", "ocr_corpus_sites.py", "word_boundary_ink_audit.py",
               "word_boundary_ownership_policy.py", "word_localization_validation.py", "semantic_validation.py", "image_io.py"]
    paths = [*EARLIER_INPUTS, FRESH, rm.OUTPUT, ROSETTES, cm.SOURCE, Path(__file__),
             *(ROOT / "tools" / name for name in helpers)]
    return dict(version="exposed-automatic-ownership-evidence-diagnostic-v7", groups=groups, measurements=measurements,
                scan_sha256=scan_hashes, inputs={p.name: digest(p) for p in paths},
                policies={"other_words": "Make ink inside other usable mandatory-word rectangles optional, excluding shared target-region IDs.",
                          "rosette_rectangles": "Make ink inside cached rosette rectangles optional; no size padding or recognition claims.",
                          "other_words_and_rosettes": "Union of the first two optional masks.",
                          "rosette_columns_stress": "Aggressive sensitivity test: project each overlapping rosette rectangle's x interval through the full original OCR box height."},
                protocol="Possible P is all thresholded in-box black/colored ink. Heuristic mandatory M excludes the policy's automatic claim mask. Compare H(M) with unmasked H(P), preserving vertical bounds and acceptance; empty M preserves the original box and has no ownership certificate. Record exact conditional horizontal supports for M subset S subset P. For clear, boundary-eligible manual partitions, independently count mandatory foreign ink, optionalized target ink and extra target pixels clipped by the candidate. Manual labels are evaluation only and never construct a proposal.",
                caveat="Every cohort, including the formerly fresh v6 sample, is exposed development here. Overlapping cohorts and methods must not be pooled. Automatic rectangles are evidence, not certified ownership: M may contain foreign ink and P may omit full-word ink outside the OCR box. Conditional invariance therefore cannot certify identity or complete word segmentation. All earlier labels/reports and conservative exclusions are unchanged. No mask is adopted or presented as fresh accuracy.")


def review(directory, report):
    """Highlight every scored regression or reference-confirmed extra clipping."""
    import numpy as np
    from PIL import Image, ImageDraw
    from image_io import open_rgb
    from ocr_ownership_evidence import ink_mask, rectangle_mask
    directory.mkdir(parents=True, exist_ok=True)
    chosen = {}
    for cohort, methods in report["groups"].items():
        for method, policies in methods.items():
            for policy, results in policies.items():
                for row in results["details"]:
                    ref = row.get("manual_reference_checks")
                    focus = cohort == "fresh_v6_now_development" and method == "original_broad" and is_failure(row, "baseline")
                    if row["regressions"] or ref and ref["extra_target_pixels_clipped"] or focus:
                        chosen[row["measurement_key"], policy, json.dumps(row["letter_core"])] = row
    for (key, policy, core_key), row in chosen.items():
        measurement = report["measurements"][key]
        n = measurement["page"]
        path = ROOT / "hayrat-pics" / f"page_{n}.png"
        if digest(path) != report["scan_sha256"][str(n)]:
            raise AssertionError("ownership review scan hash differs")
        image = open_rgb(path)
        box = row["raw_ocr_bbox"]
        left, top = max(0, box[0]-65), max(0, box[1]-20)
        right, bottom = min(image.width, box[2]+65), min(image.height, box[3]+20)
        crop = image.crop((left, top, right, bottom)).resize(((right-left)*3, (bottom-top)*3))
        sheet = Image.new("RGB", (crop.width, crop.height+65), "white")
        sheet.paste(crop, (0, 65))
        draw = ImageDraw.Draw(sheet)
        draw.text((0, 0), f'p{n} {row["verse"]} {policy}; 3x; post-exposure diagnostic', fill="black")
        draw.text((0, 16), "gray baseline; blue proposal; orange claims; green core; red clipped target pixels", fill="black")
        for x in range(((left+9)//10)*10, right, 10):
            draw.text(((x-left)*3, 42), str(x), fill="black")
        automatic = []
        if policy in {"other_words", "other_words_and_rosettes"}:
            automatic += [r["bbox"] for r in measurement["other_word_claims"]]
        if policy != "other_words":
            automatic += [r["bbox"] if policy != "rosette_columns_stress" else
                          [r["bbox"][0], box[1], r["bbox"][2], box[3]] for r in measurement["rosette_claims"]]
        for rect, color in [(r, "orange") for r in automatic]+[(row["baseline_bbox"], "gray"),
                           (row["candidate_bbox"], "blue"), (row["letter_core"], "green")]:
            if rect:
                draw.rectangle(((rect[0]-left)*3, (rect[1]-top)*3+65,
                                (rect[2]-left)*3-1, (rect[3]-top)*3+64), outline=color, width=2)
        reference = measurement["pixels"]["clear_manual_reference"]
        if reference is not None:
            truth = ink_mask(image, box, reference["ink_class"]) & rectangle_mask(box, [reference["partition"]])
            candidate = row["candidate_bbox"]
            excluded = np.zeros_like(truth)
            excluded[:, :candidate[0]-box[0]] = True
            excluded[:, candidate[2]-box[0]:] = True
            for y, x in np.argwhere(truth & excluded):
                px, py = (box[0]+int(x)-left)*3, (box[1]+int(y)-top)*3+65
                draw.rectangle((px, py, px+2, py+2), fill="red")
        core_digest = hashlib.sha256(core_key.encode()).hexdigest()[:8]
        sheet.save(directory / f'{measurement["frame"]}_p{n}_v{measurement["v_id"]}_{policy}_{key[-8:]}_{core_digest}.png')


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
            raise AssertionError("automatic ownership evidence diagnostic differs")
        print("PASS all ownership evidence, conditional supports, manual contradictions and retained cohorts")
    else:
        OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
    print("measurements", len(report["measurements"]), "scans", len(report["scan_sha256"]))
    for method, policies in report["groups"]["fresh_v6_now_development"].items():
        for policy, result in policies.items():
            print(method, policy, result["summary"])


if __name__ == "__main__":
    main()
