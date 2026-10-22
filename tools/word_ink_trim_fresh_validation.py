"""Locked, scan-first paired validation of original and ink-trimmed v5 boxes."""
import argparse
from collections import defaultdict
import json
from pathlib import Path

import ocr_corpus_map as cm
import ocr_corpus_sites as cs
import ocr_word_boundary_map as wm
import word_boundary_sites as ws
from ocr_ink_trim import measure, trim
from semantic_validation import DATA, ROOT
from word_boundary_ownership_policy import score_support
from word_ink_trim_fresh_sample import LABELS, MANUAL, PLAN, build, frozen_plan
from word_localization_validation import assess
from word_union_review import digest

LOCK = DATA / "audit_word_ink_trim_fresh_evaluation_lock_v6.json"
OUTPUT = DATA / "audit_word_ink_trim_fresh_validation_v6.json"
EVALUATION_SOURCES = ["word_ink_trim_fresh_sample.py", "word_boundary_extent_review.py",
                      "word_boundary_fresh_sample.py", "word_boundary_ownership_policy.py",
                      "word_localization_validation.py", "ocr_ink_trim.py", "semantic_validation.py", "image_io.py"]


def evaluation_lock():
    # This path hashes frozen artifacts but never opens selected predictions.
    frozen_plan()
    manual = json.loads(MANUAL.read_text())
    if build(False, manual) != manual:
        raise AssertionError("scan-first ink-trim labels differ before evaluation")
    sources = [Path(__file__)] + [ROOT / "tools" / name for name in EVALUATION_SOURCES]
    return dict(version="scan-first-ink-trim-evaluation-lock-v6",
                stage="all_scan_labels_saved_before_selected_predictions_read",
                inputs={p.name: digest(p) for p in (PLAN, LABELS, MANUAL)},
                evaluation_sources={p.name: digest(p) for p in sources},
                protocol="All 54 scheduled slots labelled or explicitly unavailable before first selected prediction comparison. Letter-core inclusion scores centers, recomputed after horizontal trimming. The earlier 12px tolerance, fixed-edge denominator and exact all-ownership denominator are retained, including abstentions. Generic unresolved ownership and partition contact remain unscorable. Four paired dependent methods: original/trimmed broad and original/trimmed conservative. Every failure and regression is retained. No subsequent label/evaluator/inference retuning in this report; corrections require a separate post-exposure artifact.")


def assess_label(box, label):
    if label.get("status") == "unavailable":
        return dict(status="unavailable")
    result = assess(dict(bbox=box), label)
    score = None
    if not label["ownership_evaluable"]:
        ownership = "unscorable"
    elif box is None:
        ownership = "abstained"
    else:
        score = score_support([box[0], box[2]], label["edge_support"], label["x_edge_tolerance"])
        ownership = score["ownership_outcome"] if result["correct_line"] else "wrong_line"
    result.update(all_ownership_outcome=ownership, ownership_error=score,
                  all_ownership_boundary_pass=(ownership == "all_pass") if label["ownership_evaluable"] else None)
    return result


def summarize(details):
    rows = [r for r in details if r["status"] != "unavailable"]
    return dict(scheduled=len(details), labelled=len(rows), unavailable=len(details)-len(rows),
                accepted=sum(r["accepted"] for r in rows), correct_centers=sum(r["center_correct"] for r in rows),
                wrong_accepted=sum(r["accepted"] and not r["center_correct"] for r in rows),
                abstentions=sum(not r["accepted"] for r in rows),
                boundary_evaluable=sum(r["boundary_eligible"] for r in rows),
                boundary_pass=sum(r["horizontal_boundary_pass"] for r in rows),
                ownership_evaluable=sum(r["ownership_evaluable"] for r in rows),
                all_ownership_boundary_pass=sum(r["all_ownership_boundary_pass"] is True for r in rows),
                ownership_sensitive=sum(r["all_ownership_outcome"] == "ownership_sensitive" for r in rows),
                unscorable_boundaries=sum(not r["ownership_evaluable"] for r in rows))


