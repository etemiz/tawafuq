"""Frozen broad/conservative v5 comparison after scan-first labels are saved."""
import argparse
from collections import defaultdict
import json
from pathlib import Path

import ocr_corpus_map as cm
import ocr_corpus_sites as cs
import ocr_word_boundary_map as wm
import word_boundary_sites as ws
from semantic_validation import DATA
from word_boundary_fresh_sample import MANUAL, LABELS, PLAN, build, frozen_plan
from word_localization_validation import assess
from word_union_review import digest

LOCK = DATA / "audit_word_boundary_fresh_evaluation_lock_v5.json"
OUTPUT = DATA / "audit_word_boundary_fresh_validation_v5.json"


def evaluation_lock():
    # Freeze label/evaluator hashes without opening a prediction JSON.
    frozen_plan()
    manual = json.loads(MANUAL.read_text())
    if build(False, manual) != manual:
        raise AssertionError("scan-first annotation replay differs before evaluation")
    sources = (Path(__file__), Path(__file__).with_name("word_localization_validation.py"))
    return dict(version="scan-first-v5-evaluation-lock", stage="labels_saved_before_selected_predictions_read",
                inputs={p.name: digest(p) for p in (PLAN, LABELS, MANUAL)},
                evaluation_sources={p.name: digest(p) for p in sources},
                protocol="Lock created after saving all 54 scan-first slots, before first selected-prediction "
                "comparison. Core inclusion scores centers; earlier 12px horizontal edge convention is "
                "retained. Unavailable positions stay outside the word denominator; label-eligible boundaries "
                "stay in the boundary denominator even if a mapper abstains. All failures retained. "
                "Any later label correction must be explicitly post-exposure with the original result retained.")


def summarize(details):
    labelled = [r for r in details if r["status"] != "unavailable"]
    return dict(scheduled=len(details), labelled=len(labelled), unavailable=len(details)-len(labelled),
                accepted=sum(r["accepted"] for r in labelled),
                correct_centers=sum(r["center_correct"] for r in labelled),
                wrong_accepted=sum(r["accepted"] and not r["center_correct"] for r in labelled),
                abstentions=sum(not r["accepted"] for r in labelled),
                boundary_evaluable=sum(r["boundary_eligible"] for r in labelled),
                boundary_pass=sum(r["horizontal_boundary_pass"] for r in labelled))


def analyze():
    if evaluation_lock() != json.loads(LOCK.read_text()):
        raise AssertionError("scan-first v5 labels or evaluation rules changed after lock")
    manual = json.loads(MANUAL.read_text())
    frozen_sites = json.loads(ws.OUTPUT.read_text())
    if frozen_sites["inputs"][wm.OUTPUT.name] != digest(wm.OUTPUT):
        raise AssertionError("broad v5 predictions differ from frozen site-policy input")
    mapping = json.loads(wm.OUTPUT.read_text())
    for path in (cm.SOURCE, cm.mt.TOKENS_F):
        if mapping["inputs"][path.name] != digest(path):
            raise AssertionError("fresh validation corpus/OCR input hashes differ")
    raw = {p["page"]: p for p in json.loads(cm.SOURCE.read_text())["pages"]}
    selected = {p["page"] for p in manual["pages"]}
    broad, conservative = {}, {p["page"]: p for p in frozen_sites["pages"] if p["page"] in selected}
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
    methods = {}
    for method, pages in (("broad_v5", broad), ("conservative_v5", conservative)):
        details = []
        for page in manual["pages"]:
            predicted = pages[page["page"]]
            if predicted["image_sha256"] != page["image_sha256"]:
                raise AssertionError("prediction and independent annotation scan hashes differ")
            words = {w["v_id"]: w for w in predicted["words"]}
            if len(words) != len(predicted["words"]):
                raise AssertionError("duplicate virtual token within selected page")
            for label in page["word_samples"]:
                if label.get("status") == "unavailable":
                    details.append(dict(page=page["page"], **label))
                else:
                    row = words.get(label["v_id"], {})
                    if row and (row["t"], row["form"]) != (label["t"], label["form"]):
                        raise AssertionError("prediction and annotation token identity differs")
                    outcome = assess(row, label)
                    details.append(dict(page=page["page"], **label, **outcome))
        groups = {}
        for key in ("page", "physical_row", "lexical_position_rtl"):
            subsets = defaultdict(list)
            for row in details:
                subsets[row[key]].append(row)
            groups[key] = {str(k): summarize(rows) for k, rows in sorted(subsets.items())}
        methods[method] = dict(summary=summarize(details), groups=groups, details=details,
                               failures=[r for r in details if r["status"] != "unavailable"
                                         and (not r["center_correct"] or (r["boundary_eligible"] and not r["horizontal_boundary_pass"]))])
    return dict(version="fresh-physical-position-validation-v5", methods=methods,
                inputs={p.name: digest(p) for p in (PLAN, LABELS, MANUAL, LOCK, wm.OUTPUT, ws.OUTPUT)},
                caveat="Fresh for frozen v5 inference/policy; one AI reader, structured physical positions, "
                "no independent double annotation or uniform-word corpus accuracy estimate. Two unavailable "
                "positions remain explicit. Center cores are separate from measured horizontal ink extents; "
                "uncertain mark ownership/contact is unscorable. The broad/conservative methods share "
                "images, OCR and labels and are dependent. No inference rule retuned after evaluation.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--lock", action="store_true")
    modes.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.lock:
        LOCK.write_text(json.dumps(evaluation_lock(), ensure_ascii=False, indent=2)+"\n")
        print("Saved scan-first annotation and evaluation hashes before prediction comparison")
        return
    report = analyze()
    if args.verify:
        if report != json.loads(OUTPUT.read_text()):
            raise AssertionError("fresh v5 physical-position validation differs")
        print("PASS fresh v5 validation, frozen labels/rules and every scheduled outcome")
    else:
        OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
    for method, result in report["methods"].items():
        print(method, result["summary"])
        for row in result["failures"]:
            print("failure", row["page"], row["physical_row"], row["lexical_position_rtl"], row["verse"],
                  row["form"], row["status"], row.get("bbox"), row.get("signed_x_edge_errors"),
                  "boundary eligible", row["boundary_eligible"])


if __name__ == "__main__":
    main()