def paired(before, after):
    if len(before) != len(after):
        raise AssertionError("paired inventory length differs")
    transitions = {name: dict(both_pass=0, rescued=0, regressed=0, both_fail=0)
                   for name in ("center", "fixed_boundary", "all_ownership_boundary")}
    changes, regressions = [], []
    for old, new in zip(before, after):
        key = lambda r: (r["page"], r["physical_row"], r["lexical_position_rtl"])
        if key(old) != key(new) or (old["status"] == "unavailable") != (new["status"] == "unavailable"):
            raise AssertionError("paired physical positions differ")
        if old["status"] == "unavailable":
            continue
        if old["accepted"] != new["accepted"]:
            raise AssertionError("trimming changed frozen acceptance")
        fields = [("center", "center_correct", True),
                  ("fixed_boundary", "horizontal_boundary_pass", old["boundary_eligible"]),
                  ("all_ownership_boundary", "all_ownership_boundary_pass", old["ownership_evaluable"])]
        lost = []
        for name, field, eligible in fields:
            if not eligible:
                continue
            a, b = bool(old[field]), bool(new[field])
            status = "both_pass" if a and b else "regressed" if a else "rescued" if b else "both_fail"
            transitions[name][status] += 1
            if status == "regressed":
                lost.append(name)
        changed = old.get("bbox") != new.get("bbox")
        if changed or lost:
            detail = {k: old[k] for k in ("page", "physical_row", "lexical_position_rtl", "verse", "form")}
            detail.update(original_bbox=old.get("bbox"), trimmed_bbox=new.get("bbox"),
                          original_center_correct=old["center_correct"], trimmed_center_correct=new["center_correct"],
                          original_boundary_pass=old["horizontal_boundary_pass"], trimmed_boundary_pass=new["horizontal_boundary_pass"],
                          original_all_ownership_pass=old["all_ownership_boundary_pass"],
                          trimmed_all_ownership_pass=new["all_ownership_boundary_pass"], regressions=lost)
            changes.append(detail)
            if lost:
                regressions.append(detail)
    return dict(transitions=transitions, changed_boxes=len(changes), changes=changes, regressions=regressions)


def prediction_pages(manual):
    frozen = json.loads(ws.OUTPUT.read_text())
    mapping = json.loads(wm.OUTPUT.read_text())
    raw = {p["page"]: p for p in json.loads(cm.SOURCE.read_text())["pages"]}
    if frozen["inputs"][wm.OUTPUT.name] != digest(wm.OUTPUT):
        raise AssertionError("conservative policy refers to other broad predictions")
    for path in (cm.SOURCE, cm.mt.TOKENS_F):
        if mapping["inputs"][path.name] != digest(path):
            raise AssertionError("frozen prediction input hash differs")
    selected = {p["page"] for p in manual["pages"]}
    broad = {}
    for page in mapping["pages"]:
        n = page["page"]
        if n not in selected:
            continue
        rows = []
        if page["status"] == "conditional_word_window_match":
            for word in page["words"]:
                row, _ = cs.site(word, raw[n]["regions"])
                if row is not None:
                    rows.append(row)
        broad[n] = dict(page=n, image_sha256=page["image_sha256"], words=rows)
    conservative = {p["page"]: p for p in frozen["pages"] if p["page"] in selected}
    return {"broad": broad, "conservative": conservative}


def analyze(scans=False, stored=None):
    # Must pass the scan-label/evaluator lock BEFORE any prediction JSON is opened.
    if evaluation_lock() != json.loads(LOCK.read_text()):
        raise AssertionError("ink-trim scan labels or evaluator changed after lock")
    manual = json.loads(MANUAL.read_text())
    policies = prediction_pages(manual)
    measurements, images, methods = {}, {}, {}
    for policy, pages in policies.items():
        for variant in ("original", "trimmed"):
            details = []
            for page in manual["pages"]:
                n = page["page"]
                if pages[n]["image_sha256"] != page["image_sha256"]:
                    raise AssertionError("frozen prediction and independent scan hashes differ")
                words = {w["v_id"]: w for w in pages[n]["words"]}
                if len(words) != len(pages[n]["words"]):
                    raise AssertionError("duplicate token within frozen selected page")
                for label in page["word_samples"]:
                    if label.get("status") == "unavailable":
                        details.append(dict(page=n, **label))
                        continue
                    word = words.get(label["v_id"], {})
                    if word and (word["t"], word["form"]) != (label["t"], label["form"]):
                        raise AssertionError("prediction/scan token identity differs")
                    box, measurement_key = word.get("bbox"), None
                    original_box = box
                    if variant == "trimmed" and box is not None:
                        measurement_key = f"{n}:"+":".join(map(str, box))
                        if measurement_key not in measurements:
                            if scans:
                                from image_io import open_rgb
                                if n not in images:
                                    path = ROOT / "hayrat-pics" / f"page_{n}.png"
                                    if digest(path) != page["image_sha256"]:
                                        raise AssertionError("fresh trim scan hash differs")
                                    images[n] = open_rgb(path)
                                pixels = measure(images[n], box)
                            else:
                                pixels = stored["trim_measurements"][measurement_key]["pixels"]
                            measurements[measurement_key] = dict(page=n, original_bbox=box, pixels=pixels, **trim(box, pixels))
                        box = measurements[measurement_key]["bbox"]
                        if not (original_box[0] <= box[0] < box[2] <= original_box[2] and box[1::2] == original_box[1::2]):
                            raise AssertionError("candidate expanded or changed vertical bounds")
                    details.append(dict(page=n, **label, **assess_label(box, label),
                                        original_bbox=original_box, trim_measurement_key=measurement_key))
            groups = {}
            for key in ("page", "physical_row", "lexical_position_rtl"):
                subsets = defaultdict(list)
                for row in details:
                    subsets[row[key]].append(row)
                groups[key] = {str(k): summarize(rows) for k, rows in sorted(subsets.items())}
            methods[f"{variant}_{policy}"] = dict(summary=summarize(details), groups=groups, details=details,
                failures=[r for r in details if r["status"] != "unavailable" and
                          (not r["center_correct"] or r["boundary_eligible"] and not r["horizontal_boundary_pass"]
                           or r["ownership_evaluable"] and not r["all_ownership_boundary_pass"])],
                unscorable_boundaries=[r for r in details if r["status"] != "unavailable" and not r["ownership_evaluable"]])
    pairs = {policy: paired(methods[f"original_{policy}"]["details"], methods[f"trimmed_{policy}"]["details"])
             for policy in policies}
    return dict(version="locked-scan-first-paired-ink-trim-validation-v6", methods=methods, paired_comparisons=pairs,
                trim_measurements=measurements,
                inputs={p.name: digest(p) for p in (PLAN, LABELS, MANUAL, LOCK, wm.OUTPUT, ws.OUTPUT)},
                caveat="Fresh scan-first labels for the frozen candidate, but one AI reader and structured physical positions, not independent double annotation or uniform-word corpus accuracy. Four dependent methods share scans, OCR, identities and acceptance. Fixed-edge and exact all-ownership scoring retain their separate denominators including abstentions. Generic ownership uncertainty and unavailable physical slots remain explicit. Horizontal tolerance does not certify complete word segmentation. All original failures, rescues and regressions retained; no retuning after comparison.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--lock", action="store_true")
    modes.add_argument("--build", action="store_true")
    modes.add_argument("--verify", action="store_true")
    parser.add_argument("--scans", action="store_true")
    args = parser.parse_args()
    if args.lock:
        report = evaluation_lock()
        if LOCK.exists() and report != json.loads(LOCK.read_text()):
            raise AssertionError("existing scan-first evaluation lock differs; preserve it")
        LOCK.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
        print("Saved complete scan-label and evaluator lock before selected prediction comparison")
        return
    saved = json.loads(OUTPUT.read_text()) if args.verify else None
    report = analyze(scans=args.build or args.scans, stored=saved)
    if args.verify:
        if report != saved:
            raise AssertionError("fresh paired ink-trim validation differs")
        print("PASS frozen paired ink-trim validation, labels/evaluator lock, all outcomes and regressions")
    else:
        OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
    for method, result in report["methods"].items():
        print(method, result["summary"])
        for row in result["failures"]:
            print("failure", row["page"], row["physical_row"], row["lexical_position_rtl"], row["verse"], row["form"],
                  row["status"], row.get("bbox"), row.get("signed_x_edge_errors"), row["all_ownership_outcome"])
    for policy, result in report["paired_comparisons"].items():
        print("paired", policy, result["transitions"], "regressions", result["regressions"])


if __name__ == "__main__":
    main()
